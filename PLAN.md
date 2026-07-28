# Mobile Eggbert Bible — plan

## Source code size (measured 2026-07-28)

`mobile-eggbert` (`develop` branch, commit `07e0a67`):

- `include/WindowsPhoneSpeedyBlupi/**/*.hpp`: 34 files
- `src/WindowsPhoneSpeedyBlupi/**/*.cpp`: 16 files
- Total C++ (`.hpp` + `.cpp`) plus a handful of residual `.cs` stubs: **31,301 lines**
  - `Decor.cpp` alone: **11,720 lines** (over a third of the whole project — the gameplay
    simulation core)
  - `Tables.cpp`: 2,208 lines, `Decor.hpp`: 2,064 lines, `InputPad.cpp`: 1,970 lines,
    `Game1.cpp`: 1,113 lines
- `worlds/*.txt`: 78 files (text-based level / save-game format)
- `Content/icons/`: 9 sprite-atlas PNGs (`blupi.png`, `blupi1.png`, `object-m.png`, `element.png`,
  `explo.png`, `button.png`, `pad.png`, `jauge.png`, `text.png`)
- `Content/backgrounds/`: 38 PNGs (per-region background/decor art, e.g. `decor000.png`, plus
  title-screen art `blupiyoupie.png`)
- `Content/sounds/`: 93 `.wav` files
- Existing `.md` docs in the repo (input material, not a substitute for reading the source):
  `README.md`, `CLAUDE.md`, `ANDROID.md`, `AUDIO_ANALYSIS.md`, `ENUMS.md` (a **proposal**, not
  implemented code!), `RAM.md`, `WINDOWS.md`, `TODO.md`, `DOXYGEN_DOCUMENTATION_PLAN.md`,
  `.Net and XNA used part.md` (empty stub), `documentation/Cheat System.md`

## Sprite atlas algorithm (read directly from `Pixmap.cpp`, needed by Part V and the tools/ scripts)

`Pixmap::DrawIcon(channel, icon, ...)` (`Pixmap.cpp:509`) resolves an icon index to a source
rectangle in the channel's atlas via `Pixmap::GetSrcRectangle` (`Pixmap.cpp:683`):

```cpp
intcs column = icon % (width / bitmapGridX);
intcs row    = icon / (width / bitmapGridX);
// returns Rectangle(gap + column * (bitmapGridX + gap), gap + row * (bitmapGridY + gap),
//                    iconWidth, iconHeight)
```

Per-channel grid parameters (all at `RESOLUTION_SCALE = 1`, i.e. matching the raw PNGs on disk),
read from the `switch (channel)` in `Pixmap::DrawIcon` (`Pixmap.cpp:550`-`648`):

| Channel | File | Grid cell | Gap | Atlas size |
|---|---|---|---|---|
| `Blupi` / `Blupi1_11/12/13` | `blupi.png` / `blupi1.png` | 60×60 | 0 | 600×2040 (10×34 = 340 icons) |
| `Object` | `object-m.png` | 64×64 | 1 | 1301×1431 |
| `Element` | `element.png` | 60×60 | 0 | 600×1740 (10×29 = 290 icons) |
| `Explosion` | `explo.png` | 144×144 base grid, per-icon size from `Tables::table_explo_size[icon]` | 0 | 1440×1440 |
| `Text` | `text.png` | 32×32 | 0 | 512×256 |
| `Button` | `button.png` | 40×40 | 0 | 240×1040 |
| `Pad` | `pad.png` | 140×140 | 0 | 1120×420 |
| `Jauge` | `jauge.png` | 124×88 (whole image, single icon) | — | 124×88 |
| `SpeedyBlupiBackground` | `Content/backgrounds/*.png` (via `BackgroundCache`) | 640×160 | 0 | per-file |
| `BlupiYoupieBackground` | `blupiyoupie.png` | 410×380 | 0 | matches file |
| `GearBackground` | (gear background) | 226×226 | 0 | matches file |

