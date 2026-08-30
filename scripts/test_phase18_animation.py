#!/usr/bin/env python3
"""Phase 18 animation pose tests (hermetic against committed fixtures)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animation_pose as AP  # noqa: E402
import skeleton as SK  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "ban_phase18.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "ban_phase18_samples")
BSK_FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsk_phase18.json")


def _bandit_bones():
    with open(BSK_FIXTURE) as fh:
        f = json.load(fh)
    return f["samples"]["bandit"]["bones"]


class TestBanFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.load(open(FIXTURE))

    def test_raw_match_sha256(self):
        for key, rec in self.fixture["samples"].items():
            raw = open(os.path.join(SAMPLES_DIR, key + ".ban"), "rb").read()
            self.assertEqual(len(raw), rec["size"], key)
            self.assertEqual(
                __import__("hashlib").sha256(raw).hexdigest(),
                rec["sha256"], key)

    def test_durations(self):
        self.assertEqual(
            self.fixture["samples"]["bandit_stand01"]["duration_ms"], 2000)
        self.assertEqual(
            self.fixture["samples"]["bandit_walk"]["duration_ms"], 1333)

    def test_channels_map_to_skeleton(self):
        bones = _bandit_bones()
        skel = {b["name"] for b in bones}
        for rec in self.fixture["samples"].values():
            for name in rec["channel_names"]:
                self.assertIn(name, skel, name)

    def test_keyframe_counts_consistent(self):
        for rec in self.fixture["samples"].values():
            n = len(rec["timestamps"])
            for count in rec["channel_keyframe_counts"].values():
                self.assertEqual(count, n)


class TestEvaluatePose(unittest.TestCase):
    def setUp(self):
        self.bones = _bandit_bones()
        self.raw = {
            k: open(os.path.join(SAMPLES_DIR, k + ".ban"), "rb").read()
            for k in ("bandit_stand01", "bandit_walk")
        }

    def test_animated_channels_are_unit_quats(self):
        pose = AP.evaluate_pose(self.raw["bandit_stand01"], 500.0, self.bones)
        for i, b in enumerate(self.bones):
            q, _ = pose[i]
            norm = (q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2) ** 0.5
            self.assertAlmostEqual(norm, 1.0, places=4, msg=b["name"])

    def test_pelvis_channel_equals_bind_and_stays_constant(self):
        # Proven: Bip01 Pelvis channel == bind rot_parent/tr_parent for the
        # whole stand01 clip (idle pose keeps pelvis at bind).
        f = json.load(open(FIXTURE))
        chans = f["samples"]["bandit_stand01"]["channel_names"]
        self.assertIn("Bip01 Pelvis", chans)
        idx = [b["name"] for b in self.bones].index("Bip01 Pelvis")
        for t in (0.0, 500.0, 1000.0, 2000.0):
            pose = AP.evaluate_pose(self.raw["bandit_stand01"], t, self.bones)
            q, p = pose[idx]
            for k in range(4):
                self.assertAlmostEqual(q[k], self.bones[idx]["rot_parent"][k],
                                       places=3)
            for k in range(3):
                self.assertAlmostEqual(p[k], self.bones[idx]["tr_parent"][k],
                                       places=2)

    def _channel_names(self, key):
        f = json.load(open(FIXTURE))
        return set(f["samples"][key]["channel_names"])

    def test_pose_deterministic(self):
        for key in ("bandit_stand01", "bandit_walk"):
            p1 = AP.evaluate_pose(self.raw[key], 500.0, self.bones)
            p2 = AP.evaluate_pose(self.raw[key], 500.0, self.bones)
            for i in range(len(self.bones)):
                for k in range(4):
                    self.assertAlmostEqual(p1[i][0][k], p2[i][0][k], places=9)
                for k in range(3):
                    self.assertAlmostEqual(p1[i][1][k], p2[i][1][k], places=9)

    def test_unanimated_bones_keep_bind(self):
        pose = AP.evaluate_pose(self.raw["bandit_stand01"], 1000.0, self.bones)
        for i, b in enumerate(self.bones):
            if b["name"] not in self._channel_names("bandit_stand01"):
                q, p = pose[i]
                self.assertEqual(q, b["rot_parent"])
                self.assertEqual(p, b["tr_parent"])

    def test_world_chain_stays_bounded(self):
        pose = AP.evaluate_pose(self.raw["bandit_walk"], 700.0, self.bones)
        wrot, wpos = AP.chain_world(pose, self.bones)
        for wp in wpos:
            for c in wp:
                self.assertLess(abs(c), 100.0)

    def test_interpolation_midpoint(self):
        # The stand01 clip is a loop (frame0 == frameN). Midpoint quat must be
        # a valid unit quaternion and lie between the endpoints (dot > 0.9).
        pose0 = AP.evaluate_pose(self.raw["bandit_stand01"], 0.0, self.bones)
        poseM = AP.evaluate_pose(self.raw["bandit_stand01"], 1000.0, self.bones)
        poseN = AP.evaluate_pose(self.raw["bandit_stand01"], 2000.0, self.bones)
        idx = [b["name"] for b in self.bones].index("Bip01 Spine")
        q0, qN = pose0[idx][0], poseN[idx][0]
        qm = poseM[idx][0]
        self.assertAlmostEqual(sum(x * x for x in qm), 1.0, places=4)
        dot0 = abs(sum(a * b for a, b in zip(q0, qm)))
        dotN = abs(sum(a * b for a, b in zip(qN, qm)))
        self.assertGreater(dot0, 0.9)
        self.assertGreater(dotN, 0.9)


if __name__ == "__main__":
    unittest.main()
