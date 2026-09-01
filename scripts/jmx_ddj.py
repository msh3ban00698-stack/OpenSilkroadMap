#!/usr/bin/env python3
"""Deterministic JMX .ddj texture-container parser.

The Joymax `.ddj` format is a 20-byte JMX wrapper around an embedded standard
DDS texture. Structure (PROVEN against 47,495 real files across Data/Media/
Particles; verified here on samples of 2 KB .. 2.9 MB):

    offset  size  field
    0       12    magic + version  "JMXVDDJ 1000"
    12      4     u32  data_size  == total_file_size - 12 (constant across all)
    16      4     u32  level/flag == 3 (constant; semantics UNKNOWN)
    20      ..    embedded DDS texture ("DDS " magic + 124-byte header + data)

The embedded DDS is a standard DirectDraw Surface: dwMagic, dwSize(124),
dwFlags, dwHeight, dwWidth, pitch/linear-size, depth, mipmap count, 11 reserved
u32, then DDS_PIXELFORMAT (dwSize, dwFlags, dwFourCC, RGB bit count, masks) and
DDS_HEADER_DXT10 (optional). Only the DDS metadata is parsed here; pixel data
is not decoded (already proven in prior phases via `dds_decode.py` /
`convert_ddjs.py`).

Read-only. Emits JSON on stdout or via --out.
"""
from __future__ import annotations

import argparse
import json
import struct

DDJ_MAGIC = b"JMXVDDJ 1000"
DDJ_HEADER = 20
DDS_MAGIC = b"DDS "

# DDSD_* flags
DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PITCH = 0x8
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDSD_LINEARSIZE = 0x80000
DDSD_DEPTH = 0x800000

# DDPF_* flags
DDPF_ALPHAPIXELS = 0x1
DDPF_FOURCC = 0x4
DDPF_RGB = 0x40


def parse_dds_header(buf):
    if buf[:4] != DDS_MAGIC:
        return None
    if len(buf) < 128:
        return None
    size = struct.unpack_from("<I", buf, 4)[0]
    flags = struct.unpack_from("<I", buf, 8)[0]
    height = struct.unpack_from("<I", buf, 12)[0]
    width = struct.unpack_from("<I", buf, 16)[0]
    pitch = struct.unpack_from("<I", buf, 20)[0]
    depth = struct.unpack_from("<I", buf, 24)[0]
    mipmaps = struct.unpack_from("<I", buf, 28)[0]
    pf_size = struct.unpack_from("<I", buf, 76)[0]
    pf_flags = struct.unpack_from("<I", buf, 80)[0]
    fourcc = buf[84:88]
    rgb_bits = struct.unpack_from("<I", buf, 88)[0]
    rmask = struct.unpack_from("<I", buf, 92)[0]
    gmask = struct.unpack_from("<I", buf, 96)[0]
    bmask = struct.unpack_from("<I", buf, 100)[0]
    amask = struct.unpack_from("<I", buf, 104)[0]
    return {
        "dds_header_size": size,
        "flags": flags,
        "width": width,
        "height": height,
        "pitch_or_linear_size": pitch,
        "depth": depth,
        "mipmap_count": mipmaps,
        "has_mipmaps": bool(flags & DDSD_MIPMAPCOUNT),
        "pixelformat_size": pf_size,
        "pixelformat_flags": pf_flags,
        "fourcc": fourcc.decode("latin-1") if pf_flags & DDPF_FOURCC else None,
        "rgb_bit_count": rgb_bits,
        "is_fourcc": bool(pf_flags & DDPF_FOURCC),
        "is_rgb": bool(pf_flags & DDPF_RGB),
        "has_alpha": bool(pf_flags & DDPF_ALPHAPIXELS),
        "r_mask": rmask,
        "g_mask": gmask,
        "b_mask": bmask,
        "a_mask": amask,
    }


def parse_ddj(blob, path="<memory>"):
    if len(blob) < DDJ_HEADER + 4:
        return {"path": path, "valid": False, "reason": "too short"}
    if blob[:12] != DDJ_MAGIC:
        return {"path": path, "valid": False, "reason": "bad magic"}
    data_size = struct.unpack_from("<I", blob, 12)[0]
    level = struct.unpack_from("<I", blob, 16)[0]
    dds = parse_dds_header(blob[DDJ_HEADER:])
    return {
        "path": path,
        "valid": True,
        "total_size": len(blob),
        "magic": DDJ_MAGIC.decode("latin-1"),
        "data_size": data_size,
        "data_size_matches": (data_size == len(blob) - 12),
        "level_field": level,
        "dds_offset": DDJ_HEADER,
        "dds": dds,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=None, help="write JSON to this path")
    args = ap.parse_args()

    results = []
    for path in args.files:
        with open(path, "rb") as fh:
            blob = fh.read()
        results.append(parse_ddj(blob, path))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
            fh.write("\n")
    else:
        print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
