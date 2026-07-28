# Chapter 51: Android Deep Dive

Part II, [Chapter 9](../part02-building-and-running/ch09-android-build.md), covers the mechanics
of *building* mobile-eggbert for Android — installing the NDK, running `./gradlew assembleDebug`,
signing a release APK. This chapter assumes that ground is already covered and goes somewhere Part
II does not: what actually happens to the game's assets once they leave the ordinary filesystem and
get folded into an APK, and a specific, real, still-open question about whether that process is as
safe as `ANDROID.md` assumes.

The center of this chapter is a single worked case study: a suspected — not confirmed —
Android-specific asset-loading bug, found by static reading of `cna`'s `ContentManager` and
recorded in `mobile-eggbert`'s own `AUDIO_ANALYSIS.md`. It is presented here with the same
epistemic caution the source document uses: as a plausible root cause derived from reading the
code, not as a verified defect.

## Two symlinks holding up the whole asset pipeline

Android's Gradle build does not compile `mobile-eggbert`'s `Content/` and `worlds/` directories
from wherever they happen to live in the repository checkout. Android Studio's asset merger only
picks up files reachable from `sourceSets.main.assets.srcDirs`, and mobile-eggbert's `android/app/`
module sets that to a single directory:

*From `android/app/build.gradle:96-97`:*

```groovy
sourceSets {
    main {
        assets.srcDirs = ['src/main/assets']
```

`src/main/assets` itself contains no real files — it contains two symbolic links, checked into the
Android module and confirmed on disk in this checkout:

```
android/app/src/main/assets/Content -> ../../../../../Content
android/app/src/main/assets/worlds  -> ../../../../../worlds
```

Counting the `../` segments from `android/app/src/main/assets/`, both links resolve back up to the
`mobile-eggbert` repository root's own `Content/` and `worlds/` directories — the same directories
every other platform's build copies or preloads directly (see Chapters 5, 8, and 9). Android is the
one platform that doesn't copy these directories at all; it *links* to them and lets Gradle's asset
merge step walk through the link at build time.

The comment block directly above `sourceSets` in `build.gradle` explains the intent plainly:

*From `android/app/build.gradle:82-94`:*

```groovy
// Package game assets into the APK as Android assets (read-only).
//
// Asset layout in the APK must match the paths the game uses at runtime.
// The game loads e.g. "Content/backgrounds/decor000.png" and "worlds/world001.txt".
// SDL_IOFromFile on Android first checks internal storage, then the APK AAssetManager.
//
// We set the asset source to the mobile-eggbert root so that the directory
// structure is preserved:
//   <mobile-eggbert>/Content/backgrounds/... -> Content/backgrounds/... in APK
//   <mobile-eggbert>/worlds/...              -> worlds/... in APK
//
// Other files at that level (src/, cmake/, etc.) are excluded by AGP because
// the asset merger only includes directories/files reachable from assets.srcDirs.
```

This is a deliberate, documented design choice, and it works — `AUDIO_ANALYSIS.md` independently
confirms it, while also flagging exactly why it is a little fragile:

*From `AUDIO_ANALYSIS.md:101-111`:*

> `android/app/build.gradle:82-99` — the comment above `sourceSets` claims assets are packaged
> "from the mobile-eggbert root," but the actual `assets.srcDirs = ['src/main/assets']` relies on
> two symlinks:
> ```
> android/app/src/main/assets/Content -> ../../../../../Content
> android/app/src/main/assets/worlds  -> ../../../../../worlds
> ```
> This generally works because Gradle's asset merge task follows symlinks on Linux, but it is a
> fragile point — a different Gradle version, CI environment, or symlink-unaware tooling could
> silently drop or partially package the `sounds/` subtree. This was **not verified** by unzipping
> an actual built APK.

Note the honest hedge at the end. Nobody has actually unzipped a built `app-debug.apk` and
confirmed all 93 files under `Content/sounds/` are present inside it. The symlink approach is
plausible and probably fine on a Linux-hosted Gradle build (Git itself stores the two paths as
symlinks, `git ls-tree` would show mode `120000` for each), but "probably fine" and "verified" are
different claims, and this chapter keeps that distinction rather than upgrading one into the other.

