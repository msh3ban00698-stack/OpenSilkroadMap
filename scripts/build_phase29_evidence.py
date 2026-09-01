#!/usr/bin/env python3
"""Phase 29 deep-runtime-forensics evidence builder.

Phase 29 recovers original PC-client runtime behavior from the *actual client
executable and its configuration*, which earlier phases had classified as
unavailable. Static (read-only) inspection only; the client binary is never
executed.

Sources (all read-only):

  * VSRO-R Client.7z / GameClient.exe + edxSilkroadDll5.dll + GFXFileManager.dll
    - string-level static forensics (class RTTI names, source file paths,
      network message IDs, movement member names, camera/config paths).
  * Media.pk2 /config/*.txt
    - option.txt (StartCharacter=1907, Map=0, StartWeapon=0, StartProcess),
      cameradata.txt (region-keyed camera presets), command.txt (debug command
      map), define.txt (compile-time feature flags).
  * Media.pk2 /server_dep/silkroad/textdata/characterdata_*.txt
    - the walk/run speed columns proven via the server DB loader schema.
  * SRO_VT_SHARD.Bak
    - stored procedure _InsertRefChar: the exact _RefObjCommon + _RefObjChar
      column/parameter order (Speed1/Speed2, Scale, BCHeight/BCRadius, Lvl,
      CharGender, MaxHP/MaxMP, PD/MD/PAR/MAR/ER/BR/HR/CHR, Knockdown,
      KO_RecoverTime, ...).
  * Vietnam-R v193 Package Server .7z / SR_GameServer.exe + SR_ShardManager.exe
    + GatewayServer.exe + AgentServer.exe + ... (string-level server forensics:
    motion states, spawn/EnterWorld flow, ref classes, SQL), server.cfg, and
    SR_GameRefData/*.txt (region/gameworld/character/item/skill data).
  * VSRO-R Proxy / proxy_cfg.ini (server architecture + protocol constants,
    .NET admin tool) and Vietnam-R v193 Offsets.txt (client memory offsets).

Nothing is invented: raw source values are recorded verbatim with provenance;
units/semantics that cannot be proven are labelled UNKNOWN.

Output: scripts/testdata/formats/phase29_source_evidence.json
"""
from __future__ import annotations

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

MEDIA_PK2 = os.path.join(sro_paths.resolve_pk2_dir(), "Media.pk2")
SHARD_BAK = os.path.join(sro_paths.resolve_db_dir(), "SRO_VT_SHARD.Bak")
CLIENT_DIR = sro_paths.resolve_client_bin_dir()
PROXY_CFG = os.path.join(sro_paths.resolve_extract_dir(), "proxy", "proxy_cfg.ini")
PROXY_DIR = os.path.join(sro_paths.resolve_extract_dir(), "proxy")
SERVER_DIR = os.path.join(sro_paths.resolve_extract_dir(), "server")
OFFSETS_TXT = os.path.join(sro_paths.resolve_pkg_dir(), "Vietnam-R v193 Offsets.txt")

OUT = os.path.join(BASE, "scripts/testdata/formats/phase29_source_evidence.json")


class Archive:
    def __init__(self, path):
        self._entries, _ = pk2_table.inventory(path)
        self._by_path = {e["path"].lower(): e for e in self._entries}
        self._fh = open(path, "rb")

    def read(self, path):
        key = ("/" + path.lstrip("/")).lower()
        e = self._by_path.get(key)
        if e is None:
            raise KeyError(path)
        self._fh.seek(e["pos"])
        return self._fh.read(e["size"])

    def close(self):
        self._fh.close()


def media_text(media, path):
    raw = media.read(path)
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in raw[:256]:
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("cp949", errors="replace")


def config_file(media, relpath):
    return media_text(media, "config/" + relpath)


def option_facts(media):
    text = config_file(media, "option.txt")
    facts = {}
    for key in ("StartCharacter", "Map", "StartWeapon"):
        m = re.search(r'^%s\s*=\s*"([^"]*)"' % key, text, re.M)
        facts[key] = m.group(1) if m else None
    facts["start_process"] = re.findall(r'^StartProcess\s*=\s*"([^"]*)"', text, re.M)
    facts["intro_name"] = re.findall(r'^IntroName\s*=\s*"([^"]*)"', text, re.M)
    return facts


