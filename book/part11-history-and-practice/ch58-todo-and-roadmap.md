# Chapter 58: TODO.md — A Point-in-Time Snapshot

`TODO.md` is 15 lines long. This chapter reads all of them and presents what they say about the
project's open issues as of the commit this book was written against (`07e0a67`). It is
deliberately short, in proportion to its source: there is no forward-looking roadmap document
anywhere in this repository to draw on, and padding a 15-line file into a long chapter would
misrepresent how much genuine planning material actually exists. What follows is everything the
file contains, in context, plus one honest caveat repeated from this chapter's title: a TODO list
is a snapshot of a moving target, not a specification, and by the time a reader opens this chapter
some items below may already be resolved, reprioritized, or joined by others that didn't exist
when this was written.

## The file, in full

*From `TODO.md:1-15`:*
```markdown
# Todo

- [ ] Accelerometer must be not shown in settings if there is no accelerometer available
- [ ] Sound - to check
- [ ] transparency
- [ ] Fullscreen is not working correctly
- [ ] Web version: Sound is a little bit delayed
- [ ] Cheats quick and quicklollypop are in a conflict. Possible solution: rename cheat quick to fast.
- [ ] Audio Issue: High-pitched sound effects reported - investigate if audio is being played at incorrect speed/pitch
- [ ] Audio Issue: Some audio files appear to be missing or not loading properly
- [ ] User Report: Audio in gameplay video sounds distorted (possibly sped up) - verify audio playback rate is correct

## Done

- [x] Player {number} - number should be a letter
-
```

Nine open items under an unlabeled top-level list, followed by a `## Done` section containing
exactly one completed item and one trailing, empty checkbox-less bullet (`-` with nothing after
it) — itself a small, literal artifact of how someone edited this file (an item removed or never
filled in) rather than a formatting error worth over-reading.

## Reading the nine open items

Taken individually, the list spans several different kinds of unfinished work, worth separating
out rather than treating as a uniform backlog:

- **A UI-correctness item**: "Accelerometer must be not shown in settings if there is no
  accelerometer available" — a platform-conditional display bug, not a functional one: the setting
  presumably still *works* where hardware exists, but is offered even on platforms/devices that
  can't act on it. This connects directly to the accelerometer input path covered in this book's
  [Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md), and to
  [Chapter 55](ch55-ilspy-decompilation-and-csharp-stubs.md)'s coverage of the accelerometer's
  Windows-Phone-era C# origins.
- **Two terse, single-phrase placeholders**: "Sound - to check" and "transparency" — these carry
  essentially no information about what specifically is wrong beyond a topic area. They read as
  reminders-to-self rather than filed, reproducible bug reports; this book cannot responsibly
  expand on what "to check" or "transparency" refers to without evidence, so it doesn't guess.
- **A platform-specific rendering bug**: "Fullscreen is not working correctly" — no further detail
  given (which platform, which backend, what "not working" means concretely). Readers interested
  in this project's rendering-backend surface generally should see this book's
  [Part II](../part02-building-and-running/ch04-build-overview.md) chapters on the build system and
  backend selection.
- **A platform-specific timing bug**: "Web version: Sound is a little bit delayed" — narrower and
  more actionable than the two placeholders above, since it names a specific build target
  (Emscripten/Web) and a specific symptom (latency, not absence). This item is also cited directly,
  by the exact same wording, inside `AUDIO_ANALYSIS.md` as corroborating evidence that this
  project's audio backend already behaves differently across platforms/backends — see the
  cross-reference below.
- **A design/UX conflict between two cheat codes**: "Cheats quick and quicklollypop are in a
  conflict. Possible solution: rename cheat quick to fast." This is the one item in the list that
  already proposes its own fix, not just names a symptom. It concerns the cheat-code system this
  book covers in [Chapter 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md)
  and catalogs in [Appendix E](../appendices/appendix-e-cheat-code-reference.md).
