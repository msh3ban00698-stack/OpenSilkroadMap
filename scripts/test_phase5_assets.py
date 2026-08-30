"""Tests for Phase 5: DDJ/DDS decoding, deterministic PNG output, and manifest
consistency for the generated android-assets tree.

These run WITHOUT the real 4.8 GB PK2 dataset: decoder tests use synthetic
in-memory DDS/DDJ blobs with hand-computed expected pixels, and the manifest
tests validate the committed android-assets/ outputs. When Pillow is installed
the pure-Python decoder is additionally cross-checked against Pillow's DDS
plugin; when SRO_PHASE5_SAMPLES points at a Phase 4 controlled extraction dir
(e.g. /tmp/opencode/phase4/extract) real vSRO samples are cross-checked too.

Running:
    python3 scripts/test_phase5_assets.py
"""

import hashlib
import io
import json
import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from dds_decode import (  # noqa: E402
    InvalidDDS,
    UnsupportedPixelFormat,
    ddj_to_rgba,
    decode_dds,
    png_from_rgba,
    parse_png_header,
)

DDPF_ALPHAPIXELS = 0x1
DDPF_FOURCC = 0x4
DDPF_RGB = 0x40


def make_dds(width, height, pixel_data, fourcc=None, bitcount=0,
             masks=(0, 0, 0, 0), pf_flags=DDPF_FOURCC, mipmaps=0):
    hdr = bytearray()
    hdr += b"DDS "
    flags = 0x1000 | 0x2 | 0x4 | 0x80000
    hdr += struct.pack("<7I", 124, flags, height, width, 0, 0, mipmaps)
    hdr += b"\x00" * 44
    hdr += struct.pack("<II4sIIIII", 32, pf_flags,
                       fourcc or b"\x00\x00\x00\x00", bitcount, *masks)
    hdr += struct.pack("<4I", 0x1000, 0, 0, 0)
    hdr += b"\x00" * 4
    return bytes(hdr) + pixel_data


def make_ddj(payload):
    return b"JMXVDDJ 1000" + b"\x00" * 8 + payload


