# Game Content Verification Report

Direct, source-verified audit of the Silkroad map/game application at `/workspace`.
All findings verified against the actual repo tree, committed assets, generated build
config, and CI workflow. Nothing is assumed from documentation alone.

Verification date: 2026-08-27

---

## 1. COMPLETE AND VERIFIED

| Item                                                 | Evidence                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2D world basemap                                     | `map/public/assets/world.pmtiles` (44,660,581 B) — loaded by `map.ts` PMTiles layer (`/assets/${key}.pmtiles`); world tiles render.                                                                                                                                         |
| Cave of Meditation map layer                         | `map/public/assets/32785.pmtiles` (81,908 B); layer select option `32785` → non-blank tiles.                                                                                                                                                                                |
| NPC markers                                          | `map/public/assets/npcs.json` (82,184 B) — loaded by `markers.ts:fetchMarkersData`; renders on world map.                                                                                                                                                                   |
| Teleport markers                                     | `map/public/assets/teleports.json` (87,576 B) — loaded same path; 8 teleport styles + connection lines render.                                                                                                                                                              |
| Zone/region names                                    | `map/public/assets/regionnames.json` (111,360 B) — region overlay + popups (`map.ts`, `main.ts`).                                                                                                                                                                           |
| 3D regions 1–9 (all authentic geometry)              | `map/public/assets/img/silkroad/game/region{1..9}/` each contains `mesh.json`, `floor.webp`, `buildings.json`, `buildings.bgeo`, `atlasN.webp`. Verified region1: 216 geoms, 5,535 building instances, 85 NPC/mob groups, 4 atlas pages. All 9 load via `region_loader.ts`. |
| 3D region 32785 (Phase B)                            | `region32785/mesh.json` + `floor.webp` present (cave; no buildings expected).                                                                                                                                                                                               |
| Character rig                                        | `map/public/assets/img/silkroad/game/character/chinaman_fighter/` — 41-bone rig, loaded by `character_loader.ts`; verified via Phase E.                                                                                                                                     |
| Mob actors                                           | `actor/{wolf,baroi,dowb,kyklopes,lion,barpolle}` dirs present; used by `mobs_data.ts`.                                                                                                                                                                                      |
| Phase H verified game data (committed & bundled)     | `map/src/game/data/level_progression.json` (150 levels, source `leveldata.txt`), `items.json` (7 starter items, official names), `skills.json` (6 classes), `masteries.json` (10 masteries). Loaded by `data_loader.ts`, no runtime fetch.                                  |
| Entry flow (intro → select → create → enter)         | `flow.ts` `initGameFlow`; wired from `main.ts:799`.                                                                                                                                                                                                                         |
| Animation state machine + joystick + combat vs dummy | `game3d.ts` (idle/walk/run/attack), Phase F verified.                                                                                                                                                                                                                       |
| HUD / inventory / equipment / gold / death+respawn   | `hud.ts`, `inventory_panel`, Phase G verified.                                                                                                                                                                                                                              |
| Skill/icon webp library                              | `map/public/assets/img/silkroad/icons/` — 4,476 files.                                                                                                                                                                                                                      |
| Map-marker icon PNGs                                 | `map/public/assets/icons/` — 10 PNGs, every path referenced by `styles.ts` exists.                                                                                                                                                                                          |
| Dungeon navmesh (region 32785)                       | `minimap/navmesh/d/manifest.json` + `17_floor01.webp`; 49 dungeon tiles under `minimap/d/{3,6,8,9}`.                                                                                                                                                                        |

## 2. PRESENT BUT INCOMPLETE

| Item                 | Status                                                                                                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3D regions 1–9       | Geometry + buildings render, but NPCs/teleport gates inside them fail to load (see §7).                                                                                      |
| Mob system           | Region 1: 3 hardcoded camps (Wolf/Baroi/Dowb). Regions 2–9: `mobs_data.ts` `mobCampsFor()` procedurally scales generic mobs by `REGION_TIER` — no authentic spawn placement. |
| Skills               | Only level-1 starter skills from bundled `skills.json`. Full skill names/icons (`skills_full.json`) missing → later skills degrade to procedural.                            |
| Skill icons          | 4,476 webp exist but are unreachable without `skills_full.json`/`items.json` item→icon mapping.                                                                              |
| Navmesh              | Dungeon navmesh only for region 32785; world navmesh (`navmesh_world.pmtiles`) missing.                                                                                      |
| Navigation linkage   | `navigation_linkage.json.gz` not in repo; downloaded at build time from GitHub (network-dependent).                                                                          |
| Shop/quest/item data | Generator exists (`scripts/build_game_database.py`) but output was never produced/committed.                                                                                 |

