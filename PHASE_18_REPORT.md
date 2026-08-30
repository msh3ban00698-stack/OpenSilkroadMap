# PHASE 18 REPORT — NPC / Player Skinning Pipeline

Branch: `260830-feat-phase18-npc-player-skinning` · Phase 17 baseline: `9e1084d`
Date: 2026-08-30

Phase 18 closes the Phase 16/17 blocker (`flags==2` skinned tail, `.bsk` palette
UNKNOWN): the full NPC character pipeline is PROVEN from ORIGINAL PK2 bytes —
`characterdata refid -> .bsr -> .bsk` skeleton (bind pose, `[x,y,z,w]`
quaternions), `.bms` per-vertex skin block, `.ban` pose evaluation, `.bmt` ->
`.ddj` textures — converted to committed Android assets (skeleton.json, MSH v2
skinned meshes, PNGs, anims, placements, provenance), and wired into a Java
bind-pose skinned renderer. Nothing below is invented; every structural claim is
reproduced from real archive bytes and asserted by hermetic Python tests.

---

## Status vocabulary

- **DONE** — proven from ORIGINAL archive bytes + executed, hermetic Python tests.
- **IMPLEMENTED** — native code committed and structurally reviewed; device run not possible here.
- **PARTIAL** — a proven subset works; the rest is documented.
- **BLOCKED** — cannot proceed without missing evidence/decoder.
- **UNKNOWN** — no honest claim possible yet.
- **NOT EXECUTED** — not run in this environment (no JDK/Android SDK/emulator).

---

## 18-line phase status

| # | Metric | Status |
|---|---|---|
| 1 | **BSK DECODER** | **DONE** — `JMXVBSK 0101`; u32 bone_count@12; per bone u8 type + str name + str parent + 21×f32 (rot_parent4, tr_parent3, rot_origin4, tr_origin3, rot_local4, tr_local3) + u32 child_count + children + 8 zero trailer; byte-exhausts **1034/1035** nonzero `Data.pk2` `.bsk`. Outlier `/prim/skel/item/common/mob_select.bsk` structure **UNKNOWN**. |
| 2 | **BSK SEMANTICS** | **UNKNOWN** — `bone_type` u8 meaning; rot_origin/tr_origin/rot_local/tr_local usage (only rot_parent/tr_parent feed the proven bind pose). |
| 3 | **BSR DECODER** | **DONE** — `JMXVRES 0109/0108/0107`; 8×u32 table@12 + 16 zero bytes + body@0x3C of u32-len-prefixed ASCII tokens; classified `.bmt/.bms/.ban/.bsk/.efp/.wav`; `is_character` = has `.bsk`; group order bmt→bms→ban→bsk→efp→wav asserted for characters. bandit = 3 bmt + 3 bms + 16 ban + 1 bsk + 7 efp + 16 wav. |
| 4 | **BSR 8×u32 HEADER** | **UNKNOWN** — the 8-u32 table semantics (values non-monotonic; not a section table). |
| 5 | **BMS SKIN BLOCK** | **DONE** — in the bone section, 6 B/vertex `[u8 b1][u16 w1][u8 b2][u16 w2]`; `0xFF` sentinel; single-influence `w2=0`; span == 6×vcount byte-exhausts. `parse_bms` gains `skin` (None for static meshes). |
| 6 | **SKIN WEIGHT NORMALIZATION** | **UNKNOWN** — two-influence sums are mesh-dependent (bandit_part1 min sum 49146, bandit_sword has NO two-influence vertices), so weights are NOT pre-normalized to 65535. Renderer normalizes by per-vertex sum (documented decision). `skinned_vertex_count` header meaning is mesh-dependent. |
| 7 | **VERTEX TAIL u32@36** | **UNKNOWN** — global `bone_index` reaches 151 (beyond local bone tables); not a local skin index. |
| 8 | **SKELETON BIND POSE** | **DONE** — quaternion convention **PROVEN `[x,y,z,w]`** (wxyz attempt discarded: planted toes y≈2.5 vs feet ~4.8–6.8); chained `rot_parent`/`tr_parent` aligns to mesh bounds (bandit L Toe0 world y≈0.02 vs mesh ground 0.03; pelvis 6.94; head 12.38; hands ±8.2). |
| 9 | **BAN POSE EVALUATION** | **DONE** — `load_keyframes` full parse (per-bone channels aligned to global timestamps); slerp/pos-lerp `evaluate_pose`; unanimated bones fall back to bind local transforms. bandit_stand01 2000ms/5kf/34 channels; bandit_walk 1333ms/15kf/34 channels (irregular 33/133/266 ms timestamps justify adjacent-key interpolation). |
| 10 | **ANIMATION PLAYBACK** | **UNKNOWN / PARTIAL** — runtime playback not implemented; the renderer draws the static bind pose. Only the first keyframe per channel is committed per animation (keeps JSON small). |
| 11 | **MSH v2 (SKINNED) CONVERSION** | **DONE** — `bms_to_msh_skinned`: version=2, flags bit1 has_skin; 24 B header + vertex records + 6 B/vertex skin + triangles + u32 bone_count + names; `read_msh` round-trips v1+v2. |
| 12 | **CHARACTER MANIFEST (bandit)** | **DONE** — committed `game/world/characters/bandit/`: skeleton.json (35 bones, xyzw, bind_world), 3 MSH v2 (sword 76v/134t/1 bone, part1 214v/276t/18, part2 556v/766t/17), 3 PNG (real `.ddj`), anims.tsv (16), 2 anim JSON (stand01/walk), npc_placements.tsv (60 rows/31 regions), provenance.json (sha256 of every input). |
| 13 | **NPC WORLD PLACEMENT** | **DONE** — 60 real `npcpos` rows for refid 1949 across 31 sectors; **2 on committed terrain 156x90** at world (1592.44, 3321.47) and (724.69, 3583.85) via `npc_to_world` (REF 156,89). |
| 14 | **PLAYER ASSETS** | **DONE at decoder level** — `chinaman_skel.bsk` (38 bones) and islamman (43) parse byte-exact; characterdata col52 maps player refids to `mob\china\*.bsr`; NO player manifest/rendering committed (NPC-only scope). |
| 15 | **JAVA CHARACTER INDEX** | **IMPLEMENTED** — `CharacterMeshIndex` (Android-free skeleton/meshes/placements/anims loaders + minimal JSON parser + `skinnedBindPositions` = Σ(w/Σw)·(R·v+t)); JVM structural test written. |
| 16 | **JAVA SKINNED RENDERER** | **IMPLEMENTED** — `StaticMeshAsset.parseSkinned` (MSH v2), `NativeWorldRenderer.drawCharacters` (static bind pose; placement theta = 0 UNKNOWN). |
| 17 | **ANDROID BUILD** | **NOT EXECUTED** — no JDK/Gradle/Android SDK in this environment. |
| 18 | **DEVICE TEST** | **NOT EXECUTED** — no device/emulator. |

