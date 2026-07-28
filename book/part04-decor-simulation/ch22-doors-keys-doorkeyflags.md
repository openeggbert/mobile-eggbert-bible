# Chapter 22: Doors, Keys, DoorKeyFlags

Progression in Speedy Blupi is gated by doors, and doors are unlocked by a mixture of collected
keys, collected treasure, completed sub-levels, and — on the hub/world-select level — simple
save-file progress. This chapter covers the `DoorKeyFlags` bitmask, the persistent door-state array
`m_doors[]` it interacts with, the lift ("ascenseur") mechanics that transport Blupi between
platforms, and the door-opening sequences that fire at the start and end of a level.

## `DoorKeyFlags`

`DoorKeyFlags` (`include/WindowsPhoneSpeedyBlupi/decor/DoorKeyFlags.hpp`, 174 lines) is a small
bitmask enum tracking which of the three collectible keys Blupi currently carries:

*From `DoorKeyFlags.hpp:58-65`:*
```cpp
enum class DoorKeyFlags : DoorKeyFlagsUnderlying
{
    None = 0,                  ///< @brief No keys are held; Blupi cannot open any locked door.
    Key1 = 1 << 0,             ///< @brief The first key (bit 0); collected via ObjectType49 and consumed to open the matching locked door.
    Key2 = 1 << 1,             ///< @brief The second key (bit 1); collected via ObjectType50 and consumed to open the matching locked door.
    Key3 = 1 << 2,             ///< @brief The third key (bit 2); collected via ObjectType51 and consumed to open the matching locked door.
    All  = Key1 | Key2 | Key3, ///< @brief All three keys simultaneously; used as a convenience mask or to grant every key at once.
};
```

The header's own doc comment (`DoorKeyFlags.hpp:10-15`) documents the full lifecycle directly:
picking up a key object (`ObjectType49`/`50`/`51`, see [Chapter 19](ch19-moving-objects-and-decor-actions.md))
ORs the matching flag into `m_blupiCle` (`m_blupiCle` — French *clé*, "key" — declared
`DoorKeyFlags m_blupiCle;` at `Decor.hpp:417`); using a key to open a door AND-masks the flag back
out; a cheat/power-up path ORs `DoorKeyFlags::All` in to grant every key at once; and the field is
serialised through `Worlds::WriteIntField`/`Worlds::GetIntField` for save compatibility. This
chapter has already seen where the OR-in actually happens, in
[Chapter 20](ch20-enemy-and-creature-ai.md)'s coverage of `VoyageStep()`:

*From `Decor.cpp:10276-10290` (excerpted):*
```cpp
if (m_voyageIcon == 215 && m_voyageChannel == PixmapChannel::Element)
{
    m_blupiCle = m_blupiCle | DoorKeyFlags::Key1;
    m_sound->PlayImage(SoundChannel::SoundChannel3, m_voyageEnd, -1, false);
}
if (m_voyageIcon == 222 && m_voyageChannel == PixmapChannel::Element)
{
    m_blupiCle = m_blupiCle | DoorKeyFlags::Key2;
    m_sound->PlayImage(SoundChannel::SoundChannel3, m_voyageEnd, -1, false);
}
if (m_voyageIcon == 229 && m_voyageChannel == PixmapChannel::Element)
{
    m_blupiCle = m_blupiCle | DoorKeyFlags::Key3;
    m_sound->PlayImage(SoundChannel::SoundChannel3, m_voyageEnd, -1, false);
}
```

Confirming a detail worth stating precisely: a key is not granted the instant Blupi touches it —
it is granted only once the pickup's "Voyage" fly-to-HUD animation (see
[Chapter 20](ch20-enemy-and-creature-ai.md)) actually completes, exactly like every other
collectible reward in this game.

## The persistent door array: `InitializeDoors` / `MemorizeDoors`

Door state is not stored per-level in the save file directly — it lives in a flat, mission-indexed
array shared across the whole game, `Decor::m_doors[m_doorsLength]` (`m_doorsLength = 200`,
`Decor.hpp:497-508`), which is synchronised with `GameData` at level start and level end:

*From `Decor.cpp:1701-1735`:*
```cpp
void Decor::InitializeDoors(GameData& gameData)
{
    gameData.GetDoors(m_doors);
    const int doorIndex = m_mission + 1;
    if (doorIndex >= 0 && doorIndex < 200)
    {
        log::Debug("Decor::InitializeDoors mission=" + std::to_string(m_mission)
            + " doorIndex=" + std::to_string(doorIndex)
            + " state=" + std::to_string(m_doors[doorIndex]));
    }
    else
    {
        log::Debug("Decor::InitializeDoors mission=" + std::to_string(m_mission)
            + " doorIndex=" + std::to_string(doorIndex)
            + " out_of_range");
    }
}

void Decor::MemorizeDoors(GameData& gameData)
{
    gameData.SetDoors(m_doors);
    const int doorIndex = m_mission + 1;
    ...
}
```

`InitializeDoors()` copies the whole 200-entry door array out of the current gamer's persistent
`GameData` when a level loads; `MemorizeDoors()` copies it back when the player wins or saves.
Neither method touches only "this level's" doors — the entire array round-trips every time,
because (as `AdaptDoors()` below shows) a single mission's win state is recorded at index
`m_mission + 1`, meaning each level's door entry actually represents *the next* level's unlock
state. The debug logging around `doorIndex` — added specifically to trace this indexing scheme —
underscores that this ported code has clearly needed active debugging to keep the off-by-one
mission/door relationship correct.

## `ActiveSwitch`, `IsSwitch`, `GetTypeBarre`: switches and bars

*From `Decor.cpp:7131-7149`:*
```cpp
void Decor::ActiveSwitch(bool bState, TinyPoint cel)
{
    TinyPoint pos;
    pos.X = cel.X * 64;
    pos.Y = cel.Y * 64;
    ModifDecor(pos, bState ? 384 : 385);
    PlaySound(bState ? SoundChannel::SoundChannel77 : SoundChannel::SoundChannel76, pos);
    cel.X -= 20;
    for (int i = 0; i < 41; i++)
    {
        if (cel.X >= 0 && cel.X < 100 && m_decor[cel.X][cel.Y].icon == (bState ? 379 : 378))
        {
            pos.X = cel.X * 64;
            pos.Y = cel.Y * 64;
            ModifDecor(pos, bState ? 378 : 379);
        }
        cel.X++;
    }
}
```

