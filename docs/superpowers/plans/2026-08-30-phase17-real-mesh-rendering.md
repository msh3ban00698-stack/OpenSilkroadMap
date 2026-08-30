# Phase 17: Real Static Mesh Conversion + Native World Rendering

**Goal:** Convert REAL proven BMS mesh geometry into Android runtime mesh assets and render them through `NativeWorldRenderer` at verified world coordinates.

**Architecture:** Offline Python pipeline (executed, deterministic) proves the full chain `o2 → object.ifo → bsr → bms/bmt → ddj → DDS → RGBA`, converts real meshes to a compact binary asset (`.msh`) and textures to PNG, and commits a manifest + assets. Android Java (structural, NOT EXECUTED) parses the assets and draws real triangles flat-shaded from real normals.

**Tech Stack:** Python 3.11 (pk2_table, world_terrain, bms_decoder, dds_decode), Java (Android Canvas), unittest.

## Global Constraints

- Continue ONLY from Phase 16 HEAD `d8669a7`; preserve all Phase 10–15 work.
- No placeholder/fake geometry; every model→texture→material link PROVEN from original archive bytes.
- Native Android Canvas only (no WebView/JS/EXE).
- JDK/Gradle unavailable → Android build/tests reported NOT EXECUTED; executed gate = Python unittest.
- UNKNOWN stays UNKNOWN; flags==2 tail semantics remain documented as UNKNOWN.
- Feature branch `260830-feat-phase17-real-object-rendering`; secret-scan staged diff; commit; push; verify SHA.

## Proven facts this plan builds on (Phase 17 forensics, live archives)

- `.o2` record = `[u16 count][count x 30-byte instance]` from offset 72; instance =
  `nameI u32@0, x,y,z f32@4/8/12, tail u16@28 (tx=tail&0xFF, tz=tail>>8)`; positions are
  LOCAL to sector (tx,tz); y ≈ real terrain height (validated 2.7..32.5 diff).
- Sector 156x90 `.o2` = 32 instances: nameI 574 (tre_tree02) x9, nameI 820 (tre_tree03) x23.
- `object.ifo` (3307 entries) maps nameI → bsr path (820→`/res/nature/common/tree/new-maple/tre_tree03.bsr`, 574→`/res/nature/common/tree/tre_tree02.bsr`).
- `.bsr` → bmt + bms parts (each tree: 3 parts; standard 44 B; 0-1 bones).
- `.bmt` → ddj filename resolved in bmt dir (`prim/mtrl/nature/common/tree/new-maple/tre_tree03_01.ddj`).
- `.ddj` → DDS → RGBA (256x256) via `dds_decode.ddj_to_rgba` + `png_from_rgba`.

## File structure

- Create `scripts/o2_decoder.py` — .o2 parser + object.ifo index.
- Create `scripts/bms_to_asset.py` — BMS → `.msh` binary converter.
- Create `scripts/build_object_manifest.py` — full chain → `world/objects/manifest.tsv` + placements.
- Create `scripts/test_phase17_o2.py`, `scripts/test_phase17_conversion.py` — executed tests.
- Create `android/app/src/main/java/com/opensilkroadmap/app/world/StaticMeshAsset.java`, `MeshObjectIndex.java`, `ObjectMesh.java`.
- Modify `NativeWorldRenderer.java`, `GameActivity.java`.
- Create JVM tests `StaticMeshAssetTest.java`, `MeshObjectIndexTest.java`, instrumented `GameActivityTest` additions.
- Assets under `android/app/src/main/assets/game/world/objects/`.
- Update `FORMAT_RESEARCH.md`, `DATA_FORMAT_CATALOG.md`, `ANDROID_ASSET_DEPENDENCY_GRAPH.json`, `PHASE_17_REPORT.md`.

## Tasks

### Task 1: `scripts/o2_decoder.py` + tests
Parser for `.o2` (proven layout) and `object.ifo` index. Public API:
- `parse_object_ifo(text) -> {nameI: bsr_path}` (reuse/extend `world_terrain.parse_object_ifo`)
- `parse_o2(blob, index) -> [Placement(nameI, x, y, z, tx, tz, rotation_fields)]` walking `[u16 cnt][cnt x 30B]` from offset 72.
- `Placement` as a small class or dict.
Tests: consume exactly 32 instances for 156x90; tail tx/tz in {156,157}x{90,91}; all nameI resolve in object.ifo; y within 60 of committed-terrain height for 156x90-local placements.

### Task 2: `scripts/bms_to_asset.py`
- `bms_to_msh(bms_bytes, texture_index) -> bytes` writing `MSH1` container:
  `4B 'MSH1', u8 version=1, u8 layout(0=std44,1=lightmap52), u16 flags, u32 vcount, u32 tcount, u16 tex_index, u16 reserved, then per-vertex pos(3f)+normal(3f)+uv(2f) [+uv2(2f) if lightmap], then u16 indices`.
- Only flags==0 (unskinned) vertices; indices remapped to surviving vertices; flagged vertices (flags==2) excluded and reported.
- `read_msh(bytes) -> dict` for round-trip tests.
- Tests: round-trip pos/normal/uv/indices equality; flagged-vertex exclusion; lightmap uv2 preserved; deterministic byte-identical output.

### Task 3: `scripts/build_object_manifest.py`
- Resolves, for the committed sector set, every o2 instance → model asset + texture asset, writes:
  - `world/objects/manifest.tsv` (nameI, bsr, bms part -> .msh asset, ddj -> png asset, layout, vcount, tcount)
  - `world/objects/o2_<sx>_<sy>.tsv` (per-instance nameI, x, y, z, tx, tz)
  - writes `.msh` + `.png` files into assets dir.
- Tests: manifest rows resolve to real files; per-object geometry from bms equals converted asset geometry; texture png exists and is valid PNG.

### Task 4: Java (Android-free) + renderer wiring
- `StaticMeshAsset` parses `MSH1`.
- `MeshObjectIndex` loads placements + manifest.
- `NativeWorldRenderer` gains `setMeshObjects(...)` and draws each object's triangles flat-shaded from real normals (projected top-down); toggles.
- `GameActivity` loads objects overlay for the active world.
- JVM + instrumented tests (structural).

### Task 5: Docs, report, branch, push
- Update FORMAT_RESEARCH / DATA_FORMAT_CATALOG / dependency graph.
- `PHASE_17_REPORT.md` with the required status matrix.
- Branch, secret-scan, commit, push, verify SHA.
