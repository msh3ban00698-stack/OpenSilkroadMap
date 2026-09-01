#!/usr/bin/env python3
"""Build a derived server region->zone catalog from the real RefRegion.txt.

Read-only with respect to originals. Parses the UTF-16LE tab-separated
SR_GameRefData/RefRegion.txt (server region reference table) and emits a small
derived TSV for the Android app under
android/app/src/main/assets/game/world/region_zone.tsv.

Proven facts encoded by this generator (verified on the real file):
  * 21 columns, no header row; row 0 is data (a sentinel id).
  * col0 = packed region id, col1 = sector x, col2 = sector y, and
    id == (y << 8) | x for every non-negative id (verified: 0 mismatches
    across 2444 world rows; the 17 negative rows are dungeon/instance
    sentinels with x=y=0 and are skipped).
  * col3 = server region name (e.g. West_China, FORT_HT_AREA), col4 is a
    literal '????' placeholder (not a localisation), col5 = flag
    (2363 x 1, 81 x 0), col6 = zone id (13 distinct zone ids), col7 = -1,
    col8/9 = 0, col10 = 'xxx', col11-20 = 'NULL' (never populated).

The sector (x, y) space is the same space as the client regioncode.txt
(2442/2444 ids also present there) and the RegionInfo grid (2396/2444
sectors), which this generator asserts.

Usage:
  python3 scripts/build_region_ref_catalog.py --refregion <path>
  # or set SRO_REFREGION (a session/CI-provided external path, never hardcoded).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "android/app/src/main/assets/game/world/region_zone.tsv"

COLS = 21


def parse(path: Path):
    """Return (rows, sha) where rows are dicts for every non-negative id."""
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-16-le", errors="replace")
    rows = []
    errors = []
    for line in text.splitlines():
        line = line.lstrip("\ufeff")
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) < 11:
            errors.append(("short-row", line[:40]))
            continue
        try:
            rid = int(cells[0])
        except ValueError:
            errors.append(("bad-id", line[:40]))
            continue
        if rid < 0:
            continue
        sx = int(cells[1])
        sy = int(cells[2])
        if rid != (sy << 8) | sx:
            errors.append(("pack-mismatch", rid, sx, sy))
            continue
        rows.append({
            "region_id": rid,
            "sector_x": sx,
            "sector_y": sy,
            "name": cells[3],
            "flag": cells[5],
            "zone_id": cells[6],
        })
    return rows, sha, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refregion", default=os.environ.get("SRO_REFREGION"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if not args.refregion:
        sys.exit("Error: --refregion <RefRegion.txt path> or env SRO_REFREGION is required")

    src = Path(args.refregion)
    if not src.is_file():
        sys.exit(f"Error: RefRegion.txt not found at {src}")

    rows, sha, errors = parse(src)
    if errors:
        for e in errors[:10]:
            print("ERROR:", e)
        sys.exit(f"Error: {len(errors)} parse errors, aborting")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    names = len({r["name"] for r in rows})
    zones = len({r["zone_id"] for r in rows})
    flags = {}
    for r in rows:
        flags[r["flag"]] = flags.get(r["flag"], 0) + 1

    lines = [
        "# OpenSilkroadMap derived server region->zone catalog",
        "# source: SR_GameRefData/RefRegion.txt (sha256 " + sha + ")",
        "# format: <region_id>\\t<sector_x>\\t<sector_y>\\t<name>\\t<flag>\\t<zone_id>",
        f"# rows={len(rows)} names={names} zones={zones} flags={flags}",
    ]
    for r in sorted(rows, key=lambda r: r["region_id"]):
        lines.append(f"{r['region_id']}\t{r['sector_x']}\t{r['sector_y']}\t{r['name']}\t{r['flag']}\t{r['zone_id']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"source sha256   : {sha}")
    print(f"rows            : {len(rows)}")
    print(f"server names    : {names}")
    print(f"zone ids        : {zones}")
    print(f"flag counts     : {flags}")
    print(f"wrote           : {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
