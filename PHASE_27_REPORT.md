# PHASE 27 REPORT — Real Player Runtime: Spawn, Input, Movement, Camera (evidence)

Branch: `260831-feat-phase27-real-player-runtime` · Baseline: Phase 26 HEAD `c18a0031`
Date: 2026-08-31

Phase 27 asks whether a **real native player runtime** (identity → spawn →
input → movement/state → animation → camera → renderer) can be wired from the
authoritative vSRO 1.193 sources alone. It is a pure source-recovery phase: the
four runtime domains (spawn, input, movement, camera) are exhausted against the
full corpus (server DB backups, PK2 archives, package-server configs, client
settings). Everything the source proves is recorded as PROVEN; everything it
cannot prove stays UNKNOWN and the Phase 26 fail-closed runtime is preserved —
**no runtime behavior is invented**. Only the Phase 26 testing reality is used
(real JUnit 4.13.2; the empty-bodied `Assert` stub never returns).

## 1. Scope, baseline, and deliverables

Baseline: Phase 26 HEAD `c18a0031` (134 JVM tests, real JUnit). Phase 27 branch
created from it.

| Task | Deliverable |
|---|---|
| A | Spawn: character-creation proc `_AddNewChar` recovered from `SRO_VT_SHARD.Bak`; start region/position is **caller-supplied**, the only server hint is `-- set @StartRegionID=25000`; region 25000 = RN_CH_JANGAN proven via `regioncode.txt`; actual spawn coordinates UNKNOWN (fail-closed) |
| B | Input: input-options window (`ifoption_input.txt`), key-option slot widget (`ifkeyoptionslot.txt`), per-user binary OptionSet (`SROptionSet.dat`, 681 B), client debug commands — key→action semantics are client-code, UNKNOWN (fail-closed) |
| C | Movement: only client debug `/fast` and `/setspeed` exist; Phase 26 negative proof (no speed table, no baked root motion) stands — speeds UNKNOWN (fail-closed) |
| D | Animation linkage: Phase 26 BSR census / keyword resolver stands; player ATTACK/DAMAGE/DEATH remain MISSING — no new wiring warranted |
| E | Camera: three modes FREE / THIRD_PERSON / QUARTER_VIEW (`ifoption_camera.txt`), camera-data debug window (time / region / position / rotation), debug `/zoom` `/camera` `/setfov` — numeric parameters client-code, UNKNOWN (fail-closed) |
| F | Machine-readable evidence `scripts/testdata/formats/phase27_source_evidence.json` + builder `scripts/build_phase27_evidence.py` |
| G | `Phase27SourceEvidenceTest` (5 real-JUnit tests) + bounded verification run (139 PASS / 0 FAIL) |
| H | This report |

## 2. Corpus actually searched

| Source | Used for |
|---|---|
| `Database.7z` → `SRO_VT_SHARD.Bak` (~122 MB, MSSQL TAPE backup) | `_AddNewChar`, `_Char` insert, `_CharInstanceWorldDataUpdate`, item grants, region-name hints |
| `SRO_VT_ACCOUNT.Bak`, `SRO_CERTIFICATION.Bak`, `SRO_VT_SHARDLOG.Bak` | negative: no start/spawn/position config |
| `VSRO-R Client.7z` → `GameClient.exe`, `Setting/SROptionSet.dat`, `silkcfg.dat` | negative: spawn not in client config; OptionSet binary key bindings |
| `Media.pk2` (823 MB) | `regioncode.txt`, `characterdata_25000.txt`, `resinfo/ifoption_*.txt`, `ifkeyoptionslot.txt`, `ifcameradatawnd.txt`, `/config/command.txt` |
| `Data.pk2` | Phase 26 locomotion clips (reused), BSR census (reused) |
| `Vietnam-R v193 Package Server.7z` (880 files) | negative: `server.cfg`, `ServiceManager.cfg`, … contain no spawn/movement config |
| `Event-HAPPY-Working-Files-vsro-193.7z` | `Event.sct` / `EventList.sct` only (client events, no spawn) |
| `Vietnam-R v193 Offsets.txt` | negative: no input/camera/movement lines |

