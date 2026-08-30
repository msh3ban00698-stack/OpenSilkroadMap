#!/usr/bin/env python3
"""Build Phase 18 BSK fixtures from real Data.pk2 samples.

Commits raw sample .bsk bytes under scripts/testdata/formats/bsk_samples/ and
a parsed JSON fixture scripts/testdata/formats/bsk_phase18.json so the test
suite runs hermetically (no archive required). Regenerate with:

    uv run scripts/build_bsk_fixture.py --pk2-dir <dir>   # or set SRO_PK2_DIR
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsk_decoder as B  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "testdata", "formats", "bsk_phase18.json")
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

    os.makedirs(SAMPLES_DIR, exist_ok=True)
    fixture = {"samples": {}, "census": None}
    for key, path in SAMPLES.items():
        e = by.get(path.lower())
        if e is None:
            raise SystemExit("missing sample %s -> %s" % (key, path))
        raw = read(e)
        with open(os.path.join(SAMPLES_DIR, key + ".bsk"), "wb") as fh:
            fh.write(raw)
        parsed = B.parse_bsk(raw)
        if not parsed["exact"]:
            raise SystemExit("sample %s did not parse exactly: %s"
                             % (key, parsed["error"]))
        fixture["samples"][key] = {
            "path": path,
            "size": len(raw),
            "sha256": __import__("hashlib").sha256(raw).hexdigest(),
            "bone_count": parsed["bone_count"],
            "parsed_bytes": parsed["parsed_bytes"],
            "exact": True,
            "bones": parsed["bones"],
        }

    census = B.census_bsk(entries, read)
    fixture["census"] = {
        "total_nonzero": census["total_nonzero"],
        "exact": census["exact"],
        "inexact": census["inexact"],
        "zero": census["zero"],
    }
    with open(OUT, "w") as fh:
        json.dump(fixture, fh, indent=1, sort_keys=True)
    print("wrote %s (%d samples, census %d/%d exact)"
          % (OUT, len(fixture["samples"]), census["exact"],
             census["total_nonzero"]))


if __name__ == "__main__":
    main()
