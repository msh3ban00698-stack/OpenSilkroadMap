#!/usr/bin/env python3
"""Deterministic JMX .nvm navmesh parser (PARTIAL).

The Joymax `.nvm` (JMXVNVM) format is a navigation mesh. Proven structure:

    offset 0..11   magic + version  "JMXVNVM 1000"
    offset 12..    variable-length header (extent floats in [0,1920], grid dims,
                   and other fields whose semantics are NOT yet proven)
    ...            a flat array of 8-byte little-endian nav-cell records
                   (4 x u16) with a dominant count of 9216 = 96x96; fields are
                   (field0 == 0, flag, type-marker, value)
    ...            a trailing region of f32 values (~37 KB for a full cell)
    ...            trailing fill of -20.0 f32 words (commonly 36)

UNPROVEN (explicit): the header field meanings (vertex count vs triangle count
vs extent layout), the nav-cell record semantics (type-marker 279/271, flag,
value), and the f32 vertex/triangle layout. This parser LOCATES and reports the
proven regions without asserting semantics it cannot evidence.

Read-only. Emits JSON per file.
"""
from __future__ import annotations

import argparse
import json
import struct

NVM_MAGIC = b"JMXVNVM 1000"
FILL_WORD = struct.pack("<f", -20.0)


def find_largest_const_u0_run(blob, start=12, stop=None):
    """Return (count, offset) of the longest run of 8-byte records whose first
    u16 is constant and non-negative; the nav-cell grid in .nvm files."""
    n = len(blob)
    if stop is None:
        stop = n
    best = (0, None)
    for s0 in range(start, min(stop - 8, n - 8) + 1, 8):
        u0 = struct.unpack_from("<H", blob, s0)[0]
        if u0 != 0:
            continue
        o = s0
        c = 0
        while o + 8 <= n and struct.unpack_from("<H", blob, o)[0] == 0:
            c += 1
            o += 8
        if c > best[0]:
            best = (c, s0)
        if c >= 9000:
            break
    return best


def trailing_fill_words(blob):
    t = len(blob)
    while t - 4 >= 0 and blob[t - 4:t] == FILL_WORD:
        t -= 4
    return (len(blob) - t) // 4


def extent_floats(blob, start=12, stop=256):
    """Scan the header for the group of f32 values in the [0,1920] extent
    range. Returns the list of (offset, value) for plausible extent floats."""
    out = []
    stop = min(stop, len(blob) - 4)
    for off in range(start, stop, 4):
        f = struct.unpack_from("<f", blob, off)[0]
        if 0.0 < f <= 1920.0 and f == int(f):
            out.append((off, f))
    return out


def parse_nvm(blob, path="<memory>"):
    if len(blob) < 20:
        return {"path": path, "valid": False, "reason": "too short"}
    if blob[:12] != NVM_MAGIC:
        return {"path": path, "valid": False, "reason": "bad magic"}

    grid_count, grid_start = find_largest_const_u0_run(blob)
    grid_records = []
    if grid_start is not None:
        for i in range(min(grid_count, 8)):
            o = grid_start + i * 8
            grid_records.append(struct.unpack_from("<4H", blob, o))

    fill = trailing_fill_words(blob)
    ext = extent_floats(blob)

    return {
        "path": path,
        "valid": True,
        "total_size": len(blob),
        "magic": NVM_MAGIC.decode("latin-1"),
        "grid_start": grid_start,
        "grid_record_count": grid_count,
        "grid_is_96x96": grid_count == 9216,
        "grid_sample_records": [list(r) for r in grid_records],
        "grid_bytes": grid_count * 8 if grid_start is not None else 0,
        "header_bytes": grid_start if grid_start is not None else None,
        "trailing_fill_words": fill,
        "extent_float_offsets": ext,
        "unknown": [
            "header field semantics (counts/extents layout)",
            "nav-cell record semantics (flag / type-marker 279|271 / value)",
            "f32 vertex/triangle layout after the grid",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results = []
    for path in args.files:
        with open(path, "rb") as fh:
            blob = fh.read()
        results.append(parse_nvm(blob, path))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
            fh.write("\n")
    else:
        print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
