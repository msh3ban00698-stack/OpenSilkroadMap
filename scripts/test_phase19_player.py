#!/usr/bin/env python3
"""Phase 19 Part L player pipeline tests (chinaman).

The player is a distinct character from NPCs: no npcpos spawn and no
/mob/ BSR. This test proves the player's core rendering components
(skeleton, body/face/hair meshes, skinning) from committed samples, and the
live player_pipeline() (only with SRO_PK2_DIR) reports the full component
status including the documented BSR->skeleton mismatch and missing static
spawn reference.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as M  # noqa: E402
import bsk_decoder as BSK  # noqa: E402
import build_character_manifest as BCM  # noqa: E402
import skeleton as SK  # noqa: E402

TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata",
                  "formats")
PK2_DIR = os.environ.get("SRO_PK2_DIR")


class TestPlayerPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(TD, "bsk_samples", "chinaman_skel.bsk"),
                  "rb") as fh:
            cls.skel = BSK.parse_bsk(fh.read())["bones"]
        cls.skel_names = {b["name"] for b in cls.skel}

    def test_player_skeleton_rooted_tree(self):
        hier = SK.verify_hierarchy(self.skel)
        self.assertEqual(len(self.skel), 38)
        self.assertTrue(hier["single_root"], hier)
        self.assertEqual(hier["roots"][0], "Bip01")
        self.assertTrue(hier["is_tree"], hier)

    def test_player_mesh_skin_and_bones(self):
        for part in ("man_pelvis", "man_arm_lower", "man_face", "man_hair"):
            with open(os.path.join(TD, "bms_skin_samples", part + ".bms"),
                      "rb") as fh:
                parsed = M.parse_bms(fh.read())
            self.assertIsNotNone(parsed["skin"], part)
            for name in parsed["bones"]["bone_names"]:
                self.assertIn(name, self.skel_names, (part, name))

    def test_player_has_fingers_and_spinebase(self):
        self.assertIn("Bip01 L Finger01", self.skel_names)
        self.assertIn("Bip01 R Finger21", self.skel_names)
        self.assertIn("Spine_Base", self.skel_names)

    @unittest.skipUnless(PK2_DIR, "SRO_PK2_DIR not set (live pipeline skipped)")
    def test_live_player_pipeline(self):
        r = BCM.player_pipeline(pk2_dir=PK2_DIR)
        self.assertEqual(r["status"], "PARTIAL")
        c = r["components"]
        self.assertEqual(c["skeleton"]["status"], "PROVEN", c["skeleton"])
        self.assertEqual(c["meshes"]["status"], "PROVEN", c["meshes"])
        self.assertEqual(c["animations"]["status"], "PROVEN", c["animations"])
        self.assertEqual(c["spawn_reference"]["status"], "UNKNOWN")
        # the BSR exists and resolves, but to the europe skeleton (documented)
        self.assertIn("europeman_skel", c["bsr"]["evidence"])


if __name__ == "__main__":
    unittest.main()
