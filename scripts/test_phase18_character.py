#!/usr/bin/env python3
"""Phase 18 character manifest tests (hermetic against committed assets)."""
import csv
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_to_asset  # noqa: E402
import skeleton as SK  # noqa: E402

CHAR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "android", "app", "src", "main", "assets", "game", "world", "characters", "bandit")


def _read_tsv(name):
    with open(os.path.join(CHAR, name)) as fh:
        r = csv.DictReader(fh, delimiter="\t")
        return [dict(row) for row in r]


class TestSkeletonJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(CHAR, "skeleton.json")) as fh:
            cls.skel = json.load(fh)

    def test_bone_count(self):
        self.assertEqual(self.skel["bone_count"], 35)
        self.assertEqual(len(self.skel["bones"]), 35)

    def test_quaternion_convention(self):
        self.assertEqual(self.skel["quaternion_convention"], "xyzw")

    def test_bind_world_consistent(self):
        # Recompute bind world from committed local fields and compare.
        bones = [{
            "name": b["name"], "parent": b["parent"],
            "children": b["children"],
            "rot_parent": b["rot_parent"], "tr_parent": b["tr_parent"],
        } for b in self.skel["bones"]]
        _, wpos = SK.bind_world(bones)
        for i, b in enumerate(self.skel["bones"]):
            for k in range(3):
                self.assertLess(abs(wpos[i][k] - b["bind_world_pos"][k]),
                                1e-3, b["name"])

    def test_single_root(self):
        parents = SK.bone_parents(self.skel["bones"])
        self.assertEqual(sum(1 for p in parents if p == -1), 1)

    def test_path(self):
        self.assertEqual(self.skel["path"], "/prim/skel/mob/china/bandit.bsk")


class TestMeshes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _read_tsv("meshes.tsv")

    def test_part_count(self):
        self.assertEqual(len(self.rows), 3)

    def test_skin_records_equal_vcount(self):
        for r in self.rows:
            self.assertEqual(int(r["skin_records"]), int(r["vcount"]), r["bms_path"])

    def test_msh_round_trip(self):
        for r in self.rows:
            with open(os.path.join(CHAR, r["msh_asset"]), "rb") as fh:
                blob = fh.read()
            m = bms_to_asset.read_msh(blob)
            self.assertEqual(m["version"], 2, r["msh_asset"])
            self.assertTrue(m["has_skin"])
            self.assertEqual(m["vertex_count"], int(r["vcount"]))
            self.assertEqual(m["triangle_count"], int(r["tcount"]))
            self.assertEqual(len(m["skin"]), m["vertex_count"])
            self.assertEqual(len(m["bone_names"]), int(r["bone_count"]))
            # skin bone indices in local range
            bc = len(m["bone_names"])
            for s in m["skin"]:
                self.assertLess(s["bone1"], bc)
                if s["bone2"] != 0xFF:
                    self.assertLess(s["bone2"], bc)

    def test_materials_resolve(self):
        self.assertEqual(self.rows[0]["material"], "Bandit1")
        self.assertEqual(self.rows[0]["ddj_path"],
                         "/prim/mtrl/mob/china/bandit_sword.ddj")
        for r in self.rows[1:]:
            self.assertEqual(r["material"], "Bandit")
            self.assertEqual(r["ddj_path"], "/prim/mtrl/mob/china/bandit.ddj")

    def test_textures_exist(self):
        for r in self.rows:
            p = os.path.join(CHAR, r["tex_asset"])
            self.assertTrue(os.path.isfile(p), r["tex_asset"])
            self.assertGreater(os.path.getsize(p), 0)


class TestAnimations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _read_tsv("anims.tsv")

    def test_anim_count(self):
        self.assertEqual(len(self.rows), 16)

    def test_stand01_and_walk(self):
        by_name = {r["name"]: r for r in self.rows}
        self.assertEqual(by_name["bandit_stand01"]["duration_ms"], "2000")
        self.assertEqual(by_name["bandit_walk"]["duration_ms"], "1333")
        # Full-body clips animate all 34 skeleton bones; some clips animate a
        # subset (e.g. bandit_damage01 has 3 channels) -- PROVEN real data.
        for stem in ("bandit_stand01", "bandit_walk"):
            self.assertEqual(by_name[stem]["channels"], "34")
        for r in self.rows:
            self.assertGreaterEqual(int(r["channels"]), 1, r["name"])

    def test_anim_json_schema(self):
        for stem in ("bandit_stand01", "bandit_walk"):
            with open(os.path.join(CHAR, "anim", stem + ".json")) as fh:
                a = json.load(fh)
            self.assertEqual(len(a["channels"]), 34)
            self.assertEqual(len(a["timestamps"]), a["keyframes_count"]
                             if "keyframes_count" in a else len(a["timestamps"]))
            for name, recs in a["channels"].items():
                self.assertEqual(len(recs), len(a["timestamps"]), name)
                for rec in recs:
                    q, p = rec[0], rec[1]
                    self.assertEqual(len(q), 4)
                    self.assertEqual(len(p), 3)
                    norm = (q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2) ** 0.5
                    self.assertAlmostEqual(norm, 1.0, places=3, msg=name)


class TestPlacements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _read_tsv("npc_placements.tsv")

    def test_committed_sector_spawns(self):
        on156x90 = [r for r in self.rows if r["sector"] == "156x90"]
        self.assertEqual(len(on156x90), 2)
        coords = {(r["world_x"], r["world_z"]) for r in on156x90}
        self.assertEqual(coords, {("1592.44", "3321.47"), ("724.69", "3583.85")})

    def test_all_rows_are_bandit(self):
        for r in self.rows:
            self.assertEqual(r["refid"], "1949")
        on156x90 = [r for r in self.rows if r["sector"] == "156x90"]
        for r in on156x90:
            self.assertEqual(r["region"], "23196")

    def test_world_spread(self):
        # Bandit is a world mob: spawns across many regions; the committed
        # sector subset is exactly the two rows on 156x90.
        self.assertGreater(len({r["region"] for r in self.rows}), 20)


class TestProvenance(unittest.TestCase):
    def test_resolved_chain(self):
        with open(os.path.join(CHAR, "provenance.json")) as fh:
            p = json.load(fh)
        self.assertEqual(p["resolved"]["bsr"], "/res/mob/china/bandit.bsr")
        self.assertEqual(p["resolved"]["bsk"], "/prim/skel/mob/china/bandit.bsk")
        self.assertEqual(len(p["resolved"]["bms"]), 3)
        self.assertEqual(len(p["resolved"]["ban"]), 16)
        for key in ("bsr", "bsk", "bmt"):
            self.assertEqual(len(p[key]["sha256"]), 64)
        for sha in p["meshes"].values():
            self.assertEqual(len(sha), 64)
        for sha in p["animations"].values():
            self.assertEqual(len(sha), 64)


if __name__ == "__main__":
    unittest.main()
