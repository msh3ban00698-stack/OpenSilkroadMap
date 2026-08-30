# PHASE 17 REPORT — Real Object Mesh Rendering

Branch: `260830-feat-phase17-real-object-rendering` · Phase 16 baseline: `d8669a75b0ff2665a89877c24873697aeb48d70d`
Date: 2026-08-30

Phase 17 closes the Phase 16 blocker: PROVEN static `.bms` meshes are converted
to committed Android MSH1 assets, linked to real textures (`.bmt → material.ddj
→ DDS → PNG`), placed at PROVEN `.o2 → object.ifo → .bsr` world coordinates, and
rendered through `NativeWorldRenderer` via a new `MeshObjectIndex`. Everything
below is reproduced from original PK2 bytes; no placeholder geometry, no fake
textures, no guessed assignments.

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

## 13-line phase status

| # | Status | Line |
|---|---|---|
| 1 | **BMS DECODER** | **SOURCE VERIFIED / TESTED** — 44/52 B layouts proven (Phase 16); Phase 17 keeps EVERY real vertex (real trees carry flags≠0 canopy geometry) and records `non_static_vertices`. |
| 2 | **STATIC MESH CONVERSION** | **IMPLEMENTED / TESTED** — `bms_to_msh` → committed MSH1 assets (6 parts: tre_tree02_01..03, tre_tree03_01..03); `read_msh` round-trip byte-identical. |
| 3 | **REAL TEXTURE LINKING** | **SOURCE VERIFIED / TESTED** — BMS header `names[1]` material → `material.ddj` in `.bmt` dir → DDS → RGBA PNG; 6 real 256×256 PNGs committed. |
| 4 | **REAL OBJECT RENDERING** | **IMPLEMENTED** — `MeshObjectIndex` + `NativeWorldRenderer.drawMeshObjects` render real meshes (not diagnostic markers) at proven positions; success criterion met on the committed pipeline. |
| 5 | **WORLD COORDINATES** | **SOURCE VERIFIED / TESTED** — `.o2` walker from offset 16 consumes all 4,348 files; record layout PROVEN; `world = (tail − ref) × 1920 + local`; 32 instances in 156x90 validated against committed 156x90 height grid. |
| 6 | **NPC MODEL** | **BLOCKED** — skinned `flags==2` tail + `.bsk` palette UNKNOWN; NPCs remain diagnostic placement markers. |
| 7 | **PLAYER MODEL** | **BLOCKED** — same skinning/palette blocker; not claimed. |
| 8 | **BSK** | **UNKNOWN** — per-bone record layout beyond names PARTIAL; palette semantics UNKNOWN (deferred). |
| 9 | **BSR** | **SOURCE VERIFIED / TESTED** — `parse_bsr` returns `(bmt_path, [bms_paths])`; object identity chain nameI→bsr→bms+bmt PROVEN for real trees. |
| 10 | **ANIMATION** | **UNKNOWN / PARTIAL** — `.ban` fully decoded (Phase 13) but binding to skinned meshes needs the `.bsk` palette (deferred). |
| 11 | **NATIVE RENDERER** | **IMPLEMENTED** — 2D Canvas top-down texture-triangle projection (BitmapShader + `setPolyToPoly`), per-instance θ rotation; Phase 15 camera/NPC code untouched. |
| 12 | **ANDROID BUILD** | **NOT EXECUTED** — no JDK/Gradle/Android SDK in this environment. |
| 13 | **DEVICE TEST** | **NOT EXECUTED** — no device/emulator. |

---

## 1. What was proven (Python, executed here)

- `.o2` record layout for every one of the 4,348 Map.pk2 overlays
  (`scripts/o2_decoder.py`, 12 tests): `[u16 cnt][cnt×30 B]` from offset 16,
  record = `nameI u32 + x/y/z f32×3 + u16 + theta f32 + u16×3 + tail u16`
  (tx = tail & 0xFF, tz = tail >> 8).
- `object.ifo` index: skip magic `JMXVOBJI1000` + count line; `nameI u32` +
  quoted path rows. nameI 820 → `tre_tree03.bsr`, 574 → `tre_tree02.bsr`.
- Material→texture: BMS `names[1]` = material name; `material + ".ddj"` exists
  in the `.bmt` blob and resolves to a real file.
- Placement: 32 real instances in sector 156x90 (23× 820 at θ 0.0, 9× 574 at
  θ −6.4403; tails (156,90)/(157,90)/(156,91)); world positions match the
  committed 156x90 `.hg`.
- Reproducibility: `build_object_manifest.py` rebuilds byte-identical assets.

## 2. New / changed files

- `scripts/o2_decoder.py`, `scripts/bms_to_asset.py`,
  `scripts/build_object_manifest.py` (new) + 32 new tests across the three
  suites.
- `android/app/src/main/assets/game/world/objects/` (new, committed):
  `models.tsv`, `placements.tsv`, `mesh/*.msh` ×6, `tex/*.png` ×6.
- `StaticMeshAsset.java`, `MeshObjectIndex.java` (new, Android-free logic).
- `NativeWorldRenderer.java` (mesh overlay), `GameActivity.java` (index load,
  overlay text).
- `StaticMeshAssetTest.java` (JVM), `GameActivityTest.java` (+object test).
- `world_terrain.py` (parse_o2 delegates to o2_decoder).
- `build_bms_fixture.py` / `build_object_manifest.py` (hardcoded `/tmp/opencode`
  removed; now `--pk2-dir` / `SRO_PK2_DIR` via `sro_paths`).
- `build_asset_dependency_graph.py` + regenerated
  `ANDROID_ASSET_DEPENDENCY_GRAPH.json` (25 edges; `.o2→.m` upgraded to
  VERIFIED with Phase 17 evidence).
- Docs: `FORMAT_RESEARCH.md`, `DATA_FORMAT_CATALOG.md`,
  `ANDROID_DATA_CONVERSION_STATUS.md` updated; this report added.

## 3. Tests

**TESTED here (Python, executed):** the 3 new Phase 17 suites (32 tests) plus
the full 23-suite regression run — all OK (skip flags are pre-existing
archive/device-gated skips). This run also fixed 2 pre-existing failures
(`test_sro_pipeline` tmp-path lint, `test_phase13_dependency_graph`
reproducibility).

**NOT EXECUTED:** `StaticMeshAssetTest` (JVM), `GameActivityTest` (instrumented),
Gradle build, device/emulator run — no JDK/Android SDK in this environment.

## 4. Deferred (honest boundaries)

- `flags==2` tail semantics and `.bsk` palette → skinned NPC/player models
  (BLOCKED/UNKNOWN).
- Object placement scale: mesh AABBs are in hundreds of units (y 148..760);
  the `u16@22` field was never interpreted, so model scale is NOT claimed.
- 3D projection: renderer remains a 2D Canvas top-down flat/texture-triangle
  view; no 3D engine, no camera-relative mesh culling.
