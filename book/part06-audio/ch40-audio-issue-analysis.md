# Chapter 40: Audio Issue Analysis

Alongside its source code, the `mobile-eggbert` repository carries a small set of first-party
analysis documents — written by a prior session investigating a specific bug report rather than
describing steady-state architecture. `AUDIO_ANALYSIS.md` (151 lines) is one of these. This
chapter presents its findings as a book chapter, cross-referenced against the actual source it
cites (and, in a few places, against source read directly for this book that the analysis document
itself did not quote), while preserving the document's own explicit epistemic status: it is an
analysis produced entirely by reading code, **not a confirmed root-cause report**, and it says so
about itself repeatedly. Nothing in this chapter should be read as upgrading "suspected" to
"confirmed" — where the source document hedges, this chapter hedges with it.

## Where the report came from

`AUDIO_ANALYSIS.md` opens by quoting its own trigger verbatim — a YouTube comment on a gameplay
video:

> "Will you be able to fix the high pitched sound effects and missing audio files in a near
> future update?"

with a clarifying follow-up from the same commenter:

> "I'm talking about the audio that's playing in the video. Unless you purposely sped it up, which
> may be why it sounds like that."

The document is explicit about its own method and limits (`AUDIO_ANALYSIS.md:15-17`):

> This is an **analysis only** document. No code changes were made. It was written after reading
> the current `mobile-eggbert` and `cna` source; no runtime/device testing was performed, so
> several points below are flagged as needing empirical verification rather than confirmed root
> causes.

The same two complaints (or an earlier phrasing of them) are already present in the project's
`TODO.md`, which `AUDIO_ANALYSIS.md` quotes and identifies as the backlog entries it responds to:

*From `TODO.md:9-11`:*
```
- [ ] Audio Issue: High-pitched sound effects reported - investigate if audio is being played at incorrect speed/pitch
- [ ] Audio Issue: Some audio files appear to be missing or not loading properly
- [ ] User Report: Audio in gameplay video sounds distorted (possibly sped up) - verify audio playback rate is correct
```

`TODO.md` also carries one line of independent, adjacent evidence that `AUDIO_ANALYSIS.md` treats
as a meaningful data point rather than the same complaint restated: `- [ ] Web version: Sound is a
little bit delayed` (`TODO.md:7`). This is a separate, unrelated symptom (latency, not pitch or
missing files) that nonetheless demonstrates the audio backend's behavior is known to already
differ across build targets — a fact the "high-pitched sounds" analysis leans on directly (see
below). `TODO.md` also records other unrelated open items (an accelerometer/settings-visibility
issue, a fullscreen bug, a cheat-name collision) that `AUDIO_ANALYSIS.md` does not touch and that
are out of scope for this chapter.

`AUDIO_ANALYSIS.md` is careful to date itself against a specific commit: the TODO entries "added
in the current `develop` HEAD commit (`c2202a1 TODO.md was updated`)... This document is the first
deep-dive into that backlog entry" (`AUDIO_ANALYSIS.md:26-28`) — i.e. this analysis is the first
attempt at investigating these reports, not a follow-up to an earlier one.

## Complaint 1: "High-pitched" / sped-up sound effects

### What the analysis ruled out

The document walks through three specific areas of the codebase and concludes each is *not* the
cause, with a cited comparison or code-reading backing each conclusion:

**The `tableVolumePitch` table itself.** This is the per-channel volume/pitch table covered in
depth in [Chapter 39](ch39-soundchannel-and-mixing.md). `AUDIO_ANALYSIS.md:36-40` reports it was
"compared byte-for-byte against the original decompiled C# source
(`mobile-eggbert-legacy/mobile-eggbert-core/Sound.cs:58`) and is identical," and that the small
group of channels with `pitch = 1.0` (one octave up) and `volume = 0.5` is "original game design
(verbatim from the Windows Phone XNA release), not a porting bug." This book's own independent
read of `Sound.hpp:190-212` for [Chapter 39](ch39-soundchannel-and-mixing.md) corroborates the
existence and identity of that group — four channels, `1`, `2`, `38`, `39` — and finds nothing in
the table itself that looks like a transcription error. This specific conclusion is one of the
sturdier ones in the document, since it rests on a direct byte-for-byte comparison against the
original source rather than on static reasoning about a library the author couldn't fully verify.

