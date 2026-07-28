# Chapter 10: Config — LEGACY vs. MODERN

Two files govern one of the most consequential compile-time decisions in the entire codebase:
`ConfigDef.hpp` (which defines the enumerations and shared constants) and `Config.hpp` (which
selects, at compile time, between two entirely different behavior profiles: `LEGACY` and
`MODERN`). `mobile-eggbert`'s own `CLAUDE.md` describes this pair as affecting "timing, resolution,
and feature flags globally" — this chapter reads both files in full and verifies exactly which
values differ between the two modes, which stay identical, and how the resulting constants and
helper functions are actually consumed elsewhere in the codebase.

## The mode switch itself

`Config.hpp` opens with the mechanism that selects between the two modes:

*From `Config.hpp:1-19`:*
```cpp
/**
 * @file Config.hpp
 * @brief Compile-time configuration constants for the Speedy Blupi port (LEGACY and MODERN modes).
 *
 * @details Exactly one of LEGACY or MODERN must be defined. LEGACY reproduces the original
 * 20 FPS behaviour unchanged. MODERN enables higher frame rates and touch-button auto-hiding,
 * and requires all frame-count values to be passed through ScaleTime()/ScaleDiv().
 *
 * @note Do not mix LEGACY and MODERN defines in the same translation unit.
 */

#pragma once

#include "WindowsPhoneSpeedyBlupi/ConfigDef.hpp"
//#define LEGACY

#ifndef LEGACY
#define MODERN
#endif
```

The mechanism is a plain preprocessor `#ifndef`: `LEGACY` is defined only if a commented-out
`//#define LEGACY` line is uncommented (there is no CMake `option()` or build-system flag driving
this choice — it is a hand-edited source toggle), and whichever of `LEGACY`/`MODERN` is *not*
active is defined as the fallback. As shipped, with `LEGACY` commented out, **`MODERN` is the
active mode** in the current codebase. A boolean is also derived and exposed to the rest of the
program for runtime queries about which mode is compiled in:

*From `Config.hpp:21-29`:*
```cpp
namespace WindowsPhoneSpeedyBlupi
{
#ifdef LEGACY
    /** @brief True when the legacy (original behaviour) mode is compiled in. */
    static constexpr bool LEGACY_ENABLED = true;
#else
    /** @brief False when the modern port mode is compiled in. */
    static constexpr bool LEGACY_ENABLED = false;
#endif
```

## `ConfigDef.hpp`: the enumerations shared by both modes

Before either `LEGACY` or `MODERN`'s `#ifdef` blocks apply, `Config.hpp` includes `ConfigDef.hpp`,
whose own file-header comment explains why its contents are deliberately kept unconditional:

*From `ConfigDef.hpp:1-8`:*
```cpp
/**
 * @file ConfigDef.hpp
 * @brief Defines the ResolutionScale and Fps enumerations and their default constants used by Config.
 *
 * @details These definitions are shared between LEGACY and MODERN build configurations and must
 * not be conditionally compiled. They are included by Config.hpp before the LEGACY/MODERN
 * preprocessor guards take effect.
 */
```

It defines two enum classes. The first governs resolution scaling:

*From `ConfigDef.hpp:12-26`:*
```cpp
namespace WindowsPhoneSpeedyBlupi
{
    /**
     * @brief Selects the rendering resolution multiplier for the game viewport.
     *
     * @details Used to scale the base 640x480 logical resolution up for high-DPI displays.
     * Only ScaleResolution1 (1:1) is currently active in production builds.
     * Higher values are reserved for future high-DPI support.
     */
    enum class ResolutionScale
    {
        ScaleResolution1 = 1, ///< @brief Native 640x480 logical resolution (default, 1:1 pixel mapping).
        ScaleResolution2 = 2, ///< @brief 2x upscale — 1280x960 logical resolution.
        ScaleResolution4 = 4  ///< @brief 4x upscale — 2560x1920 logical resolution.
    };

    // Please do not change
    inline constexpr ResolutionScale RESOLUTION_SCALE_DEFAULT = ResolutionScale::ScaleResolution1;
```

and the second governs the target update rate:

