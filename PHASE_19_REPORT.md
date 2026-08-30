# PHASE 19 REPORT — Real Character Skinning + BSK Semantics + Animation Playback

Branch: `260830-feat-phase19-real-character-skinning` · Phase 18 baseline: `44a48db`
Date: 2026-08-30

Phase 19 closes the remaining Phase 18 open questions around REAL character
skinning and animation: the BSK transform-field semantics (origin/local/parent),
the skinning-weight normalization truth, and real animation playback. The bandit
NPC (refid 1949) is now rendered **and** animated from original archive bytes
(proven pose chaining + deterministic snapshots), and a Java pose-driven skinning
renderer is committed (compile-checked, device NOT EXECUTED). The player
(chinaman) is honestly reported PARTIAL with a documented BSR->skeleton
mismatch. Nothing is invented; every claim is reproduced from archive bytes and
asserted by hermetic Python tests.

---

## Status vocabulary

- **DONE** — proven from ORIGINAL archive bytes + executed, hermetic tests.
- **PARTIAL** — a proven subset works; the rest is documented with evidence.
- **BLOCKED** — cannot proceed without missing evidence/decoder.
- **UNKNOWN** — no honest claim possible yet.
- **NOT EXECUTED** — not run in this environment (no Gradle/Android SDK/device).

---

## 18-line phase status

| # | Metric | Status |
|---|---|---|
| 1 | **BSK TRANSFORM SEMANTICS** | **DONE** — `rot_origin`/`tr_origin` == the bone WORLD (bind/model-space) transform (byte-exact to `skeleton.json` `bind_world`); `rot_parent`/`tr_parent` == parent-relative local; `rot_local`/`tr_local` == inverse-bind on the ROOT (conjugate pattern). Child-bone inverse is **PARTIAL/UNKNOWN** (local vector-part sign differs from plain conjugate; documented). |
| 2 | **BSK bone_type u8** | **UNKNOWN** — census across all 29,957 bones (1,035 nonzero `.bsk`) = `{0: 29957}` (constant zero). Meaning still not asserted. |
| 3 | **SKELETON HIERARCHY** | **DONE** — every sampled skeleton is a rooted tree (single root `Bip01`, no cycles, no scale fields); max depth < 40. |
| 4 | **BSR PROVEN EDGES** | **DONE** — bandit BSR->BSK (35 bones), BSR->3 bms (skin), BSR->16 ban, BSR->bmt, bms->ddj texture, npc_record->world; all PROVEN byte-exact. 8×u32 header still UNKNOWN. |
| 5 | **SKIN WEIGHT NORMALIZATION** | **DONE** — max 2 influences/vertex, u16 weights, `0xFF` sentinel; sums are NOT exactly 65535 (bandit_part1 min 49146/max 65531/mean 64755.68; part2 min 43686; sword single-influence only). Normalization is a renderer operation only. |
| 6 | **BIND-POSE SKINNING** | **DONE** — `validate_skinned_mesh` reproduces stored rest vertices with max deform ≈ `2e-6` for all 3 bandit parts (indices/weights/mapping/semantics cross-checked together). |
| 7 | **BAN FULL KEYFRAMES** | **DONE** — all keyframes exported (walk 34 ch × 15 kf, stand01 34 ch × 5 kf); timestamps non-uniform (proves NO fixed FPS). Committed `anim/*.json` now hold full keyframes. |
| 8 | **BAN CHANNEL SPACE** | **DONE** — channel (q,pos) are ABSOLUTE parent-relative transforms that REPLACE bind `rot_parent`/`tr_parent` (proven by chaining: stand01 t=0 toes on ground; walk t=0 L Toe planted / R Toe lifted). |
| 9 | **BAN LOOPING / ROOT MOTION** | **DONE** — looping PROVEN (first==last channel data); Bip01 root translation drift is loop-contained (no accumulated offset). |
| 10 | **BAN FORMAT ANOMALIES** | **UNKNOWN** — 2 files use `JMXVBAN 0101` (`spidey_attack01.ban`, `chakji_stand02.ban`) with an unproven layout; 4,793/4,795 parse byte-exact as `0102`. |
| 11 | **FIRST REAL NPC** | **DONE** — bandit refid 1949: `/res/mob/china/bandit.bsr`, 35 bones, 3 meshes (76/214/556 = 846 verts), 3 real `.ddj` textures, 16 anims, 61 npcpos spawns, 2 on committed terrain 156x90. |
| 12 | **FIRST REAL ANIMATION** | **DONE** — walk/stand01 rendered at deterministic timestamps; poses genuinely move the skeleton (walk t=0 R Toe lifted +1.25); 6 SVGs committed under `docs/phase19/snapshots/`. |
| 13 | **PLAYER PIPELINE** | **PARTIAL** — chinaman skeleton (38 bones) + body/face/hair/clothes/weapon meshes + 5 anims all PROVEN with skin; BSR->skeleton MISMATCH (references `europeman_skel.bsk`, 43 bones) and NO static spawn (no npcpos for player). |
| 14 | **JAVA POSE/SKINNING** | **DONE (compile-only)** — `Pose.java` + `CharacterRenderer.java` compile clean (`javac`); `chainWorld`/`skin` math verified (bind reproduces rest vertex, 90° rotation, 2-bone parent->child chaining). |
| 15 | **JAVA RENDERER WIRING** | **DONE (compile-only)** — `NativeWorldRenderer.setCharacterPose` + pose-driven `drawCharacters` with bind-pose fallback; `CharacterMeshIndex.poseAt`; `StaticMeshAsset.Mesh` de-finalized (latent compile bug fixed). |
| 16 | **PROOF ARTIFACTS** | **DONE** — `build_phase19_evidence.py` + committed `phase19_evidence.json` (bandit DONE / chinaman PARTIAL; hashes/counts only). |
| 17 | **ANDROID APK BUILD** | **NOT EXECUTED** — no Gradle/Android SDK (JDK 17 installed, `javac` available). |
| 18 | **DEVICE TEST** | **NOT EXECUTED** — no device/emulator. |

