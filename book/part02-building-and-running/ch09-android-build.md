# Chapter 9: Android Build

`mobile-eggbert` ships a complete Android Gradle project under `android/`, producing an APK built
with SDL3's Java glue, the Android NDK, and CMake — the same `CMakeLists.txt` covered in
[Chapter 4](ch04-build-overview.md), invoked from inside the Gradle build via Android Studio's
`externalNativeBuild` mechanism. This chapter reads `ANDROID.md` (the project's own 251-line
Android build guide) in full, and cross-checks its claims against the real Gradle files —
`android/build.gradle`, `android/app/build.gradle`, `android/app/proguard-rules.pro`,
`android/settings.gradle`, and `android/gradle.properties`.

One immediate note on scope, worth flagging before the rest of this chapter: `README.md`'s own
"Backend status" summary states plainly, **"Android: planned"** (`README.md:214`). That line is
stale relative to the actual repository contents. `ANDROID.md` is a substantial, detailed,
251-line document describing a working build; the `android/` directory contains a complete, real
Gradle project with a real package name (`org.openeggbert.speedyblupi`), a real `AndroidManifest.xml`
declaring a real launcher `Activity`, and even build-output artifacts already present under
`android/app/.cxx/` from prior CMake/NDK configure runs. This chapter documents the Android build as
it actually exists in the repository, not as "planned" — but flags the `README.md` inconsistency
explicitly, since a reader skimming only `README.md`'s summary table would be misled into thinking
no Android support exists yet.

## Prerequisites

*From `ANDROID.md:8-18`:*

| Tool | Recommended version |
|------|---------------------|
| Android Studio | Ladybug (2024.2) or newer |
| Android SDK | API level 35 |
| Android NDK | 28.2.13676358 (installed via SDK Manager) |
| CMake (NDK bundle) | 3.21+ (installed via SDK Manager) |
| Java (JDK) | 17 (bundled with Android Studio) |
| Git | any recent version |

*From `ANDROID.md:19-24`:*
```markdown
### Install NDK and CMake via Android Studio

1. Open **Android Studio → Settings → SDK Manager → SDK Tools**.
2. Check **NDK (Side by side)** version **28.2.13676358**.
3. Check **CMake** (version 3.21 or higher).
4. Click **Apply** and let Android Studio download and install.
```

Cross-checking the NDK version against the actual Gradle configuration turns up a real
discrepancy: `android/app/build.gradle` declares a *different* NDK version than the one `ANDROID.md`
recommends installing:

*From `android/app/build.gradle:11-14`:*
```groovy
android {
    namespace = "org.openeggbert.speedyblupi"
    compileSdkVersion 35
    ndkVersion = "29.0.14206865"
```

`ANDROID.md` instructs installing NDK **28.2.13676358**, while `build.gradle` itself pins
`ndkVersion` to **29.0.14206865** — a different major version. `compileSdkVersion 35` does match
between the two documents (`ANDROID.md`'s "Android SDK | API level 35" and `build.gradle`'s
`compileSdkVersion 35`), so that part is consistent; the NDK version is the part that has drifted.
A reader following `ANDROID.md`'s prerequisite table verbatim and installing NDK 28.2.13676358 via
the SDK Manager would find that Gradle's own `externalNativeBuild` step requests NDK
29.0.14206865 specifically (Android Gradle Plugin resolves and, if necessary, auto-downloads the
exact `ndkVersion` pinned in `build.gradle`, rather than using whatever NDK happens to already be
installed), so the practical effect is likely a second, automatic NDK download rather than an
outright failure — but the two documents disagree on the specific version, and this book records
that as a real, observed inconsistency rather than silently reconciling it.

## Clone and initialise submodules

*From `ANDROID.md:28-38`:*
```markdown
## Clone and initialise submodules

```bash
git clone <repository-url> speedy-blupi-2013
cd speedy-blupi-2013
git submodule update --init --recursive
```

The vendored SDL3 / SDL_image / SDL_mixer sources are required.  They live under
`mobile-eggbert/../cna/third_party/`.
```

This matches the pattern already established in [Chapter 5](ch05-linux-build.md) and
[Chapter 8](ch08-web-emscripten-build.md): the real Git submodules (`third_party/SDL`,
`third_party/SDL_image`, `third_party/SDL_mixer`, `vendor/googletest`) live in `cna`'s own
`.gitmodules`, not `mobile-eggbert`'s (which has none). `ANDROID.md`'s phrasing here is notably more
accurate than `README.md`'s equivalent instruction, since it explicitly names the path
(`mobile-eggbert/../cna/third_party/`) where the vendored sources actually end up — correctly
implying that this command's real effect happens one level up from `mobile-eggbert` itself, in the
sibling `cna` checkout.

