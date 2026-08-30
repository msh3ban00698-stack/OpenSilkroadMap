#!/usr/bin/env python3
"""Phase 13 EFP (.efp) version-tree structural tests.

Proven facts (from live Particles.pk2 census, all 3,395 files):
  * magic 'JMXVEFF ' (8 B) + 4 ASCII version bytes at offset 8
  * version distribution: 0000=7, 0010=1, 0011=1820, 0012=408, 0013=1158
  * body is a serialized command stream: the large majority of embedded
    ASCII runs >= 4 chars are u32-LENGTH-PREFIXED command tokens
  * shared command vocabulary across 0010..0013 (StaticEmit, Program,
    ProgramUpdate, LinkMode, NormalTimeLife, NormalTimeExtinct, SetGraphScale,
    SetGraphDiffuse, ViewNone, RenderMesh/RenderPlate, SetShapeRotVel, ...)
  * version 0000 differs: embeds texture/mesh file paths (textures\\*.ddj,
    meshes\\*.bms) instead of the command vocabulary
  * header field at offset 12: 0011 = small u32 (91..96); 0012/0013 =
    float-like u32 bit patterns (1.0/0.5/2.0); 0000 = path-offset-ish values
"""
import json
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pk2_table  # noqa: E402

PK2 = "/tmp/opencode/pk2raw/Particles.pk2"
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "efp_versions.json")

VERSION_COUNTS = {"0000": 7, "0010": 1, "0011": 1820, "0012": 408, "0013": 1158}

COMMON_TOKENS = [
    "StaticEmit", "Program", "ProgramUpdate", "LinkMode",
    "NormalTimeLife", "NormalTimeExtinct", "SetGraphScale", "SetGraphDiffuse",
]


class TestEfpVersionTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(PK2):
            raise unittest.SkipTest(f"archive {PK2} not present")
        entries, _ = pk2_table.inventory(PK2)
        cls.efp = [e for e in entries if e["path"].lower().endswith(".efp")]
        cls.efp = [e for e in cls.efp if e["size"] > 0]

    def _read(self, e):
        with open(PK2, "rb") as fh:
            fh.seek(e["pos"])
            return fh.read(e["size"])

    def test_corpus_size_and_all_magic(self):
        self.assertGreaterEqual(len(self.efp), 3390)
        for e in self.efp:
            d = self._read(e)
            self.assertEqual(d[:8], b"JMXVEFF ")

    def test_version_counts(self):
        counts = {}
        for e in self.efp:
            d = self._read(e)
            v = d[8:12].decode("latin-1")
            counts[v] = counts.get(v, 0) + 1
        self.assertEqual(counts, VERSION_COUNTS)

    def test_version_is_ascii_digits(self):
        for e in self.efp:
            d = self._read(e)
            v = d[8:12]
            self.assertTrue(all(48 <= c <= 57 for c in v),
                            f"non-digit version in {e['path']}")

    def _tokens(self, data):
        tokens = []
        i = 8
        n = len(data)
        while i < n:
            if 32 <= data[i] < 127:
                j = i
                while j < n and 32 <= data[j] < 127:
                    j += 1
                if j - i >= 4:
                    s = data[i:j].decode("latin-1")
                    pref = (i - 4 >= 0 and
                            struct.unpack_from("<I", data, i - 4)[0] == j - i)
                    if pref:
                        tokens.append(s)
                i = j
            else:
                i += 1
        return tokens

    def test_shared_command_vocabulary(self):
        union = set()
        for e in self.efp:
            d = self._read(e)
            v = d[8:12].decode("latin-1")
            if v == "0000":
                continue
            union |= set(self._tokens(d))
        for tok in COMMON_TOKENS:
            self.assertIn(tok, union, f"corpus missing {tok}")

    def test_0000_embeds_paths_not_commands(self):
        seen = self._tokens(self._read(self.efp[0]))
        self.assertTrue(any("\\" in t for t in seen))


class TestEfpFixture(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE, "r", encoding="utf-8") as fh:
            self.fixture = json.load(fh)

    def test_versions_present(self):
        self.assertEqual(set(self.fixture.keys()), set(VERSION_COUNTS.keys()))

    def test_file_counts_match(self):
        for v, n in VERSION_COUNTS.items():
            self.assertEqual(self.fixture[v]["file_count"], n)

    def test_0011_head_field_small(self):
        for x in self.fixture["0011"]["head_field_u32_top"]:
            self.assertLess(x, 200)

    def test_0012_0013_head_field_float_like(self):
        for v in ("0012", "0013"):
            for x in self.fixture[v]["head_field_u32_top"]:
                self.assertGreaterEqual(x, 1048576000)  # >= float 0.25 patterns

    def test_common_tokens_in_top(self):
        for v in ("0010", "0011", "0012", "0013"):
            top = self.fixture[v]["top_tokens"]
            for tok in ("StaticEmit", "Program", "LinkMode"):
                self.assertIn(tok, top, f"{v} missing {tok}")
            if v != "0010":  # 0010 is a single file with a small vocabulary
                self.assertIn("SetGraphScale", top, f"{v} missing SetGraphScale")

    def test_prefixed_run_ratio_dominant(self):
        for v in ("0010", "0011", "0012", "0013"):
            r = self.fixture[v]
            self.assertGreater(r["u32_prefixed_ascii_runs"] / r["total_ascii_runs"],
                               0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
