"""Generate the 3D runtime assets for one verified playable region (Region 32785).

Turns the extracted dungeon sources into a compact mesh + texture pair that the
runtime (map/src/game/region_loader.ts) loads with three.js:

    map/public/assets/img/silkroad/game/region32785/mesh.json  (mesh + UVs + spawn)
    map/public/assets/img/silkroad/game/region32785/floor.webp  (minimap composite)

Data sources (verified in Phase B, extracted by extract_region.py):
  - Data/Dungeon/wchina/fortress_dungeon.dof  (block transforms)
  - Data/prim/mesh/dun/.../*.bms              (real 3D floor geometry)
  - Media/minimap_d/fort_dungeon/fort_dungeon01_{127..129}x{126..128}.ddj

The floor mesh is genuine source geometry (vertices carry real heights); the
texture is the official dungeon minimap. Alignment uses the same sector mapping
as the verified 2D map: sector = (128 + x/1920, 127 + z/1920); the minimap tiles
cover sectors X 127..129, Y 126..128, so UV = ((x+1920)/5760, (z+1920)/5760).

Usage: python3 scripts/generate_region_mesh.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from generate_navmesh import parse_dungeon_dof, transform_obj_point  # noqa: E402

from PIL import Image

REGION = 32785
DATA_DIR = os.path.join("game_source", "Data")
DOF_REL = os.path.join("Dungeon", "wchina", "fortress_dungeon.dof")
MINIMAP_REL = os.path.join("game_source", "Media", "minimap_d", "fort_dungeon")

OUT_DIR = os.path.join("map", "public", "assets", "img", "silkroad", "game", f"region{REGION}")

TILE_XS = range(127, 130)
TILE_YS = range(126, 129)
TILE_SIZE = 256
SECTOR_WIDTH = 1920.0

# Dungeon minimap tiles cover sectors X in [127,130), Y in [126,129).
UV_SCALE = SECTOR_WIDTH * 3.0


def local_to_uv(wx, wz):
    """Dungeon local coords -> UV in the 3x3 minimap composite."""
    u = (wx + SECTOR_WIDTH) / UV_SCALE
    v = (wz + SECTOR_WIDTH) / UV_SCALE
    return max(0.0, min(1.0, u)), max(0.0, min(1.0, v))


def load_ddj_image(path):
    with open(path, "rb") as f:
        f.seek(20)  # skip 20-byte JMX header
        dds = f.read()
    from io import BytesIO

    return Image.open(BytesIO(dds)).convert("RGB")


def build_floor_texture():
    composite = Image.new("RGB", (TILE_SIZE * 3, TILE_SIZE * 3))
    for x in TILE_XS:
        for y in TILE_YS:
            path = os.path.join(MINIMAP_REL, f"fort_dungeon01_{x}x{y}.ddj")
            tile = load_ddj_image(path)
            composite.paste(tile, ((x - 127) * TILE_SIZE, (128 - y) * TILE_SIZE))
    out = os.path.join(OUT_DIR, "floor.webp")
    os.makedirs(OUT_DIR, exist_ok=True)
    composite.save(out, "WEBP", quality=85)
    return out


def point_in_triangle(px, pz, a, b, c):
    def sign(x1, z1, x2, z2, x3, z3):
        return (x1 - x3) * (z2 - z3) - (x2 - x3) * (z1 - z3)

    d1 = sign(px, pz, a[0], a[1], b[0], b[1])
    d2 = sign(px, pz, b[0], b[1], c[0], c[1])
    d3 = sign(px, pz, c[0], c[1], a[0], a[1])
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


def sample_height(vertices, indices, px, pz):
    """Interpolate mesh height at (px, pz); fall back to nearest vertex height."""
    best_h = None
    best_d = None
    for i in range(0, len(indices), 3):
        a = vertices[indices[i]]
        b = vertices[indices[i + 1]]
        c = vertices[indices[i + 2]]
        if point_in_triangle(px, pz, (a[0], a[2]), (b[0], b[2]), (c[0], c[2])):
            v0x, v0z = b[0] - a[0], b[2] - a[2]
            v1x, v1z = c[0] - a[0], c[2] - a[2]
            d00 = v0x * v0x + v0z * v0z
            d01 = v0x * v1x + v0z * v1z
            d11 = v1x * v1x + v1z * v1z
            denom = d00 * d11 - d01 * d01
            if denom == 0:
                return a[1]
            v2x, v2z = px - a[0], pz - a[2]
            w1 = (d11 * (v2x * v0x + v2z * v0z) - d01 * (v2x * v1x + v2z * v1z)) / denom
            w2 = (d00 * (v2x * v1x + v2z * v1z) - d01 * (v2x * v0x + v2z * v0z)) / denom
            w0 = 1.0 - w1 - w2
            return a[1] * w0 + b[1] * w1 + c[1] * w2
        for v in (a, b, c):
            d = (v[0] - px) ** 2 + (v[2] - pz) ** 2
            if best_d is None or d < best_d:
                best_d = d
                best_h = v[1]
    return best_h if best_h is not None else 0.0


def main():
    dof_path = os.path.join(DATA_DIR, *DOF_REL.split(os.sep))
    if not os.path.isfile(dof_path):
        sys.exit(f"Missing {dof_path}; run scripts/extract_region.py first")

    dof = parse_dungeon_dof(open(dof_path, "rb").read(), DATA_DIR)
    if not dof:
        sys.exit("Failed to parse DOF")

    verts = []
    idx = []
    bounds = {"minX": None, "minZ": None, "maxX": None, "maxZ": None, "minY": None, "maxY": None}
    block_names = []

    for block in dof["blocks"]:
        obj = block["obj_data"]
        if obj is None:
            continue
        lx, ly, lz = block["position"]
        yaw = block["yaw"]
        base = len(verts)
        for v in obj["vertices"]:
            wx, wz = transform_obj_point(v[0], v[2], yaw, lx, lz)
            wy = v[1] + ly
            u, vt = local_to_uv(wx, wz)
            verts.append((wx, wy, wz, u, vt))
            b = bounds
            b["minX"] = wx if b["minX"] is None else min(b["minX"], wx)
            b["maxX"] = wx if b["maxX"] is None else max(b["maxX"], wx)
            b["minZ"] = wz if b["minZ"] is None else min(b["minZ"], wz)
            b["maxZ"] = wz if b["maxZ"] is None else max(b["maxZ"], wz)
            b["minY"] = wy if b["minY"] is None else min(b["minY"], wy)
            b["maxY"] = wy if b["maxY"] is None else max(b["maxY"], wy)
        for c in obj["cells"]:
            idx.append(base + c[0])
            idx.append(base + c[1])
            idx.append(base + c[2])
        block_names.append({"id": block["id"], "name": block["name"], "floor": block["floor_index"]})

    # Flatten
    flat = []
    for v in verts:
        flat.extend(v)

    # Spawn: verified "Dungeon Exit" NPC position inside region 32785.
    spawn = {"x": 1134.79, "z": -864.29}
    spawn["y"] = sample_height(verts, idx, spawn["x"], spawn["z"])

    mesh = {
        "region": REGION,
        "name": "Cave of Meditation",
        "source": {
            "dof": DOF_REL.replace(os.sep, "/"),
            "minimap": "Media/minimap_d/fort_dungeon/fort_dungeon01_{127..129}x{126..128}.ddj",
        },
        "vertexCount": len(verts),
        "indexCount": len(idx),
        "vertices": [round(v, 3) for v in flat],
        "indices": idx,
        "bounds": bounds,
        "spawn": spawn,
        "blocks": block_names,
    }

    floor_path = build_floor_texture()
    mesh_path = os.path.join(OUT_DIR, "mesh.json")
    with open(mesh_path, "w") as f:
        json.dump(mesh, f)

    print(f"vertices={len(verts)} triangles={len(idx) // 3} blocks={len(block_names)}")
    print(f"bounds X {bounds['minX']:.1f}..{bounds['maxX']:.1f}  Z {bounds['minZ']:.1f}..{bounds['maxZ']:.1f}  "
          f"H {bounds['minY']:.2f}..{bounds['maxY']:.2f}")
    print(f"spawn ({spawn['x']}, {spawn['y']:.2f}, {spawn['z']})")
    print(f"texture -> {floor_path}")
    print(f"mesh    -> {mesh_path}")


if __name__ == "__main__":
    main()
