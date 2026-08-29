#!/usr/bin/env python3
"""Prepare the on-device proof assets for the Phase 8 native minimap renderer.

Copies the real verified manifest and five representative minimap PNGs from the
committed android-assets tree into the gitignored native assets directory so
the instrumented tests (NativeMinimapRendererTest) can run against REAL assets
on a device/emulator:

    android/app/src/main/assets/minimap_proof/
        manifest.json
        maps/minimap/27x53.png
        maps/minimap/100x100.png
        maps/minimap/105x101.png
        maps/minimap/237x124.png
        maps/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.png

Representative set covers small / medium / large / a different region path.
Source paths are resolved through the manifest (never hard-coded filenames) and
every copied file's sha256 is verified against the manifest before copying.

Usage:
    python3 scripts/prepare_phase8_proof_assets.py
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_ASSETS = REPO / "android-assets"
MANIFEST = SRC_ASSETS / "manifest.json"
DST_ROOT = REPO / "android" / "app" / "src" / "main" / "assets" / "minimap_proof"

PROOF_SOURCES = [
    "/minimap/27x53.ddj",
    "/minimap/100x100.ddj",
    "/minimap/105x101.ddj",
    "/minimap/237x124.ddj",
    "/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
]


def phase_rank(phase):
    try:
        return int(str(phase).replace("phase", ""), 10)
    except ValueError:
        return 0


def pick_preferred(records):
    return sorted(records, key=lambda r: (-phase_rank(r.get("phase", "")), r.get("output_path", "")))[0]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if not MANIFEST.exists():
        print(f"FAIL: manifest not found: {MANIFEST}")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_source = {}
    for record in manifest["records"]:
        by_source.setdefault(record["source_path"], []).append(record)

    DST_ROOT.mkdir(parents=True, exist_ok=True)
    copied = []

    dst_manifest = DST_ROOT / "manifest.json"
    shutil.copyfile(MANIFEST, dst_manifest)
    if sha256_file(dst_manifest) != sha256_file(MANIFEST):
        print("FAIL: manifest copy sha256 mismatch")
        return 1
    copied.append(f"{dst_manifest.relative_to(REPO)} ({dst_manifest.stat().st_size} B)")

    for source in PROOF_SOURCES:
        records = by_source.get(source)
        if not records:
            print(f"FAIL: no manifest record for {source}")
            return 1
        preferred = pick_preferred(records)
        src = SRC_ASSETS / preferred["output_path"]
        if not src.exists():
            print(f"FAIL: source file missing: {src}")
            return 1
        digest = sha256_file(src)
        if digest != preferred.get("output_sha256", ""):
            print(f"FAIL: sha256 mismatch for {source}")
            return 1
        dst = DST_ROOT / preferred["output_path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        if sha256_file(dst) != digest:
            print(f"FAIL: copy sha256 mismatch for {source}")
            return 1
        copied.append(f"{dst.relative_to(REPO)} ({dst.stat().st_size} B)")

    print(f"OK: prepared {len(copied)} proof assets under {DST_ROOT.relative_to(REPO)}/")
    for entry in copied:
        print("  " + entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
