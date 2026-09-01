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

## 1. `.ban` — animation (`JMXVBAN 0102`) — **FULL LAYOUT PROVEN (Phase 13 Part D)**

### Complete proven structure

Phase 13 Part D proved the FULL layout by parsing three real files to the exact
last byte (171 / 29,686 / 926,897 — all `parse_exact`):

```
offset    size      field                          evidence
------    ----      -----                          --------
0x00      8         magic b"JMXVBAN "               all 3 samples
0x08      4         version b"0102"                all 3 samples
0x0C      8         reserved zeros                 all 3 samples (UNKNOWN semantics)
0x14      4         u32 LE name length             ferry=17, royalsoldier=16, venefica=16
0x18      N         animation name (NO NUL)        "cj_ferry_boat_old" etc.
--- body at name_end (byte at name_end is 0x40/0x96/0x70 -- never 0x00) ---
body+0    4         u32 duration_ms                8000 / 2966 / 6000
body+4    4         u32 frame_rate                 = 30 in all 3
body+8    4         u32 UNKNOWN                    1 / 0 / 1
body+12   4         u32 keyframes_per_bone (kpb)   3 / 27 / 181
body+16   kpb*4     u32 timestamp_ms each          ascending, first=0, last=duration
then+4   4         u32 bone_count                  1 / 38 / 182
then      N         bone_count x [ u32 name_len, name (no NUL),
                  u32 per-bone keyframe count (= kpb), kpb x 28 B keyframes ]
```

**Keyframe record — 28 bytes:** bytes 0..15 = 4 x `f32 LE` normalized rotation
quaternion (`x,y,z,w`); bytes 16..27 = 3 x `f32 LE` position.

**Bone names proven by exact parse** (royalsoldier = full Bip01 human skeleton
plus 4 attachment bones; venefica = Bip02 skeleton plus 144 attachment bones
feathers/skirt/chair/effect chains, 182 total):

| Sample | bones | kpb | duration | parse end == size |
|---|---|---|---|---|
| ferry_boat | 1 (`Bone04`) | 3 | 8000 | 171 == 171 |
| royalsoldier_die | 38 (Bip01 + Bone01..04) | 27 | 2966 | 29,686 == 29,686 |
| venefica_stand01 | 182 ([root], Bip02, attachments) | 181 | 6000 | 926,897 == 926,897 |

### Remaining UNKNOWN (documented, not guessed)

- The u32 at body+8 (`1 / 0 / 1`) — possibly a loop/override flag. **UNKNOWN.**
  (Note: looping itself is now PROVEN from the keyframe data — first keyframe ==
  last for every channel — independent of this flag.)
- The reserved 8 bytes at 0x0C. **UNKNOWN.**
- Interpolation type / event records / world-vs-bone-local reference frame.

### Phase 19 — full keyframes, looping, and anomalies

- **Full keyframe export** (`scripts/animation_pose.py::load_keyframes`): every
  keyframe is committed (bandit_stand01 34 ch × 5 kf @ 2000 ms; bandit_walk 34 ch
  × 15 kf @ 1333 ms). Timestamps are non-uniform (`[0,33,133,266,333,400,533,566,
  666,800,933,1000,1066,1200,1333]`), proving NO fixed FPS assumption.
- **Looping PROVEN** (walk + stand01): first keyframe == last keyframe for every
  channel (tolerance `2e-3` for float32 keyframe rounding); the Bip01 root
  translation drift is loop-contained (no accumulated offset).
- **Channel space PROVEN**: BAN channel (q,pos) are ABSOLUTE parent-relative
  transforms that REPLACE the bind `rot_parent`/`tr_parent` (chaining proof:
  stand01 t=0 toes on ground; walk t=0 L Toe planted / R Toe lifted +1.25).
- **Format anomalies**: 4,793/4,795 `.ban` parse byte-exact as `JMXVBAN 0102`;
  2 files use `JMXVBAN 0101` (`spidey_attack01.ban`, `chakji_stand02.ban`) with an
  unproven layout — documented UNKNOWN, not guessed.

### Deliverables

- Decoder: `scripts/ban_decoder.py` — `parse_ban()` full proven parse (raises if a
  file does not land exactly on EOF), `parse_ban_header()`, `find_keyframe_runs()`.
  The Phase 12 `body_start = name_end + 1` NUL assumption was corrected to
  `name_end` (proven: the byte at name_end is never 0x00).
- Tests: `scripts/test_phase13_ban.py` (8 tests) + `scripts/test_phase12_formats.py`
  (11 tests) — all pass static + live-archive (`SRO_PK2_DIR`).


---

## 2. `.nvm` — navmesh (`JMXVNVM 1000`) — **PARTIAL (structure proven, semantics UNKNOWN)**

Magic/version proven (`JMXVNVM 1000`). Head bytes (after the 12-byte magic):

| Sample | bytes 12..63 | observations |
|---|---|---|
| nv_1f29 | `00 00 01 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00` then float `f0 44 00 00` = **1920.0** twice, `01 00 00 00` | LE float 1920.0 (region extents) present; small/unknown count fields |
| nv_74bf | `02 00 28 08 00 00` then `f32 (1752.06, 623.83, -141.96)` | a 3D coordinate (min corner?) right after a short prefix; u16 `28 08` = 2088 |
| nv_198c | `00 00 09 07 00 00 8b 03 00 00` then `f32 (1620.0, 820.0)`, more floats 1920.0, 1080.0, 460.0, 1660.0… | counts `09 07` (u16=1801), `8b 03` (u32=907); a run of extent floats |

### Phase 13 Part E findings (proven from real bytes, 17 samples)

Header carries 32-bit LE floats in the range 128–1920 (map extents / min-max
corners, consistent with the SRO 1920-unit region scale) and small integer
fields (possibly counts) — meanings **UNKNOWN**, not asserted.

**Proven structure: a flat nav-cell grid array.** After the header/obstacle
region each sample contains a flat array of **8-byte LE records (4 × u16)**. The
dominant record count is **9,216 (= 96×96)**; measured across a random sample of
17 real files:

| Sample | size | grid start | grid records | post-grid f32 bytes | trailing -20.0 words |
|---|---|---|---|---|---|
| nv_5ba3 | 152,578 | 41,036 | 9,216 | 37,814 | 36 |
| nv_6e50 | 124,026 | 12,484 | 9,216 | 37,814 | 36 |
| nv_1614 | 122,274 | 10,732 | 9,216 | 37,814 | 0 |
| nv_64aa | 132,698 | 21,156 | 9,216 | 37,814 | 1 |
| nv_6876 | 113,520 | 1,980 | 9,236 | 37,652 | 36 |
| nv_154e | 111,942 | 404 | 9,216 | 37,810 | 36 |
| nv_1f29 | 74,643 | 148 | 9,311 | 7 | 0 |
| nv_74bf | 121,810 | 10,268 | 9,216 | 37,814 | 0 |
| nv_198c | 232,418 | 120,876 | 9,216 | 37,814 | 36 |

