# Phase C: World Map Basemap + Region/Marker Pipeline

Status: COMPLETE — the full-world basemap ships as a PMTiles pyramid served by the
existing mobile web runtime, with world + dungeon markers rendered from verified
vSRO textdata and named regions in the overlay/popups.

## Source Assets Verified

All resolved from the external `Media.pk2` archive (never committed to Git).

| Asset                                                     | Count / Size        | Role                      |
| --------------------------------------------------------- | ------------------- | ------------------------- |
| `Media/minimap/{secX}x{secY}.ddj`                         | 5,523 x 256x256 RGB | per-sector world minimaps |
| `Media/server_dep/silkroad/textdata/characterdata_*.txt`  | 9 files             | NPC templates             |
| `Media/server_dep/silkroad/textdata/npcpos.txt`           | —                   | NPC spawn positions       |
| `Media/server_dep/silkroad/textdata/teleportbuilding.txt` | 106 buildings       | teleport gate definitions |
| `Media/server_dep/silkroad/textdata/teleportdata.txt`     | 246 entries         | teleport nodes            |
| `Media/server_dep/silkroad/textdata/teleportlink.txt`     | 200 link sets       | teleport graph            |
| `Media/server_dep/silkroad/textdata/textdata_object.txt`  | —                   | object name translations  |
| `Media/server_dep/silkroad/textdata/textzonename.txt`     | 4,129 named rows    | region/zone names         |

Extraction: `scripts/extract_world.py` -> 5,682 files, 340 MB under the gitignored
`game_source/` tree (5,523 world minimaps + 159 textdata files).

- World sector extent: X 26..252, Y 35..126 (5,523 minimaps; coverage is sparse —
  sectors without game minimaps, e.g. ocean, simply have no tile).
- vSRO textdata is UTF-16 with English inline; translation key at column 2
  (`parts[1]`), English at column 9 (`parts[8]`).

## Tile Pyramid (mobile-friendly)

Built by the new streaming builder `scripts/generate_world.py` (reuses
`convert_ddj_to_webp` from `convert_ddjs.py` + the repo's pmtiles writer):

| Level            | Tiles | Content                                     |
| ---------------- | ----- | ------------------------------------------- |
| z8 (native, top) | 5,523 | one 256px webp per sector, q60 (~8 KB each) |
| z6 (region)      | 1,392 | 4x4 sectors merged @64px/sector, q80        |
| z3 (overview)    | 24    | 32x32 sectors merged @8px/sector, q80       |

Output: `map/public/assets/world.pmtiles` — **42.6 MB**, 5,789 entries /
6,027 addressed tiles, minzoom 3 / maxzoom 8, webp, compression none.

Design decisions:

- **Native z8 is the top level** (resolutions `[1/8, 1/64, 1/256]`), not the
  previous z9 (2x upscaled) plan. Rationale: the z9 level was 22092 tiles /
  127 MB — over GitHub's 100 MB hard file limit and wasteful for mobile (2x
  zoom beyond native). z8 is native sharpness (1px per sector pixel), fetches
  fewer tiles at max detail, and keeps the archive under 50 MB. Zooming past
  z8 continues to work via OpenLayers scaling (the runtime already
  "extrapolates" between the three grid levels).
- Streaming build: each DDJ is converted once to a z8 webp on disk; z6/z3 tiles
  assemble only the sectors they need — peak memory stays at a handful of tiles
  (required: the full world exceeds the ~210 MB free RAM of this environment).
- Intermediates stay under gitignored `game_source/out/minimap/`; only the
  packed archive is committed.

## Region/Marker Pipeline

`scripts/generate_game_data.py` (parsers fixed for the verified vSRO column
layout) now produces:

- `npcs.json` — **535 NPCs** (453 world / 5 dungeon-region, e.g. region 32785
  has "Dungeon Exit"; Phase B's zero-marker finding was an artifact of the old
  parser reading the wrong columns).
