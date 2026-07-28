# Chapter 23: Secret Powers and the Cheat System

## Overview

`Decor` tracks exactly one "special power" bonus for the player at a time — the `SecretPower`
enum — and, layered on top of ordinary gameplay, an entire parallel debug/cheat subsystem that can
mutate almost any piece of Blupi's state on demand. The two are related but distinct: `SecretPower`
is gameplay content (something a player earns by picking up an item in a level), while the cheat
system is a set of developer/debug hooks that happen to reuse some of the same underlying booleans
(`m_blupiShield`, `m_blupiPower`, `m_blupiCloud`, `m_blupiHide`) plus a much larger set of
vehicle-mode and item-count fields that have nothing to do with `SecretPower` at all.

This chapter documents both, and — per this book's methodology — cross-checks the repository's own
`documentation/Cheat System.md` against the real implementation rather than simply repeating it.
The short version of that cross-check: the document is accurate as far as it goes, but it describes
only the older of *two* independent cheat-activation paths that exist in the current source, and it
omits two `CheatCodes` values that the enum defines but that `Decor::CheatAction` never actually
implements.

## `SecretPower`: the four gameplay bonuses

*From `include/WindowsPhoneSpeedyBlupi/def/SecretPower.hpp:30-37`:*

```cpp
enum class SecretPower : SharpRuntime::ushortcs
{
    None   = 0,      ///< @brief No special power active.
    Shield = 1,      ///< @brief Temporary invincibility shield (SEC_SHIELD).
    Power  = 2,      ///< @brief Enhanced strength/power bonus (SEC_POWER).
    Cloud  = 3,      ///< @brief Cloud/floating bonus (SEC_CLOUD).
    Hide   = 4       ///< @brief Invisibility bonus (SEC_HIDE).
};
```

The comment `SEC_SHIELD`/`SEC_POWER`/`SEC_CLOUD`/`SEC_HIDE` names the original C# integer constants
this enum replaces — a naming convention this book has seen before wherever a `.hpp` in `def/`
documents its origin as a straight port of `#define`-style constants.

`Decor` stores the *currently active* power in `m_blupiSec` (`Decor.hpp:319`), but that field is
not the primary gameplay state — it is a **per-frame rendering flag**, recomputed at the top of
each `Build()` call and consumed immediately by the drawing code that follows it in the same
function:

*From `Decor.cpp:769` (inside `Build()`):*

```cpp
m_blupiSec = SecretPower::None;
if (!m_blupiFront)
{
    ...
    if (m_blupiShield)
    {
        m_blupiSec = SecretPower::Shield;
        ...
    }
    else if (m_blupiPower)
    {
        m_blupiSec = SecretPower::Power;
        ...
    }
    else if (m_blupiCloud)
    {
        m_blupiSec = SecretPower::Cloud;
        ...
    }
    else if (m_blupiHide)
    {
        m_blupiSec = SecretPower::Hide;
        ...
    }
```

The actual gameplay state that persists frame to frame is the quartet of independent booleans
`m_blupiShield`, `m_blupiPower`, `m_blupiCloud`, `m_blupiHide` (`Decor.hpp:367-376`), each
documented individually:

*From `Decor.hpp:366-377`:*

```cpp
/** True when the Shield secret power is active (temporary invincibility). */
bool m_blupiShield;

/** True when the Power secret power is active (enhanced strength). */
bool m_blupiPower;

/** True when the Cloud secret power is active (float/levitation). */
bool m_blupiCloud;

/** True when the Hide secret power is active (invisibility). */
bool m_blupiHide;
```

`SecretPower` itself has no bitmask combination logic and no setter method on `Decor` — the four
booleans are the real store, and `SecretPower` exists purely as a small enum vocabulary that
`m_blupiSec` and the rendering code use to talk about "which one, if any, is active" without a
`switch` on four raw booleans. `m_blupiTimeShield` (`Decor.hpp:429`) is the frame countdown that
eventually turns `m_blupiShield` back off; see the `RoundShield` cheat below for where it is set.

