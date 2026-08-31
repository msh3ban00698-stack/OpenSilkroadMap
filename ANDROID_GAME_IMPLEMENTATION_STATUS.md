# Android Game Implementation Status (native game core)

Date: 2026-08-31 (updated for Phase 28)
Scope: Status of the Android-native systems (Phase 9 Part B + Phase 22 native
runtime migration). All behavior is Android-free Java (runs under `./gradlew test`)
with thin native Views; every value is traceable to verified real source or marked
UNKNOWN.

Phase 22 (2026-08-31): removed the Capacitor/WebView runtime. `GameActivity` is
now the launcher; the retired wrapper is preserved under `legacy/capacitor/`. See
`WEB_RUNTIME_AUDIT.md` and `PHASE_22_REPORT.md`.

Phase 27 (2026-08-31): exhaustive source recovery for the **real player
runtime** (spawn / input / movement / camera) against the full original corpus
(server DB backups, PK2 archives, client settings). Every domain resolves to
caller-supplied or client-code-defined behavior, so the fail-closed runtime is
unchanged — nothing is invented. Proven chains recorded in
`scripts/testdata/formats/phase27_source_evidence.json` (builder
`scripts/build_phase27_evidence.py`): `_AddNewChar` start region/pos is
caller-supplied (only hint: `-- set @StartRegionID=25000`; region 25000 =
RN_CH_JANGAN proven via `regioncode.txt`), key bindings exist only as binary
`SROptionSet.dat`, camera has FREE/THIRD_PERSON/QUARTER_VIEW modes with
client-code parameters, movement has only debug `/fast`/`/setspeed`.
`Phase27SourceEvidenceTest` (5 tests) asserts these. Bounded real-JUnit
verification: **139 PASS / 0 FAIL**. See `PHASE_27_REPORT.md` and
`PHASE_26_REPORT.md` (runtime: `CharacterWorld`, evidence-based, fail-closed).

Phase 28 (2026-08-31): **source runtime semantics recovery**. The `Data.pk2`
`.ban` corpus (4,691 clips) proves the animation-state vocabulary
(`attack`/`damage`/`die`/`down`/`wakeup`/`sit`/`pickup`/`stun`/`blocking`…);
`characterdata_5000.txt` yields 13 player class templates (`CHAR_CH_MAN_*` →
BSR); `characterdata_25000.txt` (Jangan) is a 3,736-row entity catalog with 120
distinct meshes and no position column; `skilldata.tsv` is an unparsed 7-file
stub. `AnimState` + `AnimStateResolver` were extended with the proven `DOWN`
(knockdown) and `WAKEUP` (recovery) states (the bandit manifest now resolves 8
states). The native-runtime audit confirms the Android gameplay runtime is 100%
native (no WebView/Capacitor/browser); the retired wrapper stays under
`legacy/capacitor/`; the separate `map/` web project carries a TS browser
prototype (DEAD, not the Android runtime). Evidence in
`scripts/testdata/formats/phase28_source_evidence.json` (builder
`scripts/build_phase28_evidence.py`); matrix in
`PHASE_28_SOURCE_RUNTIME_MATRIX.tsv`; `Phase28SourceEvidenceTest` (6 tests) + 3
new `AnimStateResolverTest` cases. Bounded real-JUnit verification: **148 PASS /
0 FAIL**. ANDROID RUNTIME: NOT EXECUTED. See `PHASE_28_REPORT.md`.

---

## 1. Implemented systems (code committed, tests written)

Package `com.opensilkroadmap.app.game`, `android/app/src/main/java/` + tests.

### 1.1 Runtime
- `GameLoop.java` — fixed-dt accumulator (default 0.05 s, catch-up cap 0.25 s).
  Engine scaffolding, not authentic VSRO timing (real tick rate UNKNOWN).
- `GameLoopTest.java` — 6 tests.
- `GameClock.java` — monotonic frame clock; converts a time source to a clamped
  per-frame delta (default clamp 0.1 s). Phase 22.
- `GameClockTest.java` — 6 tests.
- `InputController.java` — Android-free gesture accumulator (drag pan, pinch
  zoom, joystick direction); drained per frame by the renderer. Phase 22.
