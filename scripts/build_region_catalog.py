#!/usr/bin/env python3
"""Build a derived Android region catalog from the real Data.pk2 RegionInfo.txt.

Read-only with respect to originals. Parses the ASCII tab-separated
RegionInfo.txt (TOWN/FIELD sections -> grid cells) and emits a small derived
TSV for the Android app under android/app/src/main/assets/game/regions.tsv.
The cell (x,y) coordinate space is the same space as the converted minimap
assets maps/minimap/{x}x{y}.png (verified: 3267 of 3387 unique cells have a
committed minimap; the remainder fall outside the minimap grid or have no
source image).

Usage:
  python3 scripts/build_region_catalog.py --regioninfo <path to RegionInfo.txt>
  # or set SRO_REGIONINFO (a session/CI-provided external path, never hardcoded).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game/regions.tsv"
MINIMAP_DIR = Path(__file__).resolve().parent.parent / "android-assets/maps/minimap"

CELL_RE = re.compile(r"^(\d+)\t(\d+)\t(ALL|RECT)(\t(.*))?$")


def parse(path: Path):
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("ascii", errors="replace")
    sections = []
    cur = None
    for line in text.splitlines():
        line = line.rstrip("\r\t ")
        if not line.strip():
            continue
        if line.startswith("#"):
            parts = line.split("\t")
            sec_type = parts[0][1:]
            name = parts[1].strip() if len(parts) > 1 else ""
            code = parts[2].strip() if len(parts) > 2 else ""
            cur = {"type": sec_type, "name": name, "code": code, "cells": []}
            sections.append(cur)
            continue
        m = CELL_RE.match(line)
        if not m or cur is None:
            continue
        x, y = int(m.group(1)), int(m.group(2))
        kind = m.group(3)
        extra = m.group(5).strip() if m.group(5) else ""
        cell = f"{x}:{y}"
        if kind == "RECT" and extra:
            cell += ":R:" + extra.replace("\t", ":")
        cur["cells"].append(cell)
    return sections, sha


def main():
    ap = argparse.ArgumentParser(description="Build derived Android region catalog")
    ap.add_argument("--regioninfo", default=os.environ.get("SRO_REGIONINFO"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if not args.regioninfo:
        sys.exit("Error: --regioninfo <RegionInfo.txt path> or env SRO_REGIONINFO is required")

    src = Path(args.regioninfo)
    if not src.is_file():
        sys.exit(f"Error: RegionInfo.txt not found at {src}")

    sections, sha = parse(src)
    total_cells = sum(len(s["cells"]) for s in sections)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# OpenSilkroadMap derived Android region catalog",
        "# source: Data.pk2 /RegionInfo.txt (sha256 " + sha + ")",
        "# format: <type>\\t<name>\\t<code>\\t<cell tokens: x:y or x:y:R:x0:y0:x1:y1>",
        f"# sections={len(sections)} cells={total_cells}",
    ]
    for s in sections:
        lines.append(f"{s['type']}\t{s['name']}\t{s['code']}\t" + ",".join(s["cells"]))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cells = set()
    for s in sections:
        for c in s["cells"]:
            cells.add(tuple(int(v) for v in c.split(":")[:2]))

    have = set()
    for f in MINIMAP_DIR.glob("*.png"):
        m = re.match(r"^(\d+)x(\d+)\.png$", f.name)
        if m:
            have.add((int(m.group(1)), int(m.group(2))))

    covered = cells & have
    print(f"source sha256   : {sha}")
    print(f"sections        : {len(sections)} (FIELD {sum(1 for s in sections if s['type']=='FIELD')}, TOWN {sum(1 for s in sections if s['type']=='TOWN')})")
    print(f"unique cells    : {len(cells)}")
    print(f"with committed minimap: {len(covered)} ({100.0*len(covered)/len(cells):.1f}%)")
    print(f"without minimap : {sorted(cells - have)[:10]}{'...' if len(cells-have)>10 else ''}")
    print(f"wrote           : {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
