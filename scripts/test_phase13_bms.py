#!/usr/bin/env python3
"""Phase 13 BMS (.bms) structural tests against live archive + fixture.

Proven facts (both samples petra + demon):
  * magic 'JMXVBMS 0110', u32 header_size == section_offsets[0]
  * header: u32 header_size @12, 6 section offsets @16..36, u32 end_offset @48
  * section 2 = triangle list: u32 count + count x (3 x u16 LE), stride 6
  * section 5 = AABB: 6 x f32 (minx,miny,minz,maxx,maxy,maxz)
  * triangle indices < section0 vertex_count (index-validity check)
  * section0 vertex stride 44 B only fits petra -> UNKNOWN in general
  * section1 = bone table (u32 count); demon has 0 bones
"""
import json
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pk2_table  # noqa: E402

PK2 = "/tmp/opencode/pk2raw/Data.pk2"
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "bms_layout.json")

SAMPLES = {
    "petra": "/prim/mesh/bldg/arabia/Bagh_Petra/Bagh_Petra_Core01.BMS",
    "demon": "/prim/mesh/dun/Demon/Fire/Demon_tower_Fire/demon_tower_mbrazier_fire.BMS",
}


class BmsProbe:
    def __init__(self, data):
        self.data = data
        self.magic = data[:12]
        self.header_size = struct.unpack_from("<I", data, 12)[0]
        self.offsets = [struct.unpack_from("<I", data, 16 + i * 4)[0]
                        for i in range(6)]
        self.sections = [self.header_size] + self.offsets
        self.end_offset = struct.unpack_from("<I", data, 48)[0]

    def vertex_count(self):
        return struct.unpack_from("<I", self.data, self.sections[0])[0]

    def vertex_stride(self):
        vc = self.vertex_count()
        body = self.sections[1] - self.sections[0] - 4
        return body / vc if vc and body > 0 else None

    def bone_count(self):
        return struct.unpack_from("<I", self.data, self.sections[1])[0]

    def triangle_count(self):
        return struct.unpack_from("<I", self.data, self.sections[2])[0]

    def triangles(self, limit=None):
        tc = self.triangle_count()
        o = self.sections[2] + 4
        n = limit if limit else tc
        return [struct.unpack_from("<3H", self.data, o + 6 * i) for i in range(n)]

    def aabb(self):
        return struct.unpack_from("<6f", self.data, self.sections[5])

    def names(self):
        names = []
        o = 72
        for _ in range(4):
            l = struct.unpack_from("<I", self.data, o)[0]
            if not (0 < l < 80):
                break
            s = self.data[o + 4:o + 4 + l]
            if not all(32 <= c < 127 for c in s):
                break
            names.append(s.decode("latin-1"))
            o += 4 + l
        return names

    def header_tail_unknown(self):
        _, o = self._name_end()
        return struct.unpack_from("<I", self.data, o)[0]

    def _name_end(self):
        o = 72
        for _ in range(4):
            l = struct.unpack_from("<I", self.data, o)[0]
            if not (0 < l < 80):
                break
            s = self.data[o + 4:o + 4 + l]
            if not all(32 <= c < 127 for c in s):
                break
            o += 4 + l
        return self.data, o


def _load_archive():
    if not os.path.exists(PK2):
        raise unittest.SkipTest(f"archive {PK2} not present")
    entries, _ = pk2_table.inventory(PK2)
    files = {e["path"]: e for e in entries}
    return files


def _read(files, path):
    e = files[path]
    with open(PK2, "rb") as fh:
        fh.seek(e["pos"])
        return fh.read(e["size"])


def _load_fixture():
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)


class TestBmsLiveArchive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = _load_archive()
        cls.probes = {k: BmsProbe(_read(cls.files, p)) for k, p in SAMPLES.items()}

    def test_magic(self):
        for p in self.probes.values():
            self.assertEqual(p.magic, b"JMXVBMS 0110")

    def test_header_size_matches_first_section(self):
        for p in self.probes.values():
            self.assertEqual(p.header_size, p.sections[0])

    def test_offsets_ascending_and_end_offset(self):
        for p in self.probes.values():
            self.assertEqual(len(p.offsets), 6)
            for a, b in zip(p.offsets, p.offsets[1:]):
                self.assertLess(a, b)
            self.assertEqual(p.end_offset, len(p.data) - 4)
            self.assertLess(p.offsets[-1], p.end_offset)

    def test_triangle_section_stride_six(self):
        for p in self.probes.values():
            tc = p.triangle_count()
            o = p.sections[2] + 4
            self.assertEqual(p.sections[3] - o, tc * 6)

    def test_triangle_indices_within_vertex_count(self):
        for p in self.probes.values():
            vc = p.vertex_count()
            for t in p.triangles(limit=50):
                for idx in t:
                    self.assertLess(idx, vc)

    def test_aabb_24_bytes_at_section5(self):
        for p in self.probes.values():
            self.assertEqual(p.sections[6] - p.sections[5], 24)
            mn, mx = p.aabb()[:3], p.aabb()[3:]
            for lo, hi in zip(mn, mx):
                self.assertLessEqual(lo, hi)

    def test_bone_count_matches_phase12_note(self):
        self.assertEqual(self.probes["petra"].bone_count(), 2)
        self.assertEqual(self.probes["demon"].bone_count(), 0)


class TestBmsFixture(unittest.TestCase):
    def setUp(self):
        self.fixture = _load_fixture()

    def test_fixture_has_both_samples(self):
        self.assertEqual(set(self.fixture.keys()), {"petra", "demon"})

    def test_fixture_triangle_consistency(self):
        for rec in self.fixture.values():
            self.assertEqual(rec["triangle_record_stride"], 6)
            self.assertEqual(rec["triangle_section_index"], 2)
            self.assertEqual(rec["aabb_section_index"], 5)

    def test_petra_vertex_stride_44(self):
        self.assertEqual(self.fixture["petra"]["section0_vertex_stride_bytes"], 44.0)

    def test_demon_vertex_stride_not_integer(self):
        s = self.fixture["demon"]["section0_vertex_stride_bytes"]
        self.assertIsNotNone(s)
        self.assertNotEqual(s, int(s))

    def test_names_present(self):
        self.assertEqual(self.fixture["petra"]["header_names"],
                         ["Bagh_Petra_Core01", "Bagh_Petra_core01"])
        self.assertEqual(self.fixture["demon"]["header_names"],
                         ["demon_tower_mbrazier_fire", "Demon_Tower_Brazier_fire"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
