# Chapter 4: Build Overview (CMake)

Everything about how `mobile-eggbert` gets turned into a running binary — on Linux, Windows,
the Web, or Android — is decided by a single, deliberately compact file: the top-level
`CMakeLists.txt` at the repository root. At 247 lines it is short for a file that has to steer
four very different target platforms and up to thirteen different graphics backends, and that
compactness is itself a design decision the file's own comments explain: an earlier, longer
version of this file duplicated logic that already lived in `cna`'s build system, and it kept
silently drifting out of sync with it. This chapter reads that file end to end.

## Project setup and the C++ standard

The file opens plainly:

*From `CMakeLists.txt:1-6`:*
```cmake
cmake_minimum_required(VERSION 3.21)
project(WindowsPhoneSpeedyBlupi LANGUAGES C CXX)

message(STATUS "Project: ${PROJECT_NAME}")
message(STATUS "Platform: ${CMAKE_SYSTEM_NAME}")
message(STATUS "Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
```

The CMake project name, `WindowsPhoneSpeedyBlupi`, is the same name used throughout the codebase
for the namespace (`namespace WindowsPhoneSpeedyBlupi`) and the `include/`/`src/` directory that
holds the game's own C++ sources — a naming choice that is a direct fossil of the game's Windows
Phone/XNA origin (see [Chapter 1](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md)).
The three `message(STATUS …)` lines are pure diagnostics: they print the project name, the host
CMake's `CMAKE_SYSTEM_NAME`, and the detected compiler and its version at configure time, which is
useful when a build behaves differently across machines and the first question is "which compiler
and platform did CMake actually pick."

Immediately after, a sanity check catches a specific class of user error — reusing a build
directory across toolchains:

*From `CMakeLists.txt:8-12`:*
```cmake
if (NOT WIN32 AND CMAKE_BINARY_DIR MATCHES "build-windows")
    message(WARNING "Building in 'build-windows' directory, but WIN32 is not set. "
                    "Make sure you used -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/mingw-w64.cmake "
                    "on a CLEAN build directory.")
endif()
```

This doesn't prevent the build from continuing (it's a `WARNING`, not a `FATAL_ERROR`); it exists
because CMake caches toolchain decisions in a build directory's `CMakeCache.txt`, and reusing a
directory named `build-windows` without actually cross-compiling for Windows is a classic way to
get an unexplained failure. [Chapter 6](ch06-windows-and-cross-compilation.md) covers the MinGW-w64
cross-build this check is guarding against in detail.

The language standard follows immediately:

*From `CMakeLists.txt:14-16`:*
```cmake
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
```

`mobile-eggbert` targets **C++23** — a comparatively modern standard for a project whose origin is
a decompiled 2013 C# codebase (see [Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
for that migration history). `CMAKE_CXX_STANDARD_REQUIRED ON` means the build fails outright if the
selected compiler cannot actually provide C++23, rather than silently falling back to an older
standard. `CMAKE_CXX_EXTENSIONS OFF` disables compiler-specific extensions (e.g. GNU extensions
under GCC/Clang), keeping the code within the portable standard — a sensible default for a project
that already has to compile cleanly under at least MSVC-flavoured MinGW, GCC/Clang on Linux, and
Emscripten's Clang-based toolchain.

## `CNA_SPRITE_BATCHING_ENABLED`

The next block is a single `option()`, but its comment is doing a lot of work:

*From `CMakeLists.txt:18-23`:*
```cmake
# Enable sprite-batch grouping in Pixmap: all Draw calls between BeginBatch/
# EndBatch in Game1::Draw share a single SpriteBatch Begin/End pair instead of
# one per sprite.  Reduces GL draw calls by ~50-100x.  OFF by default so that
# the original Daniel Roux per-sprite behaviour is preserved until the feature
# has been thoroughly tested.
option(CNA_SPRITE_BATCHING_ENABLED "Group all Pixmap draws into one SpriteBatch Begin/End per frame" OFF)
```