Record shape (nv_198c, first 32 records): `(0, flag∈{0,1}, 0x0117=279, value)`.
nv_198c records carry a repeating type-marker (u16 `0x0117`=279, minority
`0x010F`=271); nv_1f29 records are `(0, {0|255}, 0, 0)`. The `0000 0100` words
that dominate some bands are simply the tails of flag=1 records.

Other proven facts: a consistent **~37,814-byte f32 region** immediately follows
the grid in 6 of 8 grid files (nv_6876=37,652, nv_154e=37,810); trailing
**-20.0 f32 fill** words (commonly exactly 36 = 144 bytes) mark empty/unused nav
cells (nv_198c, nv_5ba3, nv_6e50, nv_1614→0, nv_64aa→1, etc.). The ~37.8 KB f32
region does not divide into a clean vec2/vec3 stride at the measured boundaries,
so the vertex/triangle layout is **UNKNOWN**.

**NOT proven** (explicitly UNKNOWN): which header integer is the vertex count,
which is the triangle count, the record semantics (type-marker/flag meaning), the
f32 vertex/triangle layout, and the header field meanings. `907 * 256 ≈ 232,192`
vs 232,418 is NOT the file structure (the grid is 9,216×8 = 73,728 B at
120,876–194,604; `907`/`1801` do not divide the body). Structural parser:
`scripts/jmx_nvm.py` (deterministic: verifies magic, locates the largest const-u0
8-byte-record grid run, parses sample records, counts trailing −20.0 fill words,
and reports header extent f32 in [0,1920]); tests `scripts/test_jmx_parsers.py`.
Evidence fixture: `scripts/testdata/formats/nvm_grid.json`; tests:
`scripts/test_phase13_nvm.py`.

### Phase 29 refinement (25-sample survey, this batch)

A 25-file size-stratified survey (`/tmp/opencode/nvm_samples/s00..s24`,
read from `Data.pk2 /navmesh/`) disproves the assumption that every `.nvm`
grid is `96×96` = 9,216 records. The `find_largest_const_u0_run` heuristic in
`jmx_nvm.py` therefore returns **false positives** on a large fraction of
files: on 25 samples the "grid" it reports ranges from 5 to 9,311 records and,
for roughly half the files, lands at a small trailing run rather than the real
cell array. Two distinct header layouts are visible in the first bytes after
the magic:

- **Simple layout** (`nv_1f29`, `nv_198c`, `nv_2527`, `nv_5240`, `nv_18be`,
  `nv_6367`, `nv_74ea`): `u16 0, u16 N, u16 0, u16 M` then extent floats
  (`1920.0` etc.). `N`/`M` are small counts (e.g. `nv_198c` 1801/907;
  `nv_5240` 150/80).
- **Complex layout** (`nv_6df6`, `nv_664a`, `nv_1bc1`, `nv_6a64`, `nv_179d`,
  …): the header bytes 12+ immediately decode as f32 3D coordinates
  (e.g. `nv_1bc1` `1794.08, -2.67, -3.45, -40.07`), consistent with a
  vertex/triangle block rather than a simple count header.

The cell record shape also differs: simple files carry `(0, flag∈{0,1},
0x0117=279|0x010F=271, value)`, while complex files carry `(0|4, 0, 0, value)`
with small value integers. The grid dimensions/offset are NOT proven to be
recoverable from a single header field, so `.nvm` stays PARTIAL and the
locator heuristic is documented as unreliable (it identifies a candidate
const-zero run, not a proven grid). No semantics are asserted.

### `.ddj` header — **PROVEN 20-byte wrapper + embedded DDS**

`scripts/jmx_ddj.py` proves the exact `.ddj` container header (verified against
samples 2 KB – 2.9 MB and a 23-file sample):

| offset | size | field | evidence |
|---|---|---|---|
| 0 | 12 | `JMXVDDJ 1000` | magic + version, all files |
| 12 | 4 | u32 `data_size` | == `file_size − 12` across every sample |
| 16 | 4 | u32 `level` | constant `3`; semantics UNKNOWN |
| 20 | .. | embedded DDS | `DDS ` magic + 124-byte header + data |

The embedded DDS pixel format is either uncompressed RGB (16/24/32 bpp, no
fourcc) or `DXT3` fourcc. No DXT1/DXT5 observed in the sampled set. Tests:
`scripts/test_jmx_parsers.py`.

---

## 3. `.bms` — static mesh (`JMXVBMS 0110`) — **STRUCTURE PROVEN; VERTEX LAYOUT PROVEN (44/52 B); SKINNING TAIL UNKNOWN**

Phase 16 decodes the vertex layout that Phase 13 could not (the earlier
"52.11 B" stride was an ERROR — the vertex section ends at `s1 = offset@0x10`,
not `s2 = offset@0x14`). Full census of all 22,684 `Data.pk2` BMS files:

| class | count | vertex_size | description |
|---|---|---|---|
| standard | 17,247 | 44 B | pos+normal+uv + 12 B tail |
| lightmap | 5,399 | 52 B | pos+normal+uv+uv2 + 12 B tail |
| morph80 | 5 | 80 B | 4 weight streams (morph/skin) |
| morph_trailing | 1 | 80 B + trailing | 80 B + trailing bytes |
| unproven | 32 | — | triangle section unparseable |

### Proven layout (all 22,684 files, `scripts/bms_decoder.py`, tests `scripts/test_phase16_bms.py`, fixtures `scripts/testdata/formats/bms_phase16.json` + `scripts/testdata/formats/bms_samples/`)

```
0x00  char[12]  magic = "JMXVBMS 0110"
0x0C  u32       header_size (== s0 = offset of vertex section)
0x10  u32 x6    section offsets s1..s6 (ascending, all < file size)
0x28  u32 x2    zero padding
0x30  u32       end_offset (== file size - 4)
0x34  u32 x3    zero / 1, 0, 0
0x40  u32       name1_len, char[] name1; name2_len, char[] name2
      u32       skinned_vertex_count  (= u32@0x80-4 in all 11 samples; == vertex_count for skinned meshes)
────────────────────────────────────────────────────────────
s0  vertex data: u32 vertex_count, then vertex records (stride = (s1-s0-4)/vertex_count)
s1  bone table : u32 bone_count, then per-bone [u32 name_len + name] + transform data
s2  triangle list: u32 tri_count, then tri_count x 3 x u16 LE indices (stride 6)
s3  4 B  (0)
s4  4 B  (0)
s5  AABB: 6 x f32 LE (minx,miny,minz,maxx,maxy,maxz) — 24 B
s6  4 B  (0)
    then end_offset..EOF = 4 B (0)
```

### Vertex record layouts (PROVEN)

```
44 B "standard"  (17,247 files — items, nature, mob, npc, bldg, dun, artifact)
   0  3x f32  position
  12  3x f32  normal        (unit-length verified across all 44/44.5/45/50 samples)
  24  2x f32  uv
  32  f32     blend_weight  (0.0 = unskinned)
  36  u32     bone_index    (0xFFFFFFFF = none; 0..N for skinned vertices)
  40  u32     flags         (0 = unskinned, 2 = skinned/flagged)
    tail @32 == [0, 0xFFFFFFFF, 0] for unflagged vertices in static meshes

52 B "lightmap"  (5,399 files — bldg/dungeon with lightmap UV)
   0  3x f32  position
  12  3x f32  normal        (unit-length verified)
  24  2x f32  uv
  32  2x f32  uv2           (lightmap UV; range 0.02..1e9 across v52_bldg sample)
  40  f32     0.0
  44  u32     0xFFFFFFFF
  48  u32     0
```

