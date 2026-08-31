# PHASE 23 REPORT — Data-Driven Character Runtime (Task Phase: F, A–E)

Branch: `260831-feat-phase23-character-animation` · Baseline: Phase 23 increment 2 `9331def425a8b83c728aa56a73b96d9c6f30f2ce`
Date: 2026-08-31

This task phase continues the verified increment-2 checkpoint on the same
branch. It fixes a skinning defect and locks the character/NPC runtime to the
REAL committed data with bounded, runnable tests. Nothing is invented: every
state, duration, refid, spawn count, and classification below is read from the
committed assets under `android/app/src/main/assets/game/world/characters/` and
`android/app/src/main/assets/game/textdata/npcpos.tsv`.

---

## 1. Scope, baseline, and deliverables

Baseline (verified before this phase): commit `9331def4`, pushed,
local==remote==HEAD, clean tree, 42 JVM tests green (increment 2) with one
pre-existing red test (`CharacterMeshIndexTest#skinnedBindPositions…`).

Deliverables of this phase:

| Task | Deliverable |
|---|---|
| F | Fix animated/bind skinning to the PROVEN inverse-bind semantics (`A·B⁻¹`) |
| A | Word-start state resolution (bug fix) + real-clip data-driven runtime tests |
| B | Structural chain tests: refid → key → manifest → shared → runtime state |
| C | Player identity trace (evidence only; no wiring) |
| D | NPC → spawn linkage over real `index.tsv` + `npcpos.tsv` |
| E | Movement/combat evidence report (proven subset only) |

## 2. Verification methodology

Pure-JVM harness under `/tmp/opencode/phase23/`: custom `JUnitRunner` + real
`org.junit.Assert` (`junitreal`), Android stubs (`AssetManager`/`Bitmap`/
`BitmapFactory`), JDK 17 (`/usr/bin/javac`, `/usr/bin/java`). Every run is from
`/workspace/android/app` with bounded timeouts. 69 tests PASS, 0 FAIL (see §9).

## 3. TASK F — inverse-bind skinning (IMPLEMENTED PROVEN)

Root cause of the pre-existing red test: the Java port never applied the
inverse-bind step. Raw skinned meshes ARE stored in bind pose, and the proven
LB-skin formula (Phase 19 Part I, `scripts/bms_to_asset.py` line 210) is
`sum w_i * A_i * B_i⁻¹ * v_rest` where `B_i⁻¹` is the inverse of the committed
`bind_world_rot/pos` (numerically EXACTLY the BSK `rot_local/tr_local`,
verified on Bip01/Pelvis/LUpperArm/RFinger21/LToe0/Head/RHand against
`scripts/testdata/formats/bsk_samples/bandit.bsk`).

Changes:
- `CharacterMeshIndex.skinnedBindPositions` now validates mesh bones
  fail-closed against the skeleton, then returns the stored rest vertices
  (`mesh.positions.clone()`): at the bind pose the transform is identity.
- `CharacterRenderer.skin` now composes `A_i · B_i⁻¹` (conjugate quaternion +
  `-R⁻¹·t`), with the 255-sentinel weight handling preserved.
- The flawed tests (`swordSkinnedPositionsMatchSingleBoneTransform` used the
  old tautological formula) were replaced by rest-vertex assertions; a new
  `skinAtBindPoseReproducesRestVertices` proves the FULL renderer path equals
  the raw committed part1 vertices (`214·3` positions, tol `1e-3`).

Evidence: raw bandit bounds (sword X=[-13.40,-8.53]; part1 X=[-11.53,11.53]
symmetric Y=[10.86,12.68]; part2 X=[-4.60,4.60] Y=[0.02,14.67]) are reproduced
identically by both paths.

## 4. TASK A — word-start resolution + real-clip runtime tests (IMPLEMENTED PROVEN)

### 4.1 Bug found by data: substring keyword false positives
The increment-2 `AnimStateResolver` matched keywords with `contains()`. Against
the real clip names this fabricated states:
- `die` inside `soldier`/`bonesoldier`/`tombsoldier` → a spurious DEATH state on
  52 characters (e.g. `soldierearthghost_stand02` resolved DEATH);
- `run` inside `trunk`/`union` → a spurious RUN state on
  `res_mob_oasis_deserttrunkz` and `res_npc_npc_easteuropesystem_hunterunion`;
