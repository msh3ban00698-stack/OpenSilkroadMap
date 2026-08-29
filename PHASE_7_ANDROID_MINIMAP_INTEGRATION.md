# PHASE 7 — Android Minimap Pack Integration

## 1. Objective

Integrate the VERIFIED minimap assets (7,737 Phase 6 PNGs) into a safe,
manifest-driven Android-side asset/resource layer that proves the Android
application can:

1. locate minimap assets using the generated manifest,
2. resolve original PK2 paths to Android asset paths,
3. load minimap PNGs without loading the entire minimap collection,
4. respect bounded memory/resource usage,
5. handle missing/corrupt assets explicitly,
6. preserve source-to-output traceability,
7. provide a clean API that a future Android world/map renderer can consume.

This is an ASSET INTEGRATION phase. No gameplay, rendering, networking, or
server code was written.

## 2. Source of truth

- `android-assets/manifest.json` (7,755 records, schema `sro-android-assets-v2`)
  is the authoritative mapping. The resolver never guesses paths.
- Real assets under `android-assets/maps/` are the tested inputs.
- Repo docs: `README.md`, `ANDROID_ASSET_MANIFEST.md`,
  `PHASE_5_ANDROID_ASSET_CONVERSION.md`,
  `PHASE_6_BULK_ANDROID_ASSET_CONVERSION.md`, `VSRO_V193_SOURCE_INVENTORY.md`.

### Deviation from the Phase 7 spec premise

The Phase 7 spec states generated PNGs are "intentionally OUTSIDE Git". In
this repository the 7,737 PNGs were committed to git during Phase 6 by an
explicit user decision ("Commit the PNGs too", superseding the standing
no-massive-assets rule for that deliverable). This phase therefore did NOT
stage any new generated assets: it only adds code, tests, and documentation.
The already-committed PNGs are the test fixtures the Phase 7 tests run against.

## 3. Exact minimap inventory (VERIFIED)

Counts taken from `android-assets/manifest.json` (source of truth), cross-checked
against the filesystem (all 7,755 `output_path` files exist).

| Group | Count |
|---|---|
| Total manifest records | 7,755 (18 Phase 5 + 7,737 Phase 6) |
| Phase 6 minimap records | 7,737 |
| — `Media/minimap/*` | 5,523 |
| — `Media/minimap_d/<8 regions>/*` | 2,214 |
| Phase 5 non-minimap records (textures/audio/text) | 18 |
| Unique source PK2 paths | 7,753 |
| Unique output paths | 7,755 (no output-path collisions) |
| Source PK2 | `Media.pk2` only |

Regions in `minimap_d`: Arabia, donwhang, donwhang_event, egypt, flame_dungeon,
fort_dungeon, jinsi, jupiter.

### Format groups (VERIFIED)

Phase 6 minimap records by `detected_format`:

| Format | Count |
|---|---|
| `DDJ+DDS(DXT1)` | 7,441 |
| `DDJ+DDS(RGB32/(16711680, 65280, 255, 4278190080))` | 283 |
| `DDJ+DDS(RGB32/(16711680, 65280, 255, 0))` | 13 |

All outputs are PNG (bit depth 8; color type 6 = RGBA or 2 = RGB). The Phase 5
records use `JMXVDDJ+DDS` / `text/UTF-16LE` / `text/ASCII` / `copy` labels.

### Dimension groups (VERIFIED)

Phase 6 records carry two dimension pairs:
- `width`/`height` = PNG/DDS-padded dimensions of the actual output file.
- `logical_width`/`logical_height` = original minimap logical size.

Padded output dimensions (all records with a `width`): 256×256 (7,731),
384×384 (8), and one each of 512×512, 104×104, 44×44, 8×12, 256×128, 128×128,
1024×768, 1024×1024 (the last two are Phase 5 textures).

Distinct logical dimension groups: 6,105. Logical-width distribution
(Phase 6): ≤ 100 px → 2,399; 101–256 px → 5,338; none > 256 px.

Output sizes (Phase 6): min 659 B, max 187,769 B, median ~69,293 B, total
~408 MB.

## 4. Manifest mapping

Phase 5 and Phase 6 both converted two of the same sources, so two
`source_path` values appear twice (Phase 5 + Phase 6 records):
- `/minimap/100x100.ddj`
- `/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj`

Collision policy (deterministic, documented, not a guess): the resolver keys
records by the exact normalized PK2 source path (no basename-only matching)
and, for duplicates, prefers the later phase (Phase 6) with a stable
tie-break on output path. `resolveAll()` exposes every record for a source;
`duplicateSources()` reports the 2 colliding sources.

## 5. Android asset resolution design (VERIFIED)