Why does this matter more on Android than it would on, say, Linux? Because unlike the native
desktop build (Chapter 5), which just runs `cp -r Content/ build/`, or the CMake-driven Emscripten
build (Chapter 8, and [Chapter 53](ch53-web-virtual-filesystem.md)), which explicitly lists each
`--preload-file` argument one directory at a time, the Android path has exactly one indirection
layer — the symlink — standing between "the asset exists in the repository" and "the asset exists
in the APK." If that one layer silently drops a subtree on some CI runner's filesystem or a
different Gradle/AGP version, there is no build-time or run-time check anywhere in the pipeline
that would catch it. It would only be discovered as a missing-asset symptom at runtime, potentially
much later, on a device.

## Why Android doesn't need a content copy step at all

The root `CMakeLists.txt` makes the platform split explicit. Every non-Android, non-Emscripten
target gets a `POST_BUILD` step that copies `Content/` next to the built executable; Android gets
nothing, because Gradle's asset packaging (via the symlinks above) has already done the equivalent
job before CMake's `externalNativeBuild` invocation even runs:

```cmake
if(ANDROID)
    # ---------------------------------------------------------------------------
    # Android: no content copy needed (assets are in the APK).
    # ---------------------------------------------------------------------------
elseif(EMSCRIPTEN)
    ...
```

This is a clean design on paper: three platform branches (Android / Emscripten / everything else),
each handling asset packaging in whatever way is idiomatic for that target. The `externalNativeBuild`
block in `build.gradle` confirms the two build systems are wired together correctly, with the
native CMake project's root pointed at directly:

*From `android/app/build.gradle:74-78`:*

```groovy
externalNativeBuild {
    cmake {
        // Point to the game's root CMakeLists.txt (one level up from android/).
        path '../../CMakeLists.txt'
        version "4.1.2"
    }
}
```

## How the game reads its assets back out at runtime

`ANDROID.md` states the runtime access path in one line:

*From `ANDROID.md:172-175`:*

> Game assets are packaged into the APK as Android assets. At runtime they are read via
> `SDL_IOFromFile` which transparently falls back to the APK `AAssetManager` when a file is not
> found in internal storage.

This is SDL3's own documented Android I/O behavior: `SDL_IOFromFile` on Android checks the
filesystem first (for writable internal-storage files) and, if that fails, opens the path through
`AAssetManager`, the Android NDK API purpose-built for reading files bundled inside an APK's
`assets/` directory. `AAssetManager` is not a regular POSIX filesystem — it's a separate read-only
archive interface baked into the Android platform, because the files packaged as assets live
compressed inside the `.apk` zip container on the device, not as loose files on disk.

That distinction — "a real path SDL/AAssetManager can open" versus "a real path the OS filesystem
can see" — is exactly where the case study below finds a mismatch.

## Case study: `ContentManager::ResolveAssetPath` and `std::filesystem::exists()`

`mobile-eggbert` never talks to `AAssetManager` or `SDL_IOFromFile` directly for content loading.
It goes through CNA's generic `ContentManager::Load<T>()`, which needs to first decide *which*
on-disk path a logical asset name (`"Content/backgrounds/decor000"`, say) actually resolves to,
because a bare asset name might need `.png`, `.wav`, `.cnj`, or no extension at all appended,
depending on what type is being loaded and what sidecar metadata exists. That decision is made by
`ResolveAssetPath`:

*From `ContentManager.hpp:504-543`:*

