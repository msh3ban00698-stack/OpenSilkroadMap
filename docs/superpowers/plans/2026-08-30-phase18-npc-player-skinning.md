# Phase 18 — Real NPC + Player + BSK/BSR Skinning + Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the REAL character pipeline (NPC/player → characterdata → BSR → BMS+BSK+BAN → bind pose → skinning → animation → NativeWorldRenderer) using only PROVEN original-archive data, with deterministic tests.

**Architecture:** Python-first forensics on Data.pk2/Media.pk2 (proven parsers + committed fixtures + committed per-character assets), then Java Android-free parsers structurally wired into NativeWorldRenderer. Every claim must be reproduced byte-for-byte from original assets; anything unproven stays UNKNOWN/BLOCKED/NOT EXECUTED.

**Tech Stack:** Python 3.11 stdlib, existing `pk2_table.py`/`bms_decoder.py`/`ban_decoder.py`/`world_terrain.py`/`o2_decoder.py`, Java Android (static Canvas renderer).

## Global Constraints

- NEVER invent formats/fields/transforms/indexes. UNKNOWN is a valid result.
- No placeholders, fake skeletons, generated animation, guessed geometry.
- Preserve all verified Phase 12–17 work (terrain, coords, BMS decode, NPC placement, dependency graph, renderer).
- DISCOVER → INSPECT → PARSE → VALIDATE → TEST → DOCUMENT → CONVERT → INTEGRATE.
- Do not claim device/runtime success without a real Android build + device execution.
- Archives (source of truth): `/tmp/opencode/pk2raw/{Data,Map,Media}.pk2`; characterdata text at `/tmp/opencode/textdata/`.
- No hardcoded `/tmp/opencode` in non-test scripts (use `sro_paths`/`SRO_PK2_DIR`).
- Branch `260830-feat-phase18-npc-player-skinning` off Phase 17 HEAD `9e1084d`.

## PROVEN FACTS (recon, this session — must be preserved by tests)

1. **BSK layout** (`JMXVBSK 0101`): `u32 bone_count@12`; per bone `u8 bone_type, str name, str parent, 21×f32 (rot_parent4+tr_parent3+rot_origin4+tr_origin3+rot_local4+tr_local3), u32 child_count, child_count×str`; 8 zero trailer bytes. Byte-exhausts 1034/1035 nonzero Data.pk2 BSK files (1 outlier `skel/item/common/mob_select.bsk` — UNKNOWN).
2. **BMS skin block** lives in the BONE section: `u32 bone_count + names + vcount×6 B (u8 b1, u16 w1, u8 b2, u16 w2)`; `0xFF` sentinel = no 2nd influence; weights u16/65535; 2-influence sums ≈ 65535; `flags==2` vertex count == `skinned_vertex_count` == 2-influence count. Byte-exhausts every character mesh tested (pelvis/torso/arm/thigh/calf/face/hair/cj_chicken).
3. **BSR** (`JMXVRES 0109/0108/0107`): header `8×u32` table (meaning PARTIAL); grouped `[u32 len][ascii path]` tokens ordered materials(.bmt) → meshes(.bms) → animations(.ban) → skeleton(.bsk) → effects(.efp) → sounds(.wav). Group-separator semantics PARTIAL.
4. **NPC chain**: `characterdata_*.txt` col1=refid, col52=.bsr path; `npcpos.tsv` col0=refid, col1=region, col2/4=local x/z; `unpack_region`: sx=region&0xFF, sy=region>>8. Target NPC **bandit** refid 1949: region 23196 = sector (156,90), locals (1592.44,1401.47) and (724.69,1663.85) — ON committed terrain. col52 → `/res/mob/china/bandit.bsr` → 3 bmt + 3 bms (sword/part1/part2) + 18 ban + 1 bsk.
5. **Name-based bone mapping**: every mesh-local bone name exists in the matching skeleton (PROVEN for chinaman player parts; must verify bandit parts).
6. **Player assets** exist: `/prim/skel/char/china/chinaman_skel.bsk` (38 bones), man_* mesh parts, chinaman_fighter bans.

