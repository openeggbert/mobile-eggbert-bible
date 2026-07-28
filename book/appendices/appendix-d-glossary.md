# Appendix D: Glossary

Alphabetical glossary of terms used throughout this book. Three kinds of term are mixed together
and marked accordingly:

- **Game-specific terms** — mechanics/objects internal to Speedy Blupi's design, many carrying
  their original French internal names from the source.
- **Technical terms** — XNA/CNA/rendering vocabulary the book uses when describing the engine.
- **Project-specific terms** — vocabulary specific to the `mobile-eggbert` C++ port and this book's
  own methodology.

Where a French-derived internal name's meaning is confirmed directly by a Doxygen comment or an
unambiguous code site (a predicate method, an enum comment), that is stated as fact with a
citation. Where a term is not directly glossed in a comment and the meaning below rests on reading
the French word itself, that is flagged explicitly as **an inferred translation, not one
confirmed from a code comment.**

---

**Ascenseur** *(game-specific, French: "elevator/lift")* — Internal name for the platform-lift
mechanic. `Decor::AscenseurDetect()` returns "the index of the lift object in `m_moveObject[]`
that Blupi has entered" (`Decor.hpp:1516-1519`), confirming the translation directly.
`ObjectType1`, `ObjectType47`, and `ObjectType48` are the three lift variants (see
[Appendix B](appendix-b-enum-catalog.md)). Covered in
[Chapter 19](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md).

