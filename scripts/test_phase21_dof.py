"""Phase 21: .dof dungeon-object container structural tests.

Proven here:
  * .dof (JMXVDOF 0101) 8-u32 section-offset header + embedded .bsr mesh
    references and RN_ region names, on every real Data.pk2 sample.
  * Per-section record layouts (object instances, transforms) remain UNKNOWN.
"""

import functools
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dof_decoder  # noqa: E402

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


def _build_fixture_dof():
    blob = bytearray(b"JMXVDOF 0101")
    # 8-u32 section-offset table; [0]=116 [7]=68 (constants); others 0.
    blob += struct.pack("<8I", 116, 0, 0, 0, 0, 0, 0, 68)
    body = b"Noname" + b"\x00" * 8
    blob += body
    # a couple of length-prefixed strings
    for s in (b"res\\dun\\demo\\x.bsr", b"RN_DEMO_01"):
        blob += struct.pack("<I", len(s)) + s
    return bytes(blob)


class DofFixtureTest(unittest.TestCase):
    def test_roundtrip(self):
        d = dof_decoder.parse_dof(_build_fixture_dof())
        self.assertTrue(d["valid"])
        self.assertEqual([116, 0, 0, 0, 0, 0, 0, 68], d["header_table"])
        self.assertIn("res\\dun\\demo\\x.bsr", d["meshes"])
        self.assertIn("RN_DEMO_01", d["regions"])

    def test_bad_magic(self):
        d = dof_decoder.parse_dof(b"not-a-dof-file-xxxxxxxxxxxxxxx")
        self.assertFalse(d["valid"])


@unittest.skipUnless(ARCHIVES, "live archives not present")
class DofLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read = functools.partial(_reader_for(DATA_PK2))
        import pk2_table

        entries, _ = pk2_table.inventory(DATA_PK2)
        cls.dof = [e for e in entries if e["path"].lower().endswith(".dof")]

    def test_header_invariants(self):
        self.assertTrue(len(self.dof) > 30)
        for e in self.dof:
            d = dof_decoder.parse_dof(self.read(e["path"]))
            self.assertTrue(d["valid"], e["path"])
            self.assertEqual(116, d["header_table"][0], e["path"])
            self.assertEqual(68, d["header_table"][7], e["path"])
            self.assertTrue(d["header_offsets_in_range"], e["path"])

    def test_mesh_references_present(self):
        total = 0
        for e in self.dof:
            d = dof_decoder.parse_dof(self.read(e["path"]))
            total += len(d["meshes"])
            for m in d["meshes"]:
                self.assertTrue(m.lower().endswith(".bsr"), (e["path"], m))
        self.assertGreater(total, 10000)


if __name__ == "__main__":
    unittest.main()
