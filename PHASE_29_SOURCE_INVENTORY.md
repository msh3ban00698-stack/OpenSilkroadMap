# PHASE 29 SOURCE INVENTORY — Deep Runtime Forensics

Branch: `260831-feat-phase29-deep-runtime-forensics` · Baseline: Phase 28 HEAD `fcab6b34`
Date: 2026-08-31

This inventory classifies every major subsystem and forensic source recovered in
Phase 29 using exactly six statuses:

- **PROVEN** — recovered and directly evidenced (symbols, schema, config, data).
- **PARTIAL** — partly evidenced; some link in the chain is still unproven.
- **UNKNOWN** — recovered but semantics not established (no direct evidence).
- **MISSING** — referenced by the corpus but absent from this extraction.
- **UNREADABLE** — present but not interpretable with current tooling.
- **DEAD** — existed at build time but is no longer recoverable (source only).

Nothing is executed. All binaries are inspected statically (PE metadata, string
tables, RTTI class names, source-file paths, and cross-referenced config/DB/data).

## 1. Subsystem verdict summary (2 PROVEN / 6 PARTIAL / 2 UNKNOWN)

| # | Subsystem | Verdict |
|---|---|---|
| A | Client executable provenance | **PROVEN** |
| B | Server package provenance | **PROVEN** |
| C | Movement walk/run speed | **PARTIAL** |
| D | Input key→action | **PARTIAL** |
| E | Camera behavior | **PARTIAL** |
| F | Network / gameplay protocol | **PARTIAL** |
| G | Combat / status schema | **PARTIAL** |
| H | Player spawn | **UNKNOWN** |
| I | Skill semantics | **UNKNOWN** |
| J | Motion states | **PARTIAL** |

## 2. PROVEN (2)

### A. Client executable provenance
`GameClient.exe` (11,845,632 B, PE32 i386 GUI, ts `0x4ee5cf79`, PDB
`D:\vss-od\Silkroad\Client\Out\SRO_Client.pdb`, 1 export `fcEXP`),
`edxSilkroadDll5.dll` (296,448 B, export `Initialize`), `GFXFileManager.dll`
(client 731,128 B; exports `GFXDllCreateObject`/`GFXDllReleaseObject`/`GFXFMInfo`).
Static only; no symbol table in `GameClient.exe`.

### B. Server package provenance
`/tmp/opencode/extract/server/`: 8 game-server EXEs (`SR_GameServer.exe`
9,576,448 B; `SR_ShardManager.exe`; `GatewayServer.exe`; `AgentServer.exe`;
`GlobalManager.exe`; `MachineManager.exe`; `DownloadServer.exe`;
`FarmManager.exe`) with embedded PDB paths and PE timestamps, `server.cfg`,
`SR_GameRefData/` (50+ textdata files), `Map1.CS3`/`Map2.CS3`. Static only; no
exported symbols and no shipped `.pdb` files.

## 3. PARTIAL (6)

### C. Movement walk/run speed
- PROVEN: `_InsertRefChar` params `@Speed1 smallint`(45), `@Speed2 smallint`(46),
  `@Scale int`(47); client `m_nSpeed2` member; server `PCSpeedRatio`,
  `RefreshMoveSpeed()`, `SetMoveMode()`; position system `Pos_RegionID`,
  `DestPos_RegionID`, `MoveTo: [%d, (%f,%f,%f)]`, `LastUpdateTick`.
- PROVEN coordinate structure: `RefRegion.txt` (2,461 rows × 21 cols: region id,
  worldmap grid X/Y, name, zone id), `worldmap_mapinfo.txt` (59 rows: region
  bounds + coord bounds), `regioncode.txt` (1,390 rows, CP949), navmesh
  block/cell ids `CurBlockID`/`DestBlockID`/`CurPosRegionX/Z`.
- UNKNOWN: textdata positional triplet 16/50/100 → `Speed1/Speed2/Scale` mapping;
  world-units-per-second conversion (no numeric scale constant recovered); exact
  speed/tick integration formula.
- `m_nSpeed1` is **MISSING** from all binaries/strings searched.

### D. Input key→action
- PROVEN: `config/command.txt` (47 debug commands); client `CIFOption_Input`,
  `CIFEInputChatBox`.
- UNKNOWN: key→action binding (`SROptionSet.dat` is **UNREADABLE**).

### E. Camera behavior
- PROVEN: `config/cameradata.txt` (2 region-keyed presets); client
  `CCameraSlid/CCameraWorking/SC_CameraShake/...`.
- UNKNOWN: preset column semantics + interpolation.

### F. Network / gameplay protocol
- PROVEN: `proxy_cfg.ini` protocol `CL_VERSION=188`, `CL_GW_PORT=15779`; client
  `RecMsg.dat`, `MSGID:0x%X`, 51 `SC_*` (server→client) message classes; server
  `MsgSender`/`SendMsg`/`SendMsgToPeer`; ShardManager relay `OnSR_RELAY_MSG_SM_TO_GS`.
- PROVEN message-dispatch layer: client `MsgStreamBuffer.h`, `NetEngine::MsgPool`,
  `m_MsgList`/`m_nCurrentReadMsg`, `MSG_ID = %X`,
  `_OnMsgReceivedBeforeHandshake()`; server `CGame::ProcessMessage() MsgID : %x`,
  `Unhandled Game SR_MSG: 0x%x [data size: %d]`, `IGObj::AllocMsgForPeer`,
  `DumpMsgPool`, header checks `INVALID_MSG_HEADER`/`INVALID_MSGSIZE`/
  `NO_MSGTARGET`, packet log `IP:%s %s:0x%04X (0x%04X) (MsgType:%d), %d - %d`.
