# PHASE 28 REPORT — Source Runtime Semantics Recovery

Branch: `260831-feat-phase28-runtime-semantics` · Baseline: Phase 27 HEAD `452c8620`
Date: 2026-08-31

Phase 28 performs a rigorous, source-driven recovery of the remaining gameplay
semantics required for true 1:1 Android-native parity, continuing from the
committed Phase 27 baseline. The guiding rule is unchanged: **every behavior is
proven from the original source/data or left UNKNOWN / MISSING / PARTIAL /
BLOCKED.** No conventional MMORPG behavior is substituted for an unproven
semantic, and the gameplay runtime stays 100% native Android.

## 1. Scope and priorities

| # | Priority | Result |
|---|---|---|
| 1 | Player spawn | UNKNOWN (fail-closed) — reaffirmed with new char-gen negative evidence |
| 2 | Input/action semantics | UNKNOWN (fail-closed) — OptionSet binary, key→action is client-code |
| 3 | Movement semantics | UNKNOWN (fail-closed) — no speed table anywhere |
| 4 | Camera semantics | PARTIAL — three modes PROVEN by name; numeric parameters UNKNOWN |
| 5 | Player state transitions | PROVEN at animation level (attack/damage/die/down/wakeup); combat triggers MISSING |
| 6 | Animation ↔ entity state wiring | Extended: `AnimState` now models the proven DOWN + WAKEUP states |
| 7 | NPC/monster runtime behavior | Data-driven entities PROVEN; AI behavior UNKNOWN (server-side) |
| 8 | Dead/duplicate/WebView/Capacitor removal | Audited; Android runtime is 100% native; no gameplay runtime code removed (none present) |

## 2. Corpus searched this phase

| Source | Used for |
|---|---|
| `Data.pk2` (3.35 GB) | 4,691 `.ban` animation clips — the client's shipped animation-state vocabulary |
| `Media.pk2` (823 MB) | `characterdata_5000.txt` (player templates), `characterdata_25000.txt` (Jangan catalog) |
| `SRO_VT_SHARD.Bak` | Phase 27 `_AddNewChar` facts (reused) |
| Committed android assets | `bandit/anims.tsv` (single decoded animation set), `skilldata.tsv`, `npcpos.tsv` |
| Repository source tree | Native-runtime audit (no WebView/Capacitor/browser in `android/`) |

## 3. Priority 1 — Player spawn: UNKNOWN, reaffirmed (fail-closed)

Phase 27 proved the start region/position is **caller-supplied** to `_AddNewChar`
(the GameServer C++ layer decides it; the DB defines no default). Phase 28 adds a
stronger negative: the per-region character-generation tables carry **no position
column**.

- `characterdata_25000.txt` (Jangan) is a 3,736-row entity catalog with 120
  distinct BSR mesh paths and **no position data** (`has_position_column: false`).
- `characterdata_5000.txt` holds the 13 player class templates
  (`CHAR_CH_MAN_ADVENTURER` … `CHAR_CH_MAN_WARRIOR`, refid 1907–1919) → BSR,
  again with no spawn coordinates.

> Conclusion: player spawn location remains **UNKNOWN (fail-closed)**.
> `PlayerSpawn.unknown()` is the only constructible spawn.

## 4. Priority 2 — Input: UNKNOWN (fail-closed)

No new source was recovered. The client's key→action mapping lives in
`SROptionSet.dat` (681-byte binary, repeating id/value records) whose action-id
semantics require the client executable. `InputController` remains a gesture
accumulator, not an SRO key map.

## 5. Priority 3 — Movement: UNKNOWN (fail-closed)

No speed/acceleration/turn-rate table exists in any searched archive. Phase 26's
negative proof stands. `PlayerMover`/`PlayerMovementConfig` remain fail-closed
(`UNKNOWN_SPEED`).

## 6. Priority 4 — Camera: PARTIAL

Three modes are PROVEN by name (`FREE` / `THIRD_PERSON` / `QUARTER_VIEW` from
`ifoption_camera.txt`), with a camera-data debug window and `/zoom` `/camera`
`/setfov` commands. Numeric camera parameters (distance, FOV, angle limits,
follow offset, interpolation) are client-code — **UNKNOWN**. `Camera2D` is a
generic 2D viewport clamp, not authentic SRO camera math.

## 7. Priority 5 — Player state transitions

The `Data.pk2` `.ban` corpus proves the client's shipped animation states:

| Action | Count | Action | Count |
|---|---|---|---|
| attack | 925 | down | 131 |
| stand | 504 | up | 96 |
| damage | 358 | ready | 79 |
| die | 343 | wait | 67 |
| rm (die-remove) | 277 | loop (die-loop) | 61 |
| run | 273 | downdie | 35 |
| walk | 248 | downdamage | 33 |
| downwait | 30 | downup | 19 |
| wakeup | 17 | sit* / pickup / stun / blocking | ~20 |

The player (`chinaman_*`, 74 clips) additionally ships `standbattle`, `standcity`,
`walkforward`, `runforward`, `walkbackward`, `runforward_sword`, `sitstand`/
`sitbreath`/`sitground`, `blocking`, `stun`, `handhook*`/`handstraight*` (attack
combos), `magicass*` (magic), `down`/`downwait`/`downdamage`/`downdie`/`wakeup`,
and `reborn`.

> ATTACK / DAMAGE / DEATH are therefore **PROVEN at the animation level** — the
> clips exist. What is MISSING is the *combat state machine* that triggers them:
> damage formulas, attack cadence and cooldowns live server-side and are absent
> from the corpus. `PlayerController` deliberately never drives these states.

## 8. Priority 6 — Animation ↔ entity state wiring (implementation)

The single decoded animation set (committed `bandit/anims.tsv`) resolves to 16
clips: `stand01/02, walk, run, attack01/02/03, damage01/02, die, die_loop, down,
downwait, downdamage, wakeup, downdie`. The prior `AnimState` enum modeled only 6
of the proven states and silently dropped the `down`/`wakeup` family.

Phase 28 extends the wiring with **source-proven** states:

- `AnimState.DOWN` (knockdown) — proven by `down`/`downwait`/`downup`.
- `AnimState.WAKEUP` (recovery) — proven by `wakeup`/`up`.
- `AnimStateResolver` now maps word-start `down` → DOWN and `wakeup` → WAKEUP,
  keeping the same fail-closed word-boundary discipline (the down-family clips
  `downdamage`/`downdie`/`downwait` group under DOWN; the canonical `down` clip
  wins).
- `CharacterAnimator` documents that DOWN/WAKEUP transition order is UNKNOWN and
  the runtime never drives them; no transition logic is invented.

The full bandit manifest now resolves to **8 proven states**
(IDLE, WALK, RUN, ATTACK, DAMAGE, DEATH, DOWN, WAKEUP).

## 9. Priority 7 — NPC/monster runtime behavior

Entities are **data-driven and PROVEN**: `npcpos.tsv` (spawn positions) +
`characterdata_25000.txt` (region catalog, 120 distinct meshes) +
`characterdata_5000.txt` (player templates). Runtime *behavior* (aggro,
pathfinding, combat AI) is server-side and **UNKNOWN**.

## 10. Priority 8 — Native Android requirement + dead-code audit

- The Android gameplay runtime (`android/app/src/main/java/.../game|world|data`)
  contains **no** WebView, Capacitor, browser, HTML/JS, or `loadUrl` path. It is
  100% native Java. `GameActivity` is a plain native `Activity`.
- The retired Capacitor/WebView wrapper was already relocated (Phase 22) to
  `legacy/capacitor/` as a reference; it is **not** compiled into the app and is
  not a runtime path.
- `map/` is a **separate web project** (the OpenLayers map tool). Its
  `map/src/game/` TypeScript game prototype (wired via `initGameFlow` in
  `map/src/main.ts`) is browser code but is **not part of the Android runtime**;
  it is classified DEAD/obsolete in the matrix and was left untouched (removing
  it is out of the Android-runtime scope and it is not proven safe to delete).
- `skilldata.tsv` is an unparsed 7-line source-file list (no skill semantics) —
  recorded as UNKNOWN, not deleted (it documents which source files exist).
- No hardcoded demo character or fake movement/fake animation transition was
  found in the Android runtime: the committed `"player"` identity key is
  explicitly fail-closed (not a `npcpos` refid), and `PlayerMover` refuses to
  move without a proven speed.

No files were deleted; nothing merited deletion under the "only remove proven
dead/duplicate/obsolete code" rule.

## 11. Matrix

`PHASE_28_SOURCE_RUNTIME_MATRIX.tsv` records 27 subsystems with columns
`Subsystem / Original evidence / Exact semantics / Android implementation /
Status / Test / Evidence path / Remaining unknowns`, using only the allowed
statuses. Summary by status: PROVEN 12, PARTIAL 4, UNKNOWN 7, MISSING 1, DEAD 2.

## 12. Verification

`scripts/build_phase28_evidence.py` regenerates
`scripts/testdata/formats/phase28_source_evidence.json` from `Data.pk2`,
`Media.pk2` and the committed assets. New/changed tests:

