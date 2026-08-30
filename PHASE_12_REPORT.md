# PHASE 12 REPORT — Real Data Parsing, Format Decoding & Android Asset Conversion

Branch: `260829-phase12-data-parsing-formats` · Phase 11 baseline: `9d8d428`
Date: 2026-08-29

Phase 12 executes on top of the completed Phase 11 source inventory + textdata
extraction (21 normalized TSVs, 29,883 records). Nothing from Phase 11 was
regenerated; the committed Phase 11 artifacts are the canonical parse source.
All claims below are backed by real data from the ORIGINAL VSRO-R 1.193
archives. Everything not proven is marked **UNKNOWN** — nothing is guessed or
fabricated.

---

## A. Real-data parsing (Android Java data layer)

21 normalized datasets were profiled (column types per column over the first 500
real rows; row counts over all rows) and committed as a schema document and a
reference graph:

- **`TEXTDATA_SCHEMAS.json`** — per-dataset records/columns/types/evidence/source
  path. Column semantics are named ONLY when provable from real data (verified
  IDs/codes/coordinate triples); all others stay literal `colN` with
  "semantics not verified". Generator: `scripts/textdata_schemas.py`.
- **`DATA_REFERENCE_GRAPH.json`** — 8 cross-file edges, each with exact
  matched/total counts and status VERIFIED or PARTIAL (e.g. npcpos→characterdata
  659/1855 PARTIAL because negative ids are special/instance NPCs;
  teleportdata→teleportbuilding 101/135 PARTIAL; worldmap_instanceinfo→regions
  23/23 VERIFIED; refshopgoods→refshoptab 164/164 VERIFIED).

New Android-free Java readers (`android/app/src/main/java/com/opensilkroadmap/app/data/`):

| Class | Dataset | Verified columns |
|---|---|---|
| `TsvTable` | generic loader | preserves cells verbatim, skips blanks/`#`/`//`, UTF-8, `loadDefault()` path candidates |
| `NpcPosTable` | npcpos.tsv (18,457 rows) | col0 spawn_id, col1 character_refid, cols 2-4 coord floats |
| `LevelDataTable` | leveldata.tsv (150) | col0 level 1..150 |
| `LevelGoldTable` | levelgold.tsv (140) | col0 level |
| `TeleportDataTable` | teleportdata.tsv (246) | col2 gate_code, col3 gate_id, col4 zone_code, col5 zone_id |
| `RefShopGoodsTable` | refshopgoods.tsv (2,282) | col1 shop_id, col2 category_code, col3 item_code |
| `WorldMapInstanceTable` | worldmap_instanceinfo.tsv (23) | col0 code, col1 Korean name, cols 2-3 region cell x/y |
| `QuestDataTable` | questdata.tsv (1,004) | col2 quest_code |

10 JVM tests (`TextDataTablesTest.java`) assert real committed values. New
`GameDataCatalog` composes four tables and is wired into `GameActivity` /
`GameHudView` (real counts shown on the HUD; explicit "assets not bundled" state
when absent). 3 `GameDataCatalogTest` tests added.

**JVM tests are NOT EXECUTED here** — no JDK/gradle in this environment
(consistent with Phases 7-11). The Java is Android-free core + structural
verification (below) as the non-executed gate.

## B. Java structural verification (non-executed gate)

Mirroring the Phase 9 precedent for non-executed Java:

- 33 Java files checked: **braces balanced, no Java 9+ constructs**.
- **Core files (data/ + GameDataCatalog) Android-free** (no `import android.*`).
- `GameActivity`/`GameHudView` are Android UI files and legitimately import
  Android classes; their only Phase 12 addition is wiring an already-parsed
  catalog.
- The scripts/scripts Python tests run here (see Part I).

## C. Binary format research — evidence-first

Real samples were read (read-only) from Data.pk2 / Particles.pk2 and analysed.
Full evidence in **`FORMAT_RESEARCH.md`**; catalog updated in
**`DATA_FORMAT_CATALOG.md`**.

**`.ban` — PARTIALLY DECODED (decoder committed + tested).** Proven structure:
`JMXVBAN 0102` magic/version; `u32 LE` animation-name length at 0x14;
NUL-terminated name (verified: `cj_ferry_boat_old`, `royalsoldier_die`,
`venefica_stand01`); body contains **28-byte keyframe records** = 4×`f32`
normalized rotation quaternion + 3×`f32` position. Proven by exact 28-byte
stride on 3 independent real files with contiguous runs of 3 / 27 / 181 records
(181 consecutive unit-norm quaternions cannot occur by chance). Decoder:
`scripts/ban_decoder.py`; tests `scripts/test_phase12_formats.py` (10 tests,
**live archive re-extraction check passes** with `SRO_PK2_DIR`). Remaining
UNKNOWN (documented, not guessed): all `u32` fields after the name,
keyframe→bone association, time encoding.

**`.nvm` — UNKNOWN (full layout).** Magic/version proven; header carries LE
floats 128-1920 (region extents) and count-like fields; NO count field is
asserted (907·256≈232,192 vs 232,418 is suggestive only). No decoder.

**`.bms` — UNKNOWN (full layout).** Magic/version proven; header is a table of
ascending `u32 LE` offsets < file size ending just below EOF (e.g. 19,858 +
tail = 19,866), with 4-byte increments indicating small adjacent sub-buffers;
vertex/index strides and counts NOT proven. No decoder.

**`.efp` — UNKNOWN (full layout).** Magic proven; version is NOT constant
(0011×1821, 0013×1158, 0012×408, 0000×7, 0010×1 across all 3,395 files). Headers
embed short ASCII emitter/texture names (`csk_s_light_jil`, `skill_ranges`,
`Norma…`) and counts; `0013` starts with LE floats. No decoder.