```cpp
template <typename T>
[[nodiscard]] std::string ResolveAssetPath(
    const std::string& assetName,
    LooseFileContentTypeReader<T>& reader) const
{
    const std::string base = BuildAssetPath(assetName);

    // If the literal path already exists, use it as-is. This covers
    // assetName with an explicit, correct extension. Checking
    // existence rather than std::filesystem::path::has_extension()
    // matters because asset names can legitimately contain a '.'
    // that is not a file extension (e.g. localized names like
    // "Flag.en-US"), which has_extension() would otherwise
    // misinterpret as already-resolved and never try appending
    // a reader extension.
    if (std::filesystem::exists(base))
    {
        return base;
    }

    // .cnj is always tried before any native/reader-declared extension ...
    const std::string cnjCandidate = base + ".cnj";
    if (std::filesystem::exists(cnjCandidate))
    {
        return cnjCandidate;
    }

    // Try each extension declared by the reader.
    const auto extensions = reader.GetExtensions();
    for (const auto& ext : extensions)
    {
        const std::string candidate = base + ext;
        if (std::filesystem::exists(candidate))
        {
            return candidate;
        }
    }

    // Fall back to bare path (reader may handle the extension itself).
    return base;
}
```

(This function lives in `cna`, the underlying framework — cited here only because it is the exact
mechanism mobile-eggbert's asset loading goes through on every platform, Android included; see
`CLAUDE.md` on this book's CNA-internals scope boundary.)

Every existence check in this function is `std::filesystem::exists()` — a standard C++17 call that
asks the *operating system's own filesystem* whether a path resolves to something. On desktop
Linux, Windows, or macOS, that's exactly the right question to ask: the game's content directory is
a real directory of real files sitting next to the executable, and `std::filesystem::exists()` sees
it correctly.

On Android, it is very plausibly the wrong question. Content packaged into the APK is not sitting
in a directory `std::filesystem` can enumerate — it exists only inside the APK's own asset
container, reachable exclusively through `AAssetManager`'s API (or, transitively, through SDL's
Android `SDL_IOFromFile` binding that wraps it). `std::filesystem::exists()` has no way to know
`AAssetManager` exists at all; it can only see the process's ordinary filesystem view. `mobile-eggbert`'s own analysis states the conclusion directly:

*From `AUDIO_ANALYSIS.md:85-100`:*

> `cna/include/Microsoft/Xna/Framework/Content/ContentManager.hpp:190-222`
> (`ContentManager::ResolveAssetPath`) uses `std::filesystem::exists()` to probe whether a
> candidate asset path exists before returning it. On Android, assets packaged inside the APK
> (`android/app/src/main/assets/Content` → symlink to `../../../../../Content`) are **not regular
> files on the device filesystem** — they only exist inside the APK's asset store, reachable via
> `AAssetManager`, not via a POSIX path. `std::filesystem::exists()` only sees the real OS
> filesystem / process working directory, so on Android it will effectively always return `false`
> for packaged assets.

(The line numbers cited in `AUDIO_ANALYSIS.md` — `190-222` — point at an earlier revision of
`ContentManager.hpp`; in the checkout this chapter was written against, the same function is at
`ContentManager.hpp:500-543`, quoted above. The function's logic is unchanged; only its position in
the file has drifted as the surrounding file grew. This kind of citation drift is itself worth
flagging: any AI or reader cross-checking a doc's `file:line` citation against a newer checkout
should expect line numbers to move even when the underlying claim still holds.)

### Why the game might still work despite this

Critically, `ResolveAssetPath` is not a hard gate. Read its last line again: if every
`std::filesystem::exists()` probe returns `false` — which is expected to be the case for every
Android-packaged asset — the function does **not** throw or return an empty string. It falls
through to `return base;` and hands back a constructed, plausible-looking path anyway (e.g.
`Content/backgrounds/decor000.png`) regardless of whether the existence probe actually confirmed
it. The caller then passes that path down to the actual load path — for a `SoundEffect`, ultimately
`SDL_IOFromFile` via `MIX_LoadAudio`.

