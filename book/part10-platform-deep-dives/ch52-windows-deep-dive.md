# Chapter 52: Windows Deep Dive

[Chapter 6](../part02-building-and-running/ch06-windows-and-cross-compilation.md) already covers
the Windows native build and the MinGW-w64 cross-compilation setup, and
[Chapter 7](../part02-building-and-running/ch07-direct3d-wine-proton.md) covers the D3D11/D3D12
backends and their Wine/Proton story in depth. This chapter does not repeat either of those. It
covers the one thing `mobile-eggbert`'s own `WINDOWS.md` documents that neither of those chapters
does: how the project makes a MinGW-built `.exe` runnable on a plain Windows machine that has never
had MinGW, CLion, or MSYS2 installed on it. `WINDOWS.md` itself is short — 66 lines — so this
chapter stays proportionate to it rather than padding out a small, focused topic.

## The problem `WINDOWS.md` is solving

`mobile-eggbert` builds on Windows through CLion's bundled MinGW toolchain (GCC/G++ targeting
`x86_64-w64-mingw32`) as its default configuration. A binary compiled this way normally links
dynamically against a handful of MinGW-specific runtime DLLs that exist inside a MinGW/MSYS2
installation but are not part of a stock Windows install. Copy just the `.exe` to another machine
and it fails to launch — a `DLL not found` error, not a game bug.

*From `WINDOWS.md:10-20`:*

> When built with MinGW the executable normally depends on MinGW runtime DLLs that
> are only available inside the CLion/MSYS2 environment:
>
> | DLL | Handled by |
> |-----|-----------|
> | `libgcc_s_seh-1.dll` | Statically linked (`-static-libgcc`) |
> | `libstdc++-6.dll` | Statically linked (`-static-libstdc++`) |
> | `libwinpthread-1.dll` | Copied next to the executable at build time |
> | `SDL3.dll` | Copied next to the executable at build time |
> | `SDL3_image.dll` | Copied next to the executable at build time |
> | `SDL3_mixer.dll` | Copied next to the executable at build time |

The table lays out two distinct fixes for what looks like one problem: two of the runtime
dependencies are eliminated by static linking, and the remaining four are solved by copying the
DLL next to the executable at build time instead. The result, confirmed by `WINDOWS.md`, is a
self-contained build output directory:

*From `WINDOWS.md:22-32`:*

> After a successful build the output directory (`cmake-build-debug/` or your chosen build dir)
> should contain:
> ```
> WindowsPhoneSpeedyBlupi.exe
> libwinpthread-1.dll
> SDL3.dll
> SDL3_image.dll
> SDL3_mixer.dll
> Content/   (game assets)
> ```
> You can copy this entire directory to any Windows machine and run the game without installing
> MinGW, CLion, or any other runtime.

## How the two fixes are actually wired into the build

### Static linking of the GCC/C++ runtime

The static-linking half is a two-line, unconditional addition inside a `if(MINGW)` guard in the
root `CMakeLists.txt`:

*From `CMakeLists.txt:228-234`:*

```cmake
if(MINGW)
    # Statically link the MinGW GCC and C++ runtime so the exe runs outside
    # CLion/MSYS2 without needing libgcc_s_seh-1.dll / libstdc++-6.dll.
    target_link_options(${_game_target} PRIVATE -static-libgcc -static-libstdc++)
    # libwinpthread-1.dll cannot be statically linked this way; copy it instead.
    cna_copy_mingw_runtime(${_game_target})
endif()
```

The inline comment on the last line explains why `libwinpthread-1.dll` gets different treatment
from the other two: `-static-libgcc`/`-static-libstdc++` are standard GCC driver flags for folding
the GCC and C++ standard library runtime directly into the binary, but MinGW-w64's pthread
compatibility shim does not have an equivalent static-linking flag in this toolchain, so it has to
be shipped as a loose DLL instead.

### Locating and copying the remaining DLLs

The copy half of the fix is a pair of CMake helper functions defined in `cna`'s shared build
tooling (`cna/cmake/ThirdPartySDL.cmake`), called from mobile-eggbert's own `CMakeLists.txt`:

*From `CMakeLists.txt:224-226`:*

```cmake
if(WIN32)
    cna_copy_sdl_runtime(${_game_target})
endif()
```

`cna_copy_mingw_runtime()` does the more interesting work of the two, because `libwinpthread-1.dll`
isn't at a fixed, well-known path — its location depends on which MinGW installation is active.
`WINDOWS.md` describes the resolution strategy at a high level:

*From `WINDOWS.md:45-50`:*

