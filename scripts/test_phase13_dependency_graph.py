#!/usr/bin/env python3
"""Phase 13 Part N: asset dependency graph validation.

Checks the committed ANDROID_ASSET_DEPENDENCY_GRAPH.json for structural
soundness and that it only contains edges whose status/evidence are consistent
with the Phase 12/13 verification record. Does not invent edges; asserts the
graph is reproducible from DATA_REFERENCE_GRAPH.json + the asset-edge table.
"""
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import build_asset_dependency_graph as bag  # noqa: E402

REPO = SCRIPTS.parent
GRAPH = REPO / "ANDROID_ASSET_DEPENDENCY_GRAPH.json"

ALLOWED_STATUS = {"VERIFIED", "PARTIAL"}


class DependencyGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(GRAPH.read_text(encoding="utf-8"))

    def test_graph_has_edges_and_description(self):
        self.assertIn("edges", self.doc)
        self.assertGreaterEqual(len(self.doc["edges"]), 15)
        self.assertTrue(self.doc["description"])

    def test_edge_schema(self):
        for e in self.doc["edges"]:
            for side in ("from", "to"):
                self.assertIn("kind", e[side])
                self.assertIn("role", e[side])
            self.assertIn("status", e)
            self.assertIn("evidence", e)
            self.assertIn("relationship", e)
            self.assertIn(e["status"], ALLOWED_STATUS, e)

    def test_verified_edges_have_non_empty_evidence(self):
        for e in self.doc["edges"]:
            if e["status"] == "VERIFIED":
                self.assertTrue(e["evidence"].strip(), e)

    def test_asset_chain_edges_present(self):
        kinds = {(e["from"]["kind"], e["to"]["kind"]) for e in self.doc["edges"]}
        self.assertIn((".bsr", ".bmt"), kinds)
        self.assertIn((".bsr", ".bms"), kinds)
        self.assertIn((".bmt", ".ddj"), kinds)
        self.assertIn((".o2", "object.ifo"), kinds)
        self.assertIn(("characterdata_*.txt", ".bsr"), kinds)

    def test_textdata_npcpos_edges_are_verified(self):
        npc_edges = [e for e in self.doc["edges"]
                     if e["from"]["kind"] == "npcpos.tsv"]
        self.assertGreaterEqual(len(npc_edges), 2)
        for e in npc_edges:
            self.assertEqual(e["status"], "VERIFIED", e)

    def test_reproducible_from_builder(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = bag.build(Path(tmp) / "graph.json")
            self.assertEqual(rebuilt["edges"], self.doc["edges"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
