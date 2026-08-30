"""Build the Phase 18 character rendering assets + manifest (offline, deterministic).

Chain resolved for the bandit NPC (all edges PROVEN from original archives):
  characterdata_*.txt refid 1949 -> mob\\china\\bandit.bsr
  npcpos.tsv rows for refid 1949 -> region/local coords -> world coords
  .bsr -> .bmt (base material) + .bms parts + .ban animations + .bsk skeleton
  .bms part -> material name (header names[1]) -> .ddj via .bmt (case-insensitive)
  .ddj -> DDS -> RGBA PNG
  .bms part -> MSH v2 (skinned) mesh asset
  .bsk -> skeleton.json (bind pose, [x,y,z,w] quaternions)
  .ban -> decoded keyframe JSON

Writes into android/app/src/main/assets/game/world/characters/bandit/:
  skeleton.json        bind skeleton (names, parents, local + world bind)
  meshes.tsv           per mesh part manifest
  mesh/*.msh           converted skinned meshes (MSH v2)
  tex/*.png            converted real textures
  anims.tsv            per animation manifest
  anim/*.json          decoded keyframes for stand01/walk
  npc_placements.tsv   real world spawns (ref sector 156x89, region 156x90)
  provenance.json      sha256 of every original input + resolved chain

Usage:  uv run scripts/build_character_manifest.py --pk2-dir <dir>
        (or set SRO_PK2_DIR)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import pk2_table  # noqa: E402
import world_terrain as wt  # noqa: E402
import sro_paths  # noqa: E402
import bsk_decoder  # noqa: E402
import bsr_decoder  # noqa: E402
import bms_decoder as B  # noqa: E402
import animation_pose as AP  # noqa: E402
import skeleton as SK  # noqa: E402
from dds_decode import ddj_to_rgba, png_from_rgba  # noqa: E402
from bms_to_asset import bms_to_msh_skinned  # noqa: E402

ASSETS = os.path.join(
    BASE, "..", "android", "app", "src", "main", "assets", "game", "world", "characters"
)
CHARACTER = "bandit"
REFID = "1949"
REF_SX, REF_SY = 156, 89

TEXTDATA = os.path.join(
    BASE, "..", "android", "app", "src", "main", "assets", "game", "textdata"
)


class ChainError(ValueError):
    pass


class _Pk2Reader:
    def __init__(self, pk2):
        self._entries, _ = pk2_table.inventory(pk2)
        self._by_path = {e["path"].lower(): e for e in self._entries}
        self._fh = open(pk2, "rb")

    def paths_matching(self, sub):
        return [e["path"] for e in self._entries if sub in e["path"].lower()]

    def read(self, path):
        key = ("/" + path.lstrip("/")).lower()
        e = self._by_path.get(key)
        if e is None:
            raise ChainError(f"missing in archive: {path}")
        self._fh.seek(e["pos"])
        return self._fh.read(e["size"])

    def close(self):
        self._fh.close()


def load_characterdata(read_media):
    """Join characterdata_*.txt (Media.pk2) on col1 (proven refid column)."""
    idx = {}
    for p in sorted(read_media.paths_matching("characterdata")):
        raw = read_media.read(p)
        try:
            text = raw.decode("utf-16-le", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            text = raw.decode("utf-8", errors="replace")
        for ln in text.split("\r\n"):
            cols = ln.split("\t")
            if len(cols) > 52 and cols[1].isdigit():
                idx.setdefault(cols[1], cols[52])
    return idx


def load_npcpos():
    rows = []
    with open(os.path.join(TEXTDATA, "npcpos.tsv"), encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if not ln.strip() or ln.startswith("character"):
                continue
            c = ln.split("\t")
            rows.append(c)
    return rows


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _bmt_materials(bmt_blob):
    return wt.parse_bmt(bmt_blob)


def resolve_texture(read_data, bmt_blob, bmt_path, material_ref):
    """material_ref (from bms names[1]) -> ddj path (case-insensitive)."""
    mats = _bmt_materials(bmt_blob)
    bmt_dir = os.path.dirname(bmt_path)
    want = material_ref.lower()
    for name, ddj in mats.items():
        if name.lower() == want:
            return (bmt_dir + "/" + ddj).replace("\\", "/")
    raise ChainError(f"material {material_ref!r} not in bmt {bmt_path}: {sorted(mats)}")


def build(out_dir, pk2_dir=None):
    pk2_dir = pk2_dir or os.environ.get("SRO_PK2_DIR")
    if not pk2_dir:
        raise SystemExit("--pk2-dir or SRO_PK2_DIR is required")
    data_pk2 = sro_paths.pk2_archive(pk2_dir, "Data.pk2")
    media_pk2 = sro_paths.pk2_archive(pk2_dir, "Media.pk2")
    read_data = _Pk2Reader(data_pk2)
    read_media = _Pk2Reader(media_pk2)
    try:
        return _build_with(read_data, read_media, out_dir)
    finally:
        read_data.close()
        read_media.close()


def _build_with(read_data, read_media, out_dir):
    out_dir = os.path.join(out_dir, CHARACTER)
    mesh_dir = os.path.join(out_dir, "mesh")
    tex_dir = os.path.join(out_dir, "tex")
    anim_dir = os.path.join(out_dir, "anim")
    for d in (mesh_dir, tex_dir, anim_dir):
        os.makedirs(d, exist_ok=True)

    provenance = {}

    # 1. characterdata -> bsr (col1 refid join, col52 model path)
    chardata = load_characterdata(read_media)
    bsr_rel = chardata.get(REFID)
    if not bsr_rel:
        raise ChainError(f"refid {REFID} missing from characterdata")
    bsr_path = "/res/" + bsr_rel.replace("\\", "/")
    bsr_blob = read_data.read(bsr_path)
    provenance["bsr"] = {"path": bsr_path, "sha256": sha256_bytes(bsr_blob)}
    parsed = bsr_decoder.parse_bsr_references(bsr_blob)
    if not parsed["is_character"]:
        raise ChainError(f"{bsr_path} is not a character bsr")

    # 2. skeleton
    bsk_path = parsed["skeleton"][0]
    bsk_blob = read_data.read(bsk_path)
    provenance["bsk"] = {"path": bsk_path, "sha256": sha256_bytes(bsk_blob)}
    skel = bsk_decoder.parse_bsk(bsk_blob)
    if not skel["exact"]:
        raise ChainError(f"bsk {bsk_path} not exact: {skel['error']}")
    wrot, wpos = SK.bind_world(skel["bones"])
    skeleton_json = {
        "path": bsk_path,
        "bone_count": len(skel["bones"]),
        "quaternion_convention": "xyzw",
        "bones": [
            {
                "name": b["name"],
                "parent": b["parent"],
                "children": b["children"],
                "rot_parent": [round(x, 6) for x in b["rot_parent"]],
                "tr_parent": [round(x, 6) for x in b["tr_parent"]],
                "bind_world_rot": [round(x, 6) for x in wrot[i]],
                "bind_world_pos": [round(x, 6) for x in wpos[i]],
            }
            for i, b in enumerate(skel["bones"])
        ],
    }
    with open(os.path.join(out_dir, "skeleton.json"), "w") as fh:
        json.dump(skeleton_json, fh, indent=1)

    # 3. meshes + textures
    base_bmt = parsed["materials"][0]
    bmt_blob = read_data.read(base_bmt)
    provenance["bmt"] = {"path": base_bmt, "sha256": sha256_bytes(bmt_blob)}
    mesh_rows = []
    mesh_prov = {}
    for idx, bms_path in enumerate(parsed["meshes"]):
        bms_blob = read_data.read(bms_path)
        mesh_prov[bms_path] = sha256_bytes(bms_blob)
        header = B.parse_bms_header(bms_blob)
        if len(header["names"]) < 2:
            raise ChainError(f"bms {bms_path} missing material name")
        material_ref = header["names"][1]
        ddj_path = resolve_texture(read_data, bmt_blob, base_bmt, material_ref)
        ddj_blob = read_data.read(ddj_path)
        provenance.setdefault("ddj", {})[ddj_path] = sha256_bytes(ddj_blob)
        msh_bytes, prov = bms_to_msh_skinned(bms_blob, texture_index=idx)
        stem = os.path.basename(bms_path)[:-4]
        msh_name = f"mesh/{stem}.msh"
        png_name = f"tex/{stem}.png"
        with open(os.path.join(out_dir, msh_name), "wb") as fh:
            fh.write(msh_bytes)
        w, h, rgba = ddj_to_rgba(ddj_blob)
        with open(os.path.join(out_dir, png_name), "wb") as fh:
            fh.write(png_from_rgba(w, h, rgba))
        mesh_rows.append({
            "part_idx": idx,
            "bms_path": bms_path,
            "material": material_ref,
            "ddj_path": ddj_path,
            "msh_asset": msh_name,
            "tex_asset": png_name,
            "vcount": prov["asset"]["vertex_count"],
            "tcount": prov["asset"]["triangle_count"],
            "skin_records": prov["asset"]["skin_records"],
            "bone_count": prov["asset"]["bone_count"],
        })
    with open(os.path.join(out_dir, "meshes.tsv"), "w") as fh:
        cols = ["part_idx", "bms_path", "material", "ddj_path", "msh_asset",
                "tex_asset", "vcount", "tcount", "skin_records", "bone_count"]
        fh.write("\t".join(cols) + "\n")
        for r in mesh_rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")

    # 4. animations (decode all, commit stand01 + walk)
    anim_rows = []
    anim_prov = {}
    for ban_path in parsed["animations"]:
        ban_blob = read_data.read(ban_path)
        anim_prov[ban_path] = sha256_bytes(ban_blob)
        anim = AP.load_keyframes(ban_blob)
        stem = os.path.basename(ban_path)[:-4]
        if stem in ("bandit_stand01", "bandit_walk"):
            anim_json = {
                "path": ban_path,
                "duration_ms": anim["duration_ms"],
                "timestamps": anim["timestamps"],
                "channels": {
                    name: [[[round(x, 6) for x in q], [round(x, 6) for x in p]]
                           for q, p in recs]
                    for name, recs in anim["channels"].items()
                },
            }
            with open(os.path.join(anim_dir, stem + ".json"), "w") as fh:
                json.dump(anim_json, fh, indent=1)
        anim_rows.append({
            "ban_path": ban_path,
            "name": stem,
            "duration_ms": anim["duration_ms"],
            "keyframes": len(anim["timestamps"]),
            "channels": len(anim["channels"]),
            "anim_asset": f"anim/{stem}.json" if stem in ("bandit_stand01", "bandit_walk") else "",
        })
    with open(os.path.join(out_dir, "anims.tsv"), "w") as fh:
        cols = ["ban_path", "name", "duration_ms", "keyframes", "channels", "anim_asset"]
        fh.write("\t".join(cols) + "\n")
        for r in anim_rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")

    # 5. NPC placements -> world coords (ref sector 156x89)
    placements = []
    for row in load_npcpos():
        if row[0] != REFID:
            continue
        region = int(row[1])
        x, z = float(row[2]), float(row[4])
        wx, wz = wt.npc_to_world(x, z, region, REF_SX, REF_SY)
        sx, sy = wt.unpack_region(region)
        placements.append({
            "refid": REFID,
            "region": region,
            "sector": f"{sx}x{sy}",
            "local_x": round(x, 3),
            "local_z": round(z, 3),
            "world_x": round(wx, 3),
            "world_z": round(wz, 3),
            "height": row[3],
        })
    with open(os.path.join(out_dir, "npc_placements.tsv"), "w") as fh:
        cols = ["refid", "region", "sector", "local_x", "local_z", "world_x",
                "world_z", "height"]
        fh.write("\t".join(cols) + "\n")
        for r in placements:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")

    # 6. provenance
    provenance["meshes"] = mesh_prov
    provenance["animations"] = anim_prov
    provenance["resolved"] = {
        "bsr": bsr_path,
        "bsk": bsk_path,
        "bmt": base_bmt,
        "bms": parsed["meshes"],
        "ban": parsed["animations"],
    }
    with open(os.path.join(out_dir, "provenance.json"), "w") as fh:
        json.dump(provenance, fh, indent=1, sort_keys=True)

    return {
        "skeleton_bones": len(skel["bones"]),
        "meshes": len(mesh_rows),
        "animations": len(anim_rows),
        "placements": len(placements),
        "out_dir": out_dir,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=ASSETS)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"),
                    help="Directory containing Data.pk2 (default: $SRO_PK2_DIR)")
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    res = build(args.out, args.pk2_dir)
    print("wrote %s: %d skeleton bones, %d meshes, %d anims, %d placements"
          % (res["out_dir"], res["skeleton_bones"], res["meshes"],
             res["animations"], res["placements"]))


if __name__ == "__main__":
    main()
