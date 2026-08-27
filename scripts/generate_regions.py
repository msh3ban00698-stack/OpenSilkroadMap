#!/usr/bin/env python3
"""Generate runtime 3D assets for multiple authentic world regions.

Generalization of scripts/generate_region_ct.py. For every region in REGIONS
it reads the extracted CT sources (scripts/extract_regions.py -> game_source/CT)
and emits under map/public/assets/img/silkroad/game/<region>/:

  mesh.json         decimated terrain mesh (vertices + UVs + bounds + spawn +
                    height grid for terrain-following)
  floor.webp        NxN minimap composite
  buildings.json    manifest: atlas pages, geometry slices, building instances,
                    npc/mob models + placements
  buildings.bgeo    packed binary geometry
  atlas<N>.webp     texture atlas page(s)

Missing sectors (ocean edges) get a flat zero-height grid and a water-colour
floor tile so mesh generation never fails.

Usage: uv run scripts/generate_regions.py
"""

import json
import os
import struct
import sys

from io import BytesIO

from PIL import Image

CT = os.path.join(os.path.dirname(__file__), "..", "game_source", "CT")
OUT_ROOT = os.path.join("map", "public", "assets", "img", "silkroad", "game")

SECTOR_W = 1920.0
STRIDE = 2
PAGE = 4096
CELL = 64
PAGE_CELLS = PAGE // CELL

REGIONS = [
    ("region2", "Jangan", 164, 94, 5120.0, 5760.0),
    ("region3", "Donwhang", 150, 99, 5760.0, 5760.0),
    ("region4", "Hotan", 132, 89, 5760.0, 5760.0),
    ("region5", "Samarkand", 104, 102, 5760.0, 5760.0),
    ("region6", "Baghdad", 86, 84, 5760.0, 5760.0),
    ("region7", "Alexandria", 45, 90, 5760.0, 5760.0),
    ("region8", "Mt. Roc", 106, 89, 5760.0, 5760.0),
    ("region9", "Jupiter Temple", 199, 88, 5760.0, 5760.0),
]


class ShelfPage:
    def __init__(self):
        self.rows = []
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
        p = self.clone()
        for wc, hc in items:
            if p.place(wc, hc) is None:
                return False
        return True


class Atlas:
    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.tex_list = {}
        self.rects = {}
        self.pages = []
        self.page_texs = []
        self.geom_tex_page = []
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
                        raise RuntimeError(f"texture too large for atlas: {k}")
                    self.rects[(pg, self.tex_key(k))] = r
                    self.page_texs[pg].add(k)
                page_map[k] = pg
            self.geom_tex_page.append(page_map)
        self.page_count = len(self.pages)

    def uv(self, geom_gi, path, u, v):
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
            fn = os.path.join(self.out_dir, f"atlas{pg}.webp")
            img.save(fn, "WEBP", quality=82, method=4)
            out.append(f"atlas{pg}.webp")
        return out


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
    if bd[:12] != b"JMXVRES 0109":
        return None
    num, num2, _num3 = struct.unpack_from("<III", bd, 12)
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
        if q + 52 > len(bd):
            break
        x, y, z = struct.unpack_from("<fff", bd, q)
        u, v = struct.unpack_from("<ff", bd, q + 24)
        verts.append(((x, y, z), (u, v)))
        q += stride
    q = off_faces
    fc = struct.unpack_from("<I", bd, q)[0]
    q += 4
    idx = []
    for _ in range(fc):
        if q + 6 > len(bd):
            break
        idx.extend(struct.unpack_from("<HHH", bd, q))
        q += 6
    return {"verts": verts, "indices": idx, "mat_name": mat_name}


def load_ddj_image(path):
    with open(path, "rb") as f:
        f.seek(20)
        dds = f.read()
    return Image.open(BytesIO(normalize_dds(dds))).convert("RGBA")


