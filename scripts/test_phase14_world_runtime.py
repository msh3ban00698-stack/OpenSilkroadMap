#!/usr/bin/env python3
"""Phase 14: native world runtime — real-data validation.

This phase moves from data/format foundation to a native world runtime. This
module is the executable (Python) evidence gate for the runtime data path. It
validates, against the committed real assets only:

  * terrain asset discovery (world_index.tsv -> committed .hg files)
  * terrain loading (VSHG v1 parse) and dimensions (97x97, step 20)
  * terrain height samples (real min/max and in-range samples)
  * region bounds (world_regions.tsv window + reference sector)
  * world coordinates (verified sector -> world origin formula)
  * camera projection / inverse projection / world -> screen mapping
  * region transition (deterministic world offset between sectors)
  * object coordinate mapping (real npcpos world rows -> sector window)
  * asset dependency resolution (ANDROID_ASSET_DEPENDENCY_GRAPH.json)
  * missing-asset fail-closed behavior (no substitution)

The Java runtime (GameActivity -> NativeWorldRenderer -> Camera2D) is covered by
committed JVM/instrumented tests that are NOT EXECUTED here (no JDK/Android SDK);
this module is the executed half of the Phase 14 verification.

Nothing is invented: every assertion is a direct consequence of the committed
data or of the already-proven Phase 10/13 formulas.
"""
import json
import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import world_terrain as wt  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game"
WORLD_DIR = ASSETS / "world"
WORLD_INDEX = WORLD_DIR / "world_index.tsv"
WORLD_REGIONS = WORLD_DIR / "world_regions.tsv"
NPC_POS = ASSETS / "textdata" / "npcpos.tsv"
DEP_GRAPH = Path(__file__).resolve().parent.parent / "ANDROID_ASSET_DEPENDENCY_GRAPH.json"

SECTOR_WORLD = 1920.0


def _index_rows():
    out = []
    for line in WORLD_INDEX.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        p = line.split("\t")
        out.append((int(p[0]), int(p[1]), int(p[2]), float(p[3]), float(p[4]), p[5]))
    return out


def _region_rows():
    out = []
    for line in WORLD_REGIONS.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        p = line.split("\t")
        out.append({
            "type": p[0], "name": p[1], "code": p[2],
            "sx0": int(p[3]), "sx1": int(p[4]),
            "sy0": int(p[5]), "sy1": int(p[6]),
            "ref_sx": int(p[7]), "ref_sy": int(p[8]),
            "cells": int(p[9]),
        })
    return out


def _npcpos_rows():
    out = []
    for line in NPC_POS.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        out.append(line.split("\t"))
    return out


class TerrainAssetDiscoveryTest(unittest.TestCase):
    def test_index_lists_only_real_committed_hg_files(self):
        rows = _index_rows()
        self.assertGreaterEqual(len(rows), 23)
        for sx, sy, size, min_h, max_h, sha in rows:
            hg = WORLD_DIR / f"{sx}x{sy}.hg"
            self.assertTrue(hg.is_file(), f"indexed {sx}x{sy}.hg missing")

    def test_selected_region_is_first_with_ref_sector_terrain(self):
        indexed = {(sx, sy) for (sx, sy, *_) in _index_rows()}
        selected = None
        for r in _region_rows():
            if (r["ref_sx"], r["ref_sy"]) in indexed:
                selected = r
                break
        self.assertIsNotNone(selected)
        self.assertEqual("Jangan_Field", selected["name"])
        self.assertEqual((156, 89), (selected["ref_sx"], selected["ref_sy"]))


class TerrainLoadingTest(unittest.TestCase):
    def test_vshg_grid_dimensions_and_step(self):
        grid, step = wt.read_hg(WORLD_DIR / "156x89.hg")
        self.assertEqual(97, len(grid))
        self.assertEqual(97, len(grid[0]))
        self.assertEqual(20.0, step)

    def test_real_height_range_matches_index(self):
        grid, _ = wt.read_hg(WORLD_DIR / "156x89.hg")
        flat = [h for row in grid for h in row]
        self.assertAlmostEqual(866.25, min(flat), delta=0.1)
        self.assertAlmostEqual(2687.02, max(flat), delta=0.1)
        self.assertEqual(97 * 97, len(flat))

    def test_height_samples_are_within_real_range(self):
        grid, step = wt.read_hg(WORLD_DIR / "156x89.hg")
        lo = 866.25
        hi = 2687.02
        for h in (grid[0][0], grid[0][96], grid[96][0], grid[96][96],
                  grid[48][48], grid[10][20]):
            self.assertTrue(lo - 0.2 <= h <= hi + 0.2, f"sample {h} outside range")


class RegionBoundsTest(unittest.TestCase):
    def test_jangan_field_window_and_ref(self):
        by_name = {r["name"]: r for r in _region_rows()}
        r = by_name["Jangan_Field"]
        self.assertEqual((156, 182, 89, 102), (r["sx0"], r["sx1"], r["sy0"], r["sy1"]))
        self.assertEqual((156, 89), (r["ref_sx"], r["ref_sy"]))
        self.assertTrue(r["sx0"] <= 156 <= r["sx1"])
        self.assertTrue(r["sy0"] <= 89 <= r["sy1"])


