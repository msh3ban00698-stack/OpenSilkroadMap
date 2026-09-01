"""Phase 21: .ifo polymorphic family structural tests.

Proven here:
  * layerobjectlist.ifo (JMXVOBJL1000) TEXT object-placement list: magic line +
    decimal count + 9-field entries; all 3,334 entries parse with count==entries
    and every id's top 16 bits equal to (sector_y << 8) | sector_x.
  * config.ifo (JMXVCAMR1002) camera binary: magic only (fields UNKNOWN).
  * environment.ifo (JMXVENVI1003) environment binary: magic + name (Env7).
"""

import functools
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ifo_decoder  # noqa: E402

MAP_PK2 = "/tmp/opencode/pk2raw/Map.pk2"

ARCHIVES = os.path.exists(MAP_PK2)


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


def _build_fixture_objl():
    line0 = "JMXVOBJL1000"
    line1 = "1"
    entry = "0x61a89407 9 168 97 0x44c9f49d 0xc19a7e32 0x44afd147 0x3fc90fd8 1"
    return "\n".join([line0, line1, entry])


class LayerObjectListFixtureTest(unittest.TestCase):
    def test_roundtrip(self):
        d = ifo_decoder.parse_layerobjectlist_ifo(_build_fixture_objl())
        self.assertTrue(d["valid"])
        self.assertTrue(d["count_matches"])
        self.assertEqual(1, len(d["entries"]))
        e = d["entries"][0]
        self.assertEqual(9, e["type"])
        self.assertEqual((168, 97), (e["sector_x"], e["sector_y"]))
        self.assertAlmostEqual(1.5707964, e["theta"], places=6)

    def test_bad_magic(self):
        d = ifo_decoder.parse_layerobjectlist_ifo("NOTMAGIC\n1\n")
        self.assertFalse(d["valid"])


@unittest.skipUnless(ARCHIVES, "live archives not present")
class IfoLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read = functools.partial(_reader_for(MAP_PK2))

    def test_layerobjectlist_full(self):
        text = self.read("/layerobjectlist.ifo").decode("ascii", "replace")
        d = ifo_decoder.parse_layerobjectlist_ifo(text)
        self.assertTrue(d["valid"])
        self.assertTrue(d["count_matches"])
        self.assertEqual(3334, len(d["entries"]))
        for e in d["entries"]:
            top = (e["id"] >> 16) & 0xFFFF
            self.assertEqual((e["sector_y"] << 8) | e["sector_x"], top)

    def test_camera_magic(self):
        b = self.read("/config.ifo")
        d = ifo_decoder.parse_camera_ifo(b)
        self.assertTrue(d["valid"])
        self.assertEqual(b"JMXVCAMR1002", d["magic"])

    def test_environment_magic_name(self):
        b = self.read("/environment.ifo")
        d = ifo_decoder.parse_environment_ifo(b)
        self.assertTrue(d["valid"])
        self.assertEqual("Env7", d["name"])


if __name__ == "__main__":
    unittest.main()
