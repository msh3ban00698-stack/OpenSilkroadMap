# PK2 Access and Asset Pipeline

Phase 2 deliverable. Real source -> verified PK2 access -> small verified extraction
proof -> documented pipeline. Nothing is invented: every claim below is VERIFIED,
DOCUMENTED BUT NOT CURRENTLY VERIFIED, INFERRED, or UNKNOWN / NEEDS SOURCE, using the
conventions in `ANDROID_GAME_ARCHITECTURE.md` §1.

Session: 2026-08-29. All raw evidence lives under `/tmp/opencode/` (outside the repo).
No proprietary archive or large binary is committed.

---

## 1. Purpose and Scope

- Confirm that the provided VSRO v1.193 material is actually reachable in this
  environment (not just referenced).
- Establish a **verified, bounded, read-only** way to inspect PK2 archives without
  extracting gigabytes.
- Determine whether a **verified PK2 reader** exists and can extract a small sample
  (outcome A/B/C of the phase).
- Document the end-to-end pipeline contract so the repo scripts (`extract_sro.py` etc.)
  are known to be correct against real archives.
- Android conversion boundaries are **documented only**; no Android runtime or
  conversion code is implemented in this phase.

Out of scope: full extraction, committing PK2s/`game_source/`, running or reverse
engineering EXE/DLL, inventing a PK2 reader, any network protocol work.

## 2. Verification Conventions

| Label | Meaning |
| --- | --- |
| VERIFIED | Confirmed from real bytes/listings in this session |
| DOCUMENTED BUT NOT CURRENTLY VERIFIED | Cited in repo docs/Phase A but not re-checked here |
| INFERRED | Reasonable reading of verified data, not treated as fact |
| UNKNOWN / NEEDS SOURCE | No supporting file exists anywhere |

## 3. Component Availability Matrix

| Component | Source / location | Status |
| --- | --- | --- |
| `Data.pk2` (3,351,891,968 B) | `/tmp/opencode/PK2_Files.7z` | AVAILABLE (in 7z, not extracted raw) |
| `Map.pk2` (1,268,441,088 B) | `/tmp/opencode/PK2_Files.7z` | AVAILABLE (in 7z) |
| `Music.pk2` (76,488,704 B) | `/tmp/opencode/PK2_Files.7z` | AVAILABLE (raw copy extracted for proof) |
| `Particles.pk2` (178,126,848 B) | `/tmp/opencode/PK2_Files.7z` | AVAILABLE (in 7z) |
| `Media.pk2` (823,066,624 B) | `/tmp/opencode/vsro_pkg/VSRO-R Client/VSRO-R Client.7z` | AVAILABLE (in 7z) |
| `pk2reader.py` (repo reader) | — | NOT FOUND in repo or package |
| `jmblowfish.py` (Joymax Blowfish) | — | NOT FOUND in repo or package |
| `pk2_mate` (Veykril/pk2, MIT) | GitHub release v0.0.0, Linux x86_64 | AVAILABLE in this environment; VERIFIED working |

