# NEXT — current state and what to do next

**Last updated: 2026-07-28. The book's first complete draft is DONE — all 58 chapters + 7
appendices written, reviewed, and committed.**

## What's done

Everything in `PLAN.md`'s plan is written: Parts I–XI (chapters 1–58), Appendices A–G. See
`book/SUMMARY.md` for the full table (every row `done`) and `PLAN.md`'s "Chapter status" section
for final numbers (~176,000 words, 167 real images including 2 real captured screenshots).

Also done:
- `tools/extract_sprites.py` + `tools/render_level_map.py`: the image-extraction pipeline, fully
  working and reproducible against a fresh `mobile-eggbert` checkout. `book/images/MANIFEST.md` is
  the authoritative index of every image's provenance.
- `tools/SCREENSHOT_ATTEMPT.md` + `tools/screenshot-capture.patch`: a working, reproducible recipe
  for headlessly building the real game and capturing real screenshots via CNA's `SOFTWARE`
  backend. Two screenshots exist; more are straightforward to add (see below).
- One real cross-chapter factual correction is recorded in `PLAN.md`'s session log: the tile-icon
  "invisible collision layer" hypothesis from the founding session was wrong and was corrected
  (independently, by two different chapters) once real code was read.

## What a future session could do next (all optional — this is not a gap list, it's a "further
depth" list; the book stands on its own as-is)

1. **More screenshots.** Only a title screen and one gameplay frame exist. `tools/screenshot-capture.patch`'s
   technique generalizes directly — capture a later level, the pause menu, a death/win screen, or a
   specific hazard in action, by waiting for a different `Def::Phase`/mission state before dumping.
2. **Editorial pass for voice consistency.** ~15 independent agents wrote this book; each was
   individually well-grounded and reviewed, but a full read-through for consistent tone/terminology
   across all 65 files has not been done (only spot-checks were, during the writing session).
3. **Rebuild `tools/extract_sprites.py`'s output if `mobile-eggbert` changes.** The pipeline is
   reproducible — re-run it against a newer checkout and regenerate `book/images/` + `MANIFEST.md`
   if the game's assets or `Tables.cpp` data ever change.
4. **Deepen any chapter using primary sources this pass didn't reach** — e.g. `mobile-eggbert-legacy`
   (the decompiled C# origin) was not accessible in this session's environment; Chapter 55 notes
   this explicitly and would benefit from a real comparison if that repo becomes available.
5. **If a LaTeX/PDF version is ever wanted**, the Markdown source under `book/` is structured
   (`partNN/chNN`) to convert cleanly via pandoc or similar — this wasn't attempted since no LaTeX
   toolchain was available in this session's environment and Markdown serves the stated goal (a
   reader becoming an expert on the source) without needing one.

## Open questions / decisions pending the author

None blocking. The book is complete and usable as-is.

## Repositories used this session

- `openeggbert/mobile-eggbert` — primary source (cloned read-only at `/workspace/mobile-eggbert`)
- `openeggbert/cna-bible` — style/methodology model
- `openeggbert/cna` and `openeggbert/sharp-runtime` — cloned as siblings only for the screenshot
  build attempt (not for content research; CNA internals are out of this book's scope)
