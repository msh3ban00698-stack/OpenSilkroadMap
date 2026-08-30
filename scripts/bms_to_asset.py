"""Convert proven BMS meshes to the compact Android runtime ".msh" asset.

Binary container "MSH1" (little-endian):

    offset  size  field
    0       4     magic "MSH1"
    4       1     version = 1
    5       1     layout    (0 = standard 44-byte, 1 = lightmap 52-byte)
    6       2     flags u16 (bit0 = has uv2)
    8       4     u32 vertex_count   (all real vertices)
    12      4     u32 triangle_count
    16      4     u32 non_static_vertices (vertices with flags != 0; informative)
    20      2     u16 texture_index  (index into manifest texture list)
    22      2     u16 reserved
    24      n*s   vertex records:
                     layout 0: position(3f) normal(3f) uv(2f)         = 32 B
                     layout 1: position(3f) normal(3f) uv(2f) uv2(2f) = 40 B
    24+n*s  t*6   u16 triangle indices (triangle_count * 3)

ALL real BMS vertices are preserved (Phase 17 renders real geometry; dropping
flags==2 vertices was shown to corrupt static tree canopies). The
non_static_vertices count documents how many vertices carry flags != 0
(e.g. wind-sway leaves); skinning of NPC meshes is out of Phase 17 scope and
such meshes are not built as render assets.
"""

from __future__ import annotations

import struct

from bms_decoder import (
    BmsFormatError,
    classify_bms,
    parse_bms,
)

MSH_MAGIC = b"MSH1"
MSH_VERSION = 1
MSH_VERSION_SKINNED = 2
LAYOUT_STD44 = 0
LAYOUT_LIGHTMAP = 1


class MshFormatError(ValueError):
    pass


def _raw_vertex(data: bytes, start: int, vs: int, layout: int) -> dict:
    pos = list(struct.unpack_from("<3f", data, start))
    nrm = list(struct.unpack_from("<3f", data, start + 12))
    uv = list(struct.unpack_from("<2f", data, start + 24))
    rec = {"position": pos, "normal": nrm, "uv": uv}
    if layout == LAYOUT_LIGHTMAP:
        rec["uv2"] = list(struct.unpack_from("<2f", data, start + 32))
    return rec


def bms_to_msh(bms_bytes: bytes, texture_index: int = 0) -> tuple[bytes, dict]:
    """Convert one BMS mesh blob to (MSH1 bytes, provenance dict)."""
    try:
        parsed = parse_bms(bms_bytes)
    except BmsFormatError as exc:
        raise MshFormatError(f"BMS parse failed: {exc}") from exc

    cls = classify_bms(bms_bytes)
    layout_name = cls.get("layout")
    layout = {"standard": LAYOUT_STD44, "lightmap": LAYOUT_LIGHTMAP}.get(layout_name)
    if layout is None:
        raise MshFormatError(f"unsupported vertex layout for asset: {layout_name!r}")

    vf = parsed["vertex_format"]
    vs = vf["vertex_size"]
    vstart = parsed["header"]["header_size"] + 4
    vcount = cls["vertex_count"]
    bones = parsed["bones"]
    lightmap_path = vf.get("lightmap_path")

    # Keep every real vertex; count non-static (flags != 0) for provenance only.
    vertices = [_raw_vertex(bms_bytes, vstart + i * vs, vs, layout) for i in range(vcount)]
    non_static = 0
    if layout == LAYOUT_STD44:
        for i in range(vcount):
            o = vstart + i * vs
            if struct.unpack_from("<I", bms_bytes, o + 40)[0] != 0:
                non_static += 1

    tris: list[tuple[int, int, int]] = list(parsed["triangles"]["triangles"])

    has_uv2 = 1 if layout == LAYOUT_LIGHTMAP else 0
    blob = bytearray(MSH_MAGIC)
    blob += struct.pack(
        "<BBHIIIHH",
        MSH_VERSION, layout, has_uv2,
        len(vertices), len(tris), non_static,
        texture_index, 0,
    )
    for v in vertices:
        blob += struct.pack("<8f", *v["position"], *v["normal"], *v["uv"])
        if has_uv2:
            blob += struct.pack("<2f", *v["uv2"])
    for a, b, c in tris:
        blob += struct.pack("<3H", a, b, c)

    provenance = {
        "source": {
            "vertex_count": vcount,
            "layout": layout_name,
            "bone_count": bones["bone_count"],
            "lightmap_path": lightmap_path,
            "aabb": parsed.get("aabb"),
        },
        "asset": {
            "vertex_count": len(vertices),
            "triangle_count": len(tris),
            "non_static_vertices": non_static,
        },
    }
    return bytes(blob), provenance


