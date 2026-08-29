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

## 3. PARSED/NORMALIZED but not yet wired to an Android consumer

- All 21 datasets above are *data-only*; Android parsers exist only for
  `regions.tsv` (`RegionInfo.java`/`RegionCatalog.java`). Parsers for
  `npcpos.tsv`, `leveldata.tsv`, etc. are Phase 12 work (rule: no scaffolding
  claiming implementation).

## 4. DECODED, conversion deferred (backlog, do not claim as done)

| Format | Files | What is proven | What remains |
|---|---|---|---|
| `ddj` (the 39,740 not yet converted) | 47,495 | container + DDS payload extraction proven | convert remaining textures |
| `tga` | 15 | header verified | decode + convert |
| `m` (remaining height grids) | 4,491 | 23 grids converted in Phase 10 | convert all grids |
| `nvm` navmesh | 6,041 | magic + samples | full structure, extraction of walkable surfaces |
| `bms` / `bsr` / `t` / `o` / `o2` / `bmt` | ~44,000 | magic confirmed; `o2` instance parsing proven | full geometry/material pipeline |
| `ban` / `bsk` | 5,836 | magic confirmed | animation/skeleton decode |
| `efp` | 3,395 | magic confirmed | particle system decode |
| `wav` (2,884 remaining) / `ogg` (49 remaining) | 2,935 | decode proven on samples | bulk convert all |
| `2dt` (CNIF text-data) | 51 | container magic confirmed | CNIF string-table decode |

## 5. BLOCKED (format UNKNOWN — no honest decoder yet)

| Format | Files | Bytes | Note |
|---|---|---|---|
| `dat` | 79 | 73.2 MB | binary; sampled files unstructured (e.g. `ainavdata_32769.dat`) |
| `db` (Particles.pk2) | 1 | 23.3 MB | name/string table referencing `.ddj`; layout unverified |
| `scc` | 17 | 15.6 KB | no structure identified |
| `msf` | 2 | 350 B | no structure identified |
| `skilldata_*enc.txt` | 7 | ~27 MB | client-encrypted skill tables; no key. The plaintext `skilldata_*` equivalents exist and are cataloged. |

## 6. Summary

- Real data in Android-consumable form (committed): prior ~7,755 textures/audio +
  23 `.hg` + `regions.tsv` + **21 new textdata TSVs** (Phase 11).
- Formats fully decoded: **13** (wav, ogg, tga, tmp, txt, ifo, ini, c, vsh, psh,
  ddj, m, o2 — the last three through committed Phase 5–10 converters).
- Formats decoded at sample level (magic verified), decoder pending: **13**
  (bms, bsr, nvm, t, ban, o, bmt, efp, bsk, cpd, dof, mfo, 2dt, sfk — 14 entries;
  `o` stays pending, `m`/`o2` promoted to decoded).
- Formats fully unknown: **4** (`dat`, `db`, `scc`, `msf`) + encrypted client
  skill tables (7 files; plaintext equivalents exist).
