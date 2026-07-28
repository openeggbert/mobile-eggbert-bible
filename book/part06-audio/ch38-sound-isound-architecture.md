# Chapter 38: Sound/ISound Architecture

Mobile Eggbert's audio subsystem is small by comparison to the 11,720-line `Decor.cpp` gameplay
core, but it is touched from dozens of places in that core, and it is where three different
concerns meet: a pure-virtual interface that keeps gameplay code decoupled from any particular
audio backend, a concrete implementation that talks to CNA's SDL3-based sound classes, and a
verbatim-ported per-channel tuning table inherited from the original 2013 Windows Phone/XNA
release. This chapter covers the interface/implementation split and the playback pipeline; the
tuning table itself is the subject of [Chapter 39](ch39-soundchannel-and-mixing.md).

## The `ISound` interface

`ISound.hpp` declares a pure-virtual interface with no data members and no implementation at all
— it exists purely to let `Decor`, `InputPad`, and `Game1` depend on "some sound player" without
depending on the concrete `Sound` class or, transitively, on the CNA audio types it wraps
(`Microsoft::Xna::Framework::Audio::SoundEffect` / `SoundEffectInstance`). This is the standard
interface/implementation split used throughout the codebase (compare `IPixmap`/`Pixmap` in
[Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)).

*From `ISound.hpp:41-133`:*
```cpp
class ISound
{
public:
    virtual ~ISound() = default;
    virtual void LoadContent() = 0;
    virtual bool Create() = 0;
    virtual void SetState(bool bState) = 0;
    virtual void SetCDAudio(bool bAudio) = 0;
    virtual bool GetEnable() = 0;
    virtual void SetAudioVolume(int volume) = 0;
    virtual int GetAudioVolume() = 0;
    virtual void SetMidiVolume(int volume) = 0;
    virtual int GetMidiVolume() = 0;
    virtual void StopAll() = 0;
    virtual bool PlayImage(SoundChannel channel, TinyPoint pos, int rank = -1, bool bLoop = false) = 0;
    virtual bool PosImage(SoundChannel channel, TinyPoint pos) = 0;
    virtual bool Stop(SoundChannel channel) = 0;
};
```

Eleven methods, four of which (`SetCDAudio`, `SetMidiVolume`, `GetMidiVolume`, and — as we'll see
— `SetState`) are vestiges of the original Windows Phone game that the concrete implementation
answers with no-ops or fixed constants. The interface was kept complete rather than trimmed down,
which is a useful signal for a reader trying to understand the game's Windows-Phone-era shape:
the original C# game had a CD-audio / MIDI music layer and an audio-focus enable/disable hook for
phone-call interruptions, neither of which the C++ port needs, but both of which remain visible
in the interface's shape.

The header's own doc comment states the positional-audio convention plainly: `PlayImage` and
`PosImage` both take a `pos` parameter that is a point in **logical game-space, 640×480**, and
volume/balance are derived from that point relative to the viewport — not from any 3D or true
stereo distance model. This 640×480 space is the same fixed HUD coordinate system used throughout
the rendering and input code (see `Def::LXIMAGE` / `Def::LYIMAGE` in `Def.hpp:147-148`, and
[Chapter 41](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) for how `InputPad`
uses the same space for hit-testing).

One documentation note embedded directly in the header is worth repeating verbatim, because it is
effectively a warning to future maintainers not to "clean up" call sites without understanding
why they exist:

*From `ISound.hpp:38-40`:*
```cpp
/**
 * @note Sound triggers in Decor are tied to gameplay events. Do not move
 *       PlayImage calls without preserving the original event timing.
 */
```

## `Sound`: the concrete implementation

`Sound` (declared in `Sound.hpp`, 427 lines including its extensive Doxygen commentary; implemented
in `Sound.cpp`, 335 lines) is the sole production implementation of `ISound`. It is constructed
once by `Game1` and handed out by pointer to `Decor` and `InputPad`.

### Construction and dependencies