def normalize_dds(dds):
    """Remap VSRO premultiplied DXT2/DXT4 to DXT3/DXT5.

    Some package textures store the fourcc string in the pixel-format
    dwRGBBitCount field (offset 84) while dwFourCC (offset 80) holds the
    DDPF_FOURCC flag value (4). PIL reads that field and fails on DXT2/DXT4;
    DXT1/3/5 there already decode. DXT2/DXT4 share the exact block layout of
    DXT3/DXT5, so we swap the string in place and leave everything else alone.
    """
    if len(dds) < 128 or dds[:4] != b"DDS ":
        return dds
    fourcc = dds[80:84]
    bitcount = dds[84:88]
    if fourcc == b"\x04\x00\x00\x00":
        if bitcount == b"DXT2":
            return dds[:84] + b"DXT3" + dds[88:]
        if bitcount == b"DXT4":
            return dds[:84] + b"DXT5" + dds[88:]
        return dds
    if fourcc == b"DXT2":
        return dds[:80] + b"DXT3" + dds[84:]
    if fourcc == b"DXT4":
        return dds[:80] + b"DXT5" + dds[84:]
    return dds


def collect_geom_raw(bsr):
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


WATER_H = 0.0


def load_m_grid(sx, sy):
    path = os.path.join(CT, "Map", str(sy), f"{sx}.m")
    if not os.path.isfile(path):
        return [[WATER_H] * 97 for _ in range(97)]
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