*From `ConfigDef.hpp:36-71`:*
```cpp
    /**
     * @brief Target update rates supported by the compile-time configuration.
     *
     * @details Fps20 is the original stable timing from the Windows Phone release.
     * Higher values are experimental and require gameplay code to preserve the original
     * real-time behaviour using Config::ScaleTime(), Config::ScaleDiv(), and
     * Config::SPEED_SCALE where appropriate.
     *
     * @warning Using frame rates other than Fps20 without applying the scale helpers
     *          will cause gameplay to run at incorrect speeds.
     */
    enum class Fps
    {
        Fps20  = 20,  ///< @brief Original 20 FPS game speed (default, stable).
        Fps30  = 30,  ///< @brief 30 FPS (experimental, requires ScaleTime/ScaleDiv/SPEED_SCALE).
        Fps60  = 60,  ///< @brief 60 FPS (experimental, requires ScaleTime/ScaleDiv/SPEED_SCALE).
        Fps90  = 90,  ///< @brief 90 FPS (experimental, requires ScaleTime/ScaleDiv/SPEED_SCALE).
        Fps120 = 120, ///< @brief 120 FPS (experimental, requires ScaleTime/ScaleDiv/SPEED_SCALE).
        Fps144 = 144, ///< @brief 144 FPS (experimental, requires ScaleTime/ScaleDiv/SPEED_SCALE).
    };

    // Please do not change
    inline constexpr Fps FPS_DEFAULT = Fps::Fps20;

    /**
     * @brief The original game's update rate as a plain integer (20).
     *
     * @details Used as the denominator in TIME_SCALE and SPEED_SCALE calculations.
     * All ScaleTime()/ScaleDiv() computations are relative to this value. Do not change.
     */
    static constexpr int ORIGINAL_FPS = static_cast<int>(Fps::Fps20);
}
```

`Fps20` is explicitly the original Windows Phone release's timing (20 updates per second — a low
figure by modern standards, but the number the entire original game's tuning, animation timing, and
physics were built against). The `Fps` enum offers five higher options up through `Fps144`, each
annotated "experimental, requires ScaleTime/ScaleDiv/SPEED_SCALE" — a warning that these are not
free performance upgrades; they require every frame-count-based timer and per-frame movement value
in the gameplay code to be explicitly rescaled (via the helpers detailed below) to keep real-world
timing and speeds correct, since the original code's constants are frame-count values tuned
specifically for 20 Hz.

## What actually differs between LEGACY and MODERN, verified value by value

`Config` struct's body is split into two large, mutually exclusive `#ifdef MODERN` / `#ifdef
LEGACY` blocks defining the same set of named members. Verifying them side by side against the
real source:

| Constant / method | `MODERN` (`Config.hpp:49-176`) | `LEGACY` (`Config.hpp:178-244`) |
|---|---|---|
| `FPS` | `Fps::Fps20` | `Fps::Fps20` |
| `CURRENT_FPS` | `static_cast<int>(FPS)` (currently `20`) | `static_cast<int>(Fps::Fps20)` (`20`) |
| `TIME_SCALE` | `CURRENT_FPS / ORIGINAL_FPS` (computed; currently `1.0`) | hardcoded `1.0` |
| `SPEED_SCALE` | `ORIGINAL_FPS / CURRENT_FPS` (computed; currently `1.0`) | hardcoded `1.0` |
| `RESOLUTION_SCALE` | `static_cast<int>(ResolutionScale::ScaleResolution1)` (`1`) | `static_cast<int>(ResolutionScale::ScaleResolution1)` (`1`) |
| `TOUCH_BUTTONS_SHOWN_ONLY_IF_TOUCHSCREEN_IS_AVAILABLE` | `true` | `false` |
| `INPUT_DETAILED_DEBUGGING_ENABLED` | `false` | `false` |
| `ScaleTime(value)` | identity at `Fps20`; otherwise `(value * CURRENT_FPS + ORIGINAL_FPS/2) / ORIGINAL_FPS` | always `value` unchanged (no `if constexpr` branch at all) |
| `ScaleDiv(value)` | calls `ScaleTime(value)` | always `value` unchanged |
| `ScaleAsset(value)` | `value * RESOLUTION_SCALE` | `value * RESOLUTION_SCALE` |

The single, concrete, currently-observable difference between the two modes, given the values
actually shipped in this snapshot of the code, is
**`TOUCH_BUTTONS_SHOWN_ONLY_IF_TOUCHSCREEN_IS_AVAILABLE`** (`true` in `MODERN`, `false` in
`LEGACY`) — everything else evaluates identically today, because `MODERN`'s `FPS` is currently set
to `Fps::Fps20`, the same value `LEGACY` hardcodes. This is an important nuance the "affects timing
... globally" framing in `mobile-eggbert`'s `CLAUDE.md` doesn't spell out on its own: the
*mechanism* for a timing difference exists and is fully wired up (change `MODERN`'s `FPS` to, say,
`Fps::Fps60`, and `CURRENT_FPS`/`TIME_SCALE`/`SPEED_SCALE` all recompute automatically, and
`ScaleTime`/`ScaleDiv` switch from their identity branch to their scaling branch), but as *shipped
and compiled today*, `MODERN` mode runs at the same 20 FPS as `LEGACY` — the two modes are not
currently divergent in actual runtime timing, only in the touch-button-visibility behavior and in
which code path (identity vs. computed) would activate if `FPS` were changed.

### `MODERN`'s `ScaleTime`/`ScaleDiv`: a real `if constexpr` branch, not just documentation

*From `Config.hpp:131-159`:*
```cpp
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

        static constexpr int ScaleDiv(int value)
        {
            return ScaleTime(value);
        }
