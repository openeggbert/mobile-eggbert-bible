# Chapter 18: Blupi Actions and Animation

This chapter picks up exactly where Chapter 17 leaves off. `BlupiStep()` decides *what* Blupi is
doing; this chapter covers how that decision becomes the sprite actually drawn on screen, via the
`BlupiAction` enum, `Decor::BlupiSearchIcon()`, and the packed animation-table format underlying
`Tables::table_blupi`.

## From gameplay state to a sprite

Chapter 17 traced how `BlupiStep()` decides, frame by frame, what Blupi is *doing* —
`m_blupiAction`, one of the values of the `BlupiAction` enum, plus a running `m_blupiPhase`
counter and a facing `m_blupiDir`. None of those three values is a sprite index. Turning that
triple into the actual icon drawn to the screen is the job of a single method,
`Decor::BlupiSearchIcon()`, and a single data table, `Tables::table_blupi`. This chapter reads
both closely: first the `BlupiAction` enum itself (every value, in the order it is declared), then
`BlupiSearchIcon()`'s mode-remapping logic, and finally the packed-record table format and lookup
algorithm that resolves an action into a frame — verified line-by-line against the real data
rather than assumed from the general shape of "animation table."

## The `BlupiAction` enum

`include/WindowsPhoneSpeedyBlupi/def/BlupiAction.hpp` declares all 88 values (`None` through
`PutDynamite`), stored as an unsigned byte to match the original C# enum's layout
(`BlupiAction.hpp:15`). Reading through it in order shows the state machine's structure more
clearly than the interleaved `if` chains in `BlupiStep()` do on their own:

*From `def/BlupiAction.hpp:35-125` (verbatim declaration order):*
```cpp
enum class BlupiAction : BlupiActionUnderlying
{
    None = 0, Stop = 1, March = 2, Turn = 3, Jump = 4, Air = 5, Down = 6, Up = 7,
    Vertigo = 8, Recede = 9, Advance = 10, Clear1 = 11, Set = 12, Win = 13, Push = 14,
    StopHelico = 15, MarchHelico = 16, TurnHelico = 17,
    StopNage = 18, MarchNage = 19, TurnNage = 20,
    StopSurf = 21, MarchSurf = 22, TurnSurf = 23, Drown = 24,
    StopJeep = 25, MarchJeep = 26, TurnJeep = 27,
    StopPop = 28, Pop = 29, Bye = 30,
    StopSuspend = 31, MarchSuspend = 32, TurnSuspend = 33, JumpSuspend = 34,
    Hide = 35, JumpAie = 36,
    StopSkate = 37, MarchSkate = 38, TurnSkate = 39, JumpSkate = 40, AirSkate = 41,
    TakeSkate = 42, DeposeSkate = 43,
    Ouf1a = 44, Ouf1b = 45, Ouf2 = 46, Ouf3 = 47, Ouf4 = 48, Sucette = 49,
    StopTank = 50, MarchTank = 51, TurnTank = 52, FireTank = 53,
    Glu = 54, Drink = 55, Charge = 56, Electro = 57, HelicoGlu = 58,
    TurnAir = 59, StopMarch = 60, StopJump = 61, StopJumph = 62,
    Mockery = 63, Mockeryi = 64, Ouf5 = 65,
    Balloon = 66, StopOver = 67, MarchOver = 68, TurnOver = 69,
    Recedeq = 70, Advanceq = 71, StopEcrase = 72, MarchEcrase = 73,
    Teleporte = 74,
    Clear2 = 75, Clear3 = 76, Clear4 = 77, Clear5 = 78, Clear6 = 79, Clear7 = 80, Clear8 = 81,
    Switch = 82, Mockeryp = 83, Non = 84,
    SlowdownSkate = 85, TakeDynamite = 86, PutDynamite = 87
};
```

