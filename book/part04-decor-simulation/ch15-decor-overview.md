# Chapter 15: Decor — Overview

`Decor` is the class that runs Speedy Blupi: it owns the tile map, Blupi's own state machine,
every moving object in a level, and the rules connecting all three. This chapter is a broad first
pass over that class — its size, how its data is grouped, and the handful of lifecycle methods
that drive one frame of simulation from start to finish — before Chapters 16 through 21 each take
one piece of it in depth.

## The largest class in the game

If you were handed the `mobile-eggbert` source tree and told to find the game in it, you would
end up at `Decor`. Everything else in the codebase — `Game1`'s XNA-style state machine (Part
III), `Pixmap`'s sprite rendering (Part V), `InputPad`'s touch/keyboard unification (Part VII),
`Worlds`' level-file parser (Part VIII) — exists to feed data into `Decor` or to display what
`Decor` has computed. `Decor` itself is where the game is actually simulated: the tile map,
Blupi's every last twitch, every enemy and crate and switch, all of gravity and collision, all of
win and loss.

The numbers make the point better than words. The declaration, `include/WindowsPhoneSpeedyBlupi/Decor.hpp`,
is 2,064 lines — already the second-largest header in the project. The implementation,
`src/WindowsPhoneSpeedyBlupi/Decor.cpp`, is **11,720 lines**, out of a total codebase of 31,394
lines of C++. One file, in other words, is over a third of the entire project. No other class
comes remotely close (`Tables.cpp`, the second-largest translation unit, is 2,208 lines — roughly
a fifth the size). This chapter is the reader's first real orientation to that file: what `Decor`
is responsible for, how its data is organized, and how its lifecycle methods fit together, before
the next three chapters descend into the tile map (Chapter 16) and Blupi's state machine
(Chapters 17–18) in detail.

## What the header says about itself

`Decor.hpp` opens with an unusually candid file-level Doxygen comment, and it is worth reading in
full because every later chapter in Part IV takes its vocabulary from it:

*From `Decor.hpp:1-23`:*
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
 *
 *   Coordinate systems used throughout this file:
 *   - Tile coordinates: integer (x, y) in [0, MAXCELX) x [0, MAXCELY).
 *   - Game-space pixel coordinates: tile x 64 (DIMOBJX / DIMOBJY).
 *   - Screen-space: game-space plus scroll offset; handled by IPixmap, not Decor.
 *
 * @author  Original XNA/C# game by Epsitec SA; C++ port by the mobile-eggbert team
 * @date    2013 (original); 2024 (C++ port)
 * @see     IPixmap, ISound, GameData, Tables
 */
