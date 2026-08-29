# Android Asset Manifest — VSRO v1.193

Phase 4 deliverable. A verified, evidence-based manifest of the REAL vSRO 1.193
PK2 assets for the future Android-native client. Every row is backed by an actual
extraction and byte inspection in this session. Nothing here is converted to a
final Android format yet, and no format is chosen by guessing.

Conventions: **VERIFIED** = confirmed from real bytes this session.
**UNKNOWN — DO NOT CONVERT YET** = real file inspected, but its internal format is
not understood well enough to convert. Companion docs:
`PK2_READER_FOUNDATION.md` (Phase 3, reader + validation),
`PK2_ACCESS_AND_ASSET_PIPELINE.md` (Phase 2), `EXTERNAL_PACKAGE_INVENTORY.md` (Phase A).

Session: 2026-08-29. Raw evidence outside the repo under `/tmp/opencode/phase4/`.
No proprietary archive, large extraction, or converted asset is committed.

---

## 1. Source Archives (VERIFIED)

All five archives validated by `scripts/validate_pk2.py` and fully listed by
`pk2_mate` (pinned commit `e07dec06…`, MIT). Raw files at `/tmp/opencode/pk2raw/`.

| Archive | Size (B) | SHA256 | Header | list rc | entries |
| --- | --- | --- | --- | --- | --- |
| Data.pk2 | 3,351,891,968 | `e61c8477ba1b1864ddd3e65f2e840d2d426c34e588fe2853dff3b2e800e61c17` | VERIFIED | 0 | 66,051 |
| Map.pk2 | 1,268,441,088 | `ae482b3bb6853281158f94ba976e2a242c3df8e037b4704757498a7d371987e5` | VERIFIED | 0 | 19,171 |
| Media.pk2 | 823,066,624 | `134731ac6c0fe30a4557f4210e1236386b976c65432def1fd74b5d74ce67c0fb` | VERIFIED | 0 | 29,591 |
| Music.pk2 | 76,488,704 | `f1ce4723e76cae2bb67cd6524fdeaa7f031da4f483e283461f99809f46e5f5b2` | VERIFIED | 0 | 50 |
| Particles.pk2 | 178,126,848 | `558027e2ec33e96ed17a5341726c3b9fdc7def769660393ee47083eb8dd56596` | VERIFIED | 0 | 4,768 |

Entry counts match the prior Phase A inventory (`EXTERNAL_PACKAGE_INVENTORY.md`):
Data 66,051 · Map 19,171 · Media 29,591 · Music 50 · Particles 4,768.

Inventory method (reproducible): `pk2_mate list` -> `scripts/inventory_pk2.py`.
Full per-archive listings saved at `/tmp/opencode/phase4/listings/*.list.txt`
(outside repo); per-archive `*_inv.json` at `/tmp/opencode/phase4/`.

## 2. Verified Real Sizes (partially measured by full extraction)

Data and Map are only partially extracted (controlled samples only) because the
raw archives (~4.6 GB) plus a full extraction (~4.6 GB) exceed the available disk.
Their per-directory totals are therefore **not** re-measured here; only the three
smaller archives were fully extracted:

| Archive | Full extraction size (B) | Note |
| --- | --- | --- |
| Media.pk2 | 819,003,922 | fully extracted |
| Music.pk2 | 76,475,511 | fully extracted |
| Particles.pk2 | 177,456,277 | fully extracted |
| Data.pk2 | (partial) | controlled samples only |
| Map.pk2 | (partial) | controlled samples only |

Media by top-level dir (VERIFIED from full extraction):

| Directory | files | bytes |
| --- | --- | --- |
| interface | 8,418 | 294,206,846 |
| minimap | 5,523 | 226,064,636 |
| server_dep | 165 | 114,208,765 |
| minimap_d | 2,214 | 96,829,432 |
| icon | 8,654 | 39,143,511 |
| icon64 | 4,209 | 31,645,503 |
| script | 25 | 9,649,686 |
| res_ui | 51 | 2,744,716 |
| resinfo | 243 | 2,105,786 |
| launcher (+europe) | 50 | 2,028,298 |
| effect | 26 | 351,880 |
| config | 5 | 22,576 |
| fonts | 3 | 312 |
| root misc | 8 | 4,169 |

Media by extension (VERIFIED): `.ddj` 29,025 / 697,621,324 · `.txt` 436 /
116,552,778 · `.2dt` 51 / 2,744,716 · `.dat` 52 / 2,025,408 · `.tga` 9 / 41,160 ·
`.scc` 16 / 15,316 · other 2.

