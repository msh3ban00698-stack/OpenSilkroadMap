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

## 3. PARSED/NORMALIZED — wired to Android consumers (Phase 12)

- **All 21 datasets** now have Android-free parsers in
  `android/app/src/main/java/com/opensilkroadmap/app/data/` (NpcPosTable,
  LevelDataTable, LevelGoldTable, TeleportDataTable, RefShopGoodsTable,
  WorldMapInstanceTable, QuestDataTable + generic TsvTable), with 10 JVM tests
  against real committed values (`TextDataTablesTest.java`).
- `GameDataCatalog` (Phase 12) composes npcpos/leveldata/teleportdata/
  worldmap_instanceinfo and is wired into `GameActivity`/`GameHudView`; the HUD
  shows real counts and degrades to an explicit "not bundled" state when the
  assets are absent. Schema/join provenance: `TEXTDATA_SCHEMAS.json`,
  `DATA_REFERENCE_GRAPH.json`.

### Phase 14 — native world runtime (terrain consumer)

- The Phase 10 `.hg` height grids (23 real sectors, `world_index.tsv`) are now
  consumed by the native world screen: `GameActivity` → `NativeWorldRenderer` →
  `Camera2D` renders the verified heightfield (DIAGNOSTIC TERRAIN RENDERER, not
  final 3D). Selection is deterministic (first region whose reference sector has
  a committed `.hg`): `Jangan_Field` sector `156x89` (`Map.pk2 /89/156.m`,
  min 866.25 / max 2687.02, 97×97 = 9,409 heights).
- Missing terrain assets fail closed (explicit "TERRAIN ASSET MISSING" state,
  no substitution). No models/objects/NPCs are rendered (format decode BLOCKED,
  no fabricated geometry). Executed evidence: `scripts/test_phase14_world_runtime.py`
  (16 tests). Build/runtime NOT EXECUTED here (no JDK/Android SDK).

### Phase 15 — multi-sector world + NPC placement

- The native world screen now loads EVERY committed `.hg` sector in the selected
  region window (not just the reference sector). For `Jangan_Field`
  (window `sx 156..182, sy 89..102`) this loads `156x89` + `156x90` as a
  `WorldTerrainSet` (world extent 1920 × 3840), verified edge-continuous
  (`g1[96][x] == g2[0][x]`).
- `npcpos.tsv` is now consumed at runtime by the Android-free `NpcSpawnIndex`
  (18,457 rows: 14,800 world + 3,657 dungeon). Verified world spawns are drawn as
  DIAGNOSTIC PLACEMENT MARKERS only (no character model decoded).
- Object placement (`.o2`, 4,348 overlays) characterized: magic `JMXVMAPO1001`,
  offset 12 always `u32=0`, variable data start `>= 16`; `parse_o2` is proven
  only when data starts at 16 — remaining header layout UNKNOWN.
- Executed evidence: `scripts/test_phase15_world_integration.py` (12 tests, OK).
  JVM/instrumented tests + build/runtime NOT EXECUTED (no JDK/Android SDK).

### Phase 17 — real object mesh rendering

- `.o2` record layout now PROVEN for every file (`scripts/o2_decoder.py`, 12
  tests): walker from offset 16 consumes all 4,348 files exactly (variable
  header = zero-count-group padding); record = `u32 nameI + 3x f32 x/y/z +
  u16 + f32 theta + 3x u16 + u16 tail` (30 B); `world = (tail − ref) × 1920 +
  local`.
- Real model chain PROVEN: `nameI → object.ifo → .bsr → {.bms parts + .bmt →
  material.ddj → DDS → RGBA PNG}` (`scripts/build_object_manifest.py`, 8 tests
  incl. byte-identical rebuild). Sector 156x90 yields 32 real instances (23×
  tre_tree03 + 9× tre_tree02) from 6 committed mesh parts + 6 PNG textures.
- Committed assets under `android/app/src/main/assets/game/world/objects/`
  (`models.tsv`, `placements.tsv`, `mesh/*.msh` (MSH1), `tex/*.png`).
- Java consumes them: `StaticMeshAsset` (strict MSH1 parser),
  `MeshObjectIndex` (models+placements+PNG), `NativeWorldRenderer` draws each
  real mesh at its proven world position with θ rotation and per-triangle
  texture mapping (2D Canvas top-down projection). Overlay state ends "REAL
  TERRAIN + NPC PLACEMENT + OBJECT MESH".
