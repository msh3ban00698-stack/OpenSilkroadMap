#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from misc_decoder import parse_rd, parse_2dt, parse_mfo, parse_msf, parse_pe, parse_bak


def _rd_fixture():
    import struct
    buf = bytearray(1078 + 256)
    buf[0:2] = b"BM"
    struct.pack_into("<I", buf, 2, len(buf))
    struct.pack_into("<I", buf, 10, 1078)
    struct.pack_into("<i", buf, 18, 16)
    struct.pack_into("<i", buf, 22, 16)
    struct.pack_into("<H", buf, 28, 8)
    return bytes(buf)


class TestMiscDecoders(unittest.TestCase):
    def test_rd_bmp(self):
        r = parse_rd(_rd_fixture())
        self.assertTrue(r["valid"])
        self.assertEqual((r["width"], r["height"], r["bpp"]), (16, 16, 8))

    def test_rd_not_bmp(self):
        self.assertFalse(parse_rd(b"\x00" * 64)["valid"])

    def test_2dt_cnif(self):
        data = b"\x07\x00\x00\x00CNIFBattleArenaScoreWnd\x00" + b"\x00" * 64
        r = parse_2dt(data)
        self.assertTrue(r["valid"])
        self.assertEqual(r["name"], "BattleArenaScoreWnd")
        self.assertEqual(r["field0"], 7)

    def test_2dt_not_cnif(self):
        self.assertFalse(parse_2dt(b"\x00" * 64)["valid"])

    def test_mfo(self):
        data = b"JMXVMFO 1000" + b"\x00\x01\x80\x00" + b"\x00" * 64
        r = parse_mfo(data)
        self.assertTrue(r["valid"])
        self.assertEqual((r["width"], r["height"]), (256, 128))

    def test_msf(self):
        data = b"\x01\x00\x00\x00" + b"\x02\x00\x00\x00" + b"\xff\xff\xff\xff" + \
               b"\x07\x00\x00\x00" + b"ambient" + b"\x00" + b"\x00" * 64
        r = parse_msf(data)
        self.assertTrue(r["valid"])
        self.assertEqual(r["name"], "ambient")
        self.assertEqual(r["count"], 1)

    def test_pe(self):
        data = bytearray(0x80)
        data[0:2] = b"MZ"
        import struct
        struct.pack_into("<I", data, 0x3C, 0x40)
        data[0x40:0x44] = b"PE\x00\x00"
        self.assertTrue(parse_pe(bytes(data))["valid"])
        self.assertFalse(parse_pe(b"\x00" * 64)["valid"])

    def test_bak(self):
        self.assertTrue(parse_bak(b"TAPE" + b"\x00" * 32)["valid"])
        self.assertFalse(parse_bak(b"\x00" * 32)["valid"])


if __name__ == "__main__":
    unittest.main()
