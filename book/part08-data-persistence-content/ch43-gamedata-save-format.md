# Chapter 43: GameData — the Save-Game Format

## Overview

`GameData` is a small, self-contained class with an outsized responsibility: it is the entire
persistence layer for a player's progress in Mobile Eggbert. Everything the game remembers between
runs — which of the three save slots is active, whether sound effects are on, how many lives a
player has left, and which of the game's 200 door flags have been opened — lives inside a single
flat byte array owned by one `GameData` instance.

The class is declared in `GameData.hpp` (369 lines, almost entirely Doxygen documentation) and
implemented in `GameData.cpp` (172 lines). The header's own file-level comment states the design
intent plainly:

*From `GameData.hpp:6-10`:*
```cpp
 * GameData serialises all player progress and settings into a flat byte array
 * that mirrors the original Windows Phone save format exactly.  The array is
 * read from / written to the platform file system via Worlds::ReadGameData() and
 * Worlds::WriteGameData().
```

This is not an accident of the C++ port — it is a deliberate constraint. The original Windows
Phone 8 / Silverlight game (see [Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md))
saved its progress as a raw byte blob via `IsolatedStorageFile`, and the C++ rewrite preserves that
exact byte layout so that the semantics of "what a save file means" never had to be re-derived —
only re-implemented. `GameData` itself never touches a file handle; all I/O is delegated to static
helpers on `Worlds` (covered in depth for the *level* file format in
[Chapter 44](ch44-worlds-level-file-format.md), but used here for the *save* format specifically).

## The byte array: layout and sizing

The entire persistent state — for all three gamer slots combined — fits into 640 bytes. The sizing
constants are declared as `static constexpr intcs` members of `GameData`:

*From `GameData.hpp:84-99`:*
```cpp
        /** @brief Number of bytes in the global save-file header. */
        static constexpr intcs SaveHeaderLength = 10;

        /** @brief Number of bytes in the per-gamer header (before the door array). */
        static constexpr intcs GamerHeaderLength = 10;

        /** @brief Number of door state entries per gamer (200 total: 180 secondary + 20 main). */
        static constexpr intcs DoorsLength = 200;

        /** @brief Total bytes per gamer block (GamerHeaderLength + DoorsLength). */
        static constexpr intcs GamerLength = GamerHeaderLength + DoorsLength;

        /** @brief Maximum number of gamer save slots. */
        static constexpr intcs MaxGamer = 3;

        /** @brief Total byte size of the save data array (SaveHeaderLength + GamerLength * MaxGamer). */
        static constexpr intcs TotalLength = SaveHeaderLength + GamerLength * MaxGamer;
```

That resolves to `GamerLength = 10 + 200 = 210` bytes per gamer, and
`TotalLength = 10 + 210 * 3 = 640` bytes overall. The array itself is a fixed-size member, not a
`std::vector` — there is no dynamic allocation involved in holding save state:

*From `GameData.hpp:101-106`:*
```cpp
        /** @brief Flat byte array holding all save data.  Indexed by the accessor methods.
         *
         *  @warning Do not access this array directly outside accessor methods;
         *           incorrect offsets silently corrupt save data.
         */
        bytecs data[TotalLength]{};
```

`bytecs` is the project's `unsigned char` alias from `SharpRuntime::bytecs`, used throughout the
codebase wherever the original C# code used `byte`.

### Global header (bytes 0–9)

The first ten bytes of the array are not tied to any gamer slot — they are global settings that
apply regardless of which of the three players is currently selected:

| Offset | Field | Type | Meaning | Default |
|---|---|---|---|---|
| 0 | *(reserved)* | byte | Version/format tag; written but never read back by any accessor | 1 |
| 1 | *(reserved)* | byte | Unused | 1 |
| 2 | `selectedGamer` | byte | Index (0–2) of the active gamer slot | 0 |
| 3 | `sounds` | byte (bool) | Sound effects on/off | 1 (on) |
| 4 | `jumpRight` | byte (bool) | Jump button placed on the right side of the touch screen | 1 (right) |
| 5 | `autoZoom` | byte (bool) | Auto-zoom-on-action camera feature | 1 (on) |
| 6 | `accelActive` | byte (bool) | Accelerometer tilt-steering enabled | 0 (off) |
| 7 | `accelSensitivity` | byte (0–100) | Accelerometer sensitivity, stored ×100 | 50 (→ 0.50) |
| 8 | *(reserved)* | byte | Unused | 0 |
| 9 | *(reserved)* | byte | Unused | 0 |

This table is drawn directly from the constructor's `Initialize()` and the accessor bodies in
`GameData.cpp`:

