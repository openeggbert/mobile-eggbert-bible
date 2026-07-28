# Chapter 30: Tables — Animation and Movement Data

## A static data warehouse

`Tables` is not a class in the object-oriented sense — it has a deleted constructor and destructor
(`Tables.hpp:70-71`) and exists purely as a namespace-scoped container for `static` arrays. Every
member is data ported verbatim from the original C# game, and the header's own warning is blunt
about the consequence: "any corruption here affects every Blupi movement and action" (`Tables.hpp:128-129`).
This chapter reads that data warehouse closely — not just cataloging array sizes, but verifying the
exact record layouts against the real consumer code in `Decor.cpp` wherever a table's format is
non-obvious from its declaration alone. Chapters 31–33's illustrated catalogs all lean on the
precision established here.

*From `Tables.hpp:60-65`:*
```cpp
/**
 * @note Do not renumber, reorder, or resize any table without updating all code
 *       that indexes into it.  Array sizes are part of the original game's data
 *       contract.
 * @note table_training1..4 are the only mutable tables (modified by Init() ...).
 *       All others are const.
 * @note This is data, not gameplay logic.  Tables does not own any runtime state.
 */
```

## `table_blupi`: the packed record format, verified

`table_blupi` is a single flat array of 2,911 `shortcs` values (`Tables.hpp:131`) that encodes
*every* animation sequence for *every* `BlupiAction` — 88 possible actions
([Chapter 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md) lists the full enum),
almost all of them represented somewhere in this one table. Its header comment describes the shape
in general terms ("each animation block begins with a header record whose first value is the
action ID, followed by the icon index sequence," `Tables.hpp:120-126`); the exact record shape is
only fully pinned down by reading its one real consumer, `Decor::BlupiSearchIcon()`:

*From `Decor.cpp:2393-2403`:*
```cpp
for (; Tables::table_blupi[i] != 0; i += Tables::table_blupi[i + 1] + 3)
{
    if (ToRaw(blupi_action) == Tables::table_blupi[i])
    {
        int num7 = ((Tables::table_blupi[i + 2] == 0 || num6 <= Tables::table_blupi[i + 2])
                        ? (num6 % Tables::table_blupi[i + 1])
                        : Tables::table_blupi[i + 2]);
        num = Tables::table_blupi[i + 3 + num7];
        break;
    }
}
```

Each record is precisely a three-value fixed header — `[actionId, frameCount, specialThreshold]` —
followed by `frameCount` raw sprite-icon indices, and the array is walked linearly from `i = 0` on
*every single call* (there is no side index or offset table anywhere in the codebase mapping action
IDs to their record's position). The terminator is a literal `0` in the `actionId` slot, not `-1`
or any other sentinel — which matters because `0` is also `BlupiAction::None`'s raw value, so the
table's own final record is implicitly unreachable by design; `None` never needs an animation.

The frame-selection arithmetic resolves a real, previously only loosely described behavior into an
exact rule: when `specialThreshold` is `0`, or the (possibly mode-halved — see
[Chapter 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md)'s coverage of the
walking-speed phase-halving step) phase `num6` is still at or below a non-zero threshold, the frame
index loops ordinarily via `num6 % frameCount`. Once `num6` **exceeds** a non-zero threshold, the
frame index is pinned at the threshold value itself, not wrapped or clamped — converting what would
otherwise be an endless loop into a play-once-then-freeze animation. `Air` (`actionId = 5`,
`Tables.cpp:157`, `frameCount = 5`, `threshold = 4`) is the clean textbook example: it loops
`169, 26, 170, 170, 27` while the airborne phase is 4 or under, then freezes on icon `27` — the last
frame — for as long as Blupi keeps falling, rather than replaying the whole rise-and-fall cycle.
`Down` (`actionId = 6`, threshold `2`) shows the identical mechanism at a smaller scale.

Reading the raw data confirms the format concretely. The table's very first record:

*From `Tables.cpp:118-119`:*
```cpp
35, 9, 0, 276, 277, 278, 279, 280, 281, 282,
283, 284, 1, 330, 0, 0, 0, 0, 0, 0,
```
`actionId=35` (`BlupiAction::Hide`), `frameCount=9`, `threshold=0`, icons `276..284`; immediately
followed by `Stop`'s record (`actionId=1, frameCount=330, threshold=0`) — a 330-entry, mostly-empty
idle loop whose length is exactly the cycle `BlupiSearchIcon()`'s blink-sound trigger checks against
(`scaledPhase % 330`, [Chapter 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md)).

Not every stretch of the array is a clean, contiguous record. Walking the full 2,911-entry table
programmatically by the same `frameCount + 3` stride `BlupiSearchIcon()` uses turns up a run of 43
consecutive `-1` values sitting between the `Clear3` record (`actionId=76`) and the `Clear4` record
(`actionId=77`) — reserved padding, not corruption. Because `-1 != 0`, the traversal loop never
mistakes this stretch for the terminator; each fake "record" it walks through in the padding has a
bogus `frameCount` of `-1`, so the loop advances only 2 entries at a time through that stretch until
it reaches `77`'s genuine header. Since no real `BlupiAction` value is ever `-1`, none of the fake
records in that padding can ever match a real lookup — the padding is silently, safely skipped on
every call. Cross-referencing this against `book/images/MANIFEST.md`'s own independent scan of the
table (produced by `tools/extract_sprites.py`, which had to walk the exact same record structure to
know which byte ranges are real animation data worth cropping into contact sheets) confirms the
same finding from the tooling side: **15 distinct degenerate/filler pseudo-records** are encountered
while stepping through that one padding stretch between `Clear3` and `Clear4` (43 raw `-1` values,
consumed 2 at a time with one final partial step, producing 15 non-matching header attempts before
reaching `Clear4`'s real record) — real, verified data-authoring debris preserved faithfully from
the original C# table, exactly the kind of thing this book's "ported data is fixed, not cleaned up"
observation (Chapter 18) predicts.

The manifest also records, independently and by the same exhaustive walk, the full set of
`BlupiAction` enumerators that have **no `table_blupi` record at all**: `Advanceq`, `None`,
`Recedeq`, and `Set`. This lines up exactly with what the enum declaration order
([Chapter 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md)) would predict:
`None` is the initial/idle sentinel value never itself rendered, `Set` (`actionId=12`) never
appears in `BlupiStep()`'s assignment sites as a value that survives to `BlupiSearchIcon()`, and
`Recedeq`/`Advanceq` (`actionId=70, 71`) are queued/pending variants of `Recede`/`Advance` that get
substituted to their non-`q` counterparts before ever reaching the table lookup. All four are real,
declared `BlupiAction` values that simply never need a sprite of their own — [Chapter 31](ch31-blupi-animation-catalog.md)
presents this alongside the illustrated catalog as a verified finding, not a guess.

## `table_mirror`: one atlas, both facings

Blupi's sprite atlas (`blupi.png`) never stores a separate left-facing frame for most animations.
Instead, `table_mirror` is a 335-entry lookup (`Tables.hpp:144`) mapping each right-facing icon
index directly to its already-prepared, horizontally-flipped counterpart:

*From `Tables.cpp:413-449` (first row):*
```cpp
const shortcs Tables::table_mirror[335] =
{
    4, 3, 2, 1, 0, 11, 12, 13, 14, 15,
    16, 5, 6, 7, 8, 9, 10, 20, 21, 22,
    // ...
```
Icon `0` mirrors to `4`, `1` to `3`, `2` to itself — a small local swap consistent with those three
icons being a symmetric or near-symmetric pose grouping. `BlupiSearchIcon()`
([Chapter 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md)) applies this lookup
unconditionally whenever `m_blupiDir == Direction::Left` and the resolved icon is on the `Blupi`
channel and in range `[0, 335)`, with exactly three hardcoded exceptions for the `StopSuspend`
(rope-hanging) action whose left-facing grip poses could not be produced by a simple mirror.
`PixmapChannel::Element`-sourced icons get a much narrower, separate correction (only icons
`168`–`171` shift by `+4` when facing left) rather than using `table_mirror` at all — implying that
one specific four-icon block genuinely stores its own left-facing variant contiguously in the atlas.

## Speed curves: `table_vitesse_march`/`_nage`/`_surf`

Three short tables convert a repeating phase counter into a per-tick pixel displacement, giving
each locomotion mode its own hand-tuned cadence rather than a uniform constant speed:

*From `Tables.cpp:452`:*
```cpp
/** @details Index = phase % 4; value = pixels moved per tick during walking. */
const shortcs Tables::table_vitesse_march[4] = {2, 4, 6, 8};
```

Walking accelerates smoothly across its 4-phase cycle (2, 4, 6, then 8 pixels/tick) rather than
moving at a flat rate — the walk cycle's foot-plant frames correspond to the higher-speed phases,
producing a visually consistent walk/speed relationship instead of a sprite that appears to slide.
`table_vitesse_nage[7]` and `table_vitesse_surf[6]` (`Tables.hpp:165, 174`) apply the identical idea
to swimming and surfing, each with its own paddle/wave cadence — `table_vitesse_surf`'s own header
comment notes its first and last entries are both zero, producing a brief pause at each extreme of
the surf motion rather than a perfectly cyclic speed.

## The creature side-tables: `table_bulldozer_*`, `table_poisson_*`, and the rest

A large family of smaller tables — one quartet per creature/vehicle type — supplies the
direction-and-turn animation data for every patrol enemy and non-Blupi vehicle in the game. Each
quartet follows an identical four-table shape: `_left` and `_right` (short, looping straight-line
cycles) plus `_turn2l` and `_turn2r` (longer, non-looping transition sequences played once when the
creature reverses direction):

| Creature/vehicle | `_left`/`_right` length | `_turn2l`/`_turn2r` length |
|---|---|---|
| Bulldozer (`ObjectType4`) | 8 | 22 |
| Fish/"poisson" (`ObjectType17`) | 8 | 48 |
| Bird/"oiseau" (`ObjectType20`) | 8 | 10 |
| Wasp/"guepe" (`ObjectType44`) | 6 | 5 |
| Large creature (`ObjectType54`) | 8 | 152 (one shared table for both turn directions) |
| Blupi-hostile clone "blupih" (`ObjectType32`) | 8 | 26 |
| Blupi-hostile clone "blupit" (`ObjectType33`) | 8 | 24 |

*From `Tables.cpp:1186`:*
```cpp
const shortcs Tables::table_bulldozer_left[8] = {66, 66, 67, 67, 66, 66, 65, 65};
```

The turn-transition tables are dramatically longer than their straight-line counterparts — the
fish's 48-frame turn versus its 8-frame swim, the large creature's 152-frame turn versus its 8-frame
walk — because a direction reversal is the one moment these otherwise simple patrol loops get an
elaborate, hand-animated flourish (a fish arcing its body through the turn, a bulldozer's treads
visibly reversing) rather than an instant flip. [Chapter 32](ch32-creature-and-object-animation-catalog.md)'s
illustrated catalog shows every one of these sequences as a real contact sheet.

The `blupih`/`blupit` pair deserve one more note, precisely because their real data resolves an
otherwise-unconfirmed detail: `table_blupih_left[8]` (`Tables.cpp:1314`) contains icon values `66,
67, 68, ...` and `table_blupit_left[8]` (`Tables.cpp:1340`) contains `249, 249, 250, ...` — both
comfortably inside `blupi.png`'s addressable icon range (recall `blupi.png` is 600×2040 =
340 slots, [Chapter 29](ch29-sprite-atlas-system.md)), and their table names mirror the Blupi asset
family's naming convention. `Decor::MoveObjectStepIcon()` never explicitly assigns a `PixmapChannel`
for `ObjectType32`/`33` the way it does for every other patrol-creature type in the same function —
so their rendering channel is a reasoned inference from the data (every icon value these tables
produce falls inside `Blupi`'s range) rather than a directly observed assignment; `book/images/MANIFEST.md`
flags this explicitly as an inference, and this chapter preserves that same honesty rather than
upgrading it to a confirmed fact it is not.

## Explosion and effect tables

Eight numbered explosion tables — `table_explo1` through `table_explo8` — each supply a flat icon
sequence played on the `Explosion` channel (`explo.png`), consumed one entry per game tick by the
`MoveObjectStep()` dispatcher's per-`ObjectType` branches. Sizes range from 5 frames
(`table_explo8`) to 128 (`table_explo7`):

*From `Tables.cpp:1368-1426` (declarations, abridged):*
```cpp
const shortcs Tables::table_explo1[table_explo1Length] = { /* 39 entries */ };
const shortcs Tables::table_explo2[20] = { /* ... */ };
const shortcs Tables::table_explo3[20] = { /* ... */ };
const shortcs Tables::table_explo4[9] = {12, 13, 14, 15, 7, 8, 9, 10, 11};
const shortcs Tables::table_explo5[12] = { /* ... */ };
const shortcs Tables::table_explo6[6] = {54, 55, 56, 57, 58, 59};
const shortcs Tables::table_explo7[128] = { /* ... */ };
const shortcs Tables::table_explo8[5] = {7, 8, 9, 10, 11};
```

Each table is paired one-to-one with a dedicated `ObjectType` in `Decor::MoveObjectStep()`'s
explosion-lifecycle block (`ObjectType8` through `11`, and `90` through `93` — verified directly by
grepping every `Tables::table_explo{1..8}` reference in `Decor.cpp`, not inferred from numbering):

*From `Decor.cpp:8395-8490` (one representative branch of eight nearly-identical ones):*
```cpp
if (m_moveObject[i].type == ObjectType::ObjectType8)
{
    if (m_moveObject[i].phase / Config::ScaleDiv(1) >= Tables::table_explo1Length)
    {
        m_moveObject[i].type = ObjectType::ObjectType0;   // self-despawn once the sequence ends
    }
    else
    {
        m_moveObject[i].icon = Tables::table_explo1[m_moveObject[i].phase / Config::ScaleDiv(1)];
        m_moveObject[i].channel = PixmapChannel::Explosion;
    }
}
```

Every one of the eight branches follows this identical shape: index the table by the scaled phase,
assign `PixmapChannel::Explosion`, and self-despawn (revert to `ObjectType0`, the null/inactive
slot) the instant the phase runs past the table's length — there is no looping explosion in this
family; all eight play exactly once and vanish. [Chapter 33](ch33-explosions-and-effects.md) covers,
with real `Decor.cpp` trigger call sites for each of the eight, *what specific gameplay event*
spawns each one — this chapter's job is only the data format.

`table_explo_size[100]` is the companion table that makes `Explosion`-channel sprites variably sized
rather than locked to the atlas's uniform 144×144 stride (Chapter 29's `GetSrcRectangle()` coverage):

*From `Tables.cpp:2088-2103` (header comment plus real data, abridged):*
```
Observed values and their channel ranges:
  128 — channels 0-65, 87-89:  standard blast / debris.
  64  — channels 60-65, 70-86, 90-99: small fragment / spark.
  144 — channels 66-68:        oversized mega-blast (e.g. TNT crate).
```
```cpp
const shortcs Tables::table_explo_size[100] =
{
    128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
    // ... (channels 0-59 are all 128) ...
    64, 64, 64, 64, 64, 64, 144, 144, 144, 128,
    // ... (channel 66-68 are the 144 "mega-blast" outliers) ...
};
```
Reading the real data confirms the header comment's summary directly: the table is overwhelmingly
`128` (the standard blast bounding box) for the first sixty channels, with a short run of `64`
(small-fragment) values starting at channel 60, a three-entry spike to `144` at channels 66–68 (the
single largest bounding box used anywhere in the explosion system), and further `64`-valued stretches
beyond that. This is indexed directly by the *icon* value inside a `table_explo*` sequence, not by
the explosion table number itself — `table_explo_size[icon]` in `GetSrcRectangle`'s `Explosion`
case (Chapter 29) is keyed on whichever specific frame is currently playing, so a single explosion
sequence can legitimately mix frame sizes as it plays if its icon values happen to span more than
one of these size bands.

## Smaller effect tables not covered by the illustrated chapters

A number of `Tables` members are real, documented animation data that `tools/extract_sprites.py`'s
scope did not turn into standalone contact sheets — either because their consuming `ObjectType`
was already covered by a different table in [Chapter 32](ch32-creature-and-object-animation-catalog.md),
or because they drive a hazard directly inside `Decor::Build()`'s tile-rendering pass
([Chapter 16](../part04-decor-simulation/ch16-tile-map.md)) rather than through a `MoveObject`
slot. Recorded here for completeness, since this chapter's job is the data layer in full:

- **`table_sploutch1`/`_2`/`_3`** (10/13/18 frames) — three graduated water-entry splash sizes,
  consumed by `ObjectType98`/`99`/`100` respectively (`decor/ObjectType.hpp:149-151`). Each longer
  variant's header comment describes progressively more leading `-1` (blank) frames — 3 for
  `table_sploutch2`, 8 for `table_sploutch3` — producing a longer pause before the splash actually
  appears, consistent with a bigger fall needing a longer "impact is imminent" beat before the
  splash itself plays.
- **`table_tentacule`** (45 frames) — a tentacle hazard's rise/hold/retract cycle, with `-1` blanks
  at frame 7 and the final frame producing a snap-hide effect at both ends of the motion
  (`Tables.hpp:408-414`).
- **`table_marine`** (11 frames) and **`table_ressort`** (8 frames) — the sea-mine spin cycle and
  the spring/coil compress-release cycle respectively, both driving `m_bigDecor`-layer tile
  animation directly inside `Decor::Build()` rather than a `MoveObject` slot
  ([Chapter 16](../part04-decor-simulation/ch16-tile-map.md) covers `table_marine`'s specific
  `m_bigDecor` call site).
- **`table_decor_lave`, `table_decor_piege1`/`_2`, `table_decor_goutte`, `table_decor_ecraseur`,
  `table_decor_scie`, `table_decor_temp`, `table_decor_eau1`/`_2`** — lava, spike-trap, dripping
  water, crusher, saw, temperature, and water-surface tile animations, all consumed directly inside
  `Decor::Build()`'s per-tile animated-icon remapping pass ([Chapter 16](../part04-decor-simulation/ch16-tile-map.md)
  shows the `table_decor_lave`/`table_decor_piege1`/`table_decor_piege2` call sites in full as a
  representative sample of this whole family's consumption pattern).
- **`table_decor_ventillog`/`_d`/`_h`/`_b`** and **`table_decor_ventg`/`_d`/`_h`/`_b`** — four-way
  (left/right/up/down) fan-blade and wind-vent-particle animations, each a short 3- or 4-frame loop
  selected by the specific fan/vent tile's facing direction.
- **`table_shield_blupi`**, **`table_magicloop`**, **`table_shieldloop`**, **`table_drinkeffect`** —
  small looping shimmer effects (5–16 frames each) layered directly on top of Blupi's own sprite
  while a shield, magic-loop, or drink power-up is active, distinct from the *pickup* animations
  `table_shield`/`table_magictrack`/`table_shieldtrack` catalogued via their `ObjectType` in
  [Chapter 32](ch32-creature-and-object-animation-catalog.md) — the pickup and the on-Blupi overlay
  are two separate tables even when (as with `table_shield`/`table_shield_blupi`) they hold
  identical data.
- **`table_chenille`/`table_chenillei`** (6 frames each) — a caterpillar-style forward/reverse crawl
  cycle (`chenille` is French for caterpillar), consumed directly by `ObjectType47`/`48`'s
  platform-lift carry-bonus tiles inside `Decor::MoveObjectStepIcon()` (`Decor.cpp:8196-8200`:
  `if (type == ObjectType47) icon = table_chenille[phase/2 % 6];` /
  `if (type == ObjectType48) icon = table_chenillei[phase/2 % 6];`) rather than by any creature
  covered in [Chapter 32](ch32-creature-and-object-animation-catalog.md).
- **`table_drinkoffset`** (3 entries) — not an icon sequence at all, but three byte *offsets into
  `table_blupi` itself*, marking where the `Drink` action's three animation phases begin
  (`Tables.hpp:729-739`) — a small, self-referential index into the very same packed-record table
  this chapter opened with, used to jump directly into a sub-range of `Drink`'s frames rather than
  always starting from the top of its record.
- **`world_terminal`** (30 entries) — not animation data at all, but 15 `(tile-x, tile-y)`
  coordinate pairs positioning the decorative trophy/portal tiles shown on the end-of-game victory
  screen (`Tables.hpp:987-995`) — included here only because it lives in the same `Tables` class,
  not because it drives any sprite-frame sequencing.

## Tile-adaptation tables: a brief cross-reference

`table_decor_quart[7056]` and `table_adapt_decor[144]`/`table_adapt_fromage[32]` drive the
collision-classification and auto-tiling systems covered in full in
[Chapter 16](../part04-decor-simulation/ch16-tile-map.md) (`IsPassIcon()`/`IsBlocIcon()`'s
16-quarter-tile lookup, and `AdaptMidBorder()`'s 4-neighbor-bitmask border auto-tiler,
respectively). This chapter does not repeat that analysis — it belongs to Part IV's Decor coverage,
not Part V's rendering coverage — but it is worth naming here precisely because these two tables
share the same `Tables` class and the same "flat array, arithmetic-derived record boundaries"
design philosophy as every animation table above: `table_decor_quart`'s 7,056 entries are logically
`icon * 16 + subTileIndex`, and `table_adapt_decor`'s 144 entries are 9 terrain-family rows of 16
neighbor-bitmask columns each — the same "big flat array, index arithmetic recovers structure"
pattern this whole chapter has been describing for animation data, applied instead to tile geometry.

## The mutable exception: `table_training1`–`4` and `Init()`

Every table this chapter has covered so far is `const` — genuinely immutable, baked-in game data.
`table_training1` through `table_training4` are the sole exception, declared `static` but *not*
`const` (`Tables.hpp:922, 933, 943, 953`), because they hold the tutorial levels' hint-text tile
records, and each 6-element record's final slot is a localized text-resource ID that has to be
patched in at runtime rather than baked into the binary:

*From `Tables.hpp:907-921`:*
```cpp
/**
 * @brief Tutorial level 1 tile layout and hint data (133 entries, mutable).
 * @details Records are 6 elements wide:
 *   [0] start tile index, [1] end tile index,
 *   [2] minimum tile row (0 = any), [3] maximum tile row (50 = full height),
 *   [4] action flag (-1 = no restriction),
 *   [5] localised text-resource ID -- patched by Init().
 * The table terminates with a -1 sentinel in element [0] of the last record.
 */
static shortcs table_training1[133];
```

`Tables::Init()` is the one function in this entire class that actually executes logic rather than
just declaring data — called exactly once at startup, idempotently (a static flag prevents
re-running), it walks each of the four training tables and overwrites the localized text-ID slot in
every 6-element record with the correct resource ID sourced from `MyResource`
([Chapter 46](../part08-data-persistence-content/ch46-myresource-resource-management.md)) for the
player's current language. `table_training2`, `_3`, and `_4` document exactly how many text slots
each contains (5, 11, and 5 respectively) — a small, precisely-bounded mutation of otherwise
completely static game data, and the only place in the `Tables` class where "do not renumber,
reorder, or resize" (this chapter's opening quote) does not also imply "never write to it."

## See also

- [Chapter 16 — The Tile Map](../part04-decor-simulation/ch16-tile-map.md)
- [Chapter 17 — Blupi: the State Machine](../part04-decor-simulation/ch17-blupi-state-machine.md)
- [Chapter 18 — Blupi Actions and Animation](../part04-decor-simulation/ch18-blupi-actions-and-animation.md)
- [Chapter 19 — Moving Objects and Decor Actions](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md)
- [Chapter 20 — Enemy and Creature AI](../part04-decor-simulation/ch20-enemy-and-creature-ai.md)
- [Chapter 29 — The Sprite Atlas System](ch29-sprite-atlas-system.md)
- [Chapter 31 — The Blupi Animation Catalog](ch31-blupi-animation-catalog.md)
- [Chapter 32 — The Creature and Object Animation Catalog](ch32-creature-and-object-animation-catalog.md)
- [Chapter 33 — Explosions and Effects](ch33-explosions-and-effects.md)
- [Chapter 46 — MyResource: Resource Management](../part08-data-persistence-content/ch46-myresource-resource-management.md)
