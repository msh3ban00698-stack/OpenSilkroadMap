#!/usr/bin/env python3
"""Pure-Python (stdlib-only) DDS decoder and PNG writer.

Decodes the subset of DDS formats VERIFIED present in the real vSRO 1.193
PK2 archives (see ANDROID_ASSET_MANIFEST.md Phase 4):

  - DXT1 (BC1), 1-bit-alpha and 4-color modes
  - DXT3 (BC2), explicit 4-bit-per-pixel alpha + 4-color interpolation
  - Uncompressed bitmasks: RGB565, ARGB1555, X8R8G8B8, A8R8G8B8 (generic
    channel-mask decode)

Any other pixel format raises UnsupportedPixelFormat. It does NOT guess.

The PNG writer uses only zlib/struct (no Pillow dependency) so output is
byte-for-byte deterministic (no embedded timestamps, fixed compression).

Verification: cross-checked against Pillow's DDS plugin on the real samples
in scripts/test_phase5_assets.py.
"""

import struct
import zlib

DDS_MAGIC = b"DDS "
JMX_DDJ_MAGIC = b"JMXVDDJ 1000"
DDS_HEADER_SIZE = 124

FOURCC_DXT1 = b"DXT1"
FOURCC_DXT3 = b"DXT3"

DDPF_ALPHAPIXELS = 0x1
DDPF_FOURCC = 0x4
DDPF_RGB = 0x40


class UnsupportedPixelFormat(Exception):
    pass


class InvalidDDS(Exception):
    pass