**Resolved finding (originally logged here as an unverified hypothesis; corrected after Chapter 16
was actually written — this note is kept as a record of the correction, not the live claim):** the
initial guess was that `m_decor[][]`'s numeric `icon` values are a purely invisible
gameplay/collision layer, with all visible tile art coming from `Pixmap::BackgroundCache`-loaded
region images. **Reading `Decor.cpp`'s actual `Build()` tile loop showed this is half right and
half wrong.** In truth: `Decor` keeps *two* parallel grids, and for the large majority of tiles the
very same `m_decor[][]` icon integer is used both for collision (`IsPassIcon`/`IsBlocIcon`/etc.)
**and** as a direct sprite index into `PixmapChannel::Object` (`object-m.png`, a 1301×1431 atlas
with a 64×64 grid — not `Element` as first guessed) via `Pixmap::QuickIcon`. That resolves the
"icon numbers exceed 290" puzzle in the *opposite* direction from the original guess: they're not
avoiding `Element`'s small atlas by staying invisible, they're correctly indexing `Object`'s much
larger one (~440 usable slots, matching `MAXQUART = 441`). A small, specific exclusion list of
animated tiles (lava `68`, traps `373`, drips `404`/`410`, switch-doors `384`/`385`, etc.) is
handled by a second per-frame remapping pass instead of the direct 1:1 mapping, but even those are
ordinary animated sprites, not invisible logic — see Chapter 16 for the full, source-cited account.
This correction was propagated to Chapters 44/45 and Appendix C, which had drafted text based on
the original, incorrect hypothesis.

## Honest note on scope

The ask was for a book "as long as a thousand pages." `cna-bible` covers the **entire** CNA
ecosystem (CNA itself + 5 graphics backends + sharp-runtime + easy-gl + free-direct +
networking/audio/input/storage + cross-platform porting across 4 platforms + a dozen satellite
repos) and, holding the line that every claim must be source-grounded, still landed at 233 pages —
not the 4000 originally requested. `mobile-eggbert` is **one game**, ~31k lines, not an ecosystem.
A text-only honest estimate of genuinely unique, non-padded content is roughly **300–450 pages
equivalent** (at ~500 words/page) across 58 chapters + 7 appendices. The addition of a fully
illustrated sprite/animation catalog (potentially dozens of real extracted images across Part V)
and, if achievable, real screenshots, adds real additional size beyond that text estimate without
padding — images are not prose page-count filler, they are additional genuine content.

**Goal: maximum honest depth and completeness, not an artificial page count.** This document
tracks the actual estimated scope in "Chapter status" below and will be refined as work proceeds.

## Methodology

See `CLAUDE.md` for the full non-negotiable rules. Summary:

1. Every chapter is grounded in an actual read of the corresponding `.hpp`/`.cpp`/`.txt`/`.md`
   files in `mobile-eggbert` (and `cna`/`mobile-eggbert-legacy` only where truly needed for
   context — `cna` internals themselves are out of scope, see `CLAUDE.md`).
2. Code samples = real excerpts with `file:line` citations.
3. Images = real sprite crops, real screenshots, or clearly-labeled data-driven reconstructions —
   never fabricated. See `CLAUDE.md`'s "Images and screenshots" section.
4. `ENUMS.md` = an analysis/proposal document, not implemented code — must be labeled as such
   whenever cited.
5. Commit in small steps, push after each.
6. Chapters are drafted by sub-agents but must pass a review pass by the main session before being
   committed — spot-check grounding (does it actually cite real code?) and style consistency.

## Book structure — 58 chapters + 7 appendices, 11 parts

### Part I — Origins and the OpenEggbert Ecosystem (`part01-origins-and-ecosystem/`)
1. `ch01-what-is-mobile-eggbert.md` — History: Speedy Blupi → Windows Phone/XNA (2013) → ILSpy
   decompilation → MonoGame → C++ → CNA
2. `ch02-openeggbert-ecosystem-map.md` — Brief map of the OpenEggbert ecosystem (cna, sharp-runtime,
   mobile-eggbert-core/legacy/libgdx, galaxy-eggbert) — kept short; CNA itself is out of scope here
