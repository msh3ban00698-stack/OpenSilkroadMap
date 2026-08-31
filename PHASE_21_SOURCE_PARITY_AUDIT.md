# PHASE 21 — SOURCE PARITY AUDIT

Branch: `260830-feat-phase20-data-driven-character-runtime` (audit run on top of Phase 20)
Date: 2026-08-31
Type: AUDIT ONLY. No feature work, no refactor, no deletion, no invention.

## Verdict (spec §14 rule)

**PARITY NOT YET PROVEN.**

The Android project is a faithful *data* port for a proven subset of vSRO 1.193
assets (character models, skeletons, animations, minimaps, terrain samples,
object meshes, text tables). It is **not** a faithful port of the original
*gameplay* — the original game-logic source (client/server engine code, formulas,
network protocol, database schema) is not available in this workspace, so
gameplay parity cannot be proven from data alone.

---

## 0. Classification legend (spec §3)

| Code | Meaning |
|---|---|
| A — PORTED | Functionally implemented end-to-end (data → parser → runtime object), with executed-test evidence where the toolchain allows. Device runtime still NOT EXECUTED for every system (see §Q). |
| B — PARTIAL | A proven subset works; parity incomplete. |
| C — STUB | Placeholder / interface only. |
| D — DATA-ONLY | Data exists (decoded/committed) but no runtime consumes it for gameplay. |
| E — DEAD | Code exists but is unreachable/unused. |
| F — MISSING | No Android equivalent. |
| G — UNKNOWN | Insufficient evidence. |

A is reserved for pipelines whose *behavior is actually exercised* (Python tests
execute here; Java is compile-checked only). No classification anywhere converts
"compiles" into "works" (spec §12).

---

## A. Original source inventory

What is actually available in `/workspace` (and `/tmp/opencode`, outside git):

| Material | Location | Status |
|---|---|---|
| `Data.pk2` (66,051 files) | `/tmp/opencode/pk2raw/` | Listed + partially extracted |
| `Map.pk2` (19,171 files) | `/tmp/opencode/pk2raw/` | Listed + partially extracted |
| `Media.pk2` (29,591 files) | `/tmp/opencode/pk2raw/` | Fully extracted |
| `Music.pk2` (50 files) | `/tmp/opencode/pk2raw/` | Fully extracted |
| `Particles.pk2` (4,768 files) | `/tmp/opencode/pk2raw/` | Fully extracted |
| `pk2_mate` reader | `/tmp/opencode/pk2_mate` | Pinned, reproducible |
| Server package (`Vietnam-R v193 Package Server.7z`) | `/tmp/opencode/…` | Inventoried only |
| Database (`Database.7z`, SQL `.Bak` ×4) | `/tmp/opencode/…` | **NOT restored/opened** |
| Client binaries (`GameClient.exe`, DLLs) | `/tmp/opencode/…` | **NOT executed/disassembled** |
| Memory offsets (`Offsets.txt`) | `/tmp/opencode/…` | Not a packet spec |

**Available and decoded/derived (the actual parity basis):**

- 119,631 PK2 files across 5 archives (5.7 GB), per-format census in
  `COMPLETE_SOURCE_INVENTORY.json`.
- 159 server `textdata` tables (UTF-16LE/cp949/UTF-8) → 21 normalized TSVs.
- 839 Lua quest/event scripts + `.sct` (server package) — **inventoried, not decoded**.
- 126 `SR_GameRefData/*.txt` game tables (server package) — **inventoried, not decoded**.
- `server.cfg` / `proxy_cfg.ini` / `Certification.xml` — reference configs only.

**NOT available (blocks gameplay parity):**

- Original C++ source / headers / `.pdb` for client or server. Only compiled
  `GameClient.exe`, `SR_GameServer.exe`, DLLs exist.
- Network protocol: packet layouts, opcode dictionary, encryption (offsets file
  is memory addresses, not packets).
- Database schema: `SRO_*.Bak` are unopened; table structures unknown.
- Gameplay formulas/rules: EXP, damage, defense, attack/move speed, drop rates,
  item plus/grades, silk/premium, starting state — these live in compiled game
  logic and the DB, **not** in the decoded data files.

> Section 1 interpretation: the original **data** baseline is available and
> heavily decoded; the original **source-code** baseline (engine/game logic) is
> **unavailable**. The audit below is therefore complete on the data side and
> honestly `UNKNOWN`/`MISSING` on the source-logic side.

---

## B. Android inventory

### B.1 Native Java (`android/app/src/main/java`, 43 classes)

