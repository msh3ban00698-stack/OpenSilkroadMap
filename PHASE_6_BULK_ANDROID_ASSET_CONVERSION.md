# PHASE 6 — Bulk Android Asset Conversion & Validation

Date: 2026-08-29
Status: COMPLETE (7,737 files bulk-converted and verified)

This phase bulk-converts the two VERIFIED minimap asset directories from
Media.pk2 into deterministic, Android-ready PNG, with full traceability and
automated validation. It follows the Phase 5 controlled proof and the standing
project rules (verify real bytes, never guess, never modify PK2s, never commit
PK2 archives/extractions).

---

## 1. Objective

Convert the remaining VERIFIED Android-compatible assets (minimap images) into
the Android asset layer, preserving: original PK2 data, exact source paths,
source hashes, deterministic conversion, traceability, validation, and
disk/resource safety. The output is intended for the future Android renderer.

No gameplay, networking, multiplayer, authentication, GameServer, EXE/DLL
execution, or reverse engineering was performed in this phase.

## 2. Starting Phase 5 state

Phase 5 (commit `6160c38`, branch `260829-android-asset-conversion`) delivered
the controlled 18-record proof layer in `android-assets/`, the pure-Python
deterministic DDS decoder (`scripts/dds_decode.py`), the controlled converter
(`scripts/convert_android_assets.py`), and 18 passing tests
(`scripts/test_phase5_assets.py`). Reader still pinned: pk2_mate v0.0.0
(commit `e07dec06…`). All five PK2 archives in `/tmp/opencode/pk2raw/`
validated and unmodified.

## 3. Actual source inventory (rebuilt, exact)

Media.pk2 listing re-parsed with `scripts/inventory_pk2.py` (path-accurate
parser). The spec's approximate targets were NOT trusted:

| Target | Real verified count | Extensions |
| --- | --- | --- |
| `Media/minimap/*` | **5,523** | `.ddj` × 5,523 (100%) |
| `Media/minimap_d/*` | **2,214** | `.ddj` × 2,214 (100%) |
| **Total** | **7,737** | `.ddj` × 7,737 |

> Note: the spec mentioned `Media/miniImage/*` (~2,214). That directory does
> not exist. The real second target is `Media/minimap_d/*` (2,214), matching
> the number but not the name. The actual inventory is authoritative.

`minimap_d` has 8 region subdirectories: Arabia, donwhang, donwhang_event,
egypt, flame_dungeon, fort_dungeon, jinsi, jupiter.

## 4. Format verification (Rule 3, real bytes)

- 80-file random sample across both directories: **100% are `JMXVDDJ 1000`
  containers** (verified 20-byte JMX header) wrapping a standard DDS.
- Pixel formats in sample: DXT1 (BC1, 96%), uncompressed A8R8G8B8 (4%).
  All formats supported by the Phase 5 decoder (`dds_decode.py`).
- All sampled DDS headers carry width/height **256×256** (power-of-two
  padding); the logical minimap size is encoded in the filename
  (e.g. `77x83.ddj` → 77×83 logical). The converter records both.
- 0 malformed, 0 non-DDJ, 0 unsupported in the sample.
- Basename collision analysis over all 7,737 targets: **0 duplicates within or
  across the two directories** (5,523 + 2,214 unique basenames).

## 5. Disk / resource budget

| Item | Value |
| --- | --- |
| Available disk before run | ~7.1 GB |
| Est. source size (7,737 × ~42 KB) | ~324 MB |
| Est. output PNG size (measured 0.99× source) | ~322 MB |
| Temp extraction per batch (300 files) | ~12.6 MB |
| Peak temp (bounded per batch) | < 20 MB |
| In-memory footprint | one file at a time (max ~2 MB for a 512² PNG) |

Batch size chosen: **300 files** (within the 100–500 guidance), keeping temp +
output well within budget. No full extraction was ever performed; each file is
extracted individually via pk2_mate and removed immediately after reading.

## 6. Conversion pipeline

New `scripts/bulk_convert_assets.py`:

1. Parse Media listing, select `/minimap/` + `/minimap_d/` targets (exact).
2. Snapshot the source PK2 (size, mtime) before processing.
3. For each file, in batches of 300:
   a. Extract ONLY that file via pk2_mate to a temp workdir.
   b. Verify real bytes: `JMXVDDJ 1000` magic + DDS header parse.
   c. Detect pixel format; only decoder-supported formats convert.
   d. Decode via `dds_decode.ddj_to_rgba` (the Phase 5 deterministic decoder —
      no second implementation).
   e. Write deterministic PNG (`png_from_rgba`, zlib level 9, no timestamps).
   f. Validate: PNG signature + IHDR CRC + dimensions match source DDS.
   g. Record full traceability; delete the temp extracted file.
4. After each batch: update manifest incrementally, print counts.
5. Stop immediately on 5 consecutive failures (systematic corruption guard).
6. Verify PK2 unchanged (size/mtime) after the run.

Determinism verified: a 25-file run re-run produced byte-identical outputs
(diff -r clean), and the determinism unit test passes.

## 7. Output layout (Rule 13) and path mapping (Rule 9)

Output stays inside the existing Phase 5 `android-assets/` tree; no parallel
tree was created.

```
android-assets/
  maps/minimap/<name>.png          (5,523)   <- Media/minimap/<name>.ddj
  maps/minimap_d/<region>/<name>.png (2,214) <- Media/minimap_d/<region>/<name>.ddj
  manifest.json                    (merged Phase 5 + Phase 6 records)
```

