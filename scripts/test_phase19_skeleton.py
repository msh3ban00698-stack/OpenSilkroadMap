#!/usr/bin/env python3
"""Phase 19 Part D skeleton-reconstruction tests (hermetic).

Proven facts asserted here (all 5 committed raw skeletons):
  * the parent-name graph is a rooted tree: single root, every parent exists,
    zero cycles, max_depth < bone_count
  * the BSK layout has NO scale fields (21 floats = rot_parent/tr_parent/
    rot_origin/tr_origin/rot_local/tr_local only)
  * chained world positions (scale behavior) land in plausible bind geometry
    (feet y ~ 0, pelvis y > 6) for the bandit
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsk_decoder as B  # noqa: E402
import skeleton as SK  # noqa: E402

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsk_samples")

BONE_COUNTS = {
    "chinaman_skel": 38,
    "bandit": 35,
    "islamman": 43,
    "blackrobber": 35,
    "horse1": 31,
}


class TestHierarchy(unittest.TestCase):
    def _bones(self, key):
        with open(os.path.join(SAMPLES_DIR, key + ".bsk"), "rb") as fh:
            raw = fh.read()
        r = B.parse_bsk(raw)
        self.assertTrue(r["exact"], key)
        return r["bones"]

    def test_all_skeletons_are_rooted_trees(self):
        for key in BONE_COUNTS:
            v = SK.verify_hierarchy(self._bones(key))
            self.assertEqual(v["bone_count"], BONE_COUNTS[key], key)
            self.assertTrue(v["is_tree"], key + " " + str(v))
            self.assertTrue(v["single_root"], key)
            self.assertEqual(v["missing_parents"], [], key)
            self.assertEqual(v["cycles"], [], key)
            self.assertTrue(0 < v["max_depth"] < v["bone_count"], key)

    def test_root_names(self):
        v = SK.verify_hierarchy(self._bones("bandit"))
        self.assertEqual(v["roots"], ["Bip01"])
        self.assertEqual(v["root_count"], 1)
        v2 = SK.verify_hierarchy(self._bones("chinaman_skel"))
        self.assertEqual(v2["roots"], ["Bip01"])

    def test_no_scale_fields(self):
        for key in BONE_COUNTS:
            bones = self._bones(key)
            for b in bones:
                for k in b:
                    self.assertNotIn("scale", k.lower(), key)
            v = SK.verify_hierarchy(bones)
            self.assertTrue(v["scale_fields_absent"], key)

    def test_bind_world_scale_and_handedness_evidence(self):
        bones = self._bones("bandit")
        rot, pos = SK.bind_world([{
            "name": b["name"], "parent": b["parent"], "children": b["children"],
            "rot_parent": b["rot_parent"], "tr_parent": b["tr_parent"],
        } for b in bones])
        names = [b["name"] for b in bones]
        # feet on ground, pelvis mid-body: unit scale, y-up handedness
        self.assertLess(abs(pos[names.index("Bip01 L Toe0")][1]), 0.2)
        self.assertLess(abs(pos[names.index("Bip01 R Toe0")][1]), 0.2)
        self.assertGreater(pos[names.index("Bip01 Pelvis")][1], 6.0)
        self.assertLess(pos[names.index("Bip01 Head")][1], 16.0)
        v = SK.verify_hierarchy(bones)
        self.assertEqual(
            v["handedness_evidence"]["quaternion_convention"], "[x,y,z,w]")


if __name__ == "__main__":
    unittest.main()