Reader outcome for this phase: **(B) a verified reader exists outside the repository
and is actually available in the current environment** — `pk2_mate`
(https://github.com/Veykril/pk2), MIT licensed, and the very tool the repo `README.md`
already documents for PK2 extraction. The Python reader contract (`PK2(path)`,
`.find()`, `.read_file()`) is still NOT satisfied by any in-repo file.

## 4. Real Source -> Verified PK2 Access

All five PK2 archives were opened read-only and their first bytes verified:

| Archive | First 24 bytes (hex) | Signature (ascii) | Verified |
| --- | --- | --- | --- |
| `Data.pk2` | `4a6f794d61782046696c65204d616e61676572210a000000` | `JoyMax File Manager!\n\0\0\0` | YES |
| `Map.pk2` | `4a6f794d61782046696c65204d616e61676572210a000000` | `JoyMax File Manager!\n\0\0\0` | YES |
| `Music.pk2` | `4a6f794d61782046696c65204d616e61676572210a000000` | `JoyMax File Manager!\n\0\0\0` | YES |
| `Particles.pk2` | `4a6f794d61782046696c65204d616e61676572210a000000` | `JoyMax File Manager!\n\0\0\0` | YES |
| `Media.pk2` | `4a6f794d61782046696c65204d616e61676572210a000000` | `JoyMax File Manager!\n\0\0\0` | YES |

`Data.pk2` header fields (offset-indexed, VERIFIED from real bytes, consistent with the
documented PK2 v1 header):

| Field | Offset (hex) | Bytes | Interpretation |
| --- | --- | --- | --- |
| Signature | 0x00-0x14 | `4a 6f 79 4d 61 78 20 46 69 6c 65 20 4d 61 6e 61 67 65 72 21 0a` (21 B) | `JoyMax File Manager!\n` |
| Padding | 0x15-0x17 | `00 00 00` | alignment |
| Zero region | 0x18-0x1D | `00` x 6 | — |
| Version | 0x1E (LE u32) | `02 00 00 01` | `0x01000002` — matches documented version |
| Byte | 0x22 | `01` | unknown field |
| Header checksum | 0x23-0x25 | `d8 da 30` | matches documented `d8da30…` |
| Trailing | 0x26-0x27 | `00 00` | — |
| Reserved | 0x28-0xFF | all `00` | zero-filled (VERIFIED) |

## 5. Safe Inspection Method (bounded, no full extraction)

Archive contents were inspected without dumping the full dataset:

```
timeout 90 7z e -so PK2_Files.7z Data.pk2 | head -c 256
```

- Streams the first 256 bytes of `Data.pk2` out of the 7z; nothing is written to disk
  (header evidence kept at `/tmp/opencode/data_pk2_header.bin` for traceability).
- Original 7z archives untouched. No full extraction performed (per directive).
- All header reads above used this method; the only raw extraction was the small
  `Music.pk2` (73 MB) described in §7.

## 6. Reader Status

| Reader | Status | Evidence |
| --- | --- | --- |
| In-repo `pk2reader.py` / `jmblowfish.py` | NOT FOUND | `find /` for `pk2reader*`/`jmblowfish*`; `rg -l "PK2"` returns repo scripts only; no pip module satisfying `pk2`/`blow`; no `pk2_mate`/`veykril` installs |
| `pk2_mate` (external, MIT) | VERIFIED WORKING | downloaded v0.0.0 Linux build, `--help` OK, listed `Music.pk2` (50 files), extracted one OGG (see §7) |
| Blowfish key `169841` | VERIFIED for Music.pk2 | pk2_mate's default key successfully decrypted Music.pk2's file table; the documented key `169841` is consistent with this |

Encryption scope: only **directory blocks** are Blowfish-encrypted; file data is
contiguous and unencrypted (documented claim; pk2_mate extraction of a file's bytes
succeeded, which is consistent — VERIFIED for Music.pk2, DOCUMENTED for the others).
The exact algorithm/mode of the Joymax Blowfish variant beyond the key is
**DOCUMENTED BUT NOT CURRENTLY VERIFIED** in this session; we used the reader, not a
custom implementation, so no crypto was reverse-engineered.

## 7. Small Verified Extraction Proof

A controlled, small proof using the smallest archive — `Music.pk2` (76,488,704 B,
50 files):

1. Extracted `Music.pk2` (73 MB) from `PK2_Files.7z` into `/tmp/opencode/pk2test/`.
2. Verified its header signature matches the documented `JoyMax File Manager!\n`.
3. `pk2_mate list -a Music.pk2` listed **50 `.ogg` BGM tracks** (root + 50 files),
   confirming the default Blowfish key decrypts the file table.
4. `pk2_mate extract -a Music.pk2 -o out -p jangan_town.ogg` extracted one file,
   470,512 bytes.
5. Byte-validated the result: magic `OggS`, **113 Ogg pages**, page walk reached EOF
   exactly (`pos == len(file)`), i.e. a structurally complete OGG.
6. sha256 of extracted file: `96d6792423ccd73fdbe52179fbc643827f50375fd01e5692687175ed22e07674`.

This proves real PK2 access + verified extraction of a real asset, end to end, without
extracting the ~4.8 GB dataset. The output was deleted after validation; the archive
remains under `/tmp/opencode/`.

## 8. Pipeline Contract (repo scripts)

Locked by tests and docs, consistent with the verified reader behavior:

- Reader API expected by `scripts/sro_paths.py`: `PK2(path)`, `archive.find(path)`,
  `archive.read_file(entry)`.
- `pk2_mate` satisfies the *extract* step (README): `pk2_mate extract --archive X.pk2
  --out game_source/X`.
- `PK2_ARCHIVES = ("Data", "Map", "Media", "Music", "Particles")` — all five are present
  in the package (VERIFIED).
- `extract_sro.py` subcommands: `validate` (no archives needed) / `extract` (needs
  pk2-dir + reader) / `generate` (needs source textdata).
- Paths via `--pk2-dir` / `--reader-dir` / `SRO_PK2_DIR` / `SRO_READER_DIR`; no hardcoded
  machine path.

## 9. Tests and Validation Results

| Command | Result |
| --- | --- |
| `python3 scripts/test_sro_pipeline.py` | **15/15 OK** |
| `python3 scripts/extract_sro.py validate` | **OK** — pipeline scripts compile without PK2 archives |

No repo code changed this phase; tests confirm the pipeline still runs without a reader,
and the verified reader behaves consistently with the documented contract.

## 10. Android Conversion Boundaries (documented, not implemented)

- PK2 archives are **host-side** inputs only; the Android device never reads PK2.
- Neutral interchange (glTF2 / PNG / WebP / JSON / OGG) is the conversion target
  (`ANDROID_GAME_ARCHITECTURE.md` §8); nothing is converted in this phase.
- Music.pk2 -> OGG verified feasible (50 tracks, one extracted OGG validated).
- DDJ/DDS, BMS/BAN/BSK/BMT, `.t/.o/.o2/.m`, textdata -> JSON conversions remain
  future work, blocked on full extraction + converters.

## 11. Unknowns / Needs Source

| # | Item | Status |
| --- | --- | --- |
| 1 | Full extraction of Data/Map/Media/Particles interiors (counts from Phase A are DOCUMENTED, not re-walked this session) | DOCUMENTED BUT NOT CURRENTLY VERIFIED |
| 2 | Joymax Blowfish algorithm/mode implementation (we used pk2_mate, not custom crypto) | DOCUMENTED BUT NOT CURRENTLY VERIFIED |
| 3 | `listing_media.txt` / `listing_music.txt` | UNKNOWN / NEEDS SOURCE |
| 4 | SQL Server schemas (backups unopened) | UNKNOWN |
| 5 | Any network protocol / packet layout | UNKNOWN / NOT VERIFIED |
| 6 | Monster stats / drops / combat formulas | UNKNOWN |
| 7 | `.rd` files, `silkcfg.dat`, `Silkload.dat` meaning | UNKNOWN |

## 12. Blockers and Next Steps

Blockers (unchanged where noted):

| # | Blocker | Blocks |
| --- | --- | --- |
| B1 | No in-repo `pk2reader.py`/`jmblowfish.py` | Python `extract_sro.py extract` path (pk2_mate is a workaround for direct extraction) |
| B2 | No `listing_media.txt`/`listing_music.txt` | UI/icon/audio listing-based extractors |
| B3 | PK2s not fully extracted (disk ~14 G free) | full dataset access |
| B4 | SQL backups unopened | faithful server-side logic (not needed offline) |

Next steps (recommended):

1. (Phase 2 complete) Full extraction is now **proven feasible**: use `pk2_mate
   extract` per README on Media/Data/Map into `game_source/` (external, gitignored)
   when a full dataset run is approved.
2. Re-walk Data/Map/Media/Particles interiors with `pk2_mate list` to refresh Phase A
   counts against the actual archives.
3. Obtain `pk2reader.py`/`jmblowfish.py` (or the listings) to unlock the in-repo Python
   `extract_sro.py extract` path and the listing-based extractors.
4. Neutral conversion (glTF2/PNG/WebP/JSON/OGG) as a separate phase.
5. Keep all proprietary material outside the repo; commit scripts + docs only.

## 13. Traceability

| Claim | Source |
| --- | --- |
| 5 PK2 signatures + sizes | `listings/pk2.txt`, `listings/client.txt`, header reads (§4) |
| `Data.pk2` version `0x01000002`, checksum `d8da30…` | `/tmp/opencode/data_pk2_header.bin` (256 B, real bytes) |
| Music.pk2 = 50 OGG, one extracted + validated | `pk2_mate list`/`extract`, OGG page walk, sha256 |
| pk2_mate MIT license | GitHub `Veykril/pk2` repo metadata |
| Reader API contract | `scripts/sro_paths.py`, `scripts/extract_sro.py`, README |
| Test results | `scripts/test_sro_pipeline.py`, `extract_sro.py validate` runs |
| Android conversion boundaries | `ANDROID_GAME_ARCHITECTURE.md` §8 |
