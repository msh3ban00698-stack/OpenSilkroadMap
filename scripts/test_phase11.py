"""Phase 11 inventory + textdata catalog tests.

Static tests run against the committed outputs (no archives required):
  COMPLETE_SOURCE_INVENTORY.json / .md
  TEXTDATA_CATALOG.tsv / TEXTDATA_NORMALIZED_MANIFEST.tsv
  android/app/src/main/assets/game/textdata/*.tsv

A live determinism check reruns the generators against the real archives when
SRO_PK2_DIR is set (requires the 5 read-only VSRO-R 1.193 archives); otherwise
it reports SKIPPED. No test writes to the source archives.

Running:
    python3 scripts/test_phase11.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import build_source_inventory as bsi  # noqa: E402
import build_textdata_catalog as btc  # noqa: E402

ARCHIVES = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")
TEXTDATA_DIR = REPO / "android" / "app" / "src" / "main" / "assets" / "game" / "textdata"


def load_json():
    with open(REPO / "COMPLETE_SOURCE_INVENTORY.json", encoding="utf-8") as fh:
        return json.load(fh)


def load_catalog():
    rows = {}
    with open(REPO / "TEXTDATA_CATALOG.tsv", encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            cells = line.rstrip("\n").split("\t")
            rows[cells[0]] = dict(zip(header, cells))
    return rows


class InventoryJsonTests(unittest.TestCase):
    def setUp(self):
        self.doc = load_json()

    def test_schema_and_archive_counts(self):
        self.assertEqual(self.doc["schema"], "sro-source-inventory-v1")
        names = [a["name"] for a in self.doc["archives"]]
        self.assertEqual(names, list(ARCHIVES))
        for a in self.doc["archives"]:
            self.assertGreaterEqual(a["bytes"], 0)
            self.assertEqual(len(a["fingerprint_sha256_1mib"]), 64)

    def test_files_match_archive_counts(self):
        total = sum(a["files"] for a in self.doc["archives"])
        self.assertEqual(len(self.doc["files"]), total)
        per = {a["name"]: a["files"] for a in self.doc["archives"]}
        got = {}
        for rec in self.doc["files"]:
            name = self.doc["archives"][rec[0]]["name"]
            got[name] = got.get(name, 0) + 1
        self.assertEqual(got, per)

    def test_no_duplicate_paths(self):
        seen = set()
        for rec in self.doc["files"]:
            key = (rec[0], rec[1])
            self.assertNotIn(key, seen, f"duplicate {key}")
            seen.add(key)

    def test_files_sorted(self):
        keys = [(r[0], r[1]) for r in self.doc["files"]]
        self.assertEqual(keys, sorted(keys))

    def test_every_extension_has_status(self):
        for rec in self.doc["files"]:
            ext = rec[1].rsplit(".", 1)[-1].lower() if "." in rec[1] else "(none)"
            info = self.doc["extensions"].get(ext)
            self.assertIsNotNone(info, f"no extension entry for {ext}")
            self.assertIn(info["status"], ("TEXT", "VERIFIED", "PARSEABLE", "UNKNOWN"))

    def test_extension_census_sums(self):
        by_ext = {}
        for rec in self.doc["files"]:
            ext = rec[1].rsplit(".", 1)[-1].lower() if "." in rec[1] else "(none)"
            by_ext[ext] = by_ext.get(ext, 0) + rec[2]
        for ext, info in self.doc["extensions"].items():
            self.assertEqual(info["count"], sum(1 for r in self.doc["files"]
                                                if (r[1].rsplit(".", 1)[-1].lower()
                                                    if "." in r[1] else "(none)") == ext))

    def test_classifier_consistency(self):
        for rec in self.doc["files"]:
            ext = rec[1].rsplit(".", 1)[-1].lower() if "." in rec[1] else "(none)"
            self.assertEqual(self.doc["extensions"][ext]["status"], bsi.ext_status(ext))

    def test_ext_status_mapping(self):
        self.assertEqual(bsi.ext_status("wav"), "VERIFIED")
        self.assertEqual(bsi.ext_status("ogg"), "VERIFIED")
        self.assertEqual(bsi.ext_status("ddj"), "PARSEABLE")
        self.assertEqual(bsi.ext_status("txt"), "TEXT")
        self.assertEqual(bsi.ext_status("vsh"), "TEXT")
        self.assertEqual(bsi.ext_status("dat"), "UNKNOWN")


class TextdataCatalogTests(unittest.TestCase):
    def setUp(self):
        self.cat = load_catalog()

    def test_all_files_cataloged(self):
        expected = 159
        self.assertEqual(len(self.cat), expected)

    def test_allowlist_normalized(self):
        for name in btc.ALLOWLIST:
            self.assertIn(name, self.cat)
            self.assertEqual(self.cat[name]["status"], "NORMALIZED", name)

    def test_status_rollup(self):
        counts = {}
        for row in self.cat.values():
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        self.assertGreaterEqual(counts.get("NORMALIZED", 0), 20)
        self.assertEqual(counts.get("ENCRYPTED", 0), 7)
        self.assertEqual(sum(counts.values()), 159)

    def test_normalized_assets_exist_on_disk(self):
        normalized = [n for n, r in self.cat.items() if r["status"] == "NORMALIZED"]
        for name in normalized:
            target = TEXTDATA_DIR / (name[:-4] + ".tsv")
            self.assertTrue(target.is_file(), f"missing {target}")

    def test_normalized_count_matches_disk(self):
        disk = sorted(p.name for p in TEXTDATA_DIR.glob("*.tsv"))
        expected = sorted(n[:-4] + ".tsv" for n, r in self.cat.items()
                          if r["status"] == "NORMALIZED")
        self.assertEqual(disk, expected)

    def test_key_record_counts(self):
        checks = {
            "npcpos.txt": (18457, 5),
            "leveldata.txt": (151, 10),
            "questdata.txt": (1005, None),
            "refoptionalteleport.txt": (45, None),
            "refshopgoods.txt": (2283, None),
            "regioncode.txt": (3294, 4),
            "teleportdata.txt": (247, None),
        }
        for name, (records, cols) in checks.items():
            row = self.cat[name]
            self.assertEqual(int(row["records"]), records, name)
            if cols is not None:
                self.assertEqual(int(row["cols"]), cols, name)

    def test_npcpos_content(self):
        with open(TEXTDATA_DIR / "npcpos.tsv", encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
        self.assertEqual(len(lines), 18457)
        first = lines[0].split("\t")
        self.assertEqual(len(first), 5)
        int(first[0])
        float(first[2])
        float(first[4])

    def test_leveldata_content(self):
        with open(TEXTDATA_DIR / "leveldata.tsv", encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
        self.assertEqual(len(lines), 151)
        data = [l for l in lines if not l.startswith("//")]
        self.assertEqual(len(data), 150)
        levels = [int(l.split("\t")[0]) for l in data]
        self.assertEqual(levels[0], 1)
        self.assertEqual(levels[-1], 150)


class LiveDeterminismTests(unittest.TestCase):
    def test_regeneration_matches_committed(self):
        pk2 = os.environ.get("SRO_PK2_DIR")
        if not pk2 or not (Path(pk2) / "Media.pk2").is_file():
            self.skipTest("SRO_PK2_DIR with real archives not set")
        with tempfile.TemporaryDirectory() as tmp:
            doc = bsi.build(Path(pk2), Path(tmp))
            committed = load_json()
            for key in ("files", "extensions", "archives"):
                self.assertEqual(doc[key], committed[key], key)
            with open(Path(tmp) / "TEXTDATA_CATALOG.tsv", "w") as _:
                pass
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            assets = out / "assets"
            btc.build(Path(pk2), out, assets)
            committed_cat = (REPO / "TEXTDATA_CATALOG.tsv").read_text(encoding="utf-8")
            self.assertEqual((out / "TEXTDATA_CATALOG.tsv").read_text(encoding="utf-8"),
                             committed_cat)


if __name__ == "__main__":
    unittest.main()
