#!/usr/bin/env python3
"""Phase 20 Part C: bulk conversion + player (live, gated on SRO_PK2_DIR)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_character_manifest as BCM  # noqa: E402
import character_resolve as CR  # noqa: E402
import sro_paths  # noqa: E402

PK2_DIR = os.environ.get("SRO_PK2_DIR")


@unittest.skipUnless(PK2_DIR, "SRO_PK2_DIR not set")
class TestLiveConversion(unittest.TestCase):
    def test_bandit_converts_to_shared_store(self):
        data_pk2 = sro_paths.pk2_archive(PK2_DIR, "Data.pk2")
        media_pk2 = sro_paths.pk2_archive(PK2_DIR, "Media.pk2")
        rd = BCM._Pk2Reader(data_pk2)
        rm = BCM._Pk2Reader(media_pk2)
        try:
            with tempfile.TemporaryDirectory() as out:
                manifest = BCM.convert_character(
                    rd, rm, "mob\\china\\bandit.bsr", out, "mob_china_bandit")
                self.assertEqual(manifest["key"], "mob_china_bandit")
                self.assertTrue(manifest["meshes"])
                self.assertTrue(manifest["anims"])
                skel = os.path.join(out, "shared", "skel",
                                    manifest["skeleton"] + ".json")
                self.assertTrue(os.path.isfile(skel))
                self.assertTrue(os.path.isfile(
                    os.path.join(out, "mob_china_bandit", "manifest.json")))
                self.assertTrue(os.path.isfile(
                    os.path.join(out, "mob_china_bandit", "npc_placements.tsv")))
        finally:
            rd.close()
            rm.close()

    def test_jupiter_texture_resolves(self):
        data_pk2 = sro_paths.pk2_archive(PK2_DIR, "Data.pk2")
        rd = BCM._Pk2Reader(data_pk2)
        try:
            cls = CR.classify_character(
                rd.read, rd._has, "mob\\jupiter\\charm_witch.bsr")
            self.assertIn(cls["status"], (CR.STATUS_PROVEN, CR.STATUS_PARTIAL))
            tex_issues = [
                m for m in cls["meshes"]
                if m.get("reason", "").startswith("texture")
            ]
            self.assertFalse(tex_issues, cls["meshes"])
        finally:
            rd.close()

    def test_player_converts(self):
        data_pk2 = sro_paths.pk2_archive(PK2_DIR, "Data.pk2")
        rd = BCM._Pk2Reader(data_pk2)
        try:
            with tempfile.TemporaryDirectory() as out:
                manifest = BCM.convert_player(rd, rd, out)
                self.assertEqual(manifest["key"], "player")
                self.assertTrue(manifest["meshes"])
        finally:
            rd.close()


if __name__ == "__main__":
    unittest.main()
