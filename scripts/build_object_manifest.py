"""Build the Phase 17 object rendering assets + manifest (offline, deterministic).

Chain resolved per object (all edges PROVEN from original archives):
  sector .o2 placement -> nameI -> object.ifo -> .bsr -> .bms parts + .bmt
  .bms part -> material name (header names[1]) -> .ddj = material + ".ddj"
     resolved in the .bmt directory -> DDS -> RGBA PNG
  .bms part -> MSH1 mesh asset

Writes into android/app/src/main/assets/game/world/objects/:
  mesh/*.msh          converted real mesh parts (MSH1)
  tex/*.png           converted real textures (RGBA)
  models.tsv          one row per mesh part (real provenance)
  placements.tsv      one row per object instance (real placement)

Usage:  uv run scripts/build_object_manifest.py --pk2-dir <dir> [--sectors XxY ...]
        (or set SRO_PK2_DIR)
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import pk2_table  # noqa: E402
import world_terrain as wt  # noqa: E402
import bms_decoder as B  # noqa: E402
import sro_paths  # noqa: E402
from dds_decode import ddj_to_rgba, png_from_rgba  # noqa: E402
from bms_to_asset import bms_to_msh  # noqa: E402
from o2_decoder import parse_o2, parse_object_ifo_map  # noqa: E402

ASSETS = os.path.join(
    BASE, "..", "android", "app", "src", "main", "assets", "game", "world", "objects"
)
IFO_PATH = "/navmesh/object.ifo"


def archive_paths(pk2_dir):
    """Resolve Data/Map.pk2 through sro_paths (SRO_PK2_DIR / --pk2-dir)."""
    return (
        sro_paths.pk2_archive(pk2_dir, "Data.pk2"),
        sro_paths.pk2_archive(pk2_dir, "Map.pk2"),
    )


class ChainError(ValueError):
    pass


class _Pk2Reader:
    """Single-inventory archive reader; read(path) raises ChainError if missing."""

    def __init__(self, pk2):
        self._entries, _ = pk2_table.inventory(pk2)
        self._by_path = {e["path"].lower(): e for e in self._entries}
        self._fh = open(pk2, "rb")

    def read(self, path):
        key = ("/" + path.lstrip("/")).lower()
        e = self._by_path.get(key)
        if e is None:
            raise ChainError(f"missing in archive: {path}")
        self._fh.seek(e["pos"])
        return self._fh.read(e["size"])

    def close(self):
        self._fh.close()


def parse_bsr(blob):
    """Proven .bsr -> (material_path, [bms_paths]) (see world_terrain.parse_bsr)."""
    return wt.parse_bsr(blob)


def bmt_contains_ddj(bmt_blob, ddj):
    return ddj.encode("ascii", "replace") in bmt_blob


def resolve_models(read_data, object_index, nameI):
    """Resolve nameI -> list of (bms_path, material_name, ddj_path, msh_bytes, prov)."""
    bsr_path = object_index[nameI]
    bsr_blob = read_data.read(bsr_path)
    parsed = parse_bsr(bsr_blob)
    if parsed is None:
        raise ChainError(f"bsr unparsed: {bsr_path}")
    bmt_path, bms_paths = parsed
    bmt_blob = read_data.read(bmt_path)
    bmt_dir = os.path.dirname(bmt_path)
    models = []
    for idx, bms_path in enumerate(bms_paths):
        bms_blob = read_data.read(bms_path)
        header = B.parse_bms_header(bms_blob)
        if len(header["names"]) < 2:
            raise ChainError(f"bms names missing material: {bms_path}")
        material = header["names"][1]
        ddj_rel = material + ".ddj"
        ddj_path = (bmt_dir + "/" + ddj_rel).replace("\\", "/")
        if not bmt_contains_ddj(bmt_blob, ddj_rel):
            raise ChainError(f"bmt {bmt_path} lacks {ddj_rel} (material {material!r})")
        ddj_blob = read_data.read(ddj_path)
        msh_bytes, prov = bms_to_msh(bms_blob, texture_index=idx)
        models.append({
            "bms_path": bms_path,
            "material": material,
            "ddj_path": ddj_path,
            "ddj_blob": ddj_blob,
            "msh_bytes": msh_bytes,
            "provenance": prov,
        })
    return bsr_path, bmt_path, models


def build(out_dir, sectors, pk2_dir=None):
    pk2_dir = pk2_dir or os.environ.get("SRO_PK2_DIR")
    if not pk2_dir:
        raise SystemExit("--pk2-dir or SRO_PK2_DIR is required")
    data_pk2, map_pk2 = archive_paths(pk2_dir)
    read_data = _Pk2Reader(data_pk2)
    read_map = _Pk2Reader(map_pk2)
    try:
        return _build_with(read_data, read_map, out_dir, sectors)
    finally:
        read_data.close()
        read_map.close()


def _build_with(read_data, read_map, out_dir, sectors):
    ifo_blob = read_data.read(IFO_PATH)
    object_index = parse_object_ifo_map(ifo_blob.decode("ascii", "replace"))

    mesh_dir = os.path.join(out_dir, "mesh")
    tex_dir = os.path.join(out_dir, "tex")
    os.makedirs(mesh_dir, exist_ok=True)
    os.makedirs(tex_dir, exist_ok=True)

    model_rows = []
    placement_rows = []
    model_cache = {}

    for sector in sectors:
        sx, sy = sector
        path = f"/{sy}/{sx}.o2"
        try:
            o2_blob = read_map.read(path)
        except ChainError:
            continue  # sector has no object overlay
        placements = parse_o2(o2_blob)
        file_sector = (sx, sy)
        for p in placements:
            if p.nameI not in object_index:
                raise ChainError(f"nameI {p.nameI} missing from object.ifo")
            key = p.nameI
            if key not in model_cache:
                bsr, bmt, models = resolve_models(read_data, object_index, key)
                for i, m in enumerate(models):
                    stem = os.path.basename(m["bms_path"])[:-4]
                    msh_name = f"mesh/{stem}.msh"
                    png_name = f"tex/{stem}.png"
                    with open(os.path.join(out_dir, msh_name), "wb") as fh:
                        fh.write(m["msh_bytes"])
                    w, h, rgba = ddj_to_rgba(m["ddj_blob"])
                    with open(os.path.join(out_dir, png_name), "wb") as fh:
                        fh.write(png_from_rgba(w, h, rgba))
                    prov = m["provenance"]
                    model_rows.append({
                        "nameI": key,
                        "bsr": bsr,
                        "bmt": bmt,
                        "part_idx": i,
                        "bms_path": m["bms_path"],
                        "material": m["material"],
                        "ddj_path": m["ddj_path"],
                        "msh_asset": msh_name,
                        "tex_asset": png_name,
                        "layout": prov["source"]["layout"],
                        "vcount": prov["asset"]["vertex_count"],
                        "tcount": prov["asset"]["triangle_count"],
                        "non_static": prov["asset"]["non_static_vertices"],
                        "bone_count": prov["source"]["bone_count"],
                    })
                model_cache[key] = bsr
            placement_rows.append({
                "file_sx": file_sector[0], "file_sy": file_sector[1],
                "nameI": p.nameI,
                "x": round(p.x, 3), "y": round(p.y, 3), "z": round(p.z, 3),
                "theta": round(p.theta, 6), "tx": p.tx, "tz": p.tz,
                "u0": p.unknown0, "u1": p.unknown1,
            })

    with open(os.path.join(out_dir, "models.tsv"), "w") as fh:
        cols = ["nameI", "bsr", "bmt", "part_idx", "bms_path", "material", "ddj_path",
                "msh_asset", "tex_asset", "layout", "vcount", "tcount", "non_static",
                "bone_count"]
        fh.write("\t".join(cols) + "\n")
        for r in model_rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")
    with open(os.path.join(out_dir, "placements.tsv"), "w") as fh:
        cols = ["file_sx", "file_sy", "nameI", "x", "y", "z", "theta", "tx", "tz",
                "u0", "u1"]
        fh.write("\t".join(cols) + "\n")
        for r in placement_rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")

    return {
        "models": len(model_rows),
        "placements": len(placement_rows),
        "nameIs": sorted({r["nameI"] for r in model_rows}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sectors", nargs="+", default=["156x90"])
    ap.add_argument("--out", default=ASSETS)
    ap.add_argument(
        "--pk2-dir",
        default=os.environ.get("SRO_PK2_DIR"),
        help="Directory containing Data.pk2/Map.pk2 (default: $SRO_PK2_DIR)",
    )
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    sectors = []
    for s in args.sectors:
        x, _, y = s.partition("x")
        sectors.append((int(x), int(y)))
    report = build(args.out, sectors, args.pk2_dir)
    print(report)


if __name__ == "__main__":
    main()
