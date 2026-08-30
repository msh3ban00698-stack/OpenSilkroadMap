"""Decoder for the JMXVBMS mesh format (VSRO-R 1.193).

Proven layout (common case, static + skinned meshes):

  offset  size  field
  ------  ----  -----
  0x00    12    magic b"JMXVBMS 0110"
  0x0C    4     u32 header_size (also the start of the vertex section)
  0x10    6*4   u32 section offsets [o0..o5]
  0x28    4     u32 optional 7th offset (0 when absent)
  0x30    4     u32 end_offset (== len-4 in the common case)
  0x34    4     u32 name0 length
  ...     N     name0 bytes (no trailing NUL)
  ...     N     name1 length + name1 bytes
  ...    4     u32 skinned_vertex_count (last 4 bytes of the header)
  --- sections ---
  [header_size .. o0]  vertex section: u32 vertex_count
                       + vc x vertex records
                       + optional lightmap path (52-byte meshes only)
  [o0 .. o1]           bone table: u32 bone_count + per-bone
                       [u32 name_len + name]; extra per-bone transform data
                       follows but its layout is NOT proven (reported verbatim)
  [o1 .. o2]           triangle list: u32 tri_count + tri_count x (3 x u16)
  [o2 .. o3]           unknown 4-byte field (reported verbatim)
  [o3 .. o4]           unknown 4-byte field (reported verbatim)
  [o4 .. o5]           AABB: 6 x f32 (minx,miny,minz,maxx,maxy,maxz)
  [o5 .. end_offset]   trailing (reported verbatim)

Vertex record formats (both proven by unit-normal and byte-span checks):

  44 B (static + skinned):
    f32 position xyz @0, f32 normal xyz @12, f32 uv @24,
    f32 blend_weight @32, u32 bone_index @36 (0xFFFFFFFF = unskinned),
    u32 flags @40 (0 unskinned / 2 skinned; 4 also observed)

  52 B (lightmap meshes):
    f32 position xyz @0, f32 normal xyz @12, f32 uv @24, f32 uv2 @32,
    3 x u32 @40..52 (0, 0xFFFFFFFF, 0 in all proven samples)
    then: u32 path_len + lightmap texture path (backslash .ddj), ending at o0.

Proven facts:
  * the u32 at header_size-4 equals the number of vertices whose bone index is
    not 0xFFFFFFFF (skinned count). Verified on 9/9 common samples.
  * vertex normals are unit length (used as a layout sanity check).
  * triangle indices are always < vertex_count.
  * vertex section byte span is exactly 4 + vc*44 (44-byte meshes) or
    4 + vc*52 + (4 + path_len) (52-byte lightmap meshes).

Reported, never invented: the 7th offset block (nature_tree has a trailing
vertex-animation block), per-bone transform bytes, and the s3/s4 unknown u32s.

Variants:
  * prefix-22 skinned meshes (166 files, e.g. avatar_m_2012_new_devil): the
    triangle section is a 22-byte prefix followed by a u16 index stream whose
    count is derived from the section span; the AABB section does not hold a
    valid box and is reported as aabb=None with the raw bytes.
  * 80-byte morph meshes (5 festival files): 3 x (pos+normal) + 2 tail floats.
  * 44-byte + trailing per-vertex morph block (ghost-captain, 1 file).
  * skinned-particle meshes (32 compound files, e.g. electus_w_xmas) have a
    different bone section and an unparseable index stream; parse_bms raises
    BmsFormatError for them instead of guessing.
  * files with no vertex-count field at header_size (3 part files, e.g.
    avatar_m_ghost_captain_part2) are reported as unproven vertex layout.
"""

from __future__ import annotations

import math
import struct

MAGIC = b"JMXVBMS 0110"
MAGIC_PREFIX = b"JMXVBMS "
MAGIC_VERSIONS = (b"0109", b"0110")
VERTEX_SIZE_44 = 44
VERTEX_SIZE_52 = 52
VERTEX_SIZE_80 = 80  # morph variant: 3 x (pos+normal) + 2 tail floats
MORPH_TRAIL = 24  # ghost-captain variant: 44-byte verts + [u32 vc][vc x 24B morph]
UNSKINNED = 0xFFFFFFFF
NORMAL_TOLERANCE = 0.01


class BmsFormatError(ValueError):
    pass


