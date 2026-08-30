#!/usr/bin/env python3
"""Phase 20 bulk character catalog builder (offline, deterministic).

Enumerates every spawning NPC, classifies its model(s) at component
granularity, converts every PROVEN model into a content-addressed shared
asset store, and emits:

  android/app/src/main/assets/game/world/characters/index.tsv     (refid->key)
  android/app/src/main/assets/game/world/characters/coverage.json (audit)
  shared/{skel,mesh,tex,anim}/<slug>.*                            (deduped assets)
  <key>/manifest.json + <key>/provenance.json + <key>/npc_placements.tsv

Usage: python3 scripts/build_character_catalog.py --pk2-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import pk2_table  # noqa: E402
import sro_paths  # noqa: E402
import build_character_manifest as BCM  # noqa: E402
import character_resolve as CR  # noqa: E402

ASSETS = os.path.join(
    BASE, "..", "android", "app", "src", "main", "assets",
    "game", "world", "characters")

INDEX_COLS = ["refid", "key", "variant", "status", "spawn_count"]


def enumerate_spawns(chardata, spawn_rows):
    """(spawn_refids, refid_models, model_spawn_counts) from npcpos rows.

    spawn_rows are raw npcpos columns (col0=refid). refid_models maps a
    spawning refid to its model list; model_spawn_counts counts spawn rows
    per distinct model path (first variant only).
    """
    spawn_refids = set()
    refid_models = {}
    model_counts = {}
    for row in spawn_rows:
        refid = row[0]
        spawn_refids.add(refid)
        models = chardata.get(refid)
        if not models:
            continue
        refid_models[refid] = models
        primary = models[0]
        model_counts[primary] = model_counts.get(primary, 0) + 1
    return spawn_refids, refid_models, model_counts


def _build(out_root, pk2_dir):
    data_pk2 = sro_paths.pk2_archive(pk2_dir, "Data.pk2")
    media_pk2 = sro_paths.pk2_archive(pk2_dir, "Media.pk2")
    read_data = BCM._Pk2Reader(data_pk2)
    read_media = BCM._Pk2Reader(media_pk2)
    try:
        return _build_with(read_data, read_media, out_root)
    finally:
        read_data.close()
        read_media.close()


def _build_with(read_data, read_media, out_root):
    os.makedirs(out_root, exist_ok=True)
    chardata = BCM.load_characterdata(read_media)
    spawn_rows = BCM.load_npcpos()
    spawn_refids, refid_models, model_counts = enumerate_spawns(chardata, spawn_rows)

    # Distinct model set across all spawning refids (comma-split already done).
    models = {}
    for refid, ms in refid_models.items():
        for m in ms:
            models.setdefault(m, refid)

    # All game data (.bsr/.bsk/.bms/.bmt/.ddj/.ban) lives in Data.pk2, so
    # existence checks must use read_data, not read_media (Media.pk2 only has
    # the characterdata_*.txt text files). classify_character expects read()
    # to raise KeyError when absent; _Pk2Reader.read raises ChainError, so wrap.
    def _read_keyerror(path):
        try:
            return read_data.read(path)
        except BCM.ChainError as exc:
            raise KeyError(path) from exc

    # Classify every distinct model.
    classified = {m: CR.classify_character(
        _read_keyerror, read_data._has, m) for m in sorted(models)}

    # Convert every PROVEN model + player; PARTIAL/UNKNOWN are documented only.
    index_rows = []
    audit_models = []
    proven = partial = unknown = 0
    for m in sorted(models):
        cls = classified[m]
        key = CR.slug(CR.bsr_path(m))
        if cls["status"] == CR.STATUS_PROVEN:
            try:
                BCM.convert_character(read_data, read_media, m, out_root, key)
            except Exception as exc:  # noqa: BLE001 - per-model fail-closed
                cls["status"] = CR.STATUS_PARTIAL
                cls["reasons"].append("conversion failed: %s" % exc)
        status = cls["status"]
        if status == CR.STATUS_PROVEN:
            proven += 1
        elif status == CR.STATUS_PARTIAL:
            partial += 1
        else:
            unknown += 1
        refids = [r for r, ms in refid_models.items() if m in ms]
        for refid in refids:
            variant = refid_models[refid].index(m)
            index_rows.append([refid, key, variant, status,
                               model_counts.get(m, 0)])
        audit_models.append({
            "refids": refids, "key": key, "model": m,
            "status": status, "spawn_count": model_counts.get(m, 0),
            "skeleton": cls["skeleton"],
            "mesh_parts": cls["meshes"],
            "animations": cls["animations"],
            "reasons": cls["reasons"],
        })

    # Player (always attempted; documented PARTIAL regardless).
    player_status = CR.STATUS_PARTIAL
    try:
        BCM.convert_player(read_data, read_media, out_root)
        player_ok = True
    except Exception as exc:  # noqa: BLE001
        player_ok = False
        player_status = CR.STATUS_UNKNOWN

    _write_index(out_root, index_rows)
    coverage = {
        "totals": {
            "spawn_rows": len(spawn_rows),
            "spawn_refids": len(spawn_refids),
            "refids_with_model": len(refid_models),
            "distinct_models": len(models),
            "proven_models": proven,
            "partial_models": partial,
            "unknown_models": unknown,
            "player": {"status": player_status, "converted": player_ok},
        },
        "models": audit_models,
    }
    with open(os.path.join(out_root, "coverage.json"), "w") as fh:
        json.dump(coverage, fh, indent=1, sort_keys=True)
    return coverage


def _write_index(out_root, rows):
    rows = sorted(rows, key=lambda r: (r[0], r[2]))
    with open(os.path.join(out_root, "index.tsv"), "w") as fh:
        fh.write("\t".join(INDEX_COLS) + "\n")
        for r in rows:
            fh.write("\t".join(str(c) for c in r) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=ASSETS)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    coverage = _build(args.out, args.pk2_dir)
    t = coverage["totals"]
    print("proven=%d partial=%d unknown=%d models=%d player=%s"
          % (t["proven_models"], t["partial_models"], t["unknown_models"],
             t["distinct_models"], t["player"]["status"]))


if __name__ == "__main__":
    main()
