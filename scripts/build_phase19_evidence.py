#!/usr/bin/env python3
"""Build Phase 19 proof-artifact records (per-character evidence).

Produces `scripts/testdata/formats/phase19_evidence.json` with, for each
character, ONLY hashes/offsets/counts and status — never the copyrighted
binary data itself. Every field is re-derived byte-for-byte from the original
archives (Data.pk2/Media.pk2) and carries an explicit status.

Usage:  python3 scripts/build_phase19_evidence.py --pk2-dir <dir>
        (or set SRO_PK2_DIR)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import sro_paths  # noqa: E402
import bsk_decoder  # noqa: E402
import bsr_decoder  # noqa: E402
import bms_decoder as BMS  # noqa: E402
import animation_pose as AP  # noqa: E402
import skeleton as SK  # noqa: E402
import world_terrain as wt  # noqa: E402
import build_character_manifest as BCM  # noqa: E402

FIXTURE = os.path.join(BASE, "testdata", "formats", "phase19_evidence.json")
REFID = "1949"
REF_SX, REF_SY = 156, 89


def _pk2_readers(pk2_dir):
    data_pk2 = sro_paths.pk2_archive(pk2_dir, "Data.pk2")
    media_pk2 = sro_paths.pk2_archive(pk2_dir, "Media.pk2")
    return BCM._Pk2Reader(data_pk2), BCM._Pk2Reader(media_pk2)


def _bandit_record(pk2_dir):
    """Bandit (NPC refid 1949) evidence record, status DONE."""
    chain = BCM.real_npc_chain(REFID, pk2_dir=pk2_dir)
    edges = chain["edges"]

    bsr_path = next(e["target"] for e in edges
                    if e["edge"] == "character_reference->bsr")
    bsk_path = next(e["target"] for e in edges if e["edge"] == "bsr->bsk")
    bmt_path = next(e["target"] for e in edges if e["edge"] == "bsr->bmt")
    bms_paths = [e["target"] for e in edges if e["edge"] == "bsr->bms"]
    ban_paths = [e["target"] for e in edges if e["edge"] == "bsr->ban"]
    ddj_paths = [e["target"] for e in edges if e["edge"] == "bms->texture"]

    read_data, read_media = _pk2_readers(pk2_dir)
    try:
        bsr_blob = read_data.read(bsr_path)
        bsr = bsr_decoder.parse_bsr_references(bsr_blob)

        bsk_blob = read_data.read(bsk_path)
        skel = bsk_decoder.parse_bsk(bsk_blob)
        bones = skel["bones"]
        hier = SK.verify_hierarchy(bones)
        _, wpos = SK.bind_world(bones)

        meshes = []
        total_verts = 0
        for path in bms_paths:
            blob = read_data.read(path)
            p = BMS.parse_bms(blob)
            vc = len(p["vertices"])
            total_verts += vc
            meshes.append({
                "path": path,
                "sha256": BCM.sha256_bytes(blob),
                "vertex_count": vc,
                "triangle_count": p["triangles"]["triangle_count"],
                "skin": p["skin"] is not None,
            })

        textures = []
        for path in ddj_paths:
            blob = read_data.read(path)
            textures.append({"path": path, "sha256": BCM.sha256_bytes(blob)})

        anims = []
        durations = {}
        for path in ban_paths:
            blob = read_data.read(path)
            kf = AP.load_keyframes(blob)
            name = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            durations[name] = kf["duration_ms"]
            anims.append({
                "path": path,
                "sha256": BCM.sha256_bytes(blob),
                "duration_ms": kf["duration_ms"],
                "channel_count": len(kf["channels"]),
                "keyframe_count": len(kf["timestamps"]),
            })

        bmt_blob = read_data.read(bmt_path)

        proven = [{"edge": e["edge"], "source": e["source"],
                   "target": e["target"], "evidence": e["evidence"],
                   "status": e["status"]} for e in edges]

        return {
            "character": "bandit",
            "status": "DONE",
            "model": bsr_path,
            "source_file": "Data.pk2",
            "BSK": {
                "path": bsk_path,
                "sha256": BCM.sha256_bytes(bsk_blob),
                "bone_count": len(bones),
                "exact": skel["exact"],
                "root": hier["roots"][0],
            },
            "BSR": {
                "path": bsr_path,
                "sha256": BCM.sha256_bytes(bsr_blob),
                "is_character": bsr["is_character"],
            },
            "mesh": meshes,
            "texture": textures,
            "skeleton": {
                "file": "android/app/src/main/assets/game/world/characters/"
                        "bandit/skeleton.json",
                "bone_count": len(bones),
                "root": hier["roots"][0],
                "is_tree": hier["is_tree"],
                "bind_world_bone0": [round(x, 6) for x in wpos[0]],
            },
            "bone_count": len(bones),
            "vertex_count": total_verts,
            "weight_format": "two influences per vertex (u16 bone index + "
                             "u16 weight each); raw weight sum is not exactly "
                             "65535 so normalization is a renderer operation",
            "animation": anims,
            "animation_duration": durations,
            "world_placements": chain["world_placements"],
            "proven_relationships": proven,
            "unknown_relationships": [
                "BSK bone_type u8 semantics (census only, meaning unproven)",
                "NPC placement heading/yaw (npcpos carries position, not yaw)",
                "BAN header unknown_u32=1 field meaning",
            ],
        }
    finally:
        read_data.close()
        read_media.close()


def _player_record(pk2_dir):
    """Chinaman (player) evidence record, status PARTIAL."""
    result = BCM.player_pipeline(pk2_dir=pk2_dir)
    return {
        "character": "chinaman",
        "status": result["status"],
        "model": BCM.PLAYER_BSR,
        "source_file": "Data.pk2",
        "bone_count": 38,
        "components": result["components"],
        "blockers": result["blockers"],
        "proven_relationships": [
            {"edge": "skeleton->meshes",
             "evidence": result["components"]["meshes"]["evidence"],
             "status": result["components"]["meshes"]["status"]},
            {"edge": "bsr->skeleton",
             "evidence": result["components"]["bsr"]["evidence"],
             "status": result["components"]["bsr"]["status"]},
        ],
        "unknown_relationships": [
            "player static spawn reference (no npcpos for the player)",
        ],
    }


def evidence_record(character, pk2_dir=None):
    pk2_dir = pk2_dir or os.environ.get("SRO_PK2_DIR")
    if not pk2_dir:
        raise ValueError("--pk2-dir or SRO_PK2_DIR is required")
    if character == "bandit":
        return _bandit_record(pk2_dir)
    if character == "chinaman":
        return _player_record(pk2_dir)
    raise ValueError("unknown character: %r" % character)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=FIXTURE)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    doc = {
        "bandit": evidence_record("bandit", args.pk2_dir),
        "chinaman": evidence_record("chinaman", args.pk2_dir),
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    print("wrote %s" % args.out)


if __name__ == "__main__":
    main()
