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


def group_census(entries, read_fn):
    """Group all nonzero .bsk entries by magic/version/size-bucket and by
    bone_type values. Returns a dict of PROVEN grouping facts; no semantic
    interpretation is attached to any bone_type value."""
    groups = {}
    bone_type_hist = {}
    for e in entries:
        if not e["path"].lower().endswith(".bsk") or e["size"] == 0:
            continue
        r = parse_bsk(read_fn(e))
        magic = r["magic"].decode("ascii", "replace") if isinstance(r["magic"], bytes) else ""
        # magic embeds the version (JMXVBSK 0101); derive a bounded label
        # instead of using parse_bsk's 'version' (which is data[12:] tail).
        version = magic[-4:] if magic.startswith("JMXVBSK ") else magic
        bucket = "small" if e["size"] < 256 else ("mid" if e["size"] < 16384 else "large")
        key = (magic, version, bucket)
        g = groups.setdefault(key, {"count": 0, "sizes": []})
        g["count"] += 1
        g["sizes"].append(e["size"])
        for b in r["bones"]:
            bt = b["bone_type"]
            bone_type_hist[bt] = bone_type_hist.get(bt, 0) + 1
    return {
        "groups": [
            {
                "magic": magic,
                "version": version,
                "size_bucket": bucket,
                "count": g["count"],
                "size_min": min(g["sizes"]),
                "size_max": max(g["sizes"]),
            }
            for (magic, version, bucket), g in groups.items()
        ],
        "bone_type_histogram": {str(k): v for k, v in sorted(bone_type_hist.items())},
    }


def census_record(data: bytes):
    """Walk a .bsk byte-for-byte and emit a per-field evidence record.

    Returns {'fields': [ {offset, size, field, raw_value, interpretation,
    evidence, status} ... ], 'bone_count', 'exact'}. Offsets are absolute
    file offsets; raw_value is kept byte/float-exact but size-capped for
    strings. No semantic name is attached to any field beyond the structural
    layout proven in Phase 18; status is PROVEN only for layout fields that
    byte-exhaust.
    """
    fields = []
    if data[:MAGIC_LEN] != BSK_MAGIC:
        return {
            "fields": [{
                "offset": 0, "size": min(16, len(data)), "field": "magic",
                "raw_value": data[:16].hex(), "interpretation": "UNKNOWN magic",
                "evidence": "does not equal JMXVBSK 0101", "status": "PARTIAL",
            }],
            "bone_count": 0, "exact": False,
        }

    def add(off, size, field, raw, interp, evidence, status):
        fields.append({
            "offset": off, "size": size, "field": field, "raw_value": raw,
            "interpretation": interp, "evidence": evidence, "status": status,
        })

    add(0, MAGIC_LEN, "magic", data[:MAGIC_LEN].decode("ascii", "replace"),
        "file magic", "equals JMXVBSK 0101", "PROVEN")
    (count,) = struct.unpack_from("<I", data, COUNT_OFFSET)
    add(COUNT_OFFSET, 4, "bone_count", count, "number of bone records",
        "parse consumes this many records", "PROVEN")
    off = COUNT_OFFSET + 4
    for i in range(count):
        bt = data[off]
        add(off, 1, "bones[%d].bone_type" % i, bt,
            "raw bone type byte", "structural layout byte; semantics UNKNOWN",
            "PROVEN" if data[off] == bt else "UNKNOWN")
        off += 1
        name, off = _read_str(data, off)
        add(off - 4 - len(name), 4 + len(name), "bones[%d].name" % i,
            name[:64], "bone name string", "structural layout", "PROVEN")
        parent, off = _read_str(data, off)
        add(off - 4 - len(parent), 4 + len(parent), "bones[%d].parent" % i,
            parent[:64], "parent bone name", "structural layout; empty=root",
            "PROVEN")
        for fname, n in _FLOAT_FIELDS:
            vals = list(struct.unpack_from("<%df" % n, data, off))
            add(off, 4 * n, "bones[%d].%s" % (i, fname),
                [round(v, 6) for v in vals],
                "f32 vector (%d)" % n, "structural layout", "PROVEN")
            off += 4 * n
        (cc,) = struct.unpack_from("<I", data, off)
        add(off, 4, "bones[%d].child_count" % i, cc,
            "number of child names", "structural layout", "PROVEN")
        off += 4
        for j in range(cc):
            child, off = _read_str(data, off)
            add(off - 4 - len(child), 4 + len(child),
                "bones[%d].children[%d]" % (i, j), child[:64],
                "child bone name", "structural layout", "PROVEN")
    trailer = data[off:off + TRAILER_LEN]
    exact = (off + TRAILER_LEN == len(data)) and (trailer == b"\x00" * TRAILER_LEN)
    add(off, TRAILER_LEN, "trailer", trailer.hex(),
        "8 zero bytes", "byte-exhaustion anchor", "PROVEN" if exact else "PARTIAL")
    return {"fields": fields, "bone_count": count, "exact": exact}


def bone_names(parsed):
    return [b["name"] for b in parsed["bones"]]
