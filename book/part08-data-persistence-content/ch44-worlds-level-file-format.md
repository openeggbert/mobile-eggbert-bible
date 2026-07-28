# Chapter 44: Worlds — the Level File Format

## Overview

Every playable stage in Mobile Eggbert — 78 of them, `worlds/world001.txt` through
`worlds/world199.txt`, ranging from 20 KB to 76 KB of plain text — is described by a single text
file in a compact, line-oriented, key/value format. The class responsible for reading and writing
this format is `Worlds` (`Worlds.hpp`, 540 lines; `Worlds.cpp`, 728 lines), a static-only helper:
it cannot be instantiated (`Worlds() = delete;`), and every one of its members is a `static`
function operating on caller-supplied line arrays or on a private, shared `StringBuilder` output
buffer.

`Worlds` actually serves **two** related but distinct file formats that share the same low-level
grammar:

1. **Level design files** (`worlds/worldNNN.txt`) — read-only content shipped with the game,
   produced by the original level editor, describing a level's fixed geometry: the tile grid,
   decorative overlay grid, moving-object definitions, and Blupi's starting position. Loaded by
   `Decor::Read()` (`Decor.cpp:11304`).
2. **The `CurrentGame` quick-save** — a single, in-progress-session save file (not one of the three
   `GameData` gamer slots from [Chapter 43](ch43-gamedata-save-format.md), but a snapshot of the
   *live simulation* — Blupi's exact position, held items, timers, active moving-object states, and
   so on) written by `Decor::CurrentWrite()` and read by `Decor::CurrentRead()`
   (`Decor.cpp:10986`, `Decor.cpp:11143`).

Both formats are built from the same section/field grammar implemented by `Worlds`'s `Get*Field`
and `Write*Field` methods; they differ only in *which* field names appear under the `DescFile`
section, and in some fine details of how the `Decor` and `MoveObject` sections get filled back in.
This chapter documents the shared grammar first, then each format's specific field set, grounded in
real files from `mobile-eggbert/worlds/`.

## The file-format grammar

The clearest formal description of the grammar is the block comment at the top of `Worlds.cpp`
itself, which the C++ port's author wrote as an EBNF-flavoured summary of the original C#
serializer's behaviour:

*From `Worlds.cpp:7-26`:*
```
 * ### File format grammar (detailed)
 * Every save document produced by the Write* methods (and consumed by the Get*
 * methods) follows this structure:
 *
 * ```
 * <document>   ::= <section-line>* <decor-block>*
 * <section-line>::= <name> ": " <field>* "\n"
 * <field>      ::= <id> "=" <value> " "
 * <value>      ::= <int> | <double> | <bool> | <point> | <int-array>
 *
 * <int>        ::= [-]?[0-9]+
 * <double>     ::= [-]?[0-9]+("."[0-9]+)?([eE][-+]?[0-9]+)?   (C locale)
 * <bool>       ::= "True" | "False"    (case-insensitive on read)
 * <point>      ::= <int> ";" <int>
 * <int-array>  ::= (<int>? ",")* <int>?   (empty slot = 0 for normal arrays,
 *                                           1 for doors arrays)
 *
 * <decor-block>::= <section-line-decor> <decor-row>*
 * <decor-row>  ::= (<int>? ",")* <int>? "\n"   (empty slot = -1 tile)
 * ```
```

In plain terms: the file is a sequence of lines. Most lines are **section headers** carrying inline
`name=value` fields separated by spaces (`Decor:` and `BigDecor:` are the two exceptions — their
header lines carry no fields, and are instead followed by 100 raw data rows each). Field values use
five encodings, chosen per field by convention (there is no type tag in the file itself — the
reader and writer must agree out-of-band on each field's type, exactly as they do via the shared
constant field names).

### Reading a real `DescFile:` header line

Every level file begins with exactly one `DescFile:` line. Here is the complete first line of
`worlds/world001.txt`, the game's very first level:

*From `worlds/world001.txt:1`:*
```
DescFile: posDecor=250;5570 dimDecor=100;100 world=0 music=0 region=0 blupiPos=770;5894 blupiDir=2 
```

Breaking this down field by field, against the grammar above:
- `posDecor=250;5570` — a `<point>` (`x;y`): the initial scroll/camera position in pixels.
- `dimDecor=100;100` — a `<point>`: the tile-grid dimensions. Every one of the 78 level files uses
  `100;100` — the grid is always the full 100×100 `Decor::m_decor[][]` size (see
  [Chapter 16](../part04-decor-simulation/ch16-tile-map.md)); `dimDecor` is read but never actually
  varied in practice.
- `world=0` — an `<int>`. As detailed below, this field is **written to every level file but never
  read back by `Decor::Read()`** — it is dead data in the current C++ port.
- `music=0` — an `<int>`: which music track (`0`–`10` across the sample below) plays during this
  level.
- `region=0` — an `<int>`: selects which `Content/backgrounds/decorNNN.png` background image to
  load (see [Chapter 45](ch45-content-pipeline.md)).
- `blupiPos=770;5894` — a `<point>`: Blupi's starting pixel position.
- `blupiDir=2` — an `<int>`, later converted via `ToDirection()` to a `Direction` enum value.

The exact same seven fields appear, in the same order, at the top of every level file this book's
research sampled. Here are several more real header lines, showing the range of values actually
used in the shipped content:

| File | `posDecor` | `music` | `region` | `blupiPos` | `blupiDir` |
|---|---|---|---|---|---|
| `world001.txt` | `250;5570` | `0` | `0` | `770;5894` | `2` |
| `world010.txt` | `200;2700` | `10` | `0` | `578;3078` | `2` |
| `world045.txt` | `100;300` | `6` | `3` | `386;454` | `2` |
| `world080.txt` | `350;2400` | `0` | `26` | `770;2694` | `2` |
| `world100.txt` | `850;3150` | `0` | `2` | `1090;3398` | `2` |
| `world122.txt` | `1500;4120` | `10` | `24` | `1794;4358` | `2` |
| `world199.txt` | `4082;0` | `1` | `31` | `4482;6` | `2` |

*From `worlds/world010.txt:1`, `worlds/world080.txt:1`, `worlds/world199.txt:1` (source of the
table rows above).*

Scanning `music=` across all 78 shipped level files turns up exactly the values `0`–`10` (eleven
distinct music tracks); `blupiDir=` only ever takes the values `1` or `2` in the shipped content,
even though `Direction` (see [Chapter 17](../part04-decor-simulation/ch17-blupi-state-machine.md))
defines more directions than that — every level starts Blupi facing one of just two directions.

### The dead `world=` field

Grepping every `DescFile:` line across all 78 files in `worlds/` for the value of `world=` turns up
a single, universal value: `world=0`, with no exceptions. That alone is suspicious for a field whose
name suggests it should identify *which* world/region a level belongs to — and reading
`Decor::Read()`, the level-file loader, confirms why: it is never queried.

*From `Decor.cpp:11320-11325`:*
```cpp
        m_posDecor = Worlds::GetPointField(array, vectorSize, "DescFile", 0, "posDecor");
        m_dimDecor = Worlds::GetPointField(array, vectorSize, "DescFile", 0, "dimDecor");
        m_music = Worlds::GetIntField(array, vectorSize, "DescFile", 0, "music");
        m_region = Worlds::GetIntField(array, vectorSize, "DescFile", 0, "region");
        m_blupiStartPos = Worlds::GetPointField(array, vectorSize, "DescFile", 0, "blupiPos");
        m_blupiStartDir = ToDirection(Worlds::GetIntField(array, vectorSize, "DescFile", 0, "blupiDir"));
```

