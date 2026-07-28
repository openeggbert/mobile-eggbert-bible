# Chapter 19: Moving Objects and Decor Actions

Everything in a Speedy Blupi level that is not Blupi himself and not a static tile is a
`MoveObject`. Enemies, crates, keys, treasures, projectiles, explosions, water splashes, the
lifts Blupi rides, the door-opening animation, even the little sparkle trail that follows a
collected item — all of them are the same 13-field struct, differing only in a numeric
`ObjectType` tag and the behaviour that a long dispatcher function attaches to that tag at
run time. This chapter reads that struct, the `ObjectType` and `DecorAction` enums that classify
it, and the object lifecycle methods in `Decor.cpp` that create, animate, sort, and destroy
objects every frame.

## The `MoveObject` struct

`MoveObject` is declared as a private nested struct inside `Decor` (`Decor.hpp:139-154`), and its
Doxygen comment states the model plainly:

*From `Decor.hpp:118-138`:*
```cpp
/**
 * @struct MoveObject
 * @brief  Represents a moving object (enemy, crate, projectile, collectible, etc.)
 *         currently active in the level.
 * @details
 *   Moving objects are stored in the fixed-size pool m_moveObject[MAXMOVEOBJECT].
 *   Each object moves between posStart and posEnd along a linear path, advancing
 *   by stepAdvance pixels per frame and receding by stepRecede pixels per frame.
 *   The object pauses at each end for timeStopStart / timeStopEnd frames before
 *   reversing direction.
 *
 *   The object's visual representation is identified by (channel, icon), which are
 *   looked up in the animation tables at each frame via MoveObjectStepIcon().
 */
```

and the fields themselves:

*From `Decor.hpp:139-154`:*
```cpp
struct MoveObject
{
    ObjectType    type;          ///< Type of this moving object (enemy, crate, etc.).
    intcs         stepAdvance;   ///< Pixels per frame while moving toward posEnd.
    intcs         stepRecede;    ///< Pixels per frame while moving toward posStart.
    intcs         timeStopStart; ///< Frames to wait at posStart before advancing.
    intcs         timeStopEnd;   ///< Frames to wait at posEnd before receding.
    TinyPoint     posStart;      ///< Start position in game-space pixel coordinates.
    TinyPoint     posEnd;        ///< End position in game-space pixel coordinates.
    TinyPoint     posCurrent;    ///< Current position in game-space pixel coordinates.
    intcs         step;          ///< Current movement step / distance traveled this leg.
    intcs         time;          ///< Remaining wait time at current endpoint (frames).
    intcs         phase;         ///< Animation step counter (indexes into animation tables).
    PixmapChannel channel;       ///< Sprite sheet to use when drawing this object.
    intcs         icon;          ///< Icon slot index within the sprite sheet.
};
```

Two things fall out of this design immediately. First, a single object's *motion* and its
*animation* are governed by two independent counters: `step`/`time` (plus `posStart`/`posEnd`)
drive where the object physically is, while `phase` drives which sprite frame is shown — an
object can sit motionless (`posStart == posEnd`) and still animate forever by incrementing
`phase`, which is exactly how explosions, sparkle trails, and stationary collectibles work.
Second, "moving" is a two-endpoint back-and-forth, not an arbitrary path: `MoveObjectStepLine()`
(covered below) is a four-phase state machine over exactly `posStart` and `posEnd`, so anything
that patrols further than two points (a multi-waypoint lift, say) has to be built as several
chained objects or worked around in the per-type logic, not by `MoveObject` itself.

The pool is fixed-size and flat:

*From `Decor.hpp:184-221`:*
```cpp
/** Maximum number of simultaneously active moving objects. */
static constexpr intcs MAXMOVEOBJECT = 200;
...
/** Pool of all active moving objects in the level. */
MoveObject m_moveObject[MAXMOVEOBJECT];
```

Two hundred slots serve an entire level's enemies, crates, projectiles, and every one-shot visual
effect at once — a bullet, an explosion, and a splash all consume a slot from the same pool as a
patrolling enemy. A slot is "free" precisely when its `type` field equals `ObjectType::ObjectType0`
(the sentinel documented as "null / inactive slot" in `ObjectType.hpp:67`); there is no separate
liveness flag.

`MoveObjectCopy()` is the plumbing that makes the pool reorderable — it is a plain
field-by-field copy used by the sort and compaction routines later in this chapter:

