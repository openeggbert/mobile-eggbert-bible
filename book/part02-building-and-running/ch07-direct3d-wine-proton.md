# Chapter 7: Direct3D via Wine/Proton

Among the thirteen graphics backends `mobile-eggbert` can be built against (catalogued in
[Chapter 4](ch04-build-overview.md)), two are Windows-only Direct3D backends — `D3D11` and
`D3D12` — and yet both can be built *and run* entirely from a Linux machine, without ever touching
real Windows. This chapter covers `README.md`'s detailed account of that path, including a genuine,
specific engineering finding about why D3D12 needs Proton while D3D11 runs fine under plain Wine —
a real DLL-pairing mismatch, not a hypothetical caveat.

## Why this is possible at all

The two backends are cross-compiled using exactly the MinGW-w64 toolchain covered in
[Chapter 6](ch06-windows-and-cross-compilation.md) — the resulting `.exe` is a genuine Windows PE
binary, just produced by a cross-compiler running on Linux. What makes it *runnable* on Linux too
is Wine (a compatibility layer that implements the Windows API on top of Linux) and, for one of the
two backends, Proton (Valve's Wine-based compatibility layer for Steam, bundled with its own
patched DXVK/vkd3d-proton translation libraries). `README.md` states the headline result plainly:

*From `README.md:62-66`:*
```markdown
### Direct3D 11 / Direct3D 12 (Windows backends, runnable on Linux via Wine/Proton)

CNA has full Direct3D 11 and Direct3D 12 backends. They are Windows-only, but you can build **and
run** them from Linux — the D3D11 build even runs under plain Wine. Both were verified end to end
(the game builds, starts, creates a real GPU device and swapchain, and presents frames).
```

"Verified end to end" here means something specific and checkable, not a vague claim: the game
actually builds, actually starts, actually creates a real GPU device and swapchain through the
Direct3D API, and actually presents rendered frames — the full pipeline, not just a compile check.

## Building either backend

Both backends are built with the same MinGW-w64 cross-compilation approach as
[Chapter 6](ch06-windows-and-cross-compilation.md)'s Windows cross-build, just selecting `D3D11` or
`D3D12` as the backend and adding two extra flags:

*From `README.md:68-82`:*
```bash
# Direct3D 11
cmake -S . -B build-d3d11 -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=../cna/cmake/toolchains/mingw-w64.cmake \
  -DCNA_GRAPHICS_BACKEND=D3D11 -DCMAKE_BUILD_TYPE=Release -DCNA_BUILD_TESTS=OFF
cmake --build build-d3d11 --target WindowsPhoneSpeedyBlupi

# Direct3D 12 (same, with D3D12)
cmake -S . -B build-d3d12 -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=../cna/cmake/toolchains/mingw-w64.cmake \
  -DCNA_GRAPHICS_BACKEND=D3D12 -DCMAKE_BUILD_TYPE=Release -DCNA_BUILD_TESTS=OFF
cmake --build build-d3d12 --target WindowsPhoneSpeedyBlupi
```

Three details are worth calling out against what [Chapter 6](ch06-windows-and-cross-compilation.md)
already established about the MinGW toolchain path:

- The toolchain file path here is given as `../cna/cmake/toolchains/mingw-w64.cmake` rather than
  `cmake/toolchains/mingw-w64.cmake` (the path used in the plain Windows cross-build section of
  `README.md` and confirmed to exist at that location inside `mobile-eggbert` itself, per
  [Chapter 6](ch06-windows-and-cross-compilation.md)). Both paths point at functioning MinGW-w64
  toolchain files in this ecosystem, but they are not necessarily *the same file*: `mobile-eggbert`
  carries its own copy at `cmake/toolchains/mingw-w64.cmake` (read in full in
  [Chapter 6](ch06-windows-and-cross-compilation.md)), while `cna` also ships one at
  `cna/cmake/toolchains/mingw-w64.cmake`. A reader following this section of `README.md` literally
  ends up using `cna`'s toolchain file instead of `mobile-eggbert`'s own — both work for this
  purpose, but it's a real inconsistency in the documentation worth being aware of rather than
  assuming a typo.
- `-G Ninja` selects the Ninja generator explicitly, rather than the default Unix Makefiles
  generator used in the plainer build examples elsewhere in this book.
- `-DCNA_BUILD_TESTS=OFF` is required, and `README.md` explains exactly why:

*From `README.md:84-86`:*
```markdown
`-DCNA_BUILD_TESTS=OFF` is needed because CNA's own GTest suite does not currently compile under
MinGW (a known, unrelated POSIX-portability gap — see `cna/plan_dx.md` `DX-15`). It has no
effect on the game itself.
```

This is a `cna`-internal limitation (its GTest-based test suite has a POSIX-portability gap under
MinGW), tracked in `cna`'s own planning document as task `DX-15` — explicitly out of scope for this
book's own coverage of CNA internals (per [`CLAUDE.md`](../../CLAUDE.md)), but relevant here purely
as "why this exact flag is required for the game itself to build cleanly under this toolchain."

## Running D3D11 on Linux — plain Wine + DXVK

Once built, the D3D11 executable runs under an ordinary Wine prefix with DXVK installed — no
special Proton setup needed:

*From `README.md:88-95`:*
```markdown
#### Running D3D11 on Linux — plain Wine + DXVK

D3D11 needs nothing special beyond a Wine prefix with DXVK installed:
```
```bash
cd build-d3d11
WINEPREFIX=~/.wine-cna-d3d11 wine ./WindowsPhoneSpeedyBlupi.exe
```

DXVK translates Direct3D 9/10/11 calls to Vulkan, and is a common, well-tested compatibility layer
bundled or easily installed into most Wine setups (via distro packages, `winetricks`, or a manual
DXVK install into the prefix's `system32`/`syswow64`). The `WINEPREFIX` environment variable simply
points Wine at a dedicated, isolated prefix directory (`~/.wine-cna-d3d11` in this example) rather
than the user's default `~/.wine`, which is good practice for isolating a specific application's
Windows-environment state.

## Running D3D12 on Linux — must go through Proton, not plain Wine

D3D12 is where the interesting, specific finding lives. Under plain system Wine, launching the
D3D12 build does not merely run slowly or render incorrectly — it crashes immediately on startup,
with a null-pointer page fault:

*From `README.md:97-104`:*
```markdown
#### Running D3D12 on Linux — **must** go through Proton, not plain Wine

Under plain system Wine, a D3D12 game **crashes on startup** with a null-pointer page fault:
```
```
vkd3d_instance_get_vk_instance(instance=0000000000000000)
  ← inside Wine's OWN dxgi.dll (dlls/dxgi/swapchain.c)
```

### The root cause: a DLL-pairing mismatch, not a bug in the game

`README.md` is explicit and specific about diagnosing this, and the diagnosis is worth stating
precisely because it's easy to misattribute a crash like this to the game or to `cna`:

*From `README.md:106-110`:*
```markdown
**This is not a bug in the game or in CNA.** It is a DLL-pairing mismatch in the environment: a
distro's system `dxgi.dll` cannot hand a D3D12 command queue to vkd3d-proton's separately-installed
`d3d12.dll` — those two only work as a matched pair, which is what Proton ships. (Full analysis:
`cna/plan_dx.md`, tasks `DX-100`/`DX-102`.) **On real Windows this does not happen at all**,
since there is only one DXGI, Microsoft's own.
```

Unpacking this: Direct3D 12 rendering on Linux via Wine requires two cooperating pieces —
`dxgi.dll` (which manages the swapchain and adapter enumeration) and `d3d12.dll` (which implements
the actual D3D12 device/command-queue API), with `vkd3d-proton` translating D3D12 calls to Vulkan
underneath `d3d12.dll`. A plain, distro-packaged Wine installation ships its *own* `dxgi.dll`
implementation, which was never written with knowledge of, or compiled against, a
separately-installed `vkd3d-proton` `d3d12.dll` — the two are not designed to be mixed and matched
independently. The crash trace shown (`vkd3d_instance_get_vk_instance(instance=0000000000000000)`,
happening *inside Wine's own `dxgi.dll`*, specifically in `dlls/dxgi/swapchain.c`) is the visible
symptom: Wine's `dxgi.dll` tries to hand off a Vulkan instance pointer to `d3d12.dll` that it never
received in the first place, because the two weren't built and packaged as the matched pair that
Proton ships them as. Genuinely on real Windows, this entire class of failure cannot occur, because
there is exactly one Microsoft-authored DXGI implementation and it always matches whatever D3D12
runtime Windows itself provides — the mismatch is purely an artifact of Wine's Linux-side
reimplementation of a piece of Windows' own plumbing being independently versioned from the
separately-distributed `vkd3d-proton` translation library.

### The fix: run through Proton, using a helper script from `cna`

Because Proton bundles its *own* internally-consistent, matched `dxgi.dll`/`d3d12.dll` pair (along
with the rest of vkd3d-proton), running the D3D12 build through a Proton-managed launch — rather
than plain system Wine — sidesteps the mismatch entirely:

*From `README.md:112-120`:*
```markdown
So run D3D12 through a properly Proton-managed launch, using the helper script in cna:
```
```bash
cd build-d3d12
bash ../../cna/scripts/run-proton-vkd3d.sh "$(pwd)/WindowsPhoneSpeedyBlupi.exe"
```
```markdown
It needs a local Steam install with "Proton - Experimental"; it bootstraps its own dedicated prefix
on first use and never touches your personal `~/.wine`.
```

The script (`cna/scripts/run-proton-vkd3d.sh`) requires a local Steam installation with the
"Proton - Experimental" compatibility tool available, and is designed to be non-invasive: it
bootstraps its own dedicated Proton prefix on first use, isolated from — and never touching — the
user's personal `~/.wine` prefix (the one plain Wine invocations, including the D3D11 launch
command above, would use by default).

### Confirmed working, in the same concrete terms as the D3D11 claim

`README.md` closes this section with the same level of specificity as the opening claim:

*From `README.md:122-124`:*
```markdown
Verified working: a real vkd3d-proton D3D12 device initialises against the GPU and
`dxgi_vk_swap_chain_init` creates a real 800x480 swapchain (the game's own resolution), which then
presents frames — zero crashes, zero exceptions.
```

The 800×480 figure is notable in its own right: it is the game's *own* native resolution being
correctly requested and honored end to end through the entire D3D12/vkd3d-proton/Vulkan
translation stack, not a placeholder or a generic default swapchain size — concrete evidence that
the pipeline is genuinely presenting frames at the resolution the game itself is asking for, rather
than merely "not crashing."

## Why this matters as an engineering finding, not just a workaround

The D3D11-vs-D3D12 asymmetry documented here is a genuinely instructive real-world case of two
superficially similar backends having very different Linux compatibility stories for a reason that
has nothing to do with the backends' own correctness. D3D11 has had mature, independently-installed
Wine/DXVK support for years precisely because DXVK long ago solved the equivalent DLL-pairing
problem by shipping DXVK's `dxgi.dll` *and* `d3d11.dll` as its own matched pair, replacing Wine's
built-in ones wholesale rather than mixing Wine's DXGI with a separately-sourced D3D11
implementation. D3D12 support via vkd3d-proton is comparatively newer and, per this finding, has
not (at least as observed here) had its `dxgi.dll` half decoupled from Proton's own bundling in the
same way DXVK's has — so a plain-Wine `dxgi.dll` paired with a separately-installed vkd3d-proton
`d3d12.dll` breaks, while Proton's own bundled, matched pair works cleanly. This is precisely the
kind of environment-specific, non-obvious compatibility detail this book aims to preserve
accurately rather than smooth over as "just use Proton" without explaining why plain Wine fails
first.

## Backend status summary (Windows, per `README.md`)

*From `README.md:204-206`:*
```markdown
- **Windows**: SDL_Renderer is the default. **Direct3D 11** and **Direct3D 12** both work (verified:
  the game builds, runs, and presents frames on each). See the D3D section above for building them
  from Linux, and for the one real caveat — D3D12 needs Proton, not plain Wine.
```

This matches the CMake-level picture from [Chapter 4](ch04-build-overview.md): `D3D11`, `D3D12`,
and `D3D9` are all present in `MOBILE_EGGBERT_BACKENDS` and documented there as "Windows-only, same
as D3D11/D3D12" for `D3D9` specifically — `README.md`'s own worked-through verification, however,
covers `D3D11` and `D3D12` only; `D3D9` is not given the same end-to-end Wine/Proton treatment in
`README.md`, so this book does not claim it has been verified running under Wine/Proton the way
`D3D11`/`D3D12` have.

## See also

- [Chapter 4: Build Overview (CMake)](ch04-build-overview.md)
- [Chapter 6: Windows and Cross-Compilation](ch06-windows-and-cross-compilation.md)
- [Chapter 52: Windows Deep Dive](../part10-platform-deep-dives/ch52-windows-deep-dive.md)
