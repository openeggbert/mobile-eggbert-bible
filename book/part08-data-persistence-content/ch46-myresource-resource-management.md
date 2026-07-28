# Chapter 46: MyResource — Localized String Resources

## What `MyResource` actually is

The name `MyResource`, and this chapter's position in a "Data, Persistence, and Content" part of
the book, might suggest a general-purpose asset or resource manager — something that loads and
tracks textures, sounds, or files. Reading `MyResource.hpp` (364 lines) and `MyResource.cpp` (662
lines) in full shows this is not the case at all: **`MyResource` is exclusively a localized UI
string table.** It maps integer resource IDs to human-readable strings — button labels, HUD text,
tutorial hints — for one of up to three spoken languages. It has no relationship whatsoever to
textures, sound effects, or the `Content/` pipeline covered in
[Chapter 45](ch45-content-pipeline.md); it never touches a `ContentManager`, a file handle, or
`IsolatedStorage`. The class's own file-level documentation is unambiguous about this:

*From `MyResource.hpp:1-9`:*
```cpp
/**
 * @file MyResource.hpp
 * @brief Declares the MyResource class, which provides localised UI strings.
 *
 * @details
 * MyResource is the C++ port of the original Windows Phone C# resource table.
 * It maps integer resource IDs (the TX_* constants) to localised strings for
 * one of three supported locales: French ("fr"), English (default), or German
 * ("de").
```

