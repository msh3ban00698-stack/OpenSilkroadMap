#!/usr/bin/env python3
"""Phase 19 Part I skinned-mesh bind-pose validation tests.

Proves that the real bandit meshes, skinned with the proven skin block
(Part C) and the proven BSK transform semantics (Part B: origin=bind world,
local=inverse-bind), reproduce their stored rest vertices at the bind pose
within a tight tolerance. A non-distorting bind pose is the signature of a
correct linear-blend skinning setup, so this cross-checks indices, weights,
bone mapping, and transform semantics in a single reproduction.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as M  # noqa: E402
import bms_to_asset as BA  # noqa: E402
import bsk_decoder as B  # noqa: E402

TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata",
                  "formats")


class TestSkinnedMeshValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(TD, "bsk_samples", "bandit.bsk"), "rb") as fh:
            cls.skeleton = B.parse_bsk(fh.read())["bones"]

    def _validate(self, part):
        with open(os.path.join(TD, "bms_weights_samples", part + ".bms"),
                  "rb") as fh:
            parsed = M.parse_bms(fh.read())
        pos = [v["position"] for v in parsed["vertices"]]
        return BA.validate_skinned_mesh(
            parsed["skin"], parsed["bones"]["bone_names"], self.skeleton, pos)

    def test_bandit_sword(self):
        r = self._validate("bandit_sword")
        self.assertEqual(r["vertex_count"], 76)
        self.assertEqual(r["skin_record_count"], 76)
        self.assertTrue(r["every_vertex_exists"], r)
        self.assertTrue(r["every_bone_exists"], r)
        self.assertTrue(r["indices_valid"], r)
        self.assertTrue(r["weights_valid"], r)
        self.assertTrue(r["bind_pose_no_distortion"], r)
        self.assertLess(r["max_deform"], 0.01)

    def test_bandit_part1(self):
        r = self._validate("bandit_part1")
        self.assertEqual(r["vertex_count"], 214)
        self.assertTrue(r["every_vertex_exists"], r)
        self.assertTrue(r["every_bone_exists"], r)
        self.assertTrue(r["indices_valid"], r)
        self.assertTrue(r["weights_valid"], r)
        self.assertTrue(r["bind_pose_no_distortion"], r)
        self.assertLess(r["max_deform"], 0.01)

    def test_bandit_part2(self):
        r = self._validate("bandit_part2")
        self.assertEqual(r["vertex_count"], 556)
        self.assertTrue(r["every_vertex_exists"], r)
        self.assertTrue(r["every_bone_exists"], r)
        self.assertTrue(r["indices_valid"], r)
        self.assertTrue(r["weights_valid"], r)
        self.assertTrue(r["bind_pose_no_distortion"], r)
        self.assertLess(r["max_deform"], 0.01)

    def test_every_mesh_bone_resolves(self):
        for part in ("bandit_sword", "bandit_part1", "bandit_part2"):
            with open(os.path.join(TD, "bms_weights_samples", part + ".bms"),
                      "rb") as fh:
                parsed = M.parse_bms(fh.read())
            skel = {b["name"] for b in self.skeleton}
            for name in parsed["bones"]["bone_names"]:
                self.assertIn(name, skel, (part, name))

    def test_two_influence_bandit_part2(self):
        # Part 2 carries two-influence vertices; the blend uses both and
        # still reproduces the rest vertex (no single-bone shortcut).
        with open(os.path.join(TD, "bms_weights_samples", "bandit_part2.bms"),
                  "rb") as fh:
            parsed = M.parse_bms(fh.read())
        self.assertGreater(parsed["skin"]["two_influence"], 0)
        r = self._validate("bandit_part2")
        self.assertTrue(r["bind_pose_no_distortion"], r)


if __name__ == "__main__":
    unittest.main()
