# Appendix A: Class and File Catalog

This appendix catalogs every `.hpp` and `.cpp` file in `include/WindowsPhoneSpeedyBlupi/` and
`src/WindowsPhoneSpeedyBlupi/` as of `mobile-eggbert`'s `develop` branch (commit `07e0a67`,
measured 2026-07-28 — see `PLAN.md`). The count is **34 headers** and **16 source files**, for
**50 files** and **31,394 lines** total (verified directly with `find`/`wc -l`, not taken on
faith from prior documentation).

Purposes are drawn from each file's top-of-file Doxygen `@file`/`@brief` comment — per
`DOXYGEN_DOCUMENTATION_PLAN.md`, every file in this codebase is required to carry one, and in
practice all 50 do. Chapter pointers cross-reference the real chapter list and titles in
[`book/SUMMARY.md`](../SUMMARY.md).

Files are grouped into seven subsystems. Within each group, headers are listed before their
matching `.cpp` (where one exists), otherwise alphabetically.

## Directory layout

The 34 headers are not flat: 28 live directly under `include/WindowsPhoneSpeedyBlupi/`, 3 live
under `include/WindowsPhoneSpeedyBlupi/decor/` (`DecorAction.hpp`, `DoorKeyFlags.hpp`,
`ObjectType.hpp`), and 9 live under `include/WindowsPhoneSpeedyBlupi/def/` (`BlupiAction.hpp`,
`ContinueMission.hpp`, `Direction.hpp`, `GameSpeed.hpp`, `KeyPressFlags.hpp`, `PixmapChannel.hpp`,
`SecretPower.hpp`, `SoundChannel.hpp`, `Zoom.hpp`). All 16 `.cpp` files live directly under
`src/WindowsPhoneSpeedyBlupi/` — there is no `src/.../decor/` or `src/.../def/` mirror, because
every file in those two header-only subdirectories is a self-contained `enum class` plus
`constexpr` helper functions with no out-of-line definitions to place in a `.cpp`. This is a
deliberate convention: `decor/` holds gameplay-object enums used by `Decor.cpp`, and `def/` holds
the smaller, broadly-shared enums referenced from multiple subsystems (e.g. `GameSpeed` is read
by both `Game1` and `InputPad`).

Two files are conditionally compiled in whole or in part:

- `def/Zoom.hpp` is wrapped in `#ifdef MODERN … #endif` — the entire file, including the
  `ZoomCheat` enum, does not exist at all in a LEGACY build.
- `Tables.hpp`'s `CheatCodes` enum has a `Quick` enumerator gated on `#ifndef LEGACY` and four more
  (`Ghost`, `Debug`, `Zoom`, `Cheats`) gated on `#ifdef MODERN` — see
  [Appendix E](appendix-e-cheat-code-reference.md) for the full cheat-code reference.

## 1. Entry Point

| File | Lines | Purpose | Chapter(s) |
|---|---:|---|---|
| `src/.../Program.cpp` | 83 | Application entry point: constructs `Game1`, runs its loop, wraps the whole thing in `try`/`catch` blocks that log fatal errors via `CNA::Logger` and exit with code 1. On Android, `main` is renamed to `SDL_main` by `CNA/Entrypoint.hpp` so SDL's Java bridge can find it. | [Ch. 11](../part03-architecture/ch11-program-and-entry-point.md) |

## 2. Core Simulation (Game1, Decor, and their gameplay enums)

This is the largest subsystem by both file count and line count: `Decor.cpp` alone (11,720
lines) is over a third of the entire codebase.

