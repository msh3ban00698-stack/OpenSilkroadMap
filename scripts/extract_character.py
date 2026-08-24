"""Convert one real Silkroad character preset into runtime viewer assets.

Parses the verified JMXVB* binary formats (BSK skeleton, BMS mesh, BAN
animation, BMT material, DDJ texture) and emits a compact JSON + webp set
that map/src/game/character_loader.ts consumes:

    map/public/assets/img/silkroad/game/character/<preset>/
        skeleton.json   bone names, parents, bind local transforms
        meshes.json     positions/normals/uvs/skin data/indices per part
        anims.json      per-bone keyframes keyed by bone index + timing
        meta.json       preset metadata (height, scale, camera)
        <texture>.webp  converted material maps

Data source: game_source/Data/prim (extracted from Data.pk2).

Usage: uv run scripts/extract_character.py [preset]
"""

import json
import math
import os
import struct
import sys
import io

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

PRIM_DIR = os.path.join("game_source", "Data", "prim")
OUT_BASE = os.path.join("map", "public", "assets", "img", "silkroad", "game", "character")

PRESETS = {
    "chinaman_fighter": {
        "name": "China Fighter",
        "race": "China",
        "class": "Fighter",
        "skeleton": "skel/char/china/chinaman_skel.bsk",
        "body": [
            "mesh/char/china/man/man_pelvis.bms",
            "mesh/char/china/man/man_torso_lower.bms",
            "mesh/char/china/man/man_torso_upper.bms",
            "mesh/char/china/man/man_arm_upper.bms",
            "mesh/char/china/man/man_arm_lower.bms",
            "mesh/char/china/man/man_thigh.bms",
            "mesh/char/china/man/man_calf.bms",
        ],
        "face": "mesh/char/china/man/chinaman_fighter_face.bms",
        "hair": "mesh/char/china/man/chinaman_fighter_hair.bms",
        "clothes": [
            "mesh/item/china/man_item/clothes_01_aa.bms",
            "mesh/item/china/man_item/clothes_01_ba.bms",
            "mesh/item/china/man_item/clothes_01_fa.bms",
            "mesh/item/china/man_item/clothes_01_ha.bms",
            "mesh/item/china/man_item/clothes_01_la.bms",
            "mesh/item/china/man_item/clothes_01_sa.bms",
        ],
        "weapon": "mesh/item/china/weapon/sword_01.bms",
        "attach_weapon_to": "Bip01 R Hand",
        "materials": [
            "mtrl/char/china/man/chinaman_fighter.bmt",
            "mtrl/item/china/man_item/clothes_01.bmt",
            "mtrl/item/china/man_item/clothes_01_sa.bmt",
            "mtrl/item/china/weapon/sword1_2_3.bmt",
        ],
        "anims": [
            ("idle", "Idle (battle)", "ani/char/china/man/chinaman_standbattle.ban"),
            ("idle_city", "Idle (city)", "ani/char/china/man/chinaman_fighter_standcity.ban"),
            ("walk", "Walk", "ani/char/china/man/chinaman_fighter_walkforward.ban"),
            ("run", "Run", "ani/char/china/man/chinaman_fighter_runforward_sword.ban"),
            ("attack", "Attack", "ani/char/china/man/sword_base_01.ban"),
            ("attack2", "Combo attack", "ani/char/china/man/chinaman_s_light_cho_sword.ban"),
        ],
        "world_scale": 0.15,
    },
}


class BS:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.p)[0]
        self.p += 2
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def string(self):
        n = self.u32()
        s = self.d[self.p : self.p + n].decode("ascii", errors="replace")
        self.p += n
        return s

    def skip(self, n):
        self.p += n


def parse_skeleton(data):
    s = BS(data)
    assert s.d[:12] == b"JMXVBSK 0101", s.d[:12]
    s.p = 12
    count = s.u32()
    bones = []
    for _ in range(count):
        bone_type = s.u8()
        name = s.string()
        parent = s.string()
        rot_parent = [s.f32() for _ in range(4)]
        tr_parent = [s.f32() for _ in range(3)]
        rot_origin = [s.f32() for _ in range(4)]
        tr_origin = [s.f32() for _ in range(3)]
        rot_local = [s.f32() for _ in range(4)]
        tr_local = [s.f32() for _ in range(3)]
        child_count = s.u32()
        children = [s.string() for _ in range(child_count)]
        bones.append(
            {
                "name": name,
                "parent": parent,
                "rot": rot_parent,
                "pos": tr_parent,
                "rot_origin": rot_origin,
                "pos_origin": tr_origin,
            }
        )
    return bones


