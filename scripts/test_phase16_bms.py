#!/usr/bin/env python3
"""Phase 16 BMS (.bms) decoding tests: hermetic samples + fixture + live archive.

Proven facts asserted here (see bms_decoder.py and FORMAT_RESEARCH.md):
  * magic 'JMXVBMS ' with version '0109' or '0110'; header_size at 0x0C;
    6 section offsets at 0x10..0x28; end_offset at 0x30; names at 0x48.
  * the u32 at header_size-4 equals the number of vertices whose bone index is
    not 0xFFFFFFFF (skinned count).
  * vertex formats: 44 B (position/normal/uv/weight/boneIndex/flags) and
    52 B (position/normal/uv/uv2/tail) lightmap meshes with a trailing
    length-prefixed lightmap texture path.
  * triangle section: u32 count + count x (3 x u16); indices < vertex_count;
    skinned meshes use a 22-byte-prefix variant whose count is span-derived.
  * AABB: 24 bytes at offsets[4], min <= max.
"""
import json
import math
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as B  # noqa: E402
import pk2_table  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "testdata", "formats")
SAMPLES_DIR = os.path.join(DATA_DIR, "bms_samples")
FIXTURE = os.path.join(DATA_DIR, "bms_phase16.json")
PK2 = "/tmp/opencode/pk2raw/Data.pk2"

# Sample key -> (expected vertex_size, expected layout)
SAMPLES = {
    "npc_chicken": (44, "standard", 14, 64),
    "char_face": (44, "standard", 5, 88),
    "item_shield": (44, "standard", 1, 87),
    "artifact_table": (44, "standard", 0, 0),
    "bldg_tree": (44, "standard", 0, 8072),
    "v52_bldg": (52, "lightmap", 0, 0),
    "v44p5": (44, "standard", 0, 0),
    "v50_avatar": (44, "standard", 2, 47),
    "nature_tree": (44, "standard", 0, 19),
    "petra": (44, "standard", 2, 94),
    "demon": (52, "lightmap", 0, 58),
}


def _sample_bytes(key):
    with open(os.path.join(SAMPLES_DIR, key + ".bms"), "rb") as fh:
        return fh.read()


class TestBmsHermeticSamples(unittest.TestCase):
    def test_all_samples_decode(self):
        for key in SAMPLES:
            r = B.parse_bms(_sample_bytes(key))
            self.assertGreater(len(r["vertices"]), 0)

    def test_magic_version_and_end_offset(self):
        for key in SAMPLES:
            d = _sample_bytes(key)
            h = B.parse_bms_header(d)
            self.assertEqual(d[:8], b"JMXVBMS ")
            self.assertIn(h["version"], ("0109", "0110"))
            offs = h["offsets"]
            for a, b in zip(offs, offs[1:]):
                self.assertLess(a, b)
            self.assertLessEqual(h["end_offset"], len(d))

    def test_header_tail_is_skinned_vertex_count(self):
        """The u32 at header_size-4 equals the count of verts with a bone index."""
        for key, (vs, _layout, _bones, expected_skinned) in SAMPLES.items():
            d = _sample_bytes(key)
            r = B.parse_bms(d)
            actual = sum(1 for v in r["vertices"]
                         if vs == 44 and v["bone_index"] != 0xFFFFFFFF)
            self.assertEqual(r["header"]["skinned_vertex_count"],
                             expected_skinned, key)
            if vs == 44:
                self.assertEqual(actual, expected_skinned, key)

    def test_vertex_size_and_layout(self):
        for key, (vs, layout, _bones, _sk) in SAMPLES.items():
            r = B.parse_bms(_sample_bytes(key))
            self.assertEqual(r["vertex_format"]["vertex_size"], vs, key)
            self.assertEqual(r["vertex_format"]["layout"], layout, key)

    def test_44_vertex_field_offsets(self):
        d = _sample_bytes("npc_chicken")
        h = B.parse_bms_header(d)
        v0 = h["header_size"] + 4
        pos = struct.unpack_from("<3f", d, v0)
        nrm = struct.unpack_from("<3f", d, v0 + 12)
        m = math.sqrt(nrm[0] ** 2 + nrm[1] ** 2 + nrm[2] ** 2)
        self.assertAlmostEqual(m, 1.0, places=2)
        self.assertTrue(all(abs(x) < 1000 for x in pos))

    def test_52_lightmap_path(self):
        r = B.parse_bms(_sample_bytes("v52_bldg"))
        self.assertEqual(r["vertex_format"]["layout"], "lightmap")
        self.assertEqual(
            r["vertex_format"]["lightmap_path"],
            r"prim\lightmap\bldg\arabia\bagh_city\dungeon"
            r"\bagh_city_dunin_l_01_01lightingmap.ddj")

    def test_triangle_indices_within_vertex_count(self):
        for key in SAMPLES:
            r = B.parse_bms(_sample_bytes(key))
            vc = len(r["vertices"])
            for tri in r["triangles"]["triangles"][:50]:
                for idx in tri:
                    self.assertLess(idx, vc, key)
            self.assertEqual(len(r["triangles"]["triangles"]),
                             r["triangles"]["triangle_count"])

    def test_aabb_min_le_max_and_matches_vertices(self):
        for key in SAMPLES:
            r = B.parse_bms(_sample_bytes(key))
            aabb = r.get("aabb")
            self.assertIsNotNone(aabb, key)
            mn, mx = aabb[:3], aabb[3:]
            for lo, hi in zip(mn, mx):
                self.assertLessEqual(lo, hi)
            vs = [v["position"] for v in r["vertices"]]
            for axis in range(3):
                col = [v[axis] for v in vs]
                self.assertLessEqual(mn[axis], min(col))
                self.assertGreaterEqual(mx[axis], max(col))

    def test_bone_names(self):
        r = B.parse_bms(_sample_bytes("npc_chicken"))
        self.assertEqual(r["bones"]["bone_count"], 14)
        self.assertEqual(r["bones"]["bone_names"][0], "Bip01 Spine")
        self.assertIn("Bip01 Head", r["bones"]["bone_names"])
        r = B.parse_bms(_sample_bytes("item_shield"))
        self.assertEqual(r["bones"]["bone_names"], ["Bone01"])

    def test_nature_tree_extra_block(self):
        r = B.parse_bms(_sample_bytes("nature_tree"))
        self.assertEqual(r["extra_block_bytes"], 202)
        self.assertEqual(r["header"]["off7"], 2086)


class TestBmsFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, "r", encoding="utf-8") as fh:
            cls.fixture = json.load(fh)

    def test_fixture_has_all_samples(self):
        self.assertEqual(set(self.fixture.keys()), set(SAMPLES.keys()))

    def test_fixture_matches_expected(self):
        for key, (vs, layout, bones, sk) in SAMPLES.items():
            rec = self.fixture[key]
            self.assertEqual(rec["vertex_format"]["vertex_size"], vs, key)
            self.assertEqual(rec["vertex_format"]["layout"], layout, key)
            self.assertEqual(rec["bone_count"], bones, key)
            self.assertEqual(rec["skinned_vertex_count"], sk, key)

    def test_fixture_lightmap_path(self):
        self.assertIn("lightingmap.ddj",
                      self.fixture["v52_bldg"]["vertex_format"]["lightmap_path"])

    def test_fixture_skinned_count_rule(self):
        for key, rec in self.fixture.items():
            if rec["vertex_format"]["vertex_size"] != 44:
                continue
            skinned = sum(1 for v in rec["vertices_sample"]
                          if v["bone_index"] != 0xFFFFFFFF) if rec["vertices_sample"] else 0
            self.assertGreaterEqual(rec["skinned_vertex_count"], skinned, key)

    def test_fixture_triangle_prefixes(self):
        for key, rec in self.fixture.items():
            self.assertIn(rec["triangle_prefix_bytes"], (0, 22), key)


class TestBmsLiveArchive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(PK2):
            raise unittest.SkipTest(f"archive {PK2} not present")
        entries, _ = pk2_table.inventory(PK2)
        cls.bms = [e for e in entries if e["path"].lower().endswith(".bms")]

    def test_corpus_classification_counts(self):
        std = lm = morph80 = morph_trail = unproven = 0
        with open(PK2, "rb") as fh:
            for e in self.bms:
                fh.seek(e["pos"])
                d = fh.read(e["size"])
                try:
                    c = B.classify_bms(d)
                except B.BmsFormatError:
                    unproven += 1
                    continue
                if c["triangle_section"] == "unproven":
                    unproven += 1
                    continue
                layout = c["layout"]
                if layout == "standard":
                    std += 1
                elif layout == "lightmap":
                    lm += 1
                elif layout == "morph80":
                    morph80 += 1
                elif layout == "morph_trailing":
                    morph_trail += 1
                else:
                    unproven += 1
        self.assertEqual(std + lm + morph80 + morph_trail + unproven,
                         len(self.bms))
        # Deterministic corpus distribution established during Phase 16 forensics.
        self.assertGreater(std, 15000)
        self.assertGreater(lm, 4500)
        self.assertEqual(morph80, 5)
        self.assertEqual(morph_trail, 1)
        self.assertLess(unproven, 40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