| File | Lines | Purpose | Chapter(s) |
|---|---:|---|---|
| `include/.../Game1.hpp` | 955 | Declares `Game1`, the top-level XNA-style `Game`: owns every subsystem (graphics, audio, gameplay, input, save data) and runs the `Initialize`/`LoadContent`/`Update`/`Draw` loop behind a `Def::Phase` state machine funnelled through `SetPhase()`. | [Ch. 12](../part03-architecture/ch12-game1-state-machine.md) |
| `src/.../Game1.cpp` | 1,113 | Implements `Game1`'s phase-transition graph (`None → First → Wait → Init → Play/…`) and per-frame `Update`/`Draw` bodies. | [Ch. 12](../part03-architecture/ch12-game1-state-machine.md) |
| `include/.../IGame1.hpp` | 301 | Declares the `IGame1` interface: the minimal callback surface `Decor`, `InputPad`, `Pixmap`, and `Sound` use to reach back into `Game1` without circular header includes (lifecycle hooks, property accessors, phase/mission control, draw helpers). | [Ch. 13](../part03-architecture/ch13-igame1-and-dependencies.md) |
| `include/.../Def.hpp` | 215 | The `Def` static class: global compile-time constants (sprite-cell dimensions, viewport size, legacy channel IDs) plus the `Phase` and `ButtonGlyph` enums that drive the state machine and UI overlay. | [Ch. 50](../part09-support-types/ch50-def-core-definitions.md) (also [Ch. 12](../part03-architecture/ch12-game1-state-machine.md) for `Phase`) |
| `include/.../Decor.hpp` | 2,064 | Declares `Decor`, the heart of the gameplay subsystem: owns the 100×100 tile map, the Blupi state machine, all active moving objects, door/switch state, and every mechanic (physics, collision, animation sequencing, viewport scrolling, sound triggering, win/loss). A direct C++ port of the original XNA/C# `Decor`. | [Ch. 15](../part04-decor-simulation/ch15-decor-overview.md), [Ch. 27](../part04-decor-simulation/ch27-decor-hpp-reference-catalog.md) |
| `src/.../Decor.cpp` | 11,720 | Implements the full per-frame simulation: tile physics/collision, the Blupi action state machine, every moving-object AI, lift ("ascenseur") and teleporter mechanics, crate ("caisse") pushing, particle/effect spawning, sound triggering, scrolling, and level I/O. The single entry point `MoveStep()` runs these sub-systems in a fixed order every tick. | [Ch. 15](../part04-decor-simulation/ch15-decor-overview.md)–[Ch. 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) |
| `include/.../decor/DecorAction.hpp` | 124 | Defines `enum class DecorAction`: the camera-shake animation the engine plays on the background layer (`None`, `SmallShake`, `BigShake`, `ElectricShake`), driven by `Tables::table_decor_action`. | [Ch. 19](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md) |
| `include/.../decor/DoorKeyFlags.hpp` | 174 | Defines `enum class DoorKeyFlags`, a bitmask of which of Blupi's three collectible keys are held, tested/combined via overloaded `\|`/`&` operators and stored in `Decor::m_blupiCle`. | [Ch. 22](../part04-decor-simulation/ch22-doors-keys-doorkeyflags.md) |
| `include/.../decor/ObjectType.hpp` | 426 | Defines `enum class ObjectType`: every species of moving object (`MoveObject`) the engine can spawn — enemies, crates, projectiles, collectibles, lifts, hazards, effects — as numeric IDs inherited verbatim from the original game and preserved for level-file compatibility. | [Ch. 19](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md), [Ch. 32](../part05-sprites-rendering-animation/ch32-creature-and-object-animation-catalog.md) |
| `include/.../def/BlupiAction.hpp` | 152 | Defines `enum class BlupiAction`: all 88 named animation/movement states of the player character (idle, walking, jumping, vehicle modes, hazard contacts, celebration, etc.), ported verbatim from the original `ACTION_*` C# constants. | [Ch. 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md), [Ch. 31](../part05-sprites-rendering-animation/ch31-blupi-animation-catalog.md) |
| `include/.../def/Direction.hpp` | 59 | Defines `enum class Direction` (`None`/`Left`/`Right`): Blupi's or an enemy's horizontal facing, used for sprite flipping and movement. | [Ch. 17](../part04-decor-simulation/ch17-blupi-state-machine.md) |
| `include/.../def/GameSpeed.hpp` | 137 | Defines `enum class GameSpeed` (`Slow=0, Normal=1, Fast=2, Faster=4, Fastest=8`), a multiplier controlling simulation ticks per rendered frame; ordering operators and an F5–F8 keyboard-to-speed mapping (MODERN builds only). | [Ch. 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md) |
| `include/.../def/ContinueMission.hpp` | 57 | Defines `enum class ContinueMissionType` (`None`/`Pending`/`Active`): tracks whether a "continue from checkpoint" request is queued, letting `Game1` skip replaying the full level-start sequence. | [Ch. 24](../part04-decor-simulation/ch24-missions-and-continuemission.md) |
| `include/.../def/SecretPower.hpp` | 64 | Defines `enum class SecretPower` (`None`/`Shield`/`Power`/`Cloud`/`Hide`): the single hidden power-up bonus active for Blupi at any time, affecting collision handling and capabilities. | [Ch. 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) |
| `include/.../def/Zoom.hpp` | 32 | Defines `enum class ZoomCheat` (`Zoom100`/`50`/`25`/`12`), a MODERN-only debug render-scale cheat, entirely absent from LEGACY builds (`#ifdef MODERN` guards the whole file). | [Ch. 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md) |

