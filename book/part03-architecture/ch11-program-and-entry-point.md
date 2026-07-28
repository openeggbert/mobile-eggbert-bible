# Chapter 11: Program and Entry Point

Every C++ program needs exactly one `main()`. For `mobile-eggbert`, that function lives in a single
83-line file, `src/WindowsPhoneSpeedyBlupi/Program.cpp`, and its job is deliberately narrow:
construct the top-level `Game1` object, run it, and make sure that no exception can escape the
process without being logged. This chapter reads that file line by line.

Despite its small size, `Program.cpp` is worth a full chapter for two reasons. First, it is the
one place in the entire codebase where platform-specific entry-point plumbing (the Android
`SDL_main` rename) is allowed to leak into game code — everywhere else, that plumbing is
deliberately hidden. Second, its exception-handling and logging strategy is a small but complete
example of a pattern this book will see again in [Chapter 12](ch12-game1-state-machine.md): using
`CNA::Logger` with a deliberately raised minimum log level so that verbose startup tracing is
available for debugging but silent in ordinary runs.

## The full file

*From `Program.cpp:1-84`:*

```cpp
/**
 * @file Program.cpp
 * @brief Application entry point for the SpeedyBlupi / mobile-eggbert game.
 * @details Constructs the top-level Game1 object, invokes its Run() loop, and
 *          handles any unhandled C++ exceptions before the process exits.
 * ...
 */

//using WindowsPhoneSpeedyBlupi;

#include <iostream>

// CNA/Entrypoint.hpp handles the SDL_main renaming required on Android so that
// SDL's Java bridge (SDLActivity.nativeRunMain) can locate main() as SDL_main.
// Game code must never include <SDL3/SDL_main.h> directly.
#include "CNA/Entrypoint.hpp"

#include "CNA/Logger.hpp"
#include "Microsoft/Xna/Framework/Game.hpp"
#include "WindowsPhoneSpeedyBlupi/Game1.hpp"

int main(int argc, char* args[])
{
    CNA::Logger::Info("SpeedyBlupi: main entered");
    CNA::Logger::SetMinimumLevel(CNA::LogLevel::ERROR);
    CNA::Logger::Info("SpeedyBlupi: before Game1 construction");
    try
    {
        WindowsPhoneSpeedyBlupi::Game1 game;
        CNA::Logger::Info("SpeedyBlupi: Game1 constructed, entering Run()");
        game.Run();
        CNA::Logger::Info("SpeedyBlupi: Run() returned normally");
    }
    catch (const std::exception& e)
    {
        CNA::Logger::Error(std::string("SpeedyBlupi: fatal exception in main: ") + e.what());
        return 1;
    }
    catch (...)
    {
        CNA::Logger::Error("SpeedyBlupi: unknown fatal exception in main");
        return 1;
    }
    CNA::Logger::Info("SpeedyBlupi: exiting normally");
    return 0;
}
```

## A dead comment, kept deliberately

The very first non-blank line of the file is a commented-out C# statement:

*From `Program.cpp:28`:*

```cpp
//using WindowsPhoneSpeedyBlupi;
```

This is a fossil from the file's C# ancestor — a `using` directive that would have brought the
`WindowsPhoneSpeedyBlupi` namespace into scope in the original decompiled/ported C# source. It has
no effect in C++ (the namespace is instead referenced explicitly, as `WindowsPhoneSpeedyBlupi::Game1`,
inside `main()`), and it is not required for anything to compile. Its survival is consistent with
the migration discipline described in [Chapter 1](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md):
the porting process has generally preferred to leave a visible trace of the original source over
silently deleting it, even when the trace is inert.

## `CNA/Entrypoint.hpp`: hiding the Android `SDL_main` rename

The file's most substantive comment block explains why it includes `CNA/Entrypoint.hpp` rather than
SDL's own header:

*From `Program.cpp:22-25`:*

```cpp
// CNA/Entrypoint.hpp handles the SDL_main renaming required on Android so that
// SDL's Java bridge (SDLActivity.nativeRunMain) can locate main() as SDL_main.
// Game code must never include <SDL3/SDL_main.h> directly.
#include "CNA/Entrypoint.hpp"
```

On Android, SDL's Java bridge (`SDLActivity.nativeRunMain`) expects the native entry point to be
named `SDL_main`, not `main`. SDL solves this the same way it always has: `<SDL3/SDL_main.h>`
`#define`s `main` to `SDL_main` when compiling for Android, so that a completely ordinary-looking
`int main(int argc, char* argv[])` definition is transparently renamed by the preprocessor before
the linker ever sees it. On every other platform this game targets (Windows, Linux, and the Web
build via Emscripten), the equivalent inclusion is either a no-op or not needed at all.