*From `Sound.hpp:214-246`:*
```cpp
class Sound : public ISound
{
    ...
public:
    virtual ~Sound() = default;
    static constexpr int MAXVOLUME = 20;

private:
    IGame1* game1;
    const GameData& gameData;
    std::vector<Microsoft::Xna::Framework::Audio::SoundEffect> soundEffects;
    std::list<Play> plays;
    double volume;

public:
    Sound(IGame1* game1, GameData& gameData);
    Sound(const Sound&) = delete;
    Sound& operator=(const Sound&) = delete;
    ...
};
```

`Sound` holds a non-owning `IGame1*` (used only to reach the content manager for asset loading)
and a `const GameData&` reference, read on every `PlayImage()` call to check whether the player has
disabled sound effects in settings (`gameData.getSoundsProperty()`). It owns two collections: a
flat `std::vector<SoundEffect>` of loaded WAV assets indexed directly by channel number, and a
`std::list<Play>` of currently (or very recently) playing instances. `Sound` is explicitly
non-copyable, both because it owns `SoundEffect`/`SoundEffectInstance` objects that are not
cheaply copyable and because a stateful list of active playbacks has no sensible copy semantics.

The constructor does very little: it sets the internal `volume` scalar to `1.0` and, unless
`SOUND_DISABLED` is active, sets the CNA/XAudio2 master volume to `1.0f`:

*From `Sound.cpp:121-131`:*
```cpp
Sound::Sound(IGame1* game1, GameData& gameData) :
    game1(game1),
    gameData(gameData)
{
    // soundEffects = new List<SoundEffect>();
    // plays = new List<Play>();
    volume = 1.0;
#ifndef SOUND_DISABLED
    Microsoft::Xna::Framework::Audio::SoundEffect::setMasterVolumeProperty(1.0f);
#endif
}
```

The commented-out `// soundEffects = new List<SoundEffect>();` lines are a direct trace of the
ILSpy-decompiled C# origin (see [Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
for the decompilation history) — in C#, `List<T>` fields need explicit allocation in the
constructor; in C++, `std::vector` and `std::list` default-construct themselves, so the equivalent
lines are dead but were evidently left in place as a paper trail during the port rather than
deleted.

### The `SOUND_ENABLED` / `SOUND_DISABLED` build switch

Unlike the header, which is silent about it, `Sound.cpp` unconditionally defines the guard that
controls whether the class does anything at all:

*From `Sound.cpp:56-58`:*
```cpp
#ifndef SOUND_ENABLED
#define SOUND_DISABLED
#endif
```

Because nothing in the repository ever defines `SOUND_ENABLED` before this file is compiled, this
resolves to `SOUND_DISABLED` being active in every configuration checked — the file always defines
`SOUND_ENABLED`'s absence, so the disabled branch is always the one taken unless a future build
adds a `-DSOUND_ENABLED` compiler flag. When `SOUND_DISABLED` is active, nearly every public
method in `Sound` short-circuits to a safe stub — `PlayImage` returns `true` without touching
`soundEffects`, `GetVolume`/`GetBalance` return fixed values, `Play`'s constructor returns before
applying any per-channel table lookup — without ever calling into the CNA/SDL3 audio layer at all.
This is explicitly a headless/testing mode ("useful for headless unit-test builds", per the file's
top-of-file comment) rather than a permanently-disabled feature; the intent is clearly that a real
build defines `SOUND_ENABLED` (or removes this guard) so that the full implementation described
below actually plays audio. Every code path described in the rest of this chapter is written to
match the *enabled* behavior, since that is what a real build (and the game's actual runtime
audio character) exercises.

### Loading content: 93 WAV files, zero-padded and sequential

`LoadContent()` is a flat loop that loads exactly 93 assets, named by a zero-padded three-digit
counter, directly into `soundEffects` at the index matching their number:

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

