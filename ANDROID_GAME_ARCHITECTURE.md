# Android Game Architecture

VSRO v1.193 → completely Android-native game — architecture + feasibility analysis.

Status: ANALYSIS ONLY. No gameplay implementation, no Android conversion, no server
implementation, no binary execution, no full PK2 extraction, no unnecessary large-file
generation. This document is a plan; the codebase is unchanged.

Verification conventions:
- **VERIFIED** — confirmed by an actual file, `7z l`/`unrar l` listing, parser source,
  or committed repo file in this workspace.
- **DOCUMENTED BUT NOT CURRENTLY VERIFIED** — a doc/listing says it exists, but the
  archive/file cannot be inspected in this session.
- **UNKNOWN / NEEDS SOURCE** — no supporting file exists anywhere in the workspace.
- **INFERRED** — reasonable reading of verified data, explicitly labelled; not treated
  as fact.
- **NOT VERIFIED** — claimed somewhere but not confirmed.

Every claim below is traceable to: the PK2/client/server listings under
`/tmp/opencode/listings/*.txt`, `VSRO_V193_SOURCE_INVENTORY.md`,
`EXTERNAL_PACKAGE_INVENTORY.md`, `GAME_CONTENT_VERIFICATION.md`, the Phase B–H docs, the
`map/src/game/*` sources, `scripts/*.py`, or the Android wrapper sources.

---

## 1. Final Product Goal

A completely **Android-native** game built only from the provided VSRO v1.193 source
material.

- The game itself runs fully on Android. No Windows EXE/DLL is executed on Android.
- The Windows EXE/DLL + SQL Server stack is **not** the runtime of the Android game.
- Phase 1 target: **offline / local play** with no server, no SQL Server, no
  GameServer/AgentServer/GatewayServer/ShardManager.
- Phase 2 (later, only when the Android game is mature): an **online backend** for
  public players, added without rewriting the game.
- Direction is conceptually like Silkroad Origin Mobile: Android game first, online
  infrastructure later.

Source of truth: the provided VSRO files. Nothing is invented. Everything not verifiable
from those files is marked UNKNOWN / NEEDS SOURCE or NOT VERIFIED.

### What "Android-native" means here

This workspace already contains a **web** game (Vite + Three.js + OpenLayers) wrapped in
a Capacitor **WebView** (`capacitor.config.ts`, `android/app/.../MainActivity.java`,
`ANDROID_APK_BUILD.md`). A WebView is not a native game engine.

The goal document does **not** say "port the existing web game". It says build a
**completely Android-native** game. That is a distinct decision that must be made
explicitly (see §7). This document does not silently assume either path; it lays out what
each requires against the real assets.

---

## 2. Verified Source Inventory

### 2.1 Source material actually in the workspace (VERIFIED)

| Item | Where | Evidence |
| --- | --- | --- |
| `PK2_Files.7z` (1,546,426,717 B) | `/tmp/opencode/PK2_Files.7z` | `listings/pk2.txt`; `7z l` shows 4 PK2s |
| `Data.pk2` (3,351,891,968 B) | inside `PK2_Files.7z` | `listings/pk2.txt` |
| `Map.pk2` (1,268,441,088 B) | inside `PK2_Files.7z` | `listings/pk2.txt` |
| `Music.pk2` (76,488,704 B) | inside `PK2_Files.7z` | `listings/pk2.txt` |
| `Particles.pk2` (178,126,848 B) | inside `PK2_Files.7z` | `listings/pk2.txt` |
| `Media.pk2` (823,066,624 B) | inside `VSRO-R Client.7z` | `listings/client.txt:26` |
| `VSRO-R_Client.zip` (213,646,487 B) | `/tmp/opencode/VSRO-R_Client.zip` | `listings/mediafire_zip.txt`; extracted to `/tmp/opencode/vsro_pkg/VSRO-R Client/` |
| Nested archives (Server.7z, Database.7z, Proxy.rar, Event.7z, 2 patchers, 2 txt) | `/tmp/opencode/vsro_pkg/VSRO-R Client/` | `listings/{server,database,event,proxy,gspatcher,clientpatcher,mediafire_zip}.txt` |
| Small config/text files (extracted, secrets redacted) | `/tmp/opencode/extract/` | this session's extraction logs |
| All listings | `/tmp/opencode/listings/` | file-name + size records |

Notable: **no `pk2reader.py` / `jmblowfish.py`** anywhere (repo or package).
**No `listing_media.txt` / `listing_music.txt`.**

### 2.2 Committed repository content (VERIFIED)

| Area | Evidence |
| --- | --- |
| Vite + OpenLayers + Three.js web app | `map/deno.json`, `map/src/{map.ts,main.ts}`, `map/src/game/*.ts` |
| Extraction/generation pipeline scripts | `scripts/*.py` (see §7) |
| Committed runtime assets | `map/public/assets/{world.pmtiles, 32785.pmtiles, npcs.json, teleports.json, regionnames.json, icons/, img/}` |
| Phase H starter JSON | `map/src/game/data/{level_progression,items,skills,masteries}.json` |
| Capacitor Android wrapper | `capacitor.config.ts`, `android/app`, `ANDROID_APK_BUILD.md` |
| Docs | `EXTERNAL_PACKAGE_INVENTORY.md`, `VSRO_V193_SOURCE_INVENTORY.md`, `GAME_CONTENT_VERIFICATION.md`, `PHASE_*.md`, `README.md` |

