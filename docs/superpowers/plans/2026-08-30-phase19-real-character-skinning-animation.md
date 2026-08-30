# Phase 19 — Real Character Skinning + BSK Semantics + Animation Playback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the REAL character pipeline (original character → original model → original BSK/BSR → verified skeleton/hierarchy/weights/skinning → original animation → verified pose → NativeWorldRenderer → real moving NPC/player) using only PROVEN original-archive data. Acceptance = ONE real original character rendered AND animated from original data, OR an evidence-backed blocker explanation (the exact missing original evidence, with offsets/structures documented).

**Architecture:** Python-first forensics on Data.pk2/Media.pk2 (proven parsers, live census, committed full-keyframe fixtures), then Java Android-native renderer wiring. Every claim must be reproduced byte-for-byte from original assets; anything unproven stays UNKNOWN/BLOCKED/NOT EXECUTED.

**Tech Stack:** Python 3.11 stdlib, existing `pk2_table.py`/`bsk_decoder.py`/`bsr_decoder.py`/`bms_decoder.py`/`ban_decoder.py`/`animation_pose.py`/`skeleton.py`/`build_character_manifest.py`, Java Android (static Canvas renderer, no WebView/HTML/JS).

## Global Constraints

- NEVER guess BSK fields, bone indices, bone hierarchy, weight normalization, quaternion/Euler conventions, animation FPS, or interpolation. UNKNOWN is a valid result.
- NEVER fabricate animation clips or use placeholder humanoids / fake skeletons.
- Preserve all verified Phase 12–18 work (terrain, coords, BMS decode, NPC placement, dependency graph, renderer, bandit assets).
- DISCOVER → INSPECT → PARSE → VALIDATE → TEST → DOCUMENT → CONVERT → INTEGRATE.
- Do not claim device/runtime success without a real Android build + device execution. JDK/Gradle/Android SDK unavailable here → Java compile/device = NOT EXECUTED, documented openly.
- Archives (source of truth): `/tmp/opencode/pk2raw/{Data,Map,Media,Music,Particles}.pk2`; characterdata text at `/tmp/opencode/textdata/`.
- No hardcoded `/tmp/opencode` in non-test scripts (use `sro_paths`/`SRO_PK2_DIR`).
- Weight normalization: never silently normalize as a decoded source fact; if the renderer needs it, document it as a renderer operation.
- Branch `260830-feat-phase19-real-character-skinning` off Phase 18 verified HEAD `44a48db`.

## PROVEN FACTS (recon, this session — must be preserved by tests)

1. **BSK transform-field semantics** (new, Phase 19): for bandit `.bsk`, `rot_origin/tr_origin` == the bone's WORLD (bind/model-space) transform — PROVEN by byte-exact match to `skeleton.json` `bind_world_pos`: Pelvis `tr_origin [0, 6.9362, 2.7382]`==`bind_world_pos [0,6.936188,2.738231]`, Head `tr_origin [0,12.379,-0.8446]`==`[5e-06,12.378977,-0.844599]`; root `Bip01` has `origin==parent` (no parent). `rot_local/tr_local` == inverse-bind (world→bone-local) — PROVEN on root by conjugate pattern (`rot_local==conj(rot_origin)`; `tr_local==R⁻¹·(−tr_origin)`); child-bone inverse pattern PARTIAL (Bip01 Pelvis local vector part sign differs from plain conjugate — needs a rigorous inverse-transform recompute test). `rot_parent/tr_parent` == parent-relative local transform (Phase 18 proven).
2. **BAN channel space** (new, Phase 19): BAN channel (q,pos) are ABSOLUTE parent-relative transforms that REPLACE the bind `rot_parent/tr_parent` — PROVEN by chaining: stand01 t=0 → both toes world-y ≈ 0 (−0.05/−0.04, on ground); walk t=0 → L Toe y≈0.00 (planted), R Toe y=+1.25 (lifted, genuine walking pose). BAN t=0 ≠ bind pose (stand01 is an idle pose, not rest pose) — do NOT assume animation starts at bind.
3. **Full keyframes exist in raw BAN** (new, Phase 19): `bandit_stand01.ban` = 34 bones × 5 kf, duration 2000 ms, timestamps [0,500,1000,1500,2000]; `bandit_walk.ban` = 34 bones × 15 kf, duration 1333 ms, timestamps [0,33,133,266,333,400,533,566,666,800,933,1000,1066,1200,1333] (non-uniform — proves NO fixed FPS assumption). Committed `anim/*.json` collapsed to `recs[0]` (build_character_manifest.py:258) — Phase 19 must export ALL keyframes.
4. **`animation_pose.py` already supports full keyframes + slerp/lerp** — only the JSON export and Java playback are missing.
5. **Java renderer is static bind-pose only**: `NativeWorldRenderer.drawCharacters` (line 342-350) draws `part.bindPositions` at theta=0; no animation loop, no `CharacterRenderer`/`Pose`/skinning-at-runtime classes.
6. **Archives present**: Data.pk2, Map.pk2, Media.pk2, Music.pk2, Particles.pk2 (no Snd.pk2). Animation census must run against Data.pk2/Media.pk2.

