# Chapter 21: Physics and Collision

Speedy Blupi's tile map does not carry any per-tile metadata beyond a single integer icon index
(`Decor::Cellule::icon`, `Decor.hpp:113-116`). Every piece of gameplay meaning — "this is lava,"
"this is a switch," "this is deep water" — is reconstructed at query time by dozens of small
`Is*()` predicate methods that each test the icon at a position against one or a few hard-coded
numeric literals. This chapter catalogues those predicates, the crate ("caisse") pushing
subsystem built on top of them, and explains — with direct source citations — where they agree
and where they subtly disagree with the project's own `ENUMS.md` proposal document.

## A note on `ENUMS.md`

Before quoting it, a reminder consistent with this book's methodology (see `CLAUDE.md`):
`mobile-eggbert`'s repository root contains a file named `ENUMS.md`, titled "Magic Number → Enum
Refactoring Plan." Its own first line states plainly: **"No code has been changed. This is an
analysis-only document."** None of the named constants it proposes (`TileIconType`, `DoorState`,
`TerrainType`, `BlitzCycle`, and others) exist anywhere in the actual `enum class` declarations
under `include/WindowsPhoneSpeedyBlupi/`. The code shown in this chapter always uses raw integer
literals (`68`, `373`, `305`, …) directly in `if`/`switch` conditions. Wherever this chapter cites
`ENUMS.md`'s proposed names below, it does so as "the project's own `ENUMS.md` analysis document
proposes naming icon *N* as *X*" — never as if `X` were a real, implemented type.

## The core passability test: `IsPassIcon` / `IsBlocIcon`

Every hazard and terrain predicate in this chapter ultimately rests on the same underlying data:
`Tables::table_decor_quart`, a per-icon 4×4 sub-tile solidity bitmap already introduced in
[Chapter 20](ch20-enemy-and-creature-ai.md)'s coverage of `DecorDetect()`. Two simpler,
whole-tile-granularity queries wrap it directly:

*From `Decor.cpp:7503-7540`:*
```cpp
bool Decor::IsPassIcon(int icon)
{
    if (icon == 324 && m_time / 4 % 20 >= 18)
    {
        return true;
    }
    if (icon >= 0 && icon < MAXQUART)
    {
        for (int i = 0; i < 16; i++)
        {
            if (Tables::table_decor_quart[icon * 16 + i] != 0)
            {
                return false;
            }
        }
    }
    return true;
}

bool Decor::IsBlocIcon(int icon)
{
    if (icon < 0 || icon >= MAXQUART)
    {
        return false;
    }
    if (icon == 324 && m_time / 4 % 20 < 18)
    {
        return true;
    }
    for (int i = 0; i < 16; i++)
    {
        if (Tables::table_decor_quart[icon * 16 + i] == 0)
        {
            return false;
        }
    }
    return true;
}
```

`IsPassIcon()` returns true — passable — if *none* of an icon's sixteen quart-cells are solid;
`IsBlocIcon()` returns true — fully blocking — only if *all sixteen* are. An icon can therefore be
neither fully passable nor fully blocking under these two whole-tile queries (a slope, say, is
partially solid) — those in-between cases are exactly what `DecorDetect()`'s fine-grained quart-cell
scan (see [Chapter 20](ch20-enemy-and-creature-ai.md)) exists to resolve properly. Both methods
share one hard-coded special case: icon `324`, a blinking/temporary platform, is treated as
time-dependent — solid for the first 18 ticks of every 20-tick cycle (`m_time / 4 % 20`), then
passable for the remaining two. `ENUMS.md` groups this icon as `Temperature` (see the "Tile Icon
Types" table below), a name this chapter's own reading of the code cannot confirm — nothing in
`IsPassIcon`/`IsBlocIcon`/`IsTemp` (below) references temperature; the actual behaviour is a timed
platform that periodically vanishes.

## `ENUMS.md`'s "Tile Icon Types" table, cross-checked

`ENUMS.md` §1 ("HIGH PRIORITY") lists icon-value groups it proposes naming as a single
`TileIconType` enum. The table below reproduces its proposal (left two columns) alongside what
this chapter's own reading of the `Is*()` predicates in `Decor.cpp` actually confirms (right
column) — marking agreement, refinement, or outright mismatch:

| Icon(s) | `ENUMS.md`'s proposed name | What `Decor.cpp` actually tests |
|---|---|---|
| 68 | `Lava` | Confirmed — `IsLave()`, `Decor.cpp:7202` |
| 91 / 92 | `WaterShallow` / `WaterDeep` | Confirmed — `IsSurfWater`/`IsDeepWater`, below |
| 211 | `Spring` | Confirmed — `IsRessort()`, `Decor.cpp:7320` |
| 214 | `HiddenTile` | Partially confirmed — non-solid only while flying/over, `DecorDetect`, ch. 20 |
| 305 | `BlitzHazard` | Confirmed — `IsBlitz()`, `Decor.cpp:7301` |
| 304 | `BlitzAnchor` | Confirmed — tested in `BlitzActif()`, `Decor.cpp:624` |
| 317 | `Crusher` | Confirmed — `IsEcraseur()`, `Decor.cpp:7288` |
| 324 | `Temperature` | **Mismatch** — actually a timed/blinking platform, not heat-related |
| 364 | `BridgeEndpoint` | Confirmed — `IsBridge()`, `Decor.cpp:7338/7345` |
| 373 | `SpikeTrap` | Confirmed — `IsPiege()`, `Decor.cpp:7217` |
| 378 | `SawBlade` | Confirmed — `IsScie()`, `Decor.cpp:7254`; also the switch-toggled saw in `ActiveSwitch()` |
| 384–385 | `BridgeOpen` / `BridgeClosed` | **Mismatch** — these are the switch tile's two states, not a bridge; see below |
| 404–420 | `DripActive*` / `DoorVariant*` | Overloaded — icon 410 alone serves as both a drip state and a world-hub marker, depending on level; see below |
| 421+ | `Treasure*` | Confirmed as door-unlock thresholds — `OpenDoorsTresor()`, [Chapter 22](ch22-doors-keys-doorkeyflags.md) |

Two of these are worth walking through in detail, because they show exactly the kind of thing
that can go wrong when proposing named constants for magic numbers without reading every call
site — and, just as importantly, why this book treats `ENUMS.md` as a proposal to check against
the code rather than a description of it.

### The 384/385 mismatch: switch, not bridge

`ENUMS.md` labels icons 384 and 385 `BridgeOpen`/`BridgeClosed`. But the only two places in
`Decor.cpp` that reference these exact values are the switch-activation method and the
switch-detection predicate:

*From `Decor.cpp:7131-7149` (`ActiveSwitch`):*
```cpp
void Decor::ActiveSwitch(bool bState, TinyPoint cel)
{
    TinyPoint pos;
    pos.X = cel.X * 64;
    pos.Y = cel.Y * 64;
    ModifDecor(pos, bState ? 384 : 385);
    PlaySound(bState ? SoundChannel::SoundChannel77 : SoundChannel::SoundChannel76, pos);
    ...
}
```

*From `Decor.cpp:7257-7275` (`IsSwitch`):*
```cpp
bool Decor::IsSwitch(TinyPoint pos, TinyPoint& celSwitch)
{
    pos.X += 30;
    ...
    celSwitch.X = pos.X / 64;
    celSwitch.Y = pos.Y / 64;
    if (m_decor[pos.X / 64][pos.Y / 64].icon != 384)
    {
        return m_decor[pos.X / 64][pos.Y / 64].icon == 385;
    }
    return true;
}
```

Icon `384` is the switch's "on" (activated) sprite and `385` is its "off" (deactivated) sprite —
there is no bridge logic anywhere near these two values. `IsBridge()` (below) tests an entirely
different icon, `364`. This is a genuine discrepancy between `ENUMS.md`'s proposal and the actual
code, not a matter of interpretation, and it is exactly the kind of error a careful refactor would
need to catch before acting on the document's suggested names.

### Icon 410: one number, at least two meanings

`ENUMS.md` groups `410`–`420` under a single `DoorVariant*` label. Reading `IsGoutte()` (a drip
hazard predicate, below) shows icon `410` is directly tested as a drip-hazard variant:

*From `Decor.cpp:7220-7241`:*
```cpp
bool Decor::IsGoutte(TinyPoint pos, bool bAlways)
{
    pos.X += 30;
    if (pos.X % 64 < 15 || pos.X % 64 > 49)
    {
        return false;
    }
    ...
    int icon = m_decor[pos.X / 64][pos.Y / 64].icon;
    if (bAlways)
    {
        if (icon != 404)
        {
            return icon == 410;
        }
        return true;
    }
    return icon == 404;
}
```

Yet `AdaptDoors()` (covered in depth in [Chapter 22](ch22-doors-keys-doorkeyflags.md)) separately
treats icons `410`–`415` as world-hub progression markers, swapping them to an "unlocked" variant
five icons higher once the corresponding `m_doors[]` flag is set. Both usages are real and both
are correct in their own context — the resolution is that the *same numeric icon value* is
reused across level types that never coexist in the same map: a drip hazard belongs to an ordinary
gameplay level, while icon `410`'s door-marker role only appears on the hub/world-select level.
This is precisely the risk `PLAN.md`'s own investigation flagged for Part IV/V: tile icon values
form a single flat numeric space with no type tag, so the same number can be safely reused for
unrelated purposes as long as the level designer never puts both uses in the same map — a design
that works in practice but would make a single `enum class TileIconType` genuinely ambiguous
without also encoding "which kind of level is this."

