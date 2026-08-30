# Phase 10 — World / Terrain Source Baseline

Read-only baseline of the REAL VSRO-R 1.193 world data used by the Phase 10
pipeline. Everything below was obtained by extracting files from the original
archives with the pinned reader; no original was modified, and no geometry was
invented.

## Source archives

| Archive | Verified size | Role |
| --- | --- | --- |
| `Map.pk2` | 823,066,624 bytes | world/terrain: sectors, heights, object overlays |
| `Data.pk2` | (client data archive) | object index, region info, navigation |
| `Media.pk2` | (media archive) | minimaps, ddj textures |

`Map.pk2` SHA-256, sizes and mtimes were captured at extraction time
(`pk2_snapshot` in `android-assets/manifest.json` for Media.pk2; Map.pk2
inventory re-derived during Phase 10).

## Pinned reader

All extraction uses the pinned read-only reader `pk2_mate` (Rust binary,
`list` / `extract` subcommands). `pk2_mate list -a Map.pk2` produces the full
archive listing; `pk2_mate extract -a Map.pk2 -o <dir> -p /<y>/<x>.m` writes a
single file with the parent directory dropped (verified behavior).

## Map.pk2 world census (real, extracted listing)

| Metric | Count | Source |
| --- | --- | --- |
| Sector directories | 87 | `pk2_mate list` |
| Files total | 19,176 | `pk2_mate list` |
| Terrain height sectors `.m` | 4,491 | listing |
| Terrain overlay `.o` | 4,491 | listing |
| Object instance overlays `.o2` | 4,348 | listing |
| Tile/zone records `.t` | 4,988 | listing |
| Textures `.ddj` | 839 | listing |

All `.m` files checked during Phase 10 parse at the documented layout
(`JMXVMAPM1000`, 12-byte header + 36 blocks of 2,575 bytes = 92,712 bytes).

## Sector inventory

`map_full_list.txt` (extraction-time listing, 19,264 lines) drives
`scripts/build_world_android.py` via `--map-list`. Sectors exist only where the
archive has them; the pipeline picks the first existing sector in each
RegionInfo window (see `WORLD_REGION_MASTER.csv`).

## Region info

`Data.pk2 /RegionInfo.txt` (58,974 bytes; SHA-256
`787d9b417cf3044ff9260f484656002089f7406afd57f229a3c5ac85460739ff`) defines 72
sections (61 `FIELD`, 11 `TOWN`) with 3,468 sector cells. This is the source of
`world_regions.tsv` and `WORLD_REGION_MASTER.csv`.

## Object index

`Data.pk2 navmesh/object.ifo` (231,665 bytes) is the index of object models;
parsed into 3,307 `.bsr` paths. All 95 object instances in the real
Constantinople sector `76.o2` resolve against it.

## Terrain verification matrix (real sectors)

Heights are raw `float32` from the actual `.m` files.

| Sector | Region window | Min height | Max height | Mean |
| --- | --- | --- | --- | --- |
| 76:103 | Constantinople | -369.93 | 75.00 | -135.95 |
| 104:90 | Roc_Mountain | 1,891.44 | 4,091.08 | — |
| 156:90 | Jangan_Field | 801.79 | 1,825.93 | — |
| 143:89 | Donwhang_Field | -117.25 | 376.59 | — |
| 130:95 | Hotan_Field | 1,472.64 | 3,092.94 | — |
| 104:100 | Central_Asia | -920.78 | 1,198.61 | — |
| 47:87 | Alexandria_Delta | 100.00 | 2,057.84 | — |
| 88:86 | Baghdad | -435.35 | 276.72 | — |

Additional per-region verification (8 named world regions, one sector each):
Mt. Roc 2024.33..2505.75, Hotan 1329.49..2770.44, Jangan 346.53..1954.69,
Alexandria 100.00..2162.86, Samarkand -1240.78..301.46, Constantinople
-369.93..75.00, Baghdad -319.48..1025.05, Donwhang -96.64..52.22. The strong
regional differentiation confirms real terrain data.

## What is deliberately NOT in this baseline

- No extracted `.m`/`.o`/`.o2` files are committed (proprietary originals).
- Only small, documented, derived normalized artifacts are committed
  (`*.hg` height grids, TSV/CSV catalogs) — see `PHASE_10_WORLD_PIPELINE.md`.
- Global world-space origin mapping and `.o`/`.t` payload semantics remain
  UNKNOWN and are documented as such (see `WORLD_FORMAT_CATALOG.md`).
