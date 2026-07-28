# Chapter 14: The XNA API via CNA

## Scope of this chapter

Every C++ file in `mobile-eggbert` that touches rendering, audio, or input does so by calling into
namespaces named `Microsoft::Xna::Framework::*` — the same namespace tree a 2013 Windows Phone XNA
4.0 developer would have used. Those namespaces are implemented by CNA, the sibling framework
introduced in [Chapter 2](../part01-origins-and-ecosystem/ch02-openeggbert-ecosystem-map.md), but
**this chapter is not about CNA**. It is about the other side of that boundary: which parts of the
XNA-shaped API surface `mobile-eggbert`'s own code actually calls, in what patterns, and why those
particular calls make sense for a 2D tile-based platformer. Readers who want to know how CNA turns
a `SpriteBatch::Draw()` call into pixels on a given backend should consult `cna-bible`; nothing in
this chapter goes there.

## Why the API is XNA-shaped at all

[Chapter 1](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md) traces the four-step
migration this codebase has been through: ILSpy decompilation, XNA 4.0 → MonoGame, C# → C++, and
finally MonoGame → CNA. The last step is the one that matters here. Both MonoGame and CNA share a
design goal — preserve the *exact shape* of Microsoft's original XNA 4.0 API — precisely so that
migrating a game between them requires touching as little application code as possible. The
practical consequence for `mobile-eggbert` is that its own source still reads exactly like an XNA
4.0 game, right down to the namespace names:

*From `Program.cpp:38`:*

```cpp
#include "Microsoft/Xna/Framework/Game.hpp"
```

*From `Game1.hpp:78`:*

```cpp
class Game1 : public Microsoft::Xna::Framework::Game, public IGame1
```

`Game1` inheriting directly from `Microsoft::Xna::Framework::Game` is the single clearest piece of
evidence that this port never abandoned the XNA programming model — it adopted a from-scratch C++
implementation of that model (CNA) rather than inventing a new one.

## `Game`: the base class and its lifecycle methods

`Game1` overrides five methods inherited from `Microsoft::Xna::Framework::Game`:
`Initialize()`, `LoadContent()`, `UnloadContent()`, `Update(GameTime&)`, and
`Draw(const GameTime&)`. This is the canonical XNA game-loop shape, and
[Chapter 12](ch12-game1-state-machine.md) covers what `mobile-eggbert` does inside each override in
full detail; what matters here is simply that the *shape* of the override set — five specific
virtual methods, called by the framework in a specific order every frame — is entirely XNA's own
convention, inherited unchanged. `Game1`'s constructor also touches base-class members directly,
using the same property-style accessor convention XNA is known for:

*From `Game1.cpp:114, 138-142`:*

```cpp
        getWindowProperty().setTitleProperty("Speedy Blupi");
        // ...
        graphics.setIsFullScreenProperty(false);
        string content = "Content";
        Game::getContentProperty().setRootDirectoryProperty(content);
        Game::setTargetElapsedTimeProperty(System::TimeSpan::FromTicks(static_cast<long>(500000L / Config::TIME_SCALE)));
        Game::setInactiveSleepTimeProperty(System::TimeSpan::FromSeconds(1.0));
```

