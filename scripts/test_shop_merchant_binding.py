#!/usr/bin/env python3
"""Phase 30 shop-merchant binding regression tests.

Proves, against the COMMITTED assets under
android/app/src/main/assets/game/textdata/, that the merchant/shop binding is
real and reproducible:

  * shopdata.tsv col5 merchant_refid (>0) names the NPC RefCharID running the
    store named in col2; every one of those 52 store codes exists in the server
    refshop.tsv store list (57/57).
  * shopdata.tsv col6.. store_tab_ids all resolve in shoptabdata.tsv col1
    (152/152), and the resolved tab codes address stock rows in the committed
    refshopgoods.tsv (empty stock stays empty, never invented).
  * 51/52 merchant RefCharIds appear in npcpos.tsv (STORE_AM_SPECIAL/7568 has
    no placement); the Jangan (region 25000) merchant set is exact.
  * refshopgoods.tsv col4 order_index is unique within every tab.

Live-corpus tests (skipped when /tmp/opencode/textdata is absent) additionally
reconcile merchant refids -> characterdata codes (NPC_CH_*), merchant tab codes
-> server refshoptab.txt, and PACKAGE_ITEM_* -> ITEM_* identity. A shard-backup
test (skipped when SRO_DB_DIR is unset) confirms the shop strings appear in the
server backup.
"""
import json
import os
import unittest
from pathlib import Path

from shop_merchant_evidence import (NPC_PREFIX, OUT, build, load_rows,
                                    tab_ids_of, _int, _str)

PACKAGE_PREFIX = "PACKAGE_"

REPO = Path(__file__).resolve().parent.parent
LIVE_TEXTDATA = Path("/tmp/opencode/textdata")


def _bak_path():
    db_dir = os.environ.get("SRO_DB_DIR")
    if not db_dir:
        return None
    p = Path(db_dir) / "SRO_VT_SHARD.Bak"
    return p if p.is_file() else None


class CommittedBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = build()
        cls.shop = load_rows("shopdata.tsv")
        cls.tabs = load_rows("shoptabdata.tsv")
        cls.refshop = load_rows("refshop.tsv")
        cls.goods = load_rows("refshopgoods.tsv")
        cls.npc = load_rows("npcpos.tsv")

    def test_asset_shapes(self):
        self.assertEqual(len(self.shop), 57)
        self.assertEqual(len(self.tabs), 161)
        self.assertEqual(len(self.goods), 2282)
        self.assertEqual(len(self.npc), 18457)
        self.assertEqual(len(self.refshop), 78)

    def test_npc_vs_mall_store_rows(self):
        store = [r for r in self.shop if len(r) > 5]
        npc_stores = [r for r in store if _int(r, 5) > 0]
        mall_stores = [r for r in store if _int(r, 5) < 0]
        self.assertEqual(len(store), 57)
        self.assertEqual(len(npc_stores), 52)
        self.assertEqual(len(mall_stores), 5)
        # MALL sentinels are the signed int32 readings of 0xF0000001..6.
        sentinels = {v - (1 << 32) for v in range(0xF0000001, 0xF0000007)}
        mall_values = {_int(r, 5) for r in mall_stores}
        self.assertEqual(mall_values & sentinels, mall_values)
        self.assertTrue(all(_int(r, 5) <= -268435450 for r in mall_stores))

    def test_store_codes_are_server_authoritative(self):
        refcodes = {_str(r, 3) for r in self.refshop if len(r) > 3}
        store_codes = {_str(r, 2) for r in self.shop if len(r) > 5}
        self.assertEqual(len(store_codes & refcodes), 57)
        self.assertEqual(self.ev["coverage"]["store_codes_in_refshop"], "57/57")

    def test_merchant_tab_ids_resolve(self):
        store = [r for r in self.shop if len(r) > 5]
        tab_ids = set(t for r in store for t in tab_ids_of(r))
        tab_lookup = {_int(t, 1) for t in self.tabs}
        self.assertEqual(len(tab_ids & tab_lookup), len(tab_ids))
        self.assertEqual(self.ev["coverage"]["used_tab_ids_resolved"], "152/152")
        self.assertEqual(self.ev["coverage"]["merchant_distinct_tab_ids"], 140)

    def test_goods_order_index_unique_per_tab(self):
        per = {}
        for r in self.goods:
            per.setdefault(_str(r, 2), []).append(_int(r, 4))
        self.assertEqual(len(per), 164)
        self.assertTrue(all(len(set(v)) == len(v) for v in per.values()))
        self.assertEqual(self.ev["coverage"]["goods_order_unique_per_tab"],
                         "164/164")

    def test_package_item_prefix_invariant(self):
        # Goods rows carry PACKAGE_ITEM_* codes; the real ITEM_* code is the
        # same string with only the "PACKAGE_" prefix dropped (verified against
        # live itemdata: 1591 distinct goods codes all resolve).
        for r in self.goods:
            code = _str(r, 3)
            self.assertTrue(code.startswith(NPC_PREFIX), code)
            self.assertTrue(code[len(PACKAGE_PREFIX):].startswith("ITEM_"), code)

    def test_spawn_binding(self):
        c = self.ev["coverage"]
        self.assertEqual(c["merchant_spawned"], 51)
        self.assertEqual(c["merchant_missing_spawn"], [7568])
        npc_refs = {_int(r, 0) for r in self.npc}
        merchant_refs = {m["merchant_refid"] for m in self.ev["merchants"]}
        self.assertEqual(merchant_refs - npc_refs, {7568})

    def test_smith_spawn_region_and_position(self):
        spawn = self.ev["anchors"]["npcpos_STORE_CH_SMITH_spawn"]
        self.assertEqual(spawn["region"], 25000)
        self.assertAlmostEqual(spawn["local_x"], 332.73, places=2)
        self.assertAlmostEqual(spawn["local_z"], 1406.7, places=1)

    def test_jangan_merchant_set_exact(self):
        self.assertEqual(self.ev["jangan_merchants"],
                         [2003, 2004, 2005, 2008, 2009, 2010, 2027])

    def test_smith_stock_profile(self):
        smith = [m for m in self.ev["merchants"]
                 if m["store_code"] == "STORE_CH_SMITH"][0]
        self.assertEqual(smith["store_id"], 966)
        self.assertEqual(smith["merchant_refid"], 2003)
        self.assertEqual([(t["tab_code"], t["stock_count"]) for t in smith["tabs"]],
                         [("STORE_CH_SMITH_TAB1", 15),
                          ("STORE_CH_SMITH_TAB2", 3),
                          ("STORE_CH_SMITH_TAB3", 1)])
        self.assertEqual(smith["stock_count"], 19)

    def test_evidence_json_reproducible(self):
        with open(OUT, encoding="utf-8") as fh:
            committed = json.load(fh)
        self.assertEqual(committed["merchants"], self.ev["merchants"])
        self.assertEqual(committed["coverage"], self.ev["coverage"])
        self.assertEqual(committed["jangan_merchants"], self.ev["jangan_merchants"])


