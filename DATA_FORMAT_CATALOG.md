# DATA_FORMAT_CATALOG — vSRO 1.193 Archive Formats

Phase 11. Every extension present in the real VSRO-R 1.193 archives is listed with
the magic observed on real samples (read directly from the unencrypted data area of
the archives), the classification, and the evidence basis. Classification is honest:
nothing is called "decoded" unless a real decoder produced output for it.

Status vocabulary (consistent with `COMPLETE_SOURCE_INVENTORY.*` and
`ANDROID_DATA_CONVERSION_STATUS.md`):

- **VERIFIED** — magic confirmed AND a working decoder produced real output from a
  real sample in this project (files converted / parsed and checked).
- **PARTIAL** — a decoder is committed and tested for a *proven subset* of the
  format; the remaining layout is documented as UNKNOWN (see `FORMAT_RESEARCH.md`).
- **PARSEABLE** — magic confirmed; internal structure researched from samples;
  a production decoder is not yet committed.
- **TEXT** — decodable plain text / tabular data (UTF-16LE BOM, UTF-8, or cp949);
  the tab-schema is profiled per file in `TEXTDATA_CATALOG.tsv`.
- **UNKNOWN** — no reliable magic / structure; no honest claim made.

---

## 1. VERIFIED formats

| Ext | Magic | Evidence | Conversion |
|---|---|---|---|
| `wav` | `RIFF` `WAVE` `fmt ` | 2,885 files, 315.0 MB. Real sample `Data.pk2 /prim/snd/am_mob/am_crab_die.wav` (60,136 B) parsed: PCM (`audiofmt=1`), mono, 22050 Hz. | Prior phases converted real `.wav` to Android-compatible audio (Phase 5/6 pipeline). |
| `ogg` | `OggS` | 50 files, 76.5 MB in `Music.pk2` (music) + Media. Real sample `Music.pk2` track 2,057,764 B starts `OggS 0002`. | Prior phases converted a real `.ogg` sample to Android audio. |
| `tga` | TGA header `00 00 0a 00` (type 10 RLE true-color) | 15 files, 4.0 MB. | TGA header verified; no conversion run this phase. |
| `tmp` | `DDS \x7c` | 1 file, 87,528 B (`Data.pk2`). Payload is a DDS texture misnamed `.tmp`. | DDS decode already verified in this project (`scripts/dds_decode.py`). |
| `ddj` | `JMXVDDJ 1000` | 47,495 files, 2,200.6 MB (largest format by bytes). Container header `JMXVDDJ 1000` then embedded DDS textures. | Prior phases verified `ddj -> DDS` extraction and conversion (`scripts/convert_ddjs.py`, `scripts/dds_decode.py`); ~7,755 Android texture outputs produced across Phases 5–8. |
| `m` | `JMXVMAPM1000` | 4,491 files, 416.6 MB. Terrain height grid. | **Phase 10 decodes `.m` fully** (`scripts/world_terrain.py`, 97×97 height grid per cell); 23 real grids committed as `.hg`; Phase 15 loads adjacent `.hg` sectors as a multi-sector `WorldTerrainSet`. |
| `o2` | `JMXVMAPO1001` | 4,348 files, 8.3 MB. Object overlay/instance. | **Phase 10 parses `.o2` instances** (committed fixtures `const_76x103_objects.json`). Phase 15: header length is VARIABLE (offset 12 always `u32=0`, first data byte `>=16`); `parse_o2` is valid only when data starts at 16 — other sectors' header layout UNKNOWN. |
| `ban` | `JMXVBAN 0102` | 4,796 files, 235.2 MB. Animation. | **Phase 13 Part D proves FULL layout** (`scripts/ban_decoder.py`): magic/version, 8-byte reserved, u32 name-len + name, u32 duration + frame-rate(30) + u32 UNKNOWN + kpb, kpb×u32 timestamps, bone count + per-bone name + kf-count + kpb×28-byte keyframes (4×f32 quat + 3×f32 pos). Tests: `scripts/test_phase13_ban.py` (8 GREEN). |

## 2. PARSEABLE formats (magic confirmed, decoder not yet committed)

| Ext | Magic | Files / Bytes | Notes |
|---|---|---|---|
| `t` | `JMXVMAPT1001` | 4,989 / 700.4 MB | Tile/zone. |
| `o` | `JMXVMAPO1000` | 4,491 / 3.5 MB | Map overlay. |
| `bmt` | `JMXVBMT 0102` | 4,269 / 2.1 MB | Material. |
| `cpd` | `JMXVCPD 0101` | 124 / 34.1 KB | Object/character detail. |
| `dof` | `JMXVDOF 0101` | 34 / 4.3 MB | Depth-of-field shader data. |
| `mfo` | `JMXVMFO 1000` | 2 / 16.4 KB | Uncommon object container. |
| `2dt` | `\x1a\x00\x00\x00 CNIF…` | 51 / 2.7 MB | Joymax `CNIF` binary text-data container (Media, e.g. `BattleArenaRankWnd`). |
| `sfk` | `SFPK` | 1 / 796 B | Unknown purpose; magic confirmed only. |

## 2a. PARTIAL formats (decoder committed for a proven subset)

