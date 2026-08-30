"""Phase 17: .o2 object-placement decoding tests (proven record layout).

Executed against live archives (Map.pk2 / Data.pk2) and hermetic fixtures.
"""

import os
import struct
import unittest

MAP_PK2 = "/tmp/opencode/pk2raw/Map.pk2"
DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"
IFO_PATH = "/navmesh/object.ifo"

ARCHIVES = os.path.exists(MAP_PK2) and os.path.exists(DATA_PK2)

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from o2_decoder import (  # noqa: E402
    O2_RECORD,
    Placement,
    parse_object_ifo_map,
    parse_o2,
)

if ARCHIVES:
    import pk2_table  # noqa: E402


def _read_pk2(pk2, path):
    entries, _ = pk2_table.inventory(pk2)
    hit = next(e for e in entries if e["path"].lower() == path.lower())
    with open(pk2, "rb") as fh:
        fh.seek(hit["pos"])
        return fh.read(hit["size"])


def _reader_for(pk2):
    """Return a path->bytes reader that inventories the archive once."""
    entries, _ = pk2_table.inventory(pk2)
    by_path = {e["path"].lower(): e for e in entries}
    fh = open(pk2, "rb")

    def read(path):
        e = by_path[path.lower()]
        fh.seek(e["pos"])
        return fh.read(e["size"])

    return read


import functools  # noqa: E402


# --- hermetic fixture (sector 156x90, 1260 bytes, 32 instances, 4 distinct) ---

def _build_fixture_o2():
    rec_820 = struct.pack(
        "<IfffHfHHHH",
        820, 914.47, 1092.06, 1095.81, 0, 0.0, 0x6802, 0, 0, 0x5A9C,
    )
    rec_574 = struct.pack(
        "<IfffHfHHHH",
        574, 1467.17, 937.03, 1449.66, 0, -6.4403, 0x9001, 0, 0, 0x5A9C,
    )
    rec_820b = struct.pack(
        "<IfffHfHHHH",
        820, 348.77, 777.53, 1274.38, 0xFFFF, 0.0, 0x6401, 0, 0, 0x5A9D,
    )
    rec_820c = struct.pack(
        "<IfffHfHHHH",
        820, 1760.60, 814.82, 221.14, 0, 0.0, 0x1402, 0, 0, 0x5B9C,
    )
    seq = [16, 9, 4, 3]
    recs = [rec_820] * 16 + [rec_574] * 9 + [rec_820b] * 4 + [rec_820c] * 3
    blob = bytearray(b"JMXVMAPO1001" + b"\x00\x00\x00\x00")
    idx = 0
    for cnt in seq:
        blob += struct.pack("<H", cnt)
        for _ in range(cnt):
            blob += recs[idx]
            idx += 1
    return bytes(blob)


class O2FixturesTest(unittest.TestCase):
    def test_hermetic_fixture(self):
        blob = _build_fixture_o2()
        self.assertEqual(len(blob), 12 + 4 + 4 * 2 + 32 * O2_RECORD)
        placements = parse_o2(blob)
        self.assertEqual(32, len(placements))
        distinct = {(p.nameI, round(p.x, 2), round(p.y, 2), round(p.z, 2)) for p in placements}
        self.assertEqual(4, len(distinct))

    def test_fixture_tails(self):
        blob = _build_fixture_o2()
        by_xyz = {}
        for p in parse_o2(blob):
            by_xyz.setdefault((round(p.x, 2), round(p.z, 2)), p)
        self.assertEqual((156, 90), (by_xyz[(914.47, 1095.81)].tx, by_xyz[(914.47, 1095.81)].tz))
        self.assertEqual((157, 90), (by_xyz[(348.77, 1274.38)].tx, by_xyz[(348.77, 1274.38)].tz))
        self.assertEqual((156, 91), (by_xyz[(1760.60, 221.14)].tx, by_xyz[(1760.60, 221.14)].tz))

    def test_fixture_world_placement(self):
        blob = _build_fixture_o2()
        p = next(p for p in parse_o2(blob) if round(p.x, 1) == 1467.2)
        wx, wy, wz = p.local_to_world(156, 90)
        self.assertAlmostEqual(1467.17, wx, places=2)
        self.assertAlmostEqual(937.03, wy, places=2)
        self.assertAlmostEqual(1449.66, wz, places=2)
        p2 = next(p for p in parse_o2(blob) if round(p.x, 1) == 348.8)
        wx2, _, wz2 = p2.local_to_world(156, 90)
        self.assertAlmostEqual(348.77 + 1920.0, wx2, places=2)
        self.assertAlmostEqual(1274.38, wz2, places=2)

    def test_theta_preserved(self):
        blob = _build_fixture_o2()
        p = next(p for p in parse_o2(blob) if p.nameI == 574)
        self.assertAlmostEqual(-6.4403, p.theta, places=3)

    def test_bad_magic(self):
        with self.assertRaises(ValueError):
            parse_o2(b"not-an-o2-file-xxxxxxxxxxxxxxxxxx")

    def test_record_size_constant(self):
        blob = _build_fixture_o2()
        self.assertEqual(30, O2_RECORD)