Music (VERIFIED): 50 `.ogg`, 76,475,511 B total (BGM only, no SFX here).

Particles by top-level (VERIFIED from full extraction):

| Directory | files | bytes | dominant ext |
| --- | --- | --- | --- |
| textures | 1,000 | 80,885,290 | .ddj (textures) |
| system | 785 | 33,891,710 | .efp |
| monster | 1,089 | 30,684,152 | .efp |
| skill | 784 | 14,086,267 | .efp |
| dun | 251 | 7,308,079 | .efp |
| map | 168 | 2,811,851 | .efp |
| cos | 89 | 2,423,239 | .efp |
| co | 55 | 1,738,802 | .efp |
| meshes | 264 | 1,277,008 | .bms |
| hiteffect | 84 | 1,044,673 | .efp |
| battle | 70 | 477,106 | .efp |
| item | 9 | 424,069 | .efp |
| animations | 107 | 210,126 | .ddj/.efp |
| npc | 11 | 192,171 | .efp |
| shader | 2 | 1,734 | .c |

## 3. Verified Format Detection (magic bytes, not filename guessing)

35 controlled samples were extracted and their first bytes inspected
(`scripts/extract_samples.py`; report `/tmp/opencode/phase4/extract_report.json`).

| Magic (ASCII) | Extensions | Where | Verdict |
| --- | --- | --- | --- |
| `JMXVDDJ 1000` + 8 B + `DDS ` | `.ddj` | Media (UI/minimap/icon), Map tile2d, Data compound, Particles textures | DDS container: DXT1, DXT3, RGB16, RGB32 verified; inner DDS header valid (124 B, correct w/h) |
| `JMXVNVM 1000` | `.nvm` | Data /navmesh | navmesh data, proprietary |
| `JMXVMAPT1001` | `.t` | Map regions | terrain height/geometry, proprietary |
| `JMXVMAPM1000` | `.m` | Map regions | region mesh, proprietary |
| `JMXVMAPO1001` | `.o`, `.o2` | Map regions | region objects, proprietary |
| `JMXVOBJI1000` | `object.ifo` | Map | text index -> `.bsr` refs (sample shows `res\bldg\china\cj_ferry\*.bsr`) |
| `JMXVCAMR1002` | `config.ifo` | Map | camera settings, proprietary |
| `JMXVBMS 0110` | `.bms` | Data prim/mesh, Particles meshes | model mesh, proprietary |
| `JMXVRES 0109` | `.bsr` | Data res/prim | material/resource, proprietary |
| `JMXVCPD 0101` | `.cpd` | Data compound | compound model, proprietary |
| `JMXVBAN 0102` | `.ban` | Data prim/ani, Particles animations | animation, proprietary |
| `JMXVEFF 0011` | `.efp` | Particles | particle effect, proprietary |
| `JMXVIMG 1100` | `.dat` | Media /fonts | font/image, proprietary |
| `RIFF`+`WAVE` | `.wav` | Data prim/snd | PCM 16-bit mono 22050 Hz verified |
| `OggS` | `.ogg` | Music | Vorbis (113 pages verified on sample) |
| `\xff\xfe` (UTF-16 LE BOM) | `.txt` | Media server_dep textdata | game text data, parseable |
| ASCII | `.txt`, `RegionInfo.txt`, `Dungeoninfo.txt` | Media config, Data root | plain text/tab-separated |
| Windows `thumbs.db` | `.db` (1 file, 23 MB) | Particles /textures/thumbs.db | NOT a game asset — Windows Explorer thumbnail cache packed into the archive; must be excluded |

DDJ inner-DDS verification (VERIFIED): for every sampled `.ddj`, bytes 20..24 =
`DDS `, bytes 24..28 = 124 (DDS_HEADER), width/height read correctly (e.g. minimap
`100x100.ddj` = 256x256 DXT1, `tile2d/alex_dust_01.ddj` = 512x512 DXT1,
`qno_script_background_white.ddj` = 768x1024 RGB16). The repo already strips the
20-byte JMX header in `scripts/convert_ddjs.py` (Pillow consumes the DDS).

## 4. Android Suitability by Asset Category

### 4.1 Directly Android-usable today (VERIFIED)