- `InputControllerTest.java` — 6 tests.

### 1.2 Rendering/camera
- `Camera2D.java` — follow + world clamp; centers when the viewport exceeds the world.
  Generic 2D camera; no authentic camera math claimed.
- `Camera2DTest.java` — 5 tests.

### 1.3 Map/world foundation (REAL DATA)
- `RegionInfo.java` + `RegionCatalog.java` — parse the committed `regions.tsv`
  derived from REAL `Data.pk2 /RegionInfo.txt` (sha256
  `787d9b417cf3044ff9260f484656002089f7406afd57f229a3c5ac85460739ff`). 72 sections
  (FIELD 61, TOWN 11), 3,468 cells; RECT extras preserved verbatim.
- `WorldGrid.java` — verified grid bounds (x∈[26,252], y∈[35,126], 5,523 cells) and
  the source/asset path mapping for the Phase 8 minimap module.
- `RegionCatalogTest.java` — 8 tests (incl. real-catalog assertions).
- `WorldGridTest.java` — 4 tests.
- `scripts/build_region_catalog.py` — reproducible generator (env `SRO_REGIONINFO` or
  `--regioninfo`; no hardcoded paths).

### 1.4 Entity/player
- `Entity.java` — id/name/position scaffolding (units UNKNOWN).
- `PlayerState.java` — level/hp/mp/gold/class/dead; clamps; `isAlive`.
- `EntityTest.java` — 2 tests. `PlayerStateTest.java` — 5 tests.

### 1.5 Native HUD + host (Android classes)
- `GameHudView.java` — FrameLayout: Phase 8 `NativeMinimapRenderer` (240dp,
  bottom-right) + region/cell/status labels; `setPlayerCell(x,y)`; explicit
  "MINIMAP ASSETS NOT BUNDLED" degradation when the manifest is absent.
- `GameActivity.java` — loads real `game/regions.tsv` via AssetManager; optional
  provider from `assets/game/manifest.json`; default HUD cell (182,96) = TOWN
  ThiefTown (VERIFIED) — a camera default, not a spawn claim; registered in
  `AndroidManifest.xml` as the LAUNCHER (Phase 22). Drives a fixed-timestep
  `GameLoop` heartbeat with a monotonic `GameClock`; no WebView.
- `MainActivity.java` — Phase 22: retired from Capacitor `BridgeActivity`; now a
  plain `Activity` that redirects to `GameActivity`.
- Instrumented `GameActivityTest.java` — 2 tests (launch + fallback states).

## 2. Reused unchanged
- Phase 8 module `com.opensilkroadmap.app.minimap` (provider/resolver/decoder/
  renderer) — consumed via `NativeMinimapAssetProvider`, `ManifestParser`,
  `BitmapFactoryDecoder`; APIs re-confirmed.

## 3. Verification status in THIS environment
- Written and verifiable here: structural scan (braces, no Java 9+ constructs,
  Android-free core), `scripts/build_region_catalog.py` run + `test_sro_pipeline`
  (no-hardcode rule), `verify_phase8_manifest_rules.py`, full Deno/Python/web
  regression matrix (all green), `deno task build` exit 0.
- EXECUTED here (pure-JVM JUnit harness, real JUnit 4.13.2, JDK present): the
  world/game runtime suite — **148 PASS / 0 FAIL** as of Phase 28 (harness
  `/tmp/opencode/ph28build/phase28_build_and_run.sh`, see Phase 26/27/28 reports).
- NOT EXECUTED: Gradle wrapper (`./gradlew test`) and instrumented
  (`./gradlew connectedAndroidTest`) runs — no Android SDK/emulator in this
  environment. No fake execution is claimed.

## 4. What is NOT implemented (unchanged)
- Everything else in the 45-system matrix (combat, NPCs, skills, quests, audio,
  persistence, networking, server) — see `SOURCE_TO_ANDROID_MAPPING.md` §B/E.
- World coordinate ↔ cell conversion (UNKNOWN from supplied material), authentic
  movement/tick/stat rules, UNKNOWN-format decoders (`.t/.m/.o/.nvm/.ban/.efp/…`).
