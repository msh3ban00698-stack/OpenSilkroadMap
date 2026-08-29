# VSRO v1.193 Source Inventory (A-H)

Read-only inventory of files actually listed in this session. Nothing here
reconstructs a server, ports the Windows client to Android, or invents a
network protocol.

Date: 2026-08-29. Method: `7z l` / `unrar l` plus extraction of small
text/config only. No EXE/DLL was executed. PK2 interiors were not re-opened.
Claims not confirmed by a listing or a small text extract are marked
**[unverified]**.

Architecture target (not implemented here): Android = client; Windows EXE +
SQL Server = external authoritative server. Do not run server EXEs on Android.

---

## A. Sources obtained

| Source | Status | Path / size | Notes |
| --- | --- | --- | --- |
| MediaFire ZIP | Obtained | `/tmp/opencode/VSRO-R_Client.zip` (213,646,487 B). ZIP magic; `unzip -t` OK. Extracted to `/tmp/opencode/vsro_pkg/VSRO-R Client/` (originals kept). | Nested archives listed below. |
| `PK2 Files.7z` | Obtained earlier | `/tmp/opencode/PK2_Files.7z` (1,546,426,717 B, valid 7z). **Not extracted.** | Data/Map/Music/Particles only. No `Media.pk2`. |
| Google Drive `1YHzlygD5HNsFGhOYX4yYJ-oS1w2MPM61` | **Blocked** | View HTTP 403 ToS (`title: Salah`); download HTTP 404. | That ZIP was not obtained. |
| `pk2reader.py` / `jmblowfish.py` | **Absent** | Not in this repo and not in the MediaFire package. | Live PK2 extraction not claimed. |
| `listing_media.txt` / `listing_music.txt` | **Absent** | Not in `PK2 Files.7z` or `VSRO-R Client.7z`. | Optional for UI/icon/audio extractors. |

MediaFire outer ZIP (`7z l`, 9 files + 1 folder):

| Nested file | Compressed size (B) |
| --- | --- |
| `VSRO-R Client.7z` | 195,170,460 |
| `Vietnam-R v193 Package Server.7z` | 10,994,403 |
| `Database.7z` | 6,951,722 |
| `VSRO-R Proxy v1005.rar` | 448,117 |
| `Event-HAPPY-Working-Files-vsro-193.7z` | 6,957 |
| `GSPatcher.rar` | 5,281 |
| `ClientPatcher.rar` | 4,870 |
| `vSRO-R.txt` | 1,680 |
| `Vietnam-R v193 Offsets.txt` | 1,527 |

Package notes (`vSRO-R.txt`): filename-level claims only (cap 140, skills
111-150, added regions/dungeons, removed penalties). **Not runtime-verified.**

`Vietnam-R v193 Offsets.txt`: GameServer / GameClient / ShardManager memory
offsets as hex addresses. **Not runtime-verified.** Not a packet spec.

Disk at inventory time: ~14 G free on `/`. Full PK2 uncompressed (~5.7 GiB
including Media) plus the existing 1.5 GiB 7z would be tight. Entire PK2s
were not extracted.

---

## B. Client (`VSRO-R Client.7z`)

Archive: 195,170,460 B, LZMA2:24 BCJ, solid. Listing: 120 files, 5 folders,
839,479,455 B uncompressed.

### Executables and DLLs (not run)

| File | Size (B) |
| --- | --- |
| `GameClient.exe` | 11,845,632 |
| `Launcher.exe` | 1,003,520 |
| `Uptodate.exe` | 593,408 |
| `MuitClient.exe` | 506,368 |
| `dbghelp.dll` | 894,464 |
| `GFXFileManager.dll` | 731,128 |
| `edxSilkroadDll5.dll` | 296,448 |
| `msvcp60.dll` | 401,462 |

### PK2 in this archive

| File | Size (B) |
| --- | --- |
| `Media.pk2` | 823,066,624 |

No `Data.pk2`, `Map.pk2`, `Music.pk2`, or `Particles.pk2` here. Those four
are only in `/tmp/opencode/PK2_Files.7z`.

### Other client files (listed, not reverse-engineered)

- Directories: `Dump/`, `RD/`, `ScreenShot/`, `Setting/`, `Temppath/`
  (Dump/ScreenShot/Temppath empty in the listing).
- `RD/*.rd`: 103 files, 1,338 B each (`A64_*.rd`, `G64_*.rd`). Purpose
  **[unverified]** (names look like region/resource dumps).
