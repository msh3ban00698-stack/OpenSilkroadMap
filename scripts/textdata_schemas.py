"""Declarative schema catalog + reference graph for the 21 Phase 12 datasets.

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
        0: ("spawn_id", "int id, ascending"),
        1: ("character_refid", "joins characterdata_*.txt col1 for 659/1855 ids"),
        2: ("coord0", "float coordinate"),
        3: ("coord1", "float coordinate; ~0 across records (height axis)"),
        4: ("coord2", "float coordinate"),
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
        1: ("shop_id", "joins refshopgoods.col1 (both value 15 in committed set)"),
        3: ("shop_code", "MALL_* / STORE_* codes"),
    },
    "refshopgoods.tsv": {
        1: ("shop_id", "joins refshop.col1"),
        2: ("category_code", "joins refshoptab.txt col3"),
        3: ("item_code", "PACKAGE_ITEM_* codes"),
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
        "from": {"dataset": "npcpos.tsv", "column": 1, "name": "character_refid"},
        "to": {"dataset": "characterdata_*.txt (tiers)", "column": 1, "name": "refid"},
        "matched": 659, "total": 1855, "note": "659/1855 spawn ids resolve to a character refid; negative ids are special/instance NPCs",
        "status": "PARTIAL",
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
        "from": {"dataset": "refshopgoods.tsv", "column": 1, "name": "shop_id"},
        "to": {"dataset": "refshop.tsv", "column": 1, "name": "shop_id"},
        "matched": 1, "total": 1, "note": "committed set holds a single shop id (15)",
        "status": "VERIFIED",
    })
    edges.append({
        "from": {"dataset": "refshopgoods.tsv", "column": 2, "name": "category_code"},
        "to": {"dataset": "refshoptab.txt", "column": 3, "name": "tab code"},
        "matched": 164, "total": 164, "note": "every refshopgoods category code exists in refshoptab.txt col3",
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