## How the APK actually reaches `mobile-eggbert`'s CMake build

The Gradle project's `externalNativeBuild` block is the mechanism that ties the Android build back
into the exact `CMakeLists.txt` read in [Chapter 4](ch04-build-overview.md):

*From `android/app/build.gradle:74-80`:*
```groovy
externalNativeBuild {
    cmake {
        // Point to the game's root CMakeLists.txt (one level up from android/).
        path '../../CMakeLists.txt'
        version "4.1.2"
    }
}
```

`path '../../CMakeLists.txt'` resolves, from `android/app/`, up two directory levels to
`mobile-eggbert`'s own root `CMakeLists.txt` — the same file this chapter's sibling chapters cover
for every other platform. This is why [Chapter 4](ch04-build-overview.md)'s reading of the
`if(ANDROID)` branches throughout `CMakeLists.txt` (the forced `SDL_RENDERER` backend, the `main`
shared-library target name, the `android`/`log` link libraries, the `lld`-without-`--start-group`
linker path) applies directly and completely to this Android build — there is exactly one CMake
project, and Gradle's native-build step is simply another caller of it, alongside the plain
command-line invocations used on other platforms.

The specific CMake arguments Gradle passes into that build are:

*From `android/app/build.gradle:23-33`:*
```groovy
externalNativeBuild {
    cmake {
        // Pass Android platform and C++ STL config.
        arguments "-DANDROID_PLATFORM=android-21",
                  "-DANDROID_STL=c++_static",
                  // Disable sharp-runtime and CNA tests (they use gtest
                  // which is not needed in the APK build).
                  "-DCNA_BUILD_TESTS=OFF",
                  "-DSHARP_RUNTIME_BUILD_TESTS=OFF"
        abiFilters 'arm64-v8a', 'x86_64'
    }
}
```

