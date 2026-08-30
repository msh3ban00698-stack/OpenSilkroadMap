# Android Game Implementation Status (Phase 9 native game core)

Date: 2026-08-29
Scope: Status of the first Android-native systems implemented in Phase 9 Part B.
All behavior is Android-free Java (runs under `./gradlew test`) with thin native
Views; every value is traceable to verified real source or marked UNKNOWN.

---

## 1. Implemented systems (code committed, tests written)

Package `com.opensilkroadmap.app.game`, `android/app/src/main/java/` + tests.

### 1.1 Runtime
- `GameLoop.java` — fixed-dt accumulator (default 0.05 s, catch-up cap 0.25 s).
  Engine scaffolding, not authentic VSRO timing (real tick rate UNKNOWN).
- `GameLoopTest.java` — 6 tests.

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
  `AndroidManifest.xml` (exported, sensorLandscape). WebView MainActivity stays the
  launcher.
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
- NOT EXECUTED: all JVM (`./gradlew test`) and instrumented
  (`./gradlew connectedAndroidTest`) tests — no JDK/Android SDK/emulator in this
  environment. No fake execution is claimed.

## 4. What is NOT implemented (unchanged)
- Everything else in the 45-system matrix (combat, NPCs, skills, quests, audio,
  persistence, networking, server) — see `SOURCE_TO_ANDROID_MAPPING.md` §B/E.
- World coordinate ↔ cell conversion (UNKNOWN from supplied material), authentic
  movement/tick/stat rules, UNKNOWN-format decoders (`.t/.m/.o/.nvm/.ban/.efp/…`).