To unpack what this actually changes: `Pixmap` (`Pixmap.cpp`, the sprite-rendering layer covered in
depth in [Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)) issues one
`SpriteBatch::Begin()`/`SpriteBatch::End()` pair per sprite draw call by default — the same
behaviour the original Windows Phone/XNA code had, attributed in the comment to Daniel Roux, the
original Speedy Blupi/Epsitec SA author (see [Chapter 3](../part01-origins-and-ecosystem/ch03-license-and-provenance.md)
for provenance). Each `Begin`/`End` pair around a GPU-backed renderer implies at least one draw
call, so hundreds of individual sprites per frame becomes hundreds of draw calls — exactly the
kind of thing a modern GPU driver handles far less efficiently than a handful of large batched
draws. `Pixmap.cpp`'s own file-header comment (`Pixmap.cpp:33-38`) describes the mechanism on the
consuming side: when the macro is defined, every draw method checks an internal `batch_started_`
flag — if a caller has already opened a batch via `BeginBatch()`, the individual draw call
contributes to that outer batch instead of opening and closing its own; if not, it falls back to
the original one-`Begin`/`End`-per-sprite behaviour. `Game1::Draw` is the call site that would open
that outer batch across an entire frame's worth of `Pixmap` calls, which is where the "~50-100x
fewer draw calls" estimate in the CMake comment comes from — one `Begin`/`End` pair for potentially
50–100 sprites instead of one each.

The flag is surfaced to the compiled binary, not just to CMake:

*From `CMakeLists.txt:111-113`:*
```cmake
if(CNA_SPRITE_BATCHING_ENABLED)
    target_compile_definitions(${_game_target} PRIVATE CNA_SPRITE_BATCHING_ENABLED)
endif()
```

so `Pixmap.cpp`'s `#if defined(CNA_SPRITE_BATCHING_ENABLED)` (see the file-header comment quoted
above) is a genuine preprocessor conditional — the option isn't just a CMake-level annotation, it
changes what code is actually compiled into the binary. It defaults to `OFF`, which is the reason
the option's own description reads as deliberately conservative: this is an optimization the
project has built and wired up, but has not yet turned on by default, "until the feature has been
thoroughly tested." A reader building from source who wants to experiment with the batched path
turns it on with `-DCNA_SPRITE_BATCHING_ENABLED=ON` at configure time.

## Graphics backend selection

This is the largest and most heavily commented section of the file, and it encodes a real piece of
the project's own build-system history.

### The two competing input paths, and why the string wins

*From `CMakeLists.txt:25-45`:*
```cmake
# -----------------------------------------------------------------------------
# Graphics backend selection.
# -----------------------------------------------------------------------------
# CNA_GRAPHICS_BACKEND is the only thing that needs setting -- it's a single
# string, and cna's own CMakeLists.txt keys every downstream decision
# (which backend sources to compile, which target to create, which sibling
# deps to pull in) off it directly.
#
# cna also exposes a parallel set of CNA_BACKEND_* boolean options,
# but those are an *optional, alternative* input path: they all default to
# OFF, and cna only consults them if one is explicitly switched ON,
# in which case it derives CNA_GRAPHICS_BACKEND from the boolean instead. A
# consumer that just sets the string never needs to touch them.
#
# This file used to force all of CNA_BACKEND_*'s 5-and-growing flags itself
# (~75 lines of if/elseif) -- pure redundancy with the string above, and it
# hardcoded a fixed backend list that silently fell out of sync every time
# cna added one (HEADLESS had already been bolted on as a partial
# exception; SOFTWARE and D3D11, which cna also defines, were never
# added at all). Replaced with: set the string, validate it against a live
# list, done.
```

