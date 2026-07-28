# Chapter 5: Linux Build

Linux is the primary development platform for `mobile-eggbert`, and its build is the shortest of
the platform-specific paths documented in this book: no cross-compiler, no toolchain file, no
emulator or browser layer between the build and the running game. This chapter covers what
`README.md` documents for the native Linux build and cross-checks it against the actual CMake
logic read in [Chapter 4](ch04-build-overview.md).

## Prerequisites

`mobile-eggbert`'s own documentation does not enumerate a Linux package list in `README.md` beyond
what the CMake configure step itself will demand: a C++23-capable compiler (GCC or Clang), CMake
3.21 or newer (the `cmake_minimum_required` floor set at `CMakeLists.txt:1`), and the sibling `cna`
checkout with its own dependencies satisfied (SDL3, SDL3_image, SDL3_mixer, built by `cna`'s own
CMake project and consumed by `mobile-eggbert` via `find_package()` — see
[Chapter 4](ch04-build-overview.md)'s section on the SDL3 packages and linker-group workaround).
Since `cna` builds SDL3 from source into its own prebuilt root rather than requiring a
system-installed `libsdl3-dev`, most of the low-level dependency management is `cna`'s concern, not
something a Linux build of `mobile-eggbert` needs to configure directly.

## Repository layout: checkout and sibling `cna`

As established in [Chapter 4](ch04-build-overview.md), `mobile-eggbert`'s `CMakeLists.txt` expects
`cna` as a **sibling directory**:

*From `CMakeLists.txt:86`:*
```cmake
set(CNA_GRAPHICS_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../cna")
```

so a working Linux checkout needs both repositories cloned next to each other, e.g.:

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/openeggbert/mobile-eggbert.git
git clone https://github.com/openeggbert/cna.git
cd mobile-eggbert
```

`README.md`'s "Init submodules" step reads:

*From `README.md:19-22`:*
```bash
git submodule init --recursive
git submodule update --recursive
```

Read literally against the actual repository contents, this instruction is worth a note of
caution: `mobile-eggbert`'s own repository root has **no `.gitmodules` file** — this project does
not vendor `cna` (or anything else) as a Git submodule of its own; the two are simply independent,
sibling checkouts, as the `CNA_GRAPHICS_SOURCE_DIR` line above shows. The real Git submodules in
this ecosystem — `third_party/SDL`, `third_party/SDL_image`, `third_party/SDL_mixer`, and
`vendor/googletest` — are declared in **`cna`'s** `.gitmodules`, one level down. So the practical
effect of running `git submodule update --init --recursive` is on `cna`'s submodules, and it needs
to be run from inside the `cna` checkout (or from a parent directory that itself treats
`mobile-eggbert` and `cna` as submodules of some larger umbrella checkout) rather than from
`mobile-eggbert`'s own root, where it is a silent no-op. A reader following `README.md` verbatim
from inside `mobile-eggbert/` won't get an error — `git submodule` on a repository with no
`.gitmodules` simply does nothing — but they also won't get `cna`'s vendored SDL3 sources unless
they separately run the same command inside `cna/`.

## Configure and build

`README.md`'s documented Linux build sequence is:

*From `README.md:26-32`:*
```bash
cmake -S . -B build-linux \
  -DCNA_BACKEND_SDL_RENDERER=ON \
  -DCNA_BACKEND_EASY_GL=OFF \
  -DCNA_BACKEND_BGFX=OFF
cmake --build build-linux --target WindowsPhoneSpeedyBlupi
```

This uses the **legacy boolean input path** described in [Chapter 4](ch04-build-overview.md) —
`CNA_BACKEND_SDL_RENDERER`, `CNA_BACKEND_EASY_GL`, `CNA_BACKEND_BGFX` are the older, per-backend
`CNA_BACKEND_*` options that `cna` still accepts and translates internally into the equivalent
`CNA_GRAPHICS_BACKEND` string, rather than the modern single-string form
(`-DCNA_GRAPHICS_BACKEND=SDL_RENDERER`) that `mobile-eggbert`'s own `CMakeLists.txt` has fully
adopted for its *own* backend-selection and validation logic (the `MOBILE_EGGBERT_BACKENDS` list
and the `FATAL_ERROR` check at `CMakeLists.txt:80-84`). Both forms are genuinely accepted and both
produce a working build — but they are documented and exercised inconsistently across this
project's own files: `README.md` still shows the boolean form for the Linux and Windows native
builds, while the actual `CMakeLists.txt` comments explicitly describe that form as "an optional,
alternative input path" that a consumer setting the string "never needs to touch." A reader who
wants the path this file's own comments treat as authoritative can equivalently write:

```bash
cmake -S . -B build-linux -DCNA_GRAPHICS_BACKEND=SDL_RENDERER
cmake --build build-linux --target WindowsPhoneSpeedyBlupi
```

since `SDL_RENDERER` is already the default `CNA_GRAPHICS_BACKEND` value on the desktop (non-Android,
non-Emscripten) branch of the platform-detection `if`/`elseif`/`else` at `CMakeLists.txt:62-77`
covered in [Chapter 4](ch04-build-overview.md) — meaning on Linux, with no `-D` flags at all, the
default configure already resolves to `SDL_RENDERER`. Either invocation, boolean-flag or
string-flag, lands at the same backend for a first build.

The `--target WindowsPhoneSpeedyBlupi` argument names the executable target created by
`add_executable(${_game_target} ${SOURCES})` at `CMakeLists.txt:102` — on Linux `_game_target`
resolves to the literal string `WindowsPhoneSpeedyBlupi` (the Android/`main` special case from
[Chapter 4](ch04-build-overview.md) doesn't apply here), so the target name in the build command
and the project name at the top of `CMakeLists.txt:2` are, by design, identical.

## Running the built binary

After a successful build, the `POST_BUILD` custom commands at `CMakeLists.txt:196-221`
(native-desktop `Content/` and `worlds/` copy steps, described in [Chapter 4](ch04-build-overview.md))
place the game's assets directly next to the executable:

```
build-linux/
├── WindowsPhoneSpeedyBlupi
├── Content/
│   ├── backgrounds/
│   ├── icons/
│   └── sounds/
└── worlds/
    └── world001.txt, world002.txt, ...
```

Because both directories are copied relative to the executable's own output location
(`$<TARGET_FILE_DIR:${_game_target}>`), the game can be run directly from the build directory
without any separate "install" step:

```bash
cd build-linux
./WindowsPhoneSpeedyBlupi
```

No `WEBGPU`-specific runtime library copy, `RPATH` adjustment, or MinGW-runtime copy step applies
on a default `SDL_RENDERER` Linux build — those blocks in `CMakeLists.txt` are guarded respectively
by `CNA_GRAPHICS_BACKEND STREQUAL "WEBGPU"` and `if(MINGW)`, neither of which is true here.

## Choosing a different backend on Linux

[Chapter 4](ch04-build-overview.md) covers the full backend catalog and the desktop `else()`
branch's comment explaining each option's caveats (`CMakeLists.txt:62-76`). On native Linux, the
practically relevant alternatives to the default `SDL_RENDERER` are:

- `-DCNA_GRAPHICS_BACKEND=EASYGL` — a lightweight OpenGL-based backend, explicitly mentioned in
  `README.md`'s backend-status summary as available on Linux ("easy-gl can be enabled explicitly
  when needed").
- `-DCNA_GRAPHICS_BACKEND=VULKAN` — native Vulkan, given as the example override in the
  `CMakeLists.txt` comment itself (`CMakeLists.txt:64`).
- `-DCNA_GRAPHICS_BACKEND=ASCII` — the SDL-windowed glyph-grid decorator, explicitly called out in
  `README.md`'s backend-status section as selectable on Linux.
- `-DCNA_GRAPHICS_BACKEND=DX3` — the portable DirectDraw-subset backend built on the sibling
  `../free-direct` repository, also explicitly listed as Linux-selectable in `README.md` (it needs
  no Wine/Proton, unlike the true Direct3D backends).
- `-DCNA_GRAPHICS_BACKEND=HEADLESS` or `-DCNA_GRAPHICS_BACKEND=SOFTWARE` — for running the game's
  own logic without a display server, useful for CI or automated testing contexts.

Selecting a backend `cna` does not currently compile a target for on the running platform (for
example `D3D11`/`D3D12`/`D3D9` outside of a Windows/MinGW toolchain) will not fail at the
`CMakeLists.txt:80-84` validation step — that check only validates the *name* against
`MOBILE_EGGBERT_BACKENDS`, not platform compatibility — but will fail further down inside `cna`'s
own build if the backend's sources genuinely can't compile for the host. The Direct3D backends'
real, Windows-toolchain-dependent build path (including how to build and run them cross-compiled
from Linux) is covered in [Chapter 6](ch06-windows-and-cross-compilation.md) and
[Chapter 7](ch07-direct3d-wine-proton.md).

## See also

- [Chapter 4: Build Overview (CMake)](ch04-build-overview.md)
- [Chapter 6: Windows and Cross-Compilation](ch06-windows-and-cross-compilation.md)
- [Chapter 7: Direct3D via Wine/Proton](ch07-direct3d-wine-proton.md)
- [Chapter 8: Web/Emscripten Build](ch08-web-emscripten-build.md)