- JVM/instrumented tests added (`StaticMeshAssetTest`, `GameActivityTest`
  additions) but NOT EXECUTED (no JDK/Android SDK).
- Executed evidence: `scripts/test_phase17_*.py` (32 tests, all OK); full 23-suite
  regression green.

### Phase 18 — skinned NPC character pipeline

- **Character chain PROVEN end-to-end for the bandit NPC** (refid 1949):
  `characterdata_*.txt` (Media.pk2) col1=refid → col52 `mob\china\bandit.bsr`
  → `{3 .bmt, 3 .bms, 16 .ban, 1 .bsk, 7 .efp, 16 .wav}` (`scripts/bsr_decoder.py`).
- **BSK decoded** (`scripts/bsk_decoder.py`): byte-exhausts 1,034/1,035 nonzero
  `.bsk`; bandit = 35 bones; quaternion convention **PROVEN `[x,y,z,w]`**; bind
  pose aligned to real mesh bounds.
- **BMS per-vertex skin block decoded** (`scripts/bms_decoder.py::parse_skin_data`):
  6 B/vertex `[u8 b1][u16 w1][u8 b2][u16 w2]`, 0xFF sentinel, single-influence
  `w2=0`.
- **BAN pose evaluation** (`scripts/animation_pose.py`): slerp/pos-lerp between
  adjacent PROVEN keyframes; bandit_stand01 2000 ms, bandit_walk 1333 ms.
- **CONVERTED and committed** under
  `android/app/src/main/assets/game/world/characters/bandit/`:
  `skeleton.json` (35 bones, bind world), 3 MSH v2 skinned meshes
  (`scripts/bms_to_asset.py::bms_to_msh_skinned`), 3 real `.ddj`→PNG textures,
  `anims.tsv` + 2 animation JSON, `npc_placements.tsv` (60 real spawns, 31
  sectors, 2 on committed terrain 156x90), `provenance.json` (sha256 of every
  input). `scripts/build_character_manifest.py` (17 tests) rebuilds
  byte-identically.
- Java: `CharacterMeshIndex` (Android-free loaders + minimal JSON parser +
  bind-pose `skinnedBindPositions` = Σ(w/Σw)·(R·v+t)), `StaticMeshAsset` MSH v2
  parser, `NativeWorldRenderer.drawCharacters` (static bind pose, theta=0
  UNKNOWN), `GameActivity` wiring. `CharacterMeshIndexTest` (JVM) +
  `GameActivityTest` additions written but **NOT EXECUTED** (no JDK/Android SDK).
- Executed evidence: 5 new Phase 18 Python suites (52 tests) + full 24-suite
  regression **294 tests, 13 skipped, OK**.

### Phase 19 — real skinning semantics + animation playback

- **BSK transform semantics PROVEN** (`scripts/test_phase19_bsk_semantics.py`):
  `rot_origin`/`tr_origin` == bone WORLD bind (byte-exact to `skeleton.json`);
  `rot_parent`/`tr_parent` == parent-relative local; `rot_local`/`tr_local` ==
  inverse-bind (root proven; child PARTIAL). `bone_type` u8 census = constant 0
  across 29,957 bones (meaning UNKNOWN).
- **Skinning weights PROVEN** (`scripts/test_phase19_weights.py`): max 2
  influences/vertex, u16 weights, `0xFF` sentinel; sums NOT exactly 65535
  (bandit_part1 min 49146/max 65531; sword single-influence only) — normalization
  is a renderer operation.
- **Bind-pose skinning PROVEN** (`scripts/bms_to_asset.py::validate_skinned_mesh`):
  reproduces stored rest vertices with max deform ≈ `2e-6`.
- **Animation PROVEN** (`scripts/test_phase19_animation.py` + `_pose.py` +
  `_real_animation.py`): full keyframes exported (walk 34×15 @1333 ms, stand01
  34×5 @2000 ms); non-uniform timestamps (no fixed FPS); LOOPING proven; channel
  space = absolute parent-relative replacing bind. 2 `JMXVBAN 0101` anomalies
  UNKNOWN.
- **FIRST REAL NPC + ANIMATION DONE**: bandit refid 1949 (35 bones, 3 meshes
  846 verts, 3 textures, 16 anims, 61 npcpos spawns, 2 on committed 156x90)
  rendered AND animated at deterministic timestamps; snapshots committed under
  `docs/phase19/snapshots/`.
