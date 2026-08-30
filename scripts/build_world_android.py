#!/usr/bin/env python3
"""Build the committed normalized Android world dataset (read-only pipeline).

Phase 10 rule: derive every committed artifact from REAL VSRO-R 1.193 data with
a pinned reader; never modify originals; never invent geometry.

Inputs (paths via flags / env):
  --pk2-dir    : directory containing Map.pk2 and Data.pk2 (SRO_PK2_DIR)
  --reader     : path to the pinned pk2_mate reader (SRO_READER_DIR)
  --regioninfo : path to RegionInfo.txt (SRO_REGIONINFO)

Outputs (committed into android/app/src/main/assets/game/world/):
  world_regions.tsv        : per-RegionInfo.txt-section sector windows
  world_index.tsv          : inventory of emitted .hg sectors
  {x}x{y}.hg               : normalized height grids (VSHG v1), real data

All windows and heights come straight from RegionInfo.txt / Map.pk2 {Y}/{X}.m.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import world_terrain as wt  # noqa: E402

OUT = REPO / "android" / "app" / "src" / "main" / "assets" / "game" / "world"

CELL_RE = re.compile(r"^\s*(-?\d+)\s+(-?\d+)\s+(ALL|RECT)\s*(.*)$")
DIR_RE = re.compile(r"^ (/\d+)$")


def list_sector_ms(pk2_dir: Path, reader: Path, cached_list=None):
    """Return the set of existing (sx, sy) terrain sectors from a Map.pk2 listing.

    Uses --map-list cache when provided (a saved `pk2_mate list` output),
    otherwise runs the read-only listing once.
    """
    if cached_list is not None:
        text = Path(cached_list).read_text(encoding="utf-8")
    else:
        res = subprocess.run(
            [str(reader), "list", "-a", str(pk2_dir / "Map.pk2")],
            check=True, capture_output=True, timeout=300,
        )
        text = res.stdout.decode("utf-8", errors="replace")
    sectors = set()
    cur = None
    for ln in text.splitlines():
        m = DIR_RE.match(ln)
        if m:
            cur = int(m.group(1)[1:])
            continue
        if cur is not None and ln.strip().endswith(".m"):
            sectors.add((int(ln.strip()[:-2]), cur))
    return sectors


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_regioninfo(path: Path):
    """Return list of {type, name, code, cells:[(x,y)]} from RegionInfo.txt."""
    text = path.read_bytes().decode("ascii", errors="replace")
    sections = []
    cur = None
    for line in text.splitlines():
        line = line.rstrip("\r\t ")
        if not line.strip():
            continue
        if line.startswith("#"):
            parts = line.split("\t")
            cur = {
                "type": parts[0][1:],
                "name": parts[1].strip() if len(parts) > 1 else "",
                "code": parts[2].strip() if len(parts) > 2 else "",
                "cells": [],
            }
            sections.append(cur)
            continue
        m = CELL_RE.match(line)
        if not m or cur is None:
            continue
        cur["cells"].append((int(m.group(1)), int(m.group(2))))
    return sections


def extract_m(pk2_dir: Path, reader: Path, sx: int, sy: int, tmp: Path):
    """Read-only extract Map.pk2 /{sy}/{sx}.m into tmp and return the blob."""
    subprocess.run(
        [str(reader), "extract", "-a", str(pk2_dir / "Map.pk2"),
         "-o", str(tmp), "-p", f"/{sy}/{sx}.m"],
        check=True, capture_output=True, timeout=120,
    )
    f = tmp / f"{sx}.m"
    if not f.exists():
        # reader drops the parent dir; locate by basename
        cands = [p for p in tmp.rglob("*.m") if p.name == f"{sx}.m"]
        if not cands:
            raise FileNotFoundError(f"sector {sx},{sy} .m not extracted")
        f = cands[0]
    return f.read_bytes()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    ap.add_argument("--reader", default=os.environ.get("SRO_READER_DIR"))
    ap.add_argument("--regioninfo", default=os.environ.get("SRO_REGIONINFO"))
    ap.add_argument("--map-list", default=os.environ.get("SRO_MAP_LIST"))
    args = ap.parse_args()

    if not args.pk2_dir or not args.reader or not args.regioninfo:
        sys.exit("Error: --pk2-dir, --reader, --regioninfo are required")

    pk2_dir, reader, rinfo = Path(args.pk2_dir), Path(args.reader), Path(args.regioninfo)
    for p in (pk2_dir / "Map.pk2", reader, rinfo):
        if not p.exists():
            sys.exit(f"Error: not found: {p}")

    sections = parse_regioninfo(rinfo)
    rinfo_sha = sha256_text(rinfo)

    world_rows = []
    world_sections = []  # (type, name, code, sx0, sx1, sy0, sy1, ref_sx, ref_sy, cells)
    emitted = []  # (sx, sy, source_m_sha)
    seen = set()
    OUT.mkdir(parents=True, exist_ok=True)

    def emit(sx, sy, blob):
        key = (sx, sy)
        if key in seen:
            return
        seen.add(key)
        grid = wt.parse_terrain_m(blob)
        hg = OUT / f"{sx}x{sy}.hg"
        wt.write_hg(hg, grid)
        emitted.append(key)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for s in sections:
            cells = s["cells"]
            if not cells:
                continue
            sx = [c[0] for c in cells]
            sy = [c[1] for c in cells]
            ref_x, ref_y = min(sx), min(sy)
            row = (s['type'], s['name'], s['code'],
                   min(sx), max(sx), min(sy), max(sy), ref_x, ref_y, len(cells))
            world_sections.append(row)
            world_rows.append("\t".join(str(v) for v in row))
        # Emit one sector per curated named world region (real data; the ref
        # sector is the first cell of the RegionInfo window that actually has a
        # terrain .m in Map.pk2, so only real existing geometry is emitted)
        CURATED = [
            "Constantinople", "Roc_Mountain", "Jangan_Field", "Donwhang_Field",
            "Hotan_Field", "Central_Asia", "Samarkand", "Alexandria_Delta",
            "Baghdad", "Arabia_Desert", "Taklamakan", "Karakoram",
            "Storm_Desert", "Kings_Valley", "Eastern_Europe", "Pharaoh_Novice",
        ]
        by_name = {}
        for s in sections:
            if s["name"] not in by_name:
                by_name[s["name"]] = s
        existing = list_sector_ms(pk2_dir, reader, args.map_list)
        for name in CURATED:
            s = by_name.get(name)
            if s is None or not s["cells"]:
                print(f"  [warn] curated section not found: {name}")
                continue
            pick = None
            for c in sorted(s["cells"]):
                if c[1] >= 128:
                    continue
                if c in existing:
                    pick = c
                    break
            if pick is None:
                print(f"  [warn] no terrain .m in window of {name}")
                continue
            sx0, sy0 = pick
            blob = extract_m(pk2_dir, reader, sx0, sy0, tmp)
            emit(sx0, sy0, blob)
        # Emit a small walkable cluster in the Constantinople (China) window
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            sx, sy = 76 + dx, 103 + dy
            blob = extract_m(pk2_dir, reader, sx, sy, tmp)
            emit(sx, sy, blob)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "world_regions.tsv").write_text(
        "# OpenSilkroadMap derived world region windows\n"
        f"# source: Data.pk2 /RegionInfo.txt (sha256 {rinfo_sha})\n"
        "# format: <type>\t<name>\t<code>\tsx0\tsx1\tsy0\tsy1\tref_sx\tref_sy\tcells\n"
        + "\n".join(world_rows) + "\n",
        encoding="utf-8",
    )
    # Index every .hg on disk so the inventory always matches the files.
    index_rows = []
    for hg in sorted(OUT.glob("*.hg")):
        name = hg.stem  # {sx}x{sy}
        sx, sy = name.split("x")
        grid, step = wt.read_hg(hg)
        flat = [h for row in grid for h in row]
        index_rows.append(
            f"{sx}\t{sy}\t{len(grid)}\t{min(flat):.2f}\t{max(flat):.2f}\t"
            f"{hashlib.sha256(hg.read_bytes()).hexdigest()}"
        )
    (OUT / "world_index.tsv").write_text(
        "# OpenSilkroadMap normalized height-grid inventory (VSHG v1)\n"
        "# source: Map.pk2 /{sy}/{sx}.m (extracted read-only via pk2_mate)\n"
        "# format: <sx>\t<sy>\t<size>\t<min_h>\t<max_h>\t<hg_sha256>\n"
        + "\n".join(index_rows) + "\n",
        encoding="utf-8",
    )
    # Region master CSV at repo root (docs artifact, same derived data).
    (REPO / "WORLD_REGION_MASTER.csv").write_text(
        "type,name,code,sx0,sx1,sy0,sy1,ref_sx,ref_sy,cells\n"
        + "\n".join(",".join(str(v) for v in row) for row in world_sections) + "\n",
        encoding="utf-8",
    )
    print(f"regions: {len(world_rows)} sections")
    print(f"emitted {len(emitted)} sector grids -> {OUT}")
    for sx, sy in emitted:
        print(f"  {sx}x{sy}.hg")
    print(f"indexed {len(index_rows)} .hg files on disk")


if __name__ == "__main__":
    main()