### UNKNOWN / PARTIAL

- **Skinned tail semantics (flags==2 vertices)**: blend_weight is 0.0/1.0; the
  u32@36 reaches values far above local `bone_count` (npc_chicken: 14 bones,
  indices 3..96) and `nature_tree` (0 bones) marks 19/36 vertices with flags=2
  and u32@36 ∈ 8..34 **with duplicates** — therefore u32@36 is **NOT a local
  bone index** (likely an external skeleton/palette reference, or a non-skinning
  payload for leaf/billboard vertices). Not decodable without original code.
  Static rendering (Phase 17 MSH1) keeps **every** vertex because real trees
  legitimately carry flags≠0 (tre_tree03_02: 49/154 flags==2 canopy vertices);
  `non_static_vertices` is recorded, nothing is dropped.
- **Phase 18 proves the per-vertex SKIN BLOCK** (inside the bone section,
  between the bone-name table end and `offsets[1]`): 6 B/vertex
  `[u8 bone1][u16 weight1][u8 bone2][u16 weight2]`; `0xFF` bone sentinel
  (⇒ `weight2=0`), single-influence vertices carry `weight2=0`; span ==
  6 × vertex_count byte-exhausts on every skinned sample. Weights are NOT
  normalized to 65535 (two-influence sums are mesh-dependent: bandit_part1 min
  sum 49,146; bandit_sword has zero two-influence vertices). `skinned_vertex_count`
  (u32@0x80−4) is mesh-dependent UNKNOWN. The u32@36 tail `bone_index` is still
  NOT a local skin index (values reach 151 beyond any local table) — the skin
  block's `bone1/bone2` ARE local bone-table indices (b1,b2 < bone_count proven).
- `morph80` (5 files) and `morph_trailing` (1): 80 B/vertex with 4 f32 weight
  streams; field-by-field layout UNKNOWN. Classified, not decoded.
- The 7th optional header offset u32@0x28 (`off7`, e.g. nature_tree=2086) and
  the trailing bytes after vertices in some lightmap files (~87–90 B).
- `.bsk`/`.bsr`/`.ban` are decoded separately (see sections below / Phase 13);
  the `.bsk`-side bone table record beyond names remains PARTIAL.
- The `demon` 52.11-B "anomaly" from Phase 13 is resolved: demon is a **52 B
  lightmap** mesh (786 vertices × 52 = 40,872 B, lightmap ddj path embedded)
  with **90 B of trailing bytes** after the vertex array — the old non-integral
  stride came from counting those trailing bytes as part of the vertex stride.

---

## 4. `.efp` — particle effect (`JMXVEFF xxxx`) — **VERSION TREE PROVEN; BODY UNKNOWN**

### Version tree (all 3,395 Particles.pk2 files read; 1 is a 0-byte placeholder)

Magic is 8 bytes `JMXVEFF ` followed by **4 ASCII version bytes**.

| version | count | size (min/med/max) | vocab size | u32-prefixed runs / total | header field @12 |
|---|---|---|---|---|---|
| `0000` | 7 | 2,275 / 75,328 / 140,990 | 43 | 161/434 | path-offset-ish u32 |
| `0010` | 1 | 10,998 | 35 | 180/192 | 230 (u32) |
| `0011` | 1,820 | 1,149 / 11,269 / 193,327 | 1,878 | 448,245/533,049 | small u32 (91–100) |
| `0012` | 408 | 1,429 / 19,089 / 219,427 | 803 | 199,248/234,220 | float-like (1.0/0.5/2.0…) |
| `0013` | 1,158 | 1,944 / 27,394 / 527,410 | 1,459 | 868,149/1,037,536 | float-like (1.0/2.0/0.5…) |

(0-byte placeholder: `/dun/petra_flame_yellow_glow.efp` — no magic, excluded
from all counts.)

### Proven body property: u32-length-prefixed command stream

For versions `0010`–`0013`, the **large majority** of embedded ASCII runs (≥4
chars) are `u32 LE` length-prefixed command tokens — ratios 0.70–0.94. The
shared command vocabulary (corpus union) includes:

```
StaticEmit  Program  ProgramUpdate  LinkMode  NormalTimeLife
NormalTimeExtinct  SetGraphScale  SetGraphDiffuse  BlendScaleGraph
BlendDiffuseGraph  DiffuseGraph  ScaleGraph  SetPosition  SetRotation
SetShapeRotVel  SetConeVel  SetSpherePos  ViewNone  ViewBillboard
ViewMode  RenderMesh  RenderPlate  RenderNone  Shape  meshes  textures
```

These read like a particle-emitter scripting language (`SetGraphDiffuse`,
`SetConeVel`, `RenderPlate`, `ViewBillboard`, …). Version `0000` instead embeds
**file paths** (`textures\plazma3.ddj`, `meshes\cho-won-004.bms`, `NONAME`) —
an older, file-referencing variant.

### UNKNOWN

- The command parameter layout (each token is followed by typed params — floats,
  sub-strings, sub-programs — but the per-command schema is **not** decoded).
- Header field @12 semantics (count in 0010/0011; float in 0012/0013; the
  `0013` head shows `0.5, 0.0` floats then a u16).
- How `0000` (paths) maps onto the command stream model. Decoder: **none**.

---

## 5. `.bsk` / `.bsr` — skeleton animation / mesh resource — **FULLY PROVEN (Phase 18)**

Phase 18 replaces the Phase 13 sampling with byte-exact decoders
(`scripts/bsk_decoder.py`, `scripts/bsr_decoder.py`; fixtures
`scripts/testdata/formats/bsk_phase18.json`, `bsr_phase18.json`).

### `.bsk` (`JMXVBSK 0101`) — **DONE (1034/1035 byte-exact)**

```
0x00  char[12]  magic "JMXVBSK 0101"
0x0C  u32       bone_count            (bandit 35, blackrobber 35, chinaman_skel 38,
                                       horse1 31, islamman 43)
per bone:
     u8         bone_type             (opaque; semantics UNKNOWN)
     str        name                  (u32 len + ascii, no NUL)
     str        parent                ("" for the root)
     21 x f32   rot_parent4 tr_parent3 rot_origin4 tr_origin3 rot_local4 tr_local3
     u32        child_count + child_count x (u32 len + ascii name)
trailer:        8 zero bytes
```

Census: **1,034 / 1,035** nonzero `Data.pk2` `.bsk` byte-exhaust (4 zero-byte
files); single outlier `/prim/skel/item/common/mob_select.bsk` structure
**UNKNOWN** (skipped, not guessed). Only `rot_parent`/`tr_parent` feed the proven
bind pose.

### Phase 19 — transform-field semantics (PROVEN) and `bone_type` census (UNKNOWN)

`scripts/build_bsk_census_fixture.py` + `scripts/test_phase19_bsk_semantics.py`
prove the three transform triples' meaning for the bandit `.bsk`:

- **`rot_origin`/`tr_origin` == the bone WORLD (bind/model-space) transform**
  (PROVEN byte-exact against `skeleton.json` `bind_world`): Pelvis `tr_origin
  [0,6.9362,2.7382]` == `[0,6.936188,2.738231]`; Head `[0,12.379,-0.8446]` ==
  `[5e-06,12.378977,-0.844599]`; root `Bip01` origin == parent (no parent).
- **`rot_parent`/`tr_parent` == parent-relative local transform** (Phase 18, re-proven).
- **`rot_local`/`tr_local` == inverse-bind (world -> bone-local)** — PROVEN on the
  ROOT by the conjugate pattern (`rot_local == conj(rot_origin)`, `tr_local ==
  R^-1·(-t)`); child-bone inverse is **PARTIAL** (the local vector-part sign
  differs from the plain conjugate — requires a full inverse recompute, kept
  UNKNOWN where not proven).
- **`bone_type` u8 census** (`build_bsk_census_fixture.py`): across 1,035 nonzero
  `.bsk` (29,957 bones) the histogram is `{0: 29957}` — a constant zero. Meaning
  remains **UNKNOWN** (raw census only, no semantics asserted).

### `.bsk` quaternion convention — **PROVEN `[x,y,z,w]` (Phase 18)**

Bind pose chaining with quaternions read as `[x,y,z,w]` aligns the bandit
skeleton to its REAL mesh bounds (L Toe0 world y ≈ 0.02 vs mesh ground 0.03;
pelvis 6.94; head 12.38; hands ±8.2 at shoulder height). The `wxyz` reading was
discarded (planted toes at y ≈ 2.5 vs real feet 4.8–6.8). See
`scripts/skeleton.py` + `scripts/test_phase18_skeleton.py` (9 tests).

### `.bsr` (`JMXVRES 0109/0108/0107`) — **DONE (path groups + classification)**

```
0x00  char[12]  magic "JMXVRES 0109"  (0108 x3, 0107 x1)
0x0C  8 x u32   table                 (non-monotonic values; semantics UNKNOWN)
0x2C  16 bytes  zeros
0x3C  body      [u32 len][ascii token] runs
```

- Tokens classified by extension: `.bmt` (materials), `.bms` (mesh parts),
  `.ban` (animations), `.bsk` (skeleton), `.efp` (effects), `.wav` (sounds).
- `is_character` = file references a `.bsk`; for characters the group order
  `bmt → bms → ban → bsk → efp → wav` is ASSERTED (static-object bsrs like
  tre_tree03 interleave and are deliberately not asserted).
- bandit: 3 bmt + 3 bms + **16 ban** + 1 bsk + 7 efp + 16 wav; chinaquest_priest
  1+3+2+1; movoi 15 ban.

### BAN pose evaluation — **DONE (Phase 18), full keyframes + playback (Phase 19)**

`scripts/animation_pose.py` aligns per-bone channels to GLOBAL timestamps and
interpolates between adjacent PROVEN keyframes (slerp for rotation, lerp for
position); unanimated bones fall back to bind `rot_parent`/`tr_parent`.
bandit_stand01: 2000 ms / 5 kf / 34 channels; bandit_walk: 1333 ms / 15 kf /
34 channels (irregular 33/133/266 ms timestamps justify adjacent-key
interpolation). Fixtures `ban_phase18_samples/` + `ban_phase18.json`; tests
`scripts/test_phase18_animation.py` (10).

Phase 19 exports ALL keyframes (not just the first) and proves, by pose chaining,
that the bandit walk/stand01 poses genuinely move the real skeleton
(`scripts/test_phase19_pose.py`, `scripts/test_phase19_animation.py`,
`scripts/test_phase19_real_animation.py`, `scripts/render_npc_animation.py`).
Runtime playback on device remains NOT EXECUTED; the committed Java renderer is
compile-only with a bind-pose fallback.

---

## 6. Cross-cutting findings

### The `JMXV` shared-container convention (PROVEN)

Every Joymax binary asset in the corpus begins with the 4-byte signature
`JMXV` (hex `4A 4D 58 56`), followed by an 8-byte format identifier that
disambiguates the container. The 8-byte identifier is a 3–4 character ASCII
tag plus a version string, and it is unique per format. 21 distinct 12-byte
magics are observed on real archive samples (all little-endian):

| 12-byte magic | extension | format | decode status |
|---|---|---|---|
| `JMXVBAN 0102` | `.ban` | animation | PROVEN (full layout; 2 `0101` anomalies) |
| `JMXVBMS 0110` | `.bms` | static mesh | PARTIAL (skinning tail UNKNOWN) |
| `JMXVBMT 0102` | `.bmt` | material | PROVEN (full layout, Phase 18) |
| `JMXVBSK 0101` | `.bsk` | skeleton | PROVEN (full layout) |
| `JMXVCPD 0101` | `.cpd` | compound manifest | PROVEN (full layout, Phase 21) |
| `JMXVDDJ 1000` | `.ddj` | texture (DDS) | PROVEN (20-byte wrapper) |
| `JMXVDOF 0101` | `.dof` | dungeon object | PARTIAL (8-u32 section table + .bsr/RN_ strings; per-section records UNKNOWN) |
| `JMXVEFF xxxx` | `.efp` | particle effect | PARTIAL (version tree only) |
| `JMXVIMG11000` | `.dat` (fonts) | font glyph image | PARTIAL (magic + u16 fields) |
| `JMXVMAPM1000` | `.m` | terrain height grid | PROVEN (97×97 grid) |
| `JMXVMAPO1000` | `.o` (empty) | empty object overlay | PROVEN (zero payload, 7 files) |
| `JMXVMAPO1001` | `.o`, `.o2` | object overlay | PROVEN (28/30-byte records) |
| `JMXVMAPT1001` | `.t` | map tile | PARTIAL (header/size/tile2d refs; grid layout UNKNOWN) |
| `JMXVMFO 1000` | `.mfo` | map info | UNKNOWN (magic only) |
| `JMXVNVM 1000` | `.nvm` | navmesh | PARTIAL (cell semantics UNKNOWN) |
| `JMXVOBJI1000` | `.ifo` | object index | PROVEN (nameI index) |
| `JMXVRES 0109` | `.bsr` | mesh resource | PROVEN (path groups; `0108`×3, `0107`×1) |
| `JMXV2DTI1001` | `.ifo` (tile2d) | 2D tile info | PROVEN (719-entry index, Phase 18) |
| `JMXVCAMR1002` | `.ifo` (config) | camera | PARTIAL (magic + f32 stream; field assignment UNKNOWN) |
| `JMXVENVI1003` | `.ifo` (environment) | environment | PARTIAL (magic + u32 header + length-prefixed names + f32 colours) |
| `JMXVOBJL1000` | `.ifo` (layerobjectlist) | object list | PROVEN (text: magic, count, 9-field entries) |

Beyond the shared 12-byte magic, the formats do **NOT** share a common
sub-structure: `.ddj` puts a `u32 data_size` + `u32 level` at offset 12,
`.bms` puts a `u32 header_size` + six section offsets, `.bsk` a `u32
bone_count`, `.bsr` an 8×u32 table, `.nvm` a variable count/extent header,
`.ban` 8 reserved bytes + a name length. The shared convention is therefore
**only** the `JMXV` signature + format identifier; everything after is
format-specific.