*From `Decor.cpp:105-120`:*
```cpp
void Decor::MoveObjectCopy(MoveObject& dst, const MoveObject& src)
{
    dst.type = src.type;
    dst.stepAdvance = src.stepAdvance;
    dst.stepRecede = src.stepRecede;
    dst.timeStopStart = src.timeStopStart;
    dst.timeStopEnd = src.timeStopEnd;
    dst.posStart = src.posStart;
    dst.posEnd = src.posEnd;
    dst.posCurrent = src.posCurrent;
    dst.step = src.step;
    dst.time = src.time;
    dst.phase = src.phase;
    dst.channel = src.channel;
    dst.icon = src.icon;
}
```

## The `ObjectType` enum

`ObjectType` (`include/WindowsPhoneSpeedyBlupi/decor/ObjectType.hpp`, 426 lines) is a scoped
enum over an unsigned byte, with values inherited verbatim from the original game because they
are stored directly in level files:

*From `ObjectType.hpp:61-67`:*
```cpp
enum class ObjectType : ObjectTypeUnderlying
{
    // -----------------------------------------------------------------------
    // Sentinel / empty slot
    // -----------------------------------------------------------------------

    ObjectType0   =   0, ///< @brief Null / inactive slot; a MoveObject whose type is 0 is considered absent and is not drawn or updated.
```

The file's own header comment is candid about how this catalogue was produced: the numeric IDs
are "inherited verbatim from the original Speedy Blupi / Windows Phone game," and IDs that never
appear anywhere in `Decor.cpp` (a long, non-contiguous list scattered across 42–203) are
documented only as "purpose unknown" — placeholders kept so a level file's byte values round-trip
losslessly even though nobody currently knows what most of them meant in the original game. This
book only makes claims about the values that are actually read, in `Decor.cpp`. Reading through
that file's `switch`/`if`-chains lets around eighty of the roughly one hundred fifty defined values
be pinned to a concrete role; a representative slice, grouped by function rather than by numeric
order:

| Category | `ObjectType` values | Source evidence |
|---|---|---|
| Sentinel | `ObjectType0` | free-slot marker, `Decor.cpp:7951` and throughout |
| Platform lifts | `ObjectType1`, `ObjectType47`, `ObjectType48` | `MoveObjectStepLine`, `Decor.cpp:8010` |
| Patrol enemies | `ObjectType2`, `ObjectType3`, `ObjectType96`, `ObjectType97` | icon ranges 12–20/48–56, `Decor.cpp:8202-8226` |
| Bulldozer | `ObjectType4` | `table_bulldozer_*`, `Decor.cpp:8628` |
| Treasure / life / goal | `ObjectType5`, `ObjectType6`, `ObjectType7`, `ObjectType21` | `Decor.cpp:8297-8323` |
| Keys | `ObjectType49`, `ObjectType50`, `ObjectType51` | `table_cle1/2/3`, `Decor.cpp:8324-8338` |
| Vehicles / power-ups | `ObjectType13,19,24,25,26,28,29,30,31,40,46,55` | doc comments in `ObjectType.hpp:116-127` |
| Explosions / flashes | `ObjectType8-11,36-38,41-42,53,90-93,98-100` | `table_explo1..8`, `Decor.cpp:8395-8538` |
| Water/goo effects | `ObjectType14`, `ObjectType15`, `ObjectType34`, `ObjectType35` | `MoveObjectPlouf/Blup/Tiplouf`, ch. 20 |
| Projectile | `ObjectType23` | fired by `blupih`/`blupit`, `Decor.cpp:8882` |
| Patrol enemies (walkers) | `ObjectType16-18,20,32,33,44,54` | ch. 20 |
| Moving decoration | `ObjectType22,27,52,56-58` | door animation, bridge build, dynamite fuse |
| Blupi avatar skins | `ObjectType200-203` | `Decor.cpp:8227-8246` |

One entry deserves a specific correction against its own header comment. `ObjectType.hpp:138`
documents `ObjectType12` as `///< @brief Purpose unknown; declared for completeness.` — but
`Decor.cpp` uses it extensively and unambiguously as the crate ("caisse") type:
`UpdateCaisse()` builds its crate index by scanning for exactly this value —

*From `Decor.cpp:9302-9312`:*
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

— and the entire crate-pushing subsystem covered in [Chapter 21](ch21-physics-and-collision.md)
keys off it too. This is a small but genuine gap between the enum header's own documentation
effort and the code it describes, and it is worth flagging precisely because it demonstrates why
this book insists on reading `Decor.cpp`'s actual usage rather than trusting a comment, however
carefully written, at face value.

