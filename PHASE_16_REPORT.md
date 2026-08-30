# PHASE 16 REPORT — Real Mesh Decoding (`.bms` Vertex Layout Proven)

Branch: `260830-feat-phase16-real-model-decoding` · Phase 15 baseline: `722c2e5`
Date: 2026-08-30

Phase 16 attacks the #1 blocker from Phase 15: the `.bms` static-mesh vertex
layout. The Phase 13 "non-integral stride" anomaly is **resolved as a reading
error** and the vertex format is now **PROVEN** at 44 B (standard) and 52 B
(lightmap) across a full-census classification of all 22,684 `Data.pk2` BMS
files. Everything below is reproduced from real archive bytes; nothing is
fabricated.

---

## Status vocabulary

- **SOURCE VERIFIED** — real data confirmed from the ORIGINAL VSRO-R 1.193 archives.
- **IMPLEMENTED** — native code committed and structurally verified.
- **PARTIAL** — a proven subset works; the rest is documented.
- **BLOCKED** — cannot proceed without missing evidence/decoder.
- **UNKNOWN** — no honest claim possible yet.
- **TESTED** — executed here (Python) and passing.
- **NOT EXECUTED** — not run in this environment (no JDK/SDK/emulator).

---

## 1. Starting point

- **Phase 15 SHA:** `722c2e5aa1d35e4656fd0baf3cce0343058f25c6`
- **Branch:** Phase 16 created from Phase 15 HEAD on a dedicated branch.

## 2. The `.bms` vertex-layout breakthrough

### The Phase 13 error, corrected

Phase 13 measured `vertex stride = (s2 − s0 − 4) / vertex_count` (vertex section
bounded by **s2 = offset@0x14**) and got 52.11 B for the demon mesh. The correct
vertex section ends at **s1 = offset@0x10** (the *bone-table* section start):

```
vertex stride = (u32@0x10 − header_size − 4) / vertex_count     # PROVEN
```

Re-measured across all 22,684 BMS files, the stride resolves to exactly
**44.00 B** (17,258 files) or **52.00–52.21 B** (≈5,400 files; the 52.21
residuals are trailing bytes after the vertex array, not stride). 3 files read
0.00 B (placeholder/empty).

### Full-census classification (classifier == full parser, counts identical)

| class | count | vertex_size | notes |
|---|---|---|---|
| standard | 17,247 | 44 B | pos + normal + uv + 12 B tail |
| lightmap | 5,399 | 52 B | + uv2 (lightmap) + 12 B tail |
| morph80 | 5 | 80 B | 4 f32 weight streams (morph/skin) |
| morph_trailing | 1 | 80 B + trailing | 80 B + trailing bytes |
| unproven | 32 | — | triangle section unparseable |

### Proven vertex record layouts

```
44 B "standard"  (17,247 files: items, nature, mob, npc, bldg, dun, artifact)
   0   3x f32  position
  12   3x f32  normal        (unit-length verified across 44/44.5/45/50 samples)
  24   2x f32  uv
  32   f32     blend_weight  (0.0 = unskinned)
  36   u32     bone_index    (0xFFFFFFFF = none; 0..N skinned)
  40   u32     flags         (0 = unskinned, 2 = skinned/flagged)

52 B "lightmap"  (5,399 files: bldg/dungeon with lightmap UV)
   0   3x f32  position
  12   3x f32  normal        (unit-length verified)
  24   2x f32  uv
  32   2x f32  uv2           (lightmap UV; 0.02..1e9 across v52_bldg sample)
  40   f32     0.0 ; u32 0xFFFFFFFF ; u32 0
```

## 3. Bone table, triangles, AABB (PROVEN)

- s1 bone table: `u32 bone_count` + per-bone `u32 name_len` + name + transform
  data. Chicken 14 bones (`Bip01 Spine`, …), char_face 5, item_shield 1
  (`Bone01`), nature_tree / artifact / bldg = 0.
- s2 triangles: `u32 tri_count` + `tri_count x 3 x u16` LE indices; every index
  `< vertex_count` (verified on all 11 hermetic samples).
- s5 AABB: 6 x f32 `(minx,miny,minz,maxx,maxy,maxz)`; min ≤ max and bounds
  contain every decoded vertex (verified on all samples).

## 4. Skinning tail semantics — UNKNOWN (honestly bounded)

The 12 B tail of `flags == 2` vertices is **NOT a local bone index**:

- `npc_chicken` has `bone_count = 14` yet tail u32@36 reaches **3..96**.
- `nature_tree` has `bone_count = 0` yet 19/36 vertices carry `flags = 2` and
  u32@36 ∈ **8..34 with duplicates**; those vertices sit at the tree crown
  (y 15.5..220) — consistent with leaf/billboard payload, not skinning.

**Static rendering is unaffected**: unflagged (`flags == 0`) vertices of
standard/lightmap meshes give complete, proven position/normal/uv[/uv2] +
index-buffer geometry. The tail is surfaced as raw PARTIAL data and excluded
from the static conversion path. Decodable skinning/skeleton attachment requires
the original runtime (or matching palette tables) — documented, not guessed.

