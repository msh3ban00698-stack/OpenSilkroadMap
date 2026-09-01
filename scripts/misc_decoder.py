#!/usr/bin/env python3
"""Decoders for the last non-JMX source-corpus formats (Phase 21 tail).

Each format below was previously extension-only UNKNOWN. This module proves a
decodable header/family for each and records the still-UNKNOWN remainder.

  * `.rd`   -> "bmp-region-thumbnail"  PROVEN: standard Windows BMP, 16x16 8bpp
                indexed; all 103 samples share the identical 1078-byte header
                (file size 1334, data offset 1078, 16x16, 1 plane, 8bpp, BI_RGB).
  * `.2dt`  -> "cnif-ui-layout"        PARTIAL: u32 field + "CNIF" magic + null-
                terminated window name; body is a serialized UI control tree
                embedding `.ddj` texture and `UIIT_` string tokens (UNKNOWN).
  * `.mfo`  -> "jmx-mfo-mapinfo"       PARTIAL: "JMXVMFO 1000" magic + u16 width
                + u16 height; trailing sparse data grid (UNKNOWN).
  * `.msf`  -> "sound-effect-script"   PARTIAL: u32 count + fixed u32 fields +
                length-prefixed "ambient" + `.efp` path refs + float triples
                (UNKNOWN semantics).
  * `.bak`  -> "mtf-sql-backup"        PARTIAL: "TAPE" MTF magic + fixed MTF
                header; embedded T-SQL dump (see FORMAT_RESEARCH section 10).
  * `.dll`/`.exe` -> "pe-executable"   PROVEN: MZ + PE\0\0 signature (standard).

Reads raw bytes only; no PK2 reader here.
"""
from __future__ import annotations

import struct

BMP_MAGIC = b"BM"
CNIF_MAGIC = b"CNIF"
MFO_MAGIC = "JMXVMFO 1000"
PE_MZ = b"MZ"
PE_SIG = b"PE\x00\x00"
MTF_MAGIC = b"TAPE"


def parse_rd(data: bytes) -> dict:
    """Standard BMP header check for the 16x16 region thumbnails."""
    if len(data) < 30 or data[:2] != BMP_MAGIC:
        return {"valid": False, "magic": data[:2], "error": "not BMP"}
    file_size = struct.unpack_from("<I", data, 2)[0]
    data_offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    height = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    return {
        "valid": True,
        "magic": "BM",
        "file_size": file_size,
        "data_offset": data_offset,
        "width": width,
        "height": height,
        "bpp": bpp,
        "error": None,
    }


def parse_2dt(data: bytes) -> dict:
    """CNIF UI layout: u32 field + 'CNIF' + null-terminated window name."""
    if len(data) < 12 or data[4:8] != CNIF_MAGIC:
        return {"valid": False, "magic": data[4:8], "error": "not CNIF"}
    field0 = struct.unpack_from("<I", data, 0)[0]
    end = data.index(0, 8)
    name = data[8:end].decode("latin1", "replace")
    return {
        "valid": True,
        "magic": "CNIF",
        "field0": field0,
        "name": name,
        "size": len(data),
        "error": None,
    }


def parse_mfo(data: bytes) -> dict:
    """JMXVMFO map info: 12-byte magic + u16 width + u16 height."""
    if len(data) < 16 or data[:12] != MFO_MAGIC.encode("latin1"):
        return {"valid": False, "magic": data[:12], "error": "bad magic"}
    width = struct.unpack_from("<H", data, 12)[0]
    height = struct.unpack_from("<H", data, 14)[0]
    return {
        "valid": True,
        "magic": MFO_MAGIC,
        "width": width,
        "height": height,
        "size": len(data),
        "error": None,
    }


def parse_msf(data: bytes) -> dict:
    """Sound-effect script: u32 count + fields + length-prefixed name + efp refs."""
    if len(data) < 24:
        return {"valid": False, "magic": b"", "error": "too short"}
    count = struct.unpack_from("<I", data, 0)[0]
    f4 = struct.unpack_from("<I", data, 4)[0]
    f8 = struct.unpack_from("<I", data, 8)[0]
    name_len = struct.unpack_from("<I", data, 12)[0]
    name = data[16:16 + name_len].decode("latin1", "replace")
    has_efp = b".efp" in data
    return {
        "valid": True,
        "magic": name or "msf",
        "count": count,
        "field4": f4,
        "field8": f8,
        "name": name,
        "has_efp_refs": has_efp,
        "size": len(data),
        "error": None,
    }


def parse_pe(data: bytes) -> dict:
    """PE executable check (MZ + PE\\0\\0 at e_lfanew)."""
    if len(data) < 0x40 or data[:2] != PE_MZ:
        return {"valid": False, "magic": data[:2], "error": "not MZ"}
    off = struct.unpack_from("<I", data, 0x3C)[0]
    sig = data[off:off + 4] if off + 4 <= len(data) else b""
    return {
        "valid": sig == PE_SIG,
        "magic": "MZ",
        "pe_signature": sig == PE_SIG,
        "error": None if sig == PE_SIG else "no PE signature",
    }


def parse_bak(data: bytes) -> dict:
    """MTF backup: 'TAPE' magic + fixed header."""
    if len(data) < 16 or data[:4] != MTF_MAGIC:
        return {"valid": False, "magic": data[:4], "error": "not MTF"}
    return {
        "valid": True,
        "magic": "TAPE",
        "size": len(data),
        "error": None,
    }
