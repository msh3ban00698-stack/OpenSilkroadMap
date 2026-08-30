#!/usr/bin/env python3
"""Build Phase 19 Part A BSK census fixture from the live Data.pk2 archive.

Writes scripts/testdata/formats/bsk_census_phase19.json with:
  * group census (magic/version/size-bucket counts across ALL .bsk files)
  * raw bone_type u8 histogram (values only, no semantics)
  * per-sample census_record field evidence for the 5 Phase 18 samples

Regenerate with:
    uv run scripts/build_bsk_census_fixture.py --pk2-dir <dir>  # or SRO_PK2_DIR
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsk_decoder as B  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "testdata", "formats", "bsk_census_phase19.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsk_samples")

SAMPLES = {
    "chinaman_skel": "/prim/skel/char/china/chinaman_skel.bsk",
    "bandit": "/prim/skel/mob/china/bandit.bsk",
    "islamman": "/prim/skel/npc/china/chinaetc_islamman.bsk",
    "blackrobber": "/prim/skel/npc/china/blackrobber.bsk",
    "horse1": "/prim/skel/npc/china/chinaetc_horse1.bsk",
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

    census = B.group_census(entries, read)
    total_bones = 0
    for e in entries:
        if e["path"].lower().endswith(".bsk") and e["size"] > 0:
            r = B.parse_bsk(read(e))
            total_bones += r["bone_count"]

    samples = {}
    for key, path in SAMPLES.items():
        e = by.get(path.lower())
        if e is None:
            raise SystemExit("missing sample %s -> %s" % (key, path))
        raw = read(e)
        rec = B.census_record(raw)
        if not rec["exact"]:
            raise SystemExit("sample %s did not census exactly" % key)
        samples[key] = {
            "path": path,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "exact": rec["exact"],
            "bone_count": rec["bone_count"],
            "record_fields": rec["fields"],
        }

    fixture = {
        "groups": census["groups"],
        "bone_type_histogram": census["bone_type_histogram"],
        "census_total_nonzero": sum(g["count"] for g in census["groups"]),
        "census_total_bones": total_bones,
        "samples": samples,
    }
    with open(OUT, "w") as fh:
        json.dump(fixture, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
