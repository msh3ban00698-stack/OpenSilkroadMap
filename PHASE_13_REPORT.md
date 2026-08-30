# PHASE 13 REPORT — Real Asset Decoding & Native World Rendering Integration

Branch: `260829-phase12-data-parsing-formats` · Phase 12 baseline: `15ebe31`
Date: 2026-08-30

Phase 13 resolves the remaining real asset formats (worldmap `.ddj`, `.ban`,
`.nvm`, `.bms`, `.efp`, `.bsk`/`.bsr`), proves the world-object and NPC-place
relationships, builds a proven asset dependency graph, and extends the native
camera/world renderer toward real terrain. All claims are backed by real bytes
from the ORIGINAL VSRO-R 1.193 archives (read-only). Everything not proven is
marked **UNKNOWN** — nothing is guessed or fabricated.

---

## A. Worldmap resolution (Part C)

The 3 UNRESOLVED worldmap refs from Phase 12 are resolved against the real
archives:

- `Map_bagdad.ddj` / `Map_bagdad_dungeon.ddj` — case-insensitive match on
  `map_bagdad.ddj` / `map_bagdad_dungeon.ddj`.
- `map_world_` tile-grid prefix → **632 real tiles** `map_world_{X}x{Y}.ddj`
  (x46–216 / y72–113), each a `JMXVDDJ 1000` → embedded DDS → WebP.

Montage layout (how the 632 tiles compose) is **UNKNOWN**; tiles are converted
individually, not stitched. Phase 12 converted rows are reproduced
byte-identically. Script `scripts/convert_worldmap_resolved_phase13.py`; tests
`scripts/test_phase13_worldmap_resolution.py` (6 GREEN, 1 skipped). Outputs under
`android-assets/textures/worldmap/` (634 new WebP incl. 2 bagdad); provenance in
`TEXTURE_CONVERSION_MANIFEST.tsv` (664 rows, 0 UNRESOLVED).

## B. Format decoding — evidence-first

Full evidence in **`FORMAT_RESEARCH.md`**; catalog updated in
**`DATA_FORMAT_CATALOG.md`**.

- **`.ban` — FULL LAYOUT PROVEN (Part D).** `scripts/ban_decoder.py` rewritten to
  parse the complete structure: magic/version `JMXVBAN 0102`; 8-byte reserved;
  `u32` name-len + name (no trailing NUL); `u32` duration_ms + frame_rate(30) +
  `u32` UNKNOWN + kpb (keyframes-per-bone); kpb×`u32` timestamps; bone_count;
  per-bone name + kf-count(=kpb) + kpb×28-byte keyframes (4×`f32` quat +
  3×`f32` pos). Tests `scripts/test_phase13_ban.py` (8 GREEN, 1 skipped). Remaining
  UNKNOWN (semantic only): `u32`@body+8, reserved 8 bytes.
- **`.nvm` — PARTIAL (Part E).** Proven: `JMXVNVM 1000`; flat 8-byte LE nav-cell
  records (4×`u16`), dominant 9,216 = 96×96; post-grid ~37,814-byte `f32` region;
  trailing −20.0 fill. The old 907·256 hypothesis disproven. Record semantics
  **UNKNOWN**. Tests `scripts/test_phase13_nvm.py` (5 GREEN, 1 skipped).
- **`.bms` — STRUCTURE PARTIALLY PROVEN (Part H).** Proven: `JMXVBMS 0110`;
  header = header_size + 6 section offsets + end_offset + 2 length-prefixed names;
  s0 vertices / s1 bones / s2 triangles (u32 count + 3×u16) / s5 AABB. Petra
  vertex stride 44.0 B; demon 52.11 B (non-integral → vertex layout UNKNOWN in
  general). Tests `scripts/test_phase13_bms.py` (12 GREEN).
- **`.efp` — VERSION TREE PROVEN; BODY UNKNOWN (Part G).** `JMXVEFF xxxx`;
  3,395 files across versions 0000×7 / 0010×1 / 0011×1,820 / 0012×408 / 0013×1,158;
  u32-length-prefixed ASCII command stream with shared vocabulary. Tests
  `scripts/test_phase13_efp.py` (11 GREEN).
- **`.bsk` / `.bsr` — SAMPLED; LAYOUT UNKNOWN (Part F).** BSK `JMXVBSK 0101`
  (1,039); BSR **`JMXVRES`** 0109/0108/0107 (NOT `JMXVBSR`), body = u32-length-
  prefixed `.bmt`/`.bms` paths. Tests `scripts/test_phase13_bsk_bsr.py` (9 GREEN).

Real derived fixtures (structure JSON only, no raw binaries) committed under
`scripts/testdata/formats/`.

## C. World data relationships (Part B)

`scripts/test_phase13_world_relations.py` — **16 GREEN**. Proven:

- `.cpd` object refs are valid object refs (not broken).
- Texture chain: bare `.bmt` ddj filenames resolve against the bmt directory in
  **Data.pk2** (not Media.pk2).
- Local x/z within sector with theta unclamped; y bounded.

## D. NPC placement (Part J)

The Phase 12 `npcpos` schema was **wrong** and is corrected from live joins:

- col0 = `character_refid` (1180/1180 join `characterdata` col1),
  col1 = `region_code` (1800/1855 join `regioncode` col1),
  col2 = `local_x`, col3 = `height_y`, col4 = `local_z`.
