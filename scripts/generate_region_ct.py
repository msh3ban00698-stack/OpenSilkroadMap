#!/usr/bin/env python3
"""Generate runtime assets for the real Constantinople world (region 1).

Reads the extracted CT sources (scripts/extract_ct.py -> game_source/CT) and
emits, under map/public/assets/img/silkroad/game/region1/:

  mesh.json         decimated terrain mesh (vertices + UVs + bounds + spawn +
                    height grid for terrain-following)
  floor.webp        6x6 minimap composite (1536x1536)
  buildings.json    manifest: atlas pages, geometry slices, building instances,
                    npc/mob models + placements
  buildings.bgeo    packed binary geometry (f32 x/y/z/u/v per vertex + u16 idx)
  atlas<N>.webp     texture atlas page(s)

All geometry is real source data:
  - terrain: 36 x 36 block-grid heights from Map.pk2 {Y}/{X}.m
  - buildings: .o2 object placements -> object.ifo bsr -> bms geometry + bmt ddj
  - npcs/mobs: npcpos.txt placements -> characterdata model bsr -> bms + bmt ddj

Usage: python3 scripts/generate_region_ct.py
"""

import json
import os
import struct
import sys

from io import BytesIO

from PIL import Image

CT = os.path.join(os.path.dirname(__file__), "..", "game_source", "CT")
OUT_DIR = os.path.join("map", "public", "assets", "img", "silkroad", "game", "region1")

SECTORS = [(x, y) for y in range(103, 109) for x in range(76, 82)]
SX, SY = 76, 103
SECTOR_W = 1920.0
WORLD_W = SECTOR_W * 6.0  # 11520

STRIDE = 2
GRID = 97 * 6 - 5  # 577
DGRID = (GRID - 1) // STRIDE + 1  # 289
STEP = 20.0 * STRIDE  # 40

PAGE = 4096
CELL = 64
PAGE_CELLS = PAGE // CELL  # 64


class ShelfPage:
    """Cell-grid shelf packer. Textures snap to a CELL grid; guaranteed correct."""
    def __init__(self):
        self.rows = []  # {"y": cells, "h": cells, "used": cells}
        self.next_y = 0
        self.used_cells = 0

    def clone(self):
        p = ShelfPage()
        p.rows = [dict(r) for r in self.rows]
        p.next_y = self.next_y
        p.used_cells = self.used_cells
        return p

    def place(self, wc, hc):
        for row in self.rows:
            if row["h"] >= hc and PAGE_CELLS - row["used"] >= wc:
                x = row["used"]
                row["used"] += wc
                self.used_cells += wc * hc
                return x * CELL, row["y"] * CELL, wc * CELL, hc * CELL
        y = self.next_y
        if y + hc > PAGE_CELLS:
            return None
        self.rows.append({"y": y, "h": hc, "used": wc})
        self.next_y = y + hc
        self.used_cells += wc * hc
        return 0, y * CELL, wc * CELL, hc * CELL

    def can_place(self, items):
        """items: list of (wc, hc). Returns True if all fit without mutation."""
        p = self.clone()
        for wc, hc in items:
            if p.place(wc, hc) is None:
                return False
        return True