3. `ch03-license-and-provenance.md` — License, authorship, provenance (Epsitec SA, `LICENSE` file)

### Part II — Building and Running the Game (`part02-building-and-running/`)
4. `ch04-build-overview.md` — `CMakeLists.txt` in depth: targets, dependencies, submodules, backends
5. `ch05-linux-build.md` — Linux native build
6. `ch06-windows-and-cross-compilation.md` — Windows native build and MinGW-w64 cross-build from Linux
7. `ch07-direct3d-wine-proton.md` — D3D11/D3D12 backends via Wine/Proton on Linux
8. `ch08-web-emscripten-build.md` — Web/Emscripten build, virtual filesystem, IndexedDB save data
9. `ch09-android-build.md` — Android build (Gradle, NDK, `ANDROID.md` in depth)
10. `ch10-config-legacy-vs-modern.md` — `Config.hpp`: LEGACY vs MODERN mode, timing, resolution

### Part III — Architecture Overview (`part03-architecture/`)
11. `ch11-program-and-entry-point.md` — `Program.cpp`, the application entry point
12. `ch12-game1-state-machine.md` — `Game1`: the top-level XNA `Game`, the game-phase state machine
13. `ch13-igame1-and-dependencies.md` — `IGame1` interface, dependencies between subsystems
14. `ch14-xna-api-via-cna.md` — How mobile-eggbert's code maps onto the XNA-style API (brief on CNA internals by design)

### Part IV — The Decor Simulation (`part04-decor-simulation/`) — the largest part
15. `ch15-decor-overview.md` — `Decor`: overview of responsibilities and data model
16. `ch16-tile-map.md` — The 100×100 tile map, `Cellule`, coordinate systems, background-art vs.
    collision-layer separation
17. `ch17-blupi-state-machine.md` — Blupi: the player character's state machine
18. `ch18-blupi-actions-and-animation.md` — `BlupiAction` and animation sequencing
19. `ch19-moving-objects-and-decor-actions.md` — `MoveObject`, `DecorAction`, `ObjectType`
20. `ch20-enemy-and-creature-ai.md` — Enemy and creature AI behaviors
21. `ch21-physics-and-collision.md` — Movement physics and collision detection
22. `ch22-doors-keys-doorkeyflags.md` — Doors, keys, `DoorKeyFlags`, teleporters, lifts
23. `ch23-secret-powers-and-cheat-system.md` — `SecretPower`, the cheat system (`Cheat System.md`)
24. `ch24-missions-and-continuemission.md` — Mission objectives, `ContinueMission`, win/loss conditions
25. `ch25-game-speed-and-zoom.md` — `GameSpeed`, `Zoom`, time scaling
26. `ch26-tile-and-icon-catalog.md` — Catalog of gameplay tile behaviors from real `Is*()`
    predicates in `Decor.cpp` (cross-referencing `ENUMS.md` explicitly as a proposal document)
27. `ch27-decor-hpp-reference-catalog.md` — Full member catalog of `Decor.hpp` (methods, fields)

### Part V — Sprites, Rendering, and the Animation System (`part05-sprites-rendering-animation/`) — illustrated
28. `ch28-pixmap-ipixmap.md` — `Pixmap`/`IPixmap`: the sprite rendering layer
29. `ch29-sprite-atlas-system.md` — `PixmapChannel` and the icon-grid system, **with real atlas
    diagrams** (full atlas images with grid overlays showing how `GetSrcRectangle` slices them)
30. `ch30-tables-animation-and-movement-data.md` — `Tables.hpp`/`.cpp`: the animation and movement data tables
31. `ch31-blupi-animation-catalog.md` — **Illustrated**: every `BlupiAction` animation sequence,
    with real cropped frame strips extracted from `blupi.png`/`blupi1.png`
32. `ch32-creature-and-object-animation-catalog.md` — **Illustrated**: `ObjectType` creatures/objects
    with real cropped frames from `object-m.png`