def _rd(data, offset, fmt):
    if offset + struct.calcsize(fmt) > len(data):
        raise BmsFormatError(f"read {fmt} at 0x{offset:x} exceeds file")
    return struct.unpack_from(fmt, data, offset)


def parse_bms_header(data: bytes) -> dict:
    if len(data) < 52:
        raise BmsFormatError("short header")
    if data[0:8] != b"JMXVBMS " or data[8:12] not in (b"0109", b"0110"):
        raise BmsFormatError(f"bad magic {data[:12]!r}")
    version = data[8:12].decode("ascii")
    header_size = _rd(data, 0x0C, "<I")[0]
    offsets = _rd(data, 0x10, "<6I")
    off7 = _rd(data, 0x28, "<I")[0]
    end_offset = _rd(data, 0x30, "<I")[0]
    if not (0 < header_size <= offsets[0] <= offsets[-1] <= end_offset <= len(data)):
        raise BmsFormatError("inconsistent header offsets")
    names, name_end = _parse_names(data, header_size)
    if name_end > header_size - 4:
        raise BmsFormatError("header_size does not accommodate names")
    skinned_count = _rd(data, header_size - 4, "<I")[0]
    return {
        "magic": data[0:12].decode("ascii"),
        "version": version,
        "header_size": header_size,
        "offsets": list(offsets),
        "off7": off7,
        "end_offset": end_offset,
        "names": names,
        "name_end": name_end,
        "skinned_vertex_count": skinned_count,
        "has_extra_block": end_offset + 4 != len(data),
    }


def _parse_names(data: bytes, bound: int) -> tuple[list[str], int]:
    names: list[str] = []
    o = 0x48
    for _ in range(8):
        l = _rd(data, o, "<I")[0]
        if not (0 < l < 80) or o + 4 + l > bound:
            break
        raw = data[o + 4:o + 4 + l]
        if not all(32 <= c < 127 for c in raw):
            break
        names.append(raw.decode("latin-1"))
        o += 4 + l
    return names, o


def vertex_count(data: bytes, header: dict) -> int:
    return _rd(data, header["header_size"], "<I")[0]


def _parse_lightmap_path(data: bytes, body_start: int, body_end: int) -> str | None:
    rem = body_end - body_start
    if rem < 4:
        return None
    plen = _rd(data, body_start, "<I")[0]
    if not (0 < plen <= rem - 4):
        return None
    raw = data[body_start + 4:body_start + 4 + plen]
    if not all(32 <= c < 127 for c in raw):
        return None
    if body_start + 4 + plen != body_end:
        return None
    return raw.decode("latin-1")


def detect_vertex_format(data: bytes, header: dict) -> dict:
    vc = vertex_count(data, header)
    body_start = header["header_size"] + 4
    body_end = header["offsets"][0]
    body = body_end - body_start
    info: dict = {"vertex_count": vc, "vertex_size": None,
                  "stride_exact": False, "lightmap_path": None,
                  "layout": None}
    if vc == 0:
        info["vertex_size"] = 0
        return info
    if body % vc == 0:
        stride = body // vc
        if stride in (VERTEX_SIZE_44, VERTEX_SIZE_52):
            info["vertex_size"] = stride
            info["stride_exact"] = True
            info["layout"] = "standard"
            return info
        if stride == VERTEX_SIZE_80:
            info["vertex_size"] = VERTEX_SIZE_80
            info["stride_exact"] = True
            info["layout"] = "morph80"
            return info
    rest_52 = body - vc * VERTEX_SIZE_52
    if rest_52 >= 0:
        path = _parse_lightmap_path(data, body_start + vc * VERTEX_SIZE_52, body_end)
        if path is not None:
            info["vertex_size"] = VERTEX_SIZE_52
            info["lightmap_path"] = path
            info["layout"] = "lightmap"
            return info
    rest_44 = body - vc * VERTEX_SIZE_44
    if rest_44 >= 0:
        rec = _parse_morph_trailing(data, body_start + vc * VERTEX_SIZE_44, body_end, vc)
        if rec is not None:
            info["vertex_size"] = VERTEX_SIZE_44
            info["layout"] = "morph_trailing"
            info["morph_records"] = rec
            return info
    raise BmsFormatError(
        f"unproven vertex layout vc={vc} body={body} (need 44, 52, or 52+path)")


