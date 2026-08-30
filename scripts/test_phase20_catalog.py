#!/usr/bin/env python3
"""Phase 20 Part B: catalog enumeration (hermetic)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_character_catalog as BCC  # noqa: E402


class TestEnumerateSpawns(unittest.TestCase):
    def test_refid_to_models(self):
        chardata = {"1949": ["mob\\china\\bandit.bsr"],
                    "26738": ["mob\\sd\\seth.bsr", "mob\\sd\\seth_t2.bsr"]}
        spawn_rows = [["1949", "1", "0", "0", "0"],
                      ["26738", "2", "0", "0", "0"],
                      ["1949", "3", "0", "0", "0"]]
        spawn_refids, refid_models, model_counts = BCC.enumerate_spawns(
            chardata, spawn_rows)
        self.assertEqual(spawn_refids, {"1949", "26738"})
        self.assertEqual(refid_models["1949"], ["mob\\china\\bandit.bsr"])
        self.assertEqual(model_counts["mob\\china\\bandit.bsr"], 2)

    def test_refid_without_model_ignored(self):
        spawn_refids, refid_models, model_counts = BCC.enumerate_spawns(
            {"1949": ["mob\\china\\bandit.bsr"]},
            [["9999", "1", "0", "0", "0"]])
        self.assertEqual(spawn_refids, {"9999"})
        self.assertEqual(refid_models, {})


if __name__ == "__main__":
    unittest.main()
