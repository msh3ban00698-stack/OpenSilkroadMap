# PK2 Reader Foundation

Phase 3 deliverable. A verified, reproducible PK2 reading/extraction foundation for the
VSRO v1.193 Android project: reader provenance pinned, dependency made reproducible,
deterministic read-only validation across all five PK2 archives, and repeatable tests.

Companion document: `PK2_ACCESS_AND_ASSET_PIPELINE.md` (Phase 2, `ed0589c`).

Session: 2026-08-29. All raw evidence lives under `/tmp/opencode/` (outside the repo).
No proprietary archive or large binary is committed. No Android runtime, gameplay, engine,
conversion, multiplayer, or server code is implemented — Phase 3 is foundation only.

---

## 1. Objective

- Replace "the reader exists and works" (Phase 2 outcome **B**) with a **pinned,
  reproducible, and testable** reader foundation.
- Prove the reader still works on all five real PK2 archives in a **read-only, bounded**
  way (no full extraction).
- Add deterministic regression tests that run without the 4.8 GB dataset.
- Document exactly where the reader comes from, its version, its license, and how to
  reproduce the artifact — so future phases never depend on a floating download.

## 2. Verification Conventions

Same labels as Phase 2 (`PK2_ACCESS_AND_ASSET_PIPELINE.md` §2):

| Label | Meaning |
| --- | --- |
| VERIFIED | Confirmed from real bytes/listings in this session |
| DOCUMENTED BUT NOT CURRENTLY VERIFIED | Cited in repo docs/Phase A but not re-checked here |
| INFERRED | Reasonable reading of verified data, not treated as fact |
| UNKNOWN / NEEDS SOURCE | No supporting file exists anywhere |

## 3. Reader Provenance (VERIFIED)

| Field | Value |
| --- | --- |
| Project | Veykril/pk2 |
| Source | https://github.com/Veykril/pk2 |
| License | MIT (c) 2018-2021 Lukas Wirth `<Veykril>` — VERIFIED from LICENSE at pinned commit |
| Default branch | `main` |
| Release | tag `v0.0.0`, published 2026-07-08, not draft/prerelease |
| Pinned commit | `e07dec0667bfed9c998cf582416f87ee2e85e6bb` |
| Artifact | `pk2_mate` release binary (Linux x86_64), 1,497,488 B |
| Binary sha256 | `f2bd9c6b96a7a53561a7a0c75908bc8f7b2fc65dcbc5d478bfca2b3f73ef5c31` |
| Tarball sha256 | `94c8483247ebf672c852c060c9680c1a48ceda6fdc295bc676c09ab175c6e325` (`pk2_mate.tar.gz`) |
| Default key | `169841` (Blowfish) |

Why this tool: it is the exact reader validated in Phase 2, it is the tool the repo
`README.md` already documents for PK2 extraction, and it is MIT licensed. No alternative
reader was downloaded. No Rust toolchain exists in this environment, so the reproducible
artifact is the **pinned GitHub release binary + sha256**, not a local build.

## 4. Format Constants Documented From Source (VERIFIED)

Pinned source tree: `src/{lib,blowfish,error,filetime,format.rs,parse.rs}`,
`src/format/{header,entry,block_chain,chain_index}.rs`, `pk2_mate/`, `crates/pk2-sync/`,
`LICENSE`, `README`, `ARCHITECTURE.md`.

| Constant | Value | Source location |
| --- | --- | --- |
| `PK2_VERSION` | `0x0100_0002` | `src/format/header.rs` |
| `PK2_SIGNATURE` | `b"JoyMax File Manager!\n"` + 9 nulls (30 B) | `src/format/header.rs` |
| `PK2_CHECKSUM` | `b"Joymax Pak File\0"` (16 B, Blowfish-encrypted) | `src/format/header.rs` |
| `PK2_CHECKSUM_STORED` | 3 (first 3 bytes of the encrypted checksum stored) | `src/format/header.rs` |
| Header size | 256 B: sig[30] + u32 version + u8 encrypted + verify[16] + reserved[205] | `src/format/header.rs` |
| Block | 20 entries x 128 B | `src/format/block_chain.rs` |
| Root chain | at file offset 256 | `src/format.rs` |

Blowfish key `169841` is pk2_mate's default and is VERIFIED (Phase 2) to decrypt the real
`Music.pk2` file table; the checksum field `d8da30` matches both the real `Data.pk2` and a
fresh `pk2_mate pack` fixture created with the default key. The algorithm itself is
implemented by pk2_mate; this project does not re-implement Joymax Blowfish.

## 5. Cross-Verification: Source Layout vs Real Data.pk2 Header (VERIFIED)

256-byte header read from the real `Data.pk2` (raw file, `/tmp/opencode/pk2raw/Data.pk2`,
3,351,891,968 B):

