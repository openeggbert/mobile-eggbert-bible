# Chapter 56: The .NET and XNA Migration

## What `.Net and XNA used part.md` actually contains

The repository ships a file named `.Net and XNA used part.md` (the space-containing filename is
exact — this is not a typo introduced by this book). Read in full, here is the entirety of its
content:

*From `.Net and XNA used part.md:1-5`:*
```markdown
# .Net and XNA used part

## .Net

## XNA
```

That is the whole file: a title and two empty section headings, with no body text under either
one. This is stated plainly and without embellishment because it is a real, verifiable fact about
the current state of the repository's own documentation, not a gap in this book's research. A file
whose name promises exactly the topic of this chapter turns out to be an unfilled placeholder —
presumably scaffolded by whoever authored the project's documentation set with the intention of
eventually writing a dedicated `.NET` section and a dedicated `XNA` section, and never populated
before the commit this book was written against (`07e0a67`).

Rather than pad that emptiness with speculation, this chapter builds its actual content from three
things that *do* exist and are directly readable: the migration chain `README.md` states, the
concrete pattern of XNA-namespace usage inside `mobile-eggbert`'s own `.hpp`/`.cpp` files, and what
that usage pattern reveals about how thoroughly (or not) XNA's API surface was carried across the
port.

## The migration chain, as the project itself states it

`README.md` gives the chain in five stages:

*From `README.md:3-9`:*
```markdown
Mobile Eggbert is a modified version of Speedy Blupi, originally developed for Windows Phone and
released in 2013. The project underwent the following transformations:

- decompiled by the ILSpy to the C# source code
- migrated from XNA 4.0 to Monogame
- migrated from C# to C++
- migrated from Monogame to CNA

CNA is XNA-like wrapper around the SDL 3 (cross-platform software development library).
```

Two migrations are named here, and they are different in kind:

1. **XNA 4.0 → MonoGame** — a same-language (C#), API-compatible reimplementation swap.
   [MonoGame](https://www.monogame.net/) exists specifically to let XNA 4.0 games keep running as
   Microsoft's own XNA Framework was discontinued (the last official XNA release was XNA 4.0,
   2010); MonoGame re-implements the same namespaces (`Microsoft.Xna.Framework.*`) against SDL/GL
   instead of Microsoft's original DirectX-based runtime. A game ported this way changes almost no
   source code — it relinquishes its dependency on the discontinued official runtime while keeping
   its entire API surface.
2. **MonoGame → CNA, alongside C# → C++** — a language change *and* a runtime change happening
   together. `CNA` (the C++ framework this book covers only marginally per its own scope rules —
   see [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md) for what mobile-eggbert
   actually calls) re-implements the same `Microsoft.Xna.Framework`-shaped API surface, but as C++
   classes, on top of SDL 3 directly rather than on top of MonoGame. `README.md`'s own one-line
   summary — "CNA is XNA-like wrapper around the SDL 3" — is the most precise short description of
   what CNA is *for* that exists anywhere in this repository.

`mobile-eggbert`'s own `CLAUDE.md` restates this chain even more tersely, and adds the one detail
`README.md` omits — that the decompilation tool was ILSpy specifically:

*From `CLAUDE.md:5-6`:*
```markdown
The port path was: original C# → decompiled with ILSpy → migrated to MonoGame → migrated to C++
→ migrated from MonoGame to **CNA**.
```

This book's [Chapter 55](ch55-ilspy-decompilation-and-csharp-stubs.md) covers the ILSpy
decompilation stage and its residual artifacts (the ten leftover `.cs` files) in depth. This
chapter's concern is the far side of that chain: what actually landed in C++, and how completely.

`README.md` additionally pins the exact commit the C++ source was created from, in a separate,
now-archived repository:

*From `README.md:13-15`:*
```markdown
The C++ source code was created using the following Git commit of the Git repository mobile-eggbert-core:

https://github.com/openeggbert/mobile-eggbert-core/commit/1cbc13415b768085b7f5c97fbf35a773d7f14a8e
```

This is a second, distinct predecessor repository from the `mobile-eggbert-legacy` one referenced
in [Chapter 55](ch55-ilspy-decompilation-and-csharp-stubs.md) — `mobile-eggbert-core` appears to be
the repository that housed the finished C++ port at the specific commit this project's own source
tree was seeded from, i.e. a snapshot dependency, not a submodule or ongoing upstream. Neither
`mobile-eggbert-core` nor `mobile-eggbert-legacy` was available as a local clone in this session, so
this chapter treats this URL as a citation of provenance only, not as source material to read.

## How much XNA-namespace usage actually remains in the C++ code

`README.md` calls CNA an "XNA-like wrapper," and the natural way to check how literally that holds
is to look at how mobile-eggbert's own `.hpp`/`.cpp` files actually reference the
`Microsoft::Xna::Framework` namespace. Grepping every header and source file under
`include/WindowsPhoneSpeedyBlupi/` and `src/WindowsPhoneSpeedyBlupi/` for
`Microsoft::Xna::Framework` or `Xna::Framework` turns up **89 matches across 14 distinct files**:

```
include/WindowsPhoneSpeedyBlupi/Game1.hpp
include/WindowsPhoneSpeedyBlupi/IGame1.hpp
include/WindowsPhoneSpeedyBlupi/IPixmap.hpp
include/WindowsPhoneSpeedyBlupi/InputPad.hpp
include/WindowsPhoneSpeedyBlupi/Misc.hpp
include/WindowsPhoneSpeedyBlupi/Pixmap.hpp
include/WindowsPhoneSpeedyBlupi/Sound.hpp
include/WindowsPhoneSpeedyBlupi/def/GameSpeed.hpp
src/WindowsPhoneSpeedyBlupi/Game1.cpp
src/WindowsPhoneSpeedyBlupi/InputPad.cpp
src/WindowsPhoneSpeedyBlupi/Misc.cpp
src/WindowsPhoneSpeedyBlupi/Pixmap.cpp
src/WindowsPhoneSpeedyBlupi/Sound.cpp
src/WindowsPhoneSpeedyBlupi/Worlds.cpp
```

That's 14 of the project's 34 header files and 16 `.cpp` files — a substantial fraction, and it
concentrates almost entirely (as one would expect) in the rendering, audio, and input layers,
which are exactly the parts of a game that talk directly to a platform framework rather than to
pure game logic. `Decor.cpp` (the 11,720-line gameplay-simulation core covered across
[Part IV](../part04-decor-simulation/ch15-decor-overview.md)) never appears in that file list at
all — the entire tile-simulation, physics, and AI layer is written against `mobile-eggbert`'s own
types (`TinyPoint`, `TinyRect`, `Def`, the `decor/` enums) with no direct XNA dependency, which is
itself informative: it shows the C++ port cleanly separated "platform/XNA-shaped plumbing" from
"portable gameplay logic," rather than threading XNA types throughout every layer.

Breaking down what's actually referenced, by sub-namespace and call frequency:

| Sub-namespace / type | Occurrences | Where |
|---|---|---|
| `Rectangle` | 15 | `Pixmap.cpp` almost exclusively — source/destination sprite rects |
| `GraphicsDeviceManager` | 7 | `Pixmap.hpp`/`.cpp`, `Game1.hpp`/`.cpp` — device/backbuffer setup |
| `GameTime` | 6 | `Game1.hpp`/`.cpp`, `IGame1.hpp` — the XNA `Update(GameTime)`/`Draw(GameTime)` pattern |
| `Graphics::SpriteSortMode`, `Graphics::BlendState` | 4 each | `Pixmap.cpp` — every `SpriteBatch::Begin()` call |
| `Audio::SoundEffect` | 4 | `Sound.hpp`/`.cpp` |
| `Input::Touch::TouchPanel` | 3 | `Pixmap.cpp`, `Game1.cpp` |
| `Graphics::GraphicsDevice` | 3 | `Pixmap.hpp`/`.cpp` |
| `Content::ContentManager` | 3 | asset loading paths |
| `Vector2`, `Input::Mouse`, `Input::Keys`, `Input::ButtonState`, `Graphics::Texture2D`, `Graphics::SpriteBatch`, `Game::Initialize`, `Color::White` | 2 each | scattered across `Pixmap`/`Game1`/`InputPad` |
| Everything else (`TitleContainer::OpenStream`, `PlayerIndex`, individual `Touch`/`Keys`/`Mouse` members, `GamerServices::Guide::*`, `Color::CornflowerBlue`/`FromNonPremultiplied`, `SpriteEffects`) | 1 each | one-off call sites |

A representative example of what this looks like in practice — `Pixmap`'s constructor takes an XNA
`GraphicsDeviceManager` by reference, exactly the signature an XNA 4.0 `Game`-derived class would
use:

*From `Pixmap.cpp:114-127`:*
```cpp
Pixmap::Pixmap(IGame1* game1, Microsoft::Xna::Framework::GraphicsDeviceManager& graphics) :
    ...
    origin(Microsoft::Xna::Framework::Vector2(0.0f, 0.0f))
{
    ...
    effect = Microsoft::Xna::Framework::Graphics::SpriteEffects::None;
```

And the sprite-batch pattern (`Begin`/`Draw`/`End`) is carried across verbatim, down to the same
enum values (`SpriteSortMode::BackToFront`, `BlendState::AlphaBlend`) an XNA 4.0 game would pass:

*From `Pixmap.cpp:362-363`:*
```cpp
spriteBatch->Begin(Microsoft::Xna::Framework::Graphics::SpriteSortMode::BackToFront,
                   Microsoft::Xna::Framework::Graphics::BlendState::AlphaBlend);
```

This is the concrete sense in which mobile-eggbert's C++ still *is* an XNA 4.0 game, architecturally
— not "inspired by" XNA, but written against a header-compatible re-implementation of XNA's actual
class names, method names, and even its historical enum values, fully qualified with the
`Microsoft::Xna::Framework::` namespace prefix throughout. A reader coming from XNA/MonoGame
experience would recognize every one of the calls above immediately; a reader with no XNA
background is, in effect, being shown 2010-era XNA idioms through a C++ lens.

## Even the state-machine's own interface is XNA-shaped

The pattern isn't confined to the obviously platform-facing files like `Pixmap.cpp`. `IGame1.hpp`
— the abstract interface `Game1` implements and every other subsystem calls back through (covered
in [Chapter 13](../part03-architecture/ch13-igame1-and-dependencies.md)) — declares its two most
central methods with XNA's own signatures verbatim:

*From `IGame1.hpp:132`:*
```cpp
virtual void Update(Microsoft::Xna::Framework::GameTime& gameTime) = 0;
```

*From `IGame1.hpp:179`:*
```cpp
virtual void Draw(const Microsoft::Xna::Framework::GameTime& gameTime) = 0;
```

`Update(GameTime)` / `Draw(GameTime)` is *the* defining method pair of an XNA 4.0 `Game`
subclass — every XNA or MonoGame tutorial ever written introduces exactly this pair, in exactly
this shape, as the first thing a new game class overrides. Seeing it survive not just in `Game1`
itself but in the abstract interface that decouples every other subsystem from `Game1` shows how
deep the XNA lifecycle model was carried into this C++ codebase: it isn't a compatibility shim
bolted onto an otherwise-independent architecture, it *is* the architecture's own top-level
contract.

Two smaller, more surgical examples round out the picture of how narrowly XNA types are pulled in
only where genuinely needed:

*From `def/GameSpeed.hpp:121-129`* uses `Microsoft::Xna::Framework::Input::Keys` purely to convert
a function-key press into a `GameSpeed` enum value — a single, self-contained conversion function
that needs XNA's key-code enum as input but has nothing else to do with rendering or the game
loop:
```cpp
static constexpr auto ToGameSpeed(const Microsoft::Xna::Framework::Input::Keys key) -> GameSpeed
{
    switch (key)
    {
        case Microsoft::Xna::Framework::Input::Keys::F5: ...
```

And `Misc::RotateAdjust` (covered in [Chapter 48](../part09-support-types/ch48-misc-utility-functions.md))
takes and returns an XNA `Rectangle` directly rather than this project's own `TinyRect`:

*From `Misc.hpp:67-68`:*
```cpp
[[nodiscard]] static Microsoft::Xna::Framework::Rectangle RotateAdjust(
    const Microsoft::Xna::Framework::Rectangle& rect,
```

— a reminder that `mobile-eggbert` maintains *two* rectangle types side by side (its own
lightweight `TinyRect`, described in [Chapter 47](../part09-support-types/ch47-tinypoint-tinyrect.md),
and XNA's `Rectangle` via CNA), choosing between them per call site depending on whether a given
function sits closer to the game's own internal data model or to an XNA-facing API boundary
(`SpriteBatch::Draw`, in `Rectangle`'s case, genuinely requires the XNA type).

## The rule that keeps the migration from drifting: sharp-runtime

One methodological detail from the project's own `CLAUDE.md` (not this book's) is directly
relevant to understanding why the migration reads as consistently XNA-faithful rather than as an
ad-hoc mix of "whatever was convenient in C++ at the time": a standing rule that any missing piece
of .NET base-class-library or XNA behavior must be added to a shared dependency, never
worked around locally.

*From `CLAUDE.md:27-29`:*
```markdown
**If something needed by this project or by CNA does not yet exist in sharp-runtime, it must be
added to sharp-runtime — not worked around in-place.**
```

`sharp-runtime` — a separate sibling repository providing C++ reimplementations of .NET primitives
(`System.Math`, `System.String`, `EventHandler<T>`, `IDisposable`, the `bytecs`/`intcs` type
aliases used throughout this codebase) — and `cna` together form the two shared dependencies that
absorb essentially all XNA/.NET-compatibility work, so that `mobile-eggbert` itself never needs to
invent a one-off local substitute for a missing framework type. This is the structural reason the
89 `Microsoft::Xna::Framework` call sites catalogued above look so uniformly faithful to real
XNA — they are not `mobile-eggbert`'s own approximation of XNA, they are calls into a shared,
disciplined re-implementation maintained one level down the dependency stack.

## One surprising survivor: `GamerServices::Guide` in live C++ code

Grepping specifically for `GamerServices` and `TrialMode` in the C++ tree turns up a detail worth
calling out on its own, because it directly connects this chapter to
[Chapter 55](ch55-ilspy-decompilation-and-csharp-stubs.md)'s residual C# files: the
Windows-Phone-era `Guide`/trial-mode concept did not just leave a dead stub behind — it survived
into live, currently-compiled C++ code.

*From `Game1.cpp:1021`:*
```cpp
isTrialMode = Microsoft::Xna::Framework::GamerServices::Guide::getIsTrialModeProperty();
```

*From `Game1.cpp:344`:*
```cpp
Microsoft::Xna::Framework::GamerServices::Guide::ShowMarketplace(PlayerIndex::One);
```

Both calls resolve to `cna`'s own `Guide` class (`cna/include/Microsoft/Xna/Framework/GamerServices/Guide.hpp`),
a considerably more complete re-implementation than the two-member `Guide.cs` stub discussed in
[Chapter 55](ch55-ilspy-decompilation-and-csharp-stubs.md) — but the *concept* being called, trial
mode with a Marketplace-launch upsell, is a straight carry-over from the original 2013 Windows
Phone Marketplace distribution model. `Game1::getIsTrialModeProperty()` itself, notably, is
hardcoded to always return `false` (`Game1.cpp:103`) in this build — meaning the trial-mode branch
exists in the code but is permanently dormant, an artifact of a distribution model (a
free-with-upsell trial gated by the Windows Phone Marketplace) that has no equivalent in Mobile
Eggbert's current open, cross-platform distribution. This is a clean example of what "migration"
looks like at the level of individual features, not just build systems: the *shape* of a
Marketplace-era mechanic was preserved faithfully enough to still compile and run, while the
mechanic itself was quietly neutralized rather than removed.

## What "XNA via CNA" means for reading the rest of this book

The practical upshot for a reader of this book, and the reason this chapter exists separately from
a deep dive into CNA's internals (which is out of this book's scope — see
[Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md) and `cna-bible` for that), is this:
almost every mobile-eggbert source file that touches rendering, audio, or input will contain
fully-qualified `Microsoft::Xna::Framework::...` names, and recognizing them as XNA's own historical
API — not a CNA-specific invention — is often the fastest way to understand what a given line of
code is doing, especially for a reader who has prior XNA or MonoGame experience. Conversely, a
reader unfamiliar with XNA does not need to learn CNA's internals to follow this book; they only
need to recognize that these fully-qualified names are a compatibility surface being called, in
the same spirit as calling any well-documented third-party library, and that `mobile-eggbert`'s own
gameplay logic (`Decor`, `Tables`, the `decor/` enums) deliberately sits one layer above that
surface and does not depend on it directly.

## See also

- [Chapter 1: What Is Mobile Eggbert](../part01-origins-and-ecosystem/ch01-what-is-mobile-eggbert.md) — the full Speedy Blupi → Windows Phone/XNA → ILSpy → MonoGame → C++ → CNA history
- [Chapter 14: The XNA API via CNA](../part03-architecture/ch14-xna-api-via-cna.md) — how mobile-eggbert's code maps onto the XNA-style API day to day
- [Chapter 55: ILSpy Decompilation and the Residual C# Stubs](ch55-ilspy-decompilation-and-csharp-stubs.md) — the leftover C# artifacts from the decompilation stage of this same migration chain
- [Chapter 12: Game1 — the State Machine](../part03-architecture/ch12-game1-state-machine.md) — `Game1`'s XNA `Game`-derived lifecycle in practice
