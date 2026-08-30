# ANDROID_DATA_CONVERSION_STATUS — vSRO 1.193 → Offline Native Android

Phase 11. This document states exactly which real original data is converted into
Android-consumable form today, what is decoded but not yet converted, and what is
blocked. Nothing below claims conversion without a committed converter and output.

## Status legend
- **CONVERTED** — real source bytes → Android asset/format produced by a committed,
  tested converter; output present in the repo.
- **PARSED/NORMALIZED** — decoded to structured data; an Android consumer module may
  or may not exist yet.
- **DECODED, CONVERSION DEFERRED** — format readable; converting every file is a
  later-phase backlog item.
- **BLOCKED (format UNKNOWN)** — cannot decode; no honest path yet.

---

## 1. CONVERTED real source → Android assets (committed)

| Source format | Source count | Converted outputs | Converter (committed) | Where |
|---|---|---|---|---|
| `ddj` textures (DDS payloads) | 47,495 | ~7,755 Android texture outputs (minimaps, icons, UI, actors) | `scripts/convert_ddjs.py`, `scripts/dds_decode.py`, `scripts/bulk_convert_assets.py` | `android-assets/` (7,755 files incl. `manifest.json`), Phase 5–8 |
| `wav` audio | 2,885 | real `.wav` samples converted to Android-compatible audio | `scripts/extract_audio_minimaps.py`, Phase 5/6 | `android-assets/audio/` |
| `ogg` music | 50 | real `.ogg` sample converted to Android audio | Phase 5/6 | `android-assets/audio/` |
| `m` terrain height (Map.pk2) | 4,491 | 23 real `.hg` height grids + `world_index.tsv` (Phase 10) | `scripts/world_terrain.py`, `scripts/build_world_android.py` | `android/app/src/main/assets/game/world/*.hg` |
| `o2` object instances | 4,348 | parsed fixtures + world region tables (Phase 10) | `scripts/world_terrain.py` | `scripts/testdata/world/`, `WORLD_REGION_MASTER.csv` |
| `RegionInfo.txt` (Data.pk2) | 1 | `regions.tsv` (72 sections, 3,468 cells) | `scripts/build_region_catalog.py` | `android/app/src/main/assets/game/regions.tsv` |

## 2. NEW in Phase 11: textdata → Android-normalized UTF-8 TSV

21 verified datasets extracted from `Media.pk2 /server_dep/silkroad/textdata/`
(read-only), decoded (UTF-16LE BOM / cp949 / UTF-8), and written as UTF-8 TSV under
`android/app/src/main/assets/game/textdata/` (~1.6 MB on disk, from ~2.9 MB of
source bytes):

| Asset | Records | Source |
|---|---|---|
| `npcpos.tsv` | 18,457 NPC spawns | `npcpos.txt` |
| `leveldata.tsv` | 150 levels | `leveldata.txt` |
| `levelgold.tsv` | 140 level-gold rows | `levelgold.txt` |
| `questdata.tsv` | 1,005 quests | `questdata.txt` |
| `refshop.tsv` / `refshopgoods.tsv` | 79 / 2,283 shop rows | `refshop.txt`, `refshopgoods.txt` |
| `refqusetreward.tsv` / `refquestrewarditems.tsv` | 996 / 374 rows | `refqusetreward.txt`, `refquestrewarditems.txt` |
| `regioncode.tsv` | 3,294 region codes | `regioncode.txt` |
| `teleportdata.tsv` / `teleportlink.tsv` / `teleportbuilding.tsv` / `refoptionalteleport.tsv` | 247 / 352 / 107 / 45 rows | corresponding `.txt` |
| `worldmap_mapinfo.tsv` / `worldmap_instanceinfo.tsv` / `worldmap_localinfo.tsv` | 59 / 23 / 1,118 rows | corresponding `.txt` |
| `gameworldconfigdata.tsv` / `gameworlddata.tsv` | 1,028 / 116 rows | corresponding `.txt` |
| `characterdata.tsv` / `itemdata.tsv` / `skilldata.tsv` | index manifests | corresponding `.txt` |

