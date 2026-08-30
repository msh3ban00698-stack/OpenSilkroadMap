"""Phase 17: committed object-manifest assets + reproducibility tests."""

import os
import struct
import unittest
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(
    BASE, "..", "android", "app", "src", "main", "assets", "game", "world", "objects"
)

MAP_PK2 = "/tmp/opencode/pk2raw/Map.pk2"
DATA_PK2 = "/tmp/opencode/pk2raw/Data.pk2"

ARCHIVES = os.path.exists(MAP_PK2) and os.path.exists(DATA_PK2)

import sys
sys.path.insert(0, BASE)

from bms_to_asset import read_msh  # noqa: E402


class CommittedManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = cls._read_tsv(os.path.join(ASSETS, "models.tsv"))
        cls.placements = cls._read_tsv(os.path.join(ASSETS, "placements.tsv"))

    @staticmethod
    def _read_tsv(path):
        with open(path) as fh:
            lines = [ln.rstrip("\n").split("\t") for ln in fh if ln.strip()]
        cols = lines[0]
        return [dict(zip(cols, ln)) for ln in lines[1:]]

    def _abs(self, rel):
        return os.path.join(ASSETS, rel)

    def test_manifests_exist(self):
        self.assertTrue(os.path.exists(self._abs("models.tsv")))
        self.assertTrue(os.path.exists(self._abs("placements.tsv")))

    def test_models_resolve_to_real_files(self):
        self.assertGreater(len(self.models), 0)
        for m in self.models:
            self.assertTrue(os.path.exists(self._abs(m["msh_asset"])), m["msh_asset"])
            self.assertTrue(os.path.exists(self._abs(m["tex_asset"])), m["tex_asset"])

    def test_msh_files_parse_with_matching_counts(self):
        for m in self.models:
            with open(self._abs(m["msh_asset"]), "rb") as fh:
                blob = fh.read()
            parsed = read_msh(blob)
            self.assertEqual(int(m["vcount"]), parsed["vertex_count"], m["msh_asset"])
            self.assertEqual(int(m["tcount"]), parsed["triangle_count"], m["msh_asset"])
            self.assertEqual(int(m["non_static"]), parsed["non_static_vertices"])

    def test_textures_are_valid_png(self):
        for m in self.models:
            with open(self._abs(m["tex_asset"]), "rb") as fh:
                head = fh.read(8)
            self.assertEqual(b"\x89PNG\r\n\x1a\n", head, m["tex_asset"])

    def test_models_cover_both_trees(self):
        nameIs = {m["nameI"] for m in self.models}
        self.assertEqual({"574", "820"}, nameIs)
        # tre_tree03 has 3 parts; textures: part0 tre_tree03_01, others pine
        mats = {m["material"] for m in self.models if m["nameI"] == "820"}
        self.assertEqual({"tre_tree03_01", "tre_pine08_02", "tre_pine08_03"}, mats)

    def test_placements_156x90(self):
        rows = [r for r in self.placements
                if r["file_sx"] == "156" and r["file_sy"] == "90"]
        self.assertEqual(32, len(rows))
        nameIs = {r["nameI"] for r in rows}
        self.assertEqual({"574", "820"}, nameIs)
        tails = {(r["tx"], r["tz"]) for r in rows}
        self.assertEqual({("156", "90"), ("157", "90"), ("156", "91")}, tails)
        counts = {}
        for r in rows:
            counts[r["nameI"]] = counts.get(r["nameI"], 0) + 1
        self.assertEqual({"820": 23, "574": 9}, counts)

    def test_placement_world_transform(self):
        # 574 at local (1467.17, 937.03, 1449.66) tail (156,90) -> same sector
        row = next(r for r in self.placements if r["nameI"] == "574")
        self.assertEqual("1467.172", row["x"])
        self.assertEqual("937.029", row["y"])
        self.assertEqual("1449.665", row["z"])


@unittest.skipUnless(ARCHIVES, "live archives not present")
class ManifestReproducibilityTest(unittest.TestCase):
    """Rebuild from original archives into a temp dir and diff against committed."""

    def test_rebuild_matches_committed(self):
        import build_object_manifest as bom
        pk2_dir = os.path.dirname(MAP_PK2)
        with tempfile.TemporaryDirectory() as tmp:
            report = bom.build(tmp, [(156, 90)], pk2_dir)
            self.assertEqual({"models": 6, "placements": 32,
                              "nameIs": [574, 820]}, report)
            for root, _dirs, files in os.walk(tmp):
                for fname in files:
                    rel = os.path.relpath(os.path.join(root, fname), tmp)
                    committed = os.path.join(ASSETS, rel)
                    self.assertTrue(os.path.exists(committed), rel)
                    with open(os.path.join(root, fname), "rb") as fh:
                        rebuilt = fh.read()
                    with open(committed, "rb") as fh:
                        original = fh.read()
                    self.assertEqual(original, rebuilt, rel)


if __name__ == "__main__":
    unittest.main()