## Hazard predicates

Each hazard predicate follows the same shape: offset the query position into the tile it actually
cares about (often by a partial-tile amount to test a specific band or edge of the 64px tile, not
its arbitrary corner), bounds-check against the 6400×6400 pixel map, then compare the tile's icon
to one or two literals.

*From `Decor.cpp:7195-7203` (lava):*
```cpp
bool Decor::IsLave(TinyPoint pos)
{
    pos.X += 30;
    if (pos.X < 0 || pos.X >= 6400 || pos.Y < 0 || pos.Y >= 6400)
    {
        return false;
    }
    return m_decor[pos.X / 64][pos.Y / 64].icon == 68;
}
```

*From `Decor.cpp:7205-7218` (trap):*
```cpp
bool Decor::IsPiege(TinyPoint pos)
{
    pos.X += 30;
    pos.Y += 60;
    if (pos.X % 64 < 15 || pos.X % 64 > 49)
    {
        return false;
    }
    ...
    return m_decor[pos.X / 64][pos.Y / 64].icon == 373;
}
```

The `pos.X % 64 < 15 || pos.X % 64 > 49` guard, shared by several predicates below, restricts the
hazard to a horizontal band across the middle of its tile — Blupi's feet have to be genuinely
centred over a spike trap, not just clipping its very edge, for it to register.

*From `Decor.cpp:7243-7255` (saw):*
```cpp
bool Decor::IsScie(TinyPoint pos)
{
    pos.X += 30;
    if (pos.X % 64 < 4 || pos.X % 64 > 60)
    {
        return false;
    }
    ...
    return m_decor[pos.X / 64][pos.Y / 64].icon == 378;
}
```

The saw's band is much wider (4–60 out of 64 pixels) than the trap's (15–49) — a saw blade is
lethal across almost its entire tile width, while a spike trap only triggers dead-centre.

*From `Decor.cpp:7277-7289` (crusher):*
```cpp
bool Decor::IsEcraseur(TinyPoint pos)
{
    if (m_time / 3 % 10 > 2)
    {
        return false;
    }
    pos.X += 30;
    ...
    return m_decor[pos.X / 64][pos.Y / 64].icon == 317;
}
```

The crusher ("écraseur") is only dangerous for the first 3 ticks of every 10-tick cycle
(`m_time / 3 % 10 > 2` rejects everything else) — it visually slams down and retracts, and only
the slam phase is lethal.

*From `Decor.cpp:7291-7310` (lightning) with `BlitzActif`:*
```cpp
bool Decor::IsBlitz(TinyPoint pos, bool bAlways)
{
    pos.X += 30;
    ...
    TinyPoint tinyPoint;
    tinyPoint.X = pos.X / 64;
    tinyPoint.Y = pos.Y / 64;
    if (m_decor[tinyPoint.X][tinyPoint.Y].icon != 305)
    {
        return false;
    }
    if (bAlways)
    {
        return true;
    }
    return BlitzActif(tinyPoint.X, tinyPoint.Y);
}
```

*From `Decor.cpp:613-634` (`BlitzActif`):*
```cpp
/**
 * @note The lightning is on a 100-tick cycle (m_time / ScaleDiv(1) % 100): it is
 *       "active" only on even ticks in the first half of the cycle (num < 50), giving
 *       a flicker. When a blitz emitter (icon 304) sits in the cell above, the zap
 *       sound is played on a fixed set of cycle ticks so the audio lines up with the
 *       visible strikes.
 */
bool Decor::BlitzActif(intcs celx, intcs cely)
{
    TinyPoint pos{celx * 64, cely * 64};
    int num = (m_time / Config::ScaleDiv(1)) % 100;
    if (m_decor[celx][cely - 1].icon == 304 && (num == 0 || num == 7 || num == 18 || num == 25 || num == 33 || num
        == 44) && cely > 0)
    {
        PlaySound(SoundChannel::SoundChannel69, pos);
    }
    if (num % 2 == 0)
    {
        return num < 50;
    }
    return false;
}
```

This is precisely the mechanism `ENUMS.md` §5 ("Blitz (Lightning) Cycle Phases") proposes naming.
The project's own analysis document is worth quoting directly here, since — unlike the 384/385
case above — it matches the code correctly and is useful as a compact restatement:

> **Suggested name:** `BlitzCycle`
> ```cpp
> enum class BlitzCycle : intcs {
>     Length          = 100, ///< Total cycle length in ticks.
>     ActiveThreshold =  50, ///< Ticks below this value are in the active (danger) half.
> };
> ```
> Specific "on" frame indices within the cycle (0, 7, 18, 25, 33, 44) could also be named if the
> pattern is understood; currently their meaning is unclear from context alone.