## OPEN QUESTIONS (to resolve with evidence, not guesses)

- Q1 (Part A/B): What is `bone_type` u8 in BSK (35 bandit bones) — census across all samples; semantics stay UNKNOWN until proven.
- Q2 (Part B): Exact inverse-bind algebra for `rot_local/tr_local` on child bones (conjugate test vs full inverse re-compute from origin).
- Q3 (Part C): Weight normalization truth — per-mesh 2-influence sums (≈65535 observed Phase 18); verify across bandit 3 parts + other characters; repeated/zero/unused influence census.
- Q4 (Part G): Clip boundaries / looping / root motion — does walk loop (t=1333 wraps to t=0)? Are Bip01 root channels root-motion (positional drift)?
- Q5 (Part L): Player (chinaman) — full original chain provable? If not, PLAYER = BLOCKED/UNKNOWN with evidence.

---

### Task 1: Part A — REAL BSK census (`bsk_decoder.py` + live census fixture)

**Files:**
- Modify: `scripts/bsk_decoder.py` (`validate_census` → per-field record: offset|size|raw value|interpretation|evidence|status; group by size/magic/version/layout; emit bone_type census; referenced-asset inference ONLY where BSR proves it)
- Modify: `scripts/test_phase18_bsk.py` → new `scripts/test_phase19_bsk_census.py`
- Create: `scripts/build_bsk_census_fixture.py` (env `--pk2-dir`/`SRO_PK2_DIR`, writes `scripts/testdata/formats/bsk_census_phase19.json`)

**Interfaces:**
- `parse_bsk(data)` unchanged (already byte-exhausting 1034/1035); add `census_record()` returning per-bone `{offset, size, raw_value, interpretation, evidence, status}` for every suspected field.
- `validate_census()` extended to group all Data.pk2/Media.pk2 BSK by magic/version/size-bucket and report field records.

- [ ] **Step 1:** Write failing test: census fixture asserts group counts by magic/version, bandit `bone_type` u8 census (raw values only, no semantics), `exact=True` for all nonzero samples.
- [ ] **Step 2:** Run → FAIL (fixture/API missing).
- [ ] **Step 3:** Implement `build_bsk_census_fixture.py`; run against live pk2 (env) to produce `bsk_census_phase19.json`.
- [ ] **Step 4:** Implement `census_record()`/extended `validate_census()` in `bsk_decoder.py`; run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 BSK census (per-field evidence records, grouped by magic/version/size)`.

### Task 2: Part B — BSK bone structure semantics (`bsk_decoder.py`)

**Files:**
- Modify: `scripts/bsk_decoder.py` (assert `origin==world bind`, `local==inverse bind` per PROVEN FACT 1)
- Modify: `scripts/test_phase18_bsk.py` → new `scripts/test_phase19_bsk_semantics.py`

**Interfaces:**
- `verify_transform_semantics(bones, bind_world) -> dict` returning per-bone `{origin_matches_world: bool, local_is_inverse: bool, parent_is_local: bool}`.

- [ ] **Step 1:** Write failing test: for bandit, every bone `rot_origin/tr_origin == skeleton.json bind_world`, `rot_local/tr_local == inverse(bind)` (rigorous inverse recompute: `R⁻¹=conj`, `t⁻¹=R⁻¹·(−t)`), `rot_parent/tr_parent == bind local`. Q2 resolution: child-bone conjugate discrepancy must be explained (either my inverse algebra or the field is NOT plain inverse — keep UNKNOWN if not proven).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `verify_transform_semantics`; resolve Q2 with a recompute-vs-stored diff table.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 BSK transform semantics (origin=world, local=inverse-bind, parent=local)`.

