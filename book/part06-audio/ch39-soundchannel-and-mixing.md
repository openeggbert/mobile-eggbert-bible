# Chapter 39: SoundChannel and Mixing

[Chapter 38](ch38-sound-isound-architecture.md) covered the `ISound`/`Sound` architecture and how
`Decor` drives it. This chapter looks at the two pieces of static data that give that architecture
its actual audio character: the `SoundChannel` enumeration that names every one of the game's 93
sound assets, and the `tableVolumePitch` lookup table that quietly reshapes a handful of them away
from "play at full volume, no pitch shift."

## `SoundChannel`: 93 flat, unstructured slots

`SoundChannel.hpp` (177 lines) declares a single `enum class SoundChannel : SoundChannelUnderlying`
(an unsigned byte, `SharpRuntime::ubytecs`) with 93 enumerators, `SoundChannel0` through
`SoundChannel92`, each simply equal to its own index:

*From `SoundChannel.hpp:35-130` (excerpted):*
```cpp
enum class SoundChannel : SoundChannelUnderlying
{
    SoundChannel0  = 0,  ///< @brief Reserved channel (index 0, not used for playback).
    SoundChannel1  = 1,  ///< @brief Sound effect slot 1.
    SoundChannel2  = 2,
    SoundChannel3  = 3,
    ...
    SoundChannel91 = 91,
    SoundChannel92 = 92
};
```