- **PLAYER (chinaman) PARTIAL**: skeleton (38 bones) + meshes + anims PROVEN;
  BSR references `europeman_skel.bsk` (43 bones) instead of `chinaman_skel.bsk`;
  no static spawn (npcpos is NPC-only).
- **Java renderer (compile-only)**: `Pose.java` + `CharacterRenderer.java`
  compile clean (`javac`); `NativeWorldRenderer` pose-driven `drawCharacters`
  with bind fallback; skinning math verified (bind reproduces rest, 90° rotation,
  parent->child chaining). APK build + device runtime NOT EXECUTED (no Gradle/
  Android SDK).
- Proof artifacts: `scripts/build_phase19_evidence.py` + committed
  `phase19_evidence.json` (bandit DONE / chinaman PARTIAL).

### Phase 20: data-driven character runtime (bulk shared store)

- **Shared store** committed under `android/app/src/main/assets/game/world/characters/`:
  `index.tsv` (`refid key variant status spawn_count`, 1,094 rows), `coverage.json`
  (audit), `shared/{skel,mesh,tex,anim}/` deduped by slug (355 / 1585 / 655 /
  2300 files), `<key>/manifest.json` + `<key>/provenance.json` +
  `<key>/npc_placements.tsv` (473 NPC keys) and `player/` (PARTIAL).
- **Models**: 477 distinct `.bsr` → 473 PROVEN (99.16%), 1 PARTIAL (karkadann,
  triangle-section parse), 3 UNKNOWN (not characters: `gate_pulley`,
  `property_recall`, `ins_quest_teleport`).
- **Java** `CharacterCatalog` (refid→key index) + key-based
  `CharacterMeshIndex.load(AssetManager, key)` (shared-store loader); NPCs
  instanced by `characterRefId` in `NativeWorldRenderer`.
- **Bandit directory migrated**: `game/world/characters/bandit/` is superseded by
  the shared store and left in place (not deleted).
- Pipeline: `scripts/character_resolve.py`, `scripts/build_character_manifest.py`
  (`convert_character`/`convert_player`), `scripts/build_character_catalog.py`
  (bulk driver). See `PHASE_20_REPORT.md`.

## 4. DECODED / PARTIALLY DECODED (Phase 12–13 decoders committed)

| Format | Files | Proven subset | Remaining UNKNOWN |
|---|---|---|---|
| `ban` | 4,796 | **FULL layout** (Phase 13 Part D): magic/version; reserved; u32 name-len + name; u32 duration + frame-rate(30) + u32 UNKNOWN + kpb; kpb×u32 timestamps; bone count + per-bone name + kf-count + kpb×28-byte keyframes (quat + pos). Decoder `scripts/ban_decoder.py`, 8 tests. **Phase 19**: full keyframes + looping + channel space proven; 2 `JMXVBAN 0101` anomalies. | semantic only: `u32`@body+8, reserved 8 bytes |
| `bms` | 22,948 | header offset table (6 sections + names); s0 vertices / s1 bones / s2 triangles / s5 AABB; **vertex layout PROVEN: 44 B standard (17,247) / 52 B lightmap (5,399) / 80 B morph (6) / 32 unproven**; **per-vertex SKIN BLOCK proven (Phase 18)**; `scripts/bms_decoder.py`, 16+7 tests. | skinned/flags==2 tail semantics (u32@36 is NOT a local bone index); 80 B morph fields; trailing bytes. Static (flags==0) meshes fully decodable. |
| `nvm` | 6,041 | flat 8-byte nav-cell records; 96×96 (9,216) grid; f32 region; trailing fill. 5 tests. | nav-cell semantics |
| `efp` | 3,395 | version tree + u32-length-prefixed command stream. 11 tests. | command-stream semantics |
| `bsk` | 1,039 | **FULL layout (Phase 18)**: u32 bone_count@12; per bone u8 type + name + parent + 21×f32 (rot_parent/tr_parent/rot_origin/tr_origin/rot_local/tr_local) + child_count + children + 8-byte trailer; byte-exhausts 1,034/1,035. `scripts/bsk_decoder.py`, 9 tests. **Phase 19**: transform semantics proven (origin==world, parent==local, local==inverse-bind root). | `bone_type` u8 (census constant 0); child-bone `rot_local/tr_local` inverse; `mob_select.bsk` outlier |
| `bsr` | 7,549 | **FULL layout (Phase 18)**: 8×u32 table@12 + 16 zero bytes + body@0x3C u32-len-prefixed token stream; classified `.bmt/.bms/.ban/.bsk/.efp/.wav`; `is_character` = has `.bsk`; group order asserted for characters. `scripts/bsr_decoder.py`. | 8×u32 header table semantics |

