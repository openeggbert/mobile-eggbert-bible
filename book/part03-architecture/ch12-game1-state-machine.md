# Chapter 12: Game1 — the State Machine

## Overview

`Game1` is the single most important class for understanding how `mobile-eggbert` fits together as
an application. It is declared across 955 lines in `include/WindowsPhoneSpeedyBlupi/Game1.hpp` and
implemented across 1,113 lines in `src/WindowsPhoneSpeedyBlupi/Game1.cpp`, and it plays two roles
simultaneously:

1. It is the concrete XNA/CNA `Game` subclass — the class whose `Initialize()`, `LoadContent()`,
   `Update()`, and `Draw()` overrides the framework calls every frame (see
   [Chapter 14](ch14-xna-api-via-cna.md) for how that base class fits into the wider XNA-shaped API
   surface `mobile-eggbert` uses).
2. It is the owner of every major subsystem in the game and the sole authority over a top-level
   **phase state machine** (`Def::Phase`) that decides which screen is showing, which subsystems are
   ticking, and how input is interpreted at any given moment.

This chapter documents both roles: what `Game1` owns and constructs, the complete phase transition
graph (verified directly against the code — including one place where it disagrees with the file's
own header comment), and how `Update()` and `Draw()` are structured frame to frame.

## What `Game1` owns

`Game1.hpp`'s own class-level Doxygen comment includes a subsystem-ownership table, and reading the
constructor confirms every entry in it:

*From `Game1.hpp:48-57`:*

```cpp
     * **Subsystem ownership**
     * | Field        | Type                      | Responsibility                                    |
     * |--------------|---------------------------|---------------------------------------------------|
     * | graphics     | GraphicsDeviceManager     | Manages the display device and window.            |
     * | pixmap       | IPixmap (Pixmap)          | Sprite rendering and background caching.          |
     * | sound        | ISound (Sound)            | Audio playback and music.                         |
     * | decor        | Decor                     | Core gameplay simulation (map, entities, physics).|
     * | inputPad     | InputPad                  | Touch / mouse / gamepad input handling.           |
     * | gameData     | GameData                  | Persistent player progress and settings.          |
     * | waitJauge    | Jauge                     | Loading progress bar shown during Wait phase.     |
```

Cross-referencing each of these to where this book covers them in depth:

- `graphics` (`Microsoft::Xna::Framework::GraphicsDeviceManager`) — the display/window manager
  inherited straight from the XNA-shaped API; see [Chapter 14](ch14-xna-api-via-cna.md).
- `pixmap` (`std::shared_ptr<IPixmap>`, concretely a `Pixmap`) — sprite rendering and the
  background-image cache; see [Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)
  and [Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md).
- `sound` (`std::shared_ptr<ISound>`, concretely a `Sound`) — audio playback; see
  [Chapter 38](../part06-audio/ch38-sound-isound-architecture.md).
- `decor` (`Decor`, held by value) — the entire gameplay simulation: tile map, Blupi's state
  machine, physics, AI, doors, missions; this is the subject of the whole of
  [Part IV](../part04-decor-simulation/ch15-decor-overview.md).
- `inputPad` (`InputPad`, held by value) — touch/mouse/keyboard/accelerometer input, translated into
  `Def::ButtonGlyph` presses; see [Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md).
- `gameData` (`GameData`, held by value) — persistent player progress and settings, the save-game
  format; see [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md).
- `waitJauge` (`Jauge`, held by value) — the HUD gauge bar reused here specifically to show loading
  progress; see [Chapter 36](../part05-sprites-rendering-animation/ch36-jauge-hud-gauges.md).

Every one of these except `graphics` is either constructed directly in the constructor's
member-initializer list or wired together explicitly in the constructor body — there is no lazy
subsystem construction anywhere in `Game1`.

## Construction order

The constructor's Doxygen comment lays out ten explicit construction steps, and the implementation
follows them closely:

*From `Game1.hpp:340-356`:*

```cpp
         * @details Construction order:
         * 1. GraphicsDeviceManager is attached to this Game instance.
         * 2. Pixmap and Sound are allocated and given cross-references.
         * 3. Decor is created with pointers to Sound, Pixmap, and GameData.
         * 4. InputPad is created with pointers to Decor, Pixmap, Sound, and GameData.
         * 5. Tables::Init() populates static game data tables.
         * 6. The Exiting event is wired to OnExiting().
         * 7. Touch/mouse cursor visibility is configured based on hardware capabilities.
         * 8. Content root is set to "Content"; target elapsed time is configured from
         *    Config::TIME_SCALE.
         * 9. waitJauge is positioned and hidden until the Wait phase.
         * 10. SetPhase(Phase::First) is called to start the boot sequence.
```

