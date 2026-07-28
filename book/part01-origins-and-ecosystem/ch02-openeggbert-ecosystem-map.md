# Chapter 2: The OpenEggbert Ecosystem Map

`mobile-eggbert` does not exist in isolation. It is one repository inside the **OpenEggbert**
GitHub organization, which hosts several related projects that together make up the game's
technical lineage and its runtime dependencies. This chapter is deliberately short: per this
book's scope (see `CLAUDE.md`), the surrounding ecosystem is covered only to the depth needed to
understand what `mobile-eggbert`'s own code depends on and where it came from. Anything deeper —
in particular a real architectural tour of the CNA framework — belongs to the sister project
`cna-bible`, not here.

A guiding rule for this chapter: every repository described below is described only as far as this
book's actual source access allows. Where a repository is not present in the material this book was
written from, that is stated plainly rather than guessed at.

## `cna` — the framework mobile-eggbert runs on

`cna` is the C++ framework that `mobile-eggbert` currently runs on top of, having arrived there via
the fourth migration step described in [Chapter 1](ch01-what-is-mobile-eggbert.md) (MonoGame →
CNA). `README.md` describes it in one line: "CNA is XNA-like wrapper around the SDL 3
(cross-platform software development library)." Looked at from `mobile-eggbert`'s side, CNA
supplies the entire `Microsoft::Xna::Framework` namespace tree that the game's code includes and
calls — `Game`, `GraphicsDeviceManager`, `SpriteBatch`, `GameTime`, `ContentManager`, the input
classes under `Microsoft::Xna::Framework::Input`, and so on — reimplemented in C++ over a pluggable
graphics backend layer (SDL_Renderer, EasyGL/OpenGL, Vulkan, Direct3D 11/12, and several more,
selectable at CMake configure time via `-DCNA_GRAPHICS_BACKEND=<name>`, as documented in
`mobile-eggbert`'s own `README.md`). `mobile-eggbert`'s `CLAUDE.md` locates the sibling checkout at
`../cna` relative to the game and points to `cna`'s own `CLAUDE.md` for "CNA-specific coding rules
(namespaces, XNA API compliance, C# property conventions, type aliases, events, visibility
mapping, etc.)" — rules that exist precisely so that `mobile-eggbert`'s ported C++ code can call
CNA exactly as a 2013 XNA game would have called the real Microsoft framework. **This book does not
describe how CNA implements any of that internally** — how a given backend turns a `SpriteBatch`
draw call into GPU commands, for instance, is out of scope here. [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md)
covers, in the only depth this book goes to, which parts of that API surface `mobile-eggbert`'s own
code actually touches. For CNA's own architecture, backends, and supporting libraries, see
`cna-bible`.

## `sharp-runtime` — the .NET base types CNA and mobile-eggbert build on

Underneath even the XNA-shaped surface, both CNA and `mobile-eggbert` depend on a second sibling
library: `sharp-runtime`, a C++ reimplementation of .NET base-class-library types. `mobile-eggbert`'s
own `CLAUDE.md` names it directly and locates it alongside `cna`:

*From `CLAUDE.md:14-18` (mobile-eggbert's own CLAUDE.md):*

```markdown
**SharpRuntime** is the C++ reimplementation of .NET base-class types (System.Math, System.String,
EventHandler, IDisposable, primitive type aliases, etc.). It lives at:
```

The same file states the dependency rule plainly: "If something needed by this project or by CNA
does not yet exist in sharp-runtime, it must be added to sharp-runtime — not worked around
in-place," and gives concrete examples of what belongs there — ".NET primitive type aliases
(`bytecs`, `intcs`, `String`, etc.)", "`System.*` classes or interfaces (`IDisposable`, `Math`,
`Random`, `EventHandler<T>`, ...)", and "any BCL behaviour required for correct XNA API compliance."
In practice, this is why `mobile-eggbert`'s own code reads like C# in places even at the level of
individual types — `intcs` instead of `int`, `string` (lowercase, aliased) instead of
`std::string`, `System::EventArgs`, `System::TimeSpan`, and so on, all seen throughout the excerpts
in this book's architecture chapters. Those are `sharp-runtime` types, not ad hoc porting
shortcuts. As with CNA, this book treats `sharp-runtime`'s own implementation as out of scope; it is
mentioned here only because `mobile-eggbert`'s code visibly depends on it.

## `mobile-eggbert-core` — the intermediate MonoGame/C# stage

`README.md` names the exact repository and commit that the C++ source in this project was derived
from:

*From `README.md:13-15`:*

```markdown
The C++ source code was created using the following Git commit of the Git repository mobile-eggbert-core:

https://github.com/openeggbert/mobile-eggbert-core/commit/1cbc13415b768085b7f5c97fbf35a773d7f14a8e
```

`mobile-eggbert-core` represents the codebase after the first two transformations described in
[Chapter 1](ch01-what-is-mobile-eggbert.md) — ILSpy decompilation to C#, then migration from XNA
4.0 to MonoGame — and before the third (the rewrite to C++). It is, in other words, the direct
input to the C++ port this book documents. This book's own source access does not include a
checkout of `mobile-eggbert-core` itself; what can be verified is only its name, its role, and the
specific commit hash pinned in `README.md` above.

## `mobile-eggbert-legacy` — the decompiled C# origin, in this book's context

A second, related name appears in `mobile-eggbert`'s own analysis documents: `mobile-eggbert-legacy`.
`AUDIO_ANALYSIS.md` cites it directly when comparing the ported `Sound` class against its ancestor:

*From `AUDIO_ANALYSIS.md:38`:*

```markdown
source (`mobile-eggbert-legacy/mobile-eggbert-core/Sound.cs:58`) and is **identical**. A handful
```

The citation path (`mobile-eggbert-legacy/mobile-eggbert-core/Sound.cs`) indicates that, at least
for the purposes of that analysis, `mobile-eggbert-legacy` is the local working name for a checkout
that contains the `mobile-eggbert-core` C# source tree — i.e., the decompiled/MonoGame-era origin
described above, kept around specifically so that later engineering work on the C++ port can be
checked line-by-line against the original C#. This is exactly the kind of comparison this book's
own methodology depends on for its own migration chapters: [Part XI](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
covers the ILSpy decompilation and the residual C# stubs still present in `mobile-eggbert` (the
`Microsoft.Xna.Framework.GamerServices/` and `Microsoft.Devices.Sensors/` directories) in the depth
this history deserves. This chapter does not attempt to describe `mobile-eggbert-legacy`'s
structure or contents beyond what the citation above already shows; Part XI cites it further only
where a session had direct access to the corresponding source.

## `mobile-eggbert-libgdx` — an archived alternate port (unverified here)

The OpenEggbert organization's repository listing includes a project named
`mobile-eggbert-libgdx`, described there as **archived**. Beyond that name and status, this chapter
makes no further claims about it: it is not referenced anywhere in `mobile-eggbert`'s own
`README.md`, `CLAUDE.md`, or analysis documents, and this book's source access does not include a
checkout of it. Rather than speculate about what a libGDX-based alternate port might contain (libGDX
is a Java/Kotlin game framework, which would imply a substantially different technology stack from
either the original XNA/C# game or this C++ port, but that inference is not confirmed by any source
this book can cite), this chapter simply records its existence and archived status and marks its
contents as out of scope and unverified. If a future session gains access to that repository, it
belongs in [Appendix F — Repository Map](../appendices/appendix-f-repository-map.md), not
retrofitted into this chapter as if it had been read.

## `galaxy-eggbert` — a 3D remake (see also, not in scope)

Also part of the wider OpenEggbert ecosystem is `galaxy-eggbert`, understood to be a full 3D remake
of the Blupi game concept rather than a port of the original 2D Speedy Blupi. Like
`mobile-eggbert-libgdx`, it falls outside this book's source access and outside its scope — this
book is about the 2D, tile-based `mobile-eggbert` port specifically. It is mentioned here purely as
a "see also" pointer for readers curious about where the wider Blupi/Eggbert lineage has gone since;
no further claims about its architecture, engine, or status are made in this book.

## How the pieces fit together

To summarize the dependency and lineage relationships this chapter has established, all grounded in
material `mobile-eggbert`'s own source tree actually references:

| Repository | Relationship to `mobile-eggbert` | Depth in this book |
|---|---|---|
| `cna` | Runtime framework `mobile-eggbert` builds on (XNA-shaped API over SDL3) | Marginal — only what `mobile-eggbert` calls; see [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md) |
| `sharp-runtime` | Supplies .NET base-class types (`intcs`, `string`, `EventHandler`, etc.) used throughout | Marginal — mentioned wherever a type originates there |
| `mobile-eggbert-core` | Direct C# source input to the C++ port (pinned commit in `README.md`) | Named/cited only; not separately checked out |
| `mobile-eggbert-legacy` | Local name for a checkout containing the decompiled/MonoGame-era C# source, used for line-by-line comparison | Covered in depth in [Part XI](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md) |
| `mobile-eggbert-libgdx` | An archived alternate port (per the org's repo listing) | Out of scope / unverified in this book |
| `galaxy-eggbert` | A full 3D remake of the Blupi concept | Out of scope — "see also" only |
| `cna-bible` | Sister book covering CNA's own internals in depth | Not a source repository — referenced as further reading |

The rest of this book stays firmly on the `mobile-eggbert` side of every boundary in that table.
When later chapters need to mention CNA or `sharp-runtime`, they will do so the same way this
chapter has: naming exactly what `mobile-eggbert`'s code calls, and pointing elsewhere for more.

## See also

- [Chapter 1 — What Is Mobile Eggbert](ch01-what-is-mobile-eggbert.md)
- [Chapter 3 — License and Provenance](ch03-license-and-provenance.md)
- [Chapter 14 — The XNA API via CNA](../part03-architecture/ch14-xna-api-via-cna.md)
- [Chapter 55 — ILSpy Decompilation and C# Stubs](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
- [Appendix F — Repository Map](../appendices/appendix-f-repository-map.md)
