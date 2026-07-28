# Chapter 8: Web/Emscripten Build

`mobile-eggbert` compiles to WebAssembly via Emscripten, producing a browser-runnable build that
loads game assets from a preloaded virtual filesystem and persists save data through the browser's
IndexedDB. This chapter covers the prerequisites, configure/build/run steps, and virtual filesystem
layout from `README.md`, cross-checked against the actual `EMSCRIPTEN`-guarded logic in
`CMakeLists.txt` (read in full in [Chapter 4](ch04-build-overview.md)) and against `cna`'s own
`Game.cpp`, which is where the fixed-timestep timing behaviour `README.md` describes is actually
implemented.

## Prerequisites

`README.md` documents two setup steps before configuring the build:

*From `README.md:128-141`:*
```markdown
#### Prerequisites

1. Install and activate the [Emscripten SDK](https://emscripten.org/docs/getting_started/downloads.html):
   ```bash
   git clone https://github.com/emscripten-core/emsdk.git
   cd emsdk
   ./emsdk install latest
   ./emsdk activate latest
   source ./emsdk_env.sh
   ```
2. Ensure all submodules are initialised:
   ```bash
   git submodule update --init --recursive
   ```
```

The first step is standard Emscripten SDK setup: clone `emsdk`, install and activate the `latest`
toolchain version, and source `emsdk_env.sh` into the current shell so that `emcmake`/`emcc`/`emrun`
resolve on `PATH`. The second step carries the same caveat already noted in
[Chapter 5](ch05-linux-build.md): `mobile-eggbert` itself has no `.gitmodules` file, so
`git submodule update --init --recursive` run from inside `mobile-eggbert`'s own root is a no-op;
the actual Git submodules that matter for this build (`third_party/SDL`, `third_party/SDL_image`,
`third_party/SDL_mixer`, `vendor/googletest`) are declared in the sibling `cna` checkout's own
`.gitmodules`, and need that command run from inside `cna/` (or from a parent umbrella checkout
that treats both as submodules of itself).

## Configure, build, run

`README.md`'s sequence is a thin wrapper around Emscripten's own `emcmake`/`emrun` tooling:

*From `README.md:143-160`:*
```bash
# Configure
source /path/to/emsdk/emsdk_env.sh
emcmake cmake -S . -B cmake-build-web -DCMAKE_BUILD_TYPE=Debug

# Build
cmake --build cmake-build-web -j

# Run
emrun cmake-build-web/WindowsPhoneSpeedyBlupi.html
```

`emcmake` wraps the ordinary `cmake` invocation so that Emscripten's own toolchain file is
transparently applied, which is what makes `EMSCRIPTEN` (as a CMake variable) become true for the
rest of `CMakeLists.txt`'s platform-detection logic — the same `if(ANDROID) ... elseif(EMSCRIPTEN)
... else()` branching read in full in [Chapter 4](ch04-build-overview.md). Two consequences follow
immediately from that branch:

- `CNA_GRAPHICS_BACKEND` defaults to `"SDL_RENDERER"` (running on WebGL under the hood), without
  `FORCE` — so `-DCNA_GRAPHICS_BACKEND=CANVAS` remains a valid override for the browser HTML5
  Canvas 2D path (`cna/plan_canvas.md`), unlike the Android branch which forces its choice.
- The output target's suffix is set to `.html` (`CMakeLists.txt:105-107`), which is why the build
  produces `WindowsPhoneSpeedyBlupi.html` as its primary artifact rather than a bare executable.

`emrun` is Emscripten's own dev-server-plus-browser-launcher tool — it serves the build output over
HTTP (required for a `.wasm` file to load correctly under most browsers' security policies, since
`file://` URLs are frequently blocked from fetching WASM) and opens the page in a browser
automatically.

## Generated files

*From `README.md:162-169`:*

| File | Description |
|------|-------------|
| `WindowsPhoneSpeedyBlupi.html` | Main entry point — open in browser |
| `WindowsPhoneSpeedyBlupi.js`   | Emscripten JS glue |
| `WindowsPhoneSpeedyBlupi.wasm` | WebAssembly binary |
| `WindowsPhoneSpeedyBlupi.data` | Preloaded asset bundle |

The `.data` file is the packaged output of the `--preload-file` link options described below — a
single bundle containing every asset directory mounted into the in-browser virtual filesystem at
page-load time, before the game itself starts running.

## The Emscripten link options, read from `CMakeLists.txt`

`README.md`'s virtual filesystem table (below) is a direct restatement of the actual
`target_link_options()` call in the `EMSCRIPTEN` branch of `CMakeLists.txt`, which is worth reading
directly since it's where every one of these behaviours is actually configured:

*From `CMakeLists.txt:166-194`:*
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