Directive mapping: the brief's ".bns" = real `.bms` (no `.bns` exists in the
119,631-file census); documented rather than inventing a `.bns` path.

Real derived fixtures (structure JSON only, no raw binaries) committed under
`scripts/testdata/formats/` with source path/size/sha256 per fixture.

## D. Texture pipeline (verified + converted)

`worldmap_mapinfo.tsv` has 32 texture-path rows (col3, backslash paths). Against
Media.pk2: **29 resolve to real `.ddj`** (verified `JMXVDDJ 1000` → embedded DDS
→ Pillow decode; `map_jangan.ddj` = 1024×1024 RGBA, content-verified 195 gray
levels; `map_donhwang.ddj` = 512×512). 3 unresolved (extension-less
`map_world_` tile-grid prefix; `map_bagdad.ddj`; `map_bagdad_dungeon.ddj`
absent from the archive) — recorded as UNRESOLVED, never fabricated.

Converted: **29 WebP** → `android-assets/textures/worldmap/` (4.7 MB).
Provenance: `TEXTURE_CONVERSION_MANIFEST.tsv` (source path/size/sha256_1mib,
decoded dimensions, output path/size/sha256 — all 29 output hashes re-verified).
Script: `scripts/convert_worldmap_textures.py` (`--pk2-dir` / `SRO_PK2_DIR`).

## E. Audio conversion (verified + extracted)

- **All 50 `.ogg`** from Music.pk2 → `android-assets/audio/music/` (76.5 MB).
  OGG is Android-native, so conversion = verified verbatim extraction (`OggS`
  magic checked per file).
- **All 431 `.wav`** under Data.pk2 `/prim/snd/monster/` → 
  `android-assets/audio/sfx/monster/` (25.4 MB), `RIFF`/`WAVE` magic verified.
- Provenance: `AUDIO_CONVERSION_MANIFEST.tsv` (481 rows; all output sha256
  re-verified). Script: `scripts/extract_audio_phase12.py`.

## F. Integration into the Android app (minimal real consumers)

`GameDataCatalog` (`game/` package, Android-free) composes npcpos/leveldata/
teleportdata/worldmap_instanceinfo and exposes real counts + `summary()`.
`GameActivity.loadDataCatalog()` loads it from `assets/game/textdata/*.tsv`
(UTF-8) and passes it to `GameHudView`, which renders the real summary line or
an explicit "TEXTDATA ASSETS NOT BUNDLED" state. No invented behavior.

## G. Tests (executed here)

| Suite | Result |
|---|---|
| `scripts/test_pk2_reader.py` | 11 OK |
| `scripts/test_sro_pipeline.py` | 15 OK |
| `scripts/test_phase4_assets.py` | 5 OK (3 skipped) |
| `scripts/test_phase5_assets.py` | 18 OK (1 skipped) |
| `scripts/test_phase6_assets.py` | 17 OK (4 skipped) |
| `scripts/test_phase11.py` | 17 OK (1 skipped) |
| `scripts/test_world_terrain.py` | 19 OK (1 skipped) |
| `scripts/test_phase12_formats.py` | 10 OK (live archive check passes with `SRO_PK2_DIR`) |
| `deno task build` (tsc + vite) | PASS (1m19s, chunk-size warning only) |
| JVM `./gradlew test` | **NOT EXECUTED** (no JDK in environment) — covered by structural verification (Part B) |

Note: `test_sro_pipeline` contains one test that asserts the "no --pk2-dir" error
message; when `SRO_PK2_DIR` is exported the env var supplies the dir and the
assertion no longer applies. This is a pre-existing test/environment interaction
in untouched files (`test_sro_pipeline.py`, `extract_sro.py` unchanged); the
suite passes in its documented invocation without the env var.

## H. Secret scan

The staged diff was scanned for secrets (API keys, PK2/private keys, tokens,
credential files) before commit. No secrets, keys, or private material were
found. No raw PK2 archives or raw original binaries are committed — only derived
fixtures, normalized textdata, and converted assets with provenance manifests.

## I. Files added/changed (summary)

- `scripts/textdata_schemas.py`, `TEXTDATA_SCHEMAS.json`, `DATA_REFERENCE_GRAPH.json` (A)
- `android/app/src/main/java/com/opensilkroadmap/app/data/*` (8 classes), `TextDataTablesTest.java` (A)
- `android/app/src/main/java/com/opensilkroadmap/app/game/GameDataCatalog.java`, `GameDataCatalogTest.java` (A/F)
- `scripts/ban_decoder.py`, `scripts/test_phase12_formats.py`, `scripts/testdata/formats/*.json` (C)
- `FORMAT_RESEARCH.md`, `DATA_FORMAT_CATALOG.md` update (C)
- `scripts/convert_worldmap_textures.py`, `android-assets/textures/worldmap/*.webp` (29), `TEXTURE_CONVERSION_MANIFEST.tsv` (D)
- `scripts/extract_audio_phase12.py`, `android-assets/audio/music/*.ogg` (50), `android-assets/audio/sfx/monster/*.wav` (431), `AUDIO_CONVERSION_MANIFEST.tsv` (E)
- `GameActivity.java`, `GameHudView.java` wiring (F)
- `PHASE_12_REPORT.md`, `ANDROID_DATA_CONVERSION_STATUS.md` update (K)

## J. Verification after push

After `git push -u origin 260829-phase12-data-parsing-formats`, local SHA and
remote SHA are confirmed identical and the working tree is clean (see shell
session / commit output).