class Atlas:
    """Texture atlas: assigns each geometry's textures to page(s) and records UVs."""

    def __init__(self):
        self.tex_list = {}   # key -> {"img": Image, "size": (w, h)}
        self.rects = {}      # (page, key) -> (x, y, w, h) in pixels
        self.pages = []      # ShelfPage per atlas page
        self.page_texs = []  # set of keys already placed per page
        self.geom_tex_page = []  # per geom: {key: page}
        self.page_count = 0
        self.seen = set()

    def tex_key(self, path):
        k = path.replace("\\", "/").lower()
        self.seen.add(k)
        return k

    def load_sizes(self):
        for key in self.seen:
            img = load_ddj_image(resolve_rel(key))
            self.tex_list[key] = {"img": img, "size": img.size}

    def assign_pages(self, geom_tex_keys):
        self.geom_tex_page = []
        for keys in geom_tex_keys:
            items = []
            for k in keys:
                w, h = self.tex_list[self.tex_key(k)]["size"]
                items.append((k, (w + CELL - 1) // CELL, (h + CELL - 1) // CELL))
            placed_pg = None
            for cand in range(len(self.pages)):
                missing = [(wc, hc) for k, wc, hc in items if k not in self.page_texs[cand]]
                if not missing or self.pages[cand].can_place(missing):
                    placed_pg = cand
                    break
            if placed_pg is None:
                fresh = ShelfPage()
                if fresh.can_place([(wc, hc) for _k, wc, hc in items]):
                    self.pages.append(fresh)
                    self.page_texs.append(set())
                    placed_pg = len(self.pages) - 1
            page_map = {}
            for k, wc, hc in sorted(items, key=lambda it: -it[2]):
                pg = placed_pg
                if pg is None:
                    for cand in range(len(self.pages)):
                        if k not in self.page_texs[cand] and self.pages[cand].can_place([(wc, hc)]):
                            pg = cand
                            break
                    if pg is None:
                        self.pages.append(ShelfPage())
                        self.page_texs.append(set())
                        pg = len(self.pages) - 1
                if k not in self.page_texs[pg]:
                    r = self.pages[pg].place(wc, hc)
                    if r is None:
                        raise RuntimeError(f"texture too large for atlas: {k} {wc*CELL}x{hc*CELL}")
                    self.rects[(pg, self.tex_key(k))] = r
                    self.page_texs[pg].add(k)
                page_map[k] = pg
            self.geom_tex_page.append(page_map)
        self.page_count = len(self.pages)

    def pack(self):
        pass

    def uv(self, geom_gi, path, u, v):
        """Map a mesh UV into atlas UV (GL-style v=0 bottom, flipY-compatible)."""
        pg = self.geom_tex_page[geom_gi][path]
        x, y, w, h = self.rects[(pg, self.tex_key(path))]
        return (x + u * w) / PAGE, 1.0 - (y + (1 - v) * h) / PAGE

    def write_pages(self):
        out = []
        for pg in range(self.page_count):
            img = Image.new("RGBA", (PAGE, PAGE), (40, 40, 46, 255))
            for (p, key), (x, y, w, h) in self.rects.items():
                if p == pg:
                    img.paste(self.tex_list[key]["img"], (x, y))
            fn = os.path.join(OUT_DIR, f"atlas{pg}.webp")
            img.save(fn, "WEBP", quality=82, method=4)
            out.append(f"atlas{pg}.webp")
        return out


# --------------------------------------------------------------------------
# Geometry / texture parsers (bsr -> bms -> bmt -> ddj)
# --------------------------------------------------------------------------

DATA_INDEX = None


def build_data_index():
    global DATA_INDEX
    if DATA_INDEX is not None:
        return
    DATA_INDEX = {}
    base = os.path.join(CT, "Data")
    for root, _, files in os.walk(base):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), base).replace("\\", "/")
            DATA_INDEX.setdefault(rel.lower(), rel)
            if rel.lower().startswith("res/"):
                DATA_INDEX.setdefault(rel.lower()[4:], rel)


def resolve_rel(rel):
    build_data_index()
    rel = rel.replace("\\", "/")
    if rel.startswith("/"):
        rel = rel.lstrip("/")
    if rel in DATA_INDEX:
        return os.path.join(CT, "Data", DATA_INDEX[rel])
    low = rel.lower()
    if low in DATA_INDEX:
        return os.path.join(CT, "Data", DATA_INDEX[low])
    return None


def data_read(rel):
    p = resolve_rel(rel)
    if p is None or not os.path.isfile(p):
        return None
    with open(p, "rb") as f:
        return f.read()


def parse_bmt(mt):
    """Return {matname: ddjpath} for a .bmt blob."""
    if mt[:12] != b"JMXVBMT 0102":
        return {}
    p = 12
    if p + 4 > len(mt):
        return {}
    mc = struct.unpack_from("<I", mt, p)[0]
    p += 4
    out = {}
    for _ in range(mc):
        if p + 4 > len(mt):
            break
        nn = struct.unpack_from("<I", mt, p)[0]
        p += 4
        if p + nn > len(mt):
            break
        name = mt[p : p + nn].decode("ascii", "replace")
        p += nn + 0x48
        if p + 4 > len(mt):
            break
        dn = struct.unpack_from("<I", mt, p)[0]
        p += 4
        if p + dn > len(mt):
            break
        ddj = mt[p : p + dn].decode("ascii", "replace")
        p += dn + 7
        out[name] = ddj
    return out