## 3. Rendering and the Sprite/Animation System

| File | Lines | Purpose | Chapter(s) |
|---|---:|---|---|
| `include/.../IPixmap.hpp` | 238 | Declares the `IPixmap` interface: the pure-virtual API for loading texture atlases, coordinate conversion, sprite drawing, background rendering, and batch-draw optimisation. Implemented by `Pixmap`. | [Ch. 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md) |
| `include/.../Pixmap.hpp` | 609 | Declares `Pixmap`, the concrete SDL3/XNA `SpriteBatch`-style implementation of `IPixmap`: owns every texture atlas, the per-frame viewport geometry (zoom/origin), and dispatches all draw calls, optionally batched via `BeginBatch()`/`EndBatch()`. | [Ch. 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md), [Ch. 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md) |
| `src/.../Pixmap.cpp` | 781 | Implements viewport zoom/origin transforms, texture loading, and the `GetSrcRectangle`/`DrawIcon` sprite-atlas slicing algorithm used to pixel-accurately crop every icon channel. | [Ch. 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md), [Ch. 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md) |
| `include/.../def/PixmapChannel.hpp` | 99 | Defines `enum class PixmapChannel`, identifying which sprite-sheet atlas (`Object`, `Blupi`, `Background`, `Explosion`, `Element`, …) a draw call targets; mirrors the legacy `CH*` integer constants in `Def`. Gaps at indices 7–8 are intentionally unused. | [Ch. 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md) |
| `include/.../Tables.hpp` | 1,019 | Declares the non-instantiable `Tables` class: every static game-data table (animation sequences, speed curves, quarter-tile adaptation, explosion/hazard data, power-up tables, the `CheatCodes` enum) ported value-for-value from the original C#. | [Ch. 30](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md) |
| `src/.../Tables.cpp` | 2,208 | Defines the storage for every table declared in `Tables.hpp` (the largest, `table_blupi`, has 2,911 entries) plus `Tables::Init()`. | [Ch. 30](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md) |
| `include/.../Text.hpp` | 216 | Declares the `Text` static class: bitmap text rendering backed by the font sprite sheet (`PixmapChannel::Text`), with left-aligned, centred, and slanted ("pente") variants and pixel-width measurement. | [Ch. 35](../part05-sprites-rendering-animation/ch35-text-rendering.md) |
| `src/.../Text.cpp` | 328 | Implements glyph-table lookup (`table_char`, 256×6 records) and the diagonal "pente" slant transform. | [Ch. 35](../part05-sprites-rendering-animation/ch35-text-rendering.md) |
| `include/.../Jauge.hpp` | 238 | Declares `Jauge` (a 124×22px HUD gauge bar for energy/time/key indicators) and `enum class JaugeMode` (`Empty`/`Red`/`Blue`/`Yellow`), one sprite row per mode. | [Ch. 36](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md) |
| `src/.../Jauge.cpp` | 160 | Implements `Jauge`'s two-flag redraw-dirty optimisation (`m_bMinimizeRedraw`/`m_bRedraw`) to skip unnecessary GPU fills. | [Ch. 36](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md) |
| `include/.../Slider.hpp` | 117 | Declares `Slider`, a draggable horizontal UI widget used on the settings screen for accelerometer sensitivity, mapping touch/click X position to a normalised `[0,1]` value. | [Ch. 37](../part05-sprites-rendering-animation/ch37-slider-ui-control.md) |
| `src/.../Slider.cpp` | 113 | Implements the drag-to-value mapping and clamping logic for `Slider::Move()`. | [Ch. 37](../part05-sprites-rendering-animation/ch37-slider-ui-control.md) |

