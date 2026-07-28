# Chapter 41: InputPad — Touch, Keyboard, and Accelerometer

`InputPad` is the game's single input funnel. Every physical input mechanism the game supports —
finger touch on a phone screen, a mouse click on desktop, a physical keyboard, a virtual
on-screen keyboard the game itself draws, and the accelerometer's tilt sensor — is normalized by
this one class into two things `Decor` consumes: a pair of `-1/0/+1`-ish directional speed values
(`SetSpeedX`/`SetSpeedY`) and a small bitmask of logical buttons (`KeyChange`). At 1,970 lines,
`InputPad.cpp` is the second-largest `.cpp` file in the project after `Decor.cpp` — not because
input is conceptually difficult, but because the file also owns nearly all of the game's
in-development/debug tooling (cheat-code typing, the MODERN-only debug overlay, a full virtual
keyboard implementation, and game-speed hotkeys), all layered on top of the same per-frame
`Update()`/`Draw()` pair. This chapter treats `InputPad.hpp` (497 lines) and `InputPad.cpp` (1,970
lines) as a single unit and reads them in full.

## Where `InputPad` sits

*From `InputPad.hpp:1-22`:*
```cpp
/**
 * @file InputPad.hpp
 * @brief Declaration of the InputPad player-input controller.
 *
 * @details
 * InputPad is the single point of contact between the platform input layer
 * (touch, mouse, keyboard, accelerometer) and the game state machine. It
 * translates raw hardware events into @c ButtonGlyph presses and directional
 * speed values each frame.
 *
 * Build-configuration variants:
 * - **LEGACY** – minimal build without typed-cheat or persistent-cheat
 *   support (no @c typedCheatBuffer, no @c activePersistentCheats).
 * - **MODERN** – full build that adds the debug overlay, virtual on-screen
 *   keyboard, Shift/Tab speed modifiers, and cheat-code cycling.
 * - **INPUT_DISABLED** (defined when @c INPUT_ENABLED is absent in the .cpp)
 *   – stubs out all processing; useful for automated testing.
 */
```

`InputPad` is constructed once by `Game1` with five non-owning pointers — `IGame1*`, `Decor*`,
`IPixmap*`, `ISound*`, `GameData*` — and holds all five for its entire lifetime:

*From `InputPad.hpp:94-102, 316`:*
```cpp
mutable IGame1* game1;
mutable Decor* decor;
mutable IPixmap* pixmap;
mutable ISound* sound;
mutable GameData* gameData;
...
InputPad(IGame1* game1, Decor* decor, IPixmap* pixmap, ISound* sound, GameData* gameData);
```

This is a genuinely central class in the architecture, comparable to `Decor` and `Pixmap` in how
many other subsystems it touches directly: it reads from `GameData` (settings — accelerometer
sensitivity, jump-hand preference, sound-enabled), writes into `Decor` (movement speed and the key
bitmask), draws through `IPixmap` (the touch-pad overlay and every on-screen button), and calls
into `ISound` (a UI click sound). Unlike `Decor`, which owns gameplay simulation state,
`InputPad`'s own state is entirely about *this frame's* input — the class-level Doxygen is explicit
that "Does not own gameplay state. This is input code, not gameplay logic" (`InputPad.hpp:67`).

Three build-configuration macros gate different slices of the class: `LEGACY` removes typed-cheat
and persistent-cheat tracking; `MODERN` (the inverse extreme) adds the debug overlay, virtual
keyboard, and Shift/Tab speed modifiers; and `INPUT_DISABLED` (active whenever the `.cpp`'s local
`INPUT_ENABLED` macro is not separately defined externally — mirroring the `SOUND_ENABLED` /
`SOUND_DISABLED` pattern in `Sound.cpp` described in [Chapter 38](../part06-audio/ch38-sound-isound-architecture.md))
stubs nearly every public method to a safe no-op, for headless/automated-test builds.

## The three raw input sources, and how they become one list of points

`InputPad::Update()` (the ~780-line core method spanning `InputPad.cpp:325-1107`) begins by
collecting *every* input event this frame — touch, mouse, and a subset of keyboard keys — into a
single, uniform `std::vector<TinyPoint> touchesOrClicks`. This is the key architectural move that
lets the rest of the method (hit-testing button rectangles, computing D-pad direction) stay
input-source-agnostic: everything downstream of this collection step treats a keyboard arrow-key
press exactly like a screen tap at a synthetic location.

### Touch and mouse

*From `InputPad.cpp:349-384`:*
```cpp
Microsoft::Xna::Framework::Input::Touch::TouchCollection touches{};
bool touchScreenIsSupported = true;
if (touchScreenIsSupported)
{
    using Microsoft::Xna::Framework::Input::Touch::TouchPanel;
    touches = TouchPanel::GetState();
    touchOrClickCount = touches.getCountProperty();
}

std::vector<TinyPoint> touchesOrClicks;

using Microsoft::Xna::Framework::Input::Touch::TouchLocation;
using Microsoft::Xna::Framework::Input::Touch::TouchLocationState;
if (touchScreenIsSupported)
    for (const TouchLocation& item : touches)
    {
        if (item.getStateProperty() == TouchLocationState::Pressed || item.getStateProperty() ==
            TouchLocationState::Moved)
        {
            TinyPoint touchPress{
                static_cast<int>(item.getPositionProperty().X), static_cast<int>(item.getPositionProperty().Y)
            };
            touchesOrClicks.push_back(touchPress);
        }
    }

using Microsoft::Xna::Framework::Input::MouseState;
using Microsoft::Xna::Framework::Input::Mouse;
using Microsoft::Xna::Framework::Input::ButtonState;
MouseState mouseState = Mouse::GetState();
if (mouseState.getLeftButtonProperty() == ButtonState::Pressed)
{
    touchOrClickCount++;
    TinyPoint mouseClick(mouseState.getXProperty(), mouseState.getYProperty());
    touchesOrClicks.push_back(mouseClick);
}
```

