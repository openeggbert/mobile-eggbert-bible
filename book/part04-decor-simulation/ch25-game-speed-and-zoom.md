# Chapter 25: Game Speed and Zoom

## Overview

This chapter covers three related but independent mechanisms: the `GameSpeed` enum that lets a
`MODERN` build run the simulation faster than the original 20-frames-per-second design, the
`ZoomCheat` enum that lets a debug build pull the camera back to see more of the level at once, and
— underlying both — `Config::ScaleTime()`, the single function that makes it possible to change the
game's actual frame rate at all without silently breaking every hand-tuned timer in `Decor.cpp`.
`Decor.hpp`'s own top-level `@warning` singles this last piece out as the one rule a contributor
must not skip:

*From `Decor.hpp:79-80`:*

```cpp
 * @warning Do not add new timer values without applying Config::ScaleTime() — all
 *          original timing assumes a base rate of 20 FPS.
```

This chapter explains concretely what that means, with real timer values from `Decor.cpp` on both
sides of the scaling.

## The problem `Config::ScaleTime()` solves

`Decor`'s entire simulation — animation phase counters, hazard cycle timers, cooldowns like
`m_blupiTimeShield` — was designed and tuned against a fixed assumption: `MoveStep()` is called
once per rendered frame, and the game renders at 20 FPS. A constant like "spring animation frame
changes every `Config::ScaleDiv(2)` ticks" or "shield lasts 100 frames" only means what it was
tuned to mean if one frame really does equal 1/20th of a second. `Config.hpp` documents the two
build modes this way:

*From `Config.hpp:36-44`:*

```cpp
 * - LEGACY mode: reproduces the exact original game behaviour at 20 FPS with no
 *   touch-button visibility adaptation.
 * - MODERN mode: allows higher FPS and enables touch-button auto-hiding on
 *   non-touchscreen devices. All frame-count values must be passed through
 *   ScaleTime() / ScaleDiv() to remain correct at the configured FPS.
```

`LEGACY` locks `Config::FPS` to `Fps::Fps20` via a `static_assert` block (`Config.hpp:246-256`), so
in a `LEGACY` build `ScaleTime()`/`ScaleDiv()` are unconditionally identity functions
(`Config.hpp:218-235`) and this whole chapter's concern disappears — every raw constant in
`Decor.cpp` is already correct as written. `MODERN` is the interesting case: it allows
`Config::FPS` to be set to something other than 20 (the current shipped value is still
`Fps::Fps20`, per `Config.hpp:57`, but the whole scaling mechanism exists specifically so that can
be changed later without a rewrite).

## What `ScaleTime()`/`ScaleDiv()`/`SPEED_SCALE` actually compute

*From `Config.hpp:118-141`:*

```cpp
/**
 * @brief Scales a frame-count timer value from 20 FPS to the current FPS.
 * ...
 * At FPS=20: returns @p value unchanged.
 * At FPS=60: returns @p value * 3.
 */
static constexpr int ScaleTime(int value)
{
    if constexpr (FPS == Fps::Fps20)
    {
        return value;
    }
    else
    {
        return (value * CURRENT_FPS + ORIGINAL_FPS / 2) / ORIGINAL_FPS;
    }
}
```

`ScaleDiv()` is a plain alias for the same computation:

*From `Config.hpp:156-159`:*

```cpp
static constexpr int ScaleDiv(int value)
{
    return ScaleTime(value);
}
```

The distinction between the two names is purely about *intent* at the call site, not behavior: a
`ScaleTime(N)` call means "this constant is a frame-count duration (a timeout, a cooldown, a phase
target)"; a `ScaleDiv(N)` call means "this constant is a divisor applied to the running frame
counter `m_time` to pick an animation frame index." Both compile to the identical rounding-division
formula. There are two more derived constants, used for continuous (not integer-frame) quantities:

*From `Config.hpp:68-90`:*