The Android client is the `map/` web app running in the Capacitor WebView
(`capacitor.config.ts` → `webDir: "map/dist"`). The asset layer therefore
lives in `map/src/game/minimap_assets.ts`, which is exactly the code the
Android app runs. Flow:

```
PK2 source path (e.g. "/minimap/100x100.ddj")
      ↓  MinimapManifestResolver.resolve(sourcePath)
Android asset path (e.g. "maps/minimap/100x100.png")
      ↓  MinimapAssetLoader.load(sourcePath)  [bounded, no preload]
PNG bytes → validated (signature, IHDR dims, chunk CRC, sha256)
      ↓  BoundedMinimapCache / CachedMinimapLoader
LoadedMinimap (bytes + parsed info + record + verified sha256)
```

`MinimapManifestResolver`:
- indexes all records by exact normalized `source_path` and `output_path`,
- `resolve(sourcePath)` → explicit `MinimapResolutionError` if missing,
- `resolveByOutputPath()` for reverse lookup,
- no fuzzy/alternate-path guessing, no filename-only matching.

## 6. Loader API / design (VERIFIED)

`MinimapAssetLoader` (constructor takes a resolver + optional `{ reader,
verifySha256 }`). `load(sourcePath)`:
1. `resolver.resolve()` (explicit error if no record),
2. read exactly one asset through the `AssetReader` (default
   `fetchAssetReader` against `MINIMAP_ASSET_BASE_URL`, injectable for tests),
3. `validatePngBytes()` → explicit `MinimapValidationError` on bad
   signature / IHDR / chunk CRC / missing IEND / trailing data,
4. verify PNG header dimensions == manifest `width`/`height`, and logical
   dimensions are within `(0, padded]`,
5. verify SHA-256 of loaded bytes == manifest `output_sha256` (traceability;
   on by default, disable via `verifySha256: false`),
6. return `LoadedMinimap { record, png, bytes, sizeBytes, sha256 }`.

Error taxonomy: `MinimapManifestError` (bad manifest), `MinimapResolutionError`
(missing source), `MinimapLoadError` (missing/unreadable output), 
`MinimapValidationError` (corrupt/mismatched asset). Missing and corrupt
assets are NEVER silently ignored.

## 7. Cache policy (VERIFIED)

`BoundedMinimapCache` is an LRU cache bounded by BOTH `maxBytes`
(default 8 MiB) and `maxEntries` (default 64). `CachedMinimapLoader` wraps the
loader: hit → return cached; miss → load once, put, evict oldest until within
bounds. `stats()` reports entries/bytes/hits/misses/evictions/limits.
`release(sourcePath)` drops one entry; `releaseAll()` empties the cache.

There is no pre-existing image/resource cache in the Capacitor shell or the
map app to reuse, so this bounded cache is the single minimap cache; no second
competing cache was created.

## 8. Memory / resource policy (VERIFIED in logic; NOT EXECUTED on device)

- The loader NEVER loads the complete minimap collection. One request = one
  read of exactly one output path; the test asserts the reader is called
  exactly once per requested asset and never for unrequested paths (no
  full-directory preload).
- The cache holds only the bounded set; evicted entries release their byte
  references and the byte accounting drops.
- Memory-policy contract is enforced by cache byte/entry accounting in Deno
  tests (measurable in this environment). Actual heap growth and GPU/bitmap
  staging on a real Android device cannot be measured here — see Section 12.

## 9. Validation method (VERIFIED)

Pure-TS `validatePngBytes` performs: 8-byte PNG signature, IHDR (length 13,
first chunk), width/height/bitDepth/colorType parse, full chunk-structure walk
with CRC32 (IEEE, standard table) on every chunk, mandatory terminating IEND,
and rejects trailing bytes. sha256 via `crypto.subtle`. Both were verified to
pass on all real assets in the controlled set and to fail on tampered input.

## 10. Real-asset proof (VERIFIED)

All loading tests use REAL committed assets (no synthetic images) through the
same `MinimapAssetLoader` a future renderer would use. Controlled set covering
small / medium / large / minimap_d / different source paths:

| Source path (PK2) | Logical | Output |
|---|---|---|
| `/minimap/27x53.ddj` | 27×53 | `maps/minimap/27x53.png` |
| `/minimap/100x100.ddj` | 100×100 | `maps/minimap/100x100.png` |
| `/minimap/105x101.ddj` | 105×101 | `maps/minimap/105x101.png` |
| `/minimap/237x124.ddj` | 237×124 | `maps/minimap/237x124.png` |
| `/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj` | 127×127 | `maps/minimap_d/Arabia/…127x127.png` |
| `/minimap_d/jupiter/jupiter_a_237x124.ddj` | 237×124 | `maps/minimap_d/jupiter/…237x124.png` |