| Asset | PK2 path | Format | Android path | Conversion required |
| --- | --- | --- | --- | --- |
| Region minimaps | `Media/minimap/*.ddj` (5,523) | JMX-DDS (DXT1) | decode DDS -> PNG/WEBP (Android BitmapFactory does NOT read DDS) | YES — decode DDS; repo Pillow path proven |
| Dungeon minimaps | `Media/minimap_d/*.ddj` (2,214) | JMX-DDS (DXT1/RGB) | same | YES — decode DDS |
| UI art | `Media/interface/**/*.ddj` (8,418) | JMX-DDS (RGB16/32/DXT) | same | YES — decode DDS |
| Icons | `Media/icon/*.ddj`, `Media/icon64/*.ddj` (12,863) | JMX-DDS | same | YES — decode DDS |
| BGM | `Music/*.ogg` (50) | Ogg Vorbis | `MediaPlayer`/`ExoPlayer` natively | NO |
| SFX | `Data/prim/snd/*.wav` (2,885) | PCM WAV | `MediaPlayer`/`SoundPool` natively | NO |
| Game text data | `Media/server_dep/silkroad/textdata/*.txt` (159) | UTF-16 LE | parse -> JSON/DB | YES — decode text, no asset conversion |
| Config text | `Media/config/*.txt`, `Data/RegionInfo.txt`, `Data/dungeon/Dungeoninfo.txt` | ASCII | parse -> JSON | YES — decode text |

### 4.2 Requires format research before conversion (UNKNOWN — DO NOT CONVERT YET)

| Asset | PK2 path | Magic | Status |
| --- | --- | --- | --- |
| Navmesh | `Data/navmesh/nv_*.nvm` (6,041) + `AINavData_*.DAT` (27) + `mapinfo.mfo` | `JMXVNVM 1000` / binary | inner layout not yet decoded; repo `generate_navmesh.py` consumes it for the web map — Android path UNKNOWN |
| Region terrain | `Map/<row>/*.t` (4,988) | `JMXVMAPT1001` | UNKNOWN — DO NOT CONVERT YET |
| Region mesh | `Map/<row>/*.m` (4,491) | `JMXVMAPM1000` | UNKNOWN — DO NOT CONVERT YET |
| Region objects | `Map/<row>/*.o` `*.o2` (8,839) | `JMXVMAPO1001` | UNKNOWN — DO NOT CONVERT YET |
| Model meshes | `Data/prim/mesh/**/*.bms` (incl. Particles meshes 264) | `JMXVBMS 0110` | UNKNOWN — DO NOT CONVERT YET |
| Materials | `Data/res/**/*.bsr`, `Data/prim/**/*.bsr` | `JMXVRES 0109` | UNKNOWN — DO NOT CONVERT YET |
| Compound models | `Data/compound/*.cpd` | `JMXVCPD 0101` | UNKNOWN — DO NOT CONVERT YET |
| Animations | `Data/prim/ani/**/*.ban` + Particles `.ban` | `JMXVBAN 0102` | UNKNOWN — DO NOT CONVERT YET |
| Particle effects | `Particles/**/*.efp` (3,395) | `JMXVEFF 0011` | UNKNOWN — DO NOT CONVERT YET |
| Fonts | `Media/fonts/*.dat` (3) | `JMXVIMG 1100` | UNKNOWN — DO NOT CONVERT YET |
| res_ui / resinfo | `Media/res_ui/*.2dt`, `Media/resinfo/*` | `.2dt` / text | UNKNOWN — DO NOT CONVERT YET |
| Tile textures | `Map/tile2d/*.ddj` (752) | JMX-DDS | decode DDS (4.1) but use-case on Android UNKNOWN |

### 4.3 Not a game asset (VERIFIED)

- `Particles/textures/thumbs.db` (23,264,254 B): Windows `thumbs.db` thumbnail
  cache — packed authoring artifact, exclude from any extraction/package.

## 5. Selected Verified Sample Extractions (evidence)

From `scripts/extract_samples.py` (all 35 OK; full table in
`/tmp/opencode/phase4/extract_report.json`):

