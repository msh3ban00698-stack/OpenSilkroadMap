# Source Subsystem Evidence (Phase 30 — functional coverage)

Read-only, deterministic evidence of what the game source actually implements.
Supersedes structural path-based coverage with concrete evidence (real table
schemas, real Lua API calls, real magic bytes). No gameplay implementation.

## Tool benchmark (result)

| Tool | Role | Speed | Verdict |
|------|------|-------|---------|
| `pk2_table.py` | entry table enumeration (names/sizes/positions) | ~25 s for all 5 PK2 | keep as index layer |
| `pk2_mate` | single-file extraction (data-chain, byte-verified) | ~0.15 s/file | keep as extractor |

Targeted `pk2_mate extract -p <path>` reproduces bytes exactly (hash of extracted
`/navmesh/nv_11a4.nvm` == cached Phase-4 SHA-256 `0e8b0fab…`). **No replacement
adopted** — the `pk2_table` (index) + `pk2_mate` (extract) combination is optimal.
`7z l -slt -ba` remains the container listing tool.

## Format families (magic-byte evidence, 52 records / 25 families)

| Family | Extensions | Magic |
|--------|-----------|-------|
| jmx-texture-ddj | .ddj | `JMXVDDJ` |
| jmx-skeleton-bms | .bms | `JMXVBMS` |
| jmx-skin-bsk | .bsk | `JMXVBSK` |
| jmx-mesh-bsr | .bsr | `JMXVRES` |
| jmx-animation-ban | .ban | `JMXVBAN` |
| jmx-effect-efp | .efp | `JMXVEFF` |
| jmx-navmesh-nvm | .nvm | `JMXVNVM` |
| jmx-strings-cpd | .cpd | `JMXVCPD` |
| jmx-font-img | .dat (fonts) | `JMXVIMG` |
| jmx-map-info-mfo | .mfo | `JMXVMFO` |
| jmx-map-model | .m, .t | `JMXVMAPM` |
| jmx-map-object | .o, .o2 | `JMXVMAPO` |
| jmx-material-bmt | .bmt | `JMXVBMT` |
| jmx-dungeon-object-dof | .dof | `JMXVDOF` |
| jmx-object-info-ifo | .ifo | `JMXVOBJI` |
| cnif-table | .2dt | `CNIF` |
| shader-source | .c, .psh, .vsh | `#include` / `vs.1.1` |
| ogg-audio / wav-audio | .ogg / .wav | `OggS` / `RIFF` |
| tga-texture / dds-texture | .tga / (misnamed .ddj.tmp) | TGA / `DDS ` |
| soundfont-sfk | .sfk | `SFPK` |
| text (utf-8 / cp949 / utf-16) | .txt | — |

The 16-magic JMX family is now named and byte-verified; internal binary
semantics remain UNKNOWN until a parser is written (see gaps).

## Textdata tables (159 tables, schema inventory)

`TEXTDATA_SCHEMAS.json` records each table's encoding, row count, and column
header names (real game headers, not inferred). Highlights:

- **item**: `itemdata_*` (161 cols × ~19,000 items), `itemeffect`,
  `magicoption*`, `refsetitemgroup`, `refpackageitem`, `refscrapofpackageitem`.
- **character/monster/npc**: `characterdata_*` (105 cols × ~16,000
  `CHAR_/MOB_/NPC_/COS_`), `npcpos` (18,456), `npcchat`, `specialnpcdata`.
- **skill**: `skilldata_*` (119 cols × ~25,000; plus `skilldata_*enc.txt`
  encrypted variants), `skilleffect`, `skillgroup`, `skillmasterydata`.
- **quest/event**: `questdata`, `questcontentsdata`, `refquestrewarditems`,
  `refqusetreward`, `textquest_*`, `eventguidedata`, `eventzonedata`.
