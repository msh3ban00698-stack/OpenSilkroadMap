"""Extract NPC and monster actors from authentic Data.pk2 BSR objects.

A .bsr object references its material, meshes, animations and skeleton.
This script parses those references, converts every referenced asset with
the proven JMXV parsers from extract_character.py and emits runtime actor
folders consumed by the client's generic actor loader:

    map/public/assets/img/silkroad/game/actor/<actor>/
        skeleton.json  meshes.json  anims.json  meta.json  *.webp

Usage: python3 scripts/extract_actors.py [npc|mob|all]
"""

import argparse
import json
import os
import re
import sys

import sro_paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_character import (  # noqa: E402
    build_bind_world,
    convert_texture,
    parse_animation,
    parse_material,
    parse_mesh,
    parse_skeleton,
)

OUT_BASE = "map/public/assets/img/silkroad/game/actor"
_pk2 = None

ANIM_RULES = [
    ("walk", "walk"),
    ("run", "run"),
    ("basic", "idle"),
    ("wait", "idle"),
    ("attack", "attack"),
    ("die", "death"),
    ("dead", "death"),
    ("dmg", "hit"),
]


def data_pk2():
    if _pk2 is None:
        raise RuntimeError("PK2 archive is not open; call main() first")
    return _pk2


def read_pk2(rel):
    p = rel.replace("\\", "/")
    if not p.startswith("/"):
        p = "/" + p
    d = data_pk2()
    entry = d.find(p)
    if entry is None:
        entry = d.find(p.lower())
    if entry is None:
        raise FileNotFoundError(rel)
    return d.read_file(entry)


def parse_bsr(blob):
    text = blob[:6000]
    strs = re.findall(rb"[\x20-\x7e\\]{6,}", text)
    out = {"mtrl": None, "meshes": [], "anims": [], "skel": None}
    for s in strs:
        v = s.decode(errors="ignore")
        low = v.lower().rstrip(".,+-\x00 ").replace("\\", "/")
        if low.endswith(".bmt") and not out["mtrl"]:
            out["mtrl"] = low
        elif low.endswith(".bms"):
            out["meshes"].append(low)
        elif low.endswith(".ban"):
            out["anims"].append(low)
        elif low.endswith(".bsk") and not out["skel"]:
            out["skel"] = low
    return out


def anim_id(name):
    base = os.path.basename(name).lower()
    stem = base.rsplit(".", 1)[0]
    for key, aid in ANIM_RULES:
        if key in stem:
            return aid
    return "idle"


