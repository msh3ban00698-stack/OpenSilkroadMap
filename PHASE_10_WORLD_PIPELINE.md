# Phase 10 — World Data Pipeline (Verified, End-to-End)

The complete, reproducible pipeline from the REAL VSRO-R 1.193 archives to a
committed, Android-native, verified world/terrain dataset. Every stage is
read-only with respect to originals and is validated by tests before the next
stage proceeds (DISCOVER -> INSPECT -> PARSE -> VALIDATE -> TEST -> DOCUMENT).

```
Map.pk2 /Data.pk2 (read-only)
   |
   | 1. DISCOVER  - pk2_mate list (pinned reader)
   v
Archive listing + RegionInfo.txt
   |
   | 2. INSPECT   - per-file byte/format inspection on extracted samples
   v
Verified format layouts (.m, .o2, object.ifo, .bsr/.bmt/.bms, .ddj)
   |
   | 3. PARSE     - scripts/world_terrain.py (committed, deterministic)
   v
Parsed heights / objects / coordinates
   |
   | 4. VALIDATE  - real-sector verification matrix (9+ sectors), region windows
   v
Validated normalized data
   |
   | 5. TEST      - scripts/test_world_terrain.py (19 tests, incl. live archive check)
   v
Committed derived dataset (android/app/src/main/assets/game/world/)
   |
   | 6. DOCUMENT  - this doc + PHASE_10_SOURCE_BASELINE.md, WORLD_FORMAT_CATALOG.md,
   |              WORLD_COORDINATE_SYSTEM.md, WORLD_REGION_MASTER.md/.csv,
   |              PHASE_10_REPORT.md
   v
Android-native renderer (real heights) + JVM tests
```

## Stage 1 — Discover

- `pk2_mate list -a Map.pk2` -> full listing (19,264 lines): 87 sector dirs,
  4,491 `.m`, 4,491 `.o`, 4,348 `.o2`, 4,988 `.t`, 839 `.ddj`.
- `pk2_mate list -a Data.pk2` -> located `RegionInfo.txt`, `navmesh/object.ifo`.
- Census and paths recorded in `PHASE_10_SOURCE_BASELINE.md`.

## Stage 2 — Inspect

Read-only extraction of real samples (kept in `/tmp`, never committed):
- 9+ terrain sectors across 8 named world regions + Constantinople cluster.
- `RegionInfo.txt`, `object.ifo` (3,307 bsr entries).
- `.o2` of Constantinople sector 76:103 (95 instances, all resolve).

Magic/layout inspection produced the tables in `WORLD_FORMAT_CATALOG.md`.
Fields not proven are marked **UNKNOWN** and never guessed.

## Stage 3 — Parse

`scripts/world_terrain.py` — deterministic parser module encoding the verified
layouts:
- `parse_terrain_m(blob)` -> 97x97 height grid.
- `parse_object_ifo(text)` -> bsr path list.
- `parse_o2(blob, index)` -> instance dicts (nameI, x/y/z, theta, tx/tz, bsr).
- `parse_bsr` / `parse_bmt` / `parse_bms_build` / `ddj_to_dds` (reused/cross-checked
  from the web-era pipeline).
- Verified coordinate transforms (region pack/unpack, sector->world, npc->world).
- `.hg` (VSHG v1) normalized container `write_hg` / `read_hg`.

## Stage 4 — Validate

- Every `.m` must match magic + exact 92,712-byte layout or raise.
- Real-sector verification matrix (8 world regions) in
  `PHASE_10_SOURCE_BASELINE.md` shows strongly differentiated real heights
  (Mt. Roc ~2000-2500 m down to Samarkand -1240 m).
- Region windows recomputed from RegionInfo.txt and cross-checked against the
  Phase 9 `regions.tsv` counts (72 sections / 3,468 cells).

## Stage 5 — Test

`scripts/test_world_terrain.py`: 19 tests (16 format/coordinate tests over
committed real-derived fixtures, 3 committed-Android-asset tests, 1 live
archive check gated on `SRO_PK2_DIR`/`SRO_READER_DIR`). Result: OK (1 live
skipped by default). The live check re-extracts the real `76.m` from Map.pk2
and verifies it matches the committed fixture.

Java JVM tests (committed, not executed here — no JDK in the build env, same
as Phases 7-9): `TerrainHeightGridTest`, `WorldCoordinatesTest`,
`WorldProjectionTest` under
`android/app/src/test/java/com/opensilkroadmap/app/world/`.

## Stage 6 — Build the committed dataset

`scripts/build_world_android.py` (idempotent):
```
SRO_PK2_DIR=<dir> SRO_READER_DIR=<pk2_mate> SRO_REGIONINFO=<RegionInfo.txt> \
SRO_MAP_LIST=<listing> python3 scripts/build_world_android.py
```
Outputs (all real-derived, committed):
- `android/app/src/main/assets/game/world/world_regions.tsv` (72 regions)
- `android/app/src/main/assets/game/world/world_index.tsv` (23 `.hg` sectors)
- `android/app/src/main/assets/game/world/{x}x{y}.hg` (23 real height grids)
- `WORLD_REGION_MASTER.csv` (repo root, docs artifact)

## Stage 7 — Android-native renderer

- `com.opensilkroadmap.app.world.TerrainHeightGrid` — loads `.hg`, bilinear
  clamped sampling.
- `WorldCoordinates` — verified coordinate transforms.
- `WorldRegion` — loads `world_regions.tsv`.
- `WorldProjection` — top-down view + height grayscale ramp.
- `NativeWorldRenderer` — Android View drawing the real height field.

## Reproducibility

- Pinned reader + `--map-list` listing (SHA captured) make re-runs bit-stable;
  the index is regenerated from the files on disk so it can never drift.
- The pipeline emits only derived normalized data; original PK2 blobs are never
  committed and never modified.