Reading `BlitzActif()` confirms both halves of this proposal precisely: the cycle length is
literally `100` (`m_time / ScaleDiv(1) % 100`), the active/danger half is literally the first `50`
ticks (`num < 50`), and — as `ENUMS.md` admits — the six specific tick values `0, 7, 18, 25, 33, 44`
are not danger thresholds at all but a *sound-cue schedule*, timed so the zap sound effect lines up
with the visible lightning strikes rather than gating the hazard itself. `IsBlitz()`'s own
`bAlways` parameter lets a caller ask "is this a lightning tile at all?" independent of the cycle
(used, for instance, to draw the tile's base sprite regardless of whether it is currently zapping),
versus the gated query that actually determines whether Blupi gets hurt.

*From `Decor.cpp:7312-7332` (spring and timed platform):*
```cpp
bool Decor::IsRessort(TinyPoint pos)
{
    pos.X += 30;
    pos.Y += 60;
    ...
    return m_decor[pos.X / 64][pos.Y / 64].icon == 211;
}

bool Decor::IsTemp(TinyPoint pos)
{
    pos.X += 30;
    pos.Y += 60;
    ...
    return m_decor[pos.X / 64][pos.Y / 64].icon == 324;
}
```

`IsRessort()` ("ressort" — French for spring) is the upward-bounce trigger, and `IsTemp()` is the
foot-level query for the same blinking platform icon (`324`) `IsPassIcon`/`IsBlocIcon` treat as
time-dependent above — "Temp" here abbreviates "temporary," not temperature, consistent with this
chapter's correction of `ENUMS.md`'s `Temperature` label.

*From `Decor.cpp:7334-7352` (bridge):*
```cpp
bool Decor::IsBridge(TinyPoint pos, TinyPoint& celBridge)
{
    pos.X += 30;
    pos.Y += 60;
    if (pos.X >= 0 && pos.X < 6400 && pos.Y >= 0 && pos.Y < 6400 && m_decor[pos.X / 64][pos.Y / 64].icon == 364)
    {
        celBridge.X = pos.X / 64;
        celBridge.Y = pos.Y / 64;
        return true;
    }
    pos.Y -= 60;
    if (pos.X >= 0 && pos.X < 6400 && pos.Y >= 0 && pos.Y < 6400 && m_decor[pos.X / 64][pos.Y / 64].icon == 364)
    {
        celBridge.X = pos.X / 64;
        celBridge.Y = pos.Y / 64;
        return true;
    }
    return false;
}
```

`IsBridge()` probes two vertical offsets (feet-level and head-level) for icon `364`, so Blupi can
be recognised as standing on a bridge segment whether the query position is measured from his
head or his feet — the same icon the bridge-construction `MoveObject` (`ObjectType52`, see
[Chapter 19](ch19-moving-objects-and-decor-actions.md)) writes into the tile map as it "builds."

*From `Decor.cpp:7432-7460` (normal jump):*
```cpp
bool Decor::IsNormalJump(TinyPoint pos)
{
    pos.X += 32;
    pos.Y -= 32;
    if (m_blupiDir == Direction::Left)
    {
        pos.X -= 15;
    }
    else
    {
        pos.X += 15;
    }
    for (int i = 0; i < 2; i++)
    {
        int num = pos.X / 64;
        int num2 = pos.Y / 64;
        if (num2 < 0)
        {
            return false;
        }
        int icon = m_decor[num][num2].icon;
        if (!IsPassIcon(icon))
        {
            return false;
        }
        pos.Y -= 64;
    }
    return true;
}
```

`IsNormalJump()` checks two tiles directly above Blupi (offset slightly in his facing direction)
are both passable — the headroom clearance test that gates a normal jump versus one that would
bump his head on a ceiling one or two tiles up.

## Water and its three states

Three separate predicates classify a position relative to water, and they are not mutually
exclusive tests over the same icons — each answers a genuinely different question:

*From `Decor.cpp:7462-7501`:*
```cpp
bool Decor::IsSurfWater(TinyPoint pos)
{
    if (pos.Y % 64 < 64 - BLUPISURF)
    {
        return false;
    }
    int icon = m_decor[(pos.X + 30) / 64][pos.Y / 64].icon;
    int icon2 = m_decor[(pos.X + 30) / 64][(pos.Y + BLUPISURF) / 64].icon;
    if (icon != 92 && icon2 == 92)
    {
        return true;
    }
    return false;
}

bool Decor::IsDeepWater(TinyPoint pos)
{
    int num = (pos.X + 30) / 64;
    int num2 = pos.Y / 64;
    if (num < 0 || num >= 100 || num2 < 0 || num2 >= 100)
    {
        return false;
    }
    int icon = m_decor[num][num2].icon;
    if (icon != 91)
    {
        return icon == 92;
    }
    return true;
}

bool Decor::IsOutWater(TinyPoint pos)
{
    int icon = m_decor[(pos.X + 30) / 64][(pos.Y + 30) / 64].icon;
    if (icon == 91 || icon == 92)
    {
        return false;
    }
    return IsPassIcon(icon);
}
```

`IsDeepWater()` is the simplest: icon `91` (shallow) or `92` (deep) both count, i.e. it answers
"is there water here at all." `IsSurfWater()` is more specific — it requires the *current* tile to
not be full deep water (`icon != 92`) while a tile `BLUPISURF` pixels (12px, `Decor.hpp:199`) below
*is* deep water (`icon2 == 92`), i.e. Blupi's surfboard is riding right at the water's surface
boundary rather than submerged in it. `IsOutWater()` answers the opposite question entirely — is
this position clear of water *and* otherwise passable — used to detect the moment Blupi's swim
state should end because he has reached dry, walkable ground.

## Doors, teleporters, fans, and switches

*From `Decor.cpp:7360-7376` (door):*
```cpp
int Decor::IsDoor(TinyPoint pos, TinyPoint& celPorte)
{
    int num = ((m_blupiDir != Direction::Left) ? 60 : (-60));
    pos.X += 30;
    for (int i = 0; i < 2; i++)
    {
        if (pos.X >= 0 && pos.X < 6400 && pos.Y >= 0 && pos.Y < 6400 && m_decor[pos.X / 64][pos.Y / 64].icon >= 334
            && m_decor[pos.X / 64][pos.Y / 64].icon <= 336)
        {
            celPorte.X = pos.X / 64;
            celPorte.Y = pos.Y / 64;
            return m_decor[pos.X / 64][pos.Y / 64].icon;
        }
        pos.X += num;
    }
    return -1;
}
```

`IsDoor()` probes Blupi's own column and one tile ahead in his facing direction, so he can open a
door he is walking *into* without needing to stand exactly on it; the icon range `334`–`336`
encodes the door's colour/lock variant and is returned directly as the "door type." Full door
mechanics — `DoorKeyFlags`, opening sequences, the treasure-gated and win-gated variants — are
covered in [Chapter 22](ch22-doors-keys-doorkeyflags.md).

*From `Decor.cpp:7378-7429` (teleporter):*
```cpp
int Decor::IsTeleporte(TinyPoint pos)
{
    if (pos.X % 64 > 6)
    {
        return -1;
    }
    pos.X += 30;
    pos.Y -= 60;
    ...
    if (m_decor[pos.X / 64][pos.Y / 64].icon >= 330 && m_decor[pos.X / 64][pos.Y / 64].icon <= 333)
    {
        return m_decor[pos.X / 64][pos.Y / 64].icon;
    }
    return -1;
}
```

Teleporters are not indexed in a side table at all: `IsTeleporte()`'s return value *is* the
teleporter's pairing ID (icon `330`–`333`), and `SearchTeleporte()` finds the matching exit by
linearly scanning the entire 100×100 map for another cell sharing that same icon, more than 40px
away from the entry — pairing is implicit in the icon value, not a lookup table.

*From `Decor.cpp:7667-7702` (fan, excerpted):*
```cpp
/**
 * @note Detects a fan tile (icons 126..137) under Blupi and, for the directional fan
 *       heads (126 left, 129 right, 132 up, 135 down), decides whether Blupi is in the
 *       fan's active band (flag) based on his sub-tile position. When triggered it
 *       additionally CONSUMES the fan: it walks the fan's air-column tile by tile in the
 *       blow direction and clears every matching air tile (ModifDecor(..,-1)). So calling
 *       this for an active fan permanently removes that fan's visual column from the map.
 * @warning Side-effecting: a true return mutates the tile map. This is not a pure query.
 */
bool Decor::IsVentillo(TinyPoint pos)
{
    int num = 0;
    bool flag = false;
    TinyPoint tinyPoint;
    pos.X += 30;
    pos.Y += 30;
    ...
    int icon = m_decor[pos.X / 64][pos.Y / 64].icon;
    switch (icon)
    {
    default:
        return false;
    case 126:
        if (pos.X % 64 <= 16)
        {
            flag = true;
        }
        tinyPoint.X = -64;
        tinyPoint.Y = 0;
        num = 110;
        break;
    ...
    }
    ...
}
```

`IsVentillo()` ("ventilateur" — French for fan) is the one hazard predicate in this chapter that
is not a pure query — a positive detection mutates the tile map, permanently consuming the fan's
visible air-column by clearing each traversed tile via `ModifDecor(pos, -1)` (see
[Chapter 19](ch19-moving-objects-and-decor-actions.md), which also covers how clearing a fan tile
this way triggers a debris fragment). This is exactly why `ModifDecor()`'s own special case checks
the `126`–`137` icon range specifically for fans, and why a fan, once triggered, visibly breaks
apart rather than simply vanishing.

## Bars and rails: `GetTypeBarre`

*From `Decor.cpp:7151-7193`:*
```cpp
/**
 * @note Returns 0 unless Blupi's grab point (offset +30,+22) sits in the upper band of a
 *       bar/rail tile (icon 138 or 202) — the band check (pos.Y % 64 > 44) rejects the
 *       lower part of the tile so he only catches the bar near the top. The return value
 *       distinguishes a "hangable" bar (1) from one that is effectively floor because the
 *       cell below is solid or Blupi already has ground contact (2).
 */
int Decor::GetTypeBarre(TinyPoint pos)
{
    TinyPoint pos2 = pos;
    pos.X += 30;
    pos.Y += 22;
    if (pos.Y % 64 > 44)
    {
        return 0;
    }
    ...
    int icon = m_decor[pos.X / 64][pos.Y / 64].icon;
    if (icon != 138 && icon != 202)
    {
        return 0;
    }
    if (pos.Y >= 6336)
    {
        return 1;
    }
    icon = m_decor[pos.X / 64][pos.Y / 64 + 1].icon;
    if (!IsPassIcon(icon))
    {
        return 2;
    }
    TinyRect rect = BlupiRect(pos2);
    rect.Top = pos2.Y + 60 - 2;
    rect.Bottom = pos2.Y + 60 - 1;
    if (DecorDetect(rect, true))
    {
        return 2;
    }
    return 1;
}
```

"Barre" is French for bar/rod; icons `138` and `202` are rope/rail tiles Blupi can grab and hang
from. This method distinguishes a genuinely hangable bar (return `1`) from a bar whose lower half
is actually solid ground or already has Blupi standing on it (return `2`), so climbing logic
elsewhere in `BlupiStep()` knows whether grabbing the bar should suspend Blupi in mid-air or treat
it as a normal floor tile. [Chapter 22](ch22-doors-keys-doorkeyflags.md) covers the switch-toggle
mechanism (`ActiveSwitch()`, discussed above) that these bars are sometimes linked to.

## Reach and range: `SearchDistRight`

*From `Decor.cpp:7620-7656`:*
```cpp
/**
 * @note Marches in tile steps along @p dir from @p pos until it leaves the map or hits a
 *       blocking tile, accumulating 64 pixels per clear tile. Projectile types (36/39/41/
 *       42/93) short-circuit to a fixed 500px range. While scanning a bullet path
 *       (ObjectType23) it also records each traversed tile into the balle-trajectory grid
 *       via SetBalleTraj(). A few types get a small trailing adjustment (one tile or 10px)
 *       so the object stops just short of the wall.
 */
int Decor::SearchDistRight(TinyPoint pos, TinyPoint dir, ObjectType type)
{
    int num = 0;
    if (type == ObjectType::ObjectType36 || type == ObjectType::ObjectType39 || type == ObjectType::ObjectType41 || type == ObjectType::ObjectType42 || type == ObjectType::ObjectType93)
    {
        return 500;
    }
    pos.X = (pos.X + 32) / 64;
    pos.Y = (pos.Y + 32) / 64;
    while (pos.X >= 0 && pos.X < 100 && pos.Y >= 0 && pos.Y < 100 && !IsBlocIcon(m_decor[pos.X][pos.Y].icon))
    {
        if (type == ObjectType::ObjectType23)
        {
            SetBalleTraj(pos);
        }
        num += 64;
        pos.X += dir.X;
        pos.Y += dir.Y;
    }
    if ((type == ObjectType::ObjectType34 || type == ObjectType::ObjectType38) && num >= 64)
    {
        num -= 64;
    }
    if (type == ObjectType::ObjectType23 && num >= 10)
    {
        num -= 10;
    }
    return num;
}
```

This is the method [Chapter 19](ch19-moving-objects-and-decor-actions.md)'s coverage of
`ObjectStart()` relies on to convert a compact `speed` value into an actual travel distance: it
walks tile by tile in a given direction, accumulating 64px per clear tile via `IsBlocIcon()`, until
it either leaves the 100×100 map or hits a blocking tile. Pure visual-effect types short-circuit to
a fixed 500px "range" rather than actually testing collision (they are never going to be blocked by
geometry that matters). A fired bullet (`ObjectType23`) additionally stamps every traversed tile
into the bit-packed `m_balleTraj` occupancy grid via `SetBalleTraj()` — the trajectory bookkeeping
other systems query via `IsBalleTraj()` to know a bullet is passing through a given cell.

## Crate ("caisse") pushing physics

"Caisse" is French for crate, and every reference in this section confirms `ObjectType12` — despite
being documented as "purpose unknown" in `ObjectType.hpp:138` (see
[Chapter 19](ch19-moving-objects-and-decor-actions.md) for that discrepancy in full) — is in fact
the crate type throughout this subsystem.

*From `Decor.cpp:9302-9312` (`UpdateCaisse`):*
```cpp
void Decor::UpdateCaisse()
{
    m_nbRankCaisse = 0;
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType12)
        {
            m_rankCaisse[m_nbRankCaisse++] = i;
        }
    }
}
```

`UpdateCaisse()` rebuilds `m_rankCaisse[]` — the flat list of pool indices classified as crates —
whenever the pool's layout changes (after `MoveObjectSort()`, or after a crate is destroyed by
dynamite, as [Chapter 19](ch19-moving-objects-and-decor-actions.md) shows).