| Offset | Field | Observed bytes | Source expectation | Match |
| --- | --- | --- | --- | --- |
| 0x00-0x1D | signature (30 B) | `JoyMax File Manager!` + 9 nulls | same | VERIFIED exact |
| 0x1E-0x21 | version u32 LE | `02 00 00 01` = `0x01000002` | `0x01000002` | VERIFIED exact |
| 0x22 | encrypted u8 | `01` | flag set | VERIFIED |
| 0x23-0x25 | verify (stored 3 B) | `d8 da 30` | `PK2_CHECKSUM_STORED` bytes of Blowfish(169841)(checksum) | VERIFIED |
| 0x26-0xFF | reserved (205 B) | all zero | reserved | VERIFIED |

The source-declared layout fully matches the observed bytes of a real archive.

## 6. Reproducibility

Two layers:

1. **Artifact reproducibility**: the reader binary is pinned by GitHub release tag + exact
   commit + sha256 (§3). Re-fetching is deterministic:
   - download the release tarball and verify `sha256sum` == `94c8483247...`;
   - extract and verify the binary `sha256sum` == `f2bd9c6b...`.
2. **Validation reproducibility**: `scripts/validate_pk2.py` is a deterministic,
   read-only validator that (a) checks the 256-byte header of every archive against the
   source-documented constants, (b) runs the reader's `list` over each archive, and
   (c) optionally extracts one small named file into a temp dir as an extraction proof.

`scripts/validate_pk2.py` exits non-zero with a clear message pointing at this document
when the reader binary cannot be located, so a missing dependency never looks like
"passing".

## 7. Deterministic Validation Commands (VERIFIED, reproducible)

Fixture-based regression tests (no real archives needed):

```bash
python3 scripts/test_pk2_reader.py        # header tests + pk2_mate integration (skips cleanly if reader absent)
```

Full real-archive validation (needs the raw PK2s, outside the repo):

```bash
python3 scripts/validate_pk2.py \
  --pk2-dir /tmp/opencode/pk2raw \
  --reader-bin /tmp/opencode/pk2_mate \
  --extract-one <tiny-known-path>
```

Reader resolution order: `--reader-bin`, `SRO_READER_BIN`, `--reader-dir/pk2_mate`,
`SRO_READER_DIR/pk2_mate`, `PATH`.

The committed synthetic fixture is regenerable at any time (MIT-origin tool, own text
data, no proprietary content):

```bash
pk2_mate pack --directory scripts/testdata/pk2_fixture/src --archive scripts/testdata/pk2_fixture/fixture.pk2
```

Regeneration reproduces the identical 256-byte header (signature/version/encrypted/verify
all match) and identical directory listing; the full-byte sha256 may differ between
regenerations because pk2_mate embeds per-file timestamps into entries. The committed
fixture sha256 is `ba9fc47cabb0eb419ba3ce45d79342d56a925f964c872c7e8808a385cf6aa5db`.

## 8. Per-Archive Validation Results

Run over `/tmp/opencode/pk2raw/` (all five raw PK2s materialized from the 7z containers).
Header checks and `list` all PASS; `--extract-one ARABIA_TOWN.ogg` proof extracted only
from Music.pk2 (the only archive containing that path).

| Archive | Size (bytes) | Header | list | entries | extraction proof |
| --- | --- | --- | --- | --- | --- |
| Data.pk2 | 3,351,891,968 | VERIFIED (sig/version/enc/verify/reserved all OK) | rc=0 | 68,518 | path not in archive (expected) |
| Map.pk2 | 1,268,441,088 | VERIFIED | rc=0 | 19,264 | path not in archive (expected) |
| Music.pk2 | 76,488,704 | VERIFIED | rc=0 | 51 | `ARABIA_TOWN.ogg` 2,686,186 B, OggS-validated (633 pages), sha256 `bb9ea1655cd084d15796865b4b98abc0cb8f6c6c7850edbf07e4af7b8b64f2c7` |
| Particles.pk2 | 178,126,848 | VERIFIED | rc=0 | 4,801 | path not in archive (expected) |
| Media.pk2 | 823,066,624 | VERIFIED | rc=0 | 29,750 | path not in archive (expected) |

Every archive header matches the source-documented layout: signature 30 B exact, version
`0x01000002`, encrypted flag set, verify prefix `d8da30`, reserved region zeroed.

Phase 2's independent Music.pk2 proof (jangan_town.ogg 470,512 B, OggS 113 pages, sha256
`96d6792423ccd73fdbe52179fbc643827f50375fd01e5692687175ed22e07674`) remains current and
was re-confirmed by the validator on the raw archive.

Note on pk2_mate behavior: `extract` on a path that does not exist in an archive panics
(rc=101); the validator therefore scopes the proof to archives whose listing contains the
path and reports others as `extract skipped`.

## 9. Tests (run and recorded this session)

| Suite | Result |
| --- | --- |
| `scripts/test_pk2_reader.py` — 11 tests | PASS (header constants vs fixture; pk2_mate list/extract; validator OK-with-reader and clear-fail-without-reader) |
| `scripts/test_sro_pipeline.py` | PASS (15/15, re-run this session) |
| `scripts/extract_sro.py validate` | PASS |
| `scripts/validate_pk2.py` (fixture, `--extract-one hello.txt`) | OK |
| `scripts/validate_pk2.py` (all five real archives, `--extract-one ARABIA_TOWN.ogg`) | OK — header+list all pass, Music proof extracted (see §8) |

