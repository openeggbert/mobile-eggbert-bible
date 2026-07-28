# Appendix F: Repository Map

A quick-reference, table-first version of the repository relationships covered narratively in
[Chapter 2](../part01-origins-and-ecosystem/ch02-openeggbert-ecosystem-map.md). Every row below is
sourced directly from `/workspace/mobile-eggbert/README.md` and
`/workspace/mobile-eggbert/CLAUDE.md` — no repository is listed here whose role could not be
verified from those two files. Where a repository is known to exist but its content was not
independently examined for this book (per its marginal-coverage scope, see `CLAUDE.md`'s "Scope"
note), that is stated explicitly rather than filled in with assumption.

## Repositories referenced by `mobile-eggbert`'s own documentation

| Repository | Role for `mobile-eggbert` | Evidence | Depth in this book |
|---|---|---|---|
| `mobile-eggbert` (this repo) | The C++ port itself — the sole subject of this book. | — | Every chapter. |
| `mobile-eggbert-core` | The Git repository whose commit `1cbc13415b768085b7f5c97fbf35a773d7f14a8e` was used to create the C++ source: *"The C++ source code was created using the following Git commit of the Git repository mobile-eggbert-core"* | `README.md:13-15` | Mentioned in [Chapter 1](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md) and [Chapter 3](../part01-origins-and-ecosystem/ch03-license-and-provenance.md) as the direct source commit; not independently explored beyond this citation. |
| `cna` | The XNA-4.0-compatible C++ framework `mobile-eggbert` is built on, described as an *"XNA-like wrapper around the SDL 3... library"*. Lives as a sibling checkout at `../cna` relative to `mobile-eggbert`'s build directory, tracked on its `develop` branch. Located locally (per `CLAUDE.md`) at `/rv/data/development/github.com/openeggbert/cna`. | `README.md:11`, `README.md:216-218`; `CLAUDE.md:9-12` | Covered only marginally, by design — see `mobile-eggbert-bible`'s own `CLAUDE.md` scope note; deep CNA internals are `cna-bible`'s job. This book cites CNA only for "what mobile-eggbert calls and why" (e.g. [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md)). |
| `sharp-runtime` | The C++ reimplementation of .NET base-class-library types (`System.Math`, `System.String`, `EventHandler`, `IDisposable`, primitive aliases like `intcs`/`ubytecs`/`ushortcs`) that both `cna` and `mobile-eggbert` depend on. `CLAUDE.md`'s stated rule: *"If something needed by this project or by CNA does not yet exist in sharp-runtime, it must be added to sharp-runtime — not worked around in-place."* Located locally at `/rv/data/development/github.com/openeggbert/sharp-runtime`. | `CLAUDE.md:14-18, 28-40` | Cited wherever an enum's underlying type or a primitive alias needs explaining (see every enum's underlying type in [Appendix B](appendix-b-enum-catalog.md)); not explored beyond its documented role. |

## The `openeggbert` GitHub organisation

Every repository above (`mobile-eggbert-core`, `cna`, `sharp-runtime`) is namespaced under the
same GitHub organisation, `github.com/openeggbert/…`, confirmed both by the `mobile-eggbert-core`
commit URL in `README.md` and by the three local checkout paths in `CLAUDE.md`, which all share
the prefix `/rv/data/development/github.com/openeggbert/`. `mobile-eggbert` (this repository) is
part of the same organisation and ecosystem, though its own README does not spell out its full
GitHub URL.

## Build-time relationship to `cna`

`README.md`'s build instructions establish the following concretely (not inferred):

- `mobile-eggbert` does not vendor a copy of CNA's source; it points at a sibling checkout via
  `CNA_GRAPHICS_SOURCE_DIR`, which "points at the sibling `../cna` checkout, currently on its
  `develop` branch" (`README.md:216-217`).
- Git submodules must be initialised before the first build (`git submodule init --recursive` /
  `git submodule update --recursive`), meaning at least part of the CNA/SharpRuntime dependency
  chain is vendored as a submodule rather than purely a sibling directory, per the two different
  setup instructions given in `README.md` and `CLAUDE.md` respectively (`git submodule update
  --init --recursive` in `CLAUDE.md:56-59`).
- CNA is graphics-backend-pluggable at CMake configure time
  (`-DCNA_GRAPHICS_BACKEND=<SDL_RENDERER|EASYGL|BGFX|VULKAN|WEBGPU|HEADLESS|SOFTWARE|D3D11|D3D12|
  CANVAS|ASCII|DX3>`), and `mobile-eggbert` inherits whichever backend is selected without any
  game-side code change — the game links against CNA's abstraction, never a backend API directly.
  A backend still in development on `cna`'s `feature/sdlgpu` branch (`SDL_GPU`) is not yet
  available to `mobile-eggbert` because `develop` (the branch mobile-eggbert's build points at)
  does not include it yet (`README.md:216-218`).

## Graphics backends CNA offers to `mobile-eggbert` (build-time selectable)

Not a separate repository each, but worth tabulating here since `README.md`'s "Backend status"
section documents per-platform availability precisely, and the backend choice is the main
practical way `mobile-eggbert` "reaches into" CNA at build time:

| Backend | Platform(s) confirmed working | Notes from `README.md` |
|---|---|---|
| `SDL_RENDERER` | Windows, Linux, Web (Emscripten) | Default on all three; the baseline backend. |
| `EASYGL` | Linux | Can be enabled explicitly when needed. |
| `D3D11` | Windows (incl. via Wine + DXVK on Linux) | Verified: builds, runs, presents frames; needs only a Wine prefix with DXVK. |
| `D3D12` | Windows (incl. via Proton on Linux) | Verified: real vkd3d-proton device + swapchain; **must** run under Proton, not plain Wine — plain Wine's system `dxgi.dll` cannot pair with vkd3d-proton's `d3d12.dll`. |
| `ASCII` | Linux | An SDL-windowed glyph-grid decorator around SDL_Renderer — explicitly *not* a real terminal/TTY backend. |
| `DX3` | Linux | A narrow DirectX 3/DirectDraw subset reimplemented on SDL3 via the sibling `../free-direct` repository; portable, no Wine/Proton needed. |
| `CANVAS` | Web (Emscripten) | Browser HTML5 Canvas 2D, no GPU; experimental alongside `SDL_RENDERER`. |
| `BGFX`, `VULKAN`, `WEBGPU`, `HEADLESS`, `SOFTWARE` | Accepted by CNA's backend list | Listed as valid `-DCNA_GRAPHICS_BACKEND=` values in `README.md:200-202`; no platform-specific verification notes given for these in the file. |
| `SDL_GPU` | Not yet available to `mobile-eggbert` | Exists only on `cna`'s in-progress `feature/sdlgpu` branch, not yet merged into the `develop` branch that `mobile-eggbert` builds against. |

`../free-direct` is named here only because `README.md` names it directly as the sibling
repository `DX3` is built on (`README.md:210-211`) — its own internals are out of scope for this
book, exactly like `cna`'s.

## How book-writing sessions (this project) source these repositories

This is a fact about the `mobile-eggbert-bible` book project's own working conventions, not about
`mobile-eggbert` itself — kept in a separate section so the two are never conflated. Per
`mobile-eggbert-bible`'s own `CLAUDE.md`, each writing session adds and clones four repositories
outside the book repository (typically to `/workspace/<repo>`, never inside
`mobile-eggbert-bible`): `mobile-eggbert` (the primary source, this appendix's subject),
`cna` (for understanding what `mobile-eggbert` calls, cited only where needed), `cna-bible` (a
sister documentation project, borrowed for style/methodology only, never for content), and
`mobile-eggbert-legacy` (the decompiled C# origin, used for the history/migration chapters in
Part XI). `mobile-eggbert-legacy` is referenced by `mobile-eggbert`'s own `AUDIO_ANALYSIS.md` too,
which cites a specific file inside it (`mobile-eggbert-legacy/mobile-eggbert-core/Sound.cs:58`) —
suggesting `mobile-eggbert-legacy` itself contains (or once contained, e.g. as a submodule or a
nested checkout) a `mobile-eggbert-core` directory, tying this section back to the
`mobile-eggbert-core` commit reference in the table above.

## Provenance chain (build path only, not a full org chart)

The port history itself — decompilation, engine migrations — is covered narratively in
[Chapter 1](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md); this table is a
compressed, source-cited version of the same chain, as stated in `README.md`'s and `CLAUDE.md`'s
own project-overview sections:

| Step | Transformation | Evidence |
|---|---|---|
| 1 | Original Windows Phone XNA 4.0 game (2013), compiled C# binary | `README.md:3` |
| 2 | Decompiled to C# source via ILSpy | `README.md:6`; `CLAUDE.md:6` |
| 3 | Migrated from XNA 4.0 to MonoGame | `README.md:7`; `CLAUDE.md:6-7` |
| 4 | Migrated from C# to C++ | `README.md:8`; `CLAUDE.md:6-7` |
| 5 | Migrated from MonoGame to CNA | `README.md:9`; `CLAUDE.md:7` |

The C++ source produced by steps 3–5 is what `mobile-eggbert-core`'s cited commit
(`1cbc13415b768085b7f5c97fbf35a773d7f14a8e`) captures, and what this repository (`mobile-eggbert`)
directly descends from (`README.md:13-15`).

## What this appendix deliberately does not claim

Consistent with this appendix's brief — "don't fabricate details about repos you haven't read" —
the following are *not* asserted here even though they are plausible members of the same
ecosystem: this appendix does not describe `mobile-eggbert-core`'s internal structure (only its
role as a cited source commit is verified), does not describe `sharp-runtime`'s or `cna`'s
internal APIs beyond the one dependency rule quoted above, and does not list any further
"sibling" OpenEggbert repositories beyond the three that `mobile-eggbert`'s own `README.md` and
`CLAUDE.md` name explicitly. Broader ecosystem context (e.g. other ports or tooling repositories
under the same organisation) belongs to
[Chapter 2](../part01-origins-and-ecosystem/ch02-openeggbert-ecosystem-map.md), which is free to
draw on additional sources beyond these two files.
