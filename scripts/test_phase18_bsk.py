#!/usr/bin/env python3
"""Phase 18 BSK decoder tests (hermetic against committed fixtures)."""
import json
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsk_decoder as B  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "bsk_phase18.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsk_samples")


def _load():
    with open(FIXTURE) as fh:
        return json.load(fh)


class TestBskFixtureIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = _load()

    def test_raw_samples_match_sha256(self):
        for key, rec in self.fixture["samples"].items():
            with open(os.path.join(SAMPLES_DIR, key + ".bsk"), "rb") as fh:
                raw = fh.read()
            self.assertEqual(len(raw), rec["size"], key)
            self.assertEqual(
                __import__("hashlib").sha256(raw).hexdigest(),
                rec["sha256"], key)

    def test_fixture_matches_live_census(self):
        census = self.fixture["census"]
        self.assertGreaterEqual(census["exact"], 1030)
        self.assertEqual(len(census["inexact"]), 1)
        self.assertEqual(census["inexact"][0].lower(),
                         "/prim/skel/item/common/mob_select.bsk")

    def test_expected_bone_counts(self):
        expect = {
            "chinaman_skel": 38,
            "bandit": 35,
            "islamman": 43,
            "blackrobber": 35,
            "horse1": 31,
        }
        for key, n in expect.items():
            self.assertEqual(self.fixture["samples"][key]["bone_count"], n, key)


class TestParseBsk(unittest.TestCase):
    def _raw(self, key):
        with open(os.path.join(SAMPLES_DIR, key + ".bsk"), "rb") as fh:
            return fh.read()

    def test_magic_and_trailer(self):
        raw = self._raw("bandit")
        self.assertEqual(raw[:12], b"JMXVBSK 0101")
        r = B.parse_bsk(raw)
        self.assertEqual(r["parsed_bytes"] + B.TRAILER_LEN, len(raw))
        self.assertEqual(r["trailer"], b"\x00" * 8)
        self.assertTrue(r["exact"])

    def test_bone_record_layout(self):
        raw = self._raw("bandit")
        r = B.parse_bsk(raw)
        self.assertEqual(len(r["bones"]), 35)
        b0 = r["bones"][0]
        self.assertEqual(b0["name"], "Bip01")
        self.assertEqual(b0["parent"], "")
        self.assertEqual(len(b0["rot_parent"]), 4)
        self.assertEqual(len(b0["tr_parent"]), 3)
        self.assertEqual(len(b0["rot_origin"]), 4)
        self.assertEqual(len(b0["tr_origin"]), 3)
        self.assertEqual(len(b0["rot_local"]), 4)
        self.assertEqual(len(b0["tr_local"]), 3)
        self.assertEqual(b0["children"], ["Bip01 Pelvis"])

    def test_children_symmetry(self):
        r = B.parse_bsk(self._raw("bandit"))
        names = [b["name"] for b in r["bones"]]
        index = {n: i for i, n in enumerate(names)}
        for i, b in enumerate(r["bones"]):
            for c in b["children"]:
                self.assertIn(c, index)
                self.assertEqual(r["bones"][index[c]]["parent"], b["name"])

    def test_parse_independent_of_file_size(self):
        for key in ("chinaman_skel", "islamman", "blackrobber", "horse1"):
            r = B.parse_bsk(self._raw(key))
            self.assertTrue(r["exact"], key)
            self.assertEqual(r["parsed_bytes"] + 8, r["file_size"], key)

    def test_bad_magic_rejected(self):
        r = B.parse_bsk(b"XXXXBSK 0101" + b"\x00" * 40)
        self.assertFalse(r["exact"])
        self.assertIsNotNone(r["error"])


class TestBoneHelpers(unittest.TestCase):
    def test_bone_names(self):
        with open(FIXTURE) as fh:
            fixture = json.load(fh)
        parsed = {"bones": fixture["samples"]["bandit"]["bones"]}
        self.assertEqual(len(B.bone_names(parsed)), 35)
        self.assertEqual(B.bone_names(parsed)[0], "Bip01")


if __name__ == "__main__":
    unittest.main()