```

The `if constexpr` here means the branch is resolved entirely at compile time, based on the `FPS`
value currently selected — with `FPS == Fps::Fps20`, the compiler generates only the identity
`return value;` path, and the scaling arithmetic branch is compiled out entirely. The scaling
formula itself, `(value * CURRENT_FPS + ORIGINAL_FPS / 2) / ORIGINAL_FPS`, is an integer
proportional scale from 20 FPS to `CURRENT_FPS`, with `+ ORIGINAL_FPS / 2` acting as a
round-to-nearest correction term before the integer division (standard technique for rounding
rather than truncating integer division results) — so a 20 FPS frame-count value of, say, `10`
scaled to `Fps60` (`CURRENT_FPS = 60`) becomes `(10*60 + 10) / 20 = 30.5` truncated to `30`, exactly
tripling the original count, which matches the doc comment's own worked example ("At FPS=60:
returns value * 3").

### `LEGACY`'s `ScaleTime`/`ScaleDiv`: unconditional identity, with no branch at all

*From `Config.hpp:218-235`:*
```cpp
        // Please do not change
        static constexpr int ScaleTime(int value)
        {
            return value;
        }

        // Please do not change
        static constexpr int ScaleDiv(int value)
        {
            return value;
        }
```

`LEGACY`'s versions have no conditional logic whatsoever — they cannot scale, ever, by
construction, since `LEGACY`'s own `FPS` value is likewise hardcoded to `Fps::Fps20` with no
alternative path available at all (unlike `MODERN`'s, which merely *currently defaults* to `Fps20`
but has the machinery in place to run at another rate). This is reinforced by a battery of
`static_assert`s at the very end of the `LEGACY` block, which exist purely to make any accidental
future edit to a `LEGACY`-mode constant fail to compile rather than silently drift:

*From `Config.hpp:246-256`:*
```cpp
#ifdef LEGACY
        static_assert(FPS == Fps::Fps20, "LEGACY mode must use Fps20");
        static_assert(CURRENT_FPS == static_cast<int>(Fps::Fps20), "LEGACY mode CURRENT_FPS must be 20");
        static_assert(TIME_SCALE == 1.0, "LEGACY mode TIME_SCALE must be 1.0");
        static_assert(SPEED_SCALE == 1.0, "LEGACY mode SPEED_SCALE must be 1.0");
        static_assert(RESOLUTION_SCALE == static_cast<int>(ResolutionScale::ScaleResolution1),
                      "LEGACY mode RESOLUTION_SCALE must be 1");
        static_assert(TOUCH_BUTTONS_SHOWN_ONLY_IF_TOUCHSCREEN_IS_AVAILABLE == false,
                      "LEGACY mode must not hide touch buttons");
        static_assert(INPUT_DETAILED_DEBUGGING_ENABLED == false, "LEGACY mode must not enable input debugging");
