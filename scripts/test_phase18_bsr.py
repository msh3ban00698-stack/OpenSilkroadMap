#!/usr/bin/env python3
"""Phase 18 BSR decoder tests (hermetic against committed fixtures)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsr_decoder as R  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "bsr_phase18.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsr_samples")


def _load():
    with open(FIXTURE) as fh:
        return json.load(fh)


class TestBrsrFixtureIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = _load()

    def test_raw_samples_match_sha256(self):
        for key, rec in self.fixture["samples"].items():
            with open(os.path.join(SAMPLES_DIR, key + ".bsr"), "rb") as fh:
                raw = fh.read()
            self.assertEqual(len(raw), rec["size"], key)
            self.assertEqual(
                __import__("hashlib").sha256(raw).hexdigest(),
                rec["sha256"], key)

    def test_bandit_character_groups(self):
        b = self.fixture["samples"]["bandit"]
        self.assertTrue(b["is_character"])
        self.assertTrue(b["group_order_ok"])
        self.assertEqual(len(b["materials"]), 3)
        self.assertEqual(len(b["meshes"]), 3)
        self.assertEqual(len(b["animations"]), 16)
        self.assertEqual(len(b["skeleton"]), 1)
        self.assertTrue(all(p.endswith(".bsk") for p in b["skeleton"]))
        self.assertGreaterEqual(len(b["effects"]), 1)
        self.assertGreaterEqual(len(b["sounds"]), 1)

    def test_bandit_mesh_paths(self):
        b = self.fixture["samples"]["bandit"]
        self.assertIn("/prim/mesh/mob/china/bandit_part1.bms", b["meshes"])
        self.assertIn("/prim/mesh/mob/china/bandit_part2.bms", b["meshes"])
        self.assertIn("/prim/mesh/mob/china/bandit_sword.bms", b["meshes"])
        self.assertEqual(b["skeleton"],
                         ["/prim/skel/mob/china/bandit.bsk"])

    def test_chinaquest_priest(self):
        c = self.fixture["samples"]["chinaquest_priest"]
        self.assertTrue(c["is_character"])
        self.assertTrue(c["group_order_ok"])
        self.assertEqual(len(c["materials"]), 1)
        self.assertEqual(len(c["meshes"]), 3)
        self.assertEqual(len(c["animations"]), 2)
        self.assertEqual(len(c["skeleton"]), 1)

    def test_movoi(self):
        m = self.fixture["samples"]["movoi"]
        self.assertTrue(m["is_character"])
        self.assertEqual(len(m["animations"]), 15)
        self.assertEqual(len(m["skeleton"]), 1)

    def test_static_object_not_character(self):
        t = self.fixture["samples"]["tre_tree03"]
        self.assertFalse(t["is_character"])
        self.assertEqual(len(t["meshes"]), 4)
        self.assertEqual(len(t["skeleton"]), 0)
        self.assertEqual(len(t["animations"]), 0)


class TestParseBrsr(unittest.TestCase):
    def _raw(self, key):
        with open(os.path.join(SAMPLES_DIR, key + ".bsr"), "rb") as fh:
            return fh.read()

    def test_magic_versions(self):
        self.assertEqual(self._raw("bandit")[:12], b"JMXVRES 0109")
        self.assertEqual(self._raw("tre_tree03")[:12], b"JMXVRES 0109")

    def test_header_table_present(self):
        r = R.parse_bsr_references(self._raw("bandit"))
        self.assertEqual(len(r["header_table"]), 8)
        self.assertTrue(all(v > 0 for v in r["header_table"]))

    def test_character_group_order_ok(self):
        r = R.parse_bsr_references(self._raw("bandit"))
        self.assertTrue(r["group_order_ok"])
        want = [e for e in R.GROUP_ORDER]
        seen = [".bmt", ".bms", ".ban", ".bsk", ".efp", ".wav"]
        self.assertEqual(want, seen)

    def test_bad_magic_rejected(self):
        r = R.parse_bsr_references(b"XXXXVES 0109" + b"\x00" * 80)
        self.assertIsNotNone(r["error"])
        self.assertFalse(r["group_order_ok"])


class TestResolveCharacter(unittest.TestCase):
    def test_resolve(self):
        raw = open(os.path.join(SAMPLES_DIR, "bandit.bsr"), "rb").read()
        parsed = R.parse_bsr_references(raw)
        res = R.resolve_character(parsed)
        self.assertEqual(len(res["bms"]), 3)
        self.assertEqual(len(res["ban"]), 16)
        self.assertEqual(len(res["bsk"]), 1)
        self.assertEqual(len(res["bmt"]), 3)


if __name__ == "__main__":
    unittest.main()