The implementation:

*From `Game1.cpp:105-165`:*

```cpp
    Game1::Game1() : graphics(this),
                     gameData(), startTime(System::TimeSpan(0)),
                     pixmap(std::make_shared<Pixmap>(this, graphics)),
                     sound(std::make_shared<Sound>(this, gameData)),
                     decor(),
                     waitJauge(),
                     inputPad(this, &decor, pixmap.get(), sound.get(), &gameData)
    {
        Tables::Init();
        getWindowProperty().setTitleProperty("Speedy Blupi");

        Exiting += [this](
            System::Object* sender,
            const System::EventArgs& args)
            {
                OnExiting(sender, args);
            };
        // ...
        graphics.setIsFullScreenProperty(false);
        string content = "Content";
        Game::getContentProperty().setRootDirectoryProperty(content);
        Game::setTargetElapsedTimeProperty(System::TimeSpan::FromTicks(static_cast<long>(500000L / Config::TIME_SCALE)));
        Game::setInactiveSleepTimeProperty(System::TimeSpan::FromSeconds(1.0));
        missionToStart1 = -1;
        missionToStart2 = -1;

        decor.Create(sound.get(), pixmap.get(), &gameData);
        TinyPoint pos{ 196, 426 };
        waitJauge.Create(pixmap.get(), sound.get(), pos, JaugeMode::Yellow, false);
        waitJauge.SetHide(false);
        waitJauge.setZoomProperty(2.0);
        phase = Def::Phase::None;
        fadeOutPhase = Def::Phase::None;

        SetPhase(Def::Phase::First);
    }
```

A few details worth calling out:

- `pixmap` and `sound` are constructed as `std::shared_ptr`s and given `this` (the `Game1` itself,
  as an `IGame1*`) in their own constructors — this is exactly the circular-dependency problem that
  [Chapter 13](ch13-igame1-and-dependencies.md) covers: `Pixmap` and `Sound` need to call back into
  `Game1` (for the graphics device, content manager, and phase-aware behavior) without including
  `Game1.hpp` themselves.
- `decor` is default-constructed in the initializer list, then wired up separately via
  `decor.Create(sound.get(), pixmap.get(), &gameData)` in the constructor body — a two-phase
  construction pattern that recurs for `waitJauge` as well (`Jauge::Create(...)`). This mirrors a
  common XNA idiom where a type's default constructor does nothing meaningful and a separate
  `Create`/`Initialize`-style method performs the real setup once dependencies are available.
- `Tables::Init()` populates the static animation/movement data tables used throughout `Decor` and
  `Pixmap` — see [Chapter 30](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md).
- `Game::setTargetElapsedTimeProperty(...)` derives the frame timing directly from
  `Config::TIME_SCALE`, tying `Game1`'s frame pacing to the LEGACY/MODERN configuration switch
  covered in [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md).
- The very last line of substantive work in the constructor is `SetPhase(Def::Phase::First)` —
  meaning the phase state machine's very first transition happens *during construction*, before
  `Program.cpp`'s `game.Run()` call (see [Chapter 11](ch11-program-and-entry-point.md)) is even
  reached.

## The `Def::Phase` enum

The state machine's states are the values of `Def::Phase`, declared in `Def.hpp`:

*From `Def.hpp:51-64`:*

```cpp
        enum class Phase
        {
            None,       ///< @brief No phase active (initial / uninitialised state).
            First,      ///< @brief Very first frame after startup.
            Wait,       ///< @brief Waiting for an asynchronous operation to complete.
            Init,       ///< @brief Main-menu / gamer-select screen.
            Play,       ///< @brief Active gameplay.
            Pause,      ///< @brief Game paused (pause overlay displayed).
            Lost,       ///< @brief Player lost the current level.
            Win,        ///< @brief Player completed the current level.
            Trial,      ///< @brief Trial / demo mode — purchase prompt screen.
            MainSetup,  ///< @brief Settings screen accessed from the main menu.
            PlaySetup,  ///< @brief Settings screen accessed during gameplay.
            Resume,     ///< @brief Resume-from-checkpoint confirmation screen.
            Ranking     ///< @brief High-score / ranking screen.
        };
```

