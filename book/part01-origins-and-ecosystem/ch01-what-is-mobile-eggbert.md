# Chapter 1: What Is Mobile Eggbert

## A game with four lives

`mobile-eggbert` is a C++ port of *Speedy Blupi*, a puzzle-platformer originally released for
Windows Phone in 2013. If you only look at the finished product — a small, tile-based game about
guiding a blue creature named Blupi through 78 hand-authored levels, opening doors, dodging traps,
and collecting treasure — it looks like an ordinary retro-style mobile game. What makes it worth an
entire book is not the game design; it is the journey the *code* has been on to still be running
today, more than a decade after it shipped on a mobile platform that no longer exists.

The project's own `README.md` states the transformation plainly:

*From `README.md:3-11`:*

```markdown
Mobile Eggbert is a modified version of Speedy Blupi, originally developed for Windows Phone and
released in 2013. The project underwent the following transformations:

- decompiled by the ILSpy to the C# source code
- migrated from XNA 4.0 to Monogame
- migrated from C# to C++
- migrated from Monogame to CNA

CNA is XNA-like wrapper around the SDL 3 (cross-platform software development library).
```

Four transformations, each one a substantial engineering project in its own right: decompilation,
a framework migration, a language migration, and a second framework migration. This book is a
guided tour of the code that survived all four — what it looks like today, why it looks that way,
and which decisions from 2013 (and from each subsequent migration) are still visible if you know
where to look.

## Speedy Blupi: the original game

The `LICENSE` file at the root of the repository names the original author directly:

*From `LICENSE:1-4`:*

```text
MIT License

Copyright (c) 2013 Daniel Roux
Copyright (c) 2024-2026 Robert Vokac
```

Daniel Roux is credited elsewhere in the codebase as working for Epsitec SA. The Doxygen file
header of `Decor.hpp` — the class that implements the entire gameplay simulation — is explicit
about both the origin and the split of labor between the original author and the porting team:

*From `Decor.hpp:19-20`:*

```cpp
 * @author  Original XNA/C# game by Epsitec SA; C++ port by the mobile-eggbert team
 * @date    2013 (original); 2024 (C++ port)
```

Speedy Blupi belongs to a small, distinctly Swiss-francophone lineage of children's puzzle-platform
games about a blue creature called "Blupi," produced by Epsitec SA (also known for the "EPSITEC"
educational software label and, notably, for the Colobot programming-education game). The Windows
Phone version, built in 2013 on Microsoft's XNA 4.0 framework, is the ancestor this entire codebase
descends from. Its gameplay is intentionally modest by modern standards: a fixed 640×480 logical
viewport (`Def::LXIMAGE` / `Def::LYIMAGE`, defined in `Def.hpp`), a single playable character, and
level data stored as plain, human-readable text files under `worlds/`. That modesty is a large part
of why the game has proven portable across four target platforms and, as later chapters show, five
different graphics backends — there simply isn't very much surface area that depends on any one
platform's rendering pipeline.

## Step one: ILSpy decompilation

Windows Phone 7/8's Silverlight- and XNA-based application model was discontinued by Microsoft
years ago, and with it went any straightforward way to keep running a 2013 XNA game on modern
hardware. The starting point for `mobile-eggbert` was therefore not source code at all, but a
compiled `.xap`/assembly — recovered as C# via **ILSpy**, a well-known open-source .NET
decompiler. `README.md` lists this as the first transformation the project underwent, and residual
evidence of it is still visible in the tree today: two top-level directories,
`Microsoft.Xna.Framework.GamerServices/` and `Microsoft.Devices.Sensors/`, hold small C# stub
files that were never fully ported to C++ (their fate, and why they were left behind rather than
translated, is the subject of [Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)).

Decompiled code is a peculiar starting material. ILSpy reconstructs plausible, compilable C# from
IL bytecode, but it cannot recover comments, and it often produces mechanically literal
control flow (nested `if`/`else` chains where a switch might read more naturally, temporary
variables named `num`, `num2`, `flag` where the original author had a meaningful local variable
name). Readers of later chapters — particularly [Chapter 12](../part03-architecture/ch12-game1-state-machine.md),
which walks through `Game1`'s `Update()`/`Draw()` methods — will notice exactly this style:
variables like `num`, `num2`, and deeply nested conditionals are not accidents of the C++ port,
they are fossils preserved intact from the decompiled C# through every subsequent migration. The
project's own engineering discipline (see `CLAUDE.md`'s instruction that ports must preserve
"movement constants, collision rules, animation table indices, and state-machine transitions") has
deliberately kept these fossils in place rather than "cleaning them up," on the reasonable premise
that gameplay-critical logic evolved and was play-tested over the original game's lifetime, and
that refactoring it risks changing behavior nobody can easily re-verify against the original.

## Step two: XNA 4.0 to MonoGame

The second transformation moved the decompiled game off Microsoft's now-defunct XNA runtime and
onto **MonoGame**, the open-source, cross-platform reimplementation of the XNA 4.0 API that has
become the de facto way to keep XNA-era games alive. This step is a framework migration, not a
language migration — the code was still C# throughout — and its purpose was almost certainly to
get the game running on modern operating systems and toolchains before undertaking the much larger
step of rewriting it in a different language entirely.

