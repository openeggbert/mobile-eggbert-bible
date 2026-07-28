# Chapter 17: Blupi — the State Machine

This chapter is a close read of `Decor::BlupiStep()`, the single method that decides, every frame,
what Blupi is doing and why — walking, jumping, dying, swimming, or reacting to a hazard. It
follows the function in the order it actually executes, stopping to explain each phase in turn, and
leaves the mapping from a resolved action to an actual sprite for Chapter 18.

## The player, as a state machine

Everything the player experiences moment to moment in Speedy Blupi — walking, jumping, riding a
jeep, swimming, getting electrocuted, dying, teleporting — is the output of one method:
`Decor::BlupiStep()`. It is called once per frame from `MoveStep()` (Chapter 15), after every
moving object has already been advanced for the frame, and it is, without much competition, the
single largest hand-coded state machine in the codebase: the function body runs from
`Decor.cpp:2734` to `Decor.cpp:6546`, roughly **3,800 lines**, more than a third the size of
several entire other source files in the project. Its own doc comment does not undersell this:

*From `Decor.cpp:2710-2732`:*
```cpp
/**
 * @note Core Blupi physics + action state machine; the single largest hand-coded state
 *       machine in the file. Per-frame order of operations:
 *         1. BlupiAdjust() resolves any stuck-in-wall situation left by the previous frame.
 *         2. The proposed move is end = m_blupiPos + m_blupiVector.
 *         3. Wind/ventilator tile effects are applied when Blupi is on an air-vent tile.
 *         4. Ground contact (flag2) and ceiling (flag3) are probed via DecorDetect().
 *         5. Hazard/feature detection runs: lava, traps, drips, saws, springs, switches,
 *            bridges, doors, teleporters, lifts, water entry/exit, etc. Each can force an
 *            action change, death (BlupiDead), a bounce, or a teleport (SearchTeleporte).
 *         6. A large switch on m_blupiAction executes the branch for the current action
 *            (march / jump / air / helico / jeep / tank / skate / swim / surf / suspend /
 *            balloon / death / clear / ...). Each branch reads m_blupiSpeedX/Y plus state
 *            and produces the next m_blupiVector, possibly transitioning to another action.
 *         7. BlupiAdjust() snaps Blupi back out of geometry after the move is committed.
 *       BlupiSearchIcon() is invoked to refresh the sprite, and the scroll target is eased
 *       toward Blupi at the end.
 * @note m_blupiVector is both the input (this frame's intended displacement) and is
 *       recomputed here for the next frame. m_blupiValidPos is updated only while Blupi is
 *       in a non-lethal position so death can respawn him at the last safe spot.
 * @warning This method mutates a large amount of member state and has many early-exit and
 *          fall-through paths between actions; the action transitions are interdependent
 *          and ordering-sensitive. Treat it as ported game logic, not free-form code.
 */
void Decor::BlupiStep()
```

This chapter walks through `BlupiStep()` in the order it actually executes, in enough detail to
understand *why* the game feels the way it does, without attempting to narrate all 3,800 lines
individually — several of the deepest topics it touches (tile-overlap collision math, per-vehicle
acceleration curves) belong more to Chapter 21 (physics and collision), and the mapping from
action to sprite is Chapter 18's subject.

## Two supporting methods first: `BlupiRect()` and `BlupiAdjust()`

Before reading `BlupiStep()` itself, two small helper methods it calls constantly are worth
understanding on their own, because nearly every hazard and collision check in the big function
is really a variant of "build Blupi's current bounding box, then test it against something."

`BlupiRect()` computes that bounding box — and it is not a single fixed size. It changes shape
depending on which vehicle or mode Blupi is currently in:

*From `Decor.cpp:2471-2532` (abridged):*
```cpp
TinyRect Decor::BlupiRect(TinyPoint pos)
{
    TinyRect result = TinyRect();
    if (m_blupiNage || m_blupiSurf)
    {
        result.Left = pos.X + 12;  result.Right = pos.X + 60 - 12;
        if (m_blupiAction == BlupiAction::Stop)
        { result.Top = pos.Y + 5;  result.Bottom = pos.Y + 60 - 10; }
        else
        { result.Top = pos.Y + 15; result.Bottom = pos.Y + 60 - 10; }
    }
    else if (m_blupiJeep)  { result.Left = pos.X + 2;  result.Right = pos.X + 60 - 2;  result.Top = pos.Y + 10; result.Bottom = pos.Y + 60 - 2; }
    else if (m_blupiTank)  { result.Left = pos.X + 2;  result.Right = pos.X + 60 - 2;  result.Top = pos.Y + 10; result.Bottom = pos.Y + 60 - 2; }
    else if (m_blupiOver)  { result.Left = pos.X + 2;  result.Right = pos.X + 60 - 2;  result.Top = pos.Y + 2;  result.Bottom = pos.Y + 60 - 2; }
    else if (m_blupiBalloon) { result.Left = pos.X + 10; result.Right = pos.X + 60 - 10; result.Top = pos.Y + 5; result.Bottom = pos.Y + 60 - 2; }
    else if (m_blupiEcrase)  { result.Left = pos.X + 5;  result.Right = pos.X + 60 - 5;  result.Top = pos.Y + 39; result.Bottom = pos.Y + 60 - 2; }
    else { result.Left = pos.X + 12; result.Right = pos.X + 60 - 12; result.Top = pos.Y + 11; result.Bottom = pos.Y + 60 - 2; }
    return result;
}
```