### 2.3 Inventory documentation status

- `EXTERNAL_PACKAGE_INVENTORY.md` — Phase A PK2 interior layout (file counts per
  archive, format headers, minimap grid). **DOCUMENTED BUT NOT CURRENTLY VERIFIED**:
  the PK2 interiors were re-listed this session; header checksums are from a prior
  session with a custom Blowfish reader (not present now).
- `VSRO_V193_SOURCE_INVENTORY.md` — this session's nested-archive inventory (A–H).
  VERIFIED at file/size level; PK2 interiors NOT re-walked.
- `GAME_CONTENT_VERIFICATION.md` — repo runtime truth table. VERIFIED against repo tree.

### 2.4 Relevant components identified

**Game client / runtime (repo):** Three.js 3D world (`game3d.ts`, `region_loader.ts`,
`character_rig.ts`, `character_loader.ts`), OpenLayers 2D map (`map.ts`), DOM UI/HUD
(`hud.ts`, `screens.ts`, `flow.ts`, panels), offline persistence (`storage.ts`).

**Data/config from package (server textdata + client):** item/skill/character/shop/
quest/teleport/region tables (UTF-16 TSV, in `SR_GameRefData/` of Server.7z and
`server_dep/silkroad/textdata` of Media.pk2 per Phase A), server `*.cfg`,
`Certification.xml`, proxy `*.ini`.

**PK2 archives (all 5):** Data (meshes/animations/sounds/navmesh/prim), Map (world
geometry `.t/.o/.o2/.m`), Media (minimaps, icons, UI, textdata), Music (ogg), Particles
(efp/ddj).

**Windows server stack (NOT the Android runtime):** 12 EXEs + SMPlugins DLLs + SQL
backups + proxy + patchers — inventory only (§5).

### 2.5 Verified vs documented-only summary

- VERIFIED on disk now: all 5 PK2 file entries (name+size), client/server/DB/proxy/
  event/patcher nested listings, repo tree, redacted configs, committed assets.
- DOCUMENTED BUT NOT CURRENTLY VERIFIED: PK2 interior file counts/layout (Phase A),
  format header bytes for `.t/.o/.o2/.m` JMX strings, Media.pk2 textdata file set.
- UNKNOWN / NEEDS SOURCE: `pk2reader.py`, SQL schemas, packet/opcode meanings, monster
  stat derivation tables, drop tables, quest flow logic beyond text.

---

## 3. Available Game Assets/Data

Asset categories from the actual listings and repo. **Verified** = listed in this
session or present in the repo tree; **DOCUMENTED** = Phase A/listing claim not
re-inspected now.

### 3.1 Maps / terrain

| Asset | Source | Status | Notes |
| --- | --- | --- | --- |
| World minimaps (`<X>x<Y>.ddj`, 5,523) | Media.pk2 `/minimap` | DOCUMENTED | Phase C consumed 5,523 tiles; repo ships `world.pmtiles` (44,660,581 B) |
| Dungeon minimaps (`minimap_d`, 2,214) | Media.pk2 | DOCUMENTED | 8 folders (Arabia, donwhang, egypt, flame, fort, jinsi, jupiter, donwhang_event) |
| Region geometry `.t/.o/.o2/.m` (17,000+) | Map.pk2 | DOCUMENTED | Headers `JMXVMAPT1001` etc.; no general tooling (EXTERNAL §6) |
| `navmesh` (`nvm`, `ainavdata`, `.dof`) | Data.pk2 | DOCUMENTED | 6,041 nvm + 27 ainavdata; dungeon `.dof` 34 |
| Committed 3D regions 1–9 + 32785 | repo `img/silkroad/game/region*` | VERIFIED | `mesh.json`, `floor.webp`, buildings/atlas; 32785 dungeon-only |

### 3.2 Meshes / models / characters / actors

| Asset | Source | Status | Notes |
| --- | --- | --- | --- |
| `prim/{mesh,skel,ani,mtrl,snd,lightmap}` (52,085 files) | Data.pk2 | DOCUMENTED | BMS 22,684 · BAN 4,691 · BSK 1,039 · BMT 4,269 · BSR 7,549 · ban 4,691 |
| `res` (7,575), `compound` (162), `dungeon` (35), `water` (30), shaders | Data.pk2 | DOCUMENTED | |
| chinaman_fighter rig (41 bones, 16 meshes, 6 anims) | repo `img/silkroad/game/character/chinaman_fighter/` | VERIFIED | `meta.json` height 15.945 |
| 19 actor folders (wolf, baroi, dowb, kyklopes, lion, barpolle + 13 NPC roles) | repo `img/silkroad/game/actor/` | VERIFIED | `extract_actors.py` output |
| Character visual change / appearance tables | Server.7z `SR_GameRefData/CharacterVisualChange.txt` | VERIFIED (listing) | content not parsed |

### 3.3 NPCs / monsters

