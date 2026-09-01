#!/usr/bin/env python3
"""Verified VSRO-R 1.193 world/terrain parsers (read-only, deterministic).

Encodes the world pipeline formats VERIFIED against real Map.pk2 / Data.pk2
samples during Phase 10. Every offset below was validated on real extracted
files (see PHASE_10_REPORT.md for the verification matrix). Unknown aspects are
deliberately NOT guessed; they are marked UNKNOWN and raise/return None rather
than inventing data.

Verified formats:
  - Map.pk2 {Y}/{X}.m  : terrain height grid (magic JMXVMAPM1000)
      12-byte magic + 36 blocks (6x6) of 2575 bytes each; each block holds a
      17x17 height grid; height float at block offset 6 + (k*17+m)*7.
  - Map.pk2 {Y}/{X}.o2 : object instance overlays (magic JMXVMAPO1001)
      offset 16: series of [cnt:u16][cnt x 30-byte records]; record =
      nameI:u32, x:y:z:f32, theta:f32@+18, tail:u16@+28 (tx=tail&0xFF,
      tz=tail>>8).
  - Data.pk2 navmesh/object.ifo : text index of bsr paths (GBK, quoted).
  - Data.pk2 *.bsr (JMXVRES 0109)  -> material path + bms list.
  - Data.pk2 *.bmt (JMXVBMT 0102)  -> material-name -> ddj path.
  - Data.pk2 *.bms (JMXVBMS 0110)  -> static geometry (pos+uv verts, u16 idx).
  - Media.pk2 *.ddj                -> 20-byte header + DDS body.

Coordinate system (verified):
  - sector world size = 1920.0 units; terrain grid step = 20.0 units;
    97x97 grid per sector; 6x6 blocks of 17x17 within each .m.
  - world_x = (sx - ref_sx) * 1920 + local_x ; world_z likewise for y.
  - region pack (npcpos): region & 0xFF = x sector, region >> 8 = y sector.
  - minimap/{x}x{y}.ddj maps to sector (x, y), 256 px per sector.
"""

from __future__ import annotations

import re
import struct
from io import BytesIO

# --------------------------------------------------------------------------
# Constants (verified)
# --------------------------------------------------------------------------

M_MAGIC = b"JMXVMAPM1000"
O_MAGIC = b"JMXVMAPO1001"
T_MAGIC = b"JMXVMAPT1001"
BSR_MAGIC = b"JMXVRES 0109"
BMT_MAGIC = b"JMXVBMT 0102"
BMS_MAGIC = b"JMXVBMS 0110"
DDJ_HEADER = 20

M_BLOCKS = 36            # 6x6 blocks per sector
M_BLOCK_BYTES = 2575     # verified: 92,712 = 12 + 36 * 2575
M_BLOCK_GRID = 17        # heights per block side
M_GRID = 97              # 6*16 + 1 heights per sector side
M_HEIGHT_STRIDE = 7      # bytes per height record inside a block
M_HEIGHT_OFFSET = 6      # height float offset inside each block

SECTOR_WORLD = 1920.0    # world units per sector
GRID_STEP = 20.0         # world units between grid heights
MINIMAP_PX_PER_SECTOR = 256

STANDARD_M_SIZE = 12 + M_BLOCKS * M_BLOCK_BYTES  # 92,712

TILE2D_MAGIC = "JMXV2DTI1001"  # tile2d.ifo first line (not a byte magic)
T_MAGIC_BYTES = 12             # .t magic length
STANDARD_T_SIZE = 140436        # 12 + 140424 (verified across 4,987 files)
T_BODY_SIZE = STANDARD_T_SIZE - T_MAGIC_BYTES  # 140424
T_EMPTY_U16 = (0x0000, 0xFFFF)  # "no tile" markers observed in .t u16 cells

# .bmt material record layout (verified on Data.pk2 /compound/*.bmt):
#   magic + u32 count, then per entry: u32 name_len, padded name, 72 bytes of
#   material floats (18x f32), u32 ddj_len, padded ddj path, 7-byte tail.
BMT_MAGIC_LEN = 12
BMT_PROPS_BYTES = 0x48  # 72 = 18 floats (ambient/diffuse/specular/emissive RGBA + extras)
BMT_TAIL_BYTES = 7      # f32 (1.0) + 3 unknown bytes


class WorldFormatError(ValueError):
    """Raised when a blob does not match the verified format."""


