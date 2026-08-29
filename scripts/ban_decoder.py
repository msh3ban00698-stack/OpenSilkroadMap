"""Partial decoder for the JMXVBAN animation format (VSRO-R 1.193).

Only the structure proven from real archive samples is decoded (see
FORMAT_RESEARCH.md / DATA_FORMAT_CATALOG.md for evidence):

  offset  size  field
  ------  ----  -----
  0x00    8     magic b"JMXVBAN 0102"
  0x0C    8     zero bytes (UNKNOWN semantics)
  0x14    4     u32 LE animation-name length
  0x18    N     animation name bytes (NUL terminated at 0x18+length)
  ...     --    body: embedded bone names + keyframe records

Keyframe record (28 bytes, stride proven on 3 independent real files):
  0..15   4 x f32 LE normalized rotation quaternion
  16..27  3 x f32 LE position

Unknown fields (all u32 LE present after the name) are exposed via
``header_after_name`` but their semantics are NOT asserted.
"""

from __future__ import annotations

import struct

MAGIC = b"JMXVBAN "  # 8 bytes, trailing space is part of the magic
VERSION_BYTES = b"0102"
KEYFRAME_STRIDE = 28
QUATERNION_TOLERANCE = 0.05


class BanFormatError(ValueError):
    pass


def parse_ban_header(data: bytes) -> dict:
    if len(data) < 0x18:
        raise BanFormatError("short header")
    if data[0:8] != MAGIC or data[8:12] != VERSION_BYTES:
        raise BanFormatError("bad magic/version")
    name_len = struct.unpack_from("<I", data, 0x14)[0]
    name_start = 0x18
    name_end = name_start + name_len
    if name_end > len(data):
        raise BanFormatError("name length exceeds file")
    name = data[name_start:name_end]
    try:
        name_text = name.decode("ascii")
    except UnicodeDecodeError:
        name_text = name.decode("latin-1")
    return {
        "magic": data[0:8].decode("ascii"),
        "version": data[8:12].decode("ascii"),
        "reserved_hex": data[0x0C:0x14].hex(),
        "name_length": name_len,
        "name": name_text,
        "body_start": name_end + 1,
    }


def _quaternion_norm_ok(data: bytes, offset: int, tolerance: float) -> bool:
    q = struct.unpack_from("<4f", data, offset)
    return abs(sum(x * x for x in q) - 1.0) < tolerance


def find_keyframe_runs(data: bytes, body_start: int, min_run: int = 2) -> list[dict]:
    """Return contiguous stride-28 runs whose records carry normalized quaternions.

    Each run is (start_offset, length_in_records). Runs shorter than ``min_run``
    are skipped to avoid single-record noise.
    """
    runs: list[dict] = []
    i = body_start
    while i + KEYFRAME_STRIDE <= len(data):
        if _quaternion_norm_ok(data, i, QUATERNION_TOLERANCE):
            start = i
            count = 0
            while (
                i + KEYFRAME_STRIDE <= len(data)
                and _quaternion_norm_ok(data, i, QUATERNION_TOLERANCE)
            ):
                count += 1
                i += KEYFRAME_STRIDE
            if count >= min_run:
                runs.append(
                    {
                        "start_offset": start,
                        "record_count": count,
                        "quaternion": [round(x, 3) for x in struct.unpack_from("<4f", data, start)],
                        "position": [round(x, 3) for x in struct.unpack_from("<3f", data, start + 16)],
                    }
                )
        else:
            i += 1
    return runs


def decode_keyframes(data: bytes, record_cap: int = 8) -> dict:
    """Parse header and the first verified keyframe runs. Reports, never invents."""
    header = parse_ban_header(data)
    runs = find_keyframe_runs(data, header["body_start"])
    result = {
        "header": header,
        "keyframe_runs": runs,
        "record_byte_size": KEYFRAME_STRIDE,
        "record_layout": ["f32 rotation quaternion (x,y,z,w)", "f32 position (x,y,z)"],
    }
    if runs:
        result["sample_records"] = [
            {
                "offset": runs[0]["start_offset"] + i * KEYFRAME_STRIDE,
                "quaternion": [round(x, 4) for x in struct.unpack_from("<4f", data, runs[0]["start_offset"] + i * KEYFRAME_STRIDE)],
                "position": [round(x, 4) for x in struct.unpack_from("<3f", data, runs[0]["start_offset"] + i * KEYFRAME_STRIDE + 16)],
            }
            for i in range(min(record_cap, runs[0]["record_count"]))
        ]
    return result