CNA wraps this behavior in its own `CNA/Entrypoint.hpp` header specifically so that game code — like
`Program.cpp` — never has to include `<SDL3/SDL_main.h>` directly, and therefore never has to know
that SDL is involved at all. This is a small but real instance of the CNA-marginal principle this
book follows throughout: `mobile-eggbert`'s own code is written entirely in terms of the
Microsoft/XNA-shaped API and a handful of CNA convenience headers like this one; the fact that SDL3
sits underneath is invisible from `Program.cpp`. (CNA's own implementation of `Entrypoint.hpp` — how
exactly it renames `main` for each platform — is CNA's business, not this book's; see
[Chapter 2](../part01-origins-and-ecosystem/ch02-openeggbert-ecosystem-map.md).)

## The logging strategy

`main()` opens with three log calls before anything interesting happens:

*From `Program.cpp:60-63`:*

```cpp
int main(int argc, char* args[])
{
    CNA::Logger::Info("SpeedyBlupi: main entered");
    CNA::Logger::SetMinimumLevel(CNA::LogLevel::ERROR);
    CNA::Logger::Info("SpeedyBlupi: before Game1 construction");
```

The sequencing here matters and is a little counter-intuitive: `CNA::Logger::Info(...)` is called
*before* `SetMinimumLevel(ERROR)` raises the log threshold, and again immediately *after*. Since
`SetMinimumLevel(ERROR)` suppresses everything below `ERROR` severity (which `Info` is), the second
call — and every other `Info`-level call later in the function — is a silent no-op in a normal run.
The file's own Doxygen comment explains the intent directly:

*From `Program.cpp:16-20`:*

```cpp
 * Logging uses CNA::Logger throughout.  The minimum log level is raised to
 * @c ERROR immediately after entering @c main() so that only error messages
 * are emitted in production builds; lower-severity messages around construction
 * and Run() are therefore silenced at runtime but remain available when the
 * log level is lowered for debugging.
```

In other words, every `Info(...)` call in this file is a piece of narration left in place for a
developer who temporarily lowers the minimum log level while debugging a startup crash — "did we
even get as far as constructing `Game1`?", "did `Run()` return, or did the process die inside it?"
— without those questions cluttering a normal player's log output. This is the same
verbose-but-normally-silent tracing style used throughout the codebase (compare
`Game1::LoadContent()`'s single `CNA::Logger::Trace("Game1::LoadContent")` call, discussed in
[Chapter 12](ch12-game1-state-machine.md)).

## Constructing and running the game

The heart of the function is four lines inside the `try` block:

*From `Program.cpp:64-70`:*

```cpp
    try
    {
        WindowsPhoneSpeedyBlupi::Game1 game;
        CNA::Logger::Info("SpeedyBlupi: Game1 constructed, entering Run()");
        game.Run();
        CNA::Logger::Info("SpeedyBlupi: Run() returned normally");
    }
```

`WindowsPhoneSpeedyBlupi::Game1 game;` constructs the entire game **on the stack**, not on the
heap. Its constructor — covered in full in [Chapter 12](ch12-game1-state-machine.md) — allocates the
graphics device manager, the `Pixmap` and `Sound` subsystems, the `Decor` gameplay simulation,
`InputPad`, and `GameData`, and immediately queues the very first phase transition
(`SetPhase(Def::Phase::First)`). None of that happens lazily; by the time the `WindowsPhoneSpeedyBlupi::Game1
game;` line finishes executing, the object is fully wired up and the phase state machine has already
taken its first step.

`game.Run()` is inherited from CNA's `Microsoft::Xna::Framework::Game` base class (the same
XNA-shaped `Game` class that `Game1` derives from — see [Chapter 12](ch12-game1-state-machine.md)
and [Chapter 14](ch14-xna-api-via-cna.md)). This is the call that actually starts the game loop: it
blocks the calling thread, repeatedly invoking `Update()` and `Draw()` at the configured frame rate,
until the game requests its own exit (via `Exit()`, wired to `Game1::OnExiting`) or the platform
closes the window. `Program.cpp` itself has no loop of its own — the entire lifetime of the running
game is inside this one call.

When `Run()` finally returns — normally, because the game decided to exit — the function logs that
fact and falls through to the final two lines:

*From `Program.cpp:81-82`:*

```cpp
    CNA::Logger::Info("SpeedyBlupi: exiting normally");
    return 0;
```

## Exception handling: two catch blocks, one behavior

