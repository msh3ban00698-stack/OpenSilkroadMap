"""Tests for Phase 4 reproducibility scripts: inventory parsing and controlled
sample extraction. These run without the real 4.8 GB PK2 dataset; they use the
committed synthetic fixture (scripts/testdata/pk2_fixture/fixture.pk2) and the
pk2_mate binary when available.

Running:
    python3 scripts/test_phase4_assets.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
FIXTURE = REPO / "scripts" / "testdata" / "pk2_fixture" / "fixture.pk2"
sys.path.insert(0, str(SCRIPTS))


def find_reader():
    return os.environ.get("SRO_READER_BIN") or shutil.which("pk2_mate")


def run_script(script, *args, env=None, cwd=None):
    cmd = [sys.executable, str(script), *[str(a) for a in args]]
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO),
        env=merged,
        capture_output=True,
        text=True,
    )


class InventoryParserTests(unittest.TestCase):
    def test_parse_fixture_listing(self):
        from inventory_pk2 import parse_listing

        # Indentation mirrors pk2_mate list_files: child indent = parent
        # indent + len(parent printed path). "/" -> children at 1;
        # "/data" (len 5) -> children at 6; "/nested" (len 7) -> child at 8;
        # "/nested/deep" (len 12) -> child at 20.
        listing = (
            "/\n"
            " /data\n"
            "      100x100.ddj\n"
            " /nested\n"
            "        /nested/deep\n"
            "                    marker.txt\n"
            " hello.txt\n"
        )
        files, dirs = parse_listing(listing)
        self.assertEqual(
            sorted(files), ["/data/100x100.ddj", "/hello.txt", "/nested/deep/marker.txt"]
        )
        self.assertEqual(sorted(dirs), ["/", "/data", "/nested", "/nested/deep"])

    def test_parse_uses_pk2_mate_listing_when_available(self):
        reader = find_reader()
        if not reader:
            self.skipTest("pk2_mate not available")
        proc = subprocess.run(
            [reader, "list", "--archive", str(FIXTURE)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        from inventory_pk2 import parse_listing

        files, dirs = parse_listing(proc.stdout)
        self.assertIn("/data/100x100.ddj", files)
        self.assertIn("/hello.txt", files)
        self.assertIn("/nested/deep/marker.txt", files)

    def test_inventory_script_runs(self):
        reader = find_reader()
        if not reader:
            self.skipTest("pk2_mate not available")
        with tempfile.TemporaryDirectory() as td:
            listing = os.path.join(td, "fixture.list.txt")
            proc = subprocess.run(
                [reader, "list", "--archive", str(FIXTURE)],
                capture_output=True,
                text=True,
            )
            Path(listing).write_text(proc.stdout)
            out = run_script(SCRIPTS / "inventory_pk2.py", listing, "--json")
            self.assertEqual(out.returncode, 0, out.stderr)
            data = json.loads(out.stdout)
            self.assertEqual(data["file_count"], 3)
            self.assertEqual(data["by_extension"]["ddj"], 1)
            self.assertEqual(data["by_extension"]["txt"], 2)


class ExtractSamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = find_reader()

    def test_extract_samples_missing_reader_fails(self):
        with tempfile.TemporaryDirectory() as td:
            out = run_script(
                SCRIPTS / "extract_samples.py",
                "--pk2-dir",
                td,
                "--reader-bin",
                os.path.join(td, "nope"),
                "--out",
                os.path.join(td, "out"),
            )
            self.assertNotEqual(out.returncode, 0)

    def test_extract_samples_pk2_missing_fails_cleanly(self):
        if not self.reader:
            self.skipTest("pk2_mate not available")
        with tempfile.TemporaryDirectory() as td:
            out = run_script(
                SCRIPTS / "extract_samples.py",
                "--pk2-dir",
                td,
                "--reader-bin",
                self.reader,
                "--out",
                os.path.join(td, "out"),
            )
            self.assertNotEqual(out.returncode, 0)
            combined = out.stdout + out.stderr
            self.assertIn("pk2 missing", combined)


if __name__ == "__main__":
    unittest.main()
