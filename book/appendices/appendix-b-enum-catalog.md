# Appendix B: Enum Catalog

This appendix catalogs every `enum class` **actually defined and compiled** in `mobile-eggbert`,
found by grepping `enum class` across `include/WindowsPhoneSpeedyBlupi/**/*.hpp` and verifying
each hit is a real definition (not a forward declaration or a comment). The estimate going into
this catalog was "around a dozen or more" (`PLAN.md`); the real count is **19** distinct `enum
class` types — noticeably more than estimated, mostly because the small single-purpose enums
under `include/WindowsPhoneSpeedyBlupi/def/` (`ContinueMission.hpp`, `Zoom.hpp`, etc.) each get
their own file and were not all individually anticipated.

One grep hit was excluded as a false positive: `ISound.hpp:14` contains
`enum class SoundChannel : SharpRuntime::ubytecs;`, which is a **forward declaration**, not a
definition — the real `SoundChannel` is defined in `def/SoundChannel.hpp` (catalogued below). A
second near-hit, a `//TODO` comment in `Def.hpp:168` that mentions "the enum class PixmapChannel"
in passing, is prose, not code, and is likewise excluded.

A clearly separate, clearly labeled section at the end of this appendix lists the **proposed, not
implemented** enums from `ENUMS.md` — a refactoring analysis document, not existing code (see
`CLAUDE.md`'s non-negotiable methodology). Confusing the two categories would misrepresent the
codebase's actual state, so they are never merged into one table.

## Quick index

| # | Enum | Underlying type | Values | Defined in | Chapter |
|---|---|---|---:|---|---|
| 1 | `BlupiAction` | `ubytecs` | 88 | `def/BlupiAction.hpp` | [Ch. 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md) |
| 2 | `Direction` | `ubytecs` | 3 | `def/Direction.hpp` | [Ch. 17](../part04-decor-simulation/ch17-blupi-state-machine.md) |
| 3 | `GameSpeed` | `ubytecs` | 5 | `def/GameSpeed.hpp` | [Ch. 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md) |
| 4 | `KeyPressFlags` | `ushortcs` | 4 (bitmask) | `def/KeyPressFlags.hpp` | [Ch. 42](../part07-input/ch42-keypressflags-and-mapping.md) |
| 5 | `SecretPower` | `ushortcs` | 5 | `def/SecretPower.hpp` | [Ch. 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) |
| 6 | `DecorAction` | `ubytecs` | 4 | `decor/DecorAction.hpp` | [Ch. 19](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md) |
| 7 | `DoorKeyFlags` | `ubytecs` | 5 (bitmask, incl. `All`) | `decor/DoorKeyFlags.hpp` | [Ch. 22](../part04-decor-simulation/ch22-doors-keys-doorkeyflags.md) |
| 8 | `ObjectType` | `ubytecs` | 139 named (~66 known + ~73 "purpose unknown") | `decor/ObjectType.hpp` | [Ch. 19](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md), [Ch. 32](../part05-sprites-rendering-animation/ch32-creature-and-object-animation-catalog.md) |
| 9 | `ContinueMissionType` | `ushortcs` | 3 | `def/ContinueMission.hpp` | [Ch. 24](../part04-decor-simulation/ch24-missions-and-continuemission.md) |
| 10 | `PixmapChannel` | `ubytecs` | 16 (2 gaps) | `def/PixmapChannel.hpp` | [Ch. 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md) |
| 11 | `SoundChannel` | `ubytecs` | 93 | `def/SoundChannel.hpp` | [Ch. 39](../part06-audio/ch39-soundchannel-and-mixing.md) |
| 12 | `Def::Phase` | `int` (implicit) | 13 | `Def.hpp` | [Ch. 12](../part03-architecture/ch12-game1-state-machine.md) |
| 13 | `Def::ButtonGlyph` | `int` (implicit) | 45 | `Def.hpp` | [Ch. 12](../part03-architecture/ch12-game1-state-machine.md) |
| 14 | `JaugeMode` | `intcs` | 4 | `Jauge.hpp` | [Ch. 36](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md) |
| 15 | `Tables::CheatCodes` | `int` (implicit) | 22 base + up to 5 build-gated | `Tables.hpp` | [Appendix E](appendix-e-cheat-code-reference.md), [Ch. 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) |
| 16 | `ResolutionScale` | `int` (implicit) | 3 | `ConfigDef.hpp` | [Ch. 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md) |
| 17 | `Fps` | `int` (implicit) | 6 | `ConfigDef.hpp` | [Ch. 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md) |
| 18 | `ZoomCheat` | `int` (implicit) | 4 | `def/Zoom.hpp` (MODERN only) | [Ch. 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md) |
| 19 | `Decor::IconType` | *(none — empty)* | 0 | `Decor.hpp` (nested, private) | [Ch. 27](../part04-decor-simulation/ch27-decor-hpp-reference-catalog.md) |

---

## 1. `BlupiAction` — player action/animation state (88 values)

*From `def/BlupiAction.hpp:35`.* `using BlupiActionUnderlying = SharpRuntime::ubytecs;` Values are
ported verbatim from the original game's `ACTION_*` C# constants; the mapping from action to
sprite frame lives in `Tables.hpp`/`Tables.cpp`, not here. Grouped below by the naming families
the header itself documents (Stop/March/Turn per vehicle mode, Jump/Air, Ouf recovery, hazard
contacts).

| Value | Raw | Meaning | Value | Raw | Meaning |
|---|---:|---|---|---:|---|
| `None` | 0 | Uninitialised state | `StopSkate` | 37 | Skateboard idle |
| `Stop` | 1 | Standing still | `MarchSkate` | 38 | Skating forward |
| `March` | 2 | Walking | `TurnSkate` | 39 | Turning on skateboard |
| `Turn` | 3 | Turning around | `JumpSkate` | 40 | Jumping on skateboard |
| `Jump` | 4 | Jumping | `AirSkate` | 41 | Airborne on skateboard |
| `Air` | 5 | Airborne / falling | `TakeSkate` | 42 | Picking up skateboard |
| `Down` | 6 | Moving down | `DeposeSkate` | 43 | Putting down skateboard |
| `Up` | 7 | Moving up | `Ouf1a` | 44 | Relief animation, variant 1a |
| `Vertigo` | 8 | Hanging on a ledge in fear | `Ouf1b` | 45 | Relief animation, variant 1b |
| `Recede` | 9 | Moving backward | `Ouf2` | 46 | Relief animation, variant 2 |
| `Advance` | 10 | Moving forward | `Ouf3` | 47 | Relief animation, variant 3 |
| `Clear1` | 11 | Clearing/erasing animation 1 | `Ouf4` | 48 | Relief animation, variant 4 |
| `Set` | 12 | Placing/setting an object | `Sucette` | 49 | Collecting a lollipop power-up |
| `Win` | 13 | Level-win celebration | `StopTank` | 50 | Tank idle |
| `Push` | 14 | Pushing a crate | `MarchTank` | 51 | Driving tank |
| `StopHelico` | 15 | Hovering (helicopter) | `TurnTank` | 52 | Turning tank |
| `MarchHelico` | 16 | Flying forward (helicopter) | `FireTank` | 53 | Tank firing |
| `TurnHelico` | 17 | Turning (helicopter) | `Glu` | 54 | Stuck in glue/trap |
| `StopNage` | 18 | Treading water | `Drink` | 55 | Drinking a power-up |
| `MarchNage` | 19 | Swimming forward | `Charge` | 56 | Being charged at by an enemy |
| `TurnNage` | 20 | Turning while swimming | `Electro` | 57 | Electrocuted |
| `StopSurf` | 21 | Surfboard idle | `HelicoGlu` | 58 | Helicopter stuck in glue |
| `MarchSurf` | 22 | Surfing forward | `TurnAir` | 59 | Turning while airborne |
| `TurnSurf` | 23 | Turning on surfboard | `StopMarch` | 60 | Decelerating from walk to stop |
| `Drown` | 24 | Drowning in deep water | `StopJump` | 61 | Jump landing |
| `StopJeep` | 25 | Jeep idle | `StopJumph` | 62 | High-jump landing |
| `MarchJeep` | 26 | Driving jeep | `Mockery` | 63 | Enemy mocking Blupi |
| `TurnJeep` | 27 | Turning jeep | `Mockeryi` | 64 | Enemy mocking Blupi, inverted |
| `StopPop` | 28 | Pop-star idle | `Ouf5` | 65 | Relief animation, variant 5 |
| `Pop` | 29 | Pop-star dancing/moving | `Balloon` | 66 | Balloon mode |
| `Bye` | 30 | Farewell/exit animation | `StopOver` | 67 | Flat/squashed idle |
| `StopSuspend` | 31 | Hanging idle | `MarchOver` | 68 | Moving while flat |
| `MarchSuspend` | 32 | Moving while hanging | `TurnOver` | 69 | Turning while flat |
| `TurnSuspend` | 33 | Turning while hanging | `Recedeq` | 70 | Quick backward movement |
| `JumpSuspend` | 34 | Jumping from a hanging position | `Advanceq` | 71 | Quick forward movement |
| `Hide` | 35 | Hiding | `StopEcrase` | 72 | Crushed idle |
| `JumpAie` | 36 | Hurt-jump | `MarchEcrase` | 73 | Moving while crushed |
| `Teleporte` | 74 | Teleporting | `Clear7` | 80 | Clearing animation, variant 7 |
| `Clear2` | 75 | Clearing animation, variant 2 | `Clear8` | 81 | Clearing animation, variant 8 |
| `Clear3` | 76 | Clearing animation, variant 3 | `Switch` | 82 | Activating a switch |
| `Clear4` | 77 | Clearing animation, variant 4 | `Mockeryp` | 83 | Enemy mocking, alternate pose |
| `Clear5` | 78 | Clearing animation, variant 5 | `Non` | 84 | Blupi refusing / shaking head |
| `Clear6` | 79 | Clearing animation, variant 6 | `SlowdownSkate` | 85 | Skateboard braking |
| | | | `TakeDynamite` | 86 | Picking up dynamite |
| | | | `PutDynamite` | 87 | Placing dynamite |

## 2. `Direction` — horizontal facing (3 values)

*From `def/Direction.hpp:101`.* Underlying `ubytecs`.

| Value | Raw | Meaning |
|---|---:|---|
| `None` | 0 | No direction / uninitialised |
| `Left` | 1 | Facing left (`DIR_LEFT`) |
| `Right` | 2 | Facing right (`DIR_RIGHT`) |

## 3. `GameSpeed` — simulation speed multiplier (5 values)

*From `def/GameSpeed.hpp:165`.* Underlying `ubytecs`. Values are powers of two (except `Slow`/
`Normal`) so speed changes are uniform tick multipliers; ordering operators (`<`, `<=`, `>`, `>=`)
are defined. MODERN-only; F5–F8 map directly to the four non-`Slow` presets.

| Value | Raw | Meaning |
|---|---:|---|
| `Slow` | 0 | Reduced speed (0 extra ticks/frame) |
| `Normal` | 1 | Standard speed, default (F5) |
| `Fast` | 2 | Double speed (F6) |
| `Faster` | 4 | Quadruple speed (F7) |
| `Fastest` | 8 | Maximum speed (F8) |

## 4. `KeyPressFlags` — active virtual buttons (bitmask, 4 values)

*From `def/KeyPressFlags.hpp:305`.* Underlying `ushortcs`. Combined with bitwise OR by `InputPad`;
consumed by `Decor`'s state machine.

| Value | Raw | Meaning |
|---|---:|---|
| `None` | 0 | No buttons pressed |
| `Jump` | 1 | Jump button active (`KEY_JUMP`) |
| `Fire` | 2 | Fire/action button active (`KEY_FIRE`) |
| `Down` | 4 | Down button active (`KEY_DOWN`) |

## 5. `SecretPower` — active hidden power-up (5 values)

*From `def/SecretPower.hpp:471`.* Underlying `ushortcs`. Only one can be active at a time;
corresponds to the original `SEC_*` constants.

| Value | Raw | Meaning |
|---|---:|---|
| `None` | 0 | No special power active |
| `Shield` | 1 | Temporary invincibility (`SEC_SHIELD`) |
| `Power` | 2 | Enhanced strength/power bonus (`SEC_POWER`) |
| `Cloud` | 3 | Cloud/floating bonus (`SEC_CLOUD`) |
| `Hide` | 4 | Invisibility bonus (`SEC_HIDE`) |

## 6. `DecorAction` — camera-shake animation (4 values)

*From `decor/DecorAction.hpp:43`.* Underlying `ubytecs`. Drives `Decor::DecorNextAction()` via
`Tables::table_decor_action`. Note the gap: values 3–4 are unassigned; the header explicitly
documents this ("the sequence jumps directly to 5 for `ElectricShake`").

| Value | Raw | Meaning |
|---|---:|---|
| `None` | 0 | No camera shake; viewport stationary |
| `SmallShake` | 1 | Minor impact (crate landing, small explosion, bonus pickup) |
| `BigShake` | 2 | Major impact (fan-blade contact, large explosion) |
| `ElectricShake` | 5 | Electric-field contact (`ObjectType90` spark); rapid jitter |

## 7. `DoorKeyFlags` — key inventory bitmask (5 values incl. `All`)

*From `decor/DoorKeyFlags.hpp:58`.* Underlying `ubytecs`. Overloads `operator|`/`operator&` for
combining/testing; stored in `Decor::m_blupiCle`, serialised via `Worlds::WriteIntField`/
`GetIntField`.

| Value | Raw | Meaning |
|---|---:|---|
| `None` | 0 | No keys held |
| `Key1` | 1 (`1<<0`) | First key; from `ObjectType49` pickup |
| `Key2` | 2 (`1<<1`) | Second key; from `ObjectType50` pickup |
| `Key3` | 4 (`1<<2`) | Third key; from `ObjectType51` pickup |
| `All` | 7 (`Key1\|Key2\|Key3`) | Convenience mask granting/testing all three keys at once |

## 8. `ObjectType` — moving-object species IDs (139 named values)

*From `decor/ObjectType.hpp:61`.* Underlying `ubytecs`. Numeric IDs are inherited verbatim from
the original game and are stored in level files — they must never be renumbered. Roughly half the
declared range (IDs 42–203, with many gaps) is documented in the header itself as
**"purpose unknown"** — declared only so the enum is contiguous and level-file round-trips are
lossless, per the header's own note. Grouped below by the header's own section comments; "purpose
unknown" ranges are condensed to save space (each such value's Doxygen comment reads verbatim
*"Purpose unknown; declared for completeness."*).