def parse_bsr(bd):
    """Return (material_path, [bms_paths]) for a .bsr blob, or None."""
    if bd[:12] != b"JMXVRES 0109":
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


def parse_bms_build(bd):
    """Parse a .bms blob for static geometry: (pos, uv) verts + u16 triangle indices."""
    if bd[:12] != b"JMXVBMS 0110":
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


def load_ddj_image(path):
    with open(path, "rb") as f:
        f.seek(20)
        dds = f.read()
    return Image.open(BytesIO(dds)).convert("RGBA")


def collect_geom_raw(bsr):
    """Resolve bsr -> parts of (ddj_path, [(pos, uv)], indices). Returns None if unusable."""
    bd = data_read(bsr)
    if bd is None:
        return None
    r = parse_bsr(bd)
    if r is None:
        return None
    mpath, bms = r
    mat = {}
    if mpath:
        mt = data_read(mpath)
        if mt is not None:
            mat = parse_bmt(mt)
            base = mpath.rsplit("/", 1)[0]
            resolved = {}
            for name, ddj in mat.items():
                ddj = ddj.replace("\\", "/")
                if ddj.startswith("/"):
                    ddj = ddj.lstrip("/")
                tp = ddj if "/" in ddj else base + "/" + ddj
                if resolve_rel(tp) is not None:
                    resolved[name] = tp
                elif "/" not in ddj and resolve_rel(base + "/" + ddj) is not None:
                    resolved[name] = base + "/" + ddj
            mat = resolved
    parts = []
    for b in bms:
        blob = data_read(b)
        if blob is None:
            continue
        gm = parse_bms_build(blob)
        if gm is None or not gm["verts"] or not gm["indices"]:
            continue
        ddj = mat.get(gm["mat_name"])
        if ddj is None:
            for name in mat:
                if name:
                    ddj = mat[name]
                    break
        if ddj is None:
            continue
        parts.append((ddj, gm["verts"], gm["indices"]))
    if not parts:
        return None
    return {"parts": parts}


# --------------------------------------------------------------------------
# Terrain / floor
# --------------------------------------------------------------------------

def load_m_grid(sx, sy):
    path = os.path.join(CT, "Map", str(sy), f"{sx}.m")
    with open(path, "rb") as f:
        d = f.read()
    grid = [[0.0] * 97 for _ in range(97)]
    for bi in range(36):
        bx = bi % 6
        by = bi // 6
        for k in range(17):
            for m in range(17):
                off = 12 + bi * 2575 + 6 + (k * 17 + m) * 7
                h = struct.unpack_from("<f", d, off)[0]
                grid[by * 16 + k][bx * 16 + m] = h
    return grid


def global_grid_height(grids, gxi, gzi):
    si = gxi // 96
    if si >= 6:
        si = 5
    lx = gxi - si * 96
    ti = gzi // 96
    if ti >= 6:
        ti = 5
    lz = gzi - ti * 96
    return grids[(SX + si, SY + ti)][lz][lx]


def sample_grid_height(grids, wx, wz):
    gx = min(max(wx / 20.0, 0.0), GRID - 1)
    gz = min(max(wz / 20.0, 0.0), GRID - 1)
    x0, z0 = int(gx), int(gz)
    fx, fz = gx - x0, gz - z0
    x1, z1 = min(x0 + 1, GRID - 1), min(z0 + 1, GRID - 1)
    h00 = global_grid_height(grids, x0, z0)
    h10 = global_grid_height(grids, x1, z0)
    h01 = global_grid_height(grids, x0, z1)
    h11 = global_grid_height(grids, x1, z1)
    return h00 * (1 - fx) * (1 - fz) + h10 * fx * (1 - fz) + h01 * (1 - fx) * fz + h11 * fx * fz