The result is `sounds/sound000.wav` through `sounds/sound092.wav` — matching the 93 `.wav` files
actually present in `Content/sounds/` (per `PLAN.md`'s source inventory). `Def::getHasSoundProperty()`
is a `constexpr` in `Def.hpp` that always returns `true` (`Def.hpp:195-198`); it is a vestige of a
platform capability check from the original game (some Windows Phone devices may not have had
audio hardware, or the flag existed for a build variant) that is not actually platform-gated in
this port. There is no per-file error handling in this loop: if `Load<SoundEffect>` throws or
otherwise fails partway through, the loop does not catch it, and `soundEffects` ends up with fewer
than 93 entries for the rest of the run. This detail matters — [Chapter 40](ch40-audio-issue-analysis.md)
covers a suspected consequence of exactly this gap when combined with `PlayImage`'s bounds check.

Because `soundEffects` is indexed directly by the integer value of `SoundChannel`, "which asset
plays for a given `SoundChannel`" is not a lookup table anywhere in the code — it is *identity*.
`SoundChannel::SoundChannel42` plays `sound042.wav`. This 1:1 index mapping is why `SoundChannel.hpp`
warns "do not renumber these values" (`SoundChannel.hpp:8, 22`): renumbering a channel would silently
swap which WAV file it plays.

### `Play`: an RAII wrapper around one playing instance

`Sound::Play` is a private nested class — one object per currently (or recently) playing sound.
Its constructor is where per-channel volume and pitch modulation is actually applied, and where
playback is kicked off, all in one step:

*From `Sound.cpp:90-111`:*
```cpp
Sound::Play::Play(Microsoft::Xna::Framework::Audio::SoundEffect& se, SoundChannel channel, double volume, double balance,
                  double pitch, bool isLooped) :
    channel(channel),
    sei(se.CreateInstance())
{
#ifdef SOUND_DISABLED
    int b;
    return;
#endif
    int tableVolumePitchLengthIndex = ToRaw(channel) * 2;
    if (tableVolumePitchLengthIndex >= 0 && tableVolumePitchLengthIndex < tableVolumePitchLength)
    {
        volume *= tableVolumePitch[tableVolumePitchLengthIndex];
        pitch = tableVolumePitch[tableVolumePitchLengthIndex + 1];
    }

    sei.setVolumeProperty((float)volume);
    sei.setPanProperty((float)balance);
    sei.setPitchProperty((float)(pitch < 0.0 ? 0.0 : pitch));
    sei.setIsLoopedProperty(isLooped);
    sei.Play();
}
```

Notice the caller-supplied `pitch` argument is *always* passed as `0.0` from every call site in
`Sound::PlayImage` (see below) — the real pitch always comes from `tableVolumePitch`, and the
parameter exists mainly so the constructor's general shape matches the field's role. The
`int b;` inside the `SOUND_DISABLED` branch is dead code with no effect (an uninitialized local
that is immediately discarded on return) — almost certainly a leftover from debugging or from a
mechanical decompilation pass rather than intentional logic; harmless, but worth flagging so a
reader doesn't waste time hunting for what `b` is for.

`getIsFreeProperty()` reports whether the instance has finished playing, by asking the underlying
`SoundEffectInstance` for its `SoundState`:

*From `Sound.cpp:64-70`:*
```cpp
bool Sound::Play::getIsFreeProperty() const
{
#ifdef SOUND_DISABLED
    return false;
#endif
    return sei.getStateProperty() == Microsoft::Xna::Framework::Audio::SoundState::Stopped;
}
```

A looped sound is never reported free until something explicitly calls `Stop()` on it — which
matters for the play-list pruning logic below, since a stuck or forgotten loop can occupy a slot
indefinitely.

### The active-play list and its 10-entry cap

`Sound` tracks all currently active instances in `std::list<Play> plays`. Two policies govern this
list, both implemented inline in `PlayImage`:

*From `Sound.cpp:220-263`:*
```cpp
bool Sound::PlayImage(SoundChannel channel, TinyPoint pos, int rank, bool bLoop)
{
#ifdef SOUND_DISABLED
    return true;
#endif
    if (!gameData.getSoundsProperty())
    {
        return true;
    }
    const intcs rawChannel = ToRaw(channel);
    if (rawChannel >= 0 && rawChannel < soundEffects.size())
    {
        if (channel != SoundChannel::SoundChannel10 && std::any_of(plays.begin(), plays.end(),
                                         [channel](const Play& p)
                                         {
                                             return p.getChannelProperty() == channel && !p.getIsFreeProperty();
                                         }))
        {
            return true;
        }

        if (plays.size() >= 10)
        {
            for (auto it = plays.begin(); it != plays.end();)
            {
                if (it->getIsFreeProperty())
                {
                    it = plays.erase(it);
                }
                else
                {
                    it++;
                }

                if (plays.size() < 10) break;
            }
        }


        plays.emplace_back(soundEffects[ToRaw(channel)], channel, (float)GetVolume(pos), (float)GetBalance(pos), 0.0,
                           bLoop);
    }
    return true;
}
```

1. **Channel-conflict policy.** If the requested channel is anything other than
   `SoundChannel10`, and a *non-free* (still-playing) `Play` already exists for that same channel,
   the new request is silently dropped — the method still returns `true`. This prevents, for
   example, a footstep sound retriggering every single frame while Blupi is walking from spamming
   dozens of overlapping copies of the same sample; only one instance of a given channel can be
   audible at a time. `SoundChannel10` is explicitly exempted and may stack freely — see
   [Chapter 39](ch39-soundchannel-and-mixing.md) for what that channel is used for and why
   stacking makes sense there.
2. **List-size cap.** If the list has reached 10 entries, the code walks the list evicting any
   *free* (finished) entries until the count drops back under 10, then always appends the new
   `Play` regardless of whether the eviction succeeded. Note this means the cap is soft in one
   direction: if all 10 existing entries are still actively playing (none are free), the loop
   evicts nothing, and the new sound is still appended anyway — `plays.size()` can therefore
   exceed 10 in that case. The comment in the class-level Doxygen ("if none are stopped, the new
   sound is silently dropped") describes an intended policy that the code as written does not
   actually enforce; the real behavior lets the list grow past 10 rather than drop the new sound.
3. Every successful `PlayImage()` call constructs a `Play` in-place with `emplace_back`, passing
   the source `SoundEffect` by reference, the channel (for the table lookup), volume and balance
   computed from `pos`, a hardcoded `pitch` of `0.0` (immediately overridden inside `Play`'s
   constructor by the table), and the loop flag.

`PlayImage()` always returns `true`, even when the sound was silently dropped for any of the
reasons above — callers (chiefly `Decor::PlaySound`, described below) cannot distinguish "played"
from "dropped" from the return value alone.

### `StopAll`, `Stop`, and `PosImage`

`StopAll()` iterates every active `Play`, calls `Stop()` on each (which calls `sei.Stop()`), and
clears the list:

*From `Sound.cpp:208-218`:*
```cpp
void Sound::StopAll()
{
#ifdef SOUND_DISABLED
    return;
#endif
    for (auto& play : plays)
    {
        play.Stop();
    }
    plays.clear();
}
```

`Stop(SoundChannel channel)` walks the list and removes every `Play` matching the given channel
(there can in principle be more than one, though the channel-conflict policy above normally
prevents that for anything but `SoundChannel10`):

*From `Sound.cpp:270-292`:*
```cpp
bool Sound::Stop(SoundChannel channel)
{
#ifdef SOUND_DISABLED
    return true;
#endif
    size_t num = 0;

    auto it = plays.begin();
    while (it != plays.end())
    {
        if (it->getChannelProperty() == channel)
        {
            it->Stop();
            it = plays.erase(it); // erase() returns the next valid iterator
        }
        else
        {
            ++it;
        }
    }

    return true;
}
```

(The local `num` is declared but never used — another small trace of a more elaborate original
implementation, or dead code left over from refactoring; it has no effect on behavior.)

`PosImage()`, by contrast, is a pure stub in this backend — it always returns `true` and does
nothing else:

*From `Sound.cpp:265-268`:*
```cpp
bool Sound::PosImage(SoundChannel channel, TinyPoint pos)
{
    return true;
}
```

The `ISound` interface promises that `PosImage` "recomputes volume and stereo balance from `pos`
without restarting playback" for a looping sound whose source is moving (the header names the
vehicle-engine use case explicitly), but the `Sound` implementation never does that — an active
loop's volume/pan is fixed at the moment its `Play` was constructed and never updated again. This
means `Decor::PosSound()` (covered below), which calls `PosImage` every frame while a vehicle motor
loop is active, is currently calling into a no-op. The panning of a moving vehicle's engine sound
does not actually track its on-screen position at runtime, despite `Decor`'s own code being
written as though it does.

### `GetVolume` and `GetBalance`: mapping HUD position to XAudio2-style scalars

Both attenuation functions treat the logical `640×480` play area as the "fully audible" zone and
fade sounds linearly toward silence outside it, on two independent axes, taking the minimum of the
two axis results as the final scalar:

*From `Sound.cpp:294-324`:*
```cpp
double Sound::GetVolume(TinyPoint pos)
{
#ifdef SOUND_DISABLED
    return 1.0;
#endif
    double val = 1.0;
    if (pos.X < 0)
    {
        val = 1.0 + (double)(pos.X / 640) * 2.0;
    }
    if (pos.X > 640)
    {
        pos.X -= 640;
        val = 1.0 - (double)(pos.X / 640) * 2.0;
    }
    val = std::max(val, 0.0);
    val = std::min(val, 1.0);
    double val2 = 1.0;
    if (pos.Y < 0)
    {
        val2 = 1.0 + (double)(pos.Y / 480) * 3.0;
    }
    if (pos.Y > 480)
    {
        pos.Y -= 480;
        val2 = 1.0 - (double)(pos.Y / 480) * 3.0;
    }
    val2 = std::max(val2, 0.0);
    val2 = std::min(val2, 1.0);
    return std::min(val, val2) * volume;
}
```

The horizontal falloff factor is `2.0` and the vertical falloff factor is `3.0` — a sound centered
280 px above the visible area (`pos.Y == -280`, i.e. `280/480 * 3 ≈ 1.75` beyond full attenuation)
fades out faster than a sound the same *proportional* distance to the side, because the play area
is narrower vertically (480 px) than horizontally (640 px) and the header comment for this method
states this steeper vertical falloff intentionally "matches the original Windows Phone game's
audio feel" (`Sound.cpp:34-36`). The final scalar is also multiplied by the global `volume` field
set via `SetAudioVolume()`, so a fully on-screen sound at max settings-volume gets `1.0`, and
anything off to the side or above/below the visible viewport fades proportionally.

`GetBalance` is a simple linear pan map across the 640-px logical width:

*From `Sound.cpp:326-334`:*
```cpp
double Sound::GetBalance(TinyPoint pos)
{
#ifdef SOUND_DISABLED
    return 1.0;
#endif
    double val = (double)pos.X * 2.0 / 640.0 - 1.0;
    val = std::max(val, -1.0);
    return std::min(val, 1.0);
}
```

`X = 0` maps to `-1.0` (full left), `X = 320` (screen center) maps to `0.0`, and `X = 640` maps to
`+1.0` (full right); values outside `[0, 640]` clamp rather than continuing to pan further.

### Volume settings: `SetAudioVolume` / `GetAudioVolume`

`Sound::MAXVOLUME` is `20`. The settings UI presumably works in integer steps of this scale;
`Sound` stores the value internally as a `double` in `[0.0, 1.0]`:

*From `Sound.cpp:183-197`:*
```cpp
void Sound::SetAudioVolume(int volume)
{
#ifdef SOUND_DISABLED
    return;
#endif
    this->volume = (double)volume / (double)MAXVOLUME;
}

int Sound::GetAudioVolume()
{
#ifdef SOUND_DISABLED
    return 1;
#endif
    return (int)(volume * (double)MAXVOLUME);
}
```

Setting the volume only affects the scalar consulted by `GetVolume()` for *future* `PlayImage`
calls — it does not retroactively touch any `Play` object already constructed and playing, since
each `Play`'s volume is fixed into the underlying `SoundEffectInstance` at construction time.

### Stub methods: `SetState`, `SetCDAudio`, `GetEnable`, MIDI volume

`SetState`, `SetCDAudio`, `SetMidiVolume` are empty bodies; `GetEnable()` always returns `true`;
`GetMidiVolume()` always returns `0`; `Create()` always returns `true` and does no actual device
initialization. These are `ISound` interface members inherited from the original Windows Phone
API surface (audio-focus enable/disable for phone-call interruption, and a MIDI/CD-audio music
layer) that this port neither needs nor implements — see `Sound.hpp:272-324`'s Doxygen, which is
explicit that each of these exists "for `ISound` interface compatibility" only.

## How `Decor` drives `Sound`: the gameplay-facing layer

`Decor` never calls `ISound::PlayImage` directly from most of its ~150 sound-triggering call
sites. Instead it wraps `m_sound` (its own `ISound*` member) behind a small set of private helper
methods — `PlaySound`, `StopSound` (two overloads), `StartSound`, `SoundEnviron`, and
`AdaptMotorVehicleSound`/`PosSound` — declared at `Decor.hpp:831-897` and implemented together at
`Decor.cpp:1434-1649`. This is the layer where gameplay concerns (surface-dependent footstep
sounds, the Hide secret power muting Blupi's own noise, vehicle engine loop management) are
translated into plain `ISound` calls.

### `PlaySound`: the common entry point, and the Hide power's audio suppression

`Decor::PlaySound(SoundChannel sound, TinyPoint pos)` is the single choke point almost every
gameplay sound effect passes through:

*From `Decor.cpp:1518-1572`:*
```cpp
void Decor::PlaySound(SoundChannel sound, TinyPoint pos)
{
    int ranSound = ToRaw(sound);
    if (!m_blupiHide || (
        ranSound != 1 &&
         ranSound != 2 &&
         ranSound != 3 &&
         ranSound != 4 &&
         ranSound != 5 &&
         ranSound != 6 &&
         ranSound != 7 &&
         ranSound != 20 &&
         /* ...continues through 21-25, 27, 32, 34-40, 46-49, 64-65, 78-91... */
         ranSound != 91)
        )
    {
        pos.X -= m_posDecor.X;
        pos.Y -= m_posDecor.Y;
        m_sound->PlayImage(sound, pos);
    }
}
```

The condition is a large disjunction that, together with `!m_blupiHide` at the front, means: *play
the sound unless Blupi's Hide secret power is currently active AND this particular channel is one
of Blupi's own action/footstep/effect sounds.* The channel list enumerated (1-7, 20-25, 27, 32,
34-40, 46-49, 64-65, and the whole 78-91 footstep-surface-variant block from `SoundEnviron`, see
below) is every sound that would otherwise announce Blupi's presence or actions while he is
supposed to be hidden — footsteps, jumps, splashes, and the like — while purely ambient/environment
sounds (a distant machine, a background effect) are allowed to keep playing because they are not
tied to Blupi's own movement and would look like a bug (silence breaking immersion) if suppressed.
Before forwarding to `ISound`, `PlaySound` subtracts the current scroll origin (`m_posDecor`) from
the absolute game-space position, converting it into a screen-relative HUD coordinate — this is
the point at which the 640×480 logical space described in `ISound.hpp` actually gets populated
from a level's much larger absolute coordinate space (a level can be up to `100×100` tiles of 64 px
each, per `Def::MAXCELX`/`MAXCELY`/`DIMOBJX`/`DIMOBJY` in `Def.hpp:149-152`, far larger than one
screen).

