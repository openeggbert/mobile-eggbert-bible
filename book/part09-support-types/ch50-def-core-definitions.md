# Chapter 50: Def.hpp — Core Definitions

`Def` is the closest thing `mobile-eggbert` has to a single global header of constants. It is a
215-line file, `include/WindowsPhoneSpeedyBlupi/Def.hpp`, with no matching `.cpp` — every member
is either a `static constexpr` value, an `enum class`, or an inline static function, so the whole
class compiles away to nothing at link time. Like `Misc` ([Chapter 48](ch48-misc-utility-functions.md)),
it is a C++ port of an original C# static class of the same name, and like `Misc` it can never be
instantiated:

*From `Def.hpp:36-40`:*
```cpp
class Def
{
public:
    Def() = delete;
    ~Def() = delete;
```

The file's own top-of-file summary is a fair description of its contents:

*From `Def.hpp:1-8`:*
```cpp
/**
 * @file Def.hpp
 * @brief Global game constants, enumerations, and static helpers for the Speedy Blupi port.
 *
 * @details Contains the Def class, which aggregates compile-time integer constants for
 * sprite-sheet cell dimensions, viewport size, legacy channel identifiers, and the
 * Phase and ButtonGlyph enumerations that drive the game's state machine and UI overlay.
 */
```

`Def.hpp` pulls in five other small headers from the `WindowsPhoneSpeedyBlupi/def/` subdirectory
— `BlupiAction.hpp`, `Direction.hpp`, `SecretPower.hpp`, `KeyPressFlags.hpp`, and
`GameSpeed.hpp` — each of which defines its own `enum class`, covered in their own chapters
elsewhere in this book rather than here (`Def` itself only `#include`s them; it does not define
them). What `Def.hpp` defines directly is: two enums (`Phase`, `ButtonGlyph`), one static helper
function (`isNotOneOf`), nineteen `static constexpr intcs` integer constants, and two
`static constexpr bool` properties. This chapter catalogs every one of them.

## Phase: the top-level game-screen state

*From `Def.hpp:42-66`:*
```cpp
/**
 * @brief Represents the current high-level game phase (screen/mode).
 *
 * @details The game is always in exactly one Phase. Transitions are performed
 * by Game1::SetPhase(). The phase controls which UI buttons are drawn and
 * which update path is executed each frame.
 *
 * @note Status: Ported
 */
enum class Phase
{
    None,       ///< No phase active (initial / uninitialised state).
    First,      ///< Very first frame after startup.
    Wait,       ///< Waiting for an asynchronous operation to complete.
    Init,       ///< Main-menu / gamer-select screen.
    Play,       ///< Active gameplay.
    Pause,      ///< Game paused (pause overlay displayed).
    Lost,       ///< Player lost the current level.
    Win,        ///< Player completed the current level.
    Trial,      ///< Trial / demo mode — purchase prompt screen.
    MainSetup,  ///< Settings screen accessed from the main menu.
    PlaySetup,  ///< Settings screen accessed during gameplay.
    Resume,     ///< Resume-from-checkpoint confirmation screen.
    Ranking     ///< High-score / ranking screen.
};
```

`Def::Phase` is the game's single top-level state variable — thirteen named values covering
every screen the game can show, from the startup splash (`First`) through the main menu
(`Init`), active play (`Play`), pause overlay (`Pause`), win/loss screens (`Win`/`Lost`), the
trial-mode purchase prompt (`Trial`), two flavors of settings screen depending on where they were
opened from (`MainSetup` vs. `PlaySetup`), a resume confirmation (`Resume`), and the ranking/
high-score screen (`Ranking`). The doc comment states that transitions are centralized through
`Game1::SetPhase()` and that the current phase governs both which UI buttons are visible and
which per-frame update path runs — this state machine is the subject of
[Chapter 12](../part03-architecture/ch12-game1-state-machine.md), which should be consulted for how
transitions between these values actually occur; `Def.hpp` itself only declares the enum.

