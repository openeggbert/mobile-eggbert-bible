# Chapter 27: `Decor.hpp` Reference Catalog

This chapter is a dense, appendix-style reference to every declaration in
`include/WindowsPhoneSpeedyBlupi/Decor.hpp` (2,064 lines): the nested types, every `static
constexpr` constant, every member variable, and every method — public and private. It complements
rather than repeats [Chapters 15–26](ch15-decor-overview.md), which narrate *how* the interesting
subsystems work; here, each entry gets one row and a pointer to the chapter that covers it in prose,
with extra detail only where no narrative chapter already owns the topic. Line numbers cite
`Decor.hpp` unless a row is explicitly about the `.cpp` implementation.

## Nested types

| Type | Kind | Purpose | Citation |
|---|---|---|---|
| `IconType` | `enum class` (empty) | Explicitly documented placeholder: *"ported from the original C# codebase... not yet populated with values and has no effect on current gameplay."* Declared but has zero enumerators and is never referenced anywhere else in `Decor.hpp`/`.cpp`. | `Decor.hpp:93-96` |
| `Cellule` | `struct` | One tile map cell: a single `intcs icon` field. The entire collision/rendering classification system in [Chapter 26](ch26-tile-and-icon-catalog.md) reduces to comparisons against this one field. | `Decor.hpp:113-116` |
| `MoveObject` | `struct` | One active moving object (enemy, crate, projectile, collectible, vehicle, lift, particle-emitting object, etc.) — see field table below. Pool: `m_moveObject[MAXMOVEOBJECT]`. [See Chapter 19](ch19-moving-objects-and-decor-actions.md). | `Decor.hpp:139-154` |
| `ByeByeObject` | `class` | Short-lived, gameplay-inert visual fragment (e.g., helicopter-destruction debris). Stored in `std::vector<ByeByeObject> byeByeObjects`, not a fixed pool. | `Decor.hpp:170-182` |

### `MoveObject` fields

| Field | Type | Purpose |
|---|---|---|
| `type` | `ObjectType` | What kind of object this is. [See Chapter 19](ch19-moving-objects-and-decor-actions.md). |
| `stepAdvance` / `stepRecede` | `intcs` | Pixels per frame moving toward `posEnd` / back toward `posStart`. |
| `timeStopStart` / `timeStopEnd` | `intcs` | Frames to pause at each endpoint before reversing. |
| `posStart` / `posEnd` / `posCurrent` | `TinyPoint` | Path endpoints and live position, game-space pixels. |
| `step` | `intcs` | Distance traveled along the current leg. |
| `time` | `intcs` | Remaining pause countdown at the current endpoint. |
| `phase` | `intcs` | Animation step counter (table index, not a sprite ID). |
| `channel` | `PixmapChannel` | Sprite sheet used to draw this object. |
| `icon` | `intcs` | Icon slot within `channel`. |

### `ByeByeObject` fields

| Field | Type | Purpose |
|---|---|---|
| `channel` / `icon` | `PixmapChannel` / `intcs` | Sprite for this fragment. |
| `posX` / `posY` | `double` | Float game-space position (smooth motion, unlike the integer `TinyPoint` used elsewhere). |
| `rotation` | `double` | Current rotation, radians. |
| `phase` | `double` | Float animation progress (not a table index). |
| `animationSpeed` | `double` | Phase increment per frame. |
| `rotationSpeed` | `double` | Angular velocity, radians/frame. |
| `speedX` | `double` | Horizontal velocity, pixels/frame. |

## `static constexpr` constants