---

## 1. What was proven (Python, executed here)

- **BSK** (`scripts/bsk_decoder.py`, 9 tests): 1,034/1,035 nonzero files
  byte-exhaust; census `{'exact': 1034, 'inexact': [mob_select.bsk], 'zero': 4}`;
  8-byte zero trailer. Proven samples: bandit 35, blackrobber 35, chinaman_skel 38,
  horse1 31, islamman 43.
- **BSR** (`scripts/bsr_decoder.py`, `test_phase18_bsr.py`): token stream at
  body@0x3C; bandit resolves 3 bmt + 3 bms + 16 ban + 1 bsk + 7 efp + 16 wav;
  `is_character` requires a `.bsk`; static bsrs (e.g. tre_tree03) deliberately not
  group-ordered.
- **BMS skin** (`scripts/bms_decoder.py::parse_skin_data`, 7 tests): 6 B/vertex,
  `0xFF` sentinel, single-influence `w2=0`; 7 fixtures; `bandit_part1` skvc=74 vs
  two_influence=127 (mesh-dependent, UNKNOWN).
- **Skeleton bind pose** (`scripts/skeleton.py`, 9 tests): `[x,y,z,w]` proven
  empirically; `bone_parents` acyclic/single-root; `bind_world` aligns bandit to
  real mesh bounds; bandit mesh bones ⊆ 35-skel.
- **BAN pose** (`scripts/animation_pose.py`, 10 tests): full keyframe parse;
  slerp/lerp evaluation; bandit_stand01 2000ms, bandit_walk 1333ms (irregular
  timestamps).