`ActiveSwitch()` does two things when a switch is toggled: it redraws the switch tile itself
(icon `384` activated, `385` deactivated — see [Chapter 21](ch21-physics-and-collision.md) for the
correction of `ENUMS.md`'s mislabelling of these two icons as bridge state), and it sweeps a
41-tile-wide band centred on the switch's column, flipping every saw-blade tile (icon `378`/`379`,
[Chapter 21](ch21-physics-and-collision.md)'s `IsScie()`) between its active and inactive icon.
Switches in this game are therefore wired to a *horizontal row* of linked hazards, not to a single
tile — flipping one switch can silence or activate an entire lane of saws at once.

`IsSwitch()` is the read-side counterpart, used to detect whether Blupi is standing on a switch
tile at all:

*From `Decor.cpp:7257-7275`:*
```cpp
bool Decor::IsSwitch(TinyPoint pos, TinyPoint& celSwitch)
{
    pos.X += 30;
    if (pos.X % 64 < 4 || pos.X % 64 > 60)
    {
        return false;
    }
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

`GetTypeBarre()` (covered in full in [Chapter 21](ch21-physics-and-collision.md), reproduced here
for completeness) is unrelated to doors mechanically, but shares the same French-terminology
convention ("barre" — bar/rod) for the rope/rail tiles (icon `138`/`202`) Blupi grabs and hangs
from; it distinguishes a genuinely hangable bar from one whose lower half is solid floor.

## `IsDoor`

*From `Decor.cpp:7360-7376`:*
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

This probes Blupi's own tile and one tile ahead in his facing direction for a door icon (`334`–
`336`), so a door directly in his path can be opened as he walks up to it, without requiring him to
stand precisely centred on the door tile.

## Teleporters: `IsTeleporte`, `SearchTeleporte`

*From `Decor.cpp:7378-7429`:*
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

/**
 * @note Pairing is implicit in the tile icon: the entry teleporter's icon (330..333,
 *       returned by IsTeleporte) IS the pair id. This linearly scans the whole 100x100 map
 *       for the first cell sharing that same icon and far enough from @p pos (>40px in any
 *       axis, to skip the entry cell itself), and returns its position as the exit. There
 *       is no separate teleporter index table.
 * @warning If a third tile shares the same teleporter icon, the first match in row-major
 *          order wins; level data must keep teleporter icons in matched pairs.
 */
bool Decor::SearchTeleporte(TinyPoint pos, TinyPoint& newpos)
{
    int num = IsTeleporte(pos);
    if (num == -1)
    {
        return false;
    }
    for (int i = 0; i < 100; i++)
    {
        for (int j = 0; j < 100; j++)
        {
            if (num == m_decor[i][j].icon)
            {
                newpos.X = i * 64;
                newpos.Y = j * 64 + 60;
                if (newpos.X < pos.X - 40 || newpos.X > pos.X + 40 || newpos.Y < pos.Y - 40 || newpos.Y > pos.Y +
                    40)
                {
                    return true;
                }
            }
        }
    }
    return false;
}
```

There is no teleporter table, index, or list anywhere in `Decor`'s data model — a teleporter's
*icon value itself* (`330` through `333`, four independent pairing IDs) is the only linkage between
an entry and its exit. `SearchTeleporte()` finds the paired exit by brute-force scanning the whole
map for a second occurrence of the same icon, and its own warning is explicit about the fragility
this implies: if a level author accidentally places a third tile with the same teleporter icon, the
first match in row-major scan order silently wins, with no error raised.

## Lifts ("ascenseurs")

`Decor.hpp`'s own class-level doc comment lists "doors, switches, teleporters, and lifts
(ascenseurs)" as one of `Decor`'s core responsibilities (`Decor.hpp:57`), confirming "ascenseur" —
French for elevator/lift — is the correct reading before even reaching the methods themselves.
Lifts are ordinary `MoveObject`s of type `1`, `47`, or `48` (see
[Chapter 19](ch19-moving-objects-and-decor-actions.md) for their linear back-and-forth motion and
[Chapter 20](ch20-enemy-and-creature-ai.md) for `MoveAscenseurDetect()`'s box-overlap query), and
four further methods handle the specifics of carrying Blupi safely.

*From `Decor.cpp:9184-9230`:*
```cpp
int Decor::AscenseurDetect(TinyRect rect, TinyPoint oldpos, TinyPoint newpos)
{
    if (m_blupiTimeNoAsc != 0)
    {
        return -1;
    }
    int num = newpos.Y - oldpos.Y;
    int num2 = ((num >= 0) ? 30 : (-30));
    num = std::abs(num);
    TinyRect src = TinyRect();
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (
            m_moveObject[i].type != ObjectType::ObjectType1 &&
            m_moveObject[i].type != ObjectType::ObjectType47 &&
            m_moveObject[i].type != ObjectType::ObjectType48)
        {
            continue;
        }
        src.Left = m_moveObject[i].posCurrent.X;
        src.Right = m_moveObject[i].posCurrent.X + 64;
        src.Top = m_moveObject[i].posCurrent.Y;
        src.Bottom = m_moveObject[i].posCurrent.Y + 16;
        TinyRect dst;
        if (num < 30)
        {
            if (Misc::IntersectRect(dst, src, rect))
            {
                return i;
            }
            continue;
        }
        TinyRect src2 = rect;
        src2.Top -= num / 30 * num2;
        src2.Bottom -= num / 30 * num2;
        for (int j = 0; j <= num / 30; j++)
        {
            if (Misc::IntersectRect(dst, src, src2))
            {
                return i;
            }
            src2.Top += num2;
            src2.Bottom += num2;
        }
    }
    return -1;
}
```

`AscenseurDetect()` guards against fast vertical movement skipping straight through a thin lift's
16px-tall collision strip in a single frame: when Blupi's vertical delta this frame (`newpos.Y -
oldpos.Y`) exceeds 30px, it doesn't just test the final position — it steps the probe rectangle
back through the intermediate 30px increments the movement passed through, so a fast fall (or a
fast lift) can't tunnel through undetected. It is gated by `m_blupiTimeNoAsc`, a short cooldown
timer set after Blupi deliberately slides off a lift's edge (below), preventing him from
immediately re-attaching to the same lift.

*From `Decor.cpp:9232-9265`:*
```cpp
/**
 * @note Reports vertigo when Blupi's box hangs off the left or right edge of lift @p i so
 *       the appropriate teetering animation can play. For the wide multi-segment lifts
 *       (AscenseurShift true) it swaps the side and starts a short no-lift cooldown
 *       (m_blupiTimeNoAsc = 10) so Blupi slides off the edge rather than balancing forever.
 */
void Decor::AscenseurVertigo(int i, bool& bVertigoLeft, bool& bVertigoRight)
{
    bVertigoLeft = false;
    bVertigoRight = false;
    if (m_blupiPos.X + 20 + 4 < m_moveObject[i].posCurrent.X)
    {
        bVertigoLeft = true;
    }
    if (m_blupiPos.X + 60 - 20 - 4 > m_moveObject[i].posCurrent.X + 64)
    {
        bVertigoRight = true;
    }
    if (AscenseurShift(i))
    {
        if (bVertigoLeft)
        {
            bVertigoLeft = false;
            bVertigoRight = true;
            m_blupiTimeNoAsc = 10;
        }
        else if (bVertigoRight)
        {
            bVertigoRight = false;
            bVertigoLeft = true;
            m_blupiTimeNoAsc = 10;
        }
    }
}
```

*From `Decor.cpp:9267-9282`:*
```cpp
/**
 * @note "Shiftable" simply means the lift sprite is one of the wide horizontal-platform
 *       icons (311..316); those lifts let Blupi slide off the ends, narrow lifts do not.
 */
bool Decor::AscenseurShift(int i)
{
    if (i == -1)
    {
        return false;
    }
    if (m_moveObject[i].icon >= 311)
    {
        return m_moveObject[i].icon <= 316;
    }
    return false;
}
```

`AscenseurVertigo()` decides which side of the lift Blupi is teetering off of, purely so the
correct "teetering" animation plays; for wide lifts (icons `311`–`316`, the same range
[Chapter 19](ch19-moving-objects-and-decor-actions.md) identifies as the caterpillar-tread
conveyor platforms) it inverts the reported side and starts a 10-frame no-lift cooldown, so Blupi
actually slides off the platform's edge rather than balancing there indefinitely — narrow lifts
skip this and let him teeter in place. `AscenseurShift()` itself is a one-line icon-range check:
"shiftable" purely means the lift's *current sprite* falls in the wide-platform icon range.

*From `Decor.cpp:9284-9300`:*
```cpp
/**
 * @note The loop counter reuses (and immediately overwrites) the @p i parameter, so the
 *       passed index is ignored and EVERY object in the pool is rewound to its start state
 *       (posCurrent=posStart, step=1, time=0, phase=0). In practice this re-synchronises all
 *       lifts to a common cycle origin by resetting the whole pool's motion timers.
 * @warning @p i is not used as a selector despite its name; do not assume per-object scope.
 */
void Decor::AscenseurSynchro(int i)
{
    for (i = 0; i < MAXMOVEOBJECT; i++)
    {
        m_moveObject[i].posCurrent = m_moveObject[i].posStart;
        m_moveObject[i].step = 1;
        m_moveObject[i].time = 0;
        m_moveObject[i].phase = 0;
    }
}
```

`AscenseurSynchro()` is a small but genuine surprise in its own signature: despite taking a
per-object index `i` (suggesting it resets *one* lift), the loop immediately reuses and overwrites
that parameter, so the passed-in value is discarded and *every* object in the entire 200-slot pool
— not just lifts — is rewound to its start position. In practice this re-synchronises every lift
in the level to a common cycle origin whenever it is called, at the cost of also resetting the
motion state of every crate, enemy, and effect currently active. The method's own doc comment flags
this explicitly as a trap for future maintainers reading the parameter name.

## Door-opening sequences

Opening a door is animated, not instantaneous — the door tile is cleared from the static map and a
transient `MoveObject` slides the old door sprite away over roughly 50 frames.

*From `Decor.cpp:11667-11688`:*
```cpp
/**
 * @note Opening is animated, not instant: the door tile is cleared from the map and a
 *       transient ObjectType22 is spawned that slides the old door sprite one tile upward
 *       (posStart -> posEnd one cell up) over ~50 frames before it self-destructs, with the
 *       door-open sound. So after this call the cell is already passable while the visual
 *       lift-away plays out.
 */
void Decor::OpenDoor(TinyPoint cel)
{
    int icon = m_decor[cel.X][cel.Y].icon;
    m_decor[cel.X][cel.Y].icon = -1;
    int num = MoveObjectFree();
    m_moveObject[num].type = ObjectType::ObjectType22;
    m_moveObject[num].stepAdvance = Config::ScaleTime(50);
    m_moveObject[num].stepRecede = Config::ScaleTime(1);
    m_moveObject[num].timeStopStart = 0;
    m_moveObject[num].timeStopEnd = 0;
    m_moveObject[num].posStart.X = 64 * cel.X;
    m_moveObject[num].posStart.Y = 64 * cel.Y;
    m_moveObject[num].posEnd.X = 64 * cel.X;
    m_moveObject[num].posEnd.Y = 64 * (cel.Y - 1);
    m_moveObject[num].posCurrent = m_moveObject[num].posStart;
    m_moveObject[num].step = 1;
    m_moveObject[num].time = 0;
    m_moveObject[num].phase = 0;
    m_moveObject[num].channel = PixmapChannel::Object;
    m_moveObject[num].icon = icon;
    PlaySound(SoundChannel::SoundChannel33, m_moveObject[num].posStart);
}
```

The door cell becomes passable the instant `m_decor[cel.X][cel.Y].icon = -1` runs — gameplay
progress is not blocked on the animation finishing — but the door's old sprite keeps existing as
an `ObjectType22` `MoveObject` that visually slides one tile upward and self-destructs once it
completes its motion (see [Chapter 19](ch19-moving-objects-and-decor-actions.md) for the matching
`ObjectType22` self-destruct check in `MoveObjectStepLine()`, which triggers once `step == 3`).

Three doors-related "opening" methods key off different win/progress conditions rather than a
direct player action:

*From `Decor.cpp:11636-11658` (`OpenDoorsTresor`):*
```cpp
/**
 * @note Treasure-gated doors use consecutive icons starting at 421 (door requiring 1
 *       treasure = 421, 2 = 422, ...). This opens every such door whose treasure
 *       requirement is now met (icon in 421 .. 421 + m_nbTresor - 1). Called whenever a
 *       treasure is collected.
 */
void Decor::OpenDoorsTresor()
{
    TinyPoint cel;
    for (int i = 0; i < 100; i++)
    {
        for (int j = 0; j < 100; j++)
        {
            int icon = m_decor[i][j].icon;
            if (icon >= 421 && icon <= 421 + m_nbTresor - 1)
            {
                cel.X = i;
                cel.Y = j;
                OpenDoor(cel);
            }
        }
    }
}
```

*From `Decor.cpp:11690-11700` (`OpenDoorsWin`):*
```cpp
/**
 * @note Records the win by setting the door flag for the NEXT sublevel (m_doors[mission+1]),
 *       which is what AdaptDoors() later reads to unlock progression. This only flips the
 *       persistent flag; it does not animate any door in the current level.
 */
void Decor::OpenDoorsWin()
{
    m_doors[m_mission + 1] = 1;
    log::Debug("Decor::OpenDoorsWin mission=" + std::to_string(m_mission)
        + " unlockedDoor=" + std::to_string(m_mission + 1));
}
```

*From `Decor.cpp:11702-11710` (`OpenGoldsWin`):*
```cpp
/**
 * @note Marks the whole world (index mission/10) as cleared by setting its gold flag at the
 *       conventional offset m_doors[180 + worldIndex]; AdaptDoors() reads this on the hub to
 *       reveal the world's collected gold.
 */
void Decor::OpenGoldsWin()
{
    m_doors[180 + m_mission / 10] = 1;
}
```

The icon-range scheme in `OpenDoorsTresor()` is deliberately linear: a door gated behind one
treasure uses icon `421`, two treasures `422`, and so on, so a single range comparison
(`icon >= 421 && icon <= 421 + m_nbTresor - 1`) covers every treasure threshold in the level with
no lookup table needed — this is the entry `ENUMS.md`'s tile-icon table (see
[Chapter 21](ch21-physics-and-collision.md)) labels `Treasure*` starting at `421`, confirmed here.
`OpenDoorsWin()` and `OpenGoldsWin()` do not touch the current level's visible tiles at all — they
flip persistent bits in `m_doors[]` at two different, non-overlapping index conventions:
`m_doors[m_mission + 1]` for "the next sub-level is now unlocked," and `m_doors[180 + world]` for
"this entire world's gold has been collected," a convention `AdaptDoors()` (below) reads back.

*From `Decor.cpp:11712-11719` (`DoorsLost`):*
```cpp
/**
 * @note Despite the name it does not touch m_doors: losing simply restores the life count to
 *       the default 3 (the original game's reset-on-fail behaviour for this code path).
 */
void Decor::DoorsLost()
{
    m_nbVies = 3;
}
```

`DoorsLost()` is another name that, read literally, promises door-related behaviour it does not
deliver — despite living among the door methods and being named for the moment Blupi loses, it
does not touch `m_doors[]` at all; it simply resets the life count to the default of three, the
original game's reset-on-failure behaviour for whatever call path leads here.

## `SearchDoor`, `MainSwitchInitialize`, `AdaptDoors`

`SearchDoor()` locates a specific numbered world-door sign and the actual door tile near it:

*From `Decor.cpp:11433-11484` (excerpted):*
```cpp
/**
 * @note Finds world-door number @p n (door sign icons 174..181 map to door 1..8) and locates
 *       the actual door tile (icon 182) within two cells to either side, returning both the
 *       door cell and the cell just beyond it where Blupi should stand. The search prefers
 *       the nearer cell on each side.
 */
bool Decor::SearchDoor(int n, TinyPoint& cel, TinyPoint& blupi)
{
    for (int i = 0; i < 100; i++)
    {
        for (int j = 0; j < 100; j++)
        {
            int icon = m_decor[i][j].icon;
            if (icon >= 174 && icon <= 181 && icon - 174 + 1 == n)
            {
                if (i > 0 && m_decor[i - 1][j].icon == 182)
                {
                    cel.X = i - 1;
                    cel.Y = j;
                    blupi.X = (i - 2) * 64 + 2;
                    blupi.Y = j * 64 + BLUPIOFFY;
                    return true;
                }
                ...
            }
        }
    }
    return false;
}
```

`MainSwitchInitialize()` is a narrow hub-level-only helper, positioning Blupi's start point beside
the world he most recently completed:

*From `Decor.cpp:11503-11520`:*
```cpp
/**
 * @note Only acts on the hub level (mission 1): it moves Blupi's start position to stand
 *       beside the world he most recently completed (SearchWorld(@p lastWorld)) so re-entering
 *       the hub places him where he left off. No effect on regular gameplay levels.
 */
void Decor::MainSwitchInitialize(int lastWorld)
{
    if (m_mission == 1)
    {
        TinyPoint blupi;
        Direction dir = Direction::None;
        if (SearchWorld(lastWorld, blupi, dir))
        {
            m_blupiStartPos = blupi;
            m_blupiStartDir = dir;
        }
    }
}
```

`AdaptDoors()` is the largest of these methods and the one that actually reconciles a level's
visible door/gold tiles with the player's persistent save progress at level-load time:

*From `Decor.cpp:11522-11622` (excerpted):*
```cpp
/**
 * @note Two distinct behaviours selected by mission. Private (user) levels return early —
 *       all gates are treated as open. On the hub (mission 1) it reveals progress: collected
 *       golds animate up (ObjectType22), and world-entry/bonus tiles are swapped to their
 *       "unlocked" icon variant when the matching door flag (or the open-doors cheat) is set.
 *       On a world's entry screen (mission % 10 == 0) it opens the doors to sub-levels the
 *       player has reached and snaps Blupi's start position/direction beside the last open
 *       door.
 * @note Door indexing is by convention: m_doors[180 + worldOffset] holds gold/world flags on
 *       the hub, while m_doors[mission + i] holds the per-sublevel door flags on world screens.
 */
void Decor::AdaptDoors(bool bPrivate)
{
    TinyPoint cel;
    TinyPoint blupi;
    m_bPrivate = bPrivate;
    if (m_bPrivate)
    {
        return;
    }
    if (m_mission == 1)
    {
        for (int i = 0; i < 20; i++)
        {
            if (SearchGold(i, cel) && (m_doors[180 + i] == 1 || m_bCheatDoors))
            {
                m_decor[cel.X][cel.Y].icon = -1;
                int num = MoveObjectFree();
                m_moveObject[num].type = ObjectType::ObjectType22;
                m_moveObject[num].stepAdvance = Config::ScaleTime(50);
                ...
                m_moveObject[num].posEnd.X = 64 * cel.X;
                m_moveObject[num].posEnd.Y = 64 * (cel.Y - 1);
                ...
                m_moveObject[num].icon = 183;
                PlaySound(SoundChannel::SoundChannel33, m_moveObject[num].posStart);
            }
        }
        for (int j = 0; j < 100; j++)
        {
            for (int k = 0; k < 100; k++)
            {
                int icon = m_decor[j][k].icon;
                if (icon >= 158 && icon <= 165 && (m_doors[180 + icon - 158 + 1] == 1 || m_bCheatDoors))
                {
                    m_decor[j][k].icon += 8;
                }
                if (icon == 309 && (m_doors[189] == 1 || m_bCheatDoors))
                {
                    m_decor[j][k].icon = 310;
                }
                if (icon >= 410 && icon <= 415 && (m_doors[180 + icon - 410 + 9] == 1 || m_bCheatDoors))
                {
                    m_decor[j][k].icon += 5;
                }
            }
        }
    }
    else
    {
        if (m_mission % 10 != 0)
        {
            return;
        }
        for (int i = 0; i < 10; i++)
        {
            if (SearchDoor(i, cel, blupi))
            {
                const int doorIndex = m_mission + i;
                const bool shouldOpen = m_doors[doorIndex] == 1 || m_bCheatDoors;
                ...
                if (shouldOpen)
                {
                    OpenDoor(cel);
                    m_blupiStartPos = blupi;
                    if (blupi.X < cel.X * 64)
                    {
                        m_blupiStartDir = Direction::Right;
                    }
                    else
                    {
                        m_blupiStartDir = Direction::Left;
                    }
                }
            }
        }
    }
}
```

`AdaptDoors()` picks one of two completely different behaviours depending on the current mission
index. User-created (`m_bPrivate`) levels bypass all of this — every gate is simply treated as
open, since private levels have no save-progress concept to gate against. On the hub level
(`m_mission == 1`) it does three things: it re-plays the "gold chest opening" animation for every
world whose gold flag is already set (using the same `ObjectType22` sliding-icon animation
`OpenDoor()` uses, but built inline here rather than delegated), it swaps world-entry sign icons
(`158`–`165`) to their unlocked variant (+8) once the matching flag is set, and it swaps the bonus-
world icon (`309` → `310`) and hub icon range (`410`–`415`, +5) the same way — this is the exact
icon range [Chapter 21](ch21-physics-and-collision.md) flagged as overloaded with `IsGoutte()`'s
drip-hazard test, confirmed here as legitimately serving a second, mutually-exclusive role on the
hub level specifically. On an ordinary world's entry screen (`m_mission % 10 == 0`), it instead
opens whichever numbered sub-level doors the player has already reached, and repositions Blupi's
start point and facing direction to stand just outside the last door it opened. Every check in
both branches is also satisfiable by `m_bCheatDoors`, the "open all doors" cheat flag — one boolean
that, read alongside every `m_doors[...] == 1` condition in this method, unlocks the entire game's
progression gates at once.

## See also

- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 16 — The Tile Map](ch16-tile-map.md)
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 23 — Secret Powers and the Cheat System](ch23-secret-powers-and-cheat-system.md)
- [Chapter 24 — Missions and ContinueMission](ch24-missions-and-continuemission.md)
- [Chapter 43 — GameData: Save Format](../part08-data-persistence-content/ch43-gamedata-save-format.md)
- [Chapter 44 — Worlds: Level File Format](../part08-data-persistence-content/ch44-worlds-level-file-format.md)
- [Appendix B — Enum Catalog](../appendices/appendix-b-enum-catalog.md)