@unittest.skipUnless(LIVE_TEXTDATA.is_dir(),
                     "/tmp/opencode/textdata live corpus not available")
class LiveCorpusConcordanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import codecs
        import glob

        def rows(name):
            with codecs.open(LIVE_TEXTDATA / name, encoding="utf-16") as fh:
                text = fh.read()
            return [l for l in text.splitlines() if l.strip()]

        cls.ev = build()
        cls.characterdata = {}
        for f in sorted(glob.glob(str(LIVE_TEXTDATA / "characterdata_*.txt"))):
            for l in rows(Path(f).name):
                r = l.split("\t")
                if len(r) > 50 and r[1].isdigit():
                    cls.characterdata.setdefault(r[1], r)
        cls.refshoptab = [l.split("\t") for l in rows("refshoptab.txt")]
        itemdata_dirs = sorted(glob.glob(str(LIVE_TEXTDATA / "itemdata_*.txt")))
        cls.item_rows = []
        for f in itemdata_dirs:
            for l in rows(Path(f).name):
                r = l.split("\t")
                if len(r) > 2 and r[2].startswith("ITEM_"):
                    cls.item_rows.append(r)

    def test_merchant_refids_resolve_to_npc_codes(self):
        missing = []
        for m in self.ev["merchants"]:
            row = self.characterdata.get(str(m["merchant_refid"]))
            if row is None:
                missing.append(m)
                continue
            self.assertTrue(row[2].startswith("NPC_"), row[2])
        # Every merchant refid must exist in characterdata. STORE_AM_SPECIAL/
        # 7568 resolves as NPC_AM_SPECIAL (it is only missing from npcpos
        # spawn placement, which test_spawn_binding covers).
        self.assertEqual({m["merchant_refid"] for m in missing}, set())
        self.assertTrue(self.characterdata["7568"][2].startswith("NPC_"))
        smith = self.characterdata["2003"]
        self.assertEqual(smith[2], "NPC_CH_SMITH")
        self.assertEqual(smith[5], "SN_NPC_CH_SMITH")
        self.assertTrue("chinashop_smith.bsr" in smith[52])

    def test_npc_store_tab_codes_exist_in_server_refshoptab(self):
        server_tab_codes = {r[3] for r in self.refshoptab if len(r) > 3}
        goods_tabs = {_str(r, 2) for r in load_rows("refshopgoods.tsv")}
        self.assertTrue(goods_tabs <= server_tab_codes)
        for m in self.ev["merchants"]:
            for t in m["tabs"]:
                if t["stock_count"] > 0:
                    self.assertIn(t["tab_code"], server_tab_codes, t["tab_code"])

    def test_package_items_strip_to_real_item_codes(self):
        item_codes = {r[2] for r in self.item_rows}
        checked = 0
        for m in self.ev["merchants"]:
            for t in m["tabs"]:
                for s in t["stock"]:
                    # PACKAGE_ITEM_* codes are real ITEM_* codes with the
                    # leading PACKAGE_ prefix; drop exactly that to resolve.
                    stripped = s["item_code"][len(PACKAGE_PREFIX):]
                    self.assertIn(stripped, item_codes, s["item_code"])
                    checked += 1
        # Every merchant-bound stock row must resolve to a real item code, and
        # the visit count must equal the derived stock total (1233).
        self.assertEqual(
            checked,
            sum(t["stock_count"] for m in self.ev["merchants"] for t in m["tabs"]))
        self.assertEqual(checked, 1233)


@unittest.skipUnless(_bak_path(), "SRO_DB_DIR/SRO_VT_SHARD.Bak not available")
class ShardBakConcordanceTests(unittest.TestCase):
    def test_shop_strings_present_in_shard_backup(self):
        bak = _bak_path().read_bytes()
        for token in ("_RefShopGoods", "_RefShopObject",
                      "STORE_CH_SMITH_TAB1", "PACKAGE_ITEM_CH_BLADE_01_A",
                      "NPC_CH_SMITH"):
            self.assertIn(token.encode("ascii"), bak, token)


if __name__ == "__main__":
    unittest.main(verbosity=2)
