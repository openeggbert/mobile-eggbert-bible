# Chapter 16: The Tile Map

This chapter is about `Decor`'s tile map — the two 100×100 grids of icon indices that hold a
level's static geometry — and, specifically, about what those icon numbers actually mean. It opens
by testing a hypothesis from this book's own planning notes against the real source, because the
corrected picture turns out to be a load-bearing fact for nearly everything else in Part IV that
reads or writes a tile.

## A correction before we start

This book's own planning notes (`PLAN.md`, written before this chapter's source reading) proposed
a specific hypothesis about how `Decor`'s tile map works: that the numeric `icon` values stored in
`m_decor[][]` are used *only* for gameplay/collision classification, and that the visible
per-region art comes entirely from a separate pre-rendered background image
(`Pixmap::BackgroundCache`), making the tile icon numbers an "invisible logic layer" that never
indexes a real sprite sheet.

Having now read the actual call sites in `Decor.cpp`, that hypothesis is **half right and half
wrong**, and the corrected picture is more interesting than either the original guess or its
simple negation. This chapter's job is to lay out precisely what the source shows, because this is
one of the most consequential structural facts in the whole simulation — it explains, among other
things, why `worlds/*.txt` level files legitimately contain tile-icon numbers well past 290 (the
`Element` channel's own atlas capacity) without anything being broken.

## Two grids, two purposes, one surprise

`Decor` maintains **two** parallel 100×100 tile grids, not one:

*From `Decor.hpp:208-211`:*
```cpp
/** Primary tile map: 100x100 cells, each storing a decor/tile icon index. */
Cellule m_decor[100][100]{};
/** Secondary (large background) tile map for big-tile rendering. Same layout as m_decor. */
Cellule m_bigDecor[100][100]{};
```

Both are arrays of the same minimal struct:

*From `Decor.hpp:113-116`:*
```cpp
struct Cellule
{
    intcs icon; ///< Tile icon index used for rendering and collision classification.
};
```

Both are loaded from a real level file's text format (`worlds/*.txt`), from two separate named
sections, `Decor:` and `BigDecor:` (`Decor.cpp:11077-11098` for writing, `Decor.cpp:11326-11341`
for reading a designed level). A real level file makes this concrete — here is an excerpt from
`world001.txt`'s `Decor:` section, the game's world-selection hub map:

```
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,10,,,10,,,,10,10,10,10,10,10,10,183,10,183,10,,10,,10,,10,,10,,10,,10,10,10,10,10,10,
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,10,,,,,10,,10,10,10,10,10,10,10,183,10,10,10,,10,165,10,411,10,164,10,161,10,160,10,158,10,10,10,10,10,10,
```

Icon `10` (a wall/floor tile), `183`, and then a cluster of world-selection sign icons — `165`,
`411`, `164`, `161`, `160`, `158` — sit side by side in the same row. Several of those values are
already well above 290; `IsWorld()` (`Decor.cpp:7079`, discussed below) confirms these specific
values are meaningful world-entry markers, not corruption.

The two grids are populated identically but consumed **completely differently**, and that
difference is the crux of this chapter.

## `m_decor`: rendered *and* classified, by the same number

The instinct to treat `m_decor`'s icon as gameplay-only classification comes from a real and
important fact: dozens of `Is*()` predicate methods in `Decor.cpp` — `IsLave`, `IsPiege`,
`IsScie`, `IsBlitz`, `IsRessort`, `IsBridge`, `IsDoor`, `IsTeleporte`, `IsSurfWater`,
`IsDeepWater`, `IsVentillo`, and more — read `m_decor[x][y].icon` purely to answer yes/no
gameplay questions ("is this lava," "is this a spring," "is this a door"). The two foundational
predicates underneath nearly all of them are `IsPassIcon()` and `IsBlocIcon()`:

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

`Tables::table_decor_quart` is a flat table of 16 sub-tile "quarter" occupancy flags per icon
(`Decor.hpp:186-187` documents `MAXQUART = 441` as "Maximum number of quarter-tile entries used in
the tile adjacency system"), and `Decor::DecorDetect()` (Chapter 21) uses these two predicates to
decide whether a given pixel rectangle overlaps solid geometry. So far, this matches the
"classification layer" half of the original hypothesis exactly — and `MAXQUART`'s value of 441 is
itself a clue worth remembering for the next section.

But `m_decor`'s icon is **also** the direct argument to `IPixmap::QuickIcon()` in `Build()`'s main
tile-drawing pass — the same integer, unmodified, read straight out of the same array:

*From `Decor.cpp:916-943` (abridged):*
```cpp
if (i >= 0 && i < 100 && j >= 0 && j < 100 && m_decor[i][j].icon != -1)
{
    int num2 = m_decor[i][j].icon;
    pos.X = tinyPoint.X;
    pos.Y = tinyPoint.Y;
    // ... a handful of per-icon position nudges (e.g. icon 211 remapped through
    // Tables::table_ressort for its current animation frame) ...
    switch (num2)
    {
    default:
        m_pixmap->QuickIcon(PixmapChannel::Object, num2, pos);
        break;
    case 68: case 91: case 92: case 110: /* ... */ case 384: case 385: case 404: case 410:
        break; // handled by a *second* pass instead (see below)
    }
}
```

The `default` branch is the headline: for the overwhelming majority of tile icons, `Decor` calls
`m_pixmap->QuickIcon(PixmapChannel::Object, num2, pos)` — drawing the tile's sprite directly out
of the **`Object`** sprite sheet (`object-m.png`, per the atlas table in `PLAN.md`, not `Element`
as originally guessed), using the exact same integer that `IsPassIcon()`/`IsBlocIcon()` just used
to decide whether Blupi can walk through it. **The tile icon is not an invisible logic-only value.
It is the literal sprite index, and it is also the collision key, at the same time, in the same
integer.**

This resolves the "why do icon numbers go past 290" puzzle cleanly, and in the opposite direction
from the original guess: they are not *avoiding* a real atlas by staying invisible — they are
correctly indexing a *different, larger* atlas than `Element`'s. `object-m.png` is a 1301×1431
image with a 64×64 grid and a 1px gap (`PLAN.md`'s atlas table, sourced from `Pixmap.cpp`'s
`GetSrcRectangle`/`DrawIcon` switch), giving roughly 20 columns × 22 rows ≈ 440 usable icon
slots — which lines up almost exactly with `MAXQUART = 441`, the very same capacity constant the
*collision* table uses. The tile-icon numbering space is bounded by the `Object` atlas and the
`table_decor_quart` collision table together, not by `Element`'s smaller 290-icon atlas that this
book's planning notes initially (and incorrectly) assumed was the relevant one.

The `switch`'s exclusion list (icons `68`, `91`, `92`, `110`–`137`, `305`, `317`, `324`, `373`,
`378`, `384`, `385`, `404`, `410`) is not a set of collision-only, never-rendered icons either —
it is simply the set of tiles whose *visible appearance is animated*, and which are therefore
handled by a **second** tile-iteration pass later in `Build()` that remaps them through small
per-frame lookup tables before drawing, still via `PixmapChannel::Object`:

*From `Decor.cpp:1023-1043` (abridged):*
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
    if (num2 == 373)
    {
        num2 = (!m_blupiFocus)
                   ? Tables::table_decor_piege2[(i * 13 + j * 7 + m_time / Config::ScaleDiv(2)) % 4]
                   : Tables::table_decor_piege1[(i * 13 + j * 7 + m_time / Config::ScaleDiv(4)) % 16];
        m_pixmap->QuickIcon(PixmapChannel::Object, num2, pos);
    }
    // ... 404/410 (drips), 317 (crusher), 378 (saw), 324 (temporary platform), 92/91 (water) ...
}
```

Icon `68` (lava) cycles through 8 frames of `Tables::table_decor_lave`, offset by each tile's own
`(i, j)` so that adjacent lava tiles are not perfectly synchronized; icon `373` (a trap) picks
between two different animation tables depending on whether Blupi currently has camera focus —
one variant plays while the level is in view, a cheaper/simpler one otherwise. Icons `384`/`385`
(the two states of a switch-controlled door — see `ActiveSwitch()`, `Decor.cpp:7131`, which
literally writes `384` or `385` into `m_decor` to flip a door's visible state) get their own even
smaller dedicated pass earlier in `Build()` (`Decor.cpp:756-763`). None of this is invisible
logic; it is ordinary sprite animation, keyed by the same integer that also drives collision.

**The corrected claim for the record:** `m_decor[][]`'s icon is a single value serving two roles
simultaneously — a direct index into the `Object` sprite atlas for rendering, and a lookup key
into `Tables::table_decor_quart` for collision classification. It is not an "invisible" layer, and
it is not indexed into `Element`. The genuinely separate, non-tile-indexed visual layer in this
system is the *background panorama* (below), which really is independent of tile icons — that
part of the original hypothesis holds up.

## `m_bigDecor`: a real second render layer, and an odd default

If `m_decor` is not the "invisible" layer, `m_bigDecor` is where a version of the original
hypothesis's shape does show up — but with its own surprise. `m_bigDecor` is drawn in `Build()`
*before* `m_decor`, as a distinct culled tile pass:

*From `Decor.cpp:700-741` (abridged):*
```cpp
for (int i = posDecor.X / 64 - 1; i < posDecor.X / 64 + m_drawBounds.getWidthProperty() / 64 + 3; i++)
{
    for (int j = posDecor.Y / 64 - 1; j < posDecor.Y / 64 + m_drawBounds.getHeightProperty() / 64 + 2; j++)
    {
        if (i >= 0 && i < 100 && j >= 0 && j < 100)
        {
            int num2 = m_bigDecor[i][j].icon;
            PixmapChannel channel = PixmapChannel::Explosion;
            if (num2 != -1)
            {
                pos.X = tinyPoint.X; pos.Y = tinyPoint.Y;
                if (num2 == 203)
                {
                    num2 = Tables::table_marine[m_time / Config::ScaleDiv(3) % 11];
                    channel = PixmapChannel::Object;
                }
                // ... small per-range vertical position nudges ...
                m_pixmap->QuickIcon(channel, num2, pos);
            }
        }
        tinyPoint.Y += 64;
    }
    tinyPoint.X += 64;
}
```

Every non-empty `m_bigDecor` cell is drawn — there is no collision predicate anywhere in the file
that reads `m_bigDecor`; it is purely decorative. But the channel it draws from is, by default,
**`PixmapChannel::Explosion`** (`explo.png`, the explosion-effect atlas, sized per-icon via
`Tables::table_explo_size` — see the atlas table in `PLAN.md` and `Pixmap.cpp:582-594`), with a
single carved-out exception: icon `203` is remapped through `Tables::table_marine` (an
11-frame water-surface animation) and switched to the `Object` channel instead. This is a genuine
oddity in the ported code, not a misreading — the variable really is named `channel`, really
defaults to `PixmapChannel::Explosion`, and is only reassigned for the one special case. `Decor`
uses `m_bigDecor` for a comparatively small set of large, often-animated scenery elements
(overlaid decorative machinery, the animated water-surface tile, and similar set-dressing), reused
from the `explo.png` atlas rather than a dedicated "big decor" atlas of its own — apparently
because that atlas already had appropriately large, variably-sized sprite cells available
(`table_explo_size`-driven, up to 144×144) that ordinary 60×60/64×64 tile atlases do not.

## The genuinely separate layer: the panorama background

The one part of the original hypothesis that is fully confirmed is the *panorama* background —
and it really is independent of both tile grids. `LoadImages()` (Chapter 15) loads it once per
region:

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

This loads a whole file — `Content/backgrounds/decorNNN.png`, one of the 38 region art files
listed in `PLAN.md` — as a single cached image under `PixmapChannel::Background`, and `Build()`
blits it in a repeating 3×2 grid of 640×480 panels, offset by two-thirds of the scroll position
for a parallax effect (`Decor.cpp:649-699`, Chapter 15). Crucially, this drawing path takes no
`icon` parameter at all — `IPixmap::DrawPart(PixmapChannel::Background, tinyPoint, rect)` slices a
*rectangle* out of the cached whole image, not a numbered grid cell out of an atlas. There is no
mechanism anywhere by which a `m_decor` or `m_bigDecor` icon value selects which panorama shows;
the panorama is chosen once, per level, by `m_region` alone, and everything drawn from
`m_decor`/`m_bigDecor` is layered on top of it as separate, independently-positioned sprites.

So the full, corrected three-layer picture is:

1. **Panorama background** (`PixmapChannel::Background`, via `BackgroundCache`) — one whole image
   per region, selected by `m_region`, blitted as a repeating parallax-scrolled panel grid. Not
   tile-indexed at all.
2. **`m_bigDecor`** — a sparse, mostly-empty 100×100 overlay of large scenery sprites, drawn from
   `PixmapChannel::Explosion` by default (`Object` for the one water-surface special case),
   purely decorative.
3. **`m_decor`** — the dense, collision-relevant 100×100 foreground tile grid: every non-empty
   icon is *both* rendered directly from `PixmapChannel::Object` *and* consulted by
   `IsPassIcon()`/`IsBlocIcon()`/the `Is*()` hazard predicates for gameplay classification.

## Coordinate systems in practice: `GetPosDecor()`

`Decor.hpp`'s header comment (quoted in Chapter 15) names three coordinate systems — tile,
game-space pixel, and screen-space — and `GetPosDecor()` is where game-space becomes the
scroll-relative value that everything else in `Build()` actually iterates against:

*From `Decor.cpp:6622-6646`:*
```cpp
TinyPoint Decor::GetPosDecor(TinyPoint pos)
{
    TinyPoint result;
    if (m_dimDecor.X == 0)
    {
        result.X = 0;
    }
    else
    {
        result.X = pos.X - m_drawBounds.getWidthProperty() / 2;
        result.X = std::max(result.X, 0);
        result.X = std::min(result.X, 6400 - m_drawBounds.getWidthProperty());
    }
    // ... identical logic for result.Y using m_dimDecor.Y ...
    return result;
}
```

Given a game-space point (almost always `m_scrollPoint`, the eased camera target — Chapter 15),
this centers the viewport on it and clamps the result to `[0, 6400 - viewportSize]` — `6400`
being `100 tiles × 64 pixels`, the full extent of the level in game-space. The `m_dimDecor.X == 0`
/ `m_dimDecor.Y == 0` special case matters for single-screen levels: a level whose `dimDecor`
field marks one axis as non-scrollable pins that axis's `m_posDecor` at `0` unconditionally,
regardless of where Blupi is standing — the camera simply doesn't move along that axis at all.
`Build()`'s every tile-iteration loop starts from this same clamped `posDecor` value
(`Decor::Build()` calls `DecorNextAction()` at its very top, which returns `m_posDecor` adjusted
for any active screen-shake effect — Chapter 19 covers `DecorAction` in full) divided by 64 to get
the visible tile range, which is exactly the "game-space plus scroll offset" screen-space
definition from the header comment, applied in the direction that matters for rendering: screen
pixel position equals game-space position minus `posDecor`.

## `IsWorld()`: reading meaning out of raw icon ranges

One predicate deserves a closer look on its own, because it is the clearest illustration in the
whole file of tile icons carrying *semantic* meaning well beyond simple pass/block classification:
`IsWorld()`, used only on the hub/world-selection map to figure out which world a given tile
represents.

*From `Decor.cpp:7079-7122`:*
```cpp
int Decor::IsWorld(TinyPoint pos)
{
    pos.X += 30;
    pos.Y += 30;
    if (pos.X < 0 || pos.X >= 6400 || pos.Y < 0 || pos.Y >= 6400)
    {
        return -1;
    }
    int icon = m_decor[pos.X / 64][pos.Y / 64].icon;
    if (icon >= 158 && icon <= 165) { return icon - 158 + 1; }
    if (icon >= 166 && icon <= 173) { return icon - 166 + 1; }
    switch (icon)
    {
    case 309: case 310: return 9;
    case 411: case 412: case 413: case 414: case 415: return icon - 411 + 10;
    default:
        if (icon >= 416 && icon <= 420) { return icon - 416 + 10; }
        if (icon >= 174 && icon <= 181) { return icon - 174 + 1; }
        if (icon == 184) { return 199; }
        return -1;
    }
}
```

Four *separate, non-contiguous* icon ranges (`158`–`165`, `166`–`173`, `174`–`181`, plus the
scattered singles `309`/`310` and `411`–`420`) all map onto the same small set of world numbers
1–10 (plus the special bonus world `9` and the meta-world `199`). This is exactly the kind of
mapping `ENUMS.md` (an analysis/**proposal** document, not implemented code — see Chapter 26) sets
out to give names to; in the shipped source, all four ranges are still raw integer literals, and
`IsWorld()` is a good demonstration of why: each range corresponds to a visually distinct sign
sprite (probably different world "theme" decorations) that all mean the same *gameplay* thing, and
the arithmetic (`icon - 158 + 1`, `icon - 411 + 10`) recovers the world number from whichever
range's sprite happens to be sitting on that tile. The offsets `+30, +30` before the lookup are
worth noting too — they sample the tile under the *center* of the query rectangle (`pos` is a
game-space point, and adding half a tile-width/height before dividing by 64 samples whichever tile
that center point actually falls inside), a pattern repeated by nearly every position-to-tile
lookup in `Decor.cpp`.

## Border auto-tiling: `AdaptBorder()` and `AdaptMidBorder()`

The final piece of the tile-map story is how `m_decor`'s icons get *edited* at runtime without the
level designer having hand-picked every corner and edge variant: `AdaptBorder()` and
`AdaptMidBorder()`, the game's auto-tiling system, called after any code path that changes a tile
(`ModifDecor()`, `ActiveSwitch()`, and level-editor operations).

*From `Decor.cpp:10917-10929`:*
```cpp
/**
 * @note Re-runs the auto-tiler on the edited cell and its four orthogonal neighbours so all
 *       borders stay consistent after a tile change. ...
 */