**Pitch application in `SoundEffectInstance`.** `AUDIO_ANALYSIS.md:41-43` states that
`SoundEffectInstance.cpp:1074`'s `setPitchProperty` "is correctly clamped to `[-1, 1]` and
converted via `2^pitch` (the XAudio2/FNA octave-based convention)," and notes that "an earlier,
audibly-wrong linear approximation was already fixed per the inline comment at lines 76-79." This
detail — that a *previous*, separately-identified pitch-conversion bug already existed and was
already fixed before this analysis was written — is itself useful context: it shows the pitch
pipeline has been scrutinized before, which is part of why the analysis leans toward looking
elsewhere (the mixer's sample-rate handling, not the pitch-conversion math) for an unresolved
"sounds too high" complaint. This claim concerns `SoundEffectInstance.cpp`, a CNA-side file this
book's methodology treats as out of primary scope (see `CLAUDE.md`'s scope rule); it is reported
here as the analysis document states it, not independently re-verified against CNA internals.

**WAV sample-rate handling in `SoundEffect`'s loader.** `AUDIO_ANALYSIS.md:45-47` reports that the
loader (`SoundEffect.cpp:194-224`, via `MIX_LoadAudio`) reads the sample rate "from the actual
file" via `MIX_GetAudioFormat()`/`spec.freq`, "not hardcoded," and separately verifies the actual
shipped assets: "84 files are 22050 Hz mono, 9 files are 11025 Hz mono — no file is 44100 Hz." This
asset-format census is a piece of ground-truth evidence about `Content/sounds/` itself (93 files
total, matching the count `Sound::LoadContent()` expects, per [Chapter 38](ch38-sound-isound-architecture.md))
rather than a claim about a code path, and is the kind of fact this book's own methodology would
also want verified directly — a future reader auditing this claim can re-run the same sample-rate
census against the same directory.

### What remains suspect — explicitly unconfirmed

The document's "Still suspect" section is where its epistemic hedging matters most, and where this
chapter is most careful not to overstate anything beyond what `AUDIO_ANALYSIS.md` itself claims.

The leading candidate the document proposes is a **mixer output-device sample-rate mismatch**:
`AUDIO_ANALYSIS.md:51-60` reports that CNA's shared SDL3_mixer output device
(`CNA/Internal/Audio/AudioMixer.cpp:28-31`) is hardcoded to `44100 Hz / stereo / SDL_AUDIO_S16`,
meaning every loaded sound — all of which are 22050 Hz or 11025 Hz per the census above — must be
resampled upward to the device rate during playback. The document is careful to describe this as
an *expectation*, not a verified behavior: "this is expected to happen automatically inside
SDL3_mixer... on a per-track basis, but nothing in the codebase asserts or tests this — it is pure
reliance on the library's internal behavior." The conditional framing that follows is the crux of
the whole "still suspect" section: *if* per-track resampling is not actually engaging correctly
(the document names a "backend-specific SDL3_mixer quirk on Android" and "an API misuse when a
track is bound to the mixer" as two illustrative-but-unconfirmed possibilities) "every sound would
play faster and higher-pitched than intended — proportionally more so for the 11025 Hz files (4×
device rate) than the 22050 Hz files (2× device rate)." Nothing in the document, and nothing
independently verified for this chapter, confirms that resampling is in fact failing — this is a
plausible mechanism identified by static reading of two hardcoded numbers (source rate vs. device
rate) sitting on either side of a boundary neither side asserts is being crossed correctly, not a
measured or reproduced symptom.

Two pieces of circumstantial support are offered for treating this mixer-level theory as more
promising than the per-channel table (which was already ruled out above): the complaint describes
"the audio across the whole video" sounding sped up, "not one specific sound effect" — a pattern
the document argues "fits a systemic/device-level resampling issue better than the per-channel
`tableVolumePitch` table, which only affects specific SFX channels, not audio uniformly"
(`AUDIO_ANALYSIS.md:61-64`); and the pre-existing, independently-reported `TODO.md` line about web
audio being delayed is cited as evidence "that the audio backend already behaves differently
across platforms/backends" (`AUDIO_ANALYSIS.md:66-68`) — again, evidence of *platform variance*
existing at all, not evidence that any specific platform mispitches sound. The document explicitly
flags an open unknown that would materially narrow the investigation: "Which platform the reported
video was captured on (Android vs. web/Emscripten) is unknown" (`AUDIO_ANALYSIS.md:67-68`).

### Suggested next steps (not performed by the analysis itself)

`AUDIO_ANALYSIS.md:70-77` lists three concrete follow-up actions, none of which the document
itself carried out: (1) determine which build (Android APK vs. web) the reported video actually
came from; (2) add temporary diagnostic logging comparing `MIX_GetAudioFormat()`'s detected source
frequency against the actual output device frequency at the moment a track starts, on the affected
platform; (3) empirically play one known 22050 Hz asset (`sound000.wav` is named as an example) in
isolation and measure its actual playback duration/pitch against the expected value. All three are
runtime-diagnostic steps that require a live build and device/platform access this analysis
explicitly did not have (or did not use) when it was written.

## Complaint 2: "Missing audio files"

### A concrete suspect, with an important caveat about the fallback path

The most specific lead in the whole document concerns Android asset resolution.
`AUDIO_ANALYSIS.md:85-100` identifies `ContentManager::ResolveAssetPath`
(`cna/include/Microsoft/Xna/Framework/Content/ContentManager.hpp:190-222`) as using
`std::filesystem::exists()` to probe whether a candidate asset path is real before returning it.
On Android, assets packaged inside the APK are reachable only through `AAssetManager`, not as
regular files on the device's POSIX filesystem — so `std::filesystem::exists()`, which "only sees
the real OS filesystem / process working directory," will "effectively always return `false` for
packaged assets" on that platform. `ContentManager` is a CNA type; per this book's scope rules
(see `CLAUDE.md`) it is described here only to the extent `mobile-eggbert`'s own asset-loading path
(`Sound::LoadContent()`, [Chapter 38](ch38-sound-isound-architecture.md)) depends on it, exactly as
`AUDIO_ANALYSIS.md` itself does.

Critically, the document does not claim this actually breaks loading — it identifies a fallback
and then explicitly declines to claim the fallback is exercised correctly: "There is a fallback
(`ResolveAssetPath`, final line: `return base;`) so a constructed path is still returned even when
the existence probe fails — the loader is not necessarily broken outright," followed immediately
by: "Whether the downstream loader... transparently falls back to `AAssetManager` for a path that
failed the `std::filesystem::exists()` check depends on SDL3's own Android I/O backend behavior.
This was **not verified empirically** — it needs a real Android run with logging of
`SDL_GetError()` on any failed `MIX_LoadAudio` call" (`AUDIO_ANALYSIS.md:93-100`, emphasis in the
original document). In other words: a plausible-looking gap in one function's existence check does
not, by itself, establish that any sound actually fails to load on Android — the very next layer
down might already compensate, and nobody has checked.

