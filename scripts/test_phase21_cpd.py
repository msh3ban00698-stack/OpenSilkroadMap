"""Phase 21: .cpd compound-manifest structural tests.

Proven here:
  * .cpd (JMXVCPD 0101) full container layout -- magic, primary/count offsets,
    reserved block, type/subtype, name, flag_x/flag_y, optional primary .bsr
    path, and a count-prefixed list of component .bsr paths -- decodes on every
    real Data.pk2 sample byte-exactly.
  * flag_x / flag_y are decoded u32 values; their exact semantics remain
    UNKNOWN (see FORMAT_RESEARCH.md).
"""

import functools
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cpd_decoder  # noqa: E402

DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"

ARCHIVES = os.path.exists(DATA_PK2)


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


def _build_fixture_cpd(name, primary_path, paths, typ=2, flag_x=0, flag_y=0):
    blob = bytearray(b"JMXVCPD 0101")
    name_b = name.encode("latin1")
    primary_b = primary_path.encode("latin1")
    ne = cpd_decoder.NAME_OFFSET + len(name_b)
    primary_off = ne + 8
    count_off = ne + 12 + len(primary_b)
    blob += struct.pack("<II", primary_off, count_off)
    blob += b"\x00" * 20
    blob += struct.pack("<HH", typ, 3)
    blob += struct.pack("<I", len(name_b))
    blob += name_b
    blob += struct.pack("<II", flag_x, flag_y)
    blob += struct.pack("<I", len(primary_b))
    blob += primary_b
    blob += struct.pack("<I", len(paths))
    for p in paths:
        pb = p.encode("latin1")
        blob += struct.pack("<I", len(pb)) + pb
    return bytes(blob)


class CpdFixtureTest(unittest.TestCase):
    def test_roundtrip_with_primary(self):
        blob = _build_fixture_cpd(
            "bagh_minga_h_01",
            "res\\bldg\\bagh_minga_h_01.bsr",
            ["res\\bldg\\bagh_minga_h_01.bsr", "res\\bldg\\bagh_minga_h_01_shadow.bsr"],
        )
        d = cpd_decoder.parse_cpd(blob)
        self.assertTrue(d["valid"])
        self.assertTrue(d["byte_exact"])
        self.assertTrue(d["count_self_consistent"])
        self.assertTrue(d["reserved_zero"])
        self.assertEqual("bagh_minga_h_01", d["name"])
        self.assertEqual("res\\bldg\\bagh_minga_h_01.bsr", d["primary_path"])
        self.assertEqual(2, d["count"])
        self.assertEqual(2, len(d["paths"]))

    def test_roundtrip_no_primary(self):
        blob = _build_fixture_cpd(
            "cj_waterfall01",
            "",
            ["res\\nature\\particle\\oa_ho_waterfall01_01-1.bsr"],
            flag_x=3, flag_y=2,
        )
        d = cpd_decoder.parse_cpd(blob)
        self.assertTrue(d["valid"])
        self.assertTrue(d["byte_exact"])
        self.assertEqual("", d["primary_path"])
        self.assertEqual(3, d["flag_x"])
        self.assertEqual(2, d["flag_y"])
        self.assertEqual(1, len(d["paths"]))

    def test_character_type(self):
        blob = _build_fixture_cpd(
            "1", "", ["res\\char\\china\\chinaman_warrior.bsr"], typ=0,
        )
        d = cpd_decoder.parse_cpd(blob)
        self.assertTrue(d["valid"])
        self.assertEqual(0, d["type"])

    def test_bad_magic(self):
        d = cpd_decoder.parse_cpd(b"not-a-cpd-file-xxxxxxxxxxxxxxx")
        self.assertFalse(d["valid"])


@unittest.skipUnless(ARCHIVES, "live archives not present")
class CpdLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read = functools.partial(_reader_for(DATA_PK2))
        import pk2_table

        entries, _ = pk2_table.inventory(DATA_PK2)
        cls.cpd = [e for e in entries if e["path"].lower().endswith(".cpd")]

    def test_census_all_parse_byte_exact(self):
        self.assertTrue(len(self.cpd) > 100)
        for e in self.cpd:
            d = cpd_decoder.parse_cpd(self.read(e["path"]))
            self.assertTrue(d["valid"], e["path"])
            self.assertTrue(d["byte_exact"], e["path"])
            self.assertTrue(d["count_self_consistent"], e["path"])
            self.assertTrue(d["reserved_zero"], e["path"])
            self.assertEqual(3, d["subtype"], e["path"])

    def test_component_paths_are_bsr(self):
        for e in self.cpd:
            d = cpd_decoder.parse_cpd(self.read(e["path"]))
            for p in d["paths"]:
                self.assertTrue(p.lower().endswith(".bsr"), (e["path"], p))

    def test_type_split(self):
        types = {e["path"]: cpd_decoder.parse_cpd(self.read(e["path"]))["type"]
                 for e in self.cpd}
        self.assertIn(0, set(types.values()))
        self.assertIn(2, set(types.values()))


if __name__ == "__main__":
    unittest.main()