Only five of the header's seven emitted fields (`posDecor`, `dimDecor`, `music`, `region`,
`blupiPos`, `blupiDir` — six, correcting the count) are consumed on load; `world` is written by
whatever produced these files (the original level editor) but is entirely inert in the running
game. Which mission/world a level belongs to is instead derived at runtime purely from the mission
number passed into `Decor::Read(gamer, rank, bUser)` and the filename convention (see below) — not
from anything stored inside the file.

### The `Decor:` block — the tile grid

Immediately after the `DescFile:` line comes a `Decor:` section header (with no inline fields —
just the bare `"Decor: "` prefix and a newline), followed by exactly 100 data rows, one per tile
column, each row holding 100 comma-separated integer cells (one per tile row).

*From `worlds/world001.txt:2-6` (rows 1–4 of the grid, right-hand portion only, for width):*
```
Decor: 
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,10,10,10,10,10,10,,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,10,,,,,10,,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,10,,,,,10,,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,
```

An **empty comma slot means "no tile"** — the cell reads back as `-1`, not `0`. This is handled by
`Worlds::GetDecorField`:

*From `Worlds.cpp:543-585`:*
```cpp
    std::optional<intcs> Worlds::GetDecorField(
        const string lines[],
        intcs lineCount,
        const string& section,
        intcs x,
        intcs y)
    {
        for (intcs i = 0; i < lineCount; i++)
        {
            string text = lines[i];
            if (String::StartsWith(text, section + ":"))
            {
                const intcs rowIndex = i + 1 + x;
                ...
                text = lines[rowIndex];
                const std::vector<std::string> parts = String::Split(text, ',');

                if (y < 0 || y >= static_cast<intcs>(parts.size()))
                {
                    return std::nullopt;
                }

                if (parts[y].empty())
                {
                    return static_cast<intcs>(-1);
                }
                ...
```

The row index is computed as `i + 1 + x` — the section header line plus a one-based row offset —
which is why `GetDecorField` needs the *line index* of the `Decor:` header rather than a raw row
array: rows are addressed relative to their section header, not from the start of the file. The
double loop in `Decor::Read()` walks `x` (row/column index) as the outer variable and `y` as the
inner one, filling `m_decor[j][i]` — i.e. the file's row-major layout is transposed into
`m_decor`'s `[column][row]` indexing during load:

*From `Decor.cpp:11326-11333`:*
```cpp
        for (int i = 0; i < 100; i++)
        {
            for (int j = 0; j < 100; j++)
            {
                int decorField = Worlds::GetDecorField(array, vectorSize, "Decor", j, i).value_or(-1);
                m_decor[j][i].icon = decorField != 0 ? decorField : -1;
            }
        }
```

Notice the extra normalization here, specific to **level files** (not the quick-save format): a
decor value of literal `0` is *also* folded to `-1` (empty), via `decorField != 0 ? decorField : -1`.
This is a level-editor convention: the editor evidently used `0` to mean "no tile" internally, so
`Decor::Read()` treats both an empty CSV slot *and* an explicit `0` as "nothing here." Compare this
to `Decor::CurrentRead()` (the quick-save loader), which uses the raw `value_or(-1)` with no such
`!= 0` check (`Decor.cpp:11245`) — a `0` icon value written into a quick-save is taken at face
value, because the live simulation state was serialised by `Decor::CurrentWrite()` itself and
never went through the level editor's `0`-means-empty convention.

### The `BigDecor:` block — the overlay decoration layer

Immediately after the 100 rows of `Decor:` comes a second, structurally identical block headed
`BigDecor:`, also 100 rows of 100 comma-separated values:

*From `worlds/world001.txt:103` (header only shown):*
```
BigDecor: 
```

`m_bigDecor[][]` is a separate 100×100 grid from `m_decor[][]`, drawn as its own render pass in
`Decor::Build()` layered between the parallax background and the foreground tiles/objects/Blupi
(`Decor.cpp:636-648`). Most sample files have a `BigDecor:` block that is almost entirely empty —
`world080.txt` has zero non-empty cells in its `BigDecor:` block, `world001.txt` has three, while
the large `world199.txt` has 235 — confirming this is a sparse decoration layer used for larger
set-piece background objects, used only where a level actually needs one, not a mandatory content
layer.