- **MSH v2** (`scripts/bms_to_asset.py::bms_to_msh_skinned`): 24 B header + skin
  records + bone table; `read_msh` round-trips v1+v2.
- **Manifest** (`scripts/build_character_manifest.py`, 17 tests): full bandit
  chain from `Media.pk2 characterdata` col1=refid/col52=model; provenance sha256
  over bsr/bsk/bmt/bms/ddj/bans; byte-identical rebuild.
- **Player**: `chinaman_skel.bsk` (`/prim/skel/char/china/`) and `islamman.bsk`
  parse byte-exact (DONE at decoder level); no committed player render assets.

## 2. New / changed files

- `scripts/bsk_decoder.py`, `scripts/bsr_decoder.py`,
  `scripts/skeleton.py`, `scripts/animation_pose.py`,
  `scripts/build_character_manifest.py` + fixtures + tests:
  `test_phase18_bsk.py` (9), `test_phase18_bsr.py`, `test_phase18_skin.py` (7),
  `test_phase18_skeleton.py` (9), `test_phase18_animation.py` (10),
  `test_phase18_character.py` (17); fixtures under
  `scripts/testdata/formats/{bsk_phase18.json,bsr_phase18.json,bms_skin_phase18.json,
  ban_phase18.json,bsk_samples/,bsr_samples/,bms_skin_samples/,ban_phase18_samples/}`.
- `android/app/src/main/assets/game/world/characters/bandit/` (committed):
  `skeleton.json`, `meshes.tsv`, `mesh/*.msh` (3, MSH v2), `tex/*.png` (3),
  `anims.tsv`, `anim/bandit_{stand01,walk}.json`, `npc_placements.tsv`,
  `provenance.json`.
- Java: `CharacterMeshIndex.java` (new), `StaticMeshAsset.java` (+`parseSkinned`
  / `SkinnedMesh`), `NativeWorldRenderer.java` (+`setCharacters`/
  `drawCharacters`/`drawTexturedTriangles`), `GameActivity.java` (load + overlay
  text); `CharacterMeshIndexTest.java` (JVM), `GameActivityTest.java`
  (+character assertion).
- `ANDROID_ASSET_DEPENDENCY_GRAPH.json` regenerated (26 edges: 9 textdata + 17
  asset; `.bsr→.ban/.bsk` new; `.bsk→bones` and `.bms→skeleton` upgraded
  VERIFIED; stale "12 B tail" edge removed).
- Docs: `FORMAT_RESEARCH.md`, `DATA_FORMAT_CATALOG.md`,
  `ANDROID_DATA_CONVERSION_STATUS.md` updated; this report added.

## 3. Tests

**TESTED here (Python, executed):** the 5 new Phase 18 suites (52 tests) plus the
full 24-suite regression — **294 tests, 13 skipped, OK** (~328 s; skips are the
pre-existing archive/device-gated ones).

**NOT EXECUTED:** `CharacterMeshIndexTest` (JVM), `GameActivityTest` (instrumented),
Gradle build, device/emulator run — no JDK/Android SDK in this environment.

## 4. Player pipeline status

- **DONE (assets/decoder):** `chinaman_skel.bsk` (38 bones) + `islamman.bsk` (43)
  parse byte-exact; `man_*` character models resolve via characterdata col52;
  the same proven pipeline (bsr→bsk/bms/ban/ddj) applies.
- **NOT claimed:** no committed player render manifest (NPC-only scope), and
  player rendering carries the SAME device-untested caveat as NPCs.
- **Missing evidence (explicit):** player `npcpos`/spawn placements were not
  selected; a player character's `.bsr` group order and skin subsets were not
  re-verified end-to-end (only the shared decoders were).

## 5. Deferred (honest boundaries)

- BSK `bone_type` u8 and origin/local transform semantics UNKNOWN.
- BSR 8×u32 header table semantics UNKNOWN.
- Vertex tail `u32@36` global bone_index UNKNOWN; `skinned_vertex_count`
  exact meaning mesh-dependent; weight normalization assumption documented.
- Runtime animation playback UNKNOWN (renderer is static bind pose; only first
  keyframes committed).
- `mob_select.bsk` outlier structure UNKNOWN.
- Renderer remains a 2D Canvas top-down flat/texture-triangle view; placement
  heading (theta) is 0 because npcpos carries no heading.
- Android build + device rendering: NOT EXECUTED (no JDK/SDK/emulator).