The 64×64-pixel tile is always the frame of reference, but the *hitbox* Blupi actually occupies
inside it shrinks, grows, and shifts by mode: a jeep or tank is a wide, tall box (2px side margin,
top at +10); the crushed/`Ecrase` state collapses to a thin 21-pixel-tall strip pinned to the
bottom of the tile (top at +39 out of 60); swimming/surfing narrows the box and raises its top
when Blupi is actively moving versus idle. Every hazard test, every collision probe, and
`BlupiIsGround()` (`Decor.cpp:2459` — a one-pixel-tall strip just below the feet, skipped entirely
while `m_blupiTransport != -1`, i.e. while riding a lift) go through this one method, so a change
in vehicle mode instantly and consistently changes what Blupi can be hit by and what he can
squeeze through.

`BlupiAdjust()` is the penetration-recovery pass, called both at the very start of `BlupiStep()`
(to clean up anything the *previous* frame left overlapping solid geometry) and again after the
frame's movement is committed:

*From `Decor.cpp:2534-2543`:*
```cpp
/**
 * @note Penetration recovery. If Blupi's box is already clear it returns immediately.
 *       Otherwise it nudges him out of the overlap in fixed phases, each a bounded loop
 *       of up to 50 two-pixel steps (so worst case ~100px of correction): first push
 *       down (test a thin top edge), then push right, then push left, then two further
 *       horizontal passes using only the leading vertical edge. Each phase stops as soon
 *       as the probed edge is clear of any blocking tile.
 * @warning The 50-iteration cap means very deep penetration may not fully resolve; the
 *          caps are part of the original tuning and should not be raised casually.
 */
void Decor::BlupiAdjust()
```

If `BlupiRect(m_blupiPos)` doesn't overlap anything, it returns immediately — this is the common
case, every frame Blupi isn't touching geometry. Otherwise it runs up to five separate bounded
correction loops (down, right, left, then two more horizontal passes using only the leading edge),
each capped at 50 iterations of 2-pixel nudges, stopping as soon as the probed edge clears. This
is deliberately *not* a general physics solver — it is a small, fixed sequence of "try pushing this
way, then that way" passes tuned by hand for the specific geometry this game's levels contain, and
the source's own warning that the 50-iteration cap "should not be raised casually" is a signal
that someone already discovered, empirically, what happens if very deep penetration doesn't fully
resolve within it.

`BlupiBloque(pos, dir)` (`Decor.cpp:2623`) is the simpler directional sibling: it tests only a
narrow 2-pixel column on the leading edge, in the lower 20 pixels of the box (foot-level), used
before committing a horizontal step to ask "is this direction blocked?" without the full
adjustment machinery.

## Ghost mode: the one-line early exit

Before any of the "real" state machine runs, `BlupiStep()` checks a `MODERN`-only cheat state and,
if active, delegates to a completely separate, much simpler method and returns immediately:

*From `Decor.cpp:2736-2742`:*
```cpp
#ifdef MODERN
    if (m_blupiGhost)
    {
        BlupiGhostStep();
        return;
    }
#endif
```

`BlupiGhostStep()` (`Decor.cpp:2640-2707`) is Ghost cheat mode's entire physics model, and it
could not be more different from the ~3,800 lines it replaces: apply `m_blupiSpeedX/Y` directly to
`m_blupiPos` with no gravity and no collision test at all, clamp to the level's `[0, 6400-64]`
bounds, flip between `March` and `Stop` based on whether Blupi is moving, call
`BlupiSearchIcon()`, and ease the camera scroll toward him with the same margin/speed formula the
real `BlupiStep()` uses at its own end (below). Ghost mode exists purely for free debug/cheat
exploration of a level — Chapter 23 covers the cheat system in full — and its short-circuit here
is the cleanest illustration in the file of just how much of `BlupiStep()`'s bulk is dedicated to
collision, hazards, and vehicle-specific physics rather than to "moving a sprite around."

## Phase 1: the proposed move, and falling out of the map

With ghost mode ruled out, the ordinary path begins by resolving any leftover penetration
(`BlupiAdjust()`), snapshotting the previous position into `m_blupiLastPos`, and computing a
*proposed* new position from the vector left over from the previous frame:

*From `Decor.cpp:2745-2762`:*
```cpp
BlupiAdjust();
m_blupiLastPos = m_blupiPos;
TinyPoint end = m_blupiPos;
bool flag = m_blupiAir;
BlupiAction blupiAction = m_blupiAction;
end.X += m_blupiVector.X;
end.Y += m_blupiVector.Y;
if (m_blupiFocus && (end.Y + 30) / 64 >= 99)
{
    BlupiDead(BlupiAction::Clear2, std::nullopt);
    m_blupiRestart = true;
    m_blupiAir = true;
    m_blupiPos.Y = m_blupiPos.Y / 64 * 64 + BLUPIOFFY;
    PlaySound(SoundChannel::SoundChannel8, m_blupiPos);
    return;
}
```

