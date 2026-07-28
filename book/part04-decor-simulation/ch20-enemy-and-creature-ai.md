# Chapter 20: Enemy and Creature AI

[Chapter 19](ch19-moving-objects-and-decor-actions.md) covered how a `MoveObject` moves and
animates once it is spawned. This chapter covers the layer above that: the detection methods that
decide when Blupi and an enemy have actually collided, the hand-coded behaviours specific to each
creature type, and two effect sequences — "ByeBye" and "Voyage" — whose names give away almost
nothing about what they actually do. Every claim about what a given ambiguous name means is
verified below directly against `Decor.cpp`, not inferred from the identifier alone.

## Two styles of AI, one dispatcher

`Decor.cpp`'s own file-header comment states the split plainly:

*From `Decor.cpp:46-52`:*
```
##   Object AI state machines
##   Two styles coexist. Most enemies/effects are *table-driven*: a MoveObject moves
##   linearly between posStart and posEnd (advance/recede speeds + end-dwell timers in
##   MoveObjectStepLine) while its animation/lifetime is a phase counter indexed into
##   the Tables animation arrays by MoveObjectStepIcon(). A minority of behaviours are
##   *hand-coded* with bespoke logic keyed on ObjectType inside MoveObjectStepIcon()
##   and its helpers (dynamite, charging enemies, followers, cloud-nets, crates).
```

The detection methods in this chapter are how the hand-coded half decides *when* to act: they
answer "is Blupi standing on this?", "is this enemy touching Blupi?", "should this enemy wake up?"
— queries the pure linear-motion state machine in `MoveObjectStepLine()` has no way to express on
its own.

## Tile collision: `DecorDetect` and `TestPath`

Before any enemy-specific logic can run, the engine needs a general answer to "does this rectangle
overlap solid geometry?" Two overloads share the implementation:

*From `Decor.cpp:6678-6772`:*
```cpp
bool Decor::DecorDetect(TinyRect rect)
{
    return DecorDetect(rect, true);
}

bool Decor::DecorDetect(TinyRect rect, bool bCaisse)
{
    m_detectIcon = -1;
    if (rect.Left < 0 || rect.Top < 0)
    {
        // Treat positions outside the left/top of the world as solid boundaries.
        return true;
    }
    ...
    int num2 = rect.Left / 16;
    int num3 = (rect.Right + 16 - 1) / 16;
    int num4 = rect.Top / 16;
    int num5 = (rect.Bottom + 16 - 1) / 16;
    ...
    for (int i = num4; i <= num5; i++)
    {
        for (int j = num2; j <= num3; j++)
        {
            int num6 = j / 4;
            int num7 = i / 4;
            ...
            int icon = m_decor[num6][num7].icon;
            if (icon < 0 || icon >= MAXQUART || (m_blupiHelico && icon == 214) || (m_blupiOver && icon == 214) || (
                icon == 324 && m_time / 4 % 20 >= 18))
            {
                continue;
            }
            num6 = j % 4;
            num7 = i % 4;
            if (Tables::table_decor_quart[icon * 16 + num7 * 4 + num6] != 0)
            {
                ...
                if (Misc::IntersectRect(dst, src, rect))
                {
                    m_detectIcon = icon;
                    return true;
                }
            }
        }
    }
    if (!bCaisse)
    {
        return false;
    }
    for (int k = 0; k < m_nbRankCaisse; k++)
    {
        ...
        if (Misc::IntersectRect(dst, src, rect))
        {
            m_detectIcon = m_moveObject[num8].icon;
            return true;
        }
    }
    return false;
}
```

Collision is sub-tile, not per-64px-tile: `Tables::table_decor_quart` is a per-icon bitmap dividing
each tile into a 4×4 grid of 16px "quart" cells, so a single tile icon can be solid on one corner
and open on another (a slope, or a half-wall). The `bCaisse` parameter controls whether crates
count as blocking geometry too — the two-overload split exists because crate-pushing logic (see
[Chapter 21](ch21-physics-and-collision.md)) sometimes needs to ask "is the *terrain* clear?"
independently of "is a crate in the way?" Out-of-bounds left/top and the right wall are always
solid; the bottom wall is solid only while Blupi is in a free-floating mode (helicopter, over,
balloon, crushed, swimming, or surfing) — on foot, falling off the bottom of the map is not itself
blocked here. Two icons get conditional treatment: `214` is non-solid while Blupi is flying or
riding the overcraft, and `324` (a blinking/temporary platform) is non-solid for part of its own
20-tick blink cycle (`m_time / 4 % 20 >= 18`).