- `com.opensilkroadmap.app.minimap` (11): `NativeMinimapRenderer`, provider,
  resolver, parser, decoder — Phase 8.
- `com.opensilkroadmap.app.game` (12): `GameLoop`, `Camera2D`, `PlayerState`,
  `Entity`, `WorldGrid`, `RegionCatalog`, `RegionInfo`, `GameDataCatalog`,
  `GameHudView`, `GameActivity`, `MainActivity`.
- `com.opensilkroadmap.app.data` (10): `NpcPosTable`, `NpcSpawnIndex`,
  `LevelDataTable`, `LevelGoldTable`, `QuestDataTable`, `WorldMapInstanceTable`,
  `RefShopGoodsTable`, `TeleportDataTable`, `TsvTable`, `GameDataCatalog`.
- `com.opensilkroadmap.app.world` (13): `NativeWorldRenderer`, `CharacterCatalog`,
  `CharacterMeshIndex`, `StaticMeshAsset`, `MeshObjectIndex`, `Pose`,
  `CharacterRenderer`, `WorldTerrainIndex`, `WorldTerrainSet`, `TerrainHeightGrid`,
  `WorldProjection`, `WorldRegion`, `WorldCoordinates`.

### B.2 Committed game assets (`android/app/src/main/assets/game/`)

- `regions.tsv` — 72 sections, 3,468 cells (from real `RegionInfo.txt`).
- `textdata/` — 21 datasets (`npcpos`, `leveldata`, `levelgold`, `questdata`,
  `refshop*`, `teleport*`, `worldmap_*`, `regioncode`, `gameworld*`,
  `characterdata`/`itemdata`/`skilldata` as **index manifests**).
- `world/characters/` — shared store (skel 355 / mesh 1585 / tex 655 / anim 2300),
  473 NPC manifests + 1 player manifest, `index.tsv`, `coverage.json`.
- `world/objects/` — 6 MSH1 meshes + 6 PNG + placements (Phase 17 sample).
- `world/*.hg` — 23 terrain height grids (Phase 10).

### B.3 Web prototype (`map/src/game/`, ~40 TS modules)

Three.js/WebGL single-player prototype: flow/login/create, `game3d.ts`, character
rig + look, joystick, HUD, inventory/shop/party/teleport/warehouse panels, skill
bar, quest runtime. This is a **separate implementation** from the native path
(see §H). Its `map/public/assets/gamedata/{items,names}.json` are empty `{}`.

### B.4 Pipeline (`scripts/`, ~120 Python modules)

PK2 reader/validator/inventory, DDS/DDJ decode, audio/minimap/textdata/terrain/
object/character converters, `bsk`/`bsr`/`bms`/`ban`/`nvm`/`efp`/`o2` decoders,
`animation_pose`, `build_character_catalog/manifest`, and 40+ test suites.

---

## C. Complete parity matrix

Machine-readable copy: `PHASE_21_PARITY_MATRIX.tsv` (one row per system).