| Asset | Source | Status | Notes |
| --- | --- | --- | --- |
| NPC/mob templates `CharacterData_*.txt` (10 files) | Media textdata / Server.7z `SR_GameRefData/` | DOCUMENTED / VERIFIED (listing) | Phase A: 10 in Media; Server.7z lists 13 CharacterData files |
| Spawn positions `npcpos.txt` (1,095,280 B) | Server.7z `SR_GameRefData/npcpos.txt` | VERIFIED (listing) | content parsed only in prior Phase A |
| Mob/NPC names + spawns in repo | `npcs.json`, `chars.json`, `spawns.json` | VERIFIED (`npcs.json`); `chars.json`/`spawns.json` ABSENT (only `{}` items/names) | |
| Authentic mob stats | — | **UNKNOWN / NEEDS SOURCE** | no verified stat table; repo mob stats are tuning |

### 3.4 Items / skills / effects / particles

| Asset | Source | Status | Notes |
| --- | --- | --- | --- |
| Item tables `ItemData_*.txt` (10 files, up to 5,966,376 B) | Server.7z `SR_GameRefData/` | VERIFIED (listing) | content not parsed this session |
| Skill tables `SkillData_*.txt` (8) + `SkillMasteryData.txt` + `skilleffect.txt` | Server.7z | VERIFIED (listing) | 66-col skill rows parsed by `build_game_database.py` |
| Starter items (7) + skills + masteries JSON | repo `map/src/game/data/` | VERIFIED | from Phase H `generate_phase_h_data.py` |
| Full `gamedata/{items,skills_full,quests,shops,spawns,chars,teleports_full,levels}.json` | generated, NOT present | **ABSENT** | would need `game_source/` + `pk2reader` |
| Skill/icon webp library (4,476) | repo `img/silkroad/icons/` | VERIFIED | reachable only via item→icon mapping (missing) |
| Particles | Particles.pk2 `/animations` (4,768 files) | DOCUMENTED | `.efp` 3,395 · `.ddj` 1,000 · `.bms` 264 |
| Effects (sound/anim references) | Data `prim/snd`, `effectsound.txt` | DOCUMENTED / VERIFIED (listing) | |

### 3.5 Audio / UI / localization / tables

| Asset | Source | Status | Notes |
| --- | --- | --- | --- |
| BGM `.ogg` (50 tracks) | Music.pk2 | DOCUMENTED | `ARABIA_*`, `egypt_*`, `jangan_town`, `jupiter_*`, etc. |
| Audio in repo | — | **ABSENT** | no `assets/audio/` (GAME_CONTENT §6) |
| UI DDJs/PNG | Media.pk2 `/interface`,`/icon`,`/icon64`,`/res_ui` + 29,592 root DDJs | DOCUMENTED; repo has 45 PNGs | `extract_ui.py` needs listing files |
| Localization / text tables | `textdata_equip&skill.txt`, `textdata_object.txt`, `textquest_*.txt`, `textzonename.txt` (4,129 rows) | VERIFIED (repo `regionnames.json`; docs) | UTF-16, key col 2, English col 9 |
| Game config tables | `leveldata.txt`, `ref*.txt`, `shop*.txt`, `teleport*.txt`, `QuestData.txt` | VERIFIED (listing) | server textdata set |
| Event scripts | Event.7z `Event.sct`/`EventList.sct`; Server.7z `Script/VIETNAM*` lua/sct | VERIFIED (listing) | |

### 3.6 What is NOT available (verified)

- No `pk2reader.py`/`jmblowfish.py`.
- No `listing_media.txt`/`listing_music.txt`.
- No SQL schema (backups unopened).
- No packet/opcode spec.
- No verified monster stat / drop / loot tables (textdata has item/char templates; drop
  mechanics are server-side, UNKNOWN).
- No `navmesh_world.pmtiles`, no audio, no full `gamedata/`, only 1 of 13 dungeon pmtiles
  committed.

---

## 4. Verified Gameplay Systems

Classification key: VERIFIED / PARTIALLY VERIFIED / INFERRED / UNKNOWN / NEEDS SOURCE.
"VERIFIED" here means the **data needed to implement it** exists in the package/repo —
not that a complete implementation ships today.