For each: `sha256(loaded bytes) == manifest output_sha256`, PNG padded
dimensions 256×256, `sizeBytes == manifest output_size`, logical dimensions
match manifest. Sources were NOT modified.

## 11. Test results (VERIFIED)

New `map/src/game/minimap_assets.test.ts` — 19 tests covering all 12 required
categories:

| # | Category | Status |
|---|---|---|
| 1 | manifest parsing | PASS |
| 2 | minimap record lookup | PASS |
| 3 | path resolution (both directions) | PASS |
| 4 | missing asset handling (resolver + loader) | PASS |
| 5 | corrupt asset handling (IDAT corruption, non-PNG, bad signature) | PASS |
| 6 | dimension verification (match + mismatch rejection) | PASS |
| 7 | format verification (color type/bit depth, tampered signature) | PASS |
| 8 | collision safety (2 duplicate sources → Phase 6, exact-path keys) | PASS |
| 9 | bounded cache behavior (limits, evictions, hits, misses) | PASS |
| 10 | resource release (single, bulk clear, byte accounting) | PASS |
| 11 | representative real-asset loading + sha256 traceability | PASS |
| 12 | deterministic manifest resolution + repeated-load byte identity | PASS |
| + | sequential loads stay memory-bounded, no directory preload | PASS |

Full matrix (all previously passing suites still pass):

| Suite | Result |
|---|---|
| `deno test src/game/` (incl. new Phase 7) | 27 passed / 0 failed |
| `tsc` (project typecheck, `deno task build` first step) | exit 0 |
| `python3 scripts/test_pk2_reader.py` | 11 OK |
| `python3 scripts/test_sro_pipeline.py` | 15 OK |
| `python3 scripts/test_phase4_assets.py` | 5 OK (3 skipped) |
| `python3 scripts/test_phase5_assets.py` | 18 OK (1 skipped) |
| `python3 scripts/test_phase6_assets.py` | 17 OK (4 skipped) |
| `python3 scripts/validate_pk2.py` (real archives, read-only) | OK |

## 12. Android-runtime test status

- Android emulator/device: **NOT EXECUTED** — no JDK, no Android SDK, and no
  emulator/device exist in this environment (verified: `java`/`javac`/`gradle`
  absent, `ANDROID_HOME`/`ANDROID_SDK_ROOT` unset). No Android-runtime numbers
  are fabricated.
- What the resolver/asset layer runs on today: the Deno test environment and
  the browser/WebView via `map/dist` (the Capacitor webDir). The TypeScript
  module itself is the code that will run on Android.

### Remains to be tested on-device (UNKNOWN here)

- Actual heap/JS-Heap memory growth and GC behavior while cycling minimaps.
- WebView `fetch` of the manifest + PNGs from bundled app assets
  (`/assets/android/…` path, Vite/Capacitor asset serving).
- Decoding the PNG bytes to a `THREE.Texture`/canvas bitmap and its GPU memory
  cost; cache eviction releasing decoded bitmap references.
- `crypto.subtle` availability/behavior inside the Android WebView for
  per-load sha256 verification.

## 13. Known limitations

- sha256 verification is CPU work per load; it is on by default for
  traceability and can be disabled (`verifySha256: false`) if the future
  renderer needs the fastest path.
- `MINIMAP_ASSET_BASE_URL` defaults to `/assets/android/`; wiring the
  `android-assets/` tree into the Capacitor bundle/`map/dist` is app plumbing
  that belongs to a future phase.
- The layer verifies the PNG byte stream; it does not decode pixels (no
  gameplay/rendering in scope).
- 6,105 distinct logical dimension groups means a future renderer must scale
  each logical size to the padded texture; this is documented, not assumed.

## 14. Exact next-phase recommendation (ONE phase only, NOT executed)

**Phase 8 — HUD minimap rendering:** wire `MinimapAssetResolver` +
`CachedMinimapLoader` into the existing HUD minimap (`map/src/game/hud.ts`
`#hud-minimap` canvas), replacing the current procedural dot-only minimap with
the real minimap image for the active region (resolved by region source
path), including on-device Android memory/decoding validation once a device
or emulator is available. This is the smallest phase that exercises the asset
layer end-to-end without introducing gameplay.

## Status legend

- **VERIFIED** — executed and proven in this environment (all tests above).
- **NOT EXECUTED** — Android device/emulator runtime validation.
- **UNKNOWN** — on-device memory/decoding behavior not measurable here.

No device compatibility is claimed: nothing was tested on Android hardware.
