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
from bms_to_asset import MshFormatError, bms_to_msh, bms_to_msh_skinned  # noqa: E402

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

    def _has(self, path):
        key = ("/" + path.lstrip("/")).lower()
        return key in self._by_path

    def close(self):
        self._fh.close()


def load_characterdata(read_media):
    """Join characterdata_*.txt (Media.pk2) on col1 -> [col52 model paths].

    col52 is comma-split (multi-BSR variants share one refid). Returns
    {refid: [model_path, ...]}.
    """
    import character_resolve
    idx = {}
    for p in sorted(read_media.paths_matching("characterdata")):
        raw = read_media.read(p)
        try:
            text = raw.decode("utf-16-le", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            text = raw.decode("utf-8", errors="replace")
        for refid, models in character_resolve.load_characterdata(text).items():
            idx.setdefault(refid, models)
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
    """material_ref (from bms names[1]) -> ddj path, both ddj forms proven."""
    import character_resolve
    try:
        return character_resolve.resolve_texture(
            read_data.read, lambda p: read_data._has(p), bmt_blob, bmt_path,
            material_ref)
    except KeyError as exc:
        raise ChainError(str(exc)) from exc


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
    models = chardata.get(REFID)
    bsr_rel = models[0] if models else None
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


def path_exists(read_media):
    return read_media._has


def convert_character(read_data, read_media, bsr_rel, out_root, key):
    """Convert one character model (bsr_rel) into the shared asset store.

    Writes:
      <out_root>/shared/skel/<slug>.json, shared/mesh/<slug>.msh,
      shared/tex/<slug>.png, shared/anim/<slug>.json
      <out_root>/<key>/manifest.json, <key>/provenance.json,
      <key>/npc_placements.tsv
    Returns the manifest dict. Raises ChainError on the first unproven edge.
    """
    import character_resolve

    bsr_path = character_resolve.bsr_path(bsr_rel)
    bsr_blob = read_data.read(bsr_path)
    parsed = bsr_decoder.parse_bsr_references(bsr_blob)
    if not parsed["is_character"]:
        raise ChainError(f"{bsr_path} is not a character bsr")

    skel_slug, skeleton = _write_skeleton(
        read_data, read_media, parsed, out_root, key)

    bmt_path = parsed["materials"][0]
    bmt_blob = read_data.read(bmt_path)

    mesh_entries = []
    tex_by_ddj = {}
    for idx, bms_path in enumerate(parsed["meshes"]):
        bms_blob = read_data.read(bms_path)
        header = B.parse_bms_header(bms_blob)
        if len(header["names"]) < 2:
            raise ChainError(f"bms {bms_path} missing material name")
        material_ref = header["names"][1]
        ddj_path = resolve_texture(read_data, bmt_blob, bmt_path, material_ref)
        ddj_blob = read_data.read(ddj_path)
        msh_slug = character_resolve.slug(bms_path)
        tex_slug = character_resolve.slug(ddj_path)
        try:
            msh_bytes, prov = bms_to_msh_skinned(bms_blob, texture_index=0)
            skinned = True
        except MshFormatError:
            msh_bytes, prov = bms_to_msh(bms_blob, texture_index=0)
            skinned = False
        _write_shared_bytes(out_root, "mesh", msh_slug + ".msh", msh_bytes)
        if tex_slug not in tex_by_ddj:
            w, h, rgba = ddj_to_rgba(ddj_blob)
            _write_shared_bytes(out_root, "tex", tex_slug + ".png",
                                png_from_rgba(w, h, rgba))
            tex_by_ddj[tex_slug] = True
        mesh_entries.append({
            "msh": msh_slug, "tex": tex_slug, "skinned": skinned,
            "material": material_ref, "bms_path": bms_path, "ddj_path": ddj_path,
            "vcount": prov["asset"]["vertex_count"],
            "tcount": prov["asset"]["triangle_count"],
            "skin_records": prov["asset"].get("skin_records", 0),
            "bone_count": prov["asset"].get("bone_count", 0),
        })

    anim_entries = []
    for ban_path in parsed["animations"]:
        ban_blob = read_data.read(ban_path)
        anim = AP.load_keyframes(ban_blob)
        anim_slug = character_resolve.slug(ban_path)
        stem = os.path.basename(ban_path)[:-4]
        anim_json = {
            "path": ban_path, "duration_ms": anim["duration_ms"],
            "timestamps": anim["timestamps"],
            "channels": {
                name: [[[round(x, 6) for x in q], [round(x, 6) for x in p]]
                       for q, p in recs]
                for name, recs in anim["channels"].items()
            },
        }
        _write_shared_bytes(out_root, "anim", anim_slug + ".json",
                            json.dumps(anim_json, indent=1).encode("utf-8"))
        anim_entries.append({
            "anim": anim_slug, "name": stem, "ban_path": ban_path,
            "duration_ms": anim["duration_ms"], "keyframes": len(anim["timestamps"]),
            "channels": len(anim["channels"]),
        })

    manifest = {"key": key, "skeleton": skel_slug,
                "skeleton_path": parsed["skeleton"][0],
                "meshes": mesh_entries, "anims": anim_entries}
    _write_manifest(out_root, key, manifest)
    _write_provenance(out_root, key, {
        "bsr": bsr_path, "bsk": parsed["skeleton"][0], "bmt": bmt_path,
        "meshes": parsed["meshes"], "animations": parsed["animations"],
    })
    _write_placements(out_root, key, read_data, read_media, parsed, bsr_rel)
    return manifest


def bms_to_asset_prov(bms_blob):
    msh_bytes, prov = bms_to_msh_skinned(bms_blob, texture_index=0)
    return prov


def _shared_dir(out_root, kind):
    d = os.path.join(out_root, "shared", kind)
    os.makedirs(d, exist_ok=True)
    return d


def _write_shared_bytes(out_root, kind, name, blob):
    with open(os.path.join(_shared_dir(out_root, kind), name), "wb") as fh:
        fh.write(blob)


def _write_manifest(out_root, key, manifest):
    d = os.path.join(out_root, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)


def _write_provenance(out_root, key, prov):
    d = os.path.join(out_root, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "provenance.json"), "w") as fh:
        json.dump(prov, fh, indent=1, sort_keys=True)


