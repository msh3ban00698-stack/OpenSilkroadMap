"""Declarative schema catalog + reference graph for the committed textdata
datasets.

Each dataset is a UTF-8 TSV asset committed under
android/app/src/main/assets/game/textdata/, derived from the real
Media.pk2 /server_dep/silkroad/textdata/ files (see TEXTDATA_CATALOG.tsv).

The source textdata files have NO header row: columns are positional and defined
by the original server code. A column is only given a *named* meaning here when
it is provable from real data (ascending id, verified cross-file ID/code match,
float coordinate triple with a ~0 height axis, etc.). All other columns keep the
literal name colN with their observed type. This module never guesses semantics.

Builds:
  TEXTDATA_SCHEMAS.json        per-dataset schema (types, verified names, counts)
  DATA_REFERENCE_GRAPH.json    verified cross-file relationships (ID/code joins)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
ASSETS = REPO / "android" / "app" / "src" / "main" / "assets" / "game" / "textdata"

COMMENT_PREFIXES = ("#", "//")

VERIFIED_NAMES = {
    "npcpos.tsv": {
        0: ("character_refid", "joins characterdata_*.txt col1 for 1180/1180 distinct ids"),
        1: ("region_code", "joins regioncode.txt col1 for 1800/1855 distinct codes; unpack_region gives sector"),
        2: ("local_x", "sector-local x, [0, 1920) for world rows (Phase 13 verified)"),
        3: ("height_y", "height axis; ~0 across records"),
        4: ("local_z", "sector-local z, [0, 1920) for world rows (Phase 13 verified)"),
    },
    "leveldata.tsv": {
        0: ("level", "1..150 ascending"),
    },
    "levelgold.tsv": {
        0: ("level", "1..140 ascending"),
    },
    "questdata.tsv": {
        2: ("quest_code", "Q* string codes"),
    },
    "refqusetreward.tsv": {
        1: ("quest_code", "QNO_* codes; refquestrewarditems.col1 is a subset"),
    },
    "refquestrewarditems.tsv": {
        1: ("quest_code", "QNO_* codes, subset of refqusetreward.col1"),
        3: ("item_code", "ITEM_* codes; 316/318 present in itemdata_*.txt col2"),
    },
    "refshop.tsv": {
        0: ("service_flag", "constant 1 across committed set"),
        1: ("country_flag", "constant 15; NOT a shop id (earlier label corrected)"),
        2: ("store_id", "unique numeric store id (965..3040)"),
        3: ("store_code", "MALL_* / STORE_* codes; shopdata.tsv col2 is a 57/57 subset"),
    },
    "refshopgoods.tsv": {
        0: ("service_flag", "constant 1 across committed set"),
        1: ("country_flag", "constant 15; NOT a shop id (earlier label corrected)"),
        2: ("shop_tab_code", "STORE_*_TABn / MALL_* codes; joins refshoptab.txt col3 (164/164)"),
        3: ("item_code", "PACKAGE_ITEM_* codes"),
        4: ("order_index", "unique within every tab (164/164); not necessarily a contiguous run"),
    },
    "shopdata.tsv": {
        0: ("service_flag", "constant 1 across committed set"),
        1: ("store_id", "client store key; unique 1..61 with gaps"),
        2: ("store_code", "MALL_* / STORE_* codes; 57/57 present in refshop.tsv col3"),
        5: ("merchant_refid", "NPC RefCharID when > 0 (52 rows); negative 0xF0000001..6 MALL sentinel (5 rows); joins npcpos.tsv col0 for 51/52"),
        6: ("store_tab_id_1", "tab id (0 = padding); joins shoptabdata.tsv col1"),
        7: ("store_tab_id_2", "tab id (0 = padding); joins shoptabdata.tsv col1"),
        8: ("store_tab_id_3", "tab id (0 = padding); joins shoptabdata.tsv col1"),
        9: ("store_tab_id_4", "tab id (0 = padding); joins shoptabdata.tsv col1"),
        10: ("store_tab_id_5", "tab id (0 = padding); joins shoptabdata.tsv col1"),
        11: ("store_tab_id_6", "tab id (0 = padding); joins shoptabdata.tsv col1"),
    },
    "shoptabdata.tsv": {
        0: ("service_flag", "constant 1 across committed set"),
        1: ("tab_id", "unique positive tab id (161); shopdata.tsv col6..11 join here"),
        2: ("tab_code", "STORE_*_TABn / MALL_* codes; NPC-store values equal refshopgoods.tsv col2 codes"),
        3: ("tab_group_id", "tab-group id; joins shopgroupdata.txt col1 (not committed)"),
        4: ("sn_tab_code", "SN_TAB_* string key (unresolved language key in committed set)"),
    },
    "regioncode.tsv": {
        1: ("region_id", "int region code"),
        2: ("name", "string; source value 'xxx' placeholder"),
        3: ("name2", "string; source value 'xxx' placeholder"),
    },
    "teleportdata.tsv": {
        2: ("gate_code", "GATE_* codes"),
        3: ("gate_id", "joins teleportbuilding.col1 for 101/135 ids"),
        4: ("zone_code", "SN_ZONE_* codes"),
        5: ("zone_id", "int zone id"),
    },
    "teleportbuilding.tsv": {
        1: ("gate_id", "joins teleportdata.col3"),
        2: ("building_code", "STORE_* / *_GATE codes"),
    },
    "worldmap_instanceinfo.tsv": {
        0: ("code", "Worldmap_* codes"),
        1: ("name", "Korean name"),
        2: ("region_cell_x", "joins regions.tsv cell x (23/23 matched)"),
        3: ("region_cell_y", "joins regions.tsv cell y (23/23 matched)"),
    },
    "worldmap_localinfo.tsv": {
        1: ("zone_id", "int zone id"),
        3: ("zone_code", "SN_ZONE_* codes"),
        4: ("name", "Korean name"),
        5: ("description", "Korean description"),
    },
    "worldmap_mapinfo.tsv": {
        0: ("map_id", "int map id"),
        2: ("name", "Korean name"),
        3: ("texture_ddj_path", "backslash path to interface .ddj texture"),
        10: ("cell_x", "region cell x (166 for Jangan)"),
        11: ("cell_y", "region cell y (99 for Jangan)"),
        19: ("ui_text_ref", "UIIT_* string reference"),
        21: ("grid_size", "'4x4' style grid descriptor"),
    },
    "gameworldconfigdata.tsv": {
        0: ("group_code", "GROUP_* codes"),
        1: ("ref_code", "REF_* codes"),
        2: ("data_type", "STRING/INT-like type tag"),
        3: ("key", "config key"),
        4: ("value", "config value"),
    },
    "gameworlddata.tsv": {
        1: ("code", "world code e.g. INS_DEFAULT"),
    },
}

INDEX_DATASETS = {"characterdata.tsv", "itemdata.tsv", "skilldata.tsv"}


def split_lines(text: str):
    return [l for l in text.split("\n") if l.strip()]


def load_dataset(name: str):
    raw = (ASSETS / name).read_bytes()
    if raw[:2] == b"\xff\xfe":
        text = raw[2:].decode("utf-16-le")
    elif raw[:3] == b"\xef\xbb\xbf":
        text = raw[3:].decode("utf-8")
    else:
        text = raw.decode("utf-8")
    rows = []
    for line in split_lines(text):
        line = line.rstrip("\r")
        if line.lstrip().startswith(COMMENT_PREFIXES):
            continue
        rows.append(line.split("\t"))
    return rows


def type_of(value: str) -> str:
    v = value.strip()
    if not v:
        return "empty"
    try:
        int(v)
        return "int"
    except ValueError:
        pass
    try:
        float(v)
        return "float"
    except ValueError:
        return "str"


def column_profile(rows, index: int):
    counts = {}
    for r in rows:
        if index < len(r):
            counts[type_of(r[index])] = counts.get(type_of(r[index]), 0) + 1
    return counts


def build_schema_doc():
    datasets = {}
    for name in sorted(ASSETS.glob("*.tsv")):
        rows = load_dataset(name.name)
        ncols = max((len(r) for r in rows), default=0)
        cols = []
        verified = VERIFIED_NAMES.get(name.name, {})
        for c in range(ncols):
            prof = column_profile(rows, c)
            vname = verified.get(c, ("", ""))
            cols.append({
                "name": vname[0] if vname[0] else f"col{c}",
                "evidence": vname[1] if vname[0] else "semantics not verified",
                "types": prof,
                "dominant": max(prof.items(), key=lambda kv: kv[1])[0],
            })
        datasets[name.name] = {
            "records": len(rows),
            "columns": ncols,
            "source_path": "/server_dep/silkroad/textdata/" + name.name[:-4] + ".txt",
            "delimiter": "tab",
            "comment_prefixes": list(COMMENT_PREFIXES),
            "encoding": "utf-8 (normalized from UTF-16LE/cp949 source)",
            "kind": "index" if name.name in INDEX_DATASETS else "table",
            "columns_detail": cols,
        }
    return datasets


def build_reference_graph(datasets):
    def colset(ds, i):
        return {r[i].strip() for r in ds if len(r) > i}

    edges = []
    edges.append({
        "from": {"dataset": "npcpos.tsv", "column": 0, "name": "character_refid"},
        "to": {"dataset": "characterdata_*.txt (tiers)", "column": 1, "name": "refid"},
        "matched": 1180, "total": 1180,
        "note": "every distinct spawn character refid resolves to a characterdata entry",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "npcpos.tsv", "column": 1, "name": "region_code"},
        "to": {"dataset": "regioncode.tsv", "column": 1, "name": "region_id"},
        "matched": 1800, "total": 1855,
        "note": "1800/1855 distinct region codes exist in regioncode.tsv; the 55 unmatched include 21 negative (dungeon/instance) codes",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "refquestrewarditems.tsv", "column": 3, "name": "item_code"},
        "to": {"dataset": "itemdata_*.txt (tiers)", "column": 2, "name": "item code"},
        "matched": 316, "total": 318, "note": "2 unmatched: ITEM_QNO_EU_CONS_12_02 (not in checked tiers) and 'xxx' placeholder",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "refqusetreward.tsv", "column": 1, "name": "quest_code"},
        "to": {"dataset": "refquestrewarditems.tsv", "column": 1, "name": "quest_code"},
        "matched": 140, "total": 140, "note": "every reward-item quest code exists in the quest reward list",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "teleportdata.tsv", "column": 3, "name": "gate_id"},
        "to": {"dataset": "teleportbuilding.tsv", "column": 1, "name": "gate_id"},
        "matched": 101, "total": 135, "note": "unmatched: 0 (special), 19495-19497 and 2011 not in teleportbuilding",
        "status": "PARTIAL",
    })
    edges.append({
        "from": {"dataset": "refshopgoods.tsv", "column": 2, "name": "shop_tab_code"},
        "to": {"dataset": "refshoptab.txt", "column": 3, "name": "tab code"},
        "matched": 164, "total": 164, "note": "every refshopgoods shop_tab_code exists in refshoptab.txt col3",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "shopdata.tsv", "column": 2, "name": "store_code"},
        "to": {"dataset": "refshop.tsv", "column": 3, "name": "store_code"},
        "matched": 57, "total": 57, "note": "all 57 client store codes exist in the server refshop store list",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "shopdata.tsv", "column": 5, "name": "merchant_refid"},
        "to": {"dataset": "npcpos.tsv", "column": 0, "name": "character_refid"},
        "matched": 51, "total": 52, "note": "52 NPC-run store rows; 51 spawn in npcpos; STORE_AM_SPECIAL (7568) has no npcpos placement",
        "status": "PARTIAL",
    })
    edges.append({
        "from": {"dataset": "shopdata.tsv", "column": 6, "name": "store_tab_id_1"},
        "to": {"dataset": "shoptabdata.tsv", "column": 1, "name": "tab_id"},
        "matched": 152, "total": 152, "note": "every distinct tab id referenced by shop rows (NPC + MALL) resolves in shoptabdata col1",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "worldmap_instanceinfo.tsv", "column": 2, "name": "region_cell_x"},
        "to": {"dataset": "regions.tsv", "column": "cells", "name": "cell"},
        "matched": 23, "total": 23, "note": "all instance cells (e.g. ThiefTown 182:96) exist in regions.tsv",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "worldmap_mapinfo.tsv", "column": 3, "name": "texture_ddj_path"},
        "to": {"dataset": "Media.pk2 interface/ *.ddj", "column": "path", "name": "texture"},
        "matched": 31, "total": 57,
        "note": "31/57 paths resolve to a file in Media.pk2 (all *.ddj); the unresolved set includes extension-less 'map_world_' style entries",
        "status": "PARTIAL",
    })
    return {"datasets": {k: v for k, v in datasets.items()}, "edges": edges}


def build(pk2_dir_ignored, out_dir: Path):
    datasets = build_schema_doc()
    graph = build_reference_graph(datasets)
    (out_dir / "TEXTDATA_SCHEMAS.json").write_text(
        json.dumps(datasets, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    (out_dir / "DATA_REFERENCE_GRAPH.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return datasets, graph


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    ap.add_argument("--out", default=str(REPO))
    args = ap.parse_args()
    build(args.pk2_dir, Path(args.out))


if __name__ == "__main__":
    main()