```cpp
/** At FPS=20 this is 1.0; at FPS=60 this is 3.0. */
static constexpr double TIME_SCALE =
    static_cast<double>(CURRENT_FPS) / static_cast<double>(ORIGINAL_FPS);

/** At FPS=20 this is 1.0; at FPS=60 this is 0.333.... */
static constexpr double SPEED_SCALE =
    static_cast<double>(ORIGINAL_FPS) / static_cast<double>(CURRENT_FPS);
```

`TIME_SCALE` and `SPEED_SCALE` are reciprocals of each other by construction. The intuition: at a
higher FPS, more frames elapse per second of wall-clock time, so a *per-frame* speed value (pixels
moved per `MoveStep()` call) must shrink by `SPEED_SCALE` to keep the *per-second* speed constant,
while a frame-count *duration* must grow by `TIME_SCALE` (equivalently, be passed through
`ScaleTime`) to still represent the same number of real seconds.

## Real call sites in `Decor.cpp`

`Config::ScaleTime`/`ScaleDiv` are not a theoretical concern — `Decor.cpp` calls one or the other
**289 separate times**. A representative sample, spanning cooldowns, animation-cycle divisors, and
one-shot phase targets:

| Call site | What it scales | Citation |
|---|---|---|
| `m_hotSpotOutLag = Config::ScaleTime(30);` | Hysteresis window (in frames) that keeps the camera zoomed in briefly after Blupi stops walking. | `Decor.cpp:559` |
| `int num = (m_time / Config::ScaleDiv(1)) % 100;` | Divisor for the 100-tick lightning (`blitz`) flicker cycle. | `Decor.cpp:623` |
| `num2 = Tables::table_shield_blupi[m_time / Config::ScaleDiv(2) % 16];` | Divisor selecting the current frame of the Shield overlay animation (16-frame table). | `Decor.cpp:787` |
| `num2 = Tables::table_decor_lave[(i * 13 + j * 7 + m_time / Config::ScaleDiv(2)) % 8];` | Divisor for the lava tile's 8-frame animation cycle. | `Decor.cpp:1029` |
| `num2 = Tables::table_decor_ecraseur[m_time / Config::ScaleDiv(3) % 10];` | Divisor for the crusher hazard's 10-frame animation cycle. | `Decor.cpp:1055` |
| `if (m_blupiAction == BlupiAction::Jump && m_blupiPhase == Config::ScaleTime(3))` | One-shot phase target: the exact frame within the jump animation where a sound/effect triggers. | `Decor.cpp:2922` |
| `m_blupiTimeFire = Config::ScaleTime(10);` | Tank fire cooldown, in frames. | `Decor.cpp:3072` |
| `m_moveObject[num].stepAdvance = Config::ScaleTime(50);` (inside `OpenDoor`) | Duration, in frames, of the door-opening slide animation. | `Decor.cpp:11673` |

Every one of these is an example of the same underlying pattern: a constant that was tuned by eye
against the original 20 FPS simulation (`30` frames of camera hysteresis, `1`/`2`/`3` as animation
divisors, `10` frames of tank-fire cooldown) is written as a call to `ScaleTime`/`ScaleDiv` rather
than as the bare literal, so that if `Config::FPS` is ever changed from `Fps20` to something faster,
every one of these 289 call sites automatically re-expresses its original *duration in seconds*
instead of silently becoming three times too short (or too long) at a 60 FPS build. `Decor.hpp`'s
warning exists precisely because a contributor adding call site #290 — a brand new timer — who
writes the bare frame-count literal instead of wrapping it in `ScaleTime()`/`ScaleDiv()` produces
code that happens to work today (at `Fps20`, the wrapper is a no-op) but silently breaks the moment
anyone builds at a different `Config::FPS`.

`MoveHotSpot()` (the camera zoom-follow logic — see below) is one of the few places that reaches for
`SPEED_SCALE` directly instead of `ScaleTime`/`ScaleDiv`, because its per-frame step sizes are
continuous speeds, not frame-count durations:

*From `Decor.cpp:591-593`:*

```cpp
m_hotSpotStepZoom = Config::SPEED_SCALE / 30.0;
m_hotSpotStepX = 10.0 * Config::SPEED_SCALE;
m_hotSpotStepY = 10.0 * Config::SPEED_SCALE;
```