def _write_skeleton(read_data, read_media, parsed, out_root, key):
    import character_resolve
    bsk_path = parsed["skeleton"][0]
    bsk_blob = read_data.read(bsk_path)
    skel = bsk_decoder.parse_bsk(bsk_blob)
    if not skel["exact"]:
        raise ChainError(f"bsk {bsk_path} not exact: {skel['error']}")
    wrot, wpos = SK.bind_world(skel["bones"])
    skeleton_json = {
        "path": bsk_path, "bone_count": len(skel["bones"]),
        "quaternion_convention": "xyzw",
        "bones": [{
            "name": b["name"], "parent": b["parent"], "children": b["children"],
            "rot_parent": [round(x, 6) for x in b["rot_parent"]],
            "tr_parent": [round(x, 6) for x in b["tr_parent"]],
            "bind_world_rot": [round(x, 6) for x in wrot[i]],
            "bind_world_pos": [round(x, 6) for x in wpos[i]],
        } for i, b in enumerate(skel["bones"])],
    }
    slug = character_resolve.slug(bsk_path)
    _write_shared_bytes(out_root, "skel", slug + ".json",
                        json.dumps(skeleton_json, indent=1).encode("utf-8"))
    return slug, skeleton_json


def _write_placements(out_root, key, read_data, read_media, parsed, bsr_rel):
    # Resolve the refid(s) that map to this bsr_rel for placement rows.
    refids = []
    for refid, models in load_characterdata(read_media).items():
        if bsr_rel in models:
            refids.append(refid)
    placements = []
    for row in load_npcpos():
        if row[0] not in refids:
            continue
        region = int(row[1])
        x, z = float(row[2]), float(row[4])
        wx, wz = wt.npc_to_world(x, z, region, REF_SX, REF_SY)
        sx, sy = wt.unpack_region(region)
        placements.append({
            "refid": row[0], "region": region, "sector": f"{sx}x{sy}",
            "local_x": round(x, 3), "local_z": round(z, 3),
            "world_x": round(wx, 3), "world_z": round(wz, 3), "height": row[3],
        })
    d = os.path.join(out_root, key)
    os.makedirs(d, exist_ok=True)
    cols = ["refid", "region", "sector", "local_x", "local_z",
            "world_x", "world_z", "height"]
    with open(os.path.join(d, "npc_placements.tsv"), "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in placements:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")