`end` is `m_blupiVector` applied to `m_blupiPos` — note that `m_blupiVector` is *both* the
displacement this frame is about to apply *and* the value each downstream branch will overwrite
for next frame, exactly as the source's own second `@note` says. The very first hazard check in
the whole function is falling off the bottom of the map entirely: if the proposed Y position would
put Blupi past tile row 99, `BlupiDead(BlupiAction::Clear2, std::nullopt)` fires immediately and
the function returns early, skipping everything else for this frame. `Clear2` is one of several
"Clear" death variants (Chapter 18 documents the full `BlupiAction` set); this specific one is the
one used for falling into the void, and — as Chapter 15 mentioned in passing — it later triggers a
`VoyageInit()` angel/ascent animation arc in the post-death bookkeeping near the end of the
function.

Immediately after, if the frame actually moves Blupi at all, `TestPath()` (Chapter 21's Bresenham-
style stepwise march) is run against a narrow vertical strip to catch the case where a full jump
across a diagonal gap in geometry would otherwise skip through a corner (`Decor.cpp:2763-2770`).

## Phase 2: conveyor tiles, ground contact, ceiling contact

Four specific tile icons (`110`, `114`, `118`, `122`) are hard-coded conveyor/fan effects applied
directly to the proposed `end` position whenever Blupi is not riding a lift, jeep, tank, or
skateboard and has camera focus:

*From `Decor.cpp:2772-2805` (abridged):*
```cpp
icon = m_decor[(end.X + 30) / 64][(end.Y + 30) / 64].icon;
if (icon == 110) { end.X -= 9; }  // push left
if (icon == 114) { end.X += 9; }  // push right
if (icon == 118) { end.Y -= 20; } // push up
if (icon == 122) { end.Y += 20; } // push down
if (icon >= 110 && icon <= 125)
{
    m_blupiVent = true;
    // re-run TestPath against a widened rect so the vent push itself can't clip through geometry
}
```

(The `if constexpr (Config::FPS == Fps::Fps20) { ... } else { ... }` sub-pixel-accumulator
variants seen throughout this function, here and elsewhere, exist purely so the exact same
per-tick pixel displacement is reproduced bit-for-bit at 20 FPS while remaining frame-rate-
independent under `MODERN`'s variable-FPS support — see Chapter 10 for `Config`. This chapter
elides that branching in its excerpts for readability; both branches always apply the same
net displacement.)

Ground contact is then probed by testing a thin strip just below Blupi's feet at the *proposed*
position:

*From `Decor.cpp:2806-2834` (abridged):*
```cpp
rect = BlupiRect(end);
rect.Top = end.Y + 60 - 2;  rect.Bottom = end.Y + 60 - 1;
flag2 = !DecorDetect(rect);   // flag2 == true means "nothing solid below" -> about to fall
rect = BlupiRect(end);
rect.Top = end.Y + 10; rect.Bottom = end.Y + 20;
bool flag3 = DecorDetect(rect);  // ceiling / head contact
if (!m_blupiAir && !m_blupiHelico && /* ...every other vehicle/mode flag... */ && flag2 && m_blupiFocus)
{
    m_blupiAction = BlupiAction::Air;
    m_blupiPhase = 0;
    m_blupiVitesseY = 1.0;
    m_blupiAir = true;
}
```

If Blupi is currently on ordinary feet (none of the vehicle/mode flags set) and the strip below him
comes back clear, he transitions to `BlupiAction::Air` and starts falling — this is how walking off
a ledge is detected, independent of any key press.

## Phase 3: springs, jump initiation, and the fall/landing loop

Landing on an `IsRessort()` (spring) tile forcibly ejects Blupi from *any* vehicle mode he's
currently in — helicopter, jeep, tank, or skateboard are all kicked off with a small explosion
effect (`ObjectStart(…, ObjectType::ObjectType9, 0)`) and a shake before the bounce itself applies
(`Decor.cpp:2835-2912`), unless a Shield/Hide/Super-Blupi override is active. The bounce velocity
is one of the clearest examples in the file of the Power secret power directly scaling a physics
constant: `m_blupiVitesseY = m_blupiPower ? -25 : -19` if the jump button is also held, or `-16`
vs. `-10` for a passive bounce (`Decor.cpp:2900-2907`).

Jump initiation is a small two-step state machine of its own, nested inside the main one: pressing
Jump while grounded first switches to `BlupiAction::Jump` (a short wind-up animation), and only
*after* that animation has run for `Config::ScaleTime(3)` phases does the actual upward velocity
apply and the action become `Air`:

*From `Decor.cpp:2913-2947` (abridged):*
```cpp
if (jumpPressed && !m_blupiHelico && !m_blupiOver && /* ... */ && m_blupiFocus)
{
    if (m_blupiAction != BlupiAction::Jump && m_blupiAction != BlupiAction::Turn && !m_blupiAir)
    {
        m_blupiAction = BlupiAction::Jump;
        m_blupiPhase = 0;
    }
    if (m_blupiAction == BlupiAction::Jump && m_blupiPhase == Config::ScaleTime(3))
    {
        m_blupiAction = BlupiAction::Air;
        m_blupiPhase = 0;
        if (m_blupiSkate) { m_blupiVitesseY = m_blupiPower ? -17 : -13; }
        else if (IsNormalJump(end)) { m_blupiVitesseY = m_blupiPower ? -26 : -16; }
        else { m_blupiVitesseY = m_blupiPower ? -16 : -12; }
        m_blupiAir = true;
    }
}
```