| System | Class | Evidence / notes |
| --- | --- | --- |
| Character creation | PARTIALLY VERIFIED | Class names VERIFIED (textdata); 6 classes; Warlock/Bard have no skill data (skills.json). Appearance colors are repo-inferred (screens.ts). No verified character-creation rules/stat allocation. |
| Movement / navigation | PARTIALLY VERIFIED | Real 41-bone rig + walk/run/attack anims VERIFIED (Phase F). World bounds/regions VERIFIED (regions.ts). Pathing/graph **UNKNOWN** (NavLink data absent). |
| Camera | INFERRED | Camera-relative follow/orbit implemented in repo; no VSRO camera spec in source. |
| Combat | PARTIALLY VERIFIED | Real attack anims + dummy target (Phase F). Damage/HP/MP formulas are **repo tuning** (game3d.ts, skill_data.ts). No verified combat tables. |
| Skills | PARTIALLY VERIFIED | Skill codes/names/reqLevel/sp/mp/cooldown/icon VERIFIED in `skilldata_*.txt` (66 cols). Damage/heal **UNKNOWN** (skilleffect.txt not parsed; server computes damage). |
| Inventory / equipment | INFERRED | No VSRO inventory layout in provided files (client-exe internal). Repo panel is custom. |
| NPC interaction | PARTIALLY VERIFIED | NPC positions/templates VERIFIED (npcpos/characterdata). Dialog text VERIFIED (`npcchat.txt`, `textquest_speech&name.txt`). Interaction flow repo-inferred. |
| Quests | PARTIALLY VERIFIED | `QuestData.txt`, `questcontentsdata.txt`, quest text, reward tables (`RefQusetReward`, `RefQuestRewardItems`) VERIFIED (listing). Quest **logic** (conditions/objectives engine) **UNKNOWN** — text-only, server-side logic in SQL/scripts. |
| Monsters | PARTIALLY VERIFIED | Mob templates/positions VERIFIED. Stats/drops **UNKNOWN**. |
| Drops | **UNKNOWN / NEEDS SOURCE** | No drop/loot table verified. |
| Shops | PARTIALLY VERIFIED | `refshop.txt`, `refshopgoods.txt`, `shopitemdata.txt` etc. VERIFIED (listing). Shop UI in repo custom. |
| Character progression | PARTIALLY VERIFIED | Level curve VERIFIED (`leveldata.txt` 150 levels). Stat growth **UNKNOWN** (server-side). Masteries VERIFIED (`SkillMasteryData`, `learnablemastery`). |
| Party | PARTIALLY VERIFIED | Mercenary/COS concepts exist (CharacterData COS templates). Repo party is a 2-merc placeholder (party_data.ts) — **not** verified VSRO party. |
| Chat | INFERRED | Chat channels/colors exist in offsets doc (GameClient memory) but that's **not** a protocol. Repo has no chat. |
| World/map loading | PARTIALLY VERIFIED | Minimap/geometry/tiles VERIFIED; pmtiles pipeline works. Full world continuity (streaming) **UNKNOWN**. |
| Effects | PARTIALLY VERIFIED | `skilleffect.txt` + Particles.pk2 exist. Runtime effect playback **UNKNOWN**. |
| Audio | PARTIALLY VERIFIED | 50 ogg BGM VERIFIED in listing. Runtime audio absent. |
| Save/load | PARTIALLY VERIFIED | Repo uses localStorage (offline, custom). VSRO server-side save schema **UNKNOWN**. |
| Teleport | PARTIALLY VERIFIED | `teleportdata/link/building` VERIFIED (listing). Repo `teleports.json` committed. |
| PvP / guild / union / arena / fortress / jobs / siege | **UNKNOWN / NEEDS SOURCE** | Only config flags (`server.cfg`, `proxy_cfg.ini`) and quest/ref rows; no logic source. NOT VERIFIED as implementable. |

Summary: the **data-rich** systems are map/world, character appearance/animation,
skills/items/progression, NPCs/positions, shops, quest text/rewards, teleports, audio.
The **logic-poor** systems (drops, damage, quest flow, party, PvP, guild) have no
verified implementation source and would be **new design**, not port.

---

## 5. Windows/Server Dependencies

All of the following are inventory-only. None run on Android. Nothing in this list is
part of the Android runtime.

### 5.1 Windows EXEs (VERIFIED in Server.7z listing)

`SR_GameServer.exe` (9,576,448 B) · `SR_ShardManager.exe` (5,062,656) ·
`GlobalManager.exe` (1,417,216) · `GatewayServer.exe` (1,028,096) ·
`AgentServer.exe` (929,792) · `FarmManager.exe` (901,120) · `MachineManager.exe`
(864,256) · `DownloadServer.exe` (864,256) · `smc.exe` (708,608) ·
`CertModule/Replace.Certification.exe` (25,600) · `luac.exe` · `helper.exe`.

### 5.2 Windows DLLs (VERIFIED in listing)

`ImageTrans.dll` (12,328,960) · `GFXFileManager.dll` · `ggauth.dll` · `XTrap4Server.dll`
· `MailSender.dll` · `VerData.dll` · `CommonGuiControl.dll` · `ServerFrameworkRes.dll` ·
`dbghelp.dll` · `SMPlugins/*.dll` (18 plugins: CAS, IPBlock, Notice, Security,
ServerControl, SR_* , User*, etc.). Client DLLs: `dbghelp.dll`, `edxSilkroadDll5.dll`,
`GFXFileManager.dll`, `msvcp60.dll` (Client.7z).

### 5.3 SQL Server

- `Database.7z` backups (VERIFIED listing): `SRO_CERTIFICATION.Bak` (3,957,248),
  `SRO_VT_ACCOUNT.Bak` (21,592,576), `SRO_VT_SHARD.Bak` (93,501,952),
  `SRO_VT_SHARDLOG.Bak` (3,705,344). NOT opened; schema UNKNOWN.
- `Certification.xml` points at SQL Server Express (`[REDACTED]\SQLEXPRESS`) with sa
  credentials (redacted). NOT applicable to Android runtime.

### 5.4 Windows services / proprietary runtime

- XTrap anti-cheat DLL (XTrap4Server.dll), ggauth, patchers (`Patcher.exe`,
  `ClientPatcher.exe`), proxy (`VSROProxy.exe`, `sr_proxy.dll`), `MachineManager`,
  `GlobalManager`, `FarmManager`, DownloadServer — all Windows service-ish components.
