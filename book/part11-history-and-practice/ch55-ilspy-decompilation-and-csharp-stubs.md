# Chapter 55: ILSpy Decompilation and the Residual C# Stubs

## Introduction: fossils in a C++ repository

`mobile-eggbert` is a C++ project — `CMakeLists.txt` builds a single executable target
(`WindowsPhoneSpeedyBlupi`) from `file(GLOB_RECURSE SOURCES "src/*.cpp")`
(`CMakeLists.txt:90`), and every line of gameplay logic described elsewhere in this book lives
under `include/WindowsPhoneSpeedyBlupi/` and `src/WindowsPhoneSpeedyBlupi/`. And yet, sitting at
the repository root, ten `.cs` files remain:

```
Properties/AssemblyInfo.cs
Microsoft.Xna.Framework.GamerServices/Guide.cs
Microsoft.Xna.Framework.GamerServices/TrialMode.cs
Microsoft.Devices.Sensors/Accelerometer.cs
Microsoft.Devices.Sensors/AccelerometerFailedException.cs
Microsoft.Devices.Sensors/AccelerometerReading.cs
Microsoft.Devices.Sensors/ISensorReading.cs
Microsoft.Devices.Sensors/SensorBase.cs
Microsoft.Devices.Sensors/SensorFailedException.cs
Microsoft.Devices.Sensors/SensorReadingEventArgs.cs
```

This chapter reads every one of them in full, establishes — from direct evidence in the build
system, not assumption — that none of them are compiled into the current game, and explains what
each one represented in the original Windows Phone 7 release before the C++ port replaced it.

## Confirming these files are not live code

Before treating these `.cs` files as historical artifacts rather than a second, hidden build
target, it's worth verifying that claim directly rather than asserting it.

**No C# project file exists.** There is no `.csproj` and no `.sln` anywhere in the repository:

```bash
$ find . -iname "*.csproj" -o -iname "*.sln"
(no output)
```

**`CMakeLists.txt` never mentions `.cs`.** The only wildcard source collection in the whole build
is:

*From `CMakeLists.txt:90`:*
```cmake
file(GLOB_RECURSE SOURCES "src/*.cpp")
```

This globs `*.cpp` under `src/` only. `Properties/`, `Microsoft.Xna.Framework.GamerServices/`, and
`Microsoft.Devices.Sensors/` are all outside `src/`, and even if they weren't, the glob pattern
would not match a `.cs` extension in any case. Grepping the entire repository (all `.txt`,
`CMakeLists.txt`, `*.cmake`, `*.gradle`, `*.sln`, `*.csproj` files) for any reference to `.cs`
files by name turns up nothing — the Android Gradle build (`android/app/build.gradle`, covered in
[Chapter 9](../part02-building-and-running/ch09-android-build.md) and
[Chapter 51](../part10-platform-deep-dives/ch51-android-deep-dive.md)) doesn't touch them either.

