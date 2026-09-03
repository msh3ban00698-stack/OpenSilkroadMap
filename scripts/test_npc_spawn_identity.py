#!/usr/bin/env python3
"""Optional character_identity attach on npcpos world spawns.

Proves, from committed assets only, that every npcpos.tsv character_refid
(col0) uniquely joins character_identity.tsv (1180 spawn ids + spawn-less
7568). Geometry (region/local x/z) is unchanged. Identity is optional:
without the index, character_code/model_path stay None. Unknown refids
fail closed. SN_* names, stats, and player spawn are not invented.

Proven coverage:
  * 18457 npcpos rows / 1180 distinct refids all resolve
  * 14800 world rows identified; 3657 dungeon rows stay unplaced
  * Jangan 168x97 smith 2003 = NPC_CH_SMITH / npc\\npc\\chinashop_smith.bsr
  * sector 156x90 bandit 1949 has a real .bsr; archer 1944 model is xxx
"""
import unittest
from pathlib import Path

TEXTDATA = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game/textdata"


def _rows(name):
    out = []
    for line in (TEXTDATA / name).read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        out.append(line.split("\t"))
    return out


def _unpack(region):
    return (region & 0xFF, region >> 8)


def _identity():
    out = {}
    for r in _rows("character_identity.tsv"):
        out[int(r[0])] = {"code": r[1], "model_path": r[2]}
    return out


def _world_spawns(identity=None):
    out = []
    for r in _rows("npcpos.tsv"):
        region = int(r[1])
        if region < 0:
            continue
        refid = int(r[0])
        sx, sy = _unpack(region)
        idn = None if identity is None else identity.get(refid)
        out.append({
            "character_refid": refid,
            "region_code": region,
            "sector_x": sx,
            "sector_y": sy,
            "local_x": float(r[2]),
            "local_z": float(r[4]),
            "identity": idn,
        })
    return out


class GeometryOnlyTests(unittest.TestCase):
    def test_parse_without_identity_leaves_code_null(self):
        spawns = _world_spawns(None)
        self.assertEqual(14800, len(spawns))
        self.assertIsNone(spawns[0]["identity"])
        jangan = [s for s in spawns if s["sector_x"] == 168 and s["sector_y"] == 97]
        smith = [s for s in jangan if s["character_refid"] == 2003][0]
        self.assertEqual(332.73, smith["local_x"])
        self.assertIsNone(smith["identity"])


class UniqueJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = _identity()
        cls.npc = _rows("npcpos.tsv")
        cls.world = _world_spawns(cls.identity)

    def test_every_npcpos_refid_resolves(self):
        self.assertEqual(1181, len(self.identity))
        missing = 0
        for r in self.npc:
            if int(r[0]) not in self.identity:
                missing += 1
        self.assertEqual(0, missing)
        self.assertEqual(18457, len(self.npc))

    def test_every_world_spawn_is_identified(self):
        self.assertEqual(14800, len(self.world))
        self.assertEqual(14800, sum(1 for s in self.world if s["identity"] is not None))

    def test_jangan_smith_is_npc_ch_smith(self):
        smith = [s for s in self.world
                 if s["character_refid"] == 2003
                 and s["sector_x"] == 168 and s["sector_y"] == 97][0]
        self.assertEqual("NPC_CH_SMITH", smith["identity"]["code"])
        self.assertEqual(r"npc\npc\chinashop_smith.bsr", smith["identity"]["model_path"])
        self.assertEqual(332.73, smith["local_x"])

    def test_bandit_real_bsr_and_archer_xxx(self):
        bandits = [s for s in self.world
                   if s["character_refid"] == 1949
                   and s["sector_x"] == 156 and s["sector_y"] == 90]
        self.assertEqual(2, len(bandits))
        self.assertEqual("MOB_CH_BANDIT", bandits[0]["identity"]["code"])
        self.assertEqual(r"mob\china\bandit.bsr", bandits[0]["identity"]["model_path"])
        archer = [s for s in self.world
                  if s["character_refid"] == 1944
                  and s["sector_x"] == 156 and s["sector_y"] == 90][0]
        self.assertEqual("MOB_CH_BANDITARCHER_CLON", archer["identity"]["code"])
        self.assertEqual("xxx", archer["identity"]["model_path"])

    def test_unknown_refid_fails_closed(self):
        self.assertNotIn(0, self.identity)
        self.assertNotIn(999999, self.identity)
        self.assertIsNone(self.identity.get(999999))

    def test_spawnless_merchant_is_identified_but_not_a_world_spawn(self):
        self.assertEqual("NPC_AM_SPECIAL", self.identity[7568]["code"])
        self.assertEqual(0, sum(1 for s in self.world if s["character_refid"] == 7568))


if __name__ == "__main__":
    unittest.main(verbosity=2)
