#!/usr/bin/env python3
"""Phase 19 Part J real NPC chain tests (bandit refid 1949).

Hermetic portion validates the committed bandit asset chain is internally
consistent end-to-end: character reference -> BSK/BSR -> skeleton -> mesh
(+skin) -> texture/material -> world coordinate. The live portion (only when
SRO_PK2_DIR or --pk2-dir is available) re-derives every edge byte-for-byte
from the original archives via build_character_manifest.real_npc_chain.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_to_asset  # noqa: E402
import build_character_manifest as BCM  # noqa: E402

CHAR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "android", "app",
    "src", "main", "assets", "game", "world", "characters", "bandit")

PK2_DIR = os.environ.get("SRO_PK2_DIR")


def _load(name):
    with open(os.path.join(CHAR, name), encoding="utf-8") as fh:
        return json.load(fh)


def _tsv(name):
    with open(os.path.join(CHAR, name), encoding="utf-8") as fh:
        rows = []
        header = None
        for ln in fh:
            ln = ln.rstrip("\n")
            if not ln.strip():
                continue
            cols = ln.split("\t")
            if header is None:
                header = cols
            else:
                rows.append(dict(zip(header, cols)))
        return rows


class TestRealNpcChain(unittest.TestCase):
    def test_provenance_resolved_chain(self):
        p = _load("provenance.json")["resolved"]
        self.assertEqual(p["bsr"], "/res/mob/china/bandit.bsr")
        self.assertEqual(p["bsk"], "/prim/skel/mob/china/bandit.bsk")
        self.assertEqual(p["bmt"], "/prim/mtrl/mob/china/bandit.bmt")
        self.assertEqual(len(p["bms"]), 3)
        self.assertEqual(len(p["ban"]), 16)

    def test_skeleton_rooted_tree(self):
        skel = _load("skeleton.json")
        self.assertEqual(skel["bone_count"], 35)
        names = [b["name"] for b in skel["bones"]]
        self.assertEqual(names[0], "Bip01")
        self.assertEqual(skel["quaternion_convention"], "xyzw")

    def test_mesh_skin_and_texture_present(self):
        meshes = _tsv("meshes.tsv")
        self.assertEqual(len(meshes), 3)
        for r in meshes:
            self.assertGreater(int(r["skin_records"]), 0, r["bms_path"])
            self.assertTrue(os.path.isfile(os.path.join(CHAR, r["msh_asset"])), r)
            self.assertTrue(os.path.isfile(os.path.join(CHAR, r["tex_asset"])), r)

    def test_mesh_bones_subset_of_skeleton(self):
        skel_names = {b["name"] for b in _load("skeleton.json")["bones"]}
        for r in _tsv("meshes.tsv"):
            with open(os.path.join(CHAR, r["msh_asset"]), "rb") as fh:
                msh = bms_to_asset.read_msh(fh.read())
            self.assertTrue(msh["has_skin"], r)
            for name in msh["bone_names"]:
                self.assertIn(name, skel_names, (r["bms_path"], name))

    def test_animations_complete(self):
        anims = _tsv("anims.tsv")
        self.assertEqual(len(anims), 16)
        for r in anims:
            self.assertGreater(int(r["keyframes"]), 0, r["name"])
        by = {r["name"]: r for r in anims}
        self.assertEqual(by["bandit_walk"]["duration_ms"], "1333")
        self.assertEqual(by["bandit_stand01"]["duration_ms"], "2000")

    def test_world_placement_on_sector_156x90(self):
        rows = _tsv("npc_placements.tsv")
        on = [r for r in rows if r["sector"] == "156x90"]
        self.assertEqual(len(on), 2)
        coords = {(r["world_x"], r["world_z"]) for r in on}
        self.assertEqual(coords, {("1592.44", "3321.47"),
                                  ("724.69", "3583.85")})
        for r in on:
            self.assertEqual(r["refid"], "1949")
            self.assertEqual(r["region"], "23196")

    @unittest.skipUnless(PK2_DIR, "SRO_PK2_DIR not set (live chain skipped)")
    def test_live_chain_all_proven(self):
        chain = BCM.real_npc_chain("1949", pk2_dir=PK2_DIR)
        self.assertTrue(chain["all_proven"], chain["edges"])
        kinds = {e["edge"] for e in chain["edges"]}
        self.assertIn("npc_record->character_reference", kinds)
        self.assertIn("bsr->bsk", kinds)
        self.assertIn("bsr->bms", kinds)
        self.assertIn("bms->texture", kinds)
        self.assertIn("bsr->ban", kinds)
        self.assertIn("npc_record->world", kinds)
        sectors = {p["sector"] for p in chain["world_placements"]}
        self.assertIn("156x90", sectors)


if __name__ == "__main__":
    unittest.main()