- UNKNOWN: opcode→field layout. `RecMsg.dat`/`SendMsg.dat` are **MISSING**, and
  no `CS_*` (client→server) RTTI classes exist.
- Category split (strict): (A) gameplay client/server = PARTIAL; (B) server admin
  (`smc.exe`, `Certification.xml`, `SMC_*.cfg`) = config/tooling; (C) proxy/admin
  (`VSROProxy.exe` .NET + `sr_proxy.dll`) = tooling, NOT gameplay protocol;
  (D) config-only (`server.cfg`, `proxy_cfg.ini`, `option.txt`).

### G. Combat / status schema
- PROVEN: `_RefObjChar` columns `PD/MD/PAR/MAR/ER/BR/HR/CHR`, `Knockdown`,
  `KO_RecoverTime`, `DamagePortion`, `ExpToGive`, `CreepType`,
  `DefaultSkill_1..10`, resist family.
- UNKNOWN: damage formula, attack cadence, cooldowns.

### J. Motion states
- PROVEN: 19 server `MOTIONSTATE_*` labels (STAND/WALK/RUN/SKILL/SIT/JUMP/SWIM/
  RIDE/KNOCKDOWN/STUN/FROZEN/HIT/REQ_HELP/PAO/COUNTERATTACK/SKILL_ACTIONOFF/
  SKILL_KNOCKBACK/SKILL_PROTECTIONWALL/CHANGEMOTION).
- UNKNOWN: semantic mapping to animation (client uses separate `SC_ObjectAniToName`
  /`SC_ObjectAniToIndex`; no shared enum in the corpus) and transition triggers.

## 4. UNKNOWN (2)

### H. Player spawn
PROVEN chain so far: `SR_ShardManager.exe` calls `_AddNewChar` via ODBC
`{?=CALL _AddNewChar (...)}`; `StartRegionID/StartPos_X/Y/Z` are caller-supplied
params; server pipeline `CGame::EnterWorld → CGObj::EnterWorld →
ResolveCellAndHeight → MoveTo → ActivatePC → SR_READY_TO_PLAY`; position
persistence `_CharInstanceWorldDataUpdate` and `_Char.LatestRegion/PosX/Y/Z`.

NOT PROVEN: the concrete `StartRegionID`/`StartPos` values. The reference classes
`CRefInstanceWorldStartPos`/`CRefInstanceWorldRegion` exist but their source data
files `RefInstanceWorldStartPos.txt`/`RefInstanceWorldRegion.txt` are **MISSING**
from `SR_GameRefData`, and instance-world config is Lua-driven
(`LuaSetInstanceWorldConfig`); no start-town/region numeric constants appear in
the server strings. → Player spawn is **NOT fully proven**.

### I. Skill semantics
- PROVEN: `_RefSkill.basic_code`; `DefaultSkill_1..10` slots.
- UNKNOWN: effect/cast-time/cooldown (skilldata raw, not interpreted).

## 5. MISSING (referenced but absent)

- `RecMsg.dat` / `SendMsg.dat` — gameplay message definitions (opcode→field layout).
- `CharacterData_40000.txt` — listed in `CharacterData.txt` stub, absent from extraction.
- `RefInstanceWorldStartPos.txt` / `RefInstanceWorldRegion.txt` — instance-world
  start-position/region data (referenced by `CRefInstanceWorldStartPos` /
  `CRefInstanceWorldRegion` classes; config instead Lua-driven via
  `LuaSetInstanceWorldConfig`).
- All shipped `.pdb` symbol files (only embedded paths remain).
- `_RefInstanceWorldStartPos` / `_RefInstanceWorldRegion` source data file (if any).
- `CS_*` (client→server) message class source (absent from client RTTI).

## 6. UNREADABLE (present, not interpretable)

- `SROptionSet.dat` (key→action binding; binary, no self-describing action ids).
- `Map1.CS3` / `Map2.CS3` (map format, 13,000 B each).
- Third-party support DLLs: `dbghelp.dll`, `ggauth.dll`, `XTrap4Server.dll`,
  `ImageTrans.dll`, `CommonGuiControl.dll`, `MailSender.dll`, `VerData.dll`,
  `ServerFrameworkRes.dll` (no self-describing metadata).

## 7. DEAD (existed at build time, unrecoverable)

- The C++ source files referenced by embedded PDB/source-path strings
  (`D:\WORK2005\Source\SilkroadOnline\Server\...`,
  `D:\WORK2005\Source\JMX_Library\NavMesh_new\RTNavMeshTerrain.cpp`,
  `D:\vss-od\Silkroad\Client\client\*.cpp`). The binaries embed these paths but
  the source itself is not shipped and is not recoverable from strings alone.
- No other "dead" runtime code paths are identified in this phase.

## 8. Provenance and reproducibility

All extractions are read-only and deterministic. Binaries live under
`/tmp/opencode/{client_bin,extract/server,extract/proxy,vsro_db}`. Evidence JSON
is regenerated by `scripts/build_phase29_evidence.py` and verified by
`scripts/test_phase29_evidence.py` (stdlib unittest, 21 tests) and the pure-JVM
harness `/tmp/opencode/ph29build/phase29_build_and_run.sh` (real JUnit 4.13.2,
25 tests).