#endif
```

No equivalent `static_assert` block exists for `MODERN` — which is consistent with `MODERN` being
the mode intended to vary (higher FPS, different resolution scales in the future) while `LEGACY` is
explicitly meant to be an immutable, exact reproduction of the original 20 FPS Windows Phone
behavior, locked down by compile-time assertions against any future edit that would compromise
that guarantee.

## `INPUT_DETAILED_DEBUGGING_ENABLED`: identical in both modes today

Both modes currently set this to `false`. `MODERN`'s own doc comment frames it as a genuine,
intentionally-toggleable debugging aid rather than a mode-differentiating flag:

*From `Config.hpp:108-116`:*
```cpp
        /**
         * @brief Enables verbose console logging for input events when true.
         *
         * @details Useful for diagnosing input mapping issues during porting work.
         *
         * @warning Must be false in release builds. Setting this to true generates
         *          significant console output that may affect performance.
         */
        static constexpr bool INPUT_DETAILED_DEBUGGING_ENABLED = false;
```

This is covered further, in the context of `InputPad`'s actual input-mapping logic, in
[Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md).

## `Config::ScaleTime()` and `ScaleDiv()`: where the scaling machinery is meant to be used

`Config.hpp`'s own top-of-file doc comment states the requirement plainly: "MODERN enables higher
frame rates ... and requires all frame-count values to be passed through ScaleTime()/ScaleDiv()."
The intended usage is that any gameplay timer or animation-frame-divisor constant, expressed in the
original game's 20 FPS terms, gets wrapped in `Config::ScaleTime(...)` (for timeout/delay-style
frame counts) or `Config::ScaleDiv(...)` (for animation-frame-advance divisors) wherever it's
declared or used, so that if `MODERN`'s `FPS` is ever changed away from `Fps20`, every such value
automatically rescales rather than needing to be hand-edited. This is the compile-time contract the
mode switch depends on for correctness at any FPS other than the original 20 — and it is a
discipline that has to be maintained by hand across the gameplay code (there is no compiler
enforcement that a given `int` constant *has* been passed through `ScaleTime()`/`ScaleDiv()`
appropriately), which is presumably part of why the doc comment states the requirement so
explicitly and repeatedly across both `Config.hpp` and `ConfigDef.hpp`.

## `Config::RESOLUTION_SCALE` and `Config::ScaleAsset()`: the confirmed cross-reference into `Pixmap.cpp`

Unlike `ScaleTime`/`ScaleDiv`, `ScaleAsset()` is identical in both modes and is already exercised
extensively elsewhere in the codebase — a real, verified cross-reference into the sprite-rendering
layer covered in depth in [Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)
and [Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md).

*From `Config.hpp:161-174` (`MODERN`; `LEGACY`'s copy at `Config.hpp:237-242` is byte-for-byte
identical apart from the `@copydoc` comment style):*
```cpp
        /**
         * @brief Scales an integer pixel/size value by the asset resolution scale factor.
         *
         * @details Use this to convert 1x sprite-sheet coordinates (cell widths, heights,
         * gaps, offsets) to the corresponding pixel values in the loaded texture.
         * At RESOLUTION_SCALE=1 the value is returned unchanged.
         *
         * @param[in] value Size in 1x sprite-sheet pixels.
         * @return Equivalent size in the loaded texture pixels.
         */
        static constexpr int ScaleAsset(int value)
        {
            return value * RESOLUTION_SCALE;
        }
```

`Pixmap.cpp`'s own file-header comment independently documents the same contract from the
consuming side:

*From `Pixmap.cpp:29-32`:*
```cpp
 * ### Resolution scaling
 * Textures may be loaded at 1x, 2x, or 4x resolution (controlled by
 * Config::RESOLUTION_SCALE).  Source rectangles passed to SpriteBatch are
 * multiplied by RESOLUTION_SCALE via ScaleSourceRect() / Config::ScaleAsset() so
 * they address the correct pixels in the higher-resolution atlas.  Destination
 * rectangles always remain in 1x logical coordinates.
```

And, verified directly against `Pixmap::DrawIcon`'s real `switch (channel)` block, `Config::ScaleAsset()`
is called at every single per-channel grid-parameter assignment — not just conceptually described,
but genuinely invoked dozens of times across the atlas-addressing logic:

*From `Pixmap.cpp:556-559` (the `Blupi`/`Blupi1_*` channel case):*
```cpp
            srcGridX     = Config::ScaleAsset(60);
            srcGridY     = Config::ScaleAsset(60);
            srcIconWidth  = Config::ScaleAsset(60);
            srcIconHeight = Config::ScaleAsset(60);