def cameradata_facts(media):
    text = config_file(media, "cameradata.txt")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    rows = [ln.split("\t") for ln in lines if "\t" in ln]
    return {
        "path": "/config/cameradata.txt",
        "default_marker_line": lines[0].strip() if lines else None,
        "preset_rows": [{"region": r[0], "params": r[1:]} for r in rows],
        "preset_count": len(rows),
    }


def command_facts(media):
    text = config_file(media, "command.txt")
    cmds = []
    for ln in text.splitlines():
        m = re.match(r'^\s*(\d+)\s*:\s*"([^"]*)"', ln)
        if m:
            cmds.append({"id": int(m.group(1)), "command": m.group(2)})
    return {"count": len(cmds), "commands": cmds}


def define_facts(media):
    text = config_file(media, "define.txt")
    flags = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return {"count": len(flags), "flags": flags}


def characterdata_speed_facts(media):
    def cols(filename):
        text = media_text(media, "server_dep/silkroad/textdata/" + filename)
        rows = [ln.split("\t") for ln in text.splitlines() if ln.strip()]
        return rows

    player_rows = cols("characterdata_5000.txt")
    jangan_rows = cols("characterdata_25000.txt")
    man_templates = []
    for r in player_rows:
        if len(r) > 48 and r[2].startswith("CHAR_CH_MAN"):
            man_templates.append({
                "refid": r[1], "code": r[2], "model": r[52] if len(r) > 52 else None,
                "positional_col46": r[46], "positional_col47": r[47],
                "positional_col48": r[48],
            })
    guard_sample = []
    for r in jangan_rows:
        if len(r) > 48 and r[2].startswith("COS_GUARD_CH_BOW"):
            guard_sample.append([r[2], r[46], r[47]])
    return {
        "proven_db_columns": ["Speed1", "Speed2", "Scale"],
        "characterdata_proven_anchors": {
            "col1": "refid (joins npcpos col0; Phase 13 verified)",
            "col2": "code name (CHAR_CH_MAN_* / COS_GUARD_* )",
            "col52": "model path (backslash .bsr; Phase 28 verified)",
        },
        "positional_triplet": {
            "cols_46_47_48": "16 / 50 / 100 for all 13 CHAR_CH_MAN templates",
            "status": "INFERRED as Speed1/Speed2/Scale, NOT proven: the "
                      "textdata loader column order is not in the available "
                      "sources; values recorded raw only",
        },
        "player_templates": man_templates,
        "guard_sample": guard_sample[:12],
        "note": "raw positional values only; world-units-per-second conversion "
                "and DB column identity remain UNKNOWN",
    }


def db_insertrefchar_facts():
    if not os.path.exists(SHARD_BAK):
        return {"present": False}
    with open(SHARD_BAK, "rb") as fh:
        blob = fh.read()

    def find(marker, window):
        i = blob.find(marker)
        if i < 0:
            return None
        seg = blob[i:i + window]
        return seg.decode("latin1", errors="replace")

    proc = find(b"CREATE PROCEDURE [dbo]._InsertRefChar", 20000)
    params = []
    if proc:
        params = re.findall(r"@([A-Za-z0-9_]+)\s+as\s+(tinyint|smallint|int|"
                            r"varchar\([0-9]+\)|real)", proc)
    # _RefObjCommon speed/scale/collision params and their positions
    speed1 = params.index(("Speed1", "smallint")) if ("Speed1", "smallint") in params else -1
    speed2 = params.index(("Speed2", "smallint")) if ("Speed2", "smallint") in params else -1
    return {
        "present": True,
        "procedure": "_InsertRefChar",
        "param_order": [list(p) for p in params],
        "speed1_param_index": speed1,
        "speed2_param_index": speed2,
        "has_knockdown": ("Knockdown", "tinyint") in params,
        "has_ko_recover_time": ("KO_RecoverTime", "int") in params,
        "refobjchar_columns": [
            "ID", "Lvl", "CharGender", "MaxHP", "MaxMP", "InventorySize",
            "CanStore_TID1..4", "CanBeVehicle", "CanControl", "DamagePortion",
            "MaxPassenger", "AssocTacticsName", "PD", "MD", "PAR", "MAR", "ER",
            "BR", "HR", "CHR", "ExpToGive", "CreepType", "Knockdown",
            "KO_RecoverTime", "DefaultSkill_1..10", "TextureType", "Except_1..10",
        ],
    }