`Program.cpp`'s entire construction-and-run sequence is wrapped in two `catch` clauses, and the
file's own header comment describes the intent precisely:

*From `Program.cpp:7-14`:*

```cpp
 * ### Exception handling and logging strategy
 * The entire game construction and run loop is wrapped in two catch blocks:
 * 1. @c catch(const std::exception&) — catches all standard library exceptions
 *    and exceptions derived from @c std::exception.  The @c what() message is
 *    logged at ERROR level and the process exits with code 1.
 * 2. @c catch(...) — catches all remaining exceptions (e.g. non-standard throws).
 *    A generic fatal message is logged at ERROR level and the process exits
 *    with code 1.
```

In code:

*From `Program.cpp:71-80`:*

```cpp
    catch (const std::exception& e)
    {
        CNA::Logger::Error(std::string("SpeedyBlupi: fatal exception in main: ") + e.what());
        return 1;
    }
    catch (...)
    {
        CNA::Logger::Error("SpeedyBlupi: unknown fatal exception in main");
        return 1;
    }
```

Both branches are logged at `ERROR` level — the one level that survives the minimum-level filter set
earlier in `main()` — so a crash is guaranteed to be visible in the log even in a production build
where every `Info`/`Trace` call has been silenced. The first `catch` clause captures anything
deriving from `std::exception` (which, in a C++ codebase full of standard-library containers and
CNA/`sharp-runtime` types, is the overwhelming majority of realistic failure modes) and includes the
exception's own `what()` message in the log line, giving a developer a concrete diagnostic. The
second, catch-all `catch (...)` clause exists purely as a backstop for the rarer case of a
non-standard throw (a raw value, a type that does not derive from `std::exception`) — it cannot
report a message, only the fact that *something* fatal happened.

Both paths return `1` from `main()`, signalling failure to the calling shell or launcher; the
successful path at the bottom of the function returns `0`. This gives `mobile-eggbert` a very simple
but complete contract with its environment: **no exception is ever allowed to propagate out of
`main()` unlogged**, and the process's exit code always distinguishes a clean shutdown from a fatal
error. The file's own Doxygen documentation for `main()` states this contract explicitly as a
`@throws` clause:

*From `Program.cpp:56-57`:*

```cpp
 * @throws Nothing — all exceptions are caught internally and converted to a
 *         non-zero return value.
```

## Command-line arguments: accepted, unused

`main(int argc, char* args[])` accepts the conventional C++ command-line argument pair, but neither
`argc` nor `args` is read anywhere in the function body. The Doxygen comment for the parameters is
candid about this:

*From `Program.cpp:49-51`:*

```cpp
 * @param[in] argc Number of command-line arguments (passed through by SDL on
 *                 all platforms; not currently used by the game).
 * @param[in] args Array of command-line argument strings.
```

The parameters exist because the platform layer (SDL, via CNA's `Entrypoint.hpp` mechanism)
supplies them to whatever function ends up named `main`/`SDL_main` — the signature is not optional
— but `mobile-eggbert` currently has no command-line configuration surface of its own. A reader
looking for a `--windowed`, `--level=N`, or similar flag will not find one; every configuration knob
this game exposes (screen mode, sound, input mode, and so on) lives in `GameData` and is toggled
from in-game menus, not from the command line (see [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md)).

## What `Program.cpp` deliberately does not do

It's worth being explicit about the boundary this file draws, because it clarifies where the "real"
game logic actually lives:

- It does not touch the graphics device, the content pipeline, input, or audio directly — all of
  that is `Game1`'s responsibility, set up inside its constructor and `Initialize()`/`LoadContent()`
  overrides (see [Chapter 12](ch12-game1-state-machine.md)).
- It does not implement any part of the game loop itself — `Run()` is entirely CNA's
  (`Microsoft::Xna::Framework::Game::Run()`), not something `Program.cpp` or even `Game1` defines.
- It does not know anything about `Def::Phase`, missions, or gameplay — those concepts appear for
  the first time one layer up, in `Game1`.

In short, `Program.cpp` is infrastructure, not gameplay: its entire job is to give `Game1` a clean,
logged, exception-safe place to exist and run. That narrow scope is exactly why it fits comfortably
in 84 lines while `Game1.cpp` alone runs to 1,113.

## See also

- [Chapter 12 — Game1: the State Machine](ch12-game1-state-machine.md)
- [Chapter 13 — IGame1 and Dependencies](ch13-igame1-and-dependencies.md)
- [Chapter 14 — The XNA API via CNA](ch14-xna-api-via-cna.md)
- [Chapter 51 — Android Deep Dive](../part10-platform-deep-dives/ch51-android-deep-dive.md)