def parse_mesh(data):
    s = BS(data)
    assert s.d[:12] == b"JMXVBMS 0110", s.d[:12]
    s.p = 12
    offsets = [s.u32() for _ in range(15)]
    off_verts, off_bones, off_faces = offsets[0], offsets[1], offsets[2]
    vert_type = offsets[13]
    s.string()
    mat_name = s.string()
    s.skip(4)
    stride = 44 if vert_type == 0 else 52
    s.p = off_verts
    vert_count = s.u32()
    verts = []
    for _ in range(vert_count):
        pos = [s.f32() for _ in range(3)]
        nrm = [s.f32() for _ in range(3)]
        uv = [s.f32() for _ in range(2)]
        s.skip(stride - 32)
        verts.append((pos, nrm, uv))
    s.p = off_bones
    bone_count = s.u32()
    bone_names = [s.string() for _ in range(bone_count)]
    skin = []
    for _ in range(vert_count):
        b1 = s.u8()
        w1 = s.u16()
        b2 = s.u8()
        w2 = s.u16()
        skin.append((b1, w1, b2, w2))
    s.p = off_faces
    face_count = s.u32()
    indices = []
    for _ in range(face_count):
        indices.extend([s.u16() for _ in range(3)])
    return {"mat_name": mat_name, "verts": verts, "bones": bone_names, "skin": skin, "indices": indices}


def parse_animation(data):
    s = BS(data)
    assert s.d[:12] == b"JMXVBAN 0102", s.d[:12]
    s.p = 12
    s.i32()
    s.i32()
    name = s.string()
    duration = s.i32()
    fps = s.i32()
    anim_type = s.i32()
    time_count = s.u32()
    key_times = [s.u32() for _ in range(time_count)]
    bone_count = s.u32()
    bones = []
    for _ in range(bone_count):
        bone_name = s.string()
        kf_count = s.u32()
        rots = []
        poss = []
        for _ in range(kf_count):
            rots.extend([s.f32() for _ in range(4)])
            poss.extend([s.f32() for _ in range(3)])
        bones.append({"name": bone_name, "rot": rots, "pos": poss})
    return {
        "name": name,
        "duration": duration,
        "fps": fps,
        "type": anim_type,
        "key_times": key_times,
        "bones": bones,
    }


def parse_material(data):
    s = BS(data)
    assert s.d[:12] == b"JMXVBMT 0102", s.d[:12]
    s.p = 12
    count = s.u32()
    materials = []
    for _ in range(count):
        name = s.string()
        for _ in range(16):
            s.f32()
        s.f32()
        flag = s.u32()
        dpath = s.string()
        s.f32()
        s.u8()
        s.u8()
        is_absolute = bool(s.u8())
        materials.append({"name": name, "flag": flag, "map": dpath, "absolute": is_absolute})
    return materials


def quat_multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]


