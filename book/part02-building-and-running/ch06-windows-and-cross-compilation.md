# Chapter 6: Windows and Cross-Compilation

`mobile-eggbert` can be built for Windows in two genuinely different ways: natively, with a
Windows-hosted toolchain (documented in `README.md` and, in more operational detail, in
`WINDOWS.md`), or cross-compiled from Linux using MinGW-w64, driven by a dedicated CMake toolchain
file at `cmake/toolchains/mingw-w64.cmake`. Both paths produce the same kind of artifact — a
standalone `WindowsPhoneSpeedyBlupi.exe` that runs outside any IDE or MSYS2 environment — but they
get there via different compilers and different runtime-dependency handling. This chapter covers
both, plus what `WINDOWS.md` documents about *why* the runtime-dependency handling exists at all.

## Windows native build

`README.md`'s native Windows build command is structurally identical to the Linux one from
[Chapter 5](ch05-linux-build.md), just run under PowerShell:

*From `README.md:36-42`:*
```powershell
cmake -S . -B build-windows \
  -DCNA_BACKEND_SDL_RENDERER=ON \
  -DCNA_BACKEND_EASY_GL=OFF \
  -DCNA_BACKEND_BGFX=OFF
cmake --build build-windows --target WindowsPhoneSpeedyBlupi
```

As in the Linux case, this uses the legacy `CNA_BACKEND_*` boolean input path rather than the
single `CNA_GRAPHICS_BACKEND` string `mobile-eggbert`'s own `CMakeLists.txt` treats as canonical
(see [Chapter 4](ch04-build-overview.md)); both are accepted, and on Windows — as on Linux — the
desktop branch of the platform-detection logic (`CMakeLists.txt:62-77`) already defaults
`CNA_GRAPHICS_BACKEND` to `"SDL_RENDERER"`, so this command and a bare
`cmake -S . -B build-windows` resolve to the same backend.

`WINDOWS.md` documents the concrete, developer-facing setup this native path assumes: **CLion's
bundled MinGW toolchain** (GCC/G++ targeting `x86_64-w64-mingw32`) rather than MSVC:

*From `WINDOWS.md:1-6`:*
```markdown
# Windows Build Notes

## Building with MinGW (CLion default toolchain)

The project is configured to build on Windows using the bundled CLion MinGW
toolchain (GCC/G++ targeting `x86_64-w64-mingw32`).
```

This detail matters because it means "native Windows build" and "MinGW-w64 cross-build from
Linux" (covered next) end up producing binaries from the *same compiler family* — GCC targeting
the same `x86_64-w64-mingw32` triplet — just hosted on different operating systems. The practical
consequences described below (static runtime linking, DLL copying) are therefore identical between
the two build modes; only the CMake invocation and the compiler's own host platform differ.

### Why the executable needs runtime-DLL handling at all

A raw MinGW-compiled executable depends on several runtime DLLs that only exist inside a CLion or
MSYS2 environment by default. `WINDOWS.md` gives the exact table:

*From `WINDOWS.md:11-20`:*

| DLL | Handled by |
|-----|-----------|
| `libgcc_s_seh-1.dll` | Statically linked (`-static-libgcc`) |
| `libstdc++-6.dll` | Statically linked (`-static-libstdc++`) |
| `libwinpthread-1.dll` | Copied next to the executable at build time |
| `SDL3.dll` | Copied next to the executable at build time |
| `SDL3_image.dll` | Copied next to the executable at build time |
| `SDL3_mixer.dll` | Copied next to the executable at build time |

After a successful build, `WINDOWS.md` states the output directory should contain:

*From `WINDOWS.md:22-32`:*
```
WindowsPhoneSpeedyBlupi.exe
libwinpthread-1.dll
SDL3.dll
SDL3_image.dll
SDL3_mixer.dll
Content/   (game assets)
```

and that "you can copy this entire directory to any Windows machine and run the game without
installing MinGW, CLion, or any other runtime" — the entire point of the DLL-handling logic
documented below.

### How it's implemented: static GCC/C++ runtime

