#!/usr/bin/env python3
"""Phase 18 BMS vertex-skin tests (hermetic against committed fixtures)."""
import json
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as B  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "bms_skin_phase18.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bms_skin_samples")


def _load():
    with open(FIXTURE) as fh:
        return json.load(fh)


class TestSkinFixtureIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = _load()

    def test_raw_samples_match_sha256(self):
        for key, rec in self.fixture["samples"].items():
            with open(os.path.join(SAMPLES_DIR, key + ".bms"), "rb") as fh:
                raw = fh.read()
            self.assertEqual(len(raw), rec["size"], key)
            self.assertEqual(
                __import__("hashlib").sha256(raw).hexdigest(),
                rec["sha256"], key)

    def test_skin_block_is_6x_vcount(self):
        for key, rec in self.fixture["samples"].items():
            self.assertEqual(rec["skin_record_bytes"],
                             6 * rec["vertex_count"], key)
            self.assertEqual(len(rec["records"]), rec["vertex_count"], key)

    def test_bone_indices_in_local_range(self):
        for key, rec in self.fixture["samples"].items():
            bc = len(rec["bone_names"])
            for r in rec["records"]:
                self.assertLess(r["bone1"], bc, key)
                if r["bone2"] != 0xFF:
                    self.assertLess(r["bone2"], bc, key)
            self.assertGreaterEqual(rec["bone_names"][0], "", key)

    def test_weights_within_u16_range(self):
        for key, rec in self.fixture["samples"].items():
            for r in rec["records"]:
                self.assertLessEqual(r["weight1"], 65535, key)
                self.assertLessEqual(r["weight2"], 65535, key)
                if r["bone2"] == 0xFF:
                    self.assertEqual(r["weight2"], 0, key)

    def test_bandit_mesh_bone_names_subset_of_skel(self):
        skel = None
        for key, rec in self.fixture["samples"].items():
            if key.startswith("bandit"):
                skel = self._bandit_skel_names()
                missing = [n for n in rec["bone_names"] if n not in skel]
                self.assertEqual(missing, [], key)

    def _bandit_skel_names(self):
        with open(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "testdata", "formats", "bsk_phase18.json")) as fh:
            bsk = json.load(fh)
        return [b["name"] for b in bsk["samples"]["bandit"]["bones"]]


class TestParseSkinLive(unittest.TestCase):
    def test_live_parse_matches_fixture(self):
        fixture = _load()
        for key, rec in fixture["samples"].items():
            with open(os.path.join(SAMPLES_DIR, key + ".bms"), "rb") as fh:
                raw = fh.read()
            r = B.parse_bms(raw)
            self.assertIsNotNone(r["skin"], key)
            self.assertEqual(len(r["skin"]["records"]), rec["vertex_count"], key)
            self.assertEqual(r["skin"]["two_influence"], rec["two_influence"], key)

    def test_static_mesh_has_no_skin_block(self):
        raw = open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "testdata", "formats", "bms_samples", "artifact_table.bms"),
            "rb").read()
        r = B.parse_bms(raw)
        self.assertIsNone(r["skin"])


if __name__ == "__main__":
    unittest.main()