## 3. PLACEHOLDER / MOCK / SIMULATED

| Item                        | Details                                                                                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Party system                | `party_data.ts`: 2 hardcoded mercenaries (Swordguard Ally 2000g, Longbow Scout Ally 2500g), `MAX_PARTY_MEMBERS = 2`. Simulated, not a real recruitment system. |
| Field mobs outside region 1 | Procedurally generated camps (level/hp/attack/exp derived from a tier table), not authentic spawn data.                                                        |
| Item icons fallback         | `items.ts` renders inline SVG data-URI icons when the icon webp is absent.                                                                                     |
| Shop/quest reward items     | `authenticItemDef()` in `items.ts` synthesizes defs (name=code, price=100) when `items.json` is missing.                                                       |
| Warlock & Bard classes      | Exist in UI strings only; `skills.json` note: "warlock and bard have no mastery/skill data in this package."                                                   |

## 4. MISSING DATA

All under `map/public/assets/gamedata/` — directory does **not** exist in the repo
(gitignored; generated by `scripts/build_game_database.py` from `game_source/`, which is
absent). Every file below is fetched at runtime:

| File                           | Fetched by            | Effect when missing                                            |
| ------------------------------ | --------------------- | -------------------------------------------------------------- |
| `gamedata/quests.json`         | `quest_data.ts:34`    | Quest system broken (unhandled rejection)                      |
| `gamedata/shops.json`          | `world_npcs.ts:120`   | Shop panel fails to open                                       |
| `gamedata/items.json`          | `world_npcs.ts:146`   | No item names/prices/icons; shops + quest rewards degrade      |
| `gamedata/spawns.json`         | `world_npcs.ts:85`    | No authentic NPC spawns in any 3D region                       |
| `gamedata/chars.json`          | `world_npcs.ts:86`    | NPC names fall back to codes                                   |
| `gamedata/teleports_full.json` | `teleport_data.ts:30` | Teleport gates + region travel broken                          |
| `gamedata/skills_full.json`    | `skill_data.ts:33`    | Full skill names/icons unavailable (fails gracefully to empty) |

## 5. MISSING MAPS OR REGIONS

| Item                                                      | Status                                                                                                                                                                                                                        |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dungeon map archives for 11 of 13 selectable layers       | Only `world.pmtiles` and `32785.pmtiles` exist. Layers `32769_1..4` (Donwhang Dungeon B1–B4), `32775..32770` (Qin-Shi Tomb B1–B6), `32784` (Temple), `32786` (Flame Mountain) load `/assets/{key}.pmtiles` → 404 → blank map. |
| World minimap tile files (Phase C "5,523 world minimaps") | Not present as files (`minimap/` has only `d/` and `navmesh/`). World tiles come solely from `world.pmtiles`. Doc-vs-reality discrepancy.                                                                                     |
| `navmesh_world.pmtiles`                                   | Absent → world navmesh overlay shows nothing.                                                                                                                                                                                 |
| Dungeon navmesh images                                    | Only `17_floor01.webp` (32785). `dh_a01_*`, `qt_a01_*`, `rn_sd_egypt1_01_*`, `flame_dungeon01_*` tile patterns in `styles.ts:LAYER_URLS` have no files.                                                                       |
| 3D region 32785 buildings                                 | No `buildings.json`/`buildings.bgeo` (cave only).                                                                                                                                                                             |

## 6. MISSING MEDIA OR ASSETS

| Item                         | Status                                                                                                                                                                        |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Audio / music                | `map/public/assets/audio/` does not exist; zero `.ogg/.mp3/.wav/.m4a` anywhere in the tree. `scripts/extract_audio_minimaps.py` (targets `assets/audio/music`) was never run. |
| `navigation_linkage.json.gz` | Not committed. Only produced by the vite build plugin downloading from the Silkroad NavLink GitHub release (network required).                                                |
| Authentic gamedata outputs   | `quests/shops/items/spawns/chars/teleports_full/skills_full` (see §4).                                                                                                        |

## 7. BROKEN OR UNREACHABLE CONTENT

All of these are caused by the missing `gamedata/*.json` (no `game_source/` package to
regenerate them):