| System | Status | Evidence (Android) |
|---|---|---|
| Account / character creation | F — MISSING | web mock (`storage.ts`); no server/DB |
| Character stats | F — MISSING | `characterdata.tsv` index manifest only |
| EXP / level progression | D — DATA-ONLY | `leveldata.tsv` 150 rows + `LevelDataTable`; no runtime |
| SP / skills | F — MISSING | `skilldata.tsv` index; `*enc` encrypted |
| Inventory | F — MISSING | web panel only |
| Items | F — MISSING | `itemdata.tsv` index manifest only |
| Item grades / + system | F — MISSING | server-side; no source |
| Item attributes | F — MISSING | itemdata not decoded |
| Item drops | F — MISSING | server-side; no source |
| Starting items | F — MISSING | web 7 starter items, not source-verified |
| Silk / premium currency | F — MISSING | server-side; no source |
| NPCs | B — PARTIAL | 473 NPC models + spawns; 2D render, no AI |
| NPC AI | F — MISSING | none |
| Player model | B — PARTIAL | chinaman PARTIAL (BSR mismatch, no spawn) |
| Player movement | F — MISSING | web joystick only |
| Player combat | F — MISSING | none |
| NPC combat | F — MISSING | none |
| Monsters | B — PARTIAL | mob models converted; no AI/combat |
| Spawn system | B — PARTIAL | `npcpos` → `NpcSpawnIndex` → renderer placement |
| Character animations | B — PARTIAL | `.ban` full decode + pose; playback not device-run |
| NPC animations | B — PARTIAL | same data-driven pipeline |
| BSK/BMS/model formats | A — PORTED | decode+convert+load, 473 NPCs |
| Equipment rendering | F — MISSING | no equipment system |
| Weapons | F — MISSING | no equipment system |
| Armor | F — MISSING | no equipment system |
| Character skins | F — MISSING | none |
| Effects | F — MISSING | `efp` partial decode, no runtime |
| Maps | B — PARTIAL | minimap + world map + terrain samples; no full 3D |
| Terrain | B — PARTIAL | `.m` decoded, 23/4491 grids |
| World sectors | B — PARTIAL | `regions.tsv` + `RegionCatalog`/`WorldGrid` |
| Collision | F — MISSING | `nvm` partial decode, no runtime |
| Camera | B — PARTIAL | `Camera2D` generic follow/clamp (not authentic) |
| Input | F — MISSING | native none; web joystick |
| UI | B — PARTIAL | `GameHudView` native + web HUD |
| Shops | D — DATA-ONLY | `refshop*` decoded; parser dead; no runtime |
| Storage | F — MISSING | web panel only |
| Quests | D — DATA-ONLY | `questdata.tsv`; parser dead; Lua not decoded |
| Party | F — MISSING | none |
| Guild | F — MISSING | none |
| Chat | F — MISSING | none |
| Trade | F — MISSING | none |
| Skills | F — MISSING | index only; enc blocked |
| Buffs / debuffs | F — MISSING | none |
| Status effects | F — MISSING | none |
| Networking | F — MISSING | none |
| Server communication | F — MISSING | none |
| Game loop | C — STUB | `GameLoop` fixed-dt; real tick UNKNOWN |
| Timing | G — UNKNOWN | authentic tick rate unknown |
| Randomness / RNG | F — MISSING | none |
| Formulas | G — UNKNOWN | no source |
| Damage calculation | F — MISSING | none |
| Defense calculation | F — MISSING | none |
| Movement speed | F — MISSING | no source values |
| Attack speed | F — MISSING | no source values |
| Spawn / despawn | F — MISSING | none |
| NPC / player interaction | F — MISSING | none |
| Audio | D — DATA-ONLY | 50 ogg + 431 wav converted; no playback |
| Localization | D — DATA-ONLY | textdata UTF-16 → TSV |
| Configuration | D — DATA-ONLY | server.cfg inventoried; not runtime |
| Save / load | F — MISSING | web localStorage; no native |
| Database / persistence | F — MISSING | none |
| Security / validation | F — MISSING | none |
| Minimap (extra) | B — PARTIAL | native provider+renderer wired, not device-run |
| Object mesh rendering (extra) | B — PARTIAL | 6 real MSH1 meshes, 2D canvas |

**Rollup (64 systems):** A=1 · B=13 · C=1 · D=6 · E=0 · F=41 · G=2.
No gameplay system is PORTED.

---

## D. Missing systems

All `F — MISSING` rows above (41): account/character creation, character stats,
SP/skills, inventory, items, item grades/attributes/drops, starting items, silk,
NPC AI, movement, combat, equipment rendering, weapons/armor/skins, effects,
collision, input, storage, party, guild, chat, trade, skills, buffs/status,
networking/server, RNG, damage/defense/move/attack formulas, spawn/despawn
lifecycle, interaction, save/load, database, security.

## E. Partial systems

The 13 `B — PARTIAL` rows: NPCs, player model, monsters, spawn system,
character/NPC animations, maps, terrain, world sectors, camera, UI, minimap,
object rendering. Each is a proven data pipeline with an incomplete or unverified
runtime (2D flat canvas renderer, no AI, no combat, no dynamic lifecycle, no
device run).

## F. Stub systems

`GameLoop` (fixed-dt accumulator with catch-up cap; authentic VSRO timing
UNKNOWN). No other stub-level system.

## G. Dead code (evidence-backed)

- `QuestDataTable.java` — parses `questdata.tsv`; **never referenced** by any
  runtime class. HIGH confidence.
- `RefShopGoodsTable.java` — parses `refshopgoods.tsv`; **never referenced**.
  HIGH confidence.
- `LevelGoldTable.java` — parses `levelgold.tsv`; **never referenced**.
  HIGH confidence.
- `android/.../characters/bandit/` — superseded by the Phase 20 shared store,
  left in place (not deleted). HIGH confidence.
- Web game modules whose data feeds are empty `{}` (`shop_panel`, `quest_runtime`,
  `teleport_data`, `mobs_data`, `world_npcs` authentic spawns) are effectively
  unreachable for real data. HIGH confidence (broken links, see K).
- `map/src/game/data/*.json` starter data is web-only, not consumed by the native
  path. HIGH confidence.