## 4. Audio

| File | Lines | Purpose | Chapter(s) |
|---|---:|---|---|
| `include/.../ISound.hpp` | 134 | Declares the `ISound` interface: pure-virtual API for loading sound assets, positional playback, volume control, and stopping playback, using the logical 640×480 game-space coordinate system. | [Ch. 38](../part06-audio/ch38-sound-isound-architecture.md) |
| `include/.../Sound.hpp` | 427 | Declares `Sound`, the concrete `ISound` implementation: loads up to 93 WAV assets, maps `SoundChannel` to asset index, computes stereo volume/balance from HUD-space position, tracks up to 10 simultaneous `Play` instances, and drops duplicate channel-conflicting plays (except `SoundChannel10`, which always stacks). | [Ch. 38](../part06-audio/ch38-sound-isound-architecture.md), [Ch. 39](../part06-audio/ch39-soundchannel-and-mixing.md) |
| `src/.../Sound.cpp` | 335 | Implements asset loading (`sounds/sound000.wav`…`sound092.wav`), the `GetVolume()`/`GetBalance()` stereo-positioning formulas, and the `SOUND_DISABLED` stub path for headless builds. | [Ch. 38](../part06-audio/ch38-sound-isound-architecture.md), [Ch. 39](../part06-audio/ch39-soundchannel-and-mixing.md) |
| `include/.../def/SoundChannel.hpp` | 177 | Defines `enum class SoundChannel` (`SoundChannel0`…`SoundChannel92`), one enumerator per WAV asset index; channel 0 is reserved, 1–92 are real effects, and the numbering must never change. | [Ch. 39](../part06-audio/ch39-soundchannel-and-mixing.md) |

## 5. Input

| File | Lines | Purpose | Chapter(s) |
|---|---:|---|---|
| `include/.../InputPad.hpp` | 497 | Declares `InputPad`, the single point of contact between platform input (touch, mouse, keyboard, accelerometer) and the game state machine; translates raw events into `ButtonGlyph` presses and directional speeds. LEGACY/MODERN/`INPUT_DISABLED` build variants change feature scope (cheat buffer, debug overlay, virtual keyboard). | [Ch. 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) |
| `src/.../InputPad.cpp` | 1,970 | Implements per-frame polling of every input source, the accelerometer dead-zone/hysteresis/speed-ramp formulas, and (MODERN only) the typed-cheat-code buffer and debug/zoom/quick-speed cheat dispatch. | [Ch. 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md), [Ch. 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) |
| `include/.../def/KeyPressFlags.hpp` | 63 | Defines `enum class KeyPressFlags`, a bitmask of active virtual buttons (`Jump=1, Fire=2, Down=4`) produced by `InputPad` and consumed by `Decor`'s state machine. | [Ch. 42](../part07-input/ch42-keypressflags-and-mapping.md) |