**BlupiAction** *(technical/game-specific)* — The `enum class` (88 values) encoding every
animation/movement state Blupi's state machine can be in (idle, walking, jumping, vehicle modes,
hazard contacts, celebrations). See [Appendix B, §1](appendix-b-enum-catalog.md#1-blupiaction--player-actionanimation-state-88-values)
and [Chapter 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md).

**Blupi** *(game-specific)* — The player character; the game's namesake. Rendered from the
`Blupi`/`Blupi1_11`/`Blupi1_12`/`Blupi1_13` `PixmapChannel` atlases (`blupi.png`/`blupi1.png`).
Also used as the name of four alternate-skin `ObjectType`s (200–203) used for costume selection
and hostile clones.

**Caisse** *(game-specific, French: "crate/box")* — Internal name for pushable crate objects.
`Decor::CaisseInFront()` is documented as returning "the index of the frontmost crate" and
`Decor::UpdateCaisse()` maintains the pool of active crates (`Decor.hpp:1553-1599`), confirming
the translation directly. Crate-pushing is triggered by `BlupiAction::Push`.

**CNA** *(technical)* — The C++ framework `mobile-eggbert` runs on: an XNA-4.0-compatible,
cross-platform game framework built on SDL3 (per `README.md`: *"CNA is XNA-like wrapper around the
SDL 3... library"*). CNA itself is covered only marginally in this book — deep dives into its
internals belong to the sister project `cna-bible` (see `CLAUDE.md`'s stated scope). When this
book says "mobile-eggbert calls XNA's `SpriteBatch`," it means "calls CNA's implementation of the
XNA `SpriteBatch` API."

**Config.hpp** *(project-specific)* — The header declaring the `Config` static class that selects
LEGACY vs. MODERN at compile time and defines every timing/resolution constant those modes
depend on (`Config::ScaleTime()`, `Config::ScaleDiv()`, `Config::SPEED_SCALE`,
`Config::CURRENT_FPS`). See the **LEGACY / MODERN** entry below and
[Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md).

**ContentManager** *(technical)* — The XNA-style asset-loading object (`Microsoft::Xna::Framework::
Content::ContentManager`) exposed through `IGame1::getContentProperty()` (`IGame1.hpp:293`) and
used by `Game1`, `Pixmap`, and `Sound` to load texture atlases and WAV files respectively.

**Decor** *(game-specific and technical, French: "scenery/set")* — Two related but distinct
meanings the reader must keep separate: (1) `Decor`, the ~11,700-line C++ class that is the
gameplay simulation core (tile map, Blupi state machine, moving objects, collision — see
[Chapter 15](../part04-decor-simulation/ch15-decor-overview.md)); and (2) "decor" as a plain noun
meaning the visible per-region background art loaded via `Pixmap::BackgroundCache()` from
`Content/backgrounds/decorNNN.png`. Per `PLAN.md`'s verified finding, the numeric `icon` values
stored in `Decor::m_decor[][]` (the 100×100 tile grid) are a separate, invisible
*gameplay-classification* layer read by dozens of `Is*()` predicates — they are not indices into
the visible background art. See [Chapter 16](../part04-decor-simulation/ch16-tile-map.md).

**DoorKeyFlags** *(technical/game-specific)* — Bitmask `enum class` tracking which of Blupi's
three collectible keys are held (`Key1`/`Key2`/`Key3`/`All`). See
[Appendix B, §7](appendix-b-enum-catalog.md#7-doorkeyflags--key-inventory-bitmask-5-values-incl-all)
and [Chapter 22](../part04-decor-simulation/ch22-doors-keys-doorkeyflags.md).

**Ecraseur** *(game-specific, French: "crusher")* — Internal name for the crushing-hazard tile
type. `Decor::IsEcraseur()` is documented as testing "whether a crusher (ecraseur) hazard is
active at the given position" (`Decor.hpp:1249-1253`), confirming the translation directly.

**ENUMS.md** *(project-specific)* — A file inside the `mobile-eggbert` repository proposing eight
groups of magic-number-to-`enum class` refactorings (tile icon types, door state, terrain type,
and five smaller groups). **It is a refactoring analysis document, not implemented code** — it
opens with "No code has been changed. This is an analysis-only document." Every reference to it in
this book (see [Appendix B](appendix-b-enum-catalog.md#proposed-not-implemented-see-enumsmd) and
[Chapter 26](../part04-decor-simulation/ch26-tile-and-icon-catalog.md)) must and does label it as
such, per `CLAUDE.md`'s non-negotiable methodology.

**Fromage** *(game-specific, French: "cheese")* — Internal name for a tile-adaptation type.
`Tables::table_adapt_fromage` is documented directly as the "cheese / fromage tile-type
neighbour-to-icon mapping (32 entries)" (`Tables.hpp:618-623`), confirming the translation
directly — it is one of several neighbour-bitmask-to-replacement-tile tables alongside
`table_adapt_decor` (see [Chapter 30](../part05-sprites-rendering-animation/ch30-tables-animation-and-movement-data.md)).

**Glu** *(game-specific, French: "glue")* — Internal name for the sticky-trap hazard.
`BlupiAction::Glu` is documented as "stuck in glue/trap" and `ObjectType34` is a "goo/glue
particle (`table_glu`, 25-frame looping Element animation)" that "sticks to the level geometry"
(`decor/ObjectType.hpp:159`), confirming the translation directly.

**ILSpy** *(project-specific/technical)* — The .NET decompiler used to recover C# source from the
original 2013 compiled Windows Phone XNA binary, the first step in the port chain documented in
`README.md`: *"decompiled by the ILSpy to the C# source code."* See
[Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md).

**LEGACY / MODERN** *(project-specific)* — The two mutually-exclusive compile-time build
configurations defined by `Config.hpp`. LEGACY reproduces the original 20 FPS Windows Phone
behaviour unchanged; MODERN enables higher frame rates, touch-button auto-hiding, an expanded
cheat system (typed cheat codes, debug overlay, zoom cheat), and requires every frame-count
constant to pass through `Config::ScaleTime()`/`ScaleDiv()`. "Exactly one of LEGACY or MODERN must
be defined" (`Config.hpp`'s own `@details`). See
[Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md).

**MonoGame** *(project-specific/technical)* — The open-source, cross-platform reimplementation of
the XNA API that the ILSpy-decompiled C# source was migrated to as the second step of the port
chain, before the eventual migration to C++ and CNA (`README.md`, `CLAUDE.md`).

**ObjectType** *(technical/game-specific)* — The `enum class` (139 named values, roughly half
documented as "purpose unknown") identifying every species of `MoveObject` the `Decor` engine can
spawn: enemies, crates, projectiles, collectibles, lifts, hazards, and effects. See
[Appendix B, §8](appendix-b-enum-catalog.md#8-objecttype--moving-object-species-ids-139-named-values).

**Ouf** *(game-specific, French interjection: "phew!")* — Internal naming family for Blupi's
relief/celebration animations after surviving a dangerous situation (`BlupiAction::Ouf1a` through
`Ouf5`), confirmed directly by the header's own grouping note: *"Ouf variants: recovery/
celebration animations after a dangerous situation"* (`def/BlupiAction.hpp`).

**Pente** *(technical/game-specific, French: "slope/slant")* — The diagonal, italic-like text
rendering mode implemented by `Text::DrawTextPente()`, which accumulates rendered pixel width and
divides by a `pente` parameter to compute a per-glyph Y-offset — larger values give a shallower
slant (`Text.hpp`'s file-level `@details`). See
[Chapter 35](../part05-sprites-rendering-animation/ch35-text-rendering.md).

**Piège** *(game-specific, French: "trap")* — Internal name for the spike-trap hazard tile.
`Decor::IsPiege()` is documented as testing for "an active trap tile... at `pos`"
(`Decor.hpp:1216-1219`), confirming the translation directly.
`ENUMS.md`'s proposed (not implemented) `TileIconType` group maps icon 373 to `SpikeTrap`
("piège" in its own annotation).

**Ressort** *(game-specific, French: "spring")* — Internal name for the bounce-spring tile type.
`Decor::IsRessort()` is documented as testing for "a spring tile... causing an upward bounce"
(`Decor.hpp:1267-1270`), confirming the translation directly.

**Scie** *(game-specific, French: "saw")* — Internal name for the rotating-saw-blade hazard.
`Decor::IsScie()` is documented as testing "whether a saw (scie) hazard is present"
(`Decor.hpp:1232-1236`), confirming the translation directly.

**SharpRuntime** *(technical)* — The C++ reimplementation of .NET base-class-library types
(`System.Math`, `System.String`, `EventHandler`, `IDisposable`, primitive type aliases like
`intcs`/`ubytecs`/`ushortcs`) that both CNA and `mobile-eggbert` build on. Every enum's underlying
type in [Appendix B](appendix-b-enum-catalog.md) (`ubytecs`, `ushortcs`) is a SharpRuntime alias,
chosen to preserve the original C# enum's storage layout for save-file compatibility. Covered only
marginally, per this book's CNA-adjacent scope (`CLAUDE.md`).

**SoundChannel** *(technical/game-specific)* — The 93-value `enum class` mapping one enumerator
per `sounds/soundNNN.wav` asset. See
[Appendix B, §11](appendix-b-enum-catalog.md#11-soundchannel--sound-effect-asset-slot-93-values)
and [Chapter 39](../part06-audio/ch39-soundchannel-and-mixing.md).

**Sploutch / Plouf** *(game-specific, French onomatopoeia for a splash)* — Internal names for
water-impact visual effects of increasing size. `ObjectType14` ("water plouf splash"),
`ObjectType35` ("small `tiplouf` splash"), and `ObjectType98`–`100` (`sploutch1`/`2`/`3`, 10/13/18
frames respectively, "spawned when entering water" at increasing impact size) — meanings confirmed
directly by their `decor/ObjectType.hpp` Doxygen comments.

**SpriteBatch** *(technical)* — The XNA-style batched sprite-drawing API that `Pixmap` wraps.
`Pixmap.hpp`'s file-level `@details` documents that when `CNA_SPRITE_BATCHING_ENABLED` is defined,
callers must bracket a frame's draw calls with `BeginBatch()`/`EndBatch()` so all
`DrawPart`/`DrawIcon`/`DrawBackground` calls share one `SpriteBatch::Begin`–`End` pair, "reducing
GPU draw-call overhead by roughly 50-100x." See
[Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md).

**Sprite atlas** *(technical)* — A single image file packing many individual sprite frames on a
fixed grid, sliced at runtime by coordinate arithmetic. `Pixmap::GetSrcRectangle()`
(`Pixmap.cpp:683`) is `mobile-eggbert`'s implementation: given an icon index and a per-channel
grid cell size/gap (documented per-channel in `PLAN.md`'s sprite-atlas table), it computes the
source rectangle within the relevant `Content/icons/*.png` file. See
[Chapter 29](../part05-sprites-rendering-animation/ch29-sprite-atlas-system.md).

**State machine** *(technical)* — The general design pattern used at two distinct levels in this
codebase: `Game1`'s `Def::Phase` enum governs the top-level screen/mode (menu, playing, paused,
…), while `Decor`'s `BlupiAction` enum governs the player character's per-frame animation/movement
state within the `Play` phase. See [Chapter 12](../part03-architecture/ch12-game1-state-machine.md)
and [Chapter 17](../part04-decor-simulation/ch17-blupi-state-machine.md).

**Tile map** *(technical/game-specific)* — The 100×100 grid of `Decor::Cellule` structs
(`m_decor`/`m_bigDecor`) forming a level's layout; `MAXCELX`/`MAXCELY` in `Def.hpp` fix the grid
at 100×100, with each tile occupying `DIMOBJX`×`DIMOBJY` (64×64) game-space pixels. See
[Chapter 16](../part04-decor-simulation/ch16-tile-map.md).

**Ventillo** *(game-specific, French-derived: "ventilo," colloquial short form of "ventilateur,"
fan)* — Internal name for the fan-hazard tile. `Decor::IsVentillo()` is documented as testing for
"an active fan tile that pushes Blupi" (`Decor.hpp:1423-1426`), confirming the translation
directly. Contact with a fan triggers `DecorAction::BigShake` and `ObjectType11`'s shockwave
effect.

**Voyage** *(game-specific, French: "journey/trip")* — Internal name for the arcing
item-collection animation: a collected item visually travels from its pickup point to its HUD
destination (e.g. the treasure counter). `Decor::VoyageInit()` is documented directly as
"Initialises a Voyage (item-collection arc) animation" (`Decor.hpp:1765-1774`), confirming the
translation directly. Advanced per-frame by `VoyageStep()` and drawn by `VoyageDraw()`.

**XNA** *(technical)* — Microsoft's XNA Framework, the original 2013 Windows Phone game's
programming API (`Game`, `SpriteBatch`, `ContentManager`, `GameTime`, etc.). `mobile-eggbert`'s
entire class structure (`Game1 : Game`, XNA-shaped method names like `Initialize`/`LoadContent`/
`Update`/`Draw`) preserves this API surface exactly, now served by CNA rather than real XNA or
MonoGame. See [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md).

**`SEC_*` / `ACTION_*` / `CH*` / `KEY_*` constants** *(project-specific)* — Naming convention notes
scattered through the enum headers referring back to the *original C# source's* integer constant
names that a given `enum class` value replaces (e.g. `SecretPower::Shield` corresponds to the
original `SEC_SHIELD`, `BlupiAction::Jump` to `ACTION_JUMP`). These are documentation breadcrumbs
connecting the ported enum to its pre-port identifier, not a namespace that exists in the current
C++ code.