def _parse_morph_trailing(data: bytes, body_start: int, body_end: int, vc: int) -> dict | None:
    """Ghost-captain variant: [u32 vc][vc x 24 B (pos+normal)] after 44-byte verts."""
    rem = body_end - body_start
    if rem != 4 + vc * MORPH_TRAIL:
        return None
    count = struct.unpack_from("<I", data, body_start)[0]
    if count != vc:
        return None
    for i in range(min(vc, 16)):
        if not _normal_ok(data, body_start + 4 + i * MORPH_TRAIL + 12):
            return None
    return {"record_stride": MORPH_TRAIL,
            "layout": ["f32 position xyz", "f32 normal xyz"]}


def _normal_ok(data: bytes, offset: int) -> bool:
    n = struct.unpack_from("<3f", data, offset)
    m = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
    return abs(m - 1.0) < NORMAL_TOLERANCE


def parse_vertices(data: bytes, header: dict, info: dict) -> tuple[list[dict], int]:
    """Return (vertices, non_unit_normals). Normals are a diagnostic only:
    five meshes in the corpus carry legitimately unnormalized normals."""
    vc = info["vertex_count"]
    if vc == 0:
        return [], 0
    vs = info["vertex_size"]
    start = header["header_size"] + 4
    verts: list[dict] = []
    non_unit_normals = 0
    for i in range(vc):
        o = start + i * vs
        if o + vs > header["offsets"][0]:
            raise BmsFormatError(f"vertex {i} record exceeds vertex section")
        rec = {
            "position": [round(x, 4) for x in struct.unpack_from("<3f", data, o)],
            "normal": [round(x, 4) for x in struct.unpack_from("<3f", data, o + 12)],
            "uv": [round(x, 4) for x in struct.unpack_from("<2f", data, o + 24)],
        }
        if vs == VERTEX_SIZE_44:
            w, bi, fl = struct.unpack_from("<fII", data, o + 32)
            rec["blend_weight"] = round(w, 4)
            rec["bone_index"] = bi
            rec["flags"] = fl
        elif vs == VERTEX_SIZE_80:
            rec["morph_targets"] = [
                [round(x, 4) for x in struct.unpack_from("<3f", data, o + 24)],
                [round(x, 4) for x in struct.unpack_from("<3f", data, o + 48)],
            ]
            rec["uv"] = [round(x, 4) for x in struct.unpack_from("<2f", data, o + 72)]
        else:
            rec["uv2"] = [round(x, 4) for x in struct.unpack_from("<2f", data, o + 32)]
            rec["tail_u32s"] = list(struct.unpack_from("<3I", data, o + 40))
        if not _normal_ok(data, o + 12):
            non_unit_normals += 1
        verts.append(rec)
    return verts, non_unit_normals


def parse_bone_table(data: bytes, header: dict) -> dict:
    o0 = header["offsets"][0]
    o1 = header["offsets"][1]
    if o1 - o0 < 4:
        raise BmsFormatError("bone section too short")
    count = _rd(data, o0, "<I")[0]
    if count > 4096:
        raise BmsFormatError(f"bone_count {count} implausible")
    names: list[str] = []
    o = o0 + 4
    for _ in range(count):
        nl = _rd(data, o, "<I")[0]
        if not (0 < nl < 120) or o + 4 + nl > o1:
            raise BmsFormatError("bone name length out of range")
        raw = data[o + 4:o + 4 + nl]
        try:
            names.append(raw.decode("ascii"))
        except UnicodeDecodeError:
            names.append(raw.decode("latin-1"))
        o += 4 + nl
    return {
        "bone_count": count,
        "bone_names": names,
        "names_end": o,
        "unparsed_bytes": o1 - o,
    }


def parse_triangles(data: bytes, header: dict, vc: int) -> dict:
    o1 = header["offsets"][1]
    o2 = header["offsets"][2]
    if o2 - o1 < 4:
        raise BmsFormatError("triangle section too short")
    count = _rd(data, o1, "<I")[0]
    span = o2 - o1 - 4
    if count * 6 == span:
        start = o1 + 4
        prefix = 0
    else:
        start, count, prefix = _parse_prefixed_triangles(data, o1, o2, vc)
    tris: list[tuple[int, int, int]] = []
    for i in range(count):
        a, b, c = struct.unpack_from("<3H", data, start + i * 6)
        if a >= vc or b >= vc or c >= vc:
            raise BmsFormatError(f"triangle {i} index out of range ({a},{b},{c})")
        tris.append((a, b, c))
    return {"triangle_count": count, "triangles": tris,
            "record_stride": 6, "section_index": 1,
            "prefix_bytes": prefix}