Because MonoGame deliberately preserves XNA's namespaces and API shapes (`Microsoft.Xna.Framework`,
`SpriteBatch`, `ContentManager`, `GameTime`, and so on), this migration step is largely invisible in
the final C++ source: the game's classes still declare themselves as members of
`Microsoft::Xna::Framework` and call the same conceptual APIs a 2013 XNA programmer would recognize.
[Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md) surveys exactly which parts of that API
surface `mobile-eggbert`'s own code touches today.

## Step three: C# to C++

The third transformation is the largest single engineering effort behind this codebase: a full
rewrite from C# to C++. This is not a thin binding layer over C# — `mobile-eggbert`'s
`include/WindowsPhoneSpeedyBlupi/` and `src/WindowsPhoneSpeedyBlupi/` directories are pure C++ (with
a handful of type aliases like `intcs`, `bytecs`, and `string` that echo C#'s primitive types,
supplied by a sibling library called `sharp-runtime` — see [Chapter 2](ch02-openeggbert-ecosystem-map.md)).
By the numbers recorded in this book's own planning document, the ported codebase is substantial:
roughly 31,300 lines of C++ across 34 headers and 16 implementation files, with the gameplay
simulation class `Decor` alone accounting for over 11,700 lines — more than a third of the entire
project.

A C#-to-C++ port of this scale has to solve two problems simultaneously: reproducing C#'s runtime
semantics (properties, events, garbage-collected reference types, `readonly` fields) in a language
that has none of those things natively, and reproducing the *exact* behavior of a game whose
original design documents, if they ever existed, are long gone — the only spec is the decompiled
code itself. The project's own `CLAUDE.md` records some of the conventions adopted to manage this:
C# `readonly` fields are ported using a `#define readonly mutable` macro (visible at the top of
`Game1.hpp:33-35`) purely as a porting aid, and `TinyRect` deliberately preserves a "non-standard
field order" (`Left, Right, Top, Bottom` instead of the more conventional `Left, Top, Right,
Bottom`) because that was the original field order and countless call sites depend on positional
construction matching it. These aren't stylistic choices a C++ project would make from scratch —
they are the visible seams of a faithful, line-for-line port.

## Step four: MonoGame to CNA

The fourth and final transformation swapped the game's underlying framework a second time, this
time from MonoGame to **CNA** — a C++ framework, built by the same organization, that reimplements
the XNA 4.0 programming model on top of SDL3. `README.md` describes CNA in one sentence: "CNA is
XNA-like wrapper around the SDL 3 (cross-platform software development library)." Because CNA's
whole design goal is to preserve the *shape* of the XNA API (`Microsoft::Xna::Framework::Game`,
`GraphicsDeviceManager`, `SpriteBatch`, and so on) while replacing everything underneath it, this
final migration is — again, deliberately — the least disruptive one to `mobile-eggbert`'s own code.
`Game1`, the game's top-level class covered in depth in [Chapter 12](../part03-architecture/ch12-game1-state-machine.md),
still inherits from `Microsoft::Xna::Framework::Game` exactly as an XNA 4.0 game would.

This book treats CNA itself as largely out of scope — deliberately. As `CLAUDE.md` for this project
states, CNA is covered here "only marginally... never as a deep dive into CNA's internals." A full
treatment of CNA's own architecture (its five graphics backends, its SDL3 integration, its own
supporting libraries) is the job of the sister project `cna-bible`. What you will find in this book
is the other half of that boundary: precisely which parts of the XNA-shaped surface `mobile-eggbert`
actually calls, and why — most concentrated in [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md).

## The commit this port was built from

`README.md` also pins down exactly where the C++ source came from, which matters for provenance
and for anyone trying to compare this codebase against its immediate ancestor:

*From `README.md:13-15`:*

```markdown
The C++ source code was created using the following Git commit of the Git repository mobile-eggbert-core:

