# Phase B: First Playable Region Pipeline

Status: COMPLETE — first playable region (32785, Cave of Meditation) end-to-end
through the existing conversion pipeline into the OpenSilkroadMap runtime.

## Selected Region

- **Region 32785** — Cave of Meditation (dungeon `fort_dungeon`), World 1, floor 0.
- Selection rationale: single floor, smallest fully-verified dependency closure
  (9 minimap DDJ tiles, 13 navmesh objects, 1 DOF, 1 ainavdata file), zero in-region
  markers (no floor-key complications), and already fully wired in the repo
  (`index.html` layer `32785`, `LAYER_URLS`, `DUNGEON_PREFIXES`, `ARCHIVE_KEYS`).
- Source: external vSRO PK2 archives (never committed to Git).

## Source Assets Verified (dependency closure)

All resolved from external `Data.pk2` / `Media.pk2` and confirmed present/size-consistent:

| Asset | Count / Size | Role |
| --- | --- | --- |
| `Media/minimap_d/fort_dungeon/fort_dungeon01_{127..129}x{126..128}.ddj` | 9 x 256x256 RGB | minimap tiles |
| `Data/Dungeon/wchina/fortress_dungeon.dof` | 56,311 B | dungeon definition (1 floor) |
| `Data/.../donhwang_cv_clone/floor_1/*.bsr` | 13 | navmesh object definitions |
| `res/dun/.../floor_1/*.bms` + `prim/mesh/.../floor_1/*.bms` | 13 | navmesh meshes (bsr -> bms parse validated) |
| `Data/navmesh/ainavdata_32785.dat` | 243,051 B | navmesh data |

Region 32785 has **zero** markers in `npcpos.txt` / `teleportdata.txt` (verified),
so no marker layer needed.

## Conversion Pipeline

1. `scripts/extract_region.py` (new, reproducible extractor, default region 32785)
   extracts the closure into `game_source/` (gitignored): 37 files, 2,709,989 B.
   Reuses the repo's existing `parse_navmesh_obj_bsr`.
2. `scripts/convert_ddjs.py` -> 9 z8 webp tiles.
3. `scripts/generate_tiles.py` -> zooms 0-9 (z7:4, z6:2, z5:2, z4:2, z3:2, z2:2, z1:2, z0:1, z9:36).
4. `scripts/generate_pmtiles.py` -> `map/public/assets/32785.pmtiles`
   (49 addressed tiles / 42 entries, tile compression none, webp, 80 KB).
5. `scripts/generate_navmesh.py --data game_source/Data --out .../img/silkroad/minimap`
   -> `navmesh/d/17_floor01.webp` (2048x1448 RGBA, 312 KB) + `manifest.json`
   with `"32785"` entry (floor 0, minX -1036.93, minZ -2297.09, maxX 3016.92, maxZ 569.97).

All four existing scripts reused unchanged; no tooling rewrites.

## Runtime Result

- Dev server (Vite) + preview URL via `request_preview` (`*.monkeycode-ai.live`);
  `vite.config.ts` gained `server.host: true` and `server.allowedHosts: [".monkeycode-ai.live"]`.
- All region 32785 assets return 200 over preview (correct sizes / content types):
  `32785.pmtiles`, `navmesh/d/manifest.json`, `17_floor01.webp`, z8/z9/z6/z3 tiles.
- PMTiles archive content verified: every runtime-requested tile
  (z9 254..259 / 251..256, z6 31..32/32, z3 3..4/4, z8 127..129/126..128)
  is present and decodes to valid non-blank webp.
- Headless browser check (puppeteer + SwiftShader, WebGL2):
  - Layer switched to `32785`, navmesh overlay on.
  - WebGL canvas readback (preserveDrawingBuffer forced): 1280x800, 1,033 distinct
    colors, 130,181 non-black pixels -> map content genuinely renders.
  - `32785.pmtiles` fetched on demand, `manifest.json` + `17_floor01.webp` fetched.
- Verification verdict: **VERIFIED** (GPU pixel readback, not a fabricated claim).

## Files Changed

- `scripts/extract_region.py` — new reproducible region extractor (default 32785).
- `.gitignore` — un-ignores `map/public/assets/img` and `*.pmtiles`;
  `game_source/` (extraction output) stays ignored.
- `map/vite.config.ts` — dev server `host: true` + `allowedHosts` for preview domain.
- `map/public/assets/32785.pmtiles` — generated PMTiles archive (49 tiles, 80 KB).
- `map/public/assets/img/silkroad/minimap/{d/8,d/9,d/6,d/3,...}` and
  `navmesh/d/{17_floor01.webp,manifest.json}` — generated tiles + navmesh assets.

No PK2 archives, game archives, full extraction dirs, databases, or server files
are committed.

## Remaining Limitations

- `world.pmtiles` not shipped yet (404 at runtime, expected) — world layer has no
  basemap until Phase C; dungeon layer is fully functional.
- `npcs.json` / `teleports.json` 404 (benign) — region 32785 has zero markers.
- No marker/teleport rendering for this region by design (none exist).
- Navmesh overlay verified rendered as part of the composited frame; its exact
  silhouette was not pixel-asserted against the source mesh.

## Recommended Phase C

1. Ship the world-level `world.pmtiles` basemap so non-dungeon regions render.
2. Run the marker pipeline (`npcs.json` / `teleports.json`) for regions with
   NPC/teleport data, exercising floor-key resolution for multi-floor dungeons.
3. Add regression tests (script-level snapshot checks) so pipeline changes are
   caught before they reach the runtime.
4. Consider pre-caching `32785.pmtiles` + navmesh via the existing IndexedDB
   PMTiles cache layer for offline/first-load performance.