Two things are worth being precise about here, since the comment is describing `cna`'s behaviour
(marginal to this book's scope, per [`CLAUDE.md`](../../CLAUDE.md)) purely in terms of what
`mobile-eggbert` needs to know about it:

1. **`CNA_GRAPHICS_BACKEND`** is a single CMake cache string (e.g. `"SDL_RENDERER"`,
   `"VULKAN"`, `"D3D11"`) that `cna`'s own build logic reads directly to decide which backend's
   sources to compile and which backend static-library target to produce. This is the *only*
   variable `mobile-eggbert`'s own `CMakeLists.txt` needs to set.
2. **`CNA_BACKEND_*`** (e.g. `CNA_BACKEND_SDL_RENDERER`, `CNA_BACKEND_EASY_GL`) is a *parallel*,
   older-style set of per-backend boolean `option()`s that `cna` still supports for backward
   compatibility. They all default `OFF`; `cna` only looks at them if the caller has explicitly
   turned one on, in which case `cna` derives the equivalent `CNA_GRAPHICS_BACKEND` string from
   whichever boolean was set. Notably, `mobile-eggbert`'s own `README.md` still documents the
   Linux and Windows native-build commands using this older boolean form (`-DCNA_BACKEND_SDL_RENDERER=ON
   -DCNA_BACKEND_EASY_GL=OFF -DCNA_BACKEND_BGFX=OFF`, see [Chapter 5](ch05-linux-build.md)) even
   though the `CMakeLists.txt` itself has fully moved to the string form — both paths are live and
   both work, but they are not the same code path internally, and a reader who wants the
   authoritative, currently-maintained mechanism should prefer setting `CNA_GRAPHICS_BACKEND`
   directly.

The comment also names a concrete bug the old approach had: this file used to hardcode its own
~75-line `if/elseif` chain forcing every `CNA_BACKEND_*` boolean, duplicating a backend list that
lived, redundantly, in two places at once. That duplicated list had already fallen out of sync with
`cna`'s real backend set — `HEADLESS` had been added as a partial, bolted-on exception, while
`SOFTWARE` and `D3D11` (both real `cna` backends) were missing from it entirely. The fix recorded
here is architectural: stop mirroring `cna`'s backend list in this file at all. Set the one string
`cna` actually keys off, validate it against a list this file maintains for its own error-checking
purposes, and let `cna` do the rest.

### The full backend list

*From `CMakeLists.txt:47-51`:*
```cmake
# D3D9 (Windows-only, same as D3D11/D3D12) and SDL_GPU (portable, needs
# libshaderc for its runtime ShaderEffect GLSL->SPIR-V compile -- see
# cna/plan_sdlgpu.md SDLGPU-42/43) are cna's two newest backends and were
# missing from this list.
set(MOBILE_EGGBERT_BACKENDS SDL_RENDERER EASYGL BGFX VULKAN WEBGPU HEADLESS SOFTWARE D3D11 D3D12 CANVAS ASCII DX3 D3D9 SDL_GPU)
```

`MOBILE_EGGBERT_BACKENDS` is the definitive list of backend names this build accepts — thirteen
entries, spanning desktop GPU APIs, a software rasterizer, and non-visual/experimental modes:

| Backend | Nature |
|---|---|
| `SDL_RENDERER` | SDL3's own 2D renderer (GPU-accelerated, cross-platform); the default everywhere |
| `EASYGL` | A lightweight OpenGL-based backend |
| `BGFX` | The cross-platform `bgfx` rendering library |
| `VULKAN` | Native Vulkan |
| `WEBGPU` | WebGPU (experimental) |
| `HEADLESS` | Touches no GPU/window at all — for driving game logic under CI without a display |
| `SOFTWARE` | A CPU software rasterizer |
| `D3D11` | Direct3D 11 — Windows/Wine/Proton, see [Chapter 7](ch07-direct3d-wine-proton.md) |
| `D3D12` | Direct3D 12 — Windows/Proton-only, see [Chapter 7](ch07-direct3d-wine-proton.md) |
| `D3D9` | Direct3D 9 — Windows-only, same family as D3D11/D3D12 |
| `CANVAS` | Browser HTML5 Canvas 2D, GPU-free (Emscripten) |
| `ASCII` | An SDL-windowed glyph-grid decorator around `SDL_RENDERER` — not a real terminal/TTY backend |
| `DX3` | A narrow DirectX 3 (DirectDraw) subset reimplemented on SDL3 via the sibling `../free-direct` repo — portable, unlike `D3D11`/`D3D12`/`D3D9` |
| `SDL_GPU` | Portable but needs `libshaderc` for its runtime ShaderEffect GLSL→SPIR-V compile |

Two of these (`D3D9`, `SDL_GPU`) are called out by the comment as the two backends most recently
added to `cna` and to this list — a direct trace of the file's own maintenance history. The comment
also flags one further backend that exists in `cna` but is deliberately **not** in this list yet:
`SDL_GPU`'s sibling situation is `SDL_GPU`'s own dependency requirement (`libshaderc`), while a
separate note later in the file (`CMakeLists.txt:216-218`, echoed in `README.md`) explains that
`cna`'s `SDL_GPU` backend itself only exists on `cna`'s in-progress `feature/sdlgpu` branch and
isn't merged into `develop` yet — so a consumer tracking `cna`'s `develop` branch (which
`mobile-eggbert` does, via `CNA_GRAPHICS_SOURCE_DIR`, described below) won't actually have it
available until that branch lands, even though the name is already present in
`MOBILE_EGGBERT_BACKENDS`.

### Platform-driven defaults

Backend selection branches on the target platform, and each branch's comment explains a real
constraint rather than an arbitrary choice:

*From `CMakeLists.txt:53-77`:*
```cmake
if(ANDROID)
    # Only SDL_RENDERER is supported (no desktop GL context the same way;
    # SDL_RENDERER runs on GLES under the hood).
    set(CNA_GRAPHICS_BACKEND "SDL_RENDERER" CACHE STRING "Selected CNA backend" FORCE)
elseif(EMSCRIPTEN)
    # SDL_RENDERER (runs on WebGL under the hood) is the default and most
    # tested; CANVAS (browser HTML5 Canvas 2D, GPU-free) can be selected
    # explicitly with -DCNA_GRAPHICS_BACKEND=CANVAS -- see cna/plan_canvas.md.
    set(CNA_GRAPHICS_BACKEND "SDL_RENDERER" CACHE STRING "Selected CNA backend")
else()
    # Desktop: choose one backend, default SDL_RENDERER. Override with
    # -DCNA_GRAPHICS_BACKEND=<backend>, e.g. -DCNA_GRAPHICS_BACKEND=VULKAN.
    # WEBGPU is experimental (see cna/plan_webgpu.md). HEADLESS
    # touches no GPU/window at all (see cna/plan_headless.md) -- for
    # driving this game's own logic under CI without a display server, not
    # for visible rendering. ASCII is an SDL-windowed glyph-grid decorator,
    # not a real terminal/TTY backend (see cna/plan_ascii.md). DX3 reimplements
    # a narrow DirectX 3 (DirectDraw) subset on top of SDL3 via the sibling
    # ../free-direct repo -- portable, not Windows/Wine-only like D3D11/D3D12
    # (see cna/plan_dx3.md). D3D9 is Windows/Wine-only like D3D11/D3D12 (see
    # cna/plan_dx9.md). SDL_GPU is portable but needs libshaderc installed
    # (libshaderc1 or libshaderc-dev) for its runtime ShaderEffect GLSL compile
    # (see cna/plan_sdlgpu.md).
    set(CNA_GRAPHICS_BACKEND "SDL_RENDERER" CACHE STRING "Selected CNA backend")
endif()
set_property(CACHE CNA_GRAPHICS_BACKEND PROPERTY STRINGS ${MOBILE_EGGBERT_BACKENDS})
```

The three branches:

- **`ANDROID`**: forced to `SDL_RENDERER` with `FORCE`, meaning even a `-DCNA_GRAPHICS_BACKEND=...`
  passed on the command line is overridden — there is no alternative on Android in this codebase,
  because (per the comment) there is no equivalent desktop-style GL context path; `SDL_RENDERER`
  runs on GLES under the hood on that platform. See [Chapter 9](ch09-android-build.md).
- **`EMSCRIPTEN`**: also defaults to `SDL_RENDERER` (running on WebGL), but *without* `FORCE` — a
  Web build can still override it, most usefully to `CANVAS` for a GPU-free HTML5 Canvas 2D path.
  See [Chapter 8](ch08-web-emscripten-build.md).
- **Desktop (the `else()` branch)**: also defaults to `SDL_RENDERER`, but every one of the other
  eleven backends is a legitimate, documented override. This is the branch whose comment carries
  almost the entire backend catalog's caveats — `WEBGPU` is experimental, `HEADLESS` is for
  CI/logic-only use, `ASCII` is not a real terminal backend despite its name, `DX3` is portable via
  `../free-direct` unlike the true Direct3D backends, `D3D9` is Windows/Wine-only like `D3D11`/
  `D3D12`, and `SDL_GPU` needs `libshaderc` installed. [Chapter 7](ch07-direct3d-wine-proton.md)
  covers the two Direct3D backends' Wine/Proton story in depth.

After the branch, `set_property(CACHE CNA_GRAPHICS_BACKEND PROPERTY STRINGS ${MOBILE_EGGBERT_BACKENDS})`
registers the valid-value list with CMake's cache system, which is what lets GUI tools like
`ccmake`/`cmake-gui` present `CNA_GRAPHICS_BACKEND` as a dropdown instead of a free-text field.

### Validation against a live list

*From `CMakeLists.txt:80-84`:*
```cmake
if(NOT CNA_GRAPHICS_BACKEND IN_LIST MOBILE_EGGBERT_BACKENDS)
    message(FATAL_ERROR
        "mobile-eggbert: unknown CNA_GRAPHICS_BACKEND='${CNA_GRAPHICS_BACKEND}'. "
        "Choose one of: ${MOBILE_EGGBERT_BACKENDS}.")
endif()
```

This is the entire payoff of maintaining `MOBILE_EGGBERT_BACKENDS` at all: a typo in
`-DCNA_GRAPHICS_BACKEND=SDL_RENDER` (missing the trailing `ER`) fails immediately, at configure
time, with a message that lists every accepted spelling — rather than failing much later and much
more confusingly inside `cna`'s own backend-dispatch logic, or silently falling through to whatever
`cna`'s own default happens to be.

## Locating the sibling `cna` checkout

*From `CMakeLists.txt:86-88`:*
```cmake
set(CNA_GRAPHICS_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../cna")
add_subdirectory("${CNA_GRAPHICS_SOURCE_DIR}" CNA)
include_directories("${CNA_GRAPHICS_SOURCE_DIR}/include" CNA)
```

`mobile-eggbert` does not vendor `cna` as a Git submodule of its own (there is no `.gitmodules`
file at the repository root); instead it expects `cna` to be checked out as a **sibling
directory** — `../cna` relative to `mobile-eggbert`'s own root — and pulls it in with
`add_subdirectory()`, which folds `cna`'s entire CMake project (including its own targets, its own
`option()`s, and the `CNA_BACKEND_*`/`CNA_GRAPHICS_BACKEND` machinery discussed above) directly into
this build. `include_directories("${CNA_GRAPHICS_SOURCE_DIR}/include" CNA)` then adds `cna`'s
public headers to every target's include path so that `#include "Microsoft/Xna/Framework/Game.hpp"`
style includes (see [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md)) resolve without
per-target configuration. In this repository's own working setup, the two checkouts live at
`/workspace/mobile-eggbert` and `/workspace/cna` — exactly the sibling layout this line expects.
It is worth noting that `cna` itself vendors its third-party dependencies (SDL3, SDL_image,
SDL_mixer, GoogleTest) as *its own* Git submodules under `cna/third_party/` and `cna/vendor/` —
those are one level further down and are `cna`'s concern, not `mobile-eggbert`'s.

