# Appendix E: Cheat Code Reference

This appendix cross-verifies `documentation/Cheat System.md` (`mobile-eggbert`'s own developer
doc) against the real implementation: `Decor::CheatAction(Tables::CheatCodes)`
(`src/WindowsPhoneSpeedyBlupi/Decor.cpp:1774`–`2096`), `Game1::CheatAction(Def::ButtonGlyph)`
(`Game1.cpp:491`–`523`), the typed-cheat-name table in `InputPad.cpp` (~line 715), and the
`Tables::CheatCodes` enum (`Tables.hpp:79`). See also
[Appendix B, §15](appendix-b-enum-catalog.md#15-tablescheatcodes--cheat-identifiers-22-base--up-to-5-build-gated)
for the enum itself and
[Chapter 23](../part04-decor-simulation/ch23-secret-powers-and-cheat-system.md) for narrative
coverage.

**Headline finding: the documentation is accurate everywhere it makes a claim, but two cheat
codes that exist in the enum and are dispatchable are silently no-ops in the real code** — see
"Discrepancies" at the end of this appendix.

## Architecture in three parts

`Cheat System.md` frames the system as three cooperating parts, and reading the source confirms
the split is real and matches the file boundaries:

1. **Input handling** — `InputPad.cpp` polls hardware and, in MODERN builds, also accumulates a
   32-character rolling buffer of typed letters (`typedCheatBuffer`) checked against a table of
   known cheat-name strings after every keystroke (§4 below).
2. **UI triggers** — `Game1.hpp`'s ten-button `cheatGeste` unlock sequence (§1) and the nine
   `Cheat1`–`Cheat9` grid buttons (§2), both routed through `Def::ButtonGlyph`.
3. **Gameplay effects** — `Decor::CheatAction(Tables::CheatCodes)` (§3), the single function that
   actually mutates gameplay state (`m_blupi*` fields, `MoveObject` pools, doors) for the 20 of 22
   base cheat codes that are wired up correctly.

The `Tables::CheatCodes` enum (declared in `Tables.hpp`, not in `Decor.hpp` or `Game1.hpp`) is the
shared vocabulary that lets all three parts refer to the same cheat by a stable symbolic name
rather than a magic number — but, as §5 documents, sharing a vocabulary does not guarantee every
listed word is actually implemented.

## 1. Cheat-menu unlock gesture

The cheat menu is hidden by default. Per `Game1.hpp:109-126` (`cheatGesteLength = 10`,
`cheatGeste[]`) and confirmed by `Game1.cpp:369-386` (`cheatGesteIndex` advances on a correct
match, resets to 0 on any wrong button), the player must tap these ten `ButtonGlyph` values in
exact order:

```
Cheat12, Cheat22, Cheat32, Cheat12, Cheat11, Cheat21, Cheat22, Cheat21, Cheat31, Cheat32
```

*From `Game1.cpp:369`:*
```cpp
if (buttonPressed == cheatGeste[cheatGesteIndex])
{
    cheatGesteIndex++;
    if (cheatGesteIndex == cheatGesteLength)
    {
        ...   // showCheatMenu = true
    }
}
else
{
    cheatGesteIndex = 0;
}
```

This matches `Cheat System.md`'s documented sequence exactly, including the effect
(`showCheatMenu = true`).

## 2. UI cheat buttons (Cheat1–Cheat9)

`Game1::CheatAction(Def::ButtonGlyph)` (`Game1.cpp:491-523`) maps nine buttons to nine effects.
`Decor::GetCheatTinyText()` (`Decor.cpp:1737-1761`) supplies the single-letter label drawn on each
button.

| Button | Tiny-text label | Dispatches | Real effect |
|---|---|---|---|
| `Cheat1` | `D` | `decor.CheatAction(CheatCodes::OpenDoors)` | Toggles `m_bCheatDoors`; re-adapts door tiles |
| `Cheat2` | `B` | `decor.CheatAction(CheatCodes::SuperBlupi)` | Toggles `m_bSuperBlupi` |
| `Cheat3` | `S` | `decor.CheatAction(CheatCodes::ShowSecret)` | Toggles `m_bDrawSecret` |
| `Cheat4` | `E` | `decor.CheatAction(CheatCodes::LayEgg)` | Sets `m_nbVies = 9` |
| `Cheat5` | `R` | `gameData.Reset()` (called directly — **bypasses `Decor::CheatAction` entirely**) | Resets all save data |
| `Cheat6` | `T` | `simulateTrialMode = !simulateTrialMode` (also bypasses `Decor::CheatAction`) | Toggles trial-mode simulation |
| `Cheat7` | `C` | `decor.CheatAction(CheatCodes::CleanAll)` | Converts every enemy/hazard object into an explosion |
| `Cheat8` | `T` | `decor.CheatAction(CheatCodes::AllTreasure)` | Collects every remaining treasure instantly |
| `Cheat9` | `G` | `decor.CheatAction(CheatCodes::EndGoal)` | Triggers the level-win sequence |

This exactly matches `Cheat System.md`'s "UI Cheats (Cheat1–Cheat9)" table. One detail the doc
does not mention but the code shows clearly: `Cheat5` (Reset) and `Cheat6` (TrialMode) are handled
as inline `Game1` logic (`gameData.Reset()`, flipping `simulateTrialMode`) rather than by calling
into `Decor::CheatAction()` at all — they have no corresponding `Tables::CheatCodes` enumerator.

## 3. Full `CheatCodes` reference table

Cross-verified line-by-line against `Decor::CheatAction()`'s real `if` chain
(`Decor.cpp:1776`–`2095`). "Typed name" is the lowercase string `InputPad.cpp`'s
`cheatEntries[]` table matches against the trailing characters of the player's typed-letter
buffer (MODERN builds only — see §4).

| `CheatCodes` value | Typed name | Real effect (from `Decor::CheatAction`) | Source |
|---|---|---|---|
| `OpenDoors` | `opendoors` | Toggles `m_bCheatDoors`; calls `AdaptDoors(m_bPrivate)` to re-evaluate every door tile | `Decor.cpp:1776-1780` |
| `ShowSecret` | `showsecret` | Toggles `m_bDrawSecret` (reveals hidden/secret paths) | `Decor.cpp:1781-1784` |
| `SuperBlupi` | `megablupi` | Toggles `m_bSuperBlupi` | `Decor.cpp:1785-1788` |
| `LayEgg` | `layegg` | Sets `m_nbVies = 9` (does **not** place an egg object despite the name — see Discrepancies) | `Decor.cpp:1789-1792` |
| `CleanAll` | `cleanall` | Converts every enemy-type `MoveObject` (types 2,3,4,16,17,20,32,33,44,54,96,97) into an `ObjectType8` explosion, offsets it by (−34,−34), triggers `DecorAction::SmallShake`, plays `SoundChannel10` | `Decor.cpp:1793-1823` |
| `Skate` | `funskate` | Clears all other vehicle/mode flags, sets `m_blupiSkate = true`, stops motor-loop sounds (channels 16/18/29/31) | `Decor.cpp:1824-1840` |
| `Copter` | `givecopter` | Clears other flags, sets `m_blupiHelico = true` | `Decor.cpp:1841-1853` |
| `Jeep` | `jeepdrive` | Clears other flags (incl. `m_blupiCloud`/`m_blupiHide`), sets `m_blupiJeep = true` | `Decor.cpp:1854-1868` |
| `AllTreasure` | `alltreasure` | For every `ObjectType5` (treasure): removes it, increments `m_nbTresor`, calls `OpenDoorsTresor()`, plays `SoundChannel11` | `Decor.cpp:1869-1881` |
| `EndGoal` | `endgoal` | For every goal object (`ObjectType7`/`21`): if all treasure collected, plays the win sound/animation (`BlupiAction::Win`, clears every mode flag); otherwise plays a "not yet" sound | `Decor.cpp:1882-1930` |
| `RoundShield` | `roundshield` | Sets `m_blupiShield = true`, `m_blupiTimeShield = 100`, clears `Power`/`Cloud`/`Hide`, plays `SoundChannel42` | `Decor.cpp:1931-1941` |
| `Lollipop` | `quicklollypop` | Sets `BlupiAction::Sucette`, clears vehicle/power flags, plays `SoundChannel50` | `Decor.cpp:1942-1957` |
| `Bombs` | `tenbombs` | Sets `m_blupiPerso = 10`, plays `SoundChannel60` | `Decor.cpp:1958-1962` |
| `BirdLime` | `birdlime` | Sets `m_blupiBullet = 10` | `Decor.cpp:1963-1966` |
| `Tank` | `drivetank` | Clears other flags, sets `m_blupiTank = true`; at non-20-FPS also zeroes vertical sub-pixel velocity | `Decor.cpp:1967-1986` |
| `PowerCharge` | `powercharge` | Sets `BlupiAction::Charge`, clears vehicle/power flags, plays `SoundChannel58` | `Decor.cpp:1987-2003` |
| `Drink` | `hidedrink` | Sets `BlupiAction::Drink`, clears vehicle/power flags, plays `SoundChannel57` | `Decor.cpp:2004-2020` |
| `Overcraft` | `iovercraft` | Clears other flags, sets `m_blupiOver = true` | `Decor.cpp:2021-2033` |
| `Dynamite` | `udynamite` | Sets `m_blupiDynamite = 1`, plays `SoundChannel60` | `Decor.cpp:2034-2038` |
| `WeelKeys` | `weelkeys` | `m_blupiCle = m_blupiCle \| DoorKeyFlags::All` (grants all three keys) | `Decor.cpp:2039-2042` |
| `Ghost` *(MODERN)* | `ghost` | Toggles `m_blupiGhost`; on enable, clears all vehicle flags and velocity, forces `BlupiAction::Stop`; on disable, re-validates ground contact via `DecorDetect` | `Decor.cpp:2043-2081` |
| `BuildOfficialMissions` | `buildofficialmissions` | **No case in `CheatAction()` — silent no-op when triggered by name or by value.** See Discrepancies. | — |
| `KillEgg` | `killegg` | **No case in `CheatAction()` — silent no-op.** See Discrepancies. | — |
| `Quick` *(non-LEGACY)* | `quick` | **Handled entirely in `InputPad.cpp`, not `CheatAction()`**: toggles `quick_cheat_enabled`, which lets `GameSpeed` exceed `Fast` | `InputPad.cpp:754-761` |
| `Debug` *(MODERN)* | `debug` | **Handled in `InputPad.cpp`**: toggles `debug_cheat_enabled` (shows the runtime debug overlay) | `InputPad.cpp:763-766` |
| `Zoom` *(MODERN)* | `zoom` | **Handled in `InputPad.cpp`**: cycles `ZoomCheat::Zoom100 → 50 → 25 → 12 → 100`, calling `decor->SetCheatZoom()` each step | `InputPad.cpp:767-770, 781-814` |
| `Cheats` *(MODERN)* | `cheats` | **Handled in `InputPad.cpp`**: shows the cheats overlay for `5 * Config::CURRENT_FPS` frames | `InputPad.cpp:771-775` |

Every cheat above ends by re-evaluating three shared post-conditions (`Decor.cpp:2082-2095`): the
shield/power/cloud/hide HUD gauge is hidden if none of those states is active, and the
helicopter/overcraft and jeep/tank motor-loop sounds are stopped if none of those modes is active
— a cleanup pass that runs after *every* cheat, not just vehicle ones.

## 4. Typed cheat-code entry (MODERN builds only)

`InputPad.cpp` (~lines 686-838) accumulates typed letter keys into `typedCheatBuffer` (capped at
32 characters) during the `Play` phase and, after every keystroke, checks whether the buffer's
trailing characters match any name in a `cheatEntries[]` table. On match, most entries dispatch
straight to `decor->CheatAction(code)`; `Quick`/`Debug`/`Zoom`/`Cheats` are special-cased and
handled inline in `InputPad.cpp` instead (they toggle `InputPad`-local or `Pixmap`-facing state
rather than `Decor` state — see the "Handled in `InputPad.cpp`" rows above).

Persistent cheats (`opendoors`, `megablupi`, `showsecret`, `quick`, `debug`) are tracked in
`activePersistentCheats` for the (MODERN-only) always-visible cheat-status overlay; non-persistent
cheats are one-shot triggers.

*Cross-check against `Cheat System.md`*: the doc's "Complete List of Cheat Codes" section lists
all 22 base `CheatCodes` enumerators by their **enum names** (`OpenDoors`, `CleanAll`, …), not
their typed-entry strings. The doc is correct as far as it goes, but — as the table in §3 shows —
several typed names differ substantially from what a literal reading of the enum name would
suggest (`SuperBlupi` types as `megablupi`; `Lollipop` types as `quicklollypop`; `Skate` types as
`funskate`; `Copter` as `givecopter`; `Jeep` as `jeepdrive`; `Tank` as `drivetank`; `Bombs` as
`tenbombs`; `Drink` as `hidedrink`; `Overcraft` as `iovercraft`; `Dynamite` as `udynamite`). The
doc's note *"Only a subset of these cheats is exposed through the UI (Cheat1–Cheat9). However, all
of them can be triggered programmatically via `Decor::CheatAction`"* is accurate for 20 of the 22
base codes, but **not fully accurate for `BuildOfficialMissions` and `KillEgg`** — both are
dispatchable (both to `CheatAction()` and, per `Cheat System.md`'s own temporary-hook example, via
direct calls), but neither has any effect once `CheatAction()` receives them.

## 5. Discrepancies between documentation and code

- **`KillEgg` is a silent no-op.** It has a `Tables::CheatCodes` enumerator, a typed-entry mapping
  (`"killegg"`), and is dispatched to `decor->CheatAction(Tables::CheatCodes::KillEgg)` exactly
  like every working cheat — but `Decor::CheatAction()`'s `if`-chain (`Decor.cpp:1776-2081`) has
  no `if (cheat == Tables::CheatCodes::KillEgg)` branch at all. Typing `killegg` in a MODERN build
  compiles, runs, and does nothing. `Cheat System.md` does not flag this; it lists `KillEgg`
  alongside every working cheat with no caveat.
- **`BuildOfficialMissions` is also a silent no-op through `CheatAction()`**, for the same reason
  (no matching `if` branch). A *distinct*, unrelated method — `Decor::SetBuildOfficialMissions(bool)`
  (`Decor.cpp:2098-2101`), which does set the real backing field `m_buildOfficialMissions` — exists
  right next to `CheatAction()` in the source, but a repo-wide search confirms `SetBuildOfficialMissions()`
  is never called from anywhere else in the codebase. The enumerator, the typed name, and the
  setter all exist; nothing wires them together.
- **The doc's "TEMP CHEAT HOOK" sample is correctly labeled as an illustrative how-to, not a
  description of the shipping code — verified by reading the real `Game1::StartMission()`.**
  `Cheat System.md`'s final section, titled "How to add a temporary hook during the start to
  enable cheats," shows a modified `Game1::StartMission()` with a `// TEMP CHEAT HOOK
  (remove later):` loop that calls `decor.CheatAction()` for eleven cheats (`OpenDoors`,
  `SuperBlupi`, `ShowSecret`, `LayEgg`, `AllTreasure`, `RoundShield`, `Bombs`, `BirdLime`, `Tank`,
  `Dynamite`, `WeelKeys`) inserted just before `decor.StartSound()`. The real
  `Game1::StartMission()` (`Game1.cpp:462-484`) has **no such loop and no reference to
  `Tables::CheatCodes` at all** — it is nine plain calls (`decor.Read`, `decor.LoadImages`,
  `decor.SetMission`, …) ending in `decor.StartSound(); inputPad.StartMission(...)`. The doc is
  accurate here: it presents the hook as something a developer could *add* for debugging, not as
  standing behaviour, and the current mission-start path does not silently apply any cheats.
- **The doc is otherwise complete and accurate** for the unlock gesture, the UI Cheat1–9 mapping,
  and the base set of 22 `CheatCodes` names. It does not attempt to document the MODERN-only
  `Ghost`/`Debug`/`Zoom`/`Cheats`/`Quick` cheats or their `InputPad.cpp`-side handling at all — an
  incompleteness rather than an inaccuracy, since those five are gated behind build configurations
  the doc does not discuss.
