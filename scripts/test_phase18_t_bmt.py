"""Phase 18: .bmt material + tile2d.ifo index + .t tile-map structural tests.

Proven here:
  * .bmt (JMXVBMT 0102) full record layout -- name, 18 float material props,
    ddj texture path, 7-byte tail -- decodes on every real Data.pk2 sample.
  * tile2d.ifo (JMXV2DTI1001) text index of 719 tiles.
  * .t (JMXVMAPT1001) header/size + cross-referenceable tile IDs; the grid
    layout remains UNKNOWN (see FORMAT_RESEARCH.md).
"""

import functools
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import world_terrain as wt  # noqa: E402

MAP_PK2 = "/tmp/opencode/pk2raw/Map.pk2"
DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"
MEDIA_PK2 = "/tmp/opencode/pk2raw/Media.pk2"

ARCHIVES = os.path.exists(MAP_PK2) and os.path.exists(DATA_PK2)


def _reader_for(pk2):
    import pk2_table

    entries, _ = pk2_table.inventory(pk2)
    by_path = {e["path"].lower(): e for e in entries}
    fh = open(pk2, "rb")

    def read(path):
        e = by_path[path.lower()]
        fh.seek(e["pos"])
        return fh.read(e["size"])

    return read


def _build_fixture_bmt():
    name = b"mat0\x00\x00\x00\x00"   # 4 chars, null-padded to 8
    ddj = b"m.ddj\x00\x00\x00"       # 5 chars, null-padded to 8
    props = struct.pack("<18f", *([0.5] * 3 + [1.0]) * 4 + [0.0, 0.0])
    tail = struct.pack("<f", 1.0) + b"\x20\x08\x00"
    blob = bytearray(b"JMXVBMT 0102")
    blob += struct.pack("<I", 1)
    blob += struct.pack("<I", len(name)) + name + props
    blob += struct.pack("<I", len(ddj)) + ddj + tail
    return bytes(blob)


class BmtFixtureTest(unittest.TestCase):
    def test_hermetic_fixture(self):
        blob = _build_fixture_bmt()
        self.assertEqual(
            wt.BMT_MAGIC_LEN + 4 + 4 + 8 + wt.BMT_PROPS_BYTES + 4 + 8 + wt.BMT_TAIL_BYTES,
            len(blob),
        )
        entries = wt.parse_bmt_entries(blob)
        self.assertEqual(1, len(entries))
        self.assertEqual("mat0", entries[0]["name"])
        self.assertEqual("m.ddj", entries[0]["ddj"])
        self.assertEqual(18, len(entries[0]["props"]))
        self.assertEqual(blob[-wt.BMT_TAIL_BYTES:], entries[0]["tail"])

    def test_padded_strings_stripped(self):
        entries = wt.parse_bmt_entries(_build_fixture_bmt())
        self.assertNotIn("\x00", entries[0]["name"])
        self.assertNotIn("\x00", entries[0]["ddj"])

    def test_dict_wrapper(self):
        self.assertEqual({"mat0": "m.ddj"}, wt.parse_bmt(_build_fixture_bmt()))

    def test_bad_magic(self):
        with self.assertRaises(wt.WorldFormatError):
            wt.parse_bmt_entries(b"not-a-bmt-file-xxxxxxxxxxxxx")


@unittest.skipUnless(ARCHIVES, "live archives not present")
class BmtLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read = functools.partial(_reader_for(DATA_PK2))
        import pk2_table

        entries, _ = pk2_table.inventory(DATA_PK2)
        cls.bmt = [e for e in entries if e["path"].lower().endswith(".bmt")]

    def test_census_all_parse(self):
        self.assertTrue(len(self.bmt) > 4000)
        total = 0
        for e in self.bmt:
            blob = self.read(e["path"])
            self.assertEqual(b"JMXVBMT 0102", blob[:12], e["path"])
            entries = wt.parse_bmt_entries(blob)
            self.assertTrue(entries, e["path"])
            total += len(entries)
        self.assertGreater(total, 16000)

    def test_material_fields_resolve(self):
        blob = self.read("/compound/particle/electus_m_xmas.bmt")
        names = [r["name"] for r in wt.parse_bmt_entries(blob)]
        self.assertIn("electus_m_xmas", names)
        for r in wt.parse_bmt_entries(blob):
            self.assertTrue(r["ddj"].lower().endswith(".ddj"), r["ddj"])


@unittest.skipUnless(ARCHIVES, "live archives not present")
class Tile2dIfoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read = functools.partial(_reader_for(MAP_PK2))

    def test_index_parse(self):
        text = self.read("/tile2d.ifo").decode("ascii", "replace")
        entries = wt.parse_tile2d_ifo(text)
        self.assertEqual(719, len(entries))
        self.assertEqual("JMXV2DTI1001", text.splitlines()[0].strip())
        ids = [e["id"] for e in entries]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(0, ids[0])
        self.assertEqual(718, ids[-1])

    def test_known_entry(self):
        text = self.read("/tile2d.ifo").decode("ascii", "replace")
        idx = wt.tile2d_index(text)
        self.assertEqual("c_grass_hmfld_01.ddj", idx[7]["texture"])
        self.assertEqual(10, idx[7]["flag"])


@unittest.skipUnless(ARCHIVES, "live archives not present")
class TFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read_map = functools.partial(_reader_for(MAP_PK2))
        cls.read_media = functools.partial(_reader_for(MEDIA_PK2))
        cls.idx = wt.tile2d_index(cls.read_map("/tile2d.ifo").decode("ascii", "replace"))

    def test_standard_header_and_size(self):
        blob = self.read_map("/100/100.t")
        info = wt.parse_t(blob, self.idx)
        self.assertEqual("JMXVMAPT1001", info["magic"])
        self.assertEqual(140436, info["size"])
        self.assertEqual(140424, info["body_size"])

    def test_tile_ids_cross_reference(self):
        blob = self.read_map("/100/100.t")
        info = wt.parse_t(blob, self.idx)
        self.assertGreater(info["tile_count"], 0)
        for tid in info["tile_ids"]:
            self.assertIn(tid, self.idx, tid)

    def test_bad_magic(self):
        with self.assertRaises(wt.WorldFormatError):
            wt.parse_t(b"not-a-t-file-xxxxxxxxxxxxxxxxxxxxx")

    def test_anomaly_83_13_is_misnamed_m(self):
        blob = self.read_map("/88/83_13.t")
        self.assertEqual(b"JMXVMAPM1000", blob[:12])

    def test_media_svt_is_small(self):
        blob = self.read_media("/SV.T")
        self.assertEqual(1024, len(blob))


if __name__ == "__main__":
    unittest.main()
