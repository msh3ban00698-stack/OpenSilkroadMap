# Current Project Status Audit — OpenSilkroadMap / VSRO-R 1.193 Android-native reconstruction

Date: 2026-08-29
Type: AUDIT / FACT-FINDING ONLY. No implementation, no conversion, no downloads.
Verification basis: repository tree, `git` history, committed manifests, and the
pre-existing audit `GAME_CONTENT_VERIFICATION.md`. The external VSRO package was
only *inventoried* in earlier phases (listings + 35 format samples); it is not
re-extracted for this audit.

Status lexicon used throughout: VERIFIED / IMPLEMENTED / PARTIAL /
NOT IMPLEMENTED / BLOCKED / UNKNOWN (project rules §5). Runtime validation that
was never executed is marked NOT VERIFIED (rules §7).

---

## 1. Executive verdict

**NO — only foundation/assets have been converted (option 3).**

There is **no Android game** in the repository. What exists on the Android side
is (a) a Capacitor WebView shell that wraps a web game prototype and (b) a
standalone, **not-wired-into-the-app** native Java minimap module (Phase 8).
What was "converted" is a verified **asset pipeline**: 7,755 PK2 outputs
converted to Android-consumable formats plus manifest/resolver/loader/renderer
foundation code. The web game prototype in `map/` is a single-player Three.js
prototype that (per the committed `GAME_CONTENT_VERIFICATION.md`) has multiple
broken and placeholder systems, and it has **never been runtime-verified on any
device/emulator**. No server code exists anywhere. Rule 8/9/10/11 apply: asset
conversion is not game conversion, a loader/renderer is not a game, source-file
existence is not Android compatibility, and no multiplayer/server exists.

---

## 2. What is actually implemented

### 2.1 Verified conversion pipeline (assets)
- **PK2 access foundation**: external `pk2_mate` reader pinned (commit `e07dec06…`, MIT),
  reproducible `scripts/validate_pk2.py`, `scripts/inventory_pk2.py`, plus a pure-Python
  DDS decoder `scripts/dds_decode.py` for exactly the verified pixel formats.
- **Android asset manifest** `android-assets/manifest.json` (`schema sro-android-assets-v2`,
  phases `phase5`+`phase6`): **7,755 records, 0 failed, 0 unknown**; 7,737 from Phase 6
  (5,523 `minimap` + 2,214 `minimap_d`) + 18 Phase 5 controlled samples.
- **Converted outputs committed** (`android-assets/`): 7,747 PNGs, 1 `.wav`, 1 `.ogg`,
  6 `.txt` (textdata). PNG format verified (RGBA, bit-depth 8, 256×256 padded for 7,731;
  DDS decode proven for DXT1/DXT3/RGB16/RGB32).
- **35 PK2 format samples** byte-inspected and documented (magic bytes, inner DDS headers).

### 2.2 Native Android module (Phase 8, committed but NOT integrated)
- 11 Java files, package `com.opensilkroadmap.app.minimap` (~978 lines): exception
  hierarchy, `ManifestData`/`ManifestParser`, `ManifestResolver` (exact-path keys,
  phase6>phase5), `AssetDecoder`/`BitmapFactoryDecoder`, `BitmapAsset`,
  `NativeMinimapAssetProvider` (bounded LRU, dimension-validated), `FitMath`,
  `NativeMinimapRenderer` (custom `View`).
- JVM unit tests: 27 tests across 3 files. Instrumented tests: 12 tests (device-only).
- **NOT wired into `MainActivity`/HUD.** **NOT executed** anywhere (no JDK/SDK/device here).
- Run here (pure Python): `scripts/verify_phase8_manifest_rules.py` PASS; proof assets
  prepared (gitignored) by `scripts/prepare_phase8_proof_assets.py`.

### 2.3 Web game prototype (runs in the Capacitor WebView; `map/`)
- Full entry flow (intro → login → character select → create → world) in `flow.ts`.
- Three.js world (`game3d.ts`, 2,177 lines): 3D regions 1–9 + 32785 with authentic
  geometry/buildings; 41-bone character rig + animation state machine
  (`character_rig.ts`, `character_look.ts`); touch joystick (`player_control.ts`);
  HUD (`hud.ts`: HP/MP/EXP/gold/inventory/equipment/death+respawn); inventory, shop,
  party, teleport, warehouse panels; skill bar; level-up flow (real 150-level exp curve).