| Group | IDs | Meaning |
|---|---|---|
| Sentinel | 0 | Null / inactive `MoveObject` slot |
| Platform lifts | 1, 47, 48 | Standard lift; lift with +2px/frame right-carry bonus; lift with −2px/frame left-carry bonus |
| Patrol hazard enemies | 2, 3, 96, 97 | Standard patroller; patroller variant; follow-enemy variants 1 and 2 |
| Bulldozer | 4 | Bulldozer enemy, kills on contact |
| Treasure/life collectibles | 5, 6, 7, 21, 39 | Treasure; extra-life egg; level-exit goal; secret-exit goal; sparkle pickup effect |
| Key collectibles | 49, 50, 51 | Key 1 / Key 2 / Key 3 (see `DoorKeyFlags`) |
| Power-up / vehicle pickups | 13, 19, 24–26, 28–31, 40, 46, 55 | Helicopter, jeep, skate, shield, suction-cup, tank, bullet pack, drink, charge/cloud, mirror-invert, balloon, dynamite |
| Explosion/visual effects | 8–12, 36–38, 41, 42, 53, 90–93, 98–100 | Primary/secondary/tertiary explosions, fan shockwave, pollution puff, clear effect, electric arc, invert-start/stop bursts, tentacle hazard, spark, flash, energy-arc, water splashes |
| Water/goo effects | 14, 15, 34, 35 | Water plouf splash, rising bubble, goo/glue particle, small splash |
| Projectile | 23 | Fired projectile from `blupih`/`blupit` enemies |
| Patrol enemies (walkers) | 16, 17, 18, 20, 32, 33, 44, 54 | Spider, fish, unidentified variant, bird, "blupih"/"blupit" hostile clones (fire projectiles), wasp, large creature |
| Moving decoration | 22, 27, 52, 56, 57, 58 | Door-open animation, magic-track sparkle, bridge-construction animation, dynamite fuse, shield trail/disappear effects |
| Blupi avatar skins | 200–203 | Default skin + 3 costume variants (also usable as costume-select pickups) |
| **Purpose unknown** | 43, 45, 59–89, 94–95, 101–199 | ~73 IDs declared for enum contiguity only; semantics unverified — see `ENUMS.md`'s own note that group-1 tile icons (a *different*, unrelated numeric space) have the same "documented but unconfirmed" character |