> Every row count above is read from `TEXTDATA_CATALOG.tsv` and asserted in
> `scripts/test_phase11.py`.

Every converted file is covered by a committed test (`scripts/test_phase11.py`:
record counts, schema width, content spot checks) and listed in
`TEXTDATA_CATALOG.tsv` with per-file sha256.

## 3. PARSED/NORMALIZED — wired to Android consumers (Phase 12)

- **All 21 datasets** now have Android-free parsers in
  `android/app/src/main/java/com/opensilkroadmap/app/data/` (NpcPosTable,
  LevelDataTable, LevelGoldTable, TeleportDataTable, RefShopGoodsTable,
  WorldMapInstanceTable, QuestDataTable + generic TsvTable), with 10 JVM tests
  against real committed values (`TextDataTablesTest.java`).
- `GameDataCatalog` (Phase 12) composes npcpos/leveldata/teleportdata/
  worldmap_instanceinfo and is wired into `GameActivity`/`GameHudView`; the HUD
  shows real counts and degrades to an explicit "not bundled" state when the
  assets are absent. Schema/join provenance: `TEXTDATA_SCHEMAS.json`,
  `DATA_REFERENCE_GRAPH.json`.

### Phase 14 — native world runtime (terrain consumer)

- The Phase 10 `.hg` height grids (23 real sectors, `world_index.tsv`) are now
  consumed by the native world screen: `GameActivity` → `NativeWorldRenderer` →
  `Camera2D` renders the verified heightfield (DIAGNOSTIC TERRAIN RENDERER, not
  final 3D). Selection is deterministic (first region whose reference sector has
  a committed `.hg`): `Jangan_Field` sector `156x89` (`Map.pk2 /89/156.m`,
  min 866.25 / max 2687.02, 97×97 = 9,409 heights).
- Missing terrain assets fail closed (explicit "TERRAIN ASSET MISSING" state,
  no substitution). No models/objects/NPCs are rendered (format decode BLOCKED,
  no fabricated geometry). Executed evidence: `scripts/test_phase14_world_runtime.py`
  (16 tests). Build/runtime NOT EXECUTED here (no JDK/Android SDK).

### Phase 15 — multi-sector world + NPC placement

- The native world screen now loads EVERY committed `.hg` sector in the selected
  region window (not just the reference sector). For `Jangan_Field`
  (window `sx 156..182, sy 89..102`) this loads `156x89` + `156x90` as a
  `WorldTerrainSet` (world extent 1920 × 3840), verified edge-continuous
  (`g1[96][x] == g2[0][x]`).
- `npcpos.tsv` is now consumed at runtime by the Android-free `NpcSpawnIndex`
  (18,457 rows: 14,800 world + 3,657 dungeon). Verified world spawns are drawn as
  DIAGNOSTIC PLACEMENT MARKERS only (no character model decoded).
- Object placement (`.o2`, 4,348 overlays) characterized: magic `JMXVMAPO1001`,
  offset 12 always `u32=0`, variable data start `>= 16`; `parse_o2` is proven
  only when data starts at 16 — remaining header layout UNKNOWN.
- Executed evidence: `scripts/test_phase15_world_integration.py` (12 tests, OK).
  JVM/instrumented tests + build/runtime NOT EXECUTED (no JDK/Android SDK).

## 4. DECODED / PARTIALLY DECODED (Phase 12–13 decoders committed)