def generate_region(key, name, sx0, sy0, spawn_x, spawn_z):
    nx = 6
    nz = 6
    SECTORS = [(x, y) for y in range(sy0, sy0 + nz) for x in range(sx0, sx0 + nx)]
    out_dir = os.path.join(OUT_ROOT, key)
    os.makedirs(out_dir, exist_ok=True)
    world_w = SECTOR_W * nx

    GRID = 97 * nx - (nx - 1)
    DGRID = (GRID - 1) // STRIDE + 1
    STEP = 20.0 * STRIDE

    grids = {}
    for sx, sy in SECTORS:
        grids[(sx, sy)] = load_m_grid(sx, sy)

    def global_grid_height(gxi, gzi):
        si = min(gxi // 96, nx - 1)
        ti = min(gzi // 96, nz - 1)
        return grids[(sx0 + si, sy0 + ti)][gzi - ti * 96][gxi - si * 96]

    def sample_grid_height(wx, wz):
        gx = min(max(wx / 20.0, 0.0), GRID - 1)
        gz = min(max(wz / 20.0, 0.0), GRID - 1)
        x0, z0 = int(gx), int(gz)
        fx, fz = gx - x0, gz - z0
        x1, z1 = min(x0 + 1, GRID - 1), min(z0 + 1, GRID - 1)
        h00 = global_grid_height(x0, z0)
        h10 = global_grid_height(x1, z0)
        h01 = global_grid_height(x0, z1)
        h11 = global_grid_height(x1, z1)
        return h00 * (1 - fx) * (1 - fz) + h10 * fx * (1 - fz) + h01 * (1 - fx) * fz + h11 * fx * fz

    G = DGRID
    verts = []
    idxs = []
    min_y, max_y = 1e9, -1e9
    heights = {"size": G, "step": STEP, "data": []}
    for iz in range(G):
        wz = iz * STEP
        for ix in range(G):
            wx = ix * STEP
            h = sample_grid_height(wx, wz)
            u = wx / world_w
            v = 1.0 - (wz / world_w)
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

    terrain = {
        "vertices": verts,
        "indices": idxs,
        "bounds": {"minX": 0.0, "maxX": world_w, "minZ": 0.0, "maxZ": world_w, "minY": round(min_y, 2), "maxY": round(max_y, 2)},
        "heights": heights,
    }

    def sample_terrain_height(wx, wz):
        g = heights
        Gx = g["size"]
        step = g["step"]
        fx = min(max(wx / step, 0.0), Gx - 1)
        fz = min(max(wz / step, 0.0), Gx - 1)
        x0, z0 = int(fx), int(fz)
        x1, z1 = min(x0 + 1, Gx - 1), min(z0 + 1, Gx - 1)
        t = g["data"]
        h00 = t[z0 * Gx + x0]
        h10 = t[z0 * Gx + x1]
        h01 = t[z1 * Gx + x0]
        h11 = t[z1 * Gx + x1]
        ax, az = fx - x0, fz - z0
        return h00 * (1 - ax) * (1 - az) + h10 * ax * (1 - az) + h01 * (1 - ax) * az + h11 * ax * az

    WATER = (30, 70, 130)
    tile_w = 256
    composite = Image.new("RGB", (tile_w * nx, tile_w * nz), WATER)
    for x, y in SECTORS:
        mp = os.path.join(CT, "Media", "minimap", f"{x}x{y}.ddj")
        if not os.path.isfile(mp):
            continue
        tile = load_ddj_image(mp).convert("RGB")
        composite.paste(tile, ((x - sx0) * tile_w, (sy0 + nz - 1 - y) * tile_w))
    floor_path = os.path.join(out_dir, "floor.webp")
    composite.save(floor_path, "WEBP", quality=85)

    with open(os.path.join(CT, "Data", "navmesh", "object.ifo"), encoding="gbk", errors="replace") as f:
        objects = []
        for ln in f:
            i = ln.find('"')
            j = ln.rfind('"')
            objects.append(ln[i + 1 : j].replace("\\", "/"))

    def load_o2(sx, sy):
        path = os.path.join(CT, "Map", str(sy), f"{sx}.o2")
        if not os.path.isfile(path):
            return []
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
                    "x": x, "y": y, "z": z,
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
                rx, ry = region & 0xFF, region >> 8
                if sx0 <= rx < sx0 + nx and sy0 <= ry < sy0 + nz:
                    out.append({"ref": ref, "region": region, "x": x, "z": z})
        return out

    def compute_spawn(npcpos_records, refchars_map):
        """Spawn at the median of town NPC positions (models outside /mob/)."""
        pts = []
        for np in npcpos_records:
            model = refchars_map.get(np["ref"])
            if not model or "/mob/" in model.replace("\\", "/"):
                continue
            wx = np["x"] + ((np["region"] & 0xFF) - sx0) * SECTOR_W
            wz = np["z"] + ((np["region"] >> 8) - sy0) * SECTOR_W
            pts.append((wx, wz))
        if not pts:
            return spawn_x, spawn_z
        pts.sort()
        medx = pts[len(pts) // 2][0]
        medz = sorted(pts, key=lambda q: q[1])[len(pts) // 2][1]
        sx = min(max(medx, 300.0), world_w - 300.0)
        sz = min(max(medz, 300.0), world_w - 300.0)
        return sx, sz

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

    refchars = load_refchars()
    npcpos = load_npcpos()
    spawn_x, spawn_z = compute_spawn(npcpos, refchars)

    instances_by_bsr = {}
    for sx, sy in SECTORS:
        for inst in load_o2(sx, sy):
            if inst["nameI"] >= len(objects):
                continue
            bsr = objects[inst["nameI"]]
            wx = inst["x"] + (inst["tx"] - sx0) * SECTOR_W
            wz = inst["z"] + (inst["tz"] - sy0) * SECTOR_W
            instances_by_bsr.setdefault(bsr, []).append(
                {"x": round(wx, 2), "y": round(inst["y"], 2), "z": round(wz, 2), "ry": round(inst["theta"], 5)}
            )

    npc_by_model = {}
    for np in npcpos:
        model = refchars.get(np["ref"])
        if not model:
            continue
        if not model.startswith("res/"):
            model = "res/" + model
        wx = np["x"] + ((np["region"] & 0xFF) - sx0) * SECTOR_W
        wz = np["z"] + ((np["region"] >> 8) - sy0) * SECTOR_W
        npc_by_model.setdefault(model, []).append({"x": round(wx, 2), "z": round(wz, 2)})

    atlas = Atlas(out_dir)
    raw = {}
    bsr_list = sorted(instances_by_bsr.keys())
    for bsr in bsr_list:
        g = collect_geom_raw(bsr)
        if g is not None:
            raw[bsr] = {"parts": g["parts"], "instances": instances_by_bsr[bsr], "kind": "b"}
    for model in sorted(npc_by_model.keys()):
        g = collect_geom_raw(model)
        if g is not None:
            raw[model] = {"parts": g["parts"], "instances": npc_by_model[model], "kind": "n"}

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
    atlas_pages = atlas.write_pages()

    geoms = []
    vo = 0
    io = 0
    raw_geom_index = {}
    for gi, bsr in enumerate(raw_keys):
        gv = []
        gidx = []
        base_i = 0
        for tex_path, vv, ii in raw[bsr]["parts"]:
            for pos, uv in vv:
                au, av = atlas.uv(gi, tex_path, uv[0], uv[1])
                gv.append((pos[0], pos[1], pos[2], au, av))
            for x in ii:
                gidx.append(base_i + x)
            base_i += len(vv)
        geoms.append({
            "v0": vo, "vCount": len(gv), "i0": io, "iCount": len(gidx),
            "page": atlas.geom_tex_page[gi][raw[bsr]["parts"][0][0]],
            "verts": gv, "indices": gidx,
        })
        raw_geom_index[bsr] = gi
        vo += len(gv)
        io += len(gidx)

    buf = bytearray()
    buf += b"SROBGEO1"
    buf += struct.pack("<II", vo, io)
    for g in geoms:
        for v in g["verts"]:
            buf += struct.pack("<5f", *v)
    for g in geoms:
        buf += struct.pack(f"<{len(g['indices'])}I", *g["indices"])
    bgeo = os.path.join(out_dir, "buildings.bgeo")
    with open(bgeo, "wb") as f:
        f.write(buf)

    slice_geoms = [
        {"v0": g["v0"], "vCount": g["vCount"], "i0": g["i0"], "iCount": g["iCount"], "page": g["page"]}
        for g in geoms
    ]
    building_instances = [
        {"g": raw_geom_index[bsr], "x": i["x"], "y": i["y"], "z": i["z"], "ry": i["ry"]}
        for bsr in bsr_list if bsr in raw_geom_index
        for i in instances_by_bsr[bsr]
    ]
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

    manifest = {
        "atlas": atlas_pages,
        "pageSize": PAGE,
        "geoms": slice_geoms,
        "instances": building_instances,
        "npcGroups": npc_groups,
    }
    with open(os.path.join(out_dir, "buildings.json"), "w") as f:
        json.dump(manifest, f)

    spawn_y = sample_terrain_height(spawn_x, spawn_z)
    mesh = {
        "region": int(key.replace("region", "")),
        "name": name,
        "source": {
            "dof": f"Map.pk2 {{Y}}/{{X}}.m (6x6 sectors, window {sx0},{sy0})",
            "minimap": f"Media.pk2 minimap/{{{sx0}..{sx0 + nx - 1}}}x{{{sy0}..{sy0 + nz - 1}}}.ddj",
        },
        "vertexCount": len(terrain["vertices"]) // 5,
        "indexCount": len(terrain["indices"]),
        "vertices": terrain["vertices"],
        "indices": terrain["indices"],
        "bounds": terrain["bounds"],
        "spawn": {"x": spawn_x, "y": round(spawn_y, 3), "z": spawn_z},
        "heights": terrain["heights"],
        "blocks": [{"id": i, "name": f"CT{sx}x{sy}", "floor": 0} for i, (sx, sy) in enumerate(SECTORS)],
    }
    with open(os.path.join(out_dir, "mesh.json"), "w") as f:
        json.dump(mesh, f)

    sizes = {
        "mesh.json": os.path.getsize(os.path.join(out_dir, "mesh.json")),
        "buildings.json": os.path.getsize(os.path.join(out_dir, "buildings.json")),
        "buildings.bgeo": len(buf),
        "floor.webp": os.path.getsize(floor_path),
    }
    for a in atlas_pages:
        sizes[a] = os.path.getsize(os.path.join(out_dir, a))
    total = sum(sizes.values())
    print(
        f"{key} {name}: terrain={len(terrain['vertices']) // 5} "
        f"buildings={len(building_instances)} npcgrps={len(npc_groups)} "
        f"atlas={len(atlas_pages)} total={total / 1048576:.1f}MB "
        f"spawn=({spawn_x},{round(spawn_y, 2)},{spawn_z})"
    )


def main():
    force = "--force" in sys.argv
    build_data_index()
    for key, name, sx, sy, spx, spz in REGIONS:
        out_dir = os.path.join(OUT_ROOT, key)
        if (
            not force
            and os.path.isfile(os.path.join(out_dir, "mesh.json"))
            and os.path.isfile(os.path.join(out_dir, "floor.webp"))
        ):
            print(f"{key} {name}: up to date, skipping")
            continue
        generate_region(key, name, sx, sy, spx, spz)
    print("done")


if __name__ == "__main__":
    main()