### `SoundEnviron`: surface-dependent footstep sounds

Two generic channels — `SoundChannel3` and `SoundChannel4` — are placeholders for "footstep on
whatever surface Blupi happens to be standing on." `SoundEnviron` classifies the tile icon Blupi
is standing on into one of several material ranges and substitutes a dedicated pair of
surface-specific channels:

*From `Decor.cpp:1434-1509`:*
```cpp
SoundChannel Decor::SoundEnviron(SoundChannel sound, int obstacle)
{
    if ((obstacle >= 32 && obstacle <= 34) || (obstacle >= 41 && obstacle <= 47) || (obstacle >= 139 && obstacle <=
        143))
    {
        switch (sound)
        {
        case SoundChannel::SoundChannel4:
            return SoundChannel::SoundChannel79;
        case SoundChannel::SoundChannel3:
            return SoundChannel::SoundChannel78;
        }
    }
    if ((obstacle >= 1 && obstacle <= 28) || (obstacle >= 78 && obstacle <= 90) || (obstacle >= 250 && obstacle <=
        260) || (obstacle >= 311 && obstacle <= 316) || (obstacle >= 324 && obstacle <= 329))
    {
        switch (sound)
        {
        case SoundChannel::SoundChannel4:
            return SoundChannel::SoundChannel81;
        case SoundChannel::SoundChannel3:
            return SoundChannel::SoundChannel80;
        }
    }
    // ... five further material ranges (285-303/338, 341-363, 215-234, 246-249, 107-109),
    //     each mapping SoundChannel3/4 to its own dedicated (odd, even) channel pair
    //     in the 78-91 range.
    return sound;
}
```