def bms_to_msh_skinned(bms_bytes: bytes, texture_index: int = 0) -> tuple[bytes, dict]:
    """Convert one skinned BMS mesh to an MSH v2 (skinned) asset.

    MSH v2 adds to the v1 layout, after the vertex records:
      skin records:  n * 6 B   [u8 b1][u16 w1][u8 b2][u16 w2]   (has_skin bit1)
      triangle list: t * 6 B
      bone table:    u32 bone_count + count * (u32 len + ascii name)
    The skin block is REQUIRED (raises MshFormatError when absent).
    """
    try:
        parsed = parse_bms(bms_bytes)
    except BmsFormatError as exc:
        raise MshFormatError(f"BMS parse failed: {exc}") from exc
    if parsed["skin"] is None:
        raise MshFormatError("skinned MSH requires a skin block in the BMS")

    cls = classify_bms(bms_bytes)
    layout = {"standard": LAYOUT_STD44, "lightmap": LAYOUT_LIGHTMAP}.get(cls.get("layout"))
    if layout is None:
        raise MshFormatError(f"unsupported vertex layout: {cls.get('layout')!r}")

    vf = parsed["vertex_format"]
    vs = vf["vertex_size"]
    vstart = parsed["header"]["header_size"] + 4
    vcount = cls["vertex_count"]
    has_uv2 = 1 if layout == LAYOUT_LIGHTMAP else 0
    non_static = parsed["header"]["skinned_vertex_count"]

    vertices = []
    for i in range(vcount):
        o = vstart + i * vs
        pos = list(struct.unpack_from("<3f", bms_bytes, o))
        nrm = list(struct.unpack_from("<3f", bms_bytes, o + 12))
        uv = list(struct.unpack_from("<2f", bms_bytes, o + 24))
        rec = {"position": pos, "normal": nrm, "uv": uv}
        if has_uv2:
            rec["uv2"] = list(struct.unpack_from("<2f", bms_bytes, o + 32))
        vertices.append(rec)

    skin_records = [
        (r["bone1"], r["weight1"], r["bone2"], r["weight2"])
        for r in parsed["skin"]["records"]
    ]
    tris = list(parsed["triangles"]["triangles"])
    bone_names = parsed["bones"]["bone_names"]

    flags = has_uv2 | 2  # bit1 = has_skin
    blob = bytearray(MSH_MAGIC)
    blob += struct.pack(
        "<BBHIIIHH",
        MSH_VERSION_SKINNED, layout, flags,
        vcount, len(tris), non_static,
        texture_index, 0,
    )
    for v in vertices:
        blob += struct.pack("<8f", *v["position"], *v["normal"], *v["uv"])
        if has_uv2:
            blob += struct.pack("<2f", *v["uv2"])
    for b1, w1, b2, w2 in skin_records:
        blob += struct.pack("<BHBH", b1, w1, b2, w2)
    for a, b, c in tris:
        blob += struct.pack("<3H", a, b, c)
    blob += struct.pack("<I", len(bone_names))
    for n in bone_names:
        nb = n.encode("ascii")
        blob += struct.pack("<I", len(nb)) + nb

    provenance = {
        "source": {
            "vertex_count": vcount,
            "layout": cls.get("layout"),
            "bone_count": len(bone_names),
            "skinned_vertex_count": non_static,
            "two_influence": parsed["skin"]["two_influence"],
            "aabb": parsed.get("aabb"),
        },
        "asset": {
            "msh_version": MSH_VERSION_SKINNED,
            "vertex_count": len(vertices),
            "triangle_count": len(tris),
            "skin_records": len(skin_records),
            "bone_count": len(bone_names),
        },
    }
    return bytes(blob), provenance


def read_msh(blob: bytes) -> dict:
    """Parse MSH1 bytes back into a dict (round-trip / Android parity)."""
    if len(blob) < 24 or blob[:4] != MSH_MAGIC:
        raise MshFormatError("not an MSH1 blob")
    version, layout, flags, vcount, tcount, non_static, tex_index, _rsv = (
        struct.unpack_from("<BBHIIIHH", blob, 4)
    )
    if version not in (MSH_VERSION, MSH_VERSION_SKINNED):
        raise MshFormatError(f"unsupported MSH version {version}")
    vs = 32 if layout == LAYOUT_STD44 else 40
    has_skin = bool(flags & 2)
    o = 24 + vcount * vs
    skin = []
    if has_skin:
        if version != MSH_VERSION_SKINNED:
            raise MshFormatError("skin flag on v1 blob")
        for _ in range(vcount):
            b1, w1, b2, w2 = struct.unpack_from("<BHBH", blob, o)
            o += 6
            skin.append({"bone1": b1, "weight1": w1,
                         "bone2": b2, "weight2": w2})
    vertices = []
    o = 24
    for _ in range(vcount):
        v = {
            "position": [round(x, 4) for x in struct.unpack_from("<3f", blob, o)],
            "normal": [round(x, 4) for x in struct.unpack_from("<3f", blob, o + 12)],
            "uv": [round(x, 4) for x in struct.unpack_from("<2f", blob, o + 24)],
        }
        o += 32
        if flags & 1:
            v["uv2"] = [round(x, 4) for x in struct.unpack_from("<2f", blob, o)]
            o += 8
        vertices.append(v)
    if has_skin:
        o = 24 + vcount * vs + vcount * 6
    triangles = []
    for _ in range(tcount):
        a, b, c = struct.unpack_from("<3H", blob, o)
        o += 6
        triangles.append((a, b, c))
    bone_names = []
    if has_skin:
        (bc,) = struct.unpack_from("<I", blob, o)
        o += 4
        for _ in range(bc):
            (nl,) = struct.unpack_from("<I", blob, o)
            o += 4
            bone_names.append(blob[o:o + nl].decode("ascii"))
            o += nl
    if o != len(blob):
        raise MshFormatError(f"MSH size mismatch {len(blob)} != {o}")
    return {
        "version": version,
        "layout": layout,
        "has_uv2": bool(flags & 1),
        "has_skin": has_skin,
        "vertex_count": vcount,
        "triangle_count": tcount,
        "non_static_vertices": non_static,
        "texture_index": tex_index,
        "vertices": vertices,
        "skin": skin if has_skin else None,
        "bone_names": bone_names if has_skin else None,
        "triangles": triangles,
    }