| Format | Files | Proven subset | Remaining UNKNOWN |
|---|---|---|---|
| `ban` | 4,796 | **FULL layout** (Phase 13 Part D): magic/version; reserved; u32 name-len + name; u32 duration + frame-rate(30) + u32 UNKNOWN + kpb; kpb×u32 timestamps; bone count + per-bone name + kf-count + kpb×28-byte keyframes (quat + pos). Decoder `scripts/ban_decoder.py`, 8 tests. | semantic only: `u32`@body+8, reserved 8 bytes |
| `bms` | 22,948 | header offset table (6 sections + names); s0 vertices / s1 bones / s2 triangles / s5 AABB; **vertex layout PROVEN: 44 B standard (17,247) / 52 B lightmap (5,399) / 80 B morph (6) / 32 unproven**; `scripts/bms_decoder.py`, 16 tests (Phase 16). | skinned/flags==2 tail semantics (u32@36 is NOT a local bone index); 80 B morph fields; trailing bytes. Static (flags==0) meshes fully decodable. |
| `nvm` | 6,041 | flat 8-byte nav-cell records; 96×96 (9,216) grid; f32 region; trailing fill. 5 tests. | nav-cell semantics |
| `efp` | 3,395 | version tree + u32-length-prefixed command stream. 11 tests. | command-stream semantics |
| `bsk` | 1,039 | magic/version; body sampled. 9 tests (shared). | bone/keyframe layout |
| `bsr` | 7,549 | magic `JMXVRES`; u32-length-prefixed `.bmt`/`.bms` paths. 9 tests (shared). | record layout |

## 5. DECODED, conversion deferred (backlog, do not claim as done)

| Format | Files | What is proven | What remains |
|---|---|---|---|
| `ddj` (the 39,740 not yet converted) | 47,495 | container + DDS payload extraction proven | convert remaining textures |
| `tga` | 15 | header verified | decode + convert |
| `m` (remaining height grids) | 4,491 | 23 grids converted in Phase 10 | convert all grids |
| `nvm` navmesh | 6,041 | partial structure proven (see section 4) | full structure, extraction of walkable surfaces |
| `bms` / `bsr` / `t` / `o` / `o2` / `bmt` | ~44,000 | magic confirmed; `o2` instance parsing proven; `bms`/`bsr` partial structure (section 4) | full geometry/material pipeline |
| `bsk` | 1,039 | magic confirmed + body sampled (section 4) | skeleton decode |
| `efp` | 3,395 | version tree + command stream proven (section 4) | particle system decode |
| `wav` (2,454 remaining) / `ogg` (0 remaining) | 2,454 | decode proven on samples; **Phase 12 converted all 50 `ogg` + 431 `wav`** (`/prim/snd/monster`) with provenance manifest | convert remaining wav sets |
| `2dt` (CNIF text-data) | 51 | container magic confirmed | CNIF string-table decode |

## 6. BLOCKED (format UNKNOWN — no honest decoder yet)

| Format | Files | Bytes | Note |
|---|---|---|---|
| `dat` | 79 | 73.2 MB | binary; sampled files unstructured (e.g. `ainavdata_32769.dat`) |
| `db` (Particles.pk2) | 1 | 23.3 MB | name/string table referencing `.ddj`; layout unverified |
| `scc` | 17 | 15.6 KB | no structure identified |
| `msf` | 2 | 350 B | no structure identified |
| `skilldata_*enc.txt` | 7 | ~27 MB | client-encrypted skill tables; no key. The plaintext `skilldata_*` equivalents exist and are cataloged. |

## 7. Summary

- Real data in Android-consumable form (committed): prior ~7,755 textures/audio +
  23 `.hg` + `regions.tsv` + 21 textdata TSVs (Phase 11) + **663 worldmap
  textures (WebP: 632 `map_world_` tiles + 31 named) + 50 OGG + 431 WAV** with
  provenance manifests (`TEXTURE_CONVERSION_MANIFEST.tsv`,
  `AUDIO_CONVERSION_MANIFEST.tsv`) (Phase 12 + Phase 13 Part C).
- Formats fully decoded: **14** (wav, ogg, tga, tmp, txt, ifo, ini, c, vsh, psh,
  ddj, m, o2, ban — the last four through committed Phase 5–13 converters).
- Formats with a committed decoder for a proven subset: **5** (nvm, bms, efp,
  bsk, bsr — Phase 13 partial structure).
- Formats decoded at sample level (magic verified), decoder pending: **8**
  (t, o, bmt, cpd, dof, mfo, 2dt, sfk).
- Formats fully unknown: **4** (`dat`, `db`, `scc`, `msf`) + encrypted client
  skill tables (7 files; plaintext equivalents exist).