## The `DecorAction` enum

`DecorAction` (`include/WindowsPhoneSpeedyBlupi/decor/DecorAction.hpp`) is a much smaller enum: it
names the camera-shake animation currently playing on the background layer, not a moving object at
all.

*From `DecorAction.hpp:43-49`:*
```cpp
enum class DecorAction : DecorActionUnderlying
{
    None          = 0, ///< @brief No camera shake is active; the viewport is stationary.
    SmallShake    = 1, ///< @brief Triggered by minor impacts: a crate landing, a small explosion, or Blupi collecting a bonus item.
    BigShake      = 2, ///< @brief Triggered by major impacts: Blupi walking into a fan blade or a large explosion.
    ElectricShake = 5, ///< @brief Triggered when Blupi contacts an electric field (ObjectType90 spark object); produces a rapid jittery motion.
};
```

The header notes that values 3 and 4 are simply unassigned in the original game — the sequence
jumps straight from `BigShake` (2) to `ElectricShake` (5), a small archaeological fossil of
whatever else the original C# `DecorAction` enum once contained. `Decor::m_decorAction` holds the
single currently-active action; `DecorNextAction()` (declared in `Decor.hpp:769-784`, implemented
elsewhere in `Decor.cpp`) consults `Tables::table_decor_action` each frame to compute the pixel
offset for the current shake frame and resets the field to `None` once the sequence is exhausted.
Every trigger site this chapter's methods touch — `ObjectStart` chains reacting to enemy contact,
`DynamiteStart`'s central blast, `ActiveSwitch` — sets `m_decorAction` and `m_decorPhase = 0`
together, then lets `MoveStep()`'s per-frame call to `DecorNextAction()` carry it to completion.

## Object creation: `ObjectStart`

`ObjectStart()` is the single entry point that spawns a new `MoveObject` into the pool:

*From `Decor.cpp:7805-7873`:*
```cpp
int Decor::ObjectStart(TinyPoint pos, ObjectType type, int speed)
{
    int num = MoveObjectFree();
    if (num == -1)
    {
        return -1;
    }
    m_moveObject[num].type = type;
    m_moveObject[num].phase = 0;
    m_moveObject[num].posCurrent = pos;
    m_moveObject[num].posStart = pos;
    m_moveObject[num].posEnd = pos;
    MoveObjectStepIcon(num);
    if (speed != 0)
    {
        TinyPoint tinyPoint = pos;
        int num2 = speed;
        int num3 = 0;
        TinyPoint dir;
        if (num2 > 50)
        {
            num2 -= 50;
            dir.X = 0;
            dir.Y = 1;
            num3 = SearchDistRight(tinyPoint, dir, type);
            tinyPoint.Y += num3;
        }
        ...
        if (num3 == 0)
        {
            if (type == ObjectType::ObjectType23)
            {
                m_moveObject[num].type = ObjectType::ObjectType0;
                return num;
            }
        }
        else
        {
            m_moveObject[num].posEnd = tinyPoint;
            m_moveObject[num].timeStopStart = 0;
            m_moveObject[num].stepAdvance = Config::ScaleTime(std::abs(num2 * num3 / 64));
            m_moveObject[num].step = 2;
            m_moveObject[num].time = 0;
        }
    }
    MoveObjectPriority(num);
    return num;
}
```

The `speed` parameter is a compact encoding, not a literal pixels-per-frame value: its sign and
magnitude select a cardinal direction (encoded as `num2 > 50` for down, `< -50` for up, `> 0` for
right, `< 0` for left, with 50 subtracted/added back out for the vertical cases), and
`SearchDistRight()` (covered in [Chapter 21](ch21-physics-and-collision.md)) is used to find how
far the object can actually travel in that direction before hitting a blocking tile. That distance
becomes `posEnd`, and the object's constant-`speed` "how many pixels per frame" request is turned
into `stepAdvance`, the frame count `MoveObjectStepLine()` will take to interpolate from `posStart`
to `posEnd` — one call spawns the object, orients it, and starts it moving in a single step. A
zero `speed` spawns a stationary object (used for effects, pickups, and anything a level file
places directly). Every call ends with `MoveObjectPriority()`, which is a bullet-only fast-path
covered later in this chapter.

## Object destruction: `ObjectDelete`