- `teleports.json` — **213 physical teleports** (111 world) with destinations
  resolved from `teleportlink.txt` (e.g. Dimensional Gate at region 25000 links
  Donwhang / Hotan / Constantinople / Samarkand / Baghdad / Alexandria).
- `regionnames.json` (new) — **3,569** region ID -> zone name mappings from
  `textzonename.txt` (e.g. 25000 "Jangan", 26265 "Western China Donwhang",
  32785 "Cave of Meditation").

These three files are committed (`.gitignore` now un-ignores
`map/public/assets/*.json`); they are required runtime data, not extraction junk.

## Runtime Integration

- `map/src/regionnames.ts` (new) — loads `regionnames.json`; zone names shown in
  the coords bar, region overlay labels, and marker popups.
- `map/src/coord.ts` — tileGrid resolutions `[1/8, 1/64, 1/256]` (z3/z6/z8).
- `map/src/map.ts` + `map/src/navmesh.ts` — tile z mapping `3/6/9` -> `3/6/8`.
- `map/src/navmesh.ts` — `getDungeonFloorKey` now returns the bare region ID for
  single-floor regions (e.g. `"32785"`, matching `index.html` layer keys) so
  region-32785 markers render; multi-floor regions keep `{region}_{floor}`.
- World tiles flow through the existing `PMTilesDB` IndexedDB cache (layer key
  `"world"` -> `world.pmtiles`), so viewed tiles are cached in-browser.

## Validation (all real, headless)

- Build: `deno task build` (tsc + vite) passes.
- Dev server (Vite :3000) + preview URL; `world.pmtiles`, `npcs.json`,
  `teleports.json`, `regionnames.json`, marker icons all return 200 with correct
  sizes; `world.pmtiles` answers `Range` requests (`206`, PMTiles protocol OK).
- Headless Chromium (puppeteer) **16/16 checks pass**:
  - World map canvas renders (47% non-black, stddev 62 — tiles genuinely drawn).
  - Coords bar shows resolved zone name ("South-Karakoram").
  - Search finds + flies to real world marker "Dimensional Gate" (region 25000)
    and opens its popup.
  - Mouse drag + wheel pan/zoom changes the rendered view.
  - World teleport marker pixels detected on the canvas (gate icon color).
  - Dungeon region 32785: search "Dungeon Exit" switches layer to `32785`,
    opens the marker popup, and the dungeon map renders (9%+ non-black).
  - No unexpected console/page errors (only a benign favicon 404).
- Mobile viewport (390x844, touch): world renders, 602 marker pixels, touch drag
  pans and loads more of the map.

## Files Changed

- `scripts/extract_world.py` (new) — world minimap + textdata extractor.
- `scripts/generate_world.py` (new) — streaming z3/z6/z8 pyramid + `world.pmtiles`.
- `scripts/generate_game_data.py` — fixed vSRO textdata parsing; added
  `regionnames.json` output.
- `scripts/convert_ddjs.py` — `convert_ddj_to_webp` gained a `quality` param.
- `map/src/regionnames.ts` (new) — zone-name lookup module.
- `map/src/coord.ts`, `map/src/map.ts`, `map/src/navmesh.ts` — native-z8 top
  level + single-floor floor-key fix + zone names in overlay/popups.
- `.gitignore` — un-ignores `map/public/assets/*.json` (required runtime data).
- `map/public/assets/world.pmtiles`, `npcs.json`, `teleports.json`,
  `regionnames.json` — generated runtime assets (world.pmtiles 42.6 MB).

No PK2 archives, original game archives, full extraction dirs, databases, or
server files are committed.

## Remaining Limitations

- Zoom beyond native z8 scales the z8 tiles (design-consistent "extrapolation");
  no true 2x-res tiles are shipped.
- Sparse sectors (ocean/void) show transparent background — that is how the
  source minimap set is laid out.
- Only region 32785 has a navmesh manifest entry, so markers in other dungeon
  regions require generating their navmesh manifests (floor-key resolution is
  already fixed for both single- and multi-floor keys).
- `npcs.json` names resolve only for templates present in the vSRO
  `characterdata` set with a translation; unresolved spawns are skipped.
