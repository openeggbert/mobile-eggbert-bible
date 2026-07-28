# Chapter 24: Missions and `ContinueMission`

## Overview

"Mission" in `mobile-eggbert` is the umbrella term for what a player probably thinks of as a
"level": one self-contained `worlds/*.txt` map, loaded by index, played from a fixed start
position to a win or loss outcome. `Decor` itself knows almost nothing about *how* missions are
sequenced — it stores a single integer, `m_mission`, and lets `Game1` decide what to load next.
The actual mission-numbering scheme, the "lives" counter, and the low-level win/loss signal
(`m_term`, read via `IsTerminated()`) are all real `Decor` state, but the higher-level orchestration
— starting a mission, deciding whether "continue" means "resume this exact frame" or "reload from
the last checkpoint" — lives one layer up, in `Game1`, via the small `ContinueMissionType` enum.
This chapter covers both halves: `Decor`'s mission/lives bookkeeping, and the `Game1`-level
"continue" state machine that drives it.

## `Decor`'s mission state: `GetMission`/`SetMission`

`m_mission` is a single `intcs` field, documented plainly:

*From `Decor.hpp:494-495`:*

```cpp
/** Index of the current mission/level being played. */
intcs m_mission;
```

Its accessors are the simplest kind of getter/setter pair — no validation, no side effects:

*From `Decor.cpp:1681-1689`:*

```cpp
int Decor::GetMission()
{
    return m_mission;
}

void Decor::SetMission(int mission)
{
    m_mission = mission;
}
```

All of the *meaning* behind a mission number is imposed by callers, not by `Decor` itself. Reading
`Game1::StartMission` shows the real numbering convention in use:

*From `Game1.cpp:462-484`:*

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

Two things worth pulling out of this:

1. **The numbering scheme is `world * 10 + level`.** `mission / 10` is treated as the world index
   (used both for `gameData.setLastWorldProperty()` and, as seen in
   [Chapter 22](ch22-doors-keys-doorkeyflags.md), for `OpenDoorsWin()`'s `m_doors[mission + 1]` /
   `OpenGoldsWin()`'s `m_doors[180 + mission / 10]` bookkeeping). Mission `1` is a special case —
   the world-select hub level — and is explicitly excluded from the `setLastWorldProperty` call, so
   returning to the hub never overwrites the player's actual progress marker.
2. **Trial-mode gating happens before any of `Decor`'s mission machinery runs at all.** If
   `mission > 20` (i.e., world 3 or later) and `mission % 10 > 1` (i.e., not the world's first
   level) and the build is running in trial/demo mode, `StartMission` redirects straight to
   `Def::Phase::Trial` and returns — `decor.Read()`/`SetMission()` are never called. This is a
   `Game1`-level content-gating decision; `Decor` has no concept of "trial mode" of its own (its
   only related state, the `TrialMode` toggle behind `Cheat6`/`simulateTrialMode`, lives in
   `Game1` too — see [Chapter 23](ch23-secret-powers-and-cheat-system.md)).

`Decor::GetMission()`'s only other notable caller is `Game1::ContinueMission()`, which reads back
whatever mission `Decor` currently has loaded rather than tracking its own copy:

*From `Game1.cpp:486-491`:*

```cpp
void Game1::ContinueMission()
{
    SetPhase(Def::Phase::Play, -2);
    mission = decor.GetMission();
    if (mission != 1)
    {
```

## The mission numbering scheme, confirmed further: `MissionBack` and the pause menu

Two more `Game1` call sites make the `world * 10 + level` numbering scheme from the previous
section even more concrete, and are worth reading because they show `mission % 10 == 0` is itself a
meaningful value — "the world's own hub-return landing spot" — not just an implementation detail of
how `m_term` gets computed.

`MissionBack()` — invoked when the player presses the pause menu's "Back" button — decides where to
return to using exactly this test:

*From `Game1.cpp:450-460`:*

```cpp
void Game1::MissionBack()
{
    int num = mission;
    if (num == 1)
    {
        SetPhase(Def::Phase::Init);
        return;
    }
    num = ((num % 10 == 0) ? 1 : (num / 10 * 10));
    SetPhase(Def::Phase::Play, num);
}
```

Mission `1` (the world-select hub) backs out to the main menu (`Def::Phase::Init`) entirely.
Anything else backs out to either mission `1` (if the current mission is itself already a
`% 10 == 0` "world landing spot", i.e. `10`, `20`, `30`, …) or to the current world's own landing
spot (`mission / 10 * 10` — the same truncation used by `Decor::OpenDoorsWin()`'s ordinary-win
branch, see above). In other words: an ordinary numbered level (say, mission `23`) backs out one
step, to its world's landing page (`20`); the landing page itself backs out two steps, all the way
to the top-level hub (`1`).

The pause menu's own button visibility logic reads the same two facts — `mission == 1` and
`mission % 10 == 0` — to decide which buttons make sense to show at all:

*From `Game1.cpp:892-904`:*

```cpp
if (phase == Def::Phase::Pause)
{
    DrawTextUnderButton(Def::ButtonGlyph::PauseMenu, MyResource::TX_BUTTON_MENU);
    if (mission != 1)
    {
        DrawTextUnderButton(Def::ButtonGlyph::PauseBack, MyResource::TX_BUTTON_BACK);
    }
    DrawTextUnderButton(Def::ButtonGlyph::PauseSetup, MyResource::TX_BUTTON_SETUP);
    if (mission != 1 && mission % 10 != 0)
    {
        DrawTextUnderButton(Def::ButtonGlyph::PauseRestart, MyResource::TX_BUTTON_RESTART);
    }
    DrawTextUnderButton(Def::ButtonGlyph::PauseContinue, MyResource::TX_BUTTON_CONTINUE);
}
```

"Back" is hidden only on the hub itself (there is nowhere further back to go). "Restart" is hidden
both on the hub *and* on any world-landing-spot mission (`mission % 10 == 0`) — restarting a hub or
a landing page is meaningless because neither one is a playable level with its own start position
and hazards; only an actual numbered level (`mission % 10` in `1..9`, following the `StartMission`
gating seen earlier) can be meaningfully restarted. This is the clearest evidence in the whole
codebase that mission numbers ending in a multiple of 10 are architecturally distinct from ordinary
levels — they are hub/landing nodes in the mission graph, not gameplay content — confirming from a
completely independent angle (menu logic, not win-condition logic) the same scheme
`Decor::OpenDoorsWin()`'s `m_term = m_mission / 10 * 10` computation implied.

## `m_buildOfficialMissions`: declared, set once, read never

`SetBuildOfficialMissions(bool)` is a private `Decor` method mentioned by name in this book's
assignment brief, and it is worth being precise about what it actually does in the current source:
essentially nothing observable. Its full body is one assignment:

*From `Decor.cpp:2098-2101`:*

```cpp
void Decor::SetBuildOfficialMissions(bool bMode)
{
    m_buildOfficialMissions = bMode;
}
```

Searching the entire `mobile-eggbert` tree for callers of `SetBuildOfficialMissions` turns up
exactly one hit: its own definition. It is never invoked from `Game1`, from `InputPad`, or from
anywhere else in `Decor.cpp`. The backing field, `m_buildOfficialMissions`
(`Decor.hpp:492`, documented as *"True when building the official mission map (suppresses some
gameplay features)"*), is likewise set exactly once — to `false`, in `Decor`'s member-initializer
list (`Decor.cpp:213`) — and is never *read* anywhere in `Decor.cpp` either. There is also a
`Tables::CheatCodes::BuildOfficialMissions` enum value and a `"buildofficialmissions"` entry in
`InputPad.cpp`'s typed-cheat table (see [Chapter 23](ch23-secret-powers-and-cheat-system.md)), but
that path calls `Decor::CheatAction(Tables::CheatCodes::BuildOfficialMissions)`, and
`Decor::CheatAction` has no branch for that value either — so even the cheat-code path that names
this concept does not reach `SetBuildOfficialMissions`. Taken together, `SetBuildOfficialMissions`,
`m_buildOfficialMissions`, and the `BuildOfficialMissions` cheat code form one connected but
entirely dead subsystem in the current state of the codebase: declared consistently at every layer
(enum, cheat table, `Decor` method, backing field) but wired together nowhere. Whatever
"suppress some gameplay features while building the official mission map" behavior this was meant
to implement is not present in the running game today.

## `GetNbVies`/`SetNbVies`: "lives", confirmed

The brief for this chapter asks to verify that "vies" means lives — it does, unambiguously, on two
independent pieces of evidence. First, `GameData.hpp`'s own save-format documentation names the
field in English directly:

*From `GameData.hpp:30`:*

```
 *   +0      1     nbVies     - lives remaining (default 3)
```

Second, `Decor::DoorsLost()` — called whenever Blupi's life count reaches zero and the level is
lost (see below) — resets the counter to exactly that documented default:

*From `Decor.cpp:11716-11719`:*

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

`Decor`'s own accessors are, again, plain passthroughs with no validation of their own — despite
the header comment's `@param` note that the value "must be non-negative", nothing in `SetNbVies`
enforces that:

*From `Decor.cpp:1691-1699`:*

```cpp
int Decor::GetNbVies()
{
    return m_nbVies;
}

void Decor::SetNbVies(int nbVies)
{
    m_nbVies = nbVies;
}
```

*From `Decor.hpp:963-967`:*

```cpp
/**
 * @brief Sets the number of lives Blupi currently has.
 * @param[in] nbVies  New life count; must be non-negative.
 */
void SetNbVies(int nbVies);
```

The "must be non-negative" constraint is documentation, not enforced code — `m_nbVies` is in fact
deliberately driven negative by the death-handling logic itself:

*From `Decor.cpp:6393-6398`:*

```cpp
else
{
    m_nbVies = -1;
    m_term = -1;
    DoorsLost();
}
```

So `m_nbVies == -1` is a real, reachable runtime value, used as an internal "just died, level over"
marker in the same statement that sets the loss signal `m_term = -1` — a small but genuine
contradiction between the header's documented precondition and the method's actual observed
callers. `LayEgg` (`Cheat4`, see [Chapter 23](ch23-secret-powers-and-cheat-system.md)) is the other
direct mutator of lives outside the death/respawn logic, unconditionally setting `m_nbVies = 9`.

`m_nbVies` is decremented in the standard death path — the branch handling every "hurt" animation
(`Clear1`–`Clear8`, `Drown`, `Glu`, `Electro`) reaching its final phase — which either respawns
Blupi (if lives remain) or ends the level (if `m_nbVies` is already at or below zero):

*From `Decor.cpp:6379-6398`:*

```cpp
if (m_nbVies > 0)
{
    m_blupiAction = BlupiAction::Hide;
    m_blupiIcon = -1;
    m_blupiPhase = 0;
    if (m_blupiRestart)
    {
        m_blupiPos = m_blupiValidPos;
    }
    ...
    VoyageInit(VoyageGetPosVie(m_nbVies), m_pixmap->HotSpotToHud(celSwitch), 48, PixmapChannel::Blupi);
}
else
{
    m_nbVies = -1;
    m_term = -1;
    DoorsLost();
}
```

Note this branch never actually *decrements* `m_nbVies` in the excerpt above — the decrement must
happen earlier, at the point a hazard first triggers the hurt animation (outside the scope of this
chapter's citations; see [Chapter 21](ch21-physics-and-collision.md) for the hazard-contact code
that transitions Blupi into `Clear1`–`Clear8`/`Drown`/`Glu`/`Electro` in the first place). What this
excerpt shows is the *consequence* of that decrement once the death animation finishes: a positive
remaining count triggers a `VoyageInit` animation flying a life-icon toward the HUD position for the
new count (`VoyageGetPosVie(m_nbVies)`, `Decor.hpp:1764`), while a non-positive count ends the run.

## `IsTerminated()` and `m_term`: the win/loss signal, briefly

`Decor::IsTerminated()` is a one-line accessor for `m_term`:

*From `Decor.cpp:493-496`:*

```cpp
int Decor::IsTerminated()
{
    return m_term;
}
```

Its header documents the contract precisely: `0` = still running, positive = won, negative = lost
(`Decor.hpp:693-700`). This chapter only needs `m_term`'s value space to explain what "mission
completion" means for `GetMission`/`SetMission` purposes — the actual door/gold mechanics that
produce each value are [Chapter 22](ch22-doors-keys-doorkeyflags.md)'s territory. Reading the
win-condition block once, for grounding, shows every concrete value `m_term` can take:

*From `Decor.cpp:6411-6434`, the `BlupiAction::Win` completion branch:*

```cpp
if (m_blupiAction == BlupiAction::Win && m_blupiPhase == Config::ScaleTime(40))
{
    if (m_bPrivate)
    {
        m_term = 1;
    }
    else if (m_mission == 1)
    {
        m_term = 199;
    }
    else if (m_mission == 199)
    {
        m_term = -2;
    }
    else if (m_bFoundCle)
    {
        OpenGoldsWin();
        m_term = 1;
    }
    else
    {
        OpenDoorsWin();
        m_term = m_mission / 10 * 10;
    }
}
```

This confirms the `world * 10 + level` scheme again from a different angle: winning an ordinary
level (not the hub, not mission 199, no special key found) sets `m_term` to `m_mission / 10 * 10` —
the *current world's* base mission number, which `Game1` presumably interprets as "return to this
world's local hub/menu" rather than as a literal next-mission index. Mission `1` (the world-select
hub) winning transitions to mission `199` — a reserved, apparently special/final mission number,
confirmed by the `else if (m_mission == 199) { m_term = -2; }` branch immediately below it, which
gives mission 199's own win a distinct negative outcome code (`-2`) rather than the ordinary `1`.
`DoorsLost()`, `OpenDoorsWin()`, and `OpenGoldsWin()` — the three door/gold-state mutators called
from this and the death-path branches above — are covered in depth in
[Chapter 22](ch22-doors-keys-doorkeyflags.md); this chapter only needed their call sites to show
where `m_term`'s value comes from.