Thirteen values, one of which (`None`) is a sentinel that is never a "real" active phase after
construction — `Game1::Game1()` sets `phase = Def::Phase::None;` only as a transient value
immediately before calling `SetPhase(Def::Phase::First)`, and `fadeOutPhase` uses `Def::Phase::None`
as its own "no pending transition" sentinel throughout `Update()` and `SetPhase()`.

## The state diagram

`Game1.cpp` itself opens with an unusually thorough file-level comment documenting the entire phase
transition graph — a rare case in this codebase of the implementation file containing better
architecture documentation than the header. The diagram below is redrawn as a Mermaid state diagram,
**verified transition-by-transition against `Game1::Update()` and `Game1::SetPhase()`** rather than
transcribed from the comment alone (see the note after the diagram about one place where the two
disagree):

```mermaid
stateDiagram-v2
    [*] --> First : Game1() constructor
    First --> Wait : Update() — LoadContent, gameData.Read()
    Wait --> Resume : app reactivated + Decor::CurrentRead() succeeds
    Wait --> Init : waitProgress > 1.0 (loading complete)

    Init --> Play : InitPlay button (mission = 1)
    Init --> MainSetup : InitSetup button
    Init --> Ranking : InitRanking button
    Init --> [*] : Back (hardware) → Exit()

    Play --> Pause : PlayPause button / Back (hardware)
    Play --> Lost : Decor::IsTerminated() == -1
    Play --> Win : Decor::IsTerminated() == -2
    Play --> Play : Decor::IsTerminated() >= 1 (StartMission next level)
    Play --> Trial : next-mission redirect (trial guard: mission > 20 && sub-level > 1)

    Pause --> Init : PauseMenu button / Back (hardware)
    Pause --> Play : PauseContinue button (same level, mission = -1)
    Pause --> Play : PauseRestart button (reload current mission)
    Pause --> Play : PauseBack → MissionBack() (mission != 1)
    Pause --> Init : PauseBack → MissionBack() (mission == 1)
    Pause --> PlaySetup : PauseSetup button

    Resume --> Play : ResumeContinue button → ContinueMission()
    Resume --> Init : ResumeMenu button / Back (hardware)

    MainSetup --> Init : SetupReturn button / Back (hardware)
    PlaySetup --> Play : SetupReturn button (mission = -1)
    PlaySetup --> Play : Back (hardware) — same as SetupReturn

    Lost --> Init : WinLostReturn button
    Win --> Init : WinLostReturn button
    Trial --> Init : TrialBuy button (via Guide::ShowMarketplace) / TrialCancel button
    Ranking --> Init : RankingContinue button
```

**A correction to the file's own header comment.** `Game1.cpp`'s introductory comment states, under
"[Settings]":

*From `Game1.cpp:51`:*

```cpp
 * MainSetup / PlaySetup ──Back hardware──>      Init
```

Reading the actual hardware-Back handling in `Update()` shows this is only half true:

*From `Game1.cpp:217-236`:*

```cpp
        if (GamePad::GetState(PlayerIndex::One).getButtonsProperty().getBackProperty() == ButtonState::Pressed)
        {
            if (phase == Def::Phase::Play)
            {
                SetPhase(Def::Phase::Pause);
            }
            else if (phase == Def::Phase::PlaySetup)
            {
                SetPhase(Def::Phase::Play, -1);
            }
            else if (phase != Def::Phase::Init)
            {
                SetPhase(Def::Phase::Init);
            }
            else
            {
                Exit();
            }
            return;
        }
```

`MainSetup` does fall into the generic `else if (phase != Def::Phase::Init) SetPhase(Def::Phase::Init);`
branch, so the comment is correct for `MainSetup`. But `PlaySetup` is checked *earlier*, in its own
dedicated `else if`, and hardware Back from `PlaySetup` goes to **`Play(-1)`** — resuming gameplay,
exactly like pressing the in-game `SetupReturn` button while `playSetup` is true — not to `Init`.
This makes sense from a UX standpoint (`PlaySetup` is reached *from* gameplay, via `PauseSetup`, so
"Back" returning to gameplay rather than jumping past `Pause` all the way to the main menu is the
more sensible behavior) but it does mean the source file's own prose comment is measurably wrong on
this one point. The diagram above reflects the verified code path (`PlaySetup --> Play`), not the
comment. This kind of small drift between a hand-written architecture comment and the code it
describes is exactly the sort of thing this book's methodology — reading the actual source rather
than trusting documentation — exists to catch.

## `Update()`: structure and priority order

`Game1::Update()` is a single function of roughly 230 lines, but it is not a flat dispatch table —
it has a clear priority order, checked in sequence, with early `return`s at every stage. Reading top
to bottom:

**1. Hardware Back button** (highest priority; handled and returned from before anything else runs)
— the block quoted above.

**2. Deferred fade-out transition.** If a fade-out is pending (`fadeOutPhase != Def::Phase::None`),
`Update()` just increments the phase timer and, once `Config::ScaleTime(20)` frames have elapsed,
commits the real transition:

*From `Game1.cpp:237-245`:*

```cpp
        phaseTime++;
        if (fadeOutPhase != Def::Phase::None)
        {
            if (phaseTime >= Config::ScaleTime(20))
            {
                SetPhase(fadeOutPhase);
            }
            return;
        }
```

This is the mechanism behind every "animated" transition in the diagram above (`Init`, `MainSetup`,
`PlaySetup`, `Pause`, and `Resume` are the five phases from which `SetPhase()` defers a transition
this way — see the `SetPhase()` section below). While a fade-out is in progress, **no other Update
logic runs at all** — no input polling, no gameplay simulation — for roughly 20 scaled frames.

**3. The two-stage mission-loading pipeline's second stage.** If `missionToStart2` has been set
(by `Draw()`, as covered below), `Update()` immediately promotes it into a real `SetPhase(Play,
missionToStart2)` call and returns:

*From `Game1.cpp:246-250`:*

```cpp
        if (missionToStart2 != -1)
        {
            SetPhase(Def::Phase::Play, missionToStart2);
            return;
        }
```

**4. `Phase::First` — the one-time boot step.** On the very first real `Update()` call, this block
loads content, reads the save data, and immediately transitions to `Phase::Wait`:

*From `Game1.cpp:251-260`:*

```cpp
        if (phase == Def::Phase::First)
        {
            startTime = gameTime.getTotalGameTimeProperty();
            pixmap->LoadContent();
            sound->LoadContent();
            gameData.Read();
            inputPad.setPixmapOriginProperty(pixmap->getOriginProperty());
            SetPhase(Def::Phase::Wait);
            return;
        }
```

Note that the heavy asset loading (`pixmap->LoadContent()`, `sound->LoadContent()`) happens *here*,
in `Update()`, not in `Game1::LoadContent()` (the XNA-framework-called override, which only
pre-loads the "wait" background — see below). `gameData.Read()` is also performed here, meaning
persistent save data is not available until the game's very first logical `Update()` tick.

**5. `Phase::Wait` — the artificial loading screen.** This phase exists to show the loading gauge
for a fixed, elapsed-time-based duration rather than tying the loading screen's length to how long
`LoadContent()` genuinely took (which, on modern hardware, would likely be near-instant):

*From `Game1.cpp:261-279`:*

```cpp
        if (phase == Def::Phase::Wait)
        {
            if (continueMission == ContinueMissionType::Active)
            {
                continueMission = ContinueMissionType::None;
                if (decor.CurrentRead())
                {
                    SetPhase(Def::Phase::Resume);
                    return;
                }
            }
            long num = gameTime.getTotalGameTimeProperty().getTicksProperty() - startTime.getTicksProperty();
            waitProgress = (double)num / 50000000.0;
            if (waitProgress > 1.0)
            {
                SetPhase(Def::Phase::Init);
            }
            return;
        }
```

The `50000000.0` divisor converts elapsed ticks into a roughly fixed-duration progress fraction —
`waitProgress` climbs from 0 to just over 1.0 over a period independent of frame rate, driving the
loading gauge covered later in `DrawWaitProgress()`. The `continueMission == Active` check here is
the point where a genuine "continue a suspended game" request (queued by `OnActivated()` when the
app regains focus) is actually attempted, via `Decor::CurrentRead()` — if it succeeds, the game skips
the main menu entirely and goes straight to `Phase::Resume`.

**6. Everything else — input polling and phase-specific dispatch.** For every phase not already
handled above, `Update()` polls `InputPad` for a pressed button glyph and dispatches on it through
two `switch` statements in sequence (the first for phase-navigation buttons that always `return`
immediately, the second for gameplay/settings/cheat buttons), followed by cheat-code detection and,
if `phase == Def::Phase::Play`, the gameplay simulation step itself:

*From `Game1.cpp:394-417`:*

```cpp
        if (phase == Def::Phase::Play)
        {
            decor.setButtonPressedProperty(buttonPressed);
#ifndef LEGACY
            if (gameSpeed == GameSpeed::Slow)
            {
                static bool slow_frame = false;
                slow_frame = !slow_frame;
                if (slow_frame)
                {
                    decor.MoveStep();
                }
            }
            else
            {
                for (int speedStep = 0; speedStep < ToRaw(gameSpeed); speedStep++)
                {
                    decor.MoveStep();
                }
            }
#else
            decor.MoveStep();
#endif
            int num2 = decor.IsTerminated();
```