Two of the six DLLs above are eliminated entirely, by statically linking the compiler's own
runtime into the executable rather than shipping it as a separate file. This is the `if(MINGW)`
block already read in [Chapter 4](ch04-build-overview.md):

*From `CMakeLists.txt:228-231`:*
```cmake
if(MINGW)
    # Statically link the MinGW GCC and C++ runtime so the exe runs outside
    # CLion/MSYS2 without needing libgcc_s_seh-1.dll / libstdc++-6.dll.
    target_link_options(${_game_target} PRIVATE -static-libgcc -static-libstdc++)
```

`-static-libgcc` and `-static-libstdc++` are standard GCC linker flags that fold the GCC support
library and the C++ standard library implementation directly into the executable, at the cost of a
larger binary, in exchange for removing `libgcc_s_seh-1.dll` and `libstdc++-6.dll` from the list of
DLLs the shipped game needs alongside it.

### How it's implemented: `libwinpthread-1.dll`

`libwinpthread-1.dll` cannot be statically linked the same way (`WINDOWS.md` notes this directly:
"`libwinpthread-1.dll` cannot be statically linked this way; copy it instead"), so instead
`CMakeLists.txt` calls a helper function defined inside `cna`:

*From `CMakeLists.txt:232-233`:*
```cmake
    # libwinpthread-1.dll cannot be statically linked this way; copy it instead.
    cna_copy_mingw_runtime(${_game_target})
endif()
```

`WINDOWS.md` documents exactly what `cna_copy_mingw_runtime()` (defined in
`../../cna/cmake/ThirdPartySDL.cmake`, per `WINDOWS.md:45-46`) does, step by step:

*From `WINDOWS.md:45-51`:*
```markdown
**Copying `libwinpthread-1.dll`** — the helper function `cna_copy_mingw_runtime()`
defined in `../../cna/cmake/ThirdPartySDL.cmake`:
1. Calls `gcc -print-file-name=libwinpthread-1.dll` at configure time to locate
   the DLL inside the active MinGW installation.
2. Falls back to the directory that contains the compiler binary.
3. Adds a `POST_BUILD` command that copies the DLL next to the target executable.
```

This is a genuinely robust discovery mechanism: rather than hardcoding a path to a specific MinGW
installation (which varies between a CLion-bundled toolchain, an MSYS2 install, and a
distro-packaged cross-compiler on Linux), it asks the compiler itself where its own runtime DLL
lives via `-print-file-name`, with a directory-of-the-compiler fallback if that query doesn't
resolve to a usable path.

### How it's implemented: SDL runtime DLLs

The three SDL DLLs (`SDL3.dll`, `SDL3_image.dll`, `SDL3_mixer.dll`) are copied by a *different*
helper, `cna_copy_sdl_runtime()` — also defined in `cna/cmake/ThirdPartySDL.cmake` — called
unconditionally for every `WIN32` build, not just MinGW ones:

*From `CMakeLists.txt:224-226`:*
```cmake
if(WIN32)
    cna_copy_sdl_runtime(${_game_target})
endif()
```

`WINDOWS.md` is explicit that this call is unconditional across the whole `WIN32` platform check,
distinguishing it from the `if(MINGW)`-guarded static-runtime and `libwinpthread` steps, which are
specific to the MinGW toolchain rather than to Windows as a target OS in general (relevant should
this project ever also support building with MSVC).

### The test executable gets the same treatment

`WINDOWS.md` notes that the identical set of steps is applied to `CnaTests.exe` (`cna`'s own GTest
suite target, out of scope for `mobile-eggbert`'s own book coverage per
[`CLAUDE.md`](../../CLAUDE.md)), with one addition — the `gtest`/`gmock` shared libraries are also
copied at `POST_BUILD` — confirming that this DLL-bundling pattern is a general-purpose `cna`-level
utility rather than something written narrowly for the game's own executable.

### Scope: guarded, not global

`WINDOWS.md` closes its coverage of this mechanism with an explicit statement of scope:

*From `WINDOWS.md:63-66`:*
```markdown
### Linux / Web / Android

These changes are fully guarded by `if(MINGW)` / `if(WIN32)` and have no effect
on Linux, Emscripten (WebAssembly), or Android builds.
```

which matches what [Chapter 4](ch04-build-overview.md) and [Chapter 5](ch05-linux-build.md)
already established: the `MINGW`/`WIN32` conditionals mean none of this DLL-bundling logic runs, or
needs to run, on any other target.

## Windows cross-build from Linux (MinGW-w64)

The second Windows build path avoids needing a Windows machine at all: cross-compiling from Linux
using the `x86_64-w64-mingw32` toolchain, via a dedicated CMake toolchain file.

### Prerequisites and the clean-build-directory warning

`README.md` states this plainly:

*From `README.md:44-49`:*
```markdown
### Windows cross-build from Linux (MinGW-w64)

**Important: Always use a clean build directory when switching toolchains (e.g., `rm -rf build-windows`).**

1. Ensure you have `mingw-w64` installed (e.g., `sudo apt install mingw-w64`).
2. Run the build:
```

The warning about a clean build directory is not boilerplate caution — it corresponds directly to
the check at the very top of `CMakeLists.txt` covered in [Chapter 4](ch04-build-overview.md):

*From `CMakeLists.txt:8-12`:*
```cmake
if (NOT WIN32 AND CMAKE_BINARY_DIR MATCHES "build-windows")
    message(WARNING "Building in 'build-windows' directory, but WIN32 is not set. "
                    "Make sure you used -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/mingw-w64.cmake "
                    "on a CLEAN build directory.")
endif()
```

CMake caches the active toolchain's compiler and platform detection results inside
`CMakeCache.txt` on first configure; reusing a `build-windows` directory that was previously
configured *without* the MinGW toolchain file (or vice versa) leaves stale, inconsistent cache
entries rather than cleanly re-detecting the new toolchain. Naming the build directory
`build-windows` and then genuinely passing `-DCMAKE_TOOLCHAIN_FILE=...` on a fresh directory is
what keeps this warning from firing.

### The toolchain file

The referenced file, `cmake/toolchains/mingw-w64.cmake`, is short and does exactly what a
cross-compilation toolchain file needs to: tell CMake which system it's targeting and which
compiler binaries to use for it.

*From `cmake/toolchains/mingw-w64.cmake:1-22`:*
```cmake
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

set(MINGW_TRIPLET "x86_64-w64-mingw32" CACHE STRING "MinGW-w64 target triplet")

message(STATUS "CNA: Loading MinGW-w64 toolchain (${MINGW_TRIPLET})")

find_program(MINGW_C_COMPILER NAMES ${MINGW_TRIPLET}-gcc)
find_program(MINGW_CXX_COMPILER NAMES ${MINGW_TRIPLET}-g++)
find_program(MINGW_RC_COMPILER NAMES ${MINGW_TRIPLET}-windres)

if(NOT MINGW_C_COMPILER)
    message(FATAL_ERROR "Could not find MinGW-w64 C compiler (${MINGW_TRIPLET}-gcc). Please install mingw-w64 package or set MINGW_C_COMPILER.")
endif()

if(NOT MINGW_CXX_COMPILER)
    message(FATAL_ERROR "Could not find MinGW-w64 C++ compiler (${MINGW_TRIPLET}-g++). Please install mingw-w64 package or set MINGW_CXX_COMPILER.")
endif()

set(CMAKE_C_COMPILER "${MINGW_C_COMPILER}")
set(CMAKE_CXX_COMPILER "${MINGW_CXX_COMPILER}")
set(CMAKE_RC_COMPILER "${MINGW_RC_COMPILER}")
```

`CMAKE_SYSTEM_NAME Windows` is the line that puts CMake into cross-compiling mode at all — it's
what makes `WIN32` and `MINGW` true for the rest of the build even though the host OS running CMake
is Linux, which is exactly why the `MINGW`-guarded static-runtime linking and DLL-copying steps
from the native-Windows section above apply identically to this cross-compiled path. The three
`find_program()` calls locate the triplet-prefixed cross-compiler binaries
(`x86_64-w64-mingw32-gcc`, `-g++`, `-windres`) rather than assuming a fixed install path, each with
an explicit `FATAL_ERROR` if not found — giving a clear "install `mingw-w64`" message rather than a
confusing downstream compiler-not-found failure.

