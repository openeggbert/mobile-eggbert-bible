# Chapter 49: Helper

Despite its generic name, `Helper` is not a grab-bag of miscellaneous utilities the way `Misc`
(covered in [Chapter 48](ch48-misc-utility-functions.md)) is. Reading the actual source shows it
does exactly one thing: it provides a minimal, C#-style string formatter — a small reimplementation
of the pattern `String.Format("{0} of {1}", a, b)` from .NET, for a C++ codebase that otherwise
uses `std::string` and `std::to_string`. It is declared in
`include/WindowsPhoneSpeedyBlupi/Helper.hpp` (71 lines) and implemented in
`src/WindowsPhoneSpeedyBlupi/Helper.cpp` (47 lines) — both among the smallest files in the whole
project.

Unlike `TinyPoint`, `TinyRect`, and `Misc`, `Helper` is explicitly **not** a port of original game
logic. Its header says so directly:

*From `Helper.hpp:1-7`:*
```cpp
/**
 * @file Helper.hpp
 * @brief Declarations for the Helper static utility class and related macros.
 * @details Provides a lightweight C#-style string formatter and convenience
 *          macros used throughout the port.  This file is not part of the
 *          original game logic; it was added during the C++ porting effort.
 */
```

The file's authorship comment confirms it was written specifically for this port:

*From `Helper.hpp:9-11`:*
```cpp
//
// Created by robertvokac on 5/28/25.
//
```

So where `Misc` and `Def` (and `TinyPoint`/`TinyRect`) carry forward structures and constants
that existed in the original C# WindowsPhoneSpeedyBlupi codebase, `Helper` is scaffolding the
porting effort itself introduced, to bridge a gap between how the original C# code formatted
strings and how idiomatic C++ does it.

## Why this exists: bridging C# `String.Format` to C++

The original C# code, decompiled via ILSpy (see
[Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)), makes
use of C#'s built-in `string.Format("template {0} {1}", arg0, arg1)` idiom — a positional
placeholder substitution mechanism with no direct standard-library equivalent in C++ (C++20's
`std::format` did not yet exist as a target/dependency for this codebase, or was avoided for
portability). `Helper::formatString` fills that gap with a hand-written substitute that mimics
the same `{N}` placeholder syntax, letting ported call sites read almost identically to their C#
originals.

## The two support macros

Alongside the `Helper` class itself, the header defines two convenience macros meant to be used
together with `formatString` at call sites:

*From `Helper.hpp:18-32`:*
```cpp
/**
 * @def TO_STRING(a)
 * @brief Converts a numeric value to its std::string representation.
 * @details Thin wrapper around std::to_string() for brevity in call sites.
 * @param a Value to convert.
 */
#define TO_STRING(a) std::to_string(a)

/**
 * @def STRING_VECTOR(items)
 * @brief Creates a std::vector<string> from a brace-enclosed initialiser list.
 * @details Intended for single-expression use at call sites of Helper::formatString().
 * @param items Comma-separated string literals or std::string values.
 */
#define STRING_VECTOR(items) std::vector<string>{items}
```

`TO_STRING(a)` is nothing more than `std::to_string(a)` under a shorter name — purely a
readability/brevity aid at call sites that build argument vectors inline. `STRING_VECTOR(items)`
wraps a comma-separated list of strings into a `std::vector<string>{...}` literal, again purely
for terseness where `formatString` is called with several inline arguments.

## Helper::formatString: the core implementation

The class itself has a single static method:

*From `Helper.hpp:46-66`:*
```cpp
class Helper
{
public:
    /**
     * @brief Formats a string by substituting @c {N} placeholders with @p args.
     *
     * @details Iterates over @p args in index order.  For each element at index
     *          @c i, all occurrences of the literal token @c {i} in @p format
     *          are replaced with @c args[i].  If the format string contains a
     *          placeholder whose index is greater than or equal to
     *          @c args.size(), that placeholder is left unchanged in the output
     *          (no exception is thrown and no truncation occurs).
     *
     * @param[in] format Template string containing @c {0}, @c {1}, … tokens.
     * @param[in] args   Ordered replacement strings; index @c i replaces @c {i}.
     * @return Formatted string with all recognised placeholders substituted.
     *
     * @note Out-of-range placeholder indices are silently preserved as-is.
     */
    static std::string formatString(const std::string& format, const std::vector<std::string>& args);
};
```

And the actual implementation in `Helper.cpp`:

*From `Helper.cpp:27-44`:*
```cpp
std::string Helper::formatString(
    const std::string& format,
    const std::vector<std::string>& args
) {
    std::string result = format;

    for (size_t i = 0; i < args.size(); ++i) {
        std::string placeholder = "{" + std::to_string(i) + "}";

        size_t pos = 0;
        while ((pos = result.find(placeholder, pos)) != std::string::npos) {
            result.replace(pos, placeholder.length(), args[i]);
            pos += args[i].length();
        }
    }

    return result;
}
```

