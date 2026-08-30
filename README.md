# OpenSilkroadMap

The hackable [**Silkroad Online**](http://www.joymax.com/silkroad/) world map.

![map](map.png)

## Features

- Explore the world map, dungeons and navmeshes
- Search objects (NPCs, teleporters)
- [NavLink](https://github.com/Silkroad-Developer-Community/Silkroad-NavLink) integration
- Teleport actions, displays
- Show coordinates, region on hover
- Cachable zoom levels
- Generate maps for any Silkroad Online version with only a few scripts

## Getting Started

### Prerequisites

- [Node.js](https://deno.com/) (v18+)
- [Python 3.10+](https://www.python.org/) with [uv](https://github.com/astral-sh/uv) (recommended) or standard pip for asset processing.

### 1. Install Dependencies

```shell
deno install
```

### 2. Extracting Client Files (.pk2)

Canonical pipeline (vSRO 1.193):

```
PK2 root -> extract -> game_source/ -> generate -> map/public/assets/gamedata/
```

This repository does **not** include `pk2reader.py` / `jmblowfish.py`. Supply them
next to the archives with `--reader-dir` (defaults to `--pk2-dir`). Expected API:
`PK2(path)`, `.find(path)`, `.read_file(entry)`. Blowfish key for these archives
is `169841` (see `EXTERNAL_PACKAGE_INVENTORY.md`). Nested client/server/DB/PK2
listings and blockers: `VSRO_V193_SOURCE_INVENTORY.md`. `Media.pk2` is in
`VSRO-R Client.7z`; the other four PK2s are in `PK2 Files.7z`.

Expected layout (either flat or nested):

```
<pk2-dir>/
  Data.pk2  Map.pk2  Media.pk2  Music.pk2
  listing_media.txt  listing_music.txt   # optional, for UI/icon/audio extractors
```

or `<pk2-dir>/pk2/*.pk2` with listings next to `pk2/`.

Do not hardcode a machine path. Pass `--pk2-dir` / `--output-dir` or set
`SRO_PK2_DIR`, `SRO_READER_DIR`, `SRO_SOURCE_DIR`, `SRO_OUTPUT_DIR`.

Validate without archives:

```shell
python3 scripts/extract_sro.py validate
python3 scripts/test_sro_pipeline.py
```

Extract + generate when you have PK2s and the reader:

```shell
python3 scripts/extract_sro.py extract --pk2-dir /path/to/pk2s --reader-dir /path/to/reader
python3 scripts/extract_sro.py generate --source-dir game_source --output-dir map/public/assets/gamedata
```

You can also extract archives with [pk2_mate](https://github.com/Veykril/pk2/releases)
into `game_source/` and skip the in-repo PK2 reader:

```shell
mkdir game_source
pk2_mate extract --archive "C:\Games\SRO\Media.pk2" --out game_source/Media
pk2_mate extract --archive "C:\Games\SRO\Data.pk2" --out game_source/Data
pk2_mate extract --archive "C:\Games\SRO\Map.pk2" --out game_source/Map
```

`map/src/game/data/` is the committed Phase H starter JSON (bundled). Full
`map/public/assets/gamedata/` is generated and optional at runtime (shops/quests
degrade if missing). Do not commit PK2 archives or `game_source/`.

Phase 4 asset foundation (reproducible against real archives; raw PK2s and any
large extraction must live OUTSIDE the repo):

```shell
# 1. Validate + inventory (needs a pinned pk2_mate binary)
python3 scripts/validate_pk2.py --pk2-dir /tmp/opencode/pk2raw --reader-bin /tmp/opencode/pk2_mate
pk2_mate list --archive /tmp/opencode/pk2raw/Media.pk2 > /tmp/opencode/phase4/listings/Media.list.txt
python3 scripts/inventory_pk2.py --json /tmp/opencode/phase4/listings/Media.list.txt

# 2. Controlled extraction of curated samples (35, all categories)
python3 scripts/extract_samples.py --pk2-dir /tmp/opencode/pk2raw \
  --reader-bin /tmp/opencode/pk2_mate --out /tmp/opencode/phase4/extract \
  --json /tmp/opencode/phase4/extract_report.json

# 3. Tests
SRO_READER_BIN=/tmp/opencode/pk2_mate python3 scripts/test_phase4_assets.py
```

Verified per-archive SHA256, real sizes, format taxonomy (magic bytes) and the
Android suitability table live in `ANDROID_ASSET_MANIFEST.md`.
`PK2_READER_FOUNDATION.md` documents the pinned reader + format constants.

### 2b. Android asset conversion (Phase 5, controlled proof)

Converts only formats VERIFIED from real bytes (DDJ->PNG, OGG/WAV copy,
UTF-16LE/ASCII text -> UTF-8). Deterministic pure-Python DDS decoder; no bulk
conversion. Outputs + traceability: `android-assets/` + `manifest.json`.

```shell
python3 scripts/convert_android_assets.py \
  --pk2-dir /path/to/pk2s --reader-bin /path/to/pk2_mate \
  --out android-assets

# Cross-check the pure-Python decoder against Pillow on real samples:
SRO_PHASE5_SAMPLES=/path/to/phase4/extract python3 scripts/test_phase5_assets.py
```

`PHASE_5_ANDROID_ASSET_CONVERSION.md` documents scope, verified formats, the
UNKNOWN table, and the exact next-phase recommendation.

### 2c. Bulk minimap conversion (Phase 6)

Bulk-converts the verified minimap directories (`Media/minimap/*` = 5,523,
`Media/minimap_d/*` = 2,214) into deterministic PNG in bounded 300-file batches.
Batches respect the disk budget; each file is extracted individually and the
temp copy is removed immediately. Requires a `Media.list.txt` from
`pk2_mate list --archive Media.pk2`.

```shell
python3 scripts/bulk_convert_assets.py \
  --pk2-dir /path/to/pk2s --reader-bin /path/to/pk2_mate \
  --listing /path/to/Media.list.txt --out android-assets \
  --batch-size 300 --manifest /path/to/manifest.json

# Tests (real-bytes checks need the PK2 dir + listing):
SRO_PHASE6_PK2_DIR=/path/to/pk2s SRO_READER_BIN=/path/to/pk2_mate \
  SRO_PHASE6_LISTING=/path/to/Media.list.txt \
  python3 scripts/test_phase6_assets.py
```

`PHASE_6_BULK_ANDROID_ASSET_CONVERSION.md` documents exact inventory counts,
the verified format sampling, resource budget, determinism, and the commit
decision (all converted PNGs committed by user choice).

### 2d. Android minimap asset layer (Phase 7)

Integrates the verified minimap inventory into a manifest-driven, bounded
TypeScript asset layer that runs on Android via the Capacitor WebView
(`map/dist`): `map/src/game/minimap_assets.ts` provides a resolver
(`MinimapManifestResolver`), a validating loader (`MinimapAssetLoader`), and a
bounded LRU cache (`BoundedMinimapCache` / `CachedMinimapLoader`). It reads
`android-assets/manifest.json` as the authoritative mapping, resolves PK2
source paths to Android asset paths without filename guessing, validates PNG
signature/dimensions/CRC/sha256 per loaded asset, never preloads the
collection, and fails explicitly on missing/corrupt/mismatched assets.

```shell
cd map
deno test --allow-all --no-check src/game/minimap_assets.test.ts
```

`PHASE_7_ANDROID_MINIMAP_INTEGRATION.md` documents the exact inventory, the
resolution/validation design, the memory policy, real-asset proof, and the
Android-runtime test status (NOT EXECUTED — no device/emulator available).

### 2e. Native Android minimap renderer (Phase 8)

First native (non-WebView) module in the Android app: a Java minimap renderer in
`android/app/src/main/java/com/opensilkroadmap/app/minimap/` that consumes the
same verified `android-assets/manifest.json` through `ManifestParser` +
`ManifestResolver`, decodes Android assets with `BitmapFactory`-based
`AssetDecoder`/`BitmapFactoryDecoder`, keeps decoded payloads bounded in
`NativeMinimapAssetProvider` (LRU by bytes + entries, dimension-validated,
release on eviction), and draws them via the custom `NativeMinimapRenderer`
`View` with bounded zoom and a TEST ONLY player marker. The logic core
(resolver, fit math, cache) is Android-free so it compiles as JVM unit tests;
instrumented renderer tests run against gitignored real proof assets under
`android/app/src/main/assets/minimap_proof/`.

```shell
cd /workspace
python3 scripts/verify_phase8_manifest_rules.py   # manifest-resolution invariants (runs here)
python3 scripts/prepare_phase8_proof_assets.py   # copies real proof assets (gitignored)
```

`PHASE_8_ANDROID_MINIMAP_RENDERER.md` documents the module inventory, design,
JVM/Android test status (NOT EXECUTED — no JDK/SDK/emulator in this
environment), and next-phase recommendation.

### 3. Processing Silkroad Assets

```shell
uv run scripts/convert_ddjs.py
uv run scripts/generate_tiles.py
uv run scripts/generate_navmesh.py
uv run scripts/generate_game_data.py --source-dir game_source
uv run scripts/generate_phase_h_data.py --source-dir game_source
uv run scripts/build_game_database.py --source-dir game_source --output-dir map/public/assets/gamedata
```

### 4. Run the Development Server

```shell
deno task dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Credits

- Initial work done by [Jellybitz](https://github.com/JellyBitz) on [xSROMap](https://github.com/JellyBitz/xSROMap)
- Integrated changes made on [kis1yi](https://github.com/kis1yi)'s [fork](https://github.com/kis1yi/xSROMap)
- Adjustments, cleanup, integrations to OasisBot and scripts to further improve reproducibility by [Egezenn](https://github.com/Egezenn)

## TODO

- Teleporter imports
- Opacity sliders for layers
- Deployment
- OasisBot connection
  - Dungeon integration (on NavLink display, need to quantize heights on dungeon regions so that they don't render on top of each other)