- `Setting/`: `gmwpfort.dat`, `SRChattingBlockingList.dat`,
  `SRExtQSOption.dat`, `SRExtQSOption2.dat`, `SROptionSet.dat`, `wndpos.dat`.
- `silkcfg.dat` (23 B, binary; not decoded).
- `Silkload.dat` (170 B ASCII hex; meaning **[unverified]**).

No client `.pdb`, no packet sniffer logs, no `pk2reader.py`.

---

## C. Server (`Vietnam-R v193 Package Server.7z`)

Archive: 10,994,403 B. Listing: 1,045 files, 13 folders, 141,093,711 B
uncompressed.

### Process EXEs (not run)

| File | Size (B) | Role from filename / `server.cfg` section |
| --- | --- | --- |
| `SR_GameServer.exe` | 9,576,448 | `SR_GameServer` |
| `SR_ShardManager.exe` | 5,062,656 | `SR_ShardManager` |
| `GlobalManager.exe` | 1,417,216 | `GlobalManager` |
| `GatewayServer.exe` | 1,028,096 | `GatewayServer` |
| `AgentServer.exe` | 929,792 | `AgentServer` |
| `FarmManager.exe` | 901,120 | `FarmManager` |
| `MachineManager.exe` | 864,256 | `MachineManager` |
| `DownloadServer.exe` | 864,256 | `DownloadServer` |
| `smc.exe` | 708,608 | Service Manager Console |
| `CertModule/Replace.Certification.exe` | 25,600 | Certification helper |
| `Script/VIETNAM_LUA/luac.exe` | 208,896 | Lua compiler |
| `Script/VIETNAM_LUA/helper.exe` | 6,656 | Lua helper |

### Notable DLLs (not run)

`ImageTrans.dll` (12,328,960), `GFXFileManager.dll`, `ggauth.dll`,
`XTrap4Server.dll`, `MailSender.dll`, `VerData.dll`, `CommonGuiControl.dll`,
`ServerFrameworkRes.dll`, `dbghelp.dll`, plus `SMPlugins/*.dll`:
`CAS`, `ConcurrentUserLog`, `IPBlock`, `ModulePatch`, `Notice`, `Security`,
`ServerControl`, `SR_Notice`, `SR_Scheduler`, `SR_Statistics`, `SR_UserBlock`,
`SR_UserData`, `SR_UserEdit`, `SR_UserLog`, `SR_UserPunishment`, `UserControl`,
`UserStatistics`.

### Config (small files extracted; secrets redacted)

`server.cfg` names these processes and certification bind points (RFC1918
host in package; **not claimed live**):

| Process | Port in `server.cfg` |
| --- | --- |
| GlobalManager Certification | 32000 |
| MachineManager / Gateway / Download / Farm Certification | 15880 |
| AgentServer / SR_ShardManager / SR_GameServer Certification | 15882 |
| SR_ShardManager BILLING_SERVER_URL | HTTP port 8090 |

Also in `server.cfg` (filename-level, not runtime-verified):
`LOCALE_VIETNAM`, `ExpRatio` / `ExpRatioParty` / drop rates, Battle Arena /
Flag event toggles, `PCSpeedRatio`, `LastFullVersion_SR_Client 1`.

`ServiceManager.cfg`: SMC `DivisionManager "127.0.0.1",15880`;
ModulePatch `Patch_Internal` -> `Patch_Internal_Comp`.

`smc_updater.cfg`: GatewayServer `127.0.0.1`.

`CertModule/Config/Certification.xml`: SQL Server connection strings for
`SRO_CERTIFICATION` and `SRO_VT_ACCOUNT` (`User ID=sa; Password=[REDACTED]`),
billing IP/port 8090, whitelist hosts `[REDACTED RFC1918]`. `.NET` 4.5
runtime in `Replace.Certification.exe.config`. `NLog.config` is logging only.

`SMC_Punishment.cfg`: email placeholders only (`[REDACTED]`).
`SMC_ServerControl.cfg`: 268 B binary; not decoded.

### Scripts and ref data (listed, not executed)

- `Script/VIETNAM/`: `define.sct`, `Event.sct`, `EventList.sct`, `Quest.sct`
  (1,800,488 B), `QuestList.sct`.
- `Script/VIETNAM_LUA/`: 839 `.lua` files (Event + Quest), plus make_*.bat.
- `SR_GameRefData/`: 126 `.txt` files (character/item/skill/shop/teleport/
  npcpos/quest/region/worldmap, UTF-16 **[assumed from Phase A Media
  textdata; this session listed names/sizes only]**).