## ButtonGlyph: every on-screen button, by logical role

*From `Def.hpp:68-76`:*
```cpp
/**
 * @brief Identifies a specific on-screen button by its logical role.
 *
 * @details Each ButtonGlyph value corresponds to one interactive button that
 * can appear during a given Phase. The mapping from ButtonGlyph to on-screen
 * position and sprite is maintained in Game1's draw methods.
 *
 * @note Status: Ported
 */
enum class ButtonGlyph
{ /* 43 named values, see below */ };
```

`ButtonGlyph` has 43 values, one per interactive button the game can ever render, grouped
implicitly by which `Phase` they belong to: init-screen buttons (`InitGamerA/B/C`, `InitSetup`,
`InitPlay`, `InitBuy`, `InitRanking`), the win/lost screen's single `WinLostReturn`, trial-screen
buttons (`TrialBuy`, `TrialCancel`), settings-screen toggles (`SetupSounds`, `SetupJump`,
`SetupZoom`, `SetupAccel`, `SetupReset`, `SetupReturn`), pause-screen buttons (`PauseMenu`,
`PauseBack`, `PauseSetup`, `PauseRestart`, `PauseContinue`), the three always-visible in-play
touch controls (`PlayPause`, `PlayJump`, `PlayAction`, `PlayDown`), resume-screen buttons
(`ResumeMenu`, `ResumeContinue`), the ranking screen's `RankingContinue`, and finally thirteen
cheat-related values: six two-digit code buttons (`Cheat11`, `Cheat12`, `Cheat21`, `Cheat22`,
`Cheat31`, `Cheat32`) plus nine numbered action buttons (`Cheat1` through `Cheat9`) — reflecting
the cheat-entry UI documented in the codebase's own `documentation/Cheat System.md` and covered
in [Chapter 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md). `ButtonGlyph`
itself is only the *identity* of a button; the header's own doc comment is explicit that the
mapping from glyph to screen position and sprite lives in `Game1`'s draw methods, not here.

`ButtonGlyph` is used across four `.cpp` files: `Pixmap.cpp` (deciding which sprite/icon to draw
for a given glyph in `DrawInputButton`, `Pixmap.cpp:151` onward, with a `switch` over nearly every
value), `Game1.cpp` and `InputPad.cpp` (routing touch/click input to the currently-pressed
glyph), and `Decor.cpp` (tracking the currently-pressed button via the `ButtonPressed_` field and
mapping cheat glyphs to their display text in `GetCheatTinyText`, `Decor.cpp:1737`).

### isNotOneOf: a membership-test helper added during porting

*From `Def.hpp:125-145`:*
```cpp
/**
 * @brief Returns true if the specified glyph is not present in the given list.
 *
 * @details This is an additional helper not present in the original C# code.
 * Uses std::ranges::none_of for a clean O(n) membership test.
 *
 * @param[in] buttonGlyphToBeChecked Glyph to search for.
 * @param[in] buttonGlyphs Collection of glyphs to search within.
 * @return True if @p buttonGlyphToBeChecked is absent from @p buttonGlyphs; false otherwise.
 *
 * @note Additional
 */
static bool isNotOneOf(const ButtonGlyph& buttonGlyphToBeChecked,
                       std::initializer_list<ButtonGlyph> buttonGlyphs)
{
    return std::ranges::none_of(buttonGlyphs,
                                [&buttonGlyphToBeChecked](const ButtonGlyph candidate)
                                {
                                    return candidate == buttonGlyphToBeChecked;
                                });
}
```

The `@note Additional` tag (as opposed to `@note Status: Ported`) marks this as new code written
during the C++ port rather than a translation of existing C# logic — a small but explicit
distinction the codebase's documentation convention makes throughout. It is a thin wrapper over
`std::ranges::none_of`, returning `true` exactly when `buttonGlyphToBeChecked` matches none of the
glyphs in the `initializer_list`. Its one real call site is a negative-membership guard in
`InputPad.cpp`, checking whether the currently pressed button is anything *other than* the
"normal play" set of glyphs before running some further logic:

*From `InputPad.cpp:996-1005`:*
```cpp
if (
    Def::isNotOneOf(
        buttonGlyph, {
            Def::ButtonGlyph::None,
            Def::ButtonGlyph::PlayAction,
            Def::ButtonGlyph::Cheat11,
            Def::ButtonGlyph::Cheat12,
            Def::ButtonGlyph::Cheat21,
            Def::ButtonGlyph::Cheat22,
            Def::ButtonGlyph::Cheat31,
            /* … */
```

This reads naturally as "if the pressed button is none of these" — the kind of inline
allow-list check that would otherwise require a multi-clause `||` chain of `!=` comparisons.

## The dimensional constants

The bulk of `Def.hpp` is nineteen `static constexpr intcs` values (`intcs` being the
`SharpRuntime` 32-bit-integer typedef also used by `TinyPoint`/`TinyRect`), covering viewport
size, the tile grid, and the pixel dimensions of every sprite-sheet cell type in the game:

*From `Def.hpp:147-166`:*
```cpp
static constexpr intcs LXIMAGE = 640;     ///< Logical game viewport width in pixels.
static constexpr intcs LYIMAGE = 480;     ///< Logical game viewport height in pixels.
static constexpr intcs MAXCELX = 100;     ///< Maximum number of tile columns in a level.
static constexpr intcs MAXCELY = 100;     ///< Maximum number of tile rows in a level.
static constexpr intcs DIMOBJX = 64;      ///< Width of a moving-object sprite cell in pixels.
static constexpr intcs DIMOBJY = 64;      ///< Height of a moving-object sprite cell in pixels.
static constexpr intcs DIMBLUPIX = 60;    ///< Width of the Blupi character sprite cell in pixels.
static constexpr intcs DIMBLUPIY = 60;    ///< Height of the Blupi character sprite cell in pixels.
static constexpr intcs DIMEXPLOX = 128;   ///< Width of an explosion sprite cell in pixels.
static constexpr intcs DIMEXPLOY = 128;   ///< Height of an explosion sprite cell in pixels.
static constexpr intcs DIMBUTTONX = 40;   ///< Width of a UI button sprite cell in pixels.
static constexpr intcs DIMBUTTONY = 40;   ///< Height of a UI button sprite cell in pixels.
static constexpr intcs DIMJAUGEX = 124;   ///< Width of the HUD gauge sprite cell in pixels.
static constexpr intcs DIMJAUGEY = 22;    ///< Height of the HUD gauge sprite cell in pixels.
static constexpr intcs POSSTATX = 12;     ///< X position of the status display in HUD-space pixels.
static constexpr intcs POSSTATY = 220;    ///< Y position of the status display in HUD-space pixels.
static constexpr intcs DIMSTATX = 60;     ///< Width of the status display area in pixels.
static constexpr intcs DIMSTATY = 30;     ///< Height of the status display area in pixels.
static constexpr intcs DIMTEXTX = 32;     ///< Width of a single font glyph cell in pixels.
static constexpr intcs DIMTEXTY = 32;     ///< Height of a single font glyph cell in pixels.
```

`LXIMAGE`/`LYIMAGE` (640×480) is the logical game viewport — the design resolution the whole
UI/HUD layout is built around, scaled up or down for the actual device resolution elsewhere.
`MAXCELX`/`MAXCELY` (100×100) is the tile-grid size referenced throughout
[Chapter 16](../part04-decor-simulation/ch16-tile-map.md)'s coverage of `Decor::m_decor[][]`.
The six `DIM*X`/`DIM*Y` pairs after that (`DIMOBJ`, `DIMBLUPI`, `DIMEXPLO`, `DIMBUTTON`,
`DIMJAUGE`, `DIMTEXT`) each describe one sprite-sheet's per-icon cell size in pixels, and
`POSSTATX`/`POSSTATY` plus `DIMSTATX`/`DIMSTATY` describe the position and size of a HUD "status
display" area.