## 3. TASK A — spawn: character creation is server-authoritative (PROVEN)

The SHARD backup's `_AddNewChar` procedure creates a character from
**caller-supplied** parameters. Its `_Char` insert:

```sql
INSERT INTO _Char (RefObjID, CharName16, Scale, Strength, Intellect,
    LatestRegion, PosX, PosY, PosZ, AppointedTeleport, InventorySize,
    LastLogout, CurLevel, MaxLevel, RemainGold, RemainStatPoint,
    RemainSkillPoint, HP, MP, JobLvl_Trader, JobLvl_Hunter, JobLvl_Robber,
    WorldID, HwanLevel)
VALUES (@RefCharID, @CharName, @CharScale, 20, 20, @StartRegionID,
    @StartPos_X, @StartPos_Y, @StartPos_Z, @DefaultTeleport, 109,
    GetDate(), 1, 1, 50000000, 0, 1000000, 200, 200, 1, 1, 1, 1, 1)
```

Proven facts:

- New-character position columns are `_Char.LatestRegion`, `PosX`, `PosY`,
  `PosZ`, plus `AppointedTeleport`.
- `@StartRegionID`, `@StartPos_X/Y/Z` come from the caller (GameServer /
  GameWorld logic — C++, not in this corpus). The database defines **no default
  start position**.
- The only server-side hint is the developer comment inside `_AddNewChar`:
  `-- set @StartRegionID=25000` (a commented example, not a default).
- `_CharInstanceWorldDataUpdate` corroborates the position types:
  `@PosX float, @PosY float, @PosZ float, @RegionID int`.
- New-character state from the same insert: level 1, gold 50,000,000,
  stat-point 0, skill-point 1,000,000, HP/MP 200, inventory 109 slots.
  (Starting-item grants via `_ADD_ITEM_EXTERN` are also present.)
- Negative: `SRO_VT_ACCOUNT.Bak`, `SRO_CERTIFICATION.Bak`, the 880-file
  package-server extract, and the client configs contain no spawn/start
  coordinates.

**Region 25000 = RN_CH_JANGAN (PROVEN).** Client reference table
`Media.pk2 /server_dep/silkroad/textdata/regioncode.txt` row
`1  25000  RN_CH_JANGAN  (Jangan)`. So the commented example reads “start in
Jangan”. The per-region content table `characterdata_25000.txt` (3,736 lines)
is the `_RefCharGen`-style character-generation table for the region — it lists
entities present in Jangan, **not** the player spawn point.

> **Conclusion:** the runtime start region/position is decided by server logic
> absent from this corpus. Actual spawn coordinates remain **UNKNOWN
> (fail-closed)**. `PlayerSpawn` keeps its verified/unknown factories; no
> invented coordinates are introduced.

## 4. TASK B — input (PROVEN existence, semantics UNKNOWN)

- `resinfo/ifoption_input.txt` defines the client's input-options tab; its only
  text keys are the shortcut-key user-rule and the mouse label
  (`UIIT_STT_SHORTENKEY_USER_RULE`, `UIIT_STT_MOUSE`).
- `resinfo/ifkeyoptionslot.txt` is the key-option slot widget template.
- `Setting/SROptionSet.dat` (681 B) is a per-user binary OptionSet carrying
  repeating 4-byte little-endian id/value records (key identifiers in the
  0x0bxx range are visible) — i.e. key→action assignments exist but their
  action-id semantics require the client executable.
- `/config/command.txt` lists client debug commands: `/Pos`, `/GetPos`,
  `/fast`, `/setspeed`, `/zoom`, `/camera`, `/setfov`, …

> **Conclusion:** the client has a full key/input options surface, but the
> default key→action mapping and action identifiers are client-code. Runtime
> keyboard input semantics: **UNKNOWN (fail-closed)**.

## 5. TASK C — movement (Phase 26 negative proof stands)

