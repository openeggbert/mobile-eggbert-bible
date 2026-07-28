# Chapter 42: KeyPressFlags and Mapping

[Chapter 41](ch41-inputpad-touch-keyboard-accelerometer.md) covered how `InputPad` unifies touch,
keyboard, and accelerometer input into two things `Decor` consumes each frame: a pair of
directional speed values, and a small bitmask handed to `Decor::KeyChange()`. This short chapter
is entirely about that bitmask — the `KeyPressFlags` enum that defines it, how `InputPad` builds
it, and how `Decor`'s gameplay state machine reads it back out.

## The enum itself: three flags, not one per glyph

`KeyPressFlags.hpp` is a small, single-purpose file — 64 lines including its Doxygen — declaring a
three-value bitmask enum:

*From `KeyPressFlags.hpp:1-36`:*
```cpp
/**
 * @file KeyPressFlags.hpp
 * @brief Defines the KeyPressFlags bitmask enumeration representing active virtual game buttons.
 *
 * @details Values are powers of two and can be combined with bitwise OR. Produced by
 * InputPad from touch/keyboard/accelerometer input and consumed by the gameplay logic
 * in Decor to drive Blupi's state machine.
 */

#pragma once
#include "SharpRuntime/SharpRuntimeHelper.hpp"

namespace WindowsPhoneSpeedyBlupi
{
    using KeyPressFlagsUnderlying = SharpRuntime::ubytecs;

    enum class KeyPressFlags : SharpRuntime::ushortcs
    {
        None  = 0,      ///< @brief No buttons pressed.
        Jump  = 1,      ///< @brief Jump button active (KEY_JUMP).
        Fire  = 2,      ///< @brief Fire/action button active (KEY_FIRE).
        Down  = 4       ///< @brief Down button active (KEY_DOWN).
    };
```

Three flags — `Jump`, `Fire`, `Down` — cover the entire logical button vocabulary gameplay code
needs to read per frame. Notice this is a smaller set than `Def::ButtonGlyph` (covered in
[Chapter 41](ch41-inputpad-touch-keyboard-accelerometer.md)), which has roughly 30 values spanning
every menu, setup, pause, and cheat button in the game. `ButtonGlyph` identifies *which on-screen
control was touched*, a UI-layer concept `InputPad` alone needs to resolve hit-testing and drawing;
`KeyPressFlags` identifies *which gameplay action is currently requested*, and only three of the
roughly thirty possible `ButtonGlyph` values (`PlayJump`, `PlayAction`, `PlayDown`) ever get
translated into one. Every other glyph — menu buttons, pause buttons, cheat buttons — is consumed
entirely within `InputPad`/`Game1`'s own phase-transition logic and never reaches `Decor` as a
`KeyPressFlags` bit at all. This is a deliberate narrowing at the `InputPad`/`Decor` boundary: the
gameplay simulation only ever needs to know about the three inputs that affect Blupi's physical
state, not the whole menu-navigation surface.

One small inconsistency worth noting for a reader auditing the type declarations closely: the file
declares a type alias `KeyPressFlagsUnderlying = SharpRuntime::ubytecs` (an unsigned byte) at
`KeyPressFlags.hpp:15`, but the enum itself is declared with underlying type
`SharpRuntime::ushortcs` (an unsigned short) at `KeyPressFlags.hpp:30`, not
`KeyPressFlagsUnderlying`. The alias is defined but never actually used as the enum's storage
type — a mismatch that is harmless in practice (an unsigned short comfortably holds the same
values an unsigned byte would, and no field anywhere is declared with the unused
`KeyPressFlagsUnderlying` alias either), but is nonetheless a real, checkable discrepancy between
the file's own declared intent and its declared type. Compare this to `SoundChannel.hpp`
([Chapter 39](../part06-audio/ch39-soundchannel-and-mixing.md)), where the equivalent alias
(`SoundChannelUnderlying`) *is* consistently used as the enum's actual underlying type — the same
naming convention is applied correctly there.

### `ToRaw` / `ToKeyPressFlags`: the same conversion idiom as `SoundChannel`

`KeyPressFlags.hpp` closes with the same small pair of `constexpr` conversion helpers used by
every scoped enum in this codebase:

*From `KeyPressFlags.hpp:38-63`:*
```cpp
static constexpr auto ToRaw(KeyPressFlags flags) -> KeyPressFlagsUnderlying
{
    return static_cast<KeyPressFlagsUnderlying>(flags);
}

static constexpr auto ToKeyPressFlags(const int value) -> KeyPressFlags
{
    return static_cast<KeyPressFlags>(
        static_cast<KeyPressFlagsUnderlying>(value)
    );
}
```