### Task 3: Part C — REAL skinning weights (extend `bms_decoder.py`)

**Files:**
- Modify: `scripts/bms_decoder.py` (`parse_skin_data` → add weight census)
- Create: `scripts/test_phase19_weights.py`
- Create: `scripts/build_weights_fixture.py` (env-gated; writes `scripts/testdata/formats/weights_phase19.json` for bandit 3 parts + ≥2 other characters)

**Interfaces:**
- `skin_census(data) -> dict` per mesh part: `{vertex_count, influence_count, index_width, weight_width, normalization: {min_sum, max_sum, mean_sum, count_sum_ge_65535}, invalid_indices: n, repeated_indices: n, zero_weights: n, unused_influences: n, max_influences}`.

- [ ] **Step 1:** Write failing test: bandit sword/part1/part2 + 2 other characters — every 2-influence vertex has weight sum documented (not silently normalized), invalid/repeated/zero/unused influence counts reported.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `skin_census` + `build_weights_fixture.py`; run live (env) → fixture. Resolve Q3.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 skinning-weight census (normalization + invalid/repeated/zero/unused influence report)`.

### Task 4: Part D — skeleton reconstruction (`skeleton.py`)

**Files:**
- Modify: `scripts/skeleton.py` (cycle/impossible-parent detection, scale behavior, handedness assertion)
- Modify: `scripts/test_phase18_*.py` → new `scripts/test_phase19_skeleton.py`

**Interfaces:**
- `verify_hierarchy(bones) -> dict` `{is_tree, has_cycles, single_root, every_parent_exists, max_depth, scale_behavior, handedness_evidence}`.

- [ ] **Step 1:** Write failing test: bandit (35) + chinaman (38) skeletons are rooted trees (no cycles, one root, every parent exists), max depth < 40, scale behavior documented.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `verify_hierarchy`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 skeleton hierarchy verification (tree/cycle/scale)`.

### Task 5: Part E — BSR cross-reference (`bsr_decoder.py` + dependency graph)

**Files:**
- Modify: `scripts/bsr_decoder.py` (proven-edge table emitter)
- Modify: `scripts/build_asset_dependency_graph.py` (add `.bsr→.bsk→bones`, `.bsk→.bms` edges with PROVEN status)
- Create: `scripts/test_phase19_bsr_chain.py`

**Interfaces:**
- `proven_edges(bsr, bsk, bms_list) -> list[{source, target, evidence, status}]` — only PROVEN edges enter the graph.

- [ ] **Step 1:** Write failing test: for bandit BSR, edge chain `BSR→bandit.bsk→35 bones`, `BSR→bandit sword/part1/part2 → skin`, `bandit.bsk→skin bone names all present` — every edge must carry evidence + PROVEN.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `proven_edges`; update dependency graph builder.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 BSR→BSK→mesh proven-edge dependency graph`.

### Task 6: Part F — REAL animation file census (new archive scanner)

**Files:**
- Create: `scripts/animation_census.py` (env `--pk2-dir`/`SRO_PK2_DIR`; scans Data.pk2/Media.pk2)
- Create: `scripts/test_phase19_anim_census.py`
- Create: `scripts/testdata/formats/animation_census_phase19.json` (fixture)

**Interfaces:**
- `scan_animation_candidates(pk2) -> list[{path, size, magic, header_snapshot, classification}]`; classification ∈ {animation_data, skeleton_data, motion_data, metadata, unrelated_binary, UNKNOWN}. Inspection via magic/headers/record/timing patterns, NOT extension only.

- [ ] **Step 1:** Write failing test: fixture asserts bandit_walk/stand01 classified `animation_data`, non-animation `.dat`/`.uax`/`.bmt` NOT misclassified.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `animation_census.py`; run live (env) → fixture + live report.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 animation candidate census (magic/header/record inspection)`.

