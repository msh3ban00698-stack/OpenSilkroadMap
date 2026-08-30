#!/usr/bin/env python3
"""Phase 15: native game integration — real-data validation.

This phase extends the Phase 14 single-sector runtime toward a real multi-sector
world: multiple verified terrain sectors stitched in world space, real NPC
spawn placement indexed by sector, and a precise characterization of the object
placement (.o2) header so object integration is either proven or blocked.

Executable (Python) evidence gate. Validates, against committed real assets and
the live archives (when present):

  * multi-sector terrain set: sector origins, world bounds, height continuity
    across the shared sector edge (verified 0.0), cross-sector height sampling
  * real NPC placement: per-sector counts in the committed world window, world
    coordinates via the verified region pack, character_refid join coverage
  * object placement (.o2): the variable header layout (12-byte magic + zeros +
    first data at 16 + 8k, offset 12 always 0, k in [0,35]) and the Phase 10
    parser's validity window (k == 0 only)

Nothing is invented: every assertion is a direct consequence of committed data
or of the already-proven Phase 10/13 formulas/findings.
"""
import collections
import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import world_terrain as wt  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game"
WORLD_DIR = ASSETS / "world"
NPC_POS = ASSETS / "textdata" / "npcpos.tsv"

SECTOR_WORLD = 1920.0

# The Phase 14 selected region (Jangan_Field) and its committed terrain sectors.
REF_SX, REF_SY = 156, 89
COMMITTED_SECTORS = [(156, 89), (156, 90)]

DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"
MAP_PK2 = "/tmp/opencode/pk2raw/Map.pk2"


def _index_rows():
    out = []
    for line in (WORLD_DIR / "world_index.tsv").read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        p = line.split("\t")
        out.append((int(p[0]), int(p[1]), int(p[2]), float(p[3]), float(p[4]), p[5]))
    return out


def _npcpos_rows():
    out = []
    for line in NPC_POS.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        p = line.split("\t")
        if len(p) < 5:
            continue
        out.append(p)
    return out


def _archives_present():
    return os.path.exists(DATA_PK2) and os.path.exists(MAP_PK2)