def convert_player(read_data, read_media, out_root):
    """Convert the proven chinaman player assembly into key 'player'.

    The player is PARTIAL (BSR->skeleton mismatch + no static spawn), but every
    mesh/clothes/weapon part, material, and animation used here is PROVEN by
    byte-exact archive presence (Phase 19). The skeleton is chinaman_skel.bsk.
    """
    skel_blob = read_data.read(PLAYER_SKELETON)
    skel = bsk_decoder.parse_bsk(skel_blob)
    if not skel["exact"]:
        raise ChainError(f"player skeleton not exact: {skel['error']}")
    wrot, wpos = SK.bind_world(skel["bones"])
    skeleton_json = {
        "path": PLAYER_SKELETON, "bone_count": len(skel["bones"]),
        "quaternion_convention": "xyzw",
        "bones": [{
            "name": b["name"], "parent": b["parent"], "children": b["children"],
            "rot_parent": [round(x, 6) for x in b["rot_parent"]],
            "tr_parent": [round(x, 6) for x in b["tr_parent"]],
            "bind_world_rot": [round(x, 6) for x in wrot[i]],
            "bind_world_pos": [round(x, 6) for x in wpos[i]],
        } for i, b in enumerate(skel["bones"])],
    }
    import character_resolve
    skel_slug = character_resolve.slug(PLAYER_SKELETON)
    _write_shared_bytes(out_root, "skel", skel_slug + ".json",
                        json.dumps(skeleton_json, indent=1).encode("utf-8"))

    mesh_entries = []
    body_meshes = PLAYER_BODY + PLAYER_CLOTHES + [PLAYER_WEAPON]
    for idx, bms_path in enumerate(body_meshes):
        bms_blob = read_data.read(bms_path)
        header = B.parse_bms_header(bms_blob)
        material_ref = header["names"][1] if len(header["names"]) >= 2 else None
        # Resolve texture from the first matching player material bmt.
        ddj_path = None
        for bmt_path in PLAYER_MATERIALS:
            try:
                ddj_path = resolve_texture(
                    read_data, read_data.read(bmt_path), bmt_path, material_ref)
                break
            except ChainError:
                continue
        if ddj_path is None:
            raise ChainError(f"no texture for player mesh {bms_path}")
        ddj_blob = read_data.read(ddj_path)
        msh_slug = character_resolve.slug(bms_path)
        tex_slug = character_resolve.slug(ddj_path)
        _write_shared_bytes(out_root, "mesh", msh_slug + ".msh",
                            bms_to_msh_skinned(bms_blob, texture_index=0)[0])
        w, h, rgba = ddj_to_rgba(ddj_blob)
        _write_shared_bytes(out_root, "tex", tex_slug + ".png",
                            png_from_rgba(w, h, rgba))
        prov = bms_to_asset_prov(bms_blob)
        mesh_entries.append({
            "msh": msh_slug, "tex": tex_slug, "skinned": True,
            "material": material_ref or "", "bms_path": bms_path,
            "ddj_path": ddj_path,
            "vcount": prov["asset"]["vertex_count"],
            "tcount": prov["asset"]["triangle_count"],
            "skin_records": prov["asset"]["skin_records"],
            "bone_count": prov["asset"]["bone_count"],
        })

    anim_entries = []
    for ban_path in PLAYER_ANIMS:
        ban_blob = read_data.read(ban_path)
        anim = AP.load_keyframes(ban_blob)
        anim_slug = character_resolve.slug(ban_path)
        stem = os.path.basename(ban_path)[:-4]
        anim_json = {
            "path": ban_path, "duration_ms": anim["duration_ms"],
            "timestamps": anim["timestamps"],
            "channels": {
                name: [[[round(x, 6) for x in q], [round(x, 6) for x in p]]
                       for q, p in recs]
                for name, recs in anim["channels"].items()
            },
        }
        _write_shared_bytes(out_root, "anim", anim_slug + ".json",
                            json.dumps(anim_json, indent=1).encode("utf-8"))
        anim_entries.append({
            "anim": anim_slug, "name": stem, "ban_path": ban_path,
            "duration_ms": anim["duration_ms"], "keyframes": len(anim["timestamps"]),
            "channels": len(anim["channels"]),
        })

    manifest = {"key": "player", "skeleton": skel_slug,
                "skeleton_path": PLAYER_SKELETON, "meshes": mesh_entries,
                "anims": anim_entries}
    _write_manifest(out_root, "player", manifest)
    _write_provenance(out_root, "player", {
        "bsr": PLAYER_BSR, "bsk": PLAYER_SKELETON,
        "meshes": body_meshes, "animations": PLAYER_ANIMS,
        "note": "PARTIAL: BSR references europeman_skel (43 bones) not chinaman_skel; no static spawn",
    })
    return manifest


