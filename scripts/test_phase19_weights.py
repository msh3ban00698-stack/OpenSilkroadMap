#!/usr/bin/env python3
"""Phase 19 Part C real skinning-weight census tests (hermetic).

Proven facts asserted here (across bandit 3 parts + player face + chicken +
avatar meshes):
  * max 2 influences per vertex (u8 b1 + u16 w1 + u8 b2 + u16 w2)
  * index width 8 bits, weight width 16 bits, weight scale 65535
  * zero invalid indices, zero repeated (b1==b2), zero zero-weight slots
  * two-influence sums are approximately 65535 but NOT exactly normalized
    (source fact) -- renderer normalization must be a renderer operation
  * the 6-byte skin block is authoritative for EVERY vertex: no vertex has a
    missing skin record, regardless of the vertex-record bone_index field
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as B  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "weights_phase19.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bms_weights_samples")


class TestWeightsCensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE) as fh:
            cls.fixture = json.load(fh)

    def _raw(self, key):
        with open(os.path.join(SAMPLES_DIR, key + ".bms"), "rb") as fh:
            return fh.read()

    def test_all_samples_provable(self):
        for key, rec in self.fixture["samples"].items():
            self.assertIsNotNone(rec["census"], key + " " + str(rec.get("error")))
            self.assertTrue(rec["census"]["provable"], key)

    def test_samples_bytes_match_sha256(self):
        for key, rec in self.fixture["samples"].items():
            raw = self._raw(key)
            self.assertEqual(len(raw), rec["size"], key)
            self.assertEqual(
                __import__("hashlib").sha256(raw).hexdigest(),
                rec["sha256"], key)

    def test_influence_shape(self):
        for key, rec in self.fixture["samples"].items():
            c = rec["census"]
            self.assertLessEqual(c["max_influences"], 2, key)
            self.assertEqual(c["index_width_bits"], 8, key)
            self.assertEqual(c["weight_width_bits"], 16, key)
            self.assertEqual(c["weight_scale"], 65535.0, key)
            self.assertEqual(
                c["single_influence"] + c["two_influence"],
                c["vertex_count"], key)

    def test_no_anomalies(self):
        for key, rec in self.fixture["samples"].items():
            c = rec["census"]
            self.assertEqual(c["invalid_indices"], [], key)
            self.assertEqual(c["repeated_indices"], 0, key)
            self.assertEqual(c["zero_weight_slots"], 0, key)

    def test_weights_not_exactly_normalized_in_source(self):
        for key, rec in self.fixture["samples"].items():
            n = rec["census"]["normalization"]
            if not n:
                continue
            self.assertLess(n["count_sum_eq_65535"], n["two_influence"], key)
            self.assertLessEqual(n["max_sum"], 65535, key)

    def test_skin_block_authoritative_for_every_vertex(self):
        for key, rec in self.fixture["samples"].items():
            cc = rec["cross_check"]
            self.assertTrue(cc["provable"], key)
            self.assertEqual(cc["bone_ff_skin_ff"], 0, key)
            self.assertEqual(cc["bone_valid_skin_ff"], 0, key)
            self.assertEqual(
                cc["bone_ff_skin_valid"] + cc["bone_valid_skin_valid"],
                cc["vertex_count"], key)

    def test_bandit_mesh_bones_all_used(self):
        for key in ("bandit_part1", "bandit_part2"):
            c = self.fixture["samples"][key]["census"]
            self.assertEqual(c["unused_bones"], [], key)


if __name__ == "__main__":
    unittest.main()
