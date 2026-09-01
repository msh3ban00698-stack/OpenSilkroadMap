#!/usr/bin/env python3
"""Region resolver + coordinate model tests over the committed region tables.

Proves, from committed data only (no archives required):

  * the region packing formula region == (sector_y << 8) | sector_x holds for
    every row of the derived server region_zone.tsv;
  * the server RefRegion sector space overlaps the client regioncode id space
    (2442/2444) and the RegionInfo grid (2396/2444);
  * region 25000 resolves to RN_CH_JANGAN / 장안 at sector (168, 97);
  * the corrected regioncode.tsv contains proper Korean (no latin-1 mojibake);
  * unknown / instance codes fail closed (resolve -> None / sector None).

Nothing is invented: every assertion is a consequence of committed data or of
already-proven coordinate facts.
"""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import region_resolver as rr  # noqa: E402
import world_terrain as wt  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game"
REGION_CODE = ASSETS / "textdata" / "regioncode.tsv"
REGION_ZONE = ASSETS / "world" / "region_zone.tsv"
REGIONS = ASSETS / "regions.tsv"

MOJIBAKE_CHARS = "Á-ýßþð"


def _zone_rows():
    out = []
    for line in REGION_ZONE.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        p = line.split("\t")
        out.append((int(p[0]), int(p[1]), int(p[2]), p[3], p[4], p[5]))
    return out


def _regioninfo_cells():
    cells = set()
    for line in REGIONS.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        p = line.split("\t")
        if len(p) >= 4:
            for tok in p[3].split(","):
                first = tok.split(":")[:2]
                if len(first) == 2 and all(v.lstrip("-").isdigit() for v in first):
                    cells.add((int(first[0]), int(first[1])))
    return cells


class PackingFormulaTests(unittest.TestCase):
    def test_id_equals_y_shl8_or_x_for_all_rows(self):
        rows = _zone_rows()
        self.assertEqual(len(rows), 2444)
        for rid, x, y, _n, _f, _z in rows:
            self.assertEqual(rid, (y << 8) | x, rid)
            self.assertEqual(wt.unpack_region(rid), (x, y))

    def test_unpack_pack_roundtrip(self):
        for rid, _x, _y, _n, _f, _z in _zone_rows():
            sx, sy = wt.unpack_region(rid)
            self.assertEqual(wt.pack_region(sx, sy), rid)


class ResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = rr.RegionResolver.load_default()

    def test_jangan_region_resolution(self):
        e = self.resolver.resolve(25000)
        self.assertIsNotNone(e)
        self.assertEqual(e.name_code, "RN_CH_JANGAN")
        self.assertEqual(e.localized_name, "장안")
        self.assertEqual(e.sector_x, 168)
        self.assertEqual(e.sector_y, 97)
        self.assertEqual(e.server_name, "CHINA")
        self.assertEqual(e.zone_id, "1001")
        self.assertFalse(e.is_instance)

    def test_jangan_name_code_lookup(self):
        entries = self.resolver.by_name_code("RN_CH_JANGAN")
        self.assertGreaterEqual(len(entries), 5)
        sectors = {(e.sector_x, e.sector_y) for e in entries}
        self.assertIn((168, 97), sectors)

    def test_fail_closed_unknown(self):
        self.assertIsNone(self.resolver.resolve(0x7FFFFFFF))

    def test_instance_code_no_sector(self):
        e = self.resolver.resolve(-32760)
        self.assertIsNone(e)

    def test_known_names_have_hangul(self):
        hangul = 0
        for rid in self.resolver.region_ids():
            e = self.resolver.resolve(rid)
            if e is not None and e.localized_name:
                hangul += sum("\uac00" <= ch <= "\ud7a3" for ch in e.localized_name) > 0
        self.assertGreaterEqual(hangul, 1000)


class MojibakeTests(unittest.TestCase):
    def test_no_latin1_mojibake_in_localized_names(self):
        bad = 0
        sample = None
        for line in REGION_CODE.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) >= 4:
                for ch in p[3]:
                    if "\u00c0" <= ch <= "\u00ff" or ch in "ßð":
                        bad += 1
                        sample = sample or line
        self.assertEqual(bad, 0, f"mojibake rows: {sample}")

    def test_jangan_localized_is_proper_korean(self):
        rows = [l.split("\t") for l in REGION_CODE.read_text(encoding="utf-8").splitlines()
                if l.startswith("1\t25000\t")]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "RN_CH_JANGAN")
        self.assertEqual(rows[0][3], "장안")


class CrossEvidenceTests(unittest.TestCase):
    def test_zone_table_header_facts(self):
        header = [l for l in REGION_ZONE.read_text(encoding="utf-8").splitlines()
                  if l.startswith("# rows=")]
        self.assertEqual(len(header), 1)
        self.assertIn("rows=2444", header[0])
        self.assertIn("names=21", header[0])
        self.assertIn("zones=13", header[0])

    def test_refregion_ids_overlap_client(self):
        zone_ids = {r[0] for r in _zone_rows()}
        client_ids = set()
        for line in REGION_CODE.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) > 1 and p[1].strip().lstrip("-").isdigit():
                client_ids.add(int(p[1]))
        overlap = zone_ids & client_ids
        self.assertEqual(len(overlap), 2442)

    def test_sectors_overlap_regioninfo_grid(self):
        zone_sectors = {(r[1], r[2]) for r in _zone_rows()}
        grid = _regioninfo_cells()
        self.assertGreaterEqual(len(zone_sectors & grid), 2396)
        self.assertLessEqual(len(zone_sectors - grid), 48)


if __name__ == "__main__":
    unittest.main(verbosity=2)
