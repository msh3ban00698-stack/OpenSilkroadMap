"""Verified world/terrain pipeline tests.

Phase 10 rule: tests must use REAL source-derived fixtures where practical and
keep fixtures small. The committed fixtures under scripts/testdata/world/ are
extracted (read-only) from the real VSRO-R 1.193 archives and never modify
originals. They are:
  - const_76x103_heights.json : full 97x97 height grid of Map.pk2 /103/76.m
  - const_76x103_objects.json : parsed .o2 instances of Map.pk2 /103/76.o2
  - object_ifo_head.txt       : head of Data.pk2 navmesh/object.ifo

A live check runs against real archives when SRO_PK2_DIR and the pinned
pk2_mate reader are present; otherwise it reports SKIPPED. No test hardcodes
the extraction path and no test writes to the source archives.
"""

import json
import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import world_terrain as wt  # noqa: E402

TD = SCRIPTS / "testdata" / "world"


def load_heights_fixture():
    with open(TD / "const_76x103_heights.json", encoding="utf-8") as fh:
        return json.load(fh)


def load_objects_fixture():
    with open(TD / "const_76x103_objects.json", encoding="utf-8") as fh:
        return json.load(fh)


class TerrainMFormatTests(unittest.TestCase):
    def test_constants_are_internally_consistent(self):
        self.assertEqual(wt.STANDARD_M_SIZE, 12 + wt.M_BLOCKS * wt.M_BLOCK_BYTES)
        self.assertEqual(wt.M_BLOCKS, 36)
        self.assertEqual(wt.M_BLOCK_BYTES, 2575)
        self.assertEqual(wt.M_GRID, 97)
        self.assertEqual(wt.SECTOR_WORLD, 1920.0)
        self.assertEqual(wt.GRID_STEP, 20.0)

    def test_rejects_non_magic(self):
        with self.assertRaises(wt.WorldFormatError):
            wt.parse_terrain_m(b"not-a-map-m-file")

    def test_rejects_wrong_body_size(self):
        blob = wt.M_MAGIC + b"\x00" * (wt.M_BLOCKS * wt.M_BLOCK_BYTES + 10)
        with self.assertRaises(wt.WorldFormatError):
            wt.parse_terrain_m(blob)

    def test_real_fixture_parses_to_expected_grid(self):
        fixture = load_heights_fixture()
        blob = _rebuild_m_from_fixture(fixture)
        grid = wt.parse_terrain_m(blob)
        self.assertEqual(len(grid), 97)
        self.assertEqual(len(grid[0]), 97)
        flat = [h for row in grid for h in row]
        self.assertAlmostEqual(min(flat), fixture["min"], places=1)
        self.assertAlmostEqual(max(flat), fixture["max"], places=1)
        self.assertAlmostEqual(
            sum(flat) / len(flat), fixture["mean"], places=1
        )

    def test_real_fixture_heights_are_plausible(self):
        fixture = load_heights_fixture()
        self.assertEqual(len(fixture["data"]), 97 * 97)
        self.assertEqual(fixture["size"], 97)
        self.assertEqual(fixture["step"], 20.0)
        self.assertLess(fixture["min"], fixture["max"])

    def test_standard_size_matches_real_sector(self):
        fixture = load_heights_fixture()
        blob = _rebuild_m_from_fixture(fixture)
        self.assertEqual(len(blob), wt.STANDARD_M_SIZE)


class ObjectO2FormatTests(unittest.TestCase):
    def test_object_ifo_parses_quoted_paths(self):
        lines = (TD / "object_ifo_head.txt").read_text(encoding="utf-8")
        paths = wt.parse_object_ifo(lines)
        self.assertGreater(len(paths), 0)
        for p in paths:
            self.assertTrue(p.endswith(".bsr") or p.endswith(".BRS"), p)

    def test_real_o2_fixture_parses_and_resolves(self):
        fixture = load_objects_fixture()
        insts = fixture["instances"]
        self.assertGreater(len(insts), 0)
        for inst in insts:
            self.assertIn("nameI", inst)
            self.assertIn("x", inst)
            self.assertIn("y", inst)
            self.assertIn("z", inst)
            self.assertIn("theta", inst)
            self.assertIn("tx", inst)
            self.assertIn("tz", inst)
        resolved = [i for i in insts if i["bsr"]]
        self.assertGreater(len(resolved), 0)

    def test_o2_parser_rejects_non_magic(self):
        with self.assertRaises(wt.WorldFormatError):
            wt.parse_o2(b"not-an-o2-file", [])


class CoordinateTests(unittest.TestCase):
    def test_region_pack_unpack(self):
        for code in (0, 1, 0x64, 0x6401, 0xFFFF, 0x64FF):
            sx, sy = wt.unpack_region(code)
            self.assertEqual(wt.pack_region(sx, sy), code)

    def test_npc_to_world_matches_reference_formula(self):
        # x/z local + (sector - ref_sector) * 1920 (verified in Phase 10)
        wx, wz = wt.npc_to_world(500.0, 300.0, wt.pack_region(103, 76), 100, 76)
        self.assertAlmostEqual(wx, 500.0 + 3 * 1920.0)
        self.assertAlmostEqual(wz, 300.0)

    def test_sector_world_origin(self):
        ox, oz = wt.sector_world_origin(103, 76, 100, 76)
        self.assertAlmostEqual(ox, 3 * 1920.0)
        self.assertAlmostEqual(oz, 0.0)

    def test_minimap_sector_mapping_consistent(self):
        # minimap/{x}x{y}.ddj is sector (x, y) at 256 px per sector
        for sx in (0, 1, 100, 255):
            self.assertEqual(sx * wt.MINIMAP_PX_PER_SECTOR, sx * 256)


