# Phase 8 — Native Android Minimap Renderer

Date: 2026-08-29
Branch: `260829-phase8-native-minimap`
Status: delivered as a native Java module + tests + runnable verification; the
JVM/Android test steps are **NOT EXECUTED** in this environment (no JDK, no
Android SDK, no emulator).

## 1. Goal and Scope

Phase 8 is the first step off the WebView path: a **real native Android
minimap renderer** written in Java that consumes the verified Phase 6/7 Android
asset collection (`android-assets/manifest.json` + PNGs) and draws minimaps
through a custom Android `View`. It is the native counterpart of the Phase 7
TypeScript layer (`map/src/game/minimap_assets.ts`) and is structured so that:

- the **logic core** (manifest resolution, fit math, bounded cache) is
  **Android-free** and compiles as JVM unit tests under `./gradlew test`;
- the **Android-only** parts (Bitmap decode, `View` drawing) are isolated in
  small, thin classes and covered by instrumented tests under
  `./gradlew connectedAndroidTest`;
- proof-of-render is done with **real verified assets** copied into a
  gitignored asset directory, so no large PNGs are committed.

No gameplay, networking, authentication, or GameServer logic is implemented
(spec Phase 8 explicitly defers those). No PK2 archives are read or modified.

## 2. Inventory

### 2.1 New native module — `android/app/src/main/java/com/opensilkroadmap/app/minimap/`

| File | Lines | Role |
|------|-------|------|
| `MinimapException.java` | 51 | Exception hierarchy: `ManifestParseException`, `ResolutionException`, `MissingAssetException`, `InvalidAssetException`, `DimensionMismatchException` |
| `ManifestData.java` | 93 | Plain data: `ManifestData` + nested `MinimapRecord` + `ResolvedAsset` |
| `ManifestParser.java` | 121 | `org.json`-based manifest parse, bounded 32 MB read, source-path normalization (Android-only via `org.json`) |
| `ManifestResolver.java` | 162 | Exact-path keys, later-phase preference (phase6 > phase5), `resolveAll`/`reverse`/`duplicateSources`; **no Android deps** |
| `DecodedAsset.java` | 18 | Decoded-payload contract (`width`, `height`, `sizeBytes`, `release`) |
| `BitmapAsset.java` | 55 | Decoded payload backed by `Bitmap`; recycles on `release` (Android-only) |
| `AssetDecoder.java` | 13 | Decoder SPI (`decode(key, InputStream)` → `DecodedAsset`) |
| `BitmapFactoryDecoder.java` | 18 | `BitmapFactory` decoder with in-bounds sampling, downscale-safe (Android-only) |
| `NativeMinimapAssetProvider.java` | 201 | Resolver + `AssetReader` + `AssetDecoder` wiring; LRU cache bounded by bytes and entries; dimension-validated loads; `release`/`releaseAll`/`stats` |
| `FitMath.java` | 96 | Fit-scale, `clampZoom` (1..4), source-viewport crop; **no Android deps** |
| `NativeMinimapRenderer.java` | 150 | Custom `View`: `setMinimap`/`setZoom`/`setPlayerPosition`/`reset`, bounded zoom, TEST ONLY marker, caller owns bitmaps |

Total: 11 files, 978 lines, all in package `com.opensilkroadmap.app.minimap`.

### 2.2 New JVM unit tests — `android/app/src/test/java/com/opensilkroadmap/app/minimap/`

| File | Tests | Lines |
|------|-------|-------|
| `ManifestResolverTest.java` | 8 | exact-path keys, phase preference, duplicates, determinism, reverse, source-prefix rejection |
| `FitMathTest.java` | 7 | fit scale, clampZoom bounds, viewport crop, degenerate inputs (incl. zero-viewport guard) |
| `NativeMinimapAssetProviderTest.java` | 12 | bounded LRU (bytes + entries), no preload, dimension-mismatch release, sequential-bounded memory |

Total: 3 files, 27 tests, 542 lines. All import only JUnit + `java.*` + the
module, so they run under `./gradlew test` (JVM, no device).

### 2.3 New instrumented tests — `android/app/src/androidTest/java/com/opensilkroadmap/app/minimap/`

| File | Tests | Lines |
|------|-------|-------|
| `NativeMinimapRendererTest.java` | 12 | on-device: missing/corrupt/cached/bounded/sequential-render tests + pixel-probe proof, reading real assets from `minimap_proof/` |

Total: 1 file, 12 tests, 273 lines. Run under `./gradlew connectedAndroidTest`.

### 2.4 New verification/prepare scripts — `scripts/`

| File | Lines | Role |
|------|-------|------|
| `verify_phase8_manifest_rules.py` | 150 | Re-derives the native resolution contract from the real manifest in pure Python; prints PASS/FAIL invariants (see §6) |
| `prepare_phase8_proof_assets.py` | 112 | Copies the manifest + 5 verified real PNGs into the gitignored `android/app/src/main/assets/minimap_proof/` and records sha256 |

## 3. Design

### 3.1 Data flow

```
android-assets/manifest.json
        │ ManifestParser.parse (org.json, ≤32 MB, normalizes source paths)
        ▼
ManifestData (records) ──► ManifestResolver (exact-path keys, phase6 > phase5)
        │                            │
        │ resolver.resolve(srcPath)  │ (Android-free, unit-testable)
        ▼                            ▼
NativeMinimapAssetProvider.load(sourcePath)
        │ AssetReader.open(relativeOutputPath)
        ▼
BitmapFactoryDecoder.decode  ──►  DecodedAsset (BitmapAsset)
        │ validate(record, asset)  (dimension + logical-range check)
        ▼
bounded LRU (bytes + entries) ──►  NativeMinimapRenderer.setMinimap(...)
                                        │
                                        ▼
                                 View.onDraw → Canvas.drawBitmap (bounded zoom)
```