*From `GameData.cpp:141-156`:*
```cpp
    void GameData::Initialize()
    {
        data[0] = 1;
        data[1] = 1;
        data[2] = 0;
        data[3] = 1;
        data[4] = 1;
        data[5] = 1;
        data[6] = 0;
        data[7] = 50;
        setSelectedGamerProperty(0);
        for (intcs i = 0; i < MaxGamer; i++)
        {
            Initialize(i);
        }
    }
```

Note bytes 0 and 1 are set to `1` and never read by anything in the file — no accessor exposes
them, and no code searches for a "version" byte on load. They are the vestige of a format-version
tag in the original save file (a common defensive pattern in Windows Phone-era save formats to let
the loader detect an incompatible future format), but the C++ port's `Read()` never inspects them:
it simply overwrites `data[]` wholesale from whatever bytes are on disk, or falls back to
`Initialize()`'s defaults if the file is absent. This is a good example of a byte-exact port
preserving a field's *layout* fully while its *behavioral purpose* has quietly disappeared.

The `accelSensitivity` accessor is a small but instructive example of the byte-array design: a
floating-point value in `[0.0, 1.0]` used by gameplay code is stored as a single integer byte in
`[0, 100]`, with the conversion happening entirely inside the getter/setter pair:

*From `GameData.cpp:64-71`:*
```cpp
    double GameData::getAccelSensitivityProperty() const { return (double)(int)data[7] / 100.0; }

    void GameData::setAccelSensitivityProperty(double v)
    {
        v = System::Math::Max(v, 0.0);
        v = System::Math::Min(v, 1.0);
        data[7] = (bytecs)(v * 100.0);
    }
```

### Per-gamer blocks (bytes 10–639)

After the ten-byte global header, the array holds three identical 210-byte blocks, one per gamer
slot. The offset of gamer `g`'s block is computed by a private static helper:

*From `GameData.cpp:168-171`:*
```cpp
    intcs GameData::GetGamerOffset(intcs gamer)
    {
        return SaveHeaderLength + GamerLength * gamer;
    }
```

so gamer 0 starts at byte 10, gamer 1 at byte 220, gamer 2 at byte 430. Each 210-byte block itself
splits into a 10-byte header followed by 200 bytes of door state:

| Relative offset | Field | Type | Meaning | Default |
|---|---|---|---|---|
| +0 | `nbVies` | byte | Lives remaining | 3 |
| +1 | `lastWorld` | byte | Index of the last (hub-)world reached | 1 |
| +2 … +9 | *(reserved)* | 8 bytes | Padding, never accessed by any getter/setter | 0 |
| +10 … +189 | `doors[0..179]` | 180 bytes | **Secondary door** states | 0 (locked) |
| +190 … +209 | `doors[180..199]` | 20 bytes | **Main door** states | 0 (locked) |

Each door byte is `0` for locked/unopened and `1` for opened. `GamerHeaderLength` (10 bytes) is
larger than the two bytes actually used by `nbVies` and `lastWorld` — the remaining eight bytes are
allocated but never read or written by any method in `GameData.cpp`. This mirrors the two reserved
bytes in the global header: the layout was clearly designed with headroom for fields that either
existed in an earlier version of the original game or were planned and never added, and the C++
port preserves the spare bytes exactly rather than repacking the format.

Per-gamer `Initialize(gamer)` resets exactly the accessible fields:

*From `GameData.cpp:158-166`:*
```cpp
    void GameData::Initialize(intcs gamer)
    {
        data[GetGamerOffset(gamer)] = 3;
        data[GetGamerOffset(gamer) + 1] = 1;
        for (intcs i = 0; i < DoorsLength; i++)
        {
            data[GetGamerOffset(gamer) + GamerHeaderLength + i] = 0;
        }
    }
```

## The three-gamer-slot system

Mobile Eggbert supports three independent save slots — labelled "Player A", "Player B", "Player C"
in the UI (`std::string(1, static_cast<char>('A' + gamer))`, `Game1.cpp:829`, `Game1.cpp:874`) —
sharing one on-disk file. `selectedGamer` (byte 2 of the global header) records which of the three
is currently active, and every per-gamer accessor is a thin wrapper that first resolves this index
into a byte offset:

*From `GameData.cpp:73-77`:*
```cpp
    intcs GameData::getNbViesProperty() const { return data[getGamerOffsetProperty()]; }
    void GameData::setNbViesProperty(const intcs v) { data[getGamerOffsetProperty()] = (bytecs)v; }
    intcs GameData::getLastWorldProperty() const { return data[getGamerOffsetProperty() + 1]; }
    void GameData::setLastWorldProperty(const intcs v) { data[getGamerOffsetProperty() + 1] = (bytecs)v; }
    intcs GameData::getGamerOffsetProperty() const { return GetGamerOffset(getSelectedGamerProperty()); }
```

