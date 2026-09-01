#!/usr/bin/env python3
"""Assemble consolidated subsystem evidence + reference graph.

Combines:
  - Lua quest/event census (identifier + API + mission-type counts)
  - textdata table schemas (TEXTDATA_SCHEMAS.json)
  - binary/text format verification (FORMAT_VERIFICATION.json)
into a single deterministic SUBSYSTEM_EVIDENCE.json that maps each subsystem
to its concrete evidence sources (file paths, tables, functions, counts).

Evidence is factual (observed identifiers, table names, column counts, magic
bytes); subsystem assignments are structural/functional, never invented.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import sro_paths  # noqa: E402

LUA_DIR = os.path.join(sro_paths.resolve_extract_dir(), "server", "Script", "VIETNAM_LUA")
REPO = BASE


def lua_census():
    files = []
    for root, _dirs, names in os.walk(LUA_DIR):
        for n in names:
            if n.endswith(".lua"):
                files.append(os.path.join(root, n))
    if not files:
        return {}

    def uniq(pattern):
        ids = set()
        for fp in files:
            with open(fp, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
            ids.update(re.findall(pattern, text))
        return ids

    api = {}
    for fp in files:
        with open(fp, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
        for m in re.findall(r"\bLua[A-Za-z0-9_]+\b", text):
            api[m] = api.get(m, 0) + 1

    return {
        "files": len(files),
        "bytes": sum(os.path.getsize(f) for f in files),
        "unique_mobs": len(uniq(r"\bMOB_[A-Z0-9_]+\b")),
        "unique_items": len(uniq(r"\bITEM_[A-Z0-9_]+\b")),
        "unique_npcs": len(uniq(r"\bNPC_[A-Z0-9_]+\b")),
        "unique_npc_names": len(uniq(r"\bSN_NPC_[A-Z0-9_]+\b")),
        "mission_types": sorted(uniq(r"\bMISSION_TYPE_[A-Z0-9_]+\b")),
        "lua_api_functions": dict(sorted(api.items(), key=lambda kv: -kv[1])),
    }


def load(name):
    p = os.path.join(REPO, name)
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def main():
    census = lua_census()
    schemas = load("TEXTDATA_SCHEMAS.json")
    formats = load("FORMAT_VERIFICATION.json")

    def tables(*keys):
        out = []
        for k in keys:
            for t, meta in schemas.items():
                if k in t:
                    out.append({
                        "table": t,
                        "rows": meta.get("rows", 0),
                        "columns": meta.get("columns", []),
                        "encoding": meta.get("encoding"),
                    })
        return out

    subsystems = {
        "item": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("itemdata_", "itemeffect", "item_grouping", "magicoption", "refsetitemgroup", "refpackageitem", "refscrapofpackageitem", "refpricepolicyofitem")]},
                {"kind": "lua", "note": "quest scripts reference items", "unique_item_refs": census.get("unique_items")},
            ],
        },
        "character_monster_npc": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("characterdata_", "npcchat", "npcpos", "specialnpcdata", "charactervisualchange", "textdata_object")]},
                {"kind": "lua", "unique_mobs": census.get("unique_mobs"), "unique_npcs": census.get("unique_npcs"), "unique_npc_names": census.get("unique_npc_names")},
            ],
        },
        "skill": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("skilldata", "skilleffect", "skillgroup", "skillmasterydata", "learnableskill", "erasableskill", "learnablemastery", "erasablemastery")]},
            ],
        },
        "quest": {
            "evidence": [
                {"kind": "lua", "files": census.get("files"), "mission_types": census.get("mission_types")},
                {"kind": "textdata", "tables": [t["table"] for t in tables("questdata", "questcontentsdata", "refquestrewarditems", "refqusetreward", "textquest")]},
            ],
        },
        "event": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("eventdata", "eventguidedata", "eventzonedata", "textevent", "refeventreward", "refservereventid")]},
            ],
        },
        "shop_mall": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("shopdata", "shopitemdata", "shoptabdata", "shopgroupdata", "refshop", "refshopgoods", "refshopgroup", "refshoptab", "refshoptabgroup", "refmappingshop", "mallitemmenulistdata")]},
            ],
        },
        "teleport": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("teleportdata", "teleportlink", "teleportbuilding", "refoptionalteleport")]},
            ],
        },
        "region_zone_worldmap": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("regioncode", "textzonename", "worldmap_instanceinfo", "worldmap_localinfo", "worldmap_mapinfo", "worldmapguidedata")]},
                {"kind": "textfile", "files": ["/RegionInfo.txt", "/dungeon/Dungeoninfo.txt", "/shader/regioninfo.txt", "/camera_path.txt", "/layerobjdef.txt"], "note": "verified readable text (targeted pk2_mate extraction)"},
            ],
        },
        "siege_fortress": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("siegefortress", "siegestructupgradedata", "refsiegedungeon", "refsiegeblessbuff", "gameworldconfigdata")]},
            ],
        },
        "alchemy_magic_option": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("refalchemy_mk_", "magicoption", "magicoptionassign", "refmagicopt")]},
            ],
        },
        "gacha_collection": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("gachaitemset", "refgachatree", "collectionbook_")]},
            ],
        },
        "effect_sound": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("effectsound", "effectenvsnd", "atstructeffect")]},
                {"kind": "format", "formats": ["jmx-effect-efp"]},
            ],
        },
        "ui_text": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("textuisystem", "textdata_", "texthelp", "messagetipdata", "texttooltipdata")]},
            ],
        },
        "level_job_trade": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("leveldata", "levelgold", "hwanleveldata", "tradeconflict_", "fmncategorytreedata")]},
            ],
        },
        "abuse_filter": {
            "evidence": [
                {"kind": "textdata", "tables": [t["table"] for t in tables("abusefilter")]},
            ],
        },
    }

    # merge SQL-derived subsystems (CLIENT_SQL_EVIDENCE.json curated map)
    client_sql = load("CLIENT_SQL_EVIDENCE.json")
    sql_subs = client_sql.get("sql_backups", {}).get("curated_subsystems", {})
    for sub, tbls in sql_subs.items():
        key = sub.replace("_", "-")
        subsystems[key] = {
            "evidence": [
                {"kind": "database-table", "database": "SRO_VT_SHARD", "tables": tbls},
            ],
        }

    # format families (magic-byte evidence)
    format_families = {}
    for k, v in formats.items():
        fam = v.get("format")
        if fam and fam not in ("unknown-magic", "EXTRACT_FAILED", "NOT_EXTRACTED", "binary"):
            format_families.setdefault(fam, []).append(v.get("ext"))

    graph = {
        "lua_census": census,
        "textdata_table_count": len(schemas),
        "format_verification_count": len(formats),
        "format_families": {k: sorted(set(v)) for k, v in sorted(format_families.items())},
        "subsystems": subsystems,
    }

    out = os.path.join(REPO, "SUBSYSTEM_EVIDENCE.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("subsystems     :", len(subsystems))
    print("textdata tables:", len(schemas))
    print("format records :", len(formats))
    print("lua files      :", census.get("files"))
    print("format families:", len(format_families))
    print("wrote", out)


if __name__ == "__main__":
    main()
