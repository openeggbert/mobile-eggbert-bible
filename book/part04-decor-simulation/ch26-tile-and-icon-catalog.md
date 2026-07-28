# Chapter 26: Tile and Icon Catalog

## Overview

Every cell of `Decor::m_decor[100][100]` stores exactly one field: an `intcs icon`
(`Decor.hpp:113-116`). There is no separate "tile type" enum anywhere in the shipped code — every
piece of gameplay behavior a tile can have (lethal, blocking, springy, a door, a teleporter, a fan)
is derived, at the moment it matters, by comparing that raw integer against literal constants
inside one of roughly two dozen `bool`/`int` predicate methods on `Decor`. This chapter is the
systematic catalog of those predicates: what exact icon value or range each one tests, what
real gameplay behavior it gates, and where to find it.

This catalog was built by grepping every `Decor::Is*` definition in `Decor.cpp` and reading each
one in full — not by relying on any secondary source. `mobile-eggbert`'s own `ENUMS.md` proposes
readable names for many of these icon values (`Lava` for `68`, `Spring` for `211`, and so on); this
chapter cites those suggested names where they help, but — per this book's methodology — **`ENUMS.md`
is a refactoring proposal, not implemented code.** No `enum class TileIconType` (or any equivalent)
exists in `mobile-eggbert` today. Every table below reflects the actual runtime behavior: raw
integer literals compared with `==`/`>=`/`<=` inside ordinary `if` statements.

## First, a structural correction: tile icons *do* draw real sprites

Before cataloging individual predicates, one structural claim needs to be checked directly against
`Build()`, because getting it wrong would misdescribe every entry below. It would be easy to assume
— since `m_decor[][].icon` is clearly a *gameplay classification* value, tested by two dozen
predicate methods with no rendering logic in sight — that these icon numbers are a purely invisible
logic layer sitting on top of a separately pre-rendered background image, with the *visible* tile
art coming entirely from `Content/backgrounds/decorNNN.png` (loaded via `Pixmap::BackgroundCache`,
`Decor.cpp:250`, drawn as the very first thing in `Build()`, `Decor.cpp:687`).