The remainder of the toolchain file governs how CMake resolves `find_package()`/`find_library()`
calls when cross-compiling:

*From `cmake/toolchains/mingw-w64.cmake:24-32`:*
```cmake
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

set(CNA_WINDOWS_DEPENDENCIES_ROOT "" CACHE PATH "Optional root folder containing Windows SDL3/SDL3_image/SDL3_mixer/SDL3_ttf CMake packages")
if(CNA_WINDOWS_DEPENDENCIES_ROOT)
    list(PREPEND CMAKE_PREFIX_PATH "${CNA_WINDOWS_DEPENDENCIES_ROOT}")
endif()
```

`CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER` keeps CMake looking for host *programs* (like `windres`
or any code-generation tool run at build time) on the Linux host's own `PATH`, while
`LIBRARY`/`INCLUDE`/`PACKAGE` set to `ONLY` restrict library, header, and package lookups to the
configured root path(s) — the standard CMake cross-compilation pattern to stop the build from
accidentally picking up the Linux host's own native libraries when it needs Windows-target ones.
`CNA_WINDOWS_DEPENDENCIES_ROOT` is the toolchain file's own escape hatch for supplying those
Windows-target libraries: an optional cache path that, if set, is prepended to `CMAKE_PREFIX_PATH`
so `find_package(SDL3 ...)` and friends can locate Windows-built SDL3/SDL3_image/SDL3_mixer (and
SDL3_ttf) CMake package configs there.

### Running the cross-build

`README.md`'s full sequence:

*From `README.md:50-60`:*
```bash
# Ensure you are in mobile-eggbert directory
rm -rf build-windows
cmake -S . -B build-windows \
  -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/mingw-w64.cmake \
  -DCNA_GRAPHICS_BACKEND=SDL_RENDERER \
  -DCNA_WINDOWS_DEPENDENCIES_ROOT=/path/to/windows/sdl3/libs
cmake --build build-windows --target WindowsPhoneSpeedyBlupi
```

Note that this invocation *does* use the modern `-DCNA_GRAPHICS_BACKEND=SDL_RENDERER` string form
rather than the legacy `CNA_BACKEND_*` booleans shown for the native Linux/Windows builds earlier
in this chapter and in [Chapter 5](ch05-linux-build.md) — an inconsistency within `README.md`
itself, though both forms remain valid per the `CMakeLists.txt` logic discussed in
[Chapter 4](ch04-build-overview.md). `README.md` also flags explicitly that Windows-target SDL3
package configs are the cross-builder's own responsibility to supply: *"You must provide
Windows-target SDL3 package configs (`SDL3`, `SDL3_image`, etc.) through
`CNA_WINDOWS_DEPENDENCIES_ROOT` or `CMAKE_PREFIX_PATH`."* This follows directly from the toolchain
file's `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY`/`PACKAGE ONLY` settings above — cross-compiling
means the build cannot fall back to any SDL3 already installed for the Linux host.

The resulting `.exe` and its accompanying DLLs (per the `WINDOWS.md` table above) are produced
inside `build-windows/` exactly as in the native case, and are runnable on a real Windows machine
without any MinGW/MSYS2/CLion installation — or, as [Chapter 7](ch07-direct3d-wine-proton.md)
covers, runnable directly on the Linux host that built them, via Wine or Proton.

## See also

- [Chapter 4: Build Overview (CMake)](ch04-build-overview.md)
- [Chapter 5: Linux Build](ch05-linux-build.md)
- [Chapter 7: Direct3D via Wine/Proton](ch07-direct3d-wine-proton.md)
- [Chapter 52: Windows Deep Dive](../part10-platform-deep-dives/ch52-windows-deep-dive.md)
