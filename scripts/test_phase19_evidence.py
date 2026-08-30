#!/usr/bin/env python3
"""Phase 19 Part O proof-artifact tests (evidence records).

Verifies the committed phase19_evidence.json carries, per character, only
hashes/offsets/counts + status (never copyrighted binary payloads), and that
the bandit (DONE) and chinaman (PARTIAL) records carry the required keys. The
live portion (SRO_PK2_DIR only) re-derives the bandit record from the archives
and cross-checks it against the committed fixture.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_phase19_evidence as EV  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "phase19_evidence.json")
PK2_DIR = os.environ.get("SRO_PK2_DIR")

REQUIRED_BANDIT_KEYS = (
    "character", "status", "model", "source_file", "BSK", "BSR", "mesh",
    "texture", "skeleton", "bone_count", "vertex_count", "weight_format",
    "animation", "animation_duration", "proven_relationships",
    "unknown_relationships",
)


def _is_sha256(s):
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


class TestEvidenceFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as fh:
            cls.doc = json.load(fh)

    def test_bandit_record_present_and_done(self):
        self.assertIn("bandit", self.doc)
        self.assertEqual(self.doc["bandit"]["status"], "DONE")

    def test_bandit_required_keys(self):
        for key in REQUIRED_BANDIT_KEYS:
            self.assertIn(key, self.doc["bandit"], key)

    def test_bandit_hashes(self):
        b = self.doc["bandit"]
        self.assertTrue(_is_sha256(b["BSK"]["sha256"]), b["BSK"])
        self.assertTrue(_is_sha256(b["BSR"]["sha256"]), b["BSR"])
        self.assertTrue(len(b["mesh"]) >= 1, b["mesh"])
        for m in b["mesh"]:
            self.assertTrue(_is_sha256(m["sha256"]), m)
        self.assertTrue(_is_sha256(b["animation"][0]["sha256"]))

    def test_bandit_counts(self):
        b = self.doc["bandit"]
        self.assertEqual(b["bone_count"], 35)
        self.assertEqual(b["BSK"]["bone_count"], 35)
        self.assertGreater(b["vertex_count"], 0)
        self.assertGreater(len(b["mesh"]), 0)

    def test_bandit_animation_duration(self):
        d = self.doc["bandit"]["animation_duration"]
        self.assertEqual(d["bandit_walk"], 1333, d)
        self.assertEqual(d["bandit_stand01"], 2000, d)

    def test_bandit_weight_format_and_relationships(self):
        b = self.doc["bandit"]
        self.assertIn("65535", b["weight_format"])
        self.assertTrue(b["proven_relationships"])
        self.assertTrue(all(e["status"] == "PROVEN"
                            for e in b["proven_relationships"]))
        self.assertTrue(b["unknown_relationships"])

    def test_player_record_partial(self):
        self.assertIn("chinaman", self.doc)
        c = self.doc["chinaman"]
        self.assertEqual(c["status"], "PARTIAL")
        self.assertEqual(c["bone_count"], 38)
        self.assertTrue(c["blockers"])
        self.assertTrue(c["unknown_relationships"])

    @unittest.skipUnless(PK2_DIR, "SRO_PK2_DIR not set (live evidence skipped)")
    def test_live_bandit_record_matches_fixture(self):
        live = EV.evidence_record("bandit", pk2_dir=PK2_DIR)
        self.assertEqual(live["bone_count"],
                         self.doc["bandit"]["bone_count"])
        self.assertEqual(live["BSK"]["sha256"],
                         self.doc["bandit"]["BSK"]["sha256"])
        self.assertEqual(live["BSR"]["sha256"],
                         self.doc["bandit"]["BSR"]["sha256"])
        self.assertEqual(live["vertex_count"],
                         self.doc["bandit"]["vertex_count"])


if __name__ == "__main__":
    unittest.main()
