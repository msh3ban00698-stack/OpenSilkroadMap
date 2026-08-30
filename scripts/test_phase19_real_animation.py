#!/usr/bin/env python3
"""Phase 19 Part K real animation tests (bandit walk/stand01).

Proves the decoded BAN pose genuinely moves the REAL bandit skeleton away
from its bind pose at deterministic timestamps, and that rendering is
deterministic (byte-identical snapshots for identical inputs).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animation_pose as AP  # noqa: E402
import bsk_decoder as BSK  # noqa: E402
import render_npc_animation as R  # noqa: E402
import skeleton as SK  # noqa: E402

TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata",
                  "formats")


def _load(name, sub):
    with open(os.path.join(TD, sub, name), "rb") as fh:
        return fh.read()


class TestRealAnimation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bones = BSK.parse_bsk(_load("bandit.bsk", "bsk_samples"))["bones"]
        cls.walk = _load("bandit_walk.ban", "ban_phase18_samples")
        cls.stand = _load("bandit_stand01.ban", "ban_phase18_samples")

    def _world(self, ban, t):
        pose = AP.evaluate_pose(ban, t, self.bones)
        return AP.chain_world(pose, self.bones)[1]

    def test_walk_moves_away_from_bind(self):
        _, bind = SK.bind_world(self.bones)
        for t in (0, 700, 1333):
            w = self._world(self.walk, t)
            dev = max(
                sum((w[i][k] - bind[i][k]) ** 2 for k in range(3)) ** 0.5
                for i in range(len(self.bones)))
            self.assertGreater(dev, 0.01, t)

    def test_stand_moves_away_from_bind(self):
        _, bind = SK.bind_world(self.bones)
        for t in (0, 1000, 2000):
            w = self._world(self.stand, t)
            dev = max(
                sum((w[i][k] - bind[i][k]) ** 2 for k in range(3)) ** 0.5
                for i in range(len(self.bones)))
            self.assertGreater(dev, 0.01, t)

    def test_walk_different_poses_across_time(self):
        w0 = self._world(self.walk, 0)
        w1 = self._world(self.walk, 700)
        w2 = self._world(self.walk, 1333)
        self.assertNotEqual(w0, w1)
        self.assertNotEqual(w1, w2)
        # loop: t=1333 wraps to t=0 (source first/last keyframes differ by
        # float32 rounding, Part G proven within 2e-3)
        for i in range(len(self.bones)):
            for k in range(3):
                self.assertAlmostEqual(w0[i][k], w2[i][k], delta=2e-3)

    def test_render_deterministic(self):
        r1 = R.render_npc_pose(self.bones, self.walk, 700)
        r2 = R.render_npc_pose(self.bones, self.walk, 700)
        self.assertEqual(r1["svg"], r2["svg"])
        self.assertEqual(r1["sha256"], r2["sha256"])
        self.assertIn("<svg", r1["svg"])
        self.assertEqual(len(r1["bone_world_pos"]), len(self.bones))

    def test_render_has_bone_count(self):
        svg = R.render_npc_pose(self.bones, self.walk, 700)["svg"]
        self.assertEqual(svg.count("<circle"), len(self.bones))
        self.assertEqual(svg.count("<line"), len(self.bones) - 1)

    def test_front_and_side_differ(self):
        front = R.render_npc_pose(self.bones, self.walk, 700, view="front")
        side = R.render_npc_pose(self.bones, self.walk, 700, view="side")
        self.assertNotEqual(front["svg"], side["svg"])


if __name__ == "__main__":
    unittest.main()