`-DANDROID_PLATFORM=android-21` sets the minimum Android API level the native code targets (API 21,
matching `defaultConfig`'s `minSdkVersion 21` below), `-DANDROID_STL=c++_static` selects a
statically-linked C++ standard library (avoiding a separate shared `libc++_shared.so` dependency in
the APK), and `-DCNA_BUILD_TESTS=OFF`/`-DSHARP_RUNTIME_BUILD_TESTS=OFF` disable the GTest-based test
suites of both `cna` and `sharp-runtime` — unnecessary in a shipped APK and, per the comment, using
a testing framework (`gtest`) that has no reason to be compiled into a mobile game build at all.
This `-DCNA_BUILD_TESTS=OFF` flag is the same one seen in [Chapter 7](ch07-direct3d-wine-proton.md)'s
D3D11/D3D12 cross-build commands, for a related but distinct reason there (MinGW POSIX-portability
gaps in `cna`'s GTest suite specifically, vs. simple unnecessary bloat here).

### ABI filters: a second real discrepancy with `ANDROID.md`

`abiFilters 'arm64-v8a', 'x86_64'` in `build.gradle` already lists **two** ABIs. `ANDROID.md`,
however, describes the current configuration as building for **one** ABI only, and gives
instructions for adding a second:

*From `ANDROID.md:159-167`:*
```markdown
## Supported ABIs

The current Gradle configuration builds for **arm64-v8a** only.  To add other
ABIs (e.g. `x86_64` for the emulator) edit
`android/app/build.gradle` and extend the `abiFilters` list:

```groovy
abiFilters 'arm64-v8a', 'x86_64'
```
```

The code sample `ANDROID.md` gives as the *instruction for what to add* is, verbatim, exactly what
`android/app/build.gradle` already contains today. In other words: the change `ANDROID.md`
describes as something a reader needs to go make themselves has already been made in the actual
project. This is a second concrete instance (alongside the NDK version mismatch above) of
`ANDROID.md`'s prose having fallen slightly behind the Gradle files it describes — the document was
evidently accurate at some earlier point (when the project genuinely built `arm64-v8a` only) and
has not been updated to reflect that `x86_64` (useful specifically for running in the Android
emulator, which typically doesn't emulate `arm64-v8a` efficiently on an x86_64 host) was
subsequently added.

## Build the debug APK

*From `ANDROID.md:41-56`:*
```bash
cd mobile-eggbert/android
./gradlew assembleDebug
```

*"The first build downloads Gradle (≈ 150 MB) and compiles the NDK libraries, so it may take
several minutes. Subsequent incremental builds are much faster."*

The produced APK path:

```
mobile-eggbert/android/app/build/outputs/apk/debug/app-debug.apk
```

`android/settings.gradle` contains a single line, `include ':app'` — this is a single-module
Gradle project with just the one `app` module, consistent with the game having no separate Android
library modules of its own. `android/build.gradle` (the top-level, project-wide Gradle file)
declares the Android Gradle Plugin dependency and repository sources:

*From `android/build.gradle:1-21`:*
```groovy
// Top-level build file.
buildscript {
    repositories {
        mavenCentral()
        google()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:8.7.3'
    }
}

allprojects {
    repositories {
        mavenCentral()
        google()
    }
}

task clean(type: Delete) {
    delete rootProject.buildDir
}
```

confirming Android Gradle Plugin version 8.7.3, resolved from Maven Central and Google's Maven
repository. `android/gradle.properties` sets two project-wide Gradle JVM settings:

*From `android/gradle.properties:1-3`:*
```properties
org.gradle.jvmargs=-Xmx2048m
android.useAndroidX=true
```

`-Xmx2048m` caps the Gradle daemon's JVM heap at 2 GiB, and `android.useAndroidX=true` opts into
AndroidX (the modern successor to the legacy Android Support Library) for any AndroidX-aware
tooling in the build — notable here since, per `app/build.gradle`'s own `dependencies {}` block
(quoted further below), this project pulls in essentially no Java/Kotlin libraries beyond what
SDL's own glue provides, so this setting mostly future-proofs the build rather than reflecting a
current heavy AndroidX dependency.

## Install and run on a device or emulator

*From `ANDROID.md:59-78`:*
```bash
# Install
adb install app/build/outputs/apk/debug/app-debug.apk

# Launch
adb shell am start -n org.openeggbert.speedyblupi/.SpeedyBlupiActivity

# View logs (filter by the app's tag or by pid)
adb logcat -s SDL SpeedyBlupi

# Uninstall
adb uninstall org.openeggbert.speedyblupi
```

Both the package name (`org.openeggbert.speedyblupi`) and the launcher `Activity`
(`.SpeedyBlupiActivity`) match the real `AndroidManifest.xml` exactly:

*From `android/app/src/main/AndroidManifest.xml`:*
```xml
<activity
    android:name=".SpeedyBlupiActivity"
    android:label="@string/app_name"
    android:alwaysRetainTaskState="true"
    android:launchMode="singleTop"
    android:screenOrientation="sensorLandscape"
    android:configChanges="layoutDirection|locale|orientation|uiMode|screenLayout|screenSize|smallestScreenSize|keyboard|keyboardHidden|navigation"
    android:theme="@style/AppTheme"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>
```

The manifest's `android:screenOrientation="sensorLandscape"` locks the app to landscape
orientation (following the sensor for which landscape direction, upside-down or not) — consistent
with the game's fixed 4:3-in-landscape logical resolution (`640×480`, per
[Chapter 10](ch10-config-legacy-vs-modern.md) and `Pixmap.cpp`'s own viewport-geometry comments read
in [Chapter 4](ch04-build-overview.md)). A comment above the `Activity` declaration in the manifest
explains the choice of a custom `Activity` subclass name rather than using SDL's own default:
`SpeedyBlupiActivity` extends SDL3's `SDLActivity` purely to customize the application name and
package while reusing the entire SDL3 Java glue layer unmodified. The manifest also declares
`android.hardware.touchscreen` as `required="true"` (the game genuinely needs touch input to be
playable in its default control scheme) while `android.hardware.gamepad` is `required="false"`
(an optional input method), plus a `VIBRATE` permission for potential haptic feedback and OpenGL ES
2.0 as the declared minimum GL feature level (consistent with `SDL_RENDERER` running on GLES
underneath on Android, per [Chapter 4](ch04-build-overview.md)).

## Creating a release signing key and `key.properties`

`ANDROID.md` documents the standard Android release-signing workflow: generating a keystore with
`keytool`, then writing a `key.properties` file the release build reads:

*From `ANDROID.md:82-116`:*
```bash
cd android
keytool -genkeypair -v \
  -keystore speedy-blupi-release.keystore \
  -alias speedy-blupi \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

```properties
storeFile=speedy-blupi-release.keystore
storePassword=YOUR_STORE_PASSWORD
keyAlias=speedy-blupi
keyPassword=YOUR_KEY_PASSWORD
```

`ANDROID.md` includes explicit warnings not to commit either the keystore or `key.properties` to
version control, and states both are listed in `.gitignore`. The actual `build.gradle` logic
confirms exactly how a missing `key.properties` is handled — not silently, but with a deliberately
clear, early failure:

*From `android/app/build.gradle:5-9, 49-62`:*
```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}
```
```groovy
buildTypes {
    release {
        if (!keystorePropertiesFile.exists()) {
            doFirst {
                throw new GradleException(
                    "\n\n" +
                    "========================================================\n" +
                    " ERROR: key.properties not found in android/ directory.\n" +
                    " Cannot build a signed release APK.\n" +
                    " See ANDROID.md for instructions on creating key.properties.\n" +
                    "========================================================\n"
                )
            }
        }
        signingConfig signingConfigs.release
        minifyEnabled false
        debuggable false
        proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
    }
```

This matches `ANDROID.md`'s own claim precisely: *"If `key.properties` is not present, the build
will stop immediately with a clear error message rather than a confusing Gradle failure."* The
`doFirst { throw new GradleException(...) }` pattern runs this check before any actual compilation
work for the `release` build type begins, and the thrown message even points the developer back to
`ANDROID.md` for remediation instructions — a deliberately friendly failure mode rather than a raw
stack trace from a later, more obscure signing-related Gradle task failure.

Also visible in that same snippet: `minifyEnabled false` — code shrinking/obfuscation via R8/
ProGuard is explicitly **disabled** for release builds, even though `proguardFiles` still lists both
the default optimized ProGuard rules and the project's own `proguard-rules.pro`. Since
`minifyEnabled` is `false`, those `proguardFiles` entries are effectively inert for a straightforward
`assembleRelease` (ProGuard/R8 processing only runs when minification is enabled) — worth noting
as a real, if perhaps unintentional, detail of the current release configuration.

The actual `proguard-rules.pro` contents are minimal:

*From `android/app/proguard-rules.pro`:*
```
# SDL Activity and related classes must not be obfuscated.
-keep class org.libsdl.app.** { *; }
-keep class org.openeggbert.speedyblupi.** { *; }
```

Two `-keep` rules protecting SDL's own Java glue package (`org.libsdl.app`) and the game's own
Java package (`org.openeggbert.speedyblupi`) from being renamed or stripped — standard practice
since SDL's native code calls into specific Java class/method names by reflection-adjacent JNI
mechanisms that would break under aggressive renaming, even though (per the point above) this file
is not currently exercised by a default release build with minification off.

## Building a signed release APK

*From `ANDROID.md:120-136`:*
```bash
cd android
export JAVA_HOME=/home/robertvokac/Downloads/openjdk-17.0.2_linux-x64_bin/jdk-17.0.2
./gradlew clean assembleRelease
```

Release APK output:
```
android/app/build/outputs/apk/release/app-release.apk
```

The `JAVA_HOME` value shown is a literal, machine-specific path from the document's original
author's own environment — a reader following this instruction verbatim needs to substitute their
own JDK 17 installation path rather than copy this exact string. Verifying the signature and
installing follow standard Android tooling:

*From `ANDROID.md:139-151`:*
```bash
apksigner verify --verbose app/build/outputs/apk/release/app-release.apk
adb install -r app/build/outputs/apk/release/app-release.apk
```

with a note that side-loaded APKs (installed outside the Play Store) may require the user to
enable "Install unknown apps" in Android's security settings.

## Asset layout

*From `ANDROID.md:171-183`:*

| Source directory | Path in APK |
|------------------|-------------|
| `Content/backgrounds/` | `Content/backgrounds/` |
| `Content/icons/`       | `Content/icons/` |
| `Content/sounds/`      | `Content/sounds/` |
| `worlds/`              | `worlds/` |

*"Game assets are packaged into the APK as Android assets. At runtime they are read via
`SDL_IOFromFile` which transparently falls back to the APK `AAssetManager` when a file is not found
in internal storage."*

This is implemented in `app/build.gradle`'s `sourceSets` block, and its own comment explains the
mechanism for *why* directory structure is preserved without an explicit per-file mapping:

*From `android/app/build.gradle:82-107`:*
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
sourceSets {
    main {
        assets.srcDirs = ['src/main/assets']
        java.srcDirs = [
            // SDL3 Java glue (SDLActivity, SDLAudioManager, etc.)
            '../../../cna/third_party/SDL/android-project/app/src/main/java',
            // Game-specific Java (just the minimal stub subclassing SDLActivity)
            'src/main/java'
        ]
        res.srcDirs = ['src/main/res']
        manifest.srcFile 'src/main/AndroidManifest.xml'
    }
}
```

The comment's closing line is the key mechanical detail: Android Gradle Plugin's asset merger only
pulls in files/directories that are actually *reachable* from a declared `assets.srcDirs` entry, so
pointing `assets.srcDirs` in a way that resolves up to (or symlinks/includes) the game's own
`Content/`/`worlds/` root is what keeps unrelated files (`src/`, `cmake/`, the `CMakeLists.txt`
itself) out of the packaged APK automatically, without needing an explicit exclude list. The
`java.srcDirs` entry pointing three levels up into `../../../cna/third_party/SDL/android-project/...`
is the concrete confirmation that SDL3's own Java-side `SDLActivity`/`SDLAudioManager` glue classes
are compiled directly from the vendored `cna` submodule checkout rather than consumed as a prebuilt
AAR — matching `ANDROID.md`'s earlier statement that "the vendored SDL3 ... sources are required."

## Writable / persistent storage

*From `ANDROID.md:186-193`:*
```markdown
Save data and configuration are written to the app's private internal storage
via `SDL_GetPrefPath("org.openeggbert", "speedyblupi")`.  This storage:

- persists across app restarts,
- is cleared when the app is uninstalled,
- is **not** accessible to other apps.
```

This is a materially different persistence model from both the native desktop build (a plain
`IsolatedStorage`-backed file next to, or under a user-profile path relative to, the executable —
see [Chapter 43](../part08-data-persistence-content/ch43-gamedata-save-format.md)) and the Web
build's browser-IndexedDB-backed IDBFS mount (see [Chapter 8](ch08-web-emscripten-build.md)):
Android's `SDL_GetPrefPath()` resolves to a per-app private directory under Android's own scoped
storage model, which is why it is both automatically isolated from other apps and automatically
wiped on uninstall — behaviour governed by the Android OS itself rather than by any
`mobile-eggbert`-specific code.

## Android launcher icon

*From `ANDROID.md:197-219`:* the launcher icon is generated from a single source file, `icon.bmp`,
into the standard Android per-density `mipmap-*` PNG variants (Android does not accept BMP directly
for launcher icons), using ImageMagick's `convert` tool at five densities (`mdpi` 48px through
`xxxhdpi` 192px) for the flat icon, plus a second pass applying a circular alpha mask for the
`ic_launcher_round` variants Android uses on devices/launchers that prefer round icons. This is a
manual, run-when-`icon.bmp`-changes regeneration step rather than something Gradle automates as
part of every build.

## Troubleshooting

*From `ANDROID.md:223-251`:* the document closes with three troubleshooting entries: an
"NDK not found" Gradle failure (check that the `ndkVersion` in `app/build.gradle` matches an
installed NDK — directly relevant given this chapter's own finding above that `ANDROID.md`'s
prerequisite table and `build.gradle`'s actual pinned version disagree), an `adb: device not
found` issue (enable Developer Options/USB debugging, verify with `adb devices`), an app-crash-on-
launch section pointing to `adb logcat` and naming two common causes (`libmain.so` missing —
matching the `SHARED` library target name set for `ANDROID` in `CMakeLists.txt:96` and covered in
[Chapter 4](ch04-build-overview.md) — or a missing `Content/` directory from an incomplete
submodule checkout), and a silent-audio entry recommending `aapt dump resources ... | grep sound`
to confirm sound files were actually packaged into the APK, noting that the vendored SDL_mixer
build "enables WAV by default," consistent with `PLAN.md`'s own measurement that all 93 of
`mobile-eggbert`'s bundled sound files under `Content/sounds/` are `.wav` files.

## See also

- [Chapter 4: Build Overview (CMake)](ch04-build-overview.md)
- [Chapter 5: Linux Build](ch05-linux-build.md)
- [Chapter 43: GameData: Save Format](../part08-data-persistence-content/ch43-gamedata-save-format.md)
- [Chapter 51: Android Deep Dive](../part10-platform-deep-dives/ch51-android-deep-dive.md)