```

Three things are worth pulling out immediately. First, `Decor` is explicitly a **port**, not a
redesign — "all movement constants, collision rules, animation table indices, and state-machine
transitions are preserved from the original source." Every number the reader will see in this
Part (a jump velocity of `-19`, a 330-frame idle-blink cycle, a `MAXQUART` of 441) is not this C++
codebase's invention; it is 2013-vintage C# game-design data, carried through decompilation and
two ports unchanged. Chapters in this Part therefore treat magic numbers as *data to document*,
not *code smells to refactor* — a theme this book returns to whenever `ENUMS.md`'s proposed
enum-ification of these numbers comes up (`ENUMS.md` is a proposal document, not implemented code;
see Chapter 26).

Second, the file states its three coordinate systems up front, and getting them straight now saves
confusion in every later chapter:

- **Tile coordinates** — integer `(x, y)` in `[0, 100) x [0, 100)`. This indexes directly into
  `m_decor[x][y]` and `m_bigDecor[x][y]`.
- **Game-space pixel coordinates** — a tile coordinate times 64 (one tile is 64×64 pixels).
  Blupi's position (`m_blupiPos`), every `MoveObject`'s position, and every collision rectangle in
  the file are expressed in this space. It is a single flat coordinate system across the entire
  100×100-tile (6400×6400-pixel) level — there is no per-screen coordinate reset.
  `Decor::IsWorld()`, for instance, bounds-checks against `6400` directly (`Decor.cpp:7083`), and
  `GetPosDecor()` clamps the scroll position against `6400 - drawWidth` (`Decor.cpp:6633`).
- **Screen-space** — game-space pixels minus the current scroll offset (`m_posDecor`). This is
  the coordinate system that actually reaches `IPixmap`'s drawing calls; `Decor` computes it,
  `IPixmap` never sees game-space directly.

Third, the class comment gives the cleanest one-paragraph summary of the whole simulation that
exists anywhere in the codebase, and it is the map this chapter (and the rest of Part IV) will
walk:

*From `Decor.hpp:51-65`:*
```cpp
 *   Responsibilities:
 *   - Owning and simulating the 100x100 tile map (m_decor, m_bigDecor).
 *   - Owning and advancing the Blupi player state machine (position, action, direction,
 *     vehicle modes, bonuses, physics).
 *   - Owning and advancing all active moving objects (m_moveObject[]).
 *   - Detecting collision between Blupi and tiles, moving objects, and hazards.
 *   - Handling doors, switches, teleporters, lifts (ascenseurs), and triggers.
 *   - Managing the viewport scroll position relative to Blupi's position.
 *   - Triggering sound effects at gameplay events via ISound.
 *   - Driving animation through per-object phase counters indexed into Tables.
 *   - Reading and writing level save files via Worlds helpers.
