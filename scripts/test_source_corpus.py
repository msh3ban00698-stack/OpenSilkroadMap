#!/usr/bin/env python3
"""Source-corpus indexer integrity tests (Phase 29 source-parity).

Verifies the emitted SOURCE_CORPUS_MANIFEST/STATS/INVENTORY reconcile exactly
against the verified PK2 table enumeration, that per-file statuses sum to the
indexed total, and that the known-missing protocol tables are recorded.

Runs in a bare checkout with no Android SDK and no network.
"""
import json
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import pk2_table  # noqa: E402

REPO = BASE
PK2_DIR = "/tmp/opencode/pk2raw"
REAL_PK2 = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")

PRESENT_STATUSES = {"PROVEN", "PARTIAL", "STUB", "UNKNOWN", "UNREADABLE", "DEAD", "TEXT"}


class TestSourceCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "SOURCE_CORPUS_MANIFEST.json"), encoding="utf-8") as fh:
            cls.rows = json.load(fh)
        with open(os.path.join(REPO, "SOURCE_CORPUS_STATS.json"), encoding="utf-8") as fh:
            cls.stats = json.load(fh)

    def test_pk2_row_count_matches_enumeration(self):
        expected = {}
        for name in REAL_PK2:
            path = os.path.join(PK2_DIR, name)
            if os.path.isfile(path):
                files, _ = pk2_table.inventory(path)
                expected[name] = len(files)
        got = {}
        for r in self.rows:
            if r["source"] == "pk2":
                got[r["archive"]] = got.get(r["archive"], 0) + 1
        self.assertEqual(expected, got)
        self.assertEqual(sum(expected.values()), 119631)

    def test_reconciliation_sums(self):
        rec = self.stats["reconciliation"]
        present = sum(rec.get(s, 0) for s in PRESENT_STATUSES)
        self.assertEqual(present, len(self.rows))
        self.assertEqual(rec.get("MISSING", 0), 1)

    def test_by_source_sums(self):
        self.assertEqual(sum(self.stats["by_source"].values()), len(self.rows))

    def test_known_missing_recorded(self):
        names = {m["name"] for m in self.stats["known_missing"]}
        self.assertIn("RecMsg.dat", names)
        self.assertNotIn("SendMsg.dat", names)

    def test_no_unknown_status_leak(self):
        allowed = PRESENT_STATUSES | {"MISSING"}
        for r in self.rows:
            self.assertIn(r["status"], allowed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
