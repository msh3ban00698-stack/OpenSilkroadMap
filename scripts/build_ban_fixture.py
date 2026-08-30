#!/usr/bin/env python3
"""Build Phase 18 BAN animation fixtures from real Data.pk2 samples.

Commits raw sample .ban bytes under scripts/testdata/formats/ban_phase18_samples/
and a parsed JSON fixture scripts/testdata/formats/ban_phase18.json so the test
suite runs hermetically. Regenerate with:

    uv run scripts/build_ban_fixture.py --pk2-dir <dir>
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animation_pose as AP  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "testdata", "formats", "ban_phase18.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "ban_phase18_samples")

SAMPLES = {
    "bandit_stand01": "/prim/ani/mob/china/bandit/bandit_stand01.ban",
    "bandit_walk": "/prim/ani/mob/china/bandit/bandit_walk.ban",
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
        with open(os.path.join(SAMPLES_DIR, key + ".ban"), "wb") as fh:
            fh.write(raw)
        anim = AP.load_keyframes(raw)
        fixture["samples"][key] = {
            "path": path,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "duration_ms": anim["duration_ms"],
            "timestamps": anim["timestamps"],
            "channel_names": sorted(anim["channels"].keys()),
            "channel_keyframe_counts": {
                k: len(v) for k, v in anim["channels"].items()
            },
        }
    with open(OUT, "w") as fh:
        json.dump(fixture, fh, indent=1, sort_keys=True)
    print("wrote %s (%d samples)" % (OUT, len(fixture["samples"])))


if __name__ == "__main__":
    main()
