# SOURCE → ANDROID MAPPING (Phase 9 Part A)

Date: 2026-08-29
Scope: Static mapping from the REAL VSRO-R 1.193 source material verified present in
this environment to the Android-native reconstruction plan. Facts only — no gameplay
rules, formulas, coordinates, offsets, or server behavior are invented here.
Anything not provable from verified files is marked UNKNOWN / BLOCKED.

Status lexicon (project rules §5/§7): VERIFIED / IMPLEMENTED / PARTIAL /
NOT IMPLEMENTED / BLOCKED / UNKNOWN; runtime results that were never executed are
marked NOT EXECUTED, never claimed.

---

## A. Real source material (VERIFIED present in this environment)

| Material | Location (this environment) | Verified |
|---|---|---|
| `Data.pk2` (3,351,891,968 B) | `/tmp/opencode/pk2raw/` | 66,051 files listed |
| `Map.pk2` (1,268,441,088 B) | `/tmp/opencode/pk2raw/` | 19,171 files listed |
| `Media.pk2` (823,066,624 B) | `/tmp/opencode/pk2raw/` | 29,591 files listed; fully extracted |
| `Music.pk2` (76,488,704 B) | `/tmp/opencode/pk2raw/` | 50 files listed; fully extracted |
| `Particles.pk2` (178,126,848 B) | `/tmp/opencode/pk2raw/` | 4,768 files listed; fully extracted |
| `pk2_mate` reader (1,497,488 B) | `/tmp/opencode/pk2_mate` | pinned, reproducible |
| Full Media+Music+Particles extraction | `/tmp/opencode/phase4/full_extract/` | 159 `textdata` files incl. `itemdata*.txt`, `characterdata*.txt`, `skilldata*.txt`, `leveldata.txt`, `npcpos.txt`, `teleportdata.txt`, `regioncode.txt`, `refshop*.txt` |
| `Data.pk2 /RegionInfo.txt` | `/tmp/opencode/phase4/extract/Data/RegionInfo.txt` | ASCII, 3,622 lines, sha256 `787d9b41…`; 72 sections (FIELD 61, TOWN 11), 3,468 listed / 3,387 unique cells |
| Server + client config extracts | `/tmp/opencode/extract/server/`, `/extract/client/` | reference configs ONLY (see E and J) |
| VSRO-R Client archives | `/tmp/opencode/vsro_pkg/` | inventoried, NOT converted |

### Source-derived committed artifacts (VERIFIED)
- `android-assets/manifest.json` — 7,755 records (7,737 minimap + 18 samples), ok 7,755, failed 0, unknown 0.
- `android-assets/maps/minimap/` — 5,523 PNG + `minimap_d/` 2,214 PNG (8 dungeon codes).
- `android/app/src/main/assets/game/regions.tsv` — derived catalog (27,846 B, 72 sections, 3,468 cells, 96.5% minimap coverage) built from the REAL RegionInfo.txt by `scripts/build_region_catalog.py`.

---

## B. System matrix → Android mapping (45 systems)

Every system below is mapped from verified source behavior. **Runtime verified on a
real Android device: none.** W = web prototype, A = native Android module (Phase 8
minimap + Phase 9 game core), D = committed data/doc, P = external package
(inventoried only).