def _rgb565_to_rgb(v):
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def _lerp(c0, c1, n, d):
    return tuple((c0[i] * (d - n) + c1[i] * n) // d for i in range(3))


def _mask_shift_count(mask):
    shift = 0
    while mask and not (mask >> shift) & 1:
        shift += 1
    count = 0
    while mask >> (shift + count) & 1:
        count += 1
    return shift, count


def _unpack_masked(value, masks, alpha_present):
    rmask, gmask, bmask, amask = masks
    channels = []
    for mask in (rmask, gmask, bmask):
        if mask == 0:
            channels.append(0)
            continue
        shift, count = _mask_shift_count(mask)
        maxv = (1 << count) - 1
        channels.append(((value >> shift) & maxv) * 255 // maxv)
    if alpha_present and amask != 0:
        shift, count = _mask_shift_count(amask)
        maxv = (1 << count) - 1
        channels.append(((value >> shift) & maxv) * 255 // maxv)
    else:
        channels.append(255)
    return tuple(channels)


def _decode_dxt1_block(block, alpha_1bit):
    c0, c1 = struct.unpack_from("<HH", block, 0)
    col0 = _rgb565_to_rgb(c0)
    col1 = _rgb565_to_rgb(c1)
    if c0 > c1:
        col2 = _lerp(col0, col1, 1, 3)
        col3 = _lerp(col0, col1, 2, 3)
        palette = [col0, col1, col2, col3]
        alpha = [255, 255, 255, 255]
    else:
        col2 = _lerp(col0, col1, 1, 2)
        col3 = (0, 0, 0)
        palette = [col0, col1, col2, col3]
        alpha = [255, 255, 255, 0]
    indices = struct.unpack_from("<I", block, 4)[0]
    px = []
    for i in range(16):
        idx = (indices >> (i * 2)) & 0x3
        r, g, b = palette[idx]
        a = alpha[idx] if alpha_1bit else 255
        px.append((r, g, b, a))
    return px


def _decode_dxt3_block(block):
    alpha = []
    for i in range(8):
        byte = block[i]
        alpha.append((byte & 0x0F) * 255 // 15)
        alpha.append((byte >> 4) * 255 // 15)
    c0, c1 = struct.unpack_from("<HH", block, 8)
    col0 = _rgb565_to_rgb(c0)
    col1 = _rgb565_to_rgb(c1)
    col2 = _lerp(col0, col1, 1, 3)
    col3 = _lerp(col0, col1, 2, 3)
    palette = [col0, col1, col2, col3]
    indices = struct.unpack_from("<I", block, 12)[0]
    px = []
    for i in range(16):
        idx = (indices >> (i * 2)) & 0x3
        r, g, b = palette[idx]
        px.append((r, g, b, alpha[i]))
    return px


def parse_dds(data):
    if data[0:4] != DDS_MAGIC:
        raise InvalidDDS("missing DDS magic")
    if len(data) < DDS_HEADER_SIZE + 4:
        raise InvalidDDS("truncated DDS header")
    size, flags, height, width, pitch, depth, mipmaps = struct.unpack_from(
        "<7I", data, 4
    )
    pf_size, pf_flags, fourcc, bitcount, rmask, gmask, bmask, amask = (
        struct.unpack_from("<II4sIIIII", data, 4 + 72)
    )
    return {
        "size": size,
        "flags": flags,
        "height": height,
        "width": width,
        "pitch": pitch,
        "depth": depth,
        "mipmaps": mipmaps,
        "pf_size": pf_size,
        "pf_flags": pf_flags,
        "fourcc": fourcc,
        "bitcount": bitcount,
        "masks": (rmask, gmask, bmask, amask),
    }


def decode_dds(data):
    hdr = parse_dds(data)
    w, h = hdr["width"], hdr["height"]
    if w == 0 or h == 0:
        raise InvalidDDS("zero dimensions")
    fourcc = hdr["fourcc"]
    if hdr["pf_flags"] & DDPF_FOURCC:
        if fourcc == FOURCC_DXT1:
            return _decode_dxt(data, w, h, "DXT1")
        if fourcc == FOURCC_DXT3:
            return _decode_dxt(data, w, h, "DXT3")
        raise UnsupportedPixelFormat(
            "compressed fourcc %r not verified for vSRO (only DXT1/DXT3)" % fourcc
        )
    if hdr["pf_flags"] & DDPF_RGB:
        return _decode_uncompressed(data, hdr)
    raise UnsupportedPixelFormat(
        "pixel format flags 0x%x not recognized" % hdr["pf_flags"]
    )


def _decode_dxt(data, w, h, fmt):
    blocks_x = (w + 3) // 4
    blocks_y = (h + 3) // 4
    block_size = 8 if fmt == "DXT1" else 16
    pix = [None] * (w * h)
    pos = DDS_HEADER_SIZE + 4
    alpha_1bit = fmt == "DXT1"
    for by in range(blocks_y):
        for bx in range(blocks_x):
            block = data[pos:pos + block_size]
            pos += block_size
            if len(block) < block_size:
                raise InvalidDDS("truncated block data")
            if fmt == "DXT1":
                px = _decode_dxt1_block(block, alpha_1bit)
            else:
                px = _decode_dxt3_block(block)
            for py in range(4):
                for px2 in range(4):
                    x = bx * 4 + px2
                    y = by * 4 + py
                    if x < w and y < h:
                        pix[y * w + x] = px[py * 4 + px2]
    return w, h, pix


def _decode_uncompressed(data, hdr):
    w, h = hdr["width"], hdr["height"]
    bpp = hdr["bitcount"] // 8
    if bpp not in (2, 3, 4):
        raise UnsupportedPixelFormat(
            "uncompressed bitcount %d not verified for vSRO" % hdr["bitcount"]
        )
    rmask, gmask, bmask, amask = hdr["masks"]
    alpha_present = bool(hdr["pf_flags"] & DDPF_ALPHAPIXELS)
    pos = DDS_HEADER_SIZE + 4
    pitch = hdr["pitch"] or (w * bpp)
    pix = []
    for _y in range(h):
        row = data[pos:pos + pitch]
        pos += pitch
        if len(row) < w * bpp:
            raise InvalidDDS("truncated pixel row")
        for x in range(w):
            off = x * bpp
            value = int.from_bytes(row[off:off + bpp], "little")
            pix.append(_unpack_masked(value, (rmask, gmask, bmask, amask), alpha_present))
    return w, h, pix


def ddj_to_rgba(data):
    """Strip the verified 20-byte JMX header, decode the DDS payload."""
    if len(data) < 20 or data[0:12] != JMX_DDJ_MAGIC:
        raise InvalidDDS("not a verified JMXVDDJ 1000 container")
    return decode_dds(data[20:])


def png_from_rgba(w, h, pixels):
    """Deterministic PNG encoder (8-bit RGBA, filter None, zlib level 9)."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(pixels[y * w + x])
    idat = zlib.compress(bytes(raw), 9)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)

    def chunk(typ, payload):
        return (
            struct.pack(">I", len(payload))
            + typ
            + payload
            + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        )

    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def parse_png_header(png):
    """Return (width, height, bit_depth, color_type) from a PNG, validating
    signature/IHDR length and CRC."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise InvalidDDS("not a PNG")
    length = struct.unpack(">I", png[8:12])[0]
    if length != 13:
        raise InvalidDDS("bad IHDR length")
    if png[12:16] != b"IHDR":
        raise InvalidDDS("IHDR not first chunk")
    payload = png[16:16 + 13]
    crc_ok = struct.unpack(">I", png[29:33])[0] == (
        zlib.crc32(b"IHDR" + payload) & 0xFFFFFFFF
    )
    if not crc_ok:
        raise InvalidDDS("IHDR CRC mismatch")
    w, h, bit_depth, color_type = struct.unpack(">IIBB", payload[:10])
    return w, h, bit_depth, color_type
