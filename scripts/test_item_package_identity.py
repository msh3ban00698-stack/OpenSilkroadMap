#!/usr/bin/env python3
"""Phase 30 itemdata package-join parity tests.

Proves, from committed assets, that every merchant-bound refshopgoods
PACKAGE_ITEM_* code becomes a real ITEM_* code by dropping exactly the
leading "PACKAGE_" prefix, and that the committed item_package_identity.tsv
covers those ITEM_* rows using only the proven itemdata anchors:

  col1 item id     unique numeric id
  col2 item code   ITEM_* (join key after PACKAGE_ strip)
  col52 model path backslash .bsr, or the literal placeholder xxx
  col54 icon path  backslash .ddj (784/784 merchant unique)

316/318 is the refquestrewarditems.tsv -> itemdata col2 join, NOT merchant
stock coverage. Merchant stock is 1233/1233 rows (784 unique ITEM_*).

Live-corpus tests (skipped when /tmp/opencode/textdata is absent) confirm
the committed extract matches live Media.pk2 itemdata_*.txt bytes.
Unproven fields (SN_* language keys, prices, scrap-of-package contents,
stock quantity) are not present.
"""
import glob
import unittest
from pathlib import Path

from shop_merchant_evidence import _str, build, load_rows

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "android/app/src/main/assets/game/textdata"
LIVE = Path("/tmp/opencode/textdata")
PACKAGE_PREFIX = "PACKAGE_"
IDENTITY = ASSETS / "item_package_identity.tsv"


def load_identity():
    rows = {}
    with open(IDENTITY, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#") or line.startswith("//"):
                continue
            cols = line.split("\t")
            rows[cols[0]] = (int(cols[1]), cols[2], cols[3])
    return rows


def strip_package(code):
    if not code.startswith(PACKAGE_PREFIX):
        return None
    stripped = code[len(PACKAGE_PREFIX):]
    if not stripped.startswith("ITEM_"):
        return None
    return stripped


def merchant_package_codes(ev):
    codes = []
    for m in ev["merchants"]:
        for t in m["tabs"]:
            for s in t["stock"]:
                codes.append(s["item_code"])
    return codes


class CommittedPackageJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = build()
        cls.identity = load_identity()
        cls.goods = load_rows("refshopgoods.tsv")
        cls.quest = load_rows("refquestrewarditems.tsv")

    def test_every_goods_row_is_package_item_prefix(self):
        for r in self.goods:
            code = _str(r, 3)
            self.assertTrue(code.startswith(PACKAGE_PREFIX), code)
            self.assertTrue(code[len(PACKAGE_PREFIX):].startswith("ITEM_"), code)

    def test_merchant_stock_package_strip_covers_1233(self):
        codes = merchant_package_codes(self.ev)
        self.assertEqual(len(codes), 1233)
        stripped = [strip_package(c) for c in codes]
        self.assertTrue(all(s is not None for s in stripped))
        missing = [s for s in stripped if s not in self.identity]
        self.assertEqual(missing, [])
        self.assertEqual(len(self.identity), 784)

    def test_smith_blade_and_arrow_anchors(self):
        blade = self.identity["ITEM_CH_BLADE_01_A"]
        self.assertEqual(blade[0], 107)
        self.assertEqual(blade[1], r"item\china\weapon\blade_01.bsr")
        self.assertEqual(blade[2], r"item\china\weapon\blade_01.ddj")
        sword = self.identity["ITEM_CH_SWORD_01_A"]
        self.assertEqual(sword[0], 71)
        self.assertEqual(sword[1], r"item\china\weapon\sword_01.bsr")
        arrow = self.identity["ITEM_ETC_AMMO_ARROW_01"]
        self.assertEqual(arrow[0], 62)
        self.assertEqual(arrow[1], "xxx")
        self.assertEqual(arrow[2], r"item\etc\ammo_arrow_01.ddj")

    def test_unknown_item_code_is_absent(self):
        self.assertNotIn("ITEM_DOES_NOT_EXIST", self.identity)
        self.assertIsNone(strip_package("ITEM_CH_BLADE_01_A"))
        self.assertIsNone(strip_package("PACKAGE_NOT_AN_ITEM"))

    def test_quest_reward_316_of_318_is_not_merchant_stock(self):
        quest_codes = {_str(r, 3) for r in self.quest if len(r) > 3}
        self.assertEqual(len(quest_codes), 318)
        self.assertIn("ITEM_QNO_EU_CONS_12_02", quest_codes)
        self.assertIn("xxx", quest_codes)
        merchant_items = set(self.identity)
        self.assertNotEqual(len(merchant_items), 318)
        self.assertEqual(len(merchant_items), 784)

    def test_every_merchant_unique_icon_is_ddj(self):
        for code, (_iid, model, icon) in self.identity.items():
            self.assertTrue(code.startswith("ITEM_"), code)
            self.assertTrue(icon.lower().endswith(".ddj"), (code, icon))
            self.assertTrue(model.lower().endswith(".bsr") or model == "xxx",
                            (code, model))


@unittest.skipUnless(LIVE.is_dir(), "/tmp/opencode/textdata live corpus not available")
class LiveCorpusConcordanceTests(unittest.TestCase):
    def test_committed_extract_matches_live_itemdata(self):
        live = {}
        for path in sorted(glob.glob(str(LIVE / "itemdata_*.txt"))):
            raw = Path(path).read_bytes()
            if raw[:2] == b"\xff\xfe":
                text = raw[2:].decode("utf-16-le")
            else:
                text = raw.decode("utf-16", errors="replace")
            for line in text.splitlines():
                cols = line.split("\t")
                if len(cols) <= 54 or not cols[2].startswith("ITEM_"):
                    continue
                live.setdefault(cols[2].strip(),
                                (int(cols[1]), cols[52].strip(), cols[54].strip()))
        identity = load_identity()
        for code, row in identity.items():
            self.assertIn(code, live)
            self.assertEqual(live[code], row, code)

    def test_live_merchant_stock_and_quest_coverage(self):
        live_codes = set()
        for path in sorted(glob.glob(str(LIVE / "itemdata_*.txt"))):
            raw = Path(path).read_bytes()
            text = raw[2:].decode("utf-16-le") if raw[:2] == b"\xff\xfe" else raw.decode(
                "utf-16", errors="replace")
            for line in text.splitlines():
                cols = line.split("\t")
                if len(cols) > 2 and cols[2].startswith("ITEM_"):
                    live_codes.add(cols[2].strip())
        ev = build()
        codes = merchant_package_codes(ev)
        stripped = [strip_package(c) for c in codes]
        self.assertEqual(len(stripped), 1233)
        self.assertTrue(all(s in live_codes for s in stripped))
        quest = load_rows("refquestrewarditems.tsv")
        quest_codes = {_str(r, 3) for r in quest if len(r) > 3}
        hits = quest_codes & live_codes
        miss = sorted(quest_codes - live_codes)
        self.assertEqual(len(quest_codes), 318)
        self.assertEqual(len(hits), 316)
        self.assertEqual(miss, ["ITEM_QNO_EU_CONS_12_02", "xxx"])


if __name__ == "__main__":
    unittest.main()