A second, related suspect is the Android build's asset packaging itself:
`AUDIO_ANALYSIS.md:101-111` notes that `android/app/build.gradle:82-99` packages `Content/` and
`worlds/` into the APK's asset tree via two symlinks (`android/app/src/main/assets/Content ->
../../../../../Content` and the equivalent for `worlds`), relying on Gradle's asset-merge task
following symlinks on Linux. The document calls this "generally works... but... a fragile point" —
again explicitly unverified: "This was **not verified** by unzipping an actual built APK."

### The concrete finding this book independently confirmed: `Sound::PlayImage`'s silent bounds check

The one piece of this section that is a direct, verifiable statement about `mobile-eggbert`'s own
code (rather than about CNA or the Android toolchain) is the observation about
`Sound::PlayImage`'s bounds check, and this book's own reading of `Sound.cpp` for
[Chapter 38](ch38-sound-isound-architecture.md) confirms it exactly as described:

*From `Sound.cpp:229-230` (quoted in `AUDIO_ANALYSIS.md:112-117`):*
```cpp
const intcs rawChannel = ToRaw(channel);
if (rawChannel >= 0 && rawChannel < soundEffects.size())
```

If `soundEffects.size()` ends up smaller than 93 — the document's proposed mechanism is that
`LoadContent()`'s loop (covered in [Chapter 38](ch38-sound-isound-architecture.md)) "partially
failed — one `.wav` threw during `MIX_LoadAudio` and aborted the loop, or was silently skipped" —
then any channel index at or beyond the point where loading stopped simply never plays, silently,
because the bounds check quietly declines to index into the vector rather than plays, errors, or
logs anything. `AUDIO_ANALYSIS.md:117` puts this precisely: "This would look exactly like 'some
audio files are missing' from a player's perspective, without leaving any trace to grep for in a
crash log." Reading `Sound::LoadContent()` (`Sound.cpp:133-163`) directly confirms the loop has no
per-iteration error handling: it is a flat `for` loop over exactly 93 indices, and nothing catches
or logs a failure from `game1->getContentProperty().Load<SoundEffect>(...)`. Whether a real load
failure has ever actually happened on any platform is, again, not something either the original
analysis or this chapter has empirically confirmed — the code shape simply makes such a failure
invisible if it does occur, which is a real property of the code regardless of whether it has ever
been triggered.

### Ruled out

Two possibilities are explicitly ruled out rather than left open. `Def::getHasSoundProperty()`
(`Def.hpp:195`, also discussed in [Chapter 38](ch38-sound-isound-architecture.md)) is a `constexpr`
that always returns `true`, so it "cannot selectively disable audio on one platform"
(`AUDIO_ANALYSIS.md:121-122`) — this rules it out as a platform-specific silencing mechanism. And a
direct inventory of the repository's own `Content/sounds/` directory found "all 93 expected files
(`sound000.wav` … `sound092.wav`) are present and non-empty... there is no gap in the local asset
set" (`AUDIO_ANALYSIS.md:123-124`) — whatever is causing a "missing audio" complaint (if the
complaint reflects a real, reproducible symptom at all), it is not that the source repository is
missing files at the point of packaging.

### Suggested next steps (not performed by the analysis itself)

`AUDIO_ANALYSIS.md:126-137` proposes: (1) unzip an actual built APK and confirm
`assets/Content/sounds/*.wav` really contains all 93 files after Gradle's asset-merge step; (2)
add error logging around `MIX_LoadAudio` failures in `SoundEffect.cpp:205-211` so a failed load
surfaces in `adb logcat` instead of silently producing an unusable `SoundEffect`; (3) consider
replacing `ContentManager::ResolveAssetPath`'s `std::filesystem::exists()` check with an SDL3
I/O-based existence probe (`SDL_IOFromFile` open/close) so path resolution behaves consistently
across desktop and packaged Android/similar builds — a fix the document notes "would also fix the
same class of platform-filesystem mismatch for any other asset type reachable through
`ContentManager::Load<T>`, not just `SoundEffect`," i.e. a genuinely general fix rather than an
audio-specific patch, if it turns out to be needed at all.

## Summary table, as the analysis itself frames it

`AUDIO_ANALYSIS.md:143-146` closes with a table explicitly labeling both symptoms "Suspected but
unconfirmed" — language this chapter preserves verbatim rather than upgrading:

| Symptom | Status | Most likely area |
|---|---|---|
| High-pitched sound effects | Suspected but unconfirmed | SDL3_mixer per-track resampling from source rate (22050/11025 Hz) to the hardcoded 44100 Hz mixer device (`AudioMixer.cpp:28-31`) — needs runtime verification |
| Missing audio files | Suspected but unconfirmed | `ContentManager::ResolveAssetPath`'s use of `std::filesystem::exists()`, which cannot see Android APK assets (`ContentManager.hpp:190-222`); possibly compounded by silent swallow-on-bounds-miss in `Sound::PlayImage` (`Sound.cpp:230`) |

The document's closing paragraph is worth quoting in full, because it is the clearest possible
statement of the document's own epistemic status and this chapter has no reason to say it any
better:

> Both root causes proposed here are **candidates derived from static code reading**, not
> confirmed via a live run of the app. Before attempting a fix, the recommended first step is
> targeted runtime diagnostics (see the "Suggested next steps" under each section) to confirm
> which mechanism is actually responsible, since more than one plausible cause exists for each
> symptom.

## What this chapter adds versus what it repeats

Everything in the "ruled out" sections above and the `Sound::PlayImage` bounds-check finding is
independently confirmable against the source this book has itself read for
[Chapter 38](ch38-sound-isound-architecture.md) and [Chapter 39](ch39-soundchannel-and-mixing.md),
and this chapter's own re-reading found no discrepancy between what `AUDIO_ANALYSIS.md` claims
about `Sound.cpp`/`Sound.hpp` and what those files actually contain. The claims that concern CNA
internals proper (`AudioMixer.cpp`, `SoundEffectInstance.cpp`, `ContentManager.hpp`,
`SoundEffect.cpp`) are reported here exactly as `AUDIO_ANALYSIS.md` states them, consistent with
this book's scope decision to treat CNA as something `mobile-eggbert` calls rather than a subject
for its own deep dive (see `CLAUDE.md`) — a reader wanting to independently verify those specific
claims against CNA's own source should do so via `cna-bible`, the sister project dedicated to
CNA's internals.

## See also

- [Chapter 38: Sound/ISound Architecture](ch38-sound-isound-architecture.md) — the `Sound::LoadContent()`
  loop and `Sound::PlayImage`'s bounds check discussed above, in full architectural context.
- [Chapter 39: SoundChannel and Mixing](ch39-soundchannel-and-mixing.md) — the `tableVolumePitch`
  table this chapter's "ruled out" section relies on, including the byte-for-byte comparison
  against the original C# source.
- [Chapter 51: Android Deep Dive](../part10-platform-deep-dives/ch51-android-deep-dive.md) — the
  Android asset-symlink packaging (`android/app/build.gradle`) this chapter's "missing audio
  files" section touches on.
- [Chapter 58: TODO and Roadmap](../part11-history-and-practice/ch58-todo-and-roadmap.md) — the
  full `TODO.md` backlog this analysis document responds to, including the unrelated items not
  covered here.