- `scripts/generate_*` / `build_game_database.py` web-gamedata generator emits
  empty `{}` without `game_source`. MEDIUM confidence (superseded by `build_*`
  converters for native assets).

Per spec §10, nothing is deleted.

## H. Duplicate code

- **Two parallel game stacks**: the web prototype (`map/src/game/*`: combat,
  inventory, skills, quests, party, shops, movement, camera) and the native
  Android stack (`com.opensilkroadmap.app.*`: minimap, terrain, data tables,
  character/object rendering). Functionally overlapping (camera, minimap, world,
  player, NPC) with **no shared code**. HIGH confidence.
- Overlapping data-table parsers: generic `TsvTable` plus one dedicated table
  class per dataset (`NpcPosTable`, `LevelDataTable`, …). LOW–MEDIUM confidence
  (by design; not yet flagged for removal).
- Multiple `extract_*`/`generate_*` scripts (early Phases 5–8) now shadowed by
  newer `build_*`/`convert_*` scripts (Phases 10–20). MEDIUM confidence; needs a
  reference-count pass before any removal.

---

## I. Missing assets (asset parity, spec §6)

Original → committed Android, per family:

| Family | Original | Converted | Missing | Notes |
|---|---:|---:|---:|---|
| Skeletons `.bsk` | 1,039 | 355 (characters) | 684 | non-character skeletons excluded |
| Meshes `.bms` | 22,948 | 1,585 (char) + 6 (objects) | 21,357 | static+skinned character subset only |
| Textures `.ddj` | 47,495 | ~8,410 | ~39,085 | minimap 7,737 + char 655 + samples |
| Animations `.ban` | 4,796 | 2,300 (character clips) | 2,496 | 2 `JMXVBAN 0101` unproven |
| Character models `.bsr` | 7,549 | 474 (473 NPC + player) | 7,075 | 3 not-character; rest non-char props |
| Terrain `.m` | 4,491 | 23 `.hg` | 4,468 | |
| Tiles `.t` | 4,989 | 0 | 4,989 | PARSEABLE, no decoder |
| Overlays `.o`/`.o2` | 8,839 | 6 meshes (o2 sample) | 8,833 | |
| Navmesh `.nvm` | 6,041 | 0 | 6,041 | partial decode |
| Particles/effects `.efp` | 3,395 | 0 | 3,395 | partial decode |
| Audio `.wav`/`.ogg` | 2,885/50 | 431 wav + 50 ogg | 2,454 wav | |

Duplicates: shared store dedups byte-identical assets (e.g. `ChinaEtc_IslamMan.bsr`
== `chinaetc_islamman.bsr`, one key). Unused-converted: audio (no player), most
textdata (no consumer), object meshes (render-only, no gameplay).

## J. Unused assets

- All 431+50 converted audio files — no Android playback path.
- Most `textdata/` TSVs — parsed by Java tables but no gameplay consumer.
- `world/objects/` meshes — rendered but not part of any gameplay system.

## K. Runtime wiring gaps (spec §9)

End-to-end chains that are **proven** (data → parser → runtime → render):

- Minimap: `ddj → PNG → ManifestResolver → BitmapAsset → NativeMinimapRenderer`.
- Character: `bsr/bsk/bms/ban/ddj → MSH/skeleton/anim/PNG → CharacterCatalog +
  CharacterMeshIndex → NativeWorldRenderer`.
- Terrain: `m → .hg → WorldTerrainIndex/Set → renderer`.
- Object: `o2 → ifo → bsr/bms/bmt/ddj → MSH1 → MeshObjectIndex → renderer`.
- Spawn placement: `npcpos → NpcSpawnIndex → NativeWorldRenderer` (markers).

Broken links:

- `itemdata`/`characterdata`/`skilldata` → index manifest only → **no game system**.
- `questdata`/`refshopgoods`/`levelgold` → dedicated table classes exist but are
  **unreferenced (DEAD)** → no runtime consumer.
- `leveldata`/`teleportdata`/`worldmap_instanceinfo` → loaded into `GameDataCatalog`
  but only surfaced as HUD status; **no EXP/teleport/worldmap gameplay**.
- `npcpos` → placement works; → AI/gameplay **missing**.
- Audio → converted → **no player/consumer**.
- `gamedata/*.json` → empty `{}` → web shop/quest/teleport/spawns **non-functional**.
- Lua quest/event scripts + `SR_GameRefData` → **not decoded, not wired**.
- `nvm` → partial decode → **no collision/nav runtime**.
- `efp` → partial decode → **no effects/particles runtime**.

---

## L. NPC / player / animation coverage (spec §7)