| Feature                          | Location                                                         | Failure mode                                                                                          |
| -------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Teleport gates (3D)              | `game3d.ts:176` `void this.buildGates()` → `teleport_data.ts:30` | Uncaught rejection; gates never spawn.                                                                |
| Region travel / teleport panel   | `flow.ts:313` `showTeleportPanel`                                | Uncaught rejection; panel never opens → **cannot travel between the 9 regions from gameplay**.        |
| Authentic NPC spawns             | `game3d.ts:907` `populateAuthenticNpcs`                          | Caught → "NPC data unavailable"; only generic manifest NPCs remain.                                   |
| Quests                           | `quest_runtime.ts:20,37`                                         | Uncaught rejection at module load and in `questsForNpc`; quest panel blank; Quest button never shown. |
| Shops                            | `shop_panel.ts:25`, `hud.ts:447`                                 | Uncaught rejection; shop panel fails to open.                                                         |
| Item info (shops, quest rewards) | `world_npcs.ts:146`                                              | Rejects when `items.json` missing.                                                                    |
| Navlink visualization            | `main.ts:479–525`, `navlink.ts:53`                               | No local file → download fails → feature disabled.                                                    |
| World navmesh                    | `navmesh.ts:25`                                                  | `navmesh_world.pmtiles` 404 → transparent tiles.                                                      |
| Dungeon 2D layers (11 of 13)     | `map.ts:84`                                                      | Blank (missing pmtiles).                                                                              |

> Note: On 2026-08-27 the unguarded fetch sites were hardened so a missing
> `gamedata/*.json` now degrades cleanly (empty panels + `onLog` warning) instead of
> producing unhandled promise rejections. The features above are therefore no longer
> "crashes" — but they remain non-functional until the data is regenerated.
> Files changed: `game3d.ts` (`buildGates`), `flow.ts` (`showTeleportPanel`),
> `quest_runtime.ts`, `shop_panel.ts`, `world_npcs.ts` (`loadShops`/`loadItemInfo`),
> `hud.ts`.

## 8. NOT INCLUDED IN THE FINAL APK

| Item                          | Status                                                                                                                                                                                                                                                                                           |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `map/dist` (production build) | Does not exist in the repo (gitignored). Would be produced by CI (`deno task build`).                                                                                                                                                                                                            |
| Synced Capacitor web assets   | `android/app/src/main/assets/public` absent locally (gitignored; produced by `npx cap sync android` in CI).                                                                                                                                                                                      |
| Local APK artifact            | None. APK is built only by GitHub Actions (`.github/workflows/android-apk.yml` → `opensilkroadmap-debug-apk` artifact).                                                                                                                                                                          |
| Consequence                   | Even if the CI APK is built today, `gamedata/`, `audio/`, and `navigation_linkage.json.gz` are gitignored and absent, so the APK ships the same broken teleport/quest/shop behavior. The only assets that reliably reach an APK are the committed `img/` + `icons/` + root `*.pmtiles`/`*.json`. |

## 9. REQUIRED NEXT WORK

1. **Restore the external VSRO 1.193 package** (`game_source/` + PK2 archives via
   `--pk2-dir` / `SRO_PK2_DIR` — both currently absent). This is the hard blocker.
2. Regenerate + commit the missing data with the repo's own scripts:
   - `scripts/build_game_database.py` → all `gamedata/*.json` (§4)
   - `scripts/generate_pmtiles.py` → dungeon pmtiles for `32769_*`, `32775..32770`, `32784`, `32786` (§5)
   - `scripts/generate_navmesh.py` → `navmesh_world.pmtiles` (§5)
   - `scripts/extract_audio_minimaps.py` → `assets/audio/music` (§6)
   - `scripts/extract_icons.py` → full item/skill icon mapping (§6)
3. ~~Harden the fetch sites~~ **DONE (2026-08-27)** — `game3d.ts:buildGates`,
   `flow.ts:showTeleportPanel`, `quest_runtime.ts`, `shop_panel.ts`, `hud.ts:447,453`,
   `world_npcs.ts:loadShops`/`loadItemInfo` now degrade cleanly when gamedata is missing.
4. **DONE (2026-08-27)** — fixed the navlink packaging bug in `vite.config.ts`: the build
   plugin wrote `navigation_linkage.json.gz` to `public/assets/` in `closeBundle`, which is
   after Vite copies `public/` → `dist/`, so it never reached a clean build/APK. It now
   writes into `dist/assets/`; verified present in `dist/` (199,635 B).
5. Rebuild `map/dist`, re-sync `npx cap sync android`, and run the CI APK workflow; verify
   the APK contains `world.pmtiles`, `32785.pmtiles`, `img/`, `icons/`,
   `navigation_linkage.json.gz`, and the regenerated `gamedata/`.
6. Once authentic data is back, remove/replace the §3 placeholders (party mercenaries,
   procedural mob camps, procedural item defs) with real data.