- **shop/mall**: `shop*`, `refshop*`, `mallitemmenulistdata`, `refpricepolicyofitem`.
- **teleport**: `teleportdata`, `teleportlink`, `teleportbuilding`, `refoptionalteleport`.
- **region/worldmap**: `regioncode` (3,293), `textzonename` (4,249),
  `worldmap_*`, `worldmapguidedata_*`.
- **siege/fortress**: `siegefortress*`, `siegestructupgradedata`, `refsiege*`.
- **alchemy/magic**: `refalchemy_mk_*`, `magicoption*`, `refmagicopt*`.
- **effect/sound/ui**: `effectsound` (6,529), `effectenvsnd`, `atstructeffect`,
  `textuisystem` (5,180), `textdata_object` (9,021).

## Server Lua (quest/event) census

839 files / 1.52 MB: 830 quest + 6 event + `@Define.lua`/`@QuestList.lua`/
`@EventList.lua`.

- unique monsters `647`, unique items `707`, unique NPCs `207`, unique NPC name
  strings `205`.
- mission types (13): catch monster, change item, deliver item, dialog,
  different-quest-clear, escort NPC, gather item from field/monster/NPC, kill
  monster, kill player, talisman collection, time check.
- 77 Lua API functions, top: `LuaGetQuestID`, `LuaSetStartMethod`,
  `LuaSetStartCodition`, `LuaQuestInsertNpc`, `LuaSetMissionDataSize`,
  `LuaInsertQuest`, `LuaSetAchievementLimit`, `LuaSetCollectionItemMissionData`,
  `LuaSetAchievedItem`/`SkillPont`/`Point`, `LuaSetPayStep`, race/job start
  conditions.

## Subsystem → evidence map

`SUBSYSTEM_EVIDENCE.json` maps 15 subsystems (item, character/monster/npc, skill,
quest, event, shop/mall, teleport, region/zone/worldmap, siege/fortress,
alchemy/magic-option, gacha/collection, effect/sound, ui/text, level/job/trade,
abuse-filter) to their concrete evidence sources.

## Data/Map text files upgraded to PROVEN (targeted extraction)

`RegionInfo.txt` (TOWN/FIELD region table), `dungeon/Dungeoninfo.txt`,
`shader/regioninfo.txt`, `camera_path.txt`, `layerobjdef.txt` — all extracted and
decoded as readable text (utf-8/cp949). Confirmed region/map data, not stubs.

## Gaps + best next evidence source

| Gap | Best next source |
|-----|------------------|
| `RecMsg.dat` / `SendMsg.dat` (protocol opcode→payload) | disassemble `GameClient.exe`/`SR_GameServer.exe`: static string/xref of message dispatch + receive/send structs |
| SQL `.Bak` contents | restore/parse `SRO_VT_SHARD.Bak` etc. for live schema + seed data |
| JMX binary internal semantics | write parsers from the 16 magic-verified families (start: `.nvm` navmesh, `.ddj` texture) |
| `VSRO-R Client.7z` (client exe/dll/RD region/Setting) | extract the 121 files (small, non-PK2) |
| `skilldata_*enc.txt` (encrypted) | locate encryption scheme in `SR_GameServer.exe` / client |
| compiled `.sct`/`.crb` server scripts | decompile (Lua bytecode) |

## Verification

- `scripts/verify_formats.py` → `FORMAT_VERIFICATION.json` (52 records).
- `scripts/parse_textdata.py` → `TEXTDATA_SCHEMAS.json` (159 tables).
- `scripts/build_subsystem_evidence.py` → `SUBSYSTEM_EVIDENCE.json` (15 subsystems).
- Python `test_source_corpus.py` (5) + `test_pk2_reader.py` (11) still pass.

## Deliverables (new this phase)

`FORMAT_VERIFICATION.json` · `TEXTDATA_SCHEMAS.json` · `SUBSYSTEM_EVIDENCE.json` ·
`SOURCE_SUBSYSTEM_EVIDENCE.md` · `scripts/verify_formats.py` ·
`scripts/parse_textdata.py` · `scripts/build_subsystem_evidence.py`.
