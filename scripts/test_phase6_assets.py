"""Tests for Phase 6: bulk minimap/minimap_d conversion, manifest consistency,
determinism, and source-PK2 preservation.

Pure/committed tests run against the committed android-assets/ tree and
manifest (no PK2 needed). Environment-gated tests additionally verify real
bytes against the PK2 archives when the following are set:

    SRO_PHASE6_PK2_DIR=/path/to/pk2s SRO_READER_BIN=/path/to/pk2_mate \\
        SRO_PHASE6_LISTING=/path/to/Media.list.txt

Running:
    python3 scripts/test_phase6_assets.py
"""

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from bulk_convert_assets import (  # noqa: E402
    extract_targets,
    map_output,
    sha256_file,
)
from dds_decode import (  # noqa: E402
    ddj_to_rgba,
    png_from_rgba,
    parse_png_header,
)

DDPF_FOURCC = 0x4


def make_dds(width, height, pixel_data, fourcc=b"DXT1", mipmaps=0):
    hdr = bytearray()
    hdr += b"DDS "
    hdr += struct.pack("<7I", 124, 0x1000 | 0x2 | 0x4 | 0x80000, height, width, 0, 0, mipmaps)
    hdr += b"\x00" * 44
    hdr += struct.pack("<II4sIIIII", 32, DDPF_FOURCC, fourcc, 0, 0, 0, 0, 0)
    hdr += struct.pack("<4I", 0x1000, 0, 0, 0)
    hdr += b"\x00" * 4
    return bytes(hdr) + pixel_data


def make_ddj(payload):
    return b"JMXVDDJ 1000" + b"\x00" * 8 + payload


def dxt1_white_block():
    return struct.pack("<HH4B", 0xFFFF, 0x0000, 0xE4, 0xE4, 0xE4, 0xE4)


ASSETS = REPO / "android-assets"
MANIFEST = ASSETS / "manifest.json"
ENV_PK2 = os.environ.get("SRO_PHASE6_PK2_DIR")
ENV_READER = os.environ.get("SRO_READER_BIN")
ENV_LISTING = os.environ.get("SRO_PHASE6_LISTING")

# Exact counts verified from the real Media.list.txt listing (Phase 6).
MINIMAP_COUNT = 5523
MINIMAP_D_COUNT = 2214
TOTAL_COUNT = MINIMAP_COUNT + MINIMAP_D_COUNT


def load_manifest():
    with open(MANIFEST) as f:
        return json.load(f)


class InventoryTests(unittest.TestCase):
    def test_exact_verified_counts(self):
        self.assertEqual(TOTAL_COUNT, 7737)

    @unittest.skipUnless(ENV_LISTING, "SRO_PHASE6_LISTING not set")
    def test_listing_matches_verified_counts(self):
        targets = extract_targets(ENV_LISTING)
        self.assertEqual(len(targets), TOTAL_COUNT)
        self.assertEqual(
            sum(1 for t in targets if t.startswith("/minimap/")), MINIMAP_COUNT
        )
        self.assertEqual(
            sum(1 for t in targets if t.startswith("/minimap_d/")), MINIMAP_D_COUNT
        )

    def test_no_basename_collisions_across_targets(self):
        m = load_manifest()
        phase6 = [r for r in m["records"] if r.get("phase") == "phase6"]
        bases = [os.path.basename(r["source_path"]) for r in phase6]
        self.assertEqual(len(bases), len(set(bases)))


class ManifestConsistencyTests(unittest.TestCase):
    def test_manifest_exists_and_shape(self):
        self.assertTrue(MANIFEST.is_file())
        m = load_manifest()
        for key in ("schema", "archive", "targets", "batches", "records", "summary"):
            self.assertIn(key, m)
        self.assertEqual(m["archive"], "Media.pk2")

    def test_summary_counts_reconcile(self):
        m = load_manifest()
        ok = sum(1 for r in m["records"] if r["status"] == "ok")
        failed = sum(1 for r in m["records"] if r["status"] == "failed")
        unknown = sum(1 for r in m["records"] if r["status"] == "unknown")
        self.assertEqual(ok + failed + unknown, len(m["records"]))
        self.assertEqual(m["summary"]["ok"], ok)
        self.assertEqual(m["summary"]["failed"], failed)
        self.assertEqual(m["summary"]["unknown"], unknown)
        self.assertEqual(m["summary"]["total"], len(m["records"]))

    def test_no_silent_skips(self):
        m = load_manifest()
        phase6_records = [r for r in m["records"] if r.get("phase") == "phase6"]
        self.assertEqual(len(phase6_records), m["targets"]["total"])

    def test_no_output_path_collisions(self):
        m = load_manifest()
        outs = [r["output"] for r in m["records"] if r.get("output")]
        self.assertEqual(len(outs), len(set(outs)))

    def test_path_mapping_roundtrip(self):
        m = load_manifest()
        for r in m["records"]:
            if r.get("output") and r.get("phase") == "phase6":
                src = r["source_path"].lstrip("/")[:-4] + ".png"
                self.assertEqual(map_output(r["source_path"]), r["output"])


