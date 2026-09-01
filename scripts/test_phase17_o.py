"""Phase 17 (follow-up): .o object-placement decoding tests (28-byte records).

.o shares the JMXVMAPO1001 magic and group framing with .o2 but uses a 28-byte
record (drops the always-zero unknown3 u16), so its tail sits at offset 26.
"""

import functools
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from o2_decoder import O_RECORD, O2_MAGIC, Placement, parse_o  # noqa: E402

MAP_PK2 = "/tmp/opencode/pk2raw/Map.pk2"
DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"
IFO_PATH = "/navmesh/object.ifo"

ARCHIVES = os.path.exists(MAP_PK2) and os.path.exists(DATA_PK2)

if ARCHIVES:
    import pk2_table  # noqa: E402


def _read_pk2(pk2, path):
    entries, _ = pk2_table.inventory(pk2)
    hit = next(e for e in entries if e["path"].lower() == path.lower())
    with open(pk2, "rb") as fh:
        fh.seek(hit["pos"])
        return fh.read(hit["size"])


def _reader_for(pk2):
    entries, _ = pk2_table.inventory(pk2)
    by_path = {e["path"].lower(): e for e in entries}
    fh = open(pk2, "rb")

    def read(path):
        e = by_path[path.lower()]
        fh.seek(e["pos"])
        return fh.read(e["size"])

    return read


def _build_fixture_o():
    rec_a = struct.pack("<IfffHfHHH", 820, 10.0, 5.0, 20.0, 0, 0.0, 0x0101, 0, 0)
    rec_b = struct.pack("<IfffHfHHH", 574, 30.0, 6.0, 40.0, 0xFFFF, -6.44, 0x0102, 0, 0)
    rec_c = struct.pack("<IfffHfHHH", 820, 50.0, 7.0, 60.0, 0, 0.0, 0x0201, 0, 1)
    blob = bytearray(b"JMXVMAPO1001" + b"\x00\x00\x00\x00")
    blob += struct.pack("<H", 2) + rec_a + rec_b
    blob += struct.pack("<H", 1) + rec_c
    blob += struct.pack("<H", 0)
    return bytes(blob)


class OFixturesTest(unittest.TestCase):
    def test_hermetic_fixture(self):
        blob = _build_fixture_o()
        self.assertEqual(len(blob), 12 + 4 + 3 * 2 + 3 * O_RECORD)
        placements = parse_o(blob)
        self.assertEqual(3, len(placements))
        self.assertEqual([820, 574, 820], [p.nameI for p in placements])

    def test_record_size_constant(self):
        self.assertEqual(28, O_RECORD)

    def test_tail_relative_encoding(self):
        blob = _build_fixture_o()
        placements = parse_o(blob)
        self.assertEqual(0, placements[0].tail)
        self.assertEqual(1, placements[2].tail)

    def test_theta_preserved(self):
        blob = _build_fixture_o()
        p = next(p for p in parse_o(blob) if p.nameI == 574)
        self.assertAlmostEqual(-6.44, p.theta, places=2)

    def test_bad_magic(self):
        with self.assertRaises(ValueError):
            parse_o(b"not-an-o-file-xxxxxxxxxxxxxxxxxx")

    def test_unknown3_absent(self):
        blob = _build_fixture_o()
        self.assertTrue(all(p.unknown3 == 0 for p in parse_o(blob)))


@unittest.skipUnless(ARCHIVES, "live archives not present")
class OLiveArchivesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read_map = functools.partial(_reader_for(MAP_PK2))
        entries, _ = pk2_table.inventory(MAP_PK2)
        cls.o = [e for e in entries if e["path"].endswith(".o")]
        ifo_blob = _read_pk2(DATA_PK2, IFO_PATH)
        from o2_decoder import parse_object_ifo_map
        cls.object_index = parse_object_ifo_map(ifo_blob.decode("ascii", "replace"))

    def _read(self, path):
        return self.read_map(path)

    def test_census_walker_consumes_every_file(self):
        malformed = 0
        for e in self.o:
            blob = self._read(e["path"])
            if len(blob) < 16:
                continue
            if blob[:12] != O2_MAGIC:
                continue
            placements = parse_o(blob)
            if not placements and any(b != 0 for b in blob[16:]):
                malformed += 1
        self.assertEqual(0, malformed)

    def test_sector_100x100_exact(self):
        blob = self._read("/100/100.o")
        placements = parse_o(blob)
        self.assertEqual(58, len(placements))
        counts = {}
        for p in placements:
            counts[p.nameI] = counts.get(p.nameI, 0) + 1
        self.assertEqual({1489: 39, 669: 11, 1488: 7, 1748: 1}, counts)

    def test_all_nameI_resolve(self):
        blob = self._read("/100/100.o")
        for p in parse_o(blob):
            self.assertIn(p.nameI, self.object_index, f"nameI {p.nameI} missing from object.ifo")


if __name__ == "__main__":
    unittest.main()
