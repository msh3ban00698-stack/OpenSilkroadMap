#!/usr/bin/env python3
"""Build Phase 19 Part F animation census fixture from the live archives.

Scans Data.pk2 + Particles.pk2 (the only archives containing .ban files) and
writes scripts/testdata/formats/animation_census_phase19.json with the
classification summary, magic/version histograms, and a sample record list.

Regenerate with:
    uv run scripts/build_anim_census_fixture.py --pk2-dir <dir>  # or SRO_PK2_DIR
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animation_census as AC  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "testdata", "formats", "animation_census_phase19.json")

ARCHIVES = ("Data.pk2", "Particles.pk2")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pk2-dir", default=None)
    args = parser.parse_args()
    pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)

    combined = {"counts": {}, "magic_histogram": {}, "version_histogram": {},
                "duration_buckets": {}, "samples": []}
    for arch in ARCHIVES:
        archive = os.path.join(pk2_dir, arch)
        entries, _ = pk2_table.inventory(archive)
        cache = {}

        def read(e, _arch=arch):
            if e["pos"] in cache:
                return cache[e["pos"]]
            need = e["size"] if e["path"].lower().endswith(".ban") else min(e["size"], 12)
            with open(os.path.join(pk2_dir, _arch), "rb") as fh:
                fh.seek(e["pos"])
                raw = fh.read(need)
            cache[e["pos"]] = raw
            return raw

        res = AC.scan_candidates(entries, read)
        for k in ("counts", "duration_buckets"):
            for kk, vv in res[k].items():
                combined[k][kk] = combined[k].get(kk, 0) + vv
        for kk, vv in res["magic_histogram"].items():
            combined["magic_histogram"][kk] = combined["magic_histogram"].get(kk, 0) + vv
        for kk, vv in res["version_histogram"].items():
            combined["version_histogram"][kk] = combined["version_histogram"].get(kk, 0) + vv
        combined["samples"].extend(res["samples"])
        combined.setdefault("anomalies", []).extend(res["anomalies"])

    with open(OUT, "w") as fh:
        json.dump(combined, fh, indent=1, sort_keys=True)
    print("wrote", OUT, "counts=", combined["counts"])


if __name__ == "__main__":
    main()