The algorithm is a straightforward nested loop: for each argument index `i` from `0` to
`args.size() - 1`, build the literal token `"{i}"` (e.g. `"{0}"`, `"{1}"`), then scan the
(mutating) result string with `std::string::find` in a loop, replacing every occurrence of that
token with `args[i]`.

### Documented edge-case behavior

The implementation's own file-level comment is unusually explicit about two edge cases, both of
which are worth quoting directly since they define real, observable behavior rather than
incidental implementation detail:

*From `Helper.cpp:6-19`:*
```cpp
/**
 * ### Edge-case behaviour for out-of-range placeholder indices
 * The implementation iterates only over indices 0 … args.size()-1.
 * Any placeholder @c {N} in @p format whose index @c N is greater than or
 * equal to @c args.size() is never visited and is therefore left verbatim in
 * the returned string.  No exception is thrown and no empty string is
 * substituted — the original token is preserved unchanged.
 *
 * ### Multiple occurrences of the same placeholder
 * Each placeholder token @c {N} is replaced in a single pass using
 * @c std::string::find in a loop.  All occurrences are replaced.  The search
 * position advances past each replacement to avoid re-scanning already-
 * substituted text, so self-referential placeholders (e.g. a replacement that
 * itself contains @c {N}) are not processed recursively.
 */
```

Concretely:

1. **Out-of-range placeholders are left alone.** `formatString("Hello {0}, you are {1}", {"Bob"})`
   returns `"Hello Bob, you are {1}"` — the `{1}` token survives verbatim because the loop never
   reaches index `1`. There is no bounds check that throws or logs; a caller who miscounts
   arguments simply gets a partially-formatted string with a literal `{N}` visible in the output.
2. **Every occurrence of a repeated placeholder is substituted**, not just the first. If
   `"{0}"` appears three times in the format string, all three are replaced with `args[0]`.
3. **Replacements are not re-scanned for further placeholders.** Because `pos` is advanced past
   each freshly-inserted replacement (`pos += args[i].length()`), if an argument string itself
   happens to contain the literal text `"{0}"`, that text is *not* recursively expanded — it is
   left as plain text in the output. This prevents infinite loops or unexpected recursive
   expansion, at the cost of not supporting nested formatting.

## Real call sites

`Helper::formatString` is used at six locations in the codebase — in `Game1.cpp` (UI/HUD text
composition) and `Decor.cpp` (in-game HUD text). A representative pair from `Decor.cpp`, building
the on-screen "current character" and "treasure count" HUD strings:

*From `Decor.cpp:1207`:*
```cpp
string text = Helper::formatString("= {0}", STRING_VECTOR(std::to_string(m_blupiPerso)));
```

*From `Decor.cpp:1245`:*
```cpp
string text = Helper::formatString("{0}/{1}", std::vector{TO_STRING(m_nbTresor), TO_STRING(m_totalTresor)});
```

The second example shows the `TO_STRING` macro in use directly inside a `std::vector` braced
initializer (rather than via `STRING_VECTOR`), producing a two-element argument vector from two
integer member variables — the current and total treasure counts — substituted into the
`"{0}/{1}"` template to build a string like `"3/12"`.

`Game1.cpp` uses the same pattern to localize numeric HUD text pulled from `MyResource` (the
string-resource/localization system covered in
[Chapter 46](../part08-data-persistence-content/ch46-myresource-resource-management.md)):

*From `Game1.cpp:881,888,895` (structure, argument substituted from a resource string):*
```cpp
text = Helper::formatString(MyResource::LoadString(MyResource::TX_GAMER_MDOORS), ...);
text = Helper::formatString(MyResource::LoadString(MyResource::TX_GAMER_SDOORS), ...);
text = Helper::formatString(MyResource::LoadString(MyResource::TX_GAMER_LIFES), ...);
```

Here the *format string itself* is loaded from a localized resource table rather than hard-coded
in the source — meaning translators can freely reorder `{0}`/`{1}` tokens per language (e.g. to
accommodate a language where the natural word order differs) without touching any C++ code, which
is precisely the kind of flexibility the C#-style positional-placeholder format was designed for
in the first place.

## Summary

`Helper` is a single-purpose, minimal string-formatting utility — not a general "helper"
grab-bag — introduced purely as porting scaffolding to let C++ call sites mirror the original C#
codebase's `String.Format`-style HUD and UI text construction, one placeholder-substitution
function (`formatString`) plus two small convenience macros (`TO_STRING`, `STRING_VECTOR`) that
exist only to make its call sites terser.

## See also

- [Chapter 48: Misc — Utility Functions](ch48-misc-utility-functions.md) — the other small
  static-utility class in this part, covering geometry rather than strings.
- [Chapter 46: MyResource — Resource Management](../part08-data-persistence-content/ch46-myresource-resource-management.md) —
  the localized string-resource system whose loaded template strings are frequently passed
  straight into `Helper::formatString`.
- [Chapter 12: Game1 — the State Machine](../part03-architecture/ch12-game1-state-machine.md) — a
  primary caller of `Helper::formatString` for HUD text composition.
- [Chapter 55: ILSpy Decompilation and C# Stubs](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md) —
  more on the C#-to-C++ porting effort `Helper` was written to support.