## 6. Data, Persistence, and Content

| File | Lines | Purpose | Chapter(s) |
|---|---:|---|---|
| `include/.../GameData.hpp` | 369 | Declares `GameData`: persistent save data for up to three gamer slots, serialised into a flat 640-byte array mirroring the original Windows Phone save format exactly. | [Ch. 43](../part08-data-persistence-content/ch43-gamedata-save-format.md) |
| `src/.../GameData.cpp` | 172 | Implements the byte-array accessors and default-initialisation logic per the documented offset schema (10-byte global header + 3×210-byte gamer blocks). | [Ch. 43](../part08-data-persistence-content/ch43-gamedata-save-format.md) |
| `include/.../Worlds.hpp` | 540 | Declares `Worlds`: static helpers reading/writing level files and save-game data in the line-based `<section>: field=value …` text format, including the special `Decor:`/`Doors:` sections. | [Ch. 44](../part08-data-persistence-content/ch44-worlds-level-file-format.md) |
| `src/.../Worlds.cpp` | 728 | Implements the field-level parser/serialiser (`int`, `double`, `bool`, `point`, `int[]` encodings) and the safe-default fallback behaviour for missing/malformed fields. | [Ch. 44](../part08-data-persistence-content/ch44-worlds-level-file-format.md) |
| `include/.../MyResource.hpp` | 364 | Declares `MyResource`: localised UI strings (button labels, gamer stats, trial-mode upsell text, training-world hints) keyed by integer `TX_*` resource IDs across French/English/German locales. | [Ch. 46](../part08-data-persistence-content/ch46-myresource-resource-management.md) |
| `src/.../MyResource.cpp` | 662 | Implements locale detection (`std::locale("")`, `"fr"`/`"de"`/default-English) and the three `InitializeFR()`/`InitializeEN()`/`InitializeDE()` string-table populators (German currently falls back to French text for training hints). | [Ch. 46](../part08-data-persistence-content/ch46-myresource-resource-management.md) |
| `include/.../Tables.hpp` | 1,019 | *(listed above under Rendering — Tables is primarily animation/movement data, but it is also the canonical data-table content of the engine.)* | [Ch. 30](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md) |
| `src/.../Tables.cpp` | 2,208 | *(see above)* | [Ch. 30](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md) |

## 7. Utilities and Support Types

| File | Lines | Purpose | Chapter(s) |
|---|---:|---|---|
| `include/.../Misc.hpp` | 226 | Declares the `Misc` static utility class: rectangle intersection/union, point rotation (standard 2D rotation matrix), and angle/direction conversions — all pure, side-effect-free functions. | [Ch. 48](../part09-support-types/ch48-misc-utility-functions.md) |
| `src/.../Misc.cpp` | 133 | Implements the geometry helpers declared in `Misc.hpp`. | [Ch. 48](../part09-support-types/ch48-misc-utility-functions.md) |
| `include/.../Helper.hpp` | 70 | Declares `Helper`, a lightweight C#-style `String.Format`-alike (`{N}` placeholder substitution) and convenience macros; added during the C++ port, not part of the original game logic. | [Ch. 49](../part09-support-types/ch49-helper.md) |
| `src/.../Helper.cpp` | 46 | Implements `Helper::formatString()`: out-of-range placeholders are left verbatim, all occurrences of a given placeholder are replaced, no recursive substitution. | [Ch. 49](../part09-support-types/ch49-helper.md) |
| `include/.../TinyPoint.hpp` | 84 | Declares `TinyPoint`: the primary lightweight 2D integer screen-coordinate carrier (`X`, `Y` as `intcs`), used throughout the game. | [Ch. 47](../part09-support-types/ch47-tinypoint-tinyrect.md) |
| `include/.../TinyRect.hpp` | 140 | Declares `TinyRect`, a lightweight integer rectangle — **with a non-standard field order** (`Left, Right, Top, Bottom`, not the conventional `Left, Top, Right, Bottom`), preserved from the original C# codebase. | [Ch. 47](../part09-support-types/ch47-tinypoint-tinyrect.md) |
| `src/.../TinyRect.cpp` | 32 | Implements `TinyRect`'s non-inline methods, repeating the field-order warning at the top of the file. | [Ch. 47](../part09-support-types/ch47-tinypoint-tinyrect.md) |
| `include/.../Config.hpp` | 258 | Declares `Config`: compile-time constants selecting LEGACY (original 20 FPS behaviour, unchanged) vs. MODERN (higher frame rates, touch-button auto-hiding, `ScaleTime()`/`ScaleDiv()` required everywhere timing matters) build modes. Exactly one of `LEGACY`/`MODERN` must be defined. | [Ch. 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md) |
| `include/.../ConfigDef.hpp` | 72 | Defines `enum class ResolutionScale` (`ScaleResolution1/2/4`) and `enum class Fps` (`Fps20/30/60/90/120/144`) plus their default constants — shared, unconditional definitions included by `Config.hpp` before the LEGACY/MODERN guards take effect. | [Ch. 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md) |

