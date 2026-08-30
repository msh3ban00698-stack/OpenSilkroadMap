#!/usr/bin/env python3
"""Build scripts/testdata/formats/bms_phase16.json from real BMS samples.

The fixture captures only PROVEN facts so the Phase 16 test suite runs
hermetically (no archive required). Regenerate with:

    uv run scripts/build_bms_fixture.py --pk2-dir <dir>   # or set SRO_PK2_DIR

Samples are read from Data.pk2 in the given directory; the raw
bytes are committed under scripts/testdata/formats/bms_samples/ so the
fixture builder and tests never depend on the archive.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as B  # noqa: E402
import sro_paths  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "testdata", "formats", "bms_phase16.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bms_samples")

SAMPLES = {
    "npc_chicken": "/prim/mesh/npc/animal/cj_chicken.bms",
    "char_face": "/prim/mesh/char/china/man/chinaman_adventurer_face.bms",
    "item_shield": "/prim/mesh/item/china/armor/ch_shield_11_set_a.bms",
    "artifact_table": "/prim/mesh/artifact/china/cj_ table_01.bms",
    "bldg_tree": "/prim/mesh/bldg/arabia/Bagh_Arabia_F/ArabianF_B_tree01.BMS",
    "v52_bldg": "/prim/mesh/bldg/arabia/Bagh_City/dungeon/Bagh_City_Dunin_L_01_01.BMS",
    "v44p5": "/prim/mesh/artifact/europe/east eurpoe/euro_constan_bumship01_07.bms",
    "v50_avatar": "/prim/mesh/avatar/booth_mob_mangyang.bms",
    "nature_tree": "/prim/mesh/nature/Arabia/Masin/Bagh_Masin_GSmalltree_01.BMS",
    "petra": "/prim/mesh/bldg/arabia/Bagh_Petra/Bagh_Petra_Core01.BMS",
    "demon": "/prim/mesh/dun/Demon/Fire/Demon_tower_Fire/demon_tower_mbrazier_fire.BMS",
}


def _find(pk2_files, path):
    low = path.lower()
    for e in pk2_files:
        if e["path"].lower() == low:
            return e
    return None


def _record(d, path):
    r = B.parse_bms(d)
    h = r["header"]
    out = {
        "path": path,
        "size": len(d),
        "version": h["version"],
        "header_size": h["header_size"],
        "offsets": h["offsets"],
        "off7": h["off7"],
        "end_offset": h["end_offset"],
        "names": h["names"],
        "skinned_vertex_count": h["skinned_vertex_count"],
        "vertex_format": {
            "vertex_size": r["vertex_format"]["vertex_size"],
            "layout": r["vertex_format"]["layout"],
            "lightmap_path": r["vertex_format"]["lightmap_path"],
            "non_unit_normals": r["vertex_format"]["non_unit_normals"],
        },
        "vertex_count": len(r["vertices"]),
        "vertices_sample": r["vertices"][:2],
        "bone_count": r["bones"]["bone_count"],
        "bone_names": r["bones"]["bone_names"],
        "bone_unparsed_bytes": r["bones"]["unparsed_bytes"],
        "triangle_count": r["triangles"]["triangle_count"],
        "triangle_prefix_bytes": r["triangles"]["prefix_bytes"],
        "triangles_sample": r["triangles"]["triangles"][:3],
        "aabb": r.get("aabb"),
        "extra_block_bytes": r.get("extra_block_bytes", 0),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pk2-dir",
        default=os.environ.get("SRO_PK2_DIR"),
        help="Directory containing Data.pk2 (default: $SRO_PK2_DIR)",
    )
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    pk2 = sro_paths.pk2_archive(args.pk2_dir, "Data.pk2")

    os.makedirs(SAMPLES_DIR, exist_ok=True)
    fixture = {}
    if os.path.exists(pk2):
        import pk2_table  # noqa: PLC0415
        entries, _ = pk2_table.inventory(pk2)
        for key, path in SAMPLES.items():
            e = _find(entries, path)
            if e is None:
                print(f"WARN sample missing from archive: {path}")
                continue
            with open(pk2, "rb") as fh:
                fh.seek(e["pos"])
                d = fh.read(e["size"])
            rec = _record(d, path)
            fixture[key] = rec
            with open(os.path.join(SAMPLES_DIR, key + ".bms"), "wb") as fh:
                fh.write(d)
            print(f"{key:14s} {rec['vertex_format']['layout']:>10s} "
                  f"vs={rec['vertex_format']['vertex_size']} "
                  f"vc={rec['vertex_count']} bones={rec['bone_count']} "
                  f"tris={rec['triangle_count']}")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(fixture, fh, indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