- **Three audio items**, covered together in the next section since they were investigated as a
  group in this repository's own `AUDIO_ANALYSIS.md`.

## The three audio items: already analyzed elsewhere in this book

The last three open items are a matched set, all describing symptoms from the same underlying
report:

```
- [ ] Audio Issue: High-pitched sound effects reported - investigate if audio is being played at incorrect speed/pitch
- [ ] Audio Issue: Some audio files appear to be missing or not loading properly
- [ ] User Report: Audio in gameplay video sounds distorted (possibly sped up) - verify audio playback rate is correct
```

This book does not re-derive an analysis of these three items here, because one already exists,
grounded in real source reading, in [Chapter 40: Audio Issue Analysis](../part06-audio/ch40-audio-issue-analysis.md)
— that chapter works through the project's own `AUDIO_ANALYSIS.md`, which explicitly traces its own
origin back to these same three `TODO.md` entries, quoting them verbatim as "already tracked in
`TODO.md`" and dating their addition to a specific commit (`c2202a1`, "TODO.md was updated"). In
short: these are not merely three isolated TODO bullets — they are the seed of a genuine, real
investigative document elsewhere in the repository, and a reader who wants the actual technical
analysis (candidate root causes in `AudioMixer.cpp`'s hardcoded 44100 Hz mixer device, and in
`ContentManager::ResolveAssetPath`'s Android-incompatible `std::filesystem::exists()` check) should
go there rather than expect it repeated in this chapter.

## The "Done" section

Exactly one item is marked complete:

```
- [x] Player {number} - number should be a letter
```

Taken alone this is nearly impossible to interpret with confidence from the TODO file text by
itself — it appears to describe a UI-label fix (some on-screen "Player {number}" text changed to
use a letter instead of a numeral, plausibly to distinguish save-game gamer slots, which this
book's [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md) covers as
supporting three gamer slots). This book does not speculate further on it beyond what the single
line states, since no accompanying commit message, diff, or explanatory note exists in this
repository to confirm the specifics.

## Why this chapter stays short

`TODO.md` is not a roadmap in the sense of a maintained, prioritized plan with target versions or
owners — it's a flat, unordered scratch list, and treating it as more structured than it is would
misrepresent the source. Compare this to `DOXYGEN_DOCUMENTATION_PLAN.md`
([Chapter 57](ch57-doxygen-methodology.md)), which *is* a structured, prioritized plan for a single
well-scoped effort — that document earns a long chapter because it contains 512 lines of genuine
per-file analysis; `TODO.md` earns a short one because it contains 15 lines of genuinely
unelaborated notes. Matching chapter length to source substance, rather than to a fixed target
regardless of what's actually there, is the same principle this book applies everywhere else.

## A closing caveat on staleness

This chapter describes `TODO.md` as read at commit `07e0a67`, on 2026-07-28. Every list like this
one is a snapshot, not a permanent record: items get fixed and should be checked off (or deleted);
new issues get discovered and added; the file itself might be restructured entirely. A reader
consulting this chapter alongside a newer checkout of `mobile-eggbert` should treat the `TODO.md`
excerpt above as historical evidence of what the project's maintainers considered open at one
specific point in time, not as a live status report — and should read the current `TODO.md` in the
actual repository for anything resembling up-to-date information.

## See also

- [Chapter 40: Audio Issue Analysis](../part06-audio/ch40-audio-issue-analysis.md) — the full technical investigation of this chapter's three audio-related TODO items
- [Chapter 23: Secret Powers and the Cheat System](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) — context for the `quick`/`quicklollypop` cheat-code conflict
- [Appendix E: Cheat Code Reference](../appendices/appendix-e-cheat-code-reference.md) — the full cheat-code catalog
- [Chapter 41: InputPad — Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) — context for the accelerometer-settings-visibility item
- [Chapter 57: The Doxygen Documentation Methodology](ch57-doxygen-methodology.md) — a contrasting example of a much more structured planning document in the same repository
