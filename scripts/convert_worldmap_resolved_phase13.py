"""Phase 13 Part C: resolve and convert the 3 worldmap assets Phase 12 left UNRESOLVED.

The 3 unresolved texture refs in worldmap_mapinfo.tsv are now resolved against the
ORIGINAL Media.pk2 archive (read-only source of truth):

  1. interface/worldmap/map/map_world_          -> tile-grid prefix. Expands to 632
     real files /interface/worldmap/map/map_world_<cellx>x<celly>.ddj (128x128 DDS
     tiles, one per region-cell block). worldmap_mapinfo.tsv row 0 declares the
     montage geometry: 4224x1408 px = 132x44 region cells at 32 px/cell, tile =
     128 px = 4x4 cells ("4x4" tag). Tile placement is non-uniform (base grid
     every 4 cells plus interleaved denser rows and 45 out-of-bounds cells
     x>=199), so the exact montage layout is NOT reconstructed here; each tile is
     converted individually and layout is documented as UNKNOWN.
  2. interface/worldmap/map/map_bagdad.ddj        -> exists as Map_bagdad.ddj
     (case-insensitive match, 524436 B, 1024x1024).
  3. interface/worldmap/map/map_bagdad_dungeon.ddj -> exists as Map_bagdad_dungeon.ddj
     (case-insensitive match, 524436 B, 1024x1024).

Outputs: android-assets/textures/worldmap/<name>.webp (Pillow WebP), reusing the
Phase 12 converter conventions. TEXTURE_CONVERSION_MANIFEST.tsv is regenerated;
the 29 already-CONVERTED Phase 12 rows are reproduced byte-identically.

Run: uv run --with pillow scripts/convert_worldmap_resolved_phase13.py --pk2-dir <dir>
"""

import argparse
import hashlib
import io
import os
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import pk2_table  # noqa: E402

from PIL import Image  # noqa: E402

TSV = Path("android/app/src/main/assets/game/textdata/worldmap_mapinfo.tsv")
OUT_DIR = Path("android-assets/textures/worldmap")
MANIFEST = Path("TEXTURE_CONVERSION_MANIFEST.tsv")

HEADER = [
    "source_archive", "source_path", "status", "source_size",
    "source_sha256_1mib", "decoded_format", "decoded_w", "decoded_h",
    "output_path", "output_size", "output_sha256",
]


def texture_refs():
    rows = []
    with open(TSV, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            cells = line.rstrip("\n").split("\t")
            if len(cells) < 4:
                continue
            tex = cells[3]
            if tex.startswith("interface"):
                rows.append(tex.replace("\\", "/").lstrip("/"))
    return rows


def convert_one(data, out):
    img = Image.open(io.BytesIO(data[20:]))
    w, h = img.size
    img.convert("RGB").save(out, "WEBP", quality=85)
    return w, h


def make_record(archive_name, tex, files, fh):
    lower = tex.lower()
    exact = next((f for f in files if f["path"].lstrip("/") == tex), None)
    if exact is None:
        exact = next((f for f in files if f["path"].lstrip("/").lower() == lower), None)
    if exact is None:
        return {"source_archive": archive_name, "source_path": tex, "status": "UNRESOLVED"}
    data = read_entry(fh, exact)
    if data[:12] != b"JMXVDDJ 1000":
        return {"source_archive": archive_name, "source_path": tex, "status": "BAD_MAGIC"}
    out = OUT_DIR / (exact["path"].rsplit("/", 1)[-1].replace(".ddj", ".webp"))
    try:
        w, h = convert_one(data, out)
        out_data = out.read_bytes()
        return {
            "source_archive": archive_name,
            "source_path": exact["path"].lstrip("/"),
            "status": "CONVERTED",
            "source_size": len(data),
            "source_sha256_1mib": hashlib.sha256(data[:1048576]).hexdigest(),
            "decoded_format": "DDS",
            "decoded_w": w,
            "decoded_h": h,
            "output_path": str(out),
            "output_size": len(out_data),
            "output_sha256": hashlib.sha256(out_data).hexdigest(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "source_archive": archive_name, "source_path": tex,
            "status": f"DECODE_ERROR: {exc}",
        }


def read_entry(fh, entry):
    fh.seek(entry["pos"])
    return fh.read(entry["size"])


def main():
    ap = argparse.ArgumentParser(description="Convert resolved Phase 13 worldmap assets to WebP.")
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    args = ap.parse_args()
    if not args.pk2_dir:
        raise SystemExit("--pk2-dir or SRO_PK2_DIR is required")
    archive = str(Path(args.pk2_dir) / "Media.pk2")
    archive_name = Path(archive).name

    files, _ = pk2_table.inventory(archive)
    os.makedirs(OUT_DIR, exist_ok=True)

    records = []
    with open(archive, "rb") as fh:
        for tex in texture_refs():
            if "." not in tex.rsplit("/", 1)[-1]:
                prefix_lower = tex.lower()
                family = [
                    f for f in files
                    if f["path"].lstrip("/").lower().startswith(prefix_lower)
                    and f["path"].endswith(".ddj")
                ]
                if not family:
                    rec = {"source_archive": archive_name, "source_path": tex, "status": "UNRESOLVED"}
                    records.append(rec)
                    print(f"{rec['status']:12} {tex}")
                    continue
                rec = {
                    "source_archive": archive_name,
                    "source_path": tex,
                    "status": "RESOLVED_FAMILY",
                    "source_size": sum(f["size"] for f in family),
                    "decoded_format": "DDS",
                    "decoded_w": 128,
                    "decoded_h": 128,
                    "output_path": str(OUT_DIR / f"{tex.rsplit('/', 1)[-1]}*.webp ({len(family)} files)"),
                }
                records.append(rec)
                print(f"{rec['status']:12} {tex} -> {len(family)} files")
                for entry in sorted(family, key=lambda e: e["path"]):
                    sub = make_record(archive_name, entry["path"].lstrip("/"), files, fh)
                    records.append(sub)
                    print(f"  {sub['status']:12} {sub['source_path']}")
            else:
                rec = make_record(archive_name, tex, files, fh)
                records.append(rec)
                print(f"{rec['status']:12} {rec['source_path']}")

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write("\t".join(HEADER) + "\n")
        for rec in records:
            fh.write("\t".join(str(rec.get(h, "")) for h in HEADER) + "\n")

    counts = {}
    for rec in records:
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
    print(f"\nsummary: {counts} total_rows={len(records)} -> {MANIFEST}")


if __name__ == "__main__":
    main()