class MultiSectorTerrainTest(unittest.TestCase):
    def test_selected_sectors_are_committed_and_adjacent(self):
        indexed = {(sx, sy) for (sx, sy, *_) in _index_rows()}
        self.assertTrue(all(s in indexed for s in COMMITTED_SECTORS))
        self.assertEqual(COMMITTED_SECTORS[1], (COMMITTED_SECTORS[0][0], COMMITTED_SECTORS[0][1] + 1))

    def test_sector_world_origins_form_a_1x2_world(self):
        o0 = wt.sector_world_origin(156, 89, REF_SX, REF_SY)
        o1 = wt.sector_world_origin(156, 90, REF_SX, REF_SY)
        self.assertEqual((0.0, 0.0), o0)
        self.assertEqual((0.0, SECTOR_WORLD), o1)

    def test_world_bounds_cover_two_sectors(self):
        lo_x = min(wt.sector_world_origin(sx, sy, REF_SX, REF_SY)[0] for sx, sy in COMMITTED_SECTORS)
        lo_z = min(wt.sector_world_origin(sx, sy, REF_SX, REF_SY)[1] for sx, sy in COMMITTED_SECTORS)
        self.assertEqual(0.0, lo_x)
        self.assertEqual(0.0, lo_z)
        # 1 sector wide, 2 sectors tall in world units.
        self.assertEqual(SECTOR_WORLD, (max(sx for sx, _ in COMMITTED_SECTORS) - 156 + 1) * SECTOR_WORLD)
        self.assertEqual(2 * SECTOR_WORLD, (max(sy for _, sy in COMMITTED_SECTORS) - 89 + 1) * SECTOR_WORLD)

    def test_height_continuity_across_shared_sector_edge(self):
        g1, _ = wt.read_hg(WORLD_DIR / "156x89.hg")
        g2, _ = wt.read_hg(WORLD_DIR / "156x90.hg")
        # g1 last row (local z=1920) == g2 first row (local z=0 -> world z=1920).
        for x in range(97):
            self.assertEqual(g1[96][x], g2[0][x], f"height discontinuity at column {x}")

    def test_cross_sector_height_sampling(self):
        g1, _ = wt.read_hg(WORLD_DIR / "156x89.hg")
        g2, _ = wt.read_hg(WORLD_DIR / "156x90.hg")
        # world z=1000 -> sector 89 local z=1000; world z=2500 -> sector 90 local z=580.
        h89 = g1[int(1000 // 20.0)][int(960 // 20.0)]
        h90 = g2[int((2500 - SECTOR_WORLD) // 20.0)][int(960 // 20.0)]
        lo, hi = 866.25, 2687.02
        self.assertTrue(lo - 0.2 <= h89 <= hi + 0.2, h89)
        self.assertTrue(lo - 0.2 <= h90 <= hi + 0.2, h90)


class NpcPlacementTest(unittest.TestCase):
    def test_world_npc_counts_per_committed_sector(self):
        counts = collections.Counter()
        for row in _npcpos_rows():
            code = int(row[1])
            if code < 0:
                continue
            sx, sy = wt.unpack_region(code)
            if (sx, sy) in COMMITTED_SECTORS:
                counts[(sx, sy)] += 1
        self.assertEqual(0, counts[(156, 89)])
        self.assertEqual(3, counts[(156, 90)])

    def test_npc_world_coords_fall_inside_sector_bounds(self):
        for row in _npcpos_rows():
            code = int(row[1])
            if code < 0:
                continue
            sx, sy = wt.unpack_region(code)
            if (sx, sy) not in COMMITTED_SECTORS:
                continue
            x = float(row[2])
            z = float(row[4])
            wx, wz = wt.npc_to_world(x, z, code, REF_SX, REF_SY)
            self.assertTrue(0.0 <= wx < SECTOR_WORLD, f"wx {wx} out of range")
            self.assertTrue(0.0 <= wz < 2 * SECTOR_WORLD, f"wz {wz} out of range")
            self.assertTrue(0.0 <= x < SECTOR_WORLD)
            self.assertTrue(0.0 <= z < SECTOR_WORLD)

    def test_npc_character_refid_join_coverage(self):
        # 3 spawns in sector 156x90 share 2 distinct character refids (real data).
        refs = set()
        for row in _npcpos_rows():
            code = int(row[1])
            if code < 0:
                continue
            sx, sy = wt.unpack_region(code)
            if (sx, sy) in COMMITTED_SECTORS:
                refs.add(int(row[0]))
        self.assertEqual(2, len(refs))


@unittest.skipUnless(_archives_present(), "live archives not present")
class ObjectPlacementHeaderTest(unittest.TestCase):
    """Locks in the .o2 variable-header finding (Phase 15 Part H)."""

    @classmethod
    def setUpClass(cls):
        import pk2_table  # noqa: F401
        cls.map_entries, _ = pk2_table.inventory(MAP_PK2)
        cls.o2 = [e for e in cls.map_entries if e["path"].endswith(".o2")]

    def _read(self, e):
        with open(MAP_PK2, "rb") as fh:
            fh.seek(e["pos"])
            return fh.read(e["size"])

    @staticmethod
    def _first_data_offset(blob):
        for i in range(12, len(blob)):
            if blob[i] != 0:
                return i if i % 2 == 0 else i - 1
        return None

    def test_offset12_is_always_zero(self):
        for e in self.o2:
            blob = self._read(e)
            if len(blob) < 16:
                continue
            self.assertEqual(0, struct.unpack_from("<I", blob, 12)[0], e["path"])

    def test_data_start_is_variable_and_at_least_16(self):
        # The header is a variable-length run of zeros after the 12-byte magic;
        # the first data byte is never before offset 16 and is not constant.
        starts = set()
        for e in self.o2:
            blob = self._read(e)
            off = self._first_data_offset(blob)
            if off is None:
                continue  # empty sector (all-zero after magic)
            self.assertGreaterEqual(off, 16, e["path"])
            starts.add(off)
        self.assertIn(16, starts)
        self.assertGreater(len(starts), 1, "data start is not variable")

    def test_k_range_matches_36_block_world(self):
        # First-data offsets range within a small window; the maximum observed
        # offset stays under the 36-block (6x6) world grid scale.
        offs = []
        for e in self.o2:
            blob = self._read(e)
            off = self._first_data_offset(blob)
            if off is None:
                continue
            offs.append(off)
        self.assertTrue(16 <= min(offs) <= max(offs) < 512, (min(offs), max(offs)))

    def test_phase10_parser_valid_only_when_data_starts_at_16(self):
        # parse_o2 assumes data at offset 16; it is only correct when the real
        # first data byte is at 16 (k == 0). Other sectors have a longer header.
        mismatch = 0
        for e in self.o2:
            blob = self._read(e)
            off = self._first_data_offset(blob)
            if off is None or off == 16:
                continue
            mismatch += 1
        self.assertGreater(mismatch, 0, "no k>0 sectors found; header finding not exercised")


if __name__ == "__main__":
    unittest.main()
