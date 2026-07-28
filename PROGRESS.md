# Mobile Eggbert Bible — historical progress log

This file is a historical record of completed work from previous phases. New work is logged in
`PLAN.md` (the "Session log" section) and in `NEXT.md` (current state for the next session) — new
entries aren't added here as work happens, only periodically as a closed phase's summary.

## Phase 0 — Project founding (2026-07-28)

Repository founded. First draft was in Czech with a 54-chapter/6-appendix, text-only plan; the
author then clarified the book must be in English, focused on mobile-eggbert only (CNA marginal),
and must include real screenshots plus a fully illustrated animation system. Re-scaffolded in
English with an expanded 58-chapter/7-appendix plan including an illustrated Part V and a
screenshot/visual-gallery appendix. See `PLAN.md` for the full scope breakdown and the honest
scope estimate.

## Phase 1 — First complete draft (2026-07-28, same day)

All 58 chapters and 7 appendices written, reviewed, and committed — the book's first complete
draft. ~176,000 words across 65 files, plus 167 real images (an extraction pipeline producing 165
pixel-accurate sprite crops and data-reconstructed diagrams, plus 2 real screenshots captured from
an actually built and running headless copy of the game via CNA's `SOFTWARE` backend). Executed as
roughly 15 parallel background agents, each grounding its chapters in direct source reads, with a
review pass over every landing batch. One real cross-chapter factual correction surfaced and was
propagated (the tile-icon "invisible collision layer" hypothesis from Phase 0 was wrong; corrected
independently by two chapters once the real `Decor.cpp` code was read). See `PLAN.md`'s "Chapter
status" section and session log for full details, and `NEXT.md` for optional further-depth work a
future session could take on (none of it is a gap — the book is complete and usable as-is).