`getXProperty()`/`setXProperty()` pairs like these are C++'s stand-in for C#'s native `get`/`set`
property syntax (`Game.Window.Title = "Speedy Blupi";` in the original C#) — a convention that
recurs on every XNA-shaped type this chapter discusses, and one `mobile-eggbert`'s own `CLAUDE.md`
and `cna`'s `CLAUDE.md` both codify as a project-wide rule for porting C# properties into C++.
`Game::setTargetElapsedTimeProperty(...)` is worth calling out specifically: it ties the game's
frame-pacing directly to `Config::TIME_SCALE`, connecting this XNA-level timing knob to the
LEGACY/MODERN build configuration covered in [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md).

## `GameTime`: the one parameter every frame carries

`GameTime` is the type XNA passes into both `Update()` and `Draw()` every frame, carrying elapsed
and total simulation time. `mobile-eggbert` uses it narrowly but precisely — almost entirely to
drive the artificial loading-screen delay in `Phase::Wait`:

*From `Game1.cpp:219, 261, 280`:*

```cpp
    void Game1::Update(Microsoft::Xna::Framework::GameTime& gameTime)
    ...
            startTime = gameTime.getTotalGameTimeProperty();
    ...
            long num = gameTime.getTotalGameTimeProperty().getTicksProperty() - startTime.getTicksProperty();
```

[Chapter 12](ch12-game1-state-machine.md) covers what this calculation is for (deriving
`waitProgress`, the fraction that drives the loading gauge). The pattern itself —
`gameTime.getTotalGameTimeProperty().getTicksProperty()` returning a `System::TimeSpan` and then a
raw tick count — is exactly the API shape an XNA 4.0 programmer would recognize: `GameTime` never
exposes wall-clock time directly, only `TimeSpan` values, forcing all timing math through the
`sharp-runtime`-supplied `TimeSpan` type (see [Chapter 2](../part01-origins-and-ecosystem/ch02-openeggbert-ecosystem-map.md)
on `sharp-runtime`'s role) rather than a raw `float`/`double` seconds value. `Draw()` receives
`GameTime` too, but `mobile-eggbert`'s own `Draw()` never reads from it directly — it exists purely
because the base-class override signature requires it, and is forwarded unread to `Game::Draw(gameTime)`
at the end of the method.

## `SpriteBatch`: the rendering primitive underneath every drawn sprite

Every visible pixel in `mobile-eggbert` — the tile map, Blupi, UI buttons, text, HUD gauges — is
ultimately drawn through a single `Microsoft::Xna::Framework::Graphics::SpriteBatch`, owned by
`Pixmap` (see [Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md) for
`Pixmap`'s own design). `Pixmap.cpp`'s file header names this directly:

*From `Pixmap.cpp:3-4`:*

```cpp
 *        SpriteBatch draw calls for the Speedy Blupi rendering back-end.
```

The classic XNA `Begin()`/`Draw()`/`End()` triad appears throughout `Pixmap.cpp` exactly as an XNA
4.0 tutorial would present it:

*From `Pixmap.cpp:362, 372`:*

```cpp
        spriteBatch->Begin(Microsoft::Xna::Framework::Graphics::SpriteSortMode::BackToFront,
        // ...
        spriteBatch->End();
```

*From `Pixmap.cpp:400-403`:*

```cpp
        if (!batch_started_) spriteBatch->Begin(Microsoft::Xna::Framework::Graphics::SpriteSortMode::BackToFront,
        // ...
        spriteBatch->Draw(bitmap, destinationRectangle, srcRectangle, Microsoft::Xna::Framework::Color::White);
        if (!batch_started_) spriteBatch->End();
```

Note the `if (!batch_started_)` guards wrapped around several of these `Begin()`/`End()` calls —
this is `Pixmap`'s own bookkeeping for the fact that `Game1::Draw()` opens one long-lived
`BeginBatch()`/`EndBatch()` pair around an entire frame's worth of drawing (see the call sequence in
[Chapter 12](ch12-game1-state-machine.md)'s `Draw()` walkthrough), while some lower-level `Pixmap`
methods can also be called standalone, outside that outer batch, and need to open and close their
own `SpriteBatch::Begin`/`End` pair in that case. `SpriteSortMode::BackToFront` — used consistently
at every call site shown above — is itself a meaningful, specific choice from the enum XNA exposes:
it means the game leans on `SpriteBatch`'s own depth-based sort rather than submitting draws in a
pre-sorted, layer-correct order itself, letting `Pixmap` pass an explicit depth value per sprite and
trust `SpriteBatch` to order them correctly.

`SpriteBatch::Draw()` itself is called with the classic XNA overload shape — a `Texture2D`, a
destination rectangle, a source rectangle, and a tint color:

*From `Pixmap.cpp:402`:*

```cpp
        spriteBatch->Draw(bitmap, destinationRectangle, srcRectangle, Microsoft::Xna::Framework::Color::White);
```

`Microsoft::Xna::Framework::Color::White` here is not "no tint" as a special case — it is the
literal, fully-opaque white tint value that leaves a sprite's own pixel colors unmodified, the same
convention any XNA `SpriteBatch::Draw` call uses to mean "draw the texture as-is." Wherever
`mobile-eggbert` needs actual transparency or tinting (e.g. the translucent panel backgrounds in
`Game1::DrawButtonsBackground()`, covered in [Chapter 12](ch12-game1-state-machine.md)), it
constructs a different `Color` value with an explicit alpha component instead.

## `ContentManager`: loading textures and sounds by name

`Game1` sets the content root directory once, in its constructor (`Game::getContentProperty()
.setRootDirectoryProperty("Content")`, shown above), and every subsequent asset load throughout the
game goes through that same `ContentManager`, reached via `IGame1::getContentProperty()` (see
[Chapter 13](ch13-igame1-and-dependencies.md) for why subsystems reach it through the interface
rather than a concrete `Game1*`). `Pixmap::LoadContent()` is the single largest consumer, loading
every sprite-atlas texture the game owns in one block:

*From `Pixmap.cpp:288-300`:*

```cpp
        bitmapText    = game1->getContentProperty().Load<Texture2D>(iconPrefix + "text");
        bitmapButton  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "button");
        bitmapJauge   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "jauge");
        bitmapBlupi   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "blupi");
        bitmapBlupi1  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "blupi1");
        bitmapObject  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "object-m");
        bitmapElement = game1->getContentProperty().Load<Texture2D>(iconPrefix + "element");
        bitmapExplo   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "explo");
        bitmapPad     = game1->getContentProperty().Load<Texture2D>(iconPrefix + "pad");
        bitmapSpeedyBlupi = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "speedyblupi");
        bitmapBlupiYoupie = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "blupiyoupie");
        bitmapGear        = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "gear");
```

This is XNA's `ContentManager::Load<T>(string assetName)` pattern used exactly as designed: a
generic, type-parameterized load call keyed by a logical asset name (no file extension), resolved
against the content root configured earlier. `Sound.cpp` uses the identical pattern for audio,
substituting the type parameter:

*From `Sound.cpp:160`:*

```cpp
                game1->getContentProperty().Load<SoundEffect>(oss.str())
```

Neither call site needs to know anything about how a given platform actually locates or decodes the
underlying asset file — that resolution logic belongs entirely to CNA's `ContentManager`
implementation, and is out of scope here by design (see [Chapter 45](../part08-data-persistence-content/ch45-content-pipeline.md)
for how `mobile-eggbert`'s own content is organized on disk, which is a `mobile-eggbert`-side
concern, distinct from how `ContentManager::Load` resolves it under the hood).

## `Audio`: `SoundEffect` and `SoundEffectInstance`

Audio playback follows the same two-type XNA pattern any XNA game uses: `SoundEffect` is the loaded,
reusable audio asset (loaded via `ContentManager` as shown above), and `SoundEffectInstance` is a
single playable instance of it, with its own volume, pitch, and pan:

*From `Sound.cpp:90`:*

```cpp
    Sound::Play::Play(Microsoft::Xna::Framework::Audio::SoundEffect& se, SoundChannel channel, double volume, double balance,
```

*From `Sound.cpp:129`:*

```cpp
        Microsoft::Xna::Framework::Audio::SoundEffect::setMasterVolumeProperty(1.0f);
```

`SoundEffect::setMasterVolumeProperty` is a static/class-level property in the original XNA API —
a single global multiplier applied across every playing sound — and `mobile-eggbert` uses it exactly
that way, setting it once during initialization rather than per-sound. The full design of
`mobile-eggbert`'s own `Sound`/`ISound` wrapper around this XNA primitive — including its channel
model and the `tableVolumePitch` mixing table — is the subject of
[Part VI](../part06-audio/ch38-sound-isound-architecture.md); this chapter stops at noting which raw
XNA audio types the game calls.

## `Input`: three device families under one dispatcher

`InputPad` is where `mobile-eggbert` reaches furthest across the XNA input API, because it has to
unify three physically different input devices — touch, mouse, and keyboard — into one internal
button model (`Def::ButtonGlyph`). All three device APIs are queried with the same
static-`GetState()`-then-inspect pattern XNA uses throughout its input namespace:

*From `InputPad.cpp:354`:*

```cpp
            touches = TouchPanel::GetState();
```

*From `InputPad.cpp:378`:*

```cpp
        MouseState mouseState = Mouse::GetState();
```

*From `InputPad.cpp:428, 435`:*

```cpp
        KeyboardState newKeyboardState = Keyboard::GetState();
        // ...
            if (newKeyboardState.IsKeyDown(keys)) touchesOrClicks.push_back(TinyPoint(-1, static_cast<int>(keys)));
```

`TouchPanel::GetState()` returns a `TouchCollection` of active touch points; `Mouse::GetState()`
returns a `MouseState` snapshot; `Keyboard::GetState()` returns a `KeyboardState` snapshot queried
per-key via `IsKeyDown(Keys)`. This is precisely XNA 4.0's input model — immediate-mode polling once
per frame, rather than an event-driven callback API — and `InputPad` builds its own event-like
abstraction (a single pressed `ButtonGlyph` per frame) entirely on top of it. `Game1::Update()`
itself also polls a fourth XNA input family directly, for the hardware Back button:

*From `Game1.cpp:217`:*

```cpp
        if (GamePad::GetState(PlayerIndex::One).getButtonsProperty().getBackProperty() == ButtonState::Pressed)
```

`GamePad::GetState(PlayerIndex::One)` is XNA's controller API, and its presence here is a direct
inheritance from the Windows Phone origin: the hardware Back button on a Windows Phone device is
modeled, in XNA's API, as a gamepad button (`Buttons.Back`) rather than a distinct phone-specific
API. `mobile-eggbert` keeps this exact call shape unchanged, which is why a hardware button that no
longer physically exists on most platforms this game now targets still shows up in the code as a
`GamePad` query — see [Chapter 42](../part07-input/ch42-keypressflags-and-mapping.md) for how that
Back-button concept is remapped on platforms without one. The full unification logic — how touch,
mouse, and keyboard state all collapse into one `ButtonGlyph` per frame — belongs to
[Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md); this chapter's job ends
at identifying which raw XNA input types are queried and how.

## What this survey deliberately leaves out

In keeping with this book's scope, this chapter has not attempted to explain:

- How CNA's `SpriteBatch` actually rasterizes a draw call on any given graphics backend
  (SDL_Renderer, EasyGL, Vulkan, Direct3D, and so on).
- How CNA's `ContentManager` resolves an asset name to a file on disk, or how its content pipeline
  differs from Microsoft's original `.xnb`-based one.
- How CNA's audio mixer schedules `SoundEffectInstance` playback under the hood.
- How CNA's input classes read platform input events and turn them into `TouchCollection`/
  `MouseState`/`KeyboardState` snapshots.

Every one of those questions is legitimate and interesting — and every one of them belongs to
`cna-bible`, which covers CNA's own architecture in the depth this book deliberately does not. What
this chapter has shown instead is the complete, if narrow, list of XNA-shaped surfaces
`mobile-eggbert`'s own code actually depends on: `Game`'s lifecycle methods, `GameTime`,
`SpriteBatch`, `ContentManager`, `SoundEffect`/`SoundEffectInstance`, and the `TouchPanel`/`Mouse`/
`Keyboard`/`GamePad` input quartet. That list is short enough to hold in your head, which is itself
a useful fact about how modest this 2D platformer's platform-facing surface really is — the vast
majority of the game's 31,000-plus lines of C++, as later parts of this book show, is gameplay
logic that never touches any of these APIs directly at all.

## See also

- [Chapter 11 — Program and Entry Point](ch11-program-and-entry-point.md)
- [Chapter 12 — Game1: the State Machine](ch12-game1-state-machine.md)
- [Chapter 13 — IGame1 and Dependencies](ch13-igame1-and-dependencies.md)
- [Chapter 2 — The OpenEggbert Ecosystem Map](../part01-origins-and-ecosystem/ch02-openeggbert-ecosystem-map.md)
- [Chapter 28 — Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)
- [Chapter 38 — Sound/ISound Architecture](../part06-audio/ch38-sound-isound-architecture.md)
- [Chapter 41 — InputPad: Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md)