`IsNormalJump()` (a small predicate on the tile under Blupi's feet) is what distinguishes a full
running jump from a shallower jump off certain surfaces, and Power again scales every one of these
velocities upward. Once airborne, the gravity-integration block runs every frame Blupi is in the
air:

*From `Decor.cpp:2948-2977` (abridged):*
```cpp
if (m_blupiAir)
{
    if (flag3 && m_blupiVitesseY < 0.0)   // hit a ceiling while still rising
    {
        if (m_blupiVitesseY < -14.0 && /* not already in a Clear/death animation, not skating */)
        {
            m_blupiJumpAie = true;         // will trigger the "hurt" landing variant
            PlaySound(SoundChannel::SoundChannel40, end);
        }
        else { PlaySound(SoundEnviron(SoundChannel::SoundChannel4, detectIcon), end); }
        m_blupiVitesseY = 1.0;             // bounce back downward
    }
    end.Y += (int)(m_blupiVitesseY * 2.0);
    if (m_blupiVitesseY < 20.0) { m_blupiVitesseY += 2.0; }   // constant downward acceleration
    // ... landing test against a strip near the feet; on contact:
    //     m_blupiAction = BlupiAction::StopJump; m_blupiAir = false;
    //     if (m_blupiJumpAie) { m_blupiAction = BlupiAction::JumpAie; }
}
```

Gravity here is not a physically-motivated constant; it is a flat `+2.0` added to `m_blupiVitesseY`
every frame, capped so it never exceeds `20.0` — a simple, hand-tuned terminal velocity rather than
any real acceleration model, exactly the kind of "ported game logic, not free-form code" the
function's own warning comment describes. Hitting your head on a ceiling hard enough
(`vitesseY < -14.0`) sets `m_blupiJumpAie`, a flag that, once Blupi lands, redirects the *landing*
animation from a plain `StopJump` to the more dramatic hurt-landing `JumpAie` — this is the
mechanism behind the recognizable "ow" reaction when you jump straight into a low ceiling.

While falling, `AscenseurDetect()` is also probed every frame (`Decor.cpp:3013-3039`): if Blupi's
downward fall intersects the top of a lift (*ascenseur*) object, he is attached to it
(`m_blupiTransport = icon`) mid-air, exactly as if he had landed on solid ground, and the lift's
own vertical position takes over from there — this is how jumping onto a moving platform from
above works without any special-casing in the render or collision code; it is purely a `MoveObject`
index stored in `m_blupiTransport` that everything else (`BlupiIsGround()`, gravity, ground
detection) is written to respect.

## Phase 4: ropes and bars

`GetTypeBarre(pos)` (`Decor.cpp:7152`) reports whether Blupi's grab point overlaps a rope/rail
tile, and its result gates a small climbing sub-state used throughout the mid-section of
`BlupiStep()` (`Decor.cpp:4744` onward) — different bar types support different combinations of
hanging, swinging, and climbing, and this is also where the 10-slot FIFO `m_blupiFifoPos`
(recorded by `BlupiAddFifo()`, `Decor.cpp:6654`) is populated, purely so the rope-hanging animation
has a short trail of recent positions to reference for its swing rendering — Chapter 18 covers
that animation's icon lookup, and Chapter 21 covers the rest of the rope-collision geometry.

## Phase 5: the hazard gauntlet

Roughly in the middle of the function sits a long, flat sequence of independent hazard checks, all
guarded by "Blupi is not already in a Clear1–Clear8 death animation" (`Decor.cpp:5494-5495`), each
testing one specific tile predicate against `m_blupiPos` and each capable of unilaterally killing,
teleporting, or otherwise redirecting Blupi regardless of whatever the rest of the state machine
was doing that frame:

*From `Decor.cpp:5497-5548` (abridged, showing the pattern):*
```cpp
if (IsLave(m_blupiPos) && !m_blupiShield && !m_blupiHide && !m_bSuperBlupi)
{
    BlupiDead(BlupiAction::Clear3, std::nullopt);
    m_blupiRestart = true;
    m_blupiPos.Y = m_blupiPos.Y / 64 * 64 + BLUPIOFFY;
    PlaySound(SoundChannel::SoundChannel8, m_blupiPos);
}
if (IsPiege(m_blupiPos) && !m_blupiOver && !m_blupiJeep && !m_blupiTank && !m_blupiShield && !m_blupiHide && !m_bSuperBlupi && m_blupiFocus)
{
    BlupiDead(BlupiAction::Glu, std::nullopt);
    m_blupiRestart = true;
    m_blupiAir = true;
    ObjectStart(m_blupiPos, ObjectType::ObjectType53, 0);
    PlaySound(SoundChannel::SoundChannel51, m_blupiPos);
}
// IsGoutte (drip), IsScie (saw) follow the identical Glu/Clear4 pattern...
if (IsBlitz(m_blupiPos, false) && !m_blupiShield && !m_blupiHide && !m_bSuperBlupi)
{
    BlupiDead(BlupiAction::Clear1, std::nullopt);
    /* ... */
}
```

The pattern repeats with small, meaningful variations: lava (`IsLave`) and lightning (`IsBlitz`)
both kill outright via `BlupiDead`, snap Blupi's Y to a tile boundary, and play the same falling-
death sound (`SoundChannel8`); traps (`IsPiege`) and drips (`IsGoutte`) instead use the `Glu`
(stuck-in-glue) death action and spawn a glue-splash object; a saw (`IsScie`) uses `Clear4` and
sets `m_blupiFront = true` so the death animation renders in front of other objects rather than
behind. Every single one of these checks is also individually guarded by `!m_blupiShield &&
!m_blupiHide && !m_bSuperBlupi` — the three ways a hazard can be no-op'd (the Shield secret power,
the Hide secret power, and the Super Blupi cheat), spelled out explicitly at every hazard site
rather than factored into one shared "is Blupi currently invincible" predicate. This is a small
but real code-quality observation about the ported source: the invincibility check is duplicated
verbatim roughly a dozen times through this section rather than centralized.