Pushing a crate is a two-stage, atomic group operation, because crates stacked together must move
as one unit:

*From `Decor.cpp:9314-9344` (`TestPushCaisse`):*
```cpp
/**
 * @note Two-pass group push. It first collects the linked crate group (SearchLinkCaisse),
 *       then tests every member with TestPushOneCaisse against the desired horizontal move;
 *       if any member is obstructed the whole push fails and nothing moves. Only when all
 *       members are clear does the second pass commit the move to each crate's
 *       posCurrent/posStart/posEnd, so a crate stack always moves atomically.
 */
bool Decor::TestPushCaisse(int i, TinyPoint pos, bool bPop)
{
    TinyPoint move;
    move.X = pos.X - m_moveObject[i].posCurrent.X;
    move.Y = 0;
    SearchLinkCaisse(i, bPop);
    int y = m_moveObject[i].posCurrent.Y;
    for (int j = 0; j < m_nbLinkCaisse; j++)
    {
        i = m_linkCaisse[j];
        if (!TestPushOneCaisse(i, move, y))
        {
            return false;
        }
    }
    for (int j = 0; j < m_nbLinkCaisse; j++)
    {
        i = m_linkCaisse[j];
        m_moveObject[i].posCurrent.X += move.X;
        m_moveObject[i].posStart.X += move.X;
        m_moveObject[i].posEnd.X += move.X;
    }
    return true;
}
```