| # | System | Source basis (VERIFIED) | Android-native status | Notes |
|---|---|---|---|---|
| 1 | Client startup | Capacitor WebView boots web app | PARTIAL | WebView shell; Phase 9 `GameActivity` registered, not launcher |
| 2 | Login | — | NOT IMPLEMENTED | web mock only; no server |
| 3 | Character selection | — | NOT IMPLEMENTED | web mock only |
| 4 | Character creation | starter kits in web data | NOT IMPLEMENTED | web mock only |
| 5 | World/map loading | `RegionInfo.txt` + minimap grid | PARTIAL | Phase 9 `RegionCatalog`/`WorldGrid`; cell-space only |
| 6 | Terrain | `.t` (magic `JMXVMAPT1001`) | BLOCKED | UNKNOWN layout, no decoder |
| 7 | Buildings | `.m`/`.o` (magic `JMXVMAPM1000`/`JMXVMAPO1001`) | BLOCKED | UNKNOWN layout, no decoder |
| 8 | NPCs | `npcpos.txt` (inventoried) | NOT IMPLEMENTED | spawn parsing future |
| 9 | Player character | `characterdata*.txt` (inventoried) | PARTIAL | Phase 9 `PlayerState`/`Entity` (units UNKNOWN) |
| 10 | Movement | — | NOT IMPLEMENTED | web joystick only |
| 11 | Camera | — | PARTIAL | Phase 9 `Camera2D` (clamp/center) |
| 12 | Animations | `.ban` (magic `JMXVBAN 0102`) | BLOCKED | UNKNOWN layout, no decoder |
| 13 | Equipment | `itemdata*.txt` (inventoried) | NOT IMPLEMENTED | parsing future |
| 14 | Inventory | — | NOT IMPLEMENTED | web panel only |
| 15 | Items | `itemdata*.txt` (inventoried) | NOT IMPLEMENTED | parsing future |
| 16 | Skills | `skilldata*.txt` (inventoried) | NOT IMPLEMENTED | parsing future |
| 17 | Skill effects | `.efp` (magic `JMXVEFF 0011`) | BLOCKED | UNKNOWN layout, no decoder |
| 18 | Monsters | `npcpos.txt` + mob type files (inventoried) | NOT IMPLEMENTED | authentic spawns future |
| 19 | NPC interaction | — | NOT IMPLEMENTED | web only |
| 20 | Shops | `refshop*.txt`/`refshopgoods.txt` (inventoried) | NOT IMPLEMENTED | parsing future |
| 21 | Quests | — | NOT IMPLEMENTED | web `{}` gamedata |
| 22 | Party | — | NOT IMPLEMENTED | web simulated |
| 23 | Guild | — | NOT IMPLEMENTED | none |
| 24 | Chat | — | NOT IMPLEMENTED | none |
| 25 | Trading | — | NOT IMPLEMENTED | none |
| 26 | Storage | — | NOT IMPLEMENTED | web panel only |
| 27 | Teleport | `teleportdata.txt`/`refoptionalteleport.txt` (inventoried) | PARTIAL | 2,214 dungeon minimaps converted; routing future |
| 28 | Level/EXP | `leveldata.txt`/`levelgold.txt` (inventoried) | PARTIAL | web 150-level curve bundled; native future |
| 29 | Stats | `characterdata*.txt` class columns (inventoried) | NOT IMPLEMENTED | web tuning only |
| 30 | Combat | — | NOT IMPLEMENTED | web simulated |
| 31 | Damage calc | — | NOT IMPLEMENTED | values = tuning, not source |
| 32 | Drops | — | NOT IMPLEMENTED | none |
| 33 | Loot | — | NOT IMPLEMENTED | none |
| 34 | Spawns | `npcpos.txt` (inventoried) | BLOCKED | parsing future |
| 35 | AI | — | NOT IMPLEMENTED | none |
| 36 | Effects | `.efp` | BLOCKED | UNKNOWN layout |
| 37 | Particles | Particles.pk2 4,768 (inventoried) | BLOCKED | `.efp` UNKNOWN |
| 38 | Sounds | Music.pk2 50 ogg, Media 2,885 wav (inventoried) | NOT IMPLEMENTED | 1 wav + 1 ogg samples converted |
| 39 | Music | 50 ogg (inventoried) | NOT IMPLEMENTED | 1 ogg sample converted |
| 40 | Minimap | 5,523 + 2,214 DDJ → PNG (VERIFIED) | PARTIAL | Phase 8 provider + renderer; Phase 9 HUD wired |
| 41 | UI/HUD | — | PARTIAL | Phase 9 `GameHudView` (region/cell/status) |
| 42 | Settings | — | NOT IMPLEMENTED | none |
| 43 | Save/load | — | PARTIAL | web localStorage only |
| 44 | Network protocol | — | NOT IMPLEMENTED | offsets txt is memory offsets, NOT a packet spec |
| 45 | Server/DB/auth | — | NOT IMPLEMENTED | see E; never invented |