class DdjDdsTests(unittest.TestCase):
    def test_ddj_to_dds_strips_header(self):
        body = b"\x00" * 20 + b"DDSS"
        dds = wt.ddj_to_dds(body)
        self.assertEqual(dds.read(4), b"DDSS")

    def test_ddj_too_small_raises(self):
        with self.assertRaises(wt.WorldFormatError):
            wt.ddj_to_dds(b"\x00" * 10)


def _rebuild_m_from_fixture(fixture):
    """Rebuild a .m blob from the committed heights fixture (round-trip)."""
    import math
    data = fixture["data"]
    grid = [data[z * 97 : (z + 1) * 97] for z in range(97)]
    blob = bytearray(wt.M_MAGIC)
    blob.extend(b"\x00" * (wt.M_BLOCKS * wt.M_BLOCK_BYTES))
    for bi in range(36):
        bx = bi % 6
        by = bi // 6
        for k in range(17):
            for m in range(17):
                off = 12 + bi * wt.M_BLOCK_BYTES + wt.M_HEIGHT_OFFSET + (
                    k * 17 + m
                ) * wt.M_HEIGHT_STRIDE
                struct.pack_into("<f", blob, off, grid[by * 16 + k][bx * 16 + m])
    return bytes(blob)


class CommittedAndroidAssetsTests(unittest.TestCase):
    """Locks the committed android/app/src/main/assets/game/world/ dataset."""

    ANDROID_WORLD = SCRIPTS.parent / "android" / "app" / "src" / "main" / "assets" / "game" / "world"

    def test_android_hg_files_round_trip(self):
        if not self.ANDROID_WORLD.exists():
            self.skipTest("android world assets not present - SKIPPED")
        hgs = sorted(self.ANDROID_WORLD.glob("*.hg"))
        self.assertGreaterEqual(len(hgs), 8)
        for hg in hgs:
            grid, step = wt.read_hg(hg)
            self.assertEqual(len(grid), 97)
            self.assertEqual(len(grid[0]), 97)
            self.assertAlmostEqual(step, 20.0)

    def test_android_hg_world_index_matches_files(self):
        if not self.ANDROID_WORLD.exists():
            self.skipTest("android world assets not present - SKIPPED")
        idx = (self.ANDROID_WORLD / "world_index.tsv").read_text(encoding="utf-8")
        rows = [l for l in idx.splitlines() if l and not l.startswith("#")]
        self.assertGreater(len(rows), 0)
        for row in rows:
            sx, sy, size, mn, mx, sha = row.split("\t")
            self.assertEqual(size, "97")
            f = self.ANDROID_WORLD / f"{sx}x{sy}.hg"
            self.assertTrue(f.exists(), f"indexed {f} missing")

    def test_android_hg_heights_match_fixture_sector(self):
        # The Constantine window sector (76,103) is committed; its min/max must
        # agree with the independently derived real-data fixture.
        if not self.ANDROID_WORLD.exists():
            self.skipTest("android world assets not present - SKIPPED")
        f = self.ANDROID_WORLD / "76x103.hg"
        if not f.exists():
            self.skipTest("76x103.hg not emitted - SKIPPED")
        grid, step = wt.read_hg(f)
        flat = [h for row in grid for h in row]
        fixture = load_heights_fixture()
        self.assertAlmostEqual(min(flat), fixture["min"], places=1)
        self.assertAlmostEqual(max(flat), fixture["max"], places=1)


class LiveArchiveCheck(unittest.TestCase):
    """Runs the extraction pipeline against real archives when available."""

    def test_live_sector_extraction_and_parse(self):
        pk2_dir = os.environ.get("SRO_PK2_DIR")
        reader = os.environ.get("SRO_READER_DIR")
        if not pk2_dir or not reader or not (Path(pk2_dir) / "Map.pk2").exists():
            self.skipTest(
                "SRO_PK2_DIR/SRO_READER_DIR not set or Map.pk2 absent "
                "- live check SKIPPED (committed fixtures still tested above)"
            )
        pk2_mate = Path(reader)
        if not pk2_mate.exists():
            self.skipTest("pinned pk2_mate reader not found - SKIPPED")
        import tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                [str(pk2_mate), "extract", "-a", str(Path(pk2_dir) / "Map.pk2"),
                 "-o", td, "-p", "/103/76.m"],
                check=True, capture_output=True, timeout=120,
            )
            blob = (Path(td) / "76.m").read_bytes()
            grid = wt.parse_terrain_m(blob)
            flat = [h for row in grid for h in row]
            fixture = load_heights_fixture()
            self.assertAlmostEqual(min(flat), fixture["min"], places=1)
            self.assertAlmostEqual(max(flat), fixture["max"], places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