This is the game's actual simulation tick: `Decor::MoveStep()` is called once per frame in `LEGACY`
builds, or between 0 and 8 times per frame in `MODERN` builds depending on the `gameSpeed` field
(`Slow` runs a step every other frame via the `slow_frame` toggle; `Normal`/`Fast`/`Faster`/`Fastest`
run 1/2/4/8 steps respectively, via `ToRaw(gameSpeed)` — see
[Chapter 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md) for the full `GameSpeed` enum
and [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md) for the LEGACY/MODERN
compile-time switch that gates this feature entirely). `Decor::IsTerminated()`'s return value then
drives three of the diagram's `Play` outgoing edges directly: `-1` → `Lost`, `-2` → `Win`, `>= 1` →
the next mission (via `StartMission`, with `MemorizeGamerProgress()` called first in every case to
persist lives and door state before leaving `Play`).

Finally, `Update()` ends by calling the base class's own `Game::Update(gameTime)` — the point at
which CNA's own `Game` machinery (component updates, the audio `FrameworkDispatcher`, etc.) gets to
run.

## `Draw()`: structure

`Game1::Draw()` is much shorter and is organized around a single dispatch on `phase`:

*From `Game1.cpp:525-566`:*

```cpp
    void Game1::Draw(const Microsoft::Xna::Framework::GameTime& gameTime)
    {
        if (continueMission == ContinueMissionType::Pending)
        {
            continueMission = ContinueMissionType::Active;
        }
        pixmap->BeginBatch();
        if (phase == Def::Phase::Wait || phase == Def::Phase::Init || phase == Def::Phase::Pause || phase ==
            Def::Phase::Resume || phase == Def::Phase::Lost || phase == Def::Phase::Win || phase ==
            Def::Phase::MainSetup || phase == Def::Phase::PlaySetup || phase == Def::Phase::Trial || phase ==
            Def::Phase::Ranking)
        {
            pixmap->DrawBackground();
            if (fadeOutPhase == Def::Phase::None && missionToStart1 != -1)
            {
                missionToStart2 = missionToStart1;
                missionToStart1 = -1;
            }
            else
            {
                DrawBackgroundFade();
                if (fadeOutPhase == Def::Phase::None)
                {
                    DrawButtonsBackground();
                    inputPad.Draw();
                    DrawButtonsText();
                }
            }
        }
        else if (phase == Def::Phase::Play)
        {
            decor.Build();
            inputPad.Draw();
        }
        if (phase == Def::Phase::Wait)
        {
            DrawWaitProgress();
        }
        pixmap->EndBatch();
        Game::Draw(gameTime);
    }
```

Three things worth drawing attention to:

1. **The `continueMission` state machine's second step lives in `Draw()`, not `Update()`.**
   `OnActivated()` sets it to `Pending`; the very next `Draw()` call promotes it to `Active`; only
   then does `Update()` (specifically the `Phase::Wait` block above) attempt the actual
   `Decor::CurrentRead()`. This three-state dance (`None` → `Pending` → `Active` → `None`) exists so
   that the restore attempt always happens on a frame boundary after at least one render has
   completed, rather than synchronously inside the platform's activation callback.
2. **The `missionToStart1` → `missionToStart2` promotion also lives in `Draw()`.** This is the
   other half of the two-stage mission-loading pipeline introduced in the `SetPhase()` discussion
   below: `Draw()` only promotes `missionToStart1` once the *new* background texture has actually
   been drawn (via `pixmap->DrawBackground()` just above), guaranteeing the background for the
   destination phase is resident before gameplay is allowed to start.
3. **Ten of the thirteen phases share one drawing path** (background + fade animation + buttons +
   text); only `Play` has a fundamentally different draw path (`decor.Build()`, delegating entirely
   to the gameplay simulation's own rendering — see
   [Chapter 15](../part04-decor-simulation/ch15-decor-overview.md)), and `Wait` layers the loading
   gauge on top of the shared path. `Phase::First` and `Phase::None` are not drawn at all — by the
   time the very first `Draw()` call happens, `Update()` has already advanced past `First` into
   `Wait` (`Update()` always runs before `Draw()` in a given frame in the XNA/CNA game loop; see
   [Chapter 14](ch14-xna-api-via-cna.md)).