- `Crest/*.crb` (18), `Map1.CS3` / `Map2.CS3`, `AbuseFilter.txt`,
  `EmailTemplate/Template.html`.
- `Patch_Internal/` and `Patch_Internal_Comp/` exist as empty dirs in the
  listing.

---

## D. Database (`Database.7z`)

SQL Server `.Bak` files dated 2021-09-03. **Not restored. Not opened.**
Contents unknown beyond filenames and uncompressed sizes.

| File | Uncompressed size (B) |
| --- | --- |
| `SRO_CERTIFICATION.Bak` | 3,957,248 |
| `SRO_VT_ACCOUNT.Bak` | 21,592,576 |
| `SRO_VT_SHARD.Bak` | 93,501,952 |
| `SRO_VT_SHARDLOG.Bak` | 3,705,344 |
| **Total** | **122,757,120** |

Name mismatch vs proxy config: proxy `MSSQL_LOG_DB=SRO_VT_LOG` while the
backup is `SRO_VT_SHARDLOG.Bak`. Unresolved.

Engine implied by `Certification.xml`: SQL Server Express instance name in
the package (`[REDACTED]\SQLEXPRESS`). Not present in this Linux workspace.

---

## E. PK2 archives

### Where each archive lives (this session)

| Archive | Uncompressed size (B) | Container | Extracted? |
| --- | --- | --- | --- |
| `Data.pk2` | 3,351,891,968 | `PK2_Files.7z` | No |
| `Map.pk2` | 1,268,441,088 | `PK2_Files.7z` | No |
| `Music.pk2` | 76,488,704 | `PK2_Files.7z` | No |
| `Particles.pk2` | 178,126,848 | `PK2_Files.7z` | No |
| `Media.pk2` | 823,066,624 | `VSRO-R Client.7z` | No |

`PK2_Files.7z` listing total: 4,874,948,608 B uncompressed, 4 files.
Five-PK2 uncompressed total including Media: 5,698,015,232 B.

`EXTERNAL_PACKAGE_INVENTORY.md` previously said `PK2 Files.7z` held five
PK2s. This listing shows four; `Media.pk2` is in the client 7z.

### Interior layout

**Not re-walked this session.** Prior Phase A inventory (pk2_mate / custom
Joymax Blowfish reader, key `169841`) described Data/Map/Media/Music/Particles
trees. Treat those counts as **previously verified, not re-verified here**.
This session did not run a PK2 reader and does not claim header checksums.

Canonical pipeline (repo):

```
PK2 root -> extract -> game_source/ -> generate -> map/public/assets/gamedata/
```

Expected layout: `Data.pk2` `Map.pk2` `Media.pk2` `Music.pk2` plus optional
`Particles.pk2` and listings. Reader API: `PK2(path)`, `.find()`,
`.read_file()`. Blowfish key `169841` is documented; **not re-checked here**.

---

## F. Protocol / networking

**No packet layout, opcode dictionary, or TCP/WebSocket spec exists in this
package or in the repo.** Do not invent one.

What was actually found:

- Memory offsets file (client/GS/ShardManager) — not packets.
- Proxy `Features/MALICIOUS_OPCODES.txt`: 38 hex values as a **blocklist**
  (no structure, no direction, no payload).
- Proxy `proxy_cfg.ini` bind/public ports (package values, not live):

| Service | Public port | Private port |
| --- | --- | --- |
| Gateway | 5001 | 1337 |
| Agent | 5002 | 1338 |
| Download | 15881 | 15881 |

- Proxy `[SR_CLIENT]`: `CL_GW_PORT=15779`, `CL_VERSION=188`, `CL_LOCALE=22`.
  Package is labeled v193; client version **188** in this ini is a
  discrepancy, **unresolved**.
- `server.cfg` certification ports (15880 / 15882 / 32000) and billing HTTP
  8090 — process bind config, not a client protocol.
- No Wireshark dumps, no `*.pkt`, no Joymax gateway handshake docs.

Repo client (`map/src/game/storage.ts`, `capacitor.config.ts`):
`localStorage` + static `/assets` fetch. Capacitor WebView scheme `https`.
No GameServer TCP/WebSocket client.

---

## G. Repository client (what git already is)

This repo is OpenSilkroadMap: a Vite/OpenLayers map plus a Capacitor Android
wrapper around the same web build. It is **not** a vSRO GameServer and **not**
a replacement protocol stack.