Reading the rest of `Build()` shows this is only true for a specific, enumerable subset of icons.
The general case is the opposite: **most `m_decor[][].icon` values are real sprite indices**, drawn
directly through `PixmapChannel::Object` (`object-m.png`, the 64×64-grid atlas documented in
`PLAN.md`'s sprite-atlas table) using the icon number itself as the sprite index. The relevant loop
in `Build()` iterates every visible tile and, by default, draws it verbatim:

*From `Decor.cpp:1023-1030` (the second `m_decor` iteration pass in `Build()`):*

```cpp
if (i >= 0 && i < 100 && j >= 0 && j < 100 && m_decor[i][j].icon != -1)
{
    int num2 = m_decor[i][j].icon;
    pos = tinyPoint;
    if (num2 == 68)
    {
        num2 = Tables::table_decor_lave[(i * 13 + j * 7 + m_time / Config::ScaleDiv(2)) % 8];
        m_pixmap->QuickIcon(PixmapChannel::Object, num2, pos);
    }
```

and, in the *earlier* pass over the same grid, the default branch of a large `switch` on the same
icon value does exactly this for every icon **not** in a specific exclusion list:

*From `Decor.cpp:935-966`:*

```cpp
switch (num2)
{
default:
    m_pixmap->QuickIcon(PixmapChannel::Object, num2, pos);
    break;
case 68:
case 91:
case 92:
case 110: /* ...110-137... */
case 305:
case 317:
case 324:
case 373:
case 378:
case 384:
case 385:
case 404:
case 410:
    break;
}
```

So the true picture is: **static** tile icons (ordinary ground, walls, decoration, most collectible
and door-frame tiles — anything not in that exclusion list) are drawn straight through
`PixmapChannel::Object` using their own icon number as the sprite index, in the first pass. The
handful of icons in the exclusion list — every animated or time-varying hazard/interactive tile
(lava `68`, water `91`/`92`, the fan family `110`–`137`, lightning `305`, the crusher `317`, the
temporary platform `324`, the spike trap `373`, the saw `378`, both bridge-door states `384`/`385`,
and the drip family `404`/`410`) — are deliberately skipped in that first pass and instead drawn in
the **second** pass shown above, where each one is first remapped through a dedicated per-icon
animation table (`Tables::table_decor_lave`, `table_decor_eau1`/`eau2`, `table_decor_ventg`/`ventd`/
`venth`/`ventb`, `table_decor_ventillog`/`ventillod`/`ventilloh`/`ventillob`, `table_decor_piege1`/
`piege2`, `table_decor_ecraseur`, `table_decor_scie`, `table_decor_temp`, `table_decor_goutte`) to
pick the *current frame*'s real sprite index before drawing — still through `PixmapChannel::Object`,
still a real sprite. (Door icons `384`/`385` are the one exception drawn in a third, separate loop
just before this one, at `Decor.cpp:917-925`, for reasons unrelated to animation.)

The corrected structural summary, then: `m_decor[][].icon` is **both** the gameplay-hazard
classifier the predicates below test **and**, for the large majority of static tiles, the literal
sprite index rendered into `PixmapChannel::Object`. The pre-rendered `Content/backgrounds/*.png`
supplies the parallax scenery *behind* these tiles (mountains, sky, distant terrain), not the tiles
themselves. The only icons for which the visible art is *not* a direct function of the raw icon
number are the animated/hazard set enumerated above, where the real per-frame sprite comes from a
small lookup table keyed by `(tile position, m_time)` rather than being the icon value itself.

## The complete `Decor::Is*` inventory

Grepping `bool Decor::Is`/`int Decor::Is` across `Decor.cpp` (excluding `IsTerminated`, which tests
level-completion state, not a tile) turns up **29 methods** total. Of these, **24** genuinely
classify a tile by its `icon` value (or, for `IsFloatingObject`, the icon of the tile *beneath* a
moving object) — noticeably more than this chapter's ~20 estimate. The remaining 5 test unrelated
state: `IsDisplayInfo` (HUD treasure-counter display gating, keyed on `m_nbTresor`, not any tile),
`IsBalleTraj`/`IsMoveTraj` (bit-packed occupancy grids for bullets/moving objects, not the tile map
at all), `IsGhost` (`MODERN` cheat-mode flag), and `IsTerminated` itself.

| Method | Returns | Icon-classifying? | Covered in this chapter |
|---|---|---|---|
| `IsWorld` | `int` (world index) | Yes | §World markers |
| `IsLave` | `bool` | Yes | §Lethal hazards |
| `IsPiege` | `bool` | Yes | §Lethal hazards |
| `IsGoutte` | `bool` | Yes | §Lethal hazards |
| `IsScie` | `bool` | Yes | §Lethal hazards |
| `IsEcraseur` | `bool` | Yes | §Lethal hazards |
| `IsBlitz` | `bool` | Yes | §Lethal hazards |
| `IsSwitch` | `bool` | Yes | §Interactive tiles |
| `IsRessort` | `bool` | Yes | §Interactive tiles |
| `IsTemp` | `bool` | Yes | §Interactive tiles |
| `IsVentillo` | `bool` | Yes | §Interactive tiles |
| `IsBridge` | `bool` | Yes | §Structural tiles |
| `IsDoor` | `int` (icon/-1) | Yes | §Structural tiles |
| `IsTeleporte` | `int` (icon/-1) | Yes | §Structural tiles |
| `IsNormalJump` | `bool` | Yes (via `IsPassIcon`) | §Structural tiles |
| `IsSurfWater` | `bool` | Yes | §Water |
| `IsDeepWater` | `bool` | Yes | §Water |
| `IsOutWater` | `bool` | Yes | §Water |
| `IsPassIcon` | `bool` | Yes (table-driven) | §Collision classification |
| `IsBlocIcon` | `bool` | Yes (table-driven) | §Collision classification |
| `IsFloatingObject` | `bool` | Yes (tile beneath object) | §Collision classification |
| `IsRightBorder` | `bool` | Yes (auto-tiling) | §Auto-tiling |
| `IsFromage` | `bool` | Yes | §Auto-tiling |
| `IsGrotte` | `bool` | Yes | §Auto-tiling |
| `IsDisplayInfo` | `bool` | No (treasure-count HUD gate) | out of scope |
| `IsBalleTraj` | `bool` | No (bullet occupancy grid) | out of scope |
| `IsMoveTraj` | `bool` | No (moving-object occupancy grid) | out of scope |
| `IsGhost` | `bool` | No (`m_blupiGhost` cheat flag) | out of scope |
| `IsTerminated` | `int` | No (`m_term` win/loss state) | [Chapter 24](ch24-missions-and-continuemission.md) |

All position-based predicates share the same calling convention: they take a `TinyPoint pos` in
**game-space pixel coordinates** (not tile coordinates), apply a small fixed pixel offset specific
to what part of Blupi's or the object's bounding box they're probing (feet, head, grab-point), then
divide by 64 to reach the tile index — `m_decor[pos.X / 64][pos.Y / 64].icon`. The offsets differ
predicate to predicate (e.g. `IsPiege` probes `pos.X += 30; pos.Y += 60` — Blupi's feet — while
`IsLave` probes only `pos.X += 30` at the caller-supplied `Y`), which is why they cannot be
collapsed into one generic "what hazard is here" function even though their bodies look similar.

## Lethal and damaging hazards

| Icon(s) | Predicate | Real behavior | `ENUMS.md` proposed name | Citation |
|---|---|---|---|---|
| `68` | `IsLave` | Instant-lethal lava tile; feet-probe only (`pos.X += 30`, no Y offset). | `Lava` | `Decor.cpp:7195-7203` |
| `373` | `IsPiege` | Spike trap; only triggers within a narrow horizontal band of the tile (`pos.X % 64` in `[15,49]`), probed at feet height (`pos.Y += 60`). | `SpikeTrap` | `Decor.cpp:7205-7218` |
| `404` (and, once cycled, `410`) | `IsGoutte(pos, bAlways)` | Drip hazard. With `bAlways=false`, only icon `404` (the "about to fall" frame) counts as active; with `bAlways=true`, either `404` or `410` counts. Same horizontal-band restriction as `IsPiege`. | `DripActive*` (icons `404`–`407`, per `ENUMS.md` group 4) | `Decor.cpp:7220-7241` |
| `378` | `IsScie` | Saw blade; wide horizontal tolerance (`pos.X % 64` in `[4,60]`, almost the whole tile width) compared to the traps above. | `SawBlade` | `Decor.cpp:7243-7255` |
| `317` | `IsEcraseur` | Crusher; gated by a **time-based duty cycle** independent of position — `m_time / 3 % 10 > 2` short-circuits to inactive for 7 of every 10 ticks (of a 3-tick-scaled counter) *before* the icon is even checked. | `Crusher` | `Decor.cpp:7277-7289` |
| `305` | `IsBlitz(pos, bAlways)` | Lightning bolt. With `bAlways=false`, additionally requires `BlitzActif(x,y)` — itself a 100-tick cycle (`m_time / ScaleDiv(1) % 100 < 50` and even) — to be "active" (see [Chapter 25](ch25-game-speed-and-zoom.md) for how `ScaleDiv` enters here). | `BlitzHazard` (icon `304` is the anchor/emitter above it, `BlitzAnchor`) | `Decor.cpp:7291-7310`, `Decor.cpp:620-634` |

Three distinct "activity gating" strategies appear across just these six predicates: pure position
(`IsLave`, always active if the icon matches), a narrow sub-tile hit-band (`IsPiege`/`IsGoutte`/
`IsScie`), and a global time-based duty cycle independent of position (`IsEcraseur`, `IsBlitz`).
This is a real design pattern worth naming: hazards that must be *visually* dodgeable (a
saw blade swinging, a crusher slamming down) use `m_time`-driven activity windows so a careful
player can time a safe crossing, whereas hazards with no visible warning (`IsLave`) are simply
always lethal.

## Interactive / mechanism tiles

| Icon(s) | Predicate | Real behavior | `ENUMS.md` proposed name | Citation |
|---|---|---|---|---|
| `384` / `385` | `IsSwitch(pos, celSwitch&)` | Switch tile; matches *either* icon (open or closed state) and writes the matched tile's coordinates to the out-parameter regardless of which state it's in. | `BridgeOpen`/`BridgeClosed` (per `ENUMS.md` — note the name overlaps with the bridge-state icons `384`/`385` share; see caveat below) | `Decor.cpp:7257-7275` |
| `211` | `IsRessort` | Spring tile; feet-probe (`pos.Y += 60`) causing an upward bounce. Its *visible* animation frame is picked from `Tables::table_ressort` cycling on `Config::ScaleDiv(2)`, independent of this predicate. | `Spring` | `Decor.cpp:7312-7321` |
| `324` | `IsTemp` | Temporary/disappearing platform, feet-probed. Notably, `IsPassIcon`/`IsBlocIcon` (below) *also* special-case icon `324` directly, driven by a different, longer `m_time`-based cycle — so a `324` tile's solidity and this predicate's own detection can be checked independently of each other. | `Temperature` (per `ENUMS.md`; the name is a guess — nothing in the code suggests thermal behavior, just a disappear/reappear cycle) | `Decor.cpp:7323-7332` |
| `126`–`137` | `IsVentillo` | Fan tile family. Only the four *directional head* icons (`126` left, `129` right, `132` up, `135` down) can actually trigger (checked via sub-tile position bands per direction); the rest of the range (`127`,`128`,`130`,`131`,`133`,`134`,`136`,`137` — presumably the fan's body/column segments) fall through with no effect. **Side-effecting**: a triggering call walks the fan's air column and permanently clears every matching air tile via `ModifDecor(pos, -1)` — calling this for an active fan mutates the map. | `FanLeft`/`FanRight`/`FanUp`/`FanDown` for the four head icons; `BarRail*` is `ENUMS.md`'s (unrelated, mis-scoped) suggested name for this same range — see caveat below | `Decor.cpp:7667-7752` |

**A caveat on `ENUMS.md`'s icon-range table worth stating plainly:** `ENUMS.md`'s own "Tile Icon
Types" table (its main, highest-priority section) lists `126–137` under the single suggested name
`BarRail*` ("Bar / rope / rail tiles") — but the actual predicate that tests icons in that exact
range, `IsVentillo`, is about fans/ventilators, not bars or rails (the real bar/rail tiles are icons
`138` and `202`, tested directly by `Decor::GetTypeBarre`, not by any `Is*` predicate in this
chapter's inventory, at `Decor.cpp:7158-7193`). This is worth flagging exactly because `ENUMS.md`
is a proposal document reviewed here for the first time against the real predicate bodies: its
authors evidently grouped `126–137` by proximity to the `107–137` "jump/fan" region without
checking each individual `Is*` predicate's actual icon literals, and the same range also collides
with its own separate `FanLeft`/`FanRight`/`FanUp`/`FanDown` entries for `110`/`114`/`118`/`122` a
few rows above. A reader using `ENUMS.md` as a vocabulary should treat its ranges as a *starting
point for further reading*, not a verified fact — which is exactly the caution this book's
methodology asks for.

## Structural tiles: bridges, doors, teleporters

| Icon(s) | Predicate | Real behavior | `ENUMS.md` proposed name | Citation |
|---|---|---|---|---|
| `364` | `IsBridge(pos, celBridge&)` | Bridge tile; probed at *two* Y offsets (`pos.Y += 60` then, if that misses, `pos.Y -= 60` again to check one tile up) so Blupi can be detected as "on the bridge" from either just above or just at its surface. | `BridgeEndpoint` | `Decor.cpp:7334-7352` |
| `334`–`336` | `IsDoor(pos, celPorte&)` | Door tile. Probes Blupi's own tile *and* one tile in his current facing direction (`m_blupiDir`), so a door can be opened by walking toward it, not just standing on it. Returns the matched icon itself (which encodes the door's specific color/lock variant), not just a boolean. | Not directly listed; `ENUMS.md` covers the surrounding `158–184`/`309`/`410–420` door-adjacent ranges as `Door*`/`DoorPortal*`/`DoorAnchor*`/`DoorExtra`/`DoorSpecial`/`DoorVariant*`, but not `334–336` specifically | `Decor.cpp:7360-7376` |
| `330`–`333` | `IsTeleporte(pos)` | Teleporter entry pad. Restricted to a thin vertical strip of the tile (`pos.X % 64 <= 6`). Returns the matched icon itself, because — as `SearchTeleporte` shows — **the icon value doubles as the pairing key**: `SearchTeleporte` scans the entire 100×100 grid for another cell sharing the *same* icon, more than 40px away, and treats it as the exit. There is no separate teleporter-pair index table. | `Teleporter*` | `Decor.cpp:7378-7395`, `7406-7430` |
| n/a (uses `IsPassIcon` on two cells above) | `IsNormalJump` | Not a single-icon test — checks that both the tile directly above and the tile above that (offset toward Blupi's facing direction) are passable, to permit a normal (non-vehicle) jump. | — | `Decor.cpp:7432-7460` |

## Water tiles

| Icon(s) | Predicate | Real behavior | `ENUMS.md` proposed name | Citation |
|---|---|---|---|---|
| `91` | (part of) `IsDeepWater` | Deep-water icon; `IsDeepWater` treats *either* `91` or `92` as deep water. | `WaterShallow` (per `ENUMS.md` — note this reads backward from the code's own usage; see caveat below) | `Decor.cpp:7477-7491` |
| `92` | `IsSurfWater`, (part of) `IsDeepWater` | `IsSurfWater` fires only at the **boundary**: the current tile's own icon is *not* `92` but the tile `BLUPISURF` (12px) below *is* `92` — i.e., Blupi's feet are right at the water's surface line, which is when surfboard mode engages. | `WaterDeep` (per `ENUMS.md`) | `Decor.cpp:7462-7476` |
| anything except `91`/`92` that also passes `IsPassIcon` | `IsOutWater` | "Dry land adjacent to water" — literally defined as *not* `91`, *not* `92`, and passable. | — | `Decor.cpp:7493-7501` |

**Another `ENUMS.md` caveat:** its table lists `91` as `WaterShallow` and `92` as `WaterDeep`. Reading
the predicates directly suggests the opposite emphasis, if anything: `IsSurfWater` (the *shallow*,
surfboard-appropriate behavior) fires when the tile **below** the current one is `92`, while
`IsDeepWater` treats **both** `91` and `92` as deep water indiscriminately. Nothing in these three
predicates alone proves which literal icon is the "true" shallow tile and which is "true" deep — the
evidence is genuinely ambiguous from `Decor.cpp` alone, and this is exactly the kind of claim this
chapter will not resolve by guessing. The safe, source-grounded statement is: `91` and `92` are both
water-family icons, `92` is specifically the one whose presence one tile below Blupi triggers
surf/surfboard behavior, and `ENUMS.md`'s shallow/deep labels for the two should be treated as an
unverified guess, not a confirmed fact.

## Collision classification: `IsPassIcon`/`IsBlocIcon` and `table_decor_quart`

Every hazard and mechanism predicate above answers "is this a hazard/mechanism of type X?" — a
completely separate question from "can Blupi's body physically occupy this tile at all?", which is
what `IsPassIcon`/`IsBlocIcon` answer. They are not simple booleans-per-icon; they consult a large
data table, `Tables::table_decor_quart` (7,056 `shortcs` entries — 441 icons × 16 quarter-tile
sub-cells, matching `Decor::MAXQUART = 441`, `Decor.hpp:187`):

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

Each icon (below `MAXQUART = 441`) owns 16 consecutive entries in `table_decor_quart` — one per
quarter-tile sub-cell of a 4×4 collision grid inside that one 64×64 tile. `IsPassIcon` returns
`false` (not passable) the moment it finds *any* non-zero sub-cell; `IsBlocIcon` returns `false`
(not fully blocking) the moment it finds *any* zero sub-cell — meaning a tile can be neither fully
passable nor fully blocking under this scheme (a partial-collision shape, like a slope or a
half-block), and callers that need finer-grained collision (rather than these two whole-tile yes/no
answers) presumably index `table_decor_quart` directly elsewhere in the collision code covered in
[Chapter 21](ch21-physics-and-collision.md). Icons at or above `441` (i.e., every value the game
actually uses for the `421+` treasure-door range, and others) automatically report as passable by
`IsPassIcon` (falls through the `if` unchanged) and never blocking by `IsBlocIcon` (rejected by the
first bounds check) — those higher icon numbers are collision-transparent by construction, which
matches their role as decorative/logic-only overlays (treasure doors, world markers) rather than
physical obstacles.

Both methods special-case icon `324` (the temporary/disappearing platform from the interactive-tiles
table above) identically but inversely, keyed on a **different** time cycle (`m_time / 4 % 20`,
period 20) than the one `Build()` uses to pick that tile's *visual* animation frame
(`Tables::table_decor_temp[m_time / Config::ScaleDiv(4) % 20]`, `Decor.cpp:1063-1066` — same period,
same divisor, so the two cycles are in fact synchronized, just expressed as two separately-written
`m_time / 4 % 20` computations rather than a shared named constant). For roughly the first 18 of
every 20 ticks the platform blocks (`IsBlocIcon` true, `IsPassIcon` false); for the remaining ~2
ticks it briefly becomes passable, letting Blupi fall through if he lingers.

`IsFloatingObject(int i)` reuses `IsPassIcon` for a different purpose entirely — not classifying the
tile a *character* occupies, but the tile *beneath a moving object* (crate, raft, etc.), to decide
whether that object is floating on water rather than resting on solid ground:

*From `Decor.cpp:10350-10357`:*

```cpp
bool Decor::IsFloatingObject(int i)
{
    TinyPoint posCurrent = m_moveObject[i].posCurrent;
    int num = (posCurrent.X + 32) / 64;
    int num2 = posCurrent.Y / 64 + 1;
    int icon = m_decor[num][num2].icon;
    return IsPassIcon(icon);
}
```

## World markers and auto-tiling helpers

`IsWorld` is a specialized lookup used by the world-select hub level, converting a small family of
icon ranges into a 1-based *world index* rather than a plain boolean:

*From `Decor.cpp:7079-7122`:*

```cpp
int Decor::IsWorld(TinyPoint pos)
{
    pos.X += 30;
    pos.Y += 30;
    ...
    int icon = m_decor[pos.X / 64][pos.Y / 64].icon;
    if (icon >= 158 && icon <= 165) { return icon - 158 + 1; }
    if (icon >= 166 && icon <= 173) { return icon - 166 + 1; }
    switch (icon)
    {
    case 309:
    case 310:
        return 9;
    case 411: case 412: case 413: case 414: case 415:
        return icon - 411 + 10;
    default:
        if (icon >= 416 && icon <= 420) { return icon - 416 + 10; }
        if (icon >= 174 && icon <= 181) { return icon - 174 + 1; }
        if (icon == 184) { return 199; }
        return -1;
    }
}
```

Two independent icon families (`158–165` and `166–173`, and again `174–181`) all map to world
indices `1`–`8` via the same `icon - base + 1` arithmetic, `411–420` maps to worlds `10`–`19`, the
pair `309`/`310` are both hard-coded to world `9`, and icon `184` alone maps to the special world
index `199` — the same reserved mission number seen in [Chapter 24](ch24-missions-and-continuemission.md)'s
win-condition logic (`Decor.cpp:6417-6423`), confirming `184`/`199` is the hub's marker for the
game's special/final destination rather than an ordinary numbered world.

`IsFromage` ("cheese" — a specific decorative/collectible-adjacent terrain feature) and `IsGrotte`
("cave") are simpler multi-icon membership tests used by the auto-tiling adaptation code
(`AdaptMidBorder`/`AdaptBorder`, which re-picks border sprite variants after `ModifDecor` changes a
tile):

*From `Decor.cpp:10677-10711`:*

```cpp
bool Decor::IsFromage(int x, int y)
{
    ...
    int icon = m_decor[x][y].icon;
    if (icon >= 246 && icon <= 249) { return true; }
    if (icon == 339) { return true; }
    return false;
}

bool Decor::IsGrotte(int x, int y)
{
    ...
    switch (m_decor[x][y].icon)
    {
    case 284:
    case 301:
        return true;
    case 337:
        return true;
    default:
        return false;
    }
}
```

`IsRightBorder(x, y, dx, dy)` is the largest and most structurally different predicate in the whole
inventory: a **neighbor-relationship** test, not a single-tile classification. It answers "does the
tile at `(x+dx, y+dy)` form a border edge relative to the block at `(x,y)`?", and its body is a
several-hundred-line nested `switch` (`Decor.cpp:10367` onward) classifying icon ranges including
`386–397` (a dedicated "always border" range), `245`/`400` (special-cased), `250–260` (compared
against the *origin* tile's own icon, not just the neighbor's), and a long `default` fallback
covering dozens more individual icons. It exists purely to drive `AdaptMidBorder`'s neighbor-mask
computation for auto-tiled terrain blocks, and off-map neighbor coordinates always count as a
border (`return true`) so map edges auto-tile correctly with no special-casing at the call site.
Because its purpose is structural (deciding which of several pre-drawn border sprite variants to
select) rather than a hazard/interaction classification, it is catalogued here for completeness but
not exhaustively itemized icon-by-icon — the individual icons it inspects mostly duplicate ranges
already covered above or in `ENUMS.md`'s `TerrainType`/border-adjacent groups.

## Master reference table

The table below consolidates every icon-classifying predicate's primary trigger value(s) in one
place, for quick lookup. "Proposal name" columns cite `ENUMS.md`'s suggested vocabulary explicitly
as a proposal, never as an existing type.

| Icon range | Predicate(s) | Behavior | `ENUMS.md` proposal name |
|---|---|---|---|
| `68` | `IsLave` | Instant-lethal lava | `Lava` |
| `91`, `92` | `IsDeepWater`, `IsSurfWater`, `IsOutWater` | Water family; `92` triggers surf mode from one tile above it | `WaterShallow` (91) / `WaterDeep` (92) — order unverified, see caveat above |
| `107–109` | (not tested by any `Is*` predicate in this inventory — used elsewhere for spring/jump visuals) | — | `NormalJumpA`–`NormalJumpC` |
| `110`,`114`,`118`,`122` | `IsVentillo` | Directional fan heads (left/right/up/down) | `FanLeft`/`FanRight`/`FanUp`/`FanDown` |
| `111–113,115–117,119–121,123–125,127,128,130,131,133,134,136,137` | `IsVentillo` (range check only; non-head icons never trigger) | Fan body/column segments, inert for triggering purposes | (covered by `ENUMS.md`'s broader, partly-mismatched `BarRail*` label — see caveat above) |
| `126`, `129`, `132`, `135` | (same `IsVentillo` range; these + the four heads above cover `110–137`) | See directional fan heads | — |
| `138`, `202` | `GetTypeBarre` (not an `Is*` predicate; documented here since `ENUMS.md` conflates this range with `126-137`) | Bar/rope/rail grab points | `BarRail*` (more accurately applies here than to `126–137`) |
| `211` | `IsRessort` | Spring bounce | `Spring` |
| `246–249`, `339` | `IsFromage` | "Cheese" terrain feature | `Bridge*` (`ENUMS.md` labels `246-249` as `Bridge*`; note this is a different structure than the `364` bridge tile below) |
| `284`, `301`, `337` | `IsGrotte` | Cave terrain feature | (not covered by `ENUMS.md`'s table) |
| `305` (`304` = emitter above) | `IsBlitz` | Lightning, time-gated by `BlitzActif` | `BlitzHazard` (305) / `BlitzAnchor` (304) |
| `317` | `IsEcraseur` | Crusher, time-gated | `Crusher` |
| `324` | `IsTemp`, `IsPassIcon`, `IsBlocIcon` | Disappearing platform, ~90%/10% solid/passable duty cycle | `Temperature` |
| `330–333` | `IsTeleporte`, `SearchTeleporte` | Teleporter; icon value is also the pairing key | `TeleporterPair*` |
| `334–336` | `IsDoor` | Door, opens toward Blupi's facing direction | (not directly covered by `ENUMS.md`) |
| `364` | `IsBridge` | Bridge surface | `BridgeEndpoint` |
| `373` | `IsPiege` | Spike trap, narrow hit-band | `SpikeTrap` |
| `378` | `IsScie` | Saw blade, wide hit-band | `SawBlade` |
| `384`, `385` | `IsSwitch` | Switch (open/closed state) | `BridgeOpen`/`BridgeClosed` (name collides with `IsSwitch`'s actual role — see caveat above) |
| `404`, `410` | `IsGoutte` | Drip hazard, two-frame active/settled distinction | `DripActive*` |
| `421+` | (not an `Is*` predicate — see `OpenDoorsTresor`, [Chapter 22](ch22-doors-keys-doorkeyflags.md)) | Treasure-gated doors; always collision-transparent (`IsPassIcon`/`IsBlocIcon` treat `>= MAXQUART` as passable) | `Treasure*` |
| `158–184`, `309–310`, `411–420` | `IsWorld` | World-select hub markers, encode world index 1–19 plus special index 199 | `Door*`/`Teleporter*`/`DoorPortal*`/`DoorAnchor*`/`DoorExtra`/`DoorSpecial`/`DoorVariant*` (`ENUMS.md` treats this range as door-related, not as world markers — a further gap between the proposal document and this predicate's actual role) |

That last row is worth pausing on: `ENUMS.md`'s table assigns door-flavored names (`Door*`,
`DoorPortal*`, `DoorAnchor*`, and so on) to almost the exact icon ranges that `IsWorld` actually
treats as *hub world-select markers*, not doors at all. This is the single largest gap this
chapter's direct-source-reading turned up between the proposal document's suggested vocabulary and
the real predicate that owns each range — a concrete demonstration of why `CLAUDE.md`'s rule to
treat `ENUMS.md` as an unverified proposal, not a description of the code, matters in practice.

## See also

- [Chapter 16 — The Tile Map](ch16-tile-map.md) — `Cellule`, `m_decor`/`m_bigDecor`, and the
  coordinate systems these predicates all convert through.
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md) —
  `ModifDecor`, `DecorAction`, and the animated-tile mechanics `IsVentillo`/`IsTemp` interact with.
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md) — how `IsPassIcon`/`IsBlocIcon`
  and `TestPath`/`DecorDetect` combine into Blupi's actual movement resolution.
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md) — `IsDoor`,
  `OpenDoorsTresor`, and the `421+` treasure-door range.
- [Chapter 23 — Secret Powers and the Cheat System](ch23-secret-powers-and-cheat-system.md) —
  `ShowSecret`/`m_bDrawSecret`, which gates icon `214`'s visibility (referenced via `IsRightBorder`'s
  neighbor table).
- [Chapter 24 — Missions and ContinueMission](ch24-missions-and-continuemission.md) — mission index
  `199`, also `IsWorld`'s special return value for icon `184`.
- [Chapter 29 — The Sprite Atlas System](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md) —
  the `PixmapChannel::Object` atlas (`object-m.png`) these icon values index into directly.
- [Appendix B — Enum Catalog](../appendices/appendix-b-enum-catalog.md)
