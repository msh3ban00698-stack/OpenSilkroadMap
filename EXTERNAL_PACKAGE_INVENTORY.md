# External Package Inventory — VSRO 1.193

Phase A deliverable. Everything below is **VERIFIED** directly against the downloaded
package (listings produced with `pk2_mate list` and a purpose-built Python PK2 reader
porting Veykril/pk2's Joymax Blowfish variant). Claims that are inferred rather than
verified are explicitly marked **[assumed]**.

All external material lives outside the repository. Supply the PK2 root with
`--pk2-dir` or `SRO_PK2_DIR`; nothing from the package is imported into the repo.

---

## 1. Source Package

- File: `VSRO Database & Clients 1.193.zip` (1,760,013,684 bytes), downloaded from MEGA.
- 10 files inside `VSRO 1.193/`:

| File                                    | Size (bytes)  | Content                                                                                                                                                                                             |
| --------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PK2 Files.7z`                          | 1,546,426,717 | The 5 game PK2 archives (see below)                                                                                                                                                                 |
| `VSRO-R Client.7z`                      | 195,170,460   | Game client (source of `Media.pk2`)                                                                                                                                                                 |
| `Vietnam-R v193 Package Server.7z`      | 10,994,403    | Server binaries (`MachineManager.exe`, `smc.exe`, `ImageTrans.dll`, `MailSender.dll`, `SMPlugins/*.dll`, `Script/VIETNAM_LUA/luac.exe`, `helper.exe`)                                               |
| `Database.7z`                           | 6,951,722     | SQL Server backups `SRO_CERTIFICATION.Bak`, `SRO_VT_ACCOUNT.Bak`, `SRO_VT_SHARD.Bak`, `SRO_VT_SHARDLOG.Bak`                                                                                         |
| `VSRO-R Proxy v1005.rar`                | 448,117       | `VSROProxy.exe`, `proxy_cfg.ini`, `HWID_DLL/sr_proxy.dll`, `Auto Events/*.txt`, `Features/*.txt` (e.g. `BLOCKED_SKILL_IDS`, `FILTER_KEYWORDS`, `MALICIOUS_OPCODES`), `Message/*.txt`, Prerequisites |
| `Vietnam-R v193 Offsets.txt`            | 1,527         | GameServer memory offsets (Level, Pet, CH/EU Mastery, GreenBook, BA Guild, ...)                                                                                                                     |
| `vSRO-R.txt`                            | 1,680         | Server feature list (cap 140, skills 111–150, removed penalties, added regions/dungeons)                                                                                                            |
| `Event-HAPPY-Working-Files-vsro-193.7z` | 6,957         | `Event.sct` (60,366 B), `EventList.sct` (712 B)                                                                                                                                                     |
| `ClientPatcher.rar`                     | 4,870         | `ClientPatcher.exe`                                                                                                                                                                                 |
| `GSPatcher.rar`                         | 5,281         | `Patcher.exe`                                                                                                                                                                                       |

- Uncompressed PK2 content totals ~4.87 GB (Data 3.12 GiB, Map 1.18 GiB, Media 767 MiB,
  Particles 166 MiB, Music 71 MiB).

## 2. PK2 Inventory

All five archives: signature `"JoyMax File Manager!\n"`, version `0x01000002`,
encrypted, Blowfish key `169841` (the pk2_mate default; verified by header checksum
`d8da30…` and by correct listing of every archive). File data is contiguous and
unencrypted; only directory blocks are Blowfish-encrypted.

### Data.pk2 — 3,351,891,968 B — 66,051 files

Top-level dirs (count, bytes): `prim` 52,085 / 2.44 GB · `navmesh` 6,072 / 850 MB ·
`res` 7,575 / 13 MB · `compound` 162 / 26.7 MB · `dungeon` 35 / 4.3 MB · `shader` 73 ·
`water` 30 · `shader_maptool` 18 · root file `RegionInfo.txt` (58,974 B).
Extensions: `.bms` 22,684 · `.ddj` 16,631 · `.bsr` 7,549 · `.nvm` 6,041 · `.ban` 4,691 ·
`.bmt` 4,269 · `.wav` 2,885 · `.bsk` 1,039 · `.cpd` 124 · `.dof` 34 · `.dat` 26 ·
`.psh` 14 · `.vsh` 8 · `.ifo` 4.

- `/navmesh`: `AINavData_32768..32794.DAT` (27 files; **region IDs 32769–32775 and
  32784–32786 match the repo's dungeon PMTiles prefixes exactly**), `mapinfo.mfo`,
  `nv_*.nvm` (6,041 files, hex region IDs `0x11a4`…`0x7fee`), plus index files
  `object.ifo`, `objectstring.ifo`, `objext.ifo`, `tile2d.ifo`.
- `/dungeon`: 34 `.dof` across subdirs `Arabia`, `asiam`, `Boss_dungeon`, `china`,
  `Demon/{Death,Fire,Poison}`, `etc`, `jupiter`, `property/flame`, `wchina`, plus
  `Dungeoninfo.txt` (1,071 B, tab-separated `1\t<rid>\t"Dungeon\...dof"`).
- `/prim/{ani,lightmap,mesh,mtrl,skel,snd}`: 3D models, animations, materials, sounds.
- `/compound`, `/water`, `/shader`, `/shader_maptool`.

### Map.pk2 — 1,268,441,088 B — 19,171 files

Per-region world geometry: `.t` 4,988 · `.m` 4,491 · `.o` 4,491 · `.o2` 4,348, laid out in
87 row directories (`0,1,35–42,49–52,54–64,66–127`) with per-cell filenames `0..252`.
Headers: `.t`=`JMXVMAPT1001`, `.o`/`.o2`=`JMXVMAPO1001`, `.m`=`JMXVMAPM1000`.

- `/tile2d`: 754 files (752 `.ddj` terrain textures + 2 `.tga`), 132 MB.
- `/skybox`, `/sun`, `/water`, `/weather`.
- Index files: `config.ifo`, `environment.ifo`, `layerobjectlist.ifo`, `object.ifo`,
  `objectstring.ifo`, `objext.ifo`, `tile2d.ifo`, `tile3d.ifo`, `mapinfo.mfo`,
  `plugin.dat`.

### Media.pk2 — 823,066,624 B — 29,590 files

- `/minimap`: 5,523 region minimaps (226 MB), named `<X>x<Y>.ddj`, grid
  **x ∈ [26,252], y ∈ [35,126]** — exactly the repo's `WORLD_BOUNDS_Z9` halved to zoom 8.
- `/minimap_d`: 2,214 dungeon minimaps (97 MB) in 8 folders: `Arabia`, `donwhang`,
  `donwhang_event`, `egypt`, `flame_dungeon`, `fort_dungeon`, `jinsi`, `jupiter`.
  Tile prefixes (`dh_a01_floor01..04`, `qt_a01_floor01..06`, `rn_sd_egypt1_01`,
  `flame_dungeon01`, `fort_dungeon01`) match the repo's dungeon PMTiles prefixes.
- `/interface` 8,418 · `/icon` 8,654 · `/icon64` 4,209 · `/res_ui` 51 ·
  `server_dep/silkroad/textdata` 159 files / 109 MB (incl. **10 `characterdata_*.txt`**,
  `npcpos.txt`, `teleportbuilding.txt`, `teleportdata.txt`, `teleportlink.txt`,
  `regioncode.txt`, `itemdata*.txt`, `skilldata*.txt`, `shop*`, quest/siege data).
- `/script`, `/config`, `/fonts`, `/launcher`, `/effect`, plus 29,592 root-level DDJs
  (UI frames, cursors, effect icons). `.ddj` files are `"JMXVDDJ 1000"` (20-byte JMX
  header) + DDS payload (verified on `minimap/100x100.ddj`).

### Music.pk2 — 76,488,704 B — 50 files

50 `.ogg` BGM tracks (`ARABIA_*`, `egypt_*`, `jangan_town`, `jupiter_*`,
`petra_dungeon`, `roc_battle`, …).

### Particles.pk2 — 178,126,848 B — 4,768 files

`/animations`: `.efp` 3,395 · `.ddj` 1,000 · `.bms` 264 · `.ban` 105 · `.bsk` 1 · `.db` 1.

## 3. Asset Categories

- World minimaps (Media `/minimap`) — consumed by `convert_ddjs.py` → `generate_tiles.py`.
- Dungeon minimaps (Media `/minimap_d`) — consumed by `convert_ddjs.py` → `generate_tiles.py` → `generate_pmtiles.py`.
- Navmesh (Data `/navmesh`) — consumed by `generate_navmesh.py`.
- Game text data (Media `server_dep/silkroad/textdata`) — consumed by `generate_game_data.py`.
- UI art (Media interface/icon/icon64/res_ui + root DDJs).
- Terrain / object geometry (Map `.t/.o/.o2/.m` + tile2d) — **not** consumed by current tooling.
- 3D models / animations / materials / sounds (Data `prim`).
- Music (Music.pk2). Particles (Particles.pk2).
- Server-side only (not map-relevant): Database.7z, Package Server.7z, Proxy, offsets, notes.

## 4. Repository Compatibility

| Repo tooling                                           | Requires                                                                        | In package?                                  |
| ------------------------------------------------------ | ------------------------------------------------------------------------------- | -------------------------------------------- |
| `convert_ddjs.py`                                      | `game_source/Media/minimap` (+`_d`)                                             | ✅ 5,523 + 2,214 DDJs                        |
| `generate_tiles.py`                                    | converted WEBP tiles                                                            | ✅ pipeline                                  |
| `generate_navmesh.py`                                  | `NavMesh/MapInfo.mfo`, `nv_{rid}.nvm`, `DungeonInfo.txt`, `.dof`                | ✅ all present                               |
| `generate_game_data.py`                                | `characterdata_*.txt`, `teleportbuilding.txt`, `teleportlink.txt`, `npcpos.txt` | ✅ all present (UTF-16 LE)                   |
| `generate_pmtiles.py`                                  | dungeon prefixes `32769_1..4`, `32770–32775`, `32784–32786`                     | ✅ `AINavData_32769..32775`, `_32784..32786` |
| Runtime bounds `WORLD_BOUNDS_Z9` (52–505 × 70–253 @z9) | minimap grid                                                                    | ✅ x 26–252 / y 35–126 @z8                   |

## 5. Existing Repository Tools

- README pipeline: `pk2_mate extract` (Media/Data/Map) → `convert_ddjs.py` →
  `generate_tiles.py` → `generate_navmesh.py` → `generate_game_data.py` →
  `generate_pmtiles.py` → `deno task dev`.
- Runtime: OpenLayers 9 map, XYZ/PMTiles tile sources, IndexedDB cache, NavLink viz.

## 6. Missing Components

- No tooling for Map.pk2 3D region geometry (`.t/.o/.o2/.m`, `tile3d.ifo`) — 2D minimap only today.
- No tooling for Data `prim` 3D models/animations.
- No item/skill/quest search surfaced in the UI (data is present in textdata).
- No direct teleporter import flow (README TODO), though teleport data is present.
- Canonical pipeline entrypoint: `scripts/extract_sro.py` (`validate` / `extract` / `generate`).
  PK2 reader (`pk2reader.py` / `jmblowfish.py`) is an external dependency, not in this repo.

## 7. Recommended Future Pipeline

1. Extract `Media.pk2`, `Data.pk2`, `Map.pk2` into `game_source/` (pk2_mate or the custom reader).
2. `convert_ddjs.py` → `generate_tiles.py` → `generate_navmesh.py` → `generate_game_data.py` → `generate_pmtiles.py`.
3. Add Map.pk2 region-geometry ingestion (terrain tiles / objects) as a follow-up.
4. Add item/skill search from `itemdata_*.txt` / `skilldata_*.txt`.
5. Serve assets from external hosting (see Risks) instead of committing binaries.

## 8. Recommended First Target

One small region to prove end-to-end fit:

- Pick a small cell, e.g. minimap `100x100` (x∈[26,252], y∈[35,126]) + its
  `nv_{rid}.nvm` (hex ID from the same region), the matching `AINavData_*.DAT`, and one
  dungeon `.dof` (e.g. `dunhwang_cv.dof`).
- Run `convert_ddjs.py` + `generate_tiles.py` for that region and
  `generate_navmesh.py` for its navmesh; verify tile URLs and navmesh overlay render.

## 9. Risks and Constraints

- **Licensing**: assets are Joymax / NetSGameplay / third-party (vSRO) copyrighted
  material; the extracted client data should not be redistributed in the public repo.
- **Size**: ~4.87 GB uncompressed PK2 content; GitHub commit/size limits require
  external hosting (Git LFS or a CDN) for generated assets — the repo's `.gitignore`
  already excludes `game_source` and `map/public/assets/*`.
- **Storage**: analysis data currently uses ~12 GB under `/tmp` (package + PK2s + listings).
- **Decryption**: PK2 uses a custom Joymax Blowfish variant (verified ported); standard
  Blowfish libraries will not decrypt these archives.
- **Performance**: pure-Python Blowfish walk of Data.pk2 takes minutes; use pk2_mate or a
  compiled reader for full extraction.
- **Verification depth**: counts/layout verified; deep content correctness of every
  individual file (esp. Data `prim`) is [assumed] until the pipeline consumes it.
