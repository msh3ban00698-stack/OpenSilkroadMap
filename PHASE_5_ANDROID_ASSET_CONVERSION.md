# PHASE 5 — Android Asset Conversion & Verification

Date: 2026-08-29
Status: COMPLETE (controlled conversion proof only; no bulk conversion)

This phase establishes a **VERIFIED Android-ready asset layer** from the real
vSRO 1.193 PK2 archives. Every claim below is backed by byte-level inspection
and decoding of the actual files. Where a format could not be verified, it is
marked UNKNOWN and left untouched.

VERIFIED / INFERRED / UNKNOWN are distinguished explicitly throughout.

---

## 1. Scope

Convert a **small controlled proof set** of already-verified assets into
Android-ready outputs; verify each conversion; record full traceability; commit
the proof layer. Bulk conversion of thousands of files is explicitly out of
scope. No EXE/DLL execution, no gameplay, no server, no multiplayer, no SQL.

## 2. Source archives

All five PK2 archives from Phase 4 (SHA256 verified then, unchanged since):

| Archive | Size (B) | SHA256 |
| --- | --- | --- |
| Data.pk2 | 3,351,891,968 | `e61c8477ba1b1864ddd3e65f2e840d2d426c34e588fe2853dff3b2e800e61c17` |
| Map.pk2 | 1,268,441,088 | `ae482b3bb6853281158f94ba976e2a242c3df8e037b4704757498a7d371987e5` |
| Media.pk2 | 823,066,624 | `134731ac6c0fe30a4557f4210e1236386b976c65432def1fd74b5d74ce67c0fb` |
| Music.pk2 | 76,488,704 | `f1ce4723e76cae2bb67cd6524fdeaa7f031da4f483e283461f99809f46e5f5b2` |
| Particles.pk2 | 178,126,848 | `558027e2ec33e96ed17a5341726c3b9fdc7def769660393ee47083eb8dd56596` |

Originals live at `/tmp/opencode/pk2raw/` (outside the repo, never committed).
They were **not modified** in this phase (verified by re-listing; extraction is
read-only).

## 3. Tools

| Tool | Version / pin | Purpose |
| --- | --- | --- |
| pk2_mate | v0.0.0, commit `e07dec06…`, MIT | PK2 list/extract (reader of record) |
| Python | 3.11.2 | conversion scripts |
| `scripts/dds_decode.py` | NEW (this phase) | pure-Python (stdlib-only) DDS decoder + deterministic PNG encoder |
| Pillow | 12.3.0 | independent cross-check of the DDS decoder (installed for validation only) |
| `scripts/convert_android_assets.py` | NEW (this phase) | controlled conversion + traceability manifest |
| `scripts/test_phase5_assets.py` | NEW (this phase) | 18 tests (13 pure + 5 manifest + Pillow/real cross-checks) |

The DDS decoder is **stdlib-only** (struct, zlib), so conversion output is
deterministic and Pillow is not required to reproduce it.

## 4. DDJ / DDS investigation (VERIFIED)

A controlled `.ddj` sample set (10 files across all five archives) was parsed
byte-by-byte. Every file:

- begins with the **20-byte** JMX header `JMXVDDJ 1000` + 8 bytes;
- at offset 20 carries a **standard `DDS `** container (`DDS_HEADER` 124 bytes);
- has valid `dwHeight`/`dwWidth`/`dwMipMapCount` and a `DDS_PIXELFORMAT`.

Pixel formats VERIFIED present in real samples:

| FourCC / bit masks | Real sample(s) | VERIFIED |
| --- | --- | --- |
| `DXT1` (BC1) | `Media/minimap/100x100.ddj`, `Map/tile2d/alex_dust_01.ddj` | yes |
| `DXT3` (BC2) | `Particles/textures/00illusion_basic.ddj`, `Data/compound/particle/electus_m_xmas.ddj` | yes |
| 16-bit RGB (R5G6B5) | `Media/script/image/qno_script_background_white.ddj` | yes |
| 16-bit ARGB1555 | `Media/interface/minimap/mm_alpha.ddj`, `Media/effect/icon/cool_time_0.ddj` | yes |
| 32-bit X8R8G8B8 | `Media/interface/2secret/sec_num_00.ddj` | yes |
| 32-bit A8R8G8B8 | `Media/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj` | yes |

Mipmaps: `alex_dust_01.ddj` (10) and `electus_m_xmas.ddj` (11) carry mip chains;
the decoder reads the base level (0). Dimensions of all 10 decoded outputs were
verified against the DDS header and independently against Pillow (identical).