Seven distinct surface-material ranges are recognized in total (the excerpt above shows the first
two; the remaining five follow the identical pattern up to `SoundChannel90`/`91`), each mapping the
two generic footstep channels to its own dedicated pair in the `78`-`91` range. Any tile icon
falling outside every listed range, or any input channel other than `SoundChannel3`/`4`, passes
through unchanged. The obstacle-icon ranges here are exactly the kind of "magic number" tile
classification covered in depth in [Chapter 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md);
this method is one more consumer of that same raw-icon classification scheme, this time for audio
rather than collision.

### `StopSound`, `StartSound`, and pause/resume

Two public overloads exist on `Decor`. The no-argument `StopSound()` silences everything and
resets the tracked motor-loop state:

*From `Decor.cpp:1574-1588`:*
```cpp
void Decor::StopSound()
{
    m_blupiMotorSound = SoundChannel::SoundChannel0;
    m_sound->StopAll();
}

void Decor::StartSound()
{
    AdaptMotorVehicleSound();
}

void Decor::StopSound(SoundChannel sound)
{
    m_sound->Stop(sound);
}
```

`StopSound()` is the pause-menu hook: all sound effects, one-shot or looping, are killed
immediately, and `m_blupiMotorSound` is reset to `SoundChannel0` so `AdaptMotorVehicleSound`
treats the next frame as "coming from silence." `StartSound()` does not resume any specific
sounds — it simply re-invokes `AdaptMotorVehicleSound()`, which will restart a vehicle-engine loop
if Blupi is currently in a vehicle, since that is the only *looping* gameplay sound this game has.
One-shot sound effects that were interrupted mid-pause are not resumed; the game does not track
which ones were playing.