### The `MoveObject:` sections — moving-object records

After both 100-row grids, the file lists zero or more `MoveObject:` sections, one line each, one
section per active moving object placed in the level (lifts, sliding platforms, projectile
sources, and other `ObjectType` entities — see
[Chapter 19](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md)):

*From `worlds/world001.txt:204`:*
```
MoveObject: type=7 stepAdvance=1 stepRecede=1 timeStopStart=0 timeStopEnd=0 posStart=962;5124 posEnd=962;5124 posCurrent=962;5124 step=1 time=0 phase=800 channel=10 icon=31 
```

In a **level file**, `MoveObject` records are packed *densely*: the loader assumes record `n`
(the zero-based occurrence count of `MoveObject:` lines in the file) corresponds directly to slot
`n` of the in-memory `m_moveObject[MAXMOVEOBJECT]` array, and it stops scanning at the first record
whose `type` field is `0`:

*From `Decor.cpp:11346-11371`:*
```cpp
        for (int n = 0; n < MAXMOVEOBJECT; n++)
        {
            int intField = Worlds::GetIntField(array, vectorSize, "MoveObject", n, "type");
            if (intField == 0)
            {
                break;
            }
            m_moveObject[n].type = ToObjectType(intField);
            m_moveObject[n].stepAdvance = Config::ScaleTime(Worlds::GetIntField(array, vectorSize, "MoveObject", n, "stepAdvance"));
            ...
            if (m_moveObject[n].type == ObjectType::ObjectType54)
            {
                m_moveObject[n].timeStopStart = Config::ScaleTime(152);
                m_moveObject[n].timeStopEnd = Config::ScaleTime(152);
            }
        }
```

Two details worth flagging: every time-based field (`stepAdvance`, `stepRecede`, `timeStopStart`,
`timeStopEnd`) is passed through `Config::ScaleTime()` on load, so a level authored assuming one
frame-rate/timing model plays back correctly under the project's configurable LEGACY/MODERN timing
(see [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md)); and objects of
`ObjectType::ObjectType54` get a hard-coded override of both stop-timer fields to a fixed 152
ticks regardless of what the file says — a special-cased behavioural quirk baked directly into the
loader rather than expressed in the data.

The 199-file end of the size spectrum illustrates just how many moving objects a level can pack in:
`worlds/world199.txt` (75,770 bytes, the largest file in the set) contains 196 `MoveObject:` lines,
versus a single one in the tiny `world001.txt`.

*From `worlds/world199.txt` (tail, illustrative sample of two of its 196 `MoveObject:` lines):*
```
MoveObject: type=16 stepAdvance=10 stepRecede=10 timeStopStart=0 timeStopEnd=0 posStart=5888;4160 posEnd=5888;4160 posCurrent=5888;4160 step=1 time=0 phase=3393 channel=10 icon=77 
MoveObject: type=6 stepAdvance=1 stepRecede=1 timeStopStart=0 timeStopEnd=0 posStart=2306;6024 posEnd=2306;6024 posCurrent=2306;6024 step=1 time=0 phase=3393 channel=10 icon=21 
```

Level files never contain `Jauge:` or `Doors:` sections, and never carry the underscore-wrapped
`_prefixed_` `DescFile` fields described below — those are exclusive to the `CurrentGame` quick-save
format.

## Field-level parsing: how `Worlds` finds a value

All the scalar `Get*Field` methods (`GetIntField`, `GetBoolField`, `GetDoubleField`,
`GetPointField`) share one private helper, `TryGetFieldValueText`, which does the actual text
scanning: find the `rank`-th line starting with `"<section>:"`, then find `"<name>="` within that
line, then take the substring up to the next space:

*From `Worlds.cpp:387-419`:*
```cpp
        [[nodiscard]] std::optional<std::string> TryGetFieldValueText(
            const string lines[],
            intcs lineCount,
            const string& section,
            intcs rank,
            const string& name)
        {
            for (intcs i = 0; i < lineCount; i++)
            {
                const string& text = lines[i];

                if (String::StartsWith(text, section + ":") && rank-- == 0)
                {
                    std::size_t num = text.find(name + "=");
                    if (num == string::npos)
                    {
                        return std::nullopt;
                    }

                    num += name.length() + 1;

                    const std::size_t num2 = text.find(" ", num);
                    if (num2 == string::npos)
                    {
                        return std::nullopt;
                    }

                    return text.substr(num, num2 - num);
                }
            }

            return std::nullopt;
        }
```

The `rank` parameter is what lets `Worlds` disambiguate between multiple sections of the same name
in one file — for `MoveObject:`, `rank` is the object's slot index, since every moving object gets
its own `MoveObject:` line with the same field names (`type`, `posStart`, `icon`, …) but different
values; `Worlds::GetIntField(array, vectorSize, "MoveObject", n, "type")` walks past the first `n`
`MoveObject:` lines before reading the `n`-th one. Because the search is a plain substring scan on
`"name="`, field names must be chosen so no field name is a prefix of another within the same
section (e.g. `posStart=` vs. `posEnd=` never collide because the trailing `=` is part of the
search key).

Every `Get*Field` method documents (and implements) a graceful, silent fallback for a missing or
malformed field, so a hand-edited or truncated level file degrades rather than crashes: `GetIntField`
→ `0`, `GetDoubleField` → `0.0`, `GetBoolField` → `false`, `GetPointField` → `{0,0}`,
`GetDecorField` → `std::nullopt` (then `-1` via `.value_or(-1)` at the call site).

## The `CurrentGame` quick-save format

`Decor::CurrentWrite()` (`Decor.cpp:10986-11132`) serialises the *entire live simulation* — not
just the tile grid, but every one of Blupi's state flags, timers, and transient counters — as a
single `DescFile:` section whose field names are wrapped in leading/trailing underscores
(`_posDecor_`, `_blupiPos_`, `_blupiAction_`, and so on) to distinguish them, at a glance, from the
plain level-file field names (`posDecor`, `blupiPos`) used by `Worlds::ReadWorld`. A representative
excerpt of the roughly 80 fields it writes:

*From `Decor.cpp:10989-11012` (excerpted):*
```cpp
        Worlds::WriteSection("DescFile");
        Worlds::WriteIntField("_version_", 1);
        Worlds::WritePointField("_posDecor_", m_posDecor);
        Worlds::WritePointField("_dimDecor_", m_dimDecor);
        Worlds::WriteIntField("_term_", m_term);
        Worlds::WriteIntField("_music_", m_music);
        Worlds::WriteIntField("_region_", m_region);
        Worlds::WriteIntField("_time_", m_time);
        Worlds::WritePointField("_blupiPos_", m_blupiPos);
        Worlds::WritePointField("_blupiValidPos_", m_blupiValidPos);
        Worlds::WriteIntField("_blupiAction_", ToRaw(m_blupiAction));
        Worlds::WriteIntField("_blupiDir_", ToRaw(m_blupiDir));
        Worlds::WriteIntField("_blupiPhase_", m_blupiPhase);
        Worlds::WriteDoubleField("_blupiVitesseX_", m_blupiVitesseX);
        Worlds::WriteDoubleField("_blupiVitesseY_", m_blupiVitesseY);
        Worlds::WriteIntField("_blupiIcon_", m_blupiIcon);
        Worlds::WriteIntField("_blupiSec_", ToRaw(m_blupiSec));
```