## `GameSpeed`: a simulation-tick multiplier, not a frame-rate change

*From `include/WindowsPhoneSpeedyBlupi/def/GameSpeed.hpp:29-36`:*

```cpp
enum class GameSpeed : GameSpeedUnderlying
{
    Slow    = 0,  ///< @brief Reduced speed (0 extra ticks per frame).
    Normal  = 1,  ///< @brief Standard game speed (1 tick per frame, default).
    Fast    = 2,  ///< @brief Double speed (2 ticks per frame).
    Faster  = 4,  ///< @brief Quadruple speed (4 ticks per frame).
    Fastest = 8   ///< @brief Maximum speed (8 ticks per frame).
}
```

It is important not to confuse `GameSpeed` with `Config::FPS`/`ScaleTime()`. `Config::FPS` changes
how many real frames occur per second and rescales every timer so gameplay *feels* the same at any
render rate. `GameSpeed`, by contrast, changes how many times `Decor::MoveStep()` — a full
simulation tick — is invoked per rendered frame, which makes the simulation itself run faster or
slower in wall-clock time; nothing about it touches `ScaleTime()`. The dispatch lives entirely in
`Game1::Update()`, not in `Decor`:

*From `Game1.cpp:394-416`:*

```cpp
if (phase == Def::Phase::Play)
{
    decor.setButtonPressedProperty(buttonPressed);
#ifndef LEGACY
    if (gameSpeed == GameSpeed::Slow)
    {
        static bool slow_frame = false;
        slow_frame = !slow_frame;
        if (slow_frame)
        {
            decor.MoveStep();
        }
    }
    else
    {
        for (int speedStep = 0; speedStep < ToRaw(gameSpeed); speedStep++)
        {
            decor.MoveStep();
        }
    }
#else
    decor.MoveStep();
#endif
```

`Slow` is the one value that doesn't fit the "N ticks per frame" pattern its own doc comment
implies (`0 extra ticks per frame`, `ToRaw(Slow) == 0`) — if the loop above literally used
`ToRaw(gameSpeed)` as the iteration count for `Slow`, `MoveStep()` would never run at all. Instead
`Slow` is special-cased to call `MoveStep()` on every *other* rendered frame (a toggling
`slow_frame` bool), giving an effective 0.5 ticks per frame — hence the UI label quoted directly in
`InputPad.cpp`:

*From `InputPad.cpp:1386-1389`:*

```cpp
if (spd > GameSpeed::Normal || spd == GameSpeed::Slow)
{
    std::string speedText = (spd == GameSpeed::Slow) ? "0.5x" : std::to_string(ToRaw(spd)) + "x";
```

Every other value (`Normal`, `Fast`, `Faster`, `Fastest`) calls `Decor::MoveStep()` back-to-back,
`ToRaw(gameSpeed)` times, within a single rendered frame — `Fastest` runs eight full simulation
frames for every one frame actually drawn to the screen. This is a `LEGACY`-excluded feature
entirely: the `#else` branch compiles to a single unconditional `decor.MoveStep()`, so a `LEGACY`
build has no speed control at all and always runs at exactly one tick per rendered frame.

### How a player reaches each `GameSpeed` value

Three independent input paths all funnel into the same `Game1::SetGameSpeed`/`getGameSpeed`
pair (`Game1.cpp:1077-1094`):

| Trigger | Effect | Citation |
|---|---|---|
| `F5`/`F6`/`F7`/`F8` keys | Set `Normal`/`Fast`/`Faster`/`Fastest` respectively, via `GameSpeed ToGameSpeed(Keys key)`. | `GameSpeed.hpp:121-136`, `InputPad.cpp:603-629` |
| `Tab` key | Toggles between `Slow` and `Normal`. | `InputPad.cpp:657-676` |
| `Left Shift` held | Temporarily forces `Fast` (or `Fastest`, if the `quick` typed cheat is active), restoring the prior speed on release. | `InputPad.cpp:633-655` |
| Typed cheat `"quick"` | Toggles `quick_cheat_enabled`; when turned off while faster than `Fast`, clamps back down to `Fast`. | `InputPad.cpp:754-761` |
| Typed cheat `"ghost"` (`MODERN`) | Turning ghost mode on saves the current speed and forces `Faster`; turning it off restores the saved speed. | `InputPad.cpp:819-836` |