Rules 8/9/10/11 hold: asset conversion is not game conversion; a loader/renderer is
not a game; source-file existence is not Android compatibility; "Android-ready" is
never claimed without runtime verification.

---

## C. Asset coverage (from the committed manifest + repo)

- PK2 files inventoried (all 5 archives): **119,631** (Data 66,051 · Map 19,171 ·
  Media 29,591 · Music 50 · Particles 4,768).
- Converted to Android formats and committed: **7,755** (7,747 PNG · 1 WAV · 1 OGG ·
  6 TXT) ≈ **0.65 %** of the inventoried collection.
- Minimap coverage is complete for its category: all 5,523 `minimap` + 2,214
  `minimap_d` DDJ sources have committed PNG outputs; `regions.tsv` cross-check:
  3,267 / 3,387 unique RegionInfo cells (96.5 %) have a committed minimap PNG.
- Remaining unconverted: ≈ 111,876 inventoried files, dominated by UNKNOWN
  proprietary formats (no decoder): navmesh `.nvm` (6,041), terrain `.t` (4,988),
  region mesh `.m` (4,491), objects `.o`/`.o2` (8,839), material `.bsr` (7,549),
  compound `.cpd` (124), animation `.ban`, particle `.efp` (~3,395+), fonts, `.2dt`.
  Per project rules: UNKNOWN means DO NOT CONVERT YET.
- Audio: 0 files under `map/`; only the 2 converted samples exist in `android-assets/`.

---

## D. Android state (incl. rules §11)

Rules §11 ("Android-ready is not claimed without runtime verification") is the
governing constraint. Current Android tree:

| Area | Code | Integrated? | Runtime verified? |
|---|---|---|---|
| Capacitor shell | 68 files | YES | NO |
| Phase 8 minimap module (11 Java files) | `com.opensilkroadmap.app.minimap` | NOW YES (wired via GameHudView/GameActivity) | NO |
| Phase 9 game core (7 Android-free Java files) | `com.opensilkroadmap.app.game` | NOW YES (GameHudView + GameActivity) | NO |
| Derived real data (`regions.tsv`) | `assets/game/regions.tsv` | YES (loaded by GameActivity) | NO |
| JVM tests | 27 (phase 8) + 30 (phase 9: RegionCatalog 8, GameLoop 6, Camera2D 5, PlayerState 5, WorldGrid 4, Entity 2) | — | NOT EXECUTED (no JDK) |
| Instrumented tests | 12 (phase 8) + 2 (phase 9 GameActivity) | — | NOT EXECUTED (no SDK/device) |
| CI (`android-apk.yml`) | builds debug APK on main/PR | — | UNKNOWN for feature branches |

---

## E. Server — NOT built (by directive)

- No server source, executable, packet spec, database schema, or client–server
  protocol exists in the repository or is implemented anywhere.
- The external package's server EXEs/DLLs and SQL `.Bak` files exist ONLY as
  inventoried reference files outside the repo; they are never committed and never
  run. The Android game must run standalone.
- Config extracts in `/tmp/opencode/extract/…` are reference material only; they
  contain a live credential and a private LAN IP and are excluded from the repo
  (see J).

---

## G. GitHub state (VERIFIED)

- origin = `github.com/msh3ban00698-stack/OpenSilkroadMap`; `main` = `12f9bc3` (web map app only).
- Android reconstruction = a linear stack of commits on feature branches NOT merged
  into `main`; branch tip before Phase 9 = `260829-phase8-native-minimap`
  `8238def6…` (remote SHA verified MATCH). Phase 9 lives on a new branch stacked on
  the audit branch.
- Tracked files (pre-Phase 9): 12,839 (android-assets 7,756 · map 4,942 · android 68 ·
  scripts 40 · docs 21 · workflows 2).
- Committed: converted assets + provenance docs + tests. Never committed: PK2, EXE,
  DLL, SQL backups, credentials, private IPs, APK signing material (gitignored).

---

## H. Handoff for another AI