The naming families — spread through the declaration rather than grouped by it — map cleanly onto
Chapter 17's structure: every vehicle/mode gets its own
`Stop*`/`March*`/`Turn*` triple (`Helico`, `Nage`, `Surf`, `Jeep`, `Suspend`, `Skate`, `Tank`,
`Over`), each independently animated and independently timed (Chapter 17's per-mode turn-duration
table is a direct consequence of this — the *code* picks the duration, but the *animation data*
for each of these actions is a wholly separate `table_blupi` record). The six `Ouf*` values are
the "phew, that was close" relief animations played after certain near-misses; the eight `Clear*`
values are the death/hazard animation variants Chapter 17's `BlupiDead()` and hazard gauntlet
choose between (`Clear1` for lightning, `Clear2` for falling off the map, `Clear3` for lava,
`Clear4` for a saw, and so on); `Mockery`/`Mockeryi`/`Mockeryp` are the poses played when an enemy
taunts Blupi (Chapter 20). The header's own note is worth repeating because it is the load-bearing
warning for this entire chapter: "This is gameplay state, not a sprite/icon index. The mapping
from `BlupiAction` to sprite frame is determined by the animation tables in `Tables.hpp`"
(`BlupiAction.hpp:30-31`).

## `BlupiSearchIcon()`: remapping the action for the current mode

`BlupiSearchIcon()` (`Decor.cpp:2123-2452`) does not look `m_blupiAction` up directly. Its first
and largest section is a long sequence of `if` blocks that *substitute* a different, more specific
action in place of the generic one, depending on which vehicle/mode/hazard flags are currently
set. A `Stop`, for instance, becomes one of nine different concrete actions depending on context:

*From `Decor.cpp:2123-2224` (abridged to show the substitution pattern):*
```cpp
BlupiAction blupi_action = m_blupiAction;
if (m_blupiVent && !m_blupiHelico && !m_blupiOver)
{
    if (blupi_action == BlupiAction::Stop)  { blupi_action = BlupiAction::Vertigo; }
    if (blupi_action == BlupiAction::March) { blupi_action = BlupiAction::Push; }
}
if (m_blupiHelico)
{
    if (blupi_action == BlupiAction::Stop)    { blupi_action = BlupiAction::StopHelico; }
    if (blupi_action == BlupiAction::March)   { blupi_action = BlupiAction::MarchHelico; }
    if (blupi_action == BlupiAction::Turn)    { blupi_action = BlupiAction::TurnHelico; }
    if (blupi_action == BlupiAction::Advance) { blupi_action = BlupiAction::StopHelico; }
    if (blupi_action == BlupiAction::Recede)  { blupi_action = BlupiAction::StopHelico; }
    m_blupiRealRotation = (int)(m_blupiVitesseX * 2.0);
}
// ... identical-shaped blocks follow for m_blupiOver, m_blupiJeep, m_blupiTank, m_blupiSkate,
//     m_blupiNage, m_blupiSurf, m_blupiSuspend, m_blupiBalloon, m_blupiEcrase ...
```

This is the mechanism by which `m_blupiAction` can stay a small, generic vocabulary
(`Stop`/`March`/`Turn`/`Advance`/`Recede`) throughout the whole of `BlupiStep()`'s hazard and
physics logic in Chapter 17, while still producing mode-correct, visually distinct animations —
`BlupiStep()` never needs to know it should be playing `MarchHelico` instead of `March`; it just
sets `March`, and `BlupiSearchIcon()` performs the substitution based on `m_blupiHelico` being
true. Some of these blocks do more than a flat substitution: the swimming (`m_blupiNage`) block
additionally computes a *rotation angle* from the sign of Blupi's recent horizontal and vertical
movement (`Decor.cpp:2273-2312`), so that swimming visibly tilts Blupi's sprite toward the
direction of travel — 8 discrete rotation targets (0°, 45°, 90°, 135°, 180°) approached smoothly
via `Misc::Approach()`, plus a small continuous sine-wave wobble (`sin(m_time / 6.0) * 20.0`)
layered on top purely for a bobbing-in-water look. The surfboard block does the same with a
gentler, slower wobble (`sin(m_time / 10.0) * 10.0`, `Decor.cpp:2328-2330`).

A handful of idle-animation sound triggers live in this same method, keyed directly on specific
phase values — for instance, the ordinary `Stop` idle plays a blink/fidget sound
(`SoundChannel37`) at a fixed set of phase offsets within a 330-tick cycle
(`scaledPhase % 330 == 125, 129, 135, 139, 215, 219, ...`, `Decor.cpp:2371-2378`). That number,
330, is not arbitrary — it is exactly the frame count of the `Stop` action's own `table_blupi`
record, confirmed below.

## The phase-halving step

Immediately before the table lookup itself, one more transformation is applied to the phase
counter — and it is easy to miss because it looks like an unrelated, self-contained tweak:

*From `Decor.cpp:2387-2392`:*
```cpp
int num6 = scaledPhase;
if (!m_blupiHelico && ((m_blupiSpeedX > 0.1 && m_blupiSpeedX < 0.75) ||
                       (m_blupiSpeedX < -0.1 && m_blupiSpeedX > -0.75)))
{
    num6 /= 2;
}
```

`scaledPhase` (`m_blupiPhase / Config::ScaleDiv(1)`, computed a few lines earlier at
`Decor.cpp:2370`) is halved whenever Blupi is walking *slowly* — a horizontal input speed strictly
between `0.1` and `0.75` in magnitude, outside helicopter mode. This is the mechanism behind a
subtle but real piece of game feel: when the player nudges the joystick only gently, Blupi's walk
cycle visibly plays back at half speed rather than at the same cadence as a full-speed walk, so
the animation's apparent tempo tracks how fast Blupi is actually moving instead of always cycling
at one fixed rate regardless of input magnitude.

## `Tables::table_blupi`: the packed record format, verified

`table_blupi` is declared as a flat, fixed-size array of 2,911 `shortcs` values
(`Tables.hpp:131`), and its header comment describes the layout in general terms: "each animation
block begins with a header record whose first value is the action ID, followed by the icon index
sequence for that action" (`Tables.hpp:120-126`). Reading `BlupiSearchIcon()`'s actual lookup loop
makes the exact record shape precise:

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

Each record is therefore exactly `table_blupi[i] = actionId`, `table_blupi[i+1] = frameCount`,
`table_blupi[i+2] = specialThreshold`, followed by `frameCount` raw icon indices at
`table_blupi[i+3 .. i+3+frameCount-1]` — a fixed 3-value header plus a variable-length payload,
which is exactly why the traversal step is `table_blupi[i+1] + 3` rather than a fixed stride, and
why the whole table has to be walked linearly from the start every single call rather than indexed
directly (there is no side index of action-ID-to-offset anywhere in the codebase; every
`BlupiSearchIcon()` call re-scans from `i = 0`). The array is terminated the moment a record's
`actionId` field is literally `0` — not `-1`, not any other sentinel.

