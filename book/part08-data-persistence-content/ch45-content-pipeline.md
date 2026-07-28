# Chapter 45: The Content Pipeline

## Scope of this chapter

This chapter surveys what actually ships inside `mobile-eggbert/Content/` and how the game's own
code loads it. It deliberately stays on the mobile-eggbert side of the line: every load call in
this chapter goes through `IGame1::getContentProperty().Load<Texture2D>(path)` or
`Load<SoundEffect>(path)` — the same XNA-style `ContentManager` API the original Windows Phone game
used. How CNA implements that `Content.Load<T>()` call underneath — asset resolution, decoding,
caching internals — is CNA's own concern and is covered by the sister project, `cna-bible`, not
here (see `CLAUDE.md`'s scope note). What this chapter documents is the **call sites**: which files
mobile-eggbert asks for, in what order, and under what naming convention.

## What is actually in `Content/`

The `Content/` directory has exactly three subdirectories, no nesting beyond that:

| Directory | File count | Content |
|---|---|---|
| `Content/icons/` | 9 | Sprite-atlas PNGs: `blupi.png`, `blupi1.png`, `object-m.png`, `element.png`, `explo.png`, `button.png`, `pad.png`, `jauge.png`, `text.png` |
| `Content/backgrounds/` | 38 | Per-region background PNGs (`decorNNN.png`), fixed UI-phase backgrounds (`init.png`, `pause.png`, `lost.png`, `win.png`, `setup.png`, `trial.png`, `wait.png`), and three special images (`speedyblupi.png`, `blupiyoupie.png`, `gear.png`) |
| `Content/sounds/` | 93 | `sound000.wav` through `sound092.wav` |

*(Directory contents verified directly, `Content/icons/`, `Content/backgrounds/`,
`Content/sounds/` — see `mobile-eggbert/Content/`.)*

Breaking the 38 background files down further: 28 are `decorNNN.png` per-region art
(`decor000.png` through `decor031.png`, but with gaps — `decor005`, `decor014`, `decor017`, and
`decor023` do not exist), 7 are fixed single-purpose UI-phase backgrounds (`init.png`, `pause.png`,
`lost.png`, `win.png`, `setup.png`, `trial.png`, `wait.png`), and 3 are special-purpose images
loaded eagerly at startup (`speedyblupi.png`, `blupiyoupie.png`, `gear.png`, discussed below).
Cross-checking the `region=` values actually used across all 78 `worlds/*.txt` files
(see [Chapter 44](ch44-worlds-level-file-format.md)) against the available `decorNNN.png` files
confirms the gaps are intentional, not missing assets: every `region=` value that appears in a real
level file (`0`–`4`, `6`–`13`, `15`–`16`, `18`–`22`, `24`–`31`) has a matching PNG on disk, and the
four skipped numbers (`5`, `14`, `17`, `23`) are never referenced by any shipped level either —
whatever regions those numbers once denoted were apparently retired from both the level data and
the art assets together, consistently.

Two things are conspicuously absent from this list, and both are worth calling out because a reader
skimming a typical XNA-derived game's `Content/` folder might expect them: there is no `.xnb`
compiled-content pipeline output anywhere (the original Windows Phone / XNA build would have run a
Content Pipeline build step to compile `.png`/`.wav` sources into `.xnb` binary assets; the C++
port instead loads the raw `.png`/`.wav` files directly, which is what makes `Content.Load<T>()`'s
CNA-side implementation a runtime image/audio decoder rather than a binary deserializer — again,
CNA's concern, not mobile-eggbert's), and there is no `Content/fonts/` — all in-game text is drawn
from the `text.png` glyph atlas in `icons/` rather than from a system or TrueType font (see
[Chapter 35](../part05-sprites-rendering-animation/ch35-text-rendering.md)).

The nine icon atlases and 38 background PNGs are exactly the numbers already recorded in
`PLAN.md`'s source-size survey; this chapter grounds those counts against the actual loader code
that consumes them.

## Icons and backgrounds: `Pixmap::LoadContent()`

All nine icon atlases, plus three of the backgrounds, are loaded eagerly, once, at startup, inside
`Pixmap::LoadContent()`:

*From `Pixmap.cpp:251-304`:*
```cpp
    void Pixmap::LoadContent()
    {
        CNA::Logger::Info("SpeedyBlupi: Pixmap::LoadContent entered");
        CNA::Logger::Info("SpeedyBlupi: asset root = " + game1->getContentProperty().getRootDirectoryProperty());
        spriteBatch = std::make_unique<Microsoft::Xna::Framework::Graphics::SpriteBatch>(
            game1->getGraphicsDeviceProperty());

        // Select asset sub-folders based on the configured resolution scale.
        // Icons:
        //   1x -> "icons/"    (original assets)
        //   2x -> "icons2x/"  (TODO: 2x assets not yet available)
        //   4x -> "icons4x/"  (4x upscaled assets)
        // Backgrounds:
        //   1x -> "backgrounds/"
        //   2x -> "backgrounds2x/"  (TODO: 2x assets not yet available)
        //   4x -> "backgrounds4x/"
        std::string iconPrefix;
        std::string backgroundPrefix;
        switch (Config::RESOLUTION_SCALE)
        {
        case 4:
            iconPrefix       = "icons4x/";
            backgroundPrefix = "backgrounds4x/";
            break;
        case 2:
            // TODO: 2x assets are not yet available. Add icons2x/ and backgrounds2x/ when ready.
            iconPrefix       = "icons2x/";
            backgroundPrefix = "backgrounds2x/";
            break;
        default:
            iconPrefix       = "icons/";
            backgroundPrefix = "backgrounds/";
            break;
        }
        CNA::Logger::Info("SpeedyBlupi: loading icons (prefix=" + iconPrefix + ")");
        CNA::Logger::Info("SpeedyBlupi: loading backgrounds (prefix=" + backgroundPrefix + ")");

        bitmapText    = game1->getContentProperty().Load<Texture2D>(iconPrefix + "text");
        bitmapButton  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "button");
        bitmapJauge   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "jauge");
        bitmapBlupi   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "blupi");
        bitmapBlupi1  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "blupi1");
        bitmapObject  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "object-m");
        bitmapElement = game1->getContentProperty().Load<Texture2D>(iconPrefix + "element");
        bitmapExplo   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "explo");
        bitmapPad     = game1->getContentProperty().Load<Texture2D>(iconPrefix + "pad");

        bitmapSpeedyBlupi = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "speedyblupi");
        bitmapBlupiYoupie = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "blupiyoupie");
        bitmapGear        = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "gear");

        CNA::Logger::Info("SpeedyBlupi: Pixmap::LoadContent done");
        UpdateGeometry();
    }
```

Every one of the nine `Content/icons/*.png` atlases maps 1:1 to a `bitmapXxx` member loaded exactly
once here, using a filename (without extension) that matches the on-disk PNG. Three background
images — `speedyblupi.png` (the title/splash art), `blupiyoupie.png` (the "you win" celebration
screen background — see [Chapter 34](../part05-sprites-rendering-animation/ch34-backgrounds-and-level-art.md)),
and `gear.png` (background art for a settings/options screen) — are also loaded up front rather
than on demand, presumably because they are needed on the very first screens the player sees,
before any level has been selected.

### Resolution-scale asset folders — a real prefix mechanism, not yet real content

The `iconPrefix`/`backgroundPrefix` switch is a genuine, working piece of code — `Config::
RESOLUTION_SCALE` (see [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md))
really does change which subfolder every `Load<Texture2D>()` call reaches into. But as the inline
`TODO` comment states plainly, only the `1x` folders (`icons/`, `backgrounds/`) actually exist in
the shipped `Content/` tree today; `icons2x/`, `icons4x/`, `backgrounds2x/`, `backgrounds4x/` are
referenced by this switch but do not exist on disk. Running the game with `RESOLUTION_SCALE` set to
`2` or `4` would therefore fail every `Load<Texture2D>()` call in this method — this is
forward-looking infrastructure for a not-yet-delivered higher-resolution asset pass, not a
currently working feature. `PLAN.md`'s own file-count survey (9 icon PNGs, 38 background PNGs)
independently confirms only the base-resolution folders are present.

### Per-region backgrounds: loaded lazily, one at a time, by `Pixmap::BackgroundCache`

The remaining 35 background PNGs — the `decorNNN.png` region art and the fixed-phase screens
(`init.png`, `pause.png`, `lost.png`, `win.png`, `setup.png`, `trial.png`, `wait.png`) — are **not**
loaded in `LoadContent()`. They go through a separate, on-demand method, `Pixmap::BackgroundCache`,
which loads exactly one background texture into a single reusable slot, replacing whatever was
there before:

*From `Pixmap.cpp:321-333`:*
```cpp
    void Pixmap::BackgroundCache(const string& name)
    {
        std::string backgroundPrefix;
        switch (Config::RESOLUTION_SCALE)
        {
        case 4:  backgroundPrefix = "backgrounds4x/"; break;
        case 2:  backgroundPrefix = "backgrounds2x/"; break;
        default: backgroundPrefix = "backgrounds/";   break;
        }
        CNA::Logger::Info("SpeedyBlupi: BackgroundCache loading " + backgroundPrefix + name);
        bitmapBackground = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + name);
        CNA::Logger::Info("SpeedyBlupi: BackgroundCache done " + backgroundPrefix + name);
    }
```

`Game1::SetPhase()` calls `BackgroundCache()` with the fixed-phase names whenever the game
transitions into a non-gameplay phase — `"init"`, `"pause"`, `"lost"`, `"win"`, `"setup"`,
`"trial"` (`Game1.cpp:1027-1049`, one call per `case` in the phase `switch`) — while
`Decor::LoadImages()` calls it with a computed `decorNNN` name whenever a level starts or resumes:

*From `Decor.cpp:245-252`:*
```cpp
    bool Decor::LoadImages()
    {
        std::ostringstream oss;
        oss << "decor" << std::setw(3) << std::setfill('0') << m_region;
        string name = oss.str();
        m_pixmap->BackgroundCache(name);
        return true;
    }
```

`m_region` is exactly the `region=` field read out of the level's `DescFile:` header (see
[Chapter 44](ch44-worlds-level-file-format.md)) — so which of the roughly 30 `decorNNN.png` images
gets loaded is entirely level-data-driven, one texture at a time, and is *replaced* (not
accumulated into a cache keyed by name, despite the method's name) on every level transition. There
is no eviction logic to worry about because there is only ever one `bitmapBackground` slot; the
"cache" in `BackgroundCache` refers to holding the currently-active background in a member variable
for repeated per-frame drawing, not to a multi-entry lookup cache.

This lazy, single-slot loading pattern is also where the background/foreground split documented in
[Chapter 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) matters directly: the one
`bitmapBackground` texture loaded here by `Pixmap::BackgroundCache(name)` supplies only the
back-most parallax scenery (distant terrain, sky) for a level's region. It is not where the level's
foreground tiles come from — those are drawn separately, per tile, from the `icons/object-m.png`
atlas loaded in `LoadContent()` above, using the numeric `icon` values stored in
`Decor::m_decor[][]` (populated from the level file's `Decor:` block) directly as sprite indices
for the large majority of static tiles, with a small set of animated/hazard icons remapped through
a per-icon frame table first. See [Chapter 16](../part04-decor-simulation/ch16-tile-map.md) and
[Chapter 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) for the full argument, which
corrects an earlier, unverified hypothesis in this project's own `PLAN.md` that the tile-grid icon
numbers formed a purely invisible layer never contributing to visible art.

## Sounds: `Sound::LoadContent()`

All 93 `.wav` files are loaded eagerly, in one pass, at startup — mirroring `Pixmap`'s icon-atlas
loading rather than its lazy per-region background loading:

*From `Sound.cpp:133-163`:*
```cpp
    void Sound::LoadContent()
    {
#ifdef SOUND_DISABLED
        return;
#endif
        if (!Def::getHasSoundProperty())
        {
            return;
        }

        static constexpr SharpRuntime::intcs SOUND_COUNT = 93;

        soundEffects.clear();
        soundEffects.reserve(SOUND_COUNT);

        using Microsoft::Xna::Framework::Audio::SoundEffect;

        for (SharpRuntime::intcs i = 0; i < SOUND_COUNT; ++i)
        {
            std::ostringstream oss;
            oss << "sounds/sound"
                << std::setw(3)
                << std::setfill('0')
                << i
                << ".wav";

            soundEffects.push_back(
                game1->getContentProperty().Load<SoundEffect>(oss.str())
            );
        }
    }
```

The naming convention (`sounds/sound000.wav` … `sounds/sound092.wav`, three-digit zero-padded
index) matches exactly `ls Content/sounds/` — 93 files, `sound000.wav` through `sound092.wav`, no
gaps. `soundEffects` is a flat, index-addressed vector: playing "sound N" elsewhere in the codebase
(via `SoundChannel`, see [Chapter 38](../part06-audio/ch38-sound-isound-architecture.md) and
[Chapter 39](../part06-audio/ch39-soundchannel-and-mixing.md)) is simply indexing into this vector,
with no name-based lookup at play time — the file-level doc comment for `Sound.cpp` spells out this
convention explicitly:

*From `Sound.cpp:16-21`:*
```
 * ### LoadContent asset naming
 * Assets are loaded with a zero-padded three-digit counter:
 * @code
 *   sounds/sound000.wav, sounds/sound001.wav, ..., sounds/sound092.wav
 * @endcode
 * The padding is generated with @c std::setw(3) / @c std::setfill('0') so
 * the filenames are portable across all target platforms.
```

Two guard conditions can skip sound loading entirely: the compile-time `SOUND_DISABLED` macro
(defined automatically whenever `SOUND_ENABLED` is not externally defined —
`Sound.cpp:56-58` — useful for headless/unit-test builds that must never touch an audio backend),
and the runtime `Def::getHasSoundProperty()` check. Reading that check's actual definition shows it
is not a live capability probe at all:

*From `Def.hpp:195-198`:*
```cpp
        static constexpr bool getHasSoundProperty()
        {
            return true;
        }
```

It is a `constexpr` function that always returns `true` — a vestige of what was presumably, on the
original Windows Phone hardware line, a genuine per-device or per-platform capability flag (some
early Windows Phone models shipped without functioning audio, or a build target needed to disable
sound entirely), now permanently pinned "on" in this port. `AUDIO_ANALYSIS.md` (an existing analysis
document in the repository, not this book's own conclusion — see
[Chapter 40](../part06-audio/ch40-audio-issue-analysis.md) for a full treatment) independently flags
this same function as always-`true` and "not currently platform-sensitive." In practice this means
the only way sound loading is actually skipped in a real build today is the compile-time
`SOUND_DISABLED` path, not this runtime check. Either guard, when active, causes `LoadContent()` to
return immediately, leaving `soundEffects` empty and every later `Load`-dependent playback call
effectively a no-op.

## Content loading is entry-point-driven, not lazy-on-first-use (mostly)

Between `Pixmap::LoadContent()` (9 icon atlases + 3 backgrounds, eager) and
`Sound::LoadContent()` (93 sounds, eager), the overwhelming majority of the game's binary content is
pulled into memory in one pass at startup, driven by `Game1`'s own top-level `LoadContent()`
override (see [Chapter 12](../part03-architecture/ch12-game1-state-machine.md) for the XNA
`Game.LoadContent()` lifecycle hook that ultimately triggers both of these). The one deliberate
exception is the per-region background art, which is streamed in one texture at a time via
`BackgroundCache()` exactly when a level or UI phase needs it — the only genuinely lazy,
data-driven content load path in the game. There is no explicit unloading/disposal path visible in
either `Pixmap::LoadContent()` or `Sound::LoadContent()`; texture and sound-effect lifetime is left
to whatever the underlying `Texture2D`/`SoundEffect` resource-management model provides (CNA's
concern, out of scope here).

## Summary

Mobile Eggbert's content pipeline, as seen from the game's own code, is almost the simplest
possible design: nine hand-authored sprite atlases and 93 numbered `.wav` files loaded once at
startup by name, plus a resolution-scale prefix switch that anticipates 2x/4x asset variants that
do not yet exist on disk, and a single lazily-swapped background texture slot driven entirely by
level data (`region=`) and UI phase transitions. There is no `.xnb` binary content-pipeline step,
no font directory, and — per `Pixmap::BackgroundCache`'s naming despite its single-slot behaviour —
no multi-entry runtime cache to reason about. What each of the nine icon atlases actually contains,
pixel-for-pixel, and how their sprite grids are sliced into individual game icons, is the subject of
[Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md).

## See also

- [Chapter 12: Game1 — the State Machine](../part03-architecture/ch12-game1-state-machine.md) —
  the XNA `LoadContent()` lifecycle hook that triggers both `Pixmap::LoadContent()` and
  `Sound::LoadContent()`.
- [Chapter 16: The Tile Map](../part04-decor-simulation/ch16-tile-map.md) — the background-art vs.
  collision-layer separation that `BackgroundCache` sits on one side of.
- [Chapter 28: Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md) and
  [Chapter 29: The Sprite Atlas System](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md)
  — full detail on how each loaded icon atlas is sliced into individual sprites.
- [Chapter 34: Backgrounds and Level Art](../part05-sprites-rendering-animation/ch34-backgrounds-and-level-art.md)
  — the `decorNNN.png`/fixed-phase background images themselves, illustrated.
- [Chapter 35: Text Rendering](../part05-sprites-rendering-animation/ch35-text-rendering.md) — why
  there is no font directory: all text is drawn from `text.png`.
- [Chapter 38: Sound/ISound Architecture](../part06-audio/ch38-sound-isound-architecture.md) — how
  the 93-entry `soundEffects` vector loaded here is played back.
- [Chapter 44: Worlds — Level File Format](ch44-worlds-level-file-format.md) — the `region=` field
  that drives `Decor::LoadImages()`'s `BackgroundCache()` call.
