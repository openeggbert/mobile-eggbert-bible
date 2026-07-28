# Chapter 13: IGame1 and Dependencies

## Why this interface exists

`IGame1` is a 301-line pure-abstract interface declared in
`include/WindowsPhoneSpeedyBlupi/IGame1.hpp`, implemented by exactly one class, `Game1`. Its file
header states its purpose without ambiguity:

*From `IGame1.hpp:1-8`:*

```cpp
/**
 * @file IGame1.hpp
 * @brief Declares the IGame1 interface that exposes the top-level game object to subsystems.
 *
 * @details IGame1 is the minimal interface that Decor, InputPad, Pixmap, and Sound need to
 * call back into Game1 without creating circular header dependencies. It covers game-loop
 * lifecycle hooks, property accessors, phase/mission control, and drawing helpers.
 */
```

This is a textbook **dependency-inversion** pattern, and reading `Game1.cpp`'s own constructor
confirms exactly why it is needed: `Game1` constructs `Pixmap` and `Sound` by handing them `this`
as their very first constructor argument —

*From `Game1.cpp:105-111`:*

```cpp
    Game1::Game1() : graphics(this),
                     gameData(), startTime(System::TimeSpan(0)),
                     pixmap(std::make_shared<Pixmap>(this, graphics)),
                     sound(std::make_shared<Sound>(this, gameData)),
                     decor(),
                     waitJauge(),
                     inputPad(this, &decor, pixmap.get(), sound.get(), &gameData)
```

— and `InputPad` likewise takes `this` as its first argument. If `Pixmap.hpp`, `Sound.hpp`, and
`InputPad.hpp` each had to `#include "Game1.hpp"` to know the type of that first argument, and
`Game1.hpp` in turn `#include`s `Decor.hpp`, `IPixmap.hpp`, `ISound.hpp`, and `InputPad.hpp` to
declare its own member fields, the header graph would be circular and simply would not compile in
C++'s single-pass, textual-inclusion model. `IGame1` breaks that cycle: `Pixmap`, `Sound`, and
`InputPad` are handed an `IGame1*` (or, in `Decor`'s case, indirectly through the same interface)
instead of a `Game1*`, so their own headers only need to `#include "IGame1.hpp"` — a much smaller,
leaf-level header with no dependency back on any of the concrete subsystem classes.

`Game1.hpp`'s own class documentation confirms the interface's consumers by name:

*From `Game1.hpp` (via `IGame1.hpp:36-46`):*

```cpp
     * The concrete implementation is Game1, which owns:
     * - The graphics device manager (GraphicsDeviceManager).
     * - The Pixmap rendering subsystem.
     * - The Sound audio subsystem.
     * - The Decor gameplay simulation.
     * - The InputPad input handler.
     * - The GameData persistent state.
     *
     * @note The interface exists to allow subsystems to reference Game1 without
     *       creating a circular include dependency. Do not add gameplay logic here.
```

That last line is important, and this chapter treats it as the interface's real design contract:
`IGame1` is a **layering boundary**, not a place to grow new features. Every method on it either
forwards directly to (or is implemented directly by) `Game1`, and the interface adds no behavior of
its own beyond what a pure-virtual class necessarily requires (a protected, non-virtual destructor —
covered below).

## Shape of the interface: five method categories

Reading through `IGame1.hpp` top to bottom, its roughly two dozen pure-virtual methods fall cleanly
into five groups. This is not a group structure imposed by the file's own comments (the file has no
section headers) — it emerges naturally from what each method actually does.

### 1. Ranking/trial-mode queries (public)

*From `IGame1.hpp:52-64`:*

```cpp
    public:
        [[nodiscard]] virtual bool getIsRankingModeProperty() const = 0;

    public:
        [[nodiscard]] virtual bool getIsTrialModeProperty() const = 0;
```