### Cross-checking the DIM* constants against real usage

`PLAN.md` (this book's own working plan) independently reverse-engineered the sprite-atlas grid
sizes directly from `Pixmap::DrawIcon`'s `switch (channel)` statement, and it is worth confirming
here, from the actual source, how these two independently-obtained sets of numbers relate. The
grid cell sizes assigned in that `switch` do match `Def`'s constants value-for-value — but they
are written as **raw integer literals**, not as references to `Def::DIMBLUPIX` etc.:

*From `Pixmap.cpp:552-610` (abridged):*
```cpp
case PixmapChannel::Blupi:
    /* … */
    dstIconWidth  = 60;
    dstIconHeight = 60;
    /* … */
case PixmapChannel::Object:
    /* … */
    dstIconWidth  = 64;
    dstIconHeight = 64;
    /* … */
case PixmapChannel::Text:
    /* … */
    dstIconWidth  = 32;
    dstIconHeight = 32;
    /* … */
case PixmapChannel::Button:
    /* … */
    dstIconWidth  = 40;
    dstIconHeight = 40;
```

The values `60`, `64`, `32`, `40` are exactly `Def::DIMBLUPIX`, `Def::DIMOBJX`, `Def::DIMTEXTX`,
and `Def::DIMBUTTONX` respectively — but `Pixmap.cpp` never writes `Def::DIMBLUPIX`; it
duplicates the number as a literal. The same pattern holds for the HUD gauge: `Jauge::Create`
sets its own dimension field directly, again with a literal rather than a reference to `Def`:

*From `Jauge.cpp:46-47`:*
```cpp
m_dim.X = 124;
m_dim.Y = 22;
```

`124` and `22` are exactly `Def::DIMJAUGEX` and `Def::DIMJAUGEY`. A codebase-wide search
(`grep -rn "Def::DIM" src include`, restricted to files other than `Def.hpp` itself) confirms
this pattern holds everywhere: **not one of the nineteen `DIM*`/`POSSTAT*`/`LXIMAGE`/`LYIMAGE`/
`MAXCEL*` constants is ever referenced by name (`Def::DIMOBJX`, etc.) outside `Def.hpp` itself.**
`MAXCELX`/`MAXCELY` fare slightly better — they at least appear in `Decor.hpp`'s own Doxygen
prose describing the tile-coordinate range (`Decor.hpp:16`, `67`) — but the actual tile-grid code
in `Decor.cpp` still indexes its 100×100 array using the bare literal `100`, not
`Def::MAXCELX`/`Def::MAXCELY`.

This is a genuine, source-confirmed finding rather than a stylistic quibble: **`Def.hpp`'s
dimensional constants function today more as a documented reference table than as values the
rest of the code actually reads.** The numbers they hold are correct and match real sprite/HUD
dimensions exactly — but the sprite-drawing code in `Pixmap.cpp` and the HUD code in `Jauge.cpp`
each independently hard-code the same numbers rather than including and referencing `Def`. Anyone
changing a sprite-sheet cell size (say, re-exporting `blupi.png` at a different resolution) would
need to update both the literal in `Pixmap.cpp`'s `switch` *and* the corresponding `Def::DIM*`
constant to keep the two in sync — `Def.hpp` alone does not enforce this. This mirrors exactly
the sprite-atlas grid table this book's `PLAN.md` built directly from `Pixmap.cpp` (see
[Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md)) — the two sources of
truth agree on the numbers, but only one of them (`Pixmap.cpp`) is actually load-bearing at
runtime.

## The legacy channel-index constants