*From `Decor.cpp:7881-7917`:*
```cpp
bool Decor::ObjectDelete(TinyPoint pos, ObjectType type)
{
    int num = MoveObjectSearch(pos, type);
    if (num == -1)
    {
        return false;
    }
    if (
        m_moveObject[num].type == ObjectType::ObjectType4 ||
        m_moveObject[num].type == ObjectType::ObjectType12 ||
        m_moveObject[num].type == ObjectType::ObjectType16 ||
        m_moveObject[num].type == ObjectType::ObjectType17 ||
        m_moveObject[num].type == ObjectType::ObjectType20 ||
        m_moveObject[num].type == ObjectType::ObjectType40 ||
        m_moveObject[num].type == ObjectType::ObjectType96 ||
        m_moveObject[num].type == ObjectType::ObjectType97)
    {
        int num2 = 17;
        double animationSpeed = 1.0;
        if (m_moveObject[num].type == ObjectType::ObjectType4)
        {
            num2 = 7;
        }
        if (m_moveObject[num].type == ObjectType::ObjectType17 || m_moveObject[num].type == ObjectType::ObjectType20)
        {
            num2 = 33;
        }
        if (m_moveObject[num].type == ObjectType::ObjectType40)
        {
            animationSpeed = 0.5;
        }
        ByeByeAdd(m_moveObject[num].channel, m_moveObject[num].icon, m_moveObject[num].posCurrent, num2,
                  animationSpeed);
    }
    m_moveObject[num].type = ObjectType::ObjectType0;
    return true;
}
```

Freeing a slot is nothing more than resetting `type` back to `ObjectType0` — the rest of the
struct's stale data is simply left in place and overwritten the next time `ObjectStart()` claims
that slot. But for a specific set of "physical" object types (the bulldozer, the crate, several
walking enemies, the follower pair, and the invert power-up) deletion is not silent: it calls
`ByeByeAdd()` (the same debris-fragment pool covered in [Chapter 20](ch20-enemy-and-creature-ai.md))
using the object's *current* sprite as the fragment's appearance, with a per-type spin speed
(`num2`) tuned so heavier things (the bulldozer, spin speed 7) tumble more slowly than lighter ones
(fish/birds at 33). This is why destroying a crate or an enemy is visually punctuated even though
the `MoveObject` slot itself vanishes instantly — the debris system is layered independently on top.

## Editing the tile map: `ModifDecor`

*From `Decor.cpp:7925-7933`:*
```cpp
void Decor::ModifDecor(TinyPoint pos, int icon)
{
    int icon2 = m_decor[pos.X / 64][pos.Y / 64].icon;
    if (icon == -1 && icon2 >= 126 && icon2 <= 137)
    {
        ByeByeAdd(PixmapChannel::Object, icon2, pos, 17.0, 1.0);
    }
    m_decor[pos.X][pos.Y].icon = icon;
}
```

`ModifDecor()` is the single choke point for writing into the static `m_decor[][]` tile grid at
run time (`pos` is a game-space pixel position, divided by 64 to reach the tile index) — every
switch toggle, dynamite blast, and door-open call in this book's other Part IV chapters routes
through it. Note the special case: clearing a fan tile (icon in the 126–137 range, the fan/blower
family) to `-1` spins off a debris fragment of the fan's own sprite, exactly as `IsVentillo()`
consuming a fan's air column does (see [Chapter 21](ch21-physics-and-collision.md)) — the game
consistently treats "a fan piece disappearing" as something that should look like it broke apart
rather than teleported out of existence. The method does no bounds checking; the caller is
responsible for keeping `pos` inside the 100×100 map.

## The per-frame driver: `MoveObjectStep`

*From `Decor.cpp:7944-7987`:*
```cpp
void Decor::MoveObjectStep()
{
    m_blupiVector.X = 0;
    m_blupiVector.Y = 0;
    m_blupiTransport = -1;
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType0)
        {
            continue;
        }
        MoveObjectStepLine(i);
        MoveObjectStepIcon(i);
        if (m_moveObject[i].type == ObjectType::ObjectType4 || m_moveObject[i].type == ObjectType::ObjectType33 || m_moveObject[i].type == ObjectType::ObjectType32)
        {
            int num = MovePersoDetect(m_moveObject[i].posCurrent);
            if (num != -1)
            {
                ...
                ObjectStart(posCurrent, ObjectType::ObjectType8, 0);
                PlaySound(SoundChannel::SoundChannel10, m_moveObject[i].posCurrent);
                m_decorAction = DecorAction::SmallShake;
                m_decorPhase = 0;
                ...
                ObjectDelete(m_moveObject[i].posCurrent, m_moveObject[i].type);
                ObjectStart(posCurrent, ObjectType::ObjectType37, 0);
                ObjectDelete(m_moveObject[num].posCurrent, m_moveObject[num].type);
            }
            if (BlupiElectro(m_moveObject[i].posCurrent))
            {
                ...
                ObjectStart(posCurrent, ObjectType::ObjectType38, 55);
                PlaySound(SoundChannel::SoundChannel59, posCurrent);
            }
        }
    }
}
```