void Decor::AdaptBorder(TinyPoint cel)
{
    AdaptMidBorder(cel.X, cel.Y);
    AdaptMidBorder(cel.X + 1, cel.Y);
    AdaptMidBorder(cel.X - 1, cel.Y);
    AdaptMidBorder(cel.X, cel.Y + 1);
    // AdaptMidBorder(cel.X, cel.Y - 1); (final neighbour)
```

`AdaptBorder()` simply re-runs `AdaptMidBorder()` on the changed cell and its four orthogonal
neighbors, so that a single tile edit can never leave a stale border/corner sprite next to it.
`AdaptMidBorder()` itself is the real auto-tiler:

*From `Decor.cpp:10721-10744` (abridged):*
```cpp
void Decor::AdaptMidBorder(int x, int y)
{
    if (x < 0 || x >= 100 || y < 0 || y >= 100) { return; }
    int num = 15;
    if (!IsRightBorder(x, y + 1, 0, -1)) { num &= -2; }
    if (!IsRightBorder(x, y - 1, 0, 1)) { num &= -3; }
    if (!IsRightBorder(x + 1, y, -1, 0)) { num &= -5; }
    if (!IsRightBorder(x - 1, y, 1, 0)) { num &= -9; }
    int num2 = m_decor[x][y].icon;
    // ... a handful of icon aliases collapse to a "base" variant, e.g. 156 -> 35 ...
    for (int i = 0; i < 144; i++)
    {
        if (num2 == Tables::table_adapt_decor[i])
        {
            num2 = Tables::table_adapt_decor[i / 16 * 16 + num];
            // ... several results are randomly swapped for a cosmetic variant, e.g.
            // num2 == 35 has a 50% chance of becoming 156 instead ...
            m_decor[x][y].icon = num2;
            return;
        }
    }
    // ... separate 4-neighbour bitmask + table_adapt_fromage lookups for "fromage"
    // (cheese/block) and "grotte" (cave) terrain families ...
}
```

This builds a 4-bit neighbor bitmask (one bit per side, cleared when that side is *not* a matching
border tile per `IsRightBorder()`), reduces the current tile to its terrain family's canonical
"base" icon, and looks that base up in `Tables::table_adapt_decor` (144 entries, 16-wide rows —
one full mask-to-icon row per terrain family) to get the correct edge/corner sprite for the
current neighborhood — and then **writes the result straight back into `m_decor[x][y].icon`**.
This is the cleanest possible confirmation of this chapter's central claim: the auto-tiler
computes a value based purely on *visual* neighbor-matching logic and stores it directly in the
same field that `IsPassIcon()`/`IsBlocIcon()` will read for *collision* on the very next frame.
There is exactly one icon field per cell, and both the renderer and the physics engine read it.

Two smaller neighboring-terrain systems piggyback on the same method — `IsFromage()`/
`table_adapt_fromage` for one family of blocks and `IsGrotte()`/`table_adapt_fromage[+16]` for
cave terrain — both following the identical 4-neighbour-bitmask pattern, and both finishing with a
handful of hardcoded 50%-chance cosmetic re-rolls so that long, uniform runs of the same terrain
don't look mechanically identical tile-to-tile.

## See also

- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 17 — Blupi: the State Machine](ch17-blupi-state-machine.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md)
- [Chapter 26 — Tile and Icon Catalog](ch26-tile-and-icon-catalog.md)
- [Chapter 27 — Decor.hpp Reference Catalog](ch27-decor-hpp-reference-catalog.md)
- [Chapter 29 — The Sprite Atlas System](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md)
- [Chapter 34 — Backgrounds and Level Art](../part05-sprites-rendering-animation/ch34-backgrounds-and-level-art.md)
- [Chapter 44 — Worlds: Level File Format](../part08-data-persistence-content/ch44-worlds-level-file-format.md)
- [Appendix C — Level File Format Specification](../appendices/appendix-c-level-file-format-spec.md)