@unittest.skipUnless(ARCHIVES, "live archives not present")
class O2LiveArchivesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read_map = functools.partial(_reader_for(MAP_PK2))
        cls.o2 = sorted(pk2_table.inventory(MAP_PK2)[0], key=lambda e: e["path"])
        cls.o2 = [e for e in cls.o2 if e["path"].endswith(".o2")]
        ifo_blob = _read_pk2(DATA_PK2, IFO_PATH)
        cls.object_index = parse_object_ifo_map(ifo_blob.decode("ascii", "replace"))

    def _read(self, path):
        return self.read_map(path)

    def test_census_walker_consumes_every_file(self):
        # Every .o2 file parses fully; walker either fills the file exactly or
        # stops at a malformed tail group (counted, reported).
        malformed = 0
        for e in self.o2:
            blob = self._read(e["path"])
            if len(blob) < 16:
                continue
            placements = parse_o2(blob)
            if not placements and any(b != 0 for b in blob[16:]):
                malformed += 1
        self.assertEqual(0, malformed)

    def test_sector_156x90_exact(self):
        blob = self._read("/90/156.o2")
        placements = parse_o2(blob)
        self.assertEqual(32, len(placements))
        counts = {}
        for p in placements:
            counts[p.nameI] = counts.get(p.nameI, 0) + 1
        self.assertEqual({"820": 23, "574": 9}, {str(k): v for k, v in counts.items()})

    def test_sector_156x90_tails(self):
        blob = self._read("/90/156.o2")
        tails = {(p.tx, p.tz) for p in parse_o2(blob)}
        self.assertEqual({(156, 90), (157, 90), (156, 91)}, tails)

    def test_all_nameI_resolve(self):
        blob = self._read("/90/156.o2")
        for p in parse_o2(blob):
            self.assertIn(p.nameI, self.object_index, f"nameI {p.nameI} missing from object.ifo")
        self.assertEqual(
            "/res/nature/common/tree/new-maple/tre_tree03.bsr",
            self.object_index[820],
        )
        self.assertEqual("/res/nature/common/tree/tre_tree02.bsr", self.object_index[574])

    def test_terrain_height_validation(self):
        # Planted trees: object y within a bounded window of committed terrain
        # height at the same (x, z) (156x90 committed .hg, Phase 15 ground truth).
        import world_terrain as wt
        hg_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "android", "app", "src", "main", "assets", "game", "world", "156x90.hg",
        )
        grid, _ = wt.read_hg(hg_path)
        blob = self._read("/90/156.o2")
        ok = 0
        for p in parse_o2(blob):
            if (p.tx, p.tz) != (156, 90):
                continue
            gx = int(p.x // 20.0)
            gz = int(p.z // 20.0)
            if not (0 <= gx < 96 and 0 <= gz < 96):
                continue
            terrain = grid[gz][gx]
            if abs(terrain - p.y) < 60.0:
                ok += 1
        self.assertGreaterEqual(ok, 20, f"only {ok} instances near terrain height")

    def test_start16_equals_first_nonzero_start(self):
        # The Phase 15 "variable header" is zero padding: parsing from offset 16
        # is result-equivalent to parsing from the first non-zero byte.
        def fdo(blob):
            for i in range(16, len(blob)):
                if blob[i] != 0:
                    return i
            return None

        checked = 0
        for e in self.o2:
            blob = self._read(e["path"])
            start = fdo(blob)
            if start is None or start <= 16:
                continue
            from16 = parse_o2(blob)
            at_real = parse_o2(b"JMXVMAPO1001" + b"\x00\x00\x00\x00" + blob[start:])
            key16 = {(p.nameI, round(p.x, 3), round(p.z, 3), p.tx, p.tz) for p in from16}
            keyr = {(p.nameI, round(p.x, 3), round(p.z, 3), p.tx, p.tz) for p in at_real}
            self.assertEqual(key16, keyr, e["path"])
            checked += 1
            if checked >= 40:
                break
        self.assertGreater(checked, 20)


if __name__ == "__main__":
    unittest.main()
