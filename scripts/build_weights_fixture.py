#!/usr/bin/env python3
"""Build Phase 19 Part C skinning-weight census fixture.

Extracts the bandit 3 mesh parts from the live archive, combines them with
the already-committed real character samples (player face, NPC chicken,
avatar meshes), runs skin_census on each, and writes
scripts/testdata/formats/weights_phase19.json with sha256 + census facts.

Regenerate with:
    uv run scripts/build_weights_fixture.py --pk2-dir <dir>  # or SRO_PK2_DIR
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

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "testdata", "formats", "weights_phase19.json")
SAMPLES_DIR = os.path.join(HERE, "testdata", "formats", "bms_weights_samples")

# (key, archive path or None for committed sample)
BANDIT_PARTS = {
    "bandit_sword": "/prim/mesh/mob/china/bandit_sword.bms",
    "bandit_part1": "/prim/mesh/mob/china/bandit_part1.bms",
    "bandit_part2": "/prim/mesh/mob/china/bandit_part2.bms",
}
COMMITTED = ["char_face.bms", "npc_chicken.bms", "petra.bms", "v50_avatar.bms"]


def _census_from_raw(key, raw, source):
    try:
        header = B.parse_bms_header(raw)
        vc = B.vertex_count(raw, header)
        census = B.skin_census(raw, header, vc)
        cross = B.skin_vertex_cross_check(raw, header, vc)
    except B.BmsFormatError as exc:
        return {"key": key, "source": source, "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "error": str(exc), "census": None, "cross_check": None}
    if not census.get("provable"):
        return {"key": key, "source": source, "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "error": census.get("reason"), "census": None, "cross_check": None}
    return {"key": key, "source": source, "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "census": census, "cross_check": cross}


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
    samples = {}
    for key, path in BANDIT_PARTS.items():
        e = by.get(path.lower())
        if e is None:
            raise SystemExit("missing %s -> %s" % (key, path))
        raw = read(e)
        with open(os.path.join(SAMPLES_DIR, key + ".bms"), "wb") as fh:
            fh.write(raw)
        samples[key] = _census_from_raw(key, raw, path)

    for name in COMMITTED:
        src = os.path.join(HERE, "testdata", "formats", "bms_samples", name)
        raw = open(src, "rb").read()
        with open(os.path.join(SAMPLES_DIR, name), "wb") as fh:
            fh.write(raw)
        samples[name.replace(".bms", "")] = _census_from_raw(
            name.replace(".bms", ""), raw, "committed bms_samples/" + name)

    with open(OUT, "w") as fh:
        json.dump({"samples": samples}, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
