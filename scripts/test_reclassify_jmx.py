#!/usr/bin/env python3
"""Tests for the JMX-family reclassification mapping (scripts/reclassify_jmx.py).

Locks the extension -> status mapping and the invariant that reclassification
only upgrades UNKNOWN records and never disturbs STUB/DEAD/MISSING.
"""
import json
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import reclassify_jmx  # noqa: E402

REPO = BASE
MANIFEST = os.path.join(REPO, "SOURCE_CORPUS_MANIFEST.json")


class TestReclassifyJmx(unittest.TestCase):
    def test_mapping_values_valid(self):
        for ext, status in reclassify_jmx.EXT_STATUS.items():
            self.assertTrue(ext.startswith("."), f"non-extension key {ext}")
            self.assertIn(status, {"PROVEN", "PARTIAL"}, f"{ext} -> {status}")

    def test_mapping_extensions_present(self):
        with open(MANIFEST, encoding="utf-8") as fh:
            rows = json.load(fh)
        present = {r["extension"] for r in rows}
        for ext in reclassify_jmx.EXT_STATUS:
            self.assertIn(ext, present, f"mapped extension {ext} absent from manifest")

    def test_reclassify_preserves_stub_dead(self):
        rows = [
            {"extension": ".ddj", "status": "UNKNOWN", "internal_path": "a"},
            {"extension": ".bsk", "status": "STUB", "internal_path": "b"},
            {"extension": ".tmp", "status": "DEAD", "internal_path": "c"},
            {"extension": ".efp", "status": "UNKNOWN", "internal_path": "d"},
        ]
        reclassify_jmx.reclassify(rows)
        by_path = {r["internal_path"]: r["status"] for r in rows}
        self.assertEqual(by_path["a"], "PROVEN")
        self.assertEqual(by_path["b"], "STUB")
        self.assertEqual(by_path["c"], "DEAD")
        self.assertEqual(by_path["d"], "PARTIAL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