> **Copying `libwinpthread-1.dll`** — the helper function `cna_copy_mingw_runtime()`
> defined in `../../cna/cmake/ThirdPartySDL.cmake`:
> 1. Calls `gcc -print-file-name=libwinpthread-1.dll` at configure time to locate
>    the DLL inside the active MinGW installation.
> 2. Falls back to the directory that contains the compiler binary.
> 3. Adds a `POST_BUILD` command that copies the DLL next to the target executable.

Reading the actual function confirms this exactly — it shells out to the compiler itself to ask
where the DLL lives, rather than hardcoding a guess at an install path:

*From `ThirdPartySDL.cmake:238-250` (in `cna`):*

```cmake
execute_process(
    COMMAND "${CMAKE_C_COMPILER}" -print-file-name=libwinpthread-1.dll
    OUTPUT_VARIABLE _pthread_dll
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)

if(_pthread_dll AND _pthread_dll MATCHES "[/\\\\]")
    file(TO_CMAKE_PATH "${_pthread_dll}" _pthread_dll)
    if(EXISTS "${_pthread_dll}")
        add_custom_command(TARGET ${target_name} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${_pthread_dll}"
```

`-print-file-name` is a standard GCC driver query that returns the resolved path GCC itself would
use for a given filename, given its own configured search paths — asking the compiler rather than
guessing means the helper keeps working across different MinGW distributions (MSYS2, the one
bundled with CLion, a manually-installed toolchain) without needing per-distribution path logic.
If that query comes back empty or non-existent, the function falls back to the directory containing
the compiler binary itself before giving up and emitting a warning — the exact three-step fallback
`WINDOWS.md` summarizes.

`cna_copy_sdl_runtime()`, the second helper, is comparatively simple: it iterates over the three
SDL-family CMake import targets (`SDL3::SDL3`, `SDL3_image::SDL3_image`, `SDL3_mixer::SDL3_mixer`)
and adds a `POST_BUILD` copy command for each one's `$<TARGET_FILE:...>` generator expression —
letting CMake itself resolve the actual built/vendored DLL path per target rather than
hardcoding one.

Both helper functions guard themselves against running on the wrong platform
(`if(EMSCRIPTEN OR ANDROID)` early-returns in `cna_copy_mingw_runtime()`; `if(EMSCRIPTEN OR ANDROID
OR NOT WIN32)` in `cna_copy_sdl_runtime()`), which matches `WINDOWS.md`'s closing note that none of
this machinery has any effect on the other three platforms:

*From `WINDOWS.md:63-66`:*

> These changes are fully guarded by `if(MINGW)` / `if(WIN32)` and have no effect
> on Linux, Emscripten (WebAssembly), or Android builds.

## The same treatment applies to the test binary

`WINDOWS.md` notes that `CnaTests.exe` — the project's GoogleTest-based test executable — gets
identical treatment: the same `-static-libgcc -static-libstdc++` flags, the same
`cna_copy_mingw_runtime()` call, and the same `cna_copy_sdl_runtime()` call, plus its own additional
`POST_BUILD` copy of the `gtest`/`gmock` shared libraries it links against. This is a small but
notable detail for anyone trying to run the test suite standalone on a bare Windows machine (rather
than inside CLion) — the same DLL-portability problem exists there and is solved the same way.

## What this chapter deliberately does not repeat

Everything about *choosing* a Windows graphics backend — SDL_Renderer as the default, and the
verified-working Direct3D 11 and Direct3D 12 backends including the Wine-vs-Proton distinction for
D3D12 — belongs to [Chapter 7](../part02-building-and-running/ch07-direct3d-wine-proton.md) and is
not repeated here. Likewise, the actual cross-compilation invocation
(`cmake --toolchain cmake/toolchains/mingw-w64.cmake ...`) and its prerequisites are
[Chapter 6](../part02-building-and-running/ch06-windows-and-cross-compilation.md)'s territory. This
chapter's entire scope is the narrower, `WINDOWS.md`-specific question: once you *have* a MinGW
build, how does it become something you can hand to someone who has never installed a compiler.

## See also

- [Chapter 6](../part02-building-and-running/ch06-windows-and-cross-compilation.md) — Windows
  native build and MinGW-w64 cross-compilation from Linux.
- [Chapter 7](../part02-building-and-running/ch07-direct3d-wine-proton.md) — the D3D11/D3D12
  backends, and running them on Linux via Wine and Proton.
- [Chapter 4](../part02-building-and-running/ch04-build-overview.md) — the root `CMakeLists.txt` in
  full, of which the `if(MINGW)`/`if(WIN32)` blocks discussed here are one small part.