These are the two accessors `Game1` exposes for whether the trial/paywall UI should be visible
(`getIsRankingModeProperty()`) and whether the platform genuinely reports trial/demo mode
(`getIsTrialModeProperty()`). As [Chapter 12](ch12-game1-state-machine.md) notes, `Game1`'s concrete
implementation of `getIsTrialModeProperty()` unconditionally returns `false` in this port — the
original Windows Phone Marketplace license query has no equivalent here — while
`getIsRankingModeProperty()` can still report `true` if the QA-only `simulateTrialMode` cheat flag
has been toggled. `Decor` and `InputPad` consult these through `IGame1` rather than a concrete
`Game1*`, which is exactly why they need the interface at all: both subsystems are constructed with
an `IGame1*` (via `this` passed from `Game1`'s constructor, as shown above) so they can ask "is
ranking mode active?" without owning a full `#include "Game1.hpp"`.

### 2. Framework lifecycle hooks (protected)

*From `IGame1.hpp:66-132`:*

```cpp
    protected:
        virtual void Initialize() = 0;
        virtual void LoadContent() = 0;
        virtual void UnloadContent() = 0;
        virtual void OnDeactivated(System::Object* sender, const System::EventArgs& args) = 0;
        virtual void OnActivated(System::Object* sender, const System::EventArgs& args) = 0;
        virtual void OnExiting(System::Object* sender, const System::EventArgs& args) = 0;
        virtual void Update(Microsoft::Xna::Framework::GameTime& gameTime) = 0;
```

These mirror the XNA/CNA `Game` base-class overrides `Game1` also implements (see
[Chapter 14](ch14-xna-api-via-cna.md)) — `Initialize`, `LoadContent`, `UnloadContent`, the
activation/deactivation/exit event handlers, and `Update`. Declaring them a second time on `IGame1`
looks redundant at first, since `Game1` already overrides the identically-named methods inherited
from `Microsoft::Xna::Framework::Game`. But the redundancy is deliberate: `Game1` publicly inherits
from *both* `Microsoft::Xna::Framework::Game` and `IGame1`
(`class Game1 : public Microsoft::Xna::Framework::Game, public IGame1`, per `Game1.hpp:78`), so a
single set of overrides in `Game1` satisfies both base classes' virtual dispatch tables at once. The
practical effect is that a piece of code holding only an `IGame1*` — not a `Game1*` and not a
`Microsoft::Xna::Framework::Game*` — can still, in principle, drive these lifecycle calls. All of
these are marked `protected` on the interface, meaning `IGame1` itself does not let arbitrary outside
code call them; only a class that is itself part of the same inheritance/friend relationship can. In
practice, since `Decor`/`InputPad`/`Pixmap`/`Sound` hold `IGame1*` purely to call the phase-control
and drawing-helper methods (groups 3–5 below), this group exists mainly to keep `IGame1` a complete,
faithful mirror of everything the framework expects `Game1` to answer for — not because subsystems
routinely call `Update()` on it themselves.

### 3. Phase and mission control (private)

*From `IGame1.hpp:134-169`:*

```cpp
    private:
        virtual void MissionBack() = 0;
        virtual void StartMission(int mission) = 0;
        virtual void ContinueMission() = 0;
        virtual void CheatAction(Def::ButtonGlyph glyph) = 0;
```

These four map directly onto the private `Game1` methods covered in
[Chapter 12](ch12-game1-state-machine.md) — the mission-navigation helpers invoked from within
`Update()`'s button-dispatch logic, and the cheat-code dispatcher. Marked `private` here (an
interesting choice for an *interface* — ordinarily a base class's pure-virtual methods are `public`
or `protected` so a derived override can actually be reached through a base pointer), these exist on
`IGame1` primarily as a documentation and design-contract device: they record, in one place, the
full shape of `Game1`'s internal phase-control surface, even though nothing outside `Game1` itself
is expected to call them through the interface.

### 4. Rendering delegation (protected/private)

*From `IGame1.hpp:170-227`:*

```cpp
    protected:
        virtual void Draw(const Microsoft::Xna::Framework::GameTime& gameTime) = 0;

    private:
        virtual void DrawBackgroundFade() = 0;
        virtual void DrawButtonsBackground() = 0;
        virtual void DrawButtonsText() = 0;
        virtual void DrawButtonGamerText(Def::ButtonGlyph glyph, int gamer) = 0;
        virtual void DrawTextRightButton(Def::ButtonGlyph glyph, int res) = 0;
        virtual void DrawTextRightButton(Def::ButtonGlyph glyph, std::string text) = 0;
        virtual void DrawTextUnderButton(Def::ButtonGlyph glyph, int res) = 0;
        virtual void DrawWaitProgress() = 0;
        virtual void DrawDebug() = 0;
```