The first pass tests every linked crate with `TestPushOneCaisse()`; only if *all* of them can move
does the second pass actually commit the shift. This all-or-nothing structure is what prevents a
stack of three crates from partially sliding through a wall while one member gets stuck.

*From `Decor.cpp:9346-9386` (`TestPushOneCaisse`):*
```cpp
/**
 * @note Tests one crate's destination. It first rejects the move if the shifted crate box
 *       would collide with solid geometry (DecorDetect with bCaisse=false, so other crates
 *       are ignored — they are handled as a group elsewhere). For a crate on the floor row
 *       (@p b is the reference Y), it additionally requires support under BOTH its lower
 *       corners so a pushed ground crate cannot be shoved out over a gap; crates above the
 *       floor row skip the support test.
 */
bool Decor::TestPushOneCaisse(int i, TinyPoint move, int b)
{
    TinyRect rect = TinyRect();
    int num = (rect.Left = m_moveObject[i].posCurrent.X + move.X);
    rect.Right = num + 64;
    rect.Top = m_moveObject[i].posCurrent.Y;
    rect.Bottom = m_moveObject[i].posCurrent.Y + 64;
    if (DecorDetect(rect, false))
    {
        return false;
    }
    if (m_moveObject[i].posCurrent.Y != b)
    {
        return true;
    }
    rect.Left = num;
    rect.Right = num + 20;
    rect.Top = m_moveObject[i].posCurrent.Y + 64;
    rect.Bottom = m_moveObject[i].posCurrent.Y + 64 + 2;
    if (!DecorDetect(rect))
    {
        return false;
    }
    rect.Left = num + 64 - 20;
    rect.Right = num + 64;
    rect.Top = m_moveObject[i].posCurrent.Y + 64;
    rect.Bottom = m_moveObject[i].posCurrent.Y + 64 + 2;
    if (!DecorDetect(rect))
    {
        return false;
    }
    return true;
}
```