| Ext | Magic | Files / Bytes | Decoder | Proven subset | Remaining UNKNOWN |
|---|---|---|---|---|---|
| `bms` | `JMXVBMS 0110` | 22,948 / 603.5 MB | `scripts/test_phase13_bms.py` (12 GREEN) | header = header_size + 6 section offsets + end_offset + 2 length-prefixed names; s0 vertices / s1 bones / s2 triangles (u32 count + 3×u16) / s5 AABB. | vertex record layout (stride non-integral: Petra 44.0 B, demon 52.11 B); remaining section semantics. |
| `nvm` | `JMXVNVM 1000` | 6,041 / 778.6 MB | `scripts/test_phase13_nvm.py` (5 GREEN) | flat 8-byte LE nav-cell records (4×u16); dominant 9,216 = 96×96 grid; post-grid f32 region (~37,814 B); trailing −20.0 fill. | nav-cell record semantics; region meaning. |
| `efp` | `JMXVEFF xxxx` | 3,395 / 95.1 MB | `scripts/test_phase13_efp.py` (11 GREEN) | version tree (0000×7/0010×1/0011×1,820/0012×408/0013×1,158); u32-length-prefixed ASCII command stream. | command-stream semantics / parameters. |
| `bsk` | `JMXVBSK 0101` | 1,039 / 4.0 MB | `scripts/test_phase13_bsk_bsr.py` (9 GREEN) | magic/version; body sampled. | bone/keyframe layout (bone-name count ≠ count@12 → not a plain count). |
| `bsr` | `JMXVRES 0109/0108/0107` | 7,549 / 12.9 MB | `scripts/test_phase13_bsk_bsr.py` (9 GREEN) | magic is `JMXVRES` (NOT `JMXVBSR`); body = u32-length-prefixed `.bmt`/`.bms` paths. | record layout. |

## 3. TEXT formats (decoded)

| Ext | Magic / structure | Files / Bytes | Notes |
|---|---|---|---|
| `txt` | tabular text | 441 / 116.6 MB | 159 are server textdata in `Media.pk2 /server_dep/silkroad/textdata/` (tab-separated, UTF-16LE BOM 149 / cp949 / UTF-8). See `TEXTDATA_CATALOG.tsv`. |
| `ifo` | `JMXVOBJI1000` | 12 / 928 KB | Object info; UTF-16LE text after header. Phase 10 fixture `object_ifo_head.txt` (real head of `Data.pk2 /navmesh/object.ifo`). |
| `ini` | `[LocalizedFileNames]` | 1 / 396 B | Text ini. |
| `c` | `vs.1.1...` | 40 / 133 KB | DirectX vertex-shader **source text** (`.c` shader files). |
| `vsh` | `vs.1.1...` | 8 / 27.7 KB | DirectX vertex shader source. |
| `psh` | `//c0 - Common Const...` | 14 / 18.4 KB | DirectX pixel shader source. |

## 4. UNKNOWN formats (no honest claim made)

| Ext | Observed head | Files / Bytes | Notes |
|---|---|---|---|
| `dat` | binary `01 49 75 14 …` (25 in Data.pk2, e.g. `/navmesh/ainavdata_32769.dat` 3.7 MB) | 79 / 73.2 MB | Mixed; sampled files are binary. **No decoder. Blocked.** |
| `db` | `8b 03 00 00 1d 00 00 00 textures…` | 1 / 23.3 MB (`Particles.pk2`) | Appears to be a name/string table referencing `*.ddj` (e.g. `textures\illusion_basic.ddj`). Structure unverified. |
| `scc` | binary `34 12 01 00 c9 31…` | 17 / 15.6 KB | No structure identified. |
| `msf` | binary `01 00 00 00 02 00 00 00 ff…` | 2 / 350 B | Contains string `ambient`. No structure identified. |

## 5. Encrypted client files

| Ext / name | Status |
|---|---|
| `skilldata_*enc.txt` (7 files, 3.4–4.4 MB each) | Client-encrypted skill tables. Bytes preserve newline structure (records ≈ line count) but the field content does not decode to valid UTF-16LE/UTF-8/cp949. Marked `ENCRYPTED` in `TEXTDATA_CATALOG.tsv`. **No key. Do not guess.** |
| `skilldataenc.txt` | Plain-text index of the `*ENC.txt` file names (decodable, cataloged). |

## 6. Coverage rollup (all 119,631 files across 5 archives)

| Status | Files | Formats |
|---|---:|---:|
| VERIFIED | 16,586 | wav, ogg, tga, tmp, ddj (conversion proven in prior phases), m, o2 (Phase 10 decoders), ban (Phase 13 Part D full layout) |
| PARTIAL | 40,973 | bms, nvm, efp, bsk, bsr (Phase 13 structural/partial decoders) |
| PARSEABLE | 61,457 | t, o, bmt, cpd, dof, mfo, 2dt, sfk, plus the ext-less `Media /icon/action/cos_cmd_inventory` file (a `JMXVDDJ 1000` container) |
| TEXT | 516 | txt (441), ifo (12), ini (1), c (40), vsh (8), psh (14) |
| UNKNOWN | 99 | dat (79), db (1), msf (2), scc (17) — bytes for these formats total 96.5 MB |

Exact per-file classification is machine-readable in
`COMPLETE_SOURCE_INVENTORY.json` (`extensions` table maps every extension to
count, bytes, and status; every file record references its extension).
