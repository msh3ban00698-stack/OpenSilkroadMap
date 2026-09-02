#!/usr/bin/env python3
"""Phase 30 merchant shop placement parity test.

Proves, from the committed assets only, the concrete runtime merchant shop
placement index that the Android {@code MerchantShopSpawns} composes from
{@code ShopMerchantIndex} + {@code NpcSpawnIndex}:

  * shopdata.tsv col5 merchant_refid (>0) names the NPC RefCharID running the
    store named in col2 (52 NPC stores);
  * npcpos.tsv world rows (non-negative region code) supply each merchant
    RefCharID's spawn sector + local x/z; every placed store must have EXACTLY
    one world spawn (51/52; STORE_AM_SPECIAL/7568 has none and is never given
    coordinates);
  * file order is preserved (placed(0) = shopdata row 1 STORE_CH_SMITH / 2003);
  * the Jangan sector (168,97) holds 7 placed merchants and the Jangan_Field
    region window (156-182 x 89-102) holds 12; the committed default launch
    sectors (156x89-156x90) hold 0.

Nothing is invented: every assertion is a direct consequence of already-proven
facts or of the committed data itself.
"""
import unittest
from pathlib import Path

from shop_merchant_evidence import _int, load_rows

TEXTDATA = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game/textdata"

SECTOR_WORLD = 1920.0


def unpack_region(region: int):
    return (region & 0xFF, region >> 8)


class CommittedMerchantSpawnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shop = load_rows("shopdata.tsv")
        cls.npc = load_rows("npcpos.tsv")

    def _npc_stores(self):
        return [r for r in self.shop if len(r) > 5 and _int(r, 5) > 0]

    def _world_spawns_by_refid(self):
        out = {}
        for row in self.npc:
            region = _int(row, 1)
            if region < 0:
                continue
            rid = _int(row, 0)
            out.setdefault(rid, []).append(
                (unpack_region(region), float(row[2]), float(row[3]), float(row[4])))
        return out

    def _placed(self):
        by = self._world_spawns_by_refid()
        placed = []
        spawnless = 0
        for store in self._npc_stores():
            refid = _int(store, 5)
            spawns = by.get(refid)
            if not spawns or len(spawns) != 1:
                spawnless += 1
                continue
            placed.append((refid, store[2], spawns[0]))
        return placed, spawnless

    def test_npc_store_and_spawn_counts(self):
        placed, spawnless = self._placed()
        self.assertEqual(len(self._npc_stores()), 52)
        self.assertEqual(len(placed), 51)
        self.assertEqual(spawnless, 1)
        refids = [p[0] for p in placed]
        self.assertNotIn(7568, refids)
        self.assertEqual(len(set(refids)), 51)

    def test_placed_zero_is_smith_at_jangan_sector(self):
        placed, _ = self._placed()
        refid, code, ((sx, sy), x, y, z) = placed[0]
        self.assertEqual(refid, 2003)
        self.assertEqual(code, "STORE_CH_SMITH")
        self.assertEqual((sx, sy), (168, 97))
        self.assertAlmostEqual(x, 332.73, places=2)
        self.assertAlmostEqual(z, 1406.7, places=2)
        # world coords relative to the merchant's own sector equal local coords.
        self.assertAlmostEqual(x + (sx - 168) * SECTOR_WORLD, x, places=2)
        self.assertAlmostEqual(z + (sy - 97) * SECTOR_WORLD, z, places=2)

    def test_jangan_windows_match(self):
        placed, _ = self._placed()

        def in_window(x0, x1, y0, y1):
            return [
                (rid, code) for (rid, code, ((sx, sy), _, _, _)) in placed
                if x0 <= sx <= x1 and y0 <= sy <= y1]

        sector = in_window(168, 168, 97, 97)
        self.assertEqual(len(sector), 7)
        codes = sorted(code for _, code in sector)
        self.assertEqual(codes, sorted([
            "STORE_CH_SMITH", "STORE_CH_ARMOR", "STORE_CH_POTION",
            "STORE_CH_ACCESSORY", "STORE_CH_STABLE", "STORE_CH_SPECIAL",
            "STORE_CH_TRADER"]))
        field = in_window(156, 182, 89, 102)
        self.assertEqual(len(field), 12)
        rendered = in_window(156, 156, 89, 90)
        self.assertEqual(len(rendered), 0)


if __name__ == "__main__":
    unittest.main()