That means the real question is not "does `ResolveAssetPath` know about `AAssetManager`?" (it
doesn't) but "does `SDL_IOFromFile`, further downstream, know how to open the path it's handed even
though the upstream existence probe already gave up on it?" `AUDIO_ANALYSIS.md` is explicit that
this downstream behavior is exactly the piece nobody has actually tested:

*From `AUDIO_ANALYSIS.md:96-100`:*

> Whether the downstream loader (`SoundEffect(path)` → `MIX_LoadAudio` → SDL3's
> `SDL_IOFromFile`) transparently falls back to `AAssetManager` for a path that failed the
> `std::filesystem::exists()` check depends on SDL3's own Android I/O backend behavior. This
> was **not verified empirically** — it needs a real Android run with logging of
> `SDL_GetError()` on any failed `MIX_LoadAudio` call.

So the honest picture is a *pipeline of two independent, unverified assumptions* stacked on top of
each other:

1. `ANDROID.md` asserts `SDL_IOFromFile` "transparently falls back to the APK `AAssetManager`" —
   itself stated as a design fact, not something this checkout's tests exercise.
2. Even if assumption 1 holds, `ResolveAssetPath`'s existence probe returning `false` for every
   real Android asset means the function is, in effect, permanently guessing rather than confirming
   — it happens to guess correctly (the literal, un-suffixed `base` path) for assets that don't need
   an extension appended, but for any asset that actually depends on the `.cnj`-then-reader-extension
   fallback chain to find the right file, that chain **cannot function on Android**, because every
   branch in it depends on an `exists()` call that can only ever return `false` for a packaged
   asset. On Android such an asset would always resolve to the bare, un-suffixed `base` path,
   whether or not that is the file that's actually needed.

Whether this second point ever bites in practice depends on whether any asset mobile-eggbert loads
through `Load<T>()` genuinely needs the reader-extension or `.cnj` fallback path on Android (as
opposed to already carrying an explicit, correct extension in its logical asset name, which sidesteps
the whole problem by returning `base` correctly on the very first, always-succeeding-by-luck branch).
Nobody has enumerated which call sites those are for this specific game's asset set. This chapter
does not claim to know the answer — it presents the mechanism precisely and flags where the
uncertainty genuinely lies, exactly as `AUDIO_ANALYSIS.md` does.

### A second, independent way assets could go silently missing

`AUDIO_ANALYSIS.md` also flags a completely separate, easier-to-trigger failure mode further
downstream in `mobile-eggbert`'s own code, worth knowing about alongside the `ContentManager` issue
above because both symptoms look identical to a player — a sound simply never plays, with nothing
in the logs:

*From `AUDIO_ANALYSIS.md:112-117`:*

> `Sound::PlayImage`, `Sound.cpp:230` — if `soundEffects.size()` ends up smaller than the channel
> index being requested (e.g. because `LoadContent()` partially failed — one `.wav` threw during
> `MIX_LoadAudio` and aborted the loop, or was silently skipped), the bounds check
> `rawChannel >= 0 && rawChannel < soundEffects.size()` simply causes that sound to never play,
> with **no error, no log output**. This would look exactly like "some audio files are missing"
> from a player's perspective, without leaving any trace to grep for in a crash log.

This is a good illustration of why the symptom ("audio sounds missing on Android") does not
uniquely identify a single root cause. A partially-failed `LoadContent()` loop and a
`ResolveAssetPath`/`AAssetManager` mismatch would both produce the same silent, log-free absence of
sound from a player's perspective — which is exactly why `AUDIO_ANALYSIS.md`'s own recommended next
step is runtime diagnostics on an actual device, not a deeper static read of more source. See
[Chapter 40](../part06-audio/ch40-audio-issue-analysis.md) for the audio side of this investigation
in full, including the separate high-pitched-sound-effect hypothesis this document also covers.

## Writable storage: where Android actually differs cleanly from the rest

Unlike the read-only content path above, mobile-eggbert's writable save-data path *is* handled with
an explicit Android branch, and does not go through `std::filesystem::exists()` guesswork at all.
`SharpRuntime::Storage::StoragePaths::GetIsolatedStorageRoot()` — the function CNA's isolated
storage layer calls to find a writable root directory — has a dedicated `#if defined(__ANDROID__)`
branch:

*From `StoragePaths.cpp:23-41`* (in the `sharp-runtime` repository, cited here only for the one
Android-specific branch that mobile-eggbert's save path depends on):

```cpp
#elif defined(__ANDROID__)
    // On Android the working directory is not writable.
    // Use SDL_GetPrefPath to obtain the app's private internal storage.
    // SDL_GetPrefPath returns a path like /data/data/<package>/files/<org>/<app>/
    // which persists across app restarts but is cleared on uninstall.
    char* prefPath = SDL_GetPrefPath("org.openeggbert", "speedyblupi");
    std::filesystem::path root;
    if (prefPath) {
        root = std::filesystem::path(prefPath) / ".cna_isolated_storage";
        SDL_free(prefPath);
    } else {
        // Fallback: use the Android internal storage path directly
        const char* internalPath = SDL_GetAndroidInternalStoragePath();
        if (internalPath) {
            root = std::filesystem::path(internalPath) / ".cna_isolated_storage";
        } else {
            root = std::filesystem::path("/data/local/tmp") / ".cna_isolated_storage";
        }
    }
```

This is a genuinely robust three-tier fallback (`SDL_GetPrefPath` → `SDL_GetAndroidInternalStoragePath`
→ a hardcoded `/data/local/tmp`), and it matches `ANDROID.md`'s own description of save-data
behavior almost word for word:

*From `ANDROID.md:186-193`:*

> Save data and configuration are written to the app's private internal storage via
> `SDL_GetPrefPath("org.openeggbert", "speedyblupi")`. This storage:
> - persists across app restarts,
> - is cleared when the app is uninstalled,
> - is **not** accessible to other apps.

The contrast with the read path is instructive: writing save data always goes through an SDL API
designed specifically for cross-platform writable-directory discovery, with Android as a named,
tested branch. Reading packaged content goes through a generic C++ standard library call
(`std::filesystem::exists()`) that was never designed with Android's asset-store model in mind at
all, and only *happens* to keep working there through the un-verified fallthrough behavior
described above. The same codebase treats writable storage and read-only content very differently
on this one platform, for reasons that make sense in isolation (there is no portable standard-library
API for "does this path exist inside an Android asset archive") but that leave exactly the seam this
chapter has been describing.

## Practical implications for anyone debugging this on a real device

`AUDIO_ANALYSIS.md`'s own suggested next steps apply directly, and are worth restating in this
chapter's platform-specific framing rather than only the audio-specific one:

1. Unzip an actual built `app-debug.apk` or `app-release.apk` and confirm every expected file under
   `assets/Content/` and `assets/worlds/` is present — this would settle the symlink-fragility
   question in the "Two symlinks" section above once and for all, for a specific Gradle/AGP version.
2. Add temporary logging around any `Load<T>()` failure path (or around `MIX_LoadAudio` for audio
   specifically) so a real device run surfaces which, if any, asset resolutions are actually
   failing, instead of failing silently.
3. If a genuine mismatch is found, `AUDIO_ANALYSIS.md`'s suggested fix is not "special-case Android
   inside `ResolveAssetPath`" but broader: replace the `std::filesystem::exists()` probes with an
   SDL3 I/O-based existence check (open-then-close via `SDL_IOFromFile`), so path resolution behaves
   consistently across desktop and Android/packaged builds — fixing the same class of problem for
   every asset type `ContentManager::Load<T>()` handles, not only sounds.

None of this has been done as of this checkout. This chapter, like the source document it is based
on, reports a plausible, code-grounded hypothesis — not a confirmed bug and not a fix.

## See also

- [Chapter 9](../part02-building-and-running/ch09-android-build.md) — the Android build process
  itself (Gradle, NDK, signing).
- [Chapter 40](../part06-audio/ch40-audio-issue-analysis.md) — the full analysis of
  `AUDIO_ANALYSIS.md`, including the high-pitched-sound-effect hypothesis this chapter does not
  cover.
- [Chapter 45](../part08-data-persistence-content/ch45-content-pipeline.md) — the content pipeline
  (`ContentManager`) as mobile-eggbert calls it, independent of platform.
- [Chapter 46](../part08-data-persistence-content/ch46-myresource-resource-management.md) —
  `MyResource` and resource lifetime management.
- [Chapter 53](ch53-web-virtual-filesystem.md) — the Web/Emscripten equivalent of this chapter,
  where the virtual filesystem's read-only/writable split is explicit and largely resolved rather
  than suspected.
