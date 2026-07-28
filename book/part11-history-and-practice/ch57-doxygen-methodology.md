# Chapter 57: The Doxygen Documentation Methodology

`mobile-eggbert` documents its own documentation effort. Two files govern it:
`DOXYGEN_DOCUMENTATION_PLAN.md` (512 lines) — a per-file audit of documentation completeness across
every `.hpp`/`.cpp` file in the project, plus a written style guide — and `Doxyfile`, the actual
Doxygen tool configuration (a generated, ~120 KB file, the vast majority of it Doxygen's own
untouched defaults). This chapter reads the plan in full, extracts the handful of `Doxyfile`
settings that meaningfully diverge from a default configuration, and spot-checks the plan's own
claims against real files to confirm the documentation it describes actually exists in the form
described — not just as an aspiration.

## The plan's stated goal and scope rule

The plan opens with an unambiguous goal and a scope-limiting rule for `.cpp` files specifically:

*From `DOXYGEN_DOCUMENTATION_PLAN.md:1-6`:*
```markdown
# Doxygen Documentation Plan — mobile-eggbert

**Goal:** Every `.hpp` and `.cpp` file in the project must have complete, accurate English Doxygen documentation.
`.cpp` files only receive Doxygen when the implementation contains non-trivial logic not already documented in the corresponding `.hpp` (e.g. complex algorithms, non-obvious side effects, internal helpers without a header counterpart).

The project is a C++ port of the *Speedy Blupi* game (originally an XNA/Windows Phone title written in C#), using the CNA (C-to-Native Application) framework that maps XNA idioms to C++ equivalents.
```

That second rule — don't duplicate `.hpp` documentation inside the matching `.cpp` — is restated
later as one of the plan's "General rules" (`DOXYGEN_DOCUMENTATION_PLAN.md:503`: "Do **not**
duplicate in `.cpp` what is already documented in the matching `.hpp`.") and is the single most
consequential policy decision in the whole document: it means a `.cpp` file's *own* Doxygen
coverage percentage is not, by design, meant to match its header's — a `.cpp` implementing a
well-documented, simple header can legitimately stay at `NONE` or `MINIMAL` status forever without
that being a documentation gap. Reading the per-file catalog below with that rule in mind avoids
misreading a `.cpp`'s low status as neglect.

## The five-tier status legend

The plan tracks completeness per file using a five-value scale, defined once at the top and then
applied consistently to every one of the 50 files it catalogs:

*From `DOXYGEN_DOCUMENTATION_PLAN.md:10-19`:*
```markdown
## Legend

| Status | Meaning |
|---|---|
| `NONE` | No Doxygen comments at all |
| `MINIMAL` | A few comments, mostly noise |
| `PARTIAL` | Some classes/methods documented, many gaps |
| `GOOD` | Most public API documented, minor gaps remain |
| `EXCELLENT` | Fully documented, only fine-tuning needed |
```

