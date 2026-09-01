# Client & SQL Evidence (Phase 31 — source-gap recovery)

Read-only forensics on the two highest-value remaining sources: the client
`.7z` and the SQL `.Bak` backups, plus authoritative determination of
`RecMsg.dat` / `SendMsg.dat`. No gameplay implementation. No source modified.

## 1. Client `.7z` (VSRO-R Client.7z)

Extracted **119 of 120 files** (16.4 MB), skipping only `Media.pk2`
(823,066,624 bytes) because it is byte-identical to the already-extracted
`pk2raw/Media.pk2` (avoids wasting disk).

| Category | Count | Evidence |
|----------|-------|----------|
| Binaries (`.exe`/`.dll`) | 8 | `GameClient.exe` (11.8 MB, link ts 2011-12-12), `edxSilkroadDll5.dll`, `GFXFileManager.dll`, `Launcher.exe`, `MuitClient.exe`, `Uptodate.exe`, `dbghelp.dll`, `msvcp60.dll` |
| `RD/*.rd` | 103 | 16×16 8bpp Windows BMP (`BM` magic) — region minimap icons, **not** region data |
| `Setting/*.dat` + silk | 8 | `gmwpfort.dat` (fortress/battlefield names), `SRChattingBlockingList.dat`, `SRExtQSOption*.dat`, `SROptionSet.dat`, `wndpos.dat`, `silkcfg.dat`, `Silkload.dat` |

Key binary-evidence findings:

- `GameClient.exe` loads `RecMsg.dat` at startup via `CreateFile` (see §3).
- Build path leaked in strings: `D:\vss-od\Silkroad\Client\client\Game.cpp`
  and `D:\vss-od\silkroad\client\client\MsgStreamBuffer.h`.
- Message logging format string: `MSGID:0x%X,R(%d),W(%d),T(%d)` — confirms a
  message-opcode dispatch layer with Read/Write/Total accounting.
- `gmwpfort.dat` contains fortress/instance names (readable strings):
  `BossDungeon`, `Kalia's`, `Survival_Desert`, `Baghdad`,
  `BattlefieldOfinfinity`, `CTF(L)`, `HallofWorship`, `SkyTemple`, `Roc`,
  `Downhang` — game-world/instance/fortress registry.
- `Silkload.dat` is an encoded blob (hex), `silkcfg.dat` is a small binary
  config — item-mall (silk) bootstrap data.

## 2. SQL `.Bak` backups (server-side data model)

Read-only string extraction (ASCII + UTF-16LE) of the four backups yields
candidate table names. No restore; no `sqlcmd`/`mssql` available.

| Database | File | Bytes | Candidate tables |
|----------|------|-------|------------------|
| shard | `SRO_VT_SHARD.Bak` | 93,501,952 | 487 |
| account | `SRO_VT_ACCOUNT.Bak` | 21,592,576 | 71 |
| shardlog | `SRO_VT_SHARDLOG.Bak` | 3,705,344 | 14 |
| certification | `SRO_CERTIFICATION.Bak` | 3,957,248 | 0 (SQL system objects only) |

Curated SHARD tables (definite server-side data model):

- **objects**: `_RefObjCommon`, `_RefObjItem`, `_RefObjChar`, `_RefObjStruct`
- **skills**: `_RefSkill`, `_RefSkillGroup`, `_RefSkillMastery`,
  `_RefAbilityByItemOptLevel`, `_RefSkillByItemOptLevel`
- **characters**: `_Char`, `_CharSkill`, `_CharSkillMastery`, `_CharQuest`,
  `_CharCOS`, `_CharTrijob`, `_CharStorage`, `_CharInstanceWorldData`,
  `_CharNameList`, `_CharNickNameList`, `_DeletedChar`
- **inventory/items**: `_Inventory`, `_InventoryForAvatar`, `_Items`,
  `_InvCOS`, `_ItemPool`, `_ItemQuotation`, `_LatestItemSerial`
- **guild**: `_Guild`, `_GuildMember`, `_GuildChest`, `_GuildWar`, `_AlliedClans`
- **friend**: `_Friend`, `_FriendGroup`
- **teleport**: `_RefTeleport`, `_RefTeleLink`, `_RefOptionalTeleport`
- **shop**: `_RefShop`, `_RefShopGoods`, `_RefShopGroup`, `_RefShopTab`,
  `_RefShopTabGroup`, `_RefShopItemGroup`, `_RefShopObject`,
  `_RefTreatItemOfShop`, `_RefAccessPermissionOfShop`
- **drop**: `_RefDropClassSel_*` (Alchemy_Tablet/Ammo/Cure/Equip/RareEquip/
  Recover/Reinforce/Scroll), `_RefDropGold`, `_RefDropItemAssign`,
  `_RefDropOptLvlSel`, `_RefCustomizingReservedItemDropForMonster`
- **quest**: `_RefQuest`, `_RefCharDefault_Quest`, `_RefSiegeQuest_QuestName`,
  `_RefSiegeQuestReward_QuestID`
- **siege**: `_SiegeFortress*`, `_RefSiege*`, `_SiegeFortressBattleRecord`,
  `_SiegeFortressRequest`, `_SiegeFortressStoneState`, `_SiegeFortressObject`,
  `_SiegeFortressStruct`
- **instance/game world**: `_RefInstance_World_Region`,
  `_RefInstance_World_Start_Pos`, `_RefGame_World`, `_RefClimate`