---

## 1. What was proven (Python, executed here)

- **BSK semantics** (`scripts/bsk_decoder.py`, 12 suites): `rot_origin/tr_origin ==
  bind_world` byte-exact (Pelvis `[0,6.9362,2.7382]` == `[0,6.936188,2.738231]`);
  `rot_parent/tr_parent == bind local`; root `rot_local == conj(rot_origin)` and
  `tr_local == R^-1·(-t)` (inverse-bind). Child-bone inverse remains PARTIAL.
- **bone_type census** (`scripts/build_bsk_census_fixture.py`): 29,957 bones,
  1,035 nonzero files, histogram `{0: 29957}`; 4 size groups + 1 outlier.
- **Weights** (`scripts/build_weights_fixture.py`, `test_phase19_weights.py`):
  bandit_part1/part2/sword + 4 other characters; max 2 influences; sums not
  exactly 65535; zero repeated/invalid indices.
- **Hierarchy** (`scripts/skeleton.py::verify_hierarchy`): rooted trees, single
  root, no cycles, no scale.
- **Bind-pose skinning** (`scripts/bms_to_asset.py::validate_skinned_mesh`):
  max deform ≈ `2e-6`.
- **Animation** (`scripts/animation_pose.py`): full-keyframe export; `_sample`
  short-circuits exact bounds (byte-exact keyframes); looping PROVEN; slerp/lerp.
- **Real NPC chain** (`scripts/build_character_manifest.py::real_npc_chain`):
  28 proven edges + 61 world placements.
- **Real animation render** (`scripts/render_npc_animation.py`): deterministic
  pose snapshots for walk/stand01.
- **Player** (`scripts/build_character_manifest.py::player_pipeline`): PARTIAL
  with documented BSR mismatch and missing spawn.

## 2. New / changed files

- Python: `scripts/animation_pose.py` (full keyframes + exact-boundary `_sample`),
  `scripts/bms_to_asset.py` (`validate_skinned_mesh`),
  `scripts/build_character_manifest.py` (`real_npc_chain`, `player_pipeline`,
  full-keyframe export), `scripts/build_phase19_evidence.py`,
  `scripts/render_npc_animation.py`, `scripts/animation_decoder.py` (thin facade).
- Tests: `test_phase19_bsk_census.py`, `test_phase19_bsk_semantics.py`,
  `test_phase19_weights.py`, `test_phase19_skeleton.py`,
  `test_phase19_bsr_chain.py`, `test_phase19_anim_census.py`,
  `test_phase19_animation.py`, `test_phase19_pose.py`,
  `test_phase19_skinned_mesh.py`, `test_phase19_real_npc.py`,
  `test_phase19_real_animation.py`, `test_phase19_player.py`,
  `test_phase19_evidence.py`, `test_phase19_matrix.py`.
- Fixtures: `bsk_census_phase19.json`, `weights_phase19.json`,
  `animation_census_phase19.json`, `phase19_evidence.json`.
- Committed bandit assets: `anim/bandit_{walk,stand01}.json` now FULL keyframes.
- Java: `Pose.java`, `CharacterRenderer.java` (new); `CharacterMeshIndex.java`
  (`poseAt`), `NativeWorldRenderer.java` (`setCharacterPose`, pose-driven draw),
  `StaticMeshAsset.java` (`Mesh` de-finalized).
- Snapshots: `docs/phase19/snapshots/` (6 SVGs).

## 3. Tests

Full regression (`python3 -m unittest discover -s scripts -p 'test_phase*.py'`):
**446 tests, 18 skipped, OK** (~408 s; skips are archive/device-gated live tests).

NOT EXECUTED: Gradle build, Android device/emulator — no Android SDK here.

## 4. Player pipeline status

- **PROVEN:** `chinaman_skel.bsk` (38 bones, rooted tree); 9 body/face/hair
  meshes + 6 clothes + 1 weapon all parse with skin blocks whose bone names are
  a subset of the chinaman skeleton; 5 clips parse; 3 `.bmt` materials present.
- **MISMATCH (documented):** every `/res/char/china/chinaman_*.bsr` references
  `/prim/skel/char/europe/europeman_skel.bsk` (43 bones), NOT `chinaman_skel.bsk`;
  the player skeleton is a standalone asset, not BSR-referenced.
- **MISSING:** no static player spawn in the archives (npcpos is NPC-only).
- **Status: PARTIAL** — rendering components proven, spawn/BSR edges not.

## 5. Deferred (honest boundaries)

- `bone_type` u8 meaning UNKNOWN (census constant zero).
- Child-bone `rot_local/tr_local` inverse algebra PARTIAL/UNKNOWN.
- BSR 8×u32 header table semantics UNKNOWN.
- 2 `JMXVBAN 0101` animations UNKNOWN (layout unproven).
- BAN `u32`@body+8 flag meaning UNKNOWN (looping proven separately from data).
- Java device rendering / APK build / runtime animation clock: NOT EXECUTED.