`touchScreenIsSupported` is hardcoded `true` — the variable exists as a single toggle point but is
never conditionally set to `false` anywhere in the file, so touch polling is unconditional on every
platform this game runs on. Any active `Pressed` or `Moved` touch contact contributes one point;
`touchOrClickCount` (exposed publicly via `getTotalTouchOrClickProperty()`) tallies both touch
contacts and a pressed mouse button, and is used elsewhere (per the MODERN debug overlay, later in
this chapter) purely for diagnostic display, not gameplay logic.

### Android wide-screen touch remapping

Because the game's whole coordinate system is a fixed logical `640×480` HUD space (`Def::LXIMAGE`/
`LYIMAGE`, `Def.hpp:147-148` — the same space `ISound` uses for positional audio, per
[Chapter 38](../part06-audio/ch38-sound-isound-architecture.md)), raw touch coordinates on a
physically wider-than-4:3 Android screen need remapping before any hit-test against a button
rectangle makes sense:

*From `InputPad.cpp:391-425`:*
```cpp
if ((CNA::getCurrentPlatform() == CNA::Platform::Android && screenRatio > 1.3333333333333333)
    /*|| Env.IMPL.isKNI()*/)
{
    for (int i = 0; i < touchesOrClicks.size(); i++)
    {
        auto touchOrClick = touchesOrClicks[i];
        if (touchOrClick.X == -1) continue;

        float originalX = touchOrClick.X;
        float originalY = touchOrClick.Y;

        float widthHeightRatio = screenWidth / screenHeight;
        float heightRatio = 480 / screenHeight;
        float widthRatio = 640 / screenWidth;
        ...
        if (screenHeight > 480)
        {
            touchOrClick.X = (int)(originalX * heightRatio);
            touchOrClick.Y = (int)(originalY * heightRatio);
            touchesOrClicks[i] = touchOrClick;
        }
        ...
    }
}
```

Only the height ratio (`480 / screenHeight`) is actually applied to both axes — the separately
computed `widthRatio` is logged for debugging (via the `INPUT_DEBUG` macro, gated by
`Config::INPUT_DETAILED_DEBUGGING_ENABLED`) but never used to transform a coordinate. This means
the remap is uniform-scale (both X and Y scaled by the same height-derived factor), which keeps
touch-point aspect ratio consistent with the vertical logical space rather than independently
squashing X and Y — appropriate given the game's visible play area is itself letterboxed/pillarboxed
to preserve its 4:3-ish aspect on wider screens, a detail belonging to `Pixmap`'s draw-bounds
computation (see [Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)). The
guard `touchOrClick.X == -1; continue;` deliberately skips synthetic keyboard-encoded points
(described next), since those already carry logical HUD-space values, not raw screen pixels.

### Keyboard: encoding special keys as fake touch points at `X == -1`

The cleverest — and, on first read, least obvious — piece of `InputPad`'s unification design is how
a small fixed set of keyboard keys is folded into the same `touchesOrClicks` vector used for touch
and mouse, using a sentinel `X` value to distinguish them:

*From `InputPad.cpp:426-436`:*
```cpp
KeyboardState newKeyboardState = Keyboard::GetState();

Keys keysToBeChecked[] = {
    Keys::LeftControl, Keys::Up, Keys::Right, Keys::Down, Keys::Left, Keys::Space, Keys::Escape,
};
for (Keys keys : keysToBeChecked)
{
    if (newKeyboardState.IsKeyDown(keys)) touchesOrClicks.push_back(TinyPoint(-1, static_cast<int>(keys)));
}
```

Every currently-held key from this fixed list of seven becomes a `TinyPoint(-1, <Keys enum value>)`
appended to the same list that touch/mouse points live in. Downstream code recognizes `X == -1` as
"this is not a real screen coordinate, it's an encoded key" and recovers the actual `Keys` value
from `Y`:

*From `InputPad.cpp:884-895`:*
```cpp
for (TinyPoint touchOrClickItem : touchesOrClicks)
{
    bool keyboardPressed = false;
    if (touchOrClickItem.X == -1)
    {
        keyboardPressed = true;
    }
    Keys keyPressed = keyboardPressed ? (Keys)touchOrClickItem.Y : Keys::None;
    keyPressedUp = keyPressed == Keys::Up ? true : keyPressedUp;
    keyPressedDown = keyPressed == Keys::Down ? true : keyPressedDown;
    keyPressedLeft = keyPressed == Keys::Left ? true : keyPressedLeft;
    keyPressedRight = keyPressed == Keys::Right ? true : keyPressedRight;
```

