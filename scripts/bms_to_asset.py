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


def read_msh(blob: bytes) -> dict:
    """Parse MSH1 bytes back into a dict (round-trip / Android parity)."""
    if len(blob) < 24 or blob[:4] != MSH_MAGIC:
        raise MshFormatError("not an MSH1 blob")
    version, layout, flags, vcount, tcount, non_static, tex_index, _rsv = (
        struct.unpack_from("<BBHIIIHH", blob, 4)
    )
    if version != MSH_VERSION:
        raise MshFormatError(f"unsupported MSH version {version}")
    vs = 32 if layout == LAYOUT_STD44 else 40
    need = 24 + vcount * vs + tcount * 6
    if len(blob) != need:
        raise MshFormatError(f"MSH size mismatch {len(blob)} != {need}")
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
    triangles = []
    for _ in range(tcount):
        a, b, c = struct.unpack_from("<3H", blob, o)
        o += 6
        triangles.append((a, b, c))
    return {
        "version": version,
        "layout": layout,
        "has_uv2": bool(flags & 1),
        "vertex_count": vcount,
        "triangle_count": tcount,
        "non_static_vertices": non_static,
        "texture_index": tex_index,
        "vertices": vertices,
        "triangles": triangles,
    }
