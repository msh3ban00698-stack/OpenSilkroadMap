# PHASE 15 REPORT — Native Multi-Sector World + NPC Placement

Branch: `260830-phase15-native-world-integration` · Phase 14 baseline: `f5be202`
Date: 2026-08-30

Phase 15 extends the native world runtime (Phase 14) from a single diagnostic
terrain sector to a REAL multi-sector world plus verified NPC placement. All
claims are backed by the committed real assets; anything not proven is
classified honestly below.

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

## 1. Starting point

- **Phase 14 SHA:** `f5be202abd149e08e5e8f07d26904fc3408a19a3`
- **Branch:** Phase 15 continues from Phase 14 HEAD on a dedicated branch.

## 2. Selected multi-sector world

Deterministic rule: select the first region (in `world_regions.tsv` file order)
whose reference sector has a committed `.hg`, then load EVERY committed sector
in that region's window.

| Field | Value |
|---|---|
| Region | `Jangan_Field` (FIELD), window `sx 156..182, sy 89..102` |
| Reference sector | `156x89` |
| Committed sectors loaded | `156x89`, `156x90` (the only committed sectors in the window) |
| World extent | 1920 × 3840 world units (1 × 2 sectors) |
| Sector origins | `(156,89)=(0,0)`, `(156,90)=(0,1920)` |
| Height range | 156x89: 866.25..2687.02; 156x90: 801.79..1825.93 |
| Edge continuity | `g1[96][x] == g2[0][x]` for sampled columns (difference `0.0`) |

`ThiefTown` (182,96) remains without a committed `.hg` and is NOT substituted.

## 3. NPC placement integration

- Source: `game/textdata/npcpos.tsv` (18,457 real rows), parsed by the new
  Android-free `NpcSpawnIndex`.
- Classification: **14,800 world** rows vs **3,657 dungeon/instance** rows
  (negative region code → never projected into world coordinates).
- Jangan_Field window contains **862** world NPC spawns.
- Committed sectors: `156x90` has **3** world spawns (2 distinct character
  refids), `156x89` has **0**.
- World coordinates use the proven formula
  `world = (sector − refSector) * 1920 + local`.
- **Rendering: DIAGNOSTIC PLACEMENT MARKERS ONLY** — real `npcpos` coordinates
  are drawn as small markers; no character model is decoded or fabricated.

## 4. World object placement (`.o2`) — PARTIAL

- `Map.pk2` contains **4,348** `.o2` object-instance overlays.
- Proven: 12-byte magic `JMXVMAPO1001`; offset 12 is always `u32 = 0`; the first
  data byte is **variable and >= 16** (observed 16, 18, 26, 34, 72, 104, 106,
  114, 192, …).
- The Phase 10 `parse_o2` assumes data starts at offset 16 and is **valid only
  when the first data byte is at 16**. The variable-header layout for other
  sectors is **UNKNOWN**.
- Object/model rendering remains **BLOCKED** (`.bms` vertex layout UNKNOWN); no
  object geometry is fabricated.

## 5. Runtime wiring

- `GameActivity` now loads `world_index.tsv` + `world_regions.tsv` + `npcpos.tsv`,
  builds a `WorldTerrainSet` of every committed sector in the selected region
  window, attaches `NpcSpawnIndex`, and renders via `NativeWorldRenderer`.
- Fail-closed: missing terrain shows `TERRAIN ASSET MISSING (verified .hg absent)`;
  no other region is substituted.
- `NativeWorldRenderer` rewritten for multi-sector rendering (real heightfield
  quads per sector) plus optional NPC markers; backward-compatible `setGrid`.

## 6. New / changed files

- `android/app/src/main/java/com/opensilkroadmap/app/world/WorldTerrainSet.java` (new, Android-free)
- `android/app/src/main/java/com/opensilkroadmap/app/data/NpcSpawnIndex.java` (new, Android-free)
- `android/app/src/main/java/com/opensilkroadmap/app/world/NativeWorldRenderer.java` (multi-sector + NPC markers)
- `android/app/src/main/java/com/opensilkroadmap/app/game/GameActivity.java` (multi-sector wiring)
- `android/app/src/test/java/com/opensilkroadmap/app/world/WorldTerrainSetTest.java` (new, 4 tests)
- `android/app/src/test/java/com/opensilkroadmap/app/data/NpcSpawnIndexTest.java` (new, 4 tests)
- `android/app/src/androidTest/java/com/opensilkroadmap/app/game/GameActivityTest.java` (rewritten for multi-sector)
- `scripts/test_phase15_world_integration.py` (new, 12 tests)
- `ANDROID_ASSET_DEPENDENCY_GRAPH.json` (4 new asset edges; 14 total)

## 7. Tests

**TESTED here (Python, executed):** `scripts/test_phase15_world_integration.py` —
12 tests (5 multi-sector terrain, 3 NPC placement, 4 `.o2` header). All 12 OK.
Related suites re-run green: `test_phase14_world_runtime` +
`test_world_terrain` + `test_phase13_world_relations` (51 tests, 1 skipped, OK).

**NOT EXECUTED (no JDK/Android SDK):**
- JVM unit tests `WorldTerrainSetTest` (4), `NpcSpawnIndexTest` (4).
- Instrumented test `GameActivityTest` (2).
- `./gradlew test` / `assembleDebug`.

## 8. Android build + runtime

- **Build: NOT EXECUTED** — no JDK/Gradle/Android SDK (`java`, `javac`, `gradle`
  not found; `ANDROID_HOME` unset).
- **APK execution: NOT EXECUTED** — no device/emulator.
- **Performance: NOT EXECUTED** — no benchmarks invented.

## 9. Remaining classification summary

- **BLOCKED:** object/model rendering (`.bms` vertex layout UNKNOWN); NPC model
  rendering (no decoded model); authentic player spawn.
- **UNKNOWN:** `.o2` variable header layout; `.bms` vertex record; `.nvm`
  nav-cell semantics.

## 10. What Phase 16 should do

1. Decode `.bms` vertex/index layout (blocked since Phase 13) to render real
   world-object geometry.
2. Decode `.bsr`/`.bsk` → attach real character skeletons/models; then replace
   NPC diagnostic markers with real models at verified `npcpos` positions.
3. Extend multi-sector world to full region streaming + runtime transitions.
4. Establish a real (verified) player spawn once source evidence exists.
5. Run the real Gradle build + instrumented tests in a JDK/Android SDK environment.
