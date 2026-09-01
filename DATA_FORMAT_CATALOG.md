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
| `ddj` | `JMXVDDJ 1000` | 47,495 files, 2,200.6 MB (largest format by bytes). 20-byte header: 12-byte magic + `u32 data_size` (= `file_size − 12`, PROVEN across samples) + `u32 level` (constant 3; semantics UNKNOWN), then a standard embedded DDS at offset 20 (uncompressed RGB 16/24/32 bpp or `DXT3` fourcc). | Prior phases verified `ddj -> DDS` extraction and conversion (`scripts/convert_ddjs.py`, `scripts/dds_decode.py`); ~7,755 Android texture outputs produced across Phases 5–8. **This phase commits `scripts/jmx_ddj.py`** (deterministic 20-byte header + DDS metadata parser: width/height/bpp/masks/fourcc), `scripts/test_jmx_parsers.py`. |
| `bmp` (in `.dat`) | `BM` (Windows BITMAPFILEHEADER) | 48 / ~2.5 MB (`Media.pk2 /launcher/*`, `/launcher_europe/*`) | Launcher UI bitmaps misnamed `.dat`. Standard BMP; `bg_1.dat` = 700×419 32 bpp, `bg_*`/`bg_division_*`/`bitmap_g`/`gauge*`/`config_*`/etc. all `BM`. Reclassified by `scripts/dat_families.py`. |
| `jmxvimg` (in `.dat`) | `JMXVIMG11000` | 3 / 312 B (`Media.pk2 /fonts/{0,i,y}.dat`) | **NEW JMX family.** Image/glyph container: 12-byte magic + u16 field@12 + u16 field@14 + 4-byte BGRA pixel data. Font glyph bitmaps (the glyphs for `0`, `i`, `y`). Reclassified by `scripts/dat_families.py`. |
| `palette` (in `.dat`) | (none — 768-byte 256×RGB) | 1 / 768 B (`Media.pk2 /silk.dat`) | 256-entry RGB color palette (768 B = 256 × 3). Classic 16-color VGA head (`00 00 00`, `80 00 00`, …). Reclassified by `scripts/dat_families.py`. |
| `hex-token` (in `.dat`) | ASCII hex `[0-9A-F]` | 2 / 340 B (`Silkload.dat` in client + `.7z`) | ASCII hex string token/ID (no newline). Reclassified by `scripts/dat_families.py`. |
| `plugin` (in `.dat`) | `u32 count` + 16-byte id + name | 1 / 46 B (`Map.pk2 /plugin.dat`) | Plugin loader manifest: u32 LE count, per entry 16-byte identifier (GUID/hash) + u16 LE name length + null-terminated name. Single entry `bsnetEx.dll`. Reclassified by `scripts/dat_families.py`. |
| `m` | `JMXVMAPM1000` | 4,491 files, 416.6 MB. Terrain height grid. | **Phase 10 decodes `.m` fully** (`scripts/world_terrain.py`, 97×97 height grid per cell); 23 real grids committed as `.hg`; Phase 15 loads adjacent `.hg` sectors as a multi-sector `WorldTerrainSet`. |
| `o2` | `JMXVMAPO1001` | 4,348 files, 8.3 MB. Object overlay/instance. | **Phase 17 PROVES the record layout** (`scripts/o2_decoder.py`, 12 GREEN): walker from offset 16 consumes every file exactly (variable header = zero-count-group padding); record = `u32 nameI + 3x f32 x/y/z + u16 + f32 theta + 3x u16 + u16 tail` (30 B); `world = (tail − ref) × 1920 + local`. 32 real instances in 156x90 resolve to real trees. |
| `o` | `JMXVMAPO1001` (7 empty `JMXVMAPO1000`) | 4,491 files, 3.5 MB. Object overlay/instance. | **PROVEN** (`scripts/o2_decoder.py::parse_o`, `scripts/test_phase17_o.py`, 9 GREEN): shares `JMXVMAPO1001` + group framing with `.o2` but uses a 28 B record (drops `unknown3`, tail at 26); full 4,484-file walk consumes every file exactly; `max nameI == 3306` (object.ifo 0..3306). `tail` is RELATIVE (0 = own sector, 1 = +x, 256 = +z) vs `.o2`'s absolute sector. `/100/100.o` = 58 instances `{1489:39, 669:11, 1488:7, 1748:1}`. |
| `ban` | `JMXVBAN 0102` | 4,796 files, 235.2 MB. Animation. | **Phase 13 Part D proves FULL layout** (`scripts/ban_decoder.py`): magic/version, 8-byte reserved, u32 name-len + name, u32 duration + frame-rate(30) + u32 UNKNOWN + kpb, kpb×u32 timestamps, bone count + per-bone name + kf-count + kpb×28-byte keyframes (4×f32 quat + 3×f32 pos). Tests: `scripts/test_phase13_ban.py` (8 GREEN). **Phase 18** adds pose evaluation (`scripts/animation_pose.py`, 10 GREEN): per-bone channels aligned to global timestamps, slerp/pos-lerp adjacent-key interpolation. **Phase 19** exports ALL keyframes (bandit walk 34×15, stand01 34×5), proves LOOPING (first==last channel data, root motion loop-contained), proves the channel space (absolute parent-relative replacing bind), and documents 2 `JMXVBAN 0101` anomalies as UNKNOWN (4,793/4,795 `0102` byte-exact). |
| `bsk` | `JMXVBSK 0101` | 1,039 / 4.0 MB. Skeleton. | **Phase 18 proves FULL layout** (`scripts/bsk_decoder.py`, 9 GREEN): u32 bone_count@12; per bone u8 type + str name + str parent + 21×f32 (rot_parent4/tr_parent3/rot_origin4/tr_origin3/rot_local4/tr_local3) + u32 child_count + children + 8 zero trailer; byte-exhausts 1,034/1,035 nonzero files. Quaternion convention **PROVEN `[x,y,z,w]`** via bind-pose alignment to real mesh bounds. **Phase 19 proves transform semantics** (`test_phase19_bsk_semantics.py`): rot_origin/tr_origin == world bind; rot_parent/tr_parent == local; rot_local/tr_local == inverse-bind (root proven, child PARTIAL); `bone_type` u8 census = constant 0 across 29,957 bones (meaning UNKNOWN). |
| `bsr` | `JMXVRES 0109/0108/0107` | 7,549 / 12.9 MB. Mesh resource. | **Phase 18 proves FULL layout** (`scripts/bsr_decoder.py`): 8×u32 table@12 + 16 zero bytes + body@0x3C = u32-len-prefixed ASCII token stream; classified `.bmt/.bms/.ban/.bsk/.efp/.wav`; `is_character` = has `.bsk`; bandit resolves 3 bmt + 3 bms + 16 ban + 1 bsk + 7 efp + 16 wav. |
| `bmt` | `JMXVBMT 0102` | 4,269 / 2.1 MB. Material. | **PROVEN** (`scripts/world_terrain.py::parse_bmt_entries`, `scripts/test_phase18_t_bmt.py`): magic + `u32 count`; per entry `u32 name_len` + null-padded material name + 72 B (18×f32 material props: ambient/diffuse/specular/emissive RGBA + extras) + `u32 ddj_len` + null-padded `.ddj` texture path + 7 B tail (`f32 1.0` + 3 B). All 4,269 files / 16,328 entries parse byte-exactly; null-padding now stripped (fixes `.endswith('.ddj')` lookups). |
| `cpd` | `JMXVCPD 0101` | 124 / 34.1 KB. Compound manifest. | **PROVEN** (`scripts/cpd_decoder.py::parse_cpd`, `scripts/test_phase21_cpd.py`, 7 GREEN): magic + `u32 primary_off` + `u32 count_off` + 20 B reserved + `u16 type` (0=char, 2=object) + `u16 subtype` (always 3) + `u32 name_len` + name + `u32 flag_x` + `u32 flag_y` + `u32 primary_len` + optional primary `.bsr` path + `u32 count` + `count × {u32 len + .bsr path}`. All 124 files parse byte-exactly and self-consistently; every component path is a `.bsr` reference. `flag_x`/`flag_y` semantics UNKNOWN (observed {0,3} / {0,1,2}). |