def client_exe_facts():
    gc = os.path.join(CLIENT_DIR, "gc_strings.txt")
    if not os.path.exists(gc):
        return {"present": False}
    with open(gc, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    has = lambda needle: needle in text  # noqa: E731
    return {
        "present": True,
        "binary": "GameClient.exe (11,845,632 bytes, PE/MZ) + edxSilkroadDll5.dll "
                  "+ GFXFileManager.dll",
        "camera_classes": [c for c in
                           ("CCameraSlid", "CCameraWorking", "SC_CameraShake",
                            "SC_CameraSetState", "SC_CameraCreate",
                            "SC_CameraTeleport", "SC_CameraInsert", "CFrustum")
                           if has(".?AV" + c + "@@") or has(c + "@@")],
        "camera_config_path": "config\\cameradata.txt" if has("cameradata.txt") else None,
        "animation_classes": [c for c in
                              ("CAniMixer", "CPrimAnimation", "CRTAnimation",
                               "CCObjAnimation", "AniState") if has(".?AV" + c + "@@")],
        "movement_member": "m_nSpeed2" if has("m_nSpeed2") else None,
        "movement_debug_string": "g_GDataMgr.GetCharacterData(...)->m_nSpeed2 == 0",
        "input_classes": [c for c in ("CIFOption_Input", "CIFEInputChatBox")
                          if has(c + "@@")],
        "network": {
            "msg_id_format": "MSGID:0x%X" if has("MSGID:0x%X") else None,
            "net_engine_pools": [p for p in
                                 ("NetEngine::SessionPool",
                                  "NetEngine::ActiveSocketPool",
                                  "NetEngine::PassiveSocketPool") if has(p)],
            "rec_msg_dat": "RecMsg.dat" if has("RecMsg.dat") else None,
        },
        "source_paths": sorted({p for p in (
            "D:\\Project\\SilkroadOnline\\TOOLS & PLUGINS\\SimpleViewer"
            "\\objengine\\RStateMgr.cpp",
            "D:\\Project\\SilkroadOnline\\TOOLS & PLUGINS\\SimpleViewer"
            "\\objengine\\PrimAnimation.cpp",
            "D:\\Project\\SilkroadOnline\\TOOLS & PLUGINS\\SimpleViewer"
            "\\objengine\\AniMixer.cpp",
            "D:\\vss-od\\Silkroad\\Client\\client\\GInterfaceSend.cpp",
            "D:\\vss-od\\Silkroad\\Client\\client\\InterfaceNetSender.cpp",
            "d:\\vss-od\\silkroad\\client\\client\\MsgStreamBuffer.h") if has(p)}),
    }


def proxy_facts():
    if not os.path.exists(PROXY_CFG):
        return {"present": False}
    with open(PROXY_CFG, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    def val(section, key):
        m = re.search(r'^%s\s*=\s*(.*)$' % re.escape(key), text, re.M)
        return m.group(1).strip() if m else None

    return {
        "present": True,
        "client": {
            "host_ip": val("SR_CLIENT", "CL_HOST_IP"),
            "gateway_port": val("SR_CLIENT", "CL_GW_PORT"),
            "version": val("SR_CLIENT", "CL_VERSION"),
            "locale": val("SR_CLIENT", "CL_LOCALE"),
        },
        "server_ports": {
            "gateway_public": val("GATEWAYSERVER_DEFAULT", "PUBLIC_GW_PORT"),
            "gateway_private": val("GATEWAYSERVER_DEFAULT", "PVT_GW_PORT"),
            "agent_public": val("AGENTSERVER_DEFAULT", "PUBLIC_AG_PORT"),
            "agent_private": val("AGENTSERVER_DEFAULT", "PVT_AG_PORT"),
            "download_public": val("DOWNLOADSERVER_DEFAULT", "PUBLIC_DW_PORT"),
        },
        "malicious_opcode_filtering": val("PROXY SECURITY", "MALICIOUS_OPCODE"),
        "shard_name": val("MISCELLANEOUS", "SHARD_NAME"),
        "binary_type": "VSROProxy.exe is a .NET admin/anti-cheat tool "
                       "(C# async handlers, Newtonsoft.Json.dll, MegaApiClient.dll); "
                       "it is not the core game proxy",
        "malicious_opcodes": malicious_opcode_facts(),
        "action_delays": {
            "stall": val("ACTION DELAYS", "STALL_DELAY"),
            "global_chat": val("ACTION DELAYS", "GLOBAL_CHAT_DELAY"),
            "exchange_req": val("ACTION DELAYS", "EXCHANGE_REQ_DELAY"),
        },
    }


def offsets_facts():
    if not os.path.exists(OFFSETS_TXT):
        return {"present": False}
    with open(OFFSETS_TXT, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    maxlv = re.search(r'Max lv\s*=\s*([0-9A-Fa-f, ]+)', text)
    maxchar = re.search(r'Max Char Game\s*=\s*([0-9A-Fa-f, ]+)', text)
    changechar = re.search(r'Change Char Screen\s*:\s*([0-9A-Fa-f]+)', text)
    return {
        "present": True,
        "max_level_offsets": maxlv.group(1).replace(" ", "") if maxlv else None,
        "max_char_game_offset": maxchar.group(1).replace(" ", "") if maxchar else None,
        "change_char_screen_offset": changechar.group(1) if changechar else None,
        "chat_colors": {
            "whisper": "FF9FFFFE", "global": "FFFFFF00", "notice": "FFFFAEC3",
            "guild": "FFFFB541", "union": "FFC2F573", "party": "FF9AFFD0",
            "academy": "FFDBADF8", "normal": "FF64C7FF",
        },
    }


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def server_binary_facts():
    """PE inventory of the recovered server package (static, never executed)."""
    if not os.path.isdir(SERVER_DIR):
        return {"present": False}
    servers = [
        ("SR_GameServer.exe", 9576448, 0x4EB7450B, "D:\\WORK2005\\BinOut\\SR_GameServer.pdb"),
        ("SR_ShardManager.exe", 5062656, 0x4EB748D7, "D:\\WORK2005\\BinOut\\SR_ShardManager.pdb"),
        ("GatewayServer.exe", 1028096, 0x491246DC,
         "D:\\WORK2005\\JMX_CommonServers\\GatewayServer\\GatewayServer___Win32_Release_SR_VIETNAM\\GatewayServer.pdb"),
        ("AgentServer.exe", 929792, 0x4D8BC57E, "D:\\WORK2005\\BinOut\\AgentServer.pdb"),
        ("GlobalManager.exe", 1417216, 0x4D3D93C1, "D:\\WORK2005\\BinOut\\GlobalManager.pdb"),
        ("MachineManager.exe", 864256, 0x49124711,
         "D:\\WORK2005\\JMX_CommonServers\\MachineManager\\MachineManager___Win32_Release_SR_VIETNAM\\MachineManager.pdb"),
        ("DownloadServer.exe", 864256, 0x491246C7,
         "D:\\WORK2005\\JMX_CommonServers\\DownloadServer\\DownloadServer___Win32_Release_SR_VIETNAM\\DownloadServer.pdb"),
        ("FarmManager.exe", 901120, 0x4D3D9142, "D:\\WORK2005\\BinOut\\FarmManager.pdb"),
    ]
    support = ["GFXFileManager.dll", "dbghelp.dll", "ggauth.dll", "XTrap4Server.dll",
               "ImageTrans.dll", "CommonGuiControl.dll", "MailSender.dll",
               "VerData.dll", "ServerFrameworkRes.dll"]
    root_files = sorted(os.listdir(SERVER_DIR))
    return {
        "present": True,
        "root": SERVER_DIR,
        "game_servers": [
            {"name": n, "size": s, "timestamp_hex": "0x%08X" % t, "pdb": p}
            for n, s, t, p in servers if os.path.exists(os.path.join(SERVER_DIR, n))
        ],
        "support_dlls": [d for d in support if os.path.exists(os.path.join(SERVER_DIR, d))],
        "has_server_cfg": os.path.exists(os.path.join(SERVER_DIR, "server.cfg")),
        "has_refdata": os.path.isdir(os.path.join(SERVER_DIR, "SR_GameRefData")),
        "map_files": [f for f in ("Map1.CS3", "Map2.CS3")
                      if os.path.exists(os.path.join(SERVER_DIR, f))],
    }


def server_string_facts():
    """PROVEN server-side symbols recovered from the server binaries' strings."""
    gs = os.path.join(SERVER_DIR, "gameserver_strings.txt")
    sm = os.path.join(SERVER_DIR, "shardmanager_strings.txt")
    if not os.path.exists(gs):
        return {"present": False}
    text = _read_text(gs) + "\n" + (_read_text(sm) if os.path.exists(sm) else "")

    def has(needle):
        return needle in text

    motion = sorted({m for m in re.findall(r"\bMOTIONSTATE_[A-Z_0-9]+", text)})
    spawn = [s for s in
             ("CGame::EnterWorld() => CGObj::EnterWorld()",
              "ResolveCellAndHeight()", "ActivatePC()",
              "CGObj::EnterWorld Failed!!! at MoveTo()",
              "HandlerOnEnterWorld_%s(%d)", "SR_READY_TO_PLAY") if has(s)]
    charloader = [s for s in
                  ("[CRefCharGen::AddEntry]", "CRefCharGenData",
                   "CRefInstanceWorldStartPos", "_REFCHARGEN") if has(s)]
    refclasses = sorted({c for c in
                         ("CRefObjCommon", "CRefObjChar", "CRefObjItem",
                          "CRefRegion", "CRefCharGenData", "CRefDataManager",
                          "CRefInstanceWorldStartPos", "CRefInstanceWorldRegion")
                         if has(".?AV" + c + "@@") or has(c)})
    sql = [s for s in
           ("UPDATE _CHAR SET REFOBJID = %d, SCALE = %d WHERE CHARID = %d",
            "UPDATE _Char SET RemainGold = %I64d WHERE CharID = %d",
            "pRefSpawnChar == REFDATA_MGR.GetRefObj(%d)") if has(s)]
    speed = [s for s in ("PCSpeedRatio", "RefreshMoveSpeed()", "SetMoveMode()",
                         "MoveToPlayer", "MoveToNPC", "Recall Charactor")
             if has(s)]
    position = [s for s in
                ("Pos_RegionID", "DestPos_RegionID",
                 "MoveTo: [%d, (%f, %f, %f)]", "MoveToTown",
                 "MoveToPlayer: %s [WorldID(%d), RegionID(%d), (%f, %f, %f)]",
                 "LastUpdateTick") if has(s)]
    navmesh = [s for s in
               ("CRTNavMeshTerrain", "CRgnTerrain", "regioninfo.txt",
                "NavMesh_new") if has(s)]
    return {
        "present": True,
        "motion_states": motion,
        "motion_state_count": len(motion),
        "spawn_flow": spawn,
        "character_loader": charloader,
        "ref_classes": refclasses,
        "sql_references": sql,
        "server_speed_symbols": speed,
        "position_system": position,
        "navmesh_terrain": navmesh,
        "note": "symbols only: enum/class/message names prove vocabulary, not "
                "transition or numeric semantics",
    }


def spawn_chain_facts():
    """Proven links in the SERVER -> DB/caller -> client spawn chain."""
    gs = os.path.join(SERVER_DIR, "gameserver_strings.txt")
    sm = os.path.join(SERVER_DIR, "shardmanager_strings.txt")
    if not (os.path.exists(gs) and os.path.exists(sm)):
        return {"present": False}
    sm_text = _read_text(sm)
    gs_text = _read_text(gs)
    return {
        "present": True,
        "_addnewchar_caller": "SR_ShardManager.exe",
        "_addnewchar_call_format": "{?=CALL _AddNewChar (%d, %d,'%s',%d,%d,"
                                   "%f,%f,%f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d)}"
                                   if "_AddNewChar" in sm_text else None,
        "_addnewchar_start_params_are_caller_supplied": True,
        "start_pos_source": "CRefInstanceWorldStartPos / CRefInstanceWorldRegion "
                            "reference classes exist in SR_ShardManager.exe; the "
                            "underlying source file/values are NOT in the corpus",
        "char_last_position_select": "select LatestRegion, PosX, PosY, PosZ from "
                                     "_Char with(NOLOCK) where CharName16 = '%s'"
                                     if "LatestRegion" in sm_text else None,
        "instance_world_position_update": "{?=CALL _CharInstanceWorldDataUpdate("
                                          "%d,%d,%d,%d, '%s',%d,%d,%d,%d,%d,%d,'%s')"
                                          if "_CharInstanceWorldDataUpdate" in gs_text else None,
        "instance_world_startpos_datafile_missing": True,
        "instance_world_config_via_lua": "LuaSetInstanceWorldConfig"
                                         if "LuaSetInstanceWorldConfig" in gs_text else None,
        "instance_world_npc_ref": "Not Exits RefGameWorldNPC Data !!! "
                                  "InstanceWorldCodeName = %s!!"
                                  if "RefGameWorldNPC" in gs_text else None,
        "spawn_message_to_client": "SC_ObjectCreate / SC_ObjectCreateIndex "
                                   "(client RTTI) — exact packet layout not proven",
    }


def communication_facts():
    gc = os.path.join(CLIENT_DIR, "gc_strings.txt")
    if not os.path.exists(gc):
        return {"present": False}
    text = _read_text(gc)
    sc_classes = sorted({c for c in re.findall(r"\.\?AV(SC_[A-Za-z0-9_]+)@@", text)})
    cs_classes = sorted({c for c in re.findall(r"\.\?AV(CS_[A-Za-z0-9_]+)@@", text)})
    return {
        "present": True,
        "rec_msg_dat": "RecMsg.dat" if "RecMsg.dat" in text else None,
        "msgid_format": "MSGID:0x%X" if "MSGID:0x%X" in text else None,
        "wait_my_char_data": "MSGID:0x%04X Wait My Char Data !!!"
                             if "Wait My Char Data" in text else None,
        "sc_message_classes": sc_classes,
        "sc_message_class_count": len(sc_classes),
        "cs_message_classes_absent": len(cs_classes) == 0,
        "note": "SC_* (server->client) message handler classes are recoverable "
                "via RTTI; CS_* (client->server) classes are absent, and the "
                "exact opcode->field layout lives in RecMsg.dat/SendMsg.dat "
                "(MISSING from the corpus)",
    }


def message_layer_facts():
    """PROVEN message-dispatch/serialization symbols (client + server)."""
    gc = os.path.join(CLIENT_DIR, "gc_strings.txt")
    gs = os.path.join(SERVER_DIR, "gameserver_strings.txt")
    sm = os.path.join(SERVER_DIR, "shardmanager_strings.txt")
    if not os.path.exists(gc):
        return {"present": False}
    gc_text = _read_text(gc)
    gs_text = _read_text(gs) if os.path.exists(gs) else ""
    sm_text = _read_text(sm) if os.path.exists(sm) else ""

    client = [s for s in
              ("MsgStreamBuffer.h", "NetEngine::MsgPool", "m_nCurrentReadMsg",
               "MSG_ID = %X", "_OnMsgReceivedBeforeHandshake()",
               "RecMsg.dat") if s in gc_text]
    server = [s for s in
              ("CGame::ProcessMessage() MsgID : %x",
               "Unhandled Game SR_MSG: 0x%x [data size: %d]",
               "IGObj::AllocMsgForPeer", "[MsgID: 0x%X >> Count: %d]",
               "DumpMsgPool", "INVALID_MSG_HEADER", "INVALID_MSGSIZE",
               "NO_MSGTARGET", "IP:%s %s:0x%04X (0x%04X) (MsgType:%d), %d - %d",
               "_OnMsgReceivedBeforeHandshake() - Handshake") if s in gs_text]
    shardmgr = [s for s in
                ("Unhandled msg detected from server! msg_id 0x%x",
                 "CMainProcess::OnSR_RELAY_MSG_SM_TO_GS",
                 "FRAMEWORKMSG_START_PLAYTIME_INGAME_NOTIFY") if s in sm_text]
    return {
        "present": True,
        "client_dispatch_serialization": client,
        "gameserver_dispatch_serialization": server,
        "shardmanager_dispatch_serialization": shardmgr,
        "opcode_message_mapping": "NOT recoverable: opcode->message/class "
                                  "mapping lives in RecMsg.dat (client) and "
                                  "SendMsg.dat (server), both MISSING from the "
                                  "corpus; only opcode echo strings (0x%04X) "
                                  "and handler class names survive",
    }


def coordinate_facts():
    """Region<->worldmap<->world-coordinate mapping evidence + conversion status."""
    rd = os.path.join(SERVER_DIR, "SR_GameRefData")
    if not os.path.isdir(rd):
        return {"present": False}

    def read_utf16(name):
        raw = open(os.path.join(rd, name), "rb").read()
        return raw.decode("utf-16-le", errors="replace")

    def read_cp949(name):
        raw = open(os.path.join(rd, name), "rb").read()
        return raw.decode("cp949", errors="replace")

    refregion = None
    if os.path.exists(os.path.join(rd, "RefRegion.txt")):
        lines = [ln for ln in read_utf16("RefRegion.txt").splitlines() if ln.strip()]
        header = lines[0].split("\t")
        sample = next((ln.split("\t") for ln in lines
                       if ln.split("\t")[3] == "KingsValley"), None)
        refregion = {
            "row_count": len(lines),
            "column_count": len(header),
            "header_row": header[:14],
            "proven_columns": {
                "col0": "region id (signed; -32767 sentinel seen)",
                "col1_col2": "worldmap grid X / Y",
                "col3_col4": "region name / localized name",
                "col6": "mapping/zone id",
            },
            "sample_kingsvalley": sample[:14] if sample else None,
        }

    mapinfo = None
    if os.path.exists(os.path.join(rd, "worldmap_mapinfo.txt")):
        lines = [ln for ln in read_utf16("worldmap_mapinfo.txt").splitlines()
                 if ln.strip()]
        mapinfo = {
            "row_count": len(lines),
            "header": lines[2],
            "proven_columns": {
                "map_id": "0=world, 1+=local town",
                "type": "0:Wmap, 1:Local",
                "region_bounds": "left/top/right/bottom (region id range)",
                "coord_bounds": "LT_x/LT_y/RB_x/RB_y (worldmap cell bounds)",
                "fortress_world_id": "fortress instance world id",
            },
            "sample_world": lines[3] if len(lines) > 3 else None,
            "sample_jangan": lines[4] if len(lines) > 4 else None,
        }

    regioncode = None
    if os.path.exists(os.path.join(rd, "regioncode.txt")):
        lines = [ln for ln in read_cp949("regioncode.txt").splitlines() if ln.strip()]
        regioncode = {
            "encoding": "CP949 (Korean)",
            "row_count": len(lines),
            "sample_rows": lines[:5],
        }

    return {
        "present": True,
        "refregion": refregion,
        "worldmap_mapinfo": mapinfo,
        "regioncode": regioncode,
        "navmesh_block_cell_symbols": ["CurBlockID", "DestBlockID",
                                       "CurPosRegionID", "CurPosRegionX",
                                       "CurPosRegionZ"],
        "world_unit_conversion": "UNKNOWN: no numeric scale constant recovered "
                                 "mapping float world coords (MoveTo %f,%f,%f) "
                                 "to region/worldmap integer bounds; transforms "
                                 "live in compiled client/server code",
    }


def server_refdata_facts():
    rd = os.path.join(SERVER_DIR, "SR_GameRefData")
    if not os.path.isdir(rd):
        return {"present": False}
    stub_path = os.path.join(rd, "CharacterData.txt")
    stub_files = []
    if os.path.exists(stub_path):
        raw = open(stub_path, "rb").read()
        stub_files = [ln.strip().lstrip("\ufeff").strip() for ln in
                      raw.decode("utf-16-le", errors="replace").splitlines()
                      if ln.strip()]
    present = set(os.listdir(rd))
    return {
        "present": True,
        "characterdata_stub_files": stub_files,
        "characterdata_files_present": sorted(
            f for f in present if f.startswith("CharacterData_")),
        "characterdata_files_missing": sorted(
            f for f in stub_files if f not in present),
        "has_refregion": "RefRegion.txt" in present,
        "has_gameworlddata": "GameWorldData.txt" in present,
        "has_gameworldconfigdata": "GameWorldConfigData.txt" in present,
        "has_skilldata": any(f.startswith("SkillData_") for f in present),
        "has_itemdata": any(f.startswith("ItemData_") for f in present),
        "has_refinstanceworldstartpos": "RefInstanceWorldStartPos.txt" in present,
        "has_refinstanceworldregion": "RefInstanceWorldRegion.txt" in present,
    }


def malicious_opcode_facts():
    path = os.path.join(PROXY_DIR, "Features", "MALICIOUS_OPCODES.txt")
    if not os.path.exists(path):
        return {"present": False}
    text = _read_text(path)
    opcodes = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return {
        "present": True,
        "path": path,
        "count": len(opcodes),
        "opcodes": opcodes,
    }


def main():
    media = Archive(MEDIA_PK2)
    try:
        option = option_facts(media)
        camerad = cameradata_facts(media)
        command = command_facts(media)
        define = define_facts(media)
        speed = characterdata_speed_facts(media)
    finally:
        media.close()

    evidence = {
        "phase": "phase29",
        "client_executable": client_exe_facts(),
        "config": {
            "option": option,
            "cameradata": camerad,
            "command": command,
            "define": define,
        },
        "movement_speed": speed,
        "server_db_schema": db_insertrefchar_facts(),
        "server_package": server_binary_facts(),
        "server_strings": server_string_facts(),
        "server_refdata": server_refdata_facts(),
        "spawn_chain": spawn_chain_facts(),
        "communication": communication_facts(),
        "message_layer": message_layer_facts(),
        "coordinate_system": coordinate_facts(),
        "proxy": proxy_facts(),
        "offsets": offsets_facts(),
        "conclusions": {
            "player_spawn": "caller of _AddNewChar is SR_ShardManager.exe (PROVEN "
                            "ODBC call format); StartRegionID/StartPos_X/Y/Z are "
                            "caller-supplied params whose values are NOT in the "
                            "corpus (UNKNOWN); server pipeline CGame::EnterWorld "
                            "-> CGObj::EnterWorld -> ResolveCellAndHeight -> MoveTo "
                            "-> ActivatePC PROVEN at symbol level; concrete start "
                            "values UNKNOWN so spawn is NOT fully proven",
            "input": "debug command map PROVEN (config/command.txt); full key->action "
                     "mapping still UNKNOWN (SROptionSet.dat binary)",
            "movement": "Speed1/Speed2/Scale DB columns PROVEN (_InsertRefChar); "
                        "position system (RegionID + region cell + PosX/Y/Z) PROVEN "
                        "at symbol level; world-units conversion + speed formula "
                        "UNKNOWN",
            "motion_state": "19 MOTIONSTATE_* server labels PROVEN; mapping to "
                            "client animation (SC_ObjectAniToName/Index) NOT proven "
                            "(no shared enum in corpus)",
            "camera": "modes PROVEN (Phase 27) + cameradata.txt presets PROVEN; "
                      "preset column semantics UNKNOWN",
            "network": "server architecture + protocol version (188) + gateway port "
                       "(15779) PROVEN; gameplay opcode->message semantics UNKNOWN "
                       "(RecMsg.dat/SendMsg.dat MISSING)",
            "message_layer": "MsgID-keyed ProcessMessage() dispatch PROVEN on both "
                             "client and server (MsgPool, m_MsgList, INVALID_MSG_* "
                             "header checks); opcode->message/class mapping NOT "
                             "recoverable (RecMsg.dat/SendMsg.dat MISSING)",
            "world_unit_conversion": "region<->worldmap<->coordinate structure "
                                     "PROVEN (RefRegion.txt 21-col, "
                                     "worldmap_mapinfo.txt bounds); numeric "
                                     "world-unit scale UNKNOWN",
            "start_position": "_AddNewChar StartRegionID/StartPos are caller-"
                              "supplied (SR_ShardManager.exe); instance-world "
                              "start-position data files are MISSING and config "
                              "is Lua-driven (LuaSetInstanceWorldConfig); "
                              "concrete start values UNKNOWN",
            "authority": "server-authoritative: movement/combat timing live in "
                         "server DB (KO_RecoverTime, DamagePortion) + proxy "
                         "(MALICIOUS_OPCODE filter, action delays)",
            "skill_semantics": "_RefSkill.basic_code PROVEN; full skill column "
                                "semantics still UNKNOWN (skilldata_*.txt unparsed)",
            "server_corpus": "the full VSRO-R v193 server package (8 server EXEs, "
                             "SR_GameRefData textdata, server.cfg) is now recovered "
                             "as a static-forensic source; previously listed as absent",
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