### The polymorphic `.ifo` extension (NEW — this batch)

The `.ifo` extension is NOT a single format. Reading the 12 `.ifo` files
across `Data.pk2`/`Map.pk2` reveals **five distinct JMX magics** plus one
plain-text file:

| file | size | magic | family |
|---|---|---|---|
| `object.ifo` (both archives) | 231,665 | `JMXVOBJI1000` | object index (PROVEN, Phase 17) |
| `objectstring.ifo` (both archives) | 55,207 / 40,444 | `JMXVOBJI1000` | object string index |
| `objext.ifo` (both archives) | 41 | `JMXVOBJI1000` | object extension index |
| `tile2d.ifo` (both archives) | 36,629 | `JMXV2DTI1001` | 2D tile info (PROVEN, Phase 18: 719 entries `id → flag(0x00–0x0c) → class → .ddj → {x,y}`) |
| `config.ifo` | 111 | `JMXVCAMR1002` | camera config (UNKNOWN) |
| `environment.ifo` | 76,000 | `JMXVENVI1003` | environment (UNKNOWN) |
| `layerobjectlist.ifo` | 219,890 | `JMXVOBJL1000` | object list (UNKNOWN) |
| `tile3d.ifo` | 2 | `0\n` (ASCII) | plain text, not JMX |

`JMXVCAMR1002`, `JMXVENVI1003`, and `JMXVOBJL1000` are new magic tags not
previously catalogued. `JMXV2DTI1001` (`tile2d.ifo`) is now decoded (719-entry
text index; see Phase 18). The remaining three are magic-confirmed but
otherwise undecoded (UNKNOWN). This explains why the `.ifo` extension must not
be blanket-classified: the extension is a container-family shorthand, and the
magic is the authoritative discriminator.

- `.ban`/`.bms`/`.nvm`/`.efp`/`.bsk` bodies all embed short ASCII strings
  (animation names, `BoneNN` bone names, emitter command tokens) that can aid
  future field identification.
- Real derived fixtures (structure only, no raw binaries) are committed under
  `scripts/testdata/formats/` for the format tests; each fixture records its
  source archive path, size, and structure facts proven against the live
  archive.

## 7. World data relationships (Phase 13 Part B/J)

### `npcpos.txt` (Media.pk2, UTF-16 TSV) — column semantics CORRECTED

The Phase 12 schema labeled `npcpos.tsv` columns `col0=spawn_id`,
`col1=character_refid`. Live-data joins disproved that; the proven layout is:

| col | name | evidence |
|-----|------|----------|
| 0 | `character_refid` | 1180/1180 distinct values join `characterdata_*.txt` col1 |
| 1 | `region_code` | 1800/1855 distinct values join `regioncode.txt` col1; `region & 0xFF` = x sector, `region >> 8` = y sector |
| 2 | `local_x` | sector-local x, `[0, 1920)` for world rows |
| 3 | `height_y` | height axis, finite, varies (elevation) |
| 4 | `local_z` | sector-local z, `[0, 1920)` for world rows |

Placement facts proven on the committed 18,457-row set:
- 14,800 world rows (region high bit clear) vs 3,657 instance/dungeon rows
  (region high bit set -> 21 distinct negative/signed-16 codes).
- World rows place `(local_x, local_z)` in `[0, 1920)`; exactly 13 boundary
  rows sit at `1920.0` on one axis (sector edge), documented, not repaired.
- Region pack is the verified `pack_region` convention (sector = unpack_region).
- `npc_to_world(x, z, region, ref_sx, ref_sy)` matches the Phase 10 reference
  formula; RN_CH_JANGAN region codes (9 codes) place 53 NPCs in sectors
  `167..169 x 96..98`.
- Instance/dungeon coordinate space is a separate UNKNOWN space (local coords
  not bounded to `[0,1920)`); not guessed.

Deliverables: `scripts/test_phase13_npcpos_regions.py` (14 tests),
`scripts/textdata_schemas.py` `VERIFIED_NAMES` corrected, `TEXTDATA_SCHEMAS.json`
+ `DATA_REFERENCE_GRAPH.json` regenerated, `NpcPosTable.java` column accessors
renamed (`characterRefId`/`regionCode`/`localX`/`heightY`/`localZ`).

---

## 8. `.o2` object overlays + object identity chain (Phase 17) — **PROVEN**

### `.o2` — object instance overlay (`JMXVMAPO1001`) — **RECORD LAYOUT PROVEN**

All 4,348 Map.pk2 `.o2` files were walked with a parser that starts at a
variable data offset and consumes records until exhaustion. Starting at
**offset 16** consumes every file exactly (1,322 are empty after the header),
and the resulting instance count equals the first-nonzero-start result for
every file — the variable header is pure zero-count-group padding.

```
header:  magic[12] "JMXVMAPO1001"  u32 count_groups   (always zero fields)
record (30 B each, after offset 16):
   0  u32   nameI          index into /navmesh/object.ifo
   4  f32   x  y  z        position LOCAL to the tail sector (tx,tz)
  16  u16   unknown0       0xFFFF for boundary-sector records
  18  f32   theta          yaw (radians; 820 -> 0.0, 574 -> -6.4403)
  22  u16   unknown1       (0 for all 820 records; never interpreted)
  24  u16   unknown2       (0)
  26  u16   unknown3       (0)
  28  u16   tail           tx = tail & 0xFF, tz = tail >> 8
world = (tail_sector - reference_sector) * 1920 + local   # PROVEN
```

Verified on `/90/156.o2`: 32 instances = 4 distinct raw records duplicated by
the author (820 ×16, 574 ×9, 820 ×4 tail (157,90), 820 ×3 tail (156,91)).

### `.o` — object overlay, 28-byte records (`JMXVMAPO1001`) — **PROVEN**

`.o` files share the `JMXVMAPO1001` magic and group framing with `.o2`, but use
a **28-byte record** (they drop the always-zero `unknown3` u16, so `tail` lands
at offset 26 instead of 28). A 352-file stratified sample plus a full 4,484-file
walk confirm the group-stream walker consumes every `JMXVMAPO1001` `.o` file
exactly; `max nameI == 3306`, matching `object.ifo`'s 3307-entry index (0..3306).

```
header:  magic[12] "JMXVMAPO1001"  u32 @12 == 0
record (28 B each, after offset 16):
   0  u32   nameI          index into /navmesh/object.ifo
   4  f32   x  y  z        position LOCAL to the tail sector
  16  u16   unknown0       0xFFFF for boundary-sector records
  18  f32   theta          yaw (radians)
  22  u16   unknown1       varies (packed grid; UNKNOWN)
  24  u16   unknown2       (0)
  26  u16   tail           RELATIVE: 0 = own sector, 1 = +x, 256 = +z
```