## 9. `ContinueMissionType` — continue-from-checkpoint lifecycle (3 values)

*From `def/ContinueMission.hpp:749`.* Underlying `ushortcs`.

| Value | Raw | Meaning |
|---|---:|---|
| `None` | 0 | No continue-mission request pending |
| `Pending` | 1 | Request issued but not yet acted on |
| `Active` | 2 | Continue sequence currently executing |

## 10. `PixmapChannel` — sprite-atlas slot identifier (16 values, 2 gaps)

*From `def/PixmapChannel.hpp:373`.* Underlying `ubytecs`. Mirrors the legacy `CH*` integer
constants in `Def` for backward compatibility; indices 7 and 8 are intentionally unused gaps.

| Value | Raw | Atlas file | Value | Raw | Atlas file |
|---|---:|---|---|---:|---|
| `PixmapChannel0` | 0 | (reserved, unused) | `Explosion` | 9 | `explo.png` |
| `Object` | 1 | `object-m.png` | `Element` | 10 | `element.png` |
| `Blupi` | 2 | `blupi.png` | `Blupi1_11` | 11 | `blupi1.png` (variant 1) |
| `Background` | 3 | `Content/backgrounds/*.png` | `Blupi1_12` | 12 | `blupi1.png` (variant 2) |
| `Button` | 4 | `button.png` | `Blupi1_13` | 13 | `blupi1.png` (variant 3) |
| `Jauge` | 5 | `jauge.png` | `Pad` | 14 | (touch-pad overlay) |
| `Text` | 6 | `text.png` | `SpeedyBlupiBackground` | 15 | title/background art |
| *(gap)* | 7–8 | unused | `BlupiYoupieBackground` | 16 | Blupi Youpie background |
| | | | `GearBackground` | 17 | settings/gear background |

