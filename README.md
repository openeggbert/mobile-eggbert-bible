# Mobile Eggbert Bible

An extensive, deep-dive technical book about the source code of **Mobile Eggbert** — a C++ port
of *Speedy Blupi* (originally a Windows Phone/XNA game, 2013), built on the
[CNA](https://github.com/openeggbert/cna) framework.

This book is about **`mobile-eggbert` itself** — every class, every file, every gameplay
mechanic, the level file format, the sprite/animation system (with real extracted sprite images),
the build system for every supported platform, and the history of the port from the original
C#/XNA codebase. CNA (the underlying framework) is covered only where necessary to understand
`mobile-eggbert`'s own code — a deep dive into CNA itself belongs to the sister project,
[`cna-bible`](https://github.com/openeggbert/cna-bible), whose methodology this book follows.

## Goal

After reading this book, the reader should understand the `mobile-eggbert` source code deeply
enough to navigate it like an expert: knowing where each gameplay mechanic lives, how the Blupi
character's state machine works, how level maps are stored, how the sprite atlases and animation
tables work (illustrated with real cropped sprite images extracted from the game's own assets),
how save games work, how audio and input work, and how the game is built and run on Linux,
Windows, the Web (Emscripten), and Android.

## Honest note on scope

The original ask was for a book "as long as a thousand pages." `mobile-eggbert` is about 31,000
lines of C++ (see `PLAN.md`) — one game, not an entire ecosystem. The sister book `cna-bible`,
which covers the **entire** CNA ecosystem (dozens of repositories), landed honestly at 233 pages
because its authors refused to pad the text with unsupported or repetitive filler just to hit a
page count. The same rule applies here: **no sentence without an actual source read.** We aim for
maximum honest depth (see `PLAN.md` for the current scope estimate) rather than artificial
padding. The addition of a fully illustrated sprite/animation catalog and (where technically
achievable) real screenshots substantially increases the book's genuine size beyond a text-only
estimate. The book is structured so it can keep growing across future sessions.

## Repository layout

- `book/` — the book itself, in Markdown. `book/SUMMARY.md` is the table of contents with each
  chapter's status. Chapters live under `book/partNN-slug/chNN-slug.md` across 11 parts (Part
  I–XI), plus `book/appendices/` (Appendices A–G).
- `book/images/` — real images used by the book: sprite crops extracted directly from the game's
  own `Content/icons/*.png` atlases, background art from `Content/backgrounds/`, data-driven level
  map renders, and (where achieved) real screenshots from a built/running copy of the game.
- `tools/` — scripts used to generate the images in `book/images/` (sprite-atlas extraction,
  level-map rendering), so the pipeline is reproducible against a fresh `mobile-eggbert` checkout.
- `PLAN.md` — the working plan: chapter list, target depth, methodology, open questions. The
  durable source of truth for what's left to write and why.
- `NEXT.md` — a short, current-state briefing for whichever session picks up work next. Read this
  first when resuming work.
- `PROGRESS.md` — historical log of completed work.

## Source repositories this book draws on

- [`openeggbert/mobile-eggbert`](https://github.com/openeggbert/mobile-eggbert) — the game itself (primary source)
- [`openeggbert/cna`](https://github.com/openeggbert/cna) — the CNA framework the game runs on (cited only where needed)
- [`openeggbert/cna-bible`](https://github.com/openeggbert/cna-bible) — style/methodology model
- [`openeggbert/mobile-eggbert-legacy`](https://github.com/openeggbert/mobile-eggbert-legacy) — the decompiled C# origin