The name `MyResource` is itself a direct carry-over from the original C# codebase's naming, where
`.resx`-style resource classes are conventionally auto-generated with names like `Resource` or
`Resources` by Visual Studio's resource designer — the `My` prefix most likely exists simply to
avoid colliding with a framework-reserved `Resource` identifier, a common pattern in hand-ported
Windows Phone code (see [Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
for more on this codebase's ILSpy-decompilation lineage). This is a genuinely useful finding for
anyone approaching the file cold: despite living in a chapter about "resource management," and
despite its generic-sounding name, `MyResource` is purely a **localization string table** — the
data-pipeline sibling to compare it against is `Content/` (icons, sounds, backgrounds — the actual
binary assets), while `MyResource` is closer in spirit to a `.po`/`.resx` translation catalog.

## Resource IDs: the `TX_*` constant groups

Every string `MyResource` knows about is addressed by an integer ID, exposed as a `static const
intcs` constant named `TX_*`. There is no enum — each ID is an individually declared class-static
constant, grouped by a numeric range convention documented at the top of the header:

*From `MyResource.hpp:62-74`:*
```cpp
     * Resource-ID ranges:
     *  - 100–113  Button / menu labels (TX_BUTTON_*, TX_BUTTON_SETUP_*,
     *             TX_BUTTON_RANKING)
     *  - 200–203  Gamer / ranking screen labels (TX_GAMER_*)
     *  - 300–305  Trial-mode upsell lines (TX_TRIAL*)
     *  - 1000–1022 Training world 1 d-pad hints (TX_TRAINING1xx)
     *  - 2000–2009 Training world 2 d-pad hints (TX_TRAINING2xx)
     *  - 3000–3010 Training world 3 d-pad hints (TX_TRAINING3xx)
     *  - 4000–4009 Training world 4 d-pad hints (TX_TRAINING4xx)
     *  - 11000–11022 Training world 1 accelerometer hints (TX_TRAINING1xxa)
     *  - 12000–12009 Training world 2 accelerometer hints (TX_TRAINING2xxa)
     *  - 13000–13010 Training world 3 accelerometer hints (TX_TRAINING3xxa)
     *  - 14000–14009 Training world 4 accelerometer hints (TX_TRAINING4xxa)
```

The ranges are non-contiguous in a telling way: ID `106` is deliberately absent from the
button/menu group (`100`–`113`), and the surrounding source comment confirms this is not an
oversight in the port but a preserved gap from the original resource table:

*From `MyResource.cpp:93-96`:*
```cpp
    // -----------------------------------------------------------------------
    // Static constant definitions — UI button / menu labels (IDs 100-113)
    // ID 106 is intentionally absent from the original game resource table.
    // -----------------------------------------------------------------------
```

`TX_BUTTON_PLAY` = `100`, `TX_BUTTON_MENU` = `101`, ..., `TX_BUTTON_BUY` = `105`, then a gap, then
`TX_BUTTON_SETUP` = `107` onward (`MyResource.cpp:98-110`). This is a small but genuine artifact of
one-to-one ID preservation across the C#-to-C++ port: rather than renumbering IDs to be dense, the
port keeps the original numeric gaps exactly, which is only possible/sensible because — unlike
`GameData`'s byte-array offsets ([Chapter 43](ch43-gamedata-save-format.md)) — nothing about
`MyResource`'s ID values is serialized to disk; the IDs only ever need to be *self-consistent*
between the constant declarations and the `unordered_map` lookup table, never binary-compatible
with an external save format. The gap survives purely as documentation of provenance, not as a
functional requirement.

The four "training world" groups (IDs `1000`–`4009` and their accelerometer-variant mirrors
`11000`–`14009`) are the largest by far — 84 base hint strings, doubled to 168 once the
accelerometer variants are counted — because they cover the game's four tutorial levels
(`TX_TRAINING1xx` through `TX_TRAINING4xx`), each hint duplicated once for players using the
on-screen directional wheel and once for players using tilt/accelerometer controls (see
[Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md)). A representative
sample of what these IDs actually mean, taken from the header's own per-constant documentation:

*From `MyResource.hpp:125-147` (excerpted):*
```cpp
        static const intcs TX_TRAINING101; ///< @brief Tutorial hint 1-01: how to use the directional wheel (d-pad variant) (ID 1000).
        static const intcs TX_TRAINING102; ///< @brief Tutorial hint 1-02: how to use the Jump button (ID 1001).
        static const intcs TX_TRAINING105; ///< @brief Tutorial hint 1-05: avoid falling into water (ID 1004).
        static const intcs TX_TRAINING119; ///< @brief Tutorial hint 1-19: eggs give extra lives (ID 1018).
        static const intcs TX_TRAINING122; ///< @brief Tutorial hint 1-22: go to the red arrow to finish (ID 1021).
```

and the accelerometer mirror of the very first one:

*From `MyResource.hpp:201`:*
```cpp
        static const intcs TX_TRAINING101a; ///< @brief Accelerometer variant of TX_TRAINING101: tilt the phone (ID 11000).
```

The trailing `a` suffix on the C++ constant name (`TX_TRAINING101a` vs. `TX_TRAINING101`) is the
only naming distinction between the two control-scheme variants; both variants' underlying text
usually differs only in which control is being described (the on-screen wheel vs. tilting the
device), and several of the "empty" hint slots (`TX_TRAINING106`, `TX_TRAINING109`,
`TX_TRAINING111`, and their peers) are genuinely blank strings in every locale — these correspond
to tutorial beats that apparently need no text prompt at all, but still consume an ID for
positional consistency with the sequence of in-level trigger zones that request hints by number.

## Lazy initialization and locale detection

`MyResource`'s public interface is a single method, `LoadString(intcs res)`, guarded by a
lazily-triggered one-time initializer:

*From `MyResource.cpp:69-91`:*
```cpp
    void MyResource::EnsureInitialized()
    {
        static const bool initialized = []()
        {
            Init();
            return true;
        }();
        (void)initialized;
    }

    const string& MyResource::LoadString(const intcs res)
    {
        EnsureInitialized();

        auto it = resources.find(res);
        if (it != resources.end())
        {
            return it->second;
        }

        static const string DEFAULT_VALUE = "???";
        return DEFAULT_VALUE;
    }
```

The `static const bool initialized = [](){ ... }();` idiom is the standard C++11 "magic static"
pattern: the immediately-invoked lambda runs exactly once, on the first call to
`EnsureInitialized()` from any call site, with thread-safe initialization guaranteed by the
language runtime — a clean way to defer the (comparatively expensive, hundreds of `unordered_map`
insertions) population of the string table until it is actually needed, without a separate explicit
"did I already initialize?" boolean flag to maintain by hand. An unknown resource ID — one that was
never `emplace`d into the table — resolves to the sentinel string `"???"` rather than throwing or
asserting, which fails visibly but non-fatally in the UI if a `TX_*` ID is ever referenced before
its corresponding language's `Initialize*()` function defines it.

Locale detection happens exactly once, inside `Init()`, by asking the C++ standard library for the
platform's default locale name and inspecting its first two characters:

*From `MyResource.cpp:272-307`:*
```cpp
    void MyResource::Init()
    {
        std::string languageCode = "en";

        try
        {
            std::locale loc("");
            std::string localeName = loc.name();

            if (localeName.size() >= 2)
            {
                languageCode = localeName.substr(0, 2);
                std::transform(
                    languageCode.begin(),
                    languageCode.end(),
                    languageCode.begin(),
                    [](unsigned char c)
                    {
                        return static_cast<char>(std::tolower(c));
                    });
            }
        }
        catch (...)
        {
            languageCode = "en";
        }

        if (languageCode == "fr")
        {
            InitializeFR();
        }
        else
        {
            InitializeEN();
        }
    }
```

`std::locale("")` constructs a locale object from the platform's own default (on POSIX systems,
typically driven by the `LANG`/`LC_ALL` environment variables; on other platforms, whatever the OS
reports). If that constructor throws — the documentation calls out "a minimal embedded system with
no locale support" as the motivating case — the `catch (...)` block falls back to `"en"` rather
than propagating the exception, so a missing or misconfigured locale environment can never crash
string lookup; it just silently means English. **The active language is detected once, at
first-use, and cannot be changed at runtime** — there is no `SetLanguage()` method anywhere in
`MyResource`'s interface, and no in-game language-selection UI is wired to this class from what
`Game1.cpp` calls. Language is a pure function of the host platform's locale setting at the moment
the very first `LoadString()` call happens to occur.

## Three locales in the source, two actually reachable

The class header documents three `InitializeXxx()` functions — `InitializeFR()`, `InitializeEN()`,
`InitializeDE()` — but `Init()`'s own branching logic, quoted above, only ever calls
`InitializeFR()` or `InitializeEN()`. `InitializeDE()` is fully implemented (198 lines,
`MyResource.cpp:579-661`) but is **never invoked** by any code path. The header is candid about
this:

*From `MyResource.hpp:353-362`:*
```cpp
        /**
         * @brief Populates the resource table with German strings.
         *
         * @details
         * Defined but not currently invoked by Init(); the German locale
         * path falls through to InitializeEN() instead.  The function provides
         * German button/trial labels and French tutorial strings as a
         * partial translation.
         */
        static void InitializeDE();
```

Reading `InitializeDE()`'s actual body confirms the header's description precisely, and turns up
something odd enough to be worth quoting directly: the button labels it defines are not German at
all — they are the *English* strings, verbatim:

*From `MyResource.cpp:579-598` (excerpted):*
```cpp
    void MyResource::InitializeDE()
    {
        resources.emplace(TX_BUTTON_PLAY, "Play");
        resources.emplace(TX_BUTTON_MENU, "Home");
        resources.emplace(TX_BUTTON_BACK, "Back");
        resources.emplace(TX_BUTTON_RESTART, "Restart");
        resources.emplace(TX_BUTTON_CONTINUE, "Continue");
        resources.emplace(TX_BUTTON_BUY, "Buy");
        resources.emplace(TX_BUTTON_RANKING, "Ranking");
        resources.emplace(TX_BUTTON_SETUP, "Setup");
        ...
        resources.emplace(TX_GAMER_TITLE, "Gamer {0}");
```

while its training-hint strings (`TX_TRAINING101` onward) are French, again verbatim, matching
`InitializeFR()`'s text almost word for word:

*From `MyResource.cpp:604-609`:*
```cpp
        resources.emplace(TX_TRAINING101,
                          MakeResourceString("Utilise la roue directionnelle \0 pour faire avancer Blupi."));
        resources.emplace(TX_TRAINING102, "Appuie maintenant sur le bouton de saut \b.");
        resources.emplace(TX_TRAINING103,
                          MakeResourceString("Appuie à droite sur la roue directionnelle \0 et sur Saut \b."));
```

So `InitializeDE()` is not a genuine, unfinished German translation with a few strings still
missing — it is a **placeholder implementation that never contained actual German text**: mostly
English button labels with French tutorial content patched in, evidently checked in as scaffolding
for a translation pass that was never completed, and then never wired up to the locale-detection
`switch` at all. Combined with the fact that it is unreachable code (`Init()` never calls it), the
practical, user-visible language support of the shipped C++ port is exactly **two** languages —
English and French — regardless of what a German-locale device reports; `Init()`'s
`languageCode == "fr"` check simply routes every non-French locale, German included, to
`InitializeEN()`.

## Embedded control characters as button-glyph placeholders

Several tutorial strings embed raw control-character bytes — `\0`, `\b` (0x08), `\t` (0x09),
``, ``, ``, and others — directly inside the string literal. These are not
formatting mistakes; they are placeholders that the text-rendering layer
([Chapter 35](../part05-sprites-rendering-animation/ch35-text-rendering.md)) recognizes and
substitutes with a small inline glyph — a picture of the Jump button, the directional wheel, or
similar — so a tutorial sentence like "Press Jump" can show the actual on-screen Jump-button icon
inline with the words, rather than spelling it out:

*From `MyResource.cpp:44-50`:*
```
 * ## Embedded control characters in strings
 *
 * Several tutorial strings contain embedded nul bytes and other control bytes
 * (such as \\u000e, \\u0003, \\u0006) that serve as button-glyph placeholders
 * for the rendering layer.  Strings containing a nul byte are constructed with
 * MakeResourceString() to preserve the full byte sequence, since a plain
 * std::string constructor would stop at the first nul byte.
```

The complication is entirely a C-string artifact: a `\0` byte terminates a plain `const char*` and
therefore also a naive `std::string(const char*)` construction, silently truncating everything
after it. `MyResource` works around this with a small helper template that takes the character
array's *compile-time* size (which the compiler knows includes everything up to, and one past, the
literal `\0` at the very end of the array) and constructs the `std::string` with an explicit length
rather than relying on the implicit null-terminator scan:

*From `MyResource.hpp:315-333`:*
```cpp
        /**
         * @brief Helper that constructs a std::string from a character array
         *        literal, including embedded null bytes.
         *
         * @details
         * Some tutorial strings embed control characters (including @c '\0')
         * that serve as button-icon placeholders in the rendering layer.
         * Using @c std::string(text, N-1) preserves those bytes, whereas a
         * plain @c std::string(text) constructor would stop at the first
         * null character.
         *
         * @tparam N  Size of the character array including the terminating null.
         * @param[in] text  Character array literal to convert.
         * @return A @c std::string containing exactly @c N-1 characters.
         */
        template <size_t N>
        static std::string MakeResourceString(const char (&text)[N])
        {
            return std::string(text, N - 1);
        }
```

Because `text` is bound by reference to a `const char[N]` — a string literal array, not a decayed
pointer — the template parameter `N` is deduced automatically from the literal's own size at every
call site, and `std::string(text, N - 1)` builds a string of exactly `N - 1` characters (excluding
only the literal's own trailing NUL terminator, but *including* any embedded `\0` earlier in the
literal). Every string containing an internal `\0` is wrapped in `MakeResourceString(...)` at its
call site rather than passed as a bare literal:

*From `MyResource.cpp:470`:*
```cpp
        resources.emplace(TX_TRAINING101, MakeResourceString("Use the directional wheel \0."));
```