```

And, just as tellingly, what it explicitly does *not* do: "Does not own rendering resources.
Drawing is done by forwarding to `IPixmap`. Does not own input; receives key state via
`KeyChange()` each frame." `Decor` sits in the middle of the architecture: `Game1` drives it once
per frame, `InputPad` feeds it key state, and it in turn drives `IPixmap` (Part V) and `ISound`
(Part VI) — but it never reaches back into either of those subsystems' internals. This is the one
architectural boundary `Decor` respects strictly, even though internally it is anything but tidy.

## The shape of the data

`Decor` is a single, non-polymorphic class with no public data members beyond a couple of
`DDATA`-declared properties — everything else is a private field, and there are a *lot* of private
fields. Reading through the header's member list (`Decor.hpp:204-601`) is itself instructive,
because the fields cluster into a small number of clearly-named groups:

- **Injected dependencies** — `m_sound` (`ISound*`), `m_pixmap` (`IPixmap*`), `m_gameData`
  (`GameData*`). None of these are owned by `Decor`; they are handed in once via `Create()` and
  never reassigned. This is the entirety of `Decor`'s coupling to the rest of the engine.
- **The tile map** — `m_decor[100][100]` and `m_bigDecor[100][100]`, both arrays of the nested
  `Cellule` struct (one `intcs icon` field each), plus the bit-packed occupancy grids
  `m_balleTraj` (projectile trajectories) and `m_moveTraj` (moving-object trajectories). Chapter
  16 is devoted to this group.
- **The moving-object pool** — `m_moveObject[MAXMOVEOBJECT]` (200 slots of the nested `MoveObject`
  struct), plus bookkeeping arrays for crate grouping (`m_rankCaisse`, `m_linkCaisse`) and a
  `byeByeObjects` vector for destruction particles. Chapter 19 covers this group in depth.
- **Blupi's state** — by a wide margin the largest single cluster, roughly seventy separate
  fields with the `m_blupi` prefix: position (`m_blupiPos`, `m_blupiLastPos`, `m_blupiValidPos`),
  the state-machine variables proper (`m_blupiAction`, `m_blupiDir`, `m_blupiPhase`), velocity and
  sub-pixel accumulators, a dozen-plus boolean vehicle/mode flags (`m_blupiHelico`, `m_blupiJeep`,
  `m_blupiTank`, `m_blupiSkate`, `m_blupiNage`, `m_blupiSurf`, `m_blupiSuspend`, `m_blupiBalloon`,
  `m_blupiEcrase`, …), secret-power flags and their countdown timers (`m_blupiShield`,
  `m_blupiPower`, `m_blupiCloud`, `m_blupiHide` and their matching `m_blupiTimeShield` /
  `m_blupiTimeFire` timers), inventory (`m_blupiCle` — keys, `m_blupiDynamite`), and a 10-slot
  FIFO of recent positions (`m_blupiFifoPos`) used purely for rope/suspension animation. Chapters
  17 and 18 are built entirely out of this cluster.
- **Level/session bookkeeping** — door state (`m_doors[200]`), treasure counters (`m_nbTresor`,
  `m_totalTresor`), the win/loss flag (`m_term`), cheat flags (`m_bCheatDoors`, `m_bSuperBlupi`,
  `m_bDrawSecret`), the current mission index, and the region/music selectors.
- **Camera and presentation** — the scroll target and step (`m_scrollPoint`, `m_scrollAdd`), the
  "hot spot" zoom-and-pan state (`m_hotSpotCurrentZoom/X/Y`, `m_hotSpotFinalZoom/X/Y`, and their
  per-frame step sizes) that drives the auto-zoom-in-while-walking camera effect, and the "Voyage"
  fly-to-HUD animation state used for collectible pickups.

Two nested types anchor the two biggest clusters. `Cellule` is almost aggressively minimal:

*From `Decor.hpp:98-116`:*
```cpp
struct Cellule
{
    intcs icon; ///< Tile icon index used for rendering and collision classification.
};
```

A single `intcs` field carrying two jobs at once — Chapter 16 is largely the story of what that
double duty means and, in one place, corrects an assumption this book's own planning notes made
about it before the source was actually read carefully. `MoveObject` is bigger (thirteen fields:
type, two speeds, two dwell timers, three positions, a step counter, a wait timer, an animation
phase, and a `(channel, icon)` sprite reference — `Decor.hpp:139-154`) and is the subject of
Chapter 19.

A recurring convention worth internalizing now: `intcs`, `shortcs`, `ubytecs` and friends
(defined in `SharpRuntime/SharpRuntimeHelper.hpp`, outside this book's scope per its CNA-marginal
policy) are the C++ port's fixed-width integer aliases standing in for the original C#'s `int`,
`short`, and `byte`. When a comment says a field is "not a sprite index" or "not gameplay state,"
as several of the Doxygen comments quoted above do, that distinction is doing real work — this
codebase reuses plain integers for several unrelated purposes (tile classification, phase
counters, table offsets) and the comments exist specifically to keep those uses from being
confused with each other.

## `Create()`: wiring, not initialization

The constructor `Decor::Decor()` (`Decor.cpp:122`) is a long member-initializer list that zeroes
essentially every Blupi flag and level-state field to a safe default. It runs once, when the
`Decor` instance itself is constructed as part of `Game1`. But the method that actually prepares
`Decor` for use is `Create()`:

*From `Decor.cpp:223-243`:*
```cpp
void Decor::Create(ISound* sound, IPixmap* pixmap, GameData* gameData)
{
    m_sound = sound;
    m_pixmap = pixmap;
    m_gameData = gameData;
    m_keyPress = 0;
    m_lastKeyPress = 0;
    m_blupiMotorSound = SoundChannel::SoundChannel0;
    InitDecor();
    TinyPoint pos{};
    pos.X = 90;
    pos.Y = 450;
    m_jauges[0] = Jauge();
    m_jauges[0].Create(m_pixmap, m_sound, pos, JaugeMode::Red, false);
    m_jauges[0].SetHide(true);
    pos.X = 90;
    pos.Y = 428;
    m_jauges[1] = Jauge();
    m_jauges[1].Create(m_pixmap, m_sound, pos, JaugeMode::Yellow, false);
    m_jauges[1].SetHide(true);
}
```

`Create()` is the one and only place the three injected pointers are stored, which is why the
header's precondition is unconditional: "calling any simulation method before `Create()` results
in undefined behaviour" (`Decor.hpp:645`). It then calls `InitDecor()` (see below) and constructs
the two HUD gauges (`m_jauges[0]`, the red life/energy bar; `m_jauges[1]`, the yellow charge/
special bar — see Chapter 36 for `Jauge` itself), both created hidden. `Create()` does *not* load
a level and does *not* start simulation; it purely wires `Decor` up to its three collaborators and
gives it a clean, level-independent baseline.

## `LoadImages()`: one call, one important consequence

`LoadImages()` is three lines long, but those three lines are the seed of one of this Part's more
important findings (fully unpacked in Chapter 16):

*From `Decor.cpp:245-252`:*
```cpp
bool Decor::LoadImages()
{
    std::ostringstream oss;
    oss << "decor" << std::setw(3) << std::setfill('0') << m_region;
    string name = oss.str();
    m_pixmap->BackgroundCache(name);
    return true;
}
```

Given the current region index (`m_region`, set from the level file — see `Read()` below), this
formats a filename like `decor002` and hands it to `IPixmap::BackgroundCache()`, which loads
`Content/backgrounds/decor002.png` and caches it as the region's `PixmapChannel::Background`
atlas. This is a *whole pre-rendered panorama image per region*, not a tile atlas — there is no
`icon` parameter here at all, unlike every other `Pixmap` load in the codebase. `Build()` (below)
later blits this cached image as a repeating panel grid behind everything else. Chapter 16 traces
exactly how this background layer relates — and does not relate — to the numeric tile icons
stored in `m_decor[][]`.

## `InitDecor()`: the pre-level baseline

`InitDecor()` (`Decor.cpp:263`) is private and is called from two places: once from `Create()`
(above) and once at the top of both `Read()` and `CurrentRead()`, the level-loading and
quick-save-loading paths (Chapter 44 covers `Worlds`, the file format itself, in depth). Its job
is to reset the entire simulation to a known-empty baseline before new level data is poured in:

*From `Decor.cpp:263-280` (abridged):*
```cpp
void Decor::InitDecor()
{
    m_posDecor.X = 0;
    m_posDecor.Y = 0;
    m_dimDecor.X = 100;
    m_dimDecor.Y = 100;
    m_music = 1;
    m_region = 2;
    m_decorAction = DecorAction::None;
    for (int i = 0; i < 100; i++)
    {
        for (int j = 0; j < 100; j++)
        {
            m_decor[i][j].icon = -1;
            m_bigDecor[i][j].icon = -1;
        }
    }
    m_decor[1][4].icon = 40;
    m_decor[2][4].icon = 38;
    // ... m_decor[3..6][4].icon = 38; m_decor[7][4].icon = 39;
```

Every tile in both `m_decor` and `m_bigDecor` is set to `-1` ("empty" — every icon-testing
predicate in the file treats `-1` as "no tile here"), and then a small seven-tile platform is
hand-stamped in at row 4, columns 1–7, along with two demo `MoveObject` entries (an `ObjectType5`
treasure and an `ObjectType7` object, both placed with `PixmapChannel::Element` at fixed
coordinates — `Decor.cpp:293-320`). The accompanying comment is explicit about why this baseline
exists at all: "This baseline is overwritten by `Read()` when a real level loads; it only matters
when no level file is present." It is effectively a built-in one-screen test level, useful for
booting the game (or a debug build) with no `worlds/*.txt` file loaded at all. `InitDecor()` then
resets every one of the ~40 Blupi flags to its off/default state, clears the bullet and
move-trajectory occupancy arrays (`FlushBalleTraj()`, `FlushMoveTraj()`), sets Blupi's starting
action to `BlupiAction::Stop`, and clears the `byeByeObjects` destruction-particle pool.

## `PlayPrepare()` and `BuildPrepare()`: two ways to start

Once a level's data is in `m_decor`/`m_bigDecor`/`m_moveObject[]` (via `Read()`), one of two
methods actually starts the simulation running, and which one is used depends on whether the
level is being *played* or *built* (edited):

`PlayPrepare(bool bTest)` (`Decor.cpp:381`) is the normal gameplay entry point. It places Blupi at
his level-defined start position and direction, resets essentially every one of his flags exactly
as `InitDecor()` does (this duplication across `InitDecor()` and `PlayPrepare()` is a real trait
of the ported code, not an editorial choice this book is glossing over), and then does two things
`InitDecor()` doesn't:

*From `Decor.cpp:430-450` (abridged):*
```cpp
for (int i = 0; i < MAXMOVEOBJECT; i++)
{
    if (m_moveObject[i].type == ObjectType::ObjectType5)
    {
        m_totalTresor++;
    }
    m_moveObject[i].posCurrent = m_moveObject[i].posStart;
    // ...
    if (m_moveObject[i].type == ObjectType::ObjectType5 || ... /* several decorative types */)
    {
        m_moveObject[i].phase = m_random.get()->Next(23);
    }
    if (m_moveObject[i].type == ObjectType::ObjectType23)
    {
        m_moveObject[i].type = ObjectType::ObjectType0;
    }
}
```

It counts `ObjectType5` (treasure) instances to compute the win-condition target
`m_totalTresor`, gives a handful of decorative object types a randomized starting animation
phase (0–22) purely so, say, a screen full of identical torches or sparkles doesn't visibly pulse
in lock-step, and demotes `ObjectType23` (an editor-only placement marker) down to the inert
`ObjectType0` so it never appears or acts during real play. `PlayPrepare()` finishes by calling
`MoveStep()` once and then immediately snapping the scroll target onto Blupi
(`m_scrollPoint.X = m_blupiPos.X + 30 + m_scrollAdd.X`, and the Y equivalent), so that the very
first rendered frame is already centered on the player instead of visibly panning in from
wherever `m_scrollPoint` happened to default to.

`bTest` is the level-editor's "test play" flag: when true, `m_nbVies` (lives) is force-set to 3
regardless of what the save file said, a small convenience for iterating on a level without
constantly re-granting yourself lives.

`BuildPrepare()` (`Decor.cpp:475`), by contrast, is the editor's own preparation path, used when
the level-build tool needs to reset object positions and phases without granting Blupi a starting
position or counting treasures at all — it is a much smaller subset of `PlayPrepare()`'s work,
appropriate to a mode where "playing" the level correctly is not yet the goal.

## `IsTerminated()`: the win/loss contract in one line

*From `Decor.hpp:691-701` and `Decor.cpp:493-496`:*
```cpp
int Decor::IsTerminated()
{
    return m_term;
}
```

The entire win/loss protocol boils down to a single `intcs` field, `m_term`, whose sign and
magnitude the caller (`Game1`, Chapter 12) interprets: `0` means the level is still running, a
positive value means the level was won (and, as Chapter 24 will show, the *specific* positive
value often encodes which mission or world unlocks next — `m_term = m_mission / 10 * 10 + icon`,
for instance, appears deep inside `BlupiStep()`'s win-condition handling), and a negative value
means the level was lost. `Decor` itself never reads `m_term` to decide anything; it only ever
writes it — the interpretation and the screen transition it triggers live entirely in `Game1`,
consistent with `Decor`'s stated non-ownership of "what happens on screen when this ends."

## `MoveStep()`: the fixed order of the frame

The single doc comment at the top of `Decor.cpp` lays out `MoveStep()`'s contract about as
precisely as any comment in the file, and it is worth internalizing before Chapters 17–19 dig into
the individual sub-systems it calls:

*From `Decor.cpp:507-520`:*
```cpp
void Decor::MoveStep()
{
    try
    {
        MoveObjectStep();
        ByeByeStep();
        BlupiStep();
        MoveHotSpot();
        AdaptMotorVehicleSound();
    }
    catch (std::exception e)
    {
    }
}
```

The order is fixed and load-bearing: moving objects (crates, enemies, projectiles — Chapters 19–21)
advance *before* Blupi, so that when `BlupiStep()` runs it sees this frame's already-updated
object positions rather than last frame's — this is why, for instance, a lift `Decor` is riding
can move Blupi along with it within the same tick rather than lagging a frame behind. Particle
debris (`ByeByeStep()`) is updated next, then Blupi's own physics and action state machine
(`BlupiStep()`, the subject of Chapter 17), then the camera's hot-spot zoom easing
(`MoveHotSpot()`), then vehicle motor sound pitch adaptation. The whole body is wrapped in a
catch-all `try`/`catch` that silently swallows any exception — a real, and startling, trait of the
shipped logic: a single bad frame cannot crash the game loop, but it can also leave simulation
state partially updated and rendered anyway. The source comment is blunt about this being
inherited behavior, not a place to add new logic: "Swallowing the exception means a partially-
updated frame can be rendered; this matches the original behaviour."

`MoveHotSpot()` itself (`Decor.cpp:538`) is a small but nicely self-contained piece of camera
logic worth a short digression, since it is unlikely to get its own chapter elsewhere in the
book: it decides, every frame, whether the camera should zoom in on Blupi (`m_hotSpotFinalZoom =
1.3`) or sit at the neutral `1.0`. The zoom-in condition is "Blupi is moving horizontally, has
input focus, is not in helicopter or Power mode, and auto-zoom is enabled in settings"
(`Decor.cpp:541-556`), and a `m_hotSpotOutLag` hysteresis timer (`Config::ScaleTime(30)` frames)
keeps the camera zoomed in for half a second or so after Blupi stops walking, specifically to
avoid the zoom visibly flickering in and out during brief pauses. The actual zoom/pan values are
eased toward their targets by fixed per-frame steps (`m_hotSpotStepZoom`, `m_hotSpotStepX/Y`,
scaled by `Config::SPEED_SCALE` so the easing rate is frame-rate-independent under `MODERN`'s
variable-FPS support — see Chapter 10 for `Config`'s LEGACY/MODERN distinction) rather than
snapping, which is why the in-game zoom feels like a camera drifting rather than cutting.

## `Build()`: the render dispatcher

`Build()` (`Decor.cpp:649`) is the render-side twin of `MoveStep()` — called once per frame,
always after `MoveStep()`, and (per its own header contract) never mutating simulation state,
only drawing it. It is a genuinely large method (roughly 350 lines drawing eleven distinct
layers), and Chapters 16 and 19 return to specific parts of it in detail — the tile-rendering
passes for Chapter 16, the moving-object draw loop for Chapter 19 — so this overview only
sketches its shape.

The source's own summary of the draw order is the right place to start:

*From `Decor.cpp:636-648`:*
```cpp
/**
 * @note Renders in strict back-to-front layers: (1) the tiled parallax background
 *       blitted in a 3x2 grid of 640x480 panels, (2) the big-decor tile layer
 *       (m_bigDecor) culled to the cells overlapping the visible draw bounds, (3) the
 *       foreground decor/objects/Blupi, then (4) HUD and particle/voyage overlays.
 *       Tiles are iterated by converting the scroll offset (posDecor) to a cell range
 *       padded by a one-tile margin so partially-visible edge tiles are drawn.
 * @note MODERN cheat-zoom widens the iterated cell range by zoomExtraX/Y tiles so the
 *       enlarged (zoomed-out) viewport is filled with real tiles instead of empty space.
 */