def parse_terrain_m(blob):
    """Parse a Map.pk2 {Y}/{X}.m blob into a 97x97 float height grid.

    Returns grid[z][x] (row index z, column index x). Raises
    WorldFormatError when the blob does not match the verified layout.
    """
    if blob[:12] != M_MAGIC:
        raise WorldFormatError("not a .m terrain blob")
    body = len(blob) - 12
    if body != M_BLOCKS * M_BLOCK_BYTES:
        raise WorldFormatError(
            f"unexpected .m body size {body} (expected {M_BLOCKS * M_BLOCK_BYTES})"
        )
    grid = [[0.0] * M_GRID for _ in range(M_GRID)]
    for bi in range(M_BLOCKS):
        bx = bi % 6
        by = bi // 6
        for k in range(M_BLOCK_GRID):
            for m in range(M_BLOCK_GRID):
                off = 12 + bi * M_BLOCK_BYTES + M_HEIGHT_OFFSET + (k * M_BLOCK_GRID + m) * M_HEIGHT_STRIDE
                h = struct.unpack_from("<f", blob, off)[0]
                grid[by * 16 + k][bx * 16 + m] = h
    return grid


def parse_object_ifo(text):
    """Parse Data.pk2 navmesh/object.ifo text into a list of bsr paths."""
    out = []
    for ln in text.splitlines():
        i = ln.find('"')
        j = ln.rfind('"')
        if i >= 0 and j > i:
            out.append(ln[i + 1 : j].replace("\\", "/"))
    return out


def parse_o2(blob, object_index):
    """Parse a Map.pk2 {Y}/{X}.o2 blob into object instances.

    Returns a list of dicts: {nameI, bsr, x, y, z, theta, tx, tz, extra}.
    bsr is resolved via object_index when nameI is in range, else None.
    Delegates to the Phase 17 decoder (o2_decoder) whose proven layout walks
    [u16 count][count x 30-byte record] groups from offset 16; the variable
    zero header observed in Phase 15 is leading zero-count groups (padding)
    and does not change the parsed instances.
    """
    from o2_decoder import parse_o2 as _parse, O2FormatError
    try:
        placements = _parse(blob)
    except O2FormatError:
        raise WorldFormatError("not a .o2 blob")
    out = []
    for p in placements:
        bsr = object_index[p.nameI] if p.nameI < len(object_index) else None
        out.append({
            "nameI": p.nameI, "bsr": bsr,
            "x": p.x, "y": p.y, "z": p.z, "theta": p.theta,
            "tx": p.tx, "tz": p.tz,
            "extra": (p.unknown0, p.unknown1, p.unknown2, p.unknown3),
        })
    return out


def parse_bsr(bd):
    """Return (material_path, [bms_paths]) for a .bsr blob, or None."""
    if bd[:12] != BSR_MAGIC:
        return None
    num, num2, num3 = struct.unpack_from("<III", bd, 12)
    p = num + 8
    if p + 4 > len(bd):
        return None
    cnt = struct.unpack_from("<I", bd, p)[0]
    p += 4
    if p + cnt > len(bd):
        return None
    mpath = bd[p : p + cnt].decode("ascii", "replace").replace("\\", "/")
    bms = []
    p = num2
    if p + 4 <= len(bd):
        n = struct.unpack_from("<I", bd, p)[0]
        p += 4
        for _ in range(n):
            if p + 4 > len(bd):
                break
            sl = struct.unpack_from("<I", bd, p)[0]
            if sl < 20:
                if p + 8 > len(bd):
                    break
                sl = struct.unpack_from("<I", bd, p + 4)[0]
                p += 8
            else:
                p += 4
            if p + sl > len(bd):
                break
            bms.append(bd[p : p + sl].decode("ascii", "replace").replace("\\", "/"))
            p += sl
    return mpath, bms


def _strip_padded(raw):
    """Strip a null-padded .bmt string field down to its terminator."""
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