- **region**: `_RefRegion`, `_RefRegionBindAssocServer`
- **ranking/trade**: `_RefRanking_RobberActivity`,
  `_RefRanking_RobberContribution`, `_RobberActivity`, `_TraderContribution`

New subsystems surfaced by the SHARD schema (beyond the textdata/Lua layer):

- **training camp / mentor**: `_TrainingCamp`, `_TrainingCampMember`,
  `_TrainingCampHonorRank`, `_TrainingCampBuffStatus`,
  `_TrainingCampSubMentorHonorPoint`
- **trijob (3rd job)**: `_CharTrijob`, `_OldTrijob`, `_TrijobRanking4WEB`,
  `_TrijobRewards`
- **consignment trade (auction)**: `_ConsignmentTrade_*`,
  `_UpdateProcessState_ConsignmentTrade_*`
- **flea market / stall**: `_FleaMarketNetwork`
- **robber/trader (thief–hunter–trader)**: `_RobberActivity`,
  `_TraderContribution`, `_RefRanking_*`
- **trade conflict**: `_CheckTradeConflict_UnregisterUserJob`,
  `_QueryStatics_TradeConflictJobStatus`
- **timed job / pet**: `_TimedJob`, `_TimedJobForPet`
- **silk consumption**: `_ConsumeSilkByGameServerD`
- **avatar/costume**: `_StaticAvatar`, `_InventoryForAvatar`, `_CharCOS`
- **chest/storage**: `_Chest`, `_ChestInfo`, `_GuildChest`, `_CharStorage`

No `RecMsg`/`SendMsg` table exists in any backup.

## 3. RecMsg.dat / SendMsg.dat — authoritative determination

- **`RecMsg.dat` → MISSING.** The literal string `RecMsg.dat` occurs once in
  `GameClient.exe` (byte offset 10,428,884, in `Game.cpp` startup, adjacent to
  `CreateFile(%s)` / `File Not Find.` / `Pack File Open Faile ...`). It is a
  real client-side receive-message table loaded at boot. It is absent from all
  PK2 archives, all containers, the client `.7z`, the server package, and all
  SQL backups. It is not reconstructable from any present artifact (it is a
  data table, not derivable from code alone).
- **`SendMsg.dat` → NOT authoritative.** No binary references `SendMsg.dat`.
  `SendMsg` appears only as C++ method names in `SR_GameServer.exe`
  (`SendMsgToPeer`, `SendMsgToAllGameWorldUser`,
  `SendMsgToGameWorldAllianceUser`, `CGameWorldSiege::SendMsgSiegeStructAllInfoForSiegeUser`).
  The prior `KNOWN_MISSING` entry was corrected: `SendMsg.dat` is no longer
  listed as MISSING (reconciliation MISSING count 2 → **1**).

## 4. Source coverage counts (updated)

| Status | Count |
|--------|-------|
| PROVEN | 1,444 |
| PARTIAL | 65 |
| UNKNOWN | 119,295 |
| STUB | 17 |
| DEAD | 19 |
| UNREADABLE | 0 |
| MISSING | 1 (was 2) |
| **Present total** | **120,840** |

By source: pk2 119,631 · filesystem 1,084 · sql-backup 4 · container 121.
Tracked total (present + missing) = **120,841**.

## 5. Remaining gaps (exact reason + authoritative resolver)

| Gap | Reason unresolved | Authoritative resolver |
|-----|-------------------|------------------------|
| `RecMsg.dat` | not shipped in any archive; client references it but no copy present | reverse-engineer `GameClient.exe` opcode dispatch (readable opcode→handler names table) |
| JMX binary internal semantics (`.ddj/.nvm/...`) | binary parsers not yet written | write parsers from the 16 magic-verified families |
| `VSRO-R Client.7z` `Media.pk2` | duplicate of extracted Media (skipped to save disk) | already available via `pk2raw/Media.pk2` |
| SQL `.Bak` row data / live schema | no SQL Server tooling; string scan only | restore via SQL Server (not available here) or parse pages |
| `skilldata_*enc.txt` | encrypted content | locate scheme in `SR_GameServer.exe` / client |
| compiled `.sct`/`.crb` | Lua bytecode, not decompiled | decompile Lua VM bytecode |

## 6. Disk

`/dev/root`: 2.5 GB free (87% used). Client extraction added 16.4 MB.

## 7. Tests

- `scripts/test_source_corpus.py` — updated MISSING assertion (2 → 1), pending
  final run.
- `scripts/test_pk2_reader.py` — 11 OK (unchanged).
- New deliverables JSON-validated; secret scan clean (no credentials in new
  files).

## 8. Deliverables (new/updated this batch)

`CLIENT_SQL_EVIDENCE.json` · `CLIENT_SQL_EVIDENCE.md` ·
`SQL_DATABASE_SCHEMA.json` · `scripts/extract_sql_schema.py` ·
`scripts/build_client_sql_evidence.py` · updated `SOURCE_CORPUS_STATS.json`
(MISSING 2→1) · updated `SOURCE_EXTRACTION_REPORT.md` · updated
`scripts/test_source_corpus.py` · updated `scripts/index_source_corpus.py`
(corrected `KNOWN_MISSING`).

## 9. Single highest-value next step

Write the **JMX binary parsers** for the magic-verified `.nvm` (navmesh) and
`.ddj` (texture) formats — these convert the largest `UNKNOWN` payload families
into PROVEN with real semantic content, using small streamed samples (no full
Data/Map extraction).