Verified on `/100/100.o`: 58 instances, `nameI` counts
`{1489: 39, 669: 11, 1488: 7, 1748: 1}`, all `nameI` resolve in `object.ifo`.
The `tail` field is **relative** (0 = own sector), unlike `.o2`'s absolute
packed-sector tail; 1,154 of 76,951 records cross a boundary (tail 1 or 256).
`.o` and `.o2` for the same sector carry different instance sets (`.o2` roughly
doubles `.o`), so they are distinct passes, not duplicates. Seven `.o` files are
228-byte `JMXVMAPO1000` empty placeholders with a zero payload.

### `object.ifo` — nameI → `.bsr` index (`JMXVOBJI1000`) — **PROVEN**

After the 12 B magic + count line, rows are `nameI u32` + quoted path; paths
normalize to a leading `/`. nameI **820** → `/res/nature/common/tree/new-maple/tre_tree03.bsr`,
nameI **574** → `/res/nature/common/tree/tre_tree02.bsr` (live meshes under
`/prim/mesh/nature/common/tree/...`).

### material → texture link — **PROVEN**

Per `.bms` part, the BMS header `names[1]` is the **material name**; the
texture is `material + ".ddj"` resolved in the `.bmt` directory and present in
the `.bmt` blob: tre_tree03_01 → `tre_tree03_01.ddj`, _02 → `tre_pine08_03.ddj`,
_03 → `tre_pine08_02.ddj`; tre_tree02 parts map to their own names.

### MSH1 — Android mesh asset (new committed format) — **PROVEN round-trip**

```
[4B "MSH1"][u8 version=1][u8 layout 0/1][u16 flags bit0=uv2]
[u32 vcount][u32 tcount][u32 non_static][u16 tex_index][u16 reserved]
vcount x 32 B (std: pos3f+norm3f+uv2f) | 40 B (lightmap: +uv2 2f)
u16 x tcount*3 indices
```

`bms_to_msh` / `read_msh` round-trip byte-identical; `non_static_vertices` is
informative (real trees legitimately carry `flags != 0` — dropping them removed
real canopy geometry, so MSH1 keeps every vertex).

### MSH v2 — skinned Android mesh asset (Phase 18) — **PROVEN round-trip**

```
[4B "MSH1"][u8 version=2][u8 layout 0/1][u16 flags bit0=uv2, bit1=has_skin]
[u32 vcount][u32 tcount][u32 skinned_vertex_count (informative)][u16 tex_index][u16 reserved]
vcount x 32 B | 40 B vertex records
vcount x 6 B  skin records [u8 bone1][u16 weight1][u8 bone2][u16 weight2]
u16 x tcount*3 indices
u32 bone_count + bone_count x (u32 name_len + ascii name)
```

Produced by `scripts/bms_to_asset.py::bms_to_msh_skinned`; `read_msh` round-trips
v1 + v2. Bandit parts: sword (1 bone `Bip01 R Hand`), part1 (18 bones), part2
(17 bones) — mesh bone names ⊆ the 35-bone skeleton (proven).

### Character chain (Phase 18) — **PROVEN end-to-end for bandit**

```
characterdata_*.txt col1=refid 1949 -> col52 "mob\china\bandit.bsr"
.bsr -> .bmt (bandit/clone/champ) + .bms parts + 16 .ban + .bsk + 7 .efp + 16 .wav
.bms part -> material name (header names[1]) -> .ddj via .bmt (case-insensitive)
.ddj -> DDS -> RGBA PNG (committed tex/*.png)
.bms -> MSH v2 skinned mesh (committed mesh/*.msh)
.bsk -> skeleton.json (35 bones, [x,y,z,w], bind_world_rot/pos)
.ban -> decoded keyframe JSON (stand01/walk committed)
npcpos row refid 1949 -> region/local -> world (ref sector 156x89)
```

Committed under `android/app/src/main/assets/game/world/characters/bandit/` with
`provenance.json` recording the sha256 of every original input
(`scripts/build_character_manifest.py`, 17 tests, byte-identical rebuild).

### World placement

Sector 156x90 holds 32 real instances: 23× tre_tree03 (nameI 820, θ 0) + 9×
tre_tree02 (nameI 574, θ −6.4403), tails (156,90)/(157,90)/(156,91); the world
formula above yields positions matching the committed 156x90 height grid. Scale
(the mesh AABB is in hundreds of units, y 148..760) is UNKNOWN; no scaling
claimed.

Deliverables: `scripts/o2_decoder.py` (+12 tests), `scripts/bms_to_asset.py`
(+12 tests), `scripts/build_object_manifest.py` (+8 tests, byte-identical
rebuild), committed assets under `android/app/src/main/assets/game/world/objects/`
(6 `.msh` + 6 `.png` + `models.tsv` + `placements.tsv`).

## 9. `.dat` heterogeneous families (reclassified — evidence-first)

`.dat` is NOT one format. A deterministic classifier
(`scripts/dat_families.py`, tests `scripts/test_dat_families.py`) splits every
`.dat` record into concrete families by leading bytes, never by filename.

### Corpus (88 `.dat` records, 73,247,057 bytes)

| Family | Count | Status | Source |
|---|---|---|---|
| `ainavdata` | 26 | PARTIAL | `Data.pk2 /navmesh/ainavdata_3276{9..87}.dat` |
| `bmp` | 48 | PROVEN | `Media.pk2 /launcher/*` + `/launcher_europe/*` |
| `jmxvimg` | 3 | PROVEN | `Media.pk2 /fonts/{0,i,y}.dat` |
| `palette` | 1 | PROVEN | `Media.pk2 /silk.dat` |
| `hex-token` | 2 | PROVEN | `Silkload.dat` (client + `.7z`) |
| `config` | 7 | PARTIAL | client `Setting/*.dat` |
| `plugin` | 1 | PROVEN | `Map.pk2 /plugin.dat` |

### `ainavdata` (AI navigation data) — PARTIAL (header + vertex section proven; edge records UNKNOWN)

Header (24 bytes), proven from real bytes across all 26 files:

- byte 0 = version `0x01`.
- u32 LE @1..4 = `vertex_section_offset`: the **absolute file offset** of the
  trailing vertex/sub-section (NOT a byte count). At that offset every file
  repeats its `region_id` + `type` as a sub-header (verified for all 26).
- u16 LE @5..6 = `region_id` = `0x8000 | numeric_id`; `numeric_id` == the id in
  the filename (32768..32794). e.g. `ainavdata_32787.dat` carries `0x8013`.
- byte 7 = `type` (varies: `0x01,0x05,0x0d,0x13,0x14,0x16,0x17,0x1d,0x20,
  0x23,0x29,0x2d,0x45,0x57,0x59,0x97`).
- u32 @8..11 = 0.
- u16 BE @14..15 = `count_a` (secondary count, semantics UNKNOWN).
- u16 BE @16..17 = `0x0000` (simple files) or `0x0100`/`0x0800` (complex files)
  — UNKNOWN.
- u16 BE @18..19 = `count_b` = vertex count (matches the count in the trailing
  sub-section).
- bytes 20..23 = 0 for simple files; byte 20 is occasionally `0x01`/`0x02`
  (small LE u32) — UNKNOWN.