```

*From `Pixmap.cpp:565-569` (the `Object` channel case, which also has a nonzero inter-cell gap):*
```cpp
            srcGridX     = Config::ScaleAsset(64);
            srcGridY     = Config::ScaleAsset(64);
            srcIconWidth  = Config::ScaleAsset(64);
            srcIconHeight = Config::ScaleAsset(64);
            srcGap       = Config::ScaleAsset(1);
```

and equivalent `Config::ScaleAsset(...)` calls recur for the `Element` (60×60), `Explosion`
(144×144 base grid, with per-icon width/height also individually scaled via
`Config::ScaleAsset(baseIconWidth)`/`Config::ScaleAsset(baseIconHeight)`), `Text` (32×32), `Button`
(40×40), and `Pad` (140×140) channels — the full per-channel grid table cataloged in `PLAN.md` and
covered in depth in [Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md).
Every one of those raw pixel constants (`60`, `64`, `1`, `144`, `32`, `40`, `140`, and so on) is a
1x sprite-sheet measurement, read directly off the on-disk PNG atlases; wrapping each one in
`Config::ScaleAsset()` is what would let a future `RESOLUTION_SCALE` of `2` or `4` (per the
`ResolutionScale` enum's `ScaleResolution2`/`ScaleResolution4` variants defined in `ConfigDef.hpp`)
correctly re-address a higher-resolution atlas without touching a single call site in
`Pixmap::DrawIcon` — exactly analogous, in spirit, to how `ScaleTime()`/`ScaleDiv()` are meant to
future-proof gameplay timers against a higher `FPS`. As with `RESOLUTION_SCALE` itself, this scaling
is currently a no-op multiplication by `1` in every shipped build (`RESOLUTION_SCALE_DEFAULT` and
both modes' `RESOLUTION_SCALE` all resolve to `ResolutionScale::ScaleResolution1 = 1`) — the
plumbing is real and already exercised at every sprite draw call, but the actual behavior it
enables (loading and addressing a 2x/4x atlas) is, per `ConfigDef.hpp`'s own comment, "reserved for
future high-DPI support" rather than active today.

## Summary: what "affects timing, resolution, and feature flags globally" actually means, verified

Reading both files directly confirms `mobile-eggbert`'s `CLAUDE.md` characterization is accurate in
scope, if a little broader than the *current* runtime effect: the `LEGACY`/`MODERN` switch is wired
to genuinely control timing (`FPS`, `CURRENT_FPS`, `TIME_SCALE`, `SPEED_SCALE`, and the
`ScaleTime()`/`ScaleDiv()` helpers that gameplay code depends on throughout the simulation — see
[Part IV](../part04-decor-simulation/ch15-decor-overview.md)), resolution (`RESOLUTION_SCALE` and
`ScaleAsset()`, exercised throughout `Pixmap.cpp`'s sprite-atlas addressing as shown above), and at
least one genuine feature flag (`TOUCH_BUTTONS_SHOWN_ONLY_IF_TOUCHSCREEN_IS_AVAILABLE`) — all
selected by a single compile-time toggle at the top of one header file, exactly the kind of
single-point-of-truth, globally-felt configuration the description implies. What is worth stating
precisely, though, is that as the code stands today, `MODERN`'s `FPS` is set to the same `Fps20`
value `LEGACY` hardcodes, so the timing and resolution machinery — while fully implemented, tested
via `static_assert` on the `LEGACY` side, and already load-bearing in `Pixmap.cpp` for resolution —
is not currently producing an observably different frame rate or resolution between the two modes;
the touch-button-visibility flag is the one behavior difference a player would actually notice
between a `LEGACY` build and a `MODERN` build as currently configured.

## See also

- [Chapter 4: Build Overview (CMake)](ch04-build-overview.md)
- [Chapter 25: Game Speed and Zoom](../part04-decor-simulation/ch25-game-speed-and-zoom.md)
- [Chapter 28: Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)
- [Chapter 29: The Sprite Atlas System](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md)
- [Chapter 41: InputPad: Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md)
