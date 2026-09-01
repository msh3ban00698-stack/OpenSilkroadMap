"""Deterministic tests for the `.dat` family classifier (dat_families.py).

Synthetic fixtures validate the header probes with no archive dependency. Live
tests re-verify against real archive samples when present, else SKIP.

Running:
    python3 scripts/test_dat_families.py
"""

import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import dat_families

DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"
MEDIA_PK2 = "/tmp/opencode/pk2raw/Media.pk2"


def make_bmp():
    header = b"BM" + struct.pack("<I", 0) + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00"
    return header + b"\x00" * 64


def make_jmxvimg(h, w):
    return b"JMXVIMG11000" + struct.pack("<HH", h, w) + b"\x00" * (4 * h * w)


def make_ainavdata(nav_id, count):
    blob = bytearray(24)
    blob[0] = 0x01
    struct.pack_into("<I", blob, 1, count)
    struct.pack_into("<H", blob, 5, nav_id)
    return bytes(blob) + b"\x00" * 64


class DdtClassifierTests(unittest.TestCase):
    def test_bmp(self):
        r = dat_families.classify_dat(make_bmp(), "x.dat")
        self.assertEqual(r["family"], "bmp")
        self.assertEqual(r["status"], "PROVEN")

    def test_jmxvimg(self):
        r = dat_families.classify_dat(make_jmxvimg(7, 3), "0.dat")
        self.assertEqual(r["family"], "jmxvimg")
        self.assertEqual(r["pixels_4byte"], 21)

    def test_ainavdata(self):
        r = dat_families.classify_dat(make_ainavdata(0x8013, 3169), "ainavdata_32787.dat")
        self.assertEqual(r["family"], "ainavdata")
        self.assertEqual(r["nav_id"], 0x8013)
        self.assertEqual(r["status"], "PARTIAL")

    def test_ainavdata_header_fields(self):
        blob = bytearray(24)
        blob[0] = 0x01
        struct.pack_into("<I", blob, 1, 3169)   # vertex_section_offset
        struct.pack_into("<H", blob, 5, 0x8013)  # nav_id
        blob[7] = 0x01
        struct.pack_into(">H", blob, 14, 28)     # count_a (BE)
        struct.pack_into(">H", blob, 18, 28)     # count_b (BE)
        r = dat_families.parse_ainavdata(bytes(blob))
        self.assertEqual(r["vertex_section_offset"], 3169)
        self.assertEqual(r["count_a"], 28)
        self.assertEqual(r["count_b"], 28)
        self.assertEqual(r["type_byte"], 0x01)

    def test_plugin(self):
        blob = struct.pack("<I", 1) + bytes(range(16)) + struct.pack("<H", 11) + b"bsnetEx.dll"
        r = dat_families.classify_dat(blob, "plugin.dat")
        self.assertEqual(r["family"], "plugin")
        self.assertEqual(r["status"], "PROVEN")
        self.assertEqual(r["entries"][0]["name"], "bsnetEx.dll")

    def test_config_tiny_count_prefix(self):
        blob = struct.pack("<I", 1) + b"\x01\x00"
        r = dat_families.classify_dat(blob, "SRExtQSOption2.dat")
        self.assertEqual(r["family"], "config")
        self.assertEqual(r["status"], "PARTIAL")

    def test_hex_token(self):
        r = dat_families.classify_dat(b"660970B4E849D93E", "Silkload.dat")
        self.assertEqual(r["family"], "hex-token")

    def test_palette(self):
        r = dat_families.classify_dat(b"\x00" * 768, "silk.dat")
        self.assertEqual(r["family"], "palette")

    def test_config(self):
        r = dat_families.classify_dat(struct.pack("<I", 3) + b"\x00" * 20, "wndpos.dat")
        self.assertEqual(r["family"], "config")

    def test_unknown(self):
        r = dat_families.classify_dat(b"\xde\xad\xbe\xef" * 16, "plugin.dat")
        self.assertEqual(r["family"], "unknown")


class DdtLiveTests(unittest.TestCase):
    def test_live_ainavdata_id_match(self):
        if not Path(DATA_PK2).is_file():
            self.skipTest("Data.pk2 unavailable")
        import pk2_table
        files, _ = pk2_table.inventory(DATA_PK2)
        dats = [f for f in files if f["path"].lower().startswith("/navmesh/ainavdata")]
        self.assertGreaterEqual(len(dats), 26)
        with open(DATA_PK2, "rb") as fh:
            for f in dats:
                fh.seek(f["pos"])
                blob = fh.read(min(64, f["size"]))
                r = dat_families.classify_dat(blob, f["path"])
                self.assertEqual(r["family"], "ainavdata", f["path"])
                fid = int(f["path"].lower().rsplit("_", 1)[1].split(".")[0])
                self.assertEqual(r["nav_id"], 0x8000 | fid, f["path"])

    def test_live_launcher_bmp(self):
        if not Path(MEDIA_PK2).is_file():
            self.skipTest("Media.pk2 unavailable")
        import pk2_table
        files, _ = pk2_table.inventory(MEDIA_PK2)
        launcher = [f for f in files if f["path"].startswith("/launcher/")
                    and f["path"].endswith(".dat")]
        self.assertGreaterEqual(len(launcher), 40)
        with open(MEDIA_PK2, "rb") as fh:
            for f in launcher:
                fh.seek(f["pos"])
                blob = fh.read(min(8, f["size"]))
                r = dat_families.classify_dat(blob, f["path"])
                self.assertEqual(r["family"], "bmp", f["path"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
