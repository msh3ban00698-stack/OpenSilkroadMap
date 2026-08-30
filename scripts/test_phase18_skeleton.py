#!/usr/bin/env python3
"""Phase 18 skeleton bind-pose + mesh bone mapping tests (hermetic)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skeleton as SK  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "bsk_phase18.json")
SKIN_FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "testdata", "formats", "bms_skin_phase18.json")


def _bandit_bones():
    with open(FIXTURE) as fh:
        f = json.load(fh)
    return f["samples"]["bandit"]["bones"]


class TestHierarchy(unittest.TestCase):
    def setUp(self):
        self.bones = _bandit_bones()

    def test_parents_acyclic_single_root(self):
        parents = SK.bone_parents(self.bones)
        roots = [i for i, p in enumerate(parents) if p == -1]
        self.assertEqual(roots, [0])
        self.assertEqual(parents[0], -1)
        # every non-root has a parent
        for i in range(1, len(parents)):
            self.assertGreaterEqual(parents[i], 0)

    def test_children_match_parent_links(self):
        parents = SK.bone_parents(self.bones)
        for i, b in enumerate(self.bones):
            for c in b["children"]:
                ci = {b["name"]: j for j, b in enumerate(self.bones)}[c]
                self.assertEqual(parents[ci], i)

    def test_quaternions_unit(self):
        for b in self.bones:
            for key in ("rot_parent", "rot_origin", "rot_local"):
                self.assertTrue(SK.quat_is_unit(b[key]),
                                "%s %s" % (b["name"], key))

    def test_parent_before_child_in_list(self):
        parents = SK.bone_parents(self.bones)
        for i, p in enumerate(parents):
            if p != -1:
                self.assertLess(p, i)


class TestBindWorld(unittest.TestCase):
    def setUp(self):
        self.bones = _bandit_bones()
        self.rot, self.pos = SK.bind_world(self.bones)
        self.idx = {b["name"]: i for i, b in enumerate(self.bones)}

    def test_pose_plausible(self):
        # Proven: toes near mesh ground (y~0.02 vs mesh ground y~0.03),
        # pelvis mid-body, head above pelvis, hands at arm extremity.
        pos = self.pos
        toes = pos[self.idx["Bip01 L Toe0"]]
        self.assertLess(abs(toes[1] - 0.02), 0.5)
        pelvis = pos[self.idx["Bip01 Pelvis"]]
        self.assertGreater(pelvis[1], 5.0)
        head = pos[self.idx["Bip01 Head"]]
        self.assertGreater(head[1], pelvis[1])
        self.assertLess(abs(head[0]), 0.5)
        hand = pos[self.idx["Bip01 R Hand"]]
        self.assertGreater(abs(hand[0]), 5.0)
        self.assertLess(abs(abs(hand[0]) - 8.2), 2.0)

    def test_deterministic(self):
        r2, p2 = SK.bind_world(self.bones)
        for i in range(len(self.bones)):
            for k in range(4):
                self.assertAlmostEqual(self.rot[i][k], r2[i][k], places=6)
            for k in range(3):
                self.assertAlmostEqual(self.pos[i][k], p2[i][k], places=6)

    def test_left_right_symmetric(self):
        pos = self.pos
        li = self.idx["Bip01 L Hand"]
        ri = self.idx["Bip01 R Hand"]
        self.assertAlmostEqual(pos[li][0], -pos[ri][0], places=4)
        self.assertAlmostEqual(pos[li][1], pos[ri][1], places=4)


class TestMeshBoneMapping(unittest.TestCase):
    def test_bandit_mesh_bones_subset_of_skel(self):
        with open(SKIN_FIXTURE) as fh:
            skin = json.load(fh)
        bones = _bandit_bones()
        skel_names = [b["name"] for b in bones]
        for key in ("bandit_part1", "bandit_part2", "bandit_sword"):
            mesh_names = skin["samples"][key]["bone_names"]
            missing = SK.validate_mesh_bones(skel_names, mesh_names)
            self.assertEqual(missing, [], key)


class TestPlayerSkeleton(unittest.TestCase):
    def test_chinaman_skel_hierarchy(self):
        with open(FIXTURE) as fh:
            f = json.load(fh)
        bones = f["samples"]["chinaman_skel"]["bones"]
        parents = SK.bone_parents(bones)
        self.assertEqual(len(bones), 38)
        self.assertEqual(sum(1 for p in parents if p == -1), 1)
        rot, pos = SK.bind_world(bones)
        for i, b in enumerate(bones):
            self.assertTrue(SK.quat_is_unit(b["rot_parent"]), b["name"])


if __name__ == "__main__":
    unittest.main()