## The main target: sources, name, and per-platform shape

*From `CMakeLists.txt:90-107`:*
```cmake
file(GLOB_RECURSE SOURCES "src/*.cpp")

# On Android the "executable" is a shared library loaded by SDLActivity.
# SDL's Java glue expects the native library to be named "libmain.so".
# We use a CMake variable so all subsequent target_* calls use the right name.
if(ANDROID)
    set(_game_target main)
    add_library(${_game_target} SHARED ${SOURCES}
            include/WindowsPhoneSpeedyBlupi/def/Direction.hpp
            "${CNA_GRAPHICS_SOURCE_DIR}/include/CNA/Misc.hpp")
else()
    set(_game_target WindowsPhoneSpeedyBlupi)
    add_executable(${_game_target} ${SOURCES})
endif()
# On Emscripten the output is HTML+JS+WASM; set the suffix accordingly.
if(EMSCRIPTEN)
    set_target_properties(${_game_target} PROPERTIES SUFFIX ".html")
endif()

target_include_directories(${_game_target} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
```

`file(GLOB_RECURSE SOURCES "src/*.cpp")` picks up every `.cpp` file under `src/` — at the time of
writing this is the sixteen files listed in `PLAN.md`'s source-size survey
(`Decor.cpp`, `Game1.cpp`, `GameData.cpp`, `Helper.cpp`, `InputPad.cpp`, `Jauge.cpp`, `Misc.cpp`,
`MyResource.cpp`, `Pixmap.cpp`, `Program.cpp`, `Slider.cpp`, `Sound.cpp`, `Tables.cpp`, `Text.cpp`,
`TinyRect.cpp`, `Worlds.cpp`), all under `src/WindowsPhoneSpeedyBlupi/`. A glob means a new `.cpp`
file dropped into `src/` is picked up automatically on the next fresh CMake configure — with the
usual glob caveat that CMake does not automatically re-run configure when files are merely added,
so a stale build directory after adding a new source file may need an explicit re-configure.

