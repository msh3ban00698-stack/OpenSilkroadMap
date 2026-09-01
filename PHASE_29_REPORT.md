# PHASE 29 REPORT — Deep Runtime Forensics (Client + Server Corpus Recovery)

Branch: `260831-feat-phase29-deep-runtime-forensics` · Baseline: Phase 28 HEAD `fcab6b34`
Date: 2026-08-31

Phase 29 performs deep, static (read-only) forensics on the runtime semantics
that earlier phases classified UNKNOWN, and recovers two source corpora: the
**original PC client executable + configuration**, and the **full VSRO-R v193
server package**. The guiding rule is unchanged: **every behavior is proven from
the original source/data or left UNKNOWN / MISSING / PARTIAL.** No conventional
MMORPG behavior is substituted for an unproven semantic, and the gameplay runtime
stays 100% native Android.

## 1. Headline result

Two corpora are now recovered as static-forensic targets: the client
(`GameClient.exe` + DLLs) and the server package (8 EXEs + `SR_GameRefData` +
`server.cfg`). This closes the **SERVER → DB/CALLER** leg of the chain to the
symbol level. The current pass adds: (a) PROVEN MsgID-keyed message-dispatch on
both client and server (`ProcessMessage()` / `MsgPool` / `m_MsgList` /
`INVALID_MSG_*` header checks), (b) PROVEN region↔worldmap↔coordinate structure
(`RefRegion.txt` 21-col, `worldmap_mapinfo.txt` bounds), and (c) PROVEN that
instance-world start config is Lua-driven (`LuaSetInstanceWorldConfig`) with
`RefInstanceWorldStartPos`/`RefInstanceWorldRegion` data files MISSING. The
**PROTOCOL → CLIENT** leg remains gated on `RecMsg.dat`/`SendMsg.dat` (MISSING),
and concrete numeric start/unit values remain UNKNOWN.

## 2. Evidence chain: PLAYER SPAWN (Priority 1)

Recovered links, each PROVEN from the stated artifact:

1. **Caller of `_AddNewChar`** = `SR_ShardManager.exe`. PROVEN by the ODBC call
   format string `{?=CALL _AddNewChar (%d, %d,'%s',%d,%d,%f,%f,%f,%d,%d,%d,%d,
   %d,%d,%d,%d,%d,%d,%d,%d,%d)}` whose 20 placeholders match the proc signature.
2. **`StartRegionID` + `StartPos_X/Y/Z`** are parameters in that call —
   **caller-supplied** (the proc assigns no default). PROVEN by proc signature +
   call format.
3. **Start value origin** = `CRefInstanceWorldStartPos` and
   `CRefInstanceWorldRegion` reference classes exist in `SR_ShardManager.exe`;
   their underlying source file/values are **MISSING** from the corpus →
   concrete start values UNKNOWN.
4. **Re-login position** = `_Char.LatestRegion, PosX, PosY, PosZ` (PROVEN by
   `select LatestRegion, PosX, PosY, PosZ from _Char ...`). New-char creation and
   re-login therefore use different position sources.
5. **Server pipeline** (PROVEN by `SR_GameServer.exe` strings):
   `CGame::EnterWorld() → CGObj::EnterWorld() → ResolveCellAndHeight() →
   GetWorld()/GetWorldLayer() → MoveTo() → ActivatePC() → SR_READY_TO_PLAY`.
6. **`ResolveCellAndHeight()`** consumes the region navmesh/terrain — PROVEN by
   `CRTNavMeshTerrain` / `CRgnTerrain`, `regioninfo.txt`, and source path
   `D:\WORK2005\Source\JMX_Library\NavMesh_new\RTNavMeshTerrain.cpp`. It resolves
   the region cell and terrain height for a position.
7. **`MoveTo()`** places the object at the resolved `Pos(%.3f,%.3f,%.3f)`; logs
   `MoveTo: [%d, (%f,%f,%f)]`.
8. **`ActivatePC()`** marks the PC playable (post-spawn activation step).
9. **Persistence**: `_CharInstanceWorldDataUpdate(CharID, DungeonKeyID, WorldID,
   LayerID, Openedtime, RegionID, PosX/Y/Z, ...)` persists position per
   instance-world.
10. **Client learns identity/position** via `SC_ObjectCreate` /
    `SC_ObjectCreateIndex` (PROVEN client RTTI); the exact packet layout/opcode is
    **UNKNOWN** (definitions live in `RecMsg.dat`, MISSING).

**Verdict: PLAYER SPAWN is NOT fully PROVEN.** The chain is proven from the DB
call up through the server-side pipeline, but (a) the concrete start values, and
(b) the client-side spawn message semantics are not proven.

## 3. Movement (Priority 2)

