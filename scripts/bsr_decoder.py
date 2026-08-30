#!/usr/bin/env python3
"""Phase 18 BSR decoder (vSRO 1.193, proven against original assets).

Proven facts (validated byte-for-byte against Data.pk2):
  * magic 'JMXVRES 0109' dominant (0108 x3, 0107 x1); 12-byte header
  * 8 x u32 table @12..44 (pointer semantics PARTIAL/UNKNOWN)
  * 16 zero bytes @44..60 (so body starts at 0x3C)
  * body = sequence of [u32 len][ascii] strings, length 4..300
  * paths carry a backslash and are classified by extension:
      .bmt materials, .bms mesh parts, .ban animations, .bsk skeleton,
      .efp effects, .wav sounds; non-path tokens are 'default' etc.
  * character .bsr (contains a .bsk) presents groups in first-occurrence
    order bmt -> bms -> ban -> bsk -> efp -> wav; static object .bsr
    (no .bsk) interleaves bmt/bms differently -- order NOT asserted there.

This module ships no PK2 reader; it operates on raw bytes only.
"""
from __future__ import annotations

import struct

BSR_MAGICS = (b"JMXVRES 0109", b"JMXVRES 0108", b"JMXVRES 0107")

HEADER_TABLE_OFFSET = 12
HEADER_TABLE_COUNT = 8
BODY_OFFSET = 0x3C  # 12 magic + 8*4 table + 16 zero bytes

GROUP_ORDER = (".bmt", ".bms", ".ban", ".bsk", ".efp", ".wav")


def _ext(path):
    return path.rsplit(".", 1)[-1].lower() if "." in path else ""


def _scan_tokens(data, start):
    toks = []
    i = start
    while i <= len(data) - 4:
        (ln,) = struct.unpack_from("<I", data, i)
        if 4 <= ln <= 300 and i + 4 + ln <= len(data):
            s = data[i + 4:i + 4 + ln]
            if all(32 <= c < 127 for c in s):
                toks.append((i, s.decode("ascii")))
                i += 4 + ln
                continue
        i += 1
    return toks


def parse_bsr_references(data: bytes):
    """Parse a .bsr file. Returns dict with magic, version, header_table,
    tokens (in file order), and extension-classified path lists."""
    magic = data[:12]
    if magic not in BSR_MAGICS:
        return {
            "magic": magic,
            "version": None,
            "header_table": None,
            "tokens": [],
            "materials": [],
            "meshes": [],
            "animations": [],
            "skeleton": [],
            "effects": [],
            "sounds": [],
            "paths": [],
            "is_character": False,
            "group_order_ok": False,
            "error": "unexpected magic",
        }
    header_table = list(struct.unpack_from("<8I", data, HEADER_TABLE_OFFSET))
    toks = _scan_tokens(data, BODY_OFFSET)
    paths = [t for _, t in toks if "\\" in t]

    classified = {k: [] for k in (".bmt", ".bms", ".ban", ".bsk", ".efp", ".wav")}
    for p in paths:
        ext = "." + _ext(p)
        if ext in classified:
            classified[ext].append("/" + p.replace("\\", "/"))

    is_character = bool(classified[".bsk"])
    first_order = []
    seen = set()
    for p in paths:
        e = "." + _ext(p)
        if e in classified and e not in seen:
            seen.add(e)
            first_order.append(e)
    group_order_ok = False
    if is_character:
        want = [e for e in GROUP_ORDER if e in seen]
        group_order_ok = first_order == want

    return {
        "magic": magic,
        "version": data[12:],
        "header_table": header_table,
        "tokens": [t for _, t in toks],
        "materials": classified[".bmt"],
        "meshes": classified[".bms"],
        "animations": classified[".ban"],
        "skeleton": classified[".bsk"],
        "effects": classified[".efp"],
        "sounds": classified[".wav"],
        "paths": paths,
        "is_character": is_character,
        "group_order_ok": group_order_ok,
        "error": None,
    }


def resolve_character(parsed):
    """Convenience: bmt/meshes/animations/skeleton for a character .bsr."""
    return {
        "bmt": parsed["materials"],
        "bms": parsed["meshes"],
        "ban": parsed["animations"],
        "bsk": parsed["skeleton"],
    }