Note that `F5` maps to `Normal`, not `Slow` — there is no keyboard shortcut that reaches `Slow`
directly through the F-key row; `Tab` is the only way in.

## `Zoom`/`ZoomCheat`: a `MODERN`-only render-scale cheat

The `Zoom.hpp` enum, unlike `GameSpeed`, is compiled only under `MODERN` and has no `LEGACY`
equivalent at all:

*From `include/WindowsPhoneSpeedyBlupi/def/Zoom.hpp:24-30`:*

```cpp
#ifdef MODERN
enum class ZoomCheat
{
    Zoom100,  ///< @brief 100% render scale (normal view, 640x480 logical area visible).
    Zoom50,   ///< @brief 50% render scale (visible width approximately 2x wider).
    Zoom25,   ///< @brief 25% render scale (visible width approximately 4x wider).
    Zoom12    ///< @brief 12.5% render scale (visible width approximately 8x wider).
};
#endif
```

This enum only exists in `InputPad.cpp`, as local state (`zoom_cheat_state`) driving a cycle through
the four levels each time the typed cheat `"zoom"` is entered; `Decor` itself has no `ZoomCheat`
member and never inspects this enum. What `Decor` *does* expose is a single continuous multiplier,
`m_cheatZoomFactor` (`MODERN`-only, `Decor.hpp:383`), set through one public method:

*From `Decor.cpp:11630-11633`:*

```cpp
void Decor::SetCheatZoom(double factor)
{
    m_cheatZoomFactor = factor;
}
```

`InputPad.cpp`'s cheat-cycling code calls this with the exact fractions the enum's own doc comments
promise (`1.0`, `0.5`, `0.25`, `0.125`), confirming the `ZoomCheat` names line up with the real
factors applied:

*From `InputPad.cpp:790-813`:*

```cpp
if (zoom_cheat_state == ZoomCheat::Zoom100)
{
    zoom_cheat_state = ZoomCheat::Zoom50;
    decor->SetCheatZoom(0.5);
    activePersistentCheats.push_back("zoom50");
}
else if (zoom_cheat_state == ZoomCheat::Zoom50)
{
    zoom_cheat_state = ZoomCheat::Zoom25;
    decor->SetCheatZoom(0.25);
    activePersistentCheats.push_back("zoom25");
}
else if (zoom_cheat_state == ZoomCheat::Zoom25)
{
    zoom_cheat_state = ZoomCheat::Zoom12;
    decor->SetCheatZoom(0.125);
    activePersistentCheats.push_back("zoom12");
}
else
{
    zoom_cheat_state = ZoomCheat::Zoom100;
    decor->SetCheatZoom(1.0);
    // No label added for Zoom100 (normal view).
}
```

(`ZoomCheat::Zoom12`'s doc comment says "12.5%"; `SetCheatZoom(0.125)` is exactly that fraction —
the enum member's truncated name (`Zoom12`, not `Zoom12_5`) is a naming shorthand, not an
inaccuracy.)

### What `m_cheatZoomFactor` actually changes

Two independent effects flow from `m_cheatZoomFactor`, both inside functions this book covers
elsewhere for their non-zoom behavior:

**1. The camera hotspot's target zoom is multiplied by it**, inside `MoveHotSpot()` (the same
function responsible for the ordinary walking-zoom-in behavior described in the note above it):

*From `Decor.cpp:588-590`:*

```cpp
#ifdef MODERN
    m_hotSpotFinalZoom *= m_cheatZoomFactor;
#endif
```

So a cheat-zoom of `0.125` doesn't set the camera's zoom directly — it scales whatever zoom target
`MoveHotSpot()`'s ordinary walking/idle logic already computed (`1.3` while walking with auto-zoom
on, `1.0` otherwise), and the existing per-frame interpolation (`m_hotSpotStepZoom`, `Config::SPEED_SCALE`-scaled)
still carries the *current* zoom toward that new target gradually rather than snapping to it.