`ToRaw`'s return type is declared as `KeyPressFlagsUnderlying` (the unused byte alias from above),
which means this function's declared return type does not even match the enum's own actual
underlying type (`ushortcs`) — again harmless in every call site actually present in the codebase
(every use immediately widens the result into a plain `int` or `unsigned int` for bitwise
operations, so no truncation is observable), but worth flagging as the same small documentation/
declaration drift noted above, now visible in the conversion function's signature as well as the
enum declaration itself. `ToKeyPressFlags` is declared but, unlike `ToSoundChannel`'s use in level
data deserialization, this book's search of the codebase found no call site anywhere in
`Decor.cpp` or `InputPad.cpp` that actually calls it — `Decor::KeyChange` takes a plain `int`
parameter (see below) and stores it directly, never converting it back into a `KeyPressFlags`
value; only `ToRaw` sees real use, always in the `InputPad → Decor` direction.

## Building the bitmask: `InputPad`'s per-frame `keyPress` accumulator

`InputPad::Update()` declares a plain local `int keyPress = 0` at the very top of the method
(`InputPad.cpp:345`) and only ever sets bits into it — it is never read back within `Update()`
itself for any decision, purely accumulated and handed off at the end. Two `switch` arms, both
inside the per-touch/click loop, are the only two places a bit is ever set:

*From `InputPad.cpp:936-946`:*
```cpp
switch (pressedGlyph)
{
case Def::ButtonGlyph::PlayJump:
    accelWaitZero = false;
    keyPress |= ToRaw(KeyPressFlags::Jump);
    break;
case Def::ButtonGlyph::PlayDown:
    accelWaitZero = false;
    keyPress |= ToRaw(KeyPressFlags::Down);
    break;
...
```

Both branches also clear `accelWaitZero` — pressing either button implies the player has picked
up meaningful control, so the "wait for the accelerometer to return to neutral before applying
tilt" guard from [Chapter 41](ch41-inputpad-touch-keyboard-accelerometer.md) is no longer needed
once an explicit button (jump or down) has been pressed. Notably, `KeyPressFlags::Fire` is never
set by this switch at all — searching the whole of `InputPad.cpp` for `ToRaw(KeyPressFlags::Fire)`
finds no match. `PlayAction`, the glyph that would seem the natural candidate to map to `Fire`, is
handled by an entirely separate mechanism: it is not one of the `keyPress`-affecting `case` labels
in this switch, and looking at the larger `switch (pressedGlyph)` block that spans
`InputPad.cpp:936-992`, `PlayAction` instead falls into the generic "any menu/action button was
pressed" group that only sets the shared `buttonGlyph` variable (used for the press-release edge
detection covered below and the UI click sound) — it never contributes a `KeyPressFlags` bit. This
means `KeyPressFlags::Fire` is a **declared but currently unset flag** from `InputPad`'s side: the
enum value exists, `Decor.cpp` reads it in several places (below), but nothing in the current
`InputPad.cpp` ever sets that bit in the value passed to `KeyChange`. Whatever originally drove
`Fire` — a distinct action button, in the original Windows Phone control scheme, separate from what
is now `PlayAction` — either does not correspond 1:1 to any current `ButtonGlyph`, or the mapping
was lost somewhere in the port. This is a concrete, source-grounded finding rather than
speculation: it follows directly from the absence of `ToRaw(KeyPressFlags::Fire)` (or any bitwise
`|= 2`) anywhere in `InputPad.cpp`.

Two other keyboard shortcuts *do* map directly into `ButtonGlyph::PlayJump` before reaching this
switch — `Keys::LeftControl` (`InputPad.cpp:919`) — so pressing the physical Control key still sets
`KeyPressFlags::Jump` via the same code path, just entering it one step earlier (as a glyph
substitution rather than a raw key check). `Keys::Space` maps to `ButtonGlyph::PlayAction`
(`InputPad.cpp:922`), which — per the finding above — still does not translate into `Fire`.

After the per-point loop finishes, the accumulated `keyPress` may be further overwritten by the
accelerometer-active branch (covered in [Chapter 41](ch41-inputpad-touch-keyboard-accelerometer.md)),
which reads `keyPress`'s `Down`/`Jump` bits to decide `verticalChange` but does not modify
`keyPress` itself — the value handed to `KeyChange` is exactly what the per-point loop built,
regardless of accelerometer state:

*From `InputPad.cpp:1104-1106`:*
```cpp
decor->SetSpeedX(horizontalChange);
decor->SetSpeedY(verticalChange);
decor->KeyChange(keyPress);
```

## `Decor::KeyChange`: a one-line store, and `m_lastKeyPress`'s apparent dead state

`Decor::KeyChange(int keyPress)` is, as noted in [Chapter 41](ch41-inputpad-touch-keyboard-accelerometer.md),
a trivial setter:

*From `Decor.cpp:1414-1417`:*
```cpp
void Decor::KeyChange(int keyPress)
{
    m_keyPress = keyPress;
}
```

`Decor.hpp`'s own Doxygen for this method describes a two-field edge-detection scheme: "Called by
InputPad each frame with the current bitfield of active KeyPressFlags... The gameplay state
machine in MoveStep() reads m_keyPress and m_lastKeyPress to detect new presses vs. held buttons"
(`Decor.hpp:810-819`). Reading `Decor.cpp` end-to-end to verify this claim turns up a discrepancy
worth flagging in the same spirit as [Chapter 38](../part06-audio/ch38-sound-isound-architecture.md)'s
review of `Sound.hpp`'s documentation: `m_lastKeyPress` is indeed a real field, initialized
alongside `m_keyPress` in `Decor`'s constructor and reset method (`Decor.cpp:124-125, 228-229`),
and it is written every single frame at the very end of `MoveStep()`'s per-frame update chain:

*From `Decor.cpp:6530-6536`:*
```cpp
VoyageStep();
m_blupiLastSpeedX = m_blupiSpeedX;
m_blupiLastSpeedY = m_blupiSpeedY;
m_lastKeyPress = m_keyPress;
```

But searching every read site of `m_lastKeyPress` across `Decor.cpp` turns up none — it is written,
never read, anywhere in the current codebase. Every actual gameplay branch that checks button
state reads `m_keyPress` alone (dozens of sites, several shown below), directly against
`KeyPressFlags` bits, with no comparison against the previous frame's value anywhere. The
"new-press vs. held-button" edge detection the header describes is not implemented via
`m_lastKeyPress` in `Decor` — if any such distinction exists in practice, it comes from state
flags gameplay code sets and clears itself (for example, `m_blupiAir`/`m_blupiAction` transitions
guard several of the `Jump` checks below so a held jump key doesn't perpetually retrigger a jump
once airborne), not from comparing two raw bitmasks. `m_lastKeyPress` is maintained faithfully every
frame but is, as far as this book's reading of the source can establish, currently dead state in
`Decor` — a `m_blupiLastSpeedX`/`m_blupiLastSpeedY`-style bookkeeping pattern (both of *those*
siblings are likewise updated on the same line) that was seemingly intended for the same
"compare this frame against last frame" purpose but, for `m_lastKeyPress` specifically, has no
consumer left in the code.

## Reading `m_keyPress` back: how the flags reach gameplay decisions

Every consumption of `m_keyPress` in `Decor.cpp` follows the same idiom — a bitwise AND against
`ToRaw(KeyPressFlags::Jump)` (value `1`) — cast through `(unsigned int)` for the comparison, since
`m_keyPress` is a plain `int` and the enum's raw value needs matching signedness for a clean
bitwise test:

*From `Decor.cpp:2900`:*
```cpp
if (((unsigned int)m_keyPress & ToRaw(KeyPressFlags::Jump)) != 0 && m_blupiFocus)
{
    m_blupiVitesseY = (m_blupiPower ? (-25) : (-19));
}
```

This single line — inside `BlupiStep()`'s jump-handling logic — is representative of the whole
pattern used throughout the file: a held `Jump` bit combined with `m_blupiFocus` (Blupi must be
the player's currently-controlled/focused character — relevant in multi-Blupi missions, covered in
[Chapter 17](../part04-decor-simulation/ch17-blupi-state-machine.md)) sets an initial upward
velocity, with the magnitude depending on whether the SecretPower boost (`m_blupiPower`) is
active. `KeyPressFlags::Jump` is checked at well over a dozen distinct points across `Decor.cpp`,
governing not just jump initiation but also whether Blupi is *allowed* to enter or must exit
various states — for example, guarding against popping over a crate while the jump button is
being held (`Decor.cpp:3291`: `(m_keyPress & ToRaw(KeyPressFlags::Jump)) == 0`, i.e. this
particular crate-interaction branch only applies when jump is *not* pressed), and gating vehicle
takeoff, helicopter ascent, and swimming-to-air transitions in several vehicle/mode-specific
branches (e.g. `Decor.cpp:3726, 3946, 4041, 4546, 4660, 4769, 6915`), each following the identical
`((unsigned int)m_keyPress & ToRaw(KeyPressFlags::Jump)) != 0` test.