## 5. DECODED, conversion deferred (backlog, do not claim as done)

| Format | Files | What is proven | What remains |
|---|---|---|---|
| `ddj` (the 39,740 not yet converted) | 47,495 | container + DDS payload extraction proven | convert remaining textures |
| `tga` | 15 | header verified | decode + convert |
| `m` (remaining height grids) | 4,491 | 23 grids converted in Phase 10 | convert all grids |
| `nvm` navmesh | 6,041 | partial structure proven (see section 4) | full structure, extraction of walkable surfaces |
| `bms` / `bsr` / `t` / `o` / `o2` / `bmt` | ~44,000 | magic confirmed; `o2` instance parsing proven; `bms` (incl. skin block) / `bsr` fully decoded for characters (section 4); **bandit chain converted to MSH v2 + PNG (Phase 18)** | convert every mesh/material; full geometry/material pipeline |
| `bsk` | 1,039 | **FULL decode (Phase 18, section 4)**; **bandit skeleton.json committed** | convert every skeleton; player skeleton manifests |
| `efp` | 3,395 | version tree + command stream proven (section 4) | particle system decode |
| `wav` (2,454 remaining) / `ogg` (0 remaining) | 2,454 | decode proven on samples; **Phase 12 converted all 50 `ogg` + 431 `wav`** (`/prim/snd/monster`) with provenance manifest | convert remaining wav sets |
| `2dt` (CNIF text-data) | 51 | container magic confirmed | CNIF string-table decode |

## 6. BLOCKED (format UNKNOWN — no honest decoder yet)

| Format | Files | Bytes | Note |
|---|---|---|---|
| `dat` | 79 | 73.2 MB | binary; sampled files unstructured (e.g. `ainavdata_32769.dat`) |
| `db` (Particles.pk2) | 1 | 23.3 MB | name/string table referencing `.ddj`; layout unverified |
| `scc` | 17 | 15.6 KB | no structure identified |
| `msf` | 2 | 350 B | no structure identified |
| `skilldata_*enc.txt` | 7 | ~27 MB | client-encrypted skill tables; no key. The plaintext `skilldata_*` equivalents exist and are cataloged. |

## 7. Summary

- Real data in Android-consumable form (committed): prior ~7,755 textures/audio +
  23 `.hg` + `regions.tsv` + 21 textdata TSVs (Phase 11) + **663 worldmap
  textures (WebP: 632 `map_world_` tiles + 31 named) + 50 OGG + 431 WAV** with
  provenance manifests (`TEXTURE_CONVERSION_MANIFEST.tsv`,
  `AUDIO_CONVERSION_MANIFEST.tsv`) (Phase 12 + Phase 13 Part C) + **Phase 17
  real object assets** (`game/world/objects/`: 6 MSH1 + 6 PNG + models/placements)
  + **Phase 18 character assets** (`game/world/characters/bandit/`: skeleton.json,
  3 MSH v2 + 3 PNG, anims.tsv + 2 anim JSON, npc_placements.tsv, provenance.json)
  + **Phase 20 character runtime** (`game/world/characters/`: shared store
  355 skel / 1585 mesh / 655 tex / 2300 anim + 473 NPC manifests + player +
  `index.tsv` + `coverage.json`).
- Formats fully decoded: **16** (wav, ogg, tga, tmp, txt, ifo, ini, c, vsh, psh,
  ddj, m, o2, ban, **bsk, bsr** — bsk/bsr via committed Phase 18 decoders).
- Formats with a committed decoder for a proven subset: **3** (nvm, bms, efp —
  bms now includes the proven per-vertex skin block).
- Formats decoded at sample level (magic verified), decoder pending: **8**
  (t, o, bmt, cpd, dof, mfo, 2dt, sfk).
- Formats fully unknown: **4** (`dat`, `db`, `scc`, `msf`) + encrypted client
  skill tables (7 files; plaintext equivalents exist).
