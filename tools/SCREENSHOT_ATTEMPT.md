# Screenshot capture attempt — 2026-07-28

## Outcome: SUCCESS. Two real, actually-rendered screenshots captured.

- `book/images/screenshot-title-menu.png` — the real title/player-select screen
  (Eggbert character, Player A/B/C slots, Setup gear, Play button).
- `book/images/screenshot-gameplay-level1.png` — real gameplay, mission 1 (Eggbert
  standing in a corridor next to a level gate labelled "L", collectible spheres
  tiling the rest of the frame, 3 lives shown at the bottom).

Both are genuine `Texture2D::SaveAsPng` dumps of the game's own back buffer,
captured from an actually-built, actually-running copy of `WindowsPhoneSpeedyBlupi`
using CNA's **`SOFTWARE`** graphics backend (a pure CPU rasterizer — no `DISPLAY`,
no `Xvfb`, no GPU of any kind was needed for this path). Both are 800×480 RGBA
PNGs, matching the game's native resolution, with thousands of distinct colors —
not blank/black frames.

This means the harder `Xvfb` + Mesa `llvmpipe` fallback (`SDL_RENDERER`/`EASYGL`)
documented in `cna-bible`'s README was **not needed** — `SOFTWARE` turned out to
render this game's real `SpriteBatch`-based 2D content (via `Pixmap`) just fine,
which was flagged as an open question in the task brief (`cna-bible`'s own
`SOFTWARE` demo only exercised raw 3D `VertexBuffer` draws, not `SpriteBatch`).
That open question is now resolved, at least for this game's usage pattern: no
`RenderTarget2D`-as-source-texture draw (the one specific gap `cna-bible` found
in the `SOFTWARE` backend) appears anywhere in mobile-eggbert's normal menu/level-1
rendering path, so it was never triggered.

## What was tried, in order

### 1. Clone `cna` as a sibling of `mobile-eggbert`

```bash
cd /workspace
git clone --depth 1 https://github.com/openeggbert/cna.git
cd cna
git submodule update --init   # fetches third_party/SDL, SDL_image, SDL_mixer, vendor/googletest
```

Both completed without incident (a few minutes each through the proxy).

### 2. Install apt packages

```bash
apt-get update -qq
apt-get install -y -qq libxcursor-dev libxi-dev libxinerama-dev libxrandr-dev libxss-dev \
  libxext-dev libx11-dev libxtst-dev libxkbcommon-dev libwayland-dev wayland-protocols \
  libdecor-0-dev libdbus-1-dev libudev-dev libgbm-dev \
  libavcodec-dev libavformat-dev libavutil-dev libswresample-dev xvfb libgl1-mesa-dri
```