- Verified game data bundled in `map/src/game/data/*.json` (level progression 150 levels,
  7 starter items, class skills/masteries) extracted from the external package's UTF-16
  `server_dep/silkroad/textdata` (Phase H).
- Web map app (OpenLayers): `world.pmtiles`, `32785.pmtiles`, NPC markers, teleport
  markers, region names, navmesh/navlink visualization (feature set per
  `GAME_CONTENT_VERIFICATION.md` §1).
- Auth/persistence is **local-only**: `storage.ts` keeps accounts in `localStorage`
  (salted SHA-256). No server, no network auth.

### 2.4 CI / workflow
- `.github/workflows/android-apk.yml`: builds a debug APK on `main`/PR with JDK 17 +
  Android SDK (setup-android) via `deno task build` → `npx cap sync android` →
  `./gradlew assembleDebug`. `.github/workflows/prettier.yml`: formatting check.
- **No CI evidence is available locally** for the current feature branches
  (workflows trigger on `main`/PR; Android work lives on unmerged branches) → CI
  outcome for Phase 8 = UNKNOWN.

---

## 3. What is NOT implemented

- **Native Android game**: no world rendering, player, NPCs, combat, HUD, audio,
  persistence, networking on Android. The only native module is the minimap renderer.
- **Any server**: no server source/executable/code, no database schema, no network
  protocol, no packet definitions, no auth/login/game/world server, no end-to-end
  client–server test. The server EXE/DLL + SQL Server `.Bak` files exist **only in the
  external reference package** (Documented, VERIFIED as files, NOT implemented).
- **Full game-data outputs**: `map/public/assets/gamedata/*.json` are empty (`{}`,
  2 bytes) — `quests/shops/items/spawns/chars/teleports_full/skills_full` were never
  generated (their generator `build_game_database.py` needs the absent `game_source/`).
- **Audio/music in the app**: zero `.ogg/.wav/.mp3/.m4a` anywhere under `map/`.
- **Format decoders**: everything classified UNKNOWN (navmesh `.nvm`, terrain `.t`,
  region mesh `.m`/`.o`/`.o2`, model `.bms`, material `.bsr`, compound `.cpd`,
  animation `.ban`, particle `.efp`, fonts) has **no decoder** — see §5.5.
- **On-device/emulator validation**: nothing (no JDK/Android SDK/emulator here).

---

## 4. Android coverage (D)

| # | Area | Code exists? | Integrated? | Tested? | Android runtime tested? | Device/emulator? | Production ready? | Evidence |
|---|------|--------------|-------------|---------|------------------------|------------------|-------------------|----------|
| 1 | Android infrastructure | YES | YES | PARTIAL | NO | NO | NO | Capacitor shell `android/`, `MainActivity.java`, `android-apk.yml` CI |
| 2 | Asset loading | YES (native) + YES (TS) | Native: NO; TS: yes in WebView | Native: JVM tests written, NOT run | NO | NO | NO | `NativeMinimapAssetProvider`, `ManifestResolver`; TS `minimap_assets.ts` |
| 3 | Rendering | YES (native `View`) + YES (TS/WebGL) | Native: NO; WebView: yes | Native: instrumented tests written, NOT run | NO | NO | NO | `NativeMinimapRenderer.java`, `game3d.ts` |
| 4 | Minimap | YES (native + TS) | Native: NO; WebView: yes (web minimap layer) | Written, NOT run (native); TS 19 deno tests PASS | NO | NO | NO | `minimap/` Java module; `minimap_assets.test.ts` |
| 5 | HUD | WebView only | WebView | none | NO | NO | NO | `hud.ts` (488 lines) |
| 6 | Game world | WebView only (3D regions) | WebView | none | NO | NO | NO | `game3d.ts`, `region_loader.ts` |
| 7 | Player | WebView only | WebView | none | NO | NO | NO | `flow.ts`, `player_control.ts`, `game3d.ts` |
| 8 | NPCs | WebView only (partial) | WebView | none | NO | NO | NO | `world_npcs.ts`, `mobs_data.ts` (authentic spawns broken: gamedata empty) |
| 9 | Combat | WebView only (dummy + 3 camps) | WebView | none | NO | NO | NO | `game3d.ts`, `skill_data.ts` |
| 10 | UI | WebView panels | WebView | none | NO | NO | NO | `screens.ts`, `inventory_panel.ts`, `shop_panel.ts`, etc. |
| 11 | Audio | NO | – | – | NO | NO | NO | no audio files in `map/` |
| 12 | Persistence | WebView (localStorage) | WebView | none | NO | NO | NO | `storage.ts` (local accounts/characters) |
| 13 | Networking | NO | – | – | NO | NO | NO | none in repo |
| 14 | Authentication | WebView mock (local) | WebView | none | NO | NO | NO | `storage.ts` local salted hashes |
| 15 | Backend/server comms | NO | – | – | NO | NO | NO | none in repo |
| 16 | Database layer | NO | – | – | NO | NO | NO | SQL `.Bak` only in external package |

