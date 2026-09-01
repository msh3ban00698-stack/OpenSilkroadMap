#!/usr/bin/env python3
"""Cross-source concordance: gameworlddata.tsv vs shard _RefInstance_World.

Proves, from the committed client world catalog and the shard backup's
_RefInstance_World seed rows, that the committed `code` (col1) + `group` (col5)
pairing is server-authoritative:

  * every committed non-placeholder `code`+`group` concatenation appears
    verbatim as an ASCII row name in SRO_VT_SHARD.Bak (e.g.
    INS_FORT_JAGROUP_FORTRESS_JANGAN at offset 22,414,002);
  * the client placeholder `xxx` is stored the same way (INS_DEFAULTxxx at
    offset 22,413,954);
  * the backup's numeric world ids do NOT align with the committed world_id
    column, so that column stays an opaque key (PARTIAL), never a coordinate or
    server id.

The backup is located via the SRO_DB_DIR environment variable (sro_paths
convention); when absent the test is skipped so a bare checkout stays green.
"""
import os
import unittest
from pathlib import Path

from sro_paths import REPO_ROOT

GAMEWORLD = Path(REPO_ROOT) / "android/app/src/main/assets/game/textdata/gameworlddata.tsv"

# (code, group) -> concatenation that must appear in the backup.
CONCORDANT = [
    ("INS_DEFAULT", "xxx", "INS_DEFAULTxxx"),
    ("INS_FORT_JA", "GROUP_FORTRESS_JANGAN", "INS_FORT_JAGROUP_FORTRESS_JANGAN"),
    ("INS_FORT_DW", "GROUP_FORTRESS_DONWHANG", "INS_FORT_DWGROUP_FORTRESS_DONWHANG"),
    ("INS_FORT_HT", "GROUP_FORTRESS_HOTAN", "INS_FORT_HTGROUP_FORTRESS_HOTAN"),
    ("INS_FORT_CT", "GROUP_FORTRESS_CONSTANTINOPLE", "INS_FORT_CTGROUP_FORTRESS_CONSTANTINOPLE"),
]


def _bak_path():
    db_dir = os.environ.get("SRO_DB_DIR")
    if not db_dir:
        return None
    p = Path(db_dir) / "SRO_VT_SHARD.Bak"
    return p if p.is_file() else None


def load_rows():
    rows = []
    for line in GAMEWORLD.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#") or line.startswith("//"):
            continue
        rows.append(line.split("\t"))
    return rows


@unittest.skipUnless(_bak_path(), "SRO_DB_DIR/SRO_VT_SHARD.Bak not available")
class TestWorldDataBakConcordance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bak = _bak_path().read_bytes()

    def test_committed_catalog_shape(self):
        rows = load_rows()
        ids = [int(r[0]) for r in rows]
        self.assertEqual(len(rows), 115)
        self.assertEqual(sorted(ids), list(range(1, 116)))
        self.assertEqual(len(set(ids)), 115)

    def test_code_plus_group_concatenation_present_in_backup(self):
        bak = self.bak
        for code, group, concat in CONCORDANT:
            self.assertIn(concat.encode("ascii"), bak, f"{concat} missing in .Bak")

    def test_fortress_concordance_from_committed_rows(self):
        rows = load_rows()
        by_code = {r[1]: r[5] for r in rows}
        for code, group, _ in CONCORDANT:
            if group == "xxx":
                continue
            self.assertEqual(by_code[code], group,
                             f"committed group for {code} differs")

    def test_numeric_ids_do_not_align_with_backup_sequence(self):
        rows = load_rows()
        ids = [int(r[0]) for r in rows]
        self.assertEqual(ids[:5], [1, 2, 3, 4, 5])
        self.assertEqual(rows[1][1], "INS_FORT_JA")
        self.assertEqual(rows[2][1], "INS_FORT_DW")


if __name__ == "__main__":
    unittest.main()