The target itself is genuinely different per platform, which is the reason for the `_game_target`
indirection variable:

- **Android**: the "executable" is actually a `SHARED` library named `main` (i.e. it links to
  `libmain.so`), because SDL's Java-side glue (`SDLActivity`) expects to `dlopen()` a native library
  under exactly that name. Two extra headers — `include/WindowsPhoneSpeedyBlupi/def/Direction.hpp`
  and `cna`'s own `include/CNA/Misc.hpp` — are listed explicitly alongside the globbed sources; this
  is a common CMake pattern to make header-only files show up inside an IDE's project tree even
  though they don't need to be compiled as separate translation units. See [Chapter 9](ch09-android-build.md).
- **Everything else**: an ordinary `add_executable()` named `WindowsPhoneSpeedyBlupi` — the same
  name as the CMake project itself.
- **Emscripten**, additionally, gets its output suffix forced to `.html`, since Emscripten's linker
  driver treats the target's "executable" as the entry point for generating a matching `.js` and
  `.wasm` alongside an HTML shell page. See [Chapter 8](ch08-web-emscripten-build.md).

`target_include_directories(${_game_target} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)` adds this
project's own `include/WindowsPhoneSpeedyBlupi/` headers to the target — separate from the
`include_directories()` call earlier that added `cna`'s headers globally.

