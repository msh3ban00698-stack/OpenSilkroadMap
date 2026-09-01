# Source Partial Coverage (Phase 29)

What is PROVEN, what is merely indexed, and what is unproven — so downstream
work never mistakes a filename/extension for recovered semantics.

## PROVEN (1,444) — payload on disk and readable

- Server Lua scripts (839) under `extract/server/Script/**/*.lua`.
- Server text/config (`*.txt`, `*.cfg`, `*.xml`, `*.config`, `*.sct`).
- Proxy config/feature text (`*.txt`, `*.ini`).
- Client text data tables extracted from Media.pk2
  (`server_dep/silkroad/textdata/*.txt`, 436) + other extracted text.
- Client `RegionInfo.txt` region table (extracted? — see note below).

## PARTIAL (65) — text/code identified but not extracted

Mostly the handful of text files still inside Data/Map PK2s and the client
container configs:
- Data.pk2: `RegionInfo.txt`, `shader/regioninfo.txt`, `dungeon/Dungeoninfo.txt`.
- Map.pk2: `camera_path.txt`, `layerobjdef.txt`.
- VSRO-R Client.7z: `Setting/*.dat`, `silkcfg.dat` (binary-ish config, tagged
  partial where text-typed), `Vietnam-R v193 Offsets.txt` / `vSRO-R.txt`.

## STUB (17) — zero-byte placeholders

- Data.pk2 empty `.bsk` skeletons (e.g. `Demon_Air rock01.BSK`,
  `elemental_stand01.bsk`, `ghost_gluttony_die.bsk`, `npc_eu_carnival.bsk`).
- Particles.pk2 empty `.efp` (`petra_flame_yellow_glow.efp`).
- Proxy empty feature files (`*_BLOCKED_SKILL_IDS.txt`, `MALICIOUS_OPCODES.txt`,
  `FILTER_KEYWORDS.txt`, `NETCAFE_IPS.txt` — all 0 bytes in the proxy tree).

## DEAD (19) — non-game artifacts

- `thumbs.db`, `desktop.ini`, `vssver.scc` (multiple), `*.tmp`, `*.sfk`.

## MISSING (2) — referenced but absent everywhere

- `RecMsg.dat`, `SendMsg.dat` (message protocol tables).

## UNKNOWN (119,295) — binary, semantics unproven

All binary formats. Format families identified by extension/magic only, never
decoded to semantics:
- JMX geometry: `.ddj` (47,495), `.bms` (22,948), `.bsr` (7,549), `.bsk` (1,040).
- JMX navmesh `.nvm` (6,041) + `AINavData_*.dat` (26).
- JMX animation `.ban` (4,796), JMX effect `.efp` (3,395), JMX strings `.cpd` (124).
- Map `.t/.m/.o/.o2/.ifo/.bmt/.2dt/.dof`.
- Audio `.wav` (2,885), `.ogg` (50).
- PE binaries `.exe` (client+server) and `.dll`.
- SQL backups `.Bak` (4), Windows `thumbs.db` (DEAD).

## Container-only, not extracted (121)

`VSRO-R Client.7z`: `GameClient.exe`, `Launcher.exe`, `MuitClient.exe`,
`Uptodate.exe`, DLLs, `RD/G64_*.rd` (region data), `Setting/*.dat`,
`silkcfg.dat`, `Silkload.dat`. Plus `ClientPatcher.rar`, `GSPatcher.rar`
(patcher executables).

## Principle

No UNKNOWN binary is converted to PROVEN semantics. Filenames, directory names,
and strings are coverage leads only. Any future claim about a game system
(movement, spawn, combat, economy, protocol, etc.) must be backed by a decoded
format or extracted content, not by naming.