**2. `Build()` widens the range of tiles it iterates**, so the zoomed-out (and therefore visually
larger) viewport doesn't show empty space at its edges:

*From `Decor.cpp:662-678`:*

```cpp
#ifdef MODERN
    // When zoomed out, the hotspot transform shrinks all world sprites toward the
    // screen centre.  Extra world tiles must be rendered on all sides so that the
    // enlarged visible area is filled with actual content instead of black/empty space.
    int zoomExtraX = 0;
    int zoomExtraY = 0;
    if (m_cheatZoomFactor > 0.0 && m_cheatZoomFactor < 1.0)
    {
        // How many extra pixels are needed outside each screen edge after the
        // inverse zoom:  extraPx = screenHalf * (1/zoom - 1)
        // Round up to the nearest 64-pixel tile boundary.
        double invScale = 1.0 / m_cheatZoomFactor - 1.0;
        zoomExtraX = static_cast<int>(
            std::ceil(m_drawBounds.getWidthProperty()  * 0.5 * invScale / 64.0));
        zoomExtraY = static_cast<int>(
            std::ceil(m_drawBounds.getHeightProperty() * 0.5 * invScale / 64.0));
    }
#endif
```

`zoomExtraX`/`zoomExtraY` (in whole tiles) are then added symmetrically to every tile-iteration
loop bound throughout the rest of `Build()` (background, `m_bigDecor`, `m_decor`, and moving-object
culling all repeat the same `- zoomExtraX * 64` / `+ zoomExtraX * 64` pattern on their loop
bounds) — this is why the calculation is done once, up front, rather than inline at each loop.

Two other public `MODERN`-only accessors round out the debug-zoom-adjacent surface, both trivial
passthroughs used by the debug overlay (`Cheats`/`Debug` typed cheats) rather than by gameplay:

*From `Decor.hpp:1991-2016`:*

```cpp
int GetTime() const { return m_time; }
TinyPoint GetBlupiPos() const { return m_blupiPos; }
double GetBlupiVX() const { return m_blupiVitesseX; }
double GetBlupiVY() const { return m_blupiVitesseY; }
bool GetBlupiAir() const { return m_blupiAir; }
bool GetBlupiHelico() const { return m_blupiHelico; }
bool GetBlupiSkate() const { return m_blupiSkate; }
bool GetBlupiNage() const { return m_blupiNage; }
int GetRegionDebug() { return GetRegion(); }
```

## Interaction between `GameSpeed` and zoom cheats

The `Ghost` and `quick` typed cheats both reach into `GameSpeed` as a side effect (see the table
above), but neither touches `m_cheatZoomFactor`; the zoom cheat cycle is entirely independent and
can be combined freely with any `GameSpeed` value — there is no code anywhere that couples the two.
The one place they are visually related, but not causally coupled, is that both act on the same
`MoveHotSpot()`/`Build()` camera pipeline: a `Fastest`-speed, `Zoom12`-zoomed session runs eight
simulation ticks per rendered frame while showing roughly eight times the normal viewport area, and
each of those two multipliers was reached through a completely separate cheat/keybinding path.

## See also

- [Chapter 10 — Config: LEGACY vs MODERN](../part02-building-and-running/ch10-config-legacy-vs-modern.md) —
  full coverage of `Config.hpp` beyond the timing pieces used here.
- [Chapter 12 — Game1: the State Machine](../part03-architecture/ch12-game1-state-machine.md) —
  `Game1::Update()`'s per-phase structure, of which the `GameSpeed` dispatch shown here is one part.
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md) — velocity fields
  (`m_blupiVitesseX/Y`) that `SPEED_SCALE` and `GameSpeed` both ultimately affect.
- [Chapter 23 — Secret Powers and the Cheat System](ch23-secret-powers-and-cheat-system.md) — the
  typed `quick`/`ghost`/`zoom`/`debug` cheats that drive the `GameSpeed`/zoom paths documented here.
- [Chapter 41 — InputPad: Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) —
  full `InputPad.cpp` coverage, of which the speed/zoom key bindings here are one slice.