## 11. `SoundChannel` — sound-effect asset slot (93 values)

*From `def/SoundChannel.hpp:542`.* Underlying `ubytecs`. A strict 1:1 sequence
`SoundChannel0 = 0` through `SoundChannel92 = 92`, no gaps, no named semantic groups — each
channel maps directly to `sounds/soundNNN.wav` (zero-padded 3-digit index) loaded by
`Sound::LoadContent()`. Channel 0 is reserved and never played. The only channel with unique
runtime behaviour is `SoundChannel10`: unlike every other channel, a second `PlayImage()` call
while it is still playing is **not** dropped — it is the sole channel allowed to stack multiple
simultaneous instances (used by `Decor::CheatAction`'s `CleanAll` cheat to play an explosion
sound per destroyed enemy in the same frame). Because the numbering must exactly match the
original game's sound table, renumbering is explicitly forbidden by the header's own note.

## 12. `Def::Phase` — top-level game screen/mode (13 values)

*From `Def.hpp:51`.* Nested inside the `Def` class; no explicit underlying type (`int` by
default) and no explicit numeric values — values are implicit, sequential from 0. The game is
always in exactly one `Phase`; all transitions funnel through `Game1::SetPhase()`.

| Value | Meaning |
|---|---|
| `None` | No phase active (initial/uninitialised) |
| `First` | Very first frame after startup |
| `Wait` | Waiting for an asynchronous operation |
| `Init` | Main-menu / gamer-select screen |
| `Play` | Active gameplay |
| `Pause` | Game paused (overlay shown) |
| `Lost` | Player lost the current level |
| `Win` | Player completed the current level |
| `Trial` | Trial/demo mode purchase prompt |
| `MainSetup` | Settings screen from the main menu |
| `PlaySetup` | Settings screen during gameplay |
| `Resume` | Resume-from-checkpoint confirmation |
| `Ranking` | High-score/ranking screen |