- Blowfish PK2 key `169841` documented; reader not present.

### 5.5 What must be REIMPLEMENTED as Android-native functionality

Because the Windows stack is not the runtime, any server-side logic the offline game
needs must be **reimplemented as a local Android subsystem** (single-player
authority) or marked UNKNOWN and designed fresh. Candidates:

| Windows behavior | Android replacement | Source availability |
| --- | --- | --- |
| Authentication / account | local account store (repo already does localStorage) | no server schema — new design |
| Character persistence | local DB (Room/SQLite) | new design |
| GameServer world authority | local game world / simulation | world data VERIFIED; server logic UNKNOWN |
| Monster AI / spawn / drops | local simulation | stats/drops UNKNOWN — new design |
| Combat math | local combat resolver | UNKNOWN — new design |
| Quest condition engine | local quest state machine | quest text/data VERIFIED; logic UNKNOWN |
| Party / chat / PvP | offline: n/a; online: future backend | UNKNOWN protocol |
| Billing/IBUV/certification | not needed offline | config-only |
| XTrap/ggauth anti-cheat | not needed offline; online: new security | new design |

---

## 6. Android Architecture

The proposed architecture separates concerns so the offline game is built first and an
online layer slots in later without a rewrite. It is **recommended**, not implemented.

```
┌──────────────────────────────────────────────────────────────────┐
│ UI LAYER (Jetpack Compose)                                      │
│  menus · HUD · inventory · quest log · chat · settings          │
├──────────────────────────────────────────────────────────────────┤
│ GAMEPLAY LAYER (Kotlin, platform-independent, unit-testable)    │
│  character · movement · combat · skills · inventory · quests    │
│  shops · progression · party · chat (offline = local sim)       │
│  GameEventBus <──> GameStateStore (single source of truth)      │
├──────────────────────────────────────────────────────────────────┤
│ RENDERING / GAME ENGINE LAYER                                   │
│  (see §7: Kotlin/JVM vs native)                                 │
│  world chunk manager · skinned mesh/animation · effects · audio │
├──────────────────────────────────────────────────────────────────┤
│ ASSET / DATA LAYER                                              │
│  normalized formats (glTF2/PNG/JSON/WebP/OGG) · pack index      │
│  streaming from APK assets → unpack → disk cache (mmap)         │
├──────────────────────────────────────────────────────────────────┤
│ LOCAL PERSISTENCE                                               │
│  Room/SQLite (characters, inventory, quests, world state)       │
│  preferences (settings) · save snapshots                        │
├──────────────────────────────────────────────────────────────────┤
│ INPUT / TOUCH LAYER                                             │
│  gesture recognizers · virtual joystick · tap/press/drag        │
├──────────────────────────────────────────────────────────────────┤
│ FUTURE NETWORKING LAYER (empty interface now, mock impl)        │
│  NetClient interface: send(req)/recv(evt) · session · reconnect │
│  Phase 2: real backend adapter (WebSocket/HTTP)                 │
└──────────────────────────────────────────────────────────────────┘
```

Key principles:
1. **Gameplay layer is a pure Kotlin library** with no Android/engine imports → runs
   logic in unit tests and can be shared with a future server if desired.
2. **GameStateStore is the single authority offline.** All systems read/write it.
   Later, a synchronizer mirrors it to the backend.
3. **Networking is an interface with a no-op/mock adapter** until Phase 2. Gameplay
   code calls `NetClient`; offline adapter answers locally.
4. **Assets are pre-converted offline** (§8); the device never reads PK2 or executes
   anything from the Windows package.
5. **Input is engine-agnostic** (gestures → intent), so joystick/gamepad both work.

### Persistence choice
Room/SQLite for entity state (characters, inventory, quest progress, world positions)
plus JSON snapshot for savegames. The current repo's localStorage approach is web-only
and not carried into the native game.

### Audio
Preconverted OGG/MP3 from Music.pk2 (VERIFIED 50 tracks). Android `MediaPlayer` /
`SoundPool` via an `Audio` interface. UI/SFX from Media `/interface`/`/icon` if listing
extraction becomes available.

### Future networking
`NetClient` interface only now. Phase 2 replaces the mock with a real adapter (see §10).
No original VSRO protocol is assumed.

---

## 7. Engine/Technology Decision

Constraint set (only these count):
- Assets are **VSRO proprietary formats** that must be converted to engine-neutral
  formats (PK2→DDJ/DDS→PNG/WebP; BMS/BAN/BSK/BMT→glTF2/skinned; Music→OGG; textdata→JSON).
- Target is **fully Android-native**, offline-first, later online.
- Repo already has a **Three.js web implementation** (Vite/TS). It is a WebView game,
  not native.
- No verified server logic — the game is single-player authority offline.
- Small team, docs-driven, must not depend on unavailable tools.