Rule 11 holds: "Android-ready" is **not** claimed for anything not runtime-verified.

---

## 5. Asset conversion coverage (C)

### 5.1 Numbers (from the committed manifest + repo)
- PK2 files inventoried (all five archives, via pinned reader): **119,631** files
  (Data 66,051 · Map 19,171 · Media 29,591 · Music 50 · Particles 4,768).
- PK2 files format-sampled by byte inspection: **35** (`scripts/extract_samples.py`).
- PK2 outputs converted to Android formats: **7,755** (manifest `summary.total=7755`,
  `ok=7755`, `failed=0`, `unknown=0`). This is **≈ 6.5 per 1,000** of the inventoried
  collection (0.65 %).
- Converted outputs committed to GitHub: **7,755** (7,747 PNG + 1 wav + 1 ogg + 6 txt).
- Converted but not yet integrated into any gameplay: **all 7,755** (no game consumes
  the native loader; the WebView consumes only the web app's own committed `img/` set).
- Remaining in original PC format: **≈ 111,876** inventoried but unconverted.
- Remaining UNKNOWN (format understood at magic-byte level only, decoder absent):
  see §5.5.

### 5.2 Category coverage of the five PK2 archives
| Archive | Inventoried | Converted (committed) | Android-usability now |
|---|---|---|---|
| Data.pk2 | 66,051 (all listed; partial extract) | 0 converted to `android-assets/` (samples only) | UNKNOWN formats dominate |
| Map.pk2 | 19,171 (all listed; partial extract) | 0 | UNKNOWN formats dominate |
| Media.pk2 | 29,591 (fully extracted in prior phase) | 7,755 (minimap + minimap_d + samples) | PNG/DDS-usable subset only |
| Music.pk2 | 50 | 1 (sample `jangan_town.ogg`) | Ogg → native players (no decoder needed) |
| Particles.pk2 | 4,768 (fully extracted) | 0 | UNKNOWN `.efp`/texture formats |

### 5.3 Converted asset types
- PNG (RGBA8, 256×256 padded): 7,747 — minimap 5,523, minimap_d 2,214, plus 10
  controlled samples (textures/interface/effect/particle/`minimap_100x100`,
  `minimap_d_arabia_boss_127x127`, tile2d).
- Ogg Vorbis: 1 (BGM sample). WAV PCM 16-bit 22050 Hz: 1 (SFX sample).
- Text (UTF-16/ASCII): 6 (from `server_dep/silkroad/textdata` + config).

### 5.4 Proprietary / unknown formats remaining undecoded (VERIFIED magic, UNKNOWN layout)
`JMXVNVM` (navmesh `.nvm`, 6,041), `JMXVMAPT1001` (terrain `.t`, 4,988),
`JMXVMAPM1000` (region mesh `.m`, 4,491), `JMXVMAPO1001` (region objects `.o`/`.o2`, 8,839),
`JMXVBMS 0110` (model mesh `.bms`), `JMXVRES 0109` (material `.bsr`, 7,549),
`JMXVCPD 0101` (compound `.cpd`, 124), `JMXVBAN 0102` (animation `.ban`),
`JMXVEFF 0011` (particle `.efp`, ~3,395+), `JMXVIMG 1100` (fonts), `.2dt` (res_ui).
Per project rules: **UNKNOWN means UNKNOWN — DO NOT CONVERT YET** (`ANDROID_ASSET_MANIFEST.md` §4.2).

### 5.5 GitHub safety / completeness
- Converted assets committed: **YES** (7,755 under `android-assets/`, plus 4,794 web-era
  images under `map/public/assets/img/`).
- Large proprietary originals accidentally committed: **NO** — no PK2, EXE, DLL, SQL
  backup, or server binary is tracked (root `.gitignore` excludes `game_source`, `dist`,
  `*.pk2`; verified by `git ls-files`).
- Android asset manifest completeness: **PARTIAL by design** — complete for minimaps
  (all 5,523 + 2,214), partial for the total PK2 collection (covers ~6.5‰). It is
  authoritative for the converted subset; the *overall* game asset plan is documented in
  `ANDROID_ASSET_MANIFEST.md` §4.1/4.2.

---

## 6. Original game systems coverage (B)

Evidence keys: **W** = web prototype (`map/src/game/*`), **A** = native Android module,
**D** = committed data/doc, **P** = external package (inventoried only, not in repo).
Runtime verified on a real Android device: **none** anywhere.

| System | Status | Evidence | Runtime verified? |
|---|---|---|---|
| Client startup | PARTIAL | Capacitor WebView boots web app; native shell only | NO |
| Login | PARTIAL (mock) | `storage.ts` localStorage accounts, `screens.ts` login UI | NO |
| Character selection | PARTIAL | `flow.ts`/`screens.ts`, `storage.ts` characters | NO |
| Character creation | PARTIAL | `screens.ts`, `game_data.ts` starter kits | NO |
| World/map loading | PARTIAL | `region_loader.ts`, `world.pmtiles` + 1 dungeon pmtiles; 11/13 layers missing | NO |
| Terrain | PARTIAL (web) | region geometry `mesh.json`/`floor.webp` regions 1–9+32785; native none; `.t` UNKNOWN | NO |
| Buildings | PARTIAL (web) | `buildings.json`/`buildings.bgeo` regions 1–9; 32785 none | NO |
| NPCs | PARTIAL | `npcs.json` (map markers); `world_npcs.ts`; authentic spawns broken (gamedata empty) | NO |
| Player character | PARTIAL | `character_rig.ts`, `character_look.ts`, `game3d.ts` | NO |
| Character movement | PARTIAL | `player_control.ts` joystick, `game3d.ts` | NO |
| Camera | PARTIAL | `game3d.ts` | NO |
| Animations | PARTIAL | 41-bone rig + state machine; `.ban` format UNKNOWN, no real animation assets | NO |
| Equipment | PARTIAL | `inventory_panel.ts`, `items.ts` equippable (starter only) | NO |
| Inventory | PARTIAL | `inventory_panel.ts`, `storage.ts` | NO |
| Items | PARTIAL | `items.ts` + bundled starter items (7); full `itemdata*.txt` inventoried in package | NO |
| Skills | PARTIAL | `skill_data.ts` + level-1 skills; full `skilldata*.txt` in package, `skills_full.json` missing | NO |
| Skill effects | NOT IMPLEMENTED | none; `.efp` particles UNKNOWN | NO |
| Monsters | PARTIAL (simulated) | `mobs_data.ts` procedural camps; no authentic spawn data | NO |
| NPC interaction | PARTIAL | `world_npcs.ts` | NO |
| Shops | BROKEN/partial | `shop_panel.ts` — fails without gamedata (empty `{}`) | NO |
| Quests | BROKEN/partial | `quest_runtime.ts`, `quest_data.ts` — requires empty `gamedata/quests.json` | NO |
| Party | PARTIAL (simulated) | `party_panel.ts`, `party_data.ts` (2 hardcoded mercenaries) | NO |
| Guild | NOT IMPLEMENTED | none (only guild master actor art exists) | NO |
| Chat | NOT IMPLEMENTED | none | NO |
| Trading | NOT IMPLEMENTED | none | NO |
| Storage | PARTIAL | `warehouse_panel.ts` (UI) | NO |
| Teleport | PARTIAL | `teleport_data.ts`/`teleport_panel.ts`; gates/travel broken (gamedata empty); 2,214 dungeon minimaps converted | NO |
| Level/experience | PARTIAL | real 150-level curve bundled; `level_progression.json` | NO |
| Stats | PARTIAL | `game_data.ts` class stats; tuning marked as such | NO |
| Combat | PARTIAL | dummy + 3 hardcoded camps (region 1); damage = tuning | NO |
| Damage calculation | PARTIAL | `skill_data.ts` `skillDamage`; values marked tuning | NO |
| Drops | NOT IMPLEMENTED | none | NO |
| Loot | NOT IMPLEMENTED | none | NO |
| Spawns | BLOCKED | authentic spawns need `gamedata/spawns.json` (empty); `npcpos.txt` inventoried in package | NO |
| AI | NOT IMPLEMENTED | none | NO |
| Effects | NOT IMPLEMENTED | `.efp` UNKNOWN | NO |
| Particles | NOT IMPLEMENTED | `.efp`/texture DDJs inventoried (Particles.pk2 4,768) | NO |
| Sounds | NOT IMPLEMENTED | 1 converted `.wav` sample; 2,885 `.wav` inventoried | NO |
| Music | NOT IMPLEMENTED | 1 converted `.ogg` sample; 50 `.ogg` inventoried | NO |
| Minimap | PARTIAL | Native renderer (unwired) + TS loader; 7,737 minimap PNGs integrated into manifest | NO |
| UI/HUD | PARTIAL (web) | `hud.ts`, panels; native none | NO |
| Settings | NOT IMPLEMENTED | none | NO |
| Save/load | PARTIAL (web) | `storage.ts` localStorage characters | NO |
| Account/login backend | NOT IMPLEMENTED | none (web mock only) | NO |
| Database access | NOT IMPLEMENTED | SQL `.Bak` in external package only | NO |
| Network protocol | NOT IMPLEMENTED | none; offsets txt is memory offsets, not a packet spec | NO |
| Game server | NOT IMPLEMENTED | server EXEs only in external package (not run) | NO |
| Authentication server | NOT IMPLEMENTED | none | NO |
| World server | NOT IMPLEMENTED | none | NO |
| DB/server sync | NOT IMPLEMENTED | none | NO |
| Anti-cheat/security | NOT IMPLEMENTED | proxy/HWID files only in external package | NO |

---

## 7. Server/backend coverage (E)

| Item | Status | Evidence |
|---|---|---|
| Server source available | DOCUMENTED ONLY (external) | `Vietnam-R v193 Package Server.7z` listed in `EXTERNAL_PACKAGE_INVENTORY.md` (binaries not in repo, not executed) |
| Server executable available | DOCUMENTED ONLY (external) | `MachineManager.exe`, `smc.exe`, `*dll` listed; not committed, not run |
| Server code in repository | NOT IMPLEMENTED | `git ls-files` shows none |
| Database schema available | DOCUMENTED ONLY (external) | `SRO_CERTIFICATION/VT_ACCOUNT/VT_SHARD/VT_SHARDLOG.Bak` listed; not in repo |
| Database implementation available | NOT IMPLEMENTED | none |
| Network protocol available | NOT IMPLEMENTED | `Vietnam-R v193 Offsets.txt` is memory offsets only |
| Authentication available | NOT IMPLEMENTED | web mock (localStorage) only |
| Login server | NOT IMPLEMENTED | none |
| Game/world server | NOT IMPLEMENTED | none |
| Packet definitions available | NOT IMPLEMENTED | none |
| Server/client communication implemented | NOT IMPLEMENTED | none |
| Android client networking implemented | NOT IMPLEMENTED | no network code in Android module |
| Anything tested end-to-end | NO | nothing runs client↔server |

No server is invented here (rule E: "Do NOT invent a server").

---

## 8. GitHub contents (G)

What is preserved today on `github.com/msh3ban00698-stack/OpenSilkroadMap`:

| Category | Present? | Detail |
|---|---|---|
| Android source code | YES | Capacitor shell (68 files) + Phase 8 native minimap module (11 Java files, unwired) |
| Conversion tools | YES | 40 scripts (extraction, DDS decode, manifest, verification) |
| Manifests | YES | `android-assets/manifest.json` (7,755 records) + generated metadata |
| Tests | YES | 27 Deno (web), 6 Python suites (11/15/5/18/17 tests), 27 JVM tests (not run), 12 instrumented tests (not run) |
| Documentation | YES | 21 root `.md` docs (provenance, manifest, reader foundation, architecture, phase reports) |
| Generated assets | YES | 7,755 converted Android outputs (414 MB) + 4,794 web-era images (map/public/assets/img) |
| Proprietary original archives | NO | none committed (gitignored) |
| PC binaries | NO | none committed |
| Server binaries | NO | none committed |
| Database backups | NO | none committed |
| Configuration/secrets | NO | `keystore.properties`/`release.keystore` gitignored; no secrets in tracked files |

**Important structural fact:** `main` is at `12f9bc3` (the web map app only). **All
Android reconstruction work is in a linear stack of 10 commits spread across 9
feature branches that are NOT merged into `main`** (`260829-pk2-reader-foundation` →
`260829-pk2-asset-foundation` → `260829-android-asset-conversion` →
`260829-phase6-bulk-android-assets` → `260829-phase7-android-minimap` →
`260829-phase8-native-minimap`). A fresh clone of `main` gets **none** of the Android
work; a clone of `origin/260829-phase8-native-minimap` gets all of it (the branches are
stacked linearly; `main` is an ancestor of the phase-8 branch).

---

## 9. What another AI can continue from GitHub

Cloning `origin/260829-phase8-native-minimap` (the full stack) today gives:
- Full provenance docs (source package, PK2 reader pinned, format taxonomy, manifest).
- Reproducible pipeline (scripts + pinned reader + verify scripts) and the converted
  7,755-asset collection + manifest.
- Web game prototype (Three.js) with data modules and 27 passing Deno tests.
- Android shell + Phase 8 native minimap module with written-but-unrun JVM/instrumented
  tests, plus CI (`android-apk.yml`) that builds a debug APK given JDK 17 + Android SDK.
- Clear classification of every format (VERIFIED / UNKNOWN) and every system
  (this audit + `GAME_CONTENT_VERIFICATION.md`).

It would still need from the private/external source:
- The VSRO 1.193 package (PK2 archives + `game_source` extraction) to regenerate
  `gamedata/*.json`, dungeon PMTiles, navmesh world tiles, audio, and to decode the
  UNKNOWN formats — these are **not** and must not be committed.
- A JDK + Android SDK + emulator/device to run `./gradlew test`,
  `connectedAndroidTest`, and device validation.

---

## 10. What remains private/external

- VSRO 1.193 download package (MEGA zip, ~1.76 GB): `PK2 Files.7z`, `VSRO-R Client.7z`,
  `Vietnam-R v193 Package Server.7z`, `Database.7z`, proxy/patchers, offsets/notes.
- Raw PK2 contents extracted during earlier phases under `/tmp/opencode/…` (outside repo).
- `game_source/` extraction directory (gitignored, absent now).
- APK signing material (`android/app/keystore.properties`, `release.keystore`) — gitignored.
- Any Google services config (optional; absent).

---

## 11. Blockers

1. **No Java/JDK/Android SDK/emulator in this environment** — Phase 8 JVM tests,
   instrumented tests, and any on-device validation are NOT EXECUTED. Android runtime
   status is UNKNOWN (no fake execution is claimed).
2. **No `game_source` / PK2 package present** — `gamedata/*.json` are empty `{}`;
   teleport gates, quests, shops, authentic NPC spawns, dungeon PMTiles, world
   navmesh, and audio are non-functional in the web app until data is regenerated.
3. **UNKNOWN proprietary formats** — terrain/region mesh/objects, navmesh, models,
   materials, compounds, animations, particles, fonts have no decoder; converting them
   requires format research first (project rule: UNKNOWN means DO NOT CONVERT YET).
4. **Android work not on `main`** — CI and a fresh clone of `main` do not see it;
   branches must be merged (or the stack kept on the feature branch).
5. **No server, protocol, or DB** — everything server-side is unimplemented by design
   (future phases); the external package's binaries must not be used as a runtime.

---

## 12. Remaining roadmap (I)

Marked DONE / PARTIAL / NOT STARTED / BLOCKED (status is for the Android-native target).

| Phase | Scope | Status |
|---|---|---|
| A | Android-native client foundation | PARTIAL (Capacitor shell; native renderer foundation minimal; not device-verified) |
| B | Android asset integration | PARTIAL (minimap manifest+PNGs integrated; other categories inventoried/UNKNOWN) |
| C | World/map rendering | NOT STARTED (web has PMTiles + 3D regions; native none; `.t/.m/.o` UNKNOWN) |
| D | Player/NPC/entity systems | NOT STARTED (web prototype only) |
| E | Combat/gameplay systems | NOT STARTED (web prototype only) |
| F | UI/HUD/game systems | NOT STARTED (web HUD/panels only) |
| G | Persistence/local gameplay | NOT STARTED (web localStorage only) |
| H | Networking architecture | NOT STARTED |
| I | Future server implementation | NOT STARTED |
| J | Online multiplayer | NOT STARTED |
| K | Real Android device validation | BLOCKED (no device/emulator/JDK here; CI exists but unverified for these branches) |

---

## 13. Exact next recommended phase

Identify only — **not started.**

**Prerequisite: establish a Java/Android toolchain and execute Phase 8's written
tests and build.** Concretely, with a JDK 17 + Android SDK available (or by merging the
Android stack to `main` so `android-apk.yml` runs and is verified):
1. Run `./gradlew test` (JVM unit tests, 27 tests).
2. Run `./gradlew connectedAndroidTest` (instrumented renderer tests, 12 tests) against
   the gitignored real proof assets.
3. Build and install the debug APK and confirm the WebView app boots on a device.
4. Only then, continue Phase A/B: wire `NativeMinimapRenderer` into the activity as a
   native HUD overlay driven by real player coordinates (the Phase 8 documented
   recommendation).

Everything above is blocked on the toolchain; nothing game-related may be implemented
until runtime validation is possible.

---

## Appendix — repository facts used

- Branch `260829-phase8-native-minimap`, HEAD `8238def692c9f977ec108e20388dcdff1497dc07`,
  remote `origin` = `github.com/msh3ban00698-stack/OpenSilkroadMap`, working tree clean.
- 11 commits total; `main` = `12f9bc3`; Android work = 10 stacked commits on 9 unmerged
  branches, all pushed.
- Tracked files: 12,839 total — `android-assets` 7,756 · `map` 4,942 · `android` 68 ·
  `scripts` 40 · docs 21 `.md` · `.github` 2 workflows.
- `android-assets/manifest.json`: 7,755 records (phase5 18, phase6 7,737), ok 7,755,
  failed 0, unknown 0; unique sources 7,753; duplicates 2 (phase6 preference).
- PK2 archives verified: Data 66,051 · Map 19,171 · Media 29,591 · Music 50 ·
  Particles 4,768 files (≈119,631 total).
- Converted = 7,755 outputs (≈0.65 % of inventoried), all committed as PNG/Ogg/WAV/TXT.
- `map/public/assets/gamedata/items.json` + `names.json` = `{}` (2 bytes each).
- No audio files under `map/`. No PK2/EXE/DLL/SQL committed.
- Environment: `java/javac/gradle/kotlinc/sdkmanager/adb/emulator` NOT FOUND;
  `ANDROID_HOME`/`JAVA_HOME` unset; Deno 2.9.6, Node 22, Python 3.11; disk free 6.3 GB.