Reading these one at a time: `-sALLOW_MEMORY_GROWTH=1` lets the WASM heap grow beyond its initial
allocation rather than failing on out-of-memory; `-sSTACK_SIZE=1048576` (1 MiB) and
`-sINITIAL_MEMORY=134217728` (128 MiB) set explicit stack and initial-heap sizes; `-sFORCE_FILESYSTEM=1`
ensures Emscripten's virtual filesystem layer is compiled in even if static analysis doesn't detect
filesystem calls it would otherwise strip; `-sEXPORTED_RUNTIME_METHODS=['FS','ccall','cwrap']`
exposes the `FS` filesystem API and the `ccall`/`cwrap` C-function-calling helpers to the
surrounding JavaScript (used by `cmake/web/pre.js`, below); and `-lidbfs.js` links in Emscripten's
IDBFS (IndexedDB Filesystem) backend. The four `--preload-file` entries each mount a real,
on-disk source directory (relative to `CMAKE_SOURCE_DIR`, i.e. `mobile-eggbert`'s own root) at a
matching absolute path inside the virtual filesystem — the `@` syntax is Emscripten's
`source@destination` preload mapping. `-sMIN_WEBGL_VERSION=2`/`-sMAX_WEBGL_VERSION=2` pin the build
to WebGL 2 specifically, both floor and ceiling, rather than allowing a WebGL 1 fallback.

## Virtual filesystem layout

*From `README.md:171-179`:*

| Path | Source directory | Notes |
|------|-----------------|-------|
| `/Content/backgrounds` | `Content/backgrounds/` | Read-only; preloaded |
| `/Content/icons` | `Content/icons/` | Read-only; preloaded |
| `/Content/sounds` | `Content/sounds/` | Read-only; preloaded |
| `/worlds` | `worlds/` | Read-only; preloaded |
| `/save` | IndexedDB (IDBFS) | Writable; persists `SpeedyBlupi` save file |

Four of the five mount points are read-only and populated once, at page load, from the `.data`
bundle produced by the `--preload-file` options above. The fifth, `/save`, is the only writable
mount, and is handled differently: it is not preloaded from the bundle at all, but mounted live, in
JavaScript, via the `--pre-js` script referenced in the `target_link_options()` call above.

### How `/save` actually gets mounted: `cmake/web/pre.js`

`CMakeLists.txt`'s comment attributes the IDBFS mounting logic to `StoragePaths.cpp` ("Save data is
persisted via IDBFS mounted at `/save` (see `StoragePaths.cpp`)"). No file named `StoragePaths.cpp`
exists anywhere in the `mobile-eggbert` repository as checked for this book — the save-data
read/write logic that actually runs inside the game is implemented in `Worlds.cpp`, via
`System::IO::IsolatedStorage::IsolatedStorageFile` (a `sharp-runtime`-provided C++ reimplementation
of .NET's `IsolatedStorageFile` API, consistent with the game's XNA/.NET migration history covered
in [Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)). This
book cannot confirm whether `StoragePaths.cpp` refers to a file that exists inside `sharp-runtime`
or `cna` (both out of this book's primary scope) or is simply a stale comment; readers should treat
that specific filename reference as unverified, while the *behaviour* it describes — IDBFS mounted
at `/save` — is independently confirmed by reading the actual JavaScript that does the mounting,
`cmake/web/pre.js`, referenced via `--pre-js` above:

*From `cmake/web/pre.js:1-28`:*
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
```

and the matching flush-on-unload handler:

*From `cmake/web/pre.js:30-40`:*
```javascript
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

Emscripten's IDBFS filesystem type keeps its data in an in-memory layer during normal operation;
`FS.syncfs(populate, callback)` is the explicit call that moves data between that in-memory layer
and the browser's real, persistent IndexedDB store. The `preRun` hook calls it once with
`populate=true` (load existing IndexedDB contents into memory *before* the game starts, so a
returning player's save data is available from frame one), and the `beforeunload` handler calls it
with `populate=false` (flush in-memory writes *out* to IndexedDB) as the page is closing. The file's
own `TODO` comment is worth taking at face value rather than glossing over: it explicitly flags that
IDBFS writes made *during* a session are not automatically synced to IndexedDB — only on this
`beforeunload` event — meaning a hard crash, a killed tab, or a browser that skips
`beforeunload` (some mobile browsers are unreliable about firing it) could lose save progress made
since the last sync. This is a real, currently-open gap in the Web build's persistence guarantees,
not a hypothetical one.

## Notes from `README.md`

`README.md`'s "Notes" section for the Web build covers three further points, verbatim:

*From `README.md:181-196`:*
```markdown
#### Notes

- Save data (`SpeedyBlupi`) is stored in `/save/.cna_isolated_storage/SpeedyBlupi`
  backed by the browser's IndexedDB. It is flushed to IndexedDB on every write
  and on page unload.
- Audio uses SDL_mixer; the browser may require a user gesture before audio
  starts. If no sound is heard, click the canvas once.
- CPU usage is bounded — the game uses `emscripten_set_main_loop` (backed by
  `requestAnimationFrame`) instead of a busy loop.
- **Game speed**: the Web build uses a fixed-timestep accumulator in
  `CNA/Game.cpp` to match native desktop timing. The browser calls the RAF
  callback at ~60 Hz; real inter-frame wall-clock time is measured and
  accumulated, and `Update()` fires only when one full `TargetElapsedTime`
  slice has accumulated. This ensures gameplay speed is identical to
  Linux/Windows regardless of the browser's actual RAF cadence. A 250 ms
  spike cap prevents runaway catch-up after the tab is backgrounded.
```

One factual note against the first bullet's exact wording: it states the save path is "flushed to
IndexedDB on every write and on page unload," but `pre.js` — the actual mounting/sync code read
above — only wires up a sync on `beforeunload`, plus the file's own `TODO` comment explicitly notes
that a periodic or on-every-write sync is *not yet implemented* ("Currently data is written to the
in-memory layer but may not survive a hard reload unless sync is called"). This book presents that
as an open discrepancy between `README.md`'s description and what `pre.js` currently does, rather
than resolving it in either direction — a reader relying on "every write is flushed" for data-loss
guarantees should not assume that claim is currently accurate based on `pre.js` alone.

The audio-autoplay note reflects a standard, well-known browser policy: most browsers block audio
from starting without a preceding user interaction (a click, a keypress), which is why the note
recommends clicking the canvas once if no sound is heard on load.

### The fixed-timestep accumulator, verified against `cna/Game.cpp`

The final bullet — the fixed-timestep accumulator claim — is independently verifiable, since `cna`
is available alongside `mobile-eggbert` in this book's working environment. The actual file is
`cna/src/Microsoft/Xna/Framework/Game.cpp` (not literally `CNA/Game.cpp` as `README.md`'s path
shorthand suggests, but the same underlying `Game` class implementation XNA-style code in
`mobile-eggbert` extends — see [Chapter 12](../part03-architecture/ch12-game1-state-machine.md) and
[Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md) for how `Game1` relates to it). The
Emscripten-specific main loop is guarded by `#if defined(__EMSCRIPTEN__)` and reads:

*From `cna/src/Microsoft/Xna/Framework/Game.cpp:761-806`:*
```cpp
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
    ...
}
```

and it is registered as the browser's per-frame callback exactly where `README.md` says:

*From `cna/src/Microsoft/Xna/Framework/Game.cpp:825-830`:*
```cpp
void Game::RunLoop()
{
#if defined(__EMSCRIPTEN__)
    s_emLoopState.game = this;
    s_emLoopState.gameTime = gameTime_;
    emscripten_set_main_loop(EmscriptenMainLoopCallback, 0, 1);
```

This confirms `README.md`'s claim precisely: real wall-clock elapsed time (`deltaMs`, measured via
`SDL_GetTicks()`) is capped at 250 ms per callback (exactly the "250 ms spike cap" `README.md`
describes, guarding against a burst of catch-up updates if the tab was backgrounded or the browser
otherwise stalled the RAF callback for a long stretch) before being added to a persistent
`accumulatorMs`. `Update()` is then called in a `while` loop, once per full `targetMs`
(`TargetElapsedTime`) slice accumulated — potentially zero times in a callback where too little
real time has passed, or more than once in a callback that runs after a delay — decoupling the
*rate* at which `Update()` advances game logic from the browser's own, potentially variable, RAF
firing cadence. This is the same accumulator pattern implemented for the non-Emscripten desktop
loop path elsewhere in the same file (`Game.cpp:363-393`), reused here specifically to normalize
Web timing against native desktop timing as `README.md` states. Because this touches `cna`'s own
`Game` class rather than any `mobile-eggbert`-authored code, this book's treatment of it stops here,
at "what this code path does and why it matters for the Web build's correctness" — a full
walkthrough of `cna`'s own `Game`/`GameTime` architecture belongs to `cna-bible`, not this book, per
[`CLAUDE.md`](../../CLAUDE.md).

## Backend status: Web

*From `README.md:212-213`:*
```markdown
- **Web (Emscripten)**: SDL_Renderer backend, experimental. **CANVAS** (browser HTML5 Canvas 2D,
  no GPU) is also available with `-DCNA_GRAPHICS_BACKEND=CANVAS`.
```

This matches the `EMSCRIPTEN` branch of the platform-detection logic in
[Chapter 4](ch04-build-overview.md): `SDL_RENDERER` (running on WebGL 2, per the
`-sMIN_WEBGL_VERSION=2`/`-sMAX_WEBGL_VERSION=2` link options above) is the default and, per
`README.md`, the most tested; `CANVAS` remains available as an explicit override for a GPU-free
HTML5 Canvas 2D rendering path.

## See also

- [Chapter 4: Build Overview (CMake)](ch04-build-overview.md)
- [Chapter 5: Linux Build](ch05-linux-build.md)
- [Chapter 43: GameData: Save Format](../part08-data-persistence-content/ch43-gamedata-save-format.md)
- [Chapter 53: Web Virtual Filesystem](../part10-platform-deep-dives/ch53-web-virtual-filesystem.md)