PROVEN: `_InsertRefChar` `@Speed1 smallint`(45)/`@Speed2 smallint`(46)/`@Scale
int`(47); client member `m_nSpeed2`; server speed symbols `PCSpeedRatio`,
`RefreshMoveSpeed()`, `SetMoveMode()`, `MoveTo/MoveToPlayer/MoveToNPC/MoveToTown`;
position system `Pos_RegionID`, `DestPos_RegionID`, `LastUpdateTick`; block/cell
navigation (`CurBlockID/DestBlockID/CurPosRegionID/CurPosRegion X/Z`).

UNKNOWN: the exact movement formula (speed × delta-time → new position),
world-units-per-second conversion, and `PCSpeedRatio`'s base/application.
`m_nSpeed1` is absent from all searched binaries. **Movement is NOT fully
proven; world-unit conversion remains UNKNOWN.**

### 3.1 Coordinate system (region ↔ worldmap ↔ world)

PROVEN structure (all from `SR_GameRefData`):

- `RefRegion.txt` — 2,461 rows × 21 columns: col0 region id (signed, `-32767`
  sentinel), col1/col2 worldmap grid X/Y, col3/col4 region name/localized name,
  col6 mapping/zone id.
- `worldmap_mapinfo.txt` — 59 rows; header defines Map ID (`0`=world, `1+`=local
  town), Type (`0`:Wmap / `1`:Local), texture/draw sizes, **region bounds**
  (left/top/right/bottom = region-id range) and **coord bounds**
  (`LT_x/LT_y/RB_x/RB_y` = worldmap-cell range), fortress world id.
- `regioncode.txt` — 1,390 rows, CP949 (Korean), `1 <TAB> regioncode <TAB> xxx
  <TAB> xxx`.
- Navmesh block/cell ids in server code: `CurBlockID`/`DestBlockID`/
  `CurPosRegionID`/`CurPosRegionX`/`CurPosRegionZ`.

UNKNOWN: no numeric scale constant is recovered that maps float world coords
(`MoveTo %f,%f,%f`) to region/worldmap integer bounds; the transforms live in
compiled client/server code. **World-unit conversion remains UNKNOWN.**

## 4. Motion states (Priority 3)

19 server labels PROVEN: `MOTIONSTATE_STAND/WALK/RUN/SKILL/SIT/JUMP/SWIM/RIDE/
KNOCKDOWN/STUN/FROZEN/HIT/REQ_HELP/PAO/COUNTERATTACK/SKILL_ACTIONOFF/
SKILL_KNOCKBACK/SKILL_PROTECTIONWALL/CHANGEMOTION`.

Mapping to semantics is **name-based only (not proven)**: STAND/WALK/RUN/SIT/JUMP
are self-descriptive labels but no transition trigger, timing, or numeric state
id is recovered. The client does **not** carry the server `MOTIONSTATE_*` naming;
it receives `SC_ObjectMotionState` (state) separately from `SC_ObjectAniToName`/
`SC_ObjectAniToIndex` (animation). **No shared enum or mapping table proving
server-motion-state ↔ client-animation linkage exists in the corpus.**

## 5. Communication (Priority 4)

Strict category split:

- **A. Gameplay client/server protocol** — PARTIAL. Client: `RecMsg.dat`,
  `MSGID:0x%X`, 51 `SC_*` server→client classes (`SC_ObjectCreate`,
  `SC_ObjectMoveTo`, `SC_ObjectMotionState`, `SC_ObjectAniToName/Index`,
  `SC_Teleport`, ...). Server: `MsgSender`/`SendMsg`/`SendMsgToPeer`, relay
  `OnSR_RELAY_MSG_SM_TO_GS`. No `CS_*` (client→server) RTTI classes exist, and
  the opcode→field layout is in `RecMsg.dat`/`SendMsg.dat` (MISSING).
- **B. Server admin** — `smc.exe`, `Certification.xml`, `SMC_*.cfg`, `ServiceManager.cfg`.
- **C. Proxy/admin tooling** — `VSROProxy.exe` (.NET) + `HWID_DLL/sr_proxy.dll` +
  `Features/MALICIOUS_OPCODES.txt` (38 opcodes). NOT gameplay protocol.
- **D. Config-only** — `server.cfg`, `proxy_cfg.ini`, `option.txt`.

The 38-opcode `.NET` proxy list is **not** treated as the gameplay protocol.

### 5.1 Message layer (dispatch / serialization)

PROVEN on both sides (recovered from binary strings):

- Client: `MsgStreamBuffer.h` (serialization buffer), `NetEngine::MsgPool`,
  `m_MsgList`/`m_nCurrentReadMsg` (dispatch over a message list), `MSG_ID = %X`,
  `_OnMsgReceivedBeforeHandshake()`, `RecMsg.dat`.
- GameServer: `CGame::ProcessMessage() MsgID : %x` (dispatch entry),
  `Unhandled Game SR_MSG: 0x%x [data size: %d]`, `IGObj::AllocMsgForPeer`,
  `[MsgID: 0x%X >> Count: %d]`, `DumpMsgPool`, header validation
  `INVALID_MSG_HEADER`/`INVALID_MSGSIZE`/`NO_MSGTARGET`, packet log
  `IP:%s %s:0x%04X (0x%04X) (MsgType:%d), %d - %d`,
  `_OnMsgReceivedBeforeHandshake() - Handshake`.