`TestPath()` builds on `DecorDetect()` to answer a directional question — how far can something
travel from `start` toward `end` before it would hit something:

*From `Decor.cpp:6774-6867` (excerpted):*
```cpp
bool Decor::TestPath(const TinyRect& rect, const TinyPoint& start, TinyPoint& end)
{
    int num = std::abs(end.X - start.X);
    int num2 = std::abs(end.Y - start.Y);
    TinyPoint tinyPoint = start;
    ...
    if (num > num2)
    {
        if (end.X > start.X)
        {
            for (int i = 0; i <= num; i++)
            {
                int num3 = i * (end.Y - start.Y) / num;
                rect2.Left = rect.Left + i;
                rect2.Right = rect.Right + i;
                rect2.Top = rect.Top + num3;
                rect2.Bottom = rect.Bottom + num3;
                if (DecorDetect(rect2))
                {
                    end = tinyPoint;
                    return false;
                }
                tinyPoint.X = start.X + i;
                tinyPoint.Y = start.Y + num3;
            }
        }
        ...
    }
    ...
    return true;
}
```

This is a Bresenham-style march: it steps one pixel at a time along whichever axis has the greater
distance to travel, deriving the minor-axis offset by linear interpolation, and calls
`DecorDetect()` at every step. On the first collision it rewinds `end` to the last confirmed-clear
position and returns `false`; if the whole path is clear, `end` is left unchanged and it returns
`true`. This is the method the homing follower (`ObjectType97`, discussed below) uses every frame
to check whether its one-pixel step toward Blupi is actually walkable.

## `MoveObjectFollow`: waking dormant followers

*From `Decor.cpp:9640-9678`:*
```cpp
void Decor::MoveObjectFollow(TinyPoint pos)
{
#ifdef MODERN
    if (m_blupiGhost)
    {
        return;
    }
#endif
    if (m_blupiHide)
    {
        return;
    }
    TinyRect src = BlupiRect(pos);
    src.Left = pos.X + 16;
    src.Right = pos.X + 60 - 16;
    TinyRect src2 = TinyRect();
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType96)
        {
            src2.Left = m_moveObject[i].posCurrent.X - 100;
            src2.Right = m_moveObject[i].posCurrent.X + 60 + 100;
            src2.Top = m_moveObject[i].posCurrent.Y - 100;
            src2.Bottom = m_moveObject[i].posCurrent.Y + 60 + 100;
            TinyRect dst;
            if (Misc::IntersectRect(dst, src2, src))
            {
                m_moveObject[i].type = ObjectType::ObjectType97;
                PlaySound(SoundChannel::SoundChannel92, m_moveObject[i].posCurrent);
            }
        }
    }
}
```

