#!/usr/bin/env python3
"""Phase 13 BSK/BSR sampling tests.

Proven facts (live Data.pk2 census):
  * BSK (1,039 files, 1 empty, 1 corrupt): magic 'JMXVBSK 0101' constant;
    u32 count @12; embeds skeleton bone names ([root], Bip01*, BoneNN) and
    quaternion/position keyframe floats (same naming as .ban).
  * BSR (7,549 files): magic 'JMXVRES 0109' dominant (0108 x3, 0107 x1);
    8 x u32 table @12..40 (offsets, NOT monotonic); embeds asset path refs
    to .bmt (material) and .bms (mesh parts) -> resource/attachment file.
"""
import json
import os
import re
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pk2_table  # noqa: E402

PK2 = "/tmp/opencode/pk2raw/Data.pk2"
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "bsk_bsr_samples.json")


class TestBskBrsLiveArchive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(PK2):
            raise unittest.SkipTest(f"archive {PK2} not present")
        entries, _ = pk2_table.inventory(PK2)
        cls.bsk = [e for e in entries if e["path"].lower().endswith(".bsk")
                   and e["size"] > 0]
        cls.bsr = [e for e in entries if e["path"].lower().endswith(".bsr")
                   and e["size"] > 0]

    def _read(self, e):
        with open(PK2, "rb") as fh:
            fh.seek(e["pos"])
            return fh.read(e["size"])

    def test_bsk_magic_constant(self):
        good = corrupt = 0
        for e in self.bsk:
            d = self._read(e)
            if d[:12] == b"JMXVBSK 0101":
                good += 1
            else:
                corrupt += 1
        self.assertGreaterEqual(good, 1030)
        self.assertLessEqual(corrupt, 1)

    def test_bsk_count_field_positive(self):
        for e in self.bsk:
            d = self._read(e)
            if d[:12] != b"JMXVBSK 0101":
                continue
            c = struct.unpack_from("<I", d, 12)[0]
            self.assertGreater(c, 0)

    def test_bsk_embeds_skeleton_bone_names(self):
        hits = 0
        for e in self.bsk:
            d = self._read(e)
            if d[:12] != b"JMXVBSK 0101":
                continue
            if b"Bip01" in d or b"Bone" in d or b"[root]" in d:
                hits += 1
        self.assertGreater(hits, len(self.bsk) * 0.9)

    def test_bsk_embeds_float_keyframes(self):
        d = self._read(next(e for e in self.bsk
                            if e["path"].lower().endswith("w_cd_boat.bsk")))
        floats = struct.unpack_from("<12f", d, 32)
        self.assertTrue(any(-2.0 < f < 2.0 for f in floats))

    def test_bsr_magic_versions(self):
        counts = {}
        for e in self.bsr:
            d = self._read(e)
            m = d[:12]
            counts[m] = counts.get(m, 0) + 1
        self.assertEqual(counts[b"JMXVRES 0109"], 7545)
        self.assertEqual(counts[b"JMXVRES 0108"], 3)
        self.assertEqual(counts[b"JMXVRES 0107"], 1)

    def test_bsr_has_8_u32_table_offsets(self):
        for e in self.bsr:
            d = self._read(e)
            if d[:12] != b"JMXVRES 0109":
                continue
            for i in range(8):
                v = struct.unpack_from("<I", d, 12 + i * 4)[0]
                self.assertLess(v, len(d))

    def test_bsr_embeds_bmt_bms_paths(self):
        d = self._read(next(e for e in self.bsr
                            if e["path"].lower().endswith("avatar_w_angel_wing_dress.bsr")))
        self.assertIn(b"avatar_w_angel_wing.bmt", d)
        self.assertIn(b"avatar_w_angel_wing_dress_part1.bms", d)
        self.assertIn(b"avatar_w_angel_wing_dress_part2.bms", d)


class TestBskBrsFixture(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE, "r", encoding="utf-8") as fh:
            self.fixture = json.load(fh)

    def test_bsk_samples(self):
        boat = self.fixture["bsk"]["w_cd_boat.bsk"]
        self.assertEqual(boat["magic"], "JMXVBSK 0101")
        self.assertEqual(boat["count_u32_at_12"], 6)
        self.assertIn("Bone01", boat["bone_names"])
        crazy = self.fixture["bsk"]["flame_crazy_stand01.bsk"]
        self.assertEqual(crazy["count_u32_at_12"], 55)
        self.assertEqual(crazy["bone_names"][0], "[root]")

    def test_bsr_samples(self):
        wing = self.fixture["bsr"]["avatar_w_angel_wing_dress.bsr"]
        self.assertEqual(wing["magic"], "JMXVRES 0109")
        self.assertEqual(len(wing["table8_u32"]), 8)
        self.assertTrue(any(p.endswith(".bmt") for p in wing["paths"]))
        self.assertTrue(any(p.endswith(".bms") for p in wing["paths"]))
        buda = self.fixture["bsr"]["w_cd_buda_b_01.bsr"]
        self.assertGreaterEqual(len(buda["paths"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
