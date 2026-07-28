# Mobile Eggbert Bible — guide for Claude Code sessions

This repository is a single, unified Markdown book about `openeggbert/mobile-eggbert` (a C++ port
of *Speedy Blupi*, built on the CNA framework). It is written incrementally, across many sessions,
by Claude Code itself, under the direction of the repository's author. It is written in
**English**.

**Scope: this book is about `mobile-eggbert` only.** `cna` (the underlying framework) is covered
only marginally — enough for the reader to understand how `mobile-eggbert`'s own code uses it
(e.g. "this class overrides XNA's `Game.Update()`"), never as a deep dive into CNA's internals.
A deep dive into CNA itself is the sister project `cna-bible`'s job, not this book's. If a chapter
finds itself explaining how a CNA backend works internally, that's a scope violation — cut it back
to "what mobile-eggbert calls and why," and reference `cna-bible` for readers who want more.

**Start every session by reading `NEXT.md`**, not just this file — it carries the specific,
current-state context (what was just finished, what's in progress, what to do immediately next)
that this file deliberately does not repeat. Then read `PLAN.md` for the full task list and
per-chapter depth targets. `PROGRESS.md` is the historical log of everything completed before the
current phase; useful for background, not for "what's next."

## Repository layout

- `book/SUMMARY.md` — the table of contents for the whole book, with each chapter's status
  (`done` / `in progress` / `not written`). Update this whenever a chapter's status changes.
- `book/partNN-slug/chNN-slug.md` — individual chapters, numbered 1 through 58, across eleven
  parts (Part I–XI).
- `book/appendices/appendix-X-slug.md` — Appendices A–G (class/file catalog, enum catalog, level
  file format spec, glossary, cheat codes, repository map, screenshot/visual gallery).
- `book/images/*.png` — real images referenced by chapters. Never add a placeholder or
  AI-generated image here — see "Images and screenshots" below.
- `tools/*.py` — scripts that generate `book/images/*.png` from the actual `mobile-eggbert` assets
  (sprite-atlas extraction, level-map rendering). Keep these reproducible: a fresh session with a
  fresh `mobile-eggbert` checkout should be able to re-run them and get the same images.
- `PLAN.md` — the working plan: chapter list, target page depth, methodology, open
  questions/conflicts, a dated session log. The durable source of truth for what depth each
  chapter should target and why.
- `NEXT.md` — a short, current-state briefing for whichever session picks up work next. Update
  this at the **end** of every session (not just when a chapter finishes) so a fresh session with
  no memory of this conversation can resume correctly.
- `PROGRESS.md` — historical record of what was done in previous phases. Don't add new entries
  here as you go — new work goes in `PLAN.md`'s session log and in `NEXT.md`.

## Non-negotiable methodology (applies to the whole project, not just one phase)

- **Every claim is grounded in an actual source read.** Before writing a sentence about a class,
  method, constant, or mechanic, read the real `.hpp`/`.cpp`/`.txt`/`.md` file in the
  `mobile-eggbert` repository (or `cna`/`mobile-eggbert-legacy` where genuinely needed for
  context). Never paraphrase from memory or invent a plausible-sounding API you haven't verified.
- **Code examples must be real**, taken verbatim or near-verbatim from an actual file and line
  (cite as `file.cpp:NNN`), never invented from scratch.
- **Images and screenshots: real or not at all.** Never fabricate, mock up, or AI-generate an
  image presented as a sprite, animation frame, or screenshot. Every image in `book/images/` must
  be either:
  1. A pixel-accurate crop of a real sprite atlas shipped in `mobile-eggbert/Content/icons/` or
     `Content/backgrounds/`, produced by a script in `tools/` using the exact grid/offset
     algorithm read from `Pixmap.cpp` (`GetSrcRectangle`, the per-channel grid table in
     `Pixmap::DrawIcon`) — not guessed dimensions.
  2. A real screenshot captured from an actually-built, actually-running copy of the game (see
     "Attempting real screenshots" below) — never a mockup.
  3. A data-driven diagram built directly from real level files (`worlds/*.txt`) or real table
     data (`Tables.cpp`) — clearly labeled as a *reconstruction from real data*, not a screenshot,
     so the reader never mistakes it for rendered game output.
  If a real screenshot genuinely can't be captured, say so explicitly in the chapter text instead
  of silently omitting the topic or faking an image.
- **`ENUMS.md` in `mobile-eggbert` is a refactoring proposal, not existing code.** It documents
  magic numbers that *could* be replaced with enums, but those enums are **not** implemented —
  the code still uses raw integers (`68`, `91`, …) directly in conditionals. Any chapter citing
  `ENUMS.md` must clearly mark it as an analysis/proposal document, not a description of the
  code's current state.
- **Commit in small, descriptive increments and push after each one** — not one giant commit at
  the end of a session. This is what makes a multi-session project actually resumable.
- Cross-reference chapters as `[Chapter N](../partNN-slug/chNN-slug.md)` — relative Markdown
  links that work directly on GitHub.
- Cite specific files/lines from `mobile-eggbert` as `` `Decor.cpp:1234` `` — a plain text
  citation, not a hyperlink to a specific commit (which changes over time).

## Attempting real screenshots

The game can plausibly be built headless and screenshotted the same way `cna-bible` proved out for
CNA's own demos (`SOFTWARE` backend needs no display at all; `SDL_RENDERER`/`EASYGL` work under
`Xvfb` + Mesa `llvmpipe`). See `tools/` for whatever build/capture scripts a session has produced,
and `NEXT.md`/`PLAN.md` for the current state of that effort (working / blocked / not yet
attempted) — don't re-attempt a path already logged as a dead end without new information; do
pick up a path logged as "worth retrying."

## Source repositories (per-session)

These get added to a session (via the add-repo tool) and cloned outside this repository (typically
`/workspace/<repo>`) — **do not clone them inside `mobile-eggbert-bible`**:

- `mobile-eggbert` — the primary source (the game itself)
- `cna` — the CNA framework (for understanding what mobile-eggbert calls; cite only where needed
  for mobile-eggbert's own code — deep CNA internals belong in `cna-bible`, not here)
- `cna-bible` — style/methodology model (borrow form, not content)
- `mobile-eggbert-legacy` — the decompiled C# origin, for the history/migration chapters
