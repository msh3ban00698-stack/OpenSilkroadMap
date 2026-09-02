#!/usr/bin/env python3
"""Unique-once SN_ZONE labels from committed worldmap_localinfo.tsv.

Proves, from committed assets only, that worldmap_localinfo.tsv col3 holds
SN_ZONE_* codes mixed with icon paths and other codes, and that a fail-closed
index keeps only SN_ZONE_* codes that appear exactly once:

  col1 zone_id       int (localinfo's own id, NOT teleportdata region_id)
  col3 zone_code     SN_ZONE_* join key
  col4 name          Korean (or Latin) name
  col5 description   Korean (or Latin) description

Duplicate SN_ZONE codes (18 codes / 97 rows, including SN_ZONE_21835_5 x12
and SN_ZONE_25800_8 with disagreeing names) are omitted. Non-SN_ZONE col3
values (ddj paths, STORE_*, SN_NPC_*) are ignored. Unknown codes resolve to
None.

Teleport coverage is a unique-once SN_ZONE join only: 29/246 teleportdata
rows and 32/44 refoptionalteleport rows. Missing SN_ZONE codes, xxx, and
non-SN_ZONE gate codes stay unlabeled. teleportlink.tsv is not consumed.
"""
import unittest
from collections import Counter
from pathlib import Path

from worldmap_localinfo import load_unique_labels, resolve

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "android/app/src/main/assets/game/textdata"
LOCALINFO = ASSETS / "worldmap_localinfo.tsv"
TELEPORT = ASSETS / "teleportdata.tsv"
OPTIONAL = ASSETS / "refoptionalteleport.tsv"


def _rows(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        out.append(line.split("\t"))
    return out


class UniqueOnceIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _rows(LOCALINFO)
        cls.labels = load_unique_labels(LOCALINFO)

    def test_committed_row_count(self):
        self.assertEqual(len(self.rows), 1116)

    def test_index_keeps_only_unique_once_sn_zone(self):
        self.assertEqual(353, len(self.labels))
        for code in self.labels:
            self.assertTrue(code.startswith("SN_ZONE_"), code)

    def test_duplicate_sn_zone_codes_fail_closed(self):
        sn = [r[3] for r in self.rows if r[3].startswith("SN_ZONE_")]
        dups = {k for k, n in Counter(sn).items() if n > 1}
        self.assertEqual(18, len(dups))
        self.assertEqual(97, sum(1 for c in sn if c in dups))
        for code in dups:
            self.assertIsNone(resolve(self.labels, code), code)
            self.assertNotIn(code, self.labels)

    def test_egypt_duplicate_and_disagreeing_names_fail_closed(self):
        self.assertIsNone(resolve(self.labels, "SN_ZONE_21835_5"))
        self.assertIsNone(resolve(self.labels, "SN_ZONE_25800_8"))

    def test_jangan_worldmap_label_is_unique(self):
        lab = resolve(self.labels, "SN_ZONE_22001")
        self.assertIsNotNone(lab)
        self.assertEqual(22001, lab["zone_id"])
        self.assertEqual("SN_ZONE_22001", lab["zone_code"])
        self.assertEqual("중국", lab["name"])
        self.assertEqual("장 안", lab["description"])

    def test_non_sn_zone_col3_is_ignored(self):
        self.assertIsNone(resolve(self.labels, r"interface\worldmap\map\xy_gate.ddj"))
        self.assertIsNone(resolve(self.labels, "STORE_DH_GATE_OUT"))
        self.assertIsNone(resolve(self.labels, "SN_NPC_CH_COMMERCE1"))
        self.assertIsNone(resolve(self.labels, None))
        self.assertIsNone(resolve(self.labels, ""))
        self.assertIsNone(resolve(self.labels, "xxx"))
        self.assertIsNone(resolve(self.labels, "SN_ZONE_DOES_NOT_EXIST"))

    def test_poi_row_is_not_a_teleport_zone_id_join(self):
        lab = resolve(self.labels, "SN_ZONE_11001")
        self.assertIsNotNone(lab)
        self.assertEqual("장안", lab["name"])
        self.assertEqual("대장간", lab["description"])
        self.assertNotEqual(lab["zone_id"], 25000)


class TeleportJoinCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labels = load_unique_labels(LOCALINFO)
        cls.gates = _rows(TELEPORT)
        cls.dests = _rows(OPTIONAL)

    def test_gate_rows_labeled_only_when_unique_once(self):
        labeled = [r for r in self.gates if resolve(self.labels, r[4]) is not None]
        self.assertEqual(29, len(labeled))
        self.assertEqual(246, len(self.gates))

    def test_destination_rows_labeled_only_when_unique_once(self):
        labeled = [r for r in self.dests if resolve(self.labels, r[3]) is not None]
        self.assertEqual(32, len(labeled))
        self.assertEqual(44, len(self.dests))

    def test_gate_ch_and_changan_share_unique_localinfo(self):
        gate = self.gates[0]
        self.assertEqual("GATE_CH", gate[2])
        self.assertEqual("SN_ZONE_22001", gate[4])
        lab = resolve(self.labels, gate[4])
        self.assertEqual("중국", lab["name"])
        self.assertEqual("장 안", lab["description"])
        changan = [r for r in self.dests if r[2] == "Chang'an"][0]
        self.assertEqual("SN_ZONE_22001", changan[3])
        self.assertEqual(lab, resolve(self.labels, changan[3]))

    def test_missing_and_non_sn_zone_gate_codes_stay_unlabeled(self):
        self.assertIsNone(resolve(self.labels, "SN_ZONE_25022"))
        self.assertIsNone(resolve(self.labels, "SN_JUPITER_B_1_GATE_1ATE"))
        self.assertIsNone(resolve(self.labels, "RN_OTHER_SKYTEMPLE_A_01"))
        unlabeled = [r for r in self.gates if resolve(self.labels, r[4]) is None]
        self.assertEqual(217, len(unlabeled))


if __name__ == "__main__":
    unittest.main(verbosity=2)