The frame-selection arithmetic is the one place this chapter's task explicitly called for
verification against a plausible-but-unconfirmed description ("phase % frameCount unless a
special-threshold branch applies"), and the real logic is subtly more specific than that
paraphrase: when `specialThreshold` is `0` (no threshold set) *or* the current (possibly-halved)
phase `num6` is still within the threshold, the frame index is the ordinary looping
`num6 % frameCount`. But once `num6` **exceeds** a *non-zero* threshold, the frame index becomes
the threshold value itself, verbatim — not wrapped, not clamped to `frameCount - 1`, just pinned
at `table_blupi[i + 3 + specialThreshold]`. In other words, a threshold does not shorten a loop; it
converts a looping animation into a play-once-then-freeze one, holding on whichever specific frame
the threshold happens to name.

## Reading real records out of the data

Parsing the actual 2,911-entry array (`Tables.cpp:116` onward) by the exact algorithm above turns
up concrete, verifiable examples of every part of this format. The very first record in the table
is `Hide`:

*From `Tables.cpp:118-119`:*
```cpp
35, 9, 0, 276, 277, 278, 279, 280, 281, 282,
283, 284, 1, 330, 0, 0, 0, 0, 0, 0,
```
`actionId = 35` (`BlupiAction::Hide`), `frameCount = 9`, `threshold = 0`, icons `276..284` — a
plain 9-frame loop with no freeze behavior. Immediately following it (the `1` right after `284`)
is `Stop`: `actionId = 1`, `frameCount = 330`, `threshold = 0` — a 330-entry, mostly-zero idle
loop, which is exactly the cycle length Chapter 17 and this chapter's idle-sound discussion above
both reference (`scaledPhase % 330`). Reading further into that record confirms it directly: the
handful of non-zero values scattered through those 330 icon slots are a short blink/fidget
animation, and their positions are exactly the phase offsets `BlupiSearchIcon()` checks to trigger
the blink sound.

![Blupi's Stop idle animation, all 330 frames of table_blupi's largest record laid out as a contact sheet](../images/blupi-action-stop.png)

*Every non-zero frame of the `Stop` record (offset 12 in `table_blupi`), extracted directly from
`blupi.png` by `tools/extract_sprites.py` using the real `Pixmap::GetSrcRectangle` grid algorithm
— see `book/images/MANIFEST.md` for full provenance.*

A cluster of records a little further in supplies a clean, real example of the freeze-frame
behavior in action:

*From `Tables.cpp:154-159`:*
```cpp
// ... end of the Turn (action 3) record ...
3, 6, 0, 1, 1, 2, 2, 3, 3,      // Turn:  6 frames, no threshold, plain loop
4, 3, 0, 17, 18, 19,            // Jump:  3 frames, no threshold, plain loop
5, 5, 4, 169, 26, 170, 170, 27, // Air:   5 frames, threshold = 4
59, 6, 0, 3, 3, 2, 2, 1, 1,     // TurnAir: 6 frames, no threshold
61, 5, 0, 34, 35, 34, 34, 33,   // StopJump: 5 frames, no threshold
62, 2, 0, 35, 34,               // StopJumph: 2 frames, no threshold
6, 3, 2, 33, 34, 35,            // Down: 3 frames, threshold = 2
7, 1, 0, 44,                    // Up: 1 frame (a static pose)
```

`Jump` (`actionId = 4`) is a plain 3-frame loop (`17, 18, 19`) with no threshold — and 3 is exactly
`Config::ScaleTime(3)`, the wind-up duration `BlupiStep()` waits out before switching from
`BlupiAction::Jump` to `BlupiAction::Air` (Chapter 17). `Air` (`actionId = 5`), by contrast, has
`frameCount = 5` and `threshold = 4`: as long as the airborne phase is 4 or under, it loops
normally through `169, 26, 170, 170, 27`; the instant the phase exceeds 4, the lookup freezes on
`table_blupi[i+3+4]`, which is `27` — the last frame of the sequence — and holds there
indefinitely. This is precisely the visual of a falling animation that plays its brief rise/apex
motion once and then simply holds a falling pose for however long Blupi remains airborne, rather
than looping the whole 5-frame cycle while falling. `Down` (`actionId = 6`) shows the same pattern
at a smaller scale: 3 frames, threshold 2, so it plays `33, 34` once and freezes on `35`.

| `Air` (freezes on frame 4) | `Down` (freezes on frame 2) |
|---|---|
| ![BlupiAction::Air animation frames, freezing on the final frame past phase 4](../images/blupi-action-air.png) | ![BlupiAction::Down animation frames, freezing on frame 2 past that phase](../images/blupi-action-down.png) |

*Both extracted by `tools/extract_sprites.py` directly from `table_blupi`'s real offsets (375 and
405 respectively); `book/images/MANIFEST.md` records the freeze-frame behavior for each
independently of this chapter's own reading of `Decor.cpp`, and the two agree.*

Not every record in the table follows the clean, contiguous layout these examples might suggest.
Scanning the full 2,911-entry array programmatically (walking it exactly as `BlupiSearchIcon()`
does, by `frameCount + 3` steps from each record) turns up a run of 43 consecutive `-1` values
between the `Clear3` record (`actionId = 76`) and the `Clear4` record (`actionId = 77`) — reserved,
unused padding space in the data rather than a bug in the walking logic. Because `-1 != 0`, the
traversal loop does not stop there; it simply keeps stepping through the padding (each "record" it
sees there has a bogus `frameCount` of `-1`, advancing the index by only `2` at a time) until it
reaches `77`'s real header. Since no legitimate `BlupiAction` value is ever `-1`, this padding is
silently skipped on every single call without ever matching or corrupting a lookup — a real, minor
data-authoring quirk preserved faithfully from the original C# table rather than cleaned up in the
port, consistent with this codebase's general practice of treating ported data as fixed.

## Choosing the sprite sheet, and mirroring for the left-facing direction

Once `num` (the resolved icon) is known, `BlupiSearchIcon()` still has to decide *which* sprite
sheet it indexes into, and then correct it for Blupi's facing direction:

*From `Decor.cpp:2404-2450`:*
```cpp
if (blupi_action == BlupiAction::Clear1 || blupi_action == BlupiAction::Clear2 ||
    blupi_action == BlupiAction::Clear3 || blupi_action == BlupiAction::Glu ||
    (blupi_action == BlupiAction::Electro && num < 266))
{
    m_blupiChannel = PixmapChannel::Element;
}
else
{
    m_blupiChannel = PixmapChannel::Blupi;
}

Direction num8 = m_blupiDir;
if (m_blupiInvert)  // controls-inverted cheat/hazard also mirrors which side is "left"
{
    if (m_blupiDir == Direction::Right) { num8 = Direction::Left; }
    if (m_blupiDir == Direction::Left)  { num8 = Direction::Right; }
}
if (num8 == Direction::Left && m_blupiChannel == PixmapChannel::Blupi)
{
    if (blupi_action == BlupiAction::StopSuspend)
    {
        if (num == 144) { num = 158; }
        if (num == 143) { num = 145; }
        if (num == 151) { num = 146; }
    }
    if (num >= 0 && num < 335) { num = Tables::table_mirror[num]; }
}
if (num8 == Direction::Left && m_blupiChannel == PixmapChannel::Element && num >= 168 && num <= 171)
{
    num += 4;
}
m_blupiIcon = num;
m_blupiPhase++;
```

Most of Blupi's animation lives in `PixmapChannel::Blupi` (`blupi.png`), but a handful of
special-effect actions — the lightning-clear death, the falling-into-void ascent, the lava death,
the glue-stuck state, and (specifically) the early part of the electrocution animation
(`num < 266`) — are drawn from `PixmapChannel::Element` instead, reusing icons from the same
collectible/effects atlas Chapter 16 discussed for tile rendering rather than from Blupi's own
sprite sheet. Left-facing frames are not stored separately in the atlas at all for the `Blupi`
channel: instead, whichever right-facing icon `num` was just resolved gets remapped through
`Tables::table_mirror`, a 335-entry lookup (`Tables.hpp:144`) that maps each right-facing icon
index to its already-prepared, horizontally-flipped counterpart — with three individually
hardcoded exceptions for the `StopSuspend` (rope-hanging) action, whose left-facing rope-grip
poses apparently could not be produced by a simple mirror of the right-facing art and needed
distinct sprite indices instead. `PixmapChannel::Element`-sourced icons get a much smaller,
narrower correction: only icons `168`–`171` shift by a fixed `+4` when facing left, implying that
specific four-icon block is one of the few `Element`-channel animations that *does* store a
separate left-facing variant contiguously after its right-facing one, rather than relying on
`table_mirror` at all.

The method's final two lines are almost an afterthought after all of the above, but they are the
entire point of the exercise: `m_blupiIcon = num` hands the resolved sprite index to `Build()`
(Chapter 15) for drawing this frame, and `m_blupiPhase++` advances the counter that the *next*
call to `BlupiSearchIcon()` will read — the same counter `BlupiStep()` resets to `0` every time it
assigns a new `m_blupiAction`, which is why switching actions always restarts the animation from
its first frame rather than continuing mid-cycle.

![Blupi's March cycle, the 6-frame walk loop that table_mirror horizontally flips for left-facing movement](../images/blupi-action-march.png)

*`March`'s 6 right-facing frames (`table_blupi` offset 345); left-facing playback reuses the same
frames remapped through `Tables::table_mirror` rather than storing a separate mirrored sequence.
Extracted from `blupi.png` by `tools/extract_sprites.py` — see `book/images/MANIFEST.md`.*

## Illustrating this chapter

`tools/extract_sprites.py` has since produced real, pixel-accurate cropped contact sheets for
every `BlupiAction` into `book/images/` (indexed in `book/images/MANIFEST.md`), and this chapter
now embeds the ones most directly tied to the mechanics it describes: `Stop`'s 330-frame idle
cycle, the `Air`/`Down` freeze-frame pair, and `March`'s 6-frame walk loop. The manifest's own
per-action notes — generated independently from `table_blupi`'s raw offsets rather than from this
chapter's prose — corroborate every frame count and freeze-threshold cited above, including the
padding stretch between the `Clear3` and `Clear4` records. Chapter 31 is the dedicated,
fully-illustrated catalog covering all remaining `BlupiAction` values with the same real
extracted frames.

## See also

- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 16 — The Tile Map](ch16-tile-map.md)
- [Chapter 17 — Blupi: the State Machine](ch17-blupi-state-machine.md)
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 23 — Secret Powers and the Cheat System](ch23-secret-powers-and-cheat-system.md)
- [Chapter 29 — The Sprite Atlas System](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md)
- [Chapter 30 — Tables: Animation and Movement Data](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md)
- [Chapter 31 — The Blupi Animation Catalog](../part05-sprites-rendering-animation/ch31-blupi-animation-catalog.md)
- [Appendix B — Enum Catalog](../appendices/appendix-b-enum-catalog.md)
