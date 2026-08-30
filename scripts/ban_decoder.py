"""Full decoder for the JMXVBAN animation format (VSRO-R 1.193).

The complete layout below is PROVEN from three real archive files (see
FORMAT_RESEARCH.md for evidence): ferry 171 B, royalsoldier 29,686 B,
venefica 926,897 B -- each parses exactly to the last byte.

  offset    size      field
  ------    ----      -----
  0x00      8         magic b"JMXVBAN "
  0x08      4         version b"0102"
  0x0C      8         reserved (zeros, UNKNOWN semantics)
  0x14      4         u32 animation-name length
  0x18      N         animation name (no trailing NUL; body follows at name_end)
  --- body (starts at name_end) ---
  0        4         u32 duration_ms            (8000 / 2966 / 6000)
  4        4         u32 frame_rate             (30 in all proven samples)
  8        4         u32 UNKNOWN                (1 / 0 / 1)
  12       4         u32 keyframes_per_bone (kpb)  (3 / 27 / 181)
  16       kpb*4     u32 timestamp_ms each      (ascending; first 0, last=duration)
  +4       4         u32 bone_count             (1 / 38 / 182)
  then bone_count x:
    4       u32   bone name length
    N       bone name bytes (no trailing NUL)
    4       u32   per-bone keyframe count (equals kpb in all proven samples)
    kpb*28  keyframe records (28 B = 4 x f32 rotation quaternion + 3 x f32 position)

The 0x0C reserved block and the body u32 at offset 8 remain UNKNOWN and are
reported verbatim, never asserted.
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
        "body_start": name_end,
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


def parse_ban(data: bytes, keyframe_cap: int = 4) -> dict:
    """Parse the complete proven BAN layout. Reports, never invents.

    Verifies the parse by asserting the bone records end exactly at the file
    length; any deviation raises BanFormatError (layout not proven for that file).
    """
    header = parse_ban_header(data)
    body = header["body_start"]
    if body + 20 > len(data):
        raise BanFormatError("body shorter than 5-field header")
    duration, frame_rate, unknown, kpb = struct.unpack_from("<4I", data, body)
    ts_off = body + 16
    if ts_off + kpb * 4 > len(data):
        raise BanFormatError("timestamp table exceeds file")
    timestamps = list(struct.unpack_from(f"<{kpb}I", data, ts_off))
    bones_off = ts_off + kpb * 4
    if bones_off + 4 > len(data):
        raise BanFormatError("no bone count")
    bone_count = struct.unpack_from("<I", data, bones_off)[0]

    bones: list[dict] = []
    o = bones_off + 4
    sample_keyframes = []
    for _ in range(bone_count):
        if o + 4 > len(data):
            raise BanFormatError("bone name length out of range")
        nl = struct.unpack_from("<I", data, o)[0]
        name_bytes = data[o + 4:o + 4 + nl]
        if o + 4 + nl + 4 > len(data):
            raise BanFormatError("bone name exceeds file")
        try:
            name = name_bytes.decode("ascii")
        except UnicodeDecodeError:
            name = name_bytes.decode("latin-1")
        o += 4 + nl
        perbone = struct.unpack_from("<I", data, o)[0]
        o += 4
        kf_start = o
        if o + perbone * KEYFRAME_STRIDE > len(data):
            raise BanFormatError("keyframe block exceeds file")
        bones.append({"name": name, "name_length": nl, "keyframes": perbone,
                      "keyframe_start": kf_start})
        if not sample_keyframes and perbone:
            for i in range(min(keyframe_cap, perbone)):
                off = kf_start + i * KEYFRAME_STRIDE
                q = struct.unpack_from("<4f", data, off)
                p = struct.unpack_from("<3f", data, off + 16)
                sample_keyframes.append({
                    "bone": name,
                    "offset": off,
                    "quaternion": [round(x, 4) for x in q],
                    "position": [round(x, 4) for x in p],
                })
        o += perbone * KEYFRAME_STRIDE

    if o != len(data):
        raise BanFormatError(f"parse consumed {o} bytes but file is {len(data)}")

    ts_sorted = all(a < b for a, b in zip(timestamps, timestamps[1:]))
    return {
        "header": header,
        "duration_ms": duration,
        "frame_rate": frame_rate,
        "unknown_u32": unknown,
        "keyframes_per_bone": kpb,
        "timestamps": timestamps,
        "timestamps_ascending": ts_sorted,
        "bone_count": bone_count,
        "bones": bones,
        "sample_keyframes": sample_keyframes,
        "record_byte_size": KEYFRAME_STRIDE,
        "parsed_end": o,
    }


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