| Option | What it requires for the VSRO assets | Verdict |
| --- | --- | --- |
| **A. Keep Three.js/WebView (status quo)** | Reuse existing `game3d.ts`, `region_loader.ts`, character pipeline as-is; Capacitor WebView is the runtime. | ❌ NOT "completely Android-native". WebView perf/memory for a big open world is weak; contradicts the directive. Rejected for the goal. |
| **B. Kotlin + Android view system (Canvas/OpenGL via libGDX)** | Need converters to glTF2 + PNG (already the direction of the repo scripts). libGDX reads glTF via `gdx-gltf`. Textdata→JSON tables. Simple, proven on Android, offline-first friendly. | ✅ **Recommended** for feasibility + fidelity + small team. Java/Kotlin, no engine lock-in, real native APK, easy to unit-test gameplay layer. |
| **C. Kotlin + JetBrains Compose for desktop-games-style (Skia)** | Compose Multiplatform `ComposeCanvas`/Skia can render meshes but is built for UI; 3D is not its strength. | ⚠️ UI layer yes, 3D engine no. Not primary renderer. |
| **D. Godot 4 (Android export)** | GDScript + Godot scene format; write importers for BMS/BAN/BSK/BMT or reuse converted glTF2. Native Android export exists; good 3D. | ⚠️ Viable; adds engine dependency and GDScript; importers still needed. Heavier than B for the same asset problem. |
| **E. Unity/Unreal** | Strong 3D, but overkill licensing/size for this scale and would require same converters; popular-but-not-simpler. | ❌ Not justified by constraints. |
| **F. Custom Kotlin + OpenGL ES** | Full control; highest effort; all converters + engine from scratch. | ❌ Too much for an offline-first first milestone. |

**Decision (analysis, not implementation):** Option **B — Kotlin + Android app with
libGDX (or similar lightweight GLES framework) as renderer, Jetpack Compose for UI,
Room for persistence, and a pure-Kotlin gameplay library.** The PK2 pipeline already
converts toward neutral formats; glTF2 + PNG/WebP + JSON + OGG is the interchange. This
keeps the Android app native while staying small and testable. If later the team wants a
different engine, the converted neutral assets carry over — the conversion pipeline is
engine-independent (§8).

This is a **recommendation**. Nothing is implemented in this phase. If the team prefers
D (Godot), the same neutral-asset pipeline applies; only the runtime layer differs.

---

## 8. PK2 → Android Asset Pipeline

Existing pipeline (repo, VERIFIED) with a new Android tail. Stages labeled
EXISTS / MUST-BUILD.

```
 PK2 (Data/Map/Media/Music/Particles)
   │  [EXISTS] pk2read (external pk2reader.py, NOT in repo) + extract_world.py,
   │           extract_region(s).py, extract_ct.py, extract_actors.py, extract_ui.py,
   │           extract_icons.py, extract_audio_minimaps.py  ── requires pk2reader +
   │           listing_media.txt / listing_music.txt (MISSING)
   ▼
 game_source/  (gitignored; currently ABSENT in workspace)
   │  [EXISTS] convert_ddjs.py (DDJ→webp), generate_tiles.py, generate_pmtiles.py,
   │           generate_navmesh.py, generate_region_mesh.py / _ct / _regions.py,
   │           generate_game_data.py, generate_phase_h_data.py, build_game_database.py
   ▼
 map/public/assets/ (committed subset) + map/public/assets/gamedata/ (MUST-GENERATE)
   │  [EXISTS] world.pmtiles, 32785.pmtiles, npcs.json, teleports.json,
   │           regionnames.json, region1-9/, character/, actor/, icons/, ui/, env/
   │  [MUST-BUILD] gamedata/{items,chars,spawns,shops,quests,teleports_full,
   │                         skills_full,levels,names}.json  (build_game_database.py
   │                         run against real textdata)
   ▼
 NORMALIZED ANDROID PACK (MUST-BUILD)
   │  offline converter: merge pmtiles→chunk tiles, meshes→glTF2 (skinned),
   │  textures→PNG/WebP, textdata→JSON tables, music→OGG, build pack index
   ▼
 Android assets/ (packed, versioned) ── loaded via streaming unpack → mmap cache
```

Stage status:

| Stage | Status |
| --- | --- |
| PK2 archive access | BLOCKED (pk2reader absent, archives not extracted) |
| extract_* (PK2→game_source) | EXISTS (scripts) but unrun (no reader/source) |
| convert/generate (→webp/pmtiles/json) | EXISTS (scripts) |
| gamedata JSON (full) | MUST-BUILD (script exists, needs source) |
| Neutral interchange (glTF2/PNG/WebP/JSON/OGG) | MUST-BUILD (new converter) |
| Android pack + index | MUST-BUILD (new tooling) |
| Device-side streaming cache | MUST-BUILD (native loader) |

The existing pipeline is engine-neutral; adding a glTF2/neutral step does **not** require
touching the current Vite pipeline (kept intact for the web map). Proprietary archives
never enter the repo.

---

## 9. Offline-First Development Plan

Minimum viable offline Android game. No Windows server, no SQL Server, no EXE.

### 9.1 What the offline game must contain (from verified data)

- **World**: one or more regions from committed `region1-9`/`32785` geometry
  (VERIFIED assets) or converted Map/Media pk2 tiles once extracted.
- **Character**: real chinaman_fighter rig + walk/run/attack anims (VERIFIED).
- **Progression**: real 150-level curve + masteries + skill/items starter set
  (VERIFIED Phase H JSON).