Two consequences follow directly from this encoding choice. First, when the per-point loop later
calls `ButtonDetect(touchOrClick)` to test which on-screen button glyph a point falls inside
(`InputPad.cpp:909`, discussed below), a keyboard-encoded point is deliberately substituted with
`TinyPoint(1, 1)` rather than its literal `(-1, key)` value:

*From `InputPad.cpp:897-898`:*
```cpp
TinyPoint touchOrClick = keyboardPressed ? TinyPoint(1, 1) : touchOrClickItem;
```

`(1, 1)` sits just inside the top-left corner of HUD space, a location no real button rectangle
ever covers (button rectangles are computed relative to `drawBounds` dimensions and always start
well away from the literal origin) — so a keyboard-encoded point deliberately never accidentally
matches a button glyph through the general rectangle hit-test path. Instead, the four arrow keys
feed the D-pad logic directly (via the `keyPressedUp/Down/Left/Right` booleans above), and three
more keys — `LeftControl`, `Space`, `Escape` — are mapped explicitly to specific `ButtonGlyph`
values right after the generic `ButtonDetect` call, effectively acting as fixed keyboard shortcuts
for the jump, action, and pause buttons regardless of where the pointer/finger otherwise is:

*From `InputPad.cpp:915-929`:*
```cpp
if (keyboardPressed)
{
    switch (keyPressed)
    {
    case Keys::LeftControl: pressedGlyph = Def::ButtonGlyph::PlayJump;
        pressedGlyphs.push_back(pressedGlyph);
        break;
    case Keys::Space: pressedGlyph = Def::ButtonGlyph::PlayAction;
        pressedGlyphs.push_back(pressedGlyph);
        break;
    case Keys::Escape: pressedGlyph = Def::ButtonGlyph::PlayPause;
        pressedGlyphs.push_back(pressedGlyph);
        break;
    }
}
```

This `X == -1` sentinel convention is exactly the same idiom the game uses elsewhere for "this
integer coordinate doubles as an out-of-band flag" — readers familiar with `TinyPoint`/`TinyRect`'s
own non-standard field ordering (covered in [Chapter 47](../part09-support-types/ch47-tinypoint-tinyrect.md))
will recognize the family resemblance: small coordinate types repurposed as compact tagged unions
rather than given a dedicated variant/tagged-enum type, consistent with the codebase's XNA/C#-era
origins where such lightweight struct reuse was idiomatic.

### The virtual on-screen keyboard (MODERN only)

For devices without a physical keyboard, `MODERN` builds add a full on-screen QWERTY keyboard
implementation, entirely local to `InputPad`. It is activated by a hold gesture rather than a
button: holding a touch inside the top-left 20%-wide × 10%-tall region of the screen for a full
second (`Config::CURRENT_FPS` frames) reveals the keyboard:

*From `InputPad.cpp:470-503`:*
```cpp
const int kLargerDim   = std::max(screenWidth, screenHeight);
const int kActivationW = static_cast<int>(kLargerDim * 0.20f);
const int kActivationH = static_cast<int>(kLargerDim * 0.10f);
constexpr int kHoldFrames = 1 * Config::CURRENT_FPS;  // 1 second

bool inActivationArea = false;
for (const TinyPoint& tp : touchesOrClicks)
{
    if (tp.X == -1) continue;  // keyboard event, not a touch
    if (tp.X >= 0 && tp.X <= kActivationW && tp.Y >= 0 && tp.Y <= kActivationH)
    {
        inActivationArea = true;
        break;
    }
}

if (inActivationArea && !virtualKeyboardActivationConsumed)
{
    virtualKeyboardHoldFrames++;
    if (virtualKeyboardHoldFrames >= kHoldFrames)
    {
        virtualKeyboardVisible = true;
        virtualKeyboardActivationConsumed = true;
    }
}
else if (!inActivationArea)
{
    virtualKeyboardHoldFrames = 0;
    virtualKeyboardActivationConsumed = false;
}
```