- `AnimStateResolverTest` — 3 new tests (DOWN/WAKEUP resolution, down-family
  grouping, full bandit manifest → 8 states).
- `Phase28SourceEvidenceTest` — 6 new evidence tests (animation vocabulary,
  player templates, Jangan char-gen, bandit clip set, skill stub, native audit).
- `CharacterRuntimeDataTest` — extended the `AnimState → keyword` mapping for the
  two new states.

Bounded real-JUnit verification (Phase 28 harness, real JUnit 4.13.2):

```
OK (148 tests)   # 139 baseline + 9 Phase 28 tests
```

ANDROID RUNTIME: **NOT EXECUTED** — no Android SDK/Gradle/emulator/device run was
performed; no APK/device test is claimed.

## 13. The 12-question gate

1. **Is player spawn PROVEN?** No. UNKNOWN (fail-closed). `_AddNewChar` takes the
   start region/position from the GameServer caller; no default or table exists.
2. **Is input PROVEN?** No. The key→action mapping is client-code; `SROptionSet.dat`
   is a 681-byte binary without self-describing action ids.
3. **Is movement PROVEN?** No. No speed/acceleration table exists anywhere.
4. **Is camera behavior PROVEN?** Partially. Three modes are proven by name;
   numeric parameters and follow/interpolation are UNKNOWN.
5. **Is animation/state selection PROVEN?** Partially. The state vocabulary and
   clip resolution are proven (now including DOWN/WAKEUP); the transition order
   and combat triggers are UNKNOWN/MISSING.
6. **Are NPC/monster entities data-driven?** Yes. `npcpos.tsv` + per-region
   char-gen tables drive entities; no hardcoded demo characters.
7. **Are multiple entities independently simulated?** Yes (Phase 26): each entity
   keeps its own animation clock; `PlayerController` advances only the player.
8. **Is gameplay 100% native Android?** Yes. No WebView/Capacitor/browser/JS
   gameplay path exists in the Android runtime.
9. **Does any WebView/Capacitor/browser gameplay path remain?** In the Android
   runtime: no. A separate web project (`map/`, including `map/src/game/`) still
   carries a TS browser prototype, but it is not the Android runtime.
10. **What exact UNKNOWN/MISSING/BLOCKED items remain?** Player spawn position;
    input key→action mapping; walk/run speed & acceleration; camera numeric
    parameters & interpolation; down→downwait→wakeup→idle transition order; the
    combat state machine (damage/attack cadence/cooldowns); NPC AI (aggro/path);
    skill effect/cast-time/cooldown semantics.
11. **What source evidence is still unavailable?** The client C++ executable
    (GameClient.exe behavior), the GameServer/GameWorld C++ server binaries, and
    the parsed `_RefSkill`/skill data (only a 7-file stub is committed).
12. **What is the highest-priority blocker to true 1:1 parity?** The absent
    server/client executable code: movement speed, camera parameters, and the
    combat/state transition logic all live in binaries not present in this
    corpus, so those semantics cannot be proven and must stay fail-closed.

## 14. Reproducing

```bash
# 1) Regenerate evidence (needs Data.pk2 + Media.pk2 under /tmp/opencode/pk2raw/)
python3 scripts/build_phase28_evidence.py

# 2) Compile + run the pure-JVM suite with real JUnit 4.13.2
#    (harness: /tmp/opencode/ph28build/phase28_build_and_run.sh)
#    Expect: OK (148 tests)
```

## 15. Commit

```
feat(android): Phase 28 source runtime semantics recovery

- .ban corpus (Data.pk2, 4691 clips) proves the animation state vocabulary
  (attack/damage/die/down/wakeup/...); player chinaman action names recovered
- player class templates (characterdata_5000, 13 CHAR_CH_MAN_* -> bsr) + Jangan
  region char-gen catalog (120 bsr, no positions) recovered
- skilldata.tsv is an unparsed 7-file stub -> skill semantics UNVERIFIED
- AnimState + AnimStateResolver extended with proven DOWN (knockdown) + WAKEUP
  (recovery) states; bandit manifest now resolves 8 states
- native runtime audit: Android gameplay is 100% native; no WebView/Capacitor;
  legacy wrapper in legacy/capacitor/; map/ web prototype separate (DEAD)
- phase28_source_evidence.json + builder; Phase28SourceEvidenceTest (6 tests) +
  3 new AnimStateResolverTest cases
- PHASE_28_SOURCE_RUNTIME_MATRIX.tsv (27 subsystems)
- 148 JVM tests PASS / 0 FAIL; ANDROID RUNTIME: NOT EXECUTED
```
