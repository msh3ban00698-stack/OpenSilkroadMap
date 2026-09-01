#!/usr/bin/env python3
"""Targeted format verification (Phase 29 source parity).

For each distinct file extension present in Data.pk2 / Map.pk2, extract ONE
representative sample (plus ALL text files) via the pinned pk2_mate reader and
record the leading magic bytes + inferred format family. Media/Music/Particles
samples are read directly from the existing full_extract tree (no extraction).

pk2_mate's `-p` extracts a single path into the output dir by basename, so each
sample is extracted into its own subdir to avoid name collisions and to detect
the single produced file.

Output: FORMAT_VERIFICATION.json (repo root).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

PK2_DIR = sro_paths.resolve_pk2_dir()
FULL_EXTRACT = sro_paths.resolve_full_extract_dir()
PK2_MATE = sro_paths.resolve_pk2_mate_dir()
WORK = sro_paths.resolve_work_dir()
REPO = BASE

MAGIC_TYPES = [
    (b"JMXVDDJ", "jmx-texture-ddj"),
    (b"JMXVBMS", "jmx-skeleton-bms"),
    (b"JMXVBSK", "jmx-skin-bsk"),
    (b"JMXVRES", "jmx-mesh-bsr"),
    (b"JMXVBAN", "jmx-animation-ban"),
    (b"JMXVEFP", "jmx-effect-efp"),
    (b"JMXVEFF", "jmx-effect-efp"),
    (b"JMXVNVM", "jmx-navmesh-nvm"),
    (b"JMXVCPD", "jmx-strings-cpd"),
    (b"JMXVIMG", "jmx-font-img"),
    (b"JMXVMAPT", "jmx-map-t"),
    (b"JMXVMFO", "jmx-map-info-mfo"),
    (b"JMXVMAPM", "jmx-map-model"),
    (b"JMXVMAPO", "jmx-map-object"),
    (b"JMXVBMT", "jmx-material-bmt"),
    (b"JMXVDOF", "jmx-dungeon-object-dof"),
    (b"JMXVOBJI", "jmx-object-info-ifo"),
    (b"SFPK", "soundfont-sfk"),
    (b"\x03\x00\x00\x00CNIF", "cnif-table"),
    (b"OggS", "ogg-audio"),
    (b"RIFF", "wav-audio"),
    (b"DDS ", "dds-texture"),
    (b"MZ", "pe-executable"),
    (b"\x89PNG", "png-texture"),
    (b"CNIF", "cnif-table"),
]


def infer_format(head):
    for magic, name in MAGIC_TYPES:
        if head.startswith(magic):
            return name
    if head.startswith(b"\xff\xd8"):
        return "jpeg-image"
    if head.startswith(b"\x00\x00\x02\x00"):
        return "tga-texture"
    if head.startswith(b"#include"):
        return "c-source"
    if head.startswith(b"vs.") or head.startswith(b"ps.") or head.startswith(b";"):
        return "shader-source"
    if head.startswith(b"\xff\xfe") or head.startswith(b"\xfe\xff"):
        return "utf16-text"
    return "unknown-magic"


def ext_of(path):
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else "(none)"


def extract_to_dir(archive, internal_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        [PK2_MATE, "extract", "-a", archive, "-o", out_dir, "-p", internal_path],
        capture_output=True, text=True, timeout=120,
    )
    files = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))]
    return files[0] if files else None


def is_text(blob):
    if blob.startswith(b"\xff\xfe") or blob.startswith(b"\xfe\xff"):
        return "utf-16"
    for encoding in ("utf-8", "cp949", "latin-1"):
        try:
            blob.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def sample_from_full_extract(archive_name, internal_path):
    rel = internal_path.lstrip("/")
    full = os.path.join(FULL_EXTRACT, archive_name.rsplit(".", 1)[0], rel)
    if os.path.isfile(full):
        with open(full, "rb") as fh:
            return fh.read(16)
    return None


def main():
    result = {}
    counter = 0

    for name in ("Data.pk2", "Map.pk2"):
        archive = os.path.join(PK2_DIR, name)
        files, _ = pk2_table.inventory(archive)
        per_ext = {}
        text_files = []
        for f in files:
            ext = ext_of(f["path"])
            if f["size"] <= 0:
                continue
            if ext == ".txt":
                text_files.append(f["path"])
                continue
            if ext not in per_ext or f["size"] < per_ext[ext][1]:
                per_ext[ext] = (f["path"], f["size"])

        # binary samples
        for ext, (ipath, isize) in sorted(per_ext.items()):
            counter += 1
            out_dir = os.path.join(WORK, f"sample_{counter}")
            local = extract_to_dir(archive, ipath, out_dir)
            if not local:
                result[f"{name}:{ext}"] = {"archive": name, "ext": ext, "path": ipath, "size": isize, "magic_hex": "", "format": "EXTRACT_FAILED"}
                continue
            with open(local, "rb") as fh:
                head = fh.read(16)
            result[f"{name}:{ext}"] = {
                "archive": name, "ext": ext, "path": ipath, "size": isize,
                "magic_hex": head.hex(), "format": infer_format(head),
            }

        # all text files
        for ipath in text_files:
            counter += 1
            out_dir = os.path.join(WORK, f"sample_{counter}")
            local = extract_to_dir(archive, ipath, out_dir)
            if not local:
                result[f"{name}:{ipath}"] = {"archive": name, "ext": ".txt", "path": ipath, "size": 0, "magic_hex": "", "format": "EXTRACT_FAILED"}
                continue
            with open(local, "rb") as fh:
                blob = fh.read()
            enc = is_text(blob)
            result[f"{name}:{ipath}"] = {
                "archive": name, "ext": ".txt", "path": ipath, "size": len(blob),
                "magic_hex": blob[:16].hex(), "format": "text" if enc else "binary",
                "encoding": enc or "binary", "readable": bool(enc),
            }

    # Media/Music/Particles samples read directly from full_extract
    for name in ("Media.pk2", "Music.pk2", "Particles.pk2"):
        archive = os.path.join(PK2_DIR, name)
        files, _ = pk2_table.inventory(archive)
        per_ext = {}
        for f in files:
            ext = ext_of(f["path"])
            if f["size"] <= 0:
                continue
            if ext not in per_ext or f["size"] < per_ext[ext][1]:
                per_ext[ext] = (f["path"], f["size"])
        for ext, (ipath, isize) in sorted(per_ext.items()):
            head = sample_from_full_extract(name, ipath)
            result[f"{name}:{ext}"] = {
                "archive": name, "ext": ext, "path": ipath, "size": isize,
                "magic_hex": head.hex() if head else "",
                "format": infer_format(head) if head else "NOT_EXTRACTED",
            }

    out = os.path.join(REPO, "FORMAT_VERIFICATION.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("format records :", len(result))
    print("wrote", out)


if __name__ == "__main__":
    main()