- shadowing: `res_mob_qinshi_tombsoldier` and `res_mob_god_flame_giant`
  resolved DEATH to `tombsoldier_stand01` INSTEAD of their real `tombsoldier_die`.

### 4.2 Fix (word-start matching)
A keyword now matches only at a word start: the preceding character is not
`[a-z0-9]` (or it is the string start), via `AnimStateResolver.keywordMatch`.
Real player clips keep matching (`standbattle`, `standcity`, `walkforward`,
`runforward_sword`) while `soldier`/`trunkz`/`union` no longer do. Enumerated
totals are unchanged (473 manifests / 3,689 clips / 1 zero-anim / 309 idle),
proving the fix removes ONLY spurious states.

### 4.3 Real-clip runtime tests (`CharacterRuntimeDataTest`, 5 tests)
- `res_mob_china_bandit` resolves all six states with REAL names/durations
  (`bandit_stand01` 2000, `bandit_walk` 1333, `bandit_run` 833,
  `bandit_attack01` 1133, `bandit_damage01` 366, `bandit_die` 2666).
- `res_npc_npc_arabia_smith` is idle-only (`arabia_smith_stand01` 12500);
  `res_mob_arabia_mustafa` has 5 states (no damage); the `player` manifest
  resolves IDLE/WALK/RUN only.
- Corpus-wide: for every resolved state across all 473 manifests, the clip name
  word-starts its keyword.
- Two `CharacterAnimator` instances from the SAME bandit model advance
  independent clocks (2.5 s idle wraps to 500 ms in one; the other stays 0).
- Bandit `ATTACK` returns to idle using the real 1133 ms duration.

## 5. TASK B — structural chain + classification (IMPLEMENTED PROVEN)

`CharacterChainTest` (6 tests) locks the full chain over real data:
- `CharacterCatalog` parses 1,094 `index.tsv` rows; `keyFor` maps
  14926→`res_mob_asiam_crab`, 43905→`res_mob_arabia_karkadann`,
  19553→`res_artifact_guild_pulley_gate_pulley`, 36033→
  `res_dun_property_com_property_recall`, 36031→`res_quest_ins_quest_teleport`;
  unknown refid → null.
- Row/status audit: 1,078 PROVEN / 15 UNKNOWN / 1 PARTIAL rows; 472 distinct
  PROVEN keys (the 473rd manifest is `player`, never spawned).
- Every PROVEN key has a manifest and every referenced shared file exists
  (skeleton/mesh/texture/animation); the `player` manifest's 38 refs commit.
- PARTIAL + UNKNOWN keys have NO manifest (fail-closed, not runtime-loadable).
- Classification evidence:
  - `res_mob_arabia_karkadann` (refid 43905) PARTIAL: conversion failed, only
    its shared skeleton `prim_skel_mob_arabia_karkadann.json` + one mesh are
    committed; zero committed anim clips → cannot animate → PARTIAL.
  - 3 UNKNOWN artifacts (gate pulley / property recall / quest teleport): no
    `.bsk`, zero committed assets, not characters.

## 6. TASK C — player identity trace (INVESTIGATED UNKNOWN / PARTIAL)

`PlayerModelTest` (3 tests) proves what IS known at file level:
- `player/manifest.json` is committed with 5 anims + 16 skinned meshes; all 38
  referenced shared files exist.
- The committed `chinaman_skel` parses to 38 bones (`xyzw`, root `Bip01`);
  resolved states are IDLE/WALK/RUN only (no combat/death clips in the manifest).

NOT wired (evidence only):
- PARTIAL model identity: the original `chinaman_fighter.bsr` references
  `europeman_skel` (43 bones), not the committed `chinaman_skel`.
- UNKNOWN player spawn: `npcpos` is NPC-only; no static player spawn exists
  anywhere in the archives. The player is never spawned by the runtime.

## 7. TASK D — NPC → spawn linkage (IMPLEMENTED PROVEN)

`NpcCharacterLinkageTest` (2 tests) proves the bounded data-driven split the
renderer uses (`NativeWorldRenderer`: refid → catalog key → loaded model; a
null model stays a marker, never drawn):
- 14,800 world spawns split as **10,147 renderable** (refid → PROVEN key with a
  committed manifest) and **4,653 skipped**.