## 2. PARSEABLE formats (magic confirmed, decoder not yet committed)

| Ext | Magic | Files / Bytes | Notes |
|---|---|---|---|
| `mfo` | `JMXVMFO 1000` | 2 / 16.4 KB | Uncommon object container. |
| `2dt` | `\x1a\x00\x00\x00 CNIF…` | 51 / 2.7 MB | Joymax `CNIF` binary text-data container (Media, e.g. `BattleArenaRankWnd`). |
| `sfk` | `SFPK` | 1 / 796 B | Unknown purpose; magic confirmed only. |

## 2a. PARTIAL formats (decoder committed for a proven subset)

| Ext | Magic | Files / Bytes | Decoder | Proven subset | Remaining UNKNOWN |
|---|---|---|---|---|---|
| `t` | `JMXVMAPT1001` | 4,989 / 700.4 MB | `scripts/world_terrain.py::parse_t` + `parse_tile2d_ifo` + `scripts/test_phase18_t_bmt.py` (13 GREEN) | 12-byte magic + verified size `140,436` = 12 + 140,424 (4,987 standard files); body is a dense 8-bit grid dominated by `0x00`/`0xFF`; as u16 cells, ~40% are tile IDs within `tile2d.ifo` range 0..718 (cross-referenced), the rest `0xFFFF`/`0x0000` "empty" markers + RGB565-looking colors. `tile2d.ifo` (`JMXV2DTI1001`, 719 entries) fully decoded: `id → flag(0x00–0x0c) → class → .ddj texture → {x,y} sectors`. Anomalies: `/88/83_13.t` is actually `.m` terrain (`JMXVMAPM1000`, 92,712 B) misnamed `.t`; `Media.pk2 /SV.T` is 1,024 B. | exact grid dimensions/layout (body `140,424 = 2³·3·5851`, prime 5851); per-cell semantics (tile-id vs color vs blend); the `flag` and `{x,y}` meanings in `tile2d.ifo`. |
| `dof` | `JMXVDOF 0101` | 34 / 4.3 MB | `scripts/dof_decoder.py::parse_dof` + `scripts/test_phase21_dof.py` (4 GREEN) | 12-byte magic + 8×u32 section-offset table (`[0]`=116 object-instance start, `[7]`=68 transform start, `[1]`=mesh refs, `[2]`=transforms, `[3]`=region names, `[4]`=secondary names, `[5]`/`[6]`=0); default object name follows the table; body embeds length-prefixed ASCII strings: 11,994 `.bsr` mesh references + 41 `RN_` region names across all 34 files. | per-section record layouts (object instances, transform matrices/quaternions, region-name records) and the semantics of the 24-byte pre-object header (`flags` + default name + `0xFF` sentinels). |
| `bms` | `JMXVBMS 0110` | 22,948 / 603.5 MB | `scripts/bms_decoder.py` + `scripts/test_phase16_bms.py` (16 GREEN) + `scripts/test_phase18_skin.py` (7 GREEN) | full census of 22,684 Data.pk2 files: **44 B standard** (17,247: pos+normal+uv+[weight,bone,flags]) / **52 B lightmap** (5,399: +uv2) / **80 B morph** (6) / 32 unproven. s0 vertices (stride = (s1−s0−4)/vcount), s1 bone table (names), s2 triangles (u32 count + 3×u16), s5 AABB; 44/52 B layouts PROVEN. **Phase 17** converts static meshes to committed MSH1 assets (`scripts/bms_to_asset.py`, 12 GREEN) keeping every vertex (real trees carry flags≠0 canopy geometry). **Phase 18** proves the per-vertex SKIN BLOCK in the bone section (6 B/vertex `[u8 b1][u16 w1][u8 b2][u16 w2]`; 0xFF sentinel ⇒ w2=0; span==6×vcount) and converts skinned meshes to committed MSH v2 assets. | skinned/flags==2 tail semantics: the u32@36 `bone_index` is NOT a local bone index (reaches 151); `skinned_vertex_count` mesh-dependent; weights not pre-normalized to 65535; 80 B morph fields; 7th header offset; trailing bytes. Static (flags==0) path fully decodable; flags≠0 vertices kept and recorded as `non_static`. |
| `nvm` | `JMXVNVM 1000` | 6,041 / 778.6 MB | `scripts/test_phase13_nvm.py` (5 GREEN) + `scripts/jmx_nvm.py` (deterministic locator: magic, grid run, extent floats, trailing fill) | flat 8-byte LE nav-cell records (4×u16); dominant 9,216 = 96×96 grid; post-grid f32 region (~37,814 B); trailing −20.0 fill (commonly 36 words); header carries extent f32 in [0,1920] (nv_198c: 1720/200/1920; nv_1f29: 1920/1920/1920). | header field semantics (variable-length; extent float offset differs per file); nav-cell record semantics (type-marker 279/271, flag, value); f32 vertex/triangle layout. |
| `efp` | `JMXVEFF xxxx` | 3,395 / 95.1 MB | `scripts/test_phase13_efp.py` (11 GREEN) | version tree (0000×7/0010×1/0011×1,820/0012×408/0013×1,158); u32-length-prefixed ASCII command stream. | command-stream semantics / parameters. |
| `ainavdata` (in `.dat`) | `0x01` + `u16 (0x8000|id)` | 26 / 62.7 MB (`Data.pk2 /navmesh/ainavdata_3276{9..87}.dat`) | `scripts/dat_families.py` (`parse_ainavdata`) | 24-byte header: version `0x01`, u32 LE `vertex_section_offset`@1..4 (absolute offset of trailing sub-section), u16 LE `region_id`@5..6 (= `0x8000|id`, PROVEN == filename id for all 26), u8 type@7, u16 BE `count_a`@14..15, u16 BE `count_b`@18..19 (= vertex count). Trailing sub-section at `vertex_section_offset`: repeated region_id+type + u32 BE count + f32 LE vertex triplets (region `type 0x01` → y=0 2D; dungeon `type 0x97` → real height 3D). Server loader in `SR_GameServer.exe` (`AINavData_%d.DAT`, `AINavData Version is not match!!!`, `DATA\navmesh`). | body edge-record layout (u16 BE from 24 to vertex_section_offset), `count_a` semantics, u16@16, byte@20, and the extra edge/link data appended in the 15 complex files. |
| `config` (in `.dat`) | `u32 count` prefix | 7 / ~3.6 KB (client `Setting/*.dat`: `gmwpfort.dat` 1584 B, `SROptionSet.dat`, `wndpos.dat`, `SRExtQSOption.dat` 11 B, `SRExtQSOption2.dat` 6 B, …) | `scripts/dat_families.py` (`parse_config`) | count-prefixed binary config records (u32 record count + fixed/len-prefixed records). | record field layout per-file UNKNOWN (tiny `SRExtQSOption*` blobs have indeterminate layout). |

