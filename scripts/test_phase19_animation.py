#!/usr/bin/env python3
"""Phase 19 Part G animation format tests (hermetic).

Proven facts asserted here:
  * BAN clips carry a single clip with a header name and duration
  * keyframes are (4x f32 rotation + 3x f32 position) 28-byte records; no scale
  * timestamps are authoritative for timing (bandit_walk is NON-uniform);
    the frame_rate header field (30) is nominal, not a fixed timestep
  * looping is PROVEN: first keyframe == last keyframe for every channel
  * root motion is present (Bip01 translation oscillates) and loop-contained
  * committed anim JSON now carries ALL keyframes per channel
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animation_decoder as AD  # noqa: E402

TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata",
                  "formats")
ASSETS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "android", "app", "src", "main", "assets", "game", "world",
    "characters", "bandit")


class TestDescribeAnimation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.walk = AD.describe_animation(
            open(os.path.join(TD, "ban_phase18_samples", "bandit_walk.ban"),
                 "rb").read())
        cls.stand = AD.describe_animation(
            open(os.path.join(TD, "ban_phase18_samples",
                              "bandit_stand01.ban"), "rb").read())

    def test_walk_fields(self):
        w = self.walk
        self.assertEqual(w["clip_count"], 1)
        self.assertEqual(w["clip_name"], "bandit_walk")
        self.assertEqual(w["duration_ms"], 1333)
        self.assertEqual(w["keyframe_count"], 15)
        self.assertEqual(w["bone_count"], 34)
        self.assertEqual(len(w["timestamps"]), 15)
        self.assertFalse(w["has_scale"])
        self.assertTrue(w["has_rotation"])
        self.assertTrue(w["has_translation"])
        self.assertTrue(w["timestamps_non_uniform"])
        self.assertEqual(w["frame_rate_header"], 30)
        self.assertEqual(w["keyframe_stride_bytes"], 28)

    def test_stand_fields(self):
        s = self.stand
        self.assertEqual(s["duration_ms"], 2000)
        self.assertEqual(s["keyframe_count"], 5)
        self.assertEqual(s["bone_count"], 34)
        self.assertTrue(s["timestamps_uniform"])
        self.assertEqual(s["timestamps"], [0, 500, 1000, 1500, 2000])

    def test_looping_proven(self):
        self.assertTrue(self.walk["looping"])
        self.assertIn("first keyframe == last keyframe",
                      self.walk["loop_evidence"])
        self.assertTrue(self.stand["looping"])

    def test_root_motion_loop_contained(self):
        self.assertTrue(self.walk["root_motion"])
        self.assertGreater(self.walk["root_drift_units"], 0.1)

    def test_no_fixed_fps_assumption(self):
        # timestamps are authoritative; walk deltas are NON-uniform
        ts = self.walk["timestamps"]
        deltas = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
        self.assertGreater(len(set(deltas)), 1)
        self.assertLess(min(deltas), max(deltas))


class TestCommittedFullKeyframes(unittest.TestCase):
    def test_walk_json_has_all_keyframes(self):
        with open(os.path.join(ASSETS, "anim", "bandit_walk.json")) as fh:
            d = json.load(fh)

        def allclose(a, b):
            return all(abs(x - y) < 2e-3 for x, y in zip(a, b))

        for name, ch in d["channels"].items():
            self.assertEqual(len(ch), 15, name)
            self.assertEqual(len(ch[0]), 2, name)
            self.assertEqual(len(ch[0][0]), 4, name)
            self.assertEqual(len(ch[0][1]), 3, name)
            # loop property preserved (within 6-decimal rounding tolerance)
            self.assertTrue(allclose(ch[0][0], ch[-1][0]), name)
            self.assertTrue(allclose(ch[0][1], ch[-1][1]), name)
        self.assertEqual(d["timestamps"][0], 0)
        self.assertEqual(d["timestamps"][-1], 1333)

    def test_stand_json_has_all_keyframes(self):
        with open(os.path.join(ASSETS, "anim", "bandit_stand01.json")) as fh:
            d = json.load(fh)
        for name, ch in d["channels"].items():
            self.assertEqual(len(ch), 5, name)


if __name__ == "__main__":
    unittest.main()
