#!/usr/bin/env python3
"""Phase 19 Part H pose-evaluation tests (hermetic).

Proves deterministic pose evaluation over original bandit BAN clips:
  * first keyframe (t=0), exact intermediate keyframes, exact final keyframe
  * interpolated mid-keyframe samples
  * exact keyframe boundaries (t just before/after a timestamp)
  * loop boundary: t == duration gives the same pose as t == 0
    (last keyframe duplicates the first -- proven in Part G)
  * identical inputs produce identical outputs (determinism)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animation_pose as AP  # noqa: E402
import bsk_decoder as B  # noqa: E402

TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata",
                  "formats")


class TestPoseEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(TD, "bsk_samples", "bandit.bsk"), "rb") as fh:
            cls.skeleton = B.parse_bsk(fh.read())
        cls.bones = [{
            "name": b["name"], "parent": b["parent"], "children": b["children"],
            "rot_parent": b["rot_parent"], "tr_parent": b["tr_parent"],
        } for b in cls.skeleton["bones"]]

    def _walk(self):
        with open(os.path.join(TD, "ban_phase18_samples",
                               "bandit_walk.ban"), "rb") as fh:
            return fh.read()

    def _pose(self, raw, t):
        return AP.evaluate_pose(raw, t, self.bones)

    def test_first_keyframe_matches_raw(self):
        raw = self._walk()
        pose = self._pose(raw, 0)
        anim = AP.load_keyframes(raw)
        idx = {b["name"]: i for i, b in enumerate(self.skeleton["bones"])}
        for name, recs in anim["channels"].items():
            q, p = recs[0]
            i = idx[name]
            self.assertEqual(pose[i][0], q, name)
            self.assertEqual(pose[i][1], p, name)

    def test_exact_keyframes(self):
        raw = self._walk()
        anim = AP.load_keyframes(raw)
        # walk timestamps: 0, 33, 133, 266, 333, 400, ...
        for t in (33, 133, 266, 333, 400, 533, 566, 666, 800, 933, 1000, 1066,
                  1200, 1333):
            pose = self._pose(raw, t)
            at = anim["timestamps"].index(t)
            for name, recs in anim["channels"].items():
                i = [b["name"] for b in self.skeleton["bones"]].index(name)
                q, p = recs[at]
                self.assertEqual(pose[i][0], q, (name, t))
                self.assertEqual(pose[i][1], p, (name, t))

    def test_interpolated_mid(self):
        raw = self._walk()
        anim = AP.load_keyframes(raw)
        pose = self._pose(raw, 700)
        # 700 sits between timestamps 666 (idx 8) and 800 (idx 9)
        recs = anim["channels"]["Bip01 L Thigh"]
        q700, p700 = pose[[b["name"] for b in self.bones].index("Bip01 L Thigh")]
        self.assertTrue(all(abs(v) <= 1.0 for v in q700))
        self.assertNotEqual(q700, recs[8][0])
        self.assertNotEqual(q700, recs[9][0])
        # linear blend fraction between the bracketing translations
        p8, p9 = recs[8][1], recs[9][1]
        f = (700 - 666) / (800 - 666)
        expect = [p8[k] + f * (p9[k] - p8[k]) for k in range(3)]
        self.assertTrue(all(abs(a - b) < 1e-3 for a, b in zip(p700, expect)))

    def test_boundary_flip(self):
        raw = self._walk()
        i = [b["name"] for b in self.bones].index("Bip01 L Thigh")
        # just before (interpolated) vs exactly at timestamp 1000
        pose_b = self._pose(raw, 1000 - 1)
        pose_a = self._pose(raw, 1000)
        self.assertNotEqual(pose_b[i][0], pose_a[i][0])
        # and exactly at 1000 equals the raw keyframe
        recs = AP.load_keyframes(raw)["channels"]["Bip01 L Thigh"]
        self.assertEqual(pose_a[i][0], recs[11][0])

    def test_loop_boundary_t_equals_duration_is_t0(self):
        raw = self._walk()
        anim = AP.load_keyframes(raw)
        dur = anim["duration_ms"]
        self.assertEqual(anim["timestamps"][-1], dur)
        pose_loop = self._pose(raw, dur)
        pose_zero = self._pose(raw, 0)

        def close(a, b):
            return all(abs(x - y) < 2e-3 for x, y in zip(a, b))

        for i in range(len(self.bones)):
            self.assertTrue(close(pose_loop[i][0], pose_zero[i][0]), i)
            self.assertTrue(close(pose_loop[i][1], pose_zero[i][1]), i)

    def test_determinism(self):
        raw = self._walk()
        a = self._pose(raw, 700)
        b = self._pose(raw, 700)
        self.assertEqual(a, b)
        self.assertEqual(self._pose(raw, 0), self._pose(raw, 0))

    def test_bind_pose_rest_stays_for_absent_bones(self):
        # bones absent from the walk clip fall back to their bind transform
        raw = self._walk()
        anim = AP.load_keyframes(raw)
        bones_absent = [b["name"] for b in self.bones
                        if b["name"] not in anim["channels"]]
        self.assertTrue(bones_absent)
        pose = self._pose(raw, 0)
        idx = {b["name"]: i for i, b in enumerate(self.bones)}
        for name in bones_absent:
            b = self.bones[idx[name]]
            self.assertEqual(pose[idx[name]][0], list(b["rot_parent"]), name)
            self.assertEqual(pose[idx[name]][1], list(b["tr_parent"]), name)


if __name__ == "__main__":
    unittest.main()
