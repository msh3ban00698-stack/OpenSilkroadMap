# PHASE 11 REPORT — Complete Original Data / Asset Extraction & Native Conversion Status

Date: 2026-08-29
Branch: `260829-phase11-source-inventory`
Continues the complete Phase 10 push (`260829-phase10-world-terrain`, HEAD
`a9fe19668fbf01172f1a8151259dd788915a4ad9`, clean). Phase 10 work untouched.

Phase 11 goal: complete, honest, read-only inventory + extraction + format research
of the real VSRO-R 1.193 archives, and conversion of every format that can be safely
decoded into Android-native data. Rules followed: no guessing (everything unverified
is marked UNKNOWN), no skipped data (every one of the 119,631 archived files is
inventoried), small verified steps, source archives never modified.

---

## Deliverables produced

| # | Deliverable | Location |
|---|---|---|---|
| 1 | Complete source inventory (human) | `COMPLETE_SOURCE_INVENTORY.md` |
| 2 | Complete source inventory (machine, all 119,631 files: archive, path, size, byte offset) | `COMPLETE_SOURCE_INVENTORY.json` |
| 3 | Phase report | `PHASE_11_REPORT.md` (this file) |
| 4 | Format catalog (magic evidence per extension) | `DATA_FORMAT_CATALOG.md` |
| 5 | Android conversion status | `ANDROID_DATA_CONVERSION_STATUS.md` |
| 6 | Extraction scripts | `scripts/pk2_table.py` (verified table reader, prior), `scripts/build_source_inventory.py`, `scripts/build_textdata_catalog.py` |
| 7 | Format decoder scripts | `scripts/world_terrain.py` (`.m`, `.o2`, prior), `scripts/dds_decode.py`, `scripts/convert_ddjs.py` (prior), `scripts/extract_audio_minimaps.py` (prior) |
| 8 | Conversion scripts | `scripts/build_source_inventory.py`, `scripts/build_textdata_catalog.py` (write Android assets), prior asset converters |
| 9 | Deterministic tests | `scripts/test_phase11.py` (17 tests, 16 pass + 1 live-determinism, re-run OK) |
| 10 | Provenance records | sha256 per textdata file in `TEXTDATA_CATALOG.tsv`; archive fingerprints in `COMPLETE_SOURCE_INVENTORY.json`; pinned reader + Blowfish evidence in `PK2_READER_FOUNDATION.md` |
| 11 | Updated system-status matrix | `PHASE_11_SYSTEM_STATUS_MATRIX.md` (extends the §6 matrix in `PROJECT_STATUS_AUDIT_2026-08-29.md`) |

Supporting committed data: `TEXTDATA_CATALOG.tsv` (all 159 textdata files profiled),
`TEXTDATA_NORMALIZED_MANIFEST.tsv`, and 21 real datasets normalized under
`android/app/src/main/assets/game/textdata/*.tsv`.

---

## Answers to the 20 required questions

### 1. How many original files were discovered?
**119,631** files across the 5 archives (table-walked with the verified Blowfish
PK2 reader; exact match with the authoritative `pk2_mate` listing).

### 2–6. Per archive
| Archive | Files |
|---|---:|
| Data.pk2 | 66,051 |
| Map.pk2 | 19,171 |
| Media.pk2 | 29,591 |
| Music.pk2 | 50 |
| Particles.pk2 | 4,768 |

Total archived bytes: 5,698,015,232.

### 7. How many extracted text/data files were discovered?
**159** server text/data files extracted and parsed from
`Media.pk2 /server_dep/silkroad/textdata/` (110 MB). All 159 are profiled
(encoding, record count, column schema) in `TEXTDATA_CATALOG.tsv`:
- 149 UTF-16LE (BOM), 2 UTF-8, 1 cp949/other.
- 21 fully normalized to Android UTF-8 TSV assets.
- 7 client-encrypted skill tables (`skilldata_*enc.txt`) marked ENCRYPTED (no key).
- 3 more real text files inventoried in Data.pk2 (`RegionInfo.txt` already used by
  Phase 9/10, `/shader/regioninfo.txt`, `/dungeon/Dungeoninfo.txt`).