---

### Task 1: `scripts/bsk_decoder.py` — rigorous BSK parser + fixtures

**Files:**
- Create: `scripts/bsk_decoder.py`
- Create: `scripts/test_phase18_bsk.py`
- Create: `scripts/build_bsk_fixture.py` (env `--pk2-dir`/`SRO_PK2_DIR`, writes `scripts/testdata/formats/bsk_phase18.json` + raw sample `.bsk` files)
- Modify: `scripts/build_asset_dependency_graph.py` (`.bsk → bones` edge evidence → VERIFIED Phase 18)

**Interfaces:**
- `parse_bsk(data) -> dict` with keys: `magic, version, bone_count, bones:[{bone_type, name, parent, rot_parent, tr_parent, rot_origin, tr_origin, rot_local, tr_local, child_count, children}], trailer, parsed_bytes, file_size, exact` (exact = 8-byte-trailer byte-exhaustion flag).
- `validate_census()` reads live Data.pk2 inventory (env-gated) and asserts 1034/1035 exhaust, 1 outlier named.

- [ ] **Step 1: Write failing test** `test_phase18_bsk.py` — fixtures for chinaman_skel, bandit, islamman, blackrobber, horse1 asserting bone counts 38/?, 43/35/31, `exact=True`, trailer=8 zero bytes.
- [ ] **Step 2: Run → FAIL** (`bsk_decoder` import missing).
- [ ] **Step 3: Implement `bsk_decoder.py`** per proven layout (Task header), surfacing `rot_*`/`tr_*` as 4/3 float lists, no interpretation of `bone_type` beyond raw u8 (UNKNOWN semantics).
- [ ] **Step 4: Run → PASS**; also run live census (1034/1035) when `SRO_PK2_DIR` set.
- [ ] **Step 5: Commit** `feat(scripts): Phase 18 BSK skeleton parser (proven 1034/1035 byte-exhaustion)`.

### Task 2: `scripts/bsr_decoder.py` — full path-group parser

**Files:**
- Create: `scripts/bsr_decoder.py`
- Create: `scripts/test_phase18_bsr.py`

