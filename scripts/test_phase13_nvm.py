"""Phase 13 `.nvm` navmesh structure tests.

Static tests run against the committed derived fixture scripts/testdata/formats/
nvm_grid.json (facts extracted read-only from the real Data.pk2 archive). The
live check re-verifies the same facts against the real archive when SRO_PK2_DIR
is set, otherwise it reports SKIPPED.

Proven (Part E):
  * magic+version `JMXVNVM 1000` (12 bytes)
  * a flat array of 8-byte LE records (4 x u16) with a dominant count of 9,216
    (= 96x96) in most sampled regions; records carry (field0, flag 0/1,
    type-marker 0x0117=279 or 0x010F=271, value) -- e.g. nv_198c records are
    (0, flag, 279, value); nv_1f29 records are (0, {0|255}, 0, 0)
  * a consistent ~37,814-byte f32 region immediately after the grid
  * trailing -20.0 f32 fill words (commonly exactly 36 = 144 bytes) marking
    empty/unused nav cells

NOT proven (explicitly UNKNOWN): which header u16/u32 is the vertex count, which
is the triangle count, the record semantics (type-marker meaning, flag meaning),
the f32 vertex/triangle layout, and the header field meanings beyond the
[0,1920] extent floats.

Running:
    python3 scripts/test_phase13_nvm.py
"""

import json
import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

TD = SCRIPTS / "testdata" / "formats"

FILL = struct.pack("<f", -20.0)

GRID_SAMPLES = {
    "nv_5ba3.nvm": {"grid_records": 9216, "post_grid": 37814, "fill": 36},
    "nv_6e50.nvm": {"grid_records": 9216, "post_grid": 37814, "fill": 36},
    "nv_1614.nvm": {"grid_records": 9216, "post_grid": 37814, "fill": 0},
    "nv_64aa.nvm": {"grid_records": 9216, "post_grid": 37814, "fill": 1},
    "nv_6876.nvm": {"grid_records": 9236, "post_grid": 37652, "fill": 36},
    "nv_154e.nvm": {"grid_records": 9216, "post_grid": 37810, "fill": 36},
    "nv_1f29.nvm": {"grid_records": 9311, "post_grid": 7, "fill": 0},
    "nv_74bf.nvm": {"grid_records": 9216, "post_grid": 37814, "fill": 0},
    "nv_198c.nvm": {"grid_records": 9216, "post_grid": 37814, "fill": 36},
}

NON_GRID = {"nv_5731.nvm", "nv_1bcf.nvm", "nv_1748.nvm", "nv_189f.nvm",
            "nv_59ae.nvm", "nv_169b.nvm", "nv_634d.nvm", "nv_3b5a.nvm"}


def load_fixture():
    with open(TD / "nvm_grid.json", encoding="utf-8") as fh:
        return json.load(fh)


def largest_const_u0_run(d, limit=200000):
    best = (0, None)
    n = len(d)
    for s0 in range(12, min(n - 8, limit), 8):
        o = s0
        c = 0
        u0 = struct.unpack("<H", d[o:o + 2])[0]
        while o + 8 <= n and struct.unpack("<H", d[o:o + 2])[0] == u0:
            c += 1
            o += 8
        if c > best[0]:
            best = (c, s0)
        if c > 9000:
            break
    return best


def trailing_fill_words(d):
    t = len(d)
    while t - 4 >= 0 and d[t - 4:t] == FILL:
        t -= 4
    return (len(d) - t) // 4


class NvmFixtureTests(unittest.TestCase):
    def test_fixture_magic_and_grid(self):
        fx = load_fixture()
        self.assertIn("nv_198c.nvm", fx)
        self.assertIn("nv_1f29.nvm", fx)
        self.assertEqual(fx["nv_198c.nvm"]["grid_records"], 9216)
        self.assertEqual(fx["nv_198c.nvm"]["post_grid_bytes"], 37814)

    def test_nv_198c_record_shape(self):
        fx = load_fixture()
        recs = fx["nv_198c.nvm"]["sample_records"]
        for r in recs:
            self.assertEqual(len(r), 4)
            self.assertEqual(r[0], 0)
            self.assertIn(r[1], (0, 1))
            self.assertEqual(r[2], 279)
        values = {r[3] for r in recs}
        self.assertTrue(values)

    def test_grid_family_consistency(self):
        fx = load_fixture()
        for name, expected in GRID_SAMPLES.items():
            rec = fx.get(name)
            self.assertIsNotNone(rec, name)
            self.assertEqual(rec["grid_records"], expected["grid_records"], name)
            self.assertEqual(rec["post_grid_bytes"], expected["post_grid"], name)
            self.assertEqual(rec["trailing_fill_words"], expected["fill"], name)

    def test_square_grid_arithmetic(self):
        self.assertEqual(96 * 96, 9216)
        self.assertEqual(9216 * 8, 73728)


class NvmLiveCheck(unittest.TestCase):
    def test_live_repro_from_archives(self):
        sro_dir = os.environ.get("SRO_PK2_DIR")
        if not sro_dir:
            self.skipTest("SRO_PK2_DIR not set (archives unavailable)")
        import pk2_table
        files, _ = pk2_table.inventory(os.path.join(sro_dir, "Data.pk2"))
        by_name = {f["path"].split("/")[-1]: f for f in files}
        with open(os.path.join(sro_dir, "Data.pk2"), "rb") as fh:
            for name, expected in GRID_SAMPLES.items():
                e = by_name.get(name)
                self.assertIsNotNone(e, name)
                fh.seek(e["pos"])
                d = fh.read(e["size"])
                self.assertEqual(d[:12], b"JMXVNVM 1000", name)
                cnt, start = largest_const_u0_run(d)
                self.assertGreaterEqual(cnt, 9000, f"{name}: no big grid run")
                self.assertEqual(cnt, expected["grid_records"], name)
                self.assertEqual(len(d) - (start + cnt * 8), expected["post_grid"], name)
                self.assertEqual(trailing_fill_words(d), expected["fill"], name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