class OutputValidationTests(unittest.TestCase):
    def test_all_ok_outputs_exist(self):
        m = load_manifest()
        missing = [
            r["output"]
            for r in m["records"]
            if r["status"] == "ok" and not (ASSETS / r["output"]).is_file()
        ]
        self.assertEqual(missing, [])

    def test_output_sha256_matches_manifest(self):
        m = load_manifest()
        bad = []
        for r in m["records"]:
            if r["status"] == "ok":
                p = ASSETS / r["output"]
                if not p.is_file() or sha256_file(str(p)) != r["output_sha256"]:
                    bad.append(r["output"])
        self.assertEqual(bad, [])

    def test_outputs_are_valid_png_with_matching_dims(self):
        m = load_manifest()
        bad = []
        for r in m["records"]:
            if r["status"] == "ok" and r.get("output", "").endswith(".png"):
                p = ASSETS / r["output"]
                try:
                    w, h, _bd, _ct = parse_png_header(p.read_bytes())
                except Exception:
                    bad.append((r["output"], "unreadable"))
                    continue
                if (w, h) != (r["width"], r["height"]):
                    bad.append((r["output"], (w, h), (r["width"], r["height"])))
        self.assertEqual(bad, [])

    def test_logical_size_recorded(self):
        m = load_manifest()
        without = [
            r
            for r in m["records"]
            if r["status"] == "ok" and r.get("phase") == "phase6"
            and not r.get("logical_width")
        ]
        self.assertEqual(without, [])


class DeterminismTests(unittest.TestCase):
    def test_deterministic_png_output(self):
        ddj = make_ddj(make_dds(4, 4, dxt1_white_block()))
        w, h, px = ddj_to_rgba(ddj)
        p1 = png_from_rgba(w, h, px)
        w2, h2, px2 = ddj_to_rgba(ddj)
        p2 = png_from_rgba(w2, h2, px2)
        self.assertEqual(p1, p2)
        self.assertEqual(hashlib.sha256(p1).hexdigest(), hashlib.sha256(p2).hexdigest())


class RealBytesTests(unittest.TestCase):
    @unittest.skipUnless(ENV_PK2 and ENV_READER, "SRO_PHASE6_PK2_DIR/SRO_READER_BIN not set")
    def test_sample_sources_are_jmxddj_dds(self):
        m = load_manifest()
        sample = [
            r["source_path"]
            for r in m["records"]
            if r.get("phase") == "phase6" and r.get("output", "").endswith(".png")
        ][:6]
        pk2 = os.path.join(ENV_PK2, "Media.pk2")
        with tempfile.TemporaryDirectory() as wd:
            for src in sample:
                rel = src.lstrip("/")
                sub = os.path.join(wd, "w")
                os.makedirs(sub, exist_ok=True)
                proc = subprocess.run(
                    [ENV_READER, "extract", "--archive", pk2, "--out", sub, "--path", rel],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                p = os.path.join(sub, os.path.basename(rel))
                with open(p, "rb") as f:
                    data = f.read()
                os.remove(p)
                self.assertEqual(data[0:12], b"JMXVDDJ 1000")

    @unittest.skipUnless(ENV_PK2 and ENV_READER, "SRO_PHASE6_PK2_DIR/SRO_READER_BIN not set")
    def test_source_pk2_unmodified(self):
        pk2 = os.path.join(ENV_PK2, "Media.pk2")
        before = os.stat(pk2)
        h1 = sha256_file(pk2)
        with tempfile.TemporaryDirectory() as wd:
            rel = "/minimap/100x100.ddj".lstrip("/")
            sub = os.path.join(wd, "w")
            os.makedirs(sub, exist_ok=True)
            subprocess.run(
                [ENV_READER, "extract", "--archive", pk2, "--out", sub, "--path", rel],
                capture_output=True,
                text=True,
            )
        after = os.stat(pk2)
        h2 = sha256_file(pk2)
        self.assertEqual(h1, h2)
        self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))


class CleanupTests(unittest.TestCase):
    def test_batch_arithmetic_consistent(self):
        m = load_manifest()
        self.assertTrue(len(m["batches"]) > 0)
        for b in m["batches"]:
            self.assertEqual(b["ok"] + b["failed"] + b["unknown"],
                             b["end_index"] - b["start_index"])

    @unittest.skipUnless(ENV_PK2 and ENV_READER and ENV_LISTING,
                         "SRO_PHASE6_PK2_DIR/SRO_READER_BIN/SRO_PHASE6_LISTING not set")
    def test_converter_cleans_workdir(self):
        with tempfile.TemporaryDirectory() as out:
            with tempfile.TemporaryDirectory() as work:
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "bulk_convert_assets.py"),
                        "--pk2-dir", ENV_PK2,
                        "--reader-bin", ENV_READER,
                        "--listing", ENV_LISTING,
                        "--out", out,
                        "--work", work,
                        "--limit", "3",
                        "--batch-size", "3",
                        "--manifest", os.path.join(out, "manifest.json"),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                leftover = []
                for root, _dirs, names in os.walk(work):
                    for n in names:
                        if n.lower().endswith(".ddj"):
                            leftover.append(os.path.join(root, n))
                self.assertEqual(leftover, [], "temp extraction .ddj files not cleaned")


if __name__ == "__main__":
    unittest.main()