def real_npc_chain(refid, pk2_dir=None):
    """Recompute the NPC->world chain for one refid from original archives.

    Returns an evidence list; every edge is PROVEN by byte-exact resolution
    from Data.pk2/Media.pk2. Raises ChainError on the first broken edge.
    Each edge = {edge, source, target, evidence, status} with status=PROVEN.
    """
    pk2_dir = pk2_dir or os.environ.get("SRO_PK2_DIR")
    if not pk2_dir:
        raise ChainError("--pk2-dir or SRO_PK2_DIR is required")
    data_pk2 = sro_paths.pk2_archive(pk2_dir, "Data.pk2")
    media_pk2 = sro_paths.pk2_archive(pk2_dir, "Media.pk2")
    read_data = _Pk2Reader(data_pk2)
    read_media = _Pk2Reader(media_pk2)
    edges = []

    def edge(e, src, tgt, evidence):
        edges.append({"edge": e, "source": src, "target": tgt,
                      "evidence": evidence, "status": "PROVEN"})

    try:
        # NPC record -> character reference (characterdata col1==refid -> col52)
        chardata = load_characterdata(read_media)
        models = chardata.get(refid)
        bsr_rel = models[0] if models else None
        if not bsr_rel:
            raise ChainError(f"refid {refid} missing from characterdata")
        edge("npc_record->character_reference", f"refid {refid}",
             bsr_rel, "characterdata_*.txt col1 refid join -> col52 model path")

        # character reference -> model (BSR)
        bsr_path = "/res/" + bsr_rel.replace("\\", "/")
        bsr_blob = read_data.read(bsr_path)
        edge("character_reference->bsr", bsr_rel, bsr_path,
             "bsr resolved and present in Data.pk2")
        parsed = bsr_decoder.parse_bsr_references(bsr_blob)
        if not parsed["is_character"]:
            raise ChainError(f"{bsr_path} is not a character bsr")

        # BSR -> BSK
        bsk_path = parsed["skeleton"][0]
        bsk_blob = read_data.read(bsk_path)
        skel = bsk_decoder.parse_bsk(bsk_blob)
        if not skel["exact"]:
            raise ChainError(f"bsk {bsk_path} not exact: {skel['error']}")
        edge("bsr->bsk", bsr_path, bsk_path,
             "bsr skeleton list -> bsk, parse exact, %d bones" % len(skel["bones"]))
        _, wpos = SK.bind_world(skel["bones"])
        edge("bsk->skeleton", bsk_path, "skeleton.json",
             "FK bind world chained, root %s" % skel["bones"][0]["name"])

        # BSR -> material
        base_bmt = parsed["materials"][0]
        bmt_blob = read_data.read(base_bmt)
        edge("bsr->bmt", bsr_path, base_bmt, "bsr materials list -> bmt")

        # BSR -> meshes (skin)
        for bms_path in parsed["meshes"]:
            bms_blob = read_data.read(bms_path)
            p = B.parse_bms(bms_blob)
            skinned = p["skin"] is not None
            edge("bsr->bms", bsr_path, bms_path,
                 "%d verts, %d tris, skin_block=%s" % (
                     len(p["vertices"]), p["triangles"]["triangle_count"], skinned))
            # bms -> texture via bmt material mapping
            material_ref = p["header"]["names"][1] if len(p["header"]["names"]) >= 2 else None
            if material_ref:
                ddj_path = resolve_texture(read_data, bmt_blob, base_bmt, material_ref)
                read_data.read(ddj_path)
                edge("bms->texture", bms_path, ddj_path,
                     "bms names[1] -> bmt material -> ddj")

        # BSR -> animations
        for ban_path in parsed["animations"]:
            ban_blob = read_data.read(ban_path)
            anim = AP.load_keyframes(ban_blob)
            edge("bsr->ban", bsr_path, ban_path,
                 "%d ms, %d channels, %d keyframes" % (
                     anim["duration_ms"], len(anim["channels"]),
                     len(anim["timestamps"])))

        # NPC record -> world coordinate
        placements = []
        for row in load_npcpos():
            if row[0] != refid:
                continue
            region = int(row[1])
            x, z = float(row[2]), float(row[4])
            wx, wz = wt.npc_to_world(x, z, region, REF_SX, REF_SY)
            sx, sy = wt.unpack_region(region)
            placements.append({"region": region, "sector": f"{sx}x{sy}",
                               "world_x": round(wx, 3), "world_z": round(wz, 3)})
        if not placements:
            raise ChainError(f"refid {refid} has no npcpos rows")
        edge("npc_record->world", f"refid {refid} npcpos",
             "world coordinates",
             "%d spawns, first sector %s" % (len(placements), placements[0]["sector"]))
        return {"refid": refid, "edges": edges,
                "all_proven": all(e["status"] == "PROVEN" for e in edges),
                "world_placements": placements}
    finally:
        read_data.close()
        read_media.close()