def parse_bmt_entries(mt):
    """Parse a .bmt blob into a list of structured material records.

    Each record is {"name", "ddj", "props", "tail"} where props are the 18
    decoded float32 material properties and tail is the raw 7-byte trailer.
    Raises WorldFormatError on a magic/size mismatch; stops (never overruns)
    on a truncated trailing entry.
    """
    if mt[:BMT_MAGIC_LEN] != BMT_MAGIC:
        raise WorldFormatError("not a .bmt blob")
    p = BMT_MAGIC_LEN
    if p + 4 > len(mt):
        raise WorldFormatError(".bmt too short for count")
    mc = struct.unpack_from("<I", mt, p)[0]
    p += 4
    out = []
    for _ in range(mc):
        if p + 4 > len(mt):
            break
        nn = struct.unpack_from("<I", mt, p)[0]
        p += 4
        if p + nn > len(mt):
            break
        name = _strip_padded(mt[p : p + nn])
        p += nn
        if p + BMT_PROPS_BYTES > len(mt):
            break
        props = list(struct.unpack_from("<%df" % (BMT_PROPS_BYTES // 4), mt, p))
        p += BMT_PROPS_BYTES
        if p + 4 > len(mt):
            break
        dn = struct.unpack_from("<I", mt, p)[0]
        p += 4
        if p + dn > len(mt):
            break
        ddj = _strip_padded(mt[p : p + dn])
        p += dn
        if p + BMT_TAIL_BYTES > len(mt):
            break
        tail = mt[p : p + BMT_TAIL_BYTES]
        p += BMT_TAIL_BYTES
        out.append({"name": name, "ddj": ddj, "props": props, "tail": tail})
    return out


def parse_bmt(mt):
    """Return {matname: ddjpath} for a .bmt blob (compatibility wrapper)."""
    return {r["name"]: r["ddj"] for r in parse_bmt_entries(mt)}


def parse_tile2d_ifo(text):
    """Parse Map.pk2 /tile2d.ifo into a list of tile index entries.

    Each entry: {"id", "flag", "class", "texture", "sectors"} where sectors is
    a list of (x, y) world-sector pairs named after the tile. Raises
    WorldFormatError when the header line/count is missing.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != TILE2D_MAGIC:
        raise WorldFormatError("not a tile2d.ifo index")
    out = []
    for ln in lines[2:]:
        m = re.match(r'^(\d+)\s+0x([0-9a-fA-F]+)\s+"([^"]*)"\s+"([^"]*)"(.*)$', ln)
        if not m:
            continue
        sectors = [(int(x), int(y)) for x, y in re.findall(r"\{(\d+),(\d+)\}", m.group(5))]
        out.append({
            "id": int(m.group(1)),
            "flag": int(m.group(2), 16),
            "class": m.group(3),
            "texture": m.group(4),
            "sectors": sectors,
        })
    return out


def tile2d_index(text):
    """Return {tile_id: entry} for tile2d.ifo (lookup form)."""
    return {e["id"]: e for e in parse_tile2d_ifo(text)}


def parse_t(blob, tile_index=None):
    """Validate a Map.pk2 {Y}/{X}.t blob and report proven structural facts.

    The .t grid layout is not yet proven (UNKNOWN); this decoder only asserts
    the verified header and size and, when a tile2d index is supplied, the set
    of tile IDs referenced by the blob's u16 cells. Raises WorldFormatError on
    a magic mismatch.
    """
    if blob[:T_MAGIC_BYTES] != T_MAGIC:
        raise WorldFormatError("not a .t blob")
    body = blob[T_MAGIC_BYTES:]
    info = {"magic": T_MAGIC.decode("ascii"), "size": len(blob), "body_size": len(body)}
    if tile_index is not None:
        ids = set()
        empty = 0
        for i in range(0, len(body) - 1, 2):
            v = struct.unpack_from("<H", body, i)[0]
            if v in tile_index:
                ids.add(v)
            elif v in T_EMPTY_U16:
                empty += 1
        info["tile_ids"] = sorted(ids)
        info["tile_count"] = len(ids)
        info["empty_cells"] = empty
    return info


def parse_bms_build(bd):
    """Parse a .bms blob for static geometry: (pos, uv) verts + u16 indices.

    Returns {"verts": [(x,y,z),(u,v)], "indices": [..], "mat_name": str} or None.
    """
    if bd[:12] != BMS_MAGIC:
        return None
    p = 12
    offsets = [struct.unpack_from("<I", bd, p + 4 * i)[0] for i in range(15)]
    off_verts, off_faces = offsets[0], offsets[2]
    vert_type = offsets[13]
    stride = 44 if vert_type == 0 else 52
    q = p + 60

    def read_str(qq):
        n = struct.unpack_from("<I", bd, qq)[0]
        return bd[qq + 4 : qq + 4 + n].decode("ascii", "replace"), qq + 4 + n

    _skeleton_name, q = read_str(q)
    mat_name, q = read_str(q)
    q = off_verts
    vc = struct.unpack_from("<I", bd, q)[0]
    q += 4
    verts = []
    for _ in range(vc):
        x, y, z = struct.unpack_from("<fff", bd, q)
        u, v = struct.unpack_from("<ff", bd, q + 24)
        verts.append(((x, y, z), (u, v)))
        q += stride
    q = off_faces
    fc = struct.unpack_from("<I", bd, q)[0]
    q += 4
    idx = []
    for _ in range(fc):
        idx.extend(struct.unpack_from("<HHH", bd, q))
        q += 6
    return {"verts": verts, "indices": idx, "mat_name": mat_name}


def ddj_to_dds(blob):
    """Return the embedded DDS body of a Media.pk2 .ddj blob."""
    if len(blob) < DDJ_HEADER:
        raise WorldFormatError("ddj too small")
    return BytesIO(blob[DDJ_HEADER:])


# --------------------------------------------------------------------------
# Coordinate system (verified formulas)
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Normalized Android height-grid container (".hg", VSHG v1)
#
# This is a documented derived output format (NOT a VSRO format). It packs a
# sector height grid for direct parsing on Android without any JSON/binary
# library. Layout (all little-endian):
#   offset 0  : 4 bytes  magic 'VSHG'
#   offset 4  : 2 bytes  version = 1
#   offset 6  : 2 bytes  size (heights per side, e.g. 97)
#   offset 8  : 4 bytes  step (world units between heights, e.g. 20.0)
#   offset 12 : 4*size^2 bytes  float32 heights, row-major [z][x]
# --------------------------------------------------------------------------

HG_MAGIC = b"VSHG"
HG_VERSION = 1
HG_HEADER = 12


def write_hg(path, grid, step=GRID_STEP):
    """Write a 2D height grid to the .hg container. Returns (size, min, max)."""
    size = len(grid)
    if any(len(row) != size for row in grid):
        raise WorldFormatError("grid must be square")
    flat = [h for row in grid for h in row]
    with open(path, "wb") as fh:
        fh.write(HG_MAGIC)
        fh.write(struct.pack("<H", HG_VERSION))
        fh.write(struct.pack("<H", size))
        fh.write(struct.pack("<f", step))
        fh.write(struct.pack("<%df" % (size * size), *flat))
    return size, min(flat), max(flat)


def read_hg(path):
    """Read a .hg container back into (grid, step)."""
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:4] != HG_MAGIC:
        raise WorldFormatError("not a .hg container")
    version, size = struct.unpack_from("<HH", blob, 4)
    if version != HG_VERSION:
        raise WorldFormatError(f"unsupported .hg version {version}")
    step = struct.unpack_from("<f", blob, 8)[0]
    need = HG_HEADER + size * size * 4
    if len(blob) != need:
        raise WorldFormatError(
            f".hg size mismatch {len(blob)} != {need}"
        )
    vals = struct.unpack_from("<%df" % (size * size), blob, HG_HEADER)
    grid = [list(vals[z * size:(z + 1) * size]) for z in range(size)]
    return grid, step


def unpack_region(region_code):
    """region & 0xFF = x sector, region >> 8 = y sector (verified npcpos)."""
    return region_code & 0xFF, region_code >> 8


def pack_region(sx, sy):
    return (sy << 8) | (sx & 0xFF)


def sector_world_origin(sx, sy, ref_sx, ref_sy):
    """World-space origin (in units) of sector (sx, sy) relative to a ref."""
    return (sx - ref_sx) * SECTOR_WORLD, (sy - ref_sy) * SECTOR_WORLD


def local_to_world(inst, ref_sx, ref_sy):
    """Object instance local coords -> world coords (verified formula)."""
    wx = inst["x"] + (inst["tx"] - ref_sx) * SECTOR_WORLD
    wz = inst["z"] + (inst["tz"] - ref_sy) * SECTOR_WORLD
    return wx, inst["y"], wz


def npc_to_world(x, z, region_code, ref_sx, ref_sy):
    """npcpos local coords -> world coords (verified formula)."""
    rx, ry = unpack_region(region_code)
    return x + (rx - ref_sx) * SECTOR_WORLD, z + (ry - ref_sy) * SECTOR_WORLD