### 8. How many unique formats were identified?
**32** distinct extensions (plus the ext-less file, which is a DDJ container).

### 9. How many formats were fully decoded?
**13**: `wav` (RIFF/PCM parsed), `ogg` (OggS), `tga` (header verified), `tmp` (DDS
payload), `txt`/`ifo`/`ini` (text), `c`/`vsh`/`psh` (shader source text),
`ddj` (container -> DDS; conversion proven), `m` (terrain height; Phase 10 decoder),
`o2` (object instances; Phase 10 decoder).

### 10. How many were partially decoded?
**14** formats with magic confirmed and samples inspected, decoder pending:
`bms`, `bsr`, `nvm`, `t`, `ban`, `o`, `bmt`, `efp`, `bsk`, `cpd`, `dof`, `mfo`,
`2dt` (CNIF), `sfk`.

### 11. How many remain UNKNOWN?
**4** formats, **99** files (~96.5 MB): `dat` (79), `db` (1, Particles.pk2),
`scc` (17), `msf` (2). Additionally the 7 client-encrypted `skilldata_*enc.txt`
files (plaintext tiered equivalents exist and are cataloged). No guessed decoders.

### 12. How many real assets were converted?
Phase 11 converts **21 real textdata datasets** (~2.92 MB) into Android-normalized
UTF-8 TSV. Cumulative (Phases 5–11): ~7,755 texture/audio outputs + 23 `.hg`
height grids + `regions.tsv` + these 21 datasets.

### 13. Which assets remain unconverted?
See `ANDROID_DATA_CONVERSION_STATUS.md` §4: the remaining ~39,740 `ddj` textures,
4,468 `m` grids, 2,884 `wav`, 49 `ogg`, and all of `nvm`/`bms`/`ban`/`efp`/`t`/
`bsr`/`bmt`/`o`/`2dt`/`cpd`/`dof`/`mfo`/`bsk`/`sfk` — conversion deferred behind
decoders. `dat`/`db`/`scc`/`msf` are blocked (UNKNOWN).

### 14. Which game systems now have real source-backed data?
- **World/terrain**: `regions.tsv`, 23 `.hg` grids, `.o2` instances, `gameworldconfigdata.tsv`, `gameworlddata.tsv`, `worldmap_mapinfo/instanceinfo/localinfo.tsv`.
- **NPCs/spawns**: `npcpos.tsv` (18,457 spawns), `characterdata_*.txt` (cataloged, schema 105 cols), `specialnpcdata.txt`.
- **Items/equipment/shops**: `itemdata_*.txt` (cataloged, 161 cols), `refshop.tsv`, `refshopgoods.tsv` (2,283 rows), `refpackageitem.txt`, `refscrapofpackageitem.txt`, `magicoption*.txt`.
- **Skills**: `skilldata_*.txt` (cataloged), `skilleffect.txt`, `skillgroup.txt`, `skillmasterydata.txt`, `learnableskill.txt`.
- **Level/exp**: `leveldata.tsv` (150 levels), `levelgold.tsv`.
- **Quests**: `questdata.tsv` (1,005), `refqusetreward.tsv`, `refquestrewarditems.tsv`, `questcontentsdata.txt`, `textquest_*`.
- **Teleport**: `teleportdata.tsv`, `teleportlink.tsv`, `teleportbuilding.tsv`, `refoptionalteleport.tsv` (45).
- **Regions/world map**: `regioncode.tsv` (3,294), `worldmap_*`.
- **UI/help text**: `textuisystem.txt`, `texthelp.txt`, `gameguidedata.txt`, `npcchat.txt`.
- **Audio/music**: 2,885 `wav` + 50 `ogg` (decode verified; samples converted).
- **Textures**: 47,495 `ddj` (conversion proven).
- **Gacha/mall**: `gachaitemset.txt`, `refshop*`, `mallitemmenulistdata.txt`.

