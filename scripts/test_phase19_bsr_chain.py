#!/usr/bin/env python3
"""Phase 19 Part E BSR cross-reference chain tests (hermetic).

Proves the bandit dependency chain edges from original committed bytes:
  BSR -> bmt/bms/ban/bsk -> skeleton bones -> skinned meshes
Every edge carries evidence + status PROVEN (or UNKNOWN when unprovable).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as BMS  # noqa: E402
import bsk_decoder as BSK  # noqa: E402
import bsr_decoder as BSR  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


class TestBanditBsrChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bsr = BSR.parse_bsr_references(
            open(os.path.join(HERE, "testdata", "formats", "bsr_samples",
                              "bandit.bsr"), "rb").read())
        cls.bsk = BSK.parse_bsk(
            open(os.path.join(HERE, "testdata", "formats", "bsk_samples",
                              "bandit.bsk"), "rb").read())
        cls.bms_by_path = {}
        for part in ("bandit_sword", "bandit_part1", "bandit_part2"):
            with open(os.path.join(HERE, "testdata", "formats",
                                   "bms_weights_samples", part + ".bms"),
                      "rb") as fh:
                raw = fh.read()
            cls.bms_by_path[part] = BMS.parse_bms(raw)
        cls.edges = BSR.proven_edges(
            cls.bsr, cls.bsk,
            {"bms:" + p: b for p, b in cls.bms_by_path.items()})

    def _edge(self, src_part, tgt_part):
        return [e for e in self.edges
                if src_part in e["source"] and tgt_part in e["target"]]

    def test_bsr_is_character(self):
        self.assertTrue(self.bsr["is_character"])
        self.assertTrue(self.bsr["group_order_ok"])

    def test_bsr_to_bsk_edge(self):
        skel = self.bsr["skeleton"][0]
        edges = [e for e in self.edges
                 if e["target"] == skel and e["source"] == skel]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["status"], "PROVEN")

    def test_bsr_to_three_meshes(self):
        self.assertEqual(len(self.bsr["meshes"]), 3)
        for m in self.bsr["meshes"]:
            self.assertIn("bandit", m)
        edges = [e for e in self.edges if "bms" in e["source"] or ".bms" in e["target"]]
        self.assertTrue(edges)

    def test_bsr_to_sixteen_animations(self):
        self.assertEqual(len(self.bsr["animations"]), 16)
        ban_edges = [e for e in self.edges if e["target"].endswith(".ban")]
        self.assertEqual(len(ban_edges), 16)
        for e in ban_edges:
            self.assertEqual(e["status"], "PROVEN")

    def test_bsk_to_bones_edge(self):
        skel = self.bsr["skeleton"][0]
        edges = [e for e in self.edges
                 if e["source"] == skel and e["target"].startswith("bones[")]
        self.assertEqual(len(edges), 1)
        self.assertIn("35", edges[0]["target"])
        self.assertEqual(edges[0]["status"], "PROVEN")

    def test_mesh_bones_subset_of_skeleton(self):
        skel = self.bsr["skeleton"][0]
        skel_names = {b["name"] for b in self.bsk["bones"]}
        for part, bms in self.bms_by_path.items():
            mesh_names = bms["bones"]["bone_names"]
            self.assertTrue(set(mesh_names) <= skel_names, part)
            edges = [e for e in self.edges
                     if e["source"].startswith("bms:" + part)
                     and e["target"] == skel]
            self.assertEqual(len(edges), 1, part)
            self.assertEqual(edges[0]["status"], "PROVEN", part)

    def test_all_edges_have_evidence(self):
        for e in self.edges:
            self.assertTrue(e["evidence"], e)
            self.assertIn(e["status"], ("PROVEN", "UNKNOWN"))


if __name__ == "__main__":
    unittest.main()
