# Chapter 53: Web Virtual Filesystem

[Chapter 8](../part02-building-and-running/ch08-web-emscripten-build.md) covers how to configure,
build, and run the Emscripten target — installing the Emscripten SDK, running `emcmake cmake`, and
launching the result with `emrun`. This chapter picks up where that one stops: what the browser's
virtual filesystem actually looks like once the game is running, how a save file that lives inside
a WebAssembly heap ends up surviving a page reload, and — as a specific worked example — whether
the game's timing model can be trusted to run at the same speed in a browser tab as it does on
native desktop.

## Two filesystems, not one

A `mobile-eggbert` Emscripten build does not see a single filesystem the way a native Linux or
Windows build does. Emscripten's virtual filesystem (Emscripten's own in-memory `MEMFS`, with one
subtree replaced by a different backend) presents the game with what looks like an ordinary POSIX
tree, but the paths in that tree are backed by two entirely different storage mechanisms depending
on which subtree you're in. `mobile-eggbert`'s own `README.md` lays out the mapping precisely:

*From `README.md:171-179`:*

> | Path | Source directory | Notes |
> |------|-----------------|-------|
> | `/Content/backgrounds` | `Content/backgrounds/` | Read-only; preloaded |
> | `/Content/icons` | `Content/icons/` | Read-only; preloaded |
> | `/Content/sounds` | `Content/sounds/` | Read-only; preloaded |
> | `/worlds` | `worlds/` | Read-only; preloaded |
> | `/save` | IndexedDB (IDBFS) | Writable; persists `SpeedyBlupi` save file |

The first four rows are all the same mechanism: Emscripten's `--preload-file` linker flag bakes
the real directory's contents into a `.data` file alongside the `.wasm` binary at build time, and
the Emscripten runtime unpacks that data into `MEMFS` — an in-memory filesystem — before the game's
`main()` ever runs. The root `CMakeLists.txt`'s Emscripten branch shows exactly which four
directories get this treatment, one `--preload-file` argument per directory:

*From `CMakeLists.txt:161-189`:*

```cmake
elseif(EMSCRIPTEN)
    # ---------------------------------------------------------------------------
    # Emscripten link options
    # ---------------------------------------------------------------------------
    # Asset virtual-filesystem layout (mounted paths match what the game expects
    # at runtime relative to the working directory):
    #
    #   ${CMAKE_SOURCE_DIR}/Content/backgrounds  ->  /Content/backgrounds
    #   ${CMAKE_SOURCE_DIR}/Content/icons        ->  /Content/icons
    #   ${CMAKE_SOURCE_DIR}/Content/sounds       ->  /Content/sounds
    #   ${CMAKE_SOURCE_DIR}/worlds               ->  /worlds
    #
    # Save data is persisted via IDBFS mounted at /save (see StoragePaths.cpp).
    # The JS shell code mounts IDBFS after Module init and before the game loop.
    target_link_options(${_game_target} PRIVATE
        -sALLOW_MEMORY_GROWTH=1
        -sSTACK_SIZE=1048576
        -sINITIAL_MEMORY=134217728
        -sFORCE_FILESYSTEM=1
        "-sEXPORTED_RUNTIME_METHODS=['FS','ccall','cwrap']"
        -lidbfs.js
        "SHELL:--pre-js ${CMAKE_SOURCE_DIR}/cmake/web/pre.js"
        "SHELL:--preload-file ${CMAKE_SOURCE_DIR}/Content/backgrounds@/Content/backgrounds"
        "SHELL:--preload-file ${CMAKE_SOURCE_DIR}/Content/icons@/Content/icons"
        "SHELL:--preload-file ${CMAKE_SOURCE_DIR}/Content/sounds@/Content/sounds"
        "SHELL:--preload-file ${CMAKE_SOURCE_DIR}/worlds@/worlds"
        "-sMIN_WEBGL_VERSION=2"
        "-sMAX_WEBGL_VERSION=2"
    )
```

