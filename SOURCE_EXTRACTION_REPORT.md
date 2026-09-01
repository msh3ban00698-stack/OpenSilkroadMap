# Source Extraction Report (Phase 29 — source parity)

Incremental, read-only source-corpus index. No gameplay implementation. No
source archive was modified. This report supersedes the earlier audit-only draft.

## Reconciliation (exact)

| Status | Count | Meaning |
|--------|-------|---------|
| PROVEN | 1,444 | extracted text/code/config, payload readable on disk |
| PARTIAL | 65 | text/code/config identified but payload NOT yet extracted |
| UNKNOWN | 119,295 | binary present; format family identified by extension, semantics unproven |
| STUB | 17 | zero-byte placeholder files |
| DEAD | 19 | non-game artifacts (thumbs.db, desktop.ini, vssver.scc, .tmp, .sfk) |
| UNREADABLE | 0 | none |
| MISSING | 1 | known-required file absent from every archive (RecMsg.dat) |

Present (manifest) total: **120,840** files (`119,631 + 1,084 + 4 + 121`).
With the 1 MISSING protocol table, tracked total is **120,841**.

## Source families

| Source | Files | Notes |
|--------|-------|-------|
| PK2 archives | 119,631 | Data 66,051 / Map 19,171 / Media 29,591 / Music 50 / Particles 4,768 |
| Extracted filesystem | 1,084 | server 1,052 / proxy 29 / client 2 / event 1 |
| SQL backups | 4 | SRO_CERTIFICATION / ACCOUNT / SHARD / SHARDLOG |
| Containers (unrealized) | 121 | VSRO-R Client.7z (client exe/dll + RD region data + Setting) + 2 patchers |

Extracted on disk: **35,497** files (PK2 Media/Music/Particles = 34,409 +
server/proxy/client/event = 1,084 + SQL = 4). Indexed-only: **85,343**.

## System coverage (structural, by directory/extension — not semantics)

rendering 59,915 · ui 21,628 · map 19,224 · minimap 7,737 · navigation 6,072 ·
effects 4,792 · server-logic 863 · data-tables 165 · server-data 138 ·
region-data 103 · audio 50 · unknown 49 · server-binary 40 · networking 29 ·
configuration 19 · client-binary 12 · database 4.

Literal domain tags present in paths (coverage only, NOT asserted behavior):
item, map, ui, skill, monster, npc, trade, pet, guild, quest, character, event,
thief, hunter, shop, fortress, gold, alchemy/archemy, battle, union, effect,
animation, equip, silk, buff, summon, drop, arena, combat, party, level, job,
chat, teleport, and others (see `SOURCE_CORPUS_STATS.json` → `by_domain`).

## Still inaccessible / not-yet-realized

- `RecMsg.dat` — client-side receive-message table. String `RecMsg.dat` is
  present in `GameClient.exe` (client `Game.cpp` startup, loaded via
  `CreateFile`); absent from every archive/container/SQL backup (MISSING).
- `SendMsg.dat` — NOT authoritative. No binary references `SendMsg.dat`;
  only `SendMsg` appears as C++ method names in `SR_GameServer.exe`
  (`SendMsgToPeer`, `SendMsgToAllGameWorldUser`, …). Reclassified out of
  MISSING (was wrongly assumed client+server dispatch reference).
- `VSRO-R Client.7z` content (121 files): `GameClient.exe`, client DLLs,
  `RD/G64_*.rd` region data, `Setting/*.dat`, `silkcfg.dat` — present but not
  extracted (indexed-only, `container` source).
- `Data.pk2` + `Map.pk2` payloads — indexed, not extracted (disk budget).
- SQL `.Bak` — present, not restored/parsed.
- Compiled server scripts `.sct`/`.crb` — present, not decompiled.
- All `.ddj/.bms/.bsr/.nvm/.ban/.efp/...` binary formats — format family
  identified, internal semantics UNKNOWN (never converted to PROVEN).

## Secret scan

- Repo deliverables (scripts, `.md`, `.json`): **clean** — no secrets.
- Source corpus: the game's own embedded SQL credentials were found in
  `extract/server/Certification.xml` and inside the `.Bak` connection strings
  (original leaked server config; not introduced by this work). Values are not
  reproduced here.

## Verification

- Python: `test_phase29_evidence.py` 21 OK; `test_source_corpus.py` 5 OK
  (manifest counts == PK2 enumeration, reconciliation sums, known-missing);
  `test_pk2_reader.py` 11 OK.
- JUnit: `Phase29SourceEvidenceTest` 19 OK (direct JVM run). Full Android Gradle
  suite is blocked by missing `ANDROID_HOME` (SDK absent).
- Manifest PK2 count reconciles to 119,631 (see `scripts/test_source_corpus.py`).
- Source archives verified unmodified (size+mtime unchanged; no archive touched
  since extraction).
- Disk: 2.5 GB free (87% used); deliverable set ≈ 53 MB.

## Remaining blockers

1. **Disk** (2.5 GB free) prevents full Data+Map payload extraction.
2. **Full per-file SHA-256** (5.7 GB cold read, ~10 min) deferred by decision.
3. **Android SDK** absent — full Gradle unit-test suite cannot run here.

## Deliverables

`SOURCE_CORPUS_MANIFEST.{json,tsv}` · `SOURCE_CORPUS_STATS.json` ·
`SOURCE_SYSTEM_INVENTORY.{json,tsv}` · `SOURCE_EXTRACTION_ERRORS.tsv` ·
`SOURCE_EXTRACTION_REPORT.md` · `SOURCE_PARTIAL_COVERAGE.md`.

Pipeline: `scripts/index_source_corpus.py` (incremental, resumable; cache at
`.source_index/cache.json` keyed by path+size+mtime; reuses Phase 4 hashes).
