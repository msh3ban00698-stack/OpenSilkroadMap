# PHASE 11 SYSTEM STATUS MATRIX

Updated 2026-08-29. This is the Phase 11 update of the system-status matrix
(previously §6 of `PROJECT_STATUS_AUDIT_2026-08-29.md`). Rules honoured: no system
is marked implemented on scaffolding alone; every claim cites original evidence;
UNKNOWN is stated where evidence is missing; Android runtime verification is NO
everywhere (no device/JDK in this environment — `./gradlew test` NOT EXECUTED).

Status legend:
- **DATA** — verified real source data committed (path/size/sha in
  `COMPLETE_SOURCE_INVENTORY.json` / `TEXTDATA_CATALOG.tsv`).
- **DECODED** — a committed, tested decoder produces structured output.
- **ANDROID** — a committed Android/JVM consumer module exists.
- **BLOCKED** — required format is UNKNOWN (`ban`/`nvm`/`bms`/`efp`/`t`/`dat`…).

| System | Original evidence | Source files | Format | Extraction | Conversion | Android impl | Tests | Runtime verified |
|---|---|---|---|---|---|---|---|---|
| Client startup | shell exists | — | — | — | — | PARTIAL (native shell, WebView launcher) | written | NO |
| Login | none (offline target) | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Character selection | `characterdata_*.txt` (index + tiers) | Media textdata | TEXT | PARSED | data only | NOT STARTED | catalog | NO |
| Character creation | `characterdata_*.txt`, `startchar` (none) | Media textdata | TEXT | PARSED | data only | NOT STARTED | catalog | NO |
| World/map loading | `gameworldconfigdata.tsv`, `gameworlddata.tsv`, `worldmap_*.tsv` | Media textdata | TEXT | NORMALIZED | data only | PARTIAL (native shell) | test_phase11 | NO |
| Terrain | `Map.pk2/*.m` (4,491) | `.m` | DECODED (Phase 10) | 23 grids committed | 23 `.hg` | PARTIAL (native world module) | test_world_terrain | NO |
| Zone tiles | `Map.pk2/*.t` (4,989) | `.t` | PARSEABLE | inventoried | — | NOT STARTED | — | NO |
| Buildings/static | `Data/Map *.bms`, `.bsr`, `*.o` | `.bms`/`.bsr`/`.o` | PARSEABLE | inventoried | — | NOT STARTED | — | NO |
| Object instances | `Map.pk2/*.o2` (4,348) | `.o2` | DECODED (Phase 10) | fixtures committed | — | PARTIAL (world module) | test_world_terrain | NO |
| NPCs | `npcpos.tsv` (18,457 spawns), `characterdata_*` | Media textdata | TEXT | NORMALIZED | data only | NOT STARTED | test_phase11 | NO |
| Spawns | `npcpos.tsv`, `eventzonedata.txt`, `force_addobject.txt` | Media textdata | TEXT | NORMALIZED | data only | NOT STARTED | test_phase11 | NO |
| Player character | none dedicated | — | UNKNOWN | — | — | PARTIAL (PlayerState scaffolding) | entity tests | NO |
| Character movement | `.ban`/`.bsk` | `ban`/`bsk` | PARSEABLE | inventoried | — | NOT STARTED | — | NO (needs .ban decoder) |
| Animations | `.ban` 4,796, `.bsk` 1,040 | `ban`/`bsk` | PARSEABLE | inventoried | — | NOT STARTED | — | BLOCKED (format pending) |
| Camera | none (generic) | — | UNKNOWN | — | — | PARTIAL (generic Camera2D) | camera tests | NO |
| Items | `itemdata_*.txt` (161 cols), `textdata_object.txt` | Media textdata | TEXT | PARSED | data only | NOT STARTED | catalog | NO |
| Equipment | `itemdata_*`, `item_grouping.txt` | Media textdata | TEXT | PARSED | — | NOT STARTED | — | NO |
| Inventory | none dedicated | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Skills | `skilldata_*.txt` (cataloged), `skillgroup.txt`, `skillmasterydata.txt` | Media textdata | TEXT (plaintext tiers) | PARSED | data only | NOT STARTED | catalog | NO |
| Skill effects | `skilleffect.txt`, `efp` 3,395 | `.efp` | PARSEABLE | inventoried | — | NOT STARTED | — | BLOCKED (format pending) |
| Monsters | `characterdata_*` (NPC tables), `npcpos.tsv` | Media textdata | TEXT | PARSED | data only | NOT STARTED | catalog | NO |
| NPC interaction | `npcchat.txt`, `specialnpcdata.txt` | Media textdata | TEXT | PARSED | — | NOT STARTED | — | NO |
| Shops | `refshop.tsv`, `refshopgoods.tsv`, `refshoptab*`, `shopdata.txt` | Media textdata | TEXT | NORMALIZED | data only | NOT STARTED | test_phase11 | NO |
| Quests | `questdata.tsv`, `refqusetreward.tsv`, `questcontentsdata.txt`, `textquest_*` | Media textdata | TEXT | NORMALIZED | data only | NOT STARTED | test_phase11 | NO |
| Party | none dedicated | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Guild | `refsiegebuff.txt`, `siege*` (cataloged only) | Media textdata | TEXT | PARSED | — | NOT STARTED | — | NO (partial source) |
| Chat | none (protocol) | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Trading | none dedicated | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Storage/warehouse | none dedicated | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Teleport | `teleportdata.tsv`, `teleportlink.tsv`, `teleportbuilding.tsv`, `refoptionalteleport.tsv` | Media textdata | TEXT | NORMALIZED | data only | NOT STARTED | test_phase11 | NO |
| Level/experience | `leveldata.tsv` (150), `levelgold.tsv` | Media textdata | TEXT | NORMALIZED | data only | NOT STARTED | test_phase11 | NO |
| Stats/classes | `characterdata_*`, `hwanleveldata.txt` | Media textdata | TEXT | PARSED | — | NOT STARTED | — | NO |
| Combat | `skilldata_*` + `.ban` | — | PARTIAL (data; anim BLOCKED) | PARSED | — | NOT STARTED | — | BLOCKED (format pending) |
| Damage calc | `skilldata_*`, `itemdata_*` columns | Media textdata | TEXT | PARSED (schema) | — | NOT STARTED | catalog | NO (field semantics Phase 12) |
| Drops/loot | `refscrapofpackageitem.txt`, `refpackageitem.txt` | Media textdata | TEXT | PARSED | — | NOT STARTED | — | NO |
| AI | `dat` (ainavdata), `nvm` | `.dat`/`.nvm` | UNKNOWN / PARSEABLE | inventoried | — | NOT STARTED | — | BLOCKED (format unknown) |
| Effects/particles | `efp` 3,395 + Particles.pk2 `ddj` | `.efp` | PARSEABLE | inventoried | — | NOT STARTED | — | BLOCKED (format pending) |
| Sounds | 2,885 `wav` | `.wav` | DECODED | samples converted | audio samples | NOT STARTED | sample tests | NO |
| Music | 50 `ogg` | `.ogg` | DECODED | sample converted | audio sample | NOT STARTED | — | NO |
| Minimap | Media `ddj` (5,523 + 2,214) | `ddj` | DECODED | 7,737 PNGs | textures | PARTIAL (native minimap module) | verify_phase8 | NO |
| UI/HUD | `textuisystem.txt`, `texthelp.txt`, `gameguidedata.txt`, UI `ddj` | Media textdata | TEXT | PARSED | data only | PARTIAL (native HUD) | — | NO |
| Settings | none | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Save/load | none (client state UNKNOWN) | — | UNKNOWN | — | — | NOT STARTED | — | NO |
| Account/login backend | none | — | — | — | — | NOT STARTED | — | NO |
| Database access | `db` (Particles, 23 MB, string table) | `.db` | UNKNOWN | inventoried | — | NOT STARTED | — | BLOCKED (format unknown) |
| Network protocol | none in archives | — | — | — | — | NOT STARTED | — | NO |
| Game/world server | none | — | — | — | — | NOT STARTED | — | NO |
| Auth server | none | — | — | — | — | NOT STARTED | — | NO |

## UNKNOWNs and blockers recap
- Formats UNKNOWN: `dat`, `db`, `scc`, `msf`; client-encrypted `skilldata_*enc`.
- Formats magic-verified, decoder pending: `ban`, `bsk`, `nvm`, `bms`, `bsr`, `t`,
  `o`, `bmt`, `efp`, `cpd`, `dof`, `mfo`, `2dt`, `sfk`.
- Systems blocked by those formats: animations, movement/combat timing, navmesh/AI,
  buildings/tiles rendering, effects/particles, database access.

## Exact next action per system (top blockers)
1. `.ban`/`.bsk` decoder (unblocks movement, combat, animations) — real sample fixtures, no guessing.
2. `.nvm` decoder (unblocks AI/pathing) — real sample fixtures.
3. `.bms` + `.t` decoder (unblocks building/tile rendering).
4. `.efp` decoder (unblocks effects/particles).
5. Android TSV parsers + tests for the 21 normalized datasets (npcpos, leveldata,
   teleport, shops, quests, worldmap) — unblocks spawns, progression, teleport,
   shops, quests, world UI.
