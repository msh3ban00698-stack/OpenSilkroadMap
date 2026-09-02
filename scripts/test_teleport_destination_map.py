#!/usr/bin/env python3
"""Teleport destination map parity test.

Proves, from the committed assets only, the concrete runtime teleport
destination map that the Android {@code TeleportDestinationMap} composes from
{@code TeleportGateIndex} + {@code OptionalTeleportIndex}:

  * teleportdata.tsv      246 gate rows (col2 GATE_*, col3 gate_id, col4
                           SN_ZONE_*, col5 zone_id, col6/7/8 local x/y/z);
  * teleportbuilding.tsv  gate_id -> STORE_* / SN_NPC_* codes (col1/2/5);
  * refoptionalteleport.tsv  44 destination rows (col1 index, col2 label,
                           col3 SN_ZONE_*, col4 region_id, col5/6/7 local
                           x/y/z);
  * regioncode.tsv + region_zone.tsv resolve every world region_id to
    sector + server zone + client name (proven packing sx = id & 0xFF,
    sy = id >> 8).

The map is strictly fail-closed: instance rows (negative region codes) and
world rows absent from both region tables resolve to NO placement, and the
runtime never invents a gate -> destination link (teleportlink.tsv semantics
are unproven and are NOT consumed here).

Nothing is invented: every assertion is a direct consequence of already-proven
facts or of the committed data itself.
"""
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import region_resolver as rr  # noqa: E402
from worldmap_localinfo import load_unique_labels, resolve  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game"
TEXTDATA = ASSETS / "textdata"
WORLD = ASSETS / "world"

GATE_DATA = TEXTDATA / "teleportdata.tsv"
BUILDING = TEXTDATA / "teleportbuilding.tsv"
OPTIONAL = TEXTDATA / "refoptionalteleport.tsv"