## 10. Limitations / UNKNOWN / NEEDS SOURCE

- **In-repo Python reader still absent**: `pk2reader.py` / `jmblowfish.py` are NOT FOUND
  anywhere in the repo or package index (confirmed by full-filesystem search). The Python
  pipeline's `extract_sro.py extract` path therefore still has no in-repo implementation;
  `pk2_mate` covers CLI list/extract only. This is the known blocker carried from Phase 2.
- `listing_media.txt` / `listing_music.txt`: NOT FOUND.
- SQL schemas in `game_source/` (if any): unopened this session.
- Full interior re-walk of Data/Map/Media contents beyond header+list: not re-done.
- UNKNOWN: whether newer tag/release exists beyond `v0.0.0`; pinned commit is authoritative.

## 11. Blockers and Next Phase

**Blockers**
- No Rust toolchain in the environment (reproducible artifact = pinned release binary).
- No in-repo Python PK2 reader; the Python contract (`PK2(path)` / `.find()` /
  `.read_file()` / `.walk(...)`) remains unsatisfied.

**Recommended next phase (from verified results, not assumption)**
1. Use the now-pinned `pk2_mate` as the extraction backend for pipeline scripts
   (subprocess delegation already consistent with the `sro_paths.require_pk2_reader`
   contract) — or
2. Implement a minimal in-repo read-only Python reader using ONLY the constants
   documented in §4 and validated against the fixture + real headers — or
3. Ask the user to supply the missing `pk2reader.py` / `jmblowfish.py` or a Rust toolchain
   to build pk2_mate from source.

The choice depends on user direction; Phase 3 does not presume it.

## 12. Traceability

| Item | Evidence |
| --- | --- |
| Reader source+license+commit | GitHub release v0.0.0 -> tag/commit `e07dec06...`, LICENSE MIT |
| Binary sha256 | `f2bd9c6b96a7a53561a7a0c75908bc8f7b2fc65dcbc5d478bfca2b3f73ef5c31` |
| Tarball sha256 | `94c8483247ebf672c852c060c9680c1a48ceda6fdc295bc676c09ab175c6e325` |
| Format constants | pinned source tree §4, cross-checked against real header §5 |
| Real archive headers | `/tmp/opencode/pk2raw/*.pk2` (outside repo) |
| Fixture | `scripts/testdata/pk2_fixture/` (committed; synthetic, MIT-origin tool, own text data) |
| Tests | `scripts/test_pk2_reader.py`; `scripts/test_sro_pipeline.py` |
| Validator | `scripts/validate_pk2.py` |
| Phase 2 doc | `PK2_ACCESS_AND_ASSET_PIPELINE.md` (commit `ed0589c`) |

---

# Phase 4 Addendum (2026-08-29) — Real Extraction and Asset Foundation

Phase 4 built on this foundation: real extraction + asset classification. Full
detail in `ANDROID_ASSET_MANIFEST.md`. Highlights verified this session:

- **Archive SHA256** (all five, computed over raw files at `/tmp/opencode/pk2raw/`):
  Data `e61c8477…e61c17`, Map `ae482b3b…987e5`, Media `134731ac…7c0fb`,
  Music `f1ce4723…e5f5b2`, Particles `558027e2…d56596`.
- **Inventory** (`scripts/inventory_pk2.py`, reproducible): Data 66,051 files,
  Map 19,171, Media 29,591, Music 50, Particles 4,768 — matching Phase A counts.
- **Controlled extraction** (`scripts/extract_samples.py`, 35 samples, 0 failures):
  all five archives, covering every asset category; per-file sha256 recorded.
- **Verified formats by magic bytes** (not filename guessing): `.ddj` = 20-byte
  `JMXVDDJ 1000` header + standard DDS (DXT1/DXT3/RGB16/RGB32 verified); `.ogg` =
  OggS; `.wav` = PCM 16-bit 22050 Hz; textdata = UTF-16 LE; Map `.t/.m/.o/.o2` =
  `JMXVMAPT/MAPM/MAPO`; `.nvm` = `JMXVNVM 1000`; `.bms/.bsr/.cpd/.ban/.efp` =
  `JMXVBMS/JMXVRES/JMXVCPD/JMXVBAN/JMXVEFF`; fonts `.dat` = `JMXVIMG 1100`.
- **Full extractions (outside repo)**: Media 819,003,922 B, Music 76,475,511 B,
  Particles 177,456,277 B. Data/Map partially extracted (disk bound).
- **Not a game asset**: `Particles/textures/thumbs.db` is a Windows thumbnail cache.
- **Android readiness**: Ogg/WAV native; DDJ needs DDS decode (repo `convert_ddjs.py`
  path proven against real structure); all JMX 3D/particle/terrain/navmesh formats
  remain UNKNOWN — DO NOT CONVERT YET.
- **New reproducibility**: `scripts/inventory_pk2.py`,
  `scripts/extract_samples.py`, `scripts/test_phase4_assets.py` (5 tests).