This is the largest group, and it mirrors `Game1`'s own private `Draw*` helper methods one for one —
the UI-chrome drawing routines documented in [Chapter 12](ch12-game1-state-machine.md) (background
fades, button backgrounds, button labels, the loading gauge, and a debug overlay). As with group 3,
these are declared `private` on the interface itself; their presence here is again primarily a
completeness/documentation contract rather than a set of methods any external subsystem calls
through an `IGame1*`.

### 5. Public utility and resource accessors

*From `IGame1.hpp:229-299`:*

```cpp
    private:
        virtual void SetGamer(int gamer) = 0;
        virtual void SetPhase(Def::Phase phase) = 0;
        virtual void SetPhase(Def::Phase phase, int mission) = 0;
        virtual void MemorizeGamerProgress() = 0;

    public:
        virtual void ToggleFullScreen() = 0;
        virtual bool IsFullScreen() = 0;
#ifndef LEGACY
        virtual void SetGameSpeed(GameSpeed speed) = 0;
        [[nodiscard]] virtual GameSpeed getGameSpeed() const = 0;
#endif
        virtual Microsoft::Xna::Framework::GraphicsDeviceManager getGraphics() = 0;
        [[nodiscard]] virtual Microsoft::Xna::Framework::Content::ContentManager& getContentProperty() = 0;
        [[nodiscard]] virtual Microsoft::Xna::Framework::Graphics::GraphicsDevice& getGraphicsDeviceProperty() = 0;
```

This final group is the one that actually matters for cross-subsystem calls, because it is
overwhelmingly `public`. `ToggleFullScreen()`/`IsFullScreen()` expose the display-mode toggle;
`SetGameSpeed()`/`getGameSpeed()` (gated behind the same `#ifndef LEGACY` guard seen on `Game1`
itself — see [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md)) expose
the MODERN-only simulation-speed control; and the last three — `getGraphics()`,
`getContentProperty()`, `getGraphicsDeviceProperty()` — are precisely the accessors a rendering
subsystem needs. This is the group that makes the whole interface earn its keep: `Pixmap`'s
constructor, for instance, is handed an `IGame1*` specifically so it can later call
`getGraphicsDeviceProperty()` and `getContentProperty()` to reach the graphics device and content
manager without ever needing to see the full `Game1` type.

## Why `SetPhase`, `MissionBack`, and the `Draw*` helpers are `private` on an interface

At first glance, declaring pure-virtual methods `private` on an abstract interface seems
self-defeating — a `private` virtual method cannot be invoked through a base-class pointer or
reference from outside the class itself (only from within `Game1`'s own member functions, or via a
`friend` declaration, neither of which `IGame1.hpp` uses). Yet groups 3 and 4 above do exactly this.

The most consistent reading, based only on what the header documents and what this book's
methodology allows it to claim, is that `IGame1` is used here less as a live polymorphic dispatch
surface for those specific methods and more as a **complete architectural mirror** of `Game1`'s
method set — a single file that documents the full shape of the top-level game class's interface,
public and private alike, in one place with consistent Doxygen coverage. The genuinely
cross-subsystem-facing methods (group 1's mode queries, group 5's utility/resource accessors) are
correctly `public`; the methods that exist purely as part of `Game1`'s own internal machinery
(phase transitions, drawing helpers) are marked `private` to reflect that no other class is expected
to call them through this interface — they appear on `IGame1` for documentation completeness and
to keep the interface a faithful one-to-one shadow of `Game1`'s actual API surface, not because
`Decor` or `InputPad` are meant to reach through an `IGame1*` and force a phase change directly.
(`Decor` does, in fact, trigger `Play` → `Lost`/`Win`/next-mission transitions — but it does so by
returning a status code from `Decor::IsTerminated()` that `Game1::Update()` reads and acts on itself,
never by calling `SetPhase()` through an `IGame1*` — see [Chapter 12](ch12-game1-state-machine.md).)

## The protected destructor

`IGame1` ends its declaration with a small but meaningful detail immediately after the class opens:

*From `IGame1.hpp:47-51`:*

```cpp
    class IGame1
    {
    protected:
        ~IGame1() = default;

    public:
```