https://github.com/openeggbert/mobile-eggbert-core/commit/1cbc13415b768085b7f5c97fbf35a773d7f14a8e
```

`mobile-eggbert-core` is the name used for the intermediate MonoGame/C# stage of the pipeline
described above — the artifact of steps one and two, and the direct input to step three (the C++
rewrite). [Chapter 2](ch02-openeggbert-ecosystem-map.md) places this repository in context among
its siblings in the OpenEggbert organization, and [Part XI](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
returns to the decompilation and migration history in much greater depth.

## What today's codebase actually is

It's worth being precise about what `mobile-eggbert` is *today*, as distinct from the migration
history above. It is:

- A CMake-based C++ project (`CMakeLists.txt`, detailed in [Chapter 4](../part02-building-and-running/ch04-build-overview.md))
  that builds a single executable target, `WindowsPhoneSpeedyBlupi` — the target name is itself a
  fossil of the original platform, preserved rather than renamed.
- Buildable natively on Linux and Windows, cross-compilable to Windows via MinGW-w64 from Linux,
  runnable through Wine/Proton for Direct3D backends, buildable for the Web via Emscripten, and
  targetable at Android — see [Part II](../part02-building-and-running/ch04-build-overview.md) for
  the full tour of each.
- Structured around a small number of large classes with clear, singular responsibilities: `Game1`
  (the top-level state machine, [Chapter 12](../part03-architecture/ch12-game1-state-machine.md)),
  `Decor` (the entire gameplay simulation — tile map, player state machine, physics, AI, doors,
  missions — covered across the whole of [Part IV](../part04-decor-simulation/ch15-decor-overview.md)),
  `Pixmap`/`Sound`/`InputPad` (rendering, audio, and input, covered in
  [Part V](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md),
  [Part VI](../part06-audio/ch38-sound-isound-architecture.md), and
  [Part VII](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) respectively), and
  `GameData` (save-game persistence, [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md)).
- Actively documented in-tree: every `.hpp`/`.cpp` file is expected to carry complete Doxygen
  documentation per `CLAUDE.md` and `DOXYGEN_DOCUMENTATION_PLAN.md` — a level of self-documentation
  this book leans on heavily and cites throughout, while never treating it as a substitute for
  reading the actual code.
- Actively maintained with its own `TODO.md` and analysis documents (`AUDIO_ANALYSIS.md`, `RAM.md`,
  `ENUMS.md`) that record known issues and proposed — but not yet implemented — refactorings. A
  running theme in this book, stated once clearly here: **`ENUMS.md` is a proposal document, not a
  description of the current code.** It catalogs places where raw magic numbers (`68`, `91`, and so
  on) could be replaced with named enum constants; the code itself still uses the raw integers.
  Wherever this book cites `ENUMS.md`, it will say so explicitly.

## What this book is (and is not)

This book is a source-grounded technical tour of `mobile-eggbert`'s own code — every claim in every
chapter traces back to an actual line in an actual file in the `mobile-eggbert` repository (or, in
a handful of clearly-marked cases, to a sibling repository consulted only for context). It is not:

- A CNA reference manual. CNA is mentioned wherever `mobile-eggbert`'s code calls into it, and no
  further. `cna-bible` is the right place for CNA's own internals.
- A game design or gameplay walkthrough. You will learn a great deal about how Blupi's state
  machine, physics, and AI are implemented, but this is not a strategy guide or a level-by-level
  playthrough.
- Speculative or reconstructed history. Where the transformation history above cannot be verified
  from a source file this book can actually read, the book says so rather than inventing detail —
  the same discipline applies to every other chapter.

## How the book is organized

The book is laid out in eleven parts plus seven appendices; the authoritative, continuously-updated
table of contents lives in `book/SUMMARY.md`, but a short preview here should orient you:

- **Part I — Origins and the OpenEggbert Ecosystem** (this part) covers where the game came from
  ([Chapter 2](ch02-openeggbert-ecosystem-map.md) maps the surrounding repositories,
  [Chapter 3](ch03-license-and-provenance.md) covers licensing).
- **Part II — Building and Running the Game** is a practical build guide across every supported
  platform and graphics backend.
- **Part III — Architecture Overview** (where [Chapter 12](../part03-architecture/ch12-game1-state-machine.md)
  lives) covers the application's entry point and its top-level structure.
- **Part IV — The Decor Simulation**, the largest part of the book, is a deep dive into the
  gameplay engine itself: the tile map, Blupi's state machine, physics, AI, doors, missions, and
  the cheat system.
- **Part V — Sprites, Rendering, and the Animation System** is illustrated with real, pixel-accurate
  crops from the game's own sprite atlases — every animation sequence, creature, explosion effect,
  and background catalogued with real images, never mockups.
- **Part VI — Audio** and **Part VII — Input** cover the sound and input subsystems respectively.
- **Part VIII — Data, Persistence, and Content** covers save games, the level file format, and the
  content pipeline.
- **Part IX — Support Types and Utilities** catalogs the smaller supporting classes.
- **Part X — Platform Deep Dives** returns to Android, Windows, Web, and memory-usage topics in
  more depth than Part II's build-focused chapters allow.
- **Part XI — History, Migration, and Engineering Practice** closes the book by returning to the
  ILSpy decompilation, the .NET/XNA migration, the project's documentation methodology, and its
  forward-looking roadmap.
- The **appendices** provide reference material: a full class/file catalog, an enum catalog, the
  level file format specification, a glossary, a cheat code reference, a repository map, and a
  screenshot/visual gallery.

If you read only one thing before diving into the architecture chapters, make it
[Chapter 2](ch02-openeggbert-ecosystem-map.md) next — it draws the boundary, in a handful of
paragraphs, between what this book covers and what belongs to its sister projects.

## See also

- [Chapter 2 — The OpenEggbert Ecosystem Map](ch02-openeggbert-ecosystem-map.md)
- [Chapter 3 — License and Provenance](ch03-license-and-provenance.md)
- [Chapter 12 — Game1: the State Machine](../part03-architecture/ch12-game1-state-machine.md)
- [Chapter 55 — ILSpy Decompilation and C# Stubs](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
- [Chapter 56 — .NET and XNA Migration](../part11-history-and-practice/ch56-dotnet-and-xna-migration.md)