Note the deliberate `DecorDetect(rect, false)` for the terrain check — `bCaisse = false` means
other crates are ignored here, because they are tracked as a group by the linking logic below, not
individually. The two follow-up checks (`DecorDetect(rect)`, defaulting `bCaisse = true`) only
apply to a crate on the floor row, requiring solid ground beneath *both* of its bottom corners so
a ground-level crate can never be pushed out over a gap — but crates stacked above the floor skip
this support check entirely, since they are being carried by the crate beneath them, not resting
on terrain.

*From `Decor.cpp:9388-9440` (`SearchLinkCaisse`, excerpted):*
```cpp
/**
 * @note Flood-fills the set of crates that must move together starting from @p rank. It
 *       repeatedly scans the crate list, growing m_linkCaisse with any crate whose
 *       (1px-inflated) box touches an already-linked crate, until a full pass adds nothing
 *       (the @c flag fixed-point). Only crates at or above the seed's row are considered, so
 *       you push a stack but not the floor it rests on. @p bPop additionally restricts the
 *       link to crates within +/-32px horizontally of the seed (used when a stack pops/falls
 *       rather than being pushed sideways).
 */
void Decor::SearchLinkCaisse(int rank, bool bPop)
{
    m_nbLinkCaisse = 0;
    AddLinkCaisse(rank);
    ...
    do
    {
        flag = false;
        for (int i = 0; i < m_nbLinkCaisse; i++)
        {
            ...
            for (int j = 0; j < m_nbRankCaisse; j++)
            {
                ...
                if (Misc::IntersectRect(dst, src2, src) && AddLinkCaisse(num2))
                {
                    flag = true;
                }
            }
        }
    }
    while (flag);
}
```

