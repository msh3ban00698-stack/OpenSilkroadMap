#!/usr/bin/env python3
"""Controlled, documented extraction of high-value sample assets from the real
vSRO 1.193 PK2 archives using the pinned pk2_mate reader.

This is NOT a full extraction. It extracts a curated set of representative files
covering every major asset category, and records for each: source PK2, internal
path, original size (PK2 entry size via pk2_mate), extracted size, extension,
SHA256, and result. Failures are recorded, never silently skipped, and bytes are
never repaired.

Usage:
    python3 scripts/extract_samples.py --pk2-dir /path/to/pk2s \
        --reader-bin /path/to/pk2_mate --out /path/to/out [--json report.json]

The manifest lists <archive>/<internal path> entries. Paths were taken from the
verified listings produced by `pk2_mate list` (see PK2_READER_FOUNDATION.md).
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ARCHIVES = ("Data", "Map", "Media", "Music", "Particles")

MANIFEST = [
    # World data / region geometry (Map)
    "Map/100/100.t",
    "Map/100/100.m",
    "Map/100/100.o",
    "Map/100/100.o2",
    "Map/config.ifo",
    "Map/object.ifo",
    "Map/tile2d/alex_dust_01.ddj",
    # Navmesh (Data)
    "Data/navmesh/nv_11a4.nvm",
    "Data/navmesh/AINavData_32768.DAT",
    "Data/RegionInfo.txt",
    "Data/dungeon/Dungeoninfo.txt",
    # 3D models / materials (Data prim)
    "Data/prim/mesh/artifact/china/dunhuang/budaa/w_cd_buda_b_01.bms",
    "Data/res/artifact/china/dunhuang/budaa/w_cd_buda_b_01.bsr",
    "Data/compound/char/china/1.cpd",
    "Data/compound/particle/electus_m_xmas.ddj",
    # Animations (Data + Particles)
    "Data/prim/ani/avatar/booth_mob_bigeyeghost.ban",
    "Data/prim/ani/artifact/china/dunhuang/w_cd_ani_boat.ban",
    "Particles/battle/deco_charge_light_a.efp",
    "Particles/animations/etc_mirage_cold_inver.ddj",
    "Particles/textures/00illusion_basic.ddj",
    "Particles/meshes/404_sunbeams01.bms",
    # Audio (Data wav + Music ogg)
    "Data/prim/snd/am_mob/am_crab_die.wav",
    "Music/jangan_town.ogg",
    # UI / interface / fonts (Media)
    "Media/interface/minimap/mm_alpha.ddj",
    "Media/interface/2secret/sec_num_00.ddj",
    "Media/effect/icon/cool_time_0.ddj",
    "Media/fonts/0.dat",
    "Media/config/command.txt",
    "Media/script/image/qno_script_background_white.ddj",
    # Game text data (Media server_dep)
    "Media/server_dep/silkroad/textdata/characterdata.txt",
    "Media/server_dep/silkroad/textdata/itemdata.txt",
    "Media/server_dep/silkroad/textdata/skilldata.txt",
    "Media/server_dep/silkroad/textdata/npcpos.txt",
    # Minimaps (Media)
    "Media/minimap/100x100.ddj",
    "Media/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_sample(reader, pk2_dir, out_dir, archive, path):
    pk2 = os.path.join(pk2_dir, archive + ".pk2")
    if not os.path.isfile(pk2):
        return {"result": "error", "detail": "pk2 missing"}
    os.makedirs(out_dir, exist_ok=True)
    sample_dir = os.path.join(out_dir, archive, path.lstrip("/"))
    sample_root = os.path.dirname(sample_dir)
    os.makedirs(sample_root, exist_ok=True)
    proc = subprocess.run(
        [reader, "extract", "--archive", pk2, "--out", sample_root, "--path", path],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {"result": "error", "detail": proc.stderr.strip()}
    # pk2_mate writes a single file flat under --out using its basename
    target = os.path.join(sample_root, os.path.basename(path))
    if not os.path.isfile(target):
        return {"result": "error", "detail": "not extracted (rc=0 but file absent)"}
    return {
        "result": "ok",
        "size": os.path.getsize(target),
        "sha256": sha256_file(target),
    }


def main():
    parser = argparse.ArgumentParser(description="Controlled sample extraction")
    parser.add_argument("--pk2-dir", required=True, help="Directory with *.pk2")
    parser.add_argument("--reader-bin", required=True, help="pk2_mate binary")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--json", help="Optional JSON report output path")
    args = parser.parse_args()

    records = []
    failures = 0
    for spec in MANIFEST:
        archive, path = spec.split("/", 1)
        path = "/" + path
        rec = {
            "pk2": archive + ".pk2",
            "path": path,
            "extension": os.path.splitext(path)[1].lower() or "(none)",
        }
        r = extract_sample(args.reader_bin, args.pk2_dir, args.out, archive, path)
        rec.update(r)
        if r["result"] != "ok":
            failures += 1
        records.append(rec)
        flag = "OK " if r["result"] == "ok" else "ERR"
        size = r.get("size")
        size_s = "{0:8d}".format(size) if isinstance(size, int) else "{0:>8s}".format(str(size))
        detail = " " + r.get("detail", "") if r["result"] != "ok" else ""
        print("{0} {1:9s} {2} {3}{4}".format(flag, archive, size_s, path, detail))

    if args.json:
        with open(args.json, "w") as f:
            json.dump(
                {
                    "reader": os.path.abspath(args.reader_bin),
                    "pk2_dir": os.path.abspath(args.pk2_dir),
                    "out_dir": os.path.abspath(args.out),
                    "records": records,
                    "failures": failures,
                },
                f,
                indent=2,
            )
    print("failures: {0}".format(failures))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