## Totals

| Metric | Count |
|---|---:|
| Header files (`.hpp`) | 34 |
| Source files (`.cpp`) | 16 |
| Total files | 50 |
| Total lines (headers + sources) | 31,394 (per `PLAN.md`, measured with `wc -l`) |
| Largest header | `Decor.hpp` — 2,064 lines |
| Largest source | `Decor.cpp` — 11,720 lines (over a third of the whole codebase) |
| Smallest header | `def/Zoom.hpp` — 32 lines (MODERN-only, `#ifdef`-guarded) |
| Smallest source | `TinyRect.cpp` — 32 lines |

## Notes on grouping

A handful of files legitimately serve two subsystems and are cross-listed rather than force-fit
into one bucket:

- **`Tables.hpp`/`Tables.cpp`** are gameplay/animation *data* consumed heavily by both `Decor`
  (movement, collision) and `Pixmap`/`Text` (sprite-frame sequencing). They are grouped under
  Rendering above (matching [Chapter 30](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md)'s
  placement in Part V) and cross-referenced from Data.
- **`Def.hpp`** contributes both engine-wide constants (support-type role) and the `Phase`/
  `ButtonGlyph` enums that are pure state-machine material for `Game1`; it is grouped with Core
  Simulation and also pointed to from [Chapter 50](../part09-support-types/ch50-def-core-definitions.md).
- **`InputPad.cpp`** implements the MODERN-only typed-cheat-code buffer described in
  [Appendix E](appendix-e-cheat-code-reference.md), even though its primary role is input
  translation — hence the cross-reference to Chapter 23 above.

No file in this catalog lacks a `@file`/`@brief` Doxygen header; per `CLAUDE.md`'s documentation
methodology, the purpose descriptions above are drawn directly from those comments (occasionally
supplemented by a class-level `@brief`/`@details` one level down when the file-level comment was
terse), not inferred from filenames.

## See also

- [Appendix B: Enum Catalog](appendix-b-enum-catalog.md) — the `enum class` types declared inside
  the `decor/` and `def/` header groups catalogued above.
- [Appendix E: Cheat Code Reference](appendix-e-cheat-code-reference.md) — the cross-subsystem
  behaviour of `InputPad.cpp`'s typed-cheat-code buffer, noted under Rendering/Input above.
- [Appendix F: Repository Map](appendix-f-repository-map.md) — how this repository's own files
  relate to the sibling `cna`/`sharp-runtime` repositories they depend on.
- [Chapter 15: Decor — Overview](../part04-decor-simulation/ch15-decor-overview.md) and
  [Chapter 27: Decor.hpp Reference Catalog](../part04-decor-simulation/ch27-decor-hpp-reference-catalog.md)
  — the narrative treatment of this catalog's largest single subsystem.