def _parse_prefixed_triangles(data: bytes, o1: int, o2: int, vc: int) -> tuple[int, int, int]:
    """Skinned-mesh variant: a 22-byte prefix then a u16 index stream.

    The triangle count is derived from the section span ((o2-o1-22)/6) and the
    full index stream is validated against the vertex count. Used by 166
    skinned item/mob meshes (e.g. avatar_m_2012_new_devil).
    """
    span = o2 - o1
    prefix = 22
    rem = span - prefix
    if rem <= 0 or rem % 6:
        raise BmsFormatError(
            f"triangle section has no clean count (span={span})")
    n = rem // 6
    for i in range(n):
        a, b, c = struct.unpack_from("<3H", data, o1 + prefix + i * 6)
        if max(a, b, c) >= vc:
            raise BmsFormatError(
                f"prefixed triangle {i} index out of range ({a},{b},{c})")
    return o1 + prefix, n, prefix


def parse_aabb(data: bytes, header: dict) -> list[float] | None:
    """Return the 24-byte AABB if it is a valid min<=max box, else None.

    None means the AABB is not proven for this mesh (e.g. the skinned
    prefix-22 variant stores something else in that section).
    """
    o4 = header["offsets"][4]
    o5 = header["offsets"][5]
    if o5 - o4 != 24:
        raise BmsFormatError(f"AABB section length {o5 - o4} != 24")
    vals = struct.unpack_from("<6f", data, o4)
    mn, mx = vals[:3], vals[3:]
    for lo, hi in zip(mn, mx):
        if lo > hi or not (lo == lo and hi == hi):
            return None
    return [round(x, 4) for x in vals]


def classify_bms(data: bytes) -> dict:
    """Lightweight corpus classifier: layout + triangle-section status.

    Faster than parse_bms (no vertex dicts built) and used by the corpus-wide
    classification test. Returns the layout and whether the mesh fully parses.
    """
    header = parse_bms_header(data)
    info = detect_vertex_format(data, header)
    layout = info.get("layout")
    if layout is None:
        layout = "empty" if info["vertex_size"] == 0 else "unknown"
    o1, o2 = header["offsets"][1], header["offsets"][2]
    span = o2 - o1
    count = struct.unpack_from("<I", data, o1)[0]
    triangle = "clean"
    if count * 6 != span - 4:
        if (span - 22) > 0 and (span - 22) % 6 == 0:
            n = (span - 22) // 6
            ok = True
            for i in range(n):
                if max(struct.unpack_from("<3H", data, o1 + 22 + i * 6)) >= info["vertex_count"]:
                    ok = False
                    break
            triangle = "prefix22" if ok else "unproven"
        else:
            triangle = "unproven"
    return {
        "layout": layout,
        "triangle_section": triangle,
        "parses": triangle != "unproven",
        "vertex_count": info["vertex_count"],
        "skinned_vertex_count": header["skinned_vertex_count"],
    }


def parse_bms(data: bytes, cap: int | None = None) -> dict:
    """Strict parse of a proven BMS mesh. Raises BmsFormatError otherwise."""
    header = parse_bms_header(data)
    info = detect_vertex_format(data, header)
    vertices, non_unit_normals = parse_vertices(data, header, info)
    bones = parse_bone_table(data, header)
    tris = parse_triangles(data, header, info["vertex_count"])
    aabb = parse_aabb(data, header)
    vertex_format = {
        "vertex_size": info["vertex_size"],
        "stride_exact": info["stride_exact"],
        "layout": info["layout"],
        "lightmap_path": info["lightmap_path"],
        "non_unit_normals": non_unit_normals,
    }
    if info.get("morph_records"):
        vertex_format["morph_records"] = info["morph_records"]
    result = {
        "header": header,
        "vertex_format": vertex_format,
        "vertices": vertices,
        "bones": bones,
        "triangles": tris,
        "parsed_end": header["end_offset"] + 4,
    }
    if aabb is not None:
        result["aabb"] = aabb
    else:
        o4, o5 = header["offsets"][4], header["offsets"][5]
        result["aabb"] = None
        result["aabb_section_raw"] = data[o4:o5].hex()
    if header["has_extra_block"]:
        result["extra_block_bytes"] = len(data) - (header["end_offset"] + 4)
    if cap is not None:
        result["triangles"]["triangles"] = tris["triangles"][:cap]
    return result