There is exactly one live `GameData` instance in the running game (owned by `Game1`, per
[Chapter 12](../part03-architecture/ch12-game1-state-machine.md)), and switching the active slot is
a single call:

*From `Game1.cpp:973-977`:*
```cpp
    void Game1::SetGamer(int gamer)
    {
        gameData.setSelectedGamerProperty(gamer);
        gameData.Write();
    }
```

Note that switching gamers immediately writes the *whole* 640-byte array back to disk — including
the two other slots' data, untouched — simply to persist the new value of `selectedGamer` itself.
There is no incremental/partial write path anywhere in `GameData`; `Write()` always serialises the
complete array (see "The I/O path" below).

### The gamer-selection screen and `GetGamerInfo`

Before a player picks a slot, the main-menu "gamer" screen shows a short summary for each of the
three slots: how many lives are banked, and how many main/secondary doors have been opened so far.
This is computed on demand — it is *not* stored pre-aggregated anywhere — by scanning that gamer's
200-byte door array:

*From `GameData.cpp:119-138`:*
```cpp
    void GameData::GetGamerInfo(intcs gamer, intcs& nbVies, intcs& mainDoors, intcs& secondaryDoors)
    {
        nbVies = data[GetGamerOffset(gamer)];
        secondaryDoors = 0;
        for (intcs i = 0; i < 180; i++)
        {
            if (data[GetGamerOffset(gamer) + GamerHeaderLength + i] == 1)
            {
                secondaryDoors++;
            }
        }
        mainDoors = 0;
        for (intcs j = 180; j < 200; j++)
        {
            if (data[GetGamerOffset(gamer) + GamerHeaderLength + j] == 1)
            {
                mainDoors++;
            }
        }
    }
```

`Game1::DrawButtonGamerText` calls this once per slot to render the three-line summary block next
to each gamer button (title, main-door count, secondary-door count, life count):

*From `Game1.cpp:861-897` (excerpted):*
```cpp
    void Game1::DrawButtonGamerText(Def::ButtonGlyph glyph, int gamer)
    {
        ...
        gameData.GetGamerInfo(gamer, nbVies, mainDoors, secondaryDoors);
        ...
        text = Helper::formatString(MyResource::LoadString(MyResource::TX_GAMER_MDOORS),
                                    STRING_VECTOR(std::to_string(mainDoors)));
        Text::DrawText(*pixmap.get(), pos, text, 0.45);
        ...
        text = Helper::formatString(MyResource::LoadString(MyResource::TX_GAMER_SDOORS),
                                    STRING_VECTOR(std::to_string(secondaryDoors)));
```

Interestingly, the localized label strings that these counts get inserted into (see
[Chapter 46](ch46-myresource-resource-management.md) for `MyResource`) advertise smaller totals
than the array's own reserved capacity: `TX_GAMER_MDOORS` reads `"Main gates : {0}/12"` and
`TX_GAMER_SDOORS` reads `"Secondary gates : {0}/52"` (`MyResource.cpp:461-462`). The `doors[]` array
reserves 20 main-door slots and 180 secondary-door slots, but the actual game content only ever
populates 12 main doors and 52 secondary doors across its levels — the remaining slots exist purely
as unused headroom in the byte layout, exactly like the reserved padding bytes discussed above.

## What actually gets persisted — and what does not

Reading `GameData.hpp`/`.cpp` end to end turns up a shorter list of *actually persisted* state than
one might expect from a platformer with power-ups, secrets, and per-level object state:

**Persisted (in the 640-byte `GameData` array):**
- Global: `selectedGamer`, `sounds`, `jumpRight`, `autoZoom`, `accelActive`, `accelSensitivity`.
- Per gamer: `nbVies` (lives), `lastWorld` (the hub index to resume at), and the 200-entry `doors[]`
  array (which gates the player has opened, across *all* levels, not just the current one).