## 13. `Def::ButtonGlyph` — on-screen button identity (45 values)

*From `Def.hpp:77`.* Also nested in `Def`, implicit sequential `int` values, no explicit numbers.
Each value names one interactive button that can appear during a given `Phase`.

| Category | Values |
|---|---|
| Sentinel | `None` |
| Init screen | `InitGamerA`, `InitGamerB`, `InitGamerC`, `InitSetup`, `InitPlay`, `InitBuy`, `InitRanking` |
| Win/Lost/Trial | `WinLostReturn`, `TrialBuy`, `TrialCancel` |
| Setup screen | `SetupSounds`, `SetupJump`, `SetupZoom`, `SetupAccel`, `SetupReset`, `SetupReturn` |
| Pause screen | `PauseMenu`, `PauseBack`, `PauseSetup`, `PauseRestart`, `PauseContinue` |
| Active play | `PlayPause`, `PlayJump`, `PlayAction`, `PlayDown` |
| Resume/Ranking | `ResumeMenu`, `ResumeContinue`, `RankingContinue` |
| Cheat-menu unlock gesture | `Cheat11`, `Cheat12`, `Cheat21`, `Cheat22`, `Cheat31`, `Cheat32` (see [Appendix E](appendix-e-cheat-code-reference.md)) |
| Cheat action buttons | `Cheat1`–`Cheat9` (see [Appendix E](appendix-e-cheat-code-reference.md)) |