## SDL3 packages and the linker-group workaround

Because `cna` builds SDL3 once into its own prebuilt root, `mobile-eggbert` must call
`find_package()` again in its own scope to make the resulting imported targets visible:

*From `CMakeLists.txt:115-120`:*
```cmake
# CNA builds SDL3 once into its own prebuilt root and sets SDL3_DIR / SDL3_image_DIR /
# SDL3_mixer_DIR in the CMake cache.  SDL IMPORTED targets are directory-scoped, so we
# must call find_package() here to make SDL3::SDL3 visible in this project's scope.
find_package(SDL3       REQUIRED CONFIG)
find_package(SDL3_image REQUIRED CONFIG)
find_package(SDL3_mixer REQUIRED CONFIG)
```

This is a genuine CMake wrinkle, not a redundant call: CMake `IMPORTED` targets created by
`find_package()` inside a subdirectory (`cna`, brought in via `add_subdirectory()` above) are
scoped to that subdirectory and its children by default. Since `cna`'s own `CMakeLists.txt` already
locates and configures SDL3 and records the result (`SDL3_DIR` etc.) in the shared CMake cache,
`mobile-eggbert`'s own `find_package()` calls here are cheap — they don't rebuild SDL3, they just
re-resolve the already-cached package config into `SDL3::SDL3`/`SDL3_image::SDL3_image`/
`SDL3_mixer::SDL3_mixer` imported targets usable directly by this file's own `target_link_libraries()`
calls.

The link-library selection itself branches four ways, and one branch documents another real fixed
bug:

*From `CMakeLists.txt:122-156`:*
```cmake
# CNA and the selected graphics backend static library have circular
# symbol references on Linux (backend uses Color/Rectangle/Matrix from CNA,
# CNA uses backend interfaces). Wrap them in a linker group so GNU ld
# resolves both without depending on link order.
# Note: --start-group/--end-group are not available on Emscripten's linker
# or on Android (lld does not need it and warns).
if(EMSCRIPTEN)
    target_link_libraries(${_game_target} PRIVATE CNA CNA_GamerServices SDL3::SDL3-static)
elseif(ANDROID)
    # Android uses lld which resolves circular static-lib references without
    # --start-group. On Android the executable is actually a shared library
    # (libmain.so) loaded by SDLActivity; SDL3 is linked statically.
    target_link_libraries(${_game_target} PRIVATE CNA SDL3::SDL3 android log)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang" AND NOT WIN32)
    # cna names every backend target
    # cna_backend_graphics_<backend, lowercased> -- this used to be a
    # hardcoded if/elseif chain of 5 backend names (in existence-check order,
    # not selection order) that had silently fallen behind cna's own
    # backend list: HEADLESS was missing from it entirely, so selecting
    # HEADLESS here fell through to the plain (non-grouped) link below,
    # skipping the --start-group/--end-group circular-symbol workaround this
    # branch exists for. Deriving the name directly from CNA_GRAPHICS_BACKEND
    # fixes that and covers every future backend automatically.
    string(TOLOWER "${CNA_GRAPHICS_BACKEND}" _cna_backend_lower)
    set(_cna_backend_target "cna_backend_graphics_${_cna_backend_lower}")
    if(TARGET ${_cna_backend_target})
        target_link_libraries(${_game_target} PRIVATE
            -Wl,--start-group CNA CNA_GamerServices ${_cna_backend_target} -Wl,--end-group
            SDL3::SDL3)
    else()
        target_link_libraries(${_game_target} PRIVATE CNA CNA_GamerServices SDL3::SDL3)
    endif()
else()
    target_link_libraries(${_game_target} PRIVATE CNA CNA_GamerServices SDL3::SDL3)
endif()

if(TARGET SDL3::SDL3main)
    target_link_libraries(${_game_target} PRIVATE SDL3::SDL3main)
endif()
```