**Interfaces:**
- `parse_bsr_references(data) -> dict` keys: `magic, version, materials:[], meshes:[], animations:[], skeleton:[], effects:[], sounds:[], paths:[{ext, path}], header_table:[8 u32], tail_bytes` — paths normalized to leading `/`, `\`→`/`. Extension-classified; ORDER assertion (bmt→bms→ban→bsk→efp→wav) enforced.
- `resolve_character(bsr_dict) -> {bmt, bms[], ban[], bsk}` convenience.

- [ ] **Step 1: failing test** — bandit.bsr → 3 bmt/3 bms/18 ban/1 bsk; chinaquest_priest.bsr → 1 bmt/3 bms/2 ban/1 bsk; tre_tree03.bsr → bmt+bms only (no bsk/ban).
- [ ] **Step 2: run → FAIL**
- [ ] **Step 3: implement** extension-classified token scan (len 8..200, printable, contains `\`), group-order assertion.
- [ ] **Step 4: run → PASS** (uses live archive; fixture-committed tokens too)
- [ ] **Step 5: Commit**

### Task 3: BMS skin-block decoder (extend `bms_decoder.py`)

**Files:**
- Modify: `scripts/bms_decoder.py` (add `parse_skin_data(data, header) -> list[(b1,w1,b2,w2)]`)
- Modify: `scripts/test_phase16_bms.py` (add skin assertions for char samples) + new `scripts/test_phase18_skin.py`

**Interfaces:**
- `parse_skin_data(data, header, vertex_count) -> list` of `(bone1, weight1, bone2, weight2)`; validates byte-exhaustion of bone section, `b1<bones`, `b2 in (0xFF or <bones)`, weights ≤ 65535.
- `skinned_vertices(mesh)` derived: flags==2 set == skinned_vertex_count == 2-influence count (asserted).

- [ ] **Step 1: failing test** for man_pelvis/man_arm_lower/cj_chicken skin stats (b1max<bones, sums∈[58000,65535], sentinel 0xFF).
- [ ] **Step 2: run → FAIL**
- [ ] **Step 3: implement `parse_skin_data`** in bms_decoder (keep 44/52 layouts untouched).
- [ ] **Step 4: run → PASS** (full Phase 10–18 regression re-run)
- [ ] **Step 5: Commit**

### Task 4: BSK↔BMS name mapping + bandit skeleton reconstruction (Parts C/D)

**Files:**
- Create: `scripts/skeleton.py` (build parent list, bind world transforms from bsk `rot_parent`/`tr_parent`)
- Create: `scripts/test_phase18_skeleton.py`

**Interfaces:**
- `bone_parents(bones) -> [int]`, `bind_world(bones) -> (world_rot, world_pos)` per bone (quat multiply + rotate), `name_index(bones)`.
- `validate_mesh_bones(skel_names, mesh_bone_names) -> missing[]` (must be empty).
- `build_character_skeleton(bsk_path) -> dict` with provenance (sha256, source path).

- [ ] **Step 1: failing test** — bandit.bsk: every bandit_part1/part2/sword mesh bone name present in skeleton; root bone has parent ""; parent list acyclic; bind world deterministic (compare two parses identical).
- [ ] **Step 2: run → FAIL**
- [ ] **Step 3: implement**
- [ ] **Step 4: run → PASS**
- [ ] **Step 5: Commit**

### Task 5: animation pose evaluation (Part G/H) via `ban_decoder.py`

**Files:**
- Create: `scripts/animation_pose.py` (channel→bone-by-name, quat-slerp/pos-lerp evaluation, loop clamp)
- Create: `scripts/test_phase18_animation.py`
- Modify: `scripts/build_bsk_fixture.py` → also commit bandit `bandit_stand01.ban`+`bandit_walk.ban` raw + parsed fixture.

**Interfaces:**
- `evaluate_ban(ban, t_ms, skeleton) -> {bone_idx: (quat, pos)}`; unknown channels skipped with UNKNOWN note; interpolation mode PROVEN from source (do not assume — inspect keyframe timestamps for regularity; if irregular, use linear between proven keys and document).
- `pose_bind(skeleton) -> {bone_idx: (quat,pos)}` (rest pose).

- [ ] **Step 1: failing test** — evaluate bind pose, first/mid/final keyframe of bandit_stand01; assert duration>0, channel count ≥ 1, per-bone key counts > 0; determinism (re-eval identical).
- [ ] **Step 2: run → FAIL**
- [ ] **Step 3: implement** (reuse `ban_decoder.parse_ban`; add skeleton-name→channel mapping)
- [ ] **Step 4: run → PASS**
- [ ] **Step 5: Commit**

### Task 6: `scripts/build_character_manifest.py` — bandit assets (Parts E/F/I)

**Files:**
- Create: `scripts/build_character_manifest.py` (reads bandit bsr via bsr_decoder, bms via bms_decoder+skin, bsk via bsk_decoder, ban via ban_decoder, bmt→ddj→PNG via dds_decode)
- Create: `scripts/test_phase18_character.py`
- Modify: `scripts/build_asset_dependency_graph.py` (characterdata→bsr→bsk/ban/skin edges)

**Interfaces:**
- `build(out_dir, pk2_dir) -> report` writing into `android/app/src/main/assets/game/world/characters/bandit/`:
  - `skeleton.json` (names, parents, bindRot, bindPos, provenance)
  - `meshes.tsv` + `mesh/*.msh` (MSH1 extended layout: positions/normals/uvs/indices + per-vertex skin (b1,w1,b2,w2) + local-bone-name table)
  - `tex/*.png`
  - `anims.tsv` (channel bone names, durations, key counts) + `anim/*.json` (decoded keyframes) for stand01/walk
  - `npc_placements.tsv` (region, world x/z, ref 156x90)
  - `provenance.json` (sha256 + chain of every input)

- [ ] **Step 1: failing test** — commit-schema assertions (skeleton 35± bones, 3 meshes present with skin, ≥1 anim, placements 2 rows at (1592.44,1401.47) & (724.69,1663.85)).
- [ ] **Step 2: run → FAIL**
- [ ] **Step 3: implement** (deterministic; byte-identical rebuild test)
- [ ] **Step 4: run → PASS** (run builder to produce committed assets)
- [ ] **Step 5: Commit**

### Task 7: Java — character index + renderer wiring (Part K)

**Files:**
- Create: `android/app/src/main/java/com/opensilkroadmap/app/world/CharacterMeshIndex.java` (Android-free: loads skeleton.json/meshes.tsv/placements.tsv/anims, fail-closed)
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/NativeWorldRenderer.java` (`setCharacters`, `drawCharacters` → per-instance bind-pose skinning: vertex transform = Σ w·(bone world matrix) from skeleton bind; static pose only, animation pose structurally present but playback = UNKNOWN)
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/game/GameActivity.java`
- Create: `android/app/src/test/java/com/opensilkroadmap/app/world/CharacterMeshIndexTest.java` (JVM, structural)
- Modify: `android/app/src/androidTest/.../GameActivityTest.java` (character assertion)

**Interfaces:**
- `CharacterMeshIndex.load(AssetManager, refSx, refSy)`, `characters()`, `Instance.worldX/worldZ/theta`.
- Renderer: `drawCharacters(Canvas)` mirrors `drawMeshPart` with per-vertex skinned `worldVertex`.

- [x] **Step 1: structural JVM test** (parses committed bandit assets, count assertions) — NOT EXECUTED (no JDK), documented in `CharacterMeshIndexTest` javadoc.
- [x] **Step 2: implement Java** (Android-free parser + renderer seam): `StaticMeshAsset.parseSkinned` + `SkinnedMesh` (MSH v2), `CharacterMeshIndex` (skeleton/meshes/placements/anims loaders + minimal JSON parser + bind-pose `skinnedBindPositions` = Σ(w/Σw)·(R·v+t)), `NativeWorldRenderer.drawCharacters` (theta=0), `GameActivity` wiring.
- [x] **Step 3: brace-balance + review; NO build/device claims.**
- [x] **Step 4: Commit**

### Task 8: Player pipeline status (Part J) + docs (Part O)

**Files:**
- Create: `PHASE_18_REPORT.md`
- Modify: `FORMAT_RESEARCH.md`, `DATA_FORMAT_CATALOG.md`, `ANDROID_DATA_CONVERSION_STATUS.md`, `ANDROID_ASSET_DEPENDENCY_GRAPH.json` (regenerate via builder)

**Player status:** DONE for assets (chinaman_skel + man_* + bans exist and parse); PLAYER RENDERING same BLOCKED-as-device-untested caveat as NPC; explicit missing-evidence list if any column/field unproven.

- [x] **Step 1: update docs + write report** (`PHASE_18_REPORT.md` 18-metric matrix; `FORMAT_RESEARCH.md` §3/§5/§8; `DATA_FORMAT_CATALOG.md` bsk/bsr→VERIFIED, bms skin, rollup 17,525/40,944; `ANDROID_DATA_CONVERSION_STATUS.md` Phase 18 section + summary; `ANDROID_ASSET_DEPENDENCY_GRAPH.json` regenerated = 26 edges, deterministic no-diff).
- [x] **Step 2: full regression re-run** green — 294 tests, 13 skipped (~328 s); Phase 18 + graph suites re-verified after doc edits (85 tests, OK).
- [x] **Step 3: Commit**

### Task 9: Git discipline (Part P)

- [x] `git status` + inspect all changed/untracked files
- [x] secret scan staged diff (`git diff --cached | rg` secrets); verify no `.pk2`/binaries beyond intended assets
- [x] create branch `260830-feat-phase18-npc-player-skinning`
- [x] commit
- [x] push `-u origin`
- [x] `git fetch`; verify LOCAL SHA == REMOTE SHA
- [x] verify clean tree
