#!/usr/bin/env python3
"""Build Phase 18 BMS skin fixtures from real Data.pk2 samples.

Commits raw sample .bms bytes under scripts/testdata/formats/bms_skin_samples/
and a parsed JSON fixture scripts/testdata/formats/bms_skin_phase18.json so
the test suite runs hermetically. Regenerate with:

    uv run scripts/build_bms_skin_fixture.py --pk2-dir <dir>
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bms_decoder as B  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "testdata", "formats", "bms_skin_phase18.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bms_skin_samples")

SAMPLES = {
    "bandit_part1": "/prim/mesh/mob/china/bandit_part1.bms",
    "bandit_part2": "/prim/mesh/mob/china/bandit_part2.bms",
    "bandit_sword": "/prim/mesh/mob/china/bandit_sword.bms",
    "man_pelvis": "/prim/mesh/char/china/man/man_pelvis.bms",
    "man_arm_lower": "/prim/mesh/char/china/man/man_arm_lower.bms",
    "man_face": "/prim/mesh/char/china/man/chinaman_adventurer_face.bms",
    "man_hair": "/prim/mesh/char/china/man/chinaman_adventurer_hair.bms",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pk2-dir", default=None)
    args = parser.parse_args()
    pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
    archive = os.path.join(pk2_dir, "Data.pk2")
    entries, _ = pk2_table.inventory(archive)
    by = {e["path"].lower(): e for e in entries}

    def read(e):
        with open(archive, "rb") as fh:
            fh.seek(e["pos"])
            return fh.read(e["size"])

    os.makedirs(SAMPLES_DIR, exist_ok=True)
    fixture = {"samples": {}}
    for key, path in SAMPLES.items():
        e = by.get(path.lower())
        if e is None:
            raise SystemExit("missing sample %s -> %s" % (key, path))
        raw = read(e)
        with open(os.path.join(SAMPLES_DIR, key + ".bms"), "wb") as fh:
            fh.write(raw)
        r = B.parse_bms(raw)
        skin = r["skin"]
        if skin is None:
            raise SystemExit("sample %s has no skin block" % key)
        fixture["samples"][key] = {
            "path": path,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "vertex_count": len(r["vertices"]),
            "bone_names": r["bones"]["bone_names"],
            "skin_record_bytes": skin["record_bytes"],
            "single_influence": skin["single_influence"],
            "two_influence": skin["two_influence"],
            "two_influence_min_sum": min(skin["two_influence_sums"]) if skin["two_influence_sums"] else None,
            "two_influence_max_sum": max(skin["two_influence_sums"]) if skin["two_influence_sums"] else None,
            "skinned_vertex_count": r["header"]["skinned_vertex_count"],
            "records": skin["records"],
        }
    with open(OUT, "w") as fh:
        json.dump(fixture, fh, indent=1, sort_keys=True)
    print("wrote %s (%d samples)" % (OUT, len(fixture["samples"])))


if __name__ == "__main__":
    main()