## `ContinueMissionType`: `Game1`'s resume state machine

`ContinueMissionType` is not a `Decor` type at all — it is declared in its own header,
`include/WindowsPhoneSpeedyBlupi/def/ContinueMission.hpp`, and used exclusively by `Game1`. It is
documented here because the assignment brief for this chapter names it directly, and because it is
the piece that decides *whether* `Decor`'s own quick-save mechanism (`CurrentRead()`/`CurrentWrite()`,
`Decor.hpp:1856-1881`) gets invoked on a given app resume.

*From `include/WindowsPhoneSpeedyBlupi/def/ContinueMission.hpp:29-34`:*

```cpp
enum class ContinueMissionType : SharpRuntime::ushortcs
{
    None    = 0,   ///< @brief No continue-mission request is pending.
    Pending = 1,   ///< @brief A continue request has been issued but not yet acted on.
    Active  = 2    ///< @brief The continue sequence is currently executing.
};
```

The three-state lifecycle exists to bridge an asynchronous handoff: the app can be reactivated (a
`OnActivated` callback) at a point in the frame loop where it is not yet safe to act on that fact
(because the background texture may not have been swapped back in yet), so the state is staged
through `Pending` and only promoted to `Active` on the *next* `Draw()` call:

*From `Game1.cpp:208-212` (`OnActivated`):*

