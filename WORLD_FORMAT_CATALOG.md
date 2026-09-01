# World Format Catalog (Phase 10)

Catalog of the world/terrain formats VERIFIED during Phase 10 against real
VSRO-R 1.193 files, and of the normalized Android output container. Fields not
yet proven are explicitly marked **UNKNOWN**; nothing is guessed.

Legend: **VERIFIED** = proven on real extracted files; **UNKNOWN** = not yet
proven from the supplied material.

## 1. Terrain height sectors — `Map.pk2 /{Y}/{X}.m`

VERIFIED on 9+ real sectors (8 world regions + Constantinople cluster).

| Offset | Size | Field | Status |
| --- | --- | --- | --- |
| 0 | 12 | magic `JMXVMAPM1000` | VERIFIED |
| 12 | 92,700 | 36 blocks (6x6) of 2,575 bytes | VERIFIED (file = 92,712) |
| block+6 | 4 | `float32` height at grid (k,m) | VERIFIED |

Within each 2,575-byte block: 289 height records of 7 bytes each; the height
`float32` sits at block offset 6 + (k*17 + m)*7. Block `bi`: `bx = bi%6`,
`by = bi/6`; grid cell `(z,x) = (by*16 + k, bx*16 + m)`. Grid is 97x97
(`6*16+1`). Step between heights = 20.0 world units (VERIFIED by cross-check
against the 1,920-unit sector side and the reference coordinate formula).

The 4 trailing bytes of each 7-byte record are not yet decoded -> **UNKNOWN**
(believed to hold surface/tile metadata, not used by the height grid).

## 2. Object instance overlays — `Map.pk2 /{Y}/{X}.o2`

VERIFIED on 1 real sector (Constantinople 76.o2, 95 instances; all resolve).

| Offset | Size | Field | Status |
| --- | --- | --- | --- |
| 0 | 12 | magic `JMXVMAPO1001` | VERIFIED |
| 16 | — | series of records: `u16 count` then `count x 30-byte` entries | VERIFIED |
| rec+0 | 4 | `nameI` index into `object.ifo` | VERIFIED |
| rec+4 | 12 | `x, y, z` (`float32` each) | VERIFIED |
| rec+18 | 4 | `theta` (`float32`, radians) | VERIFIED |
| rec+28 | 2 | tail `u16`; `tx = tail & 0xFF`, `tz = tail >> 8` | VERIFIED (formula) |
| rec+16 | 2 | fields between z and theta | UNKNOWN |
| rec+22 | 6 | fields between theta and tail | UNKNOWN |

## 3. Object index — `Data.pk2 navmesh/object.ifo`

VERIFIED (parsed 3,307 `.bsr` paths). Text file, GBK; each entry has a quoted
path `...\xxx.bsr`. Only quoted strings are extracted; the surrounding
per-entry counters are UNKNOWN (not needed for nameI -> bsr resolution).

## 4. Static geometry — `.bsr` / `.bmt` / `.bms`

VERIFIED on the web-era pipeline (reused, cross-checked):
- `.bsr` magic `JMXVRES 0109`; material path + list of `.bms` paths.
- `.bmt` magic `JMXVBMT 0102`; material-name -> `.ddj` texture path. **Phase 18
  PROVES the full layout** (`world_terrain.parse_bmt_entries`): magic + `u32`
  count; per entry `u32 name_len` + null-padded name + 72 B (18×f32 props) +
  `u32 ddj_len` + null-padded `.ddj` path + 7 B tail (`f32 1.0` + 3 B). All
  4,269 files / 16,328 entries parse byte-exactly.
- `.bms` magic `JMXVBMS 0110`; `(pos, uv)` vertices (stride 44 or 52) + `u16`
  triangle indices; vertex type field at byte 12 + 4*13.

## 5. Textures — `.ddj`

VERIFIED: 20-byte header + embedded DDS body (`JMXVDDJ+DDS`). Width/height and
format detected from the DDS header (DXT1/3/5 and RGB8 observed).

## 6. Normalized Android container — `.hg` (VSHG v1)

Documented derived output (NOT a VSRO format). Small, dependency-free binary
grid for direct Android parsing.

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | magic `VSHG` |
| 4 | 2 | version = 1 (`u16` LE) |
| 6 | 2 | size (heights per side, 97) |
| 8 | 4 | step (`float32`, 20.0) |
| 12 | 4*size*size | `float32` heights, row-major `[z][x]` |

Committed: 23 real sector grids under
`android/app/src/main/assets/game/world/` (see `world_index.tsv`).

## 7. Formats inventoried (Phase 18 status)

- `Map.pk2 /{Y}/{X}.o` (4,491 files) — terrain overlay / zone stamps. **PROVEN**
  (`o2_decoder.parse_o`, 28-byte records, relative tail).
- `Map.pk2 /{Y}/{X}.t` (4,988 files) — tile/zone records. **PARTIAL**
  (`world_terrain.parse_t`): magic + size `140,436` + tile-ID cross-reference to
  `tile2d.ifo` proven; grid layout **UNKNOWN** (body `140,424 = 2³·3·5851`).
- `Map.pk2 /tile2d.ifo` (`JMXV2DTI1001`, 719 entries) — **PROVEN**
  (`world_terrain.parse_tile2d_ifo`): `id → flag → class → .ddj → {x,y}` sectors.
- `Map.pk2 mapinfo.mfo` (`JMXVMFO 1000`), `layerobjdef.txt`,
  `layerobjectlist.ifo` (`JMXVOBJL1000`), `tile3d.ifo` (`0\n` text) — **UNKNOWN**.