def build_actor(name, bsr_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    spec = parse_bsr(read_pk2(bsr_path))
    print(f"{name}: {len(spec['meshes'])} meshes, {len(spec['anims'])} anims")

    bones = parse_skeleton(read_pk2(spec["skel"]))
    index = {b["name"]: i for i, b in enumerate(bones)}

    material_lookup = {}
    mrel = spec["mtrl"]
    if mrel:
        for mat in parse_material(read_pk2(mrel)):
            if mat["name"] not in material_lookup:
                material_lookup[mat["name"]] = os.path.join(os.path.dirname(mrel), mat["map"])

    meshes = []
    for mpath in spec["meshes"]:
        mname = os.path.splitext(os.path.basename(mpath))[0]
        try:
            m = parse_mesh(read_pk2(mpath))
        except Exception as e:
            print(f"  ! mesh {mname}: {e}")
            continue
        mesh_bones = []
        for bname in m["bones"]:
            mesh_bones.append(index.get(bname, 0))
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
        pos, nrm, uv = [], [], []
        for (p, n, u) in m["verts"]:
            pos.extend(p)
            nrm.extend(n)
            uv.extend(u)
        tex_name = None
        render = "opaque"
        tex_rel = material_lookup.get(m["mat_name"])
        if tex_rel:
            tex_name = os.path.basename(tex_rel).replace(".ddj", ".webp")
            webp_path = os.path.join(out_dir, tex_name)
            if not os.path.exists(webp_path):
                try:
                    convert_texture_tex(tex_rel, webp_path)
                except Exception as e:
                    print(f"  ! tex {tex_rel}: {e}")
                    tex_name = None
            if tex_name and os.path.exists(webp_path):
                from PIL import Image

                with Image.open(webp_path) as img:
                    if img.mode in ("RGBA", "LA", "P"):
                        hist = img.getchannel("A").histogram()
                        total = float(sum(hist)) or 1.0
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
                "id": mname,
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

    parents, _, _ = build_bind_world(bones)
    bind_rot, bind_pos = [], []
    for b in bones:
        bind_rot.extend(b["rot"])
        bind_pos.extend(b["pos"])

    origins = [b["pos_origin"] for b in bones if "pos_origin" in b]
    height = max((max(p[1] for p in origins) - min(p[1] for p in origins)), 1.0) if origins else 2.0

    with open(os.path.join(out_dir, "skeleton.json"), "w") as f:
        json.dump({"names": [b["name"] for b in bones], "parents": parents, "bindRot": bind_rot, "bindPos": bind_pos}, f)
    with open(os.path.join(out_dir, "meshes.json"), "w") as f:
        json.dump({"meshes": meshes}, f)

    seen_ids = set()
    anims = []
    for apath in spec["anims"]:
        aid = anim_id(apath)
        if aid in seen_ids:
            continue
        try:
            a = parse_animation(read_pk2(apath))
        except Exception as e:
            print(f"  ! anim {apath}: {e}")
            continue
        seen_ids.add(aid)
        anim_bones = []
        for b in a["bones"]:
            bi = index.get(b["name"])
            if bi is None:
                continue
            anim_bones.append({"i": bi, "rot": b["rot"], "pos": b["pos"]})
        anims.append(
            {
                "id": aid,
                "name": aid,
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
                "preset": name,
                "name": name,
                "source": bsr_path,
                "bones": len(bones),
                "meshes": len(meshes),
                "height": round(height, 3),
                "scale": 0.15,
            },
            f,
        )
    print(f"  -> {out_dir}")


def convert_texture_tex(tex_rel, webp_path):
    import struct

    from io import BytesIO

    from PIL import Image

    blob = read_pk2(tex_rel)
    img = Image.open(BytesIO(blob[20:])).convert("RGBA")
    img.save(webp_path, quality=80)


NPC_ACTORS = {
    "smith_eu": "res/npc/npc/EastEuropeShop_Smith.bsr",
    "grocery_eu": "res/npc/npc/EastEuropeShop_Accessory.bsr",
    "potion_eu": "res/npc/npc/EastEuropeShop_Potion.bsr",
    "special_eu": "res/npc/npc/EastEuropeShop_SpecialProduct.bsr",
    "warehouse_keeper": "res/npc/npc/EastEuropeQuest_GraveKeeper.bsr",
    "merchant_union": "res/npc/npc/EastEuropeSystem_MerchantUnion.bsr",
    "guild_master": "res/npc/npc/EastEuropeSystem_Guild.bsr",
    "port_manager": "res/npc/npc/EastEuropeSystem_PortManager.bsr",
    "soldier_a": "res/npc/npc/EastEuropeQuest_Soldier_Besaros.bsr",
    "soldier_b": "res/npc/npc/EastEuropeQuest_Soldier_Kasius.bsr",
    "priest": "res/npc/npc/EastEuropeQuest_Priest.bsr",
    "adventurer": "res/npc/npc/EastEuropeQuest_Adventure.bsr",
    "guide": "res/npc/npc/EastEuropeQuest_Lipria.bsr",
}

MOB_ACTORS = {
    "wolf": "res/mob/europe/wolf.bsr",
    "baroi": "res/mob/europe/baroi.bsr",
    "barpolle": "res/mob/europe/bartis.bsr",
    "dowb": "res/mob/europe/dowb.bsr",
    "kyklopes": "res/mob/europe/kyklopess.bsr",
    "lion": "res/mob/europe/lion.bsr",
}


def main():
    parser = argparse.ArgumentParser(description="Extract NPC and monster actors from Data.pk2")
    sro_paths.add_common_args(parser, pk2=True)
    parser.add_argument("which", nargs="?", default="npc", choices=("npc", "mob", "all"))
    args = parser.parse_args()
    try:
        pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
        reader_dir = sro_paths.resolve_reader_dir(args.reader_dir, pk2_dir)
        pk2reader = sro_paths.require_pk2_reader(reader_dir)
    except sro_paths.PipelineConfigError as exc:
        sys.exit("Error: {0}".format(exc))
    global _pk2
    _pk2 = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Data.pk2"))
    which = args.which
    todo = {}
    if which in ("npc", "all"):
        todo.update(NPC_ACTORS)
    if which in ("mob", "all"):
        todo.update(MOB_ACTORS)
    ok = 0
    for name, bsr in todo.items():
        try:
            build_actor(name, bsr.replace("\\", "/"), os.path.join(OUT_BASE, name))
            ok += 1
        except Exception as e:
            print(f"ACTOR FAIL {name}: {e}")
    print(f"done: {ok}/{len(todo)}")


if __name__ == "__main__":
    main()