This is where `_blupiSec_` — the field that stores the currently-held `SecretPower` — actually
lives (see [Chapter 43](ch43-gamedata-save-format.md)'s note that secret powers are *not* part of
the durable `GameData` save). Also written here: every "is Blupi doing X" boolean
(`_blupiHelico_`, `_blupiJeep_`, `_blupiTank_`, `_blupiSkate_`, `_blupiNage_`, `_blupiSurf_`,
`_blupiShield_`, `_blupiPower_`, `_blupiCloud_`, `_blupiHide_`, …), mission bookkeeping
(`_mission_`, `_nbVies_`, `_nbTresor_`, `_totalTresor_`), and four whole-array fields serialised via
`WriteIntArrayField` — `_RankCaisse_`, `_LinkCaisse_`, `_BalleTraj_`, `_MoveTraj_` — plus the
200-entry `_Doors_` array, all as comma-separated `<int-array>` values on the same line.

After the `DescFile:` section, `CurrentWrite()` emits the same `Decor:`/`BigDecor:` 100-row blocks
as a level file (this time from the *live* `m_decor`/`m_bigDecor` grids, which may have been
mutated by gameplay — e.g. crates destroyed, doors visually changed), then one `MoveObject:` section
**per occupied slot**, but critically, unlike a level file's dense packing, each line also writes
its own `index` field so a *sparse* `m_moveObject[]` array (most slots empty, individual objects at
arbitrary indices) round-trips correctly:

*From `Decor.cpp:11099-11120`:*
```cpp
        for (int m = 0; m < MAXMOVEOBJECT; m++)
        {
            if (m_moveObject[m].type != ObjectType::ObjectType0)
            {
                Worlds::WriteSection("MoveObject");
                Worlds::WriteIntField("index", m);
                Worlds::WriteIntField("type", ToRaw(m_moveObject[m].type));
                ...
```

`Decor::CurrentRead()` mirrors this by reading the `index` field per record and writing into
`m_moveObject[intField2]` rather than assuming positional packing (`Decor.cpp:11267-11268`).
Finally, two `Jauge:` sections (one per HUD gauge — see
[Chapter 36](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md)) close out the file.

`CurrentRead()`'s own doc comment captures the load-order subtlety well: it starts from a fresh
`InitDecor()` baseline and then overwrites every field it finds, so *any field this format doesn't
carry* silently falls back to `InitDecor()`'s defaults rather than to some prior in-memory state —
important because it means adding a brand-new piece of persistent Decor state requires adding both
a `Write` call in `CurrentWrite()` *and* a matching `Get` call in `CurrentRead()`, or the field
quietly resets on every quick-load.

### `CurrentGame` file I/O

Unlike the byte-exact `GameData` save (a fixed 640-byte binary blob under the filename
`"SpeedyBlupi"`), the `CurrentGame` quick-save is a UTF-8 text file under the filename
`"CurrentGame"` (`Worlds::getCurrentGameFilenameProperty()`, `Worlds.cpp:136-140`), read and written
as a whole string:

*From `Worlds.cpp:314-333`:*
```cpp
    void Worlds::WriteCurrentGame(const string& data)
    {
        log::Debug("WriteCurrentGame");

        auto userStoreForApplication = getUserStoreForApplication();

        auto isolatedStorageFileStream =
            userStoreForApplication.OpenFile(
                getCurrentGameFilenameProperty(),
                System::IO::FileMode::Create);

        std::vector<bytecs> bytes = System::Text::Encoding::UTF8()->GetBytes(data);

        isolatedStorageFileStream.Write(
            bytes.data(),
            0,
            static_cast<intcs>(bytes.size()));

        isolatedStorageFileStream.Close();
    }
```

`Decor::CurrentDelete()` (`Decor.cpp:10974-10977`) simply forwards to
`Worlds::DeleteCurrentGame()`, removing this file entirely — used when a level is completed or
abandoned, so the next launch doesn't offer to "continue" a finished session.

## World-file loading and the four related, mostly-stub methods

`Decor::Read(int gamer, int rank, bool bUser)` (`Decor.cpp:11304-11373`) is the entry point used to
load a **level design file** (as opposed to the `CurrentGame` quick-save). It calls
`Worlds::ReadWorld(gamer, rank)`, which constructs the filename and opens it as a game content
asset (not `IsolatedStorage` — level files ship inside the game package, they are not user data):