Interleaved with the lethal hazards are non-lethal interactive ones. A switch, activated by the
player-action button while standing on it (`IsSwitch`), calls `ActiveSwitch()` (Chapter 16) and
locks Blupi's focus into a brief `Switch` animation. A crusher (`IsEcraseur`) forcibly clears
*every* vehicle/mode/secret-power flag at once — the crush sequence is written out flag-by-flag
rather than delegated to `BlupiDead()`, because being crushed is not death; it is a distinct,
survivable `m_blupiEcrase` state with its own 100-frame `m_blupiTimeShield` grace timer reused for
this purpose (`Decor.cpp:5549-5591`). A teleporter tile (`IsTeleporte`) starts the `Teleporte`
action and snaps Blupi's X to a tile boundary immediately, but the *actual* relocation is deferred:
it only happens once the animation has played for `Config::ScaleTime(128)` frames, near the very
end of the function:

*From `Decor.cpp:6350-6361`:*
```cpp
if (m_blupiAction == BlupiAction::Teleporte && m_blupiPhase == Config::ScaleTime(128))
{
    TinyPoint newpos;
    if (SearchTeleporte(m_blupiPos, newpos))
    {
        m_blupiPos = newpos;
        ObjectStart(m_blupiPos, ObjectType::ObjectType27, 20);
        ObjectStart(m_blupiPos, ObjectType::ObjectType27, -20);
    }
    m_blupiFocus = true;
    m_blupiPosHelico = m_blupiPos;
}
```

`SearchTeleporte()` (`Decor.cpp:7398`) is the pairing mechanism itself, and it is worth calling out
because teleporters have no side table anywhere in `Decor`: pairing is implicit in the tile icon
range alone (entry icons `330`–`333` and their exit counterparts), and finding "the other end"
means scanning the whole 100×100 map for a matching icon at call time. A door tile
(`IsDoor`) is checked immediately after, and the key-consumption logic that opens it is a compact
piece of bit-flag arithmetic worth reading directly:

*From `Decor.cpp:5614-5619`:*
```cpp
int num = IsDoor(m_blupiPos, celBridge);
const DoorKeyFlags doorKeyMask = ToDoorKeyFlags(1 << (num - 334));
if (num != -1 && (m_blupiCle & doorKeyMask) != DoorKeyFlags::None)
{
    OpenDoor(celBridge);
    m_blupiCle = ToDoorKeyFlags(ToRaw(m_blupiCle) & ~ToRaw(doorKeyMask));
}
```

`IsDoor()` returns a *tile icon number* (starting at `334`), not a door index, and the door-key
bitmask is derived directly from it by subtracting `334` and shifting — meaning the door icon
numbering scheme and the `DoorKeyFlags` bit layout are coupled by this one line of arithmetic
rather than by an explicit lookup table. Chapter 22 covers doors and `DoorKeyFlags` in full.

## Phase 6: entering and leaving water

A separate block, gated on "not in any of the vehicle-like modes" (`Decor.cpp:5284-5285`), governs
the transitions between walking, surfing, and swimming, keyed on two tile predicates,
`IsSurfWater()` (shallow) and `IsDeepWater()` (deep):

*From `Decor.cpp:5287-5327` (abridged):*
```cpp
if (!m_blupiNage && !m_blupiSurf && IsSurfWater(m_blupiPos))
{
    m_blupiSurf = true;
    m_blupiAction = BlupiAction::Stop;
    MoveObjectPlouf(m_blupiPos);          // splash effect
    if (m_blupiTransport != -1) { m_blupiPos.Y -= 10; m_blupiTransport = -1; }  // dismount a lift into water
    if (m_blupiCloud) { m_blupiCloud = false; m_jauges[1].SetHide(true); }      // Cloud power cannot be used in water
}
if (!m_blupiNage && !IsSurfWater(m_blupiPos) && IsDeepWater(m_blupiPos))
{
    m_blupiSurf = false;
    m_blupiNage = true;
    m_blupiLevel = 100;
    m_jauges[0].SetLevel(m_blupiLevel);   // the red gauge becomes an air/stamina meter while swimming
    m_jauges[0].SetMode(JaugeMode::Blue);
    m_jauges[0].SetHide(false);
}
```