**Converter used:** `scripts/dds_decode.py` — a from-scratch, stdlib-only
decoder for exactly these verified formats. It refuses everything else
(`UnsupportedPixelFormat`), including DXT5. Output is PNG via a deterministic
zlib encoder (byte-for-byte reproducible, no timestamps).

> Android note: BitmapFactory cannot decode DDS, so DDJ->PNG is the Android
> path. The pure-Python decoder was chosen so the conversion is reproducible
> without Pillow; PNG is a safe, universally decodable texture format.

## 5. Direct Android-compatible formats (VERIFIED, no conversion needed)

| Format | Verified structure | Android consumption | Proof asset |
| --- | --- | --- | --- |
| Ogg Vorbis | `OggS`, vorbis id: v0, 2 ch, 44100 Hz | `MediaPlayer`/`ExoPlayer` | `Music/jangan_town.ogg` |
| WAV PCM | `RIFF`/`WAVE`, PCM fmt=1, mono, 22050 Hz, 16-bit | `MediaPlayer`/`SoundPool` | `Data/prim/snd/am_mob/am_crab_die.wav` |
| ASCII text | 7-bit ASCII verified | parse directly | `Data/RegionInfo.txt`, `Data/dungeon/Dungeoninfo.txt`, `Media/config/command.txt` |
| UTF-16LE text | `fffe` BOM verified | decode to UTF-8 for Android | `Media/server_dep/silkroad/textdata/*.txt` |

These were **copied byte-identical** (audio) or **re-encoded to UTF-8 without
changing semantics** (text) into `android-assets/`. OGG/WAV are not recompressed.

## 6. Successfully converted formats (VERIFIED)

| Source | Action | Output | Count |
| --- | --- | --- | --- |
| `.ddj` (all verified pixel formats) | DDJ->PNG (pure-Python) | `android-assets/maps/*.png`, `textures/*.png` | 10 |
| `.ogg` | byte-identical copy | `android-assets/audio/` | 1 |
| `.wav` | byte-identical copy | `android-assets/audio/` | 1 |
| `.txt` (UTF-16LE / ASCII) | re-encode to UTF-8 | `android-assets/data/` | 6 |

Total 18 controlled conversions, **0 failures**. Every output was re-opened and
validated (PNG header/dimensions/CRC, OGG/WAV container metadata, UTF-8
round-trip) as recorded in `android-assets/manifest.json`.

## 7. Controlled proof samples

The conversion set is curated in `scripts/convert_android_assets.py`
(`CONVERSION_MANIFEST`) using paths taken from the Phase 4 listings. Samples
cover: world minimap (DXT1), dungeon minimap (A8R8G8B8), tile texture (DXT1
+mips), UI minimap (ARGB1555), UI digits (X8R8G8B8), effect icon (ARGB1555),
script background (RGB565), particle textures (DXT3), compound texture (DXT3
+mips), town BGM (OGG), mob die SFX (WAV), and game text data (UTF-16LE/ASCII).

Generated tree (all committed):

```
android-assets/
  maps/     3 PNG   (minimap, dungeon minimap, tile2d)
  textures/ 7 PNG   (interface, script, effect, particle, compound)
  audio/    2 files (jangan_town.ogg, am_crab_die.wav)
  data/     6 UTF-8 text files (RegionInfo, Dungeoninfo, command, textdata)
  manifest.json
```

## 8. Unknown formats (VERIFIED as unknown — NOT converted)

| Extension | Magic / marker | Android status | Action | Reason |
| --- | --- | --- | --- | --- |
| `.bms` | `JMXVBMS 0110` | UNKNOWN | DO NOT CONVERT | 3D mesh structure not decoded |
| `.bsr` | `JMXVRES 0109` | UNKNOWN | DO NOT CONVERT | material/resource structure not decoded |
| `.cpd` | `JMXVCPD 0101` | UNKNOWN | DO NOT CONVERT | compound model structure not decoded |
| `.ban` | `JMXVBAN 0102` | UNKNOWN | DO NOT CONVERT | animation structure not decoded |
| `.efp` | `JMXVEFF 0011` | UNKNOWN | DO NOT CONVERT | particle effect structure not decoded |
| `.nvm` | `JMXVNVM 1000` | UNKNOWN | DO NOT CONVERT | navmesh inner layout not decoded |
| `AINavData_*.DAT` | binary (no JMX magic) | UNKNOWN | DO NOT CONVERT | navmesh data layout unknown |
| Map `.t` | `JMXVMAPT1001` | UNKNOWN | DO NOT CONVERT | terrain geometry |
| Map `.m` | `JMXVMAPM1000` | UNKNOWN | DO NOT CONVERT | region mesh |
| Map `.o` / `.o2` | `JMXVMAPO1001` | UNKNOWN | DO NOT CONVERT | region objects |
| `fonts/*.dat` | `JMXVIMG 1100` | UNKNOWN | DO NOT CONVERT | font/image structure not decoded |
| `res_ui/*.2dt` | — | UNKNOWN | DO NOT CONVERT | layout structure not decoded |
| `.ifo` (`object.ifo`, `config.ifo`) | `JMXVOBJI1000` / `JMXVCAMR1002` | DEFERRED | schema study later | plaintext index seen, meaning not yet established |