## 14. `JaugeMode` — HUD gauge fill colour (4 values)

*From `Jauge.hpp:22`.* Underlying `intcs`. Each value is a row index into the `Jauge` sprite sheet
(`PixmapChannel::Jauge`).

| Value | Raw | Meaning |
|---|---:|---|
| `Empty` | 0 | No fill drawn |
| `Red` | 1 | Danger/energy indicators |
| `Blue` | 2 | Water-level indicators |
| `Yellow` | 3 | Charge/key indicators |

## 15. `Tables::CheatCodes` — cheat identifiers (22 base + up to 5 build-gated)

*From `Tables.hpp:79`.* Implicit sequential `int`, nested in `Tables`. See
**[Appendix E: Cheat Code Reference](appendix-e-cheat-code-reference.md)** for the full
trigger-to-effect mapping, cross-verified against `Decor::CheatAction()`.

| Value | Availability | Value | Availability |
|---|---|---|---|
| `BuildOfficialMissions` | All builds | `PowerCharge` | All builds |
| `OpenDoors` | All builds | `Drink` | All builds |
| `CleanAll` | All builds | `Overcraft` | All builds |
| `SuperBlupi` | All builds | `Dynamite` | All builds |
| `LayEgg` | All builds | `WeelKeys` | All builds |
| `KillEgg` | All builds | `Quick` | `#ifndef LEGACY` |
| `Skate` | All builds | `Ghost` | `#ifdef MODERN` |
| `Copter` | All builds | `Debug` | `#ifdef MODERN` |
| `Jeep` | All builds | `Zoom` | `#ifdef MODERN` |
| `AllTreasure` | All builds | `Cheats` | `#ifdef MODERN` |
| `EndGoal` | All builds | | |
| `ShowSecret` | All builds | | |
| `RoundShield` | All builds | | |
| `Lollipop` | All builds | | |
| `Bombs` | All builds | | |
| `BirdLime` | All builds | | |
| `Tank` | All builds | | |

## 16. `ResolutionScale` — viewport resolution multiplier (3 values)

*From `ConfigDef.hpp:22`.* Implicit `int` underlying type, explicit values. Only
`ScaleResolution1` is active in production; the others are reserved for future high-DPI support.

| Value | Raw | Meaning |
|---|---:|---|
| `ScaleResolution1` | 1 | Native 640×480 (default, 1:1) |
| `ScaleResolution2` | 2 | 2x upscale — 1280×960 |
| `ScaleResolution4` | 4 | 4x upscale — 2560×1920 |

## 17. `Fps` — target update rate (6 values)

*From `ConfigDef.hpp:48`.* Implicit `int` underlying type, explicit values. `Fps20` is the
original stable Windows Phone timing; all higher rates are experimental and require
`Config::ScaleTime()`/`ScaleDiv()`/`SPEED_SCALE` to preserve original real-time behaviour.

| Value | Raw | Meaning |
|---|---:|---|
| `Fps20` | 20 | Original, stable (default) |
| `Fps30` | 30 | Experimental |
| `Fps60` | 60 | Experimental |
| `Fps90` | 90 | Experimental |
| `Fps120` | 120 | Experimental |
| `Fps144` | 144 | Experimental |

## 18. `ZoomCheat` — MODERN-only debug zoom levels (4 values)

*From `def/Zoom.hpp:710`.* The entire file, including this enum, is wrapped in
`#ifdef MODERN … #endif` and does not exist in LEGACY builds. No explicit underlying type or
values (implicit sequential `int` from 0).

| Value | Meaning |
|---|---|
| `Zoom100` | 100% render scale (normal view) |
| `Zoom50` | 50% render scale (~2x wider view) |
| `Zoom25` | 25% render scale (~4x wider view) |
| `Zoom12` | 12.5% render scale (~8x wider view) |

## 19. `Decor::IconType` — reserved, empty placeholder (0 values)