**Not persisted here at all:**
- **Secret powers.** `SecretPower` (`m_blupiSec` in `Decor`, values like `Shield`, `Power`, `Cloud`,
  `Hide` — see [Chapter 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md)) is
  *not* a `GameData` field. It is level/session state owned by `Decor`, reset to `SecretPower::None`
  every time a mission starts (`Decor.cpp:768`) and only re-populated from that level's own design
  data (`Worlds::GetIntField(lines, linesLength, "DescFile", 0, "_blupiSec_")`,
  `Decor.cpp:11169` — but note this field name only appears in the *quick-save* `CurrentGame`
  format read by `Decor::CurrentRead()`, not in the level design files in `worlds/*.txt`; see
  [Chapter 44](ch44-worlds-level-file-format.md)). In other words: your currently-held secret power
  survives a mid-level quick-save/quick-resume, but it is never part of your durable,
  cross-session save file — it is always `None` the next time you start or resume a mission from
  the main flow.
- **In-progress level state** (Blupi's exact position, held items, active moving-object positions,
  treasure counters, and so on). That state is captured by an entirely separate mechanism —
  `Decor::CurrentWrite()`/`Decor::CurrentRead()`, writing to the `CurrentGame` file — covered in
  [Chapter 44](ch44-worlds-level-file-format.md). `GameData` only remembers *coarse* long-term
  progress (lives, last hub world, door flags); it says nothing about where Blupi was standing.

This split is a clean, if implicit, design: `GameData` is a small, stable, byte-exact "profile"
format that has to survive years of platform migrations unchanged, while the much larger and more
volatile moment-to-moment simulation state is serialised separately, in a self-describing text
format that can tolerate field additions without an offset-compatibility headache.

## The I/O path: `Worlds::ReadGameData` / `Worlds::WriteGameData`

`GameData::Read()` and `GameData::Write()` do not touch the filesystem directly — they hand the raw
byte buffer to two static helpers on `Worlds`:

*From `GameData.cpp:84-97`:*
```cpp
    void GameData::Read()
    {
        const bool loaded = Worlds::ReadGameData(data, TotalLength);
        log::Debug("GameData::Read loaded=" + std::to_string(loaded ? 1 : 0)
            + " selectedGamer=" + std::to_string(getSelectedGamerProperty())
            + " lastWorld=" + std::to_string(getLastWorldProperty()));
    }

    void GameData::Write()
    {
        Worlds::WriteGameData(data, TotalLength);
        log::Debug("GameData::Write saved=1 selectedGamer=" + std::to_string(getSelectedGamerProperty())
            + " lastWorld=" + std::to_string(getLastWorldProperty()));
    }
```

`Worlds::ReadGameData`/`WriteGameData` (`Worlds.cpp:198-257`) go through
`System::IO::IsolatedStorage::IsolatedStorageFile`, a CNA-provided emulation of the Windows Phone
`IsolatedStorageFile` API (out of scope for this book — see the CNA sister project for its
internals). The save file itself is named simply `"SpeedyBlupi"`
(`Worlds::getGameDataFilenameProperty()`, `Worlds.cpp:130-134`) — the game's original working
title — and both read and write always transfer the full, fixed `TotalLength` (640) bytes:

*From `Worlds.cpp:198-226`:*
```cpp
    bool Worlds::ReadGameData(bytecs data[], size_t dataSize)
    {
        log::Debug("ReadGameData");

        auto userStoreForApplication = System::IO::IsolatedStorage::IsolatedStorageFile::GetUserStoreForApplication();
        if (userStoreForApplication.FileExists(getGameDataFilenameProperty()))
        {
            try
            {
                auto isolatedStorageFileStream =
                    userStoreForApplication.OpenFile(
                        getGameDataFilenameProperty(),
                        System::IO::FileMode::Open);

                const intcs count = std::min(
                    static_cast<intcs>(dataSize),
                    isolatedStorageFileStream.getLengthProperty());

                isolatedStorageFileStream.Read(data, 0, count);
                isolatedStorageFileStream.Close();
                return true;
            }
            catch (const System::IO::IsolatedStorage::IsolatedStorageException&)
            {
                return false;
            }
        }
        return false;
    }
```

Note the defensive `std::min` against the file's actual length: a shorter (perhaps corrupted, or
from an even older format) file is read only up to its own size, leaving the remaining bytes of
`data[]` at whatever the constructor's `Initialize()` already put there (factory defaults). If the
file does not exist at all — the very first launch — `ReadGameData` returns `false` and `data[]`
is left holding the all-defaults state from `GameData`'s constructor, which always calls
`Initialize()` first (`GameData.cpp:79-82`).

`GameData::Read()` is called exactly once at startup (`Game1.cpp:256`, inside phase
initialization), while `GameData::Write()` is called after every mutation: toggling a setting
(`Game1.cpp:296-313`), switching gamer slot (`Game1.cpp:975-976`), the `Cheat5` reset action
(`Game1.cpp:508-509` calling `GameData::Reset()` then `Write()`), and — most importantly for actual
gameplay progress — `Game1::MemorizeGamerProgress()`:

*From `Game1.cpp:1060-1067`:*
```cpp
    void Game1::MemorizeGamerProgress()
    {
        CNA::Logger::Debug("Game1::MemorizeGamerProgress begin mission=" + std::to_string(mission)
            + " nbVies=" + std::to_string(decor.GetNbVies()));
        gameData.setNbViesProperty(decor.GetNbVies());
        decor.MemorizeDoors(gameData);
        gameData.Write();
        CNA::Logger::Debug("Game1::MemorizeGamerProgress end mission=" + std::to_string(mission));
    }
```

This is the moment where `Decor`'s live simulation state (the current life count, and the
in-memory `m_doors[200]` array it has been updating as the player unlocks gates) is pulled back
into `GameData` and flushed to disk. The two-way relationship between `Decor` and `GameData` for
door state runs through two dedicated methods:

*From `Decor.cpp:1701-1735`:*
```cpp
    void Decor::InitializeDoors(GameData& gameData)
    {
        gameData.GetDoors(m_doors);
        const int doorIndex = m_mission + 1;
        ...
    }

    void Decor::MemorizeDoors(GameData& gameData)
    {
        gameData.SetDoors(m_doors);
        const int doorIndex = m_mission + 1;
        ...
    }
```

`InitializeDoors` is called once per `Game1::StartMission()` (`Game1.cpp:470`) to copy the
persisted door array into `Decor`'s live `m_doors[200]`, and `MemorizeDoors` copies it back at the
end via `MemorizeGamerProgress()`. The debug logging in both methods computes `doorIndex = mission
+ 1` — the array slot that corresponds to *this* mission's own gate — purely for diagnostic
purposes; the actual copy is always the full 200-entry array in both directions.

## Resetting progress

`GameData::Reset()` is a per-slot, not global, operation: it re-initialises only the currently
selected gamer's block, leaving the other two slots and all global settings untouched:

*From `GameData.cpp:99-102`:*
```cpp
    void GameData::Reset()
    {
        Initialize(getSelectedGamerProperty());
    }
```

It is wired to two call sites: the "Erase progress" button on the setup screen (labelled with
`TX_BUTTON_SETUP_RESET`, which itself is formatted with the current gamer's letter — "Player A:
Erase progress" — via `Game1.cpp:826-832`) and cheat glyph `Cheat5`:

*From `Game1.cpp:507-509`:*
```cpp
        case Def::ButtonGlyph::Cheat5:
            gameData.Reset();
            break;
```

Both call sites immediately follow with `gameData.Write()` to persist the reset state.

## Summary

`GameData` is deliberately small and rigid: a fixed 640-byte array, three fixed-size gamer blocks,
and a handful of accessor methods that never deviate from their documented byte offsets. It is the
book-keeping layer for cross-session profile data — lives, the hub world to resume at, per-slot
audio/control preferences, and the cumulative record of which of the game's 72 door gates (12 main
+ 52 secondary of the 20 + 180 reserved slots) have been opened. It deliberately does *not* carry
in-progress level state or the player's currently-held secret power; that heavier, more detailed
state lives in the separate `CurrentGame` quick-save format described in the next chapter.

## See also

- [Chapter 12: Game1 — the State Machine](../part03-architecture/ch12-game1-state-machine.md) —
  owns the single live `GameData` instance and drives `Read`/`Write`/`Reset`/`SetGamer`.
- [Chapter 15: Decor — Overview](../part04-decor-simulation/ch15-decor-overview.md) and
  [Chapter 22: Doors, Keys, DoorKeyFlags](../part04-decor-simulation/ch22-doors-keys-doorkeyflags.md)
  — the live `m_doors[200]` array that `InitializeDoors`/`MemorizeDoors` exchange with `GameData`.
- [Chapter 23: Secret Powers and the Cheat System](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md)
  — why `SecretPower` is level/session state, not part of this save format.
- [Chapter 44: Worlds — Level File Format](ch44-worlds-level-file-format.md) — the separate,
  text-based `CurrentGame` quick-save and `worlds/*.txt` level-design formats.
- [Chapter 46: MyResource — Resource Management](ch46-myresource-resource-management.md) — the
  localized `TX_GAMER_*` strings used to display `GetGamerInfo()`'s counts.
- [Chapter 53: Web Virtual Filesystem](../part10-platform-deep-dives/ch53-web-virtual-filesystem.md)
  — how `IsolatedStorageFile` persistence behaves under the Emscripten/IndexedDB backend.