void Decor::Build()
```

Concretely, in the order the code actually executes:

1. **Parallax background panels.** The region's cached background image (loaded once by
   `LoadImages()`) is blitted as a repeating 3×2 grid of 640×480 panels via
   `IPixmap::DrawPart(PixmapChannel::Background, …)` (`Decor.cpp:680-699`), offset by two-thirds
   of the scroll position — the `2/3` factor (`Decor.cpp:652-654`) is what makes the background
   scroll more slowly than the foreground, i.e. genuine parallax.
2. **The `m_bigDecor` layer.** A tile loop over the visible cell range draws every non-empty
   `m_bigDecor[i][j].icon` directly via `IPixmap::QuickIcon()` (`Decor.cpp:700-741`) — Chapter 16
   covers exactly which sprite sheet this pulls from and why, since it is one of this Part's
   more surprising findings.
3. **A narrow `m_decor` pre-pass** that only draws icons `384`/`385` (the visual state of switch
   tiles) via the `Object` channel (`Decor.cpp:742-767`).
4. **Blupi**, drawn according to whichever secret power is active (Shield/Power/Cloud/Hide each
   layer an extra animated overlay sprite before or instead of Blupi's own icon —
   `Decor.cpp:768-844`).
5. **Moving objects**, back-to-front by pool index with a substantial per-type exclusion list
   (some types are drawn in an earlier or later pass instead — `Decor.cpp:845-902`; full detail in
   Chapter 19).
6. **The main `m_decor` tile pass**, which is where the bulk of the visible foreground geometry —
   ground, walls, water, lava, doors, spikes — actually gets drawn, several of it re-mapped
   through small per-icon animation tables (`Tables::table_decor_lave`, `table_decor_piege1/2`,
   `table_decor_goutte`, `table_decor_ecraseur`, `table_decor_scie`, `table_decor_temp`,
   `table_decor_eau1`, …) rather than drawn as a static icon (`Decor.cpp:916-1180`, approximately —
   Chapter 16 walks this pass closely).
7. **HUD, particles, and the "Voyage" pickup-flight overlay**, via `DrawInfo()`, `ByeByeDraw()`,
   and `VoyageDraw()` respectively, each a separate private method called near the end of
   `Build()`.

The `#ifdef MODERN` blocks threaded through nearly every one of these passes exist for exactly one
feature: the cheat zoom-out (`Tables::CheatCodes::Zoom`, Chapter 23). Zooming the camera out means
more of the level becomes visible at the screen's edges, so every tile-iteration loop needs a
`zoomExtraX`/`zoomExtraY` tile margin — computed once near the top of `Build()` from the inverse
of `m_cheatZoomFactor` — added on all sides so the enlarged viewport is filled with real tiles
instead of empty space (`Decor.cpp:662-679`).