*From `Decor.hpp:93`, private nested type.* Genuinely empty: `enum class IconType { };`. The
header's own Doxygen comment calls it *"a placeholder ported from the original C# codebase... not
yet populated with values and has no effect on current gameplay"* and explicitly instructs future
maintainers not to remove it. It is listed here for completeness because it is a real, compiling
`enum class` in the codebase — just one with no enumerators and (currently) no use.

---

## Proposed, not implemented (see `ENUMS.md`)

**`ENUMS.md` is a refactoring proposal, not existing code.** None of the enums below are
`enum class` types in the actual source — the code still uses raw integer literals (`68`, `91`,
`107`–`109`, …) directly in `Is*()` predicate methods and comparisons throughout `Decor.cpp`.
`ENUMS.md` itself opens with the sentence *"No code has been changed. This is an analysis-only
document."* Any chapter or table entry that cites one of these names must make that status
explicit, per `CLAUDE.md`.

| Proposed name | Priority | Would replace | Scope |
|---|---|---|---|
| `TileIconType` (or `DecorIcon`) | High | ~50+ magic tile-icon literals across `Decor.cpp`'s `Is*()` predicates (`IsLave`, `IsPiege`, `IsScie`, `IsDoor`, `IsTeleporte`, `IsBridge`, `IsVentillo`, `IsRessort`, `IsEcraseur`, `IsBlitz`, `IsSurfWater`, `IsDeepWater`, `IsOutWater`, `IsNormalJump`, `IsTemp`) | Lava (68), shallow/deep water (91/92), jump springs (107–109), fans (110/114/118/122), rails (126–137), doors (158–165), teleporters (166–173), door/portal variants (174–184), mine (203), spring (211), hidden tile (214), bridges (246–249), collectibles (251–289), lightning (304–305, 330–336), crusher (317), temperature (324), hazard zones (341–363), spike trap (373), saw blade (378), bridge state (384–385), drip hazard (404–407), door variants (410–420), treasure (421+) |
| `DoorState` | Medium | Door open/closed literals in `MemorizeDoors`, `InitializeDoors`, `OpenDoor`, `OpenDoorsWin`, `AdaptDoors` | `Closed = 0`, `Open = 1` |
| `TerrainType` | Medium | Tile-range comparisons in `SoundEnviron` (~lines 1436–1498) selecting footstep/ambient sound | `Grass`, `Stone`, `Lava`, `Water`, `Bridge`, `Spring`, `SpecialHazard` |
| `DripHazardFrame` | Low | Frame-range literals in `Build` (~lines 1044–1052) | `ActiveStart = 404`, `ActiveEnd = 407` |
| `BlitzCycle` | Low | Cycle-length constants in `BlitzActif` (~lines 623–631) | `Length = 100`, `ActiveThreshold = 50` |
| `ShieldAnimation` | Low | Timing/divisor constants in `Build` (~lines 785–831) | `HighTimeThreshold = 25`, `CycleDivisor = 4`, `FrameToggleThreshold = 2` |
| `HazardRenderOffset` | Low | Y-offset literals in `Build` (~lines 727–733) | `Mine = -13`, `Other = -2` |
| `PowerEffectIcon` | Low | Icon-offset literals in `Build` (~lines 811–815) | `BaseOffset = 48`, `CycleLength = 6` |

`ENUMS.md` recommends that any of these, if implemented, would live under
`include/WindowsPhoneSpeedyBlupi/decor/` alongside the real `DecorAction.hpp`/`DoorKeyFlags.hpp`/
`ObjectType.hpp`, using `enum class` with an explicit `intcs` underlying type — the same
convention the 19 real enums above already follow. See
[Chapter 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) for the tile/icon catalog
built from the real `Is*()` predicates that this proposal targets.

## See also

- [Appendix A: Class and File Catalog](appendix-a-class-and-file-catalog.md) — the headers each
  enum above is declared in.
- [Appendix E: Cheat Code Reference](appendix-e-cheat-code-reference.md) — the full trigger-to-effect
  mapping for `Tables::CheatCodes` (§15 above).
- [Chapter 26: Tile and Icon Catalog](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) —
  the real `Is*()` predicates that `ENUMS.md`'s proposed enums would replace.
- [Chapter 18: Blupi Actions and Animation](../part04-decor-simulation/ch18-blupi-actions-and-animation.md)
  and [Chapter 19: Moving Objects and Decor Actions](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md)
  — narrative coverage of `BlupiAction` and `ObjectType`, this catalog's two largest enums.