33. `ch33-explosions-and-effects.md` — **Illustrated**: explosion/effect frames from `explo.png`
34. `ch34-backgrounds-and-level-art.md` — **Illustrated**: per-region background art from
    `Content/backgrounds/`
35. `ch35-text-rendering.md` — `Text`: text rendering (illustrated: the font atlas)
36. `ch36-jauge-hud-gauges.md` — `Jauge`: HUD gauge bars (illustrated)
37. `ch37-slider-ui-control.md` — `Slider`: UI slider control

### Part VI — Audio (`part06-audio/`)
38. `ch38-sound-isound-architecture.md` — `Sound`/`ISound` architecture
39. `ch39-soundchannel-and-mixing.md` — `SoundChannel`, volume/pitch (`tableVolumePitch`)
40. `ch40-audio-issue-analysis.md` — Analysis of `AUDIO_ANALYSIS.md`'s reported audio issues

### Part VII — Input (`part07-input/`)
41. `ch41-inputpad-touch-keyboard-accelerometer.md` — `InputPad`: unifying touch/keyboard/accelerometer
42. `ch42-keypressflags-and-mapping.md` — `KeyPressFlags` and input-to-action mapping

### Part VIII — Data, Persistence, and Content (`part08-data-persistence-content/`)
43. `ch43-gamedata-save-format.md` — `GameData`: save-game format, 3 gamer slots
44. `ch44-worlds-level-file-format.md` — `Worlds`: level loading, the level file's text format
45. `ch45-content-pipeline.md` — Content pipeline: icons, sounds, backgrounds
46. `ch46-myresource-resource-management.md` — `MyResource`: resource management

### Part IX — Support Types and Utilities (`part09-support-types/`)
47. `ch47-tinypoint-tinyrect.md` — `TinyPoint`, `TinyRect` (non-standard field order!)
48. `ch48-misc-utility-functions.md` — `Misc`: utility functions
49. `ch49-helper.md` — `Helper`
50. `ch50-def-core-definitions.md` — `Def.hpp`: core definitions and constants

### Part X — Platform Deep Dives (`part10-platform-deep-dives/`)
51. `ch51-android-deep-dive.md` — Android integration in depth (asset symlinks, APK packaging)
52. `ch52-windows-deep-dive.md` — Windows in depth (`WINDOWS.md`)
53. `ch53-web-virtual-filesystem.md` — Web/Emscripten virtual filesystem and IndexedDB persistence
54. `ch54-ram-memory-analysis.md` — Analysis of `RAM.md`'s memory-usage investigation

### Part XI — History, Migration, and Engineering Practice (`part11-history-and-practice/`)
55. `ch55-ilspy-decompilation-and-csharp-stubs.md` — ILSpy decompilation, residual C# stubs
    (`Microsoft.Xna.Framework.GamerServices`, `Microsoft.Devices.Sensors`)
56. `ch56-dotnet-and-xna-migration.md` — .NET/XNA migration (analysis of `.Net and XNA used part.md`)
57. `ch57-doxygen-methodology.md` — Doxygen documentation methodology (`DOXYGEN_DOCUMENTATION_PLAN.md`)
58. `ch58-todo-and-roadmap.md` — `TODO.md` and the forward roadmap