`ObjectType96` and `ObjectType97` (both documented in `ObjectType.hpp:84-85` as "follow enemy
variant 1"/"variant 2") are two states of the *same* enemy, not two different creatures: `96` is
the dormant patrol form (animated via `Tables::table_follow1`, a slow 26-frame cycle), and once
Blupi's box comes within a 100px-padded detection zone, this method promotes it in place to `97`
— the active homing form, animated via the much shorter `table_follow2` (5 frames) and stepped by
the bespoke one-pixel-per-frame logic inside `MoveObjectStepLine()` covered in
[Chapter 19](ch19-moving-objects-and-decor-actions.md). Hiding (the Hide secret power) or ghost
mode (a `MODERN`-only cheat) suppresses detection entirely, so a hidden Blupi can walk past a
dormant follower without waking it.

## `MoveObjectDetect`: the general contact scan

*From `Decor.cpp:9689-9771` (excerpted):*
```cpp
int Decor::MoveObjectDetect(TinyPoint pos, bool& bNear)
{
#ifdef MODERN
    if (m_blupiGhost)
    {
        bNear = false;
        return -1;
    }
#endif
    TinyRect src = BlupiRect(pos);
    src.Left = pos.X + 16;
    src.Right = pos.X + 60 - 16;
    TinyRect src2 = TinyRect();
    src2.Left = src.Left - 20;
    src2.Right = src.Right + 20;
    src2.Top = src.Top - 40;
    src2.Bottom = src.Bottom + 30;
    TinyRect src3 = TinyRect();
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType0 || m_moveObject[i].type == ObjectType::ObjectType27 || ...
            m_moveObject[i].type == ObjectType::ObjectType38 || ((m_blupiAction == BlupiAction::Push || m_blupiAction == BlupiAction::Pop) && m_moveObject[i].type ==
                ObjectType::ObjectType12))
        {
            continue;
        }
        src3.Left = m_moveObject[i].posCurrent.X + 16;
        src3.Right = m_moveObject[i].posCurrent.X + 60 - 16;
        src3.Top = m_moveObject[i].posCurrent.Y + 36;
        src3.Bottom = m_moveObject[i].posCurrent.Y + 60;
        if (m_moveObject[i].type == ObjectType::ObjectType3)
        {
            if (m_blupiAction == BlupiAction::Down)
            {
                continue;
            }
            src3.Top = m_moveObject[i].posCurrent.Y;
            src3.Bottom = m_moveObject[i].posCurrent.Y + 60 - 36;
        }
        if (m_moveObject[i].type == ObjectType::ObjectType12)
        {
            src3.Left = m_moveObject[i].posCurrent.X - 16;
            src3.Right = m_moveObject[i].posCurrent.X + 64 + 16;
            ...
        }
        ...
        TinyRect dst;
        if (Misc::IntersectRect(dst, src3, src))
        {
            bNear = true;
            return i;
        }
        if (m_moveObject[i].type == ObjectType::ObjectType2 && Misc::IntersectRect(dst, src3, src2))
        {
            bNear = false;
            return i;
        }
    }
    bNear = false;
    return -1;
}
```

This is the general "what is Blupi touching?" scan used for both damage and pickup logic
throughout `BlupiStep()`. It skips a fixed set of non-interactive types (sparkle trails, glue,
clear/electric effects) and skips crates entirely while Blupi is mid-push (`BlupiAction::Push`/
`Pop`, so pushing a crate doesn't also register as "touching" it for damage purposes). Each
candidate type gets a tuned contact box: a type-`3` hazard only registers from above (unless
Blupi is ducking with `BlupiAction::Down`), a crate (`12`) widens its box on the side Blupi is
approaching from, and a bullet (`23`) uses a tight central core. The return distinguishes an actual
overlap (`bNear = true`) from a wider "anticipation" box that only a thrown enemy (`ObjectType2`)
triggers with `bNear = false` — letting the caller react (e.g. play a warning cue) before contact
actually lands.

## `MoveAscenseurDetect`, `MoveChargeDetect`, `MovePersoDetect`

Three narrower detectors follow the identical box-overlap pattern for three unrelated purposes.

*From `Decor.cpp:9773-9865`:*
```cpp
int Decor::MoveAscenseurDetect(TinyPoint pos, int height)
{
    if (m_blupiTimeNoAsc != 0)
    {
        return -1;
    }
    TinyRect src = TinyRect();
    src.Left = pos.X + 12;
    src.Right = pos.X + 60 - 12;
    src.Top = pos.Y + 60 - 2;
    src.Bottom = pos.Y + 60 + height - 1;
    ...
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType1 || m_moveObject[i].type == ObjectType::ObjectType47 || m_moveObject[i].type == ObjectType::ObjectType48)
        {
            ...
            if (Misc::IntersectRect(dst, src2, src))
            {
                return i;
            }
        }
    }
    return -1;
}

int Decor::MoveChargeDetect(TinyPoint pos)
{
    ...
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType31)
        {
            ...
            if (Misc::IntersectRect(dst, src2, src))
            {
                return i;
            }
        }
    }
    return -1;
}

int Decor::MovePersoDetect(TinyPoint pos)
{
    ...
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type >= ObjectType::ObjectType200 && m_moveObject[i].type <= ObjectType::ObjectType203)
        {
            ...
            if (Misc::IntersectRect(dst, src2, src))
            {
                return i;
            }
        }
    }
    return -1;
}
```

`MoveAscenseurDetect()` finds a lift (`ObjectType1/47/48`) directly below a probe rectangle,
gated by `m_blupiTimeNoAsc` (a short cooldown set after Blupi slides off a lift's edge, covered in
[Chapter 22](ch22-doors-keys-doorkeyflags.md)). `MoveChargeDetect()` finds a nearby "charge/cloud"
power-up object (`ObjectType31`) to power the Cloud bonus's lightning-arc attack. `MovePersoDetect()`
is the odd one out: despite the "perso" (French *personnage*, "character") name suggesting an NPC
follower, it actually scans for the Blupi *avatar-skin* objects — `ObjectType200` through `203`,
documented in `ObjectType.hpp:197-200` as alternate-costume pickups and multi-skin Blupi lookalikes.
This is exactly the method `MoveObjectStep()` calls (see [Chapter 19](ch19-moving-objects-and-decor-actions.md))
to let the bulldozer and the two Blupi-hostile clone enemies (`32`/`33`, below) destroy a
skin-variant object they collide with — it is a "find the other Blupi-shaped thing" query, not a
generic follower-NPC query.

## `MockeryDetect`: enemy taunts

*From `Decor.cpp:9509-9602` (excerpted):*
```cpp
int Decor::MockeryDetect(TinyPoint pos)
{
    if (m_blupiTimeMockery > 0)
    {
        return 0;
    }
    if (m_blupiAir)
    {
        TinyPoint tinyPoint;
        tinyPoint.X = pos.X + 30;
        tinyPoint.Y = pos.Y + 30 + 64;
        if (tinyPoint.X >= 0 && tinyPoint.X < 6400 && tinyPoint.Y >= 0 && tinyPoint.Y < 6400)
        {
            int icon = m_decor[tinyPoint.X / 64][tinyPoint.Y / 64].icon;
            if (icon == 68 || icon == 317)
            {
                return 64;
            }
        }
        ...
    }
    ...
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type != ObjectType::ObjectType2 && ... )
        {
            continue;
        }
        ...
        if (m_moveObject[i].type == ObjectType::ObjectType54)
        {
            return 83;
        }
        if (m_blupiDir == Direction::Right)
        {
            if (pos.X < src2.Left)
            {
                if (m_moveObject[i].type == ObjectType::ObjectType2)
                {
                    return 0;
                }
                return 63;
            }
            return 64;
        }
        ...
    }
    return 0;
}
```

This decides whether — and which — taunt icon should appear over an enemy near Blupi. It returns
`0` (no taunt) while a cooldown (`m_blupiTimeMockery`) is active. Airborne over lava or a spike trap
(icons `68`/`317` — see [Chapter 21](ch21-physics-and-collision.md) for `IsLave`/`IsEcraseur`)
always returns taunt icon `64` regardless of enemies. Otherwise it scans the same family of patrol
enemies `MoveObjectDetect()` recognises, picking taunt icon `63`, `64`, or `83` based on which side
of Blupi the enemy sits relative to his facing direction — the giant creature (`ObjectType54`,
below) always gets its own dedicated taunt icon `83`, while a thrown-projectile enemy (`ObjectType2`)
approaching head-on suppresses the taunt entirely (`return 0`) rather than mocking Blupi from a
position that would look wrong on screen.

## `MoveObjectPollution`: not what the name suggests

*From `Decor.cpp:6869-6989` (excerpted):*
```cpp
void Decor::MoveObjectPollution()
{
    bool flag = false;
    TinyPoint blupiPos = m_blupiPos;
    TinyPoint tinyPoint;
    tinyPoint.X = 0;
    tinyPoint.Y = 0;
    int num = 20;
    if (m_blupiAction == BlupiAction::Turn)
    {
        return;
    }
    if (m_blupiHelico)
    {
        if (m_blupiVitesseY < -5.0)
        {
            if (m_time % 20 != 0 && m_time % 20 != 2 && ... )
            {
                return;
            }
        }
        ...
        tinyPoint.X = 22;
        flag = true;
    }
    if (m_blupiOver) { ... flag = true; }
    if (m_blupiJeep) { ... flag = true; }
    if (m_blupiTank) { ... flag = true; }
    if (!flag)
    {
        return;
    }
    if (m_blupiDir == Direction::Right)
    {
        blupiPos.X -= tinyPoint.X - 5;
        ...
    }
    else
    {
        blupiPos.X += tinyPoint.X;
    }
    blupiPos.Y += tinyPoint.Y;
    ObjectStart(blupiPos, ObjectType::ObjectType36, num);
}
```

Despite the header comment's own admission ("Despite the name…"), `MoveObjectPollution()` has
nothing to do with an environmental hazard — it emits the vehicle exhaust/smoke puff effect
(`ObjectType36`, documented in `ObjectType.hpp:139` as a "pollution / cloud puff effect") behind
whichever vehicle Blupi is currently driving: helicopter, overcraft, jeep, or tank. Each vehicle
gets its own dense, hand-tuned schedule of `m_time % N` / `m_blupiPhase % N` checks so puffs
appear at irregular intervals that feel organic rather than metronomic, and differ between idling
and moving. `tinyPoint` is the per-vehicle nozzle offset behind Blupi's sprite and `num` sets the
puff's lifetime; the name "pollution" is simply what the original game called the smoke-puff
`ObjectType`, and the method inherited it.

## `MoveObjectPlouf`, `MoveObjectTiplouf`, `MoveObjectBlup`: verified

The assignment for this chapter singled these three out as names that sound like water-splash
creatures and asked for verification rather than a guess from the name alone. Reading the code
confirms the intuition, precisely:

*From `Decor.cpp:6991-7003`:*
```cpp
void Decor::MoveObjectPlouf(TinyPoint pos)
{
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType14)
        {
            return;
        }
    }
    pos.Y -= 45;
    PlaySound(SoundChannel::SoundChannel23, pos);
    ObjectStart(pos, ObjectType::ObjectType14, 0);
}
```

`MoveObjectPlouf()` spawns `ObjectType14` — "plouf" being the French onomatopoeia for a splash — a
one-shot 7-frame water-entry splash animated via `Tables::table_plouf` (`ObjectType.hpp:157`),
guarded so only one plays at a time.

*From `Decor.cpp:7005-7025`:*
```cpp
void Decor::MoveObjectTiplouf(TinyPoint pos)
{
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type == ObjectType::ObjectType35)
        {
            return;
        }
    }
    if (m_blupiDir == Direction::Right)
    {
        pos.X += 5;
    }
    else
    {
        pos.X -= 5;
    }
    pos.Y -= 45;
    PlaySound(SoundChannel::SoundChannel64, pos);
    ObjectStart(pos, ObjectType::ObjectType35, 0);
}
```

`MoveObjectTiplouf()` ("ti-" being a diminutive prefix, "little plouf") spawns `ObjectType35`, a
distinct, smaller splash — a separate object type with its own single-instance guard, offset
slightly in Blupi's facing direction, used for smaller water impacts than the full `Plouf`.

*From `Decor.cpp:7027-7069` (excerpted):*
```cpp
void Decor::MoveObjectBlup(TinyPoint pos)
{
    PlaySound(SoundChannel::SoundChannel24, pos);
    pos.Y -= 20;
    int num = 0;
    TinyPoint tinyPoint = pos;
    while (tinyPoint.Y > 0)
    {
        int icon = m_decor[(tinyPoint.X + 16) / 64][tinyPoint.Y / 64].icon;
        if (icon != 91 && icon != 92)
        {
            break;
        }
        num++;
        tinyPoint.Y -= 64;
    }
    num--;
    if (num > 0)
    {
        int num2 = MoveObjectFree();
        if (num2 != -1)
        {
            m_moveObject[num2].type = ObjectType::ObjectType15;
            ...
            m_moveObject[num2].posEnd.X = pos.X;
            m_moveObject[num2].posEnd.Y = pos.Y - num * 64;
            ...
            m_moveObject[num2].stepAdvance = Config::ScaleTime(num * 10);
            ...
        }
    }
}
```

`MoveObjectBlup()` spawns `ObjectType15` — "blup" being the bubbling-underwater onomatopoeia — a
rising bubble, but unlike the two splashes it is not a fixed animation: it first walks upward
tile by tile counting consecutive water tiles (icons `91`/`92`, shallow and deep water, see
[Chapter 21](ch21-physics-and-collision.md)) to find how far the bubble can actually rise before
breaking the surface, then spawns the bubble with `posEnd` set that many tiles higher and a rise
speed proportional to the distance. If there is no clear water column above the spawn point
(`num <= 0`), no bubble is spawned at all. All three names — plouf, tiplouf, blup — are exactly
what they sound like: water-impact sound-effect objects, distinguished by size and, in blup's
case, by an actual physical simulation of how far it can float.

## Creature-specific patrol animation

The remaining assignment-listed creatures — bulldozer, fish, bird, wasp, the giant creature, and
the two Blupi-hostile clones — all share one animation shape inside `MoveObjectStepIcon()`, keyed
on the object's own `step` (the four-phase cycle from [Chapter 19](ch19-moving-objects-and-decor-actions.md))
and which direction it is currently patrolling:

*From `Decor.cpp:8628-8669` (bulldozer, `ObjectType4`, excerpted):*
```cpp
if (m_moveObject[i].type == ObjectType::ObjectType4)
{
    if (m_moveObject[i].posStart.X > m_moveObject[i].posEnd.X)
    {
        if (m_moveObject[i].step == 1)
        {
            m_moveObject[i].icon = Tables::table_bulldozer_turn2l[(m_moveObject[i].time / Config::ScaleDiv(1)) % 22];
        }
        if (m_moveObject[i].step == 3)
        {
            m_moveObject[i].icon = Tables::table_bulldozer_turn2r[(m_moveObject[i].time / Config::ScaleDiv(1)) % 22];
        }
        if (m_moveObject[i].step == 2)
        {
            m_moveObject[i].icon = Tables::table_bulldozer_left[(m_moveObject[i].time / Config::ScaleDiv(1)) % 8];
        }
        if (m_moveObject[i].step == 4)
        {
            m_moveObject[i].icon = Tables::table_bulldozer_right[(m_moveObject[i].time / Config::ScaleDiv(1)) % 8];
        }
    }
    else { /* mirrored: left/right and turn tables swapped */ }
    m_moveObject[i].channel = PixmapChannel::Element;
}
```

Every patrol creature repeats this exact structure with its own table family: eight walking-cycle
frames for steps 2/4 (moving), and a longer turn-around sequence for steps 1/3 (the dwell at each
end of the patrol, used to visually pivot the creature before it walks back). The turn sequence
length scales with how elaborate that creature's turn animation is: the bulldozer and fish and
bird use 22/48/10 frames respectively, the giant creature ("`ObjectType54`", `table_creature_turn2`)
uses a lavish 152-frame turn, and the two Blupi clones use 26 (`blupih`) and 24 (`blupit`) frames.
`ObjectType17` (fish, `table_poisson_*` — "poisson" is French for fish) and `ObjectType20` (bird,
`table_oiseau_*` — "oiseau" is French for bird) and `ObjectType44` (wasp, `table_guepe_*` —
"guêpe" is French for wasp) all confirm their French-language table names describe exactly the
creature the surrounding `Decor.cpp` collision code (`Decor.cpp:5766-5825`, `Decor.cpp:9744-9749`)
treats them as.

Two of these patrol creatures carry extra, hand-coded behaviour beyond animation. The giant
creature, `ObjectType54`, destroys Blupi's helicopter and traps him rather than simply damaging
him:

*From `Decor.cpp:5867-5893` (excerpted, in the Blupi-side contact handler):*
```cpp
if (m_moveObject[icon].type == ObjectType::ObjectType54 && m_moveObject[icon].step != 2 && m_moveObject[icon].step != 4 &&
    m_blupiFocus && !m_blupiBalloon && !m_blupiShield && !m_blupiHide && !m_bSuperBlupi)
{
    ByeByeHelico();
    celSwitch.X = m_blupiPos.X;
    celSwitch.Y = (m_blupiPos.Y + 64 - 10) / 64 * 64 + 4;
    ObjectStart(celSwitch, ObjectType::ObjectType53, 0);
    m_blupiAction = BlupiAction::Glu;
    m_blupiPhase = 0;
    ...
}
```

Contact with the creature (only while it is turning, not mid-stride) spawns `ObjectType53` — the
"tentacle" hazard documented in `ObjectType.hpp:144` — at Blupi's feet and forces
`BlupiAction::Glu`, a stuck/trapped state, while `ByeByeHelico()` (below) discards any helicopter
Blupi was riding. This confirms `ObjectType54`'s own doc comment ("destroys Blupi's helicopter on
contact") directly against the code that implements it.

The two Blupi-hostile clones, `blupih` (`ObjectType32`) and `blupit` (`ObjectType33`), are both
turret-like patrol enemies that fire `ObjectType23` projectiles at scripted points in their turn
animation:

*From `Decor.cpp:8878-8886` (`blupih`):*
```cpp
if ((m_moveObject[i].step == 1 || m_moveObject[i].step == 3) && m_moveObject[i].time == Config::ScaleTime(21))
{
    pos.X = m_moveObject[i].posCurrent.X;
    pos.Y = m_moveObject[i].posCurrent.Y + 40;
    if (ObjectStart(pos, ObjectType::ObjectType23, 55) != -1)
    {
        PlaySound(SoundChannel::SoundChannel52, pos);
    }
}
```

`blupih` fires exactly once per turn, at time tick 21. `blupit` (`Decor.cpp:8928-8949`) fires
twice per turn — once at tick 3, aimed left or right depending on which way it is about to walk,
and again at tick 21 — making it the more aggressive of the two clone enemies. Both spawn the
projectile via the ordinary `ObjectStart()` path covered in [Chapter 19](ch19-moving-objects-and-decor-actions.md),
with `SearchDistRight()` (see [Chapter 21](ch21-physics-and-collision.md)) determining how far the
bullet actually travels before hitting a wall.

## The "ByeBye" sequence: destruction debris, not a departure

The assignment framed "ByeBye" as a possible helicopter-departure sequence; reading the code shows
it is specifically destruction debris, gated so it only fires when Blupi actually has a helicopter
to lose:

*From `Decor.cpp:10048-10054`:*
```cpp
void Decor::ByeByeHelico()
{
    if (m_blupiHelico)
    {
        ByeByeAdd(PixmapChannel::Element, 68, m_blupiPos, 7.0, 0.5);
    }
}
```

`ByeByeHelico()` is a no-op unless `m_blupiHelico` is currently true; when it is, it spawns exactly
one debris fragment using icon `68` (the helicopter's own sprite, seen already in
[Chapter 21](ch21-physics-and-collision.md) as the very same icon number `IsLave()` tests for lava
— a reminder that icon numbers are reused across completely different sprite sheets/contexts, see
that chapter's discussion of `ENUMS.md`). It is called from every place Blupi's helicopter mode
can end abruptly: `BlupiDead()` (`Decor.cpp:6549`, "regardless of cause… a no-op when Blupi was
not in helicopter mode" per that method's own doc comment), the wasp/balloon-trap contact handler
(`Decor.cpp:5829`), and the giant-creature contact handler shown above (`Decor.cpp:5870`). The
general debris pool it feeds into is `ByeByeAdd()`/`ByeByeStep()`/`ByeByeDraw()`:

*From `Decor.cpp:10056-10078` (`ByeByeAdd`, excerpted):*
```cpp
void Decor::ByeByeAdd(PixmapChannel channel, int icon, TinyPoint pos, double rotationSpeed, double animationSpeed)
{
    ByeByeObject byeByeObject;
    byeByeObject.channel = channel;
    byeByeObject.icon = icon;
    byeByeObject.posX = pos.X;
    byeByeObject.posY = pos.Y;
    ...
    int num = m_random.get()->Next(0, 10);
    if (m_random.get()->Next(0, 1000) % 2 == 0)
    {
        byeByeObject2.speedX = num + 10;
    }
    else
    {
        byeByeObject2.speedX = -(num + 10);
    }
    byeByeObjects.push_back(byeByeObject2);
}
```

*From `Decor.cpp:10087-10127` (`ByeByeStep`, excerpted):*
```cpp
void Decor::ByeByeStep()
{
    int num = 0;
    while (num < byeByeObjects.size())
    {
        ByeByeObject& byeByeObject = byeByeObjects[num];
        double scaledSpeed = byeByeObject.animationSpeed * Config::SPEED_SCALE;
        double num2 = 10.0 - byeByeObject.phase;
        if (num2 > 0.0)
        {
            byeByeObject.posY -= std::pow(num2, 1.5) * scaledSpeed;
        }
        if (num2 < 0.0)
        {
            byeByeObject.posY += std::pow(0.0 - num2, 1.5) * scaledSpeed;
        }
        byeByeObject.posX += byeByeObject.speedX * scaledSpeed;
        ...
        byeByeObject.rotation += byeByeObject.rotationSpeed * Config::SPEED_SCALE;
        byeByeObject.phase += scaledSpeed;
        ...
        if (byeByeObject.phase > Config::ScaleTime(30))
        {
            byeByeObjects.erase(byeByeObjects.begin() + num);
        }
        else
        {
            num++;
        }
    }
}
```

`ByeByeObject` is a separate, purely visual pool (`std::vector<ByeByeObject> byeByeObjects`,
`Decor.hpp:601`) distinct from `MoveObject` — it never affects collision, gameplay state, or
scoring. Each fragment gets a ballistic arc (rising for the first ten phase units, falling
afterward, per `std::pow(num2, 1.5)`), decaying horizontal speed, and continuous rotation, and is
culled once its phase exceeds `Config::ScaleTime(30)`. `ObjectDelete()` ([Chapter 19](ch19-moving-objects-and-decor-actions.md))
uses the same `ByeByeAdd()` pool for its own destruction fragments — the helicopter case is simply
the one invocation with a fixed icon and a dedicated wrapper method, because it is triggered from
so many different call sites across `BlupiStep()`.

## The "Voyage" sequence: a collectible's flight to the HUD, not a level transition

The assignment raised "level transition?" and "vehicle travel montage?" as hypotheses for
"Voyage"; the code answers unambiguously: it is the fly-to-HUD animation a collected item plays,
and the actual reward is only granted at the moment that flight completes.

*From `Decor.cpp:10141-10147`:*
```cpp
TinyPoint Decor::VoyageGetPosVie(int nbVies)
{
    TinyPoint result;
    result.X = 210 + 16 * nbVies;
    result.Y = 417;
    return result;
}
```

`VoyageGetPosVie()` computes the screen position of the Nth life icon in the HUD — the destination
a collected extra-life egg flies toward.

*From `Decor.cpp:10158-10226` (`VoyageInit`, excerpted):*
```cpp
void Decor::VoyageInit(TinyPoint start, TinyPoint end, int icon, PixmapChannel channel)
{
    if (m_voyageIcon != -1)
    {
        m_voyagePhase = m_voyageTotal;
        VoyageStep();
    }
    m_voyageStart = start;
    m_voyageEnd = end;
    m_voyageIcon = icon;
    m_voyageChannel = channel;
    int num = std::abs(end.X - start.X);
    int num2 = std::abs(end.Y - start.Y);
    m_voyagePhase = 0;
    m_voyageTotal = Config::ScaleTime((num + num2) / 10);
    if (m_voyageIcon == 48 && m_voyageChannel == PixmapChannel::Blupi)
    {
        m_voyageTotal = Config::ScaleTime(40);
        m_nbVies--;
        m_sound->PlayImage(SoundChannel::SoundChannel9, end, -1, false);
    }
    ...
}
```

Only one Voyage animation can be in flight at a time: starting a new one force-completes any
already-running arc first (`m_voyagePhase = m_voyageTotal; VoyageStep();`), which immediately
applies its reward before the new arc begins. The travel duration is proportional to the Manhattan
distance between `start` and `end`, with several `(icon, channel)` combinations overriding that
duration or playing a pickup-confirmation sound up front.

*From `Decor.cpp:10237-10308` (`VoyageStep`, excerpted):*
```cpp
void Decor::VoyageStep()
{
    if (m_voyageIcon == -1)
    {
        return;
    }
    if (m_voyagePhase < m_voyageTotal)
    {
        if (m_time % Config::ScaleTime(2) == 0 && m_voyageIcon >= 230 && m_voyageIcon <= 241 && m_voyageChannel == PixmapChannel::Element)
        {
            m_voyageIcon++;
            ...
        }
    }
    else
    {
        if (m_voyageIcon == 48 && m_voyageChannel == PixmapChannel::Blupi)
        {
            m_blupiAction = BlupiAction::Stop;
            m_blupiPhase = 0;
            m_blupiFocus = true;
        }
        if (m_voyageIcon == 21 && m_voyageChannel == PixmapChannel::Element)
        {
            if (m_nbVies < MAX_EGG_COUNT)
            {
                m_nbVies++;
            }
            m_sound->PlayImage(SoundChannel::SoundChannel3, m_voyageEnd, -1, false);
        }
        if (m_voyageIcon == 6 && m_voyageChannel == PixmapChannel::Element)
        {
            m_nbTresor++;
            OpenDoorsTresor();
            m_sound->PlayImage(SoundChannel::SoundChannel3, m_voyageEnd, -1, false);
        }
        if (m_voyageIcon == 215 && m_voyageChannel == PixmapChannel::Element)
        {
            m_blupiCle = m_blupiCle | DoorKeyFlags::Key1;
            ...
        }
        ...
        m_voyageIcon = -1;
    }
    m_voyagePhase++;
}
```

While the arc is in flight, `VoyageStep()` only cycles the travelling icon (icons `230`–`241`, a
generic "flying sparkle" animation reused across several reward types); the moment `m_voyagePhase`
reaches `m_voyageTotal`, the reward is granted exactly once, keyed on the same `(icon, channel)`
pair used at init: a life gained (capped at `MAX_EGG_COUNT`, `Decor.cpp:96`), a treasure counted
and treasure-gated doors re-evaluated via `OpenDoorsTresor()` (see
[Chapter 22](ch22-doors-keys-doorkeyflags.md)), a `DoorKeyFlags` key bit set, a follower or
dynamite count incremented, or — for icon `48` on the `Blupi` channel, the angel/ascent variant —
control handed back to Blupi via `BlupiAction::Stop`. `VoyageDraw()` (`Decor.cpp:10310-10348`)
simply interpolates the drawn icon's position along the `start`→`end` line by
`phase / total`, with one extra case (icon `40`, an invert-power-up flight) that also spawns
small trailing spark particles as it flies. In short: "Voyage" is the game's name for "a picked-up
item's confirmation flight to its HUD slot," and every reward this book's Part IV chapters discuss
— extra lives, treasure, keys, followers, dynamite — is actually applied here, at the end of that
flight, not at the moment Blupi first touches the item.

## See also

- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 17 — Blupi: the State Machine](ch17-blupi-state-machine.md)
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md)
- [Chapter 30 — Tables: Animation and Movement Data](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md)
- [Chapter 32 — The Creature and Object Animation Catalog](../part05-sprites-rendering-animation/ch32-creature-and-object-animation-catalog.md)
