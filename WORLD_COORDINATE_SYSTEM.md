# World Coordinate System (Phase 10)

The coordinate conversions below were VERIFIED during Phase 10 against real
source data. Anything not proven is marked **UNKNOWN** and is not used by the
renderer.

## Verified conversions

| Conversion | Formula | Status |
| --- | --- | --- |
| region code -> sector | `sx = region & 0xFF`, `sy = region >> 8` | VERIFIED (npcpos + server RefRegion, 2444 rows) |
| sector -> world | `world = (sector - refSector) * 1920 + local` | VERIFIED (reference formula) |
| sector side | 1,920.0 world units | VERIFIED (grid 97x97, step 20) |
| height grid step | 20.0 world units | VERIFIED |
| object local -> world | `worldX = x + (tx - refSx)*1920`, `worldZ = z + (tz - refSy)*1920` | VERIFIED (.o2) |
| minimap cell | sector (x,y) at 256 px per sector | VERIFIED (Media.pk2) |

The reference formula `world = (sector - refSector) * 1920 + local` is
confirmed by the Phase 9 verified codebase and re-encoded in
`WorldCoordinates` (Java) and `world_terrain.py` (Python). All world-space
values in the pipeline are RELATIVE to a reference sector — no absolute
global origin is required.

## Verified axis orientation

- World +X increases with sector x (east on the top-down view).
- World +Z increases with sector y; the top-down renderer maps +Z to screen -Y
  so north is up.
- Height `y` is the real `float32` height from the `.m` grid.

## UNKNOWN (explicitly not invented)

- **Global world origin**: the absolute position of sector (0,0) in some
  canonical client space is not derivable from the committed sources; all
  coordinates are sector-relative. Not needed for the real-height renderer.
- **`.t` zone/tile coordinates**: how `.t` records map tile grid to world is
  not yet decoded.
- **`.o` overlay semantics**: whether `.o` carries walkable/link regions and
  how they map to the `.t` grid is not yet decoded.
- **Height sub-sector metadata**: the non-height bytes of the 7-byte `.m`
  record are not decoded.
- **Exact player spawn reference**: the China ref sector for the player-spawn
  convention used by the web map's `npcpos` region codes is UNKNOWN here; the
  renderer uses each region's own RegionInfo ref sector.
- **Instance/dungeon region codes**: codes with the high bit set (signed-16
  negative) live in a separate coordinate space; `RegionResolver` never derives
  a sector for them (returns `None`).

## Region resolution (Phase 2)

Two committed tables plus a resolver turn any packed region code into a
complete, evidence-backed description:

| Table | Source | Content |
| --- | --- | --- |
| `textdata/regioncode.tsv` | Media.pk2 `server_dep/silkroad/textdata/regioncode.txt` | region id -> RN_* string code + localized Korean name (3,287 distinct ids) |
| `world/region_zone.tsv` | server `SR_GameRefData/RefRegion.txt` | region id -> sector x/y + server name + flag + zone id (2,444 world rows, 21 names, 13 zones) |

Newly proven (Phase 2):

- The packing formula `region = (sector_y << 8) | sector_x` holds for every one
  of the 2,444 non-negative RefRegion rows (0 mismatches), independently
  confirming the Phase 10 npcpos result.
- RefRegion sector space matches the client regioncode space (2,442/2,444 ids)
  and the RegionInfo grid (2,396/2,444 sectors), so all three families reference
  the same sector grid.
- Example anchor: region `25000` -> sector `(168, 97)`, RN_CH_JANGAN / 장안,
  server name CHINA, zone 1001.
- `regioncode.tsv` was regenerated with proper CP949 Korean names. The earlier
  committed copy was mojibake (a single undecodable byte at offset ~101000 made
  the decoder fall back to latin-1); `build_textdata_catalog.py` now recovers
  CP949 with `errors="replace"`.

Implemented: `scripts/region_resolver.py` (`RegionResolver.load_default`,
`resolve`, `by_name_code`), generator `scripts/build_region_ref_catalog.py`,
tests `scripts/test_region_resolver.py`.

## Implemented (verified only)

- `scripts/world_terrain.py`: `unpack_region`, `pack_region`,
  `sector_world_origin`, `local_to_world`, `npc_to_world`.
- `scripts/region_resolver.py`: `RegionResolver` over the two committed tables.
- Java `com.opensilkroadmap.app.world.WorldCoordinates` and
  `TerrainHeightGrid.sampleWorld`.
- Tests lock all verified formulas (see `test_world_terrain.py`,
  `WorldCoordinatesTest`, `TerrainHeightGridTest`).