### `AdaptMotorVehicleSound`: the only looping sound in the game

Every looping sound in mobile-eggbert is a vehicle engine, and this single method owns all of the
logic for starting, stopping, and cross-fading between the two vehicle-loop families
(helicopter, and jeep/tank/overcraft, which share one loop):

*From `Decor.cpp:1599-1639`:*
```cpp
void Decor::AdaptMotorVehicleSound()
{
    SoundChannel num = SoundChannel::SoundChannel0;
    SoundChannel channel = SoundChannel::SoundChannel0;
    SoundChannel channel2 = SoundChannel::SoundChannel0;
    if (m_blupiHelico)
    {
        num = (m_blupiMotorHigh ? SoundChannel::SoundChannel16 : SoundChannel::SoundChannel18);
        channel = SoundChannel::SoundChannel15;
        channel2 = SoundChannel::SoundChannel17;
    }
    else if (m_blupiJeep || m_blupiOver || m_blupiTank)
    {
        num = (m_blupiMotorHigh ? SoundChannel::SoundChannel29 : SoundChannel::SoundChannel31);
        channel = SoundChannel::SoundChannel28;
        channel2 = SoundChannel::SoundChannel30;
    }
    if (m_blupiMotorSound != num)
    {
        TinyPoint blupiPos = m_blupiPos;
        blupiPos.X -= m_posDecor.X;
        blupiPos.Y -= m_posDecor.Y;
        if (m_blupiMotorSound == SoundChannel::SoundChannel0 && num != SoundChannel::SoundChannel0)
        {
            m_sound->PlayImage(channel, blupiPos);
        }
        if (m_blupiMotorSound != SoundChannel::SoundChannel0 && num == SoundChannel::SoundChannel0)
        {
            m_sound->PlayImage(channel2, blupiPos);
        }
        if (m_blupiMotorSound != SoundChannel::SoundChannel0)
        {
            m_sound->Stop(m_blupiMotorSound);
        }
        m_blupiMotorSound = num;
        if (m_blupiMotorSound != SoundChannel::SoundChannel0)
        {
            m_sound->PlayImage(m_blupiMotorSound, blupiPos, -1, true);
        }
    }
}
```