`KeyPressFlags::Down` and `KeyPressFlags::Fire` are each checked at a small number of additional
sites — `Down` primarily inside `InputPad.cpp` itself (the accelerometer branch that maps a held
Down press to `verticalChange = 1.0`, described in
[Chapter 41](ch41-inputpad-touch-keyboard-accelerometer.md)) rather than deep inside `Decor.cpp`'s
state machine; `Fire`'s few read sites in `Decor.cpp` (`Decor.cpp:3696, 4316`, both gating an
action/throw-style state transition guarded also by `m_blupiTimeFire == 0`, a cooldown timer) exist
and are real, live gameplay logic — they are simply never reachable in the current build, since
(per the finding above) nothing in `InputPad.cpp` ever sets that bit. This is the practical
consequence, in one sentence, of the `Fire`-flag gap identified earlier: two genuine gameplay
branches in `Decor.cpp` that check `KeyPressFlags::Fire` are currently unreachable dead code from
`InputPad`'s input path, though they would presumably fire correctly if a future change wired a
`ButtonGlyph` (or a keyboard key) through to set that bit.

## The complete flow, end to end

Putting [Chapter 41](ch41-inputpad-touch-keyboard-accelerometer.md) and this chapter's findings
together, the full path from a physical action to a gameplay effect is:

1. A player touches the screen inside the `PlayJump` button's (inflated) hit-test rectangle, or
   presses `LeftControl` on a keyboard, or the virtual keyboard's key-tap logic recognizes an
   equivalent input.
2. `InputPad::ButtonDetect()` (for touch/mouse) or the `Keys::LeftControl` special case
   (`InputPad.cpp:919`) resolves this to `Def::ButtonGlyph::PlayJump`.
3. The `switch (pressedGlyph)` block in `InputPad::Update()` sets `keyPress |=
   ToRaw(KeyPressFlags::Jump)` in the frame-local accumulator.
4. At the end of `Update()`, `decor->KeyChange(keyPress)` stores the whole bitmask into
   `Decor::m_keyPress` unconditionally, overwriting whatever value was stored the previous frame.
5. Somewhere later in the same game-logic tick, `Decor::MoveStep()` calls `BlupiStep()`, which
   reads `m_keyPress` directly against `ToRaw(KeyPressFlags::Jump)` at each of its many
   jump-related branch points, and reacts — setting a vertical velocity, transitioning
   `m_blupiAction`, or gating a crate/vehicle/swim state change — depending on which other state
   flags (`m_blupiFocus`, `m_blupiHelico`, `m_blupiPower`, and so on) are also true at that moment.
6. At the very end of `MoveStep()`, `m_lastKeyPress = m_keyPress` runs — bookkeeping that, per the
   finding above, nothing currently reads back.

No step in this chain performs edge detection (new-press-this-frame vs. held-since-last-frame) at
the `KeyPressFlags` level; every "don't retrigger every frame" guard in `Decor.cpp` is implemented
via a state flag or timer specific to the action in question (`m_blupiAir`, `m_blupiTimeFire`, a
specific `BlupiAction` value already being active), not via comparing `m_keyPress` against
`m_lastKeyPress`.

## See also

- [Chapter 41: InputPad — Touch, Keyboard, and Accelerometer](ch41-inputpad-touch-keyboard-accelerometer.md) —
  the full input-collection pipeline that produces the `keyPress` bitmask this chapter starts from.
- [Chapter 17: Blupi — the State Machine](../part04-decor-simulation/ch17-blupi-state-machine.md) —
  the `BlupiStep()` state machine that reads `m_keyPress` at the many jump/action branch points
  cited above.
- [Chapter 39: SoundChannel and Mixing](../part06-audio/ch39-soundchannel-and-mixing.md) — the
  sibling small bitmask/index enum on the audio side, using the identical `ToRaw`/`To*` conversion
  idiom described here.
- [Chapter 23: Secret Powers and the Cheat System](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) —
  `m_blupiPower`, referenced above as a modifier on jump velocity magnitude.
