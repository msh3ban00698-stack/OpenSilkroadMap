# PHASE 14 REPORT — Native Android World Runtime

Branch: `260829-phase12-data-parsing-formats` · Phase 13 baseline: `35ad8d2`
Date: 2026-08-30

Phase 14 moves from the data/format foundation (Phases 10–13) to a REAL native
Android world runtime: the native game activity now loads and renders verified
real terrain through the native renderer. All claims are backed by the committed
real assets; anything not proven is classified honestly below.

---

## Status vocabulary

- **SOURCE VERIFIED** — real data confirmed from the ORIGINAL VSRO-R 1.193 archives.
- **IMPLEMENTED** — native code committed and structurally verified.
- **PARTIAL** — a proven subset works; the rest is documented.
- **BLOCKED** — cannot proceed without missing evidence/decoder.
- **UNKNOWN** — no honest claim possible yet.
- **TESTED** — executed here (Python) and passing.
- **NOT EXECUTED** — not run in this environment (no JDK/SDK/emulator).

---

## 1. Starting point (Question 1–2)

- **Phase 13 SHA:** `35ad8d29c90909935a700b683a02aece0c224a76`
- **Branch:** `260829-phase12-data-parsing-formats` (Phase 14 committed on this branch).

## 2. Native entry verification (Part A, Part R)

- Launcher Activity = `MainActivity` (`com.getcapacitor.BridgeActivity`) — a
  Capacitor/WebView entry. **LEGACY / NON-FINAL ENTRY** (not claimed WebView-free).
- Native game entry = `GameActivity` (declared in `AndroidManifest.xml`), a plain
  `android.app.Activity` with **no WebView/Capacitor dependency**. Phase 14 wires
  it to the native world renderer.
- **WebView status: B** — LEGACY WEB ENTRY STILL EXISTS BUT NATIVE GAME RUNS
  INDEPENDENTLY. `MainActivity` (Capacitor) is not deleted.

## 3. Selected terrain region (Part D; Questions 3–8)

Deterministic rule: the FIRST region (in `world_regions.tsv` file order) whose
**reference sector has a committed `.hg`**. Result:

| Field | Value |
|---|---|
| Region | `Jangan_Field` (FIELD), 171 cells |
| Reference sector | `156x89` |
| Source file | `Map.pk2 /89/156.m` |
| Android asset | `game/world/156x89.hg` (VSHG v1) |
| sha256 (index) | `53c5fe1ae346e60573e3ad823543f8800ce925e9d5d9ff10d3579f967bcb709e` |
| Dimensions | 97 × 97, step 20.0 world units |
| Height samples | 9,409 (= 97×97) |
| Height range | min 866.25, max 2687.02 |

`ThiefTown` (182,96) was NOT assumed and has **no** committed `.hg`
(verified: not in `world_index.tsv`, `182x96.hg` absent).

## 4. Terrain loading + rendering (Part B, C, E, F)

- `WorldTerrainIndex` (new, Android-free) parses `world_index.tsv` and is the
  single source of truth for "which sector has a verified Android terrain asset".
- `GameActivity` loads the index + region windows from assets, selects the region
  above, loads the real `.hg` through `TerrainHeightGrid.load`, and hands it to
  `NativeWorldRenderer.setGrid(...)`. `NativeWorldRenderer` is now the displayed
  content view (previously unused).
- **Renderer classification: DIAGNOSTIC TERRAIN RENDERER** — it draws the real
  heightfield top-down as a grayscale height ramp + wireframe. It is NOT claimed
  as final 3D terrain rendering (no normals/materials/textures are manufactured).
- Fail-closed: if the `.hg` is missing the screen shows
  `TERRAIN ASSET MISSING (verified .hg absent)` and renders nothing; no other
  region is substituted.

## 5. Camera + world coordinates (Part E, I)

- Single source of truth = `Camera2D` (center/scale/clamp) + `WorldCoordinates`
  (sector→world) + `WorldProjection` (world→view). No second camera, no duplicated
  coordinate math.
- `NativeWorldRenderer` sets the camera world bounds to the grid extent
  (97 × 20 = 1920) and clamps the center inside it.
- Spaces distinguished: WORLD (sector-local = world at ref sector) → VIEW
  (top-down, +X→screen +X, +Z→screen −Y) → SCREEN (viewport center offset).

## 6. Input / camera movement (Part L)

`NativeWorldRenderer.onTouchEvent`: single-pointer drag pans, two-pointer pinch
zooms, camera is clamped to sector bounds. Generic development controls — NOT
claimed to reproduce authentic Silkroad control behavior.

