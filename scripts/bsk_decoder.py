#!/usr/bin/env python3
"""Phase 18 BSK skeleton decoder (vSRO 1.193, proven against original assets).

Proven facts (validated byte-for-byte against Data.pk2):
  * magic 'JMXVBSK 0101' constant (12 bytes)
  * u32 bone_count @12
  * per bone:
      u8  bone_type                 (raw value; semantics UNKNOWN, kept opaque)
      str name                       (u32 len + ascii)
      str parent_name                (u32 len + ascii; empty for root)
      21 x f32: rot_parent(4) tr_parent(3) rot_origin(4) tr_origin(3)
                rot_local(4) tr_local(3)
      u32 child_count + child_count x str
  * 8 zero trailer bytes
  * byte-exhausts 1034/1035 nonzero .bsk in Data.pk2 (1 outlier:
    /prim/skel/item/common/mob_select.bsk -- structure UNKNOWN)

Units/meaning of the quaternion/position fields are NOT asserted here; they
are exported verbatim. Callers wanting bind pose reconstruct parent-relative
transforms via skeleton.py (Task 4).

This module ships no PK2 reader; it operates on raw bytes only.
"""
from __future__ import annotations

import struct

BSK_MAGIC = b"JMXVBSK 0101"

MAGIC_LEN = 12
COUNT_OFFSET = 12
TRAILER_LEN = 8

_FLOAT_FIELDS = (
    ("rot_parent", 4),
    ("tr_parent", 3),
    ("rot_origin", 4),
    ("tr_origin", 3),
    ("rot_local", 4),
    ("tr_local", 3),
)


def _read_str(data, off):
    (ln,) = struct.unpack_from("<I", data, off)
    raw = data[off + 4:off + 4 + ln]
    return raw.decode("ascii"), off + 4 + ln


def parse_bsk(data: bytes):
    """Parse a .bsk file. Returns dict (never raises on layout errors; sets
    'exact'=False and 'error' when the file does not byte-exhaust cleanly)."""
    if data[:MAGIC_LEN] != BSK_MAGIC:
        return {
            "magic": data[:MAGIC_LEN],
            "version": None,
            "bone_count": 0,
            "bones": [],
            "trailer": None,
            "parsed_bytes": 0,
            "file_size": len(data),
            "exact": False,
            "error": "unexpected magic",
        }
    (count,) = struct.unpack_from("<I", data, COUNT_OFFSET)
    off = COUNT_OFFSET + 4
    bones = []
    try:
        for i in range(count):
            bone_type = data[off]
            off += 1
            name, off = _read_str(data, off)
            parent, off = _read_str(data, off)
            fields = {}
            for fname, n in _FLOAT_FIELDS:
                fields[fname] = list(struct.unpack_from("<%df" % n, data, off))
                off += 4 * n
            (child_count,) = struct.unpack_from("<I", data, off)
            off += 4
            children = []
            for _ in range(child_count):
                child, off = _read_str(data, off)
                children.append(child)
            bones.append({
                "bone_type": bone_type,
                "name": name,
                "parent": parent,
                "children": children,
                **fields,
            })
    except (struct.error, UnicodeDecodeError, IndexError) as exc:
        return {
            "magic": BSK_MAGIC,
            "version": data[MAGIC_LEN:],
            "bone_count": count,
            "bones": bones,
            "trailer": data[off:],
            "parsed_bytes": off,
            "file_size": len(data),
            "exact": False,
            "error": str(exc),
        }
    trailer = data[off:off + TRAILER_LEN]
    exact = (off + TRAILER_LEN == len(data)) and (trailer == b"\x00" * TRAILER_LEN)
    return {
        "magic": BSK_MAGIC,
        "version": data[MAGIC_LEN:],
        "bone_count": count,
        "bones": bones,
        "trailer": trailer,
        "parsed_bytes": off,
        "file_size": len(data),
        "exact": exact,
        "error": None if exact else "trailer mismatch or trailing bytes",
    }


def census_bsk(entries, read_fn):
    """Return {'exact': n, 'inexact': [path...], 'total_nonzero': n} over a
    list of archive entries (each dict with 'path'/'size') and a bytes-read
    callable. Zero-size files are skipped (reported separately)."""
    result = {"exact": 0, "inexact": [], "total_nonzero": 0, "zero": []}
    for e in entries:
        if not e["path"].lower().endswith(".bsk"):
            continue
        if e["size"] == 0:
            result["zero"].append(e["path"])
            continue
        result["total_nonzero"] += 1
        r = parse_bsk(read_fn(e))
        if r["exact"]:
            result["exact"] += 1
        else:
            result["inexact"].append(e["path"])
    return result


def bone_names(parsed):
    return [b["name"] for b in parsed["bones"]]