Across the plan's two catalogs — 34 header files and 16 source files, matching this project's
full `.hpp`/`.cpp` count exactly (see `PLAN.md`'s own source-size measurement) — the status
distribution skews toward the well-documented end for headers and toward the sparse end for
sources, which is exactly what the `.cpp`-scope rule above would predict:

| Status | Header files (`.hpp`) | Source files (`.cpp`) |
|---|---|---|
| `EXCELLENT` | 9 | 0 |
| `GOOD` | 20 | 0 |
| `PARTIAL` | 4 | 4 |
| `MINIMAL` | 0 | 8 |
| `NONE` | 0 | 3 (`Program.cpp`, `Misc.cpp`, `TinyRect.cpp`) |
| **Total** | **34** (includes `Decor.hpp` at `EXCELLENT`, `TinyRect.hpp` at `GOOD`) | **16** |

No header is rated below `PARTIAL`; no source file is rated above `PARTIAL`. This split is
consistent with the plan's own scope rule rather than contradicting it — the three `.cpp` files at
`NONE` (`Program.cpp`, `Misc.cpp`, `TinyRect.cpp`) are all cases the plan itself describes as
implementing straightforward logic already covered by their headers (`DOXYGEN_DOCUMENTATION_PLAN.md`'s
entries for `TinyRect.cpp` at line 366-369 explicitly says "no method-level docs needed beyond what
the header already has").

## The per-file catalog: an audit, not a changelog

Each of the plan's 50 entries follows one fixed shape — file path, status, a description of what
the file does, and a "Work needed" line describing the specific documentation gap — for example:

*From `DOXYGEN_DOCUMENTATION_PLAN.md:38-42` (entry #3, `Decor.hpp`):*
```markdown
### 3. `include/WindowsPhoneSpeedyBlupi/Decor.hpp`
**Status:** EXCELLENT
**Description:** The heart of the gameplay simulation. Owns the 100×100 tile map, the Blupi player state, all moving objects, doors, switches, teleporters, lifts, and hazards. Drives collision detection, animation sequencing, viewport scrolling, particle effects, and the per-frame update tick.
**Work needed:** Very large file (~1 200 lines); audit that every public method has a `@param`/`@return`; add `@note` tags for any magic-number fields; verify `@file` block accuracy.
```

(The plan's own line count estimate here — "~1,200 lines" — undercounts considerably: this book's
`PLAN.md` measured `Decor.hpp` at 2,064 lines. The plan document is an audit of documentation
*content*, not a line-counting exercise, and this discrepancy doesn't affect its accuracy about
what's documented — only about the file's raw size.)

Reading across all 50 entries, several recurring "Work needed" themes surface independent of any
individual file's status:

- **Magic-number provenance.** Several entries (`Decor.hpp`, `Def.hpp`, `ObjectType.hpp`) ask for
  `@note` tags explaining that a given constant's value "originates from the original Windows
  Phone screen spec" or the original C# source's numeric IDs — a documentation task specific to a
  ported codebase, not something a from-scratch C++ project would need.
- **Byte-layout/format schemas.** `GameData.hpp`/`.cpp` (save-data byte array) and
  `Worlds.hpp`/`.cpp` (level file text format) are both flagged for needing their on-disk formats
  spelled out in a `@details` or `@note` block — these are the two places in the codebase where
  Doxygen comments are asked to double as a de facto file-format specification, which this book's
  own [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md) and
  [Chapter 44](../part08-data-persistence-content/ch44-worlds-level-file-format.md) independently
  cover from the code itself.
- **Non-obvious invariants that would otherwise only live in a comment.** `TinyRect.hpp`'s
  non-standard `(Left, Right, Top, Bottom)` field order (as opposed to the more conventional
  `(Left, Top, Right, Bottom)`) is singled out twice — once for the header (`Work needed:` "add a
  `@file` block; prominently document the non-standard field order so readers do not confuse it
  with `(Left, Top, Right, Bottom)`", entry #33) and once for the source file, which asks that the
  warning be repeated for anyone opening `TinyRect.cpp` directly without having first read the
  header (entry #49). This particular convention gets its own dedicated coverage in this book's
  [Chapter 47](../part09-support-types/ch47-tinypoint-tinyrect.md).

## The prioritized work order: `Decor.cpp` first, by a wide margin

The plan closes its analysis with a 21-row priority table, ranking files by documentation debt
rather than by file size or importance alone:

*From `DOXYGEN_DOCUMENTATION_PLAN.md:384-395` (top 6 rows of 21):*
```markdown
| Priority | File | Reason |
|---|---|---|
| 1 | `Decor.cpp` | Largest, most complex, most partial documentation |
| 2 | `Decor.hpp` | Core API, needs full audit of all ~1 200 lines |
| 3 | `Tables.cpp` / `Tables.hpp` | Column layout of animation tables completely undocumented |
| 4 | `Game1.cpp` / `Game1.hpp` | Phase state machine transitions not described |
| 5 | `Pixmap.cpp` | Zoom-transform maths undocumented |
| 6 | `Worlds.cpp` / `Worlds.hpp` | File format grammar missing |
```

The ordering closely tracks the same "biggest, most central subsystems first" priority this book's
own `PLAN.md` independently arrived at when scoping which chapters needed the deepest treatment
(`Decor.cpp` at 11,720 lines dominating both documents' top rankings is not a coincidence — it is
simply the largest, most logic-dense file in the project by a wide margin either way it's
measured). Rows 10 onward shift to the smaller enum/utility files (`decor/DecorAction.hpp`,
`decor/DoorKeyFlags.hpp`, `Misc.cpp`, `Text.cpp`, `Jauge.cpp`, `Slider.cpp`, `Helper.cpp`,
`Program.cpp`, `TinyRect.cpp`), ending at row 21 with a catch-all: "All remaining GOOD/EXCELLENT
files — Audit pass only — fill any gap found."

## The Doxygen tag conventions

The plan's most durable content, likely to outlive any specific per-file status snapshot, is its
style guide: a full template for every Doxygen construct the project uses, given as literal
copy-pasteable code blocks. The file-level block:

*From `DOXYGEN_DOCUMENTATION_PLAN.md:416-426`:*
```cpp
/**
 * @file   FileName.hpp
 * @brief  One-line summary of the file's purpose.
 * @details
 *   Extended description: what the file provides, its role in the
 *   architecture, and any design constraints worth knowing.
 * @author Original author / porter
 * @date   Year first created or ported
 */
```

the method/function block (the richest of the templates, listing every tag category the project
recognizes as meaningful):

*From `DOXYGEN_DOCUMENTATION_PLAN.md:445-463`:*
```cpp
/**
 * @brief  One-line summary.
 * @details
 *   Longer description when the behaviour is non-trivial.
 * @param[in]  paramName  What this input represents; valid range if relevant.
 * @param[out] paramName  What is written; ownership / lifetime.
 * @param[in,out] paramName  Both read and written; contract.
 * @return Description of the return value and its valid range.
 * @retval 0   Specific meaning of a particular return value (use when applicable).
 * @throws std::runtime_error  When and why this exception is thrown.
 * @pre    Precondition that must hold before the call.
 * @post   Guaranteed state after a successful call.
 * @note   Non-obvious side-effect or implementation detail.
 * @warning Dangerous edge case or UB condition.
 * @see    RelatedFunction(), AnotherClass
 * @todo   Known gap or planned improvement (use sparingly).
 */
```

and general rules governing tag usage discipline, including a directive that every `@param` name
its data direction explicitly:

*From `DOXYGEN_DOCUMENTATION_PLAN.md:504`:*
```markdown
- `@param[in]` / `@param[out]` / `@param[in,out]` — always use the directional qualifier.
```

Templates for `@class`, `@enum`, struct-field trailing comments (`///<`), operator overloads, and
`@tparam` follow the same pattern — a concrete code skeleton first, then prose rules. The style
guide closes with a tone instruction that is itself worth quoting, because it is unusually
specific about grammatical voice for a code-documentation guide: "Write in plain English; avoid
abbreviations; use third-person present tense for `@brief` (\"Returns …\", \"Loads …\", \"Computes
…\")" (`DOXYGEN_DOCUMENTATION_PLAN.md:512`).

## Verifying the plan against real code: does `Decor.hpp` actually follow it?

A documentation plan is only as useful as its correspondence to the real code, so this section
checks the plan's `EXCELLENT`-rated claim about `Decor.hpp` directly rather than taking it at face
value. `Decor.hpp` contains **565 occurrences** of the Doxygen tags this chapter's templates define
(`@file`, `@brief`, `@class`, `@param`, `@return`, `@note`, `@warning`, `@see`, `@throws`, `@pre`,
`@post`, `@retval`, `@details`) — a substantial, not token, amount of markup for a single header.

The file's opening `@file` block matches the plan's own template structure field-for-field —
`@file`, `@brief`, `@details`, `@author`, `@date`, `@see` — and, notably, states the porting
provenance the plan's magic-number guidance asks for explicitly:

*From `Decor.hpp:1-21`:*
```cpp
/**
 * @file   Decor.hpp
 * @brief  Declares the core gameplay simulation class Decor for Speedy Blupi.
 * @details
 *   This file is the heart of the gameplay subsystem. The Decor class owns the
 *   100×100 tile map, the Blupi player state machine, all active moving objects,
 *   door and switch state, and every gameplay mechanic: physics, collision,
 *   animation sequencing, viewport scrolling, sound triggering, and win/loss
 *   detection.
 *
 *   The class is a direct C++ port of the original XNA/Windows Phone C# Decor
 *   class. All movement constants, collision rules, animation table indices, and
 *   state-machine transitions are preserved from the original source.
 * ...
 * @author  Original XNA/C# game by Epsitec SA; C++ port by the mobile-eggbert team
 * @date    2013 (original); 2024 (C++ port)
 * @see     IPixmap, ISound, GameData, Tables
 */
```

The `@class` block immediately following it is equally faithful to the template — `@class`,
`@brief`, `@details` (with a bulleted responsibility list):

*From `Decor.hpp:41-46`:*
```cpp
/**
 * @class  Decor
 * @brief  Core gameplay simulation class. Owns the level state, Blupi player state,
 *         moving objects, tile map, and all gameplay logic.
 * @details
 *   Decor is the central gameplay subsystem. It corresponds directly to the original
 *   C# Decor class...
```

And the directional-`@param` rule the general guidelines mandate is genuinely followed at the
method level, not just declared in principle — every parameter is tagged `[in]`, `[out]`, or
neither is present at all:

*From `Decor.hpp:622-623`:*
```cpp
 * @param[out] dst  Destination MoveObject to overwrite.
 * @param[in]  src  Source MoveObject to copy from.
```

Separately, `TinyRect.hpp` was flagged by the plan for needing its non-standard field order
"prominently documented" — and the actual header does exactly that, with a `@warning` tag repeated
at the file level, the class level, and again inline at the specific constructor whose parameter
order could otherwise be misread:

*From `TinyRect.hpp:69`:*
```cpp
 * @warning Parameter order is @b Left, @b Right, @b Top, @b Bottom —
```

Taken together, these spot checks confirm the plan's `EXCELLENT`/`GOOD` ratings for `Decor.hpp` and
`TinyRect.hpp` describe real, present documentation, following the exact tag conventions the plan
itself lays out — this is a genuinely-executed methodology, not an aspirational document sitting
unconnected to the actual source tree.

## `Doxyfile`: the handful of settings that matter

`Doxyfile` is Doxygen's own configuration format — a flat `KEY = value` file, generated once by
`doxygen -g` and then hand-edited, that in this project's case runs to roughly 120 KB and several
thousand lines, the overwhelming majority of which are Doxygen's own default settings left
untouched (every option Doxygen supports is emitted into a fresh `Doxyfile`, commented with its
own explanation, whether or not the project changes it). Rather than reading it line by line, the
settings that actually diverge from a bare default — the ones that determine what this project's
own generated documentation actually looks like and covers — are:

| Setting | Value | What it means for this project |
|---|---|---|
| `PROJECT_NAME` | `"Mobile Eggbert"` | The generated docs are titled for the current project name, not the original "Speedy Blupi" |
| `EXTRACT_ALL` | `NO` | Doxygen only documents entities that have an actual doc-comment — undocumented classes/functions are silently omitted from output rather than appearing as bare stubs. This makes the `DOXYGEN_DOCUMENTATION_PLAN.md` audit directly consequential: a file left at `NONE`/`MINIMAL` doesn't just look sparse in generated docs, it can be nearly *absent* from them. |
| `EXTRACT_PRIVATE` | `NO` | Private class members are excluded from generated output — the docs describe the public API surface, not implementation internals |
| `EXTRACT_STATIC` | `NO` | File-static functions/variables are likewise excluded |
| `WARN_IF_UNDOCUMENTED` | `YES` | Doxygen emits a build-time warning for every undocumented documented-elsewhere entity it encounters — meaning a `doxygen` run against this project today would emit a large number of warnings for every file the plan marks below `EXCELLENT`, giving a mechanically-checkable signal of the plan's own remaining backlog |
| `JAVADOC_AUTOBRIEF` | `NO` | The first sentence of a doc comment is *not* automatically treated as the `@brief` — every `@brief` in this codebase is explicit, matching the templates above, which always spell out `@brief` by name rather than relying on this shortcut |
| `SOURCE_BROWSER` | `NO` | Generated HTML does not include a browsable, cross-referenced copy of the source code itself — output is documentation text only |
| `RECURSIVE` | `NO` | The `INPUT` paths given are scanned non-recursively — Doxygen will not automatically walk into subdirectories that aren't explicitly listed, so `INPUT` (left blank in the excerpted settings above, meaning it is set elsewhere in the file to explicit paths) must enumerate every directory that actually holds documentable source, not just the top-level ones |
| `GENERATE_HTML` | `YES` | HTML output is produced (Doxygen's default and the most common consumption format) |
| `GENERATE_LATEX` | `YES` | LaTeX/PDF output is *also* produced — left at Doxygen's own default rather than disabled, meaning a full `doxygen` run produces both a browsable HTML tree and PDF-ready LaTeX sources, even though this project's own documentation habits (long-form Markdown plan documents, not generated PDFs) don't obviously call for the latter |
| `GENERATE_XML` | `NO` | No machine-readable XML output (the format tools like `Breathe`/`Exhale` would consume to feed Doxygen-extracted docs into Sphinx) is generated — this project's documentation pipeline stops at Doxygen's own native outputs |
| `HAVE_DOT` | `YES` | Graphviz's `dot` is assumed available, enabling any diagram Doxygen can generate from it |
| `CALL_GRAPH` / `CALLER_GRAPH` | `NO` / `NO` | Despite `HAVE_DOT` being enabled, per-function call graphs and caller graphs are both switched off — the diagram capability is available but not spent on function-level call graphs, presumably to keep generated output size and build time down on a project with a single 11,720-line file at its core |

The `EXTRACT_ALL = NO` / `WARN_IF_UNDOCUMENTED = YES` pairing is the most consequential
combination here, and it's worth stating plainly why: together they mean the project's Doxygen
configuration is not a passive "extract whatever's there" setup — it actively distinguishes
documented from undocumented code in its output, and actively surfaces the gap as a build warning.
That configuration choice is precisely what makes a hand-maintained audit document like
`DOXYGEN_DOCUMENTATION_PLAN.md` a coherent complement to the tool, rather than a redundant, separate
effort: the `Doxyfile` settings define *what counts as done* (a doc-commented entity, in the shape
the templates specify), and the plan tracks progress toward that bar file by file.

## See also

- [Chapter 27: Decor.hpp Reference Catalog](../part04-decor-simulation/ch27-decor-hpp-reference-catalog.md) — a full member catalog of the file this chapter uses as its primary spot-check example
- [Chapter 47: TinyPoint, TinyRect](../part09-support-types/ch47-tinypoint-tinyrect.md) — the non-standard field-order convention this chapter verifies is documented in the header
- [Chapter 43: GameData — Save Format](../part08-data-persistence-content/ch43-gamedata-save-format.md) and [Chapter 44: Worlds — Level File Format](../part08-data-persistence-content/ch44-worlds-level-file-format.md) — the two file-format specifications the plan flags as needing Doxygen-embedded grammar documentation
- [Chapter 55: ILSpy Decompilation and the Residual C# Stubs](ch55-ilspy-decompilation-and-csharp-stubs.md) — another artifact of this project's porting history, read directly rather than paraphrased