No speed, acceleration, or turn-rate table exists anywhere in the searched
corpus (DB backups, PK2 textdata, server configs). The only movement-related
entries are client debug commands `/fast` and `/setspeed %d` — developer
diagnostics, not runtime parameters. Phase 26 already proved the locomotion
clips carry no baked forward root motion and no speed table exists:
walk/run speeds remain **UNKNOWN (fail-closed)**.

## 6. TASK D — animation linkage (Phase 26 census stands)

No per-clip state-to-animation mapping table was found beyond the BSR itself.
The Phase 26 keyword resolver + committed manifest already link
IDLE/WALK/RUN for the player and full states for NPCs; the player's
ATTACK/DAMAGE/DEATH clips are skill-named and resolve to **MISSING**
(fail-closed, no guessed-idle fallback). No Phase 27 runtime change is
warranted.

## 7. TASK E — camera (PROVEN modes, parameters UNKNOWN)

- `resinfo/ifoption_camera.txt`: three camera-mode radio buttons —
  `UIIT_STT_SIGHT_FREE_DESC`, `UIIT_STT_SIGHT_THIRD_PERSON_DESC`,
  `UIIT_STT_SIGHT_QUARTER_VIEW_DESC` (FREE / THIRD_PERSON / QUARTER_VIEW).
- `resinfo/ifcameradatawnd.txt`: a camera-data debug window exposing
  `GDR_ST_CAMERA_TIME`, `_REGION`, `_POSITION`, `_ROTATION`.
- `/config/command.txt`: `/zoom`, `/camera`, `/setfov %d`.

> **Conclusion:** camera modes and a camera-data surface exist, but the numeric
> parameters (distance, FOV, angle limits, follow offset) are client-code
> defined: **UNKNOWN (fail-closed)**.

## 8. Deliverables and verification

`scripts/build_phase27_evidence.py` regenerates
`scripts/testdata/formats/phase27_source_evidence.json` from `SRO_VT_SHARD.Bak`
and `Media.pk2`. `Phase27SourceEvidenceTest` (5 tests) asserts the proven facts
above against the evidence file.

Bounded real-JUnit verification (Phase 26 harness extended with the new test):

```
OK (139 tests)   # 134 baseline + 5 Phase 27 evidence tests, real JUnit 4.13.2
```

No runtime source was changed: every domain resolved to UNKNOWN / UNVERIFIED
under the authoritative corpus, so wiring any of it would be invention. The
Phase 26 fail-closed runtime is byte-identical.

## 9. Reproducing

```bash
# 1) Regenerate evidence (needs SRO_VT_SHARD.Bak extracted from Database.7z
#    under /tmp/opencode/vsro_db/ and Media.pk2 under /tmp/opencode/pk2raw/)
python3 scripts/build_phase27_evidence.py

# 2) Compile + run the pure-JVM suite with real JUnit 4.13.2
#    (harness: /tmp/opencode/ph26build/phase26_build_and_run.sh)
#    Expect: OK (139 tests)
```

## 10. Commit

```
feat(android): Phase 27 real player runtime evidence (spawn/input/movement/camera)
- _AddNewChar recovered from SRO_VT_SHARD.Bak: start region/pos caller-supplied,
  only hint is developer comment 'set @StartRegionID=25000'; region 25000 = RN_CH_JANGAN
  proven via regioncode.txt; actual spawn coordinates UNKNOWN (fail-closed)
- input: option window + key slot widget + 681-byte binary OptionSet + debug commands;
  key->action semantics client-code UNKNOWN (fail-closed)
- camera: FREE/THIRD_PERSON/QUARTER_VIEW modes + camera-data debug wnd + /zoom /camera /setfov;
  numeric parameters UNKNOWN (fail-closed)
- movement: only debug /fast /setspeed; Phase 26 negative proof stands
- phase27_source_evidence.json + builder; Phase27SourceEvidenceTest (5 tests)
- 139 JVM tests PASS / 0 FAIL
```

## 11. Verification record

Run output captured at `/tmp/opencode/ph26build/junit.log`; harness
`/tmp/opencode/ph26build/phase26_build_and_run.sh`; evidence JSON + builder
committed under `scripts/`.