Unlike `PixmapChannel` (the rendering-side enum covered in
[Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md)), which groups
sprite sheets by *kind* (Blupi, Object, Element, Explosion, …), `SoundChannel` has no internal
grouping at all — it is a flat, arbitrary numbering with no semantic clusters visible from the
enum declaration itself. The header's own comment is explicit that this is deliberate and
load-bearing: "do not renumber these values as they must match the original game's sound table
indices" (`SoundChannel.hpp:7-8`, repeated at `SoundChannel.hpp:22`). As established in
[Chapter 38](ch38-sound-isound-architecture.md), the numeric value of a `SoundChannel` is used
directly as an index into both `Sound::soundEffects` (which asset plays) and
`Sound::tableVolumePitch` (how it's tuned) — renumbering would silently swap which WAV file a
gameplay event triggers and which volume/pitch modifier it receives.

The header also documents channel `0` as "reserved... not used for playback" in its top comment
(`SoundChannel.hpp:7`), yet `SoundChannel0` is in fact used — `InputPad::Update()` plays it
explicitly as the UI button-click sound:

*From `InputPad.cpp:1012-1014`:*
```cpp
TinyPoint pos(320, 240);
sound->PlayImage(SoundChannel::SoundChannel0, pos);
```

So "reserved" here means "not part of the gameplay sound vocabulary that `Decor` triggers by name
for footsteps, jumps, and effects" rather than genuinely silent or unloaded — `sound000.wav` is
loaded like any other asset and does get played, just from `InputPad` rather than from `Decor`.

### `ToRaw` / `ToSoundChannel`: the only two free functions

The file supplies the same small pair of conversion helpers used by every enum in this codebase
(compare `KeyPressFlags`'s `ToRaw`/`ToKeyPressFlags`, covered in
[Chapter 42](../part07-input/ch42-keypressflags-and-mapping.md)):

*From `SoundChannel.hpp:137-156`:*
```cpp
static constexpr auto ToRaw(SoundChannel type) -> SoundChannelUnderlying
{
    return static_cast<SoundChannelUnderlying>(type);
}

static constexpr auto ToSoundChannel(const int value) -> SoundChannel
{
    return static_cast<SoundChannel>(
        static_cast<SoundChannelUnderlying>(value)
    );
}
```

`ToRaw` is used pervasively — every `Decor::PlaySound` call site that needs to compare a channel
against a numeric range (as `SoundEnviron` and the Hide-power suppression list in
`Decor::PlaySound` both do) goes through it. `ToSoundChannel` is the reverse direction, used
whenever a gameplay table stores a raw integer sound index that needs to become a `SoundChannel`
for a `PlayImage`/`Stop` call — the comment notes the caller is responsible for keeping the value
in `[0, 92]`, since neither function performs any bounds validation itself (that check happens
downstream, in `Sound::PlayImage`'s `rawChannel < soundEffects.size()` guard, per
[Chapter 38](ch38-sound-isound-architecture.md)).

A short block of commented-out comparison operators (`operator<`, `operator>`, `operator<=`,
`operator>=`) sits at the bottom of the file (`SoundChannel.hpp:157-176`), mirroring an identical
commented-out block that likely exists for `PixmapChannel` — ordering these channel enums was
apparently considered and then not implemented, probably because nothing in the codebase actually
needs to compare two `SoundChannel` values for ordering (only for equality, which the
default-generated `==` on a scoped enum already provides).

## `tableVolumePitch`: the 100-entry tuning table

`Sound` privately declares a `static constexpr double tableVolumePitch[200]` — 100 `(volume,
pitch)` pairs, one per possible channel index `0`-`99` (channels `93`-`99` are unused padding,
since only 93 sound assets exist), even though `SoundChannel` itself only defines up to
`SoundChannel92`:

*From `Sound.hpp:158-212`:*
```cpp
static constexpr short tableVolumePitchLength = 200;

static constexpr double tableVolumePitch[tableVolumePitchLength] =
{
    1.0, 0.0, 0.5, 1.0, 0.5, 1.0, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.1, 1.0, 0.3, 1.0, 0.2, 1.0, 0.3, 1.0, 0.5,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.1, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 0.7, 0.2, 1.0, 0.1, 1.0, 0.1,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.4, 1.0, 0.0, 1.0, 0.0,
    1.0, 0.0, 1.0, 0.0, 1.0, 0.2, 1.0, 0.2, 0.7, 0.4,
    1.0, 0.2, 1.0, 0.4, 1.0, 0.2, 0.5, 1.0, 0.5, 1.0,
    1.0, 0.4, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 0.6, 0.4, 0.8, 0.1,
    0.6, 0.5, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.0,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.0,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.0, 1.0, 0.0, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 0.6, 0.4,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2,
    1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2
};
```

The indexing convention, stated in both the header and the class doc comment, is:

```
volume[ch] = tableVolumePitch[ch * 2]
pitch[ch]  = tableVolumePitch[ch * 2 + 1]
```

The **volume multiplier** is applied to whatever volume `Sound::Play`'s constructor was given
(itself derived from `Sound::GetVolume(pos)`, the positional-attenuation scalar from
[Chapter 38](ch38-sound-isound-architecture.md)) — a value below `1.0` permanently caps how loud
that channel can ever get, regardless of how close to the viewport center the sound's source
position is. The **pitch shift** is not a multiplier on top of a caller-supplied value; per
`Sound::Play`'s constructor (`Sound.cpp:99-104`), the table value *replaces* the pitch argument
outright whenever the channel index is in bounds — every `PlaySound`/`PlayImage` call site in the
entire codebase passes a hardcoded `0.0` pitch, so in practice the table is the *only* source of
pitch for every channel, always.

### Reading the table by channel: the two categories of departure from default

The overwhelming majority of the 93 real channels use `volume = 1.0, pitch = 0.2` — full volume,
a small fixed upward pitch shift applied uniformly (a stylistic choice made once for the whole
game, not something varying per effect). Scanning all 93 entries for anything that departs from
that baseline surfaces two distinct, small groups:

**Group 1 — the "octave up, half volume" channels: `SoundChannel1`, `2`, `38`, `39`.**

| Channel | Volume | Pitch | Used for (from `Decor.cpp`) |
|---|---|---|---|
| `SoundChannel1` | 0.5 | 1.0 | Jump take-off sound (`Decor.cpp:2928, 2933` — both the skate-jump and normal-jump branches of `BlupiStep`) |
| `SoundChannel2` | 0.5 | 1.0 | **Not called anywhere** in the current `src/` tree — see below |
| `SoundChannel38` | 0.5 | 1.0 | Crate-push contact sound (`Decor.cpp:6138, 6147`, when Blupi first touches a pushable crate) |
| `SoundChannel39` | 0.5 | 1.0 | Crate pop/stop sound (`Decor.cpp:3298, 3306, 3315, 3323`, when Blupi is stopped by or pops over a crate) |

A `pitch` of `1.0` is, per the XAudio2-style convention documented in `Sound.hpp:177-180` ("0.0 =
no shift, 1.0 = one octave up"), a full octave above the sample's recorded pitch — combined with
half volume, these four channels play noticeably higher and quieter than everything else in the
game. `AUDIO_ANALYSIS.md` (the game's own prior investigation, covered in full in
[Chapter 40](ch40-audio-issue-analysis.md)) specifically flagged this pattern and concluded it is
original, intentional game design rather than a porting defect: "the per-channel volume/pitch
lookup table... was compared byte-for-byte against the original decompiled C# source
(`mobile-eggbert-legacy/mobile-eggbert-core/Sound.cs:58`) and is identical. A handful of channels
do have `pitch = 1.0` (one octave up) with `volume = 0.5`, but that is original game design
(verbatim from the Windows Phone XNA release), not a porting bug" (`AUDIO_ANALYSIS.md:36-40`). This
chapter's own reading of `Sound.hpp:190-212` confirms the count and identity of that "handful":
exactly four channels (1, 2, 38, 39), all sharing the identical `(0.5, 1.0)` pair. Given what
`SoundChannel1`, `38`, and `39` are actually used for — a jump take-off "boing" and two crate-push
contact sounds — a quieter, higher-pitched variant reads as a deliberate cartoonish sound-design
choice (a small comedic "squeak" on physical contact) consistent with the game's overall visual
style, rather than an error anyone would want to "fix."

`SoundChannel2` is the interesting exception within this group: this chapter's own search of the
entire `mobile-eggbert` source tree (both `include/` and `src/`) found no call site anywhere that
passes `SoundChannel::SoundChannel2` to `PlaySound`, `PlayImage`, or `Stop` — the only place the
literal value `2` for this purpose appears is inside `Decor::PlaySound`'s Hide-power exclusion
list (`ranSound != 2`, `Decor.cpp:1523`), which defensively excludes it from suppression without
anything ever actually triggering it. `sound002.wav` is still loaded by `Sound::LoadContent()`
(since loading is a flat loop over all 93 indices, not driven by which channels are referenced
elsewhere) and the tuning table still carries a real entry for it, so this is not a loading gap —
it is simply an orphaned channel: a sound effect that exists, is tuned, and is defended by
gameplay logic that was clearly written with it in mind, but that no current code path plays. This
matches the general shape of a game where one code path (a cut mechanic, an alternate crate/jump
variant that didn't ship, or a debug trigger removed from the original C#) stopped calling a sound
some time before or during the port, without the corresponding table entry or exclusion-list guard
being cleaned up.

**Group 2 — the reduced-volume-only channels: `SoundChannel22`, `34`, `48`, `49`, `50`, `84`.**

| Channel | Volume | Pitch | Used for |
|---|---|---|---|
| `SoundChannel22` | 0.7 | 0.2 | Emerging from water / swim-to-air transition (`Decor.cpp:5356, 5378, 5392, 5405`) |
| `SoundChannel34` | 0.7 | 0.4 | (played via `Decor.cpp:5452`, in the ghost/void-fall handling branch) |
| `SoundChannel48` | 0.6 | 0.4 | Idle "Ouf3" mannerism sound, triggered after a long idle timeout (`Decor.cpp:6292`) |
| `SoundChannel49` | 0.8 | 0.1 | Idle "Ouf4" mannerism sound, a shorter-timeout variant of the same idle-fidget system (`Decor.cpp:6302`) |
| `SoundChannel50` | 0.6 | 0.5 | Played at `Decor.cpp:1956` and `6038` (`SoundChannel50`, `end`/`m_blupiPos`) |
| `SoundChannel84` | 0.6 | 0.4 | A `SoundEnviron`-generated footstep variant for tile-icon range `341`-`363` (`Decor.cpp:1468-1477`) |

These six channels keep the default `0.1`-`0.5` pitch range (no octave shift) but lower the
volume multiplier to `0.6`-`0.8`. Reading what each is used for, a pattern emerges: several are
idle "personality" sounds — the `Ouf3`/`Ouf4` mannerism sounds Blupi plays when left standing still
for a while (`m_blupiTimeOuf` timeout logic around `Decor.cpp:6286-6304`) — and one
(`SoundChannel84`) is a footstep variant for a specific surface material. Quieter idle-fidget
sounds and a quieter footstep-on-one-particular-surface both make sense as deliberate mixing
choices: idle sounds play far more often, relative to their gameplay importance, than an action
sound like a jump, and would become annoying at full volume; a specific surface footstep being
quieter than others is consistent with a level designer's ear for one texture reading as
"softer"/more muffled than the rest (sand or grass, for instance, compared to stone or metal). None
of the six channels in this second group appear in `Decor::PlaySound`'s Hide-power exclusion list
except `34`, `46`-`49` (`Decor.cpp:1544-1546`) — consistent with treating idle personality sounds
as "Blupi's own" noise that Hide should suppress, the same category as footsteps and jumps.

### Channels with `pitch = 0.0` (no shift at all)

A smaller set of channels keep full `1.0` volume but drop the pitch entry to `0.0` — no shift in
either direction, distinct from the game's otherwise-universal `0.2` baseline. These are
`SoundChannel0` (the UI click, `Sound.hpp:192`), `15`-`18` and `28`-`31` (`Sound.hpp:195,197-198`
— exactly the four looping vehicle-motor channels used by `Decor::AdaptMotorVehicleSound`, covered
in [Chapter 38](ch38-sound-isound-architecture.md): the helicopter's high/low throttle pair
(`16`/`18`) and start/stop one-shots (`15`/`17`), and the jeep/tank/overcraft equivalents
(`29`/`31` and `28`/`30`)), and a handful of others (`64`, `69`, `72`, `73`). Leaving looping
engine-sound channels at an unshifted pitch is the sensible choice — the `0.2` baseline shift
applied to most one-shot effects is a stylistic flourish that would sound wrong sustained
indefinitely on a continuous engine drone, and a UI click benefiting from staying at the
unmodified recorded pitch is likewise unsurprising.

### Bounds safety

`Sound::Play`'s constructor guards every table access:

*From `Sound.cpp:99-104`:*
```cpp
int tableVolumePitchLengthIndex = ToRaw(channel) * 2;
if (tableVolumePitchLengthIndex >= 0 && tableVolumePitchLengthIndex < tableVolumePitchLength)
{
    volume *= tableVolumePitch[tableVolumePitchLengthIndex];
    pitch = tableVolumePitch[tableVolumePitchLengthIndex + 1];
}
```

Since `ToRaw(channel)` returns an unsigned byte, the `>= 0` half of this check can never be false
by construction; the only way this branch is skipped is if `ToRaw(channel) * 2 >= 200`, i.e. a
channel value `>= 100` — impossible given `SoundChannel`'s own declared range of `0`-`92`. In
practice, every valid `SoundChannel` value always finds a table entry; the guard exists purely as
defensive programming rather than because any real call site can trigger the fallback path (in
which the caller-supplied, always-`0.0`, volume and pitch would be used unmodified).

## Why this table exists at all: mixing as static data, not per-call tuning

Structurally, `tableVolumePitch` is a compact way of saying "sound-channel N always sounds like
this" without threading a volume/pitch argument through every one of the roughly 150 `PlaySound`
call sites scattered across `Decor.cpp`. Every caller only ever supplies a base volume (itself
computed from position, never hand-tuned per call) and a placeholder pitch of `0.0`; all the
actual character of an individual sound effect — how loud it is relative to its siblings, whether
it's pitched up — lives in this one 200-entry array, indexed by the same channel number that also
selects which WAV file plays. This is a natural place to look first if a future change wanted to
retune a specific sound effect's character without touching any of `Decor.cpp`'s gameplay logic:
the mapping from gameplay event to `SoundChannel` and the mapping from `SoundChannel` to
loudness/pitch are two independent, cleanly separated tables.

## See also

- [Chapter 38: Sound/ISound Architecture](ch38-sound-isound-architecture.md) — how `Sound::Play`
  consumes this table, and how `Decor` decides which channel to play for which gameplay event.
- [Chapter 40: Audio Issue Analysis](ch40-audio-issue-analysis.md) — the game's own prior
  investigation that first compared this table against the original C# source and ruled it out as
  the cause of a "high-pitched sound effects" bug report.
- [Chapter 26: Tile and Icon Catalog](../part04-decor-simulation/ch26-tile-and-icon-catalog.md) —
  the same raw tile-icon ranges reused by `SoundEnviron` to select `SoundChannel78`-`91` variants.
- [Chapter 42: KeyPressFlags and Mapping](../part07-input/ch42-keypressflags-and-mapping.md) — the
  sibling small bitmask/lookup enum on the input side, using the same `ToRaw`/`To*` conversion
  idiom as `SoundChannel`.