Once visible, the keyboard's entire geometry — key size, panel bounds, the close button, and a
special one-slot offset for a lone `F12` key positioned to the close button's left — is computed
fresh every frame by `GetVirtualKeyboardLayout()` rather than cached, specifically so the layout
tracks screen-size changes without stale geometry (`InputPad.hpp:211-222` documents this choice
explicitly: "Both `Update()` and `Draw()` must call `GetVirtualKeyboardLayout()` independently...
the struct is not cached as a member to avoid stale data when the screen is resized between
frames"). Five key rows are defined as parallel arrays of `Keys` (for hit-testing) and matching
`const char*` labels (for `Draw()`): an F-row (`F5`-`F8` on the left, `F12` alone on the right,
directly tied to the game-speed and cheat-menu hotkeys covered later in this chapter), then the
three QWERTY letter rows. Tapping a key rectangle appends the corresponding `Keys` value to
`virtualKeysPressedThisFrame`, a vector consumed by a local lambda, `IsKeyDownOrVirtual`, that every
other keyboard-shortcut check in `Update()` calls instead of `newKeyboardState.IsKeyDown` directly:

*From `InputPad.cpp:463-468`:*
```cpp
auto IsKeyDownOrVirtual = [&](Keys key) -> bool
{
    if (newKeyboardState.IsKeyDown(key)) return true;
    return std::find(virtualKeysPressedThisFrame.begin(), virtualKeysPressedThisFrame.end(), key)
           != virtualKeysPressedThisFrame.end();
};
```

This one indirection is what lets every downstream hotkey check (Shift-boost, Tab slow-motion,
F5-F8 game speed, F12 cheat menu, the 26-letter typed-cheat scanner) work identically whether the
key came from a real keyboard or a tap on the drawn virtual one — none of that logic needed to be
duplicated for the touch-only case.

### Cheat-code typing and game-speed hotkeys: in scope here only as input plumbing

`Update()` devotes a substantial middle section (`InputPad.cpp:574-878`) to detecting F5-F8
game-speed hotkeys, a Shift-held speed boost, a Tab slow-motion toggle, an F12 cheat-menu toggle,
and — in non-`LEGACY` builds — scanning every letter key for rising edges to accumulate a 32-character
rolling buffer checked against ~27 known cheat-code names. This machinery is real and substantial
(the cheat-name table alone is `InputPad.cpp:715-745`), but it is *content* — what cheats exist and
what they do belongs to [Chapter 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md).
What is properly an `InputPad` architectural concern, and worth noting here, is the mechanism: the
same `IsKeyDownOrVirtual` unification described above governs it, edge detection uses a
`letterPrev[26]` debounce array (one bool per letter, `InputPad.hpp:156`) so a held key doesn't
retype the same letter every frame, and the whole detector is gated to the `Def::Phase::Play` phase
only (`InputPad.cpp:688`) — typed cheats cannot be entered from a menu screen. One small
correctness detail: when *not* in the Play phase, the debounce state (`letterPrev[]`) is still kept
current in an `else` branch (`InputPad.cpp:864-877`) specifically "so we don't get spurious triggers
on entry" — without that, a letter key already held down when the player enters Play could read as
a fresh press-edge rather than an already-down key.

## Turning the collected points into gameplay values

### Button hit-testing: `ButtonDetect` and reverse-priority iteration

Once a `TinyPoint` (real or keyboard-synthesized) is in hand, `ButtonDetect` decides which
on-screen button, if any, it lands on:

*From `InputPad.cpp:1109-1132`:*
```cpp
Def::ButtonGlyph InputPad::ButtonDetect(TinyPoint touchOrClick)
{
    const auto buttonGlyphs = getButtonGlyphsProperty();
    for (auto i = buttonGlyphs.rbegin(); i != buttonGlyphs.rend(); ++i)
    {
        Def::ButtonGlyph buttonGlyph = *i;
        TinyRect buttonRect = GetButtonRect(buttonGlyph);

        if (buttonGlyph == Def::ButtonGlyph::PlayJump || buttonGlyph == Def::ButtonGlyph::PlayAction || buttonGlyph
            == Def::ButtonGlyph::PlayDown || buttonGlyph == Def::ButtonGlyph::PlayPause)
        {
            buttonRect = Misc::Inflate(buttonRect, 20);
        }

        if (Misc::IsInside(buttonRect, touchOrClick))
        {
            return buttonGlyph;
        }
    }
    return Def::ButtonGlyph::None;
}
```

Two design choices stand out. The glyph list is iterated in **reverse** — the class-level Doxygen
for `getButtonGlyphsProperty()` states the rationale directly: "The order determines hit-test
priority: later entries take precedence (`ButtonDetect` iterates in reverse)" (`InputPad.hpp:278-281`).
Since `getButtonGlyphsProperty()` (below) appends cheat-menu glyphs *after* the phase's normal
glyph set whenever `showCheatMenu` is true, this reverse iteration ensures the cheat overlay's
buttons — drawn on top, visually — also win any overlapping hit-test against whatever is normally
underneath them. Second, the four primary action buttons (`PlayJump`, `PlayAction`, `PlayDown`,
`PlayPause`) get their hit-test rectangle inflated by 20 pixels on every side before testing —
a deliberate touch-accuracy accommodation, larger than their visually-drawn size, for the buttons a
player needs to hit quickly and repeatedly during active play.

### The active button-glyph set per phase

`getButtonGlyphsProperty()` (`InputPad.cpp:135-231`) rebuilds, on every call, the list of glyphs
valid for the current `Def::Phase`. This is not cached between calls within a frame — `Update()`
calls it (via `ButtonDetect`) once per touch/click point, and `Draw()` calls it again independently
to decide what to render, meaning the phase-to-glyph mapping logic runs multiple times per frame by
design rather than being computed once and stored. The switch covers every phase defined in
`Def::Phase` (`Def.hpp:51-66`: `Init`, `Play`, `Pause`, `Resume`, `Lost`/`Win`, `Trial`,
`MainSetup`, `PlaySetup`, `Ranking` — `None`, `First`, and `Wait` have no glyphs and fall through
the switch's default of an empty vector). The `Play` phase entry is the one most readers will
recognize from actually playing the game:

*From `InputPad.cpp:159-173`:*
```cpp
case Def::Phase::Play:
    glyphs.push_back(Def::ButtonGlyph::PlayPause);
    glyphs.push_back(Def::ButtonGlyph::PlayAction);
    glyphs.push_back(Def::ButtonGlyph::PlayJump);
    if (accelStarted)
    {
        glyphs.push_back(Def::ButtonGlyph::PlayDown);
    }
    glyphs.push_back(Def::ButtonGlyph::Cheat11);
    glyphs.push_back(Def::ButtonGlyph::Cheat12);
    glyphs.push_back(Def::ButtonGlyph::Cheat21);
    glyphs.push_back(Def::ButtonGlyph::Cheat22);
    glyphs.push_back(Def::ButtonGlyph::Cheat31);
    glyphs.push_back(Def::ButtonGlyph::Cheat32);
    break;
```

`PlayDown` — the on-screen "duck/go down" button — is only added when `accelStarted` is true. This
is the concrete mechanism behind the header's own note that "When accelerometer mode is active the
directional pad is hidden and touch-pad input is ignored; only the Down and Jump buttons remain
active" (`InputPad.hpp:71-74`): once tilt steering is active there is no on-screen D-pad to provide
a "down" direction, so a dedicated button appears to cover that one input the accelerometer itself
cannot express. The six `Cheat11`/`Cheat12`/`Cheat21`/`Cheat22`/`Cheat31`/`Cheat32` glyphs are
always present during Play regardless of whether the cheat menu is open — these are the small
tap-triggered zones in the top-left corner used to reveal/trigger specific cheats by touch, distinct
from `showCheatMenu`'s separate `Cheat1`-`Cheat9` overlay glyphs appended at the very end of the
method when the cheat menu is explicitly toggled open (`InputPad.cpp:218-229`).

### The directional pad: geometry, then discretized direction

The touch-pad itself is a circular zone `padRadius` (140 HUD-space pixels, `InputPad.hpp:92`)
around a center point that depends on the player's handedness setting:

*From `InputPad.cpp:233-241`:*
```cpp
TinyPoint InputPad::getPadCenterProperty() const
{
    TinyRect drawBounds = pixmap->getDrawBoundsProperty();
    int x = gameData->getJumpRightProperty() ? 100 : drawBounds.getWidthProperty() - 100;
    return {x, drawBounds.getHeightProperty() - 100};
}
```

When `getJumpRightProperty()` is true (the jump/action buttons are on the right), the pad sits on
the left at `x = 100`; otherwise the pad moves to the right side and the action buttons take the
left — a full mirrored layout swap driven by one setting, not two independently-configured
positions. The header notes the pad's hit-test itself is a square bounding box, not a true circle:
"The hit-test uses a square bounding box around the circular pad rather than a true Euclidean
distance test" (`InputPad.hpp:89-91`), confirmed by `GetPadBounds`'s implementation
(`InputPad.cpp:1471-1474`), which simply returns a `TinyRect` of `center ± radius` on each axis.

Once a touch is inside the pad zone (or an arrow key is held — both set `padPressed = true`,
`InputPad.cpp:899-907`), the actual direction is discretized from the touch's offset from pad
center against a fixed 20-pixel deadzone on each axis:

*From `InputPad.cpp:1063-1085`:*
```cpp
double horizontalPosition = padTouchPos.X - getPadCenterProperty().X;
double verticalPosition = padTouchPos.Y - getPadCenterProperty().Y;

if (horizontalPosition > 20.0)
{
    horizontalChange += 1.0;
}
if (horizontalPosition < -20.0)
{
    horizontalChange -= 1.0;
}
if (verticalPosition > 20.0)
{
    verticalChange += 1.0;
}
if (verticalPosition < -20.0)
{
    verticalChange -= 1.0;
}
```

Note this is not proportional/analog control — `horizontalChange`/`verticalChange` only ever end
up as `-1.0`, `0.0`, or `+1.0` regardless of how far past the 20-px deadzone the touch sits (there
is no further scaling by distance from center), so the touch pad is functionally an 8-directional
digital pad rendered as an analog-looking circular thumb. Keyboard arrow-key input reuses this
exact same code path by synthesizing a `padTouchPos` offset by a fixed 30 pixels in the pressed
direction(s) before falling into the same threshold logic (`InputPad.cpp:1033-1062`), which is why
diagonal keyboard movement (e.g. holding both `Up` and `Right`) works identically to a diagonal
touch — both produce a `padTouchPos` displaced on both axes simultaneously.

### Accelerometer override

If the accelerometer is active, its computed value overrides the pad-derived `horizontalChange`
entirely, and `verticalChange` is separately driven by the `Down`/`Jump` key-press flags rather
than by any touch position at all (there is no pad to read a Y-offset from once tilt mode is
active):

*From `InputPad.cpp:1087-1103`:*
```cpp
if (accelStarted)
{
    horizontalChange = accelSpeedX;
    verticalChange = 0.0;
    if (((unsigned int)keyPress & ToRaw(KeyPressFlags::Down)) != 0)
    {
        verticalChange = 1.0;
    }
#ifdef MODERN
    // In ghost mode, the Jump button moves Blupi upward (verticalChange = -1).
    if (decor != nullptr && decor->IsGhost()
        && ((unsigned int)keyPress & ToRaw(KeyPressFlags::Jump)) != 0)
    {
        verticalChange = -1.0;
    }
#endif
}
decor->SetSpeedX(horizontalChange);
decor->SetSpeedY(verticalChange);
decor->KeyChange(keyPress);
```

This is the final step of every `Update()` call: whichever source produced `horizontalChange`/
`verticalChange` (pad, keyboard-as-pad, or accelerometer), the values are handed to `Decor` via
`SetSpeedX`/`SetSpeedY`, and the accumulated `keyPress` bitmask (built up throughout the method
from `PlayJump`/`PlayDown` glyph matches, see [Chapter 42](ch42-keypressflags-and-mapping.md) for
the bitmask itself) is handed to `Decor::KeyChange`. `Decor::SetSpeedX` applies one more
transformation the reader should know about before leaving `InputPad`'s territory — a direction
inversion:

*From `Decor.cpp:1400-1407`:*
```cpp
void Decor::SetSpeedX(double speed)
{
    if (m_blupiInvert)
    {
        speed = 0.0 - speed;
    }
    m_blupiSpeedX = speed;
}
```

`m_blupiInvert` is a `Decor`-side flag (covered in [Chapter 17](../part04-decor-simulation/ch17-blupi-state-machine.md))
independent of `InputPad`'s own `gameData->getJumpRightProperty()` handedness setting — `InputPad`
never needs to know about horizontal-control inversion at all; it always reports the pad/accelerometer's
raw left/right sense, and `Decor` is solely responsible for flipping it when the game logic calls
for it (for example, certain vehicle or level-specific mechanics). `KeyChange` itself is a
one-line setter with no logic of its own:

*From `Decor.cpp:1414-1417`:*
```cpp
void Decor::KeyChange(int keyPress)
{
    m_keyPress = keyPress;
}
```

The mapping from that stored `m_keyPress` bitmask into actual gameplay decisions (jump initiation,
action triggering, and dozens of state-machine branch conditions throughout `Decor::BlupiStep`) is
the subject of [Chapter 42](ch42-keypressflags-and-mapping.md).

## Accelerometer input in detail

`InputPad` owns a `Microsoft::Devices::Sensors::Accelerometer` sensor object directly
(`accelSensor`, `InputPad.hpp:107`) and registers a member-function callback on construction:

*From `InputPad.cpp:252-261`:*
```cpp
accelSensor.CurrentValueChanged +=
    [this](
    System::Object* /*sender*/,
    const Microsoft::Devices::Sensors::SensorReadingEventArgs<AccelerometerReading>&
    sensor_reading_event_args)
    {
        HandleAccelSensorCurrentValueChanged(sensor_reading_event_args);
    };
```

`StartAccel()`/`StopAccel()` wrap `accelSensor.Start()`/`Stop()` in `try`/`catch` blocks that
silently swallow `AccelerometerFailedException` and (`StartAccel` only)
`UnauthorizedAccessException`, so that a device with no accelerometer hardware, or one that denies
sensor permission, simply falls back to `accelStarted == false` and the game continues using the
touch pad — no crash, no error surfaced to the player (`InputPad.cpp:1843-1889`). `Update()`
synchronizes this start/stop state against the player's own setting once per frame
(`InputPad.cpp:331-342`), so toggling the accelerometer setting in the setup screen takes effect
on the very next `Update()` call.

The actual sensor-reading-to-movement conversion happens entirely inside
`HandleAccelSensorCurrentValueChanged`, which runs on a **sensor thread**, not the main game
thread — a fact both the header and implementation flag prominently as the one piece of genuinely
concurrent code in this class:

*From `InputPad.cpp:1932-1957`:*
```cpp
void InputPad::HandleAccelSensorCurrentValueChanged(
    Microsoft::Devices::Sensors::SensorReadingEventArgs<Microsoft::Devices::Sensors::AccelerometerReading> e)
{
    Microsoft::Devices::Sensors::AccelerometerReading sensorReading = e.getSensorReadingProperty();
    float y = ((Microsoft::Devices::Sensors::AccelerometerReading)(sensorReading)).getAccelerationProperty().Y;
    float sensitivityThreshold = (1.0f - (float)gameData->getAccelSensitivityProperty()) * 0.06f + 0.04f;
    float adjustedThreshold = (accelLastState ? (sensitivityThreshold * 0.6f) : sensitivityThreshold);
    if (y > adjustedThreshold)
    {
        accelSpeedX = 0.0 - std::min((double)y * 0.25 / (double)sensitivityThreshold + 0.25, 1.0);
    }
    else if (y < 0.0f - adjustedThreshold)
    {
        accelSpeedX = std::min((double)(0.0f - y) * 0.25 / (double)sensitivityThreshold + 0.25, 1.0);
    }
    else
    {
        accelSpeedX = 0.0;
    }
    accelLastState = accelSpeedX != 0.0;
    if (accelWaitZero)
    {
        if (accelSpeedX == 0.0)
        {
            accelWaitZero = false;
        }
        else
        {
            accelSpeedX = 0.0;
        }
    }
}
```

Only the **Y axis** of the raw acceleration vector is used — device tilt in the other two axes is
ignored entirely. The dead-zone threshold scales with the player's configured sensitivity (a
`Slider`, see below) from about `0.10g` at minimum sensitivity down to `0.04g` at maximum,
`sensitivityThreshold = (1 - accelSensitivity) * 0.06 + 0.04`. Hysteresis matters here: once
movement is already active (`accelLastState == true`), the threshold needed to *stay* active drops
to 60% of the base value, so the character doesn't flicker in and out of motion right at the
boundary of the dead zone. The speed ramp guarantees a minimum non-zero output of `0.25` once past
threshold (rather than starting at an imperceptible near-zero value), scaling up to a max of `1.0`.
`accelWaitZero`, set by `StartMission()` (`InputPad.cpp:267-271`) whenever a new mission begins,
forces `accelSpeedX` to `0.0` until the very first reading lands back inside the dead zone — this
prevents an unwanted lurch at level start if the player is holding the device tilted at the moment
the level loads.

Both the header and implementation are explicit and consistent about the concurrency model here:
`accelSpeedX` and `accelLastState` are the *only* two fields this sensor-thread callback ever
writes, both are `double`/`bool` (naturally aligned on ARM and x86), and the code relies on aligned
scalar reads/writes being atomic at the hardware level rather than using any explicit lock —
`InputPad.hpp:75-79` calls this out directly as a known, deliberate simplification rather than an
oversight: "No explicit mutex is used; safety relies on aligned-double access being atomic on the
target architectures (ARM, x86)."

An accelerometer sensitivity `Slider` (`accelSlider`, constructed at `TinyPoint(320, 400)`, the
`AccelSensitivity` value from `GameData`) is drawn and hit-tested only on the `MainSetup`/`PlaySetup`
screens when the accelerometer setting is enabled (`InputPad.cpp:931-935, 1172-1176`) — `Slider` is
a small standalone UI control covered in its own right in
[Chapter 37](../part05-sprites-rendering-animation/ch37-slider-ui-control.md).

## Drawing the input overlay: the `Pixmap` connection

`InputPad::Draw()` (`InputPad.cpp:1134-1469`) is the visual half of the class, and it is entirely
built on `IPixmap`'s drawing primitives — `pixmap->DrawIcon(...)` for the pad background/thumb and
every debug/overlay background panel, and `pixmap->DrawInputButton(...)` for every actual button
glyph:

*From `InputPad.cpp:1139-1144`:*
```cpp
if (!accelStarted && getPhaseProperty() == Def::Phase::Play)
{
    pixmap->DrawIcon(PixmapChannel::Pad, 0, GetPadBounds(getPadCenterProperty(), padRadius / 2), 1.0, false);
    TinyPoint center = (padPressed ? padTouchPos : getPadCenterProperty());
    pixmap->DrawIcon(PixmapChannel::Pad, 1, GetPadBounds(center, padRadius / 2), 1.0, false);
}
```

Icon `0` from the `Pad` sprite sheet is the static pad background (drawn once, fixed at pad
center), and icon `1` is the movable thumb, redrawn at either the pad's resting center or the
current `padTouchPos` depending on whether the pad is actively pressed — this is the visual
directional-pad "joystick cap that follows your finger" effect players see on screen. Exactly how
`PixmapChannel::Pad`'s sprite sheet is laid out and sliced (grid dimensions, icon indices) is
`Pixmap`'s own concern — `Pixmap.cpp`'s `DrawIcon` switch statement handles `PixmapChannel::Pad`
with a `140×140` grid and no gap between cells — and is covered in full in
[Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md) and
[Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md); this chapter's
concern is only that `InputPad` is the caller driving that sheet for the touch-pad specifically
(icons `0`/`1`) and reuses the same channel's icon `15` as a generic semi-transparent background
panel for every debug/cheat/keyboard overlay drawn later in the method (`InputPad.cpp:1279, 1308,
1366, 1401, 1438`, etc.) — one flat rectangle sprite repurposed as a UI backdrop wherever the
`MODERN` build needs to lay text over a dimmed panel.

Every glyph returned by `getButtonGlyphsProperty()` for the current phase is drawn in one loop with
pressed/selected state derived from this frame's `pressedGlyphs` list and, for a handful of toggle
buttons, directly from `GameData`:

*From `InputPad.cpp:1145-1170`:*
```cpp
for (Def::ButtonGlyph buttonGlyph : getButtonGlyphsProperty())
{
    bool pressed = VECTOR_CONTAINS(pressedGlyphs, buttonGlyph);
    bool selected = false;
    if (buttonGlyph >= Def::ButtonGlyph::InitGamerA && buttonGlyph <= Def::ButtonGlyph::InitGamerC)
    {
        int selectedGamer = (int)(static_cast<intcs>(buttonGlyph) - 1);
        selected = selectedGamer == gameData->getSelectedGamerProperty();
    }
    if (buttonGlyph == Def::ButtonGlyph::SetupSounds)   selected = gameData->getSoundsProperty();
    if (buttonGlyph == Def::ButtonGlyph::SetupJump)     selected = gameData->getJumpRightProperty();
    if (buttonGlyph == Def::ButtonGlyph::SetupZoom)     selected = gameData->getAutoZoomProperty();
    if (buttonGlyph == Def::ButtonGlyph::SetupAccel)    selected = gameData->getAccelActiveProperty();
    pixmap->DrawInputButton(GetButtonRect(buttonGlyph), buttonGlyph, pressed, selected);
}
```

`GetButtonRect(glyph)` (`InputPad.cpp:1476` onward, several hundred lines) computes every button's
screen-space rectangle at draw time from two scale factors derived from the current draw-bounds
height (`buttonSizeFactor1 = drawBoundsHeight / 5.0`, `buttonSizeFactor2 = drawBoundsHeight *
140.0 / 480.0`), plus a separate fixed 80-pixel grid for the `Cheat1`-`Cheat9` overlay buttons and
a `drawBoundsHeight / 3.5`-based grid for the in-game `Cheat11`-`Cheat32` touch zones — the method
is long specifically because every one of roughly 30 `ButtonGlyph` values gets its own
hand-placed `case` computing `Left`/`Right`/`Top`/`Bottom` from these factors, rather than a data
table. This is the geometry `Game1`'s own drawing code queries via the public `GetButtonRect()`
method whenever it needs to position a text label relative to a button (`InputPad.hpp:421-431`).

## The debug overlay, cheat labels, and speed indicator (MODERN)

The remainder of `Draw()` is a series of independent, phase-gated overlays, all `MODERN`-only
except the persistent-cheat name label list (available whenever not `LEGACY`):

- **Persistent-cheat labels** (`InputPad.cpp:1289-1316`): whenever `activePersistentCheats` is
  non-empty during Play, a small top-left panel lists every currently-toggled persistent cheat by
  name — this is genuinely player-facing feedback, not a debug-only feature, since persistent
  cheats (ghost mode, zoom levels, etc.) have no other visible indicator once activated.
- **The debug overlay** (`InputPad.cpp:1206-1287`, gated on `debug_cheat_enabled`): a compact
  block of live `Decor` state — elapsed time, mission/region/lives, Blupi's position and cell
  coordinates, velocity, and a compact string of active mode flags (`air`, `heli`, `skate`, `swim`,
  `ghost`) built by checking several `Decor` accessors in sequence. This is the closest thing the
  game has to an in-game state inspector, and it is entirely optional, off by default, and reached
  only via the typed `debug` cheat code.
- **The full cheats reference overlay** (`InputPad.cpp:1317-1382`, shown for a fixed 5 seconds
  after typing `cheats`): every known cheat name laid out in two centered columns.
- **The game-speed indicator** (`InputPad.cpp:1383-1405`): a small bottom-left label (`"2x"`,
  `"0.5x"`, etc.) shown only when the current `GameSpeed` differs from `Normal`.
- **The virtual keyboard's own drawing** (`InputPad.cpp:1407-1467`): panel background, each key
  rectangle with its centered label, and the close button, all computed from the same
  `GetVirtualKeyboardLayout()` used by `Update()`'s hit-testing, guaranteeing the drawn keys and
  the tappable regions never drift apart.

All of this is `InputPad`-owned UI, drawn every frame `Draw()` runs, entirely independent of
`Decor`'s own HUD elements (health/lives gauges, mission text) — those belong to `Decor`/`Jauge`
and are covered in [Chapter 36](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md).

## `StartMission`: the one lifecycle hook

`InputPad`'s only externally-called lifecycle method besides the constructor and the per-frame
`Update()`/`Draw()` pair is `StartMission(int mission)`:

*From `InputPad.cpp:267-271`:*
```cpp
void InputPad::StartMission(int mission)
{
    this->mission = mission;
    accelWaitZero = true;
}
```

It stores the mission index (used only to decide which pause-menu buttons appear — `mission != 1`
gates the "Back" button, `mission != 1 && mission % 10 != 0` gates "Restart", per
`InputPad.cpp:176-183`, presumably reflecting level-1 and level-boundary special cases in the
mission structure covered in [Chapter 24](../part04-decor-simulation/ch24-missions-and-continuemission.md))
and arms the accelerometer's wait-for-zero guard described above. Both header and implementation
document this as a precondition: `Update()`'s own Doxygen states "`StartMission()` has been called
at least once before the first invocation in the Play phase" (`InputPad.hpp:357-358`).

## See also

- [Chapter 42: KeyPressFlags and Mapping](ch42-keypressflags-and-mapping.md) — the bitmask
  `InputPad` builds and hands to `Decor::KeyChange`, and how `Decor` consumes it.
- [Chapter 17: Blupi — the State Machine](../part04-decor-simulation/ch17-blupi-state-machine.md) —
  where `m_keyPress`, `m_blupiSpeedX`/`Y`, and `m_blupiInvert` actually drive Blupi's behavior.
- [Chapter 23: Secret Powers and the Cheat System](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) —
  full coverage of the cheat codes `InputPad`'s typed-cheat scanner and cheat-menu buttons trigger.
- [Chapter 28: Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md) and
  [Chapter 29: The Sprite Atlas System](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md) —
  the `PixmapChannel::Pad` sprite sheet `InputPad::Draw()` renders from.
- [Chapter 37: Slider — UI Control](../part05-sprites-rendering-animation/ch37-slider-ui-control.md) —
  the accelerometer-sensitivity `Slider` `InputPad` owns and draws on the setup screens.
- [Chapter 38: Sound/ISound Architecture](../part06-audio/ch38-sound-isound-architecture.md) — the
  `ISound::PlayImage` call `InputPad` makes for its own UI click sound.
- [Chapter 47: TinyPoint, TinyRect](../part09-support-types/ch47-tinypoint-tinyrect.md) — the
  coordinate types used throughout this chapter, including the `X == -1` sentinel-encoding idiom.