Strings whose only control characters are non-nul bytes (`\b`, `\t`, ``, ``, ``,
etc.) do not need this treatment — a plain `std::string(const char*)` constructor handles those
correctly, since only a `\0` byte terminates the implicit-length scan — which is exactly why some
training-hint strings in the source use `MakeResourceString(...)` and others (containing only
non-nul control bytes) are passed as ordinary string literals.

## `Helper::formatString` and placeholder substitution

Several resource strings carry a `{0}`-style placeholder — `TX_BUTTON_SETUP_RESET` ("Player {0} :
\nErase progress"), `TX_GAMER_TITLE` ("Player {0}"), `TX_GAMER_MDOORS` ("Main gates : {0}/12"),
`TX_GAMER_SDOORS` ("Secondary gates : {0}/52"), `TX_GAMER_LIFES` ("Blupi : {0}") — all consumed by
[Chapter 43](ch43-gamedata-save-format.md)'s gamer-selection screen. `MyResource` itself performs no
substitution; callers pass the raw templated string, plus the values to interpolate, into
`Helper::formatString()`:

*From `Game1.cpp:826-831`:*
```cpp
                string text = Helper::formatString(
                    MyResource::LoadString(MyResource::TX_BUTTON_SETUP_RESET),
                    STRING_VECTOR(
                        std::string(1, static_cast<char>('A' + gameData.getSelectedGamerProperty()))
                    )
                );
```

This cleanly separates *what the localized text says* (owned entirely by `MyResource`, per
language) from *how placeholders get filled in* (owned by `Helper`, covered in
[Chapter 49](../part09-support-types/ch49-helper.md)) — the same `{0}` template syntax and
`Helper::formatString` call is reused for every localized string that needs a runtime value spliced
in, regardless of which of the two working languages is active.

## Summary

`MyResource` is a lazily-initialized, locale-detected, integer-ID-to-string lookup table — the
game's entire localization layer for UI text — and nothing more. It is not an asset manager, it
does not touch `Content/`, and it has no relationship to `GameData` or the `worlds/*.txt`/
`CurrentGame` formats from the previous two chapters beyond being another example of the codebase's
general "port the original layout byte-for-byte / ID-for-ID, then note where behavior has quietly
drifted" pattern — here, an inert `InitializeDE()` translation pass and a preserved gap at resource
ID `106`. The two genuinely surprising findings worth carrying forward: despite exposing three
locale initializers, exactly two languages (English, French) are reachable at runtime, and the
"German" initializer that exists in the source is not a partial German translation but English
button labels paired with French tutorial text, wired to nothing.

## See also

- [Chapter 35: Text Rendering](../part05-sprites-rendering-animation/ch35-text-rendering.md) — how
  the embedded control-character glyph placeholders in `MyResource` strings are actually drawn.
- [Chapter 41: InputPad — Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md)
  — the d-pad vs. accelerometer control schemes that motivate the doubled `TX_TRAINING*`/`TX_TRAINING*a` string groups.
- [Chapter 43: GameData — Save Format](ch43-gamedata-save-format.md) — the gamer-selection screen
  whose `TX_GAMER_*` labels are formatted with live save data.
- [Chapter 45: Content Pipeline](ch45-content-pipeline.md) — the actual binary asset loading
  (`Content/icons/`, `Content/backgrounds/`, `Content/sounds/`) that `MyResource` is unrelated to.
- [Chapter 49: Helper](../part09-support-types/ch49-helper.md) — `Helper::formatString()`, the
  `{0}`-placeholder substitution used with every parameterized `MyResource` string.
- [Chapter 55: ILSpy Decompilation and C# Stubs](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
  — more on this codebase's decompiled-C#-to-C++ provenance, of which `MyResource`'s naming and ID
  gaps are one small example.