### Task 7: Part G — animation format + FULL keyframe export (`animation_pose.py` + `build_character_manifest.py`)

**Files:**
- Modify: `scripts/animation_pose.py` (`load_keyframes` → expose clip count/duration/loop/root-motion fields)
- Modify: `scripts/build_character_manifest.py` (export ALL keyframes per channel, not `recs[0]`; keep JSON size reasonable)
- Modify: `scripts/test_phase18_anim*` → new `scripts/test_phase19_animation.py`
- Create: `scripts/animation_decoder.py` (thin facade over `animation_pose.load_keyframes` per brief naming)

**Interfaces:**
- `describe_animation(raw) -> dict` `{clip_count, clip_name, duration_ms, keyframe_count, timestamps, target_bones, has_translation, has_rotation, has_scale, interpolation, compression, looping, root_motion}` — only PROVEN fields; no assumed 30/60 FPS or quaternion/Euler order beyond proven.

- [ ] **Step 1:** Write failing test: bandit_walk describe → duration 1333 ms, 15 kf, non-uniform timestamps, has rotation+translation, no scale, looping=UNKNOWN (resolve Q4), root_motion reported from Bip01 root channel drift.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `describe_animation`; regenerate bandit `anim/*.json` with ALL keyframes; update manifest/anims.tsv.
- [ ] **Step 4:** Run → PASS. Resolve Q4 (loop wrap: does t=duration interpolate to t=0?).
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 full-keyframe animation export + describe (bandit stand01/walk)`.

### Task 8: Part H — pose evaluation tests (`animation_pose.py`)

**Files:**
- Modify: `scripts/animation_pose.py` (boundary handling exactness)
- Create: `scripts/test_phase19_pose.py`

**Interfaces:**
- `evaluate_pose(raw, t_ms, bones)` unchanged; new `pose_boundary_checks(raw, bones)` verifying bind/rest, first/mid/last keyframe, exact boundaries, loop boundary (only if proven), determinism (same input → identical output).

- [ ] **Step 1:** Write failing test: for walk — t=0, t=33, t=700 (interpolated), t=1333, boundary t=999/1000, loop wrap (if proven); all deterministic.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement boundary handling + checks.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 pose evaluation boundary + determinism tests`.

### Task 9: Part I — REAL skinned mesh validation (`bms_to_asset.py`)

**Files:**
- Modify: `scripts/bms_to_asset.py` (`bms_to_msh_skinned` → validate bind-pose non-distortion)
- Create: `scripts/test_phase19_skinned_mesh.py`

**Interfaces:**
- `validate_skinned_mesh(skin, bones) -> dict` `{every_vertex_exists, every_bone_exists, weights_valid, indices_valid, bind_pose_no_distortion}` (bind pose skin == raw vertex positions within tolerance).

- [ ] **Step 1:** Write failing test: bandit 3 parts — every skin bone index valid, bind-pose skinning reproduces raw vertex positions (tolerance), weights per proven rules.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `validate_skinned_mesh`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 skinned-mesh validation (bind-pose no-distortion)`.

### Task 10: Part J — FIRST REAL NPC (bandit refid 1949) chain test

**Files:**
- Create: `scripts/test_phase19_real_npc.py`
- Modify: `scripts/build_character_manifest.py` (regenerate bandit assets; verify chain integrity)

**Interfaces:**
- `real_npc_chain(npc_refid) -> list[{edge, source, target, evidence, status}]` proving `NPC record → character reference → model → BSK/BSR → skeleton → mesh → texture/material → world coordinate` (npcpos region 23196, sector (156,90), locals (1592.44,1401.47)/(724.69,1663.85) — ON committed terrain).

- [ ] **Step 1:** Write failing test: bandit chain edges all PROVEN end-to-end; world coordinate ON terrain.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `real_npc_chain`; regenerate assets if needed.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 real NPC chain test (bandit 1949, proven edges to world placement)`.