Every gameplay frame walks the entire 200-slot pool once, skipping free slots, and calls exactly
two per-object methods in order — `MoveObjectStepLine()` for motion, then `MoveObjectStepIcon()`
for animation and type-specific logic. Before the loop starts it clears `m_blupiVector` and
`m_blupiTransport`; both are re-asserted this frame only if a lift object detects Blupi standing
on it during `MoveObjectStepLine()` (see below and [Chapter 22](ch22-doors-keys-doorkeyflags.md)).
After stepping the three enemy types that can destroy a follower NPC (bulldozer `4`, and the two
Blupi-lookalike enemies `32`/`33`, detailed in [Chapter 20](ch20-enemy-and-creature-ai.md)), the
loop runs their contact reactions inline: `MovePersoDetect()` finds a nearby follower object to
crush (spawning a small explosion and shake), and `BlupiElectro()` checks whether Blupi's active
Cloud bonus should zap that enemy into an electric-arc effect (`ObjectType38`) instead.

## Linear motion: `MoveObjectStepLine`

This is the method that actually advances `posCurrent` along the `posStart`↔`posEnd` axis.

*From `Decor.cpp:8005-8174` (excerpted):*
```cpp
void Decor::MoveObjectStepLine(int i)
{
    ...
    if (m_moveObject[i].posStart.X != m_moveObject[i].posEnd.X || m_moveObject[i].posStart.Y != m_moveObject[i].
        posEnd.Y)
    {
        if (m_moveObject[i].step == 1)
        {
            if (m_moveObject[i].time < m_moveObject[i].timeStopStart)
            {
                m_moveObject[i].time++;
            }
            else
            {
                m_moveObject[i].step = 2;
                m_moveObject[i].time = 0;
            }
        }
        else if (m_moveObject[i].step == 2)
        {
            if (m_moveObject[i].posCurrent.X != m_moveObject[i].posEnd.X || m_moveObject[i].posCurrent.Y !=
                m_moveObject[i].posEnd.Y)
            {
                m_moveObject[i].time++;
                if (m_moveObject[i].stepAdvance != 0)
                {
                    m_moveObject[i].posCurrent.X = (m_moveObject[i].posEnd.X - m_moveObject[i].posStart.X) *
                        m_moveObject[i].time / m_moveObject[i].stepAdvance + m_moveObject[i].posStart.X;
                    m_moveObject[i].posCurrent.Y = (m_moveObject[i].posEnd.Y - m_moveObject[i].posStart.Y) *
                        m_moveObject[i].time / m_moveObject[i].stepAdvance + m_moveObject[i].posStart.Y;
                }
            }
            else if (m_moveObject[i].type == ObjectType::ObjectType15 || m_moveObject[i].type == ObjectType::ObjectType23)
            {
                m_moveObject[i].type = ObjectType::ObjectType0;
            }
            ...
            else
            {
                m_moveObject[i].step = 3;
                m_moveObject[i].time = 0;
            }
        }
        else if (m_moveObject[i].step == 3)
        {
            if (m_moveObject[i].time < m_moveObject[i].timeStopEnd)
            {
                m_moveObject[i].time++;
            }
            else
            {
                m_moveObject[i].step = 4;
                m_moveObject[i].time = 0;
            }
        }
        else if (m_moveObject[i].step == 4)
        {
            ...
            else
            {
                m_moveObject[i].step = 1;
                m_moveObject[i].time = 0;
            }
        }
    }
    ...
}
```