def quat_rotate(q, v):
    x, y, z, w = q
    qv = [x, y, z]
    cross = lambda a, b: [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
    t1 = cross(qv, v)
    t2 = cross(qv, t1)
    return [v[i] + 2 * w * t1[i] + 2 * t2[i] for i in range(3)]


def build_bind_world(bones, extra_parents=None):
    index = {b["name"]: i for i, b in enumerate(bones)}
    parents = []
    for b in bones:
        if b["parent"] and b["parent"] in index:
            parents.append(index[b["parent"]])
        else:
            parents.append(-1)
    world_rot = []
    world_pos = []
    for i, b in enumerate(bones):
        p = parents[i]
        if p < 0:
            world_rot.append(list(b["rot"]))
            world_pos.append(list(b["pos"]))
        else:
            pr = world_rot[p]
            pp = world_pos[p]
            pos = [pp[j] + quat_rotate(pr, b["pos"])[j] for j in range(3)]
            world_rot.append(quat_multiply(pr, b["rot"]))
            world_pos.append(pos)
    return parents, world_rot, world_pos


def convert_texture(ddj_path, out_webp, flip=False):
    with open(ddj_path, "rb") as f:
        f.seek(20)
        dds_data = f.read()
    img = Image.open(io.BytesIO(dds_data))
    img = img.convert("RGBA")
    if flip:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    os.makedirs(os.path.dirname(out_webp), exist_ok=True)
    img.save(out_webp, "WEBP", quality=85)
    alpha = img.getchannel("A").getextrema() != (255, 255)
    return alpha


def main():
    preset_name = sys.argv[1] if len(sys.argv) > 1 else "chinaman_fighter"
    preset = PRESETS.get(preset_name)
    if preset is None:
        print("Unknown preset. Available:", ", ".join(PRESETS))
        sys.exit(1)

    out_dir = os.path.join(OUT_BASE, preset_name)
    os.makedirs(out_dir, exist_ok=True)

    def read(rel):
        with open(os.path.join(PRIM_DIR, rel), "rb") as f:
            return f.read()

    print(f"[skeleton] {preset['skeleton']}")
    bones = parse_skeleton(read(preset["skeleton"]))
    index = {b["name"]: i for i, b in enumerate(bones)}

    extra_bones = []
    attach = preset.get("attach_weapon_to")
    mesh_files = list(preset["body"]) + [preset["face"], preset["hair"]] + list(preset["clothes"])
    if preset.get("weapon"):
        mesh_files.append(preset["weapon"])

    print(f"[materials]")
    material_lookup = {}
    for mrel in preset["materials"]:
        for mat in parse_material(read(mrel)):
            if mat["name"] not in material_lookup:
                bmt_dir = os.path.dirname(mrel)
                material_lookup[mat["name"]] = os.path.join(bmt_dir, mat["map"])

    meshes = []
    weapon_name = os.path.splitext(os.path.basename(preset["weapon"]))[0] if preset.get("weapon") else None
    for rel in mesh_files:
        name = os.path.splitext(os.path.basename(rel))[0]
        print(f"[mesh] {name}")
        m = parse_mesh(read(rel))
        mesh_bones = []
        for bname in m["bones"]:
            if bname in index:
                mesh_bones.append(index[bname])
            else:
                known = [x[0] for x in extra_bones]
                if bname not in known:
                    parent = index[attach] if (name == weapon_name and attach and attach in index) else 0
                    extra_bones.append((bname, parent, name))
                mesh_bones.append(len(bones) + known.index(bname) if bname in known else len(bones) + len(extra_bones) - 1)

        skin_idx = []
        skin_wt = []
        for (b1, w1, b2, w2) in m["skin"]:
            s0 = mesh_bones[b1] if b1 < len(mesh_bones) else 0
            s1 = mesh_bones[b2] if b2 < len(mesh_bones) else 0
            w0 = w1 / 65535.0
            w1n = w2 / 65535.0 if b2 < len(mesh_bones) and b2 >= 0 else 0.0
            if w1n > 0.0 and s1 == s0:
                s1 = s0
            skin_idx.extend([s0, s1, 0, 0])
            skin_wt.extend([w0, w1n, 0, 0])

        pos = []
        nrm = []
        uv = []
        for (p, n, u) in m["verts"]:
            pos.extend(p)
            nrm.extend(n)
            uv.extend(u)

        tex_rel = material_lookup.get(m["mat_name"])
        tex_name = None
        render = "opaque"
        if tex_rel:
            tex_name = os.path.basename(tex_rel).replace(".ddj", ".webp")
            webp_path = os.path.join(out_dir, tex_name)
            if not os.path.exists(webp_path):
                convert_texture(os.path.join(PRIM_DIR, tex_rel), webp_path)
            with Image.open(webp_path) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    hist = img.getchannel("A").histogram()
                    total = float(sum(hist))
                    zero_frac = hist[0] / total
                    partial_frac = sum(hist[1:255]) / total
                    if partial_frac > 0.4:
                        render = "translucent"
                    elif zero_frac > 0.03:
                        render = "alpha"
        elif m["mat_name"]:
            print(f"  ! no material for '{m['mat_name']}'")

        meshes.append(
            {
                "id": name,
                "tex": tex_name,
                "render": render,
                "pos": pos,
                "nrm": nrm,
                "uv": uv,
                "sk": skin_idx,
                "sw": skin_wt,
                "idx": m["indices"],
            }
        )

    for bname, parent, src in extra_bones:
        bones.append({"name": bname, "parent": bones[parent]["name"], "rot": [0, 0, 0, 1], "pos": [0, 0, 0]})
        print(f"[bone] extra {bname} (parent {bones[parent]['name']}) from {src}")

    parents, _, _ = build_bind_world(bones)
    bind_rot = []
    bind_pos = []
    for b in bones:
        bind_rot.extend(b["rot"])
        bind_pos.extend(b["pos"])

    print(f"[meta]")
    origins = [b["pos_origin"] for b in bones if "pos_origin" in b]
    foot_y = min(p[1] for p in origins)
    head_y = max(p[1] for p in origins)
    height = max(head_y - foot_y, 1.0)
    scale = preset.get("world_scale", 0.15)

    with open(os.path.join(out_dir, "skeleton.json"), "w") as f:
        json.dump({"names": [b["name"] for b in bones], "parents": parents, "bindRot": bind_rot, "bindPos": bind_pos}, f)

    with open(os.path.join(out_dir, "meshes.json"), "w") as f:
        json.dump({"meshes": meshes}, f)

    anims = []
    for aid, aname, rel in preset["anims"]:
        print(f"[anim] {aid} {rel}")
        a = parse_animation(read(rel))
        anim_bones = []
        for b in a["bones"]:
            bi = index.get(b["name"])
            if bi is None:
                continue
            anim_bones.append({"i": bi, "rot": b["rot"], "pos": b["pos"]})
        anims.append(
            {
                "id": aid,
                "name": aname,
                "dur": a["duration"],
                "loop": a["type"] == 1,
                "times": a["key_times"],
                "bones": anim_bones,
            }
        )
    with open(os.path.join(out_dir, "anims.json"), "w") as f:
        json.dump({"anims": anims}, f)

    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(
            {
                "preset": preset_name,
                "name": preset["name"],
                "race": preset.get("race"),
                "class": preset.get("class"),
                "bones": len(bones),
                "meshes": len(meshes),
                "height": round(height, 3),
                "scale": scale,
            },
            f,
        )

    total_bytes = sum(os.path.getsize(os.path.join(out_dir, fn)) for fn in os.listdir(out_dir))
    print(f"\nWrote {len(meshes)} meshes, {len(anims)} anims, {len(bones)} bones -> {out_dir} ({total_bytes/1024:.1f} KiB)")


if __name__ == "__main__":
    main()