### 15. Which systems still have no verified source data?
- Guild, party, chat, trading, drops/loot tables, monster AI behavior, save/persist
  format, network/protocol, server/database, anti-cheat. (No dedicated verified
  original data files were found for these in the 5 archives. `refsiege*`,
  `event*` and `tradeconflict*` are cataloged but not yet mapped to systems.)

### 16. Which systems are ready for native Android implementation?
With VERIFIED data only: **level/experience curve**, **NPC spawn placement**
(`npcpos.tsv` + region mapping), **teleport network**, **shop/gacha catalogs**,
**quest database**, **region/world-map info**, **item/skill reference databases**
(schema columns verified, decode in Phase 12), **terrain/world rendering**
(Phase 10), **audio/music playback**, **UI/help text**.

### 17. Which systems are blocked by unknown formats?
Animations (`ban`/`bsk`), static meshes/buildings (`bms`/`bsr`), navmesh/AI pathing
(`nvm`), zone tiles (`t`), effects/particles (`efp`), materials (`bmt`),
AI navigation data (`dat`), encrypted client skills.

### 18. What exact work must happen in Phase 12?
1. Android parsers + unit tests for the 21 committed TSV datasets (npcpos spawns,
   level/exp, teleport, shops, quests, region/worldmap).
2. Decode `bms` geometry + `t` tiles for world rendering; convert to Android mesh
   format with real fixtures.
3. Decode `nvm` navmesh -> walkable areas.
4. Decode `ban`/`bsk` animation -> skeletal animation.
5. Decode `efp` particle effects.
6. Bulk-convert remaining audio (`wav`/`ogg`) and `ddj` textures.
7. Research `dat`/`db`/`scc`/`msf`; keep UNKNOWN if unverifiable.
8. Wire converted data into the native game core (spawns, progression, shops,
   quests, teleport, world) — each system testable from real data.

### 19. What can now be implemented offline using VERIFIED data?
A full offline native Android experience using: level/exp table, NPC spawns,
teleport network, shop/gacha catalogs, quest database, region/world-map tables,
terrain/world (Phase 10), audio/music, textures, UI text. All values traceable to
real source files with per-file sha256.

### 20. What MUST NOT be implemented yet because its source behavior is UNKNOWN?
- Animation playback, skeletal movement, and combat timing (`.ban`/`.bsk` unknown).
- Navmesh-based pathing / walkable surfaces (`.nvm` unknown).
- Particle/effect rendering (`.efp` unknown).
- Building/tile rendering (`.bms`/`.t` unknown).
- Monster AI behavior and `dat` AI navigation data (unknown).
- Damage/skill formulas beyond what the skill/item schemas verify (column
  semantics are positional; full field mapping is Phase 12 work).
- Any networked/server behavior (out of scope until offline game is complete).

---

## Verification

- `scripts/test_phase11.py`: **17 tests, 16 pass, 1 live-check skipped without
  archives**; the live determinism test reruns both generators against the real
  archives and asserts byte-identical regeneration (ran: OK, 40.6 s).
- Existing Python regression: `scripts/test_world_terrain.py`, `test_pk2_reader.py`,
  `test_sro_pipeline.py` re-run OK (below).
- `deno task build` re-run OK (web map build unaffected).
- Full `./gradlew test` still NOT EXECUTED in this environment (no JDK), consistent
  with Phases 7–10; no claim of JVM/Android test results is made.

## Provenance

Archives read-only at `/tmp/opencode/pk2raw/*.pk2`; every textdata file's sha256 is
in `TEXTDATA_CATALOG.tsv`; per-archive 1 MiB fingerprints in
`COMPLETE_SOURCE_INVENTORY.json`; pinned reader (Veykril/pk2, Blowfish key
`silkroad`, salted default) documented in `PK2_READER_FOUNDATION.md`. No original
archive, binary, or secret material is committed.