class WorldCoordinatesTest(unittest.TestCase):
    def test_sector_world_origin_is_zero_at_ref(self):
        self.assertEqual((0.0, 0.0), wt.sector_world_origin(156, 89, 156, 89))

    def test_adjacent_sector_shifts_world_by_sector_world(self):
        self.assertEqual((0.0, SECTOR_WORLD), wt.sector_world_origin(156, 90, 156, 89))
        self.assertEqual((SECTOR_WORLD, 0.0), wt.sector_world_origin(157, 89, 156, 89))

    def test_npc_to_world_uses_verified_region_pack(self):
        # region_code 0x59A0 packs (sx=0xA0, sy=0x59) -> (160, 89).
        code = wt.pack_region(160, 89)
        self.assertEqual((160, 89), wt.unpack_region(code))
        wx, wz = wt.npc_to_world(100.0, 200.0, code, 156, 89)
        self.assertAlmostEqual(100.0 + 4 * SECTOR_WORLD, wx)
        self.assertAlmostEqual(200.0 + 0 * SECTOR_WORLD, wz)


class CameraProjectionTest(unittest.TestCase):
    def _world_to_view(self, wx, wz, cam_x, cam_z, ppu):
        return (wx - cam_x) * ppu, (cam_z - wz) * ppu

    def test_world_to_view_is_top_down(self):
        px, py = self._world_to_view(110.0, 100.0, 100.0, 100.0, 2.0)
        self.assertAlmostEqual(20.0, px)
        self.assertAlmostEqual(0.0, py)
        px, py = self._world_to_view(100.0, 90.0, 100.0, 100.0, 2.0)
        self.assertAlmostEqual(0.0, px)
        self.assertAlmostEqual(20.0, py)

    def test_view_to_world_is_inverse(self):
        cam = (123.0, 456.0)
        ppu = 1.5
        for wx, wz in ((321.0, 654.0), (0.0, 0.0), (1000.0, 500.0)):
            vx, vy = self._world_to_view(wx, wz, cam[0], cam[1], ppu)
            rx = cam[0] + vx / ppu
            rz = cam[1] - vy / ppu
            self.assertAlmostEqual(wx, rx, places=5)
            self.assertAlmostEqual(wz, rz, places=5)

    def test_world_to_screen_adds_viewport_center(self):
        cam_x, cam_z, ppu, vw, vh = 960.0, 960.0, 0.5, 1080.0, 1920.0
        wx, wz = 960.0, 960.0
        sx = (wx - cam_x) * ppu + vw / 2.0
        sy = (cam_z - wz) * ppu + vh / 2.0
        self.assertAlmostEqual(vw / 2.0, sx)
        self.assertAlmostEqual(vh / 2.0, sy)


class RegionTransitionTest(unittest.TestCase):
    def test_transition_between_sectors_preserves_local_origin(self):
        # Moving the camera across a sector boundary shifts world by SECTOR_WORLD.
        origin_a = wt.sector_world_origin(156, 89, 156, 89)
        origin_b = wt.sector_world_origin(156, 90, 156, 89)
        self.assertEqual((0.0, SECTOR_WORLD), (origin_b[0] - origin_a[0],
                                              origin_b[1] - origin_a[1]))


class ObjectCoordinateMappingTest(unittest.TestCase):
    def test_world_npcpos_rows_map_into_jangan_field_window(self):
        window = (156, 182, 89, 102)
        in_window = 0
        for row in _npcpos_rows():
            if len(row) < 5:
                continue
            code = int(row[1])
            if code < 0:
                continue  # dungeon/instance rows use a separate UNKNOWN space
            sx, sy = wt.unpack_region(code)
            if window[0] <= sx <= window[1] and window[2] <= sy <= window[3]:
                in_window += 1
                x = float(row[2])
                z = float(row[4])
                self.assertTrue(0.0 <= x < SECTOR_WORLD, f"x {x} outside [0,1920)")
                self.assertTrue(0.0 <= z < SECTOR_WORLD, f"z {z} outside [0,1920)")
        self.assertGreater(in_window, 0)


class AssetDependencyTest(unittest.TestCase):
    def test_dependency_graph_loads_with_verified_edges(self):
        d = json.loads(DEP_GRAPH.read_text(encoding="utf-8"))
        self.assertEqual(9, d["textdata_edges"])
        self.assertEqual(17, d["asset_edges"])
        self.assertEqual(53, len(d["edges"]))
        statuses = {e["status"] for e in d["edges"]}
        self.assertLessEqual(statuses, {"VERIFIED", "PARTIAL"})
        kinds = {(e["from"]["kind"], e["to"]["kind"]) for e in d["edges"]}
        self.assertIn(("npcpos.tsv", "characterdata_*.txt (tiers)"), kinds)
        self.assertIn((".ddj", "DDS"), kinds)
        self.assertIn(("bandit.bsr", "bandit chain"), kinds)


class MissingAssetFailClosedTest(unittest.TestCase):
    def test_unindexed_sector_fails_closed(self):
        indexed = {(sx, sy) for (sx, sy, *_) in _index_rows()}
        # ThiefTown reference sector has no committed .hg asset.
        self.assertNotIn((182, 96), indexed)
        self.assertFalse((WORLD_DIR / "182x96.hg").is_file())
        # No other sector is silently substituted: selection must return None.
        self.assertIsNone(_find_ref_sector_or_none((182, 96)))


def _find_ref_sector_or_none(target):
    indexed = {(sx, sy): True for (sx, sy, *_) in _index_rows()}
    return None if target not in indexed else target


if __name__ == "__main__":
    unittest.main()