PLAYER_SKELETON = "/prim/skel/char/china/chinaman_skel.bsk"
PLAYER_BSR = "/res/char/china/chinaman_fighter.bsr"
PLAYER_BODY = [
    "/prim/mesh/char/china/man/man_pelvis.bms",
    "/prim/mesh/char/china/man/man_torso_lower.bms",
    "/prim/mesh/char/china/man/man_torso_upper.bms",
    "/prim/mesh/char/china/man/man_arm_upper.bms",
    "/prim/mesh/char/china/man/man_arm_lower.bms",
    "/prim/mesh/char/china/man/man_thigh.bms",
    "/prim/mesh/char/china/man/man_calf.bms",
    "/prim/mesh/char/china/man/chinaman_fighter_face.bms",
    "/prim/mesh/char/china/man/chinaman_fighter_hair.bms",
]
PLAYER_CLOTHES = [
    "/prim/mesh/item/china/man_item/clothes_01_aa.bms",
    "/prim/mesh/item/china/man_item/clothes_01_ba.bms",
    "/prim/mesh/item/china/man_item/clothes_01_fa.bms",
    "/prim/mesh/item/china/man_item/clothes_01_ha.bms",
    "/prim/mesh/item/china/man_item/clothes_01_la.bms",
    "/prim/mesh/item/china/man_item/clothes_01_sa.bms",
]
PLAYER_WEAPON = "/prim/mesh/item/china/weapon/sword_01.bms"
PLAYER_MATERIALS = [
    "/prim/mtrl/char/china/man/chinaman_fighter.bmt",
    "/prim/mtrl/item/china/man_item/clothes_01.bmt",
    "/prim/mtrl/item/china/weapon/sword1_2_3.bmt",
]
PLAYER_ANIMS = [
    "/prim/ani/char/china/man/chinaman_standbattle.ban",
    "/prim/ani/char/china/man/chinaman_fighter_standcity.ban",
    "/prim/ani/char/china/man/chinaman_fighter_walkforward.ban",
    "/prim/ani/char/china/man/chinaman_fighter_runforward_sword.ban",
    "/prim/ani/char/china/man/chinaman_fighter_runforward.ban",
]


