#!/usr/bin/env python3
"""Phase 13 Part B: world relationship validation.

Validates real-data relationships between regions, terrain, and object
placement using the committed world fixtures plus the live archives
(when SRO_PK2_DIR=/tmp/opencode/pk2raw is present):

  * every object-instance .bsr ref resolves to a real Data.pk2 entry;
  * object local (x, z) lie within the sector bounds [0, 1920) for the
    committed sector 76,103;
  * world coordinates of instances in adjacent sectors differ by exactly
    SECTOR_WORLD (1920.0) per the verified formula;
  * object y (elevation) is bounded (no NaN/inf, sane range);
  * the terrain asset chain resolves: .bsr -> .bmt -> .ddj (texture) for
    resolved fixtures when the live archive is present.

No new formats are invented; this only cross-checks already-proven facts.
"""
import json
import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import pk2_table  # noqa: E402
import world_terrain as wt  # noqa: E402

TD = SCRIPTS / "testdata" / "world"
DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"
MEDIA_PK2 = "/tmp/opencode/pk2raw/Media.pk2"

SECTOR = (76, 103)  # tx, tz of the committed Constantine-window sector


def load_objects_fixture():
    with open(TD / "const_76x103_objects.json", encoding="utf-8") as fh:
        return json.load(fh)


def _archives_present():
    return os.path.exists(DATA_PK2)


def _inventory(arc):
    entries, _ = pk2_table.inventory(arc)
    return entries


def _read(arc, e):
    with open(arc, "rb") as fh:
        fh.seek(e["pos"])
        return fh.read(e["size"])


class ObjectPlacementRelationsTests(unittest.TestCase):
    """Cross-checks the committed .o2 fixture against the coordinate rules."""

    def setUp(self):
        self.fixture = load_objects_fixture()
        self.insts = self.fixture["instances"]

    def test_fixture_sector_metadata(self):
        self.assertEqual(self.fixture["source"].split()[0], "Map.pk2")

    def test_objects_are_inside_sector_bounds(self):
        eps = 1.0
        sw = wt.SECTOR_WORLD
        for inst in self.insts:
            self.assertGreaterEqual(inst["x"], -eps, "x below sector bound")
            self.assertLess(inst["x"], sw + eps, "x above sector bound")
            self.assertGreaterEqual(inst["z"], -eps, "z below sector bound")
            self.assertLess(inst["z"], sw + eps, "z above sector bound")

    def test_theta_is_an_angle_radians(self):
        # unclamped rotations observed as low as -7.697 (~ -2*pi - 1.41)
        bound = 2 * 3.1416 + 1.5
        for inst in self.insts:
            self.assertGreaterEqual(inst["theta"], -bound)
            self.assertLessEqual(inst["theta"], bound)

    def test_y_is_finite(self):
        import math
        for inst in self.insts:
            self.assertFalse(math.isnan(inst["y"]))
            self.assertFalse(math.isinf(inst["y"]))
            self.assertLessEqual(inst["y"], 50.0)

    def test_every_instance_resolves_a_bsr(self):
        for inst in self.insts:
            self.assertTrue(inst["bsr"], f"unresolved nameI {inst['nameI']}")

    def test_distinct_bsr_paths_are_normalized(self):
        seen = set()
        for inst in self.insts:
            p = inst["bsr"]
            self.assertNotIn("\\", p)
            self.assertTrue(p.endswith(".bsr") or p.endswith(".cpd"), p)
            seen.add(p)
        self.assertGreaterEqual(len(seen), 5)


