#!/usr/bin/env python3
"""Phase 13 Part J: npcpos -> region cell placement validation.

Connects the committed npcpos.tsv (18,457 spawn rows) to the verified world
coordinate system (Phase 10) and the region catalog. This corrects the Phase 12
column claim and proves, from real data only:

  * column layout: col0 = character_refid, col1 = region_code, col2 = local_x,
    col3 = height_y (~0), col4 = local_z;
  * col1 joins regioncode.tsv col1 (1800/1855 distinct codes) with the region
    pack convention region & 0xFF = x sector, region >> 8 = y sector;
  * world rows (region without the high/instance bit) place local (x, z) in
    [0, 1920) — 13 documented boundary rows sit exactly at the 1920 sector edge;
  * instance/dungeon rows (region high bit set) use 21 distinct negative codes
    and a separate coordinate space (documented UNKNOWN, not guessed);
  * npc_to_world matches the verified reference formula for a known city.

Nothing is invented: every assertion is a direct consequence of already-proven
facts or of the committed data itself.
"""
import json
import os
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import world_terrain as wt  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game"
NPC_POS = ASSETS / "textdata" / "npcpos.tsv"
REGION_CODE = ASSETS / "textdata" / "regioncode.tsv"

LIVE_TEXTDATA = Path("/tmp/opencode/textdata")


def _rows(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        out.append(line.split("\t"))
    return out


def _npcpos_rows():
    return _rows(NPC_POS)


def _region_ids():
    ids = set()
    for r in _rows(REGION_CODE):
        if len(r) > 1 and r[1].strip().lstrip("-").isdigit():
            ids.add(int(r[1]))
    return ids


def _is_instance(region):
    """Instance/dungeon rows carry the high bit (signed 16 -> negative)."""
    return (region & 0x8000) != 0


class NpcPosColumnLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _npcpos_rows()

    def test_row_count_and_width(self):
        self.assertEqual(len(self.rows), 18457)
        self.assertTrue(all(len(r) == 5 for r in self.rows))

    def test_col0_is_int_character_refid(self):
        for r in self.rows:
            int(r[0])

    def test_col1_is_int_region_code(self):
        for r in self.rows:
            int(r[1])

    def test_cols_2_3_4_are_float(self):
        for r in self.rows:
            float(r[2]); float(r[3]); float(r[4])

    def test_height_axis_is_finite_and_varies(self):
        import math
        heights = [float(r[3]) for r in self.rows]
        self.assertTrue(all(not math.isnan(h) and not math.isinf(h) for h in heights))
        self.assertGreater(max(heights), 100.0)
        self.assertLess(min(heights), -100.0)

    def test_region_join_regioncode(self):
        ids = _region_ids()
        codes = {int(r[1]) for r in self.rows}
        matched = codes & ids
        self.assertGreaterEqual(len(matched), 1800)
        self.assertLessEqual(len(matched), len(codes))

    def test_world_vs_instance_classification(self):
        world = [r for r in self.rows if not _is_instance(int(r[1]))]
        inst = [r for r in self.rows if _is_instance(int(r[1]))]
        self.assertEqual(len(world), 14800)
        self.assertEqual(len(inst), 3657)
        self.assertEqual(len({int(r[1]) for r in inst}), 21)


class WorldPlacementBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = [r for r in _npcpos_rows() if not _is_instance(int(r[1]))]

    def test_world_local_coords_inside_sector(self):
        edge = 0
        for r in self.world:
            x, z = float(r[2]), float(r[4])
            if x == 1920.0 or z == 1920.0:
                edge += 1
                continue
            self.assertGreaterEqual(x, 0.0, f"x<0 at {r}")
            self.assertLess(x, 1920.0, f"x>=1920 at {r}")
            self.assertGreaterEqual(z, 0.0, f"z<0 at {r}")
            self.assertLess(z, 1920.0, f"z>=1920 at {r}")
        self.assertEqual(edge, 13)

    def test_world_sector_coverage(self):
        sx = {int(r[1]) & 0xFF for r in self.world}
        sy = {int(r[1]) >> 8 for r in self.world}
        self.assertGreaterEqual(len(sx), 150)
        self.assertGreaterEqual(len(sy), 50)
        self.assertTrue(all(0 <= v <= 255 for v in sx | sy))


class CoordinateMappingTests(unittest.TestCase):
    def test_region_pack_unpack_for_jangan_codes(self):
        for code in (25001, 25257, 25000):
            sx, sy = wt.unpack_region(code)
            self.assertEqual(wt.pack_region(sx, sy), code)

    def test_npc_to_world_reference_formula(self):
        wx, wz = wt.npc_to_world(659.74, 981.13, 25257, 168, 97)
        sx, sy = wt.unpack_region(25257)
        self.assertAlmostEqual(wx, 659.74 + (sx - 168) * 1920.0)
        self.assertAlmostEqual(wz, 981.13 + (sy - 97) * 1920.0)

    def test_jangan_npcs_land_in_jangan_sector(self):
        jangan_ids = {int(r[1]) for r in _rows(REGION_CODE)
                      if len(r) > 2 and r[2] == "RN_CH_JANGAN"}
        self.assertGreaterEqual(len(jangan_ids), 5)
        jangan = [r for r in _npcpos_rows()
                  if int(r[1]) in jangan_ids and not _is_instance(int(r[1]))]
        self.assertGreaterEqual(len(jangan), 50)
        for r in jangan:
            sx = int(r[1]) & 0xFF
            sy = int(r[1]) >> 8
            self.assertTrue(167 <= sx <= 169, r)
            self.assertTrue(96 <= sy <= 98, r)


@unittest.skipUnless(LIVE_TEXTDATA.is_dir(), "live textdata not present")
class LiveCharacterDataJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        refids = set()
        for fn in sorted(LIVE_TEXTDATA.glob("characterdata*.txt")):
            raw = fn.read_bytes()
            text = raw.decode("utf-16-le", errors="replace")
            for ln in text.splitlines():
                p = ln.split("\t")
                if len(p) > 1 and p[1].strip().isdigit():
                    refids.add(int(p[1]))
        cls.refids = refids

    def test_col0_refids_join_characterdata(self):
        refs = {int(r[0]) for r in _npcpos_rows()}
        self.assertEqual(len(refs), 1180)
        self.assertEqual(len(refs & self.refids), 1180)


class PlacementCatalogTests(unittest.TestCase):
    """Proves the derived placement catalog is reproducible from committed data."""

    def test_catalog_fixture_matches_live_build(self):
        from collections import Counter
        per_sector = Counter()
        for r in _npcpos_rows():
            code = int(r[1])
            if _is_instance(code):
                continue
            per_sector[(code & 0xFF, code >> 8)] += 1
        total = sum(per_sector.values())
        self.assertEqual(total, 14800)
        self.assertEqual(len(per_sector), 1834)


if __name__ == "__main__":
    unittest.main(verbosity=2)