## 3. TEXT formats (decoded)

| Ext | Magic / structure | Files / Bytes | Notes |
|---|---|---|---|
| `txt` | tabular text | 441 / 116.6 MB | 159 are server textdata in `Media.pk2 /server_dep/silkroad/textdata/` (tab-separated, UTF-16LE BOM 149 / cp949 / UTF-8). See `TEXTDATA_CATALOG.tsv`. |
| `ifo` | polymorphic `JMXV*` (5 magics + 1 text) | 12 / 928 KB | The `.ifo` extension is a container-family shorthand, NOT one format. 12 files carry 5 distinct `JMXV` magics plus one 2-byte ASCII text file: `object.ifo`/`objectstring.ifo`/`objext.ifo` → `JMXVOBJI1000` (object index; Phase 17 proves the `nameI u32` + quoted-path index, nameI 820/574 resolve to real tree `.bsr` paths); `tile2d.ifo` → `JMXV2DTI1001` (719-entry tile index, **decoded** by `parse_tile2d_ifo`: id → flag → class → `.ddj` → `{x,y}` sectors); `config.ifo` → `JMXVCAMR1002`; `environment.ifo` → `JMXVENVI1003`; `layerobjectlist.ifo` → `JMXVOBJL1000`; `tile3d.ifo` → `0\n` plain text. The three new magics (`CAMR`/`ENVI`/`OBJL`) are magic-confirmed but otherwise undecoded (UNKNOWN). |
| `ini` | `[LocalizedFileNames]` | 1 / 396 B | Text ini. |
| `c` | `vs.1.1...` | 40 / 133 KB | DirectX vertex-shader **source text** (`.c` shader files). |
| `vsh` | `vs.1.1...` | 8 / 27.7 KB | DirectX vertex shader source. |
| `psh` | `//c0 - Common Const...` | 14 / 18.4 KB | DirectX pixel shader source. |