- ShardManager: `Unhandled msg detected from server! msg_id 0x%x`,
  `CMainProcess::OnSR_RELAY_MSG_SM_TO_GS`,
  `FRAMEWORKMSG_START_PLAYTIME_INGAME_NOTIFY`.

Verdict: the **dispatch mechanism** (MsgID-keyed, pooled, header-validated) is
PROVEN; the **opcode→message/class mapping** is NOT recoverable — it lives in
`RecMsg.dat` (client) / `SendMsg.dat` (server), both MISSING, plus the compiled
`ProcessMessage()` switch.

## 6. Implementation

No runtime behavior was wired in. Only forensic evidence + fail-closed posture.

## 7. Verification

- Python evidence tests: `OK (21 tests)`.
- Pure-JVM harness (real JUnit 4.13.2): `OK (25 tests)` = 19 Phase 29 + 6 Phase 28.
- Android runtime: **NOT EXECUTED**.

## 8. Final report (10 required answers)

1. **New PROVEN findings** — ShardManager is the caller of `_AddNewChar` (ODBC
   call format); `StartRegionID/StartPos_X/Y/Z` are caller-supplied; server spawn
   pipeline `EnterWorld→ResolveCellAndHeight→MoveTo→ActivatePC`; position system
   `RegionID + region cell + PosX/Y/Z` (`Pos_RegionID`/`DestPos_RegionID`/
   `LastUpdateTick`); navmesh terrain `CRTNavMeshTerrain`/`regioninfo.txt`; 51
   client `SC_*` message classes and no `CS_*` classes; server package provenance;
   MsgID-keyed message dispatch on client+server (`ProcessMessage()`/`MsgPool`/
   `INVALID_MSG_*`); region↔worldmap↔coordinate structure (`RefRegion.txt`,
   `worldmap_mapinfo.txt`, `regioncode.txt`); instance-world config via
   `LuaSetInstanceWorldConfig`.
2. **PARTIAL findings** — movement (schema+symbols PROVEN, formula/units
   UNKNOWN); motion states (19 labels PROVEN, semantics UNKNOWN); communication
   (dispatch mechanism + classes PROVEN, opcode layout MISSING); camera, input,
   combat schema (unchanged partials).
3. **UNKNOWN findings** — concrete spawn start region/position values;
   world-unit-per-second conversion + movement formula; `PCSpeedRatio` base;
   motion-state→animation mapping; opcode→field layout; skill semantics.
4. **Player spawn fully proven?** No.
5. **Movement fully proven?** No.
6. **World-unit conversion proven?** No.
7. **Client/server gameplay protocol proven?** No — message classes are proven,
   exact opcodes/structures are not.
8. **MOTIONSTATE ↔ Android animation relationship** — None proven. The server
   19 labels have no recovered mapping to client animation; Android animation
   states must remain independent and fail-closed.
9. **Highest-value blocker** — `RecMsg.dat`/`SendMsg.dat` (message definitions)
   and the concrete server-side start-position/speed-unit constants (in
   `SR_GameServer.exe`/`SR_ShardManager.exe` code, not recoverable from strings).
10. **Evidence to close each blocker** —
    - Spawn start values: the `_RefInstanceWorldStartPos`/`_RefInstanceWorldRegion`
      data file, or a disassembly of `SR_ShardManager.exe`'s char-create handler.
    - Movement formula/units: the GameServer movement-update source or a
      disassembly of the `PCSpeedRatio`/`RefreshMoveSpeed` call sites.
    - Protocol: `RecMsg.dat`/`SendMsg.dat`.
    - Motion/anim mapping: a shared enum/table or the `SC_ObjectMotionState`
      field layout.
    - Skill semantics: the skilldata loader column order + effect interpreter.

## 9. Final verdict (A–M)

| # | Subsystem | Verdict |
|---|---|---|
| A | Client executable provenance | **PROVEN** |
| B | Server package provenance | **PROVEN** |
| C | Movement speed semantics | **PARTIAL** |
| D | Input key→action | **PARTIAL** |
| E | Camera behavior | **PARTIAL** |
| F | Network/protocol | **PARTIAL** |
| G | Combat/status schema | **PARTIAL** |
| H | Player spawn | **UNKNOWN** |
| I | Skill semantics | **UNKNOWN** |
| J | Animation/state selection | **PARTIAL** |
| K | Motion states | **PARTIAL** |
| L | GFX/Media | **PROVEN** (formats decoded Phases 13–20) |
| M | Android 1:1 parity | **PARTIAL** (native, fail-closed) |

## 10. Reproducing

```bash
python3 scripts/build_phase29_evidence.py
python3 scripts/test_phase29_evidence.py
bash /tmp/opencode/ph29build/phase29_build_and_run.sh
```
