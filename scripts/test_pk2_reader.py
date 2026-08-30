"""Reproducible PK2 reader tests.

Header/signature checks run against the committed synthetic fixture
(scripts/testdata/pk2_fixture/fixture.pk2) using the format constants documented
from the reader source (Veykril/pk2, pinned commit). These do NOT require the
pk2_mate binary.

Reader-based tests (list, extract) require the external pk2_mate binary
(validated reader, see PK2_READER_FOUNDATION.md) and are skipped with a clear
message when it is absent. Real 5.7GB archives are NOT required by these tests;
validate them separately with scripts/validate_pk2.py.

Running:
    python3 scripts/test_pk2_reader.py
"""

import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent

PK2_SIGNATURE = b"JoyMax File Manager!\n" + b"\x00" * 9
PK2_VERSION = 0x0100_0002
FIXTURE = REPO / "scripts" / "testdata" / "pk2_fixture" / "fixture.pk2"
FIXTURE_SRC = REPO / "scripts" / "testdata" / "pk2_fixture" / "src"


def find_pk2_mate():
    candidates = [
        os.environ.get("SRO_READER_BIN"),
        os.path.join(os.environ.get("SRO_READER_DIR", ""), "pk2_mate"),
        "/tmp/opencode/pk2_mate",
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    which = os.environ.get("PATH", "").split(os.pathsep)
    for base in which:
        p = os.path.join(base, "pk2_mate")
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def pk2_mate_available():
    return find_pk2_mate() is not None


class HeaderFormatTests(unittest.TestCase):
    """Pure-Python header checks against the committed fixture.

    Uses only constants documented from the reader source; does not implement a
    reader and does not decrypt anything.
    """

    @classmethod
    def setUpClass(cls):
        cls.header = FIXTURE.read_bytes()[:256]

    def test_fixture_exists(self):
        self.assertTrue(FIXTURE.is_file(), "synthetic fixture missing")

    def test_signature_matches_source_constant(self):
        self.assertEqual(self.header[0:30], PK2_SIGNATURE)

    def test_version_matches_source_constant(self):
        version = struct.unpack("<I", self.header[30:34])[0]
        self.assertEqual(version, PK2_VERSION)

    def test_encrypted_flag_is_set(self):
        self.assertNotEqual(self.header[34], 0)

    def test_verify_field_is_nonzero(self):
        self.assertNotEqual(self.header[35:38], b"\x00\x00\x00")

    def test_reserved_region_is_zero(self):
        self.assertTrue(all(b == 0 for b in self.header[51:256]))

    def test_header_is_256_bytes(self):
        self.assertEqual(len(self.header), 256)


@unittest.skipUnless(pk2_mate_available(), "pk2_mate binary not available")
class Pk2MateIntegrationTests(unittest.TestCase):
    """End-to-end list/extract using the verified external reader."""

    @classmethod
    def setUpClass(cls):
        cls.reader = find_pk2_mate()

    def run_pk2_mate(self, *args):
        return subprocess.run(
            [self.reader, *args], capture_output=True, text=True, timeout=120
        )

    def test_list_fixture(self):
        proc = self.run_pk2_mate("list", "--archive", str(FIXTURE))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("hello.txt", out)
        self.assertIn("100x100.ddj", out)
        self.assertIn("marker.txt", out)

    def test_extract_hello_txt(self):
        with tempfile.TemporaryDirectory() as td:
            proc = self.run_pk2_mate(
                "extract",
                "--archive",
                str(FIXTURE),
                "--out",
                td,
                "--path",
                "hello.txt",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            extracted = os.path.join(td, "hello.txt")
            self.assertTrue(os.path.isfile(extracted))
            with open(extracted, "rb") as fh:
                self.assertEqual(fh.read(), b"Hello OpenSilkroadMap\n")


@unittest.skipUnless(pk2_mate_available(), "pk2_mate binary not available")
class ValidateScriptTests(unittest.TestCase):
    def test_validate_script_runs_on_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            fixture_dir = os.path.join(td, "pk2")
            os.makedirs(fixture_dir)
            import shutil

            shutil.copy(FIXTURE, os.path.join(fixture_dir, "Music.pk2"))
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_pk2.py"),
                    "--pk2-dir",
                    fixture_dir,
                    "--reader-bin",
                    find_pk2_mate(),
                    "--extract-one",
                    "hello.txt",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(REPO),
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("OK", proc.stdout)

    def test_validate_script_fails_clearly_without_reader(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_pk2.py"),
                    "--pk2-dir",
                    td,
                    "--reader-bin",
                    os.path.join(td, "nonexistent_reader"),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(REPO),
            )
            self.assertNotEqual(proc.returncode, 0)
            combined = proc.stdout + proc.stderr
            self.assertIn("pk2_mate", combined)
            self.assertIn("PK2_READER_FOUNDATION.md", combined)


if __name__ == "__main__":
    unittest.main()