### Task 11: Part K — FIRST REAL ANIMATION on the real NPC

**Files:**
- Create: `scripts/test_phase19_real_animation.py`
- Create: `scripts/render_npc_animation.py` (deterministic pose renderer snapshots at T0/T1/T2)

**Interfaces:**
- `render_npc_pose(npc_refid, anim_path, t_ms) -> PNG/snapshot` — bind pose or first proven pose at T0, proven intermediate T1, proven final T2; skeleton actually receives the decoded pose (bone transform diffs assert animation effect ≠ bind).

- [ ] **Step 1:** Write failing test: for bandit walk/stand01 at T0/T1/T2 — bone world transforms differ from bind (animation genuinely applied), deterministic across runs.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `render_npc_animation.py`; run to produce snapshots.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 real NPC animation renders (walk/stand01 at deterministic timestamps)`.

### Task 12: Part L — PLAYER pipeline status

**Files:**
- Create: `scripts/test_phase19_player.py` (or evidence report)
- Modify: docs (PLAYER = DONE / BLOCKED / UNKNOWN with evidence)

**Interfaces:**
- `player_pipeline() -> dict` — independently determine player model/BSK/BSR/skeleton/textures/animation set/spawn reference from original archives (chinaman assets exist per Phase 18). Do NOT assume player == NPC. If unprovable, PLAYER = BLOCKED/UNKNOWN with documented evidence.

- [ ] **Step 1:** Write failing test / evidence extraction: chinaman full chain edges (model/BSK/BSR/skeleton/texture/animation/spawn).
- [ ] **Step 2:** Run → FAIL (if edges missing).
- [ ] **Step 3:** Implement `player_pipeline`; document result honestly.
- [ ] **Step 4:** Run → PASS / document BLOCKED.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 player pipeline evidence (chinaman) or BLOCKED report`.

### Task 13: Part M — NativeWorldRenderer extension (Java, compile-only)

**Files:**
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/NativeWorldRenderer.java`
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/CharacterMeshIndex.java`
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/StaticMeshAsset.java`
- Create: `android/app/src/main/java/com/opensilkroadmap/app/world/CharacterRenderer.java`, `SkinnedMesh.java`, `Skeleton.java`, `Pose.java` (as required by proven data only)

**Interfaces:**
- `CharacterRenderer.draw(canvas, pose, mesh, heading)` — skinning at runtime from pose arrays; `Pose` holds per-bone local (rot_parent/tr_parent) from decoded animation; `Skeleton` chains world transforms; static bind-pose render must remain for fallback. Keep Android-native (NO WebView/HTML/JS).
- Compile-only check: `deno run -A npm:vite build` and/or javac if available. Runtime = NOT EXECUTED (no JDK/Gradle/Android SDK here).

- [ ] **Step 1:** Add Java classes (CharacterRenderer/Skeleton/Pose/SkinnedMesh) with static bind-pose equivalence to existing renderer.
- [ ] **Step 2:** Wire pose-driven skinning path in `drawCharacters` (theta=0, pose from decoded bandit animation at deterministic timestamps).
- [ ] **Step 3:** Compile-check via available toolchain; document NOT EXECUTED for device runtime.
- [ ] **Step 4:** Commit `feat(android): Phase 19 character renderer pose-driven skinning (compile-only; device NOT EXECUTED)`.

### Task 14: Part N — test matrix + full regression

**Files:**
- Create: `scripts/test_phase19_matrix.py` (aggregates Parts A–N coverage)

**Interfaces:**
- Run: new Phase 19 tests + ALL existing Phase 10–18 Python tests.
- Full regression (background terminal, ~328 s): `cd /workspace && python3 -m unittest discover -s scripts -p 'test_phase*.py'`.

- [ ] **Step 1:** Assemble matrix test importing each Phase 19 suite.
- [ ] **Step 2:** Run full regression in background terminal; record counts.
- [ ] **Step 3:** Fix any regressions (preserve Phase 12–18 behavior).
- [ ] **Step 4:** Green run recorded.
- [ ] **Step 5:** Commit `test(scripts): Phase 19 test matrix + full regression green`.

### Task 15: Part O — proof artifacts

**Files:**
- Create: `scripts/build_phase19_evidence.py` (env-gated; emits per-character evidence records)
- Create: `scripts/testdata/formats/phase19_evidence.json`

**Interfaces:**
- `evidence_record(character) -> {character, model, source_file, BSK, BSR, mesh, texture, skeleton, bone_count, vertex_count, weight_format, animation, animation_duration, proven_relationships, unknown_relationships}` — hashes/offsets/counts only, NO full copyrighted binary data in docs.

- [ ] **Step 1:** Write failing test: evidence records for bandit (and player if proven) contain all required keys + hashes/offsets.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `build_phase19_evidence.py`; run live (env) → fixture.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(scripts): Phase 19 proof artifacts (per-character evidence records)`.

