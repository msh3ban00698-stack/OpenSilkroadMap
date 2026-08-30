#!/usr/bin/env python3
"""Phase 19 Part A BSK census tests (hermetic against committed fixture).

Covers: per-field evidence records (offset/size/raw_value/interpretation/
evidence/status), magic/version/size grouping across ALL original BSK files,
and the raw bone_type u8 histogram (values reported, semantics NOT asserted).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsk_decoder as B  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "bsk_census_phase19.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsk_samples")

PROVEN_FIELDS = {
    "magic", "bone_count", "trailer",
}
BONE_PREFIXES = ("bones[", )


class TestCensusFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE) as fh:
            cls.fixture = json.load(fh)

    def test_samples_bytes_match_sha256(self):
        for key, rec in self.fixture["samples"].items():
            with open(os.path.join(SAMPLES_DIR, key + ".bsk"), "rb") as fh:
                raw = fh.read()
            self.assertEqual(len(raw), rec["size"], key)
            self.assertEqual(
                __import__("hashlib").sha256(raw).hexdigest(),
                rec["sha256"], key)

    def test_groups_are_bsk_magic_families(self):
        groups = self.fixture["groups"]
        self.assertTrue(groups)
        total = 0
        jmxv = [g for g in groups if g["magic"] == "JMXVBSK 0101"]
        self.assertTrue(jmxv)
        self.assertEqual(sum(g["count"] for g in jmxv), 1034)
        other = [g for g in groups if g["magic"] != "JMXVBSK 0101"]
        # single known outlier (mob_select.bsk) forms its own family
        self.assertEqual(len(other), 1)
        self.assertEqual(other[0]["count"], 1)
        for g in groups:
            self.assertTrue(g["size_min"] <= g["size_max"])
            total += g["count"]
        self.assertEqual(total, self.fixture["census_total_nonzero"])

    def test_bone_type_histogram_reported(self):
        hist = self.fixture["bone_type_histogram"]
        self.assertTrue(hist)
        self.assertEqual(sum(hist.values()), self.fixture["census_total_bones"])
        for v in hist.values():
            self.assertGreaterEqual(v, 1)


class TestCensusRecord(unittest.TestCase):
    def _raw(self, key):
        with open(os.path.join(SAMPLES_DIR, key + ".bsk"), "rb") as fh:
            return fh.read()

    def test_record_exact_and_fields_cover_file(self):
        for key in ("chinaman_skel", "bandit", "islamman", "blackrobber",
                    "horse1"):
            raw = self._raw(key)
            rec = B.census_record(raw)
            self.assertTrue(rec["exact"], key)
            self.assertEqual(rec["bone_count"], B.parse_bsk(raw)["bone_count"])
            fields = rec["fields"]
            self.assertEqual(fields[0]["field"], "magic")
            self.assertEqual(fields[0]["raw_value"], "JMXVBSK 0101")
            last = fields[-1]
            self.assertEqual(last["field"], "trailer")
            self.assertEqual(last["status"], "PROVEN")
            for f in fields:
                self.assertEqual(f["status"], "PROVEN", f["field"] + " " + key)
                self.assertIn("interpretation", f)
                self.assertIn("evidence", f)

    def test_field_offsets_monotonic_and_contiguous(self):
        raw = self._raw("bandit")
        rec = B.census_record(raw)
        offs = [f["offset"] for f in rec["fields"]]
        self.assertTrue(all(a < b for a, b in zip(offs, offs[1:])))
        ends = [f["offset"] + f["size"] for f in rec["fields"]]
        self.assertEqual(ends[-1], len(raw))

    def test_fixture_record_matches_live(self):
        with open(FIXTURE) as fh:
            fixture = json.load(fh)
        for key, rec in fixture["samples"].items():
            live = B.census_record(self._raw(key))
            self.assertEqual(live["exact"], rec["exact"], key)
            self.assertEqual(
                [f["field"] for f in live["fields"]],
                [f["field"] for f in rec["record_fields"]], key)


if __name__ == "__main__":
    unittest.main()