Each power gates real collision and capability behavior elsewhere in `Decor.cpp` (shield
invincibility against hazards, cloud levitation physics, hide's reduced enemy-detection radius);
those effects are covered where they belong, alongside the rest of Blupi's physics, in
[Chapter 21](ch21-physics-and-collision.md) and [Chapter 20](ch20-enemy-and-creature-ai.md). This
chapter's job is the power *as data* and the cheat system that can toggle it out of turn.

## Two independent cheat-activation paths

`documentation/Cheat System.md` describes a single path — the nine on-screen `Cheat1`–`Cheat9`
buttons — as if it were the whole system. Reading `InputPad.cpp` shows a **second, larger** cheat
surface that the document does not mention at all: a typed-text cheat-code detector, available only
in `MODERN` builds, that accumulates keystrokes and matches them against cheat *names* (not button
positions).

### Path 1 — the nine UI buttons (`Cheat1`–`Cheat9`)

This is the path the documentation describes, and it checks out exactly as written. `Game1.hpp`
defines a ten-step gesture over six *menu* glyphs (`Cheat11`, `Cheat12`, `Cheat21`, `Cheat22`,
`Cheat31`, `Cheat32`) that unlocks the cheat button panel:

*From `Game1.hpp:123-134`:*

```cpp
static constexpr Def::ButtonGlyph cheatGeste[cheatGesteLength] =
{
    Def::ButtonGlyph::Cheat12,
    Def::ButtonGlyph::Cheat22,
    Def::ButtonGlyph::Cheat32,
    Def::ButtonGlyph::Cheat12,
    Def::ButtonGlyph::Cheat11,
    Def::ButtonGlyph::Cheat21,
    Def::ButtonGlyph::Cheat22,
    Def::ButtonGlyph::Cheat21,
    Def::ButtonGlyph::Cheat31,
    Def::ButtonGlyph::Cheat32
};
```

This matches the documentation's claimed sequence (`Cheat12, Cheat22, Cheat32, Cheat12, Cheat11,
Cheat21, Cheat22, Cheat21, Cheat31, Cheat32`) exactly, value for value. `Game1::Update()` tracks
progress through the sequence with `cheatGesteIndex`, resetting to zero on any wrong press, and
flips `inputPad`'s `ShowCheatMenu` property true once all ten are matched in order:

*From `Game1.cpp:363-382`:*

```cpp
case Def::ButtonGlyph::Cheat11:
case Def::ButtonGlyph::Cheat12:
case Def::ButtonGlyph::Cheat21:
case Def::ButtonGlyph::Cheat22:
case Def::ButtonGlyph::Cheat31:
case Def::ButtonGlyph::Cheat32:
    if (buttonPressed == cheatGeste[cheatGesteIndex])
    {
        cheatGesteIndex++;
        if (cheatGesteIndex == cheatGesteLength)
        {
            cheatGesteIndex = 0;
            inputPad.setShowCheatMenuProperty(true);
        }
    }
    else
    {
        cheatGesteIndex = 0;
    }
    break;
```

Once the panel is visible, the nine `Cheat1`–`Cheat9` buttons each map to one `Tables::CheatCodes`
value via `Game1::CheatAction(Def::ButtonGlyph)`:

*From `Game1.cpp:491-523`:*

```cpp
void Game1::CheatAction(Def::ButtonGlyph glyph)
{
    switch (glyph)
    {
    case Def::ButtonGlyph::Cheat1:
        decor.CheatAction(Tables::CheatCodes::OpenDoors);
        break;
    case Def::ButtonGlyph::Cheat2:
        decor.CheatAction(Tables::CheatCodes::SuperBlupi);
        break;
    case Def::ButtonGlyph::Cheat3:
        decor.CheatAction(Tables::CheatCodes::ShowSecret);
        break;
    case Def::ButtonGlyph::Cheat4:
        decor.CheatAction(Tables::CheatCodes::LayEgg);
        break;
    case Def::ButtonGlyph::Cheat5:
        gameData.Reset();
        break;
    case Def::ButtonGlyph::Cheat6:
        simulateTrialMode = !simulateTrialMode;
        break;
    case Def::ButtonGlyph::Cheat7:
        decor.CheatAction(Tables::CheatCodes::CleanAll);
        break;
    case Def::ButtonGlyph::Cheat8:
        decor.CheatAction(Tables::CheatCodes::AllTreasure);
        break;
    case Def::ButtonGlyph::Cheat9:
        decor.CheatAction(Tables::CheatCodes::EndGoal);
        break;
    }
}
```

Two of the nine (`Cheat5` = reset save data, `Cheat6` = toggle trial-mode simulation) never call
`Decor::CheatAction` at all — they act directly on `Game1`'s own `gameData`/`simulateTrialMode`
fields. This matches the documentation's table exactly, including labeling `Cheat5` as "Reset" and
`Cheat6` as "TrialMode".

The one-or-two-letter button labels the documentation quotes (`D, B, S, E, R, T, C, T, G`) come
from `Decor::GetCheatTinyText`, a static method with no dependency on `Decor` instance state:

*From `Decor.cpp:1737-1762`:*

```cpp
string Decor::GetCheatTinyText(Def::ButtonGlyph glyph)
{
    switch (glyph)
    {
    case Def::ButtonGlyph::Cheat1:
        return "D";
    case Def::ButtonGlyph::Cheat2:
        return "B";
    case Def::ButtonGlyph::Cheat3:
        return "S";
    case Def::ButtonGlyph::Cheat4:
        return "E";
    case Def::ButtonGlyph::Cheat5:
        return "R";
    case Def::ButtonGlyph::Cheat6:
        return "T";
    case Def::ButtonGlyph::Cheat7:
        return "C";
    case Def::ButtonGlyph::Cheat8:
        return "T";
    case Def::ButtonGlyph::Cheat9:
        return "G";
    default:
        return "";
    }
}
```

`Pixmap::DrawButton` is where these labels actually reach the screen — it draws the shared "blank
cheat button" background icon (`PixmapChannel::Pad`, icon 0) for all nine glyphs, then centers the
`GetCheatTinyText` string on top:

*From `Pixmap.cpp:223-247`:*

```cpp
case Def::ButtonGlyph::Cheat1:
case Def::ButtonGlyph::Cheat2:
case Def::ButtonGlyph::Cheat3:
case Def::ButtonGlyph::Cheat4:
case Def::ButtonGlyph::Cheat5:
case Def::ButtonGlyph::Cheat6:
case Def::ButtonGlyph::Cheat7:
case Def::ButtonGlyph::Cheat8:
case Def::ButtonGlyph::Cheat9:
    {
        DrawIcon(PixmapChannel::Pad, 0, rect, pressed ? 0.6 : 1.0, false);
        TinyPoint tinyPoint{
            rect.Left + rect.getWidthProperty() / 2 - static_cast<intcs>(originX),
            rect.Top + 28
        };
        Text::DrawTextCenter(*this, tinyPoint, Decor::GetCheatTinyText(glyph), 1.0);
        break;
    }
case Def::ButtonGlyph::Cheat11:
case Def::ButtonGlyph::Cheat12:
case Def::ButtonGlyph::Cheat21:
case Def::ButtonGlyph::Cheat22:
case Def::ButtonGlyph::Cheat31:
case Def::ButtonGlyph::Cheat32:
    break;
```

Notably, the six gesture-unlock glyphs (`Cheat11`–`Cheat32`) draw nothing at all — an empty `case`
block with no `DrawIcon` call. The six-button unlock grid is genuinely invisible during normal
play; a player has to already know its screen position (or find it by trial and error) to enter the
gesture. This is consistent with the documentation's framing of the gesture as a hidden unlock, but
the documentation doesn't mention that the trigger buttons render as nothing — worth stating
explicitly for anyone trying to reproduce this from the visuals alone.

### Path 2 — typed cheat-code names (undocumented, `MODERN`-only)

`documentation/Cheat System.md` says nothing about this path, but it is a large, deliberately
engineered feature in `InputPad.cpp`: while the game is in `Def::Phase::Play`, every letter key
press is appended to a rolling 32-character buffer, and after each keystroke the buffer's *suffix*
is compared against a table of cheat-code name strings:

*From `InputPad.cpp:686-746`:*

```cpp
// Typed cheat code detection: accumulate letters typed during Play phase.
// When the accumulated string matches a known cheat code name, activate it.
if (getPhaseProperty() == Def::Phase::Play)
{
    static const Keys letterKeys[26] = { /* A..Z */ };
    for (int li = 0; li < 26; li++)
    {
        bool down = IsKeyDownOrVirtual(letterKeys[li]);
        if (down && !letterPrev[li])
        {
            typedCheatBuffer += static_cast<char>('a' + li);
            if (typedCheatBuffer.size() > 32)
            {
                typedCheatBuffer = typedCheatBuffer.substr(typedCheatBuffer.size() - 32);
            }
            struct CheatEntry
            {
                const char* name;
                Tables::CheatCodes code;
                bool persistent;
            };
            static const CheatEntry cheatEntries[] = {
                { "buildofficialmissions", Tables::CheatCodes::BuildOfficialMissions, true  },
                { "opendoors",             Tables::CheatCodes::OpenDoors,             true },
                { "cleanall",              Tables::CheatCodes::CleanAll,              false },
                { "megablupi",             Tables::CheatCodes::SuperBlupi,            true  },
                { "layegg",                Tables::CheatCodes::LayEgg,                false },
                { "killegg",               Tables::CheatCodes::KillEgg,               false },
                { "funskate",              Tables::CheatCodes::Skate,                 false },
                { "givecopter",            Tables::CheatCodes::Copter,                false },
                { "jeepdrive",             Tables::CheatCodes::Jeep,                  false },
                { "alltreasure",           Tables::CheatCodes::AllTreasure,           false },
                { "endgoal",               Tables::CheatCodes::EndGoal,               false },
                { "showsecret",            Tables::CheatCodes::ShowSecret,            true },
                { "roundshield",           Tables::CheatCodes::RoundShield,           false },
                { "quicklollypop",         Tables::CheatCodes::Lollipop,              false },
                { "tenbombs",              Tables::CheatCodes::Bombs,                 false },
                { "birdlime",              Tables::CheatCodes::BirdLime,              false },
                { "drivetank",             Tables::CheatCodes::Tank,                  false },
                { "powercharge",           Tables::CheatCodes::PowerCharge,           false },
                { "hidedrink",             Tables::CheatCodes::Drink,                 false },
                { "iovercraft",            Tables::CheatCodes::Overcraft,             false },
                { "udynamite",             Tables::CheatCodes::Dynamite,              false },
                { "weelkeys",              Tables::CheatCodes::WeelKeys,              false },
#ifdef MODERN
                { "quick",  Tables::CheatCodes::Quick,  true },
                { "ghost",  Tables::CheatCodes::Ghost,  false },
                { "debug",  Tables::CheatCodes::Debug,  true },
                { "zoom",   Tables::CheatCodes::Zoom,   false },
                { "cheats", Tables::CheatCodes::Cheats, false },
#endif
            };
            ...
```

The name strings are deliberately *not* the enum member names — `SuperBlupi` types as
`"megablupi"`, `Skate` types as `"funskate"`, `Lollipop` types as `"quicklollypop"`, and so on —
which reads as an intentional light obfuscation so the cheat words aren't trivially guessable from
the source's own enum names. Each entry also carries a `persistent` flag: persistent cheats
(`buildofficialmissions`, `opendoors`, `megablupi`, `showsecret`, and the `MODERN`-only `quick` and
`debug`) are tracked in an `activePersistentCheats` list (shown in a HUD overlay elsewhere in
`InputPad.cpp`), while the rest are one-shot triggers with no persistent-state bookkeeping beyond
whatever `Decor::CheatAction` itself changes.

Three of these typed codes (`Quick`, `Debug`, `Zoom`, `Cheats`, all `MODERN`-only, plus a special
case for `Ghost`) are **intercepted before reaching `Decor::CheatAction`** and handled entirely
inside `InputPad.cpp` — `Quick` toggles a local `quick_cheat_enabled` flag and adjusts
`Game1::SetGameSpeed`, `Zoom` cycles `Decor::SetCheatZoom` (see [Chapter 25](ch25-game-speed-and-zoom.md)),
`Debug` and `Cheats` toggle local overlay-display flags. Every other typed cheat name falls through
to the same `decor->CheatAction(cheatEntries[ci].code)` call the UI buttons use — confirming that,
despite the two very different *input* mechanisms, there really is only one *execution* path,
`Decor::CheatAction`, once a cheat has been identified. One more piece of cross-wiring worth noting:
typing `opendoors` also implicitly triggers `WeelKeys` (all keys) in the same keystroke:

*From `InputPad.cpp:838-841`:*

```cpp
if (cheatEntries[ci].code == Tables::CheatCodes::OpenDoors)
{
    decor->CheatAction(Tables::CheatCodes::WeelKeys);
}
```

The nine-button UI path has no equivalent — pressing `Cheat1` (`OpenDoors`) does **not** also grant
keys. This asymmetry exists only in the typed path.

## `Tables::CheatCodes`: the complete enum, and what actually implements it

*From `Tables.hpp:79-112`:*

```cpp
enum class CheatCodes
{
    BuildOfficialMissions, ///< Toggle official mission builder mode.
    OpenDoors,             ///< Open all doors in the current level.
    CleanAll,              ///< Remove all objects from the level.
    SuperBlupi,            ///< Enable Super Blupi enhanced mode.
    LayEgg,                ///< Place an egg in front of Blupi.
    KillEgg,               ///< Remove the nearest egg.
    Skate,                 ///< Give Blupi the skateboard.
    Copter,                ///< Give Blupi the helicopter.
    Jeep,                  ///< Give Blupi the jeep.
    AllTreasure,           ///< Collect all treasures instantly.
    EndGoal,               ///< Trigger the level win condition.
    ShowSecret,            ///< Reveal secret paths.
    RoundShield,           ///< Activate the Shield power-up.
    Lollipop,              ///< Activate the lollipop power-up.
    Bombs,                 ///< Give Blupi a supply of dynamite.
    BirdLime,              ///< Activate bird-lime/glue effect.
    Tank,                  ///< Give Blupi the tank vehicle.
    PowerCharge,           ///< Activate the Power charge.
    Drink,                 ///< Trigger the drink animation.
    Overcraft,             ///< Give Blupi the overcraft.
    Dynamite,              ///< Give Blupi extra dynamite.
    WeelKeys               ///< Give Blupi a set of keys.
#ifndef LEGACY
    ,Quick                 ///< The game speed can be switched to 2x, 4x or 8x
#endif
#ifdef MODERN
    ,Ghost                 ///< Ghost mode: semi-transparent, free flight, no interactions.
    ,Debug                 ///< Debug overlay: shows runtime state in top-right corner.
    ,Zoom                  ///< Zoom cheat: cycles through zoom-out levels (100%, 25%, 50%).
    ,Cheats                ///< Cheats overlay: shows list of all cheats for 5 seconds.
#endif
};
```

The documentation's "Complete List of Cheat Codes" section reproduces the base 22 entries (minus
the conditional `Quick`/`Ghost`/`Debug`/`Zoom`/`Cheats` additions, which postdate that document) and
adds the disclaimer: *"Only a subset of these cheats is exposed through the UI (Cheat1–Cheat9).
However, all of them can be triggered programmatically via `Decor::CheatAction`."* Reading
`Decor::CheatAction` in full (`Decor.cpp:1774-2096`) shows this second sentence is **not quite
true**: two members of the enum — `BuildOfficialMissions` and `KillEgg` — have no corresponding
`if (cheat == Tables::CheatCodes::...)` branch anywhere in the method. Calling
`decor.CheatAction(Tables::CheatCodes::KillEgg)` or
`decor.CheatAction(Tables::CheatCodes::BuildOfficialMissions)` compiles, runs, and does *nothing* —
the whole body of `CheatAction` is a flat sequence of `if` statements with no `default`/`else`
fallback, so an unhandled value simply falls through every check and returns. This is true whether
the call originates from the typed-cheat table (which does list both names, `"buildofficialmissions"`
and `"killegg"`) or from hypothetical new code.

`BuildOfficialMissions` looks at first like it *should* map to `Decor::SetBuildOfficialMissions(bool)`
(`Decor.cpp:2098-2101`), a private setter for the `m_buildOfficialMissions` flag described in
[Chapter 24](ch24-missions-and-continuemission.md). But grepping the entire `mobile-eggbert` source
tree shows `SetBuildOfficialMissions` has exactly one caller: none. It is set to `false` once, in
`Decor`'s initializer (`Decor.cpp:213`), and its setter is never invoked from `CheatAction`,
`Game1`, or anywhere else. `m_buildOfficialMissions` itself is likewise never read anywhere in
`Decor.cpp`. The field, its setter, and the `BuildOfficialMissions` cheat code together form a
completely dead code path in the current state of the repository — present in the enum and in the
typed-cheat lookup table (so a player *can* type `"buildofficialmissions"` and see
`INPUT_DEBUG`/persistent-cheat bookkeeping fire in `InputPad.cpp`), but with no observable gameplay
effect once `Decor::CheatAction` is reached. This is a concrete instance of the "doc is
incomplete/stale relative to the real implementation" gap this chapter was asked to look for: the
documentation's confident "all of them can be triggered" claim does not hold for these two values.

## `Decor::CheatAction` cheat by cheat

`Decor::CheatAction` (`Decor.cpp:1774-2096`) is one long sequence of independent `if` blocks, one
per handled `CheatCodes` value — not a `switch`, so nothing prevents (and nothing in the current
code exploits) triggering more than one cheat's block in a single call were a caller to somehow
match two conditions, though in practice each call passes exactly one enum value and only one
branch's condition can be true at a time. The table below documents every branch that exists in the
method, with its exact effect:

| `CheatCodes` value | Real effect (`Decor::CheatAction`) | Citation |
|---|---|---|
| `OpenDoors` | Toggles `m_bCheatDoors`, then calls `AdaptDoors(m_bPrivate)` to re-evaluate every door against the new flag. | `Decor.cpp:1776-1780` |
| `ShowSecret` | Toggles `m_bDrawSecret` (controls whether hidden-object icon 214 renders — see [Chapter 26](ch26-tile-and-icon-catalog.md)). | `Decor.cpp:1781-1784` |
| `SuperBlupi` | Toggles `m_bSuperBlupi`. | `Decor.cpp:1785-1788` |
| `LayEgg` | Sets `m_nbVies = 9` (see [Chapter 24](ch24-missions-and-continuemission.md) on why this is "lives", not literally an egg). | `Decor.cpp:1789-1792` |
| `CleanAll` | For every pool slot whose `ObjectType` is one of a fixed list of enemy/hazard types (`ObjectType2/3/4/16/17/20/32/33/44/54/96/97`), converts it in place into an explosion (`ObjectType8`), triggers a small screen shake (`DecorAction::SmallShake`), and plays `SoundChannel10`. | `Decor.cpp:1793-1823` |
| `Skate` | Clears every other vehicle/mode flag (`m_blupiHelico`, `m_blupiOver`, `m_blupiJeep`, `m_blupiTank`, `m_blupiNage`, `m_blupiSurf`, `m_blupiVent`, `m_blupiSuspend`, `m_blupiAir`), sets `m_blupiSkate = true`, and stops the helicopter/jeep/tank motor loop sounds (`SoundChannel16/18/29/31`). | `Decor.cpp:1824-1840` |
| `Copter` | Same mutual-exclusion pattern, sets `m_blupiHelico = true`. | `Decor.cpp:1841-1853` |
| `Jeep` | Same pattern, sets `m_blupiJeep = true`; additionally clears `m_blupiCloud`/`m_blupiHide` (the two `SecretPower` flags that would otherwise visually conflict with the jeep sprite). | `Decor.cpp:1854-1868` |
| `AllTreasure` | For every pool slot of type `ObjectType5` (an uncollected treasure), converts it to `ObjectType0` (inert/removed), increments `m_nbTresor`, calls `OpenDoorsTresor()` (opens any door whose treasure requirement is now met — see [Chapter 22](ch22-doors-keys-doorkeyflags.md)), and plays `SoundChannel11`. | `Decor.cpp:1869-1881` |
| `EndGoal` | For every pool slot of type `ObjectType7` or `ObjectType21` (a level-exit marker), teleports Blupi's position to it; if `m_nbTresor >= m_totalTresor` it plays the win sequence directly (`BlupiAction::Win`, stops vehicle sounds, plays `SoundChannel14`, clears every mode/power flag) — otherwise it just plays a "not yet" sound (`SoundChannel13`). Sets `m_goalPhase = 50` either way. | `Decor.cpp:1882-1929` |
| `RoundShield` | Sets `m_blupiShield = true`, clears the other three `SecretPower` booleans, sets `m_blupiTimeShield = 100`, snapshots `m_blupiPosMagic`, unhides the second HUD gauge (`m_jauges[1]`), plays `SoundChannel42`. | `Decor.cpp:1931-1941` |
| `Lollipop` | Sets `m_blupiAction = BlupiAction::Sucette` and clears every vehicle/power flag plus `m_blupiFocus`; plays `SoundChannel50`. | `Decor.cpp:1942-1957` |
| `Bombs` | Sets `m_blupiPerso = 10` (a following-NPC/persona slot reused as a bomb-supply counter) and plays `SoundChannel60`. | `Decor.cpp:1958-1962` |
| `BirdLime` | Sets `m_blupiBullet = 10`. | `Decor.cpp:1963-1966` |
| `Tank` | Same mutual-exclusion pattern as `Skate`/`Copter`/`Jeep`, sets `m_blupiTank = true`; also clears `m_blupiCloud`/`m_blupiHide`, and — only when the build's `Config::FPS` is not exactly the original 20 — zeroes `m_blupiVitesseY`/`m_blupiSubPixelY` to avoid a residual sub-frame vertical velocity carried over from before the mode switch. | `Decor.cpp:1967-1986` |
| `PowerCharge` | Sets `m_blupiAction = BlupiAction::Charge`, clears vehicle/power flags and `m_blupiJumpAie`/`m_blupiFocus`, plays `SoundChannel58`. | `Decor.cpp:1987-2003` |
| `Drink` | Sets `m_blupiAction = BlupiAction::Drink`, same flag-clearing pattern as `PowerCharge`, plays `SoundChannel57`. | `Decor.cpp:2004-2020` |
| `Overcraft` | Same mutual-exclusion pattern, sets `m_blupiOver = true`. | `Decor.cpp:2021-2033` |
| `Dynamite` | Sets `m_blupiDynamite = 1` and plays `SoundChannel60` (the same channel as `Bombs`). | `Decor.cpp:2034-2038` |
| `WeelKeys` | `m_blupiCle = m_blupiCle \| DoorKeyFlags::All` — grants every key at once. | `Decor.cpp:2039-2042` |
| `Ghost` (`MODERN` only) | Toggles `m_blupiGhost`. Turning it **on** clears every vehicle flag, zeroes velocity/sub-pixel accumulators and `m_blupiVector`, and resets to `BlupiAction::Stop`. Turning it **off** only completes if Blupi is not currently overlapping a blocking tile (`!DecorDetect(BlupiRect(m_blupiPos))`) — otherwise the toggle is silently rejected and ghost mode stays on, preventing the player from un-ghosting inside solid geometry. | `Decor.cpp:2044-2080` |
| `BuildOfficialMissions` | **No branch exists.** Enum value is defined and reachable via the typed-cheat table, but `CheatAction` never tests for it — no-op. | — |
| `KillEgg` | **No branch exists.** Same situation as `BuildOfficialMissions`. | — |

After the per-cheat branches, three cleanup checks run unconditionally on every call, re-deriving
dependent visual/audio state from whatever the flags now say:

*From `Decor.cpp:2082-2095`:*

```cpp
if (!m_blupiShield && !m_blupiHide && !m_blupiCloud && !m_blupiPower)
{
    m_jauges[1].SetHide(true);
}
if (!m_blupiHelico && !m_blupiOver)
{
    StopSound(SoundChannel::SoundChannel16);
    StopSound(SoundChannel::SoundChannel18);
}
if (!m_blupiJeep && !m_blupiTank)
{
    StopSound(SoundChannel::SoundChannel29);
    StopSound(SoundChannel::SoundChannel31);
}
```

This is why, for example, activating `Skate` (which stops the helicopter/jeep motor sounds
explicitly inside its own branch) is not strictly necessary for correctness — the same three
`StopSound` calls would fire again at the bottom of the function regardless of which branch ran,
because none of the vehicle-exclusive flags are true after a `Skate` activation. The explicit calls
inside `Skate`'s own branch are redundant with this tail logic but harmless.

## `GetCheatTinyText` and the doc's own literal-string claim

One more small discrepancy worth flagging precisely: the documentation writes the button-label
sequence as "`D, B, S, E, R, T, C, T, G`" — nine letters for `Cheat1`–`Cheat9`. Reading
`GetCheatTinyText` character by character confirms this exactly, including the repeated `T` for
both `Cheat6` (`TrialMode`) and `Cheat8` (`AllTreasure`) — not a typo in the documentation, but a
genuine ambiguity in the game's own button labeling: a player looking at the cheat panel sees two
buttons both labeled "T" for unrelated effects.

## The `TEMP CHEAT HOOK` in `Game1::StartMission`

`Cheat System.md` also documents, as a "how to add a temporary hook" example, a block of code that
calls `decor.CheatAction()` for eleven cheat codes automatically on every mission start. As of the
version of `Game1.cpp` read for this chapter, no such hook is present in `Game1::StartMission` —
missions start through the ordinary sequence (`decor.Read()`, `LoadImages()`, `SetMission()`,
`SetNbVies()`, `InitializeDoors()`, `AdaptDoors()`, `MainSwitchInitialize()`, `PlayPrepare()`) with
no automatic cheat activation. The documentation labels this block explicitly as a *temporary*
debugging hook meant to be removed ("`remove later`"), so its absence from the current source is
consistent with the doc's own framing — it was evidently added, used, and then actually removed, as
intended. It is included in the documentation file as a *recipe* for a developer who wants to
reproduce that debugging setup, not as a description of shipped behavior — a distinction worth
making explicit since nothing else in the doc is written in that "how to" register.

## See also

- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md) — where `CleanAll`'s target
  `ObjectType` list intersects with real enemy behavior.
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md) — how `m_blupiShield`,
  `m_blupiCloud`, and the vehicle-mode flags actually change collision handling.
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md) — `DoorKeyFlags::All`
  and `OpenDoorsTresor()`, both touched by cheats in this chapter.
- [Chapter 24 — Missions and ContinueMission](ch24-missions-and-continuemission.md) — `m_nbVies`,
  `m_buildOfficialMissions`, and the dead `SetBuildOfficialMissions` path.
- [Chapter 25 — Game Speed and Zoom](ch25-game-speed-and-zoom.md) — the `Quick`/`Zoom` typed cheats
  intercepted inside `InputPad.cpp` before reaching `Decor::CheatAction`.
- [Chapter 26 — Tile and Icon Catalog](ch26-tile-and-icon-catalog.md) — icon 214, gated by
  `m_bDrawSecret`/`ShowSecret`.
- [Appendix E — Cheat Code Reference](../appendices/appendix-e-cheat-code-reference.md)