| Constant | Value | Meaning | Citation |
|---|---|---|---|
| `MAXMOVEOBJECT` | `200` | Size of the `m_moveObject` pool. | `Decor.hpp:185` |
| `MAXQUART` | `441` | Number of icons covered by the quarter-tile collision table `Tables::table_decor_quart` (441 × 16 = 7,056 entries). [See Chapter 26](ch26-tile-and-icon-catalog.md#collision-classification-ispassiconisblocicon-and-table_decor_quart). | `Decor.hpp:187` |
| `SCROLL_SPEED` | `8` | Viewport scroll speed, game-space px/frame. | `Decor.hpp:189` |
| `SCROLL_MARGX` / `SCROLL_MARGY` | `80` / `40` | Scroll-trigger margins, px. | `Decor.hpp:191-193` |
| `BLUPIFLOOR` | `2` | Blupi's sink-into-floor offset, px. | `Decor.hpp:195` |
| `BLUPIOFFY` | `4 + BLUPIFLOOR` (`6`) | Total feet-to-bounding-box-top offset. | `Decor.hpp:197` |
| `BLUPISURF` | `12` | Surfboard submersion depth, px — used directly by `IsSurfWater` ([Chapter 26](ch26-tile-and-icon-catalog.md)). | `Decor.hpp:199` |
| `BLUPISUSPEND` | `12` | Rope/bar suspend offset, px. | `Decor.hpp:201` |
| `OVERHEIGHT` | `80` | Extra bounding-box height in overcraft mode, px. | `Decor.hpp:203` |
| `m_balleTrajLength` / `m_moveTrajLength` | `1300` each | Sizes of the bit-packed bullet/object occupancy arrays. | `Decor.hpp:213`, `217` |
| `m_doorsLength` | `200` | Size of `m_doors[]`; matches `GameData`'s 200-byte per-gamer door block. [See Chapter 22](ch22-doors-keys-doorkeyflags.md). | `Decor.hpp:497` |
| `m_rankCaisseLength` / `m_linkCaisseLength` | `MAXMOVEOBJECT` (`200`) each | Crate index-array sizes. | `Decor.hpp:254`, `261` |

## Member variables

Grouped by concern; every field already carries a real Doxygen `@brief`/comment in the header, quoted or closely paraphrased here.

### Subsystem pointers (not owned by `Decor`)

| Field | Type | Purpose |
|---|---|---|
| `m_sound` | `ISound*` | Audio subsystem. |
| `m_pixmap` | `IPixmap*` | Rendering subsystem. |
| `m_gameData` | `GameData*` | Persistent save data. |

### Tile map and trajectory grids — [Chapter 16](ch16-tile-map.md)

| Field | Type | Purpose |
|---|---|---|
| `m_decor` | `Cellule[100][100]` | Primary tile map. |
| `m_bigDecor` | `Cellule[100][100]` | Secondary "big-tile" background layer, same layout. |
| `m_balleTraj` | `intcs[1300]` | Bit-packed bullet-trajectory occupancy grid (13 words/row × 100 rows). |
| `m_moveTraj` | `intcs[1300]` | Bit-packed moving-object occupancy grid, same layout. |

### Moving objects — [Chapter 19](ch19-moving-objects-and-decor-actions.md)

| Field | Type | Purpose |
|---|---|---|
| `m_moveObject` | `MoveObject[MAXMOVEOBJECT]` | The active-object pool. |
| `m_nbRankCaisse` / `m_rankCaisse` | `intcs` / `intcs[200]` | Count and indices of pool slots classified as crates. |
| `m_nbLinkCaisse` / `m_linkCaisse` | `intcs` / `intcs[200]` | Count and indices of crates currently linked for group movement. |
| `byeByeObjects` | `std::vector<ByeByeObject>` | Active destruction-debris fragments. |

### Input and viewport

| Field | Type | Purpose |
|---|---|---|
| `m_keyPress` / `m_lastKeyPress` | `intcs` | Current / previous-frame `KeyPressFlags` bitmask. [See Chapter 42](../part07-input/ch42-keypressflags-and-mapping.md). |
| `m_posDecor` | `TinyPoint` | Viewport scroll top-left, game-space px. |
| `m_dimDecor` | `TinyPoint` | Visible viewport dimensions, game-space px. |
| `m_drawBounds` | `TinyRect` | Draw-culling rectangle; exposed via `getDrawBoundsProperty()`/`setDrawBoundsProperty()`. |
| `m_scrollPoint` / `m_scrollAdd` | `TinyPoint` | Scroll target and per-frame smoothing delta. |

### Level/session state

| Field | Type | Purpose |
|---|---|---|
| `m_term` | `intcs` | Win/loss signal: `0` running, `>0` won, `<0` lost. Read via `IsTerminated()`. [See Chapter 24](ch24-missions-and-continuemission.md). |
| `m_music` | `intcs` | Current music track index. |
| `m_region` | `intcs` | World region (background/music selector). |
| `m_time` | `intcs` | Global frame counter, incremented every `MoveStep()`; the argument to nearly every `Config::ScaleTime()`/`ScaleDiv()` call. [See Chapter 25](ch25-game-speed-and-zoom.md). |
| `m_bPause` | `intcs` | Non-zero while gameplay is paused. |
| `m_mission` | `intcs` | Current mission/level index. [See Chapter 24](ch24-missions-and-continuemission.md). |
| `m_bPrivate` | `bool` | True for user-created (non-official) levels. |
| `m_buildOfficialMissions` | `bool` | Documented as suppressing gameplay features while building the official mission map — but confirmed dead in the current source (set once, read never). [See Chapter 24](ch24-missions-and-continuemission.md#m_buildofficialmissions-declared-set-once-read-never). |
| `m_doors` | `intcs[200]` | Per-level door state. [See Chapter 22](ch22-doors-keys-doorkeyflags.md). |
| `m_nbVies` | `intcs` | Lives remaining; can go to `-1` as an internal "just died" marker despite the header's "must be non-negative" comment. [See Chapter 24](ch24-missions-and-continuemission.md#getnbviessetnbvies-lives-confirmed). |
| `m_nbTresor` / `m_totalTresor` | `intcs` | Treasures collected / total in the level. |
| `m_goalPhase` | `intcs` | Win-sequence animation phase counter. |
| `m_detectIcon` | `intcs` | Last interactive tile icon seen during collision scanning. |
| `m_music`, `m_region` (see above) | — | — |

### Blupi core state — [Chapter 17](ch17-blupi-state-machine.md), [Chapter 18](ch18-blupi-actions-and-animation.md)

| Field | Type | Purpose |
|---|---|---|
| `m_blupiPos` / `m_blupiLastPos` / `m_blupiValidPos` | `TinyPoint` | Current, previous-frame, and last-known-safe position. |
| `m_blupiAction` | `BlupiAction` | Current state-machine action; combined with phase/direction to resolve the sprite via `Tables::table_blupi`. |
| `m_blupiDir` | `Direction` | Facing direction. |
| `m_blupiPhase` | `intcs` | Animation step counter for the current action (table index, not a sprite ID). |
| `m_blupiVitesseX` / `m_blupiVitesseY` | `double` | Physics velocity, px/frame at the original rate. |
| `m_blupiSubPixelX` / `m_blupiSubPixelY` | `double` | Sub-pixel accumulators preventing integer-truncation drift at higher FPS. |
| `m_blupiIcon` | `intcs` | Resolved sprite icon for the current frame — a rendering *output*, not gameplay state. |
| `m_blupiChannel` | `PixmapChannel` | Sprite sheet used to draw Blupi (varies by vehicle/mode). |
| `m_blupiVector` | `TinyPoint` | Last movement vector applied. |
| `m_blupiTransport` | `intcs` | Index of the lift object currently carrying Blupi, or `-1`. |
| `m_blupiFocus` | `bool` | True when Blupi has input focus. |
| `m_blupiAir` | `bool` | True when airborne. |
| `m_blupiFront` | `bool` | True when drawn in front of moving objects. |
| `m_blupiRestart` | `bool` | True if Blupi should respawn at `m_blupiStartPos` next update. |
| `m_blupiStartPos` / `m_blupiStartDir` | `TinyPoint` / `Direction` | Level start/respawn position and facing. |
| `m_blupiFifoNb` / `m_blupiFifoPos` | `intcs` / `TinyPoint[10]` | Circular buffer of recent positions for rope/suspend animation. |
| `m_blupiSpeedX` / `m_blupiSpeedY` | `double` | Player-input-derived speed. |
| `m_blupiLastSpeedX` / `m_blupiLastSpeedY` | `double` | Previous-frame speed, for smooth deceleration. |
| `m_blupiLevel` | `intcs` | Blupi's upgrade/experience level. |
| `m_blupiLogicRotation` / `m_blupiRealRotation` | `intcs` | Logical vs. rendered rotation angle, degrees. |
| `m_blupiOffsetY` | `intcs` | Vertical draw-position adjustment for vehicle modes. |

### Blupi vehicle/mode flags — [Chapter 17](ch17-blupi-state-machine.md)

| Field | Type | Purpose |
|---|---|---|
| `m_blupiHelico` | `bool` | Helicopter (free vertical flight) mode. |
| `m_blupiOver` | `bool` | Overcraft (flat/squashed) mode. |
| `m_blupiJeep` | `bool` | Jeep vehicle. |
| `m_blupiTank` | `bool` | Tank vehicle. |
| `m_blupiSkate` | `bool` | Skateboard. |
| `m_blupiNage` | `bool` | Swimming ("nage" = swim). |
| `m_blupiSurf` | `bool` | Surfboard. |
| `m_blupiVent` | `bool` | Currently pushed by wind. |
| `m_blupiSuspend` | `bool` | Hanging from rope/bar. |
| `m_blupiJumpAie` | `bool` | Hurt-jump animation active. |
| `m_blupiInvert` | `bool` | Controls inverted (left/right swapped). |
| `m_blupiBalloon` | `bool` | Balloon (slow-fall) mode. |
| `m_blupiEcrase` | `bool` | Crushed state. |
| `m_blupiGhost` (`MODERN`) | `bool` | Ghost/free-flight cheat mode. [See Chapter 23](ch23-secret-powers-and-cheat-system.md). |

### `SecretPower` and related — [Chapter 23](ch23-secret-powers-and-cheat-system.md)

| Field | Type | Purpose |
|---|---|---|
| `m_blupiSec` | `SecretPower` | Currently *rendered* power (recomputed each `Build()` call from the four booleans below). |
| `m_blupiShield` / `m_blupiPower` / `m_blupiCloud` / `m_blupiHide` | `bool` | The real, persistent per-power state. |
| `m_blupiTimeShield` | `intcs` | Remaining Shield-invincibility frames. |
| `m_blupiTimeFire` | `intcs` | Tank fire cooldown. |
| `m_cheatZoomFactor` (`MODERN`) | `double` | Cheat zoom multiplier. [See Chapter 25](ch25-game-speed-and-zoom.md). |

### Blupi misc timers, sound, and item counts

| Field | Type | Purpose |
|---|---|---|
| `m_blupiMotorHigh` | `bool` | Vehicle motor sound currently at high pitch. |
| `m_blupiMotorSound` | `SoundChannel` | Looping vehicle motor sound channel. |
| `m_blupiPosHelico` | `TinyPoint` | Last helicopter position (sound positioning). |
| `m_blupiPosMagic` | `TinyPoint` | Position of the active magic-effect visual. |
| `m_blupiBullet` | `intcs` | Active tank-shot count. |
| `m_blupiCle` | `DoorKeyFlags` | Keys currently held. [See Chapter 22](ch22-doors-keys-doorkeyflags.md). |
| `m_blupiPerso` | `intcs` | Index of the NPC/persona following Blupi, or `-1`; also reused as the `Bombs` cheat's dynamite-supply counter. |
| `m_blupiDynamite` | `intcs` | Dynamite stick count. |
| `m_blupiNoBarre` | `intcs` | Rope/bar-use cooldown, frames remaining. |
| `m_blupiTimeNoAsc` | `intcs` | Frames during which lifts cannot pick Blupi up. |
| `m_blupiTimeMockery` | `intcs` | Remaining enemy-mockery reaction frames. |
| `m_blupiTimeOuf` / `m_blupiActionOuf` | `intcs` / `BlupiAction` | "Ouf" (relief) animation timer and the action it interrupted. |
| `m_bFoundCle` | `bool` | True once the level's key has been picked up. |
| `m_jauges` | `Jauge[2]` | HUD gauges: `[0]` lives/energy, `[1]` charge/special. |
| `m_bCheatDoors` | `bool` | `OpenDoors` cheat toggle. [See Chapter 23](ch23-secret-powers-and-cheat-system.md). |
| `m_bSuperBlupi` | `bool` | `SuperBlupi` cheat toggle. |
| `m_bDrawSecret` | `bool` | `ShowSecret` cheat toggle (controls icon `214`'s visibility — [Chapter 26](ch26-tile-and-icon-catalog.md)). |
| `m_sucettePos` / `m_sucetteType` | `TinyPoint` / `ObjectType` | Position/type of the active lollipop power-up. |

### Decor/voyage animation state — [Chapter 19](ch19-moving-objects-and-decor-actions.md)

| Field | Type | Purpose |
|---|---|---|
| `m_voyageIcon` / `m_voyageChannel` | `intcs` / `PixmapChannel` | Sprite for the active item-collection "Voyage" flight animation. |
| `m_voyagePhase` / `m_voyageTotal` | `intcs` | Current/total animation phase steps. |
| `m_voyageStart` / `m_voyageEnd` | `TinyPoint` | Arc endpoints. |
| `m_decorAction` | `DecorAction` | Current animated-tile action state (e.g., screen shake). |
| `m_decorPhase` | `intcs` | Phase counter for `m_decorAction`. |
| `m_lastDecorIcon` | `intcs[200]` | Cache of last-drawn icon per decor position, to skip redundant redraws. |

### Camera hotspot zoom — [Chapter 25](ch25-game-speed-and-zoom.md)

| Field | Type | Purpose |
|---|---|---|
| `m_hotSpotFinalZoom/X/Y` | `double` | Target zoom/center for the camera animation. |
| `m_hotSpotCurrentZoom/X/Y` | `double` | Current interpolated zoom/center. |
| `m_hotSpotStepZoom/X/Y` | `double` | Per-frame interpolation step, `SPEED_SCALE`-derived. |
| `m_hotSpotOutLag` | `double` | Hysteresis countdown keeping the camera zoomed in briefly after motion stops. |

### Misc

| Field | Type | Purpose |
|---|---|---|
| `m_random` | `std::unique_ptr<System::Random>` | Deterministic RNG for gameplay effects (e.g., lightning color variant selection). |

## Public API, by area

### Lifecycle

| Signature | Purpose | Detail |
|---|---|---|
| `Decor()` | Constructor; default-initializes state. | Call `Create()` before simulating. |
| `void Create(ISound*, IPixmap*, GameData*)` | Binds the three non-owned subsystem pointers. | Must precede every other call. |
| `bool LoadImages()` | Loads the background image set for `m_region`. | [See Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md). |
| `void PlayPrepare(bool bTest)` | Initializes Blupi and gameplay state for play or editor-test mode. | [See Chapter 15](ch15-decor-overview.md). |
| `int IsTerminated()` | Returns `m_term` — 0 running / >0 won / <0 lost. | [See Chapter 24](ch24-missions-and-continuemission.md). |
| `void MoveStep()` | Advances the whole simulation one frame: `MoveObjectStep()` → `ByeByeStep()` → `BlupiStep()` → `MoveHotSpot()` → `AdaptMotorVehicleSound()`, wrapped in a swallowing `try`/`catch`. | [See Chapter 15](ch15-decor-overview.md). |
| `void Build()` | Renders the whole visible frame: background → `m_bigDecor` → Blupi/objects → `m_decor` (with animated-hazard remapping) → HUD/particles/voyage. [See Chapter 26](ch26-tile-and-icon-catalog.md#first-a-structural-correction-tile-icons-do-draw-real-sprites) for the icon→sprite rendering detail. | `Decor.cpp:649` onward. |

### Input

| Signature | Purpose |
|---|---|
| `void SetSpeedX(double)` / `void SetSpeedY(double)` | Store player-controlled speed, called by `InputPad` each frame. |
| `void KeyChange(int keyPress)` | Updates the current `KeyPressFlags` bitmask. |
| `DDATA(Def::ButtonGlyph, ButtonPressed)` | Generated property (getter/setter) for the last virtual button pressed — feeds `IsDoor`'s open-toward-facing logic and the win/goal checks. |

### Sound

| Signature | Purpose |
|---|---|
| `void StopSound()` | Stops all looping gameplay sounds (pause/level-end). |
| `void StartSound()` | Restarts looping sounds after unpause. |

### Viewport / dimensions

| Signature | Purpose |
|---|---|
| `TinyRect getDrawBoundsProperty() const` / `void setDrawBoundsProperty(TinyRect)` | Draw-culling rectangle accessors. |
| `TinyPoint GetDim()` / `void SetDim(TinyPoint)` | Viewport dimension accessors. |

### Missions and lives — [Chapter 24](ch24-missions-and-continuemission.md)

| Signature | Purpose |
|---|---|
| `int GetMission()` / `void SetMission(int)` | Plain accessors for `m_mission`; no validation. |
| `int GetNbVies()` / `void SetNbVies(int)` | Plain accessors for `m_nbVies`; header claims non-negative, code violates this internally (`-1` marker). |

### Doors — [Chapter 22](ch22-doors-keys-doorkeyflags.md)

| Signature | Purpose |
|---|---|
| `void InitializeDoors(GameData&)` | Loads `m_doors[]` from save data for the current mission. |
| `void MemorizeDoors(GameData&)` | Saves `m_doors[]` back to `GameData`. |
| `void MainSwitchInitialize(int lastWorld)` | Sets hub-level door/switch state from world-completion progress. |
| `void AdaptDoors(bool bPrivate)` | Re-derives accessible doors from save state (or forces all-open for private levels). |

### Cheats — [Chapter 23](ch23-secret-powers-and-cheat-system.md)

| Signature | Purpose |
|---|---|
| `static std::string GetCheatTinyText(Def::ButtonGlyph)` | Short button-label text for the nine UI cheat buttons. |
| `void CheatAction(Tables::CheatCodes)` | Activates one cheat effect; 20 of 22 base enum values (plus `Ghost` in `MODERN`) have a real branch — `BuildOfficialMissions` and `KillEgg` do not. |
| `bool IsGhost()` | Returns `m_blupiGhost` (`MODERN`) or always `false` (`LEGACY`). |
| `void SetCheatZoom(double factor)` (`MODERN`) | Sets `m_cheatZoomFactor`. |

### `MODERN`-only debug read accessors — [Chapter 25](ch25-game-speed-and-zoom.md)

| Signature | Purpose |
|---|---|
| `int GetTime() const` | Returns `m_time`. |
| `TinyPoint GetBlupiPos() const` | Returns `m_blupiPos`. |
| `double GetBlupiVX() const` / `GetBlupiVY() const` | Return velocity components. |
| `bool GetBlupiAir/Helico/Skate/Nage() const` | Return the corresponding mode flag. |
| `int GetRegionDebug()` | Returns `GetRegion()` (otherwise private). |

### Save/load

| Signature | Purpose |
|---|---|
| `void CurrentDelete()` | Deletes the quick-save file. |
| `bool CurrentWrite()` | Writes a full quick-save snapshot (same format as level files). |
| `bool CurrentRead()` | Restores a quick-save snapshot; the sole `Decor` call driven by `ContinueMissionType` in `Game1`. [See Chapter 24](ch24-missions-and-continuemission.md#continuemissiontype-game1s-resume-state-machine). |
| `bool Read(int gamer, int rank, bool bUser)` | Loads a level file into `m_decor`/`m_bigDecor`/`m_moveObject`. [See Chapter 44](../part08-data-persistence-content/ch44-worlds-level-file-format.md). |

## Private API, by area

### Lifecycle / setup

| Signature | Purpose |
|---|---|
| `void InitDecor()` | Resets tile map and moving-object state to a clean baseline. |
| `void BuildPrepare()` | Editor-mode setup path within `PlayPrepare(false)`. |
| `void SetBuildOfficialMissions(bool)` | Setter for `m_buildOfficialMissions` — confirmed unreachable from any call site. [See Chapter 24](ch24-missions-and-continuemission.md#m_buildofficialmissions-declared-set-once-read-never). |
| `void MoveObjectCopy(MoveObject& dst, const MoveObject& src)` (static) | Field-by-field `MoveObject` copy. |

### Blupi state machine and physics — [Chapters 17–18](ch17-blupi-state-machine.md), [21](ch21-physics-and-collision.md)

| Signature | Purpose |
|---|---|
| `void BlupiSearchIcon()` | Resolves `m_blupiIcon`/`m_blupiChannel` for the current frame from action+phase+direction via `Tables::table_blupi`; also triggers idle sounds/splash particles as a side effect. |
| `bool BlupiIsGround()` | Tests whether Blupi's feet rest on a passable-below surface. |
| `TinyRect BlupiRect(TinyPoint pos)` | Computes Blupi's collision bounding box at `pos`. |
| `void BlupiAdjust()` | Nudges Blupi out of minor tile-edge penetration after movement. |
| `bool BlupiBloque(TinyPoint pos, int dir)` | Tests whether movement to `pos` in `dir` is blocked. |
| `void BlupiStep()` | The core per-frame Blupi state-machine/physics update. |
| `void BlupiGhostStep()` (`MODERN`) | Free-flight movement while `m_blupiGhost` is active. |
| `void BlupiDead(BlupiAction, std::optional<BlupiAction>)` | Triggers death animation(s), decrements lives, schedules respawn. |
| `void BlupiAddFifo(TinyPoint)` | Appends to the 10-entry rope/suspend position trail. |
| `bool BlupiElectro(TinyPoint)` | Applies an electric hazard hit if Blupi is touching it. |
| `TinyPoint GetPosDecor(TinyPoint)` | Converts a game-space position to scroll-relative screen position. |
| `void GetBlupiInfo(bool&, bool&, bool&, bool&)` | Batch-fetches helicopter/jeep/skate/swim flags. |

### Collision and tile classification — [Chapter 21](ch21-physics-and-collision.md), [Chapter 26](ch26-tile-and-icon-catalog.md)

| Signature | Purpose |
|---|---|
| `bool DecorDetect(TinyRect)` / `bool DecorDetect(TinyRect, bool bCaisse)` | Tests whether a rectangle overlaps a blocking tile (optionally treating crates as blocking). |
| `bool TestPath(const TinyRect&, const TinyPoint& start, TinyPoint& end)` | Finds the furthest reachable point along a path before an obstacle. |
| `bool IsPassIcon(int icon)` / `bool IsBlocIcon(int icon)` | Whole-tile passable/blocking classification via `Tables::table_decor_quart`. Full treatment in [Chapter 26](ch26-tile-and-icon-catalog.md). |
| `bool IsLave/IsPiege/IsGoutte/IsScie/IsSwitch/IsEcraseur/IsBlitz/IsRessort/IsTemp/IsBridge/IsNormalJump/IsSurfWater/IsDeepWater/IsOutWater/IsVentillo(TinyPoint...)` | Hazard/mechanism/water predicates. Fully cataloged in [Chapter 26](ch26-tile-and-icon-catalog.md). |
| `int IsDoor(TinyPoint, TinyPoint&)` / `int IsTeleporte(TinyPoint)` / `bool SearchTeleporte(TinyPoint, TinyPoint&)` | Door/teleporter detection and pairing. [Chapter 26](ch26-tile-and-icon-catalog.md) / [Chapter 22](ch22-doors-keys-doorkeyflags.md). |
| `int IsWorld(TinyPoint)` | Hub world-marker lookup. [Chapter 26](ch26-tile-and-icon-catalog.md#world-markers-and-auto-tiling-helpers). |
| `bool IsFloatingObject(int i)` | Tests the tile beneath a moving object for water-floating. |
| `bool IsRightBorder(int,int,int,int)` / `void AdaptMidBorder(int,int)` / `void AdaptBorder(TinyPoint)` | Auto-tiling border classification and application, called after `ModifDecor`. |
| `bool IsFromage(int,int)` / `bool IsGrotte(int,int)` | Terrain-family membership tests feeding the auto-tiler. |
| `void FlushBalleTraj()` / `void SetBalleTraj(TinyPoint)` / `bool IsBalleTraj(TinyPoint)` | Bit-packed bullet-occupancy grid (tile coords in, pixel coords out on the query side). |
| `void FlushMoveTraj()` / `void SetMoveTraj(TinyPoint)` / `bool IsMoveTraj(TinyPoint)` | Same scheme for moving-object occupancy. |
| `void ModifDecor(TinyPoint, int icon)` | Sets a tile's icon and marks it dirty for redraw. |
| `int GetTypeBarre(TinyPoint)` | Classifies a bar/rail grab point (icons `138`/`202`). |
| `int SearchDistRight(TinyPoint, TinyPoint dir, ObjectType)` | Scans for the nearest blocking tile in a direction (bullet range, object placement). |

### Doors and switches — [Chapter 22](ch22-doors-keys-doorkeyflags.md)

| Signature | Purpose |
|---|---|
| `void ActiveSwitch(bool, TinyPoint)` | Toggles a switch tile and every linked saw/blade tile in a 41-cell horizontal window. |
| `void OpenDoorsTresor()` | Opens every treasure-gated door (`421`+) whose requirement is met. |
| `void OpenDoor(TinyPoint)` | Clears a door tile and spawns its animated slide-away object. |
| `void OpenDoorsWin()` | Unlocks the next sublevel's door flag on win. |
| `void OpenGoldsWin()` | Marks the current world's gold flag on win. |
| `void DoorsLost()` | Resets `m_nbVies` to `3` on life loss (despite the name, does not touch `m_doors`). |
| `bool SearchDoor(int n, TinyPoint&, TinyPoint&)` | Locates door `n` and its Blupi entry point. |
| `bool SearchWorld(int, TinyPoint&, Direction&)` | Locates a world's start marker/direction. |
| `bool SearchGold(int n, TinyPoint&)` | Locates treasure `n`. |

### Moving objects — [Chapter 19](ch19-moving-objects-and-decor-actions.md)

| Signature | Purpose |
|---|---|
| `int ObjectStart(TinyPoint, ObjectType, int speed)` | Spawns and activates a pool object. |
| `bool ObjectDelete(TinyPoint, ObjectType)` | Removes a matching object at a position. |
| `void MoveObjectStep()` | Advances every active pool object one frame. |
| `void MoveObjectStepLine(int i)` | Advances one object's linear path/pause state. |
| `void MoveObjectStepIcon(int i)` | Advances one object's animation phase/icon. |
| `void MoveObjectPollution()` | Damages/destroys objects overlapping pollution tiles. |
| `void MoveObjectPlouf/Tiplouf/Blup(TinyPoint)` | Spawns splash/bubble particle effects. |
| `void DynamiteStart(int i, int dx, int dy)` | Initiates a dynamite explosion. |
| `void NetStopCloud(int rank)` | Documented cloud-net stop; **empty body**, intentionally elided from this port. |
| `void StartSploutchGlu(TinyPoint)` | Spawns a multi-part glue-splash effect. |
| `void MoveObjectFollow(TinyPoint)` | Advances follower NPCs toward Blupi. |
| `int MoveObjectDetect(TinyPoint, bool& bNear)` / `int MoveAscenseurDetect(TinyPoint, int height)` / `int MoveChargeDetect(TinyPoint)` / `int MovePersoDetect(TinyPoint)` | Proximity queries for nearest object / lift / charging enemy / following NPC. |
| `int MoveObjectDelete(TinyPoint cel)` | Removes every object at a tile cell. |
| `int MoveObjectFree()` | Finds a free pool slot. |
| `int MoveObjectSearch(TinyPoint)` / `int MoveObjectSearch(TinyPoint, std::optional<ObjectType>)` | Finds an object at/near a position, optionally type-filtered. |
| `int SortGetType(ObjectType)` / `void MoveObjectSort()` / `void MoveObjectPriority(int i)` | Draw-order priority computation and application. |
| `int MockeryDetect(TinyPoint)` | Finds a nearby taunt/mockery object. |

### Lifts (ascenseurs) and crates (caisses) — [Chapter 19](ch19-moving-objects-and-decor-actions.md) / [Chapter 22](ch22-doors-keys-doorkeyflags.md)

| Signature | Purpose |
|---|---|
| `int AscenseurDetect(TinyRect, TinyPoint oldpos, TinyPoint newpos)` | Detects Blupi entering/leaving a lift. |
| `void AscenseurVertigo(int i, bool&, bool&)` | Computes near-left/near-right-edge "vertigo" state on a lift. |
| `bool AscenseurShift(int i)` | Re-centers Blupi on a moving lift. |
| `void AscenseurSynchro(int i)` | Synchronizes paired/linked lifts. |
| `void UpdateCaisse()` | Rebuilds `m_rankCaisse`/`m_nbRankCaisse` from the pool. |
| `bool TestPushCaisse(int i, TinyPoint pos, bool bPop)` / `bool TestPushOneCaisse(int i, TinyPoint move, int b)` | Tests whether a crate (or crate chain) can be pushed. |
| `void SearchLinkCaisse(int rank, bool bPop)` / `bool AddLinkCaisse(int rank)` | Builds the linked-crate group for a push. |
| `int CaisseInFront()` / `int CaisseGetMove(int max)` | Finds the frontmost crate / computes actual push distance. |

### Rendering hooks

| Signature | Purpose |
|---|---|
| `void DrawInfo()` | Draws the HUD overlay (lives, keys, treasures). |
| `bool IsDisplayInfo(int tableTresor)` | Tests whether a given treasure-table entry's info overlay should show. |
| `TinyPoint DecorNextAction()` | Finds the next tile needing a shake/electric animation frame. |
| `void ResetHotSpot()` / `void MoveHotSpot()` | Reset / advance the camera hotspot zoom. [See Chapter 25](ch25-game-speed-and-zoom.md). |
| `bool BlitzActif(intcs, intcs)` | Tests the 100-tick lightning duty cycle for a cell. [See Chapter 26](ch26-tile-and-icon-catalog.md). |
| `void ByeByeHelico()` / `void ByeByeAdd(...)` / `void ByeByeStep()` / `void ByeByeDraw(TinyPoint)` | Helicopter-destruction particle lifecycle. |
| `TinyPoint VoyageGetPosVie(int nbVies)` / `void VoyageInit(...)` / `void VoyageStep()` / `void VoyageDraw()` | Item-collection "Voyage" flight-arc animation lifecycle. |

### Sound

| Signature | Purpose |
|---|---|
| `SoundChannel SoundEnviron(SoundChannel, int obstacle)` | Maps a generic sound to a surface-appropriate variant. |
| `void PlaySound(SoundChannel, TinyPoint pos)` | One-shot sound with stereo panning from position. |
| `void StopSound(SoundChannel)` (private overload) | Stops one specific looping channel. |
| `void AdaptMotorVehicleSound()` | Switches vehicle motor sound pitch by speed threshold. |
| `void PosSound(TinyPoint)` | Updates panning of all active looping sounds. |

### Region/music (both private — no public exposure except `GetRegionDebug`)

| Signature | Purpose |
|---|---|
| `int GetRegion()` / `void SetRegion(int)` | Region index accessors. |
| `int GetMusic()` / `void SetMusic(int)` | Music track index accessors. |

### Save/load internals

| Signature | Purpose |
|---|---|
| `bool Delete(int gamer, int rank, bool bUser)` | Deletes a level save file. |
| `bool FileExist(int gamer, int rank, bool bUser)` | Tests whether a level save file exists. |

## A note on declaration order

`Decor.hpp`'s `public`/`private` sections are not grouped by concern — they interleave freely (a
`private:` block for `MoveObjectCopy` sits between two `public:` sections near the top; the
`MODERN`-only debug getters sit inline, mid-class, right after `AdaptDoors`). This chapter's
groupings are this book's own organization for reference purposes; they do not reflect section
boundaries in the source file itself, which reads as a fairly flat, chronological accumulation of
methods in roughly the order features were ported rather than a deliberately curated public API
surface.

## See also

- [Chapter 15 — Decor: Overview](ch15-decor-overview.md)
- [Chapter 16 — The Tile Map](ch16-tile-map.md)
- [Chapter 17 — Blupi: the State Machine](ch17-blupi-state-machine.md)
- [Chapter 18 — Blupi Actions and Animation](ch18-blupi-actions-and-animation.md)
- [Chapter 19 — Moving Objects and Decor Actions](ch19-moving-objects-and-decor-actions.md)
- [Chapter 20 — Enemy and Creature AI](ch20-enemy-and-creature-ai.md)
- [Chapter 21 — Physics and Collision](ch21-physics-and-collision.md)
- [Chapter 22 — Doors, Keys, DoorKeyFlags](ch22-doors-keys-doorkeyflags.md)
- [Chapter 23 — Secret Powers and the Cheat System](ch23-secret-powers-and-cheat-system.md)
- [Chapter 24 — Missions and ContinueMission](ch24-missions-and-continuemission.md)
- [Chapter 25 — Game Speed and Zoom](ch25-game-speed-and-zoom.md)
- [Chapter 26 — Tile and Icon Catalog](ch26-tile-and-icon-catalog.md)
- [Appendix A — Class and File Catalog](../appendices/appendix-a-class-and-file-catalog.md)
