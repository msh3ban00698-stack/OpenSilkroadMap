#!/usr/bin/env python3
"""Phase 21 DOF decoder (vSRO 1.193, proven against original Data.pk2 assets).

A `.dof` file is a Joymax "dungeon object" container: it lays out the objects,
mesh resources, transforms, and named regions that make up a dungeon interior.

Proven facts (validated across all 34 Data.pk2 `.dof` files):
  * magic 'JMXVDOF 0101' (12-byte header)
  * 8 x u32 section-offset table @12..44 (little-endian, file-relative offsets)
      [0] = object-instance section start (constant 116)
      [1] = mesh-reference section start
      [2] = transform section start
      [3] = region-name section start
      [4] = secondary name section start
      [5],[6] = 0
      [7] = transform/object data start (constant 68)
  * a default object name (e.g. 'Noname') immediately follows the table
  * the body embeds length-prefixed ASCII strings: '.bsr' mesh-resource paths
    and 'RN_' region names

Unproven (documented, not guessed):
  * per-section record layouts (object instances, transform matrices/quaternions,
    region-name records) -- only the string content and the section-offset table
    are decoded here.

This module ships no PK2 reader; it operates on raw bytes only.
"""
from __future__ import annotations

import struct

DOF_MAGIC = b"JMXVDOF 0101"

HEADER_OFFSET = 12
HEADER_COUNT = 8

MAX_STR = 300


def _scan_strings(data: bytes, start: int):
    toks = []
    i = start
    n = len(data)
    while i <= n - 4:
        (ln,) = struct.unpack_from("<I", data, i)
        if 1 <= ln <= MAX_STR and i + 4 + ln <= n:
            s = data[i + 4:i + 4 + ln]
            if all(32 <= c < 127 for c in s):
                toks.append((i, s.decode("ascii")))
                i += 4 + ln
                continue
        i += 1
    return toks


def parse_dof(data: bytes) -> dict:
    """Parse a `.dof` dungeon-object container.

    Returns magic, header_table, mesh references (.bsr), region names (RN_),
    all strings, and validity flags. Does not claim per-section record layouts.
    """
    if len(data) < HEADER_OFFSET + HEADER_COUNT * 4 or data[:12] != DOF_MAGIC:
        return {"valid": False, "magic": data[:12], "error": "bad magic or too short"}
    header_table = list(struct.unpack_from("<8I", data, HEADER_OFFSET))
    toks = _scan_strings(data, HEADER_OFFSET + HEADER_COUNT * 4)
    meshes = [s for _, s in toks if s.lower().endswith(".bsr")]
    regions = [s for _, s in toks if s.startswith("RN_")]

    in_range = [0 <= v < len(data) for v in header_table]
    return {
        "valid": True,
        "magic": data[:12],
        "header_table": header_table,
        "header_offsets_in_range": all(in_range),
        "strings": [s for _, s in toks],
        "meshes": meshes,
        "regions": regions,
        "error": None,
    }
