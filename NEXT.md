# NEXT — current state and what to do next

**Last updated: 2026-07-28, founding session (post-pivot to English + illustrated scope).**

## What's done

- Repository scaffolding: `README.md`, `CLAUDE.md`, `PLAN.md`, `PROGRESS.md`, this file — all in
  English, reflecting the author's mid-session clarifications: English language, mobile-eggbert
  only (CNA marginal), real screenshots + a fully illustrated animation system required.
- Directory structure `book/part01-…` through `book/part11-…`, `book/appendices/`,
  `book/images/`, `tools/`.
- Plan for 58 chapters + 7 appendices in `PLAN.md`, including the illustrated Part V
  (chapters 28–37) and Appendix G (screenshot/visual gallery).
- Reverse-engineered the exact sprite-atlas grid/slicing algorithm from `Pixmap.cpp` — see
  `PLAN.md`'s "Sprite atlas algorithm" section. This is what `tools/extract_sprites.py` must use.

## What to do next, in order

1. **Build the image pipeline first** (blocks Part V's illustrated chapters):
   - `tools/extract_sprites.py`: crop real animation frames from `Content/icons/*.png` per the
     algorithm in `PLAN.md`, driven by `Tables.cpp`/`Tables.hpp` animation sequence data
     (per-`BlupiAction` frame lists, per-`ObjectType` frame lists). Output contact-sheet PNGs to
     `book/images/`.
   - `tools/render_level_map.py`: render a real `worlds/*.txt` level's collision layer as a
     color-coded diagram from the actual `Is*()` predicates in `Decor.cpp` — label clearly as a
     data reconstruction, not a screenshot.
   - Verify the `Pillow` Python package is available (it was installed via `pip3 install Pillow`
     during this session — check it's still present in a fresh session's container).
2. **Attempt a real, running screenshot** (best-effort, can run in parallel with everything else):
   clone `cna` as a sibling of `mobile-eggbert` (`/workspace/cna`), try a `SOFTWARE`-backend
   headless build of the `WindowsPhoneSpeedyBlupi` target first (no display needed at all), fall
   back to `SDL_RENDERER`/`EASYGL` under `Xvfb` + Mesa `llvmpipe` if `SOFTWARE` doesn't work for a
   full game (`cna-bible`'s `tools/cna-screenshot-infra/README.md` proved both paths work for
   CNA's own small demos — a full game is a bigger, less certain lift). A screenshot capture hook
   will likely need a small, clearly-marked patch to `Game1.cpp`/`Program.cpp` (dump the back
   buffer via CNA's `Texture2D`/`GetBackBufferData` after N frames, then exit) since
   mobile-eggbert has no built-in screenshot command. Record the outcome (success, partial,
   blocked — and why) in this file and in Appendix G once attempted.
3. **Write chapters wave by wave** per `PLAN.md`'s wave breakdown (Wave 1: Part I–IV chapters
   1–27, text only; Wave 2: Part V–VIII chapters 28–46, Part V needs step 1 done first; Wave 3:
   Part IX–XI + appendices, chapters 47–58 + A–G).
4. After each wave: spot-check 2-3 chapters for grounding (does it cite real code/assets?), fix
   style/consistency, update `book/SUMMARY.md`, commit, push.
5. After all three waves and the screenshot attempt: update `PLAN.md`'s session log and this file.

## Open questions / decisions pending the author

- None currently blocking. If a real contradiction turns up while writing (e.g. the actual
  scope should be different from the plan's estimate), log it in `PLAN.md`'s session log and in
  this file rather than resolving it silently.

## Repositories needed to continue

Add to the session (via the add-repo tool) and clone outside this repository:
- `openeggbert/mobile-eggbert` — primary source
- `openeggbert/cna-bible` — style model (form only, not content)
- `openeggbert/cna` — needed only for the screenshot-build attempt (step 2 above); clone as
  `/workspace/cna` (sibling of `/workspace/mobile-eggbert`, matching mobile-eggbert's
  `CNA_GRAPHICS_SOURCE_DIR` default of `../cna`)
- `openeggbert/mobile-eggbert-legacy` — for the history/migration chapters (Part XI), if not
  already added