| PK2 | Internal path | Size (B) | SHA256 (short) | Type |
| --- | --- | --- | --- | --- |
| Media | `/minimap/100x100.ddj` | 32,916 | `bc7b1276…` | JMX-DDS 256x256 DXT1 |
| Media | `/server_dep/silkroad/textdata/npcpos.txt` | 1,262,460 | `6be53bc2…` | UTF-16 LE |
| Media | `/script/image/qno_script_background_white.ddj` | 1,573,012 | `76588dff…` | JMX-DDS 768x1024 RGB16 |
| Media | `/interface/minimap/mm_alpha.ddj` | 21,780 | `8afdad73…` | JMX-DDS 104x104 RGB16 |
| Data | `/navmesh/AINavData_32768.DAT` | 1,396,691 | `267f6e18…` | binary (navmesh) |
| Data | `/navmesh/nv_11a4.nvm` | 111,926 | `0e8b0fab…` | JMXVNVM |
| Data | `/RegionInfo.txt` | 58,974 | `787d9b41…` | ASCII |
| Data | `/prim/ani/avatar/booth_mob_bigeyeghost.ban` | 811 | `065626ad…` | JMXVBAN |
| Data | `/prim/snd/am_mob/am_crab_die.wav` | 60,136 | `d2b59582…` | PCM 22050 Hz mono |
| Map | `/100/100.t` | 140,436 | `1ebcf9f0…` | JMXVMAPT |
| Map | `/100/100.m` | 92,712 | `212cfa71…` | JMXVMAPM |
| Map | `/object.ifo` | 231,665 | `2c85272d…` | JMXVOBJI text index |
| Map | `/tile2d/alex_dust_01.ddj` | 174,924 | `f1f94e02…` | JMX-DDS 512x512 DXT1 |
| Particles | `/battle/deco_charge_light_a.efp` | 6,099 | `f6a17735…` | JMXVEFF |
| Music | `/jangan_town.ogg` | 470,512 | `96d67924…` (Phase 3) | Ogg Vorbis |

Full 35-row table with per-file sha256 is produced by rerunning:

```bash
python3 scripts/extract_samples.py --pk2-dir /tmp/opencode/pk2raw \
  --reader-bin /tmp/opencode/pk2_mate --out /tmp/opencode/phase4/extract \
  --json /tmp/opencode/phase4/extract_report.json
```

## 6. Controlled-Proven Conversion (Phase 5)

Phase 4 proved the DDJ structure; **Phase 5 performed the conversion proof**:
a pure-Python, stdlib-only DDS decoder (`scripts/dds_decode.py`) was written for
exactly the verified pixel formats (DXT1, DXT3, RGB565, ARGB1555, X8R8G8B8,
A8R8G8B8) and a deterministic PNG encoder. It decodes all 10 real sampled DDJs
**byte-identical to Pillow**, and 18 controlled conversions (10 images, 2 audio
copies, 6 UTF-8 texts) were produced into `android-assets/` with full
traceability in `android-assets/manifest.json`. No bulk conversion was run;
final Android formats (PNG vs WEBP vs KTX/ASTC) remain Phase 6+ decisions.
See `PHASE_5_ANDROID_ASSET_CONVERSION.md`.

## 7. What Is NOT Included / Blocked

- **No Data.pk2 / Map.pk2 full extraction**: raw archives (~4.6 GB) + extraction
  would exceed free disk. Only controlled samples were taken; Data/Map per-dir byte
  totals remain **UNVERIFIED** (counts verified, sizes not re-measured).
- **No Android conversion**: see §6.
- **No 3D/particle format conversion**: all JMX 3D/particle formats remain
  UNKNOWN — DO NOT CONVERT YET.
- **In-repo Python PK2 reader absent**: `pk2reader.py` / `jmblowfish.py` not in repo
  (carried blocker); pk2_mate covers CLI access only.
- `listing_media.txt` / `listing_music.txt`: NOT FOUND (optional for repo extractors).

## 8. Recommended Phase 6 (from VERIFIED evidence only)

1. **Bulk texture conversion + minimap pack integration** (Phase 6): convert
   `Media/minimap/*` (5,523) and `Media/minimap_d/*` (2,214) `.ddj` to PNG/WEBP,
   with a resource budget study; extend the deterministic decoder to any new
   `.ddj` pixel formats found during the bulk run; validate a bundled minimap
   pack loads on Android. Audio and text are already Android-ready.
2. When disk allows (or on a machine with the raw PK2s), run full Media
   extraction (already proven: 819,003,922 B) and full Data/Map extraction to
   complete the verified inventory totals for Data/Map.
3. Research `.nvm` navmesh + `.bsr` material structure (repo tooling exists for
   navmesh) — first 3D-adjacent candidates.
4. All other JMX 3D/particle formats remain UNKNOWN until individually decoded with
   real samples; do not convert.

## 9. Phase 7 status

`android-assets/manifest.json` (7,755 records, schema `sro-android-assets-v2`) is now
the authoritative mapping consumed by the Android asset layer in
`map/src/game/minimap_assets.ts` (resolver + validating loader + bounded cache,
manifest-driven, no filename guessing). Phase 7 chose PNG as the shipping minimap
format. See `PHASE_7_ANDROID_MINIMAP_INTEGRATION.md`.