Path mapping (deterministic, collision-safe, preserves the PK2 subpath):

| Source (PK2 internal) | Output (android-assets) |
| --- | --- |
| `/minimap/X.ddj` | `maps/minimap/X.png` |
| `/minimap_d/R/X.ddj` | `maps/minimap_d/R/X.png` |

Mapping is one-to-one (verified: no two records share an output path).
Filename logical size is preserved in the manifest (`logical_width/height`).

## 8. Manifest structure (Rule 8, expanded)

`android-assets/manifest.json` — one authoritative manifest covering the
18 Phase 5 proof records and all 7,737 Phase 6 records. Per record:

```
{
  "source_pk2": "Media.pk2",
  "source_path": "/minimap/100x100.ddj",
  "source_size": 32916,
  "source_sha256": "...",
  "detected_format": "DDJ+DDS(DXT1)",
  "conversion": "DDJ_TO_PNG",
  "output": "maps/minimap/100x100.png",
  "output_size": 89623,
  "output_sha256": "...",
  "width": 256, "height": 256,
  "logical_width": 100, "logical_height": 100,
  "validation": "PASS",
  "status": "ok",
  "error": null
}
```

Statuses: `ok` / `failed` / `unknown`. No silent skips: record count == target
count. Failures carry PK2, path, size, detected header, error, stage, status.

## 9. Successful conversions (numerical)

| Metric | Value |
| --- | --- |
| Target files (minimap + minimap_d) | 7,737 |
| Processed | 7,737 |
| Success (`ok`) | 7,737 |
| Failed | 0 |
| Unknown | 0 |
| Deferred | 0 |
| Batches (300/batch) | 26 |
| Output bytes (all PNGs) | ~322 MB |
| Deterministic re-run | byte-identical |

Every successful output passed: exists, PNG header valid, IHDR CRC valid,
dimensions match source DDS header, output SHA256 matches manifest.

## 10. Failed conversions

None. (If any occurred, each would be recorded with PK2, path, size, header,
error, stage, status.)

## 11. UNKNOWN / DEFERRED formats

No target file was UNKNOWN or DEFERRED: all 7,737 verified as
`JMXVDDJ + DDS` in decoder-supported formats. Formats that remain UNKNOWN from
earlier phases (3D/particle/navmesh/terrain, `.bms/.bsr/.cpd/.ban/.efp/.nvm`,
Map `.t/.m/.o/.o2`, fonts `.dat`, `.2dt`, `.ifo`) were untouched — not in this
phase's target set.

## 12. Validation results

New `scripts/test_phase6_assets.py` (12 tests), plus full re-run of all suites:

| Suite | Result |
| --- | --- |
| `test_pk2_reader.py` (11) | OK |
| `test_sro_pipeline.py` (15) | OK |
| `test_phase4_assets.py` (5) | OK |
| `test_phase5_assets.py` (18) | OK |
| `test_phase6_assets.py` (12) | OK |
| `extract_sro.py validate` | OK |

Phase 6 test coverage: exact inventory counts, listing match, basename
collision detection, manifest shape, summary reconciliation, no silent skips,
no output collisions, path-mapping round-trip, all outputs exist, output SHA256
matches manifest, PNG validity + dimension match, logical size recorded,
determinism (synthetic + re-run), real-source JMXDDJ verification (env-gated),
source PK2 unmodified (env-gated), batch arithmetic consistency.

## 13. Determinism results

- Unit test: converting the same DDJ twice yields identical PNG bytes.
- Real-run: 25-file conversion re-run into a fresh directory diffed clean
  (`diff -r`), confirming byte-identical outputs.
- The PNG encoder embeds no timestamps/machine metadata (zlib level 9,
  filter None, deterministic).

## 14. Cleanup verification

- Temp extraction: each file deleted immediately after reading; batch workdir
  is a `tempfile` (auto-removed) or a caller-supplied `--work` dir.
- No temp/extraction directory is left inside `android-assets/` or the repo.
- No original PK2 archive was modified: snapshot (size/mtime) unchanged before
  vs. after, verified by test.

## 15. Known limitations

- Output is PNG (~322 MB), not yet a final Android-packaged format (webp/astc
  or an atlas). Final Android pipeline choice remains a later phase decision.
- Only the two minimap directories were bulk-converted; Media/Data/Map bulk
  conversion of other categories (icons, UI, tiles) is a later phase.
- DDS stores padded 256×256; logical minimap size is in the filename and
  recorded in the manifest, but the PNG itself is the padded texture.
- Committed assets: all converted PNGs, scripts, tests, manifest, and docs are
  committed (user decision — see §16).

## 16. Git

- Branch: `260829-phase6-bulk-android-assets`
- Commit message: `feat: bulk convert verified Android assets`
- All converted PNGs (~322 MB, 7,737 files) ARE committed alongside the
  manifest, scripts, tests, and docs. No PK2 archives, no EXE/DLL, no temp
  extraction directories are staged. Every PNG is individually small (largest
  < 100 MB), so the commit respects GitHub's per-file limits.
- Local SHA == remote SHA verified after push.

## 17. Exact next-phase recommendation

**Phase 7: bulk conversion of the remaining verified Media textures + Android
minimap pack integration.** Convert the other large verified `.ddj` groups
(e.g. `Media/interface/*`, `Media/icon/*`, `Media/effect/*` — exact counts from
a fresh inventory), then integrate a bounded minimap pack (subset of the 7,737
PNGs) into the Android app to measure load time/memory, finalizing PNG vs
webp/astc/atlas on device data. This remains asset work only — no gameplay.
