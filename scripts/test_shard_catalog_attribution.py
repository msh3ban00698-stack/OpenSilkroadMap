#!/usr/bin/env python3
"""Catalog attribution tests for the read-only shard catalog index.

Verifies scripts/build_shard_catalog_index.py output against byte-validated
offsets in SRO_VT_SHARD.Bak (SRO_DB_DIR). The backup is never modified.

Assertions:
  * page-1835 name->id index resolves the five verified targets to the exact
    catalog ids (PROVEN), with _RefOptionalTeleport at page offset 4231.
  * the avatar `_Char` spawn column signature CharName=4, CharScale=5,
    StartRegionID=6, StartPos_X=7, StartPos_Y=8, StartPos_Z=9,
    DefaultTeleport=10 appears verbatim in the 23.1M compact column catalog
    (repeated across the replicated avatar tables).
  * every StartRegionID occurrence in the file is preceded by an avatar column
    (CharScale), never by `ID`, so no `_RefInstance_World_Start_Pos` column
    block exists under the SRO-reference Service/ID/StartRegionID/StartPos_*
    names in the scanned catalog regions.
  * the index builder is deterministic: two runs produce byte-identical JSON.
"""
import hashlib
import json
import os
import unittest
from pathlib import Path

from sro_paths import REPO_ROOT

sys_path = __import__("sys")
sys_path.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_shard_catalog_index import ShardCatalogIndex  # noqa: E402

INDEX_JSON = Path(REPO_ROOT) / "scripts/testdata/formats/shard_catalog_index.json"

EXPECTED_NAME_IDS = {
    "_RefInstance_World_Start_Pos": 524_437_538,
    "_RefInstance_World_Region": 508_437_481,
    "_RefOptionalTeleport": 935_583_017,
    "_RefGame_World": 380_437_025,
    "_RefFmnTidGroup": 284_436_683,
}

AVATAR_SPAWN_SIGNATURE = [
    (4, "CharName"),
    (5, "CharScale"),
    (6, "StartRegionID"),
    (7, "StartPos_X"),
    (8, "StartPos_Y"),
    (9, "StartPos_Z"),
    (10, "DefaultTeleport"),
]


def _bak_path():
    db_dir = os.environ.get("SRO_DB_DIR")
    if not db_dir:
        return None
    p = Path(db_dir) / "SRO_VT_SHARD.Bak"
    return p if p.is_file() else None


@unittest.skipUnless(_bak_path(), "SRO_DB_DIR/SRO_VT_SHARD.Bak not available")
class TestShardCatalogAttribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bak = _bak_path()
        cls.index = ShardCatalogIndex(str(cls.bak))
        cls.ev = cls.index.run()
        cls.ev_on_disk = json.loads(INDEX_JSON.read_text(encoding="utf-8"))

    def test_name_index_resolves_verified_targets(self):
        vt = self.ev["page1835_name_index"]["verified_targets"]
        self.assertEqual(vt, EXPECTED_NAME_IDS)

    def test_name_index_walk_reaches_optional_teleport_at_4231(self):
        rows = self.ev["page1835_name_index"]["rows"]
        self.assertGreaterEqual(len(rows), 90)
        opt = [r for r in rows if r["name"] == "_RefOptionalTeleport"]
        self.assertEqual(len(opt), 1)
        self.assertEqual(opt[0]["offset"], 4231)
        self.assertEqual(opt[0]["id"], 935_583_017)

    def test_avatar_spawn_signature_present_and_repeated(self):
        recs = self.ev["column_catalog_23_1M"]["records"]
        runs = 0
        for i in range(len(recs) - len(AVATAR_SPAWN_SIGNATURE) + 1):
            window = [
                (r["colid"], r["name"]) for r in recs[i : i + len(AVATAR_SPAWN_SIGNATURE)]
            ]
            if window == AVATAR_SPAWN_SIGNATURE:
                runs += 1
        self.assertGreaterEqual(runs, 5, "avatar spawn signature not replicated")

    def test_every_start_region_preceded_by_avatar_column_not_id(self):
        nr = self.ev["start_region_negative"]
        occs = nr["occurrences"]
        self.assertEqual(len(occs), 12)
        self.assertTrue(nr["no_occurrence_preceded_by_id"])
        self.assertTrue(nr["all_preceded_by_avatar_column"])
        for h in occs:
            self.assertNotEqual(h["prev_column"], "ID")

    def test_classifications_recorded(self):
        cls = self.ev["classification"]
        self.assertEqual(cls["page1835_name_index"], "PROVEN")
        self.assertEqual(cls["start_region_negative"], "PROVEN")

    def test_output_on_disk_matches_recomputed(self):
        round_tripped = json.loads(json.dumps(self.ev))
        self.assertEqual(round_tripped, self.ev_on_disk)

    def test_deterministic_rebuild(self):
        digest_a = hashlib.sha256(
            json.dumps(self.ev, sort_keys=True).encode("utf-8")
        ).hexdigest()
        second = ShardCatalogIndex(str(self.bak)).run()
        digest_b = hashlib.sha256(
            json.dumps(second, sort_keys=True).encode("utf-8")
        ).hexdigest()
        self.assertEqual(digest_a, digest_b)


if __name__ == "__main__":
    unittest.main()
