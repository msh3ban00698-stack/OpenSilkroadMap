#!/usr/bin/env python3
"""Phase 30 character-identity parity test.

Proves, from the committed assets only, that character_identity.tsv covers
every distinct npcpos.tsv character_refid plus the spawn-less merchant
STORE_AM_SPECIAL / 7568, using only the three Phase 29 proven characterdata
anchors (col1 refid, col2 code, col52 model path). Live-corpus tests (skipped
when /tmp/opencode/textdata is absent) confirm the committed extract matches
the live Media.pk2 characterdata_*.txt bytes.
"""
import glob
import unittest
from pathlib import Path

from shop_merchant_evidence import _int, load_rows

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "android/app/src/main/assets/game/textdata"
LIVE = Path("/tmp/opencode/textdata")


def load_identity():
    rows = {}
    with open(ASSETS / "character_identity.tsv", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#") or line.startswith("//"):
                continue
            cols = line.split("\t")
            rows[int(cols[0])] = (cols[1], cols[2])
    return rows


class CommittedIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = load_identity()
        cls.npc = load_rows("npcpos.tsv")
        cls.shop = load_rows("shopdata.tsv")

    def test_covers_every_spawn_refid_plus_spawnless_merchant(self):
        spawn_ids = {_int(r, 0) for r in self.npc}
        self.assertEqual(len(spawn_ids), 1180)
        self.assertEqual(len(self.identity), 1181)
        missing = spawn_ids - set(self.identity)
        self.assertEqual(missing, set())
        self.assertIn(7568, self.identity)
        self.assertEqual(set(self.identity) - spawn_ids, {7568})

    def test_jangan_smith_and_am_special_anchors(self):
        self.assertEqual(self.identity[2003],
                         ("NPC_CH_SMITH", r"npc\npc\chinashop_smith.bsr"))
        code, model = self.identity[7568]
        self.assertEqual(code, "NPC_AM_SPECIAL")
        self.assertTrue(model.endswith("AsiaMinor_spacialmerchant.bsr"))

    def test_every_merchant_refid_is_npc_code(self):
        merchants = [r for r in self.shop if len(r) > 5 and _int(r, 5) > 0]
        self.assertEqual(len(merchants), 52)
        for row in merchants:
            refid = _int(row, 5)
            self.assertIn(refid, self.identity)
            code, model = self.identity[refid]
            self.assertTrue(code.startswith("NPC_"), code)
            self.assertTrue(model.lower().endswith(".bsr"), model)


@unittest.skipUnless(LIVE.is_dir(), "/tmp/opencode/textdata live corpus not available")
class LiveCorpusConcordanceTests(unittest.TestCase):
    def test_committed_extract_matches_live_characterdata(self):
        live = {}
        for path in sorted(glob.glob(str(LIVE / "characterdata_*.txt"))):
            raw = Path(path).read_bytes()
            if raw[:2] == b"\xff\xfe":
                text = raw[2:].decode("utf-16-le")
            else:
                text = raw.decode("utf-16", errors="replace")
            for line in text.splitlines():
                cols = line.split("\t")
                if len(cols) <= 52 or not cols[1].strip().isdigit():
                    continue
                live.setdefault(int(cols[1]), (cols[2].strip(), cols[52].strip()))
        identity = load_identity()
        for refid, (code, model) in identity.items():
            self.assertIn(refid, live)
            self.assertEqual(live[refid], (code, model), refid)


if __name__ == "__main__":
    unittest.main()