This same "derive the target name from the live selection string instead of hardcoding a list"
pattern reappears here, for exactly the same reason as the earlier backend-list fix: an older
version of this branch enumerated five known backend names by hand, so choosing `HEADLESS` (which
wasn't in that hand-written list) silently skipped the `--start-group`/`--end-group` linker-group
wrapping this whole branch exists to provide — meaning a circular-reference link failure would only
show up for backends the original author hadn't thought to list. Computing
`cna_backend_graphics_<backend-lowercased>` directly from `CNA_GRAPHICS_BACKEND` and checking
`if(TARGET ...)` fixes that structurally: it works for every backend `cna` currently defines and
every one it adds in the future, without this file needing another edit.

The linker group itself (`-Wl,--start-group ... -Wl,--end-group`) is a standard GNU `ld` mechanism
for resolving mutually-referencing static libraries — here, `CNA` calling into backend interfaces
and the backend static library calling back into `CNA`'s own `Color`/`Rectangle`/`Matrix` types —
without the fragility of getting link order exactly right. It's explicitly unavailable/unnecessary
on two platforms: Emscripten's linker doesn't support the flag at all, and Android's `lld` resolves
circular static-library references without needing it (and would warn if given the flag anyway) —
which is why those two platforms get their own simpler `target_link_libraries()` branches above
the `GNU|Clang AND NOT WIN32` branch that needs the group.

## Content copying and platform-specific link options

The final third of the file handles getting game assets next to the built binary and applying a
handful of platform-specific post-build steps.

For **Android**, no content copy step is needed — assets are packaged directly into the APK (see
[Chapter 9](ch09-android-build.md)). For **Emscripten**, assets are preloaded into the Emscripten
virtual filesystem via `--preload-file` link options, covered in full in
[Chapter 8](ch08-web-emscripten-build.md). For **native desktop** builds:

*From `CMakeLists.txt:196-221`:*
```cmake
# Native desktop: copy Content directory next to the executable.
set(MOBILE_EGGBERT_CONTENT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/Content")
set(MOBILE_EGGBERT_WORLDS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/worlds")
if(EXISTS "${MOBILE_EGGBERT_CONTENT_DIR}")
    add_custom_command(TARGET ${_game_target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${MOBILE_EGGBERT_CONTENT_DIR}"
            "$<TARGET_FILE_DIR:${_game_target}>/Content"
            COMMENT "Copying game content next to executable")
endif()
if(CNA_GRAPHICS_BACKEND STREQUAL "WEBGPU" AND CNA_WEBGPU_RUNTIME_LIBRARY)
    add_custom_command(TARGET ${_game_target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${CNA_WEBGPU_RUNTIME_LIBRARY}" "$<TARGET_FILE_DIR:${_game_target}>"
            COMMENT "Copying wgpu-native runtime next to game executable")
    if(UNIX AND NOT APPLE)
        set_property(TARGET ${_game_target} APPEND PROPERTY BUILD_RPATH "$ORIGIN")
    endif()
endif()
if(EXISTS "${MOBILE_EGGBERT_WORLDS_DIR}")
    add_custom_command(TARGET ${_game_target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${MOBILE_EGGBERT_WORLDS_DIR}"
            "$<TARGET_FILE_DIR:${_game_target}>/worlds"
            COMMENT "Copying game worlds next to executable")
endif()
```

Both `Content/` (icons, backgrounds, sounds) and `worlds/` (level files) are copied next to the
built executable as `POST_BUILD` steps, guarded by `EXISTS` checks so a partial checkout doesn't
fail the build outright. There's also a `WEBGPU`-specific case: if `CNA_WEBGPU_RUNTIME_LIBRARY` is
set (pointing at the external `wgpu-native` shared library `cna`'s `WEBGPU` backend depends on),
it's copied alongside the executable too, and on Unix (excluding macOS) the executable's
`BUILD_RPATH` gets `$ORIGIN` appended so the dynamic loader finds that runtime library in the same
directory at launch instead of requiring it to be installed system-wide.

Finally, two more platform-conditional blocks:

*From `CMakeLists.txt:224-234`:*
```cmake
if(WIN32)
    cna_copy_sdl_runtime(${_game_target})
endif()

if(MINGW)
    # Statically link the MinGW GCC and C++ runtime so the exe runs outside
    # CLion/MSYS2 without needing libgcc_s_seh-1.dll / libstdc++-6.dll.
    target_link_options(${_game_target} PRIVATE -static-libgcc -static-libstdc++)
    # libwinpthread-1.dll cannot be statically linked this way; copy it instead.
    cna_copy_mingw_runtime(${_game_target})
endif()
```

`cna_copy_sdl_runtime()` and `cna_copy_mingw_runtime()` are helper CMake functions defined inside
`cna` (in `cna/cmake/ThirdPartySDL.cmake`) — brought into scope by the earlier
`add_subdirectory("${CNA_GRAPHICS_SOURCE_DIR}" CNA)` call — that copy the SDL3 runtime DLLs and
the MinGW `libwinpthread-1.dll` next to the built executable respectively, so a Windows build
produced with the MinGW toolchain can run standalone outside the build/IDE environment. This is
covered in operational detail in [Chapter 6](ch06-windows-and-cross-compilation.md).

The file closes with an optional Doxygen documentation target, gated on `find_package(Doxygen)`
succeeding — unrelated to the game's runtime build and out of scope for this chapter (see
[Chapter 57](../part11-history-and-practice/ch57-doxygen-methodology.md)).

## See also

- [Chapter 5: Linux Build](ch05-linux-build.md)
- [Chapter 6: Windows and Cross-Compilation](ch06-windows-and-cross-compilation.md)
- [Chapter 7: Direct3D via Wine/Proton](ch07-direct3d-wine-proton.md)
- [Chapter 8: Web/Emscripten Build](ch08-web-emscripten-build.md)
- [Chapter 9: Android Build](ch09-android-build.md)
- [Chapter 28: Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)
- [Chapter 14: The XNA API via CNA](../part03-architecture/ch14-xna-api-via-cna.md)
