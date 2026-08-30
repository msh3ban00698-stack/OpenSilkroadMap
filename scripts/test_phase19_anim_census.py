#!/usr/bin/env python3
"""Phase 19 Part F animation file census tests (hermetic).

Proven facts asserted here:
  * 4793/4795 original .ban files parse byte-exactly (JMXVBAN 0102 layout);
    2 use JMXVBAN 0101 with an UNPROVEN layout (documented anomaly)
  * zero non-.ban files carry animation magic (no misclassified animation)
  * committed samples classify correctly: bandit animations = animation_data,
    a .bsk = skeleton_data, a .bms = unrelated_binary
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animation_census as AC  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "animation_census_phase19.json")
TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata",
                  "formats")


class TestAnimationCensusFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE) as fh:
            cls.fixture = json.load(fh)

    def test_counts(self):
        c = self.fixture["counts"]
        self.assertEqual(c["animation_data"], 4793)
        self.assertEqual(c["animation_data_unparsed"], 2)
        self.assertEqual(c["skeleton_data"], 1036)
        self.assertEqual(c["motion_or_unknown"], 1)
        # every .ban accounted for
        self.assertEqual(c["animation_data"] + c["animation_data_unparsed"],
                         4795)

    def test_anomalies_documented(self):
        an = self.fixture["anomalies"]
        unparsed = [a for a in an
                    if a["classification"] == "animation_data_unparsed"]
        self.assertEqual(len(unparsed), 2)
        paths = [a["path"] for a in unparsed]
        self.assertTrue(any("spidey_attack01" in p for p in paths))
        self.assertTrue(any("chakji_stand02" in p for p in paths))
        for a in unparsed:
            self.assertIn("0101", a["evidence"])
        motion = [a for a in an
                  if a["classification"] == "motion_or_unknown"]
        self.assertEqual(len(motion), 1)

    def test_magic_histogram(self):
        h = self.fixture["magic_histogram"]
        self.assertTrue(any("JMXVBAN" in k for k in h))
        self.assertEqual(sum(h.values()), 4793)

    def test_version_histogram(self):
        v = self.fixture["version_histogram"]
        self.assertEqual(v, {"0102": 4793})

    def test_duration_buckets(self):
        d = self.fixture["duration_buckets"]
        self.assertEqual(sum(d.values()), 4793)


class TestClassifyBytes(unittest.TestCase):
    def _read(self, *parts):
        with open(os.path.join(TD, *parts), "rb") as fh:
            return fh.read()

    def test_bandit_animations_are_animation_data(self):
        raw = self._read("ban_phase18_samples", "bandit_walk.ban")
        c = AC.classify_bytes(raw, "/x/bandit_walk.ban")
        self.assertEqual(c["classification"], "animation_data")
        self.assertEqual(c["kpb"], 15)
        self.assertEqual(c["duration_ms"], 1333)

        raw2 = self._read("ban_phase18_samples", "bandit_stand01.ban")
        c2 = AC.classify_bytes(raw2, "/x/bandit_stand01.ban")
        self.assertEqual(c2["classification"], "animation_data")
        self.assertEqual(c2["kpb"], 5)
        self.assertEqual(c2["duration_ms"], 2000)

    def test_skeleton_is_not_animation(self):
        raw = self._read("bsk_samples", "bandit.bsk")
        c = AC.classify_bytes(raw, "/prim/skel/mob/china/bandit.bsk")
        self.assertEqual(c["classification"], "skeleton_data")

    def test_mesh_is_unrelated(self):
        raw = self._read("bms_samples", "nature_tree.bms")
        c = AC.classify_bytes(raw, "/prim/mesh/misc/nature_tree.bms")
        self.assertEqual(c["classification"], "unrelated_binary")


if __name__ == "__main__":
    unittest.main()
