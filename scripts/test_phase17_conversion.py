"""Phase 17: BMS -> MSH conversion tests (hermetic + live archive proofs)."""

import os
import struct
import unittest

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BASE, "testdata", "formats", "bms_samples")

MAP_PK2 = "/tmp/opencode/pk2raw/Map.pk2"
DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"

ARCHIVES = os.path.exists(MAP_PK2) and os.path.exists(DATA_PK2)

import sys
sys.path.insert(0, BASE)

from bms_to_asset import (  # noqa: E402
    LAYOUT_LIGHTMAP,
    LAYOUT_STD44,
    MSH_MAGIC,
    MshFormatError,
    bms_to_msh,
    read_msh,
)

if ARCHIVES:
    import pk2_table  # noqa: E402


def _sample(name):
    with open(os.path.join(SAMPLES, name), "rb") as fh:
        return fh.read()


class MshConversionHermeticTest(unittest.TestCase):
    def test_magic_and_version(self):
        blob, _ = bms_to_msh(_sample("artifact_table.bms"))
        self.assertTrue(blob.startswith(MSH_MAGIC))
        self.assertEqual(1, blob[4])

    def test_standard_roundtrip(self):
        blob, prov = bms_to_msh(_sample("artifact_table.bms"))
        parsed = read_msh(blob)
        self.assertEqual(LAYOUT_STD44, parsed["layout"])
        self.assertEqual(prov["asset"]["vertex_count"], parsed["vertex_count"])
        self.assertEqual(142, parsed["vertex_count"])
        self.assertEqual(74, parsed["triangle_count"])
        self.assertEqual(0, parsed["non_static_vertices"])
        # spot-check first vertex + triangle
        self.assertEqual(3, len(parsed["vertices"][0]["position"]))
        self.assertEqual(3, len(parsed["vertices"][0]["normal"]))
        self.assertEqual(2, len(parsed["vertices"][0]["uv"]))
        self.assertFalse(parsed["has_uv2"])
        for a, b, c in parsed["triangles"]:
            self.assertTrue(a < parsed["vertex_count"])
            self.assertTrue(b < parsed["vertex_count"])
            self.assertTrue(c < parsed["vertex_count"])

    def test_deterministic_bytes(self):
        blob1, _ = bms_to_msh(_sample("bldg_tree.bms"))
        blob2, _ = bms_to_msh(_sample("bldg_tree.bms"))
        self.assertEqual(blob1, blob2)

    def test_all_vertices_kept_with_flags(self):
        # Real static trees contain flags==2 canopy vertices; ALL must survive.
        blob, prov = bms_to_msh(_sample("bldg_tree.bms"))
        parsed = read_msh(blob)
        self.assertGreater(parsed["non_static_vertices"], 0)
        self.assertEqual(12948, parsed["vertex_count"])
        self.assertEqual(12948, prov["source"]["vertex_count"])
        self.assertEqual(20522, parsed["triangle_count"])
        for a, b, c in parsed["triangles"]:
            self.assertTrue(max(a, b, c) < parsed["vertex_count"])

    def test_lightmap_uv2_preserved(self):
        blob, prov = bms_to_msh(_sample("v52_bldg.bms"))
        parsed = read_msh(blob)
        self.assertEqual(LAYOUT_LIGHTMAP, parsed["layout"])
        self.assertTrue(parsed["has_uv2"])
        self.assertEqual(0, parsed["non_static_vertices"])
        self.assertTrue(all(len(v["uv2"]) == 2 for v in parsed["vertices"]))
        self.assertEqual(prov["source"]["layout"], "lightmap")

    def test_lightmap_path_provenance(self):
        blob, prov = bms_to_msh(_sample("v52_bldg.bms"))
        self.assertTrue(isinstance(prov["source"]["lightmap_path"], (str, type(None))))

    def test_bad_input(self):
        with self.assertRaises(MshFormatError):
            bms_to_msh(b"not a bms mesh at all" * 8)
        with self.assertRaises(MshFormatError):
            read_msh(b"XXXX" + b"\x00" * 40)

    def test_roundtrip_positions_preserved(self):
        blob, _ = bms_to_msh(_sample("artifact_table.bms"))
        parsed = read_msh(blob)
        src = _sample("artifact_table.bms")
        self.assertTrue(len(parsed["vertices"]) > 0)
        for v in parsed["vertices"]:
            self.assertTrue(all(isinstance(x, float) for x in v["position"]))
            self.assertTrue(all(-1.1 <= n <= 1.1 for n in v["normal"]))


@unittest.skipUnless(ARCHIVES, "live archives not present")
class MshTreeLiveTest(unittest.TestCase):
    """Proves the REAL tree meshes convert with Phase 16-verified geometry."""

    @classmethod
    def setUpClass(cls):
        entries, _ = pk2_table.inventory(DATA_PK2)
        cls.by_path = {e["path"].lower(): e for e in entries}

    def _read(self, path):
        e = self.by_path["/" + path.lstrip("/").lower()]
        with open(DATA_PK2, "rb") as fh:
            fh.seek(e["pos"])
            return fh.read(e["size"])

    def _tree03_parts(self):
        base = "/prim/mesh/nature/common/tree/new-maple/"
        parts = []
        for i in (1, 2, 3):
            parts.append(self._read(base + f"tre_tree03_0{i}.bms"))
        return parts

    def _tree02_parts(self):
        base = "/prim/mesh/nature/common/tree/"
        parts = []
        for i in (1, 2, 3):
            parts.append(self._read(base + f"tre_tree02_0{i}.bms"))
        return parts

    def test_tree03_real_geometry(self):
        parts = self._tree03_parts()
        expect_v = (216, 154, 30)
        expect_t = (108, 192, 32)
        for idx, (blob, ev, et) in enumerate(zip(parts, expect_v, expect_t)):
            _, prov = bms_to_msh(blob)
            self.assertEqual(ev, prov["asset"]["vertex_count"], f"part {idx + 1}")
            self.assertEqual(et, prov["asset"]["triangle_count"], f"part {idx + 1}")
        # canopy vertices (flags != 0) are preserved, not dropped
        _, prov = bms_to_msh(parts[1])
        self.assertGreater(prov["asset"]["non_static_vertices"], 0)

    def test_tree02_real_geometry(self):
        parts = self._tree02_parts()
        _, prov = bms_to_msh(parts[0])
        self.assertEqual(304, prov["source"]["vertex_count"])
        self.assertEqual(152, prov["asset"]["triangle_count"])
        self.assertEqual(1, prov["source"]["bone_count"])

    def test_tree_aabb_preserved_in_provenance(self):
        part = self._tree03_parts()[0]
        _, prov = bms_to_msh(part)
        self.assertIsNotNone(prov["source"]["aabb"])
        self.assertEqual(6, len(prov["source"]["aabb"]))

    def test_tree_msh_size_consistency(self):
        blob, _ = bms_to_msh(self._tree03_parts()[0])
        parsed = read_msh(blob)
        self.assertEqual(216, parsed["vertex_count"])
        self.assertEqual(108, parsed["triangle_count"])
        self.assertEqual(24 + 216 * 32 + 108 * 6, len(blob))


if __name__ == "__main__":
    unittest.main()
