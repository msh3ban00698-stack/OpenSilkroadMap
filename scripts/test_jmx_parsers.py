"""Deterministic tests for the JMX binary parsers (jmx_ddj.py, jmx_nvm.py).

Synthetic fixtures validate parser arithmetic with no archive dependency. Live
tests re-verify against real `.ddj`/`.nvm` samples when present, else SKIP.

Running:
    python3 scripts/test_jmx_parsers.py
"""

import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import jmx_ddj
import jmx_nvm

DDJ_MAGIC = b"JMXVDDJ 1000"
NVM_MAGIC = b"JMXVNVM 1000"

SAMPLE_DIRS = [
    "/tmp/opencode/jmx_samples",
    "/tmp/opencode/phase4/full_extract",
]


def make_dds_header(width, height, bpp, pf_flags, fourcc=b"\x00\x00\x00\x00"):
    pf = (struct.pack("<II", 32, pf_flags) + fourcc
          + struct.pack("<IIIII", bpp, 0xFF0000, 0x00FF00, 0x0000FF, 0))
    return (b"DDS " + struct.pack("<IIIIIII", 124, 0x1007, height, width, 0, 0, 0)
            + b"\x00" * 44 + pf + b"\x00" * 20)


def make_ddj(width, height, bpp, pf_flags, fourcc=b"\x00\x00\x00\x00"):
    body = make_dds_header(width, height, bpp, pf_flags, fourcc)
    data_size = len(body) + 8
    blob = DDJ_MAGIC + struct.pack("<I", data_size) + struct.pack("<I", 3) + body
    return blob


def find_sample(names):
    for d in SAMPLE_DIRS:
        for name in names:
            p = Path(d) / name
            if p.is_file():
                return str(p)
    return None


class DdjParserTests(unittest.TestCase):
    def test_synthetic_rgb(self):
        blob = make_ddj(32, 32, 16, 0x41)
        r = jmx_ddj.parse_ddj(blob, "synth.ddj")
        self.assertTrue(r["valid"])
        self.assertTrue(r["data_size_matches"])
        self.assertEqual(r["data_size"], len(blob) - 12)
        self.assertEqual(r["level_field"], 3)
        self.assertEqual(r["dds_offset"], 20)
        self.assertEqual(r["dds"]["width"], 32)
        self.assertEqual(r["dds"]["height"], 32)
        self.assertEqual(r["dds"]["rgb_bit_count"], 16)
        self.assertTrue(r["dds"]["is_rgb"])
        self.assertFalse(r["dds"]["is_fourcc"])

    def test_synthetic_fourcc(self):
        blob = make_ddj(64, 64, 0, 0x4, fourcc=b"DXT3")
        r = jmx_ddj.parse_ddj(blob)
        self.assertTrue(r["valid"])
        self.assertTrue(r["dds"]["is_fourcc"])
        self.assertEqual(r["dds"]["fourcc"], "DXT3")

    def test_bad_magic(self):
        r = jmx_ddj.parse_ddj(b"X" * 40)
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], "bad magic")

    def test_live_samples(self):
        sample = find_sample(["Media/icon/action/cos_cmd_inventory_open.ddj"])
        if not sample:
            self.skipTest("no .ddj sample available")
        with open(sample, "rb") as fh:
            blob = fh.read()
        r = jmx_ddj.parse_ddj(blob, sample)
        self.assertTrue(r["valid"])
        self.assertTrue(r["data_size_matches"])
        self.assertEqual(r["level_field"], 3)
        self.assertEqual(r["dds"]["width"], 32)
        self.assertEqual(r["dds"]["height"], 32)


class NvmParserTests(unittest.TestCase):
    def make_nvm(self, grid_records, fill_words):
        body = b""
        for i in range(grid_records):
            body += struct.pack("<4H", 0, i % 2, 279, 1000 + i)
        body += b"\x01" * 40
        body += jmx_nvm.FILL_WORD * fill_words
        blob = NVM_MAGIC + body
        return blob

    def test_synthetic_grid_and_fill(self):
        blob = self.make_nvm(9216, 36)
        r = jmx_nvm.parse_nvm(blob)
        self.assertTrue(r["valid"])
        self.assertTrue(r["grid_is_96x96"])
        self.assertEqual(r["grid_record_count"], 9216)
        self.assertEqual(r["trailing_fill_words"], 36)

    def test_bad_magic(self):
        r = jmx_nvm.parse_nvm(b"X" * 40)
        self.assertFalse(r["valid"])

    def test_live_nv_198c(self):
        sample = find_sample(["nv_198c.nvm"])
        if not sample:
            self.skipTest("no .nvm sample available")
        with open(sample, "rb") as fh:
            blob = fh.read()
        r = jmx_nvm.parse_nvm(blob, sample)
        self.assertTrue(r["valid"])
        self.assertTrue(r["grid_is_96x96"])
        self.assertEqual(r["grid_record_count"], 9216)
        self.assertEqual(r["trailing_fill_words"], 36)


if __name__ == "__main__":
    unittest.main(verbosity=2)