class DDCDecodeTests(unittest.TestCase):
    def test_dxt1_fourcolor_known_pixels(self):
        # color0 = 0xFFFF (white), color1 = 0x0000 (black), c0>c1 -> 4-color.
        # palette: [white, black, (170,170,170), (85,85,85)]
        # index byte 0xE4 = bits 00,01,10,11 -> indices 0,1,2,3 per row.
        block = struct.pack("<HH4B", 0xFFFF, 0x0000, 0xE4, 0xE4, 0xE4, 0xE4)
        dds = make_dds(4, 4, block, fourcc=b"DXT1")
        w, h, px = decode_dds(dds)
        self.assertEqual((w, h), (4, 4))
        expected_row = [(255, 255, 255, 255), (0, 0, 0, 255),
                        (170, 170, 170, 255), (85, 85, 85, 255)]
        for r in range(4):
            for c in range(4):
                self.assertEqual(px[r * 4 + c], expected_row[c])

    def test_dxt1_3color_transparent(self):
        # color0 < color1 -> 3-color mode; index 3 is transparent.
        # color0=0x0000 black, color1=0xFFFF white -> p2=(127,127,127)
        block = struct.pack("<HH4B", 0x0000, 0xFFFF, 0xE4, 0xE4, 0xE4, 0xE4)
        dds = make_dds(4, 4, block, fourcc=b"DXT1")
        w, h, px = decode_dds(dds)
        self.assertEqual(px[0], (0, 0, 0, 255))
        self.assertEqual(px[1], (255, 255, 255, 255))
        self.assertEqual(px[3], (0, 0, 0, 0))  # transparent index 3

    def test_dxt3_alpha_and_color(self):
        # alpha bytes: low nibble = even pixel, high nibble = odd pixel.
        # rows 0-1 alpha=255 (byte 0xFF), rows 2-3 alpha=0 (byte 0x00).
        alpha = bytes([0xFF] * 4 + [0x00] * 4)
        color = struct.pack("<HH4B", 0xFFFF, 0x0000, 0xE4, 0xE4, 0xE4, 0xE4)
        dds = make_dds(4, 4, alpha + color, fourcc=b"DXT3")
        w, h, px = decode_dds(dds)
        self.assertEqual(px[0], (255, 255, 255, 255))
        self.assertEqual(px[1], (0, 0, 0, 255))
        self.assertEqual(px[2], (170, 170, 170, 255))
        self.assertEqual(px[3], (85, 85, 85, 255))
        self.assertEqual(px[8], (255, 255, 255, 0))   # row 2, alpha 0
        self.assertEqual(px[9], (0, 0, 0, 0))

    def test_rgb565(self):
        data = struct.pack("<H", 0xF800 | 0x07E0 | 0x001F) * 4  # all white RGB565
        dds = make_dds(2, 2, data, fourcc=b"\x00\x00\x00\x00", bitcount=16,
                       masks=(0xF800, 0x07E0, 0x001F, 0x0000), pf_flags=DDPF_RGB)
        w, h, px = decode_dds(dds)
        self.assertTrue(all(p == (255, 255, 255, 255) for p in px))

    def test_argb1555(self):
        # 0xFFFF = a=1 (opaque) + white, 0x8000 = a=1 + black (bit15 is alpha)
        data = struct.pack("<H", 0xFFFF) + struct.pack("<H", 0x8000)
        dds = make_dds(1, 2, data, fourcc=b"\x00\x00\x00\x00", bitcount=16,
                       masks=(0x7C00, 0x03E0, 0x001F, 0x8000),
                       pf_flags=DDPF_RGB | DDPF_ALPHAPIXELS)
        w, h, px = decode_dds(dds)
        self.assertEqual(px[0], (255, 255, 255, 255))
        self.assertEqual(px[1], (0, 0, 0, 255))

    def test_x8r8g8b8(self):
        data = struct.pack("<I", 0x00FF0000 | 0x0000FF00 | 0x000000FF)
        dds = make_dds(1, 1, data, fourcc=b"\x00\x00\x00\x00", bitcount=32,
                       masks=(0x00FF0000, 0x0000FF00, 0x000000FF, 0x00000000),
                       pf_flags=DDPF_RGB)
        w, h, px = decode_dds(dds)
        self.assertEqual(px[0], (255, 255, 255, 255))

    def test_a8r8g8b8(self):
        data = struct.pack("<I", 0x80000000 | 0x00FF0000 | 0x000000FF)
        dds = make_dds(1, 1, data, fourcc=b"\x00\x00\x00\x00", bitcount=32,
                       masks=(0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000),
                       pf_flags=DDPF_RGB | DDPF_ALPHAPIXELS)
        w, h, px = decode_dds(dds)
        self.assertEqual(px[0], (255, 0, 255, 128))

    def test_unsupported_dxt5_refused(self):
        dds = make_dds(4, 4, b"\x00" * 16, fourcc=b"DXT5")
        with self.assertRaises(UnsupportedPixelFormat):
            decode_dds(dds)

    def test_bad_magic_rejected(self):
        with self.assertRaises(InvalidDDS):
            decode_dds(b"NOPE" + b"\x00" * 128)

    def test_ddj_container_roundtrip(self):
        block = struct.pack("<HH4B", 0xFFFF, 0x0000, 0xE4, 0xE4, 0xE4, 0xE4)
        dds = make_dds(4, 4, block, fourcc=b"DXT1")
        w, h, px = ddj_to_rgba(make_ddj(dds))
        self.assertEqual((w, h), (4, 4))
        self.assertEqual(px[0], (255, 255, 255, 255))

    def test_bad_ddj_magic_rejected(self):
        with self.assertRaises(InvalidDDS):
            ddj_to_rgba(b"JUNKDDJ1000" + b"\x00" * 8 + b"\x00" * 128)