Body (offset 24 .. `vertex_section_offset`-1): edge/cell connectivity data as
big-endian u16 values. The leading records carry a `0x00`/`0x01` type byte and
later records use `0x02`/`0x03` (a two-section structure, first section length
≈ `count_a`); exact record length and semantics are NOT yet proven.

Trailing sub-section (offset `vertex_section_offset` .. EOF), proven:

- u16 LE `region_id` (repeats header), u8 `type` (repeats header).
- u32 BE `count` (= header `count_b`).
- 3 padding bytes `0x00`.
- `count` × 12 bytes of vertex positions as f32 LE triplets `(x, y, z)`.
  For region navmesh (`type 0x01`) `y == 0.0` (2D X-Z grid; height resolved from
  terrain at runtime). For dungeon navmesh (`type 0x97`) `y` is a real height
  (3D).
- 1 trailing zero float (4 bytes `0x00`).

Simple vs complex: for 11 of 26 files the sub-section is exactly
`7 + 3 + count_b*12 + 4` bytes (sub-header + pad + vertices + trailing zero).
The other 15 files append extra edge/link data after the vertex array (not yet
decoded); these are the larger / multi-type regions and dungeons.

`SR_GameServer.exe` references confirm the loader: strings `AINavData*.*`,
`Failed To Load AI_NAVIGATION Data File! [%s]`,
`AI_NAVIGATION Data [%s] Loaded`, `AINavData Version is not match!!!`,
`AINavData_%d.DAT`, and path `DATA\navmesh`. `GameClient.exe` carries
`RTNavMeshTerrain.cpp`, `NavMesh`, `Navigation`.

### `jmxvimg` (font glyph image) — PROVEN magic, UNKNOWN header semantics

`Media.pk2 /fonts/{0,i,y}.dat` each begin `JMXVIMG11000`. Header carries two
u16-like fields (at 12 and 14) followed by BGRA pixel data. The 12-byte magic is
proven; the header field semantics (dimensions/stride) are explicitly UNKNOWN.

### `palette`, `hex-token`, `bmp`, `config`, `plugin`

- `palette`: `/silk.dat` = 768 B = 256 × RGB, classic 16-color VGA head.
- `hex-token`: `Silkload.dat` = ASCII hex string, no newline (170 B).
- `bmp`: launcher UI assets misnamed `.dat`, all `BM` (e.g. `bg_1.dat` 700×419).
- `config`: client settings, u32-count-prefixed binary records; field layout
  per-file UNKNOWN. Includes the tiny `SRExtQSOption.dat` (11 B, count 2) and
  `SRExtQSOption2.dat` (6 B, count 1) whose per-record layout is indeterminate
  from so few bytes.
- `plugin`: `/plugin.dat` (46 B) = plugin loader manifest — u32 LE count, then
  per entry a 16-byte identifier (GUID/hash, semantics UNKNOWN) + u16 LE name
  length + null-terminated name. The single entry is `bsnetEx.dll`.

### `.dat` UNKNOWN residue

None. All 88 `.dat` records now classify into a concrete family; the previous
UNKNOWN residue (`/plugin.dat`, `SRExtQSOption{,.2}.dat`) is now `plugin`
(PROVEN) and `config` (PARTIAL) respectively.

Deliverables: `scripts/dat_families.py`, `scripts/test_dat_families.py`
(12 tests), `scripts/reclassify_dat.py` (targeted `.dat` reclassification
applied to `SOURCE_CORPUS_MANIFEST.json` / `SOURCE_CORPUS_STATS.json` /
`SOURCE_SYSTEM_INVENTORY.json`).

## 10. SQL `.Bak` backups — MTF wrapper confirmed

All four `*.Bak` files (`SRO_CERTIFICATION`, `SRO_VT_ACCOUNT`,
`SRO_VT_SHARD`, `SRO_VT_SHARDLOG`) begin with the 4-byte magic `TAPE`
(`54 41 50 45`), the Microsoft Tape Format (MTF) signature that wraps SQL
Server backup streams. Proven from the first 4 bytes of each file; the MTF
container internals (backup set descriptors, media headers, database page
stream) are NOT decoded — table names were instead recovered by a read-only
strings scan (`SQL_DATABASE_SCHEMA.json`: `account` 71, `shard` 487,
`shardlog` 14, `certification` 0 tables). See `CLIENT_SQL_EVIDENCE.json` for
the consolidated client-archive + RecMsg/SendMsg + SQL schema evidence.

## 11. `.bmt` materials, `tile2d.ifo` index, and `.t` tile maps (Phase 18)

### `.bmt` material (`JMXVBMT 0102`) — **FULL LAYOUT PROVEN**

All 4,269 `Data.pk2` `.bmt` files (16,328 entries) parse byte-exactly with a
single layout; no exceptions:

| Offset | Size | Field |
|---|---|---|
| 0 | 12 | magic `JMXVBMT 0102` |
| 12 | 4 | `u32` material count |
| then per entry: | | |
| +0 | 4 | `u32` name length (null-padded to 4-byte-ish boundary) |
| +4 | len | null-padded ASCII material name |
| +len | 72 | 18 × `f32` material props (ambient/diffuse/specular/emissive RGBA + extras) |
| +72 | 4 | `u32` ddj length (null-padded) |
| +4 | len | null-padded ASCII `.ddj` texture path |
| +len | 7 | tail = `f32 1.0` + 3 bytes (semantics UNKNOWN; census: `180000`/`200800`/`000001`/`000000` dominant) |

The name/ddj length fields carry **null padding** (e.g. `electus_m_xmas` =
14 chars stored in an 18-byte field). The previous `parse_bmt` returned the
padded bytes verbatim, which broke `.endswith(".ddj")` lookups; Phase 18 fixes
this (`_strip_padded`) while preserving the dict interface.

Decoded props for `electus_m_xmas` = `[0.588,0.588,0.588,1.0, 0.588,0.588,0.588,1.0,
0.9,0.9,0.9,1.0, 0,0,0,1.0, 0,0]` — three RGBA sets (diffuse gray ~0.588,
specular ~0.9, emissive black) plus two trailing floats (0.0), i.e. a standard
fixed-function material block.

### `tile2d.ifo` 2D tile index (`JMXV2DTI1001`) — **PROVEN**

`Map.pk2 /tile2d.ifo` (and `Data.pk2 /navmesh/tile2d.ifo`) is a text index
(magic line `JMXV2DTI1001`, line 2 = count `719`), one entry per line:

```
ID 0xFLAG "CLASS" "texture.ddj" {x,y} {x,y} ...
```

719 entries, `id` 0..718, `flag` ∈ `{0,1,3,6,7,9,10,11,12}`, `class` is a
region/material group name (e.g. `CJfild`, `Arabia`, `East Eurpoe`), `texture`
is a `tile2d/*.ddj` path, and the optional `{x,y}` pairs are world-sector
coordinates naming where the tile appears. `tile3d.ifo` is a 2-byte plain-text
`0\n` (no 3D index).

### `.t` map tile (`JMXVMAPT1001`) — **PARTIAL (header/size/tile refs proven; grid UNKNOWN)**

4,989 files (Map.pk2 4,988 + Media.pk2 1). Proven facts:

- 12-byte magic `JMXVMAPT1001`; standard size `140,436` = `12 + 140,424`
  (4,987 files byte-identical in size).
- Body is a dense 8-bit stream dominated by `0x00` (40%) and `0xFF` (44%).
- As `u16` cells, ~40% are tile IDs within `tile2d.ifo` range 0..718
  (cross-referenced via `parse_t`), the rest `0xFFFF`/`0x0000` "empty" markers
  plus RGB565-looking color values (e.g. `0x9CD3`, `0xE73C`, `0x5555`).
- Anomalies: `/88/83_13.t` (92,712 B) is actually `.m` terrain (`JMXVMAPM1000`)
  misnamed `.t`; `Media.pk2 /SV.T` is 1,024 B.

**Unresolved**: the exact grid dimensions. The body `140,424 = 2³·3·5851`
(5851 prime) resists every clean grid factorization (no 96/97/128/256/512
stride fits). The trailing 2,992 bytes are a repeating
`ff ff ff ff 00 00 00 00` alternation. No authoritative `.t` loader exists in
the decompiled `com.opensilkroadmap.app.world` classes (they only handle the
`.hg` height grid). The `.t` grid layout and per-cell semantics remain UNKNOWN;
`parse_t` therefore only asserts the header/size and the tile-ID
cross-reference, never the cell grid.

Deliverables: `scripts/world_terrain.py` (`parse_bmt_entries`,
`parse_bmt`, `parse_tile2d_ifo`, `tile2d_index`, `parse_t`),
`scripts/test_phase18_t_bmt.py` (13 tests), reclassification of `.bmt` → PROVEN
and `.t` → PARTIAL via `scripts/reclassify_jmx.py`.

## 12. The polymorphic `.ifo` tail + non-JMX residue (Phase 21)

This batch closes the `.ifo` family and every remaining non-JMX UNKNOWN format
that has a provable header. Three new decoders landed: `scripts/ifo_decoder.py`
(`.ifo`), `scripts/reclassify_ifo.py`, and `scripts/misc_decoder.py` +
`scripts/reclassify_misc.py` (`.rd`/`.2dt`/`.mfo`/`.msf`/`.bak`/`.dll`/`.exe`/
`.pk2`/extension-less icon).

### `.ifo` new magics

| magic | file | status | evidence |
|---|---|---|---|
| `JMXVOBJL1000` | `layerobjectlist.ifo` | **PROVEN** | text: line 0 magic, line 1 decimal count `3334`, then 3,334 lines × 9 space-separated fields `{id_hex} {type} {sx} {sy} {x_hex} {y_hex} {z_hex} {theta_hex} {flag}`; top 16 bits of `id` == `(sy<<8)|sx`; x/y/z/theta are float32 hex bit-patterns; `type`∈1..11, `flag`∈{0,1}. Count matches exactly. |
| `JMXVCAMR1002` | `config.ifo` | PARTIAL | magic + stream of float32 camera params; pos/target/up/fov assignment UNKNOWN. |
| `JMXVENVI1003` | `environment.ifo` | PARTIAL | magic + u32 header + length-prefixed name (`Env7`) + f32 colour/lighting values. |
| `JMXV2DTI1001` | `tile2d.ifo` | PROVEN | (Phase 18) 719-entry text index. |
| `JMXVOBJI1000` | `object*.ifo`/`objext.ifo` | PROVEN | (Phase 17) object/string/extension index. |
| `0\n` | `tile3d.ifo` | TEXT | 2-byte plain text, not JMX. |

`reclassify_ifo.py` reads the leading 12 magic bytes per `.ifo` (the extension
is polymorphic) and applied PROVEN to the 9 `OBJI`/`2DTI`/`OBJL` files, PARTIAL
to `CAMR`/`ENVI`, and TEXT to `tile3d.ifo`.

### Non-JMX residue

| extension | count | status | format | evidence |
|---|---|---|---|---|
| `.rd` | 103 | PROVEN | `bmp-region-thumbnail` | all 103 `VSRO-R Client` region files are standard Windows BMP: `BM`, file size 1334, data offset 1078, 16×16, 8 bpp indexed (identical header across all). |
| `.dll` / `.exe` | 35 / 19 | PROVEN | `pe-executable` | `MZ` + `PE\0\0` at `e_lfanew` (42/44 extracted samples verified; the 12 container-only records are PE by construction). |
| `.pk2` | 1 | PROVEN | `pk2-archive` | nested `Media.pk2` inside `VSRO-R Client.7z` (`JoyM` header). |
| `(none)` icon | 1 | PROVEN | `jmx-texture` | `/icon/action/cos_cmd_inventory` is a misnamed `.ddj` (`JMXVDDJ 1000`, 32×32 DDS) — parsed by `jmx_ddj.parse_ddj`. |
| `.2dt` | 51 | PARTIAL | `cnif-ui-layout` | u32 field + `CNIF` magic + null-terminated window name (e.g. `BattleArenaRankWnd`); body is a serialized UI control tree embedding `.ddj` texture and `UIIT_` string tokens (UNKNOWN). `guild_r.2dt` is a multi-`CNIF` aggregate (first `CNIF` at offset 4,884). |
| `.mfo` | 2 | PARTIAL | `jmx-mfo-mapinfo` | `JMXVMFO 1000` + u16 width + u16 height (256×128); trailing sparse data grid (740 nonzero bytes, ~252 u32 cells) UNKNOWN. |
| `.msf` | 2 | PARTIAL | `sound-effect-script` | u32 count=1 + u32 fields + length-prefixed `ambient` name + `.efp` path refs (`system\summer_oura.efp`) + f32 triples. |
| `.bak` | 4 | PARTIAL | `mtf-sql-backup` | `TAPE` MTF magic (section 10); container internals not decoded. |
| `.crb` | 18 | PARTIAL | `crest-16x16-grid` | 256-byte fixed grid (16×16 bytes) of small integer tile/terrain codes; per-cell semantics UNKNOWN. |
| `.scc` vssver2 | 2 | DEAD | `vss-source-control` | Microsoft Visual SourceSafe version-file (`34 12 01 00` magic) + `$/project` path string + null-terminated file-name list; source-control metadata, not game data. |

**Left UNKNOWN (no provable structure):** `.cs3` ×2 (`Map1.CS3`,
`Map2.CS3`, 13,000 B each, byte entropy 5.77 with all 256 byte values present —
consistent with encryption/compression). The two files are identical except for
2 bytes at offset 12,604–12,605 (map index), which is consistent with a shared
encrypted/compressed payload whose only plaintext difference is the map
identifier; without the server's decryption routine the payload cannot be
parsed.

### Final reconciliation (120,840 indexed files)

| status | count |
|---|---|
| PROVEN | 83,216 |
| PARTIAL | 37,583 |
| UNKNOWN | 2 |
| TEXT | 1 |
| STUB | 17 |
| DEAD | 21 |
| MISSING | 1 |

Deliverables: `scripts/ifo_decoder.py`, `scripts/misc_decoder.py`,
`scripts/test_phase21_ifo.py` (5 tests), `scripts/test_phase21_misc.py`
(8 tests), `scripts/reclassify_ifo.py`, `scripts/reclassify_misc.py`.