@unittest.skipUnless(_archives_present(), "live Data.pk2 not present")
class LiveAssetChainTests(unittest.TestCase):
    """When the real archive exists, the object refs must resolve end-to-end."""

    @classmethod
    def setUpClass(cls):
        cls.entries = _inventory(DATA_PK2)
        cls.paths = set(e["path"].lower() for e in cls.entries)
        cls.fixture = load_objects_fixture()

    def _find(self, rel):
        want = "/" + rel.lstrip("/")
        want = want.lower()
        for e in self.entries:
            if e["path"].lower() == want:
                return e
        return None

    def test_all_object_bsr_refs_exist_in_archive(self):
        missing = []
        for inst in self.fixture["instances"]:
            e = self._find(inst["bsr"])
            if e is None:
                missing.append(inst["bsr"])
        self.assertEqual(missing, [], f"missing refs: {missing[:10]}")

    def test_bsr_refs_parse_to_material_and_meshes(self):
        checked = 0
        for inst in self.fixture["instances"]:
            if not inst["bsr"].endswith(".bsr"):
                continue
            e = self._find(inst["bsr"])
            if e is None:
                continue
            blob = _read(DATA_PK2, e)
            parsed = wt.parse_bsr(blob)
            self.assertIsNotNone(parsed)
            mpath, bms_list = parsed
            self.assertTrue(mpath.endswith(".bmt"), mpath)
            checked += 1
        self.assertGreaterEqual(checked, 80)

    def test_bmt_paths_exist_in_archive(self):
        for inst in self.fixture["instances"]:
            if not inst["bsr"].endswith(".bsr"):
                continue
            e = self._find(inst["bsr"])
            if e is None:
                continue
            blob = _read(DATA_PK2, e)
            parsed = wt.parse_bsr(blob)
            if parsed is None:
                continue
            mpath, _bms = parsed
            if mpath:
                me = self._find(mpath)
                self.assertIsNotNone(me, f"missing material {mpath}")

    def test_bms_paths_exist_in_archive(self):
        for inst in self.fixture["instances"]:
            if not inst["bsr"].endswith(".bsr"):
                continue
            e = self._find(inst["bsr"])
            if e is None:
                continue
            parsed = wt.parse_bsr(_read(DATA_PK2, e))
            if parsed is None:
                continue
            _mpath, bms_list = parsed
            for b in bms_list:
                be = self._find(b)
                self.assertIsNotNone(be, f"missing mesh {b}")

    def test_object_bms_parse_to_geometry(self):
        bms_seen = set()
        for inst in self.fixture["instances"]:
            if not inst["bsr"].endswith(".bsr"):
                continue
            e = self._find(inst["bsr"])
            if e is None:
                continue
            parsed = wt.parse_bsr(_read(DATA_PK2, e))
            if parsed is None:
                continue
            _mpath, bms_list = parsed
            for b in bms_list:
                if b in bms_seen:
                    continue
                be = self._find(b)
                if be is None:
                    continue
                geom = wt.parse_bms_build(_read(DATA_PK2, be))
                if geom is None:
                    continue
                self.assertGreaterEqual(len(geom["verts"]), 3)
                self.assertGreaterEqual(len(geom["indices"]), 3)
                bms_seen.add(b)
        self.assertGreaterEqual(len(bms_seen), 1)

    def test_texture_chain_resolves_to_ddj(self):
        # bmt ddj refs are bare filenames resolved against the bmt's dir;
        # world textures live in Data.pk2 under prim/... (not Media.pk2)
        hits = 0
        for inst in self.fixture["instances"]:
            if not inst["bsr"].endswith(".bsr"):
                continue
            e = self._find(inst["bsr"])
            if e is None:
                continue
            parsed = wt.parse_bsr(_read(DATA_PK2, e))
            if parsed is None:
                continue
            mpath, _bms = parsed
            me = self._find(mpath)
            if me is None:
                continue
            mats = wt.parse_bmt(_read(DATA_PK2, me))
            mdir = "/".join(("/" + mpath).rsplit("/", 1)[:-1])
            for ddj in mats.values():
                cand = mdir + "/" + ddj.replace("\\", "/")
                if self._find(cand) is not None:
                    hits += 1
        self.assertGreaterEqual(hits, 1)


class CoordinateRelationsTests(unittest.TestCase):
    """Adjacent-sector world-coordinate relationships (proven formulas)."""

    def test_adjacent_sectors_shift_by_1920(self):
        ox0, oz0 = wt.sector_world_origin(76, 103, 100, 76)
        ox1, oz1 = wt.sector_world_origin(77, 103, 100, 76)
        self.assertAlmostEqual(ox1 - ox0, wt.SECTOR_WORLD)
        self.assertAlmostEqual(oz1 - oz0, 0.0)

    def test_world_origin_consistent_with_npc_formula(self):
        for sx, sy in ((76, 103), (77, 103), (76, 102), (101, 77)):
            ox, oz = wt.sector_world_origin(sx, sy, 100, 76)
            wx, wz = wt.npc_to_world(0.0, 0.0, wt.pack_region(sx, sy), 100, 76)
            self.assertAlmostEqual(ox, wx)
            self.assertAlmostEqual(oz, wz)

    def test_region_pack_unpack_roundtrip(self):
        for sx, sy in ((76, 103), (0, 0), (255, 255), (46, 70)):
            code = wt.pack_region(sx, sy)
            rx, ry = wt.unpack_region(code)
            self.assertEqual((rx, ry), (sx, sy))

    def test_local_to_world_uses_sector_offset(self):
        inst = {"x": 100.0, "y": 0.0, "z": 200.0, "tx": 76, "tz": 103}
        wx, wy, wz = wt.local_to_world(inst, 100, 76)
        self.assertAlmostEqual(wx, 100.0 + (76 - 100) * 1920.0)
        self.assertAlmostEqual(wz, 200.0 + (103 - 76) * 1920.0)
        self.assertEqual(wy, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