def build_terrain():
    grids = {}
    for sx, sy in SECTORS:
        grids[(sx, sy)] = load_m_grid(sx, sy)
    G = DGRID
    verts = []
    idxs = []
    min_y, max_y = 1e9, -1e9
    heights = {"size": G, "step": STEP, "data": []}
    for iz in range(G):
        wz = iz * STEP
        for ix in range(G):
            wx = ix * STEP
            h = sample_grid_height(grids, wx, wz)
            u = wx / WORLD_W
            v = 1.0 - (wz / WORLD_W)
            verts.extend([wx, h, wz, u, v])
            heights["data"].append(round(h, 2))
            min_y = min(min_y, h)
            max_y = max(max_y, h)
    for iz in range(G - 1):
        for ix in range(G - 1):
            a = iz * G + ix
            b = a + 1
            c = (iz + 1) * G + ix
            d = c + 1
            idxs.extend([a, b, c, b, d, c])
    return {
        "vertices": [round(x, 3) for x in verts],
        "indices": idxs,
        "bounds": {"minX": 0.0, "minZ": 0.0, "maxX": WORLD_W, "maxZ": WORLD_W,
                   "minY": round(min_y, 2), "maxY": round(max_y, 2)},
        "heights": heights,
    }


def sample_terrain_height(terrain, wx, wz):
    g = terrain["heights"]
    G = g["size"]
    step = g["step"]
    fx = min(max(wx / step, 0.0), G - 1)
    fz = min(max(wz / step, 0.0), G - 1)
    x0, z0 = int(fx), int(fz)
    x1, z1 = min(x0 + 1, G - 1), min(z0 + 1, G - 1)
    t = g["data"]
    h00 = t[z0 * G + x0]
    h10 = t[z0 * G + x1]
    h01 = t[z1 * G + x0]
    h11 = t[z1 * G + x1]
    ax, az = fx - x0, fz - z0
    return h00 * (1 - ax) * (1 - az) + h10 * ax * (1 - az) + h01 * (1 - ax) * az + h11 * ax * az


def build_floor():
    composite = Image.new("RGB", (256 * 6, 256 * 6))
    for x, y in SECTORS:
        tile = load_ddj_image(os.path.join(CT, "Media", "minimap", f"{x}x{y}.ddj")).convert("RGB")
        composite.paste(tile, ((x - 76) * 256, (108 - y) * 256))
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "floor.webp")
    composite.save(out, "WEBP", quality=85)
    return out


# --------------------------------------------------------------------------
# Object / npc data
# --------------------------------------------------------------------------

def load_object_index():
    with open(os.path.join(CT, "Data", "navmesh", "object.ifo"), encoding="gbk", errors="replace") as f:
        objs = []
        for ln in f:
            i = ln.find('"')
            j = ln.rfind('"')
            objs.append(ln[i + 1 : j].replace("\\", "/"))
        return objs


def load_o2(sx, sy):
    path = os.path.join(CT, "Map", str(sy), f"{sx}.o2")
    with open(path, "rb") as f:
        d = f.read()
    out = []
    pos = 16
    while pos < len(d):
        cnt = struct.unpack_from("<H", d, pos)[0]
        pos += 2
        if cnt == 0:
            continue
        for _ in range(cnt):
            if pos + 30 > len(d):
                break
            nameI = struct.unpack_from("<I", d, pos)[0]
            x, y, z = struct.unpack_from("<fff", d, pos + 4)
            theta = struct.unpack_from("<f", d, pos + 18)[0]
            tail = struct.unpack_from("<H", d, pos + 28)[0]
            pos += 30
            out.append({
                "nameI": nameI,
                "x": x,
                "y": y,
                "z": z,
                "theta": theta,
                "tx": tail & 0xFF,
                "tz": tail >> 8,
            })
    return out


def load_npcpos():
    out = []
    with open(os.path.join(CT, "Media", "npcpos.txt"), encoding="utf-16-le") as f:
        for ln in f:
            cols = ln.rstrip("\r\n").split("\t")
            if len(cols) < 5:
                continue
            try:
                ref = int(cols[0].strip())
                region = int(cols[1].strip())
                x = float(cols[2].strip())
                z = float(cols[4].strip())
            except ValueError:
                continue
            if 103 <= (region >> 8) <= 108:
                out.append({"ref": ref, "region": region, "x": x, "z": z})
    return out