### Appendices (`appendices/`)
- A `appendix-a-class-and-file-catalog.md` — Full class and file catalog
- B `appendix-b-enum-catalog.md` — Full catalog of real `enum class` definitions in the codebase
- C `appendix-c-level-file-format-spec.md` — Level file format specification (`worlds/*.txt`)
- D `appendix-d-glossary.md` — Glossary of terms
- E `appendix-e-cheat-code-reference.md` — Cheat code reference
- F `appendix-f-repository-map.md` — OpenEggbert repository map (quick reference)
- G `appendix-g-screenshot-gallery.md` — Screenshot and visual asset gallery (index of every real
  image in `book/images/`, with provenance notes per `CLAUDE.md`'s three allowed image categories)

## Images pipeline (`tools/`)

- `tools/extract_sprites.py` (planned) — crops real sprite frames from `Content/icons/*.png` using
  the exact `GetSrcRectangle` grid algorithm above, driven by animation-sequence data read from
  `Tables.cpp`/`Tables.hpp`. Outputs per-action/per-object contact-sheet PNGs into `book/images/`.
- `tools/render_level_map.py` (planned) — renders a real `worlds/*.txt` level's collision-layer
  grid as a color-coded diagram (by tile behavior category, from the real `Is*()` predicates), for
  Part IV and Appendix C. Labeled explicitly as a data reconstruction, not a screenshot.
- Real gameplay/UI screenshots: attempted via a headless build (`SOFTWARE` backend or
  `SDL_RENDERER`/`EASYGL` under `Xvfb`), following the method `cna-bible`'s
  `tools/cna-screenshot-infra/README.md` proved out for CNA's own demos. Status tracked in
  `NEXT.md` — this is genuinely uncertain to succeed for a full game (vs. a small demo) within one
  session; if it doesn't pan out, Appendix G and the affected chapters say so explicitly instead of
  faking a screenshot.

## Chapter status

Status column: `not written` / `in progress` / `done (unreviewed)` / `done (reviewed)`. The
authoritative, continuously-updated status is `book/SUMMARY.md` — this table in `PLAN.md` is only
for planning work waves, not day-to-day status.

- **Wave 0 (scaffolding):** README, CLAUDE.md, PLAN.md, NEXT.md, PROGRESS.md, `book/SUMMARY.md`,
  directory skeleton for all 11 parts + appendices + `book/images/` + `tools/`.
- **Wave 1:** Part I–IV (chapters 1–27) — text-only, no image dependency.
- **Image pipeline:** `tools/extract_sprites.py`, `tools/render_level_map.py`, run to produce
  `book/images/*.png` — must complete before Part V's illustrated chapters are finalized.
- **Wave 2:** Part V–VIII (chapters 28–46) — Part V chapters depend on the image pipeline above.
- **Wave 3:** Part IX–XI + appendices (chapters 47–58 + A–G).
- **Screenshot attempt:** best-effort headless build + capture, in parallel with the waves above;
  outcome (success/partial/blocked) recorded in `NEXT.md` and Appendix G.

## Session log

### 2026-07-28 — Project founding, then pivot to English + illustrated scope
- Empty `mobile-eggbert-bible` repository (no commits). Added and cloned `mobile-eggbert` (primary
  source) and `cna-bible` (style/methodology model) into the session.
- Measured source code size (31,301 lines of C++, `Decor.cpp` = 11,720 lines as the core).
- First draft of the plan was written in **Czech** with 54 chapters/6 appendices and no image
  plan. The author then clarified mid-session: (1) the book must be in **English**; (2) CNA is to
  be covered only marginally, mobile-eggbert is the sole subject; (3) the book must include real
  screenshots from the game and a **complete, illustrated animation system** with real images.
  Rewrote all scaffolding in English and expanded the plan to 58 chapters + 7 appendices,
  including a new illustrated sub-part (Part V, chapters 28–37) and Appendix G for the visual
  gallery.
- Reverse-engineered the exact sprite-atlas slicing algorithm directly from `Pixmap.cpp`
  (`GetSrcRectangle`, the per-channel grid table in `DrawIcon`) to make real, pixel-accurate sprite
  extraction possible — recorded above for `tools/extract_sprites.py` to use.
- Found (pending in-chapter verification) that the visible per-region background art comes from
  `Pixmap::BackgroundCache`/`Content/backgrounds/decorNNN.png`, while the numeric tile-grid `icon`
  values in `Decor::m_decor[][]` are a separate, invisible gameplay-classification layer — an
  important structural fact for Part IV/Appendix C.
- Recorded the honest scope estimate: 300–450 pages of text-equivalent content across 58 chapters
  + 7 appendices, plus genuine additional size from the illustrated sprite/animation catalog and
  (if achievable) real screenshots — not a padded 1000 pages.