`step` cycles through exactly four phases: `1` dwells at `posStart` for `timeStopStart` frames,
`2` interpolates linearly from `posStart` to `posEnd` over `stepAdvance` frames, `3` dwells at
`posEnd` for `timeStopEnd` frames, and `4` interpolates back over `stepRecede` frames, looping to
`1`. Crucially, position is *recomputed from the frame counter* every tick
(`(posEnd - posStart) * time / stepAdvance + posStart`), not accumulated frame over frame, so the
motion can never drift out of sync even after millions of frames. One-shot objects short-circuit
this cycle: bubbles (`ObjectType15`) and bullets (`ObjectType23`) delete themselves the instant
they reach `posEnd` in step 2 rather than dwelling and receding, and goo (`ObjectType34`) instead
collapses its own start/end onto its current position and continues from step 3 — it has arrived
and become permanently stuck, no longer patrolling anywhere.

The function's other half handles the platform-lift special case (types `1`, `47`, `48`): it
builds a thin rectangle across the lift's top surface and Blupi's feet, and if they overlap it
records the lift's per-frame displacement into `m_blupiVector` and sets `m_blupiTransport = i` so
`BlupiStep()` (covered in [Chapter 17](ch17-blupi-state-machine.md)) carries him along —
types `47`/`48` add a constant ±2px/frame conveyor-belt nudge on top of the lift's own motion.
[Chapter 22](ch22-doors-keys-doorkeyflags.md) covers the lift ("ascenseur") mechanics this
enables in full. The homing follower type `97` is also special-cased here rather than in
`MoveObjectStepIcon()`: it walks one pixel per frame toward Blupi's current position (via
`TestPath()`) instead of running the four-phase cycle at all, and explodes if its path becomes
blocked.

## Animation and per-type behaviour: `MoveObjectStepIcon`

`MoveObjectStepIcon()` is the largest single function this chapter covers — roughly 850 lines
implementing a flat `if`-chain keyed on `ObjectType`, run once per object per frame immediately
after `MoveObjectStepLine()`. It is also the mechanism that chapter 32's illustrated object
animation catalogue will need to walk, so this section documents the pattern in detail.

The overwhelmingly common shape is table-driven cycling: compute an index from the phase counter,
look it up in one of `Tables`' `table_*` arrays (declared in `Tables.hpp` and populated in
`Tables.cpp`), and store the result into the object's own `icon`/`channel` fields for
`Build()` to draw later that frame:

*From `Decor.cpp:8309-8313`:*
```cpp
if (m_moveObject[i].type == ObjectType::ObjectType6)
{
    m_moveObject[i].icon = 21 + m_moveObject[i].phase / Config::ScaleDiv(4) % 8;
    m_moveObject[i].channel = PixmapChannel::Element;
}
```