class PNGDeterminismTests(unittest.TestCase):
    def test_png_byte_deterministic(self):
        block = struct.pack("<HH4B", 0xFFFF, 0x0000, 0xE4, 0xE4, 0xE4, 0xE4)
        w, h, px = decode_dds(make_dds(4, 4, block, fourcc=b"DXT1"))
        a = png_from_rgba(w, h, px)
        b = png_from_rgba(w, h, px)
        self.assertEqual(a, b)

    def test_png_header_valid(self):
        block = struct.pack("<HH4B", 0xFFFF, 0x0000, 0xE4, 0xE4, 0xE4, 0xE4)
        w, h, px = decode_dds(make_dds(4, 4, block, fourcc=b"DXT1"))
        png = png_from_rgba(w, h, px)
        pw, ph, bd, ct = parse_png_header(png)
        self.assertEqual((pw, ph), (4, 4))
        self.assertEqual(bd, 8)
        self.assertEqual(ct, 6)  # RGBA


class PillowCrossCheckTests(unittest.TestCase):
    def test_pillow_matches_on_real_samples(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        samples_dir = os.environ.get("SRO_PHASE5_SAMPLES")
        if not samples_dir or not os.path.isdir(samples_dir):
            self.skipTest("SRO_PHASE5_SAMPLES not set")
        found = 0
        for root, _dirs, files in os.walk(samples_dir):
            for f in files:
                if not f.endswith(".ddj"):
                    continue
                path = os.path.join(root, f)
                with open(path, "rb") as fh:
                    data = fh.read()
                try:
                    w, h, px = ddj_to_rgba(data)
                except (InvalidDDS, UnsupportedPixelFormat):
                    continue
                pil = Image.open(io.BytesIO(data[20:])).convert("RGBA")
                self.assertEqual((w, h), pil.size)
                self.assertEqual(px, list(pil.getdata()))
                found += 1
        self.assertGreater(found, 0, "no real .ddj samples found to cross-check")


class ManifestConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.manifest_path = REPO / "android-assets" / "manifest.json"
        if not self.manifest_path.exists():
            self.skipTest("android-assets/manifest.json not present")

    def test_manifest_records_match_output_files(self):
        manifest = json.loads(self.manifest_path.read_text())
        self.assertEqual(manifest["failures"], 0)
        self.assertTrue(manifest["records"])
        for rec in manifest["records"]:
            self.assertEqual(rec["result"], "ok", rec)
            out = REPO / "android-assets" / rec["output_path"]
            self.assertTrue(out.exists(), rec["output_path"])
            h = hashlib.sha256(out.read_bytes()).hexdigest()
            self.assertEqual(h, rec["output_sha256"], rec["output_path"])

    def test_manifest_png_dimensions(self):
        manifest = json.loads(self.manifest_path.read_text())
        for rec in manifest["records"]:
            if not rec["output_path"].endswith(".png"):
                continue
            out = REPO / "android-assets" / rec["output_path"]
            w, h, _bd, _ct = parse_png_header(out.read_bytes())
            self.assertEqual((w, h), (rec["width"], rec["height"]), rec["output_path"])

    def test_manifest_audio_metadata(self):
        manifest = json.loads(self.manifest_path.read_text())
        audio = {r["output_path"]: r for r in manifest["records"]
                 if r["output_path"].startswith("audio/")}
        self.assertIn("audio/am_crab_die.wav", audio)
        self.assertEqual(audio["audio/am_crab_die.wav"]["sample_rate"], 22050)
        self.assertEqual(audio["audio/am_crab_die.wav"]["channels"], 1)
        self.assertEqual(audio["audio/am_crab_die.wav"]["bits"], 16)
        self.assertIn("audio/jangan_town.ogg", audio)
        self.assertEqual(audio["audio/jangan_town.ogg"]["sample_rate"], 44100)
        self.assertEqual(audio["audio/jangan_town.ogg"]["channels"], 2)

    def test_text_outputs_valid_utf8(self):
        manifest = json.loads(self.manifest_path.read_text())
        for rec in manifest["records"]:
            if not rec["output_path"].endswith(".utf8.txt"):
                continue
            out = REPO / "android-assets" / rec["output_path"]
            out.read_text(encoding="utf-8")  # must not raise
            self.assertIn("utf-8", rec["validation"])


if __name__ == "__main__":
    unittest.main()
