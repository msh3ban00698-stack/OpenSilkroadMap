"""Phase 12 Part D: convert the verified worldmap textures to WebP.

Source of truth is the ORIGINAL Media.pk2 archive (read-only). Only the .ddj
paths that resolve to a real file inside Media.pk2 (29 of 32 texture-path rows in
worldmap_mapinfo.tsv) are converted; the 3 unresolved paths (map_world_ tile-grid
prefix without extension, map_bagdad.ddj, map_bagdad_dungeon.ddj absent from the
archive) are listed in the manifest as UNRESOLVED and are never fabricated.

Outputs: android-assets/textures/worldmap/<name>.webp (Pillow WebP).
Provenance: TEXTURE_CONVERSION_MANIFEST.tsv (per-file: source path/size/
sha256_1mib, decoded dimensions, output path/size/sha256).

Run: uv run --with pillow scripts/convert_worldmap_textures.py --pk2-dir <dir>
(or set SRO_PK2_DIR)
"""

import argparse
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import pk2_table  # noqa: E402

from PIL import Image  # noqa: E402

TSV = Path("android/app/src/main/assets/game/textdata/worldmap_mapinfo.tsv")
OUT_DIR = Path("android-assets/textures/worldmap")
MANIFEST = Path("TEXTURE_CONVERSION_MANIFEST.tsv")


def texture_paths():
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


def read_entry(fh, files, path):
    entry = next(f for f in files if f["path"].lstrip("/") == path)
    fh.seek(entry["pos"])
    return fh.read(entry["size"])


def main():
    ap = argparse.ArgumentParser(description="Convert verified worldmap textures to WebP.")
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    args = ap.parse_args()
    if not args.pk2_dir:
        raise SystemExit("--pk2-dir or SRO_PK2_DIR is required")
    archive = str(Path(args.pk2_dir) / "Media.pk2")

    files, _ = pk2_table.inventory(archive)
    paths = set(f["path"].lstrip("/") for f in files)
    textures = texture_paths()
    os.makedirs(OUT_DIR, exist_ok=True)

    records = []
    with open(archive, "rb") as fh:
        for tex in textures:
            rec = {
                "source_archive": "Media.pk2",
                "source_path": tex,
                "status": "UNRESOLVED",
            }
            if tex in paths:
                data = read_entry(fh, files, tex)
                if data[:12] != b"JMXVDDJ 1000":
                    rec["status"] = "BAD_MAGIC"
                else:
                    try:
                        img = Image.open(io.BytesIO(data[20:]))
                        w, h = img.size
                        out = OUT_DIR / (tex.rsplit("/", 1)[-1].replace(".ddj", ".webp"))
                        img.convert("RGB").save(out, "WEBP", quality=85)
                        out_data = out.read_bytes()
                        rec.update(
                            {
                                "status": "CONVERTED",
                                "source_size": len(data),
                                "source_sha256_1mib": hashlib.sha256(data[:1048576]).hexdigest(),
                                "decoded_format": img.format,
                                "decoded_w": w,
                                "decoded_h": h,
                                "output_path": str(out),
                                "output_size": len(out_data),
                                "output_sha256": hashlib.sha256(out_data).hexdigest(),
                            }
                        )
                    except Exception as exc:  # noqa: BLE001
                        rec["status"] = f"DECODE_ERROR: {exc}"
            records.append(rec)
            print(f"{rec['status']:12} {tex}")

    header = [
        "source_archive", "source_path", "status", "source_size",
        "source_sha256_1mib", "decoded_format", "decoded_w", "decoded_h",
        "output_path", "output_size", "output_sha256",
    ]
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write("\t".join(header) + "\n")
        for rec in records:
            fh.write("\t".join(str(rec.get(h, "")) for h in header) + "\n")

    converted = sum(1 for r in records if r["status"] == "CONVERTED")
    unresolved = sum(1 for r in records if r["status"] == "UNRESOLVED")
    print(f"\nconverted={converted} unresolved={unresolved} -> {MANIFEST}")


if __name__ == "__main__":
    main()
