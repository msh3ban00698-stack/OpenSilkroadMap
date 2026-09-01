#!/usr/bin/env python3
"""Phase 21 IFO decoders (vSRO 1.193, proven against original Map.pk2 assets).

The `.ifo` extension is polymorphic. This module covers the three new magics
that were previously magic-only UNKNOWN:

  * `layerobjectlist.ifo` -> `JMXVOBJL1000` (TEXT): the master object-placement
    list. PROVEN: line 0 magic, line 1 decimal count, then one entry per line
    with 9 space-separated fields:
        {id_hex} {type} {sector_x} {sector_y} {x_hex} {y_hex} {z_hex} {theta_hex} {flag}
    - id_hex: object-instance id; top 16 bits always == (sector_y << 8) | sector_x
    - x/y/z/theta: float32 encoded as hex bit-pattern (e.g. 0x3fc90fd8 == pi/2)
    - type in 1..11, flag in {0,1}
    All 3,334 entries parse; count matches exactly.

  * `config.ifo` -> `JMXVCAMR1002` (binary): camera configuration. PARTIAL:
    magic + a stream of float32 camera parameters; exact field assignment (pos /
    target / up / fov / near / far) is UNKNOWN.

  * `environment.ifo` -> `JMXVENVI1003` (binary): environment/lighting settings.
    PARTIAL: magic + u32 header + length-prefixed names ("Env7") + float32
    colour/lighting values; exact field assignment is UNKNOWN.

This module ships no PK2 reader; it operates on raw bytes / decoded text only.
"""
from __future__ import annotations

import struct

OBJL_MAGIC = "JMXVOBJL1000"
CAMR_MAGIC = b"JMXVCAMR1002"
ENVI_MAGIC = b"JMXVENVI1003"


def _hexfloat(h: str) -> float:
    return struct.unpack("<f", struct.pack("<I", int(h, 16)))[0]


def parse_layerobjectlist_ifo(text: str) -> dict:
    """Parse the TEXT object-placement list (`JMXVOBJL1000`)."""
    lines = text.splitlines()
    if not lines or lines[0] != OBJL_MAGIC:
        return {"valid": False, "magic": lines[0] if lines else "", "error": "bad magic"}
    count = int(lines[1])
    entries = []
    for ln in lines[2:]:
        p = ln.split()
        if len(p) != 9:
            return {"valid": False, "magic": OBJL_MAGIC, "error": "bad entry width"}
        id_hex, typ, sx, sy, fx, fy, fz, ft, flag = p
        entries.append({
            "id": int(id_hex, 16),
            "type": int(typ),
            "sector_x": int(sx),
            "sector_y": int(sy),
            "x": _hexfloat(fx),
            "y": _hexfloat(fy),
            "z": _hexfloat(fz),
            "theta": _hexfloat(ft),
            "flag": int(flag),
        })
    return {
        "valid": True,
        "magic": OBJL_MAGIC,
        "count": count,
        "entries": entries,
        "count_matches": count == len(entries),
        "error": None,
    }


def parse_camera_ifo(data: bytes) -> dict:
    """Parse the binary camera config (`JMXVCAMR1002`) header + float stream."""
    if len(data) < 16 or data[:12] != CAMR_MAGIC:
        return {"valid": False, "magic": data[:12], "error": "bad magic or too short"}
    return {
        "valid": True,
        "magic": data[:12],
        "size": len(data),
        "error": None,
    }


def parse_environment_ifo(data: bytes) -> dict:
    """Parse the binary environment config (`JMXVENVI1003`) header + names."""
    if len(data) < 28 or data[:12] != ENVI_MAGIC:
        return {"valid": False, "magic": data[:12], "error": "bad magic or too short"}
    hdr0 = struct.unpack_from("<I", data, 12)[0]
    name_len = struct.unpack_from("<I", data, 20)[0]
    name = data[24:24 + name_len].decode("latin1", "replace")
    return {
        "valid": True,
        "magic": data[:12],
        "size": len(data),
        "header_u32_12": hdr0,
        "name": name,
        "error": None,
    }
