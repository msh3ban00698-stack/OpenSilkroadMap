#!/usr/bin/env python3
"""Phase 21 CPD decoder (vSRO 1.193, proven against original Data.pk2 assets).

A `.cpd` file is a Joymax "compound" manifest: it names a compound object and
lists the `.bsr` mesh-resource component paths that make it up (a base mesh
plus attachments such as shadow, armor parts, or particle sub-effects).

Proven layout (validated byte-for-byte against all 124 Data.pk2 `.cpd` files):

    offset 0    magic[12]          "JMXVCPD 0101"
    offset 12   u32 primary_off    file offset of `primary_len` (== 48+name_len+8)
    offset 16   u32 count_off      file offset of `count` (== 48+name_len+12+primary_len)
    offset 20   u32[5] reserved    always zero
    offset 40   u16 type           0=character, 2=object/struct
    offset 42   u16 subtype        always 3
    offset 44   u32 name_len
    offset 48   char[name_len] name
    offset ne   u32 flag_x         (semantics UNKNOWN; observed {0,3})
    offset ne+4 u32 flag_y         (semantics UNKNOWN; observed {0,1,2})
    offset ne+8 u32 primary_len    length of primary .bsr path (0 = none)
    offset ne+12 char[primary_len] primary_path  (a .bsr path, may be empty)
    offset count_off  u32 count    number of component .bsr paths
    offset count_off+4: count x { u32 len; char[len] path }

`primary_off` and `count_off` are stored in the header and are always exactly
the arithmetic values above, so the file is fully self-consistent and the
parse is byte-exact.

This module ships no PK2 reader; it operates on raw bytes only.
"""
from __future__ import annotations

import struct

CPD_MAGIC = b"JMXVCPD 0101"

NAME_OFFSET = 48  # 12 magic + 2 offsets + 20 reserved + 2+2 type/subtype + 4 len

TYPE_CHARACTER = 0
TYPE_OBJECT = 2


def _decode(b: bytes) -> str:
    return b.decode("latin1")


def parse_cpd(data: bytes) -> dict:
    """Parse a `.cpd` compound manifest.

    Returns a dict with: valid, magic, type, subtype, name, flag_x, flag_y,
    primary_path, paths, count_self_consistent, byte_exact, error.
    """
    if len(data) < NAME_OFFSET + 8 or data[:12] != CPD_MAGIC:
        return {
            "valid": False,
            "magic": data[:12],
            "error": "bad magic or too short",
        }
    primary_off, count_off = struct.unpack_from("<II", data, 12)
    reserved = data[20:40]
    typ, subtype = struct.unpack_from("<HH", data, 40)
    name_len = struct.unpack_from("<I", data, 44)[0]
    ne = NAME_OFFSET + name_len
    if ne + 12 > len(data):
        return {"valid": False, "magic": data[:12], "error": "header overruns file"}
    name = _decode(data[NAME_OFFSET:ne])
    flag_x, flag_y = struct.unpack_from("<II", data, ne)
    primary_len = struct.unpack_from("<I", data, ne + 8)[0]
    primary_path = _decode(data[ne + 12:ne + 12 + primary_len])

    exp_primary_off = ne + 8
    exp_count_off = ne + 12 + primary_len
    consistent = primary_off == exp_primary_off and count_off == exp_count_off

    cnt = struct.unpack_from("<I", data, count_off)[0]
    off = count_off + 4
    paths = []
    exact = True
    for _ in range(cnt):
        if off + 4 > len(data):
            exact = False
            break
        ln = struct.unpack_from("<I", data, off)[0]
        off += 4
        if off + ln > len(data):
            exact = False
            break
        paths.append(_decode(data[off:off + ln]))
        off += ln

    return {
        "valid": True,
        "magic": data[:12],
        "type": typ,
        "subtype": subtype,
        "name": name,
        "flag_x": flag_x,
        "flag_y": flag_y,
        "primary_path": primary_path,
        "paths": paths,
        "count": cnt,
        "reserved_zero": reserved == b"\x00" * 20,
        "count_self_consistent": consistent,
        "byte_exact": exact and off == len(data),
        "error": None,
    }
