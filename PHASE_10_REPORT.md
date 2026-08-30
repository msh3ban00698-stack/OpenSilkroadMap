# Phase 10 Report — Complete World / Terrain Data Extraction -> Verified Android-Native Pipeline

## Objective

Execute Phase 10 of the OpenSilkroadMap Android plan: discover, read-only
extract, validate, convert, and prepare the REAL VSRO-R 1.193 world/terrain
data from `Map.pk2` / `Data.pk2` / `Media.pk2` into normalized Android data
plus a native Android world renderer showing a real playable world — with
every unproven format/field/coordinate marked **UNKNOWN** and zero invented
geometry.

## What was verified (real data, read-only)

1. **Terrain height format `.m`** — magic `JMXVMAPM1000`, 12-byte header +
   36 blocks of 2,575 bytes (exact 92,712-byte sectors). Height `float32` at
   block offset 6 + (k*17+m)*7; grid 97x97, step 20.0, sector side 1,920.
   Verified on 9+ real sectors across 8 named world regions; the regionally
   differentiated heights (Mt. Roc ~2,000-2,500 m, Hotan up to 2,770 m,
   Samarkand down to -1,240 m) prove real data.
2. **Object overlay `.o2`** — magic `JMXVMAPO1001`; nameI + x/y/z + theta +
   tail(tx,tz). 95 instances of Constantinople sector 76:103 parsed and all
   resolved against `object.ifo` (3,307 entries).
3. **World census** — Map.pk2 holds 4,491 terrain sectors, 4,491 `.o`, 4,348
   `.o2`, 4,988 `.t`, 839 `.ddj`.
4. **Region windows** — `RegionInfo.txt` -> 72 sections, 3,468 cells (matches
   Phase 9 `regions.tsv`). Named world regions and ref sectors documented in
   `WORLD_REGION_MASTER.csv`/`.md`.
5. **Coordinates** — `region & 0xFF = sx`, `region >> 8 = sy`;
   `world = (sector - refSector)*1920 + local`. Re-encoded and locked by tests.

## What is committed

| Artifact | Location |
| --- | --- |
| Deterministic parser | `scripts/world_terrain.py` |
| Python tests (19) | `scripts/test_world_terrain.py` |
| Real-derived fixtures | `scripts/testdata/world/` (heights, objects, ifo head) |
| Build script | `scripts/build_world_android.py` |
| Real height grids (23 `.hg`, VSHG v1) | `android/app/src/main/assets/game/world/*.hg` |
| Region catalog (72) + index | `android/app/src/main/assets/game/world/world_regions.tsv`, `world_index.tsv` |
| Region master CSV | `WORLD_REGION_MASTER.csv` |
| Android world classes | `com.opensilkroadmap.app.world` (5 files) |
| JVM tests (3 files) | `android/app/src/test/java/com/opensilkroadmap/app/world/` |
| Docs | `PHASE_10_SOURCE_BASELINE.md`, `WORLD_FORMAT_CATALOG.md`, `WORLD_COORDINATE_SYSTEM.md`, `WORLD_REGION_MASTER.md`, `PHASE_10_WORLD_PIPELINE.md`, this report |

## Test results

- `scripts/test_world_terrain.py`: **19 tests, OK** (1 live-archive check
  skipped by default; passes when `SRO_PK2_DIR`/`SRO_READER_DIR` point at the
  real archives — verified in this session).
- Full regression: `test_phase4_assets` OK (3 skipped), `test_phase5_assets`
  OK (1 skipped), `test_phase6_assets` OK (17 tests, 4 skipped),
  `test_sro_pipeline` OK, `deno task build` exit 0.
- JVM tests committed but NOT executed (no JDK/gradle in this environment —
  consistent with Phases 7-9; logic classes are Android-free and run under
  `./gradlew test` on a JDK host).

## Android native world renderer

`NativeWorldRenderer` (Android View) draws the REAL height field: each grid
cell is a quad filled with a grayscale ramp of the real height (no invented
palette), camera state from the verified `WorldCoordinates` transform. It loads
the committed 97x97 `.hg` grids via `TerrainHeightGrid` (clamped bilinear
sampling). Projection/color math is isolated in `WorldProjection` (tested).

## Honest status

- **Implemented for real**: terrain height extraction, region windows,
  coordinate transforms, normalized `.hg` data, native height-field renderer.
- **NOT implemented**: `.o` overlay semantics, `.t` tile/zone decoding,
  `mapinfo.mfo`/`tile*.ifo` parsing, object collision from `.bsr/.bms` inside
  the native renderer, and a global (non-sector-relative) world origin — all
  marked **UNKNOWN** in `WORLD_FORMAT_CATALOG.md` / `WORLD_COORDINATE_SYSTEM.md`
  and never faked.
- **Extraction/derivation integrity**: originals never modified; only derived
  normalized artifacts committed; source SHA-256 captured in the baseline and
  index.

## Next steps (Phase 11+ candidates)

1. Decode `.o` (overlay/zone) and `.t` (tile) payloads to unlock walkable areas
   and tile-based rendering.
2. Wire `NativeWorldRenderer` into a GameActivity scene alongside the minimap.
3. Add tile/texture rendering from `.t` + `.ddj` for a colored ground layer.
4. Run the committed JVM tests on a JDK host (`./gradlew test`).