**The single commit's history offers no trail.** The repository as cloned for this book carries
exactly one commit (`07e0a67`, `git log --oneline` shows only that one entry), a squash of
whatever came before. `git log --follow` on `Guide.cs` returns that same single commit and
nothing earlier — there is no in-repo commit history showing when these files were decompiled or
when the C++ files that superseded them were introduced. Reconstructing that timeline in more
detail would require the separate `openeggbert/mobile-eggbert-legacy` repository (the pre-C++,
MonoGame-era C# codebase this project's `README.md` describes as an intermediate step); that
repository was not available as a local clone for this session (`/workspace/mobile-eggbert-legacy`
does not exist), so a direct historical comparison against it is left as noted future work at the
end of this chapter.

**The C++ code re-implements the same names as its own headers, not these files.** This is the
strongest piece of evidence, and it is unambiguous. The actual C++ game genuinely does use
`Microsoft::Devices::Sensors::Accelerometer` and
`Microsoft::Xna::Framework::GamerServices::Guide` — but it reaches them through
`#include "Microsoft/Devices/Sensors/AccelerometerFailedException.hpp"`
(`InputPad.cpp:91`) and `#include "Microsoft/Xna/Framework/GamerServices/Guide.hpp"`
(`Game1.cpp:77`), which resolve to headers in the sibling `cna` framework repository
(`cna/include/Microsoft/Devices/Sensors/Accelerometer.hpp`,
`cna/include/Microsoft/Xna/Framework/GamerServices/Guide.hpp`), not to anything derived from the
root-level `.cs` files. `cna`'s `CNA_GRAPHICS_SOURCE_DIR` is added as a subdirectory and its
`include/` is put on the include path in `CMakeLists.txt:75-76`. The `.cs` files and the `.hpp`
files that the C++ build actually consumes merely happen to share the same namespace and class
names — the header content itself is unrelated to and considerably more elaborate than the C#
(see "How the C++ port actually diverged" below).

Put together: these ten files are **residual C# source, not part of any build path, current or
historical, that this repository's own tooling exercises**. They are best understood as artifacts
left over from the ILSpy-decompilation stage of the porting pipeline described in `README.md` and
`CLAUDE.md` — kept in the repository (deliberately or by omission) rather than deleted once the
C++ equivalents existed.

## The migration pipeline these files are evidence of

`mobile-eggbert`'s `README.md` states the transformation chain plainly:

*From `README.md:3-9`:*
```markdown
Mobile Eggbert is a modified version of Speedy Blupi, originally developed for Windows Phone and
released in 2013. The project underwent the following transformations:

- decompiled by the ILSpy to the C# source code
- migrated from XNA 4.0 to Monogame
- migrated from C# to C++
- migrated from Monogame to CNA
```

`CLAUDE.md` (the project's own AI-assistant guidance file, not this book's) restates the same
chain in one sentence:

*From `CLAUDE.md:5-6`:*
```markdown
The port path was: original C# → decompiled with ILSpy → migrated to MonoGame → migrated to C++
→ migrated from MonoGame to **CNA**.
```

[ILSpy](https://github.com/icsharplib/ILSpy) is an open-source .NET decompiler. Applying it to the
original Windows Phone 7 XNA game's compiled assembly (a `.xap`/`.dll`) does not recover the
*original* handwritten source — it reconstructs C# source code that is behaviorally equivalent to
the compiled IL, complete with whatever the decompiler chooses for naming, formatting, and
handling of compiler-generated constructs. The result is exactly what these ten files look like:
plausible, compilable-looking C#, occasionally with small tells that betray either
machine-assisted reconstruction or a deliberately minimal placeholder rather than a hand-authored
original (see the `TrialMode`/`Guide` mismatch below).

The ten files fall into two of the four groups the transformation implies:

1. **Metadata carried straight through from the compiled assembly** — `Properties/AssemblyInfo.cs`.
2. **Platform-service stand-ins for Windows Phone-specific XNA extension namespaces** — the
   `Microsoft.Xna.Framework.GamerServices` and `Microsoft.Devices.Sensors` files.

Nothing under `Content/`, `worlds/`, or the game's actual simulation logic exists in `.cs` form in
this repository — those presumably lived in `mobile-eggbert-legacy` (or an even earlier decompiled
snapshot) and were fully translated to `Decor.cpp`/`Tables.cpp`/etc. before this repository's
current single commit was made. What's left here is specifically the thin platform-integration
edge of the original game: assembly metadata and two Windows Phone system-service surfaces
(trial-mode/marketplace gating and the accelerometer).

## `Properties/AssemblyInfo.cs`: the compiled assembly's own metadata

*From `Properties/AssemblyInfo.cs:1-41`:*
```csharp
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Resources;

//[assembly: AssemblyTitle("Speedy Blupi")]
//[assembly: AssemblyProduct("Speedy Blupi")]
[assembly: AssemblyDescription("")]
[assembly: AssemblyCompany("Dada Games")]
[assembly: AssemblyCopyright("Copyright © 2013")]
[assembly: AssemblyTrademark("")]
[assembly: AssemblyCulture("")]
[assembly: NeutralResourcesLanguage("en-US")]

[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
[assembly: CompilationRelaxations(8)]

[assembly: ComVisible(false)]

[assembly: Guid("4b6c546f-6967-447a-8eda-c3236043dcf7")]

[assembly: AssemblyVersion("1.0.0.5")]
[assembly: AssemblyFileVersion("1.0.0.0")]
```

This is a standard Visual Studio-generated `AssemblyInfo.cs` — every .NET assembly compiled with
the classic (`AssemblyInfo.cs`-based, pre-SDK-style) project format carries one. It is pure
metadata, never executed logic: attributes decorating the assembly itself rather than any type
within it. A few details are genuinely informative about the original game's provenance:

- **`AssemblyCompany("Dada Games")`** and **`AssemblyCopyright("Copyright © 2013")`** independently
  corroborate the "2013 Windows Phone release" dating given in `README.md` and this book's
  [Chapter 1](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md) — this is the
  original publisher's own compiled-in copyright string, not something reconstructed after the
  fact. ("Dada Games" is a studio name distinct from Epsitec SA, the entity this book's
  [Chapter 3](../part01-origins-and-ecosystem/ch03-license-and-provenance.md) identifies from the
  `LICENSE` file — consistent with Speedy Blupi's original Epsitec-authored PC release having been
  licensed out to a separate studio, Dada Games, for the 2013 Windows Phone port.)
- **The two commented-out lines** (`AssemblyTitle`, `AssemblyProduct`, both naming "Speedy Blupi")
  are a small, telling detail: ILSpy reconstructs a plausible C# source form of the compiled
  attributes it finds, and ILSpy itself does not comment out attributes it successfully decompiles.
  A commented-out `AssemblyTitle`/`AssemblyProduct` pair sitting right next to five *uncommented*
  attributes reads as a manual edit made to the decompiled output at some point after
  decompilation — plausibly to avoid the string "Speedy Blupi" surfacing directly in a rebuilt
  assembly's file properties while the port was mid-flight and being rebranded to "Mobile
  Eggbert," though this repository offers no commit history to confirm the reason with certainty.
- **`AssemblyVersion("1.0.0.5")`** vs. **`AssemblyFileVersion("1.0.0.0")`** — a mismatch between the
  two most common .NET versioning attributes. This is unremarkable in isolation (many real-world
  projects bump one without the other), but combined with the commented-out title/product lines it
  reinforces that this file was hand-touched after ILSpy produced it, not left byte-for-byte as the
  decompiler emitted it.

None of this metadata has any C++ equivalent in `mobile-eggbert` — a C++ executable has no
assembly-attribute concept, and nothing in `Game1.cpp`, `Program.cpp`, or any build script reads
company/copyright/version strings from this file. It survives purely as a documentary trace of the
original compiled binary's own self-description.

## `Microsoft.Xna.Framework.GamerServices`: trial mode and the marketplace overlay

`GamerServices` was Microsoft's XNA namespace for Xbox LIVE and Windows Phone Marketplace
integration — sign-in, achievements, and, relevant here, the trial-mode gating that let a game
ship as a free, time/feature-limited trial with an in-game upsell to the full paid version through
the phone's Marketplace app. Two files remain from it.

### `Guide.cs` — the system overlay entry point

*From `Microsoft.Xna.Framework.GamerServices/Guide.cs:1-13`:*
```csharp
using System.Diagnostics;

namespace Microsoft.Xna.Framework.GamerServices
{
    public static class Guide
    {
        public static void Show(PlayerIndex playerIndex)
        {
            Debug.Write("The Market Place should now be shown.");
        }
        public static bool IsTrialMode { get; set; }
    }
}
```

In real XNA, `Microsoft.Xna.Framework.GamerServices.Guide` is a large static class exposing the
platform's system UI: message boxes, the on-screen keyboard, achievements, friends lists, and, on
Windows Phone, `Guide.ShowMarketplace(PlayerIndex)` — the API a trial-mode game calls to launch the
phone's Marketplace app directly to this game's purchase page. This decompiled stub reduces all of
that to two members: a `Show(PlayerIndex)` method that does nothing but write a debug string
(clearly a placeholder standing in for the real `ShowMarketplace` call — the string it logs says as
much), and a settable `IsTrialMode` boolean.

This is a **minimal stand-in, not a faithful decompilation of a fully-featured class** — genuine
ILSpy output for the real `Guide` class (which in the actual XNA Framework redistributable is a
large surface with dozens of members) would not collapse to two members. It is more likely a
deliberately trimmed placeholder — either a stub ILSpy produced against a smaller closed-source
proxy assembly the original build linked against, or a manually reduced file kept only for the
narrow purpose this game actually exercised (checking and toggling trial mode) — than a literal
decompilation of the full Microsoft-shipped `GamerServices.dll`.

### `TrialMode.cs` — expiration-timer logic that never made it into C++

*From `Microsoft.Xna.Framework.GamerServices/TrialMode.cs:1-30`:*
```csharp
using System;
using System.IO;

namespace Xna.Framework.GamerServices
{
    internal class TrialMode
    {
        private static DateTime trialStartTime;

        public static void InitializeTrialMode()
        {
            // Assuming trial mode starts when the game is launched
            trialStartTime = DateTime.Now;
        }

        public static bool IsTrialModeExpired()
        {
            return IsTrialMode7DaysLimitExpired() || IsTrialMode10MinutesLimitExpired();
        }
        private static bool IsTrialMode10MinutesLimitExpired()
        {
            // Example: Trial expires after 10 minutes
            var expired = (DateTime.Now - trialStartTime).TotalMinutes > 10;
            return expired;
        }
```

Two details are worth flagging carefully rather than skating past.

First, the **namespace is wrong**: `namespace Xna.Framework.GamerServices` (`TrialMode.cs:4`) —
missing the `Microsoft.` prefix that every other file in this group, and every real Microsoft XNA
namespace, uses (`Guide.cs`'s own namespace is the correctly-prefixed
`Microsoft.Xna.Framework.GamerServices`). A genuine ILSpy decompilation of a class living in the
real `GamerServices` assembly would never produce this — ILSpy reads the namespace directly out of
the compiled metadata, verbatim. A missing `Microsoft.` prefix is far more consistent with this
file having been *written* (by a developer, or generated by a tool other than a straight
decompiler) rather than *decompiled* from Microsoft's actual shipped assembly.

Second, the code's own comments are unusually self-aware for shipped game logic: `// Assuming
trial mode starts when the game is launched` and `// Example: Trial expires after 10 minutes` read
like a scaffold or an illustrative example rather than a finished, calibrated business rule — a "10
minutes" trial-play limit alongside a separate "7 days" limit (`IsTrialMode7DaysLimitExpired`,
persisted by writing a `trialEndTime.txt` file to disk) is a plausible *shape* for Windows
Phone/Marketplace trial gating, but the specific numbers and the "Assuming"/"Example" phrasing
suggest this file may be a reconstructed or hand-written approximation of the original trial logic
rather than a literal decompilation of Dada Games' actual, precisely-tuned trial rule.

Whatever `TrialMode.cs`'s exact origin, its logic did **not** carry forward into the C++ port. The
current game does track a trial-mode concept — `Game1.hpp` declares `isTrialMode` and
`simulateTrialMode` fields (`Game1.hpp:243`, `Game1.hpp:255`) and `Game1::getIsTrialModeProperty()`
(`Game1.cpp:103`) always returns `false` outright, with the real signal instead read from
`Microsoft::Xna::Framework::GamerServices::Guide::getIsTrialModeProperty()`
(`Game1.cpp:1021`) — but that C++ `Guide` (in `cna`, not this repository) exposes trial mode as a
plain settable boolean flag (`Guide.hpp:55-62`, `getIsTrialModeProperty`/`setIsTrialModeProperty`),
with no `DateTime`-based 7-day/10-minute expiration timer anywhere in its interface. The
timer-based expiration logic that `TrialMode.cs` implements has no C++ counterpart at all — it is
the one piece of this residual C# that appears to have been dropped outright during the port,
consistent with a modern free redistribution of Mobile Eggbert having no reason to reintroduce a
Windows Phone Marketplace trial-expiration mechanic in the first place.

## `Microsoft.Devices.Sensors`: the accelerometer surface

Windows Phone's `Microsoft.Devices.Sensors` namespace exposed the phone's motion sensors —
accelerometer, compass, gyroscope — through a small, consistent pattern: a generic
`SensorBase<TSensorReading>` base class, a per-sensor concrete subclass (`Accelerometer`), a
reading struct implementing a shared `ISensorReading` interface, and a matching failure-exception
type. Mobile Eggbert only ever used the accelerometer (for tilt-based movement input — see
[Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md)), and only the
accelerometer's supporting types were kept.

### `ISensorReading.cs` — the shared reading contract

*From `Microsoft.Devices.Sensors/ISensorReading.cs:1-10`:*
```csharp
using System;

namespace Microsoft.Devices.Sensors

{
    public interface ISensorReading
    {
        DateTimeOffset Timestamp { get; }
    }
}
```

The entire interface is one property: every sensor reading, whatever sensor produced it, carries a
timestamp of when it was captured. (Note the blank line between the `namespace` declaration and
its opening brace — a small formatting artifact recurring across several of these files, another
mild tell of decompiler/tool output rather than typical hand-formatted C#.)

### `SensorBase.cs` — the generic sensor lifecycle

*From `Microsoft.Devices.Sensors/SensorBase.cs:1-14`:*
```csharp
using System;

namespace Microsoft.Devices.Sensors
{
    public abstract class SensorBase<TSensorReading> : IDisposable where TSensorReading : ISensorReading
    {
        private TSensorReading currentValue;

        public event EventHandler<SensorReadingEventArgs<TSensorReading>> CurrentValueChanged;

        public void Dispose()
        {
        }
    }
}
```

A generic abstract base parameterized on the reading type, implementing `IDisposable` (a no-op
`Dispose()` here) and exposing a `CurrentValueChanged` event — the mechanism by which a game
subscribes to a stream of new sensor readings as they arrive, rather than polling. `currentValue`
is stored but this stub never actually assigns or exposes it through a getter; a real
implementation would back a `CurrentValue` property with this field.

### `Accelerometer.cs` — the concrete sensor, reduced to nothing

*From `Microsoft.Devices.Sensors/Accelerometer.cs:1-10`:*
```csharp
using Microsoft.Devices.Sensors;

namespace Microsoft.Devices.Sensors
{
    public class Accelerometer : SensorBase<AccelerometerReading>
    {
        public void Start() { }
        public void Stop() { }
    }
}
```

This is the starkest stub in the set: `Start()` and `Stop()` are both empty method bodies. The real
Windows Phone `Accelerometer.Start()` opens the hardware sensor and begins raising
`CurrentValueChanged` at a platform-defined interval; here, calling `Start()` does nothing
observable at all — no hardware is opened, no event is ever raised, `CurrentValueChanged`
(inherited from `SensorBase<T>`) is declared but never invoked anywhere in this file. As a
decompilation of a real, functioning sensor class this would be implausible; as a deliberately
reduced placeholder retained only to satisfy references elsewhere in the (now-superseded) C# code,
it makes sense — a stub whose entire purpose was to let calling code compile and run harmlessly on
a desktop/emulator target with no real accelerometer attached.

### `AccelerometerReading.cs` and `SensorReadingEventArgs.cs` — the data shapes

*From `Microsoft.Devices.Sensors/AccelerometerReading.cs:1-12`:*
```csharp
using System;
using Microsoft.Xna.Framework;

namespace Microsoft.Devices.Sensors

{
    public struct AccelerometerReading : ISensorReading
    {
        public Vector3 Acceleration { get; internal set; }
        public DateTimeOffset Timestamp { get; internal set; }
    }
}
```

A single reading: a 3-axis `Vector3` acceleration value (reusing XNA's own `Vector3` type — one of
the few points where this sensor namespace directly depends on the core `Microsoft.Xna.Framework`
namespace) plus the `Timestamp` required by `ISensorReading`. Both properties use `internal set` —
only code inside the same assembly (i.e., the sensor implementation itself) can construct a
populated reading; consuming game code can only read it. This is a `struct`, not a `class`,
matching real XNA's own value-type `AccelerometerReading`.

*From `Microsoft.Devices.Sensors/SensorReadingEventArgs.cs:1-10`:*
```csharp
using System;

namespace Microsoft.Devices.Sensors
{

    public class SensorReadingEventArgs<T> : EventArgs where T : ISensorReading
    {
        public T SensorReading { get; set; }
    }
}
```

The generic `EventArgs` wrapper that carries a reading through `SensorBase<T>.CurrentValueChanged`
— unlike `AccelerometerReading`'s properties, this one uses a plain public `set`, not `internal
set`, a minor inconsistency with the access-control discipline the reading struct itself follows.

### The exception pair

*From `Microsoft.Devices.Sensors/SensorFailedException.cs:1-8`:*
```csharp
using System;

namespace Microsoft.Devices.Sensors
{
    public class SensorFailedException : Exception
    {
    }
}
```

*From `Microsoft.Devices.Sensors/AccelerometerFailedException.cs:1-6`:*
```csharp
namespace Microsoft.Devices.Sensors
{
    public class AccelerometerFailedException : SensorFailedException
    {
    }
}
```

A generic `SensorFailedException` (extending `System.Exception` with no added members) and an
`Accelerometer`-specific subclass extending it. This mirrors the real Windows Phone SDK's own
exception hierarchy — every sensor type gets its own failure exception, all rooted in a shared
base — but here, since `Accelerometer.Start()`/`Stop()` are empty no-ops that never throw
anything, neither exception type is ever actually raised by this stub set. They exist purely as
declared types that calling code could `catch`, matching the shape of the real API's contract
without implementing its failure behavior.

## How the C++ port actually diverged from these stubs

The single most informative fact about this group of files is not in anything they contain, but in
how dramatically more capable their C++ namesakes turned out to be. As established above, the
actual C++ game reaches `Microsoft::Devices::Sensors::Accelerometer` and
`Microsoft::Xna::Framework::GamerServices::Guide` through headers in the sibling `cna` repository —
and those headers are not thin translations of the stubs above. `cna`'s
`Accelerometer.hpp` (76 lines longer than reproduced here, in
`cna/include/Microsoft/Devices/Sensors/Accelerometer.hpp`) implements a real SDL3-backed sensor
subsystem — `SDL_InitSubSystem(SDL_INIT_SENSOR)` bookkeeping shared and reference-counted across
every `Accelerometer` instance, thread-safe dispatch of `CurrentValueChanged`, a whole family of
`ForTesting`-suffixed hooks for headless test injection, and a documented thread-safety contract —
a world away from `Accelerometer.cs`'s two empty method bodies. Likewise `cna`'s `Guide.hpp`
implements dozens of members (message boxes, on-screen keyboard input, notification positioning,
achievements) against real rendering/input plumbing, not the two-member placeholder in `Guide.cs`.

This divergence supports the framing given at the top of this chapter: the `.cs` files are not a
faithful specification the C++ port implemented against line-by-line. They are early-stage,
partial placeholders from the C#/MonoGame phase of the pipeline — retained in this repository as
what looks like leftover scaffolding — while the actual, load-bearing implementation of these XNA
Windows-Phone-extension namespaces was built fresh, and considerably more completely, directly in
C++ as part of the `cna` framework this book's [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md)
covers.

## Why these files are likely still present

Nothing in the repository states an explicit reason for keeping ten unused `.cs` files around, and
this book does not speculate beyond what the evidence supports. Two explanations are consistent
with everything observed above and are not mutually exclusive:

- **Reference material during the port.** Even a stub as thin as `Accelerometer.cs` documents the
  original API's *shape* — method names, the `SensorBase<T>` inheritance pattern, which exceptions
  exist — which is exactly the information someone re-implementing the same surface in C++ (in
  `cna`, matching XNA's real API one-to-one, per this project's own `CLAUDE.md`) would want kept
  close at hand rather than re-derived from documentation or memory.
- **Overlooked cleanup.** A single squashed commit gives no evidence either way of whether these
  files were *deliberately* retained for the reason above, or simply never removed once their
  purpose was served. Given the repository's own `CLAUDE.md` explicitly instructs contributors to
  add missing XNA/.NET surface to `sharp-runtime` or `cna` rather than "work around it in-place"
  (`CLAUDE.md:27-29`), it is plausible these files are simply pre-that-discipline leftovers.

## Future work: comparing against `mobile-eggbert-legacy`

`README.md` and this book's own project plan both reference a separate `openeggbert/mobile-eggbert-legacy`
repository as the intermediate, decompiled/MonoGame-era C# codebase this project's C++ was ported
from. That repository was not present as a local clone in this book-writing session
(`/workspace/mobile-eggbert-legacy` does not exist), and per this project's own methodology, this
chapter does not speculate about its contents beyond what `mobile-eggbert`'s own files and build
system already prove. A genuinely deeper historical account — confirming whether these exact ten
files also appear there, whether `mobile-eggbert-legacy` has a fuller (non-squashed) commit history
that dates when each stub was introduced or superseded, and whether a *complete* set of
Windows-Phone-era C# decompiled sources (well beyond just `GamerServices`/`Sensors`) exists there —
is left as a follow-up for a future session with access to that repository.

## See also

- [Chapter 1: What Is Mobile Eggbert](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md) — the Speedy Blupi → Windows Phone/XNA → ILSpy → MonoGame → C++ → CNA history in full
- [Chapter 3: License and Provenance](../part01-origins-and-ecosystem/ch03-license-and-provenance.md) — Epsitec SA vs. Dada Games authorship
- [Chapter 14: The XNA API via CNA](../part03-architecture/ch14-xna-api-via-cna.md) — how the C++ port maps onto XNA-style APIs generally
- [Chapter 41: InputPad — Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) — how the real, working C++ accelerometer input is consumed by gameplay
- [Chapter 56: .NET and XNA Migration](ch56-dotnet-and-xna-migration.md) — the broader migration chain these stubs are one small piece of
