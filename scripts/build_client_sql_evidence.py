#!/usr/bin/env python3
"""Consolidate client .7z + SQL .Bak forensic evidence (Phase 30/31).

Produces CLIENT_SQL_EVIDENCE.json with:
  - client archive extraction facts (binaries, RD bitmaps, settings, silk cfg)
  - authoritative RecMsg.dat / SendMsg.dat determination
  - SQL backup schema (candidate table names per database) + curated subsystems

Read-only with respect to archives, .7z, and .Bak files.
"""
from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import sro_paths  # noqa: E402

REPO = BASE
CLIENT_DIR = sro_paths.resolve_client_extract_dir()
BAK_DIR = sro_paths.resolve_db_dir()

# curated subsystems discovered/confirmed from SHARD DB table names
SQL_SUBSYSTEM_TABLES = {
    "training_camp_mentor": ["_TrainingCamp", "_TrainingCampMember", "_TrainingCampHonorRank", "_TrainingCampBuffStatus", "_TrainingCampSubMentorHonorPoint"],
    "trijob": ["_CharTrijob", "_OldTrijob", "_TrijobRanking4WEB", "_TrijobRewards"],
    "consignment_trade": ["_ConsignmentTrade_Progress_RuntimeLog", "_UpdateProcessState_ConsignmentTrade_CONSI", "_UpdateProcessState_ConsignmentTrade_CONSIGNMENT_INFO", "_UpdateProcessState_ConsignmentTrade_CONSIGNMENT_STATE_ONLY", "_UpdateProcessState_ConsignmentTrade_PATH_PATROL_INFO", "_Insert_ConsignmentTrade_RewardCharLog", "_Delete_ConsignmentTrade_Invest_Rewareded"],
    "flea_market": ["_FleaMarketNetwork"],
    "robber_trader": ["_RobberActivity", "_TraderContribution", "_RefRanking_RobberActivity", "_RefRanking_RobberContribution", "_Tab_RefRanking_TraderContribution"],
    "siege_fortress": ["_SiegeFortress", "_SiegeFortressBattleRecord", "_SiegeFortressRequest", "_SiegeFortressStoneState", "_SiegeFortressObject", "_SiegeFortressStruct", "_RefSiegeFortress", "_RefSiegeFortressBattleRank", "_RefSiegeFortressGuard", "_RefSiegeFortressItemForge", "_RefSiegeStructUpgrade"],
    "guild_war": ["_GuildWar", "_AlliedClans", "_Guild__AlliedClans", "_GuildChest", "_GuildMember"],
    "friend": ["_Friend", "_FriendGroup"],
    "instance_world": ["_RefInstance_World_Region", "_RefInstance_World_Start_Pos", "_RefGame_World", "_CharInstanceWorldData", "_FlagWorld_EventParticipants"],
    "avatar_cos": ["_StaticAvatar", "_InventoryForAvatar", "_CharCOS", "_InvCOS"],
    "chest_storage": ["_Chest", "_ChestInfo", "_GuildChest", "_CharStorage"],
    "item_pool_market": ["_ItemPool", "_ItemQuotation", "_LatestItemSerial"],
    "timed_job_pet": ["_TimedJob", "_TimedJobForPet"],
    "silk_consumption": ["_ConsumeSilkByGameServerD"],
    "drop_system": ["_RefDropClassSel_Alchemy_Tablet", "_RefDropClassSel_Ammo", "_RefDropClassSel_Cure", "_RefDropClassSel_Equip", "_RefDropClassSel_RareEquip", "_RefDropClassSel_Recover", "_RefDropClassSel_Reinforce", "_RefDropClassSel_Scroll", "_RefDropGold", "_RefDropItemAssign", "_RefDropOptLvlSel", "_RefCustomizingReservedItemDropForMonster"],
    "trade_conflict": ["_CheckTradeConflict_UnregisterUserJob", "_QueryStatics_TradeConflictJobStatus"],
}


def list_files(root):
    out = []
    for dp, _d, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            out.append({"path": p[len(root):].lstrip("/"), "size": os.path.getsize(p)})
    return out


def main():
    client_files = list_files(CLIENT_DIR)
    sql_schema = {}
    if os.path.isfile(os.path.join(REPO, "SQL_DATABASE_SCHEMA.json")):
        with open(os.path.join(REPO, "SQL_DATABASE_SCHEMA.json"), encoding="utf-8") as fh:
            sql_schema = json.load(fh)

    evidence = {
        "client_archive": {
            "archive": "vsro_pkg/VSRO-R Client/VSRO-R Client.7z",
            "extracted_files": len(client_files),
            "extracted_bytes": sum(f["size"] for f in client_files),
            "skipped": "Media.pk2 (823,066,624 bytes) — duplicate of already-extracted pk2raw/Media.pk2",
            "categories": {
                "binaries": sorted([f["path"] for f in client_files if f["path"].endswith((".exe", ".dll"))]),
                "rd_bitmaps": len([f for f in client_files if f["path"].startswith("RD/")]),
                "settings": sorted([f["path"] for f in client_files if f["path"].startswith("Setting/") or f["path"] in ("silkcfg.dat", "Silkload.dat")]),
            },
            "rd_format": "16x16 8bpp Windows BMP (BM magic) — region minimap icons, not region data",
            "gameclient_recmsg_ref": {
                "file": "GameClient.exe",
                "offset": 10428884,
                "context": "Game.cpp startup, loaded via CreateFile(%s); 'File Not Find.' on absence",
                "build_path_leak": "D:\\vss-od\\Silkroad\\Client\\client\\Game.cpp",
                "debug_fmt": "MSGID:0x%X,R(%d),W(%d),T(%d)",
            },
        },
        "recmsg_sendmsg": {
            "RecMsg.dat": {
                "verdict": "MISSING",
                "evidence": "string 'RecMsg.dat' in GameClient.exe (client-side receive-message table)",
                "reconstructable": "no authoritative source contains it; would require reverse-engineering client opcode dispatch",
            },
            "SendMsg.dat": {
                "verdict": "NOT_AUTHORITATIVE",
                "evidence": "no binary references 'SendMsg.dat'; only 'SendMsg' appears as C++ method names in SR_GameServer.exe (SendMsgToPeer, SendMsgToAllGameWorldUser, ...)",
                "reclassified_from": "MISSING (prior assumption of client+server dispatch reference was incorrect)",
            },
        },
        "sql_backups": {
            "dir": BAK_DIR,
            "databases": {
                k: {"file": v.get("file"), "size": v.get("size"), "candidate_tables": len(v.get("tables", []))}
                for k, v in sql_schema.items()
            },
            "curated_subsystems": SQL_SUBSYSTEM_TABLES,
            "note": "candidate table names from read-only strings scan; exact names may carry 1-3 trailing metadata bytes",
        },
    }

    out = os.path.join(REPO, "CLIENT_SQL_EVIDENCE.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("client files:", len(client_files), "bytes:", evidence["client_archive"]["extracted_bytes"])
    print("sql databases:", {k: v["candidate_tables"] for k, v in evidence["sql_backups"]["databases"].items()})
    print("wrote", out)


if __name__ == "__main__":
    main()