## 7. Player / NPC / objects (Part G, J, K)

- **Player:** NO verified authentic spawn exists → the camera center is a clearly
  labeled DEVELOPMENT TEST POSITION ONLY (sector center 960,960), never presented
  as the real spawn.
- **World objects (Part G): BLOCKED** — object instances (`.o2`) are parsed but
  model decode (`.bms`) is UNKNOWN; no object/model is fabricated. Metadata is
  preserved, rendering is BLOCKED pending model decoding.
- **NPCs (Part K): BLOCKED** — `npcpos` is verified, but no NPC model is decoded;
  no fake NPC model or DEBUG marker is drawn.

## 8. Textures (Part H)

The DIAGNOSTIC terrain renderer consumes **no textures** (real grayscale height
ramp only). The Phase 12/13 worldmap WebP textures remain available but are not
consumed by this renderer — recorded honestly, not force-wired.

## 9. World streaming (Part M) — PARTIAL

A single sector's `.hg` is loaded on demand (not the whole world). Sector→world
transition math is verified deterministically (adjacent sector = ±1920 world
units). Multi-sector seamless streaming is NOT implemented (documented PARTIAL,
not faked).

## 10. Offline (Part N)

The native world screen uses only local Android assets/data — no server, network,
WebView, or remote API.

## 11. Tests (Part O; Questions 24–25)

**TESTED here (Python, executed):** `scripts/test_phase14_world_runtime.py` — 16
tests covering terrain discovery, loading, dimensions, height samples, region
bounds, world coordinates, camera projection/inverse/screen mapping, region
transition, object coordinate mapping, dependency resolution, and fail-closed
behavior. All 16 OK.

**NOT EXECUTED (no JDK/Android SDK):**
- JVM unit tests: `WorldTerrainIndexTest` (6 tests), plus existing
  `Camera2DTest`, `TerrainHeightGridTest`, `WorldCoordinatesTest`,
  `WorldProjectionTest`.
- Instrumented test `GameActivityTest` (2 tests, rewritten for the terrain
  runtime).
- `./gradlew test` / `assembleDebug`.

## 12. Android build + runtime (Part P, Q, S; Questions 21–23)

- **Build: NOT EXECUTED** — no JDK/Gradle/Android SDK in this environment
  (`java`, `javac`, `gradle` not found; `ANDROID_HOME` unset).
- **APK execution: NOT EXECUTED** — no device/emulator.
- **Performance: NOT EXECUTED** — no benchmarks invented. Estimated draw
  complexity is honest and documented: 96×96 quads per frame from the 97×97 grid.

## 13. Files added/changed

- `android/app/src/main/java/com/opensilkroadmap/app/world/WorldTerrainIndex.java` (new)
- `android/app/src/main/java/com/opensilkroadmap/app/world/NativeWorldRenderer.java` (pan/zoom/clamp)
- `android/app/src/main/java/com/opensilkroadmap/app/game/GameActivity.java` (terrain runtime wiring)
- `android/app/src/test/java/com/opensilkroadmap/app/world/WorldTerrainIndexTest.java` (new)
- `android/app/src/androidTest/java/com/opensilkroadmap/app/game/GameActivityTest.java` (rewritten)
- `scripts/test_phase14_world_runtime.py` (new, 16 tests)

Java structural gate: braces balanced, no Java 9+ constructs; core classes
(`WorldTerrainIndex`, `WorldTerrainIndexTest`) Android-free; `NativeWorldRenderer`,
`GameActivity` legitimately import Android classes.

## 14. Remaining classification summary (Questions 26–27)

- **BLOCKED:** object/model rendering (`.bms` vertex layout UNKNOWN), NPC model
  rendering (no decoded model).
- **UNKNOWN:** `.bms` vertex record, `.nvm` nav-cell semantics, authentic player
  spawn position, worldmap montage layout.

## 15. What Phase 15 should do (Question 28)

1. Decode `.bms` vertex/index layout (blocked since Phase 13) so real world-object
   geometry can be rendered.
2. Decode `.bsr`/`.bsk` → attach real skeletons/animations (models first).
3. Wire real NPC world positions (from `npcpos`) as DEBUG ENTITY MARKERS once a
   real model exists.
4. Implement multi-sector world streaming + region transitions at runtime.
5. Establish a real (verified) player spawn once source evidence exists.
6. Run the real Gradle build + instrumented tests in a JDK/Android SDK environment.