*From `Def.hpp:168-183`:*
```cpp
//TODO: These values exist in the enum class PixmapChannel
static constexpr intcs CHOBJECT = 1;         ///< Channel index for the moving-objects sprite sheet.
static constexpr intcs CHBLUPI = 2;          ///< Channel index for the main Blupi sprite sheet.
static constexpr intcs CHDECOR = 3;          ///< Channel index for the background/decor sprite sheet.
static constexpr intcs CHBUTTON = 4;         ///< Channel index for the UI buttons sprite sheet.
static constexpr intcs CHJAUGE = 5;          ///< Channel index for the HUD gauge sprite sheet.
static constexpr intcs CHTEXT = 6;           ///< Channel index for the font/text glyph sprite sheet.
static constexpr intcs CHEXPLO = 9;          ///< Channel index for the explosion sprite sheet.
static constexpr intcs CHELEMENT = 10;       ///< Channel index for the collectible elements sprite sheet.
static constexpr intcs CHBLUPI1 = 11;        ///< Channel index for alternate Blupi variant 1.
static constexpr intcs CHBLUPI2 = 12;        ///< Channel index for alternate Blupi variant 2.
static constexpr intcs CHBLUPI3 = 13;        ///< Channel index for alternate Blupi variant 3.
static constexpr intcs CHPAD = 14;           ///< Channel index for the touch-input pad overlay.
static constexpr intcs CHSPEEDYBLUPI = 15;   ///< Channel index for the Speedy Blupi title background.
static constexpr intcs CHBLUPIYOUPIE = 16;   ///< Channel index for the Blupi Youpie background.
static constexpr intcs CHGEAR = 17;          ///< Channel index for the gear/settings background.
```

The author's own `//TODO` comment immediately above this block is the important context: these
fourteen `CH*` integer constants (numbered 1 through 17, with gaps at 7 and 8) are explicitly
flagged as **duplicating** information that already exists as a proper `enum class PixmapChannel`
elsewhere in the codebase (covered in [Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md)).
A codebase-wide search confirms these particular `Def::CH*` names are not referenced anywhere
outside `Def.hpp` — `Pixmap.cpp` and `Decor.cpp` address sprite channels exclusively through
`PixmapChannel::Blupi`, `PixmapChannel::Object`, and so on (e.g. `Pixmap.cpp:151`'s
`Def::ButtonGlyph glyph` parameter sits alongside `case PixmapChannel::Blupi:`-style code
elsewhere in the same file). These constants read as a leftover, likely dating to an earlier,
non-enum-based version of the channel system, kept around — per the `//TODO` — as a known,
not-yet-cleaned-up duplication rather than as active, load-bearing code.

## The two boolean properties

*From `Def.hpp:185-213`:*
```cpp
/**
 * @brief Gets the HasSound property value.
 *
 * @details Corresponds to the original C# static read-only property HasSound.
 * Always returns true; the port assumes audio hardware is present.
 *
 * @return Always true.
 *
 * @note Status: Ported
 */
static constexpr bool getHasSoundProperty()
{
    return true;
}

/**
 * @brief Gets the EasyMove property value.
 *
 * @details Corresponds to the original C# static read-only property EasyMove.
 * Always returns true; the port uses the simplified movement model.
 *
 * @return Always true.
 *
 * @note Status: Ported
 */
static constexpr bool getEasyMoveProperty()
{
    return true;
}
```

Both are ports of C# read-only properties that, in the original codebase, presumably could vary
(e.g. `HasSound` gating on detected audio hardware, `EasyMove` selecting between two movement
models). In this C++ port both are hard-coded `constexpr` functions that always return `true` —
they are not platform- or configuration-gated in any way, they simply always evaluate to the same
compile-time constant.

`getHasSoundProperty()` has one real call site, in `Sound::LoadContent()`:

*From `Sound.cpp:137-140`:*
```cpp
if (!Def::getHasSoundProperty())
{
    return;
}
```