- **NPCs**: positions + templates + dialog/name text (VERIFIED tables once extracted).
- **Shops/quests/teleports**: verified tables via `build_game_database.py`.
- **Save/load**: Room/SQLite.
- **Local authority**: gameplay layer simulates GameServer locally (single player).

### 9.2 Data that must be converted to local Android data

| Data | Source | Needed for |
| --- | --- | --- |
| Region meshes/textures | converted region assets / pmtiles | world rendering |
| Skinned character + anims | converted BSK/BMS/BAN/BMT | player + actors |
| Items/skills/masteries/levels | textdata → JSON | progression/skills |
| NPC/mob templates + spawns | characterdata/npcpos → JSON | NPCs/mobs |
| Shops/quests/teleports | ref/shop/quest/teleport tables → JSON | interactions |
| Names/text (localization) | textdata → JSON | UI |
| Music/audio | Music.pk2 → OGG | ambience |
| Region names | textzonename → JSON | world labels |

### 9.3 Out of scope for offline MVP (UNKNOWN / new design)

- Drops, exact combat math, monster AI, quest condition engine, party, chat, PvP,
  guild/union/arena/fortress — UNKNOWN source; designed later, clearly labeled.

### 9.4 Milestones (detail in §13)

M1 pipeline unlock (reader+listings) → M2 neutral conversion → M3 native renderer for
one region → M4 player+combat+inventory → M5 NPC/shop/quest → M6 full offline loop.

---

## 10. Future Online Backend Plan

DOCUMENTATION ONLY. Not implemented. Two separate truth columns.

### ORIGINAL VERIFIED INFORMATION (from package)

- Process topology (EXE list, `server.cfg` ports): 15880 (Gateway/Download/Farm/Machine
  certification), 15882 (Agent/Shard/Game), 32000 (GlobalManager), billing HTTP 8090
  (proxy `server.cfg`, `Certification.xml`).
- Proxy public/private ports: Gateway 5001/1337, Agent 5002/1338, Download 15881;
  `CL_GW_PORT=15779`, `CL_VERSION=188`, `CL_LOCALE=22` (proxy_cfg.ini; version 188 vs
  label 193 — **discrepancy, NOT reconciled**).
- SQL database names: `SRO_CERTIFICATION`, `SRO_VT_ACCOUNT`, `SRO_VT_SHARD`,
  `SRO_VT_SHARDLOG` (backups + config). Schemas UNKNOWN.
- `MALICIOUS_OPCODES.txt`: 38 hex values, **blocklist only**, no structure.
- Memory offsets file: addresses for level/mastery/etc in the Windows client/GS.
  NOT a network protocol.
- **No packet layout, no opcode dictionary, no TCP/WebSocket spec exists.**

### FUTURE NEW BACKEND DESIGN (new, not VSRO)

Because the original protocol is UNKNOWN and must not be invented-as-canonical, the
online layer is a **new backend** speaking a **new API** we design:

- **Protocol/API**: REST/WebSocket JSON (or Protobuf), defined by us. No claim of
  VSRO compatibility.
- **Authentication**: token-based (JWT or similar) + account service (new schema).
- **Player persistence / character data**: server DB mirror of client state.
- **World state**: authoritative server if competitive; client-authoritative with
  server validation otherwise — design decision later.
- **Combat synchronization**: state-sync (position/HP/events) over WS; reconciliation
  offline-tested first.
- **Inventory / quests**: server-validated transactions.
- **Chat**: relay service.
- **Anti-cheat/security**: login rate limits, server-side validation, signed updates;
  XTrap/ggauth NOT reused.
- **Database/backend**: e.g. Postgres + a game server we build (Kotlin/Go/etc).
- **Separation**: all of §10.2 is NEW DESIGN and never presented as the original VSRO
  protocol.

---

## 11. Unknown / Needs Source

Explicit list. Never filled with assumptions.

| # | Item | Status |
| --- | --- | --- |
| 1 | `pk2reader.py` / `jmblowfish.py` | UNKNOWN / NEEDS SOURCE |
| 2 | `listing_media.txt` / `listing_music.txt` | UNKNOWN / NEEDS SOURCE |
| 3 | SQL Server schemas (`SRO_CERTIFICATION`, `SRO_VT_ACCOUNT`, `SRO_VT_SHARD*`) | UNKNOWN (backups unopened) |
| 4 | Original network protocol / packet layout / opcode semantics | UNKNOWN / NOT VERIFIED |
| 5 | Monster stats (HP/dmg/exp) and drop/loot tables | UNKNOWN |
| 6 | Skill damage/heal/effect formulas | UNKNOWN (skilleffect.txt not parsed; server computes) |
| 7 | Player stat growth / HP-MP curves | UNKNOWN |
| 8 | Quest condition/objective engine logic | UNKNOWN (text + reward tables only) |
| 9 | Party/guild/union/arena/fortress/job/siege logic | UNKNOWN |
| 10 | Movement/pathing graph (NavLink) | UNKNOWN (file absent) |
| 11 | Client `.rd` files purpose (103 x 1,338 B) | UNKNOWN |
| 12 | `silkcfg.dat` / `Silkload.dat` content meaning | UNKNOWN |
| 13 | Proxy version 188 vs package label 193 | UNKNOWN (unreconciled) |
| 14 | Whether GameClient.exe is patched vs stock v193 | NOT VERIFIED (never executed) |
| 15 | Full Media.pk2 interior file list | DOCUMENTED BUT NOT CURRENTLY VERIFIED |
| 16 | Map.pk2 `.t/.o/.o2/.m` full parsing | DOCUMENTED BUT NOT CURRENTLY VERIFIED |
| 17 | Audio extraction | PARTIALLY VERIFIED (ogg listed) / runtime UNKNOWN |

