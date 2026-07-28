# Appendix C: Level File Format Specification

This appendix is the dense, field-by-field reference companion to
[Chapter 44](../part08-data-persistence-content/ch44-worlds-level-file-format.md), which develops
the same material narratively with fuller code citations. Everything below is grounded in the same
two sources: `Worlds.hpp`/`Worlds.cpp` (the generic parser/serializer) and `Decor.cpp`'s
`Read`/`CurrentRead`/`CurrentWrite` methods (the format's two concrete consumers), cross-checked
against real files sampled from `mobile-eggbert/worlds/` (78 files, `world001.txt`–`world199.txt`).

<!-- TODO: embed level-map diagram from tools/render_level_map.py output once available -->

At the time this appendix was written, `book/images/MANIFEST.md` did not exist, so no
`level-map-<worldfile-stem>.png` data-reconstruction diagram is referenced here. The worked example
below is table/text-only.

## C.1 Two file kinds, one grammar

| Kind | Path convention | Written by | Read by | Filesystem backend |
|---|---|---|---|---|
| Level design file | `worlds/worldNNN.txt` (NNN = zero-padded rank) | original level editor (offline, not in this codebase) | `Decor::Read(gamer, rank, bUser)` (`Decor.cpp:11304`) via `Worlds::ReadWorld` (`Worlds.cpp:142`) | Game content asset (`TitleContainer`), read-only |
| Quick-save | `CurrentGame` (fixed name) | `Decor::CurrentWrite()` (`Decor.cpp:10986`) | `Decor::CurrentRead()` (`Decor.cpp:11143`) via `Worlds::ReadCurrentGame`/`WriteCurrentGame` | `IsolatedStorageFile`, user-writable |

Both kinds share the section/field grammar defined in `Worlds.cpp`'s file-level comment; they
differ in field-name conventions (level files use bare names like `posDecor`; the quick-save wraps
every field name in underscores, `_posDecor_`) and in which sections appear (`Jauge:` and the
`_Doors_`/`_RankCaisse_`/etc. array fields inside `DescFile:` are quick-save-only).

## C.2 Formal grammar

*From `Worlds.cpp:11-26` (the parser's own EBNF-style documentation):*

```
<document>    ::= <section-line>* <decor-block>*
<section-line>::= <name> ": " <field>* "\n"
<field>       ::= <id> "=" <value> " "
<value>       ::= <int> | <double> | <bool> | <point> | <int-array>

<int>         ::= [-]?[0-9]+
<double>      ::= [-]?[0-9]+("."[0-9]+)?([eE][-+]?[0-9]+)?   (C locale)
<bool>        ::= "True" | "False"    (case-insensitive on read)
<point>       ::= <int> ";" <int>
<int-array>   ::= (<int>? ",")* <int>?   (empty slot = 0 for normal arrays,
                                          1 for doors arrays)

<decor-block> ::= <section-line-decor> <decor-row>*
<decor-row>   ::= (<int>? ",")* <int>? "\n"   (empty slot = -1 tile)
```

### C.2.1 Encoding rules by value type

| Type | Read function | Write function | Missing/malformed → | Notes |
|---|---|---|---|---|
| `int` | `Worlds::GetIntField` | `Worlds::WriteIntField` | `0` | Plain `std::stoi`-style decimal |
| `double` | `Worlds::GetDoubleField` | `Worlds::WriteDoubleField` | `0.0` | C locale, `std::setprecision(15)` on write |
| `bool` | `Worlds::GetBoolField` | `Worlds::WriteBoolField` | `false` | Literal `True`/`False`, case-insensitive read |
| `TinyPoint` | `Worlds::GetPointField` | `Worlds::WritePointField` | `{0,0}` | `x;y`, semicolon-separated |
| `int[]` (generic array) | `Worlds::GetIntArrayField` | `Worlds::WriteIntArrayField` | array unchanged | comma-separated; **zero values suppressed on write** (empty slot ⇒ `0` on read) |
| `int[]` (Doors array) | `Worlds::GetDoorsField` | `Worlds::WriteDoorsField` | n/a | comma-separated; **value-`1` entries suppressed on write** (empty slot ⇒ `1` on read — the opposite convention from a generic array) |
| Decor/BigDecor cell | `Worlds::GetDecorField` | `Worlds::WriteDecorField` | `std::nullopt` → `-1` at call site | comma-separated per row; **value-`-1` entries suppressed on write** (empty slot ⇒ `-1` on read) |

Three different "what does an empty comma slot mean" conventions coexist in the same file format,
each chosen so the *most common* value for that field never has to be spelled out — a simple,
effective compaction scheme, at the cost of the reader needing to know, out of band, which
convention applies to which section. Contrast `WriteIntArrayField` (`Worlds.cpp:631-647`, zero
suppressed) against `WriteDoorsField` (`Worlds.cpp:703-717`, one suppressed) against
`WriteDecorField` (`Worlds.cpp:687-701`, minus-one suppressed) to see all three encoded
side by side.

### C.2.2 Section/field lookup mechanics

Every scalar `Get*Field` call takes five parameters: the line array, its length, a `section` name,
a `rank` (zero-based occurrence index — which matching section line to use, for formats with
repeated sections like `MoveObject:`), and a field `name`. The lookup is a substring scan, not a
tokenizing parser: it finds the `rank`-th line beginning with `"<section>:"`, then finds
`"<name>="` within that line's text, then takes the substring up to the next space character
(`Worlds.cpp:387-419`, the shared `TryGetFieldValueText` helper). `GetDecorField(lines, lineCount,
section, x, y)` instead locates the section header line once, then indexes row `header_line + 1 +
x`, splits that row on commas, and returns element `y` (`Worlds.cpp:543-585`).

## C.3 The `DescFile:` section — level design files

Exactly one `DescFile:` line opens every `worlds/worldNNN.txt` file. Fields actually consumed by
`Decor::Read()` (`Decor.cpp:11320-11325`) are marked **read**; fields present in every sampled file
but never queried by the loader are marked **dead**.

| Field | Type | Status | Meaning | Example (`world001.txt`) |
|---|---|---|---|---|
| `posDecor` | point | read | Initial camera/scroll position, pixels | `250;5570` |
| `dimDecor` | point | read | Tile-grid dimensions; always `100;100` in every sampled file | `100;100` |
| `world` | int | **dead** | Written by the level editor; never read by `Decor::Read()`. Value is `0` in all 78 shipped files, with no exception found. | `0` |
| `music` | int | read | Music track index; observed values `0`–`10` across all 78 files | `0` |
| `region` | int | read | Selects `Content/backgrounds/decorNNN.png`; see [Chapter 45](../part08-data-persistence-content/ch45-content-pipeline.md) | `0` |
| `blupiPos` | point | read (into `m_blupiStartPos`) | Blupi's starting pixel position | `770;5894` |
| `blupiDir` | int | read (into `m_blupiStartDir` via `ToDirection`) | Starting facing direction; only `1` or `2` observed across all sampled files | `2` |

*From `worlds/world001.txt:1`:*
```
DescFile: posDecor=250;5570 dimDecor=100;100 world=0 music=0 region=0 blupiPos=770;5894 blupiDir=2 
```

Sampled `DescFile:` headers across files of varying size, confirming the field set and value
ranges above are stable across the whole corpus:

| File | Size (bytes) | `posDecor` | `music` | `region` | `blupiPos` | `blupiDir` |
|---|---|---|---|---|---|---|
| `world001.txt` | 20,357-ish tier (small) | `250;5570` | `0` | `0` | `770;5894` | `2` |
| `world010.txt` | small | `200;2700` | `10` | `0` | `578;3078` | `2` |
| `world080.txt` | 20,357 (smallest sampled) | `350;2400` | `0` | `26` | `770;2694` | `2` |
| `world100.txt` | 20,541 | `850;3150` | `0` | `2` | `1090;3398` | `2` |
| `world045.txt` | 47,869 | `100;300` | `6` | `3` | `386;454` | `2` |
| `world122.txt` | 46,968 | `1500;4120` | `10` | `24` | `1794;4358` | `2` |
| `world199.txt` | 75,770 (largest) | `4082;0` | `1` | `31` | `4482;6` | `2` |

## C.4 The `DescFile:` section — quick-save (`CurrentGame`)

The quick-save's `DescFile:` line uses underscore-wrapped field names and carries roughly 80
fields — the entire live `Decor` simulation state — rather than the seven static fields of a level
file. Selected fields (full list: `Decor.cpp:10989-11075`):

| Field | Type | Meaning |
|---|---|---|
| `_version_` | int | Always written as `1`; format-version tag, not cross-checked on read |
| `_posDecor_`, `_dimDecor_` | point | Live camera position / grid dimensions |
| `_music_`, `_region_`, `_time_` | int | Current track, region, and elapsed tick counter |
| `_blupiPos_`, `_blupiValidPos_` | point | Live position and last-known-safe position |
| `_blupiAction_`, `_blupiDir_`, `_blupiPhase_` | int (enum-backed) | Current `BlupiAction`/`Direction`/animation phase |
| `_blupiVitesseX_`, `_blupiVitesseY_` | double | Current velocity components |
| `_blupiSec_` | int (enum-backed, `SecretPower`) | **The player's currently-held secret power** — session-only, see [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md) |
| `_blupiHelico_`, `_blupiJeep_`, `_blupiTank_`, `_blupiSkate_`, `_blupiNage_`, `_blupiSurf_`, `_blupiShield_`, `_blupiPower_`, `_blupiCloud_`, `_blupiHide_`, … | bool | Roughly 20 independent "is Blupi currently doing/holding X" flags |
| `_mission_`, `_nbVies_`, `_nbTresor_`, `_totalTresor_` | int | Mission number, lives, treasure counters |
| `_RankCaisse_`, `_LinkCaisse_`, `_BalleTraj_`, `_MoveTraj_` | int[] | Crate-stack and trajectory-occupancy arrays |
| `_Doors_` | int[] (doors convention) | The live 200-entry door array, exchanged with `GameData` via `MemorizeDoors`/`InitializeDoors` |

`Decor::CurrentRead()` starts every load from a fresh `InitDecor()` baseline before overwriting
these fields (`Decor.cpp:11150`), so any field this list omits — or any field added to
`CurrentWrite()` without a matching `CurrentRead()` counterpart — silently resets to `InitDecor()`'s
default on the next quick-load rather than persisting.

## C.5 The `Decor:` and `BigDecor:` blocks — the tile grids

| Property | Value |
|---|---|
| Section headers | `Decor: ` / `BigDecor: ` (bare, no inline fields) |
| Row count | 100 (fixed; matches `dimDecor=100;100`) |
| Columns per row | 100 |
| Cell separator | `,` (comma) |
| Empty cell meaning | `-1` (no tile) |
| Row addressing | Row `x` of section `S` is line `(header_line_index_of_S) + 1 + x` |
| Loader normalization (level files only) | A literal cell value of `0` is *also* folded to `-1` (`decorField != 0 ? decorField : -1`, `Decor.cpp:11331`); the quick-save loader does **not** apply this extra fold (`Decor.cpp:11245`, plain `value_or(-1)`) |
| In-memory destination | `m_decor[column][row].icon` (level file, `Decor::Read`) / `m_decor[row][column].icon` addressing is transposed via the `(j, i)` argument order at the call site — see [Chapter 16](../part04-decor-simulation/ch16-tile-map.md) for the full coordinate-system discussion |

`BigDecor:` is a structurally identical second grid, rendered as its own decoration overlay layer
between the parallax background and the foreground tiles (`Decor::Build()`, `Decor.cpp:636-648`,
`m_bigDecor[][]`). It is sparsely populated in most sampled files — zero non-empty cells in
`world080.txt`, three in `world001.txt`, 235 in the much larger `world199.txt` — confirming it is
used only where a level's design calls for large background set-pieces, not as a mandatory layer.

## C.6 The `MoveObject:` sections

| Property | Level file (`Decor::Read`) | Quick-save (`Decor::CurrentRead`) |
|---|---|---|
| Packing | Dense: occurrence `n` ⇒ slot `n` of `m_moveObject[]` | Sparse: each record carries its own `index` field |
| Terminator | First record with `type=0` stops the scan | Same |
| Fields | `type`, `stepAdvance`, `stepRecede`, `timeStopStart`, `timeStopEnd`, `posStart`, `posEnd`, `posCurrent`, `step`, `time`, `phase`, `channel`, `icon` | Same fields, plus `index` |
| Time-field scaling | All four timing fields passed through `Config::ScaleTime()` on load | Same |
| Special-case override | `ObjectType::ObjectType54` gets `timeStopStart`/`timeStopEnd` hard-set to `Config::ScaleTime(152)` regardless of file content | Not present in `CurrentRead` |

*From `worlds/world001.txt:204`, the file's single `MoveObject:` record:*
```
MoveObject: type=7 stepAdvance=1 stepRecede=1 timeStopStart=0 timeStopEnd=0 posStart=962;5124 posEnd=962;5124 posCurrent=962;5124 step=1 time=0 phase=800 channel=10 icon=31 
```

Record counts observed across the sample: `world001.txt` has 1; `world199.txt` (the largest file)
has 196.

## C.7 The `Jauge:` sections (quick-save only)

Two `Jauge:` lines close out every `CurrentGame` file, one per HUD gauge slot (`Decor.cpp:11121-
11128`), each carrying `hide` (bool), `mode` (int, `JaugeMode`-backed), and `level` (int). Never
present in level design files. See
[Chapter 36](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md).

## C.8 File I/O method reference

| Method | File | Purpose | Implementation status |
|---|---|---|---|
| `Decor::CurrentDelete()` | `Decor.cpp:10974` | Deletes the `CurrentGame` quick-save | Forwards to `Worlds::DeleteCurrentGame()`; fully working |
| `Decor::CurrentWrite()` | `Decor.cpp:10986` | Serializes live simulation state to `CurrentGame` | Fully working |
| `Decor::CurrentRead()` | `Decor.cpp:11143` | Deserializes `CurrentGame` into live state | Fully working; starts from `InitDecor()` baseline |
| `Decor::Read(gamer, rank, bUser)` | `Decor.cpp:11304` | Loads `worlds/worldNNN.txt` | Fully working |
| `Decor::Delete(gamer, rank, bUser)` | `Decor.cpp:11379` | Intended to delete a level file | **Stub**: always returns `true`, never touches storage |
| `Decor::FileExist(gamer, rank, bUser)` | `Decor.cpp:11387` | Intended to check level-file existence | **Stub**: always returns `false` |
| `Decor::SearchWorld(world, blupi, dir)` | `Decor.cpp:11398` | Finds a world's terminal-marker icon, returns a passable adjacent cell | Fully working; `world` valid range `0`–`12` |
| `Decor::SearchDoor(n, cel, blupi)` | `Decor.cpp:11439` | Finds numbered door-sign icons (`174`–`181`) and adjacent door tile (`182`) | Fully working |
| `Decor::SearchGold(n, cel)` | `Decor.cpp:11486` | Finds the first gold-marker icon (`183`), scanning bottom-right to top-left | Fully working; `n` accepted but unused for disambiguation |

`Worlds::GetWorldFilename(gamer, rank)` (`Worlds.cpp:184-196`) constructs the on-disk path as
`"worlds/world" + ToString(rank, 3) + ".txt"` — `gamer` is accepted for original-API compatibility
but unused; level content does not vary per gamer slot.

## C.9 Worked example: `world001.txt`

`world001.txt` is the smallest level file examined for this book and the game's very first stage.
Its complete `DescFile:` header:

*From `worlds/world001.txt:1`:*
```
DescFile: posDecor=250;5570 dimDecor=100;100 world=0 music=0 region=0 blupiPos=770;5894 blupiDir=2 
```

Interpreting each field per the table in §C.3: the camera starts at pixel `(250, 5570)` — deep into
the 6400×6400-pixel map (100 tiles × 64px) — matching the fact that this level's action does not
take place near the map's origin; `music=0` selects the first music track; `region=0` selects
`Content/backgrounds/decor000.png` as the visible per-region art
([Chapter 45](../part08-data-persistence-content/ch45-content-pipeline.md)); Blupi starts at pixel
`(770, 5894)` facing direction `2`.

A short excerpt from row 9 of the `Decor:` block (0-based row index 6, i.e. `y = 6` in
`Worlds::GetDecorField` terms — the seventh physical line of the block, first non-trivial row in
the sample), truncated to its non-empty tail:

*From `worlds/world001.txt:9` (right-hand tail of the row):*
```
...,10,10,10,10,10,,10,10,10,10,10,10,10,,,,10,163,10,162,10,159,10,309,10,412,10,413,10,10,10,10,10,10,
```

Annotating a few of the real icon values that appear in this row, cross-referencing the raw
`Is*()` predicates read directly from `Decor.cpp` (there is no `ch26` tile-and-icon catalog chapter
committed at the time this appendix was written, so predicates are cited directly rather than via
that catalog):

| Icon value | What the code says about it | Citation |
|---|---|---|
| `10` | Classified via `Tables::table_decor_quart[icon*16 .. icon*16+15]` inside `Decor::IsBlocIcon`/`Decor::IsPassIcon` — whether all 16 of its per-quarter-cell lookup entries are zero (passable) or non-zero (blocking) determines collision behaviour; `10` recurs constantly across every sampled level as filler terrain, consistent with a common solid-ground classification | `Decor.cpp:7503-7540` |
| `163`, `162`, `159`, `309`, `412`, `413` | Not matched by any of the specific numeric checks read for this appendix (`IsLave`'s `68`, `IsPiege`'s `373`, door range `174`–`182`, gold's `183`); their gameplay classification, like `10`'s, ultimately flows through the same `table_decor_quart`/`IsBlocIcon`/`IsPassIcon` machinery and the many other named `Is*()` predicates in `Decor.cpp` not exhaustively cross-referenced here | `Decor.cpp:7503-7540` (mechanism); full per-icon enumeration is [Chapter 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md)'s job once written |

Two icon values *are* precisely documented elsewhere in this codebase and are worth calling out
even though they do not happen to appear in this particular nine-cell excerpt: icon `68` is lava
(`Decor::IsLave`, `Decor.cpp:7195-7203`, checked via `m_decor[pos.X/64][pos.Y/64].icon == 68`), and
icon `373` is a trap (`Decor::IsPiege`, `Decor.cpp:7205-7218`, `icon == 373`). Icon `183` is the
game's gold/treasure marker, checked directly by `Decor::SearchGold` (`Decor.cpp:11492`,
`m_decor[num2][num].icon == 183`); door signs occupy the contiguous range `174`–`181` (door number
= `icon - 174 + 1`), with the physical door tile itself at icon `182`
(`Decor::SearchDoor`, `Decor.cpp:11446-11448`).

This is the concrete evidence behind the structural claim (`PLAN.md`, confirmed while researching
this appendix and [Chapter 44](../part08-data-persistence-content/ch44-worlds-level-file-format.md))
that `m_decor[][]`'s numeric icon values are an **invisible gameplay-classification layer**, wholly
separate from the visible per-region background art loaded via `Pixmap::BackgroundCache` — nothing
in this appendix's icon-lookup chain (`IsLave`, `IsPiege`, `IsBlocIcon`/`IsPassIcon` via
`table_decor_quart`, the door-range checks, `SearchGold`) ever calls
`Pixmap::DrawIcon(PixmapChannel::Element, icon, ...)` with these raw tile-grid values to draw
visible sprite art; `MAXQUART = 441` (`Decor.hpp:187`) is itself larger than the `Element` channel's
own 290-icon atlas capacity (`element.png`, 600×1740 px at a 60×60 grid — see `PLAN.md`'s sprite
atlas table), which would be a contradiction if these numbers were meant to directly index a visible
sprite sheet.

## See also

- [Chapter 15: Decor — Overview](../part04-decor-simulation/ch15-decor-overview.md)
- [Chapter 16: The Tile Map](../part04-decor-simulation/ch16-tile-map.md) — the coordinate systems
  and background/collision-layer split referenced throughout §C.5 and §C.9.
- [Chapter 19: Moving Objects and Decor Actions](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md)
- [Chapter 23: Secret Powers and the Cheat System](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md)
  — `_blupiSec_` and `SearchGold`'s cheat-driven callers.
- [Chapter 26: Tile and Icon Catalog](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) —
  the fuller per-icon reference this appendix's §C.9 defers to.
- [Chapter 36: Jauge — HUD Gauges](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md)
- [Chapter 43: GameData — Save Format](../part08-data-persistence-content/ch43-gamedata-save-format.md)
- [Chapter 44: Worlds — Level File Format](../part08-data-persistence-content/ch44-worlds-level-file-format.md)
  — the narrative companion to this appendix.
- [Chapter 45: Content Pipeline](../part08-data-persistence-content/ch45-content-pipeline.md) —
  the `region=` field's downstream effect on visible background art.