Succeeded (two unrelated PPA `403 Forbidden` warnings from the proxy for
`deadsnakes`/`ondrej` PPAs the container doesn't need; safe to ignore).

### 3. First configure attempt failed: missing `sharp-runtime` sibling

```bash
cd /workspace/mobile-eggbert
cmake -S . -B build-software -DCNA_GRAPHICS_BACKEND=SOFTWARE -DCMAKE_BUILD_TYPE=Release
```

Exact error:

```
CMake Error at /workspace/cna/CMakeLists.txt:76 (message):
  CNA: Missing sibling repository 'sharp-runtime' at
  /workspace/cna/../sharp-runtime -- this is a separate git checkout expected
  next to this repo's own directory, not a git submodule (git submodule
  update --init will not fetch it).  Fix: cd /workspace/cna/..  && git clone
  https://github.com/openeggbert/sharp-runtime.git
```

This sibling dependency was **not mentioned** in the task brief or in
`cna-bible`'s README (whose small demos evidently didn't need it, or it was
already present in that session's environment). Fixed exactly as the CMake
error message says:

```bash
cd /workspace
git clone --depth 1 https://github.com/openeggbert/sharp-runtime.git
```

### 4. Re-ran configure — succeeded cleanly, no other missing pieces

```bash
cd /workspace/mobile-eggbert
rm -rf build-software
cmake -S . -B build-software -DCNA_GRAPHICS_BACKEND=SOFTWARE -DCMAKE_BUILD_TYPE=Release
```

No `contentreader-stopgap` patch was needed — `cna-bible`'s README already noted
that gap was fixed upstream, and this checkout (branch `develop`,
commit `ac3aaae`) confirmed that.

### 5. Built the actual game target

```bash
cmake --build build-software --target WindowsPhoneSpeedyBlupi -j4
```

Built end-to-end on the **first try**, no source changes needed — CNA's own
static library, `CNA_GamerServices`, and all of mobile-eggbert's own `.cpp`
files (`Game1.cpp`, `Decor.cpp`, `Pixmap.cpp`, `Tables.cpp`, etc.) compiled and
linked cleanly against the `SOFTWARE` backend. Produced
`build-software/WindowsPhoneSpeedyBlupi`, a normal dynamically-linked ELF
binary, with `Content/` and `worlds/` copied next to it by the build's own
post-build copy step.

### 6. Screenshot hook: small, isolated patch to `Game1.cpp`

Mobile-eggbert has no built-in screenshot command, so a small hook was added
to `Game1::Draw()`, entirely gated behind a `MEB_SCREENSHOT_DIR` environment
variable (a no-op / dead branch unless that variable is set — zero effect on
normal builds/runs). Full diff preserved at
`tools/screenshot-capture.patch` (reproducible via `git apply` against
`/workspace/mobile-eggbert` at commit `07e0a67`). Summary of what it does,
once per frame inside the existing `Draw()` method, after the real
`Game::Draw(gameTime)` call that presents the frame:

1. Once `phase == Def::Phase::Init` (the real main-menu phase) and a few
   frames have passed, dumps the back buffer to `screenshot-title-menu.png`
   via the same `GetBackBufferData` → `Texture2D::CreateFromPixels` →
   `SaveAsPng` sequence CNA's own `examples/common/ScreenshotEXT.hpp` uses
   (reimplemented inline in the patch rather than including that header, to
   avoid touching mobile-eggbert's own include paths/CMakeLists for a
   temporary hook).
2. Immediately after, calls `SetPhase(Def::Phase::Play, 1)` — **the exact same
   call** the real `InitPlay` button handler makes in `Update()`
   (`case Def::ButtonGlyph::InitPlay: SetPhase(Def::Phase::Play, 1);`). This
   is not a shortcut around the game's logic: it goes through the same
   animated-fade / `missionToStart1` → `missionToStart2` → `StartMission()`
   state machine a real button press would, as documented in `Game1.cpp`'s
   own phase-transition-graph header comment.
3. Once `phase` has actually become `Def::Phase::Play` (confirming the fade
   and mission-start machinery really ran) and ~30 more frames have rendered,
   dumps the back buffer again to `screenshot-gameplay.png`.
4. Calls `std::exit(0)` to end the process cleanly once both shots are saved.

No gameplay code, rendering code, or CMake files were changed — only this one
temporary, clearly-commented block appended to the end of the existing
`Game1::Draw()` body, plus three new `#include` lines at the top of the file.

### 7. First run attempt failed: no audio device in the container

```bash
MEB_SCREENSHOT_DIR=/tmp/.../shots env -u DISPLAY -u WAYLAND_DISPLAY \
  timeout 60 ./build-software/WindowsPhoneSpeedyBlupi
```

```
[ERROR][APPLICATION] SpeedyBlupi: fatal exception in main: MIX_CreateMixerDevice failed: No available audio device
```

Not a rendering issue — SDL3's audio subsystem has no backend in this headless
container. Fixed with SDL's built-in dummy audio driver, no code/patch needed:

```bash
SDL_AUDIODRIVER=dummy MEB_SCREENSHOT_DIR=/tmp/.../shots \
  env -u DISPLAY -u WAYLAND_DISPLAY timeout 60 ./build-software/WindowsPhoneSpeedyBlupi
```

### 8. Success

Exit code 0. Two PNGs appeared in the target directory within well under a
second of wall-clock time:

```
-rw-r--r-- 297827 screenshot-title-menu.png   (800x480 RGBA)
-rw-r--r--  66006 screenshot-gameplay.png     (800x480 RGBA)
```

Visually confirmed (viewed both PNGs directly): the title screen shows the
real Eggbert mascot artwork, the Player A/B/C save-slot panel with real
gate/Blupi counters, a Setup gear icon, and a Play button. The gameplay shot
shows Eggbert standing in a corridor of mission 1, a level-gate icon labelled
"L", background machinery art, and the tiled collectible-sphere pattern that
fills unbuilt/background tiles — unmistakably real rendered game content, not
a blank or garbled frame.

## Environment notes for reproduction

- `/workspace/cna` (branch `develop`, commit `ac3aaae` at the time of this
  attempt) and `/workspace/sharp-runtime` (commit `b797928`) must both exist
  as siblings of `/workspace/mobile-eggbert` — `sharp-runtime` is fetched as a
  plain `git clone`, **not** via `cna`'s own submodules.
- `SDL_AUDIODRIVER=dummy` is required in any container with no real/virtual
  audio device — otherwise the game's own `main()` catches
  `MIX_CreateMixerDevice failed` and exits with code 1 before any rendering
  happens. This is unrelated to the graphics backend.
- The `Xvfb`/`SDL_RENDERER`/`EASYGL` path from `cna-bible`'s README was not
  attempted for mobile-eggbert since `SOFTWARE` worked on the first real run —
  no need to fall back.

## Files touched by this session

- `/home/user/mobile-eggbert-bible/book/images/screenshot-title-menu.png` (new)
- `/home/user/mobile-eggbert-bible/book/images/screenshot-gameplay-level1.png` (new)
- `/home/user/mobile-eggbert-bible/tools/screenshot-capture.patch` (new — the
  exact `Game1.cpp` diff, reproducible against `/workspace/mobile-eggbert`)
- `/workspace/mobile-eggbert/src/WindowsPhoneSpeedyBlupi/Game1.cpp` — modified
  in the read-only-by-convention `/workspace/mobile-eggbert` checkout (per the
  task brief, this is documented here and via the patch file rather than
  committed anywhere in that repo).
