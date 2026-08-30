"""Phase 13 worldmap asset resolution tests.

Phase 12 left 3 texture refs from worldmap_mapinfo.tsv UNRESOLVED. Phase 13
resolved all 3 against the ORIGINAL Media.pk2 archive (read-only):

  1. interface/worldmap/map/map_world_          -> tile-grid prefix expanding to
     632 real files map_world_<cellx>x<celly>.ddj (128x128 DDS tiles). Row 0 of
     worldmap_mapinfo.tsv declares the montage geometry: 4224x1408 px = 132x44
     region cells at 32 px/cell, tile 128 px = 4x4 cells ("4x4" tag). Placement
     is non-uniform (base grid every 4 cells + interleaved denser rows + 45
     out-of-bounds cells x>=199) so the exact montage layout is UNKNOWN and is
     NOT reconstructed.
  2. interface/worldmap/map/map_bagdad.ddj         -> Map_bagdad.ddj
     (case-insensitive match, 524436 B, 1024x1024).
  3. interface/worldmap/map/map_bagdad_dungeon.ddj -> Map_bagdad_dungeon.ddj
     (case-insensitive match, 524436 B, 1024x1024).

Static tests run against the committed derived fixture scripts/testdata/formats/
worldmap_resolved.json (extracted read-only from Media.pk2) and the committed
TEXTURE_CONVERSION_MANIFEST.tsv + converted WebP outputs. The live check
re-verifies the family facts against the real archive when SRO_PK2_DIR is set,
otherwise it reports SKIPPED.

Running:
    python3 scripts/test_phase13_worldmap_resolution.py
"""

import csv
import io
import json
import os
import re
import sys
import unittest
from pathlib import Path
from collections import Counter

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
TD = SCRIPTS / "testdata" / "formats"
MANIFEST = ROOT / "TEXTURE_CONVERSION_MANIFEST.tsv"
WORLDMAP_OUT = ROOT / "android-assets" / "textures" / "worldmap"

UNRESOLVED_REF1 = "interface/worldmap/map/map_world_"
UNRESOLVED_REF2 = "interface/worldmap/map/map_bagdad.ddj"
UNRESOLVED_REF3 = "interface/worldmap/map/map_bagdad_dungeon.ddj"


def load_manifest():
    rows = []
    with open(MANIFEST, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip() or line.startswith("source_archive"):
                continue
            cells = line.rstrip("\n").split("\t")
            if len(cells) >= 9:
                rows.append(dict(zip(
                    ["archive", "path", "status", "src_size", "src_sha",
                     "fmt", "w", "h", "out", "out_size", "out_sha"],
                    cells)))
    return rows


class ManifestTests(unittest.TestCase):
    def test_no_unresolved_rows(self):
        rows = load_manifest()
        unresolved = [r for r in rows if r["status"] == "UNRESOLVED"]
        self.assertEqual(unresolved, [], "all worldmap refs must now resolve")

    def test_map_world_family_row(self):
        with open(TD / "worldmap_resolved.json", encoding="utf-8") as fh:
            fx = json.load(fh)
        rows = load_manifest()
        fam = [r for r in rows if r["path"] == UNRESOLVED_REF1]
        self.assertEqual(len(fam), 1)
        r = fam[0]
        self.assertEqual(r["status"], "RESOLVED_FAMILY")
        self.assertEqual(int(r["src_size"]), fx["tile_total_bytes"])
        self.assertEqual((r["w"], r["h"]), ("128", "128"))

    def test_bagdad_rows_converted(self):
        rows = load_manifest()
        bagdad = [r for r in rows if r["path"].lower().endswith("map_bagdad.ddj")]
        dungeon = [r for r in rows if r["path"].lower().endswith("map_bagdad_dungeon.ddj")]
        self.assertEqual(len(bagdad), 1)
        self.assertEqual(len(dungeon), 1)
        for r in bagdad + dungeon:
            self.assertEqual(r["status"], "CONVERTED")
            self.assertEqual(r["fmt"], "DDS")
            self.assertEqual((r["w"], r["h"]), ("1024", "1024"))
            self.assertEqual(int(r["src_size"]), 524436)
            self.assertTrue(Path(r["out"]).is_file(), r["out"])

    def test_tile_family_count_and_outputs(self):
        with open(TD / "worldmap_resolved.json", encoding="utf-8") as fh:
            fx = json.load(fh)
        rows = load_manifest()
        tiles = [r for r in rows if re.search(r"map_world_\d+x\d+\.ddj$", r["path"])]
        self.assertEqual(len(tiles), fx["tile_count"])
        for r in tiles:
            self.assertEqual(r["status"], "CONVERTED")
            self.assertEqual((r["w"], r["h"]), ("128", "128"))
            self.assertTrue(Path(r["out"]).is_file(), r["out"])

    def test_phase12_converted_rows_preserved(self):
        rows = load_manifest()
        preserved = [r for r in rows if r["status"] == "CONVERTED"
                     and "map_world_" not in r["path"]
                     and "bagdad" not in r["path"].lower()]
        self.assertEqual(len(preserved), 29)
        for r in preserved:
            self.assertTrue(r["src_sha"], "sha must be recorded")
            self.assertTrue(Path(r["out"]).is_file(), r["out"])


class FamilyLiveCheck(unittest.TestCase):
    def test_family_against_real_archive(self):
        sro_dir = os.environ.get("SRO_PK2_DIR")
        if not sro_dir:
            self.skipTest("SRO_PK2_DIR not set (archives unavailable)")
        from PIL import Image
        import pk2_table
        with open(TD / "worldmap_resolved.json", encoding="utf-8") as fh:
            fx = json.load(fh)
        files, _ = pk2_table.inventory(os.path.join(sro_dir, "Media.pk2"))
        tiles = [f for f in files if f["path"].startswith("/interface/worldmap/map/map_world_")]
        self.assertEqual(len(tiles), fx["tile_count"])
        self.assertEqual(sum(f["size"] for f in tiles), fx["tile_total_bytes"])
        hist = Counter(f["size"] for f in tiles)
        self.assertEqual(dict(hist), {int(k): v for k, v in fx["size_histogram"].items()})
        coords = []
        for f in tiles:
            m = re.search(r"map_world_(\d+)x(\d+)\.ddj", f["path"])
            coords.append((int(m.group(1)), int(m.group(2))))
        xs = {c[0] for c in coords}
        ys = {c[1] for c in coords}
        self.assertEqual((min(xs), max(xs)), (fx["x_min"], fx["x_max"]))
        self.assertEqual((min(ys), max(ys)), (fx["y_min"], fx["y_max"]))
        sample = tiles[0]
        with open(os.path.join(sro_dir, "Media.pk2"), "rb") as fh:
            fh.seek(sample["pos"])
            data = fh.read(sample["size"])
        self.assertEqual(data[:12], b"JMXVDDJ 1000")
        img = Image.open(io.BytesIO(data[20:]))
        self.assertEqual(img.size, (128, 128))


if __name__ == "__main__":
    unittest.main(verbosity=2)