Entering shallow water switches to surf mode and always plays a splash; wading into deep water
switches to swim mode and repurposes the HUD's gauge 0 (normally the life/energy bar, red) as a
blue underwater meter initialized to a full 100 — a nice example of `Decor` reusing one piece of
UI state for two entirely different gameplay meanings depending on context rather than allocating
a second widget. Jumping out of water requires both being at a specific sub-tile Y offset (a water
surface boundary check, `m_blupiPos.Y % 64 == 64 - BLUPISURF`) and pressing Jump while at
`IsOutWater()` — the exit velocity is again Power-scaled (`-16.0` vs `-12.0`,
`Decor.cpp:5338-5358`).

## Phase 7: per-mode turn completion

A flat `if`/`else if` chain partway through the function handles one specific, recurring
transition — finishing a `Turn` animation and flipping `m_blupiDir` — separately for every
vehicle/mode, because each one plays its turn animation for a different duration:

*From `Decor.cpp:3472-3588` (summarized; each branch follows the same shape as the Helicopter one shown):*
```cpp
if (m_blupiHelico)
{
    if (m_blupiAction == BlupiAction::Turn && m_blupiPhase == Config::ScaleTime(10))
    {
        m_blupiAction = BlupiAction::March;
        m_blupiDir = (m_blupiDir == Direction::Left) ? Direction::Right : Direction::Left;
    }
}
else if (m_blupiOver)   { /* Config::ScaleTime(7),  -> March */ }
else if (m_blupiJeep)   { /* Config::ScaleTime(7),  -> Stop  */ }
else if (m_blupiTank)   { /* Config::ScaleTime(12), -> Stop  */ }
else if (m_blupiSkate)  { /* Config::ScaleTime(14), -> Stop  */ }
else if (m_blupiNage || m_blupiSurf) { /* Config::ScaleTime(10), -> March */ }
else if (m_blupiSuspend) { /* Config::ScaleTime(10), -> Stop */ }
else /* ordinary on-foot */ { /* Config::ScaleTime(6), -> Stop */ }
```

The differing durations (6 ticks on foot, up to 14 on a skateboard) are exactly the kind of tuning
constant this book's methodology treats as original game data rather than an accident: a
skateboard visibly takes longer to turn around than bare feet do, and this is the single place in
the source where that specific piece of game feel is encoded. Note also the split in what action
each mode returns to afterward — most return to `March` (implying the turn only ever triggers
mid-walk for these modes), while Jeep, Tank, Skateboard, and Suspend return to `Stop` instead.

## Phase 8: focus-gated bookkeeping, then `BlupiSearchIcon()`

A block gated on `m_blupiFocus` handles a small cluster of phase-timeout transitions — a
`Vertigo` (edge-hanging fright) animation that, after 16 ticks, becomes a `Recede` step backward,
which itself resolves to `Stop` after 3 more ticks; and an `Advance` step (used, among other
places, to walk onto a lift or bridge) that times out back to `Stop` after 5 ticks normally, or 10
for Jeep/Tank/Skate (`Decor.cpp:5038-5069`). Immediately afterward, **`BlupiSearchIcon()` is
called** (`Decor.cpp:5070`) — not at the very end of the function, as one might expect, but
roughly two-thirds of the way through it. This is the method, covered in full in Chapter 18, that
turns `m_blupiAction` + `m_blupiPhase` + `m_blupiDir` into the actual `m_blupiIcon` sprite index
via `Tables::table_blupi`. Everything computed *after* this point in `BlupiStep()` — secret-power
timers, the teleport execution, win/loss bookkeeping — does not retroactively affect this frame's
sprite; it only affects state that will matter starting next frame.

## Phase 9: secret-power countdowns

Immediately after the icon lookup, four nearly-identical blocks tick down the remaining duration
of whichever secret power is active — Shield, Power, Cloud, Hide — each on its own countdown
cadence and each sharing the single `m_blupiTimeShield` field as the actual counter (despite the
name, this field is reused as the generic "remaining bonus time" timer for whichever bonus
currently owns it, not exclusively for the Shield power):

*From `Decor.cpp:5071-5104` (abridged, showing two of the four near-identical blocks):*
```cpp
if (m_blupiShield)
{
    if (m_blupiTimeShield == 10) { PlaySound(SoundChannel::SoundChannel43, m_blupiPos); }  // warning chime
    if (m_blupiTimeShield == 0) { m_blupiShield = false; m_jauges[1].SetHide(true); }
    else if (m_time % Config::ScaleTime(5) == 0) { m_blupiTimeShield--; m_jauges[1].SetLevel(m_blupiTimeShield); }
}
if (m_blupiPower)
{
    if (m_blupiTimeShield == 20) { PlaySound(SoundChannel::SoundChannel45, m_blupiPos); }  // earlier warning
    if (m_blupiTimeShield == 0) { m_blupiPower = false; m_jauges[1].SetHide(true); }
    else if (m_time % Config::ScaleTime(3) == 0) { m_blupiTimeShield--; m_jauges[1].SetLevel(m_blupiTimeShield); }
}
```

Each power decrements at a different real-time rate (every 5 ticks for Shield, every 3 for Power,
every 4 for Cloud) and plays its own distinct "about to expire" warning sound at its own threshold
tick count — a set of tuning values that only make sense read directly from the source, since
nothing about the `SecretPower` enum itself encodes duration or urgency. `m_jauges[1]`, the yellow
gauge, is the shared visual countdown for whichever of these is currently active.

