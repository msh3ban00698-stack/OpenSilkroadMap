#!/usr/bin/env python3
"""Build Phase 18 BSR fixtures from real Data.pk2 samples.

Commits raw sample .bsr bytes under scripts/testdata/formats/bsr_samples/ and
a parsed JSON fixture scripts/testdata/formats/bsr_phase18.json so the test
suite runs hermetically. Regenerate with:

    uv run scripts/build_bsr_fixture.py --pk2-dir <dir>   # or set SRO_PK2_DIR
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bsr_decoder as R  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "testdata", "formats", "bsr_phase18.json")
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "testdata", "formats", "bsr_samples")

SAMPLES = {
    "bandit": "/res/mob/china/bandit.bsr",
    "chinaquest_priest": "/res/npc/npc/chinaquest_priest.bsr",
    "movoi": "/res/mob/europe/movoi.bsr",
    "tre_tree03": "/res/nature/common/tree/new-maple/tre_tree03.bsr",
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
        with open(os.path.join(SAMPLES_DIR, key + ".bsr"), "wb") as fh:
            fh.write(raw)
        parsed = R.parse_bsr_references(raw)
        if parsed["error"]:
            raise SystemExit("sample %s parse error: %s" % (key, parsed["error"]))
        rec = {
            "path": path,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "is_character": parsed["is_character"],
            "group_order_ok": parsed["group_order_ok"],
            "materials": parsed["materials"],
            "meshes": parsed["meshes"],
            "animations": parsed["animations"],
            "skeleton": parsed["skeleton"],
            "effects": parsed["effects"],
            "sounds": parsed["sounds"],
            "header_table": parsed["header_table"],
        }
        fixture["samples"][key] = rec
    with open(OUT, "w") as fh:
        json.dump(fixture, fh, indent=1, sort_keys=True)
    print("wrote %s (%d samples)" % (OUT, len(fixture["samples"])))


if __name__ == "__main__":
    main()