`DrawBackgroundFade()` itself is where all the phase-specific entrance/exit animation logic lives —
`Decor.hpp`'s Doxygen comment on the method (quoted in `Game1.hpp:604-631`) catalogs seven distinct
animation styles keyed on the current phase and whether a `fadeOutPhase` is active (BlupiYoupie
scale-and-spin for `Init`, sliding `SpeedyBlupi` art, counter-rotating gear overlays for the setup
screens, a six-rotation spin for `Lost`, a sine-wave pulsate for `Win`, and so on). These are
purely cosmetic transition effects layered on top of the phase graph, not additional states in their
own right — the diagram above deliberately does not attempt to enumerate every animation curve, only
the actual state transitions.

## `SetPhase()`: the single legal transition mechanism

Both header and implementation are emphatic that `phase` must never be assigned directly — every
transition goes through one of the two `SetPhase()` overloads:

*From `Game1.hpp:836-838`:*

```cpp
         * @note Calling this method with the same phase that is already active resets
         *       the phase timer and reloads background assets.
         * @warning Never assign to the @c phase member directly; always use this method.
```

`SetPhase(Def::Phase phase)` is a trivial one-line forward to `SetPhase(phase, 0)`. The two-argument
overload is where all the real logic lives, and it has three distinct concerns bundled together:

**1. Fade-out deferral.** If the *current* phase supports an exit animation (`Init`, `MainSetup`,
`PlaySetup`, `Pause`, or `Resume`) and no fade is already in progress, the requested transition is
not applied immediately — it is parked in `fadeOutPhase`/`fadeOutMission`, the phase timer is reset
to 0, and the function returns without touching `this->phase` at all:

*From `Game1.cpp:984-999`:*

```cpp
    void Game1::SetPhase(Def::Phase phase, int mission)
    {
        if (mission != -2)
        {
            if (missionToStart2 == -1)
            {
                if ((this->phase == Def::Phase::Init || this->phase == Def::Phase::MainSetup || this->phase ==
                        Def::Phase::PlaySetup || this->phase == Def::Phase::Pause || this->phase == Def::Phase::Resume)
                    &&
                    fadeOutPhase == Def::Phase::None)
                {
                    fadeOutPhase = phase;
                    fadeOutMission = mission;
                    phaseTime = 0;
                    return;
                }
```

