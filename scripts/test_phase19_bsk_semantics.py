#!/usr/bin/env python3
"""Phase 19 Part B BSK transform-field semantic tests (hermetic).

Proven facts asserted here (cross-file, against the Phase 18 FK chain):
  * rot_parent/tr_parent chain into a bind world (Phase 18).
  * rot_origin/tr_origin equals that FK-chained world for all non-helper
    bones; helper bones (Spine_Base) store identity and auto-named chains
    (islamman BoneNN) may store an authored pivot that drifts.
  * rot_local/tr_local is the inverse bind transform: inverse of the
    FK-chained world for 177/182 tested bones; rotation is self-inverse with
    the stored origin everywhere it was checked.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsk_decoder as B  # noqa: E402
import skeleton as SK  # noqa: E402

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsk_samples")

# Expected verified counts per committed raw sample (deterministic).
EXPECT = {
    "chinaman_skel": {"bones": 38, "origin_world": 37, "local_inverse_world": 38},
    "bandit": {"bones": 35, "origin_world": 34, "local_inverse_world": 35},
    "islamman": {"bones": 43, "origin_world": 38, "local_inverse_world": 38},
    "blackrobber": {"bones": 35, "origin_world": 34, "local_inverse_world": 35},
    "horse1": {"bones": 31, "origin_world": 31, "local_inverse_world": 31},
}


class TestTransformSemantics(unittest.TestCase):
    def _raw(self, key):
        with open(os.path.join(SAMPLES_DIR, key + ".bsk"), "rb") as fh:
            return fh.read()

    def test_counts_match_fixture_expectations(self):
        for key, exp in EXPECT.items():
            r = B.parse_bsk(self._raw(key))
            self.assertTrue(r["exact"], key)
            self.assertEqual(len(r["bones"]), exp["bones"], key)
            sem = B.verify_transform_semantics(r["bones"])
            self.assertEqual(sem["bone_count"], exp["bones"], key)
            self.assertEqual(sem["origin_matches_world"], exp["origin_world"],
                             key + " origin==world")
            self.assertEqual(sem["local_is_inverse_world"],
                             exp["local_inverse_world"], key + " local==inv(world)")

    def test_spine_base_is_the_helper_exception(self):
        for key in ("chinaman_skel", "bandit", "blackrobber"):
            r = B.parse_bsk(self._raw(key))
            sem = B.verify_transform_semantics(r["bones"])
            self.assertEqual(sem["origin_exceptions"], ["Spine_Base"], key)
            self.assertEqual(sem["local_inverse_world_exceptions"], [], key)

    def test_local_rotation_inverse_of_stored_origin(self):
        r = B.parse_bsk(self._raw("islamman"))
        sem = B.verify_transform_semantics(r["bones"])
        # BoneNN chain: rotation is self-inverse with origin; translation is
        # NOT the inverse of the stored origin (authored drift) -- reported.
        self.assertGreaterEqual(sem["local_is_inverse_origin"], 37)
        self.assertEqual(
            set(sem["local_inverse_origin_exceptions"]),
            set(["Spine_Base", "Bone03", "Bone04", "Bone05", "Bone06",
                 "Bone07"]))

    def test_fk_chain_world_is_mesh_aligned_bind(self):
        # Regression anchor from Phase 18: bind pose must land feet near ground.
        r = B.parse_bsk(self._raw("bandit"))
        rot, pos = SK.bind_world([{
            "name": b["name"], "parent": b["parent"], "children": b["children"],
            "rot_parent": b["rot_parent"], "tr_parent": b["tr_parent"],
        } for b in r["bones"]])
        names = [b["name"] for b in r["bones"]]
        self.assertLess(abs(pos[names.index("Bip01 L Toe0")][1]), 0.2)
        self.assertLess(abs(pos[names.index("Bip01 R Toe0")][1]), 0.2)
        self.assertGreater(pos[names.index("Bip01 Pelvis")][1], 6.0)


if __name__ == "__main__":
    unittest.main()