These were inspected at byte level in Phase 4/5 and remain **explicitly unknown**;
no decoder was invented for them.

## 9. Deferred formats

| Extension | Status | Reason / next step |
| --- | --- | --- |
| `.ifo` | DEFERRED | plaintext content observed but not yet interpreted into an Android schema |
| `.ddj` other pixel formats (e.g. DXT5) | UNKNOWN for SRO | only formats found in the real sample set were implemented; new ones require a fresh sample + verification |
| `.2dt`, `fonts/*.dat` | DEFERRED | low priority for Phase 5; require UI/font study |

## 10. Output layout

`android-assets/` at repo root (see §7). Audio/data dirs mirror their Android
roles; textures/maps are separated by function. No original PK2 archive or any
extraction workdir is inside this tree — it holds only generated proof assets +
`manifest.json`.

## 11. Traceability method

Every generated file has an entry in `android-assets/manifest.json` carrying:

- `pk2`, `source_path`, `source_extension`
- `source_size`, `source_sha256`
- `action`, `detected_format` (from real bytes), `mipmaps`
- `output_path`, `output_size`, `output_sha256`
- `width`/`height` (images), OGG/WAV metadata, `validation` string
- `result` (`ok`/`error`) — failures are recorded, never dropped

Paths come from the Phase 4 `pk2_mate list` listings; none are fabricated.

## 12. Validation / tests

New `scripts/test_phase5_assets.py` (18 tests):
- 13 pure decoder tests: DXT1 4-color/3-color, DXT3 alpha+color, RGB565,
  ARGB1555, X8R8G8B8, A8R8G8B8, DXT5 refusal, bad-magic refusal, DDJ round-trip,
  PNG determinism + header validity — all with hand-computed expected pixels.
- Pillow cross-check on real samples (`SRO_PHASE5_SAMPLES=/tmp/opencode/phase4/extract`)
  — **all 10 real DDJs decode byte-identical to Pillow**.
- Manifest consistency: outputs exist, SHA256 matches, PNG dimensions match,
  audio metadata (22050 Hz mono 16-bit PCM; 44100 Hz stereo Vorbis), UTF-8
  round-trip.

Existing suites re-run, all green:
- `test_pk2_reader.py` 11/11
- `test_sro_pipeline.py` 15/15
- `extract_sro.py validate` OK
- `test_phase4_assets.py` 5/5

One regression found and fixed this phase: `convert_android_assets.py` initially
hardcoded `/tmp/opencode` (work-dir default + docstring), which
`test_sro_pipeline.py::test_no_script_hardcodes_vsro_tmp` flags. Default work dir
now uses `tempfile.mkdtemp`.

## 13. Known limitations

- **Bulk conversion not done.** Only the 18 controlled proofs were produced;
  converting the full `Media` (~29k `.ddj`) and other archives is a later phase.
- **Pillow installed only for validation.** The committed pipeline does not need
  it; final Android rendering decisions (PNG vs WEBP/KTX) are not made here.
- **Data/Map full extraction still blocked** by disk; format conclusions for
  `Data`/`Map` come from controlled samples only.
- **3D/navmesh/particle formats remain unknown**; nothing about them was guessed.
- **Android readiness for decoded textures is asserted from structure + successful
  decode + validation, not from filename.**

## 14. Next-phase recommendation (ONE)

**Phase 6: Bulk texture conversion + minimap pack integration.** Convert the
verified `.ddj` sets with real world impact — `Media/minimap/*` (5,523) and
`Media/minimap_d/*` (2,214) — to PNG/WEBP in a resource budget study (sizes,
decode time, memory on a representative device), extend the deterministic
decoder to the remaining `.ddj` pixel formats found during the bulk run, and
validate a bundled minimap pack loads on Android. Audio (OGG/WAV) and text
(UTF-8) are already Android-ready and need no further conversion work.