## Phase 10: `BlupiElectro()`, and what "electrocuted" actually means

It is worth being precise about one easily-misread method name here. `BlupiElectro(pos)`
(`Decor.cpp:9610`) is *not* the mechanism by which a lightning hazard electrocutes Blupi — that is
`IsBlitz()` in the hazard gauntlet above, feeding into an ordinary `BlupiDead(Clear1)` call.
`BlupiElectro()` is the *reverse*: it is only meaningful while the Cloud secret power is active,
and it tests whether Blupi's own lightning aura can reach and destroy a nearby enemy at `pos`:

*From `Decor.cpp:9604-9638`:*
```cpp
/**
 * @note Only meaningful while the Cloud bonus is active (returns false otherwise, and
 *       always false in ghost mode): the cloud's lightning arcs to a nearby enemy. It tests
 *       the enemy box at @p pos against Blupi's box inflated by 40px on all sides, i.e. the
 *       arc reach. A true result tells the caller to electrocute/destroy that enemy.
 */
bool Decor::BlupiElectro(TinyPoint pos)
{
    if (m_blupiGhost) { return false; }
    if (!m_blupiCloud) { return false; }
    TinyRect src  = { pos.X + 16, pos.X + 60 - 16, pos.Y + 11, pos.Y + 60 - 2 };
    TinyRect src2 = { m_blupiPos.X - 16 - 40, m_blupiPos.X + 60 + 16 + 40,
                       m_blupiPos.Y + 11 - 40, m_blupiPos.Y + 60 - 2 + 40 };
    TinyRect dst;
    return Misc::IntersectRect(dst, src, src2);
}
```

It is called from the per-object AI dispatcher (Chapter 20), not from `BlupiStep()` directly —
included here because its name so closely parallels the hazard-side `Electro` `BlupiAction` (the
animation played when Blupi *is* electrocuted, Chapter 18) that conflating the two is an easy
mistake, and the source itself only disambiguates them via careful reading.

## Phase 11: death, the "Hide" respawn interval, and win conditions

Near the end of the function, a large disjunction watches for every death/hazard animation's
completion tick simultaneously — `Clear1` through `Clear8`, `Drown`, `Glu`, `Electro`, each with
its own specific frame count — and, when one finishes, either restarts Blupi (if lives remain) or
ends the level:

*From `Decor.cpp:6374-6400` (abridged):*
```cpp
if ((m_blupiAction == BlupiAction::Clear1 && m_blupiPhase == Config::ScaleTime(70)) ||
    (m_blupiAction == BlupiAction::Clear2 && m_blupiPhase == Config::ScaleTime(100)) ||
    /* ... six more Clear/Drown/Glu/Electro variants, each its own frame count ... */)
{
    if (m_nbVies > 0)
    {
        m_blupiAction = BlupiAction::Hide;
        m_blupiIcon = -1;
        if (m_blupiRestart) { m_blupiPos = m_blupiValidPos; }
        VoyageInit(VoyageGetPosVie(m_nbVies), /* ... */, 48, PixmapChannel::Blupi);  // life icon flies to HUD
    }
    else
    {
        m_nbVies = -1;
        m_term = -1;
        DoorsLost();
    }
}
```

