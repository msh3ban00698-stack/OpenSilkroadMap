# FORMAT_RESEARCH — Phase 12 binary format analysis (evidence-first)

Phase 12 Part C. Goal: establish real structure for `.ban`, `.nvm`, `.bms`, and
`.efp` from the ORIGINAL VSRO-R 1.193 archives before writing any decoder. No
field meaning is asserted unless it is proven from real bytes. Everything that is
not proven is marked **UNKNOWN**.

Directive note: the phase brief references ".bns geometry/static mesh". No `.bns`
file exists in the archive census (`COMPLETE_SOURCE_INVENTORY.json`, 119,631
files); the static-mesh format in the real corpus is **`.bms`** (`JMXVBMS 0110`,
22,948 files). All `.bns` references in this phase map to `.bms`.

Evidence samples (real files, read-only, extracted from the unencrypted data area
of the archives — never modified, never committed as raw binaries):

| Sample | Archive | Path | Size |
|---|---|---|---|
| BAN small | Data.pk2 | `/prim/ani/bldg/china/cj_ferry/cj_ferry_boat_old.ban` | 171 B |
| BAN medium | Data.pk2 | `/prim/ani/mob/qinshi/royalsoldier/royalsoldier_die.ban` | 29,686 B |
| BAN large | Data.pk2 | `/prim/ani/mob/arabia/venefica/venefica_stand01.BAN` | 926,897 B |
| NVM small | Data.pk2 | `/navmesh/nv_1f29.nvm` | 74,643 B |
| NVM mid | Data.pk2 | `/navmesh/nv_74bf.nvm` | 121,810 B |
| NVM large | Data.pk2 | `/navmesh/nv_198c.nvm` | 232,418 B |
| BMS small | Data.pk2 | `/prim/mesh/bldg/arabia/Bagh_Petra/Bagh_Petra_Core01.BMS` | 19,866 B |
| BMS large | Data.pk2 | `/prim/mesh/dun/Demon/Fire/Demon_tower_Fire/demon_tower_mbrazier_fire.BMS` | 45,251 B |
| EFP small | Particles.pk2 | `/skill/china/lightning_bobeop_a.efp` | 1,149 B |
| EFP large | Particles.pk2 | `/monster/arabia/skill_ar_khulood_attack02.efp` | 527,410 B |

---

## 1. `.ban` — animation (`JMXVBAN 0102`) — **PARTIAL (decoder committed)**

### Proven structure

```
offset  size  field                          evidence
------  ----  -----                          --------
0x00    8     magic b"JMXVBAN "               all 3 samples
0x08    4     version b"0102"                all 3 samples
0x0C    8     zero bytes                     all 3 samples: 00 00 00 00 00 00 00 00
0x14    4     u32 LE name length             ferry=17, royalsoldier=16, venefica=16
0x18    N     animation name (NUL at 0x18+N) "cj_ferry_boat_old", "royalsoldier_die",
                                            "venefica_stand01" (exact strings read)
...     --    body (see below)
```

**Keyframe record — 28 bytes, stride proven.** The body contains consecutive
28-byte records where bytes 0..15 are four `f32 LE` values summing to 1.0
(a normalized rotation quaternion, `x,y,z,w`) and bytes 16..27 are three `f32 LE`
position values. Verification:

- Record candidates are exactly `28` bytes apart (no gaps, no overlaps).
- Quaternion unit-norm holds for every record in every run (tolerance 0.05).
- Contiguous runs measured on real files: ferry_boat = **3** records,
  royalsoldier_die = **27** records per run (39 runs = 39 bone channels),
  venefica_stand01 = **181** records per run (182 runs). The identical per-run
  count strongly suggests each run is one bone channel with one keyframe per
  animation frame (3 / 27 / 181 frames).
- Probability of 181 consecutive random 4-float groups being unit-norm by chance
  is negligible; the stride + normalization constitute positive structural proof.

Decoded fixture (first keyframe of each real sample):

| Sample | first quaternion | first position |
|---|---|---|
| ferry_boat | 0.214, -0.374, -0.082, 0.899 | 12.82, 5.64, 6.25 |
| royalsoldier | -0.0, 0.778, -0.0, 0.628 | 0.61, 26.63, -0.24 |
| venefica_stand01 | 0, 0, 0, 1 (identity) | 0, 0, 0 |

### Remaining UNKNOWN (documented, not guessed)

- Semantics of every `u32 LE` field after the name (e.g. ferry_boat: 8000, 30, 1,
  3, 0, 4000, 8000, 1, 6 — plausibly durations/frame counts/bone index but NOT
  proven). **UNKNOWN.**
- Association of a keyframe run to a specific bone name (bone-name strings such
  as `Bone04` are present in the body but the linkage is **UNKNOWN**).