```cpp
void Game1::OnActivated(System::Object* sender, const System::EventArgs& args)
{
    continueMission = ContinueMissionType::Pending;
    Game::OnActivated(sender, args);
}
```

*From `Game1.cpp:525-531` (top of `Draw()`):*

```cpp
void Game1::Draw(const Microsoft::Xna::Framework::GameTime& gameTime)
{
    if (continueMission == ContinueMissionType::Pending)
    {
        continueMission = ContinueMissionType::Active;
    }
    pixmap->BeginBatch();
```

`Update()`, running in `Def::Phase::Wait`, is the consumer: once it sees `Active`, it immediately
resets to `None` (a request is only ever acted on once) and attempts `decor.CurrentRead()` — if
that succeeds (a quick-save file exists and parses), the game jumps straight to
`Def::Phase::Resume` instead of the normal wait/init sequence:

*From `Game1.cpp:269-279`:*

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
```

A third read site, `DrawWaitProgress()`, uses the field purely as a display guard — while any
continue-mission request is outstanding (`!= None`), the ordinary "loading" progress animation is
suppressed entirely:

*From `Game1.cpp:1033-1038`:*

```cpp
void Game1::DrawWaitProgress()
{
    if (continueMission != ContinueMissionType::None)
    {
        return;
    }
```

In short: `ContinueMissionType` answers one narrow question — "did the OS just bring this app back
to the foreground, and if so, have we had a chance to try resuming from the exact frame it was
suspended at yet?" — and its only interaction with `Decor` is the single `CurrentRead()` call. It
has nothing to do with `GetMission`/`SetMission` or `m_nbVies`; those are read again independently
by the normal `StartMission`/`ContinueMission` paths once the phase machine settles.

## See also

- [Chapter 12 — Game1: the State Machine](../part03-architecture/ch12-game1-state-machine.md) —
  `Def::Phase`, `SetPhase`, and where `ContinueMissionType` fits into the overall phase graph.
- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md) — the hazard contact code that
  first transitions Blupi into the `Clear1`–`Clear8`/`Drown`/`Glu`/`Electro` hurt actions this
  chapter picks up at their final phase.
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md) — `DoorsLost()`,
  `OpenDoorsWin()`, `OpenGoldsWin()`, and the `m_doors[]` layout referenced above.
- [Chapter 23 — Secret Powers and the Cheat System](ch23-secret-powers-and-cheat-system.md) —
  `LayEgg`'s `m_nbVies = 9`, and the dead `BuildOfficialMissions` cheat path.
- [Chapter 43 — GameData: Save Format](../part08-data-persistence-content/ch43-gamedata-save-format.md) —
  the `nbVies`/`lastWorld`/`doors[]` byte layout this chapter quotes from `GameData.hpp`.
