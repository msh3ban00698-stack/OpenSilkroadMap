#!/usr/bin/env python3
"""Deterministic probe/classifier for the heterogeneous `.dat` family.

The `.dat` extension is NOT one format. This module classifies a `.dat` blob by
its leading bytes into the real families observed across the vSRO 1.193 corpus:

    bmp        Windows BMP image ("BM")      -- launcher/launcher_europe UI
    jmxvimg    "JMXVIMG11000" image          -- /fonts glyph bitmaps (new family)
    ainavdata  AI navigation data (0x01..)   -- /navmesh/ainavdata_*.dat
    palette    256-entry RGB palette (768 B) -- /silk.dat
    hex-token  ASCII hex token               -- Silkload.dat
    config     u32 count-prefixed settings   -- client Setting/*.dat
    unknown    no reliable signature

Read-only. Pure functions are importable; the CLI emits JSON.
"""
from __future__ import annotations

import argparse
import json
import struct

JMXVIMG_MAGIC = b"JMXVIMG11000"
DDJ_MAGIC = b"JMXVDDJ 1000"


def _hex_only(blob):
    if not blob:
        return False
    return all(chr(b) in "0123456789abcdefABCDEF" for b in blob)


def parse_ainavdata(blob, path="<memory>"):
    """Parse the AI navigation header (PARTIAL).

    PROVEN (across all 26 files):
      - byte 0        = version 0x01
      - u32 LE @1..4  = vertex_section_offset: absolute file offset of the
                        trailing vertex/sub-section, which repeats region_id +
                        type as its first bytes
      - u16 LE @5..6  = nav_id = 0x8000 | numeric_id (matches filename id)
      - byte 7        = type (0x01 region, 0x97 dungeon, others)
      - u32 @8..11    = 0
      - u16 BE @14..15 = count_a
      - u16 BE @18..19 = count_b (== vertex count in the trailing sub-section)
    UNKNOWN:
      - u16 BE @16..17 (0x0000 simple, 0x0100/0x0800 complex)
      - byte 20 (LE u32 @20, small int 0/1/2)
      - count_a (u16 BE @14) semantics
      - body edge-record layout (u16 BE, offset 24 .. vertex_section_offset)
    """
    if len(blob) < 24 or blob[0] != 0x01:
        return None
    nav_id = struct.unpack_from("<H", blob, 5)[0]
    if (nav_id & 0xFF00) != 0x8000:
        return None
    return {
        "path": path,
        "family": "ainavdata",
        "version_byte": blob[0],
        "vertex_section_offset": struct.unpack_from("<I", blob, 1)[0],
        "nav_id": nav_id,
        "nav_id_matches_filename": None,  # set by caller when filename known
        "type_byte": blob[7],
        "reserved_u32_8": struct.unpack_from("<I", blob, 8)[0],
        "count_a": struct.unpack_from(">H", blob, 14)[0],
        "u16_at_16": struct.unpack_from(">H", blob, 16)[0],
        "count_b": struct.unpack_from(">H", blob, 18)[0],
        "reserved_u32_20": struct.unpack_from("<I", blob, 20)[0],
        "body_offset": 24,
        "unknown": [
            "u16@16 meaning (0x0000 simple, 0x0100/0x0800 complex)",
            "byte@20 meaning (small int 0/1/2)",
            "count_a (u16@14) semantics",
            "body edge-record layout (u16 BE from 24 to vertex_section_offset)",
        ],
    }


def parse_jmxvimg(blob, path="<memory>"):
    if blob[:12] != JMXVIMG_MAGIC:
        return None
    h = struct.unpack_from("<H", blob, 12)[0]
    w = struct.unpack_from("<H", blob, 14)[0]
    body = len(blob) - 16
    return {
        "path": path,
        "family": "jmxvimg",
        "magic": "JMXVIMG11000",
        "field_12": h,
        "field_14": w,
        "pixel_bytes": body,
        "pixels_4byte": body // 4,
        "unknown": ["header field semantics (height vs width vs stride)"],
    }


def parse_plugin(blob, path="<memory>"):
    """Parse the plugin loader manifest (Map.pk2 /plugin.dat).

    PROVEN: u32 LE count; per entry a 16-byte identifier (GUID/hash) followed by
    a u16 LE name length and a null-terminated name. The only observed entry is
    `bsnetEx.dll` (11 chars) with count 1.
    """
    if len(blob) < 6:
        return None
    count = struct.unpack_from("<I", blob, 0)[0]
    if not 1 <= count <= 8:
        return None
    off = 4
    entries = []
    for _ in range(count):
        if off + 18 > len(blob):
            return None
        ident = blob[off:off + 16]
        off += 16
        name_len = struct.unpack_from("<H", blob, off)[0]
        off += 2
        if off + name_len > len(blob) or name_len == 0:
            return None
        raw = blob[off:off + name_len]
        off += name_len
        if not all(0x20 <= b < 0x7F for b in raw):
            return None
        entries.append({
            "identifier_hex": ident.hex(),
            "name": raw.decode("ascii", "replace"),
        })
    return {
        "path": path,
        "family": "plugin",
        "count": count,
        "entries": entries,
        "unknown": ["16-byte identifier semantics (GUID vs checksum/hash)"],
    }


def classify_dat(blob, path="<memory>"):
    if blob[:2] == b"BM":
        return {"path": path, "family": "bmp", "status": "PROVEN"}
    if blob[:12] == DDJ_MAGIC:
        return {"path": path, "family": "ddj", "status": "PROVEN"}
    if blob[:12] == JMXVIMG_MAGIC:
        r = parse_jmxvimg(blob, path)
        r["status"] = "PROVEN"
        return r
    r = parse_ainavdata(blob, path)
    if r is not None:
        r["status"] = "PARTIAL"
        return r
    if len(blob) == 768:
        return {"path": path, "family": "palette", "status": "PROVEN",
                "note": "256 entries x 3 bytes RGB"}
    if _hex_only(blob):
        return {"path": path, "family": "hex-token", "status": "PROVEN"}
    r = parse_plugin(blob, path)
    if r is not None:
        r["status"] = "PROVEN"
        return r
    if len(blob) >= 4 and len(blob) < 4096:
        lead = struct.unpack_from("<I", blob, 0)[0]
        if 1 <= lead <= 64:
            return {"path": path, "family": "config", "status": "PARTIAL",
                    "note": "u32 count-prefixed settings blob"}
    return {"path": path, "family": "unknown", "status": "UNKNOWN"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results = []
    for path in args.files:
        with open(path, "rb") as fh:
            blob = fh.read()
        r = classify_dat(blob, path)
        if r.get("family") == "ainavdata":
            import os
            name = os.path.basename(path).lower().replace(".dat", "")
            if name.startswith("ainavdata_"):
                try:
                    fid = int(name.split("_")[1])
                    r["nav_id_matches_filename"] = (r["nav_id"] == 0x8000 | fid)
                except ValueError:
                    pass
        results.append(r)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
            fh.write("\n")
    else:
        print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