The logic selects one of two desired looping channels (`SoundChannel16`/`18` for the helicopter's
high/low-throttle variants, `SoundChannel29`/`31` for the jeep/tank/overcraft equivalents) based on
`m_blupiHelico` and the `m_blupiJeep || m_blupiOver || m_blupiTank` group, and a `m_blupiMotorHigh`
flag that is set elsewhere in `Decor.cpp` (at the points where the player's action/speed state
transitions — e.g. `Decor.cpp:4184`, `m_blupiMotorHigh = m_blupiAction != BlupiAction::Stop`)
rather than inside this method itself, despite the header's Doxygen describing this method as the
place that "switches between low and high motor sound variants" (`Decor.hpp:884-889`) — the switch
actually happens by the time this method reads the flag; `AdaptMotorVehicleSound` only reacts to
it. If the desired loop (`num`) differs from the one already playing (`m_blupiMotorSound`), the
method does a small crossfade dance: a one-shot "engine start" sound (`channel`) plays when going
from silence to a motor, a one-shot "engine stop" sound (`channel2`) plays when going the other
way, the old loop is stopped via `Stop()`, and the new loop is started with the looping flag set
(`PlayImage(..., -1, true)`). If the desired loop already matches the active one, the whole block
is skipped — no redundant restarts on every frame despite `AdaptMotorVehicleSound` being called
every single frame from `MoveStep()` (`Decor.cpp:515`).