Clone the full stack (newest Phase 9 branch) and you get:
1. Provenance + format taxonomy + manifest + the 7,755-asset collection.
2. Reproducible pipeline (scripts + pinned reader + verify scripts), all green.
3. Web game prototype with 27 passing Deno tests; `map/public/assets/gamedata/*.json`
   are intentionally empty `{}` (generator needs absent `game_source`).
4. Android shell + Phase 8 minimap module + Phase 9 native game core with
   written-but-NOT-EXECUTED JVM/instrumented tests + CI that builds a debug APK.
5. Every format/system classified (VERIFIED / UNKNOWN) so work can resume without
   re-auditing.

Still needed from outside the repo: the private VSRO 1.193 package (to regenerate
`gamedata/*.json`, dungeon PMTiles, navmesh tiles, audio, and decode UNKNOWN formats —
never commit it), and a JDK 17 + Android SDK + emulator/device to run
`./gradlew test`, `connectedAndroidTest`, and device validation.

---

## I. Roadmap (A–K) — status for the Android-native target

| Phase | Scope | Status |
|---|---|---|
| A | Android-native client foundation | PARTIAL (this phase adds native HUD host + game core; not device-verified) |
| B | Android asset integration | PARTIAL (minimap complete; other categories inventoried/UNKNOWN) |
| C | World/map rendering | NOT STARTED (native none; `.t/.m/.o` UNKNOWN) |
| D | Player/NPC/entity systems | PARTIAL (Phase 9 core scaffolding; systems future) |
| E | Combat/gameplay systems | NOT STARTED |
| F | UI/HUD/game systems | PARTIAL (Phase 9 HUD; full UI future) |
| G | Persistence/local gameplay | NOT STARTED (web localStorage only) |
| H | Networking architecture | NOT STARTED |
| I | Future server implementation | NOT STARTED (never invented) |
| J | Online multiplayer | NOT STARTED |
| K | Real Android device validation | BLOCKED (no JDK/SDK/device here) |

---

## J. Secret scan / no binaries

- `git ls-files` shows no PK2, EXE, DLL, SQL backup, or server binary tracked.
- `Certification.xml` (reference config) contains a live credential string; `server.cfg`
  references a private LAN IP. Both exist only in `/tmp/opencode/extract/…`, are never
  committed or quoted, and are described generically as "reference config with live
  credentials / private LAN IP, excluded from the repo."
- APK signing material (`keystore.properties`, `release.keystore`) is gitignored.
- Pre-commit scan is re-run each phase (see PHASE_9_REPORT §verification).

---

## K. Not-code-not-done rule

Per project rules, no implementation result is claimed without: real source input,
committed code, written tests, and (where tooling exists here) passing verification.
Anything unverifiable in this environment is marked NOT EXECUTED. A PK2 archive is
game data, not source code; it is never "converted into code" mechanically. Real
source → system analysis → Android-native implementation → verified assets → tests →
Android build is the only accepted flow.

---

## L. Exact phase data

| Item | Value |
|---|---|
| Phase | 9 — real-source → Android-native game core, Part A mapping + Part B first systems |
| Branch (Phase 9) | `260829-phase9-native-game` |
| Source sha256 | `787d9b417cf3044ff9260f484656002089f7406afd57f229a3c5ac85460739ff` (RegionInfo.txt) |
| Derived catalog | `android/app/src/main/assets/game/regions.tsv` — 72 sections, 3,468 cells, 27,846 B |
| Phase 9 native core | `com.opensilkroadmap.app.game` — 7 Android-free classes + 2 Android classes |
| JVM tests (new) | 6 files, 30 tests (RegionCatalog 8, GameLoop 6, Camera2D 5, PlayerState 5, WorldGrid 4, Entity 2) — NOT EXECUTED |
| Instrumented tests (new) | `GameActivityTest` 2 tests — NOT EXECUTED |
| Default HUD cell | (182, 96) → TOWN ThiefTown (VERIFIED in RegionInfo.txt) — a camera default, not a spawn claim |
| Toolchain | NO JDK/Android SDK/emulator in this environment → JVM/Android runtime NOT EXECUTED |