*From `Worlds.cpp:184-196`:*
```cpp
    std::string Worlds::GetWorldFilename(intcs gamer, intcs rank)
    {
        (void)gamer;

        return System::String::Format(
            "worlds/world{0}.txt",
            System::String::ToString(rank, 3)
            );
    }
```

`System::String::ToString(rank, 3)` zero-pads `rank` to (at least) three digits, producing the
`worldNNN.txt` naming convention seen throughout `worlds/` (`world001.txt`, `world010.txt`,
`world199.txt`, …). The `gamer` parameter is accepted for signature compatibility with the original
C# API but is unused — level content does not vary per gamer slot; only *progress* through it does
(via `GameData`'s door array, [Chapter 43](ch43-gamedata-save-format.md)).

Immediately after `Decor::Read()` in the source file sit three small methods worth noting precisely
because two of them are **stubs** in this C++ port:

*From `Decor.cpp:11379-11390`:*
```cpp
    /**
     * @note Stub in this port: level deletion is handled elsewhere, so this always reports
     *       success without touching storage. Parameters are unused.
     */
    bool Decor::Delete(int gamer, int rank, bool bUser)
    {
        return true;
    }

    /**
     * @note Stub in this port: always reports "no file". Parameters are unused.
     */
    bool Decor::FileExist(int gamer, int rank, bool bUser)
    {
        return false;
    }
```

`Decor::Delete()` unconditionally reports success without ever touching storage, and
`Decor::FileExist()` unconditionally reports "does not exist." Neither actually inspects the file
system. This matches the header-level `Worlds` documentation's own admission of "Status: Partial —
some methods retain behavioural stubs from the original C# port" (`Worlds.hpp:72-73`): level
files are read-only game content in the current build, so a user-facing "delete this level" or
"does this custom level exist" feature — plausible in a Windows Phone version that supported
downloadable or user-created levels — has no working implementation here.

## Locating things inside a loaded level: `SearchWorld`, `SearchDoor`, `SearchGold`

Three more `Decor` methods sit in the same region of the source file and round out the "level file
support" toolkit, all operating purely on the already-loaded `m_decor[][]` grid rather than on file
text:

`SearchWorld` scans the whole 100×100 grid for the world's terminal/exit marker icon (looked up per
world index in `Tables::world_terminal`) and returns a position for Blupi to stand next to it,
choosing whichever side is passable:

*From `Decor.cpp:11398-11431`:*
```cpp
    bool Decor::SearchWorld(int world, TinyPoint& blupi, Direction& dir)
    {
        if (world < 0 || world > 12)
        {
            return false;
        }
        int num = Tables::world_terminal[world * 2];
        int num2 = Tables::world_terminal[world * 2 + 1];
        for (int i = 0; i < 100; i++)
        {
            for (int j = 0; j < 100; j++)
            {
                int icon = m_decor[i][j].icon;
                if (icon == num || icon == num2)
                {
                    if (IsPassIcon(m_decor[i - 1][j].icon))
                    {
                        blupi.X = (i - 1) * 64 + 2;
                        blupi.Y = j * 64 + BLUPIOFFY;
                        dir = Direction::Right;
                        return true;
                    }
                    ...
```

This is what places Blupi next to the correct world-entry icon on the hub level (mission 1) when
returning from a completed sub-world — driven by `Decor::MainSwitchInitialize(lastWorld)`
(`Decor.cpp:11508`), itself fed by `GameData::getLastWorldProperty()` from
[Chapter 43](ch43-gamedata-save-format.md).

`SearchDoor` finds a numbered world-gate sign (icons `174`–`181`, mapped to door numbers `1`–`8` via
`icon - 174 + 1`) and the actual door tile (icon `182`) within two cells to either side:

*From `Decor.cpp:11439-11446`:*
```cpp
    bool Decor::SearchDoor(int n, TinyPoint& cel, TinyPoint& blupi)
    {
        for (int i = 0; i < 100; i++)
        {
            for (int j = 0; j < 100; j++)
            {
                int icon = m_decor[i][j].icon;
                if (icon >= 174 && icon <= 181 && icon - 174 + 1 == n)
                {
```

`SearchGold` scans (from the bottom-right corner backwards) for the first tile carrying icon `183`
— the game's treasure/gold marker — and reports its cell:

*From `Decor.cpp:11486-11501`:*
```cpp
    bool Decor::SearchGold(int n, TinyPoint& cel)
    {
        for (int num = 99; num >= 0; num--)
        {
            for (int num2 = 99; num2 >= 0; num2--)
            {
                if (m_decor[num2][num].icon == 183)
                {
                    cel.X = num2;
                    cel.Y = num;
                    return true;
                }
            }
        }
        return false;
    }
```

Note `SearchGold`'s parameter `n` is accepted but never used to disambiguate *which* piece of gold
to find — the function always returns the first `183` tile found scanning back-to-front — this is
consistent with it being called from a cheat-code handler (`CleanAll`/`AllTreasure`-style cheats,
[Chapter 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md)) that iterates `n`
externally, re-scanning each time. All three search functions are grounded in raw `m_decor[][]`
icon numbers, which is the same invisible gameplay-classification layer discussed in
[Chapter 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) and
[Appendix C](../appendices/appendix-c-level-file-format-spec.md) — icons `68` (lava, via `IsLave`),
`373` (trap, via `IsPiege`), `174`–`182` (door signs and door tile), and `183` (gold) are all
examples of numeric tile values whose meaning comes entirely from how `Decor.cpp`'s `Is*()`
predicates and hand-written comparisons interpret them, not from any visible sprite atlas lookup.

## Summary

The `worlds/*.txt` format is a hand-rolled, deliberately simple, line-oriented text serialisation:
one `DescFile:` header carrying scalar/point fields, two 100-row `Decor:`/`BigDecor:` tile-grid
blocks, and a variable number of `MoveObject:` records — all parsed by generic, type-specific
`Get*Field` helpers on `Worlds` that degrade gracefully on missing or malformed data. The exact same
grammar, with an underscore-wrapped field-naming convention and a couple of extra sections
(`Jauge:`), also serves the much larger `CurrentGame` quick-save, which captures the *entire* live
simulation state rather than a level's static design. A close read of the loader code turns up two
genuinely dead pieces of the format in the current C++ port — the `world=` field (written, never
read) and the `Delete`/`FileExist` methods (permanently stubbed) — both artifacts of features that
made sense for a Windows Phone release with (potentially) writable/deletable level content, but
that have no working counterpart in this codebase today.

## See also

- [Chapter 15: Decor — Overview](../part04-decor-simulation/ch15-decor-overview.md) and
  [Chapter 16: The Tile Map](../part04-decor-simulation/ch16-tile-map.md) — what `m_decor[][]` and
  `m_bigDecor[][]` mean once loaded, and the background-art/collision-layer split.
- [Chapter 19: Moving Objects and Decor Actions](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md)
  — the `MoveObject`/`ObjectType` semantics behind each `MoveObject:` record.
- [Chapter 23: Secret Powers and the Cheat System](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md)
  — `_blupiSec_`, `SearchGold`, and cheat-driven level searches.
- [Chapter 26: Tile and Icon Catalog](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) —
  the full catalog of `Is*()` predicates behind icons like `68`, `174`–`183`, `373`.
- [Chapter 36: Jauge — HUD Gauges](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md)
  — the `Jauge:` sections in the `CurrentGame` format.
- [Chapter 43: GameData — Save Format](ch43-gamedata-save-format.md) — the separate, byte-exact
  cross-session profile format that `CurrentGame` and `worlds/*.txt` do not overlap with.
- [Appendix C: Level File Format Specification](../appendices/appendix-c-level-file-format-spec.md)
  — the dense field-by-field reference table for this format.
