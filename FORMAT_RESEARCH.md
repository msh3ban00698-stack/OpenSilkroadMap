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
120,876–194,604; `907`/`1801` do not divide the body). Decoder: **none**.
Evidence fixture: `scripts/testdata/formats/nvm_grid.json`; tests:
`scripts/test_phase13_nvm.py`.

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

- All six formats are little-endian (LE) and share the `JMXV` magic family
  (`JMXVDDJ`, `JMXVBAN`, `JMXVBMS`, `JMXVNVM`, `JMXVEFF`, `JMXVBSK`, `JMXVRES`).
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