## 5. `.bsk`/`.bsr`/`.ban` relationship (status carried forward)

- `.bsk` `JMXVBSK 0101` skeleton: bone names (`[root]`, `Bip01*`, `BoneNN`)
  confirmed; count@12 is **not** a plain bone-name count (chicken: 28 vs 14
  mesh bones) — the per-bone record layout remains PARTIAL.
- `.bsr` `JMXVRES 0109` links `.bmt` materials and `.bms` mesh parts (Phase 13).
- `.ban` `JMXVBAN` is fully decoded (Phase 13); keyframes are quat+pos.

The animation/skinning pipeline (`bms flags==2` → `bsk` palette → `ban`) is the
Phase 17 entry point; no fabricated skinning is implemented.

## 6. New / changed files

- `scripts/bms_decoder.py` (new) — parse (header/sections/bones/triangles/AABB/
  vertices), classify (standard/lightmap/morph/unproven), 44/52 layout decode.
- `scripts/build_bms_fixture.py` (new) — regenerates committed hermetic fixtures
  from the live archive (extracted fragments, never the PK2 archives).
- `scripts/testdata/formats/bms_phase16.json` (new) — extracted sample summaries.
- `scripts/testdata/formats/bms_samples/*.bms` (new, 11 raw samples) — hermetic
  offline test data (nature_tree, npc_chicken, char_face, item_shield,
  artifact_table, bldg_tree, v50_avatar, v52_bldg, v44p5, petra, demon).
- `scripts/test_phase16_bms.py` (new, 16 tests) — hermetic samples + fixture +
  live-archive census (archive-gated with skip).
- `scripts/test_phase14_world_runtime.py` (fixed) — stale Phase 15 assertion
  (10→16 asset edges, 19→25 total edges).
- `FORMAT_RESEARCH.md` — `.bms` section rewritten with the corrected layout.
- `DATA_FORMAT_CATALOG.md` — `.bms` row updated (PROVEN subset + UNKNOWN tail).
- `ANDROID_DATA_CONVERSION_STATUS.md` — `.bms` row updated.
- `ANDROID_ASSET_DEPENDENCY_GRAPH.json` — 2 new asset edges (16 total):
  `.bms → vertices+triangles` (VERIFIED), `.bms flags==2 → skeleton` (PARTIAL).

## 7. Tests

**TESTED here (Python, executed):**

- `scripts/test_phase16_bms.py` — 16 tests, all OK (11 hermetic sample tests +
  fixture tests + live census 17,247/5,399/5/1/32).
- Regression re-run green: `test_phase13_bms` (12), `test_phase13_ban` (8, 1
  skipped), `test_phase13_bsk_bsr` (9), `test_phase13_efp` (11),
  `test_phase13_nvm` (5, 1 skipped), `test_phase13_npcpos_regions` (14),
  `test_phase13_world_relations` (16), `test_phase13_worldmap_resolution` (6, 1
  skipped), `test_phase14_world_runtime` (16, after fixing the stale Phase 15
  assertion), `test_phase15_world_integration` (12), `test_world_terrain` (19, 1
  skipped), `test_pk2_reader` (11).

**NOT EXECUTED (no JDK/Android SDK):** all JVM/instrumented tests and Gradle
builds. No Phase 16 Java/Android code was introduced (Phase 16 is decode-only);
mesh → `NativeWorldRenderer` integration is deferred to Phase 17.

## 8. Android build + runtime

- **Build: NOT EXECUTED** — no JDK/Gradle/Android SDK.
- **APK execution: NOT EXECUTED** — no device/emulator.
- **Performance: NOT EXECUTED** — no benchmarks invented.

## 9. Remaining classification summary

- **PROVEN (new):** `.bms` vertex layout (44 B standard / 52 B lightmap), bone
  table, triangle index buffer, AABB; classifier == parser across all 22,684
  files.
- **BLOCKED:** real object/NPC model rendering in `NativeWorldRenderer`
  (deferred to Phase 17 — static `.bms → mesh` conversion + placement via
  `.o2`/`.bsr`); skinning/animation (`bms flags==2` tail semantics UNKNOWN).
- **UNKNOWN:** `flags==2` tail payload; 80 B morph fields; 7th header offset;
  trailing bytes; `.bsk` per-bone record layout; `.nvm` nav-cell semantics;
  `.o2` variable header layout.

## 10. What Phase 17 should do

1. Convert proven static `.bms` meshes to an Android-friendly format and wire
   real objects into `NativeWorldRenderer` at `.o2`/`.bsr`-derived positions.
2. Resolve the `flags==2` tail (external skeleton/palette) and `.bsk` palette
   tables to unlock skinned NPCs; replace diagnostic NPC markers with real
   models at verified `npcpos` positions.
3. Extend multi-sector world to full region streaming + runtime transitions.
4. Run the real Gradle build + instrumented tests in a JDK/Android SDK environment.