| Area | In repo | Notes |
| --- | --- | --- |
| 2D world map | `world.pmtiles`, NPC/teleport JSON | See `GAME_CONTENT_VERIFICATION.md` |
| 3D regions 1-9 + 32785 | committed `img/silkroad/game/region*` | Geometry present; authentic NPC/shop/quest JSON often missing |
| Phase H starter JSON | `map/src/game/data/*.json` bundled | Levels/items/skills/masteries starter set |
| Full `gamedata/` | gitignored, generated | Needs `game_source/` from PK2 extract |
| Accounts / characters | `localStorage` | Offline |
| Android | Capacitor `com.opensilkroadmap.app`, `webDir: map/dist` | HTTPS WebView; no cleartext |
| PK2 reader | **Not in repo** | `--reader-dir` / `SRO_READER_DIR` |
| Server EXEs / SQL backups | **Not in repo** (and must stay out) | `.gitignore`: `game_source`, most `map/public/assets/*` |

Pipeline scripts: `scripts/sro_paths.py`, `scripts/extract_sro.py`
(`validate` / `extract` / `generate`), plus convert/generate_* and
`build_game_database.py`. Tests: `python3 scripts/test_sro_pipeline.py`
(no PK2 required).

Proxy/patcher/event extras (listed only):

- `VSRO-R Proxy v1005.rar`: `VSROProxy.exe` (1,496,064 B), `sr_proxy.dll`,
  `proxy_cfg.ini`, empty skill-block lists, chat keyword filter, netcafe IP
  list (IPs **[REDACTED]**), Auto Events / Message / Prerequisites text.
  RAR method needed `unrar` (p7zip failed on several files).
- `GSPatcher.rar`: `Patcher.exe` (11,776 B). **Not run.**
- `ClientPatcher.rar`: `ClientPatcher.exe` (11,264 B). **Not run.**
- `Event-HAPPY-Working-Files-vsro-193.7z`: `Event.sct` (60,366 B),
  `EventList.sct` (712 B). EventList strings include
  `QEV_CH_EVENT_MAGIC_STONE`, `UPGRADE_STONE`, `TRADE`, `KISAENG_GLOBAL2011_2`.

---

## H. Verified vs unknown, blockers, next phase

### Verified this session

- Nested archive **file names and sizes** for MediaFire ZIP, PK2 7z, client
  7z, server 7z, Database 7z, Event 7z, both patcher RARs, Proxy RAR.
- `Media.pk2` is in `VSRO-R Client.7z`, not in `PK2 Files.7z`.
- Server process list, config **keys/ports**, SQL backup **filenames**.
- Repo has no vSRO TCP/WebSocket protocol implementation.
- Google Drive ZIP not obtainable from this environment.

### Unknown / not claimed

- PK2 interior file counts (rely on prior Phase A; not re-listed).
- SQL table schemas (backups unopened).
- Any packet format, encryption beyond documented PK2 Blowfish key, or
  opcode meaning.
- Whether `GameClient.exe` is patched vs stock v193 (offsets file exists;
  binaries not executed or disassembled).
- Whether proxy `CL_VERSION=188` matches this `GameClient.exe`.
- `pk2reader.py` availability on a future machine.

### Blockers for extraction/generate (not for this inventory)

1. No `pk2reader.py` / `jmblowfish.py` in repo or package.
2. PK2s still archived; disk ~14 G; do not dump all PK2s into `/workspace`.
3. `listing_media.txt` / `listing_music.txt` missing (optional).
4. Google Drive package still 403/404.

### Explicitly out of scope (do not do next)

- Android conversion of Windows EXEs, GameWorld, multiplayer, replacement
  server.
- Running or reverse-engineering EXE/DLL.
- Committing PK2s, `game_source/`, SQL backups, or secrets.
- Inventing packet layouts.

### Allowed next phase (when a reader and disk exist)

1. Place PK2s **outside git**: Media from Client.7z + four from `PK2_Files.7z`.
2. Supply reader via `--reader-dir`; `python3 scripts/extract_sro.py extract`
   then `generate`.
3. Keep proprietary blobs out of Git; regenerate gitignored `gamedata/`.
4. Continue documenting gaps in `GAME_CONTENT_VERIFICATION.md` against real
   outputs — still no protocol work.

### Secrets handling

Extracted configs contained SQL passwords, FTP URLs, RFC1918 IPs, GM names,
and public netcafe IPs. **None of those values are copied into this repo.**
Working copies remain under `/tmp/opencode/extract/` only.