### Task 16: Part P — documentation

**Files:**
- Create: `PHASE_19_REPORT.md`
- Modify: `docs/FORMAT_RESEARCH.md`, `docs/DATA_FORMAT_CATALOG.md`, `docs/ANDROID_DATA_CONVERSION_STATUS.md`, `ANDROID_ASSET_DEPENDENCY_GRAPH.json`

**Interfaces:**
- Report MUST explicitly answer: BSK (layout/bones/hierarchy/transforms/weights), BSR (layout/proven relationships), SKINNING (indices/weights/deformation), ANIMATION (format/clips/keyframes/timing/pose evaluation/playback), NPC (model/skeleton/skin/texture/world position/rendering/animation), PLAYER (model/skeleton/skin/rendering/animation), ANDROID (compile/APK/runtime/device). Status vocabulary ONLY: DONE / PARTIAL / BLOCKED / UNKNOWN / NOT EXECUTED.

- [ ] **Step 1:** Write `PHASE_19_REPORT.md` from proven facts + task outputs.
- [ ] **Step 2:** Update the 4 docs with only PROVEN status changes.
- [ ] **Step 3:** Verify status vocabulary discipline (no invented DONE).
- [ ] **Step 4:** Commit `docs: Phase 19 report + format/status updates`.

### Task 17: Part Q — git discipline

- [ ] **Step 1:** `git status`; inspect changed/untracked files.
- [ ] **Step 2:** Secret scan staged diff; ensure NO PK2/source archive committed (`.gitignore` covers `*.pk2`).
- [ ] **Step 3:** Create branch `260830-feat-phase19-real-character-skinning` (off `44a48db`).
- [ ] **Step 4:** Commit (per-task commits already made; final aggregate if needed).
- [ ] **Step 5:** `git push -u origin <branch>`.
- [ ] **Step 6:** `git fetch origin`; verify LOCAL SHA == REMOTE SHA.
- [ ] **Step 7:** Verify clean working tree.

## FINAL ACCEPTANCE

- A) STRONG SUCCESS: one real original NPC rendered AND animated through NativeWorldRenderer from proven BSK/BSR/skeleton/weights/animation data — OR
- B) EVIDENCE BLOCK: the exact missing original evidence preventing REAL animation, with source files inspected, offsets/structures documented, what is proven, what remains UNKNOWN, why implementation cannot honestly proceed.

Final output = concise matrix `COMPONENT | STATUS | SOURCE EVIDENCE | TEST | REMAINING BLOCKER` + explicit lines:
`FIRST REAL NPC: DONE / BLOCKED`; `FIRST REAL ANIMATION: DONE / BLOCKED`; `PLAYER: DONE / BLOCKED`; `BSK: DONE / PARTIAL / UNKNOWN`; `BSR: DONE / PARTIAL / UNKNOWN`; `SKINNING: DONE / PARTIAL / UNKNOWN`; `ANDROID BUILD: DONE / NOT EXECUTED`.