### `PosSound`: intended per-frame panning update (currently a no-op downstream)

*From `Decor.cpp:1641-1649`:*
```cpp
void Decor::PosSound(TinyPoint pos)
{
    if (m_blupiMotorSound != SoundChannel::SoundChannel0)
    {
        pos.X -= m_posDecor.X;
        pos.Y -= m_posDecor.Y;
        m_sound->PosImage(m_blupiMotorSound, pos);
    }
}
```

`PosSound` is called from `Decor::VoyageStep()` (`Decor.cpp:6530`) with Blupi's current position
every frame a vehicle is active, and is clearly intended to keep the engine loop's stereo panning
following Blupi as he moves across the screen. As shown above under `PosImage`, however, `Sound`'s
concrete implementation of `PosImage` is a no-op that ignores both arguments — so in the current
codebase this call has no audible effect; the engine loop's pan is fixed at whatever it was when
`AdaptMotorVehicleSound` first started the loop, until the loop is stopped and restarted.

## What `Sound.hpp`'s own documentation gets right — and one place it overstates

`Sound.hpp`'s class-level Doxygen comment is unusually thorough and, on the whole, an accurate
description of the implementation — but reading it against the actual code in `Sound.cpp` (as this
chapter has done section-by-section) surfaces two small mismatches worth flagging explicitly for a
reader who trusts the header comments at face value: the play-list-cap description implies sounds
can be "silently dropped" when the list is full and nothing is free to evict, but the code as
written appends anyway and lets the list exceed 10; and `AdaptMotorVehicleSound`'s doc describes it
as the place that switches motor pitch based on speed, when the actual speed-to-`m_blupiMotorHigh`
decision lives elsewhere in `Decor.cpp` and this method only consumes the already-set flag. Neither
is a functional bug worth "fixing" without further investigation — they are documentation/implementation
drift of the ordinary kind that accumulates in any long-lived codebase — but they are the kind of
detail a source-grounded book should surface rather than repeat uncritically.

## See also

- [Chapter 39: SoundChannel and Mixing](ch39-soundchannel-and-mixing.md) — the `SoundChannel` enum
  in full and the `tableVolumePitch` per-channel tuning table referenced throughout this chapter.
- [Chapter 40: Audio Issue Analysis](ch40-audio-issue-analysis.md) — a deeper look at two audio bug
  reports and how they trace back to `Sound::PlayImage`'s bounds check and the content-loading path.
- [Chapter 15: Decor Overview](../part04-decor-simulation/ch15-decor-overview.md) and
  [Chapter 26: Tile and Icon Catalog](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) —
  the tile-icon classification scheme that `SoundEnviron` reuses for surface-dependent footsteps.
- [Chapter 41: InputPad](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) — the other
  consumer of `ISound`, which plays a UI click sound (`SoundChannel0`) on button presses.