def load_refchars():
    refchars = {}
    for fn in os.listdir(os.path.join(CT, "Media")):
        if not fn.lower().startswith("characterdata_"):
            continue
        with open(os.path.join(CT, "Media", fn), encoding="utf-16-le") as f:
            for ln in f:
                parts = ln.rstrip("\n").rstrip("\r").split("\t")
                if len(parts) < 3:
                    continue
                try:
                    ref = int(parts[1].strip())
                except ValueError:
                    continue
                model = ""
                for col in parts[3:]:
                    col = col.replace("\\", "/")
                    if col.lower().endswith(".bsr"):
                        model = col
                        break
                if model:
                    refchars[ref] = model
    return refchars


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    terrain = build_terrain()
    print(f"terrain vertices={len(terrain['vertices']) // 5} triangles={len(terrain['indices']) // 3}")
    build_floor()
    print("floor ->", os.path.join(OUT_DIR, "floor.webp"))

    objects = load_object_index()
    refchars = load_refchars()
    npcpos = load_npcpos()

    # ---- collect building instances by bsr ----
    instances_by_bsr = {}
    for sx, sy in SECTORS:
        for inst in load_o2(sx, sy):
            if inst["nameI"] >= len(objects):
                continue
            bsr = objects[inst["nameI"]]
            wx = inst["x"] + (inst["tx"] - SX) * SECTOR_W
            wz = inst["z"] + (inst["tz"] - SY) * SECTOR_W
            instances_by_bsr.setdefault(bsr, []).append(
                {"x": round(wx, 2), "y": round(inst["y"], 2), "z": round(wz, 2), "ry": round(inst["theta"], 5)}
            )

    # ---- collect npc/mob placements by model ----
    npc_by_model = {}
    for np in npcpos:
        model = refchars.get(np["ref"])
        if not model:
            continue
        if not model.startswith("res/"):
            model = "res/" + model
        wx = np["x"] + ((np["region"] & 0xFF) - SX) * SECTOR_W
        wz = np["z"] + ((np["region"] >> 8) - SY) * SECTOR_W
        npc_by_model.setdefault(model, []).append({"x": round(wx, 2), "z": round(wz, 2)})

    # ---- raw geometry for every needed bsr ----
    atlas = Atlas()
    raw = {}  # bsr -> {"parts": [...], "instances": [...], "kind": "b"|"n"}
    bsr_list = sorted(instances_by_bsr.keys())
    for bsr in bsr_list:
        g = collect_geom_raw(bsr)
        if g is not None:
            raw[bsr] = {"parts": g["parts"], "instances": instances_by_bsr[bsr], "kind": "b"}
    print(f"building geoms usable={len(raw)} instances={sum(len(v['instances']) for v in raw.values())}")

    for model in sorted(npc_by_model.keys()):
        g = collect_geom_raw(model)
        if g is not None:
            raw[model] = {"parts": g["parts"], "instances": npc_by_model[model], "kind": "n"}
    print(f"npc/mob groups={sum(1 for v in raw.values() if v['kind'] == 'n')} "
          f"total={sum(len(v['instances']) for v in raw.values() if v['kind'] == 'n')}")

    # ---- atlas page assignment ----
    raw_keys = list(raw.keys())
    geom_tex_keys = []
    for bsr in raw_keys:
        keys = set()
        for tex_path, _v, _i in raw[bsr]["parts"]:
            keys.add(tex_path)
        geom_tex_keys.append(keys)
    for keys in geom_tex_keys:
        for k in keys:
            atlas.tex_key(k)
    atlas.load_sizes()
    atlas.assign_pages(geom_tex_keys)
    atlas.pack()
    atlas_pages = atlas.write_pages()
    print("atlas pages:", atlas_pages)

    # ---- finalize geometry (remap UVs) ----
    geoms = []
    vo = 0
    io = 0
    raw_geom_index = {}
    for gi, bsr in enumerate(raw_keys):
        verts = []
        indices = []
        base_i = 0
        for tex_path, vv, ii in raw[bsr]["parts"]:
            for pos, uv in vv:
                au, av = atlas.uv(gi, tex_path, uv[0], uv[1])
                verts.append((pos[0], pos[1], pos[2], au, av))
            for x in ii:
                indices.append(base_i + x)
            base_i += len(vv)
        geoms.append({
            "v0": vo, "vCount": len(verts), "i0": io, "iCount": len(indices),
            "page": atlas.geom_tex_page[gi][raw[bsr]["parts"][0][0]],
            "verts": verts, "indices": indices,
        })
        raw_geom_index[bsr] = gi
        vo += len(verts)
        io += len(indices)

    vert_total = vo
    idx_total = io

    # ---- write binary geometry ----
    buf = bytearray()
    buf += b"SROBGEO1"
    buf += struct.pack("<II", vert_total, idx_total)
    for g in geoms:
        for v in g["verts"]:
            buf += struct.pack("<5f", *v)
    for g in geoms:
        buf += struct.pack(f"<{len(g['indices'])}I", *g["indices"])
    bgeo = os.path.join(OUT_DIR, "buildings.bgeo")
    with open(bgeo, "wb") as f:
        f.write(buf)
    print(f"bgeo {vert_total} verts {idx_total} idx {len(buf) / 1048576:.2f} MB -> {bgeo}")

    # ---- manifest ----
    slice_geoms = [
        {"v0": g["v0"], "vCount": g["vCount"], "i0": g["i0"], "iCount": g["iCount"], "page": g["page"]}
        for g in geoms
    ]

    building_instances = [
        {"g": raw_geom_index[bsr], "x": i["x"], "y": i["y"], "z": i["z"], "ry": i["ry"]}
        for bsr in bsr_list if bsr in raw_geom_index
        for i in raw[bsr]["instances"]
    ]
    print(f"building instances emitted={len(building_instances)}")

    npc_groups = []
    for bsr in sorted(npc_by_model.keys()):
        if bsr not in raw_geom_index:
            continue
        npc_groups.append({
            "geom": raw_geom_index[bsr],
            "name": os.path.basename(bsr).replace(".bsr", ""),
            "kind": "mob" if "/mob/" in bsr else "npc",
            "instances": npc_by_model[bsr],
        })
    print(f"npc groups emitted={len(npc_groups)}")

    manifest = {
        "atlas": atlas_pages,
        "pageSize": PAGE,
        "geoms": slice_geoms,
        "instances": building_instances,
        "npcGroups": npc_groups,
    }
    mj = os.path.join(OUT_DIR, "buildings.json")
    with open(mj, "w") as f:
        json.dump(manifest, f)
    print("buildings.json ->", mj)

    # ---- mesh.json ----
    spawn_x, spawn_z = 5000.0, 5800.0
    spawn_y = sample_terrain_height(terrain, spawn_x, spawn_z)
    mesh = {
        "region": 1,
        "name": "Constantinople",
        "source": {
            "dof": "Map.pk2 {Y}/{X}.m (36 sectors, region 1)",
            "minimap": "Media.pk2 minimap/{76..81}x{103..108}.ddj",
        },
        "vertexCount": len(terrain["vertices"]) // 5,
        "indexCount": len(terrain["indices"]),
        "vertices": [round(v, 3) for v in terrain["vertices"]],
        "indices": terrain["indices"],
        "bounds": terrain["bounds"],
        "spawn": {"x": spawn_x, "y": round(spawn_y, 3), "z": spawn_z},
        "heights": terrain["heights"],
        "blocks": [{"id": i, "name": f"CT{sx}x{sy}", "floor": 0} for i, (sx, sy) in enumerate(SECTORS)],
    }
    mesh_path = os.path.join(OUT_DIR, "mesh.json")
    with open(mesh_path, "w") as f:
        json.dump(mesh, f)
    print("mesh.json ->", mesh_path)
    print(f"spawn ({spawn_x}, {spawn_y:.2f}, {spawn_z})")

    sizes = {"mesh.json": os.path.getsize(mesh_path), "buildings.json": os.path.getsize(mj), "buildings.bgeo": len(buf)}
    for a in atlas_pages:
        sizes[a] = os.path.getsize(os.path.join(OUT_DIR, a))
    sizes["floor.webp"] = os.path.getsize(os.path.join(OUT_DIR, "floor.webp"))
    total = sum(sizes.values())
    print("sizes:", {k: f"{v / 1024:.0f}KB" for k, v in sizes.items()}, f"total {total / 1048576:.2f} MB")


if __name__ == "__main__":
    main()