def _rows(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        out.append(line.split("\t"))
    return out


def _gate_rows():
    return _rows(GATE_DATA)


def _building_by_gate():
    out = {}
    for r in _rows(BUILDING):
        out[int(r[1])] = r
    return out


def _optional_rows():
    return _rows(OPTIONAL)


def _resolver():
    return rr.RegionResolver.load_default(ASSETS)


def _is_instance(code):
    return (code & 0x8000) != 0


def _gates():
    resolver = _resolver()
    buildings = _building_by_gate()
    gates = []
    for i, r in enumerate(_gate_rows()):
        gate_id = int(r[3])
        zone_id = int(r[5])
        region = resolver.resolve(zone_id)
        row = buildings.get(gate_id)
        gates.append({
            "row": i,
            "gate_code": r[2],
            "gate_id": gate_id,
            "zone_code": r[4],
            "zone_id": zone_id,
            "local_x": float(r[6]),
            "height_y": float(r[7]),
            "local_z": float(r[8]),
            "region": region,
            "store_code": row[2] if row else None,
            "npc_code": row[5] if row else None,
        })
    return gates


def _destinations():
    resolver = _resolver()
    out = []
    for i, r in enumerate(_optional_rows()):
        out.append({
            "row": i,
            "index": int(r[1]),
            "name_label": r[2],
            "zone_code": r[3],
            "region_id": int(r[4]),
            "local_x": float(r[5]),
            "height_y": float(r[6]),
            "local_z": float(r[7]),
            "region": resolver.resolve(int(r[4])),
        })
    return out


def _world_coords(local, sector, ref):
    return local + (sector - ref) * 1920.0


class TeleportGateParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates = _gates()

    def test_row_count(self):
        self.assertEqual(len(self.gates), 246)

    def test_world_vs_instance(self):
        world = [g for g in self.gates if g["zone_id"] >= 0]
        inst = [g for g in self.gates if g["zone_id"] < 0]
        self.assertEqual(len(world), 144)
        self.assertEqual(len(inst), 102)

    def test_attribution_counts(self):
        world = [g for g in self.gates if g["zone_id"] >= 0]
        server = [g for g in world if g["region"] is not None and g["region"].zone_id is not None]
        client = [g for g in world if g["region"] is not None and g["region"].zone_id is None]
        unknown = [g for g in world if g["region"] is None]
        self.assertEqual(len(server), 104)
        self.assertEqual(len(client), 35)
        self.assertEqual(len(unknown), 5)

    def test_zones(self):
        zones = {g["region"].zone_id for g in self.gates
                 if g["region"] is not None and g["region"].zone_id is not None}
        self.assertEqual(zones, {"1001", "1005", "2001", "2002", "2004", "3001",
                                 "3002", "3003", "3004", "3005", "4001", "4002"})

    def test_gate_ch_jangan(self):
        g = self.gates[0]
        self.assertEqual(g["gate_code"], "GATE_CH")
        self.assertEqual(g["gate_id"], 2094)
        self.assertEqual(g["zone_code"], "SN_ZONE_22001")
        self.assertEqual(g["zone_id"], 25000)
        self.assertEqual(g["local_x"], 969.0)
        self.assertEqual(g["local_z"], 1369.0)
        self.assertEqual(g["region"].sector_x, 168)
        self.assertEqual(g["region"].sector_y, 97)
        self.assertEqual(g["region"].zone_id, "1001")
        self.assertEqual(g["region"].name_code, "RN_CH_JANGAN")
        self.assertEqual(g["store_code"], "STORE_CH_GATE")
        self.assertEqual(g["npc_code"], "SN_NPC_CH_GATE")
        self.assertEqual(_world_coords(g["local_x"], 168, 168), 969.0)
        self.assertEqual(_world_coords(g["local_z"], 97, 97), 1369.0)

    def test_building_join(self):
        joined = {g["gate_id"] for g in self.gates if g["store_code"] is not None}
        self.assertEqual(len(joined), 101)


class OptionalDestinationParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dests = _destinations()

    def test_row_count(self):
        self.assertEqual(len(self.dests), 44)

    def test_world_vs_instance(self):
        world = [d for d in self.dests if d["region_id"] >= 0]
        inst = [d for d in self.dests if d["region_id"] < 0]
        self.assertEqual(len(world), 40)
        self.assertEqual(len(inst), 4)

    def test_attribution_counts(self):
        world = [d for d in self.dests if d["region_id"] >= 0]
        server = [d for d in world if d["region"].zone_id is not None]
        client = [d for d in world if d["region"].zone_id is None]
        self.assertEqual(len(server), 35)
        self.assertEqual(len(client), 5)

    def test_changan_destination(self):
        d = self.dests[25]
        self.assertEqual(d["index"], 26)
        self.assertEqual(d["name_label"], "Chang'an")
        self.assertEqual(d["zone_code"], "SN_ZONE_22001")
        self.assertEqual(d["region_id"], 25000)
        self.assertEqual(d["local_x"], 995.0)
        self.assertEqual(d["local_z"], 1132.0)
        self.assertEqual(d["region"].sector_x, 168)
        self.assertEqual(d["region"].sector_y, 97)
        self.assertEqual(d["region"].zone_id, "1001")


class TeleportDestinationMapParityTests(unittest.TestCase):
    """The combined runtime map over gates + optional destinations."""

    @classmethod
    def setUpClass(cls):
        cls.gates = _gates()
        cls.dests = _destinations()
        cls.map = cls.gates + cls.dests

    def test_entry_counts(self):
        self.assertEqual(len(self.map), 246 + 44)
        self.assertEqual(len(self.gates), 246)
        self.assertEqual(len(self.dests), 44)

    def test_resolved_vs_unresolved(self):
        resolved = [e for e in self.map if e["region"] is not None]
        unresolved = [e for e in self.map if e["region"] is None]
        self.assertEqual(len(resolved), 139 + 40)
        self.assertEqual(len(unresolved), 246 + 44 - 139 - 40)

    def test_instance_entries_fail_closed(self):
        for e in self.map:
            code = e.get("zone_id", e.get("region_id"))
            if code < 0:
                self.assertIsNone(e["region"])

    def test_jangan_sector_window(self):
        in_sector = [e for e in self.map
                     if e["region"] is not None
                     and e["region"].sector_x == 168 and e["region"].sector_y == 97]
        codes = {e["gate_code"] if "gate_code" in e else e["name_label"]
                 for e in in_sector}
        self.assertIn("GATE_CH", codes)
        self.assertIn("Chang'an", codes)
        self.assertEqual(len(in_sector), 4)

    def test_jangan_field_window(self):
        win = [e for e in self.map
               if e["region"] is not None
               and 156 <= e["region"].sector_x <= 182
               and 89 <= e["region"].sector_y <= 102]
        self.assertEqual(len(win), 20)
        gates = [e for e in win if "gate_code" in e]
        dests = [e for e in win if "gate_code" not in e]
        self.assertEqual(len(gates), 16)
        self.assertEqual(len(dests), 4)
        labels = {e["gate_code"] if "gate_code" in e else e["name_label"]
                  for e in win}
        self.assertIn("GATE_CH", labels)
        self.assertIn("Chang'an", labels)


class UniqueOnceLocalinfoAttachTests(unittest.TestCase):
    """Optional unique-once SN_ZONE labels; existing map labels stay unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.gates = _gates()
        cls.dests = _destinations()
        cls.labels = load_unique_labels(TEXTDATA / "worldmap_localinfo.tsv")

    def test_two_arg_map_has_no_localinfo(self):
        self.assertEqual(self.gates[0]["gate_code"], "GATE_CH")
        self.assertNotIn("localinfo", self.gates[0])
        self.assertEqual(self.dests[25]["name_label"], "Chang'an")

    def test_unique_once_attach_does_not_replace_labels(self):
        labeled_gates = 0
        for g in self.gates:
            lab = resolve(self.labels, g["zone_code"])
            if lab is not None:
                labeled_gates += 1
                g["localinfo"] = lab
        labeled_dests = 0
        for d in self.dests:
            lab = resolve(self.labels, d["zone_code"])
            if lab is not None:
                labeled_dests += 1
                d["localinfo"] = lab
        self.assertEqual(29, labeled_gates)
        self.assertEqual(32, labeled_dests)
        self.assertEqual(61, labeled_gates + labeled_dests)
        self.assertEqual(self.gates[0]["gate_code"], "GATE_CH")
        self.assertEqual(self.gates[0]["localinfo"]["name"], "중국")
        self.assertEqual(self.gates[0]["localinfo"]["description"], "장 안")
        self.assertEqual(self.dests[25]["name_label"], "Chang'an")
        self.assertEqual(self.dests[25]["localinfo"]["name"], "중국")
        self.assertIsNone(resolve(self.labels, self.gates[8]["zone_code"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