A `protected`, non-virtual, defaulted destructor is a standard C++ idiom for a pure "interface" base
class that is never meant to be deleted polymorphically through a base pointer (`IGame1* p = ...;
delete p;` would be undefined behavior with a non-virtual destructor if `p` actually pointed at a
`Game1`). Making it `protected` prevents exactly that misuse from compiling: only a derived class
(`Game1`) can destroy an `IGame1` through its own destructor chain, and no external code holding a
bare `IGame1*` can call `delete` on it at all. Combined with the fact that every subsystem is handed
a raw, non-owning `IGame1*` (never a `std::unique_ptr<IGame1>` or similar), this confirms the
interface's role is purely referential — `Decor`, `InputPad`, `Pixmap`, and `Sound` borrow a view
into `Game1` for the lifetime of the game session; none of them owns or destroys it.

## `Def::GameSpeed` visibility across the LEGACY boundary

One more small but real structural detail: the `#ifndef LEGACY` guard around `SetGameSpeed()` /
`getGameSpeed()` on `IGame1` exactly matches the equivalent guard on `Game1.hpp` itself (see
[Chapter 12](ch12-game1-state-machine.md)). This means the interface's shape genuinely changes
depending on whether the project is built in LEGACY or MODERN mode (see
[Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md) for what that
compile-time switch controls more broadly) — a LEGACY build's `IGame1` simply does not declare those
two methods at all, and any code that tried to call them through an `IGame1*` in a LEGACY build
would fail to compile, not merely return an inert default. This is consistent with `CLAUDE.md`'s
broader note that `Config.hpp`'s LEGACY/MODERN switch "affects timing, resolution, and feature flags
globally" — here that reach extends even into which methods a core interface declares.

## Who actually consumes `IGame1`

Based on the constructor call sites in `Game1.cpp` and the consumer list in `IGame1.hpp`'s own file
comment, three concrete classes hold an `IGame1*` (or a pointer/reference typed through it) for the
lifetime of the game session:

- **`Pixmap`** — constructed as `std::make_shared<Pixmap>(this, graphics)`; needs `IGame1` to reach
  the content manager and graphics device for asset loading and rendering. See
  [Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md).
- **`Sound`** — constructed as `std::make_shared<Sound>(this, gameData)`; the file header's
  consumer list also includes `Sound` alongside `Pixmap`, `Decor`, and `InputPad`. See
  [Chapter 38](../part06-audio/ch38-sound-isound-architecture.md).
- **`InputPad`** — constructed as `InputPad(this, &decor, pixmap.get(), sound.get(), &gameData)`;
  needs `IGame1` at minimum for phase-aware button layout (different phases show different
  buttons) and the ranking/trial-mode queries. See
  [Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md).
- **`Decor`**, per the same file-header sentence, is also listed as a consumer of `IGame1`, though
  its own construction (`decor.Create(sound.get(), pixmap.get(), &gameData)`, shown in
  [Chapter 12](ch12-game1-state-machine.md)) does not pass an `IGame1*` as a direct argument in the
  excerpt this book has verified; `Decor`'s own use of the interface, if any, is left to
  [Chapter 15](../part04-decor-simulation/ch15-decor-overview.md) to confirm against `Decor.hpp`/
  `Decor.cpp` directly rather than assumed here from `IGame1.hpp`'s comment alone.

## Summary

`IGame1` is not a general-purpose plugin or testing seam in the way an "interface" in a
dependency-injection-heavy codebase often is — its own class comment is explicit that its entire
reason for existing is breaking a header-inclusion cycle between `Game1` and the subsystems it
constructs and hands `this` to. Reading its actual method list confirms that most of the interface
mirrors `Game1`'s private/protected internals faithfully (largely for documentation completeness,
not live polymorphism), while a smaller, genuinely `public` subset — the ranking/trial queries and
the graphics/content accessors — is what `Pixmap`, `Sound`, and `InputPad` actually call in
practice. Understanding this interface is the key to understanding why `mobile-eggbert`'s subsystem
headers can avoid including `Game1.hpp` at all, despite every one of them needing to call back into
it.

## See also

- [Chapter 11 — Program and Entry Point](ch11-program-and-entry-point.md)
- [Chapter 12 — Game1: the State Machine](ch12-game1-state-machine.md)
- [Chapter 14 — The XNA API via CNA](ch14-xna-api-via-cna.md)
- [Chapter 28 — Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)
- [Chapter 38 — Sound/ISound Architecture](../part06-audio/ch38-sound-isound-architecture.md)
- [Chapter 41 — InputPad: Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md)