Two variants of this pattern recur constantly. The simplest is direct arithmetic on the phase
counter, as above — a fixed base icon plus `phase` divided down and taken modulo the frame count.
The other indirects through a named table so non-contiguous or hand-tuned frame sequences (a key
spinning through an irregular icon set, or a dynamite fuse's "pseudo-random" flicker) can be
expressed as data instead of arithmetic:

*From `Decor.cpp:8194-8201`:*
```cpp
if (m_moveObject[i].type == ObjectType::ObjectType47)
{
    m_moveObject[i].icon = Tables::table_chenille[m_moveObject[i].phase / Config::ScaleDiv(1) % 6];
}
if (m_moveObject[i].type == ObjectType::ObjectType48)
{
    m_moveObject[i].icon = Tables::table_chenillei[m_moveObject[i].phase / Config::ScaleDiv(1) % 6];
}
```

`table_chenille`/`table_chenillei` ("chenille" — French for caterpillar, i.e. a tank-tread pattern)
animate the tread texture of the two conveyor-lift variants, and their own doc comment in
`Tables.hpp:589-602` confirms they walk the same six icons (311–316) forward and in reverse — the
same icon range `AscenseurShift()` (see [Chapter 22](ch22-doors-keys-doorkeyflags.md)) uses to
recognise a "shiftable" wide lift platform, tying the animation table directly back to a
gameplay predicate elsewhere in the file.

Every self-expiring effect (explosions, splashes, sparkle trails) follows the same three-line
shape: compare `phase` against `Config::ScaleTime(N)` where `N` is the table's own frame count,
free the slot if exceeded, otherwise index the table:

*From `Decor.cpp:8395-8406`:*
```cpp
if (m_moveObject[i].type == ObjectType::ObjectType8)
{
    if (m_moveObject[i].phase / Config::ScaleDiv(1) >= Tables::table_explo1Length)
    {
        m_moveObject[i].type = ObjectType::ObjectType0;
    }
    else
    {
        m_moveObject[i].icon = Tables::table_explo1[m_moveObject[i].phase / Config::ScaleDiv(1)];
        m_moveObject[i].channel = PixmapChannel::Explosion;
    }
}
```

`Config::ScaleTime()`/`Config::ScaleDiv()` (`Config.hpp:131-159`) are the mechanism that keeps
every one of these frame counts correct regardless of the configured frame rate: the original
game's timers are all expressed at 20 FPS, and both functions multiply by `CURRENT_FPS /
ORIGINAL_FPS` so a "20-frame" explosion still takes exactly one second of wall-clock time whether
the build runs at 20, 60, or any other configured FPS. `ScaleDiv()` is literally implemented as a
call to `ScaleTime()` (`Config.hpp:156-159`) — the two names exist purely so a reader of
`Decor.cpp` can tell at a glance whether a given constant is being used as a frame-count threshold
or as an animation-phase divisor, even though the underlying arithmetic is identical.

Not every branch is purely cosmetic. `ObjectType52` (a bridge-construction animation) writes its
own current icon directly back into the static tile map every frame it is active, so the visible
bridge tile and the moving object's own sprite stay in lockstep as the bridge appears to build
itself:

*From `Decor.cpp:8540-8562`:*
```cpp
if (m_moveObject[i].type == ObjectType::ObjectType52)
{
    ...
    if (m_moveObject[i].phase >= Config::ScaleTime(157))
    {
        m_moveObject[i].type = ObjectType::ObjectType0;
    }
    else
    {
        m_moveObject[i].icon = Tables::table_bridge[m_moveObject[i].phase / Config::ScaleDiv(1) % 157];
        m_moveObject[i].channel = PixmapChannel::Object;
        pos.X = m_moveObject[i].posStart.X / 64;
        pos.Y = m_moveObject[i].posStart.Y / 64;
        m_decor[pos.X][pos.Y].icon = m_moveObject[i].icon;
    }
}
```

And `ObjectType56` (the dynamite fuse) is entirely hand-coded rather than table-driven for its
side effects: it fires a scripted sequence of `DynamiteStart()` blasts at fixed phase ticks (50,
53, 55, 56, 59, 62, 64, 67, 69) before self-destructing at phase 70 — the explosion-catalogue
chapter's raw material, and the mechanic [Chapter 21](ch21-physics-and-collision.md) covers from
the blast-radius/collision side. The function ends the same way for every branch, advancing and
wrapping the phase counter:

*From `Decor.cpp:9042-9046`:*
```cpp
m_moveObject[i].phase++;
if (m_moveObject[i].phase > 32700 * Config::ScaleDiv(1))
{
    m_moveObject[i].phase = 0;
}
```

## Sorting, priority, and search

Three small utility methods keep the pool organised for drawing and lookup.

`SortGetType()`/`MoveObjectSort()` assign each object a coarse draw-order bucket and reorder the
pool so `Build()` paints back-to-front correctly:

*From `Decor.cpp:9908-9922`:*
```cpp
int Decor::SortGetType(ObjectType type)
{
    switch (type)
    {
    case ObjectType::ObjectType2:
    case ObjectType::ObjectType3:
    case ObjectType::ObjectType96:
    case ObjectType::ObjectType97:
        return 1;
    case ObjectType::ObjectType12:
        return 2;
    default:
        return 3;
    }
}
```

Small patrol enemies draw behind everything else (bucket 1), crates sit in the middle (bucket 2),
and every other type — including Blupi's lifts, collectibles, and effects — draws in front (bucket
3). `MoveObjectSort()` (`Decor.cpp:9933-9970`) uses this in two passes: first it compacts the pool
so every active object occupies a leading slot (pushing free slots to the tail), then it
bubble-sorts that active prefix by `SortGetType()`. Because compaction and sorting both move
objects between slots, it finishes by calling `UpdateCaisse()` to rebuild the crate index and
clearing `m_nbLinkCaisse` — any index into `m_moveObject[]` held across a call to `MoveObjectSort()`
is stale afterward.

`MoveObjectPriority()` is a narrower, bullet-specific fast-path called at the end of every
`ObjectStart()`:

*From `Decor.cpp:9978-10003`:*
```cpp
void Decor::MoveObjectPriority(int i)
{
    MoveObject dst;
    if (i == 0 || m_moveObject[i].type != ObjectType::ObjectType23)
    {
        return;
    }
    for (int j = 0; j < MAXMOVEOBJECT; j++)
    {
        if (m_moveObject[j].type == ObjectType::ObjectType23)
        {
            continue;
        }
        if (j <= i)
        {
            MoveObjectCopy(dst, m_moveObject[i]);
            MoveObjectCopy(m_moveObject[i], m_moveObject[j]);
            MoveObjectCopy(m_moveObject[j], dst);
            if (m_moveObject[i].type == ObjectType::ObjectType12 || m_moveObject[j].type == ObjectType::ObjectType12)
            {
                UpdateCaisse();
            }
        }
        break;
    }
}
```

It only acts on newly-spawned bullets (`ObjectType23`), swapping a bullet toward the front of the
pool so it is stepped and drawn ahead of the objects it might hit that same frame — it is a no-op
for every other type.

`MoveObjectSearch()` is overloaded for exact-position lookup, with a bullet-specific tolerance
band:

*From `Decor.cpp:10016-10046`:*
```cpp
int Decor::MoveObjectSearch(TinyPoint pos, std::optional<ObjectType> type)
{
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType0 || (type.has_value() && m_moveObject[i].type != *type))
        {
            continue;
        }
        if (m_moveObject[i].type == ObjectType::ObjectType23 && m_moveObject[i].posStart.X != m_moveObject[i].posEnd.X)
        {
            if (m_moveObject[i].posCurrent.X >= pos.X - 100 && m_moveObject[i].posCurrent.X <= pos.X + 100 &&
                m_moveObject[i].posCurrent.Y == pos.Y)
            {
                return i;
            }
        }
        ...
        else if (m_moveObject[i].posCurrent.X == pos.X && m_moveObject[i].posCurrent.Y == pos.Y)
        {
            return i;
        }
    }
    return -1;
}
```

Most objects must match `posCurrent` exactly; a moving bullet is allowed to match anywhere within
±100px along its own axis of travel (with the perpendicular axis still exact), so `ObjectDelete()`
called against a bullet's *origin* cell can still find it after it has already travelled some
distance that frame.

## Deletion and free-slot search

`MoveObjectDelete()` removes every object whose *start or end* tile matches a given cell — used
when a level edit or door action needs to sweep away anything anchored to a specific tile, not
just whatever currently occupies it:

*From `Decor.cpp:9867-9887`:*
```cpp
int Decor::MoveObjectDelete(TinyPoint cel)
{
    int result = -1;
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type != ObjectType::ObjectType0)
        {
            if (cel.X == m_moveObject[i].posStart.X / 64 && cel.Y == m_moveObject[i].posStart.Y / 64)
            {
                result = ToRaw(m_moveObject[i].type);
                m_moveObject[i].type = ObjectType::ObjectType0;
            }
            else if (cel.X == m_moveObject[i].posEnd.X / 64 && cel.Y == m_moveObject[i].posEnd.Y / 64)
            {
                result =ToRaw(m_moveObject[i].type);
                m_moveObject[i].type = ObjectType::ObjectType0;
            }
        }
    }
    return result;
}
```

`MoveObjectFree()` is the simple linear scan `ObjectStart()` relies on to find an available slot:

*From `Decor.cpp:9889-9901`:*
```cpp
int Decor::MoveObjectFree()
{
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType0)
        {
            // The self-assignment is a harmless no-op carried over from the original port.
            m_moveObject[i].type = ObjectType::ObjectType0;
            return i;
        }
    }
    return -1;
}
```

The in-code comment on the self-assignment is itself a small piece of porting archaeology: it is
a faithful, dead line preserved from whatever the original C# assignment looked like, kept rather
than "cleaned up" so the C++ port stays line-for-line traceable back to its source — consistent
with this book's own [Chapter 1](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md)
account of the project's decompile-and-port methodology. Both `MoveObjectFree()` and
`ObjectStart()` return `-1` when the pool is exhausted, and every caller in `Decor.cpp` checks for
it — a full level, with two hundred slots split between the level's designed content and every
transient bullet, splash, and explosion, can genuinely run out of room for a new spawn.

## See also

- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 16 — The Tile Map](ch16-tile-map.md)
- [Chapter 17 — Blupi: the State Machine](ch17-blupi-state-machine.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md)
- [Chapter 30 — Tables: Animation and Movement Data](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md)
- [Chapter 32 — The Creature and Object Animation Catalog](../part05-sprites-rendering-animation/ch32-creature-and-object-animation-catalog.md)
- [Appendix B — Enum Catalog](../appendices/appendix-b-enum-catalog.md)