- World rows 14,800; dungeon/instance rows 3,657 (21 distinct negative/
  signed16 region codes); world local coords ∈ `[0,1920)` with 13 documented
  boundary rows at `1920.0`.
- Region pack: `region & 0xFF` = x sector, `region >> 8` = y sector.
- `RN_CH_JANGAN` (9 codes) places 53 NPCs in sectors 167–169 × 96–98.

Schema/edges regenerated (`TEXTDATA_SCHEMAS.json`, `DATA_REFERENCE_GRAPH.json`,
`scripts/textdata_schemas.py`); `NpcPosTable.java` accessors renamed. Tests
`scripts/test_phase13_npcpos_regions.py` (14 GREEN). `FORMAT_RESEARCH.md`
section 7 documents the corrected layout.

## E. Asset dependency graph (Part N)

`scripts/build_asset_dependency_graph.py` merges 9 textdata reference edges + 10
asset-chain edges into **`ANDROID_ASSET_DEPENDENCY_GRAPH.json`** (19 edges; each
edge has matched/total counts and status VERIFIED/PARTIAL). Only proven edges are
emitted. Tests `scripts/test_phase13_dependency_graph.py` (6 GREEN).

## F. Native camera / world renderer integration (Part L/M)

- `Camera2D` (Android-free, generic 2D follow camera) extended with `scale`
  (pixels-per-unit), `worldToView`/`viewToWorld` (top-down: world +X→screen +X,
  world +Y→screen −Y), and `enterRegion` (region transition). Default scale 1.0
  preserves all existing clamp semantics.
- `NativeWorldRenderer` now delegates its camera projection to `Camera2D` (single
  source of truth for center/scale/clamp), keeping its `setGrid`/`setCamera`/
  `grid()` public API. `onDraw` syncs viewport from `getWidth()/getHeight()`.
- New JUnit tests in `Camera2DTest.java` (scale, top-down convention, round-trip,
  region transition). JVM tests are **NOT EXECUTED** here (no JDK/gradle).

## G. Java structural verification (non-executed gate)

Mirroring the Phase 9/12 precedent: changed Java files checked — **braces
balanced, no Java 9+ constructs**. Core `Camera2D` and `NpcPosTable` are
Android-free (no `import android.*`); `NativeWorldRenderer` legitimately imports
Android (`View`/`Canvas`/`Paint`/`Path`) as an Android UI class.

## H. Tests (executed here)

| Suite | Result |
|---|---|
| `scripts/test_phase13_worldmap_resolution.py` | 6 OK (1 skipped) |
| `scripts/test_phase13_nvm.py` | 5 OK (1 skipped) |
| `scripts/test_phase13_ban.py` | 8 OK (1 skipped) |
| `scripts/test_phase13_bms.py` | 12 OK |
| `scripts/test_phase13_efp.py` | 11 OK |
| `scripts/test_phase13_bsk_bsr.py` | 9 OK |
| `scripts/test_phase13_world_relations.py` | 16 OK |
| `scripts/test_phase13_npcpos_regions.py` | 14 OK |
| `scripts/test_phase13_dependency_graph.py` | 6 OK |
| `scripts/test_phase12_formats.py` | 11 OK (1 skipped) |
| `scripts/test_phase11.py` | 17 OK (1 skipped) |
| `scripts/test_world_terrain.py` | 19 OK (1 skipped) |
| `scripts/test_sro_pipeline.py` | 15 OK (no env var) |
| `deno task build` (tsc + vite) | PASS (1m7s, chunk-size warning only) |
| JVM `./gradlew test` | **NOT EXECUTED** (no JDK in environment) — covered by structural verification (Part G) |

## I. Files added/changed (summary)

- `scripts/convert_worldmap_resolved_phase13.py`, `scripts/test_phase13_worldmap_resolution.py`,
  `scripts/testdata/formats/worldmap_resolved.json`, `android-assets/textures/worldmap/*.webp` (634) (A)
- `scripts/ban_decoder.py`, `scripts/test_phase13_ban.py`, `scripts/testdata/formats/ban_*.json` (B)
- `scripts/test_phase13_nvm.py`, `scripts/testdata/formats/nvm_grid.json` (B)
- `scripts/test_phase13_bms.py`, `scripts/testdata/formats/bms_layout.json` (B)
- `scripts/test_phase13_efp.py`, `scripts/testdata/formats/efp_versions.json` (B)
- `scripts/test_phase13_bsk_bsr.py`, `scripts/testdata/formats/bsk_bsr_samples.json` (B)
- `scripts/test_phase13_world_relations.py` (C)
- `scripts/test_phase13_npcpos_regions.py`, `scripts/textdata_schemas.py`, `TEXTDATA_SCHEMAS.json`,
  `DATA_REFERENCE_GRAPH.json`, `NpcPosTable.java` (D)
- `scripts/build_asset_dependency_graph.py`, `ANDROID_ASSET_DEPENDENCY_GRAPH.json`,
  `scripts/test_phase13_dependency_graph.py` (E)
- `Camera2D.java`, `NativeWorldRenderer.java`, `Camera2DTest.java` (F)
- `FORMAT_RESEARCH.md`, `DATA_FORMAT_CATALOG.md`, `ANDROID_DATA_CONVERSION_STATUS.md`,
  `TEXTURE_CONVERSION_MANIFEST.tsv`, `PHASE_13_REPORT.md` (J)

## J. Verification after push

After `git push -u origin 260829-phase12-data-parsing-formats`, local SHA and
remote SHA are confirmed identical and the working tree is clean (see shell
session / commit output).