### 3.2 Resolution contract (identical to Phase 7)

- Keys are exact normalized source paths (`/minimap/27x53.ddj`), never guessed.
- Duplicate source paths (2 total) resolve by later phase (phase6 wins).
- The manifest's `output` field is the Android asset path; `source_path` is the
  PK2-internal path; `logical_width`/`logical_height` are the SRO logical
  dimensions; `width`/`height` are the PNG pixel dimensions (all verified in
  `verify_phase8_manifest_rules.py`).

### 3.3 Memory contract

- The provider **never preloads** the collection; only requested minimaps are
  decoded.
- LRU bounds: default 8 MiB / 64 entries; both configurable and validated
  positive.
- Evicted payloads are released (`Bitmap.recycle` via `BitmapAsset.release`);
  the renderer **never** releases bitmaps (caller owns them) — the provider is
  the sole release path.
- `releaseAll()` tears the cache down for lifecycle end.

### 3.4 Renderer contract

- `setMinimap(ResolvedMinimap)` shows the (already provider-owned) bitmap; zoom
  is clamped to `[1,4]`; a player position (world px) is mapped into the view
  via `FitMath` (fit + crop).
- `setTestMarkerVisible(true)` renders a TEST ONLY marker (only on request);
  the label `TEST ONLY` is drawn next to it. `reset()` clears the screen and
  marker.
- `onDraw` renders the "no minimap" background until a minimap is set.

## 4. Verification

### 4.1 Runned in this environment

| Check | Result |
|-------|--------|
| `python3 scripts/verify_phase8_manifest_rules.py` | **PASS** (see invariants below) |
| `python3 scripts/prepare_phase8_proof_assets.py` | **PASS** (5 proof assets + manifest copied, gitignored) |
| Full pre-existing test matrix (regression) | all **PASS** (see §4.2) |

`verify_phase8_manifest_rules.py` invariants (re-derived from the real
manifest, not from the Java code):

- records = 7755, phase6 records = 7737, targets.total = 7737
- unique sources = 7753, unique outputs = 7755, duplicates =
  `['/minimap/100x100.ddj', '/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj']`
- phase-6 preference resolves both duplicates deterministically
- sha256 verified for all 5 proof assets
- no basename collisions among phase-6 outputs
- deterministic across repeated runs

### 4.2 Regression matrix (all pre-existing suites re-run)

| Suite | Result |
|-------|--------|
| Deno game suite (`map/src/game/`) | 27 passed, 0 failed |
| `tsc` + `vite build` (`deno task build`) | exit 0 |
| `test_pk2_reader.py` | 11 OK |
| `test_sro_pipeline.py` | 15 OK |
| `test_phase4_assets.py` | 5 OK (3 skipped) |
| `test_phase5_assets.py` | 18 OK (1 skipped) |
| `test_phase6_assets.py` | 17 OK (4 skipped) |
| `validate_pk2.py` | **NOT RUNNABLE here** — pinned `pk2_mate` binary not present in this environment (passed in prior env); read-only by design |

### 4.3 NOT EXECUTED (no toolchain / no device)

| Check | Status | Reason |
|-------|--------|--------|
| `./gradlew test` (JVM unit tests) | **NOT EXECUTED** | no `java`/`javac`/`gradle`/JDK in environment |
| `./gradlew connectedAndroidTest` (instrumented) | **NOT EXECUTED** | no Android SDK, no `adb`/`emulator` device |

The Android/JVM runtime status is honestly **UNKNOWN** — no fake execution is
claimed. Structural sanity was performed instead: brace/paren balance and
Java-9+-construct scan across all 15 new Java files **PASS**; the logic-core
files (resolver, fit math, provider cache, tests) contain **zero**
`android.*` imports, so they compile as plain JVM tests once a JDK is present.

## 5. Reproducing

```shell
# 1. Manifest-resolution invariants (runs anywhere, pure Python)
python3 scripts/verify_phase8_manifest_rules.py

# 2. Prepare gitignored real proof assets for instrumented tests
python3 scripts/prepare_phase8_proof_assets.py

# 3. JVM unit tests (needs JDK 17 + Android Gradle Plugin toolchain)
cd android && ./gradlew test

# 4. Instrumented renderer tests (needs a device/emulator)
cd android && ./gradlew connectedAndroidTest
```

## 6. Files Changed

- `android/app/src/main/java/com/opensilkroadmap/app/minimap/` (11 new files, §2.1)
- `android/app/src/test/java/com/opensilkroadmap/app/minimap/` (3 new files, §2.2)
- `android/app/src/androidTest/java/com/opensilkroadmap/app/minimap/NativeMinimapRendererTest.java` (new)
- `scripts/verify_phase8_manifest_rules.py` (new)
- `scripts/prepare_phase8_proof_assets.py` (new)
- `android/.gitignore` (ignores `app/src/main/assets/minimap_proof` and `app/src/main/assets/public`)
- `README.md` (§2e pointer)

No PK2 archives, no PNGs committed (proof assets are gitignored).

## 7. Blockers / Next Phase

- **No JDK / Android SDK / emulator**: JVM and instrumented tests cannot be
  executed here. They are written and structurally validated, but
  `./gradlew test` and `./gradlew connectedAndroidTest` must be run in a
  toolchain-equipped environment before the renderer can be considered
  runtime-proven.
- Recommended next phase: wire `NativeMinimapRenderer` into the activity as a
  real HUD overlay (native, not WebView), drive it from a native source of
  player coordinates, and run the instrumented suite on an emulator to confirm
  pixel-level rendering of real assets.