- Time/frame-index encoding, interpolation type, event/trigger records.
- Whether the record is world-space or bone-local (no parent chain decoded).

### Deliverables

- Decoder: `scripts/ban_decoder.py` (header + name + verified keyframe runs).
- Tests: `scripts/test_phase12_formats.py` — 10 tests, static + live-archive
  check (`SRO_PK2_DIR`). **All pass** including live re-extraction.

---

## 2. `.nvm` — navmesh (`JMXVNVM 1000`) — **UNKNOWN (full layout)**

Magic/version proven (`JMXVNVM 1000`). Head bytes (after the 12-byte magic):

| Sample | bytes 12..63 | observations |
|---|---|---|
| nv_1f29 | `00 00 01 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00` then float `f0 44 00 00` = **1920.0** twice, `01 00 00 00` | LE float 1920.0 (region extents) present; small/unknown count fields |
| nv_74bf | `02 00 28 08 00 00` then `f32 (1752.06, 623.83, -141.96)` | a 3D coordinate (min corner?) right after a short prefix; u16 `28 08` = 2088 |
| nv_198c | `00 00 09 07 00 00 8b 03 00 00` then `f32 (1620.0, 820.0)`, more floats 1920.0, 1080.0, 460.0, 1660.0… | counts `09 07` (u16=1801), `8b 03` (u32=907); a run of extent floats |

Known: header carries 32-bit LE floats in the range 128–1920 (map extents /
min-max corners, consistent with the SRO 1920-unit region scale) and small
integer fields (possibly counts). **NOT proven**: which integer is the vertex
count, which is the triangle count, the record stride of the vertex/triangle
lists, and the cell/triangle grouping. `907 * 256 ≈ 232,192` vs file 232,418 is
suggestive but not conclusive — **no count field is asserted**. Decoder: **none**.
Stop condition per rules: layout not established -> documented as UNKNOWN.

---

## 3. `.bms` — static mesh (`JMXVBMS 0110`) — **UNKNOWN (full layout)**

Magic/version proven. Head bytes (after the 12-byte magic):

| Sample | bytes 12..44 (LE u32) | file size |
|---|---|---|
| Bagh_Petra_Core01 | `118, 15346, 17446, 19826, 19830, 19834, 19858, 0, 0` | 19,866 |
| demon_tower_mbrazier_fire | `133, 41099, 41103, 45211, 45215, 45219, 45243, 0, 0` | 45,251 |

Known: a table of ascending `u32 LE` offsets that are all `< file size` and end
just below EOF (e.g. 19858 + small tail = 19866; 45243 + tail = 45251). The
4-byte increments (19826→19830→19834; 45211→45215→45219) indicate small adjacent
sections (e.g. consecutive vertex/index sub-buffers). The first value (118 / 133)
is the header size. **NOT proven**: which offsets bound the vertex buffer vs
index buffer, vertex/index element strides, and the count encoding. Decoder:
**none**.

---

## 4. `.efp` — particle effect (`JMXVEFF xxxx`) — **UNKNOWN (full layout)**

Magic proven; **version is NOT constant**. Real version-byte distribution across
Particles.pk2 (all 3,395 files read):

| version | count |
|---|---|
| `0011` | 1,821 |
| `0013` | 1,158 |
| `0012` | 408 |
| `0000` | 7 |
| `0010` | 1 |

Sample heads (after the 8-byte magic `JMXVEFF `):

- `lightning_bobeop_a.efp` (`0011`): `67 00 00 00` (=103) `0f 00 00 00` (=15)
  then string `csk_s_light_jil` (`...` = 14 chars, likely an emitter/texture
  name), then `03 00 00 00` (=3) `0e 00 00 00` (=14) then `Norma`…
- `skill_ar_khulood_attack02.efp` (`0013`): `00 00 00 3f` (= LE float **0.5**)
  `00 00 00 00` (=0.0) `00 0a 01 00` … then `0f 00 00 00` (=15) then string
  `skill_ranges`.

Known: header embeds short ASCII strings (emitter names, `Norma…` =
"Normal…", `skill_ranges`) and small u32/u16 count fields; `0013` starts with
LE floats. **NOT proven**: particle/emitter counts, record layout, string table
structure, or how the 5 version variants differ. Decoder: **none**.

---

## 5. Cross-cutting findings

- All four formats are little-endian (LE) and share the `JMXV` magic family.
- `.ban`/`.bms`/`.nvm`/`.efp` bodies all embed short ASCII strings (animation
  names, `BoneNN` bone names, emitter names) that can aid future field
  identification.
- Real derived fixtures (structure only, no raw binaries) are committed under
  `scripts/testdata/formats/` for the `.ban` decoder tests; each fixture records
  its source archive path, size, and a `sha256` of the first 1 MiB.