Each `--preload-file SRC@DEST` argument tells Emscripten's packaging tool (`file_packager.py`,
invoked implicitly by the linker flag) to bundle that one host directory into the generated
`WindowsPhoneSpeedyBlupi.data` asset bundle, mounted at `DEST` inside the virtual filesystem at
startup. This is a meaningfully different strategy from the Android build's asset packaging
covered in [Chapter 51](ch51-android-deep-dive.md): where Android relies on two filesystem
symlinks and lets Gradle's asset merge step do the work implicitly, the Emscripten build lists each
of the four content roots as an explicit, individually-named linker argument. There is no
symlink-following step here to go wrong quietly — if a directory is missing from this list, the
build itself would simply never bundle it, which is a build-time-visible omission rather than a
runtime-only symptom.

`-sFORCE_FILESYSTEM=1` and `-sEXPORTED_RUNTIME_METHODS=['FS','ccall','cwrap']` are what make the
`FS` object (Emscripten's userspace filesystem API, exposed to the surrounding JavaScript) available
to the custom `pre.js` shell script discussed below — without them, `FS` and `IDBFS` would not be
reachable from outside the compiled module at all.

## `/save`: the one writable, persistent mount

The fifth row of the table — `/save`, backed by IDBFS rather than `MEMFS` — is where things get
more interesting. IDBFS is Emscripten's built-in filesystem backend that maps a subtree of the
virtual filesystem onto the browser's IndexedDB, a persistent, per-origin key-value store built
into every modern browser. Unlike the four preloaded content directories, `/save` starts out empty
at build time; it exists purely to give the game somewhere to *write*.

`-lidbfs.js` in the linker flags above pulls in the IDBFS backend itself, but linking the backend
in doesn't mount it — that's done explicitly by a small hand-written JavaScript file injected via
`--pre-js`, which runs before the compiled module initializes:

*From `pre.js` (in `mobile-eggbert`'s `cmake/web/` directory):*

```javascript
// pre.js - executed before the Emscripten Module is initialized.
// Mounts IDBFS at /save so that IsolatedStorage writes (SpeedyBlupi save file)
// persist across page reloads via the browser's IndexedDB.
//
// Virtual filesystem layout at runtime:
//   /Content/backgrounds  - preloaded read-only game backgrounds
//   /Content/icons        - preloaded read-only game icons
//   /Content/sounds       - preloaded read-only game sounds
//   /worlds               - preloaded read-only level files
//   /save                 - IDBFS (persistent; save data written here)
//
// TODO: call FS.syncfs(false, cb) periodically or on exit to flush IDBFS
//       writes back to IndexedDB.  Currently data is written to the in-memory
//       layer but may not survive a hard reload unless sync is called.

Module['preRun'] = Module['preRun'] || [];
Module['preRun'].push(function () {
    FS.mkdir('/save');
    FS.mount(IDBFS, {}, '/save');

    // Synchronise IDBFS from the persistent store (populate=true means
    // "load existing data into the in-memory VFS before the game starts").
    FS.syncfs(true, function (err) {
        if (err) {
            console.warn('IDBFS preRun sync failed:', err);
        }
    });
});

// Flush IDBFS to IndexedDB when the page is about to unload so that the
// last write of SpeedyBlupi save data is not lost.
window.addEventListener('beforeunload', function () {
    if (typeof FS !== 'undefined' && typeof IDBFS !== 'undefined') {
        FS.syncfs(false, function (err) {
            if (err) {
                console.warn('IDBFS beforeunload sync failed:', err);
            }
        });
    }
});
```

Two `FS.syncfs()` calls bracket the game's whole session: one at startup (`populate=true`, meaning
"pull IndexedDB's existing contents into the in-memory VFS before anything runs"), and one on the
`beforeunload` browser event (`populate=false`, meaning "push whatever's in the in-memory VFS back
out to IndexedDB before the page goes away").

### Where `README.md`'s claim and the actual code disagree

This is worth stating precisely, because it is a real discrepancy between two documents in the same
repository. `mobile-eggbert`'s `README.md` describes the flush behavior like this:

*From `README.md:183-185`:*

> Save data (`SpeedyBlupi`) is stored in `/save/.cna_isolated_storage/SpeedyBlupi`
> backed by the browser's IndexedDB. It is flushed to IndexedDB on every write
> and on page unload.

"Flushed to IndexedDB on every write" is not what the `pre.js` code above actually does, and the
`pre.js` file says so itself, in its own `TODO` comment: syncing only happens at the two bracketing
points (page load and page unload) — there is no `FS.syncfs()` call anywhere triggered by an
individual write to the save file in between. In-memory `MEMFS`-backed writes made during a play
session live only in the WebAssembly heap's virtual filesystem until the `beforeunload` handler
fires; they are not durably committed to IndexedDB the moment they happen. The `pre.js` author's own
comment is unambiguous about this gap:

> TODO: call `FS.syncfs(false, cb)` periodically or on exit to flush IDBFS writes back to
> IndexedDB. Currently data is written to the in-memory layer but may not survive a hard reload
> unless sync is called.

Practically, this means the `beforeunload` handler is doing all of the durability work for a normal
browser-tab close. That handler is reasonably reliable for an ordinary tab close or navigation, but
`beforeunload` is well known (independent of this project) to be unreliable in some
circumstances — a browser or OS process kill, a crashed tab, or certain mobile-browser
backgrounding behaviors can all skip it. In those cases, under the code as it actually exists in
this checkout, any save-file writes made since the last successful sync would not have reached
IndexedDB at all. This chapter reports the gap between the documentation's claim and the code's
actual behavior as found; there is no evidence in this repository of anyone having verified it as a
practical problem, or having fixed it, as of the checkout this chapter was written against.

### Where the save file actually lives inside `/save`

The `.cna_isolated_storage/SpeedyBlupi` sub-path referenced in `README.md` comes from `cna`'s
shared isolated-storage path resolver, which has a dedicated Emscripten branch:

*From `StoragePaths.cpp:19-22`* (in the `sharp-runtime` repository; cited here only for the one
branch relevant to the Web save path):

```cpp
#if defined(__EMSCRIPTEN__)
    // On Emscripten, persist save data under /save which is mounted as
    // IDBFS by the application startup code so data survives page reloads.
    const std::filesystem::path root = std::filesystem::path("/save") / ".cna_isolated_storage";
```

Every game — not just this one — that links against this shared storage layer and builds for
Emscripten gets its isolated-storage root rooted under `/save/.cna_isolated_storage/`; the
`SpeedyBlupi` subdirectory beneath that is `mobile-eggbert`'s own application-specific isolated
storage name, the same identifier XNA's `IsolatedStorageFile` concept uses across every platform
this game builds for. This is the same function whose Android branch is discussed in
[Chapter 51](ch51-android-deep-dive.md), and whose plain-desktop branch (the `#else` case, rooted at
`std::filesystem::current_path() / ".cna_isolated_storage"`) underlies the native Linux/Windows
save path covered by Part VIII.

## Audio needs a user gesture, CPU usage is bounded

Two smaller, but real, Web-specific notes from `README.md` round out the picture of what's
different about running in a browser tab versus a native window:

*From `README.md:186-189`:*

> Audio uses SDL_mixer; the browser may require a user gesture before audio
> starts. If no sound is heard, click the canvas once.
>
> CPU usage is bounded — the game uses `emscripten_set_main_loop` (backed by
> `requestAnimationFrame`) instead of a busy loop.

The user-gesture requirement is a standard, browser-enforced autoplay policy (not something the
game's own code can bypass), and it's a genuinely different failure mode from anything covered in
[Chapter 40](../part06-audio/ch40-audio-issue-analysis.md)'s audio-issue analysis — silence here
means "the browser is withholding the audio context," not a resampling or asset-loading bug.

## The fixed-timestep accumulator: matching desktop game speed in a browser tab

The most substantial Web-specific engineering claim in `README.md` is about timing, and it is
worth quoting in full before verifying it:

*From `README.md:190-196`:*

> **Game speed**: the Web build uses a fixed-timestep accumulator in
> `CNA/Game.cpp` to match native desktop timing. The browser calls the RAF
> callback at ~60 Hz; real inter-frame wall-clock time is measured and
> accumulated, and `Update()` fires only when one full `TargetElapsedTime`
> slice has accumulated. This ensures gameplay speed is identical to
> Linux/Windows regardless of the browser's actual RAF cadence. A 250 ms
> spike cap prevents runaway catch-up after the tab is backgrounded.

This claim can actually be checked against real code, because `cna` (the underlying framework
`README.md` refers to as `CNA/Game.cpp`) is available in this environment. The real file is
`Game.cpp` in `cna`'s `src/Microsoft/Xna/Framework/` tree, and it contains an `#if
defined(__EMSCRIPTEN__)`-guarded block that matches the `README.md` description point for point:

*From `Game.cpp:750-813` (in `cna`, cited here to verify a specific claim made in
`mobile-eggbert`'s own `README.md` — not as a broader dive into CNA's internals):*

```cpp
#if defined(__EMSCRIPTEN__)
    struct Game::EmscriptenLoopState
    {
        Game* game = nullptr;
        GameTime gameTime;
        std::uint64_t lastTickMs = 0;
        double accumulatorMs = 0.0;
    };

    Game::EmscriptenLoopState Game::s_emLoopState;

    void Game::EmscriptenMainLoopCallback()
    {
        EmscriptenLoopState& state = s_emLoopState;
        if (state.game == nullptr)
        {
            return;
        }

        state.game->PollEvents();

        const std::uint64_t nowMs = SDL_GetTicks();
        if (state.lastTickMs == 0)
        {
            state.lastTickMs = nowMs;
        }

        double deltaMs = static_cast<double>(nowMs - state.lastTickMs);
        state.lastTickMs = nowMs;

        if (deltaMs > 250.0)
        {
            deltaMs = 250.0;
        }

        state.accumulatorMs += deltaMs;
        const double targetMs = state.game->getTargetMsFrameTimeProperty();
        const auto stepSpan = System::TimeSpan::FromMilliseconds(targetMs);

        bool updated = false;
        while (state.accumulatorMs >= targetMs)
        {
            state.accumulatorMs -= targetMs;

            state.gameTime.setElapsedGameTimeProperty(stepSpan);
            state.gameTime.setTotalGameTimeProperty(state.gameTime.getTotalGameTimeProperty() + stepSpan);
            state.gameTime.setIsRunningSlowlyProperty(false);

            state.game->Update(state.gameTime);
            updated = true;
        }

        if (updated && state.game->BeginDraw())
        {
            state.game->Draw(state.gameTime);
            state.game->EndDraw();
        }

        if (!state.game->RunApplication)
        {
            emscripten_cancel_main_loop();
            state.game->OnExiting(state.game, System::EventArgs::Empty);
        }
    }
#endif
```

and the loop is wired in via `RunLoop()`:

*From `Game.cpp:825-838`:*

```cpp
void Game::RunLoop()
{
#if defined(__EMSCRIPTEN__)
    s_emLoopState.game = this;
    s_emLoopState.gameTime = gameTime_;
    emscripten_set_main_loop(EmscriptenMainLoopCallback, 0, 1);
#else
    while (RunApplication)
    {
        Tick();
    }

    OnExiting(this, System::EventArgs::Empty);
#endif
}
```

Every element of `README.md`'s description checks out against this code:

- **Wall-clock delta measurement**: `SDL_GetTicks()` is read each callback and diffed against the
  previous call's timestamp (`nowMs - state.lastTickMs`) — this is the "real inter-frame wall-clock
  time is measured" part, and it is measured independently of whatever cadence the browser actually
  calls the callback at.
- **The 250 ms spike cap**: `if (deltaMs > 250.0) { deltaMs = 250.0; }` is exactly the "runaway
  catch-up after the tab is backgrounded" guard `README.md` describes — without it, a tab that was
  backgrounded (and so received no RAF callbacks) for, say, ten real seconds would otherwise try to
  run ten seconds' worth of `Update()` calls back-to-back the moment it regains focus.
- **The accumulator and fixed-slice `Update()` firing**: `state.accumulatorMs += deltaMs;` followed
  by `while (state.accumulatorMs >= targetMs) { ...Update()... }` is precisely "`Update()` fires
  only when one full `TargetElapsedTime` slice has accumulated" — and it is a `while`, not an `if`,
  so if the browser stutters and delivers a larger-than-normal delta (up to the 250 ms cap), the
  loop calls `Update()` multiple times in a row to catch gameplay simulation back up to real time,
  each call still advancing the simulation by exactly one fixed `targetMs` slice.
- **`targetMs` matches native desktop's own timestep**: `getTargetMsFrameTimeProperty()` reads
  directly from the same `TargetElapsedTime_` field the non-Emscripten `Tick()` path uses (set to
  `System::TimeSpan(166667L)` — 166,667 hundred-nanosecond ticks, i.e. 16.6667 ms, i.e. 60 Hz — in
  `Game`'s constructor), which is exactly what makes "gameplay speed is identical to Linux/Windows
  regardless of the browser's actual RAF cadence" true rather than aspirational: both platforms are
  driven by the same fixed slice size, just measured against a different clock source
  (`emscripten_set_main_loop`'s RAF-driven callback cadence on Web, a native OS timer loop
  everywhere else).
- **`requestAnimationFrame`, not a busy loop**: `emscripten_set_main_loop(EmscriptenMainLoopCallback,
  0, 1)` — the `0` fps argument tells Emscripten to drive the callback from the browser's own RAF
  cadence rather than a fixed interval, and the final `1` (`simulate_infinite_loop`) is what lets
  `RunLoop()` return immediately after registering the callback instead of blocking, which is
  required because Emscripten's main thread must yield back to the browser's own event loop.

Because `cna`'s source was available to check against, this claim did not have to be taken on
`README.md`'s word alone — it is independently source-verified, and the verification is recorded
here specifically so the distinction is clear from the `/save`-flushing discrepancy earlier in this
chapter, which is *not* independently verified beyond reading `pre.js` itself (both `README.md` and
`pre.js` are `mobile-eggbert`-owned documents/files, so that finding rests on `mobile-eggbert`'s own
sources, just two of them that happen to disagree with each other).

## See also

- [Chapter 8](../part02-building-and-running/ch08-web-emscripten-build.md) — the Web/Emscripten
  build process itself (Emscripten SDK setup, `emcmake`/`emrun`).
- [Chapter 51](ch51-android-deep-dive.md) — the Android equivalent of this chapter's asset-mounting
  discussion, including a case where the platform-specific asset path is considerably less certain
  than the Web build's explicit `--preload-file` approach.
- [Chapter 40](../part06-audio/ch40-audio-issue-analysis.md) — `TODO.md`'s separate note that "Web
  version: Sound is a little bit delayed," referenced as supporting evidence in the audio
  investigation but not analyzed further there or here.
- [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md) — the `GameData`
  save-game format itself, independent of which platform's storage backend ultimately persists it.
- [Chapter 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md) — `GameSpeed` and time
  scaling inside the simulation itself, one layer above the fixed-timestep `Update()` cadence this
  chapter covers.