This is a flood-fill fixed-point algorithm: starting from a seed crate, it repeatedly grows the
linked set with any crate whose 1px-inflated bounding box touches an already-linked crate, stopping
only when a full pass adds nothing new. Only crates at or above the seed's row are eligible — this
is what lets Blupi push a stack of crates without also dragging along whatever crate the stack is
resting on. `bPop` narrows the link radius to ±32px horizontally, used specifically when a stack is
falling/popping apart rather than being pushed as a rigid block sideways.

`AddLinkCaisse()`, `CaisseInFront()`, and `CaisseGetMove()` round out the subsystem:

*From `Decor.cpp:9456-9479` (`CaisseInFront`):*
```cpp
int Decor::CaisseInFront()
{
    TinyPoint tinyPoint;
    if (m_blupiDir == Direction::Left)
    {
        tinyPoint.X = m_blupiPos.X + 16 - 32;
        tinyPoint.Y = m_blupiPos.Y;
    }
    else
    {
        tinyPoint.X = m_blupiPos.X + 60 - 16 + 32;
        tinyPoint.Y = m_blupiPos.Y;
    }
    for (int i = 0; i < m_nbRankCaisse; i++)
    {
        int num = m_rankCaisse[i];
        if (tinyPoint.X > m_moveObject[num].posCurrent.X && tinyPoint.X < m_moveObject[num].posCurrent.X + 64 &&
            tinyPoint.Y > m_moveObject[num].posCurrent.Y && tinyPoint.Y < m_moveObject[num].posCurrent.Y + 64)
        {
            return num;
        }
    }
    return -1;
}
```

`CaisseInFront()` projects a probe point 32px beyond Blupi's own bounding box, in whichever
direction he currently faces, and returns the crate occupying that point — the "which crate is
Blupi about to push?" query.

*From `Decor.cpp:9481-9507` (`CaisseGetMove`):*
```cpp
/**
 * @note Scales the allowed push distance by load and state: heavier stacks (more linked
 *       crates) move slower, the Power bonus doubles the distance, and during the first
 *       ScaleTime(20) frames of the push the speed ramps up from near zero so pushing
 *       starts gently. The result is clamped to at least 1px so a push always makes progress.
 */
int Decor::CaisseGetMove(int max)
{
    max -= (m_nbLinkCaisse - 1) / 2;
    if (max < 1)
    {
        max = 1;
    }
    if (m_blupiPower)
    {
        max *= 2;
    }
    if (m_blupiPhase < Config::ScaleTime(20))
    {
        max = max * m_blupiPhase / Config::ScaleTime(20);
        if (max == 0)
        {
            max++;
        }
    }
    return max;
}
```

This is where crate weight becomes a tangible gameplay effect: a bigger linked stack
(`m_nbLinkCaisse`) directly reduces the maximum push distance per frame, the Power secret bonus
doubles it, and the very start of a push ramps in gradually over `Config::ScaleTime(20)` frames
rather than snapping instantly to full speed — Blupi visibly has to "get a stack moving" before it
reaches its normal push rate. The result is always clamped to at least 1px so a push, once it
qualifies as possible at all, never silently stalls.

## See also

- [Chapter 16 — The Tile Map](ch16-tile-map.md)
- [Chapter 17 — Blupi: the State Machine](ch17-blupi-state-machine.md)
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md)
- [Chapter 26 — Tile and Icon Catalog](ch26-tile-and-icon-catalog.md)
- [Appendix B — Enum Catalog](../appendices/appendix-b-enum-catalog.md)
- [Appendix C — Level File Format Specification](../appendices/appendix-c-level-file-format-spec.md)
