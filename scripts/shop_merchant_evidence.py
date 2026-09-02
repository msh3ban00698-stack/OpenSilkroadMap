#!/usr/bin/env python3
"""Deterministic shop-merchant binding evidence (Phase 30).

Reads only committed Android assets under
android/app/src/main/assets/game/textdata/ and derives the merchant-to-store /
store-to-tab / tab-to-stock joins proven for this milestone:

  shopdata.tsv (client) col5 merchant_refid (>0) + col6.. store_tab_ids
      -> shoptabdata.tsv (client) col1 tab_id -> col2 tab_code
      -> refshopgoods.tsv (server) col2 shop_tab_code -> col3 item_code
         with col4 order_index (unique per tab)
  refshop.tsv (server) col3 store_code -> col2 store_id

Emits scripts/testdata/formats/shop_merchant_index.json with the derived
merchant index plus exact anchor rows and cross-file coverage counters. This
module never guesses semantics: prices, stock quantities, item names and NPC
behavior are NOT derived here (see the JSON's provenance/limitations).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
ASSETS = REPO / "android" / "app" / "src" / "main" / "assets" / "game" / "textdata"
OUT = SCRIPTS / "testdata" / "formats" / "shop_merchant_index.json"

NPC_PREFIX = "PACKAGE_ITEM_"


def load_rows(name: str):
    rows = []
    with open(ASSETS / name, encoding="utf-8", newline="") as fh:
        for line in csv.reader(fh, delimiter="\t"):
            if not line or line[0].startswith("//") or line[0].startswith("#"):
                continue
            rows.append(line)
    return rows


def _int(row, i):
    v = row[i].strip() if i < len(row) else ""
    return int(v) if v else 0


def _str(row, i):
    return row[i] if i < len(row) else ""


def tab_ids_of(row):
    return [_int(row, c) for c in range(6, 12) if c < len(row) and _int(row, c) != 0]


def build():
    shop = load_rows("shopdata.tsv")
    tabs = load_rows("shoptabdata.tsv")
    refshop = load_rows("refshop.tsv")
    goods = load_rows("refshopgoods.tsv")
    npc = load_rows("npcpos.tsv")

    tab_id_to = {_int(t, 1): {"code": _str(t, 2), "group": _int(t, 3), "sn": _str(t, 4)}
                 for t in tabs}
    store_code_to_id = {_str(r, 3): _int(r, 2) for r in refshop if len(r) > 3}
    refshop_codes = set(store_code_to_id)

    # stock grouped by shop_tab_code, each row keeps its order_index (col4).
    stock_by_tab = {}
    for r in goods:
        code = _str(r, 3)
        if code and _str(r, 2):
            stock_by_tab.setdefault(_str(r, 2), []).append(
                {"item_code": code, "order": _int(r, 4)})

    # col4 order_index is unique within every tab; record the statistic.
    order_unique = sum(1 for v in stock_by_tab.values()
                       if len({s["order"] for s in v}) == len(v))

    store_rows = [r for r in shop if len(r) > 5]
    npc_stores = [r for r in store_rows if _int(r, 5) > 0]
    mall_stores = [r for r in store_rows if _int(r, 5) < 0]

    merchants = []
    for r in npc_stores:
        code = _str(r, 2)
        refid = _int(r, 5)
        tabs_out = []
        for tab_id in tab_ids_of(r):
            meta = tab_id_to.get(tab_id)
            if meta is None:
                continue
            stock = sorted(stock_by_tab.get(meta["code"], []),
                           key=lambda s: s["order"])
            tabs_out.append({
                "tab_id": tab_id,
                "tab_code": meta["code"],
                "group_id": meta["group"],
                "sn_tab_code": meta["sn"],
                "stock": stock,
                "stock_count": len(stock),
            })
        merchants.append({
            "store_code": code,
            "store_id": store_code_to_id.get(code, 0),
            "merchant_refid": refid,
            "tabs": tabs_out,
            "stock_count": sum(t["stock_count"] for t in tabs_out),
        })

    merchant_refids = {m["merchant_refid"] for m in merchants}
    npc_refids = {_int(r, 0) for r in npc}
    missing_spawn = sorted(merchant_refids - npc_refids)
    spawned_merchants = sorted(merchant_refids & npc_refids)

    # merchant spawn regions (world rows only) for the runtime binding.
    spawn_by_ref = {}
    for r in npc:
        rid = _int(r, 0)
        region = _int(r, 1)
        if rid in merchant_refids and region >= 0:
            spawn_by_ref.setdefault(rid, []).append({
                "region": region,
                "local_x": float(_str(r, 2)),
                "height_y": float(_str(r, 3)),
                "local_z": float(_str(r, 4)),
            })

    used_tab_ids = {t for r in store_rows for t in tab_ids_of(r)}
    merchant_tab_ids = {t for r in npc_stores for t in tab_ids_of(r)}

    all_orders_unique = all(
        len({s["order"] for s in v}) == len(v) for v in stock_by_tab.values())

    def row_text(name, code, col):
        for r in load_rows(name):
            if r[col] == code:
                return "\t".join(r)
        return None

    evidence = {
        "description": (
            "Derived merchant shop binding from committed textdata assets "
            "(Phase 30). Prices, stock quantities, item names and NPC runtime "
            "behavior are NOT derived and remain PARTIAL/UNKNOWN."),
        "provenance": {
            "shopdata": "/server_dep/silkroad/textdata/shopdata.txt",
            "shoptabdata": "/server_dep/silkroad/textdata/shoptabdata.txt",
            "refshop": "/server_dep/silkroad/textdata/refshop.txt",
            "refshopgoods": "/server_dep/silkroad/textdata/refshopgoods.txt",
            "npcpos": "/server_dep/silkroad/textdata/npcpos.txt",
        },
        "anchors": {
            "STORE_CH_SMITH_shopdata_row": row_text("shopdata.tsv", "STORE_CH_SMITH", 2),
            "STORE_CH_SMITH_shopdata_index": 1,
            "STORE_CH_SMITH_tab_rows": [row_text("shoptabdata.tsv", c, 2)
                                        for c in ("STORE_CH_SMITH_TAB1",
                                                  "STORE_CH_SMITH_TAB2",
                                                  "STORE_CH_SMITH_TAB3")],
            "STORE_CH_SMITH_goods_row_count": len(stock_by_tab.get("STORE_CH_SMITH_TAB1", [])),
            "refshop_STORE_CH_SMITH_row": row_text("refshop.tsv", "STORE_CH_SMITH", 3),
            "npcpos_STORE_CH_SMITH_spawn": spawn_by_ref.get(2003, [])[0]
            if 2003 in spawn_by_ref else None,
        },
        "coverage": {
            "shopdata_rows": len(shop),
            "store_rows": len(store_rows),
            "npc_stores": len(npc_stores),
            "mall_stores": len(mall_stores),
            "store_codes_in_refshop": f"{len({_str(r,2) for r in store_rows} & refshop_codes)}/{len(store_rows)}",
            "merchant_store_ids_resolved": sum(1 for m in merchants if m["store_id"] > 0),
            "distinct_used_tab_ids": len(used_tab_ids),
            "used_tab_ids_resolved": f"{sum(1 for t in used_tab_ids if t in tab_id_to)}/{len(used_tab_ids)}",
            "merchant_distinct_tab_ids": len(merchant_tab_ids),
            "goods_tabs": len(stock_by_tab),
            "goods_order_unique_per_tab": f"{order_unique}/{len(stock_by_tab)}",
            "all_orders_unique": all_orders_unique,
            "merchant_spawned": len(spawned_merchants),
            "merchant_missing_spawn": missing_spawn,
            "merchant_refid_count": len(merchant_refids),
        },
        "jangan_merchants": sorted(
            (r for r, s in spawn_by_ref.items() if any(x["region"] == 25000 for x in s)),
            key=lambda x: x),
        "merchants": merchants,
        "limitations": {
            "prices": "PARTIAL/UNKNOWN: refpricepolicyofitem.txt col5 magnitudes are consistent "
                      "but not independently proven; not wired into the index",
            "stock_quantity": "UNKNOWN: per-shop stock/quantity textdata files are empty",
            "item_names": "UNKNOWN: ITEM_* display identity and language keys are not resolved "
                          "from committed assets",
            "mall_rows": "MALL stores use negative 0xF0000001..6 merchant_refid sentinels "
                         "(no NPC); not merchant-bound here",
            "npc_behavior": "UNKNOWN: no NPC runtime/script semantics derived",
        },
    }
    return evidence


def write(out=OUT):
    doc = build()
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True),
                   encoding="utf-8")
    return doc


if __name__ == "__main__":
    doc = write()
    print("wrote", OUT)
    print("merchants:", len(doc["merchants"]),
          "spawned:", doc["coverage"]["merchant_spawned"])