- **NPC**: 473 PROVEN models, 1 PARTIAL (karkadann), 3 UNKNOWN (not characters),
  resolved from `characterdata col1→col52`; 1,089 refids → model keys. Not a
  single-NPC demo. Rendering is generic/data-driven. AI/interaction absent.
- **Player**: `chinaman` PARTIAL — mesh/skeleton/anim proven, BSR→skeleton
  mismatch + no static spawn.
- **Animation**: 2,300 clips, full keyframes, looping + channel space proven;
  pose evaluation + Java `Pose`/`CharacterRenderer`. 2 `JMXVBAN 0101` clips UNKNOWN.
  Runtime playback clock not device-verified.

## M. Starting-account-state verification

**NOT VERIFIABLE from available source.** No character-creation rules exist in the
decoded data; the SQL backups are unopened; no server logic is present. The web
prototype bundles 7 starter items (Phase H) that are **not** source-parity-verified.
Status: `UNKNOWN` (requires server source/DB, which are absent).

## N. Item / Silk / plus-system verification

**NOT VERIFIABLE.** `itemdata*.txt` is indexed (not decoded); silk/premium and the
`+1/+2/+3` plus system are server/DB concepts absent from the decoded data.

## O. EXP / progression verification

**DATA-ONLY.** `leveldata.tsv` (150 levels) and `levelgold.tsv` are decoded and
committed; the actual EXP formula and reward application live in absent server
logic. The web 150-level curve is marked tuning, not source.

## P. Map / world coverage

Minimap: complete for its category (7,737 PNGs, 96.5% RegionInfo cell coverage).
World map: `world.pmtiles` + dungeon minimaps. Terrain: 23/4,491 grids. Full
3D world, buildings, and navmesh are not rendered natively.

## Q. Build / runtime limitations (spec §12)

- **JDK 17 present** (javac compile-check done for the Java subset). **No Gradle,
  no Android SDK, no emulator/device.** Therefore:
  - APK build: **NOT EXECUTED.**
  - JVM unit tests: **NOT EXECUTED** (no JUnit jar; compile-only).
  - Instrumented/device tests: **NOT EXECUTED.**
- Python tests execute here and are the only runtime evidence.

## R. Exact blockers preventing 1:1 parity

1. **No original source code** (client/server engine, formulas, protocol, DB schema).
2. **No Gradle/Android SDK/device** → no APK build or device verification.
3. **Encrypted skill tables** (`skilldata_*enc.txt`) — no key.
4. **UNKNOWN formats**: `dat` (79), `db` (1), `scc` (17), `msf` (2).
5. **PARSEABLE-not-decoded formats**: `t` (4,989), `o` (4,491), `bmt` (4,269),
   `cpd`, `dof`, `mfo`, `2dt`, `sfk`.
6. **Partial decoders**: `bms` skin tail, `nvm` semantics, `efp` commands.
7. **BSK/BSR semantics**: `bone_type`, BSR 8×u32 header, child-bone inverse-bind.
8. **Player** BSR→skeleton mismatch; no static spawn.
9. **Karkadann** triangle-section parse (1 PARTIAL model).
10. **No gameplay runtime**: AI, combat, skills, quests, shops, audio playback,
    networking, persistence, save/load.

## S. Prioritized implementation plan

1. **Toolchain**: obtain Gradle + Android SDK + emulator; execute existing JVM and
   instrumented tests; build + install the debug APK; verify the WebView/native
   boot on a device. (Unblocks §Q and the "not device-verified" caveat on every
   PORTED/PARTIAL row.)
2. **Data completeness**: decode `t`/`o`/`bmt`/`cpd` to finish terrain/overlay/
   material; complete `bms` skin tail; finish `nvm` and `efp` semantics.
3. **Runtime wiring**: wire decoded `textdata` (leveldata, npcpos, questdata,
   refshop, itemdata once decoded) into native systems; wire or remove the dead
   table classes (`QuestDataTable`, `RefShopGoodsTable`, `LevelGoldTable`); add
   audio playback; add a real 3D renderer to replace the 2D canvas.
4. **Gameplay**: NPC AI, movement, combat, skills, quests — only after a
   source/DB is obtained to derive authentic formulas; otherwise mark UNKNOWN.
5. **De-dup**: consolidate the web prototype vs native stack; retire `bandit/`;
   prune obsolete `extract_*`/`generate_*` scripts after a reference-count pass.

**Blocked** on the same two external dependencies as prior phases: the original
game-logic source/DB and a Java/Android toolchain. Neither exists in this workspace.

---

*This audit makes no code changes and deletes nothing (spec §15).*