- Every renderable key is a distinct PROVEN character; every skipped spawn's
  refid is UNKNOWN, PARTIAL (karkadann 43905), or absent from the index
  (80 refids, e.g. 1934/1936/2098).
- Spot checks: karkadann world spawns 11 (skipped), pulley 19553 = 1 (skipped),
  property_recall 36033 = 52 (skipped), crab 14926 = 65 (renderable).

## 8. TASK E — movement/combat evidence (BLOCKED BY MISSING SOURCE)

Movement and combat semantics are NOT provable from the available original
source (compiled EXEs/DLLs only; unopened SQL `.Bak`; no `CharacterData`/
`SkillData` parsed into runtime tables). `PHASE_21_SOURCE_PARITY_AUDIT` lists
attack/move speed as F — MISSING (no source values). The ONLY implemented
subset is the animation-state machine driven by real clip names/durations
(§4); the real WALK/RUN clip durations (e.g. bandit walk 1333 ms / run 833 ms)
are the only timing anchors available and are NOT treated as movement speeds.
No movement speed, no combat timing/damage, no AI is implemented or invented.

## 9. JVM test matrix (all PASS, JDK 17, bounded timeouts)

| Test class | Count |
|---|---|
| `AnimationPlayerTest` | 10 |
| `IdleAnimResolverTest` | 5 |
| `AnimStateResolverTest` | 10 |
| `CharacterAnimatorTest` | 8 |
| `CharacterRuntimeDataTest` (TASK A) | 5 |
| `CharacterManifestEnumerationTest` | 3 |
| `CharacterMeshIndexTest` (incl. new bind-pose/inverse-bind) | 7 |
| `CharacterMeshIndexMultiTest` | 3 |
| `CharacterChainTest` (TASK B) | 6 |
| `PlayerModelTest` (TASK C) | 3 |
| `NpcCharacterLinkageTest` (TASK D) | 2 |
| `CharacterCatalogTest` | 3 |
| `NpcSpawnIndexTest` | 4 |
| **TOTAL** | **69** |

Regression fixes included: the pre-existing red bind-pose test now passes; the
pre-existing `NpcSpawnIndexTest` compile error (double `Reader` wrap at line 63)
was corrected.

## 10. NOT EXECUTED

- Android APK build, `./gradlew test`, instrumented/device tests: no Android
  SDK/Gradle/emulator in this environment.
- Android-bound classes (`NativeWorldRenderer`, `CharacterEntity`,
  `GameActivity`) compiled against Android stubs only; no device claim.

## 11. Blockers / unknowns

- No Android toolchain → APK/device verification NOT EXECUTED.
- Original gameplay source baseline unavailable → movement/combat semantics
  remain UNKNOWN (TASK E); nothing invented.
- 3 UNKNOWN artifact keys + PARTIAL karkadann keep their fail-closed
  classification until the original `.Bak`/data is parsed.
- Player identity/spawn UNKNOWN; `europeman_skel` vs `chinaman_skel` mismatch
  documented as PARTIAL.

## 12. Next steps

- Parse original `CharacterData`/`SkillData` `.txt` (or the SQL `.Bak`) into
  runtime tables to prove movement/combat values before implementing them.
- Resolve karkadann's mesh conversion failure to promote it from PARTIAL.
- APK build + instrumented verification once an Android SDK is available.

---

## Classification matrix (5-way)

| Item | Classification |
|---|---|
| Inverse-bind skinning (`CharacterRenderer.skin`, `skinnedBindPositions`) | IMPLEMENTED PROVEN |
| Word-start state resolution + real-clip runtime tests | IMPLEMENTED PROVEN |
| refid→key→manifest→shared→runtime chain + classification | IMPLEMENTED PROVEN |
| NPC→spawn linkage (renderable/skipped split) | IMPLEMENTED PROVEN |
| Player model file-level chain | IMPLEMENTED PARTIAL |
| Player identity (BSR→skeleton mismatch) | INVESTIGATED UNKNOWN |
| Player spawn coordinates | INVESTIGATED UNKNOWN |
| karkadann runtime model (no manifest/anims) | INVESTIGATED PARTIAL |
| 3 UNKNOWN artifact keys | INVESTIGATED UNKNOWN |
| Movement speed / combat timing / damage / AI | BLOCKED BY MISSING SOURCE |
| APK build / instrumented / device run | NOT EXECUTED |