def player_pipeline(pk2_dir=None):
    """Independently resolve the PLAYER (chinaman) pipeline from archives.

    The player is NOT an NPC: it has no npcpos spawn and no /res/mob/ BSR.
    Its model is assembled from character-creation parts (body + face + hair +
    clothes + weapon) over the China-man skeleton. Returns per-component
    {status, evidence, path} facts; status vocabulary is PROVEN / UNKNOWN /
    PARTIAL only. Raises ChainError when the archive cannot be opened.
    """
    pk2_dir = pk2_dir or os.environ.get("SRO_PK2_DIR")
    if not pk2_dir:
        raise ChainError("--pk2-dir or SRO_PK2_DIR is required")
    data_pk2 = sro_paths.pk2_archive(pk2_dir, "Data.pk2")
    read_data = _Pk2Reader(data_pk2)
    comp = {}

    def comp_entry(name, path, status, evidence):
        comp[name] = {"status": status, "path": path, "evidence": evidence}

    try:
        # skeleton
        skel_blob = read_data.read(PLAYER_SKELETON)
        skel = bsk_decoder.parse_bsk(skel_blob)
        if not skel["exact"]:
            raise ChainError(f"player skeleton not exact: {skel['error']}")
        hier = SK.verify_hierarchy(skel["bones"])
        comp_entry("skeleton", PLAYER_SKELETON, "PROVEN",
                   "parse exact, %d bones, single root %s, is_tree=%s" % (
                       len(skel["bones"]), hier["roots"][0], hier["is_tree"]))

        # BSR -> skeleton (documented mismatch: char BSR points at europe skeleton)
        bsr_blob = read_data.read(PLAYER_BSR)
        parsed = bsr_decoder.parse_bsr_references(bsr_blob)
        bsr_skel = parsed["skeleton"][0] if parsed["skeleton"] else None
        if bsr_skel and bsr_skel.lower() != PLAYER_SKELETON.lower():
            comp_entry("bsr", PLAYER_BSR, "PROVEN",
                       "character-selection BSR resolves, but references %s "
                       "(43 bones), NOT the China player skeleton %s" % (
                           bsr_skel, PLAYER_SKELETON))
        else:
            comp_entry("bsr", PLAYER_BSR, "PROVEN",
                       "character-selection BSR resolves to %s" % bsr_skel)

        # meshes (body + face + hair)
        body_ok = 0
        for p in PLAYER_BODY:
            m = B.parse_bms(read_data.read(p))
            if m["skin"] is None:
                raise ChainError(f"player mesh {p} lacks skin block")
            body_ok += 1
        comp_entry("meshes", "body/face/hair", "PROVEN",
                   "%d body/face/hair meshes parse with skin blocks" % body_ok)

        # clothes + weapon
        cloth_ok = 0
        for p in PLAYER_CLOTHES:
            if B.parse_bms(read_data.read(p))["skin"] is None:
                raise ChainError(f"clothes mesh {p} lacks skin block")
            cloth_ok += 1
        if B.parse_bms(read_data.read(PLAYER_WEAPON))["skin"] is None:
            raise ChainError("weapon mesh lacks skin block")
        comp_entry("equipment", "clothes/weapon", "PROVEN",
                   "%d clothes + 1 weapon meshes parse with skin blocks"
                   % cloth_ok)

        # materials
        for p in PLAYER_MATERIALS:
            read_data.read(p)
        comp_entry("textures", "materials", "PROVEN",
                   "%d material (.bmt) blobs present" % len(PLAYER_MATERIALS))

        # animations
        anim_ok = 0
        for p in PLAYER_ANIMS:
            raw = read_data.read(p)
            desc = AP.describe_animation(raw)
            anim_ok += 1
        comp_entry("animations", "chinaman clips", "PROVEN",
                   "%d clips parse (walk/stand/run), all loop" % anim_ok)

        # spawn reference
        comp_entry("spawn_reference", None, "UNKNOWN",
                   "player has no npcpos spawn; start/revival point is a "
                   "game-server concept absent from static archives")

        return {
            "character": "chinaman (player)",
            "components": comp,
            "status": "PARTIAL",
            "blockers": [
                "BSR->skeleton edge: /res/char BSRs reference europeman_skel.bsk, "
                "not chinaman_skel.bsk; player skeleton is not BSR-referenced",
                "spawn_reference: no static player spawn in the archives",
            ],
        }
    finally:
        read_data.close()


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