This book's own audio-issue analysis (`AUDIO_ANALYSIS.md`, covered in
[Chapter 40](../part06-audio/ch40-audio-issue-analysis.md)) independently investigated and
explicitly **ruled out** this function as a cause of any platform-specific audio problems,
precisely because it is a `constexpr` that always returns `true`: "`Def::getHasSoundProperty()`
(`Def.hpp:195`) is a `constexpr` always returning `true` — not platform-gated, so it cannot
selectively disable audio on one platform." Reading the actual source confirms that conclusion:
the guard in `Sound::LoadContent()` can never actually trigger an early return.

`getEasyMoveProperty()` has two call sites, both in `Decor.cpp`, gating parts of Blupi's vertical
movement/jump physics:

*From `Decor.cpp:3724`:*
```cpp
if (Def::getEasyMoveProperty())
{
    if (m_blupiSpeedY <= -1.0 || ((unsigned int)m_keyPress & ToRaw(KeyPressFlags::Jump)) != 0)
    {
        if (m_blupiVitesseY > -7.0)
        {
            m_blupiVitesseY -= 0.5;
```

Because the function always returns `true`, this `if` never takes its (absent) `else` branch in
practice — the "easy move" physics path is unconditionally the active one, and any alternate
non-easy-move code path that might once have existed alongside it in the original C# is not
present in this file at either of the two call sites. Both `getHasSoundProperty` and
`getEasyMoveProperty` are, in effect, always-on feature flags whose "off" state is dead code by
construction of `constexpr` always returning `true` — a fact confirmed by the two headers'
identical wording ("Always returns true...") and validated against real call sites.

## Summary table

| Category | Members |
|---|---|
| Enums | `Phase` (13 values), `ButtonGlyph` (43 values) |
| Helper function | `isNotOneOf(glyph, {…})` — added during porting, not in original C# |
| Viewport/grid constants | `LXIMAGE`=640, `LYIMAGE`=480, `MAXCELX`=100, `MAXCELY`=100 |
| Sprite-cell dimensions | `DIMOBJX/Y`=64, `DIMBLUPIX/Y`=60, `DIMEXPLOX/Y`=128, `DIMBUTTONX/Y`=40, `DIMJAUGEX`=124/`DIMJAUGEY`=22, `DIMTEXTX/Y`=32 |
| HUD status position/size | `POSSTATX`=12, `POSSTATY`=220, `DIMSTATX`=60, `DIMSTATY`=30 |
| Legacy channel indices | `CHOBJECT`..`CHGEAR` (14 constants) — flagged `//TODO` as duplicating `PixmapChannel` |
| Boolean feature flags | `getHasSoundProperty()`, `getEasyMoveProperty()` — both always `true` |

## See also

- [Chapter 29: The Sprite Atlas System](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md) —
  the real, load-bearing grid-size logic in `Pixmap::DrawIcon`/`GetSrcRectangle` that
  independently matches `Def`'s `DIM*` constants value-for-value without referencing them by
  name, plus the `PixmapChannel` enum that duplicates `Def`'s legacy `CH*` constants.
- [Chapter 16: The Tile Map](../part04-decor-simulation/ch16-tile-map.md) — the 100×100 tile grid
  described by `Def::MAXCELX`/`Def::MAXCELY`.
- [Chapter 36: Jauge — HUD Gauges](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md) —
  where `Def::DIMJAUGEX`/`Def::DIMJAUGEY`'s values (124×22) reappear as hard-coded literals in
  `Jauge::Create`.
- [Chapter 40: Audio Issue Analysis](../part06-audio/ch40-audio-issue-analysis.md) — where
  `Def::getHasSoundProperty()` was independently ruled out as a source of platform-specific audio
  bugs.
- [Chapter 12: Game1 — the State Machine](../part03-architecture/ch12-game1-state-machine.md) —
  where `Def::Phase` transitions are actually driven, via `Game1::SetPhase()`.
- [Chapter 48: Misc — Utility Functions](ch48-misc-utility-functions.md) — the sibling static
  utility class covering geometry rather than constants/enums.