## What comes next

This chapter has deliberately stayed at the level of "what exists and how it is wired together."
The next three chapters each take one slice of this class and go deep:

- Chapter 16 opens up `m_decor`/`m_bigDecor` themselves — the `Cellule` struct, the three
  coordinate systems in practice, and a careful, source-verified answer to the question of
  whether a tile's numeric `icon` is a rendering index, a collision classifier, or (as this
  chapter's reading of `Build()`, `AdaptBorder()`, and `IsPassIcon()`/`IsBlocIcon()` will show) a
  single value doing genuinely double duty.
- Chapters 17 and 18 take on the ~70-field, ~3,800-line Blupi state machine — first the physics
  and transition logic in `BlupiStep()`, then the `BlupiAction` enum and the `table_blupi`
  animation-lookup algorithm that turns a state into a sprite.

Everything else this chapter only gestured at — moving objects, doors, hazards, cheats, missions,
game speed, and the full `Decor.hpp` member catalog — has its own chapter later in Part IV.

## See also

- [Chapter 16 — The Tile Map](ch16-tile-map.md)
- [Chapter 17 — Blupi: the State Machine](ch17-blupi-state-machine.md)
- [Chapter 18 — Blupi Actions and Animation](ch18-blupi-actions-and-animation.md)
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md)
- [Chapter 27 — Decor.hpp Reference Catalog](ch27-decor-hpp-reference-catalog.md)
- [Chapter 12 — Game1: the State Machine](../part03-architecture/ch12-game1-state-machine.md)
- [Chapter 30 — Tables: Animation and Movement Data](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md)