---

## 12. Blocking Issues

| # | Blocker | Blocks | Note |
| --- | --- | --- | --- |
| B1 | No `pk2reader.py`/`jmblowfish.py` | PK2 extraction (all asset work) | repo API expected: `PK2(path)`, `.find()`, `.read_file()` |
| B2 | No `listing_media.txt`/`listing_music.txt` | UI/icon/audio extractors | optional for core meshes/maps |
| B3 | PK2s not extracted (disk ~14 G free) | full dataset access | don't dump into `/workspace` |
| B4 | SQL backups unopened (no schema) | faithful server-side logic, online phase | offline game does not need it |
| B5 | No protocol source | any online/VSRO-compatible networking | → new backend design |
| B6 | No monster/drop/combat/quest-logic tables | faithful combat/economy | → new design, labeled |
| B7 | `GameClient.exe` internals (inventory layout, UI logic) not inspectable | exact client fidelity | → own design |
| B8 | No audio runtime assets committed | audio in-game | convert Music.pk2 later |
| B9 | Google Drive alt package 403/404 | alternate/complete source | blocked |
| B10 | Discrepancy proxy `CL_VERSION=188` vs v193 | version certainty | not reconciled |

Non-blocking for offline MVP: B4, B5, B6, B7 (they become "new design" scope).

---

## 13. Recommended Development Phases

Each phase ends with a push to GitHub (permanent workflow). Docs-first.

- **P0 — Architecture doc (THIS phase)**: analysis only. Deliverable = this document.
- **P1 — Pipeline unlock**: obtain `pk2reader.py` + listings (or prove they're truly
  unavailable). No repo change beyond docs until source available.
- **P2 — Neutral conversion**: new converter → glTF2 + PNG/WebP + JSON + OGG packs from
  verified extraction; run `build_game_database.py` to produce full `gamedata/`.
- **P3 — Native Android shell**: Kotlin app skeleton + Compose + Room + `NetClient`
  interface with mock; empty world loads a region.
- **P4 — Player core**: character render (skinned anims), movement, camera, save/load.
- **P5 — Combat + progression**: local combat resolver, skills/items/levels (verified
  data), inventory/equipment UI.
- **P6 — World content**: NPCs, mobs, shops, quests (verified tables), teleports,
  audio; full offline loop.
- **P7 — Content depth**: multiple regions, dungeon(s), polish.
- **P8 — Online backend (later)**: design + new backend (§10), then plug into
  `NetClient`.

---

## 14. Definition of Done for Each Phase

| Phase | Done when |
| --- | --- |
| P0 | Architecture doc committed + pushed; remote SHA verified; no code changed. |
| P1 | Reader+listings present (or documented unavailable); a tiny verified extract succeeds off-repo; committed status note. |
| P2 | Converted pack for ≥1 region + textdata→JSON validates; sample glTF2 loads in a viewer; full `gamedata/` generated off-repo; commit scripts (no large binaries). |
| P3 | Kotlin app builds as APK; Compose UI shows; mock NetClient present; one region renders from local assets. |
| P4 | Player walks/runs/attacks with real anims in a region; movement+camera work; save/load round-trips via Room. |
| P5 | Combat resolver uses verified level/skill/item data; inventory/equip UI functional; progression (exp/level) works offline. |
| P6 | NPCs talk, shops sell, quests complete (verified tables), mobs spawn/drop (designed), teleports work, audio plays; full offline loop. |
| P7 | All 9 regions + a dungeon reachable; performance target met (device benchmark); polish pass. |
| P8 | New backend design doc approved; `NetClient` real adapter; auth/persistence/combat-sync live; anti-cheat basic. |

Each phase: feature branch → change → verify → commit → push → confirm remote SHA →
report (branch, SHA, repo, push, verify, tests/build, blockers/unknowns).

---

## Appendix — Traceability quick map

| Claim | Source |
| --- | --- |
| 5 PK2s + sizes | `listings/pk2.txt`, `listings/client.txt` |
| Server EXE/DLL/config | `listings/server.txt`, extracted `server.cfg` |
| DB backups | `listings/database.txt` |
| Proxy config/ports | extracted `proxy_cfg.ini` |
| Class names / masteries | `map/src/game/data/skills.json`, `game_data.ts` |
| Rig/anims | `extract_character.py`, `map/src/game/character_*` |
| Regions | `map/src/game/regions.ts`, Phase B–D |
| Missing gamedata | `GAME_CONTENT_VERIFICATION.md` §4 |
| WebView-not-native | `ANDROID_APK_BUILD.md`, `capacitor.config.ts`, `MainActivity.java` |
| No protocol | `VSRO_V193_SOURCE_INVENTORY.md` §F |