A life remaining sends Blupi to a literal `Hide` action with `m_blupiIcon = -1` (invisible) at
`m_blupiValidPos` — the last position recorded as safe, tracked by the bookkeeping described next
— and fires a `VoyageInit()` life-icon-flies-to-the-HUD animation exactly like a collectible
pickup, reusing the same visual mechanism Chapter 19 documents for treasure collection. Running out
of lives sets `m_term = -1` (loss, per Chapter 15's `IsTerminated()` contract) and calls
`DoorsLost()` to reset any doors opened during the failed attempt.

The **valid-position bookkeeping** that feeds `m_blupiValidPos` is a single, carefully-guarded
condition checked every frame:

*From `Decor.cpp:6467-6478`:*
```cpp
if (m_blupiFocus && !m_blupiAir && (!m_blupiHelico || BlupiIsGround()) && (!m_blupiOver || BlupiIsGround()) &&
    !m_blupiBalloon && !m_blupiEcrase && !m_blupiShield && !m_blupiHide && !bVertigoLeft && !bVertigoRight &&
    m_blupiTransport == -1 && !IsLave(m_blupiPos) && !IsPiege(m_blupiPos) && !IsGoutte(m_blupiPos, true) &&
    !IsScie(m_blupiPos) && !IsBridge(m_blupiPos, celSwitch) && IsTeleporte(m_blupiPos) == -1 &&
    !IsBlitz(m_blupiPos, true) && !IsTemp(m_blupiPos) && !IsBalleTraj(m_blupiPos) && !IsMoveTraj(m_blupiPos))
{
    if (m_blupiFifoNb > 0) { m_blupiValidPos = m_blupiFifoPos[0]; }
    BlupiAddFifo(m_blupiPos);
}
```

Only when Blupi is grounded, focused, touching none of the lethal or interactive hazard tiles, and
not mid-transition through any special state does his position get recorded as "safe" — and even
then, it records the *oldest* entry currently in the FIFO trail rather than the current position
outright, so a respawn lands slightly behind where death actually occurred rather than exactly on
top of the hazard that caused it.

The level-win condition (`Decor.cpp:6411-6435`) is checked when the `Win` action's 40-tick
animation completes, and it is where mission numbering becomes concrete: a private (user-created)
level simply sets `m_term = 1`; the very first hub mission (`m_mission == 1`) jumps to `199` (a
reserved "meta" world index); finishing the reserved end-game mission `199` sets the special value
`-2`; and an ordinary sub-level either opens the level's gold chests (if the key was found) or
advances `m_term` to `m_mission / 10 * 10` (rounding down to the current world's base index) —
Chapter 24 unpacks this numbering scheme fully.

## Phase 12: scroll easing and frame-end bookkeeping

The function's last substantial block eases the camera scroll target toward Blupi using a speed
that itself grows the farther the camera has fallen behind — the same style of margin-based easing
`MoveHotSpot()` uses for zoom (Chapter 15):

*From `Decor.cpp:6479-6527` (abridged):*
```cpp
end.X = m_blupiPos.X + 30 + m_scrollAdd.X;
end.Y = m_blupiPos.Y + 30 + m_scrollAdd.Y;
int num3 = SCROLL_SPEED;   // base 8 px/frame
if (std::abs(m_scrollPoint.X - end.X) > SCROLL_MARGX * 2) { num3 += (/* excess */) / 4; }
if (std::abs(m_scrollPoint.Y - end.Y) > SCROLL_MARGY * 2) { num3 += (/* excess */) / 4; }
// m_scrollPoint is nudged toward end.X/end.Y by num3 pixels, clamped so it never overshoots
if (m_blupiAction != BlupiAction::Clear2 && m_blupiAction != BlupiAction::Clear3)
{
    m_posDecor = GetPosDecor(m_scrollPoint);
}
```

The `Clear2`/`Clear3` exclusion is deliberate: those are the two death variants that launch a
`VoyageInit()` ascent arc straight up off-screen (the "angel" and "balloon" death animations,
Chapter 18), and freezing `m_posDecor` during them keeps the camera from chasing Blupi's corpse
skyward mid-animation. The function closes by stepping the `VoyageStep()` animation, updating
positional audio (`PosSound()`, every 4th frame), and recording this frame's speed and key-press
state (`m_blupiLastSpeedX/Y`, `m_lastKeyPress`) for next frame's edge-detection comparisons —
precisely the kind of bookkeeping that makes "was this key *just* pressed" logic possible
elsewhere in the function without a separate input-history subsystem.

## `BlupiDead()`: the shared death entry point

Every one of the hazard checks above ultimately funnels through one shared method,
`BlupiDead(action1, action2)`:

*From `Decor.cpp:6538-6614` (abridged):*
```cpp
void Decor::BlupiDead(BlupiAction action1, std::optional<BlupiAction> action2)
{
    ByeByeHelico();   // spawns helicopter debris; a no-op if Blupi wasn't flying one
    m_blupiAction = action2.has_value()
        ? ((m_random.get()->Next() % 2 == 0) ? action1 : *action2)
        : action1;
    m_blupiPhase = 0;
    m_blupiFocus = false;
    // every single vehicle/mode/bonus flag is explicitly cleared here:
    m_blupiHelico = m_blupiOver = m_blupiJeep = m_blupiTank = m_blupiSkate = false;
    m_blupiNage = m_blupiSurf = m_blupiSuspend = m_blupiJumpAie = false;
    m_blupiShield = m_blupiPower = m_blupiCloud = m_blupiHide = false;
    m_blupiInvert = m_blupiBalloon = m_blupiEcrase = m_blupiRestart = false;
    m_jauges[0].SetHide(true);
    m_jauges[1].SetHide(true);
    StopSound(SoundChannel::SoundChannel16); /* ... 18, 29, 31: every vehicle motor loop ... */
    if (m_blupiAction == BlupiAction::Clear2) { /* VoyageInit angel-ascent arc, icon 230 */ }
    if (m_blupiAction == BlupiAction::Clear3) { /* VoyageInit balloon-ascent arc, icon 40, further and slower */ }
    if (m_blupiAction == BlupiAction::Clear4) { /* spawns four ObjectType41 debris pieces */ }
}
```

`BlupiDead()` is called with a single action, or, in several hazard sites, with *two* — in which
case a coin flip picks one at random, which is why dying to the same hazard twice does not always
look identical. It is also the one guaranteed place every vehicle, mode, and bonus flag gets reset
to a known-clean state at once, which is precisely why death is treated throughout `Decor` as the
universal reset mechanism: no matter how deeply nested Blupi's current mode combination was (Jeep
plus Shield plus mid-Turn, say), death always produces the same flat, known baseline for whatever
comes next — either the respawn described in Phase 11, or the level-loss path.

## See also

- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 16 — The Tile Map](ch16-tile-map.md)
- [Chapter 18 — Blupi Actions and Animation](ch18-blupi-actions-and-animation.md)
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md)
- [Chapter 23 — Secret Powers and the Cheat System](ch23-secret-powers-and-cheat-system.md)
- [Chapter 24 — Missions and ContinueMission](ch24-missions-and-continuemission.md)
- [Chapter 31 — The Blupi Animation Catalog](../part05-sprites-rendering-animation/ch31-blupi-animation-catalog.md)