## 4. UNKNOWN formats (no honest claim made)

| Ext | Observed head | Files / Bytes | Notes |
|---|---|---|---|
| `db` | `8b 03 00 00 1d 00 00 00 textures…` | 1 / 23.3 MB (`Particles.pk2`) | Appears to be a name/string table referencing `*.ddj` (e.g. `textures\illusion_basic.ddj`). Structure unverified. |
| `scc` | binary `34 12 01 00 c9 31…` | 17 / 15.6 KB | No structure identified. |
| `msf` | binary `01 00 00 00 02 00 00 00 ff…` | 2 / 350 B | Contains string `ambient`. No structure identified. |

## 5. Encrypted client files

| Ext / name | Status |
|---|---|
| `skilldata_*enc.txt` (7 files, 3.4–4.4 MB each) | Client-encrypted skill tables. Bytes preserve newline structure (records ≈ line count) but the field content does not decode to valid UTF-16LE/UTF-8/cp949. Marked `ENCRYPTED` in `TEXTDATA_CATALOG.tsv`. **No key. Do not guess.** |
| `skilldataenc.txt` | Plain-text index of the `*ENC.txt` file names (decodable, cataloged). |

## 6. Coverage rollup (all 120,840 indexed files across 5 archives + containers)

| Status | Files | Formats |
|---|---:|---|
| PROVEN | 83,216 | ddj (47,495), m (4,491), o (4,491), o2 (4,348), ban (4,796), bsk (1,036), bsr (7,549), bmt (4,269), cpd (124), wav (2,885), ogg (50), tga (15), tmp (1), `.dat` bmp/jmxvimg/palette/hex-token/plugin (55), `.ifo` `JMXVOBJI1000` (6) + `JMXV2DTI1001` (1) + `JMXVOBJL1000` (1), `.rd` bmp (103), pe-executable `.dll`/`.exe` (54), `.pk2` (1), extension-less ddj icon (1) |
| PARTIAL | 37,583 | bms (22,948), nvm (6,041), efp (3,394), t (4,989), dof (34), `.dat` ainavdata/config (33), `.2dt` cnif (51), `.ifo` `CAMR`/`ENVI` (2), `.mfo` (2), `.msf` (2), `.bak` mtf (4), `.crb` (18) |
| UNKNOWN | 2 | cs3 (2) |
| TEXT | 1 | `.ifo` `tile3d.ifo` (`0\n`) |
| STUB | 17 | `.txt` (12), `.bsk` (4), `.efp` (1) |
| DEAD | 21 | `.scc` vssver.scc (15) + vssver2.scc (2), `.tmp` (1), `.ini` (1), `.sfk` (1), `.db` (1) |
| MISSING | 1 | 1 known-missing file |

The `.scc` extension totals 17 files, all DEAD source-control metadata: 15 are
`vssver.scc` and 2 are `vssver2.scc` (VSS version-file magic `34 12 01 00` +
`$/project` path strings). The two `.cs3` files (`Map1.CS3`, `Map2.CS3`) are
encrypted/compressed server maps (byte entropy 5.77, all 256 byte values
present) with no provable structure; the two are identical except for 2 bytes at
offset 12,604 (map index).

Exact per-file classification is machine-readable in
`COMPLETE_SOURCE_INVENTORY.json` (`extensions` table maps every extension to
count, bytes, and status; every file record references its extension).