The `Update()` fade-out block quoted earlier is what eventually commits this deferred transition,
roughly `Config::ScaleTime(20)` frames later, by calling `SetPhase(fadeOutPhase)` again — this time
with `mission = 0` (the single-argument overload's default), which is why the special-case handling
of `fadeOutMission` inside `SetPhase` (next point) matters.

**2. Two-stage mission loading, when the target is `Play`.** If the deferred call above eventually
re-enters `SetPhase` with `phase == Def::Phase::Play`, and a real mission number had been stashed in
`fadeOutMission`, the mission is staged into `missionToStart1` for `Draw()` to promote, rather than
being started immediately:

*From `Game1.cpp:1000-1010`:*

```cpp
                if (phase == Def::Phase::Play)
                {
                    fadeOutPhase = Def::Phase::None;
                    if (fadeOutMission != -1)
                    {
                        missionToStart1 = fadeOutMission;
                        return;
                    }
                    mission = fadeOutMission;
                    decor.LoadImages();
                }
```

**3. Immediate commit**, for every case that isn't deferred by the two rules above: `this->phase` is
finally assigned, `phaseTime` and `missionToStart2` reset, `InputPad`'s own phase property updated,
`isTrialMode` re-queried from the platform, any currently-playing sound stopped
(`decor.StopSound()`), and — via a `switch` on the new phase — the matching background image
pre-loaded through `pixmap->BackgroundCache(...)`:

*From `Game1.cpp:1025-1053`:*

```cpp
        switch (this->phase)
        {
        case Def::Phase::Init:
            pixmap->BackgroundCache("init");
            break;
        case Def::Phase::Pause:
        case Def::Phase::Resume:
            pixmap->BackgroundCache("pause");
            break;
        case Def::Phase::Lost:
            pixmap->BackgroundCache("lost");
            break;
        case Def::Phase::Win:
            pixmap->BackgroundCache("win");
            break;
        case Def::Phase::MainSetup:
        case Def::Phase::PlaySetup:
            pixmap->BackgroundCache("setup");
            break;
        case Def::Phase::Trial:
            pixmap->BackgroundCache("trial");
            break;
        case Def::Phase::Ranking:
            pixmap->BackgroundCache("pause");
            break;
        case Def::Phase::Play:
            decor.setDrawBoundsProperty(pixmap->getDrawBoundsProperty());
            break;
        }
        if (this->phase == Def::Phase::Play && mission > 0)
        {
            StartMission(mission);
        }
    }
```

Note that `Ranking` reuses the `"pause"` background asset rather than having a dedicated one of its
own — a small but real economy in the game's asset set.

## `StartMission()`, `ContinueMission()`, and `MissionBack()`

Three private helpers, all invoked only from within the phase machine, round out mission-level
transitions:

- **`StartMission(int mission)`** is where the trial-mode redirect actually happens — it is the
  concrete implementation behind the `Play --> Trial` edge in the diagram:

  *From `Game1.cpp:454-476`:*

  ```cpp
  void Game1::StartMission(int mission)
  {
      if (mission > 20 && mission % 10 > 1 && getIsTrialModeProperty())
      {
          SetPhase(Def::Phase::Trial);
          return;
      }
      this->mission = mission;
      if (this->mission != 1)
      {
          gameData.setLastWorldProperty(this->mission / 10);
      }
      decor.Read(0, this->mission, false);
      decor.LoadImages();
      decor.SetMission(this->mission);
      decor.SetNbVies(gameData.getNbViesProperty());
      decor.InitializeDoors(gameData);
      decor.AdaptDoors(false);
      decor.MainSwitchInitialize(gameData.getLastWorldProperty());
      decor.PlayPrepare(false);
      decor.StartSound();
      inputPad.StartMission(this->mission);
  }
  ```

  Mission numbers encode world and sub-level positionally (tens digit = world, units digit =
  sub-level; mission 1 is the tutorial, a special case exempt from the "last world" bookkeeping).
  The trial guard blocks any mission beyond world 2 whose sub-level is not the first
  (`mission % 10 > 1`) — i.e., trial players can preview the *first* level of worlds beyond the
  second, but not go further, without `getIsTrialModeProperty()` being true. In this port,
  `getIsTrialModeProperty()` always returns `false` (see [Chapter 13](ch13-igame1-and-dependencies.md)),
  so this guard is effectively dead code in the current build — a fossil of the original Windows
  Phone Marketplace trial/paywall system.

- **`ContinueMission()`** is the counterpart used specifically after a successful
  `Decor::CurrentRead()` restore (`Phase::Resume` → `Play`): it calls `SetPhase(Play, -2)` — the one
  mission value that bypasses both the fade-deferral and two-stage staging logic entirely — then
  recovers the mission number from the already-restored `Decor` state via `decor.GetMission()`
  rather than loading anything fresh.

- **`MissionBack()`** implements the `Pause → Play` / `Pause → Init` fork on the diagram: mission 1
  (the tutorial) has nowhere "back" to go, so it returns to `Init`; any other mission rounds down to
  the first sub-level of its own world (mission 23 → 20; mission 20, already a round multiple, → 1).

## Cheat gesture and `CheatAction`

A ten-tap sequence over six dedicated grid buttons (`Cheat11`/`Cheat12`/`Cheat21`/`Cheat22`/`Cheat31`/
`Cheat32`) unlocks a separate cheat menu, tracked by `cheatGesteIndex` against the constant sequence
`cheatGeste`:

*From `Game1.hpp:123-135`:*

```cpp
        static constexpr Def::ButtonGlyph cheatGeste[cheatGesteLength] =
        {
            Def::ButtonGlyph::Cheat12, Def::ButtonGlyph::Cheat22, Def::ButtonGlyph::Cheat32,
            Def::ButtonGlyph::Cheat12, Def::ButtonGlyph::Cheat11, Def::ButtonGlyph::Cheat21,
            Def::ButtonGlyph::Cheat22, Def::ButtonGlyph::Cheat21, Def::ButtonGlyph::Cheat31,
            Def::ButtonGlyph::Cheat32
        };
```

Once matched in full, `inputPad.setShowCheatMenuProperty(true)` reveals nine numbered cheat buttons
(`Cheat1`–`Cheat9`), each mapped by `CheatAction()` to a specific effect — mostly delegating to
`Decor::CheatAction(Tables::CheatCodes::...)` (`OpenDoors`, `SuperBlupi`, `ShowSecret`, `LayEgg`,
`CleanAll`, `AllTreasure`, `EndGoal`), with two exceptions handled locally in `Game1` itself:
`Cheat5` calls `gameData.Reset()` directly, and `Cheat6` toggles `simulateTrialMode` — a
QA-only flag that forces `getIsRankingModeProperty()` to report trial/ranking mode active even in a
full build, letting a developer test the trial paywall screens without a real trial license. The
full cheat system, including how the gesture buttons are laid out on screen and the meaning of each
numbered cheat, is covered in depth in [Chapter 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md).

## `GameSpeed` and the MODERN-only speed control

Guarded entirely behind `#ifndef LEGACY`, `Game1` exposes a `gameSpeed` field
(`GameSpeed::Normal` by default) with public `SetGameSpeed()`/`getGameSpeed()` accessors. As shown in
the `Update()` walkthrough above, this field directly controls how many `Decor::MoveStep()` calls
happen per rendered frame — from a `Slow` mode that steps only every other frame up to `Fastest`,
which runs eight simulation steps per frame. This is a MODERN-mode-only feature layered on top of
the original game's fixed-speed simulation; see [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md)
for the LEGACY/MODERN split itself and [Chapter 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md)
for `GameSpeed`'s full definition and its interaction with `Decor`'s own timing.

## `OnDeactivated` / `OnActivated` / `OnExiting`: the save-on-suspend contract

Three lifecycle overrides tie the phase machine to persistence, all delegated to by
`IGame1`/`Microsoft::Xna::Framework::Game`'s own event hooks:

*From `Game1.cpp:186-209`:*

```cpp
    void Game1::OnDeactivated(System::Object* sender, const System::EventArgs& args)
    {
        if (phase == Def::Phase::Play)
        {
            decor.CurrentWrite();
        }
        else
        {
            decor.CurrentDelete();
        }
        Game::OnDeactivated(sender, args);
    }

    void Game1::OnActivated(System::Object* sender, const System::EventArgs& args)
    {
        continueMission = ContinueMissionType::Pending;
        Game::OnActivated(sender, args);
    }

    void Game1::OnExiting(System::Object* sender, const System::EventArgs& args)
    {
        decor.CurrentDelete();
    }
```

The rule is simple and conservative: a live gameplay session (`phase == Play`) is serialized to a
"current game" save slot the instant the app loses focus, via `Decor::CurrentWrite()`; any other
phase deletes that same slot, so that reactivating from a menu screen never accidentally offers to
"resume" a stale, half-finished level. `OnActivated()` doesn't attempt the restore itself — it only
*flags* the intent (`Pending`), leaving the actual `Decor::CurrentRead()` call to the `Draw()` →
`Update()` two-step described earlier. `OnExiting()`, wired up via the `Exiting +=` lambda in the
constructor, unconditionally deletes the current-game save on a clean exit, guaranteeing the next
launch always starts from `Phase::First` → `Wait` → `Init` rather than silently offering to resume.

## Summary

`Game1` is best understood as two tightly coupled halves: a conventional XNA `Game` shell
(`Initialize`/`LoadContent`/`Update`/`Draw`, discussed further in
[Chapter 14](ch14-xna-api-via-cna.md)) wrapped around a thirteen-state phase machine whose sole
mutator is `SetPhase()`. Every rule this chapter has documented — the fade-out deferral, the
two-stage mission-loading pipeline, the `continueMission` three-state dance, the trial-mode guard —
exists to solve one of two problems: making phase transitions feel animated rather than abrupt, or
making sure gameplay progress and save state survive being interrupted at an arbitrary moment. None
of that logic touches actual gameplay simulation directly; `Game1`'s job ends at calling
`decor.MoveStep()` once per (scaled) frame and `decor.Build()` once per drawn frame. What happens
inside those two calls is the subject of [Part IV](../part04-decor-simulation/ch15-decor-overview.md).

## See also

- [Chapter 11 — Program and Entry Point](ch11-program-and-entry-point.md)
- [Chapter 13 — IGame1 and Dependencies](ch13-igame1-and-dependencies.md)
- [Chapter 14 — The XNA API via CNA](ch14-xna-api-via-cna.md)
- [Chapter 10 — Config: LEGACY vs MODERN](../part02-building-and-running/ch10-config-legacy-vs-modern.md)
- [Chapter 15 — Decor: Overview](../part04-decor-simulation/ch15-decor-overview.md)
- [Chapter 23 — Secret Powers and the Cheat System](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md)
- [Chapter 25 — Game Speed and Zoom](../part04-decor-simulation/ch25-game-speed-and-zoom.md)
- [Chapter 43 — GameData: Save Format](../part08-data-persistence-content/ch43-gamedata-save-format.md)
