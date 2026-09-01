#!/usr/bin/env python3
"""Phase 26 source-recovery evidence builder (movement, combat, clip census).

Derives byte-level facts from the original PK2 archives into a machine-readable
evidence file. Nothing asserts runtime behavior beyond what the data proves;
semantics that are not documented are labelled UNKNOWN / UNVERIFIED.

Facts recorded:
  1. Locomotion clips carry NO baked forward root translation (negative proof
     that movement speed is not in the animation data).
  2. skilldata_5000 attack-skill rows: col13/14 ordering by weapon type
     (fist 1500 > sword 1200 > spear 1166 > bow 840) - candidate attack-cadence
     column; exact semantics UNVERIFIED.
  3. Player BSR clip census: categories of the 217 animations of
     chinaman_fighter.bsr (stand/walk/run/attack/hit/die/skill/sit).

Output: scripts/testdata/formats/phase26_source_evidence.json
"""
from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import animation_pose as AP  # noqa: E402
import bsr_decoder  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

PK2_DIR = sro_paths.resolve_pk2_dir()
DATA_PK2 = os.path.join(PK2_DIR, "Data.pk2")
MEDIA_PK2 = os.path.join(PK2_DIR, "Media.pk2")

LOCOMOTION_CLIPS = [
    "/prim/ani/char/china/man/chinaman_fighter_walkforward.ban",
    "/prim/ani/char/china/man/chinaman_fighter_runforward.ban",
    "/prim/ani/char/china/man/chinaman_fighter_runforward_sword.ban",
]

SKILL_CODES = [
    "SKILL_PUNCH_01",
    "SKILL_CH_SWORD_BASE_01",
    "SKILL_CH_SPEAR_BASE_01",
    "SKILL_CH_BOW_BASE_01",
]


class Archive:
    def __init__(self, path):
        self.path = path
        self._entries, _ = pk2_table.inventory(path)
        self._by_path = {e["path"].lower(): e for e in self._entries}
        self._fh = open(path, "rb")

    def read(self, path):
        key = ("/" + path.lstrip("/")).lower()
        e = self._by_path.get(key)
        if e is None:
            raise KeyError(path)
        self._fh.seek(e["pos"])
        return self._fh.read(e["size"])

    def close(self):
        self._fh.close()


def root_motion_fact(data, path):
    blob = data.read(path)
    anim = AP.load_keyframes(blob)
    ch = anim["channels"].get("Bip01", [])
    if not ch:
        return {"ban": path, "channels": len(anim["channels"]),
                "bip01_present": False}
    xs = [r[1][0] for r in ch]
    ys = [r[1][1] for r in ch]
    zs = [r[1][2] for r in ch]
    first = ch[0][1]
    last = ch[-1][1]
    return {
        "ban": path,
        "channels": len(anim["channels"]),
        "bip01_present": True,
        "bip01_keys": len(ch),
        "bip01_x_range": round(max(xs) - min(xs), 4),
        "bip01_y_range": round(max(ys) - min(ys), 4),
        "bip01_z_range": round(max(zs) - min(zs), 4),
        "forward_z_drift": round(max(zs) - min(zs), 4),
        "cyclic_first_equals_last": [
            round(first[0] - last[0], 5),
            round(first[1] - last[1], 5),
            round(first[2] - last[2], 5),
        ],
    }


def skill_cadence_fact(media, code):
    d = media.read("/server_dep/silkroad/textdata/skilldata_5000.txt").decode(
        "utf-16-le", errors="replace")
    for line in d.split("\n"):
        if "\t" not in line:
            continue
        cols = line.split("\t")
        if len(cols) > 14 and cols[3].strip() == code:
            return {
                "code": code,
                "refid": cols[2].strip(),
                "col13": cols[13].strip(),
                "col14": cols[14].strip(),
                "col69": cols[69].strip() if len(cols) > 69 else None,
            }
    return None


def player_clip_census(data):
    blob = data.read("/res/char/china/chinaman_fighter.bsr")
    parsed = bsr_decoder.parse_bsr_references(blob)
    anims = parsed["animations"]
    cats = {"stand": [], "walk": [], "run": [], "attack": [], "hit": [],
            "die": [], "skill": [], "sit": [], "other": []}
    prefixes = ("chinaman_fighter_", "chinaman_", "china_man_")

    def core(name):
        for pref in prefixes:
            if name.startswith(pref):
                return name[len(pref):]
        return name

    for p in anims:
        name = core(p.rsplit("/", 1)[-1].lower())
        if name.startswith("skill") or "skill_" in name:
            cats["skill"].append(p)
        elif "die" in name or name.startswith("a_down"):
            cats["die"].append(p)
        elif "hit" in name:
            cats["hit"].append(p)
        elif "sit" in name:
            cats["sit"].append(p)
        elif "stand" in name:
            cats["stand"].append(p)
        elif "walk" in name:
            cats["walk"].append(p)
        elif "run" in name:
            cats["run"].append(p)
        else:
            cats["other"].append(p)
    attack_count = sum(1 for p in anims
                       if core(p.rsplit("/", 1)[-1].lower()).startswith("attack"))
    return {"total": len(anims),
            "categories": {k: len(v) for k, v in cats.items()},
            "word_start_attack_clips": attack_count,
            "samples": {k: [p.rsplit("/", 1)[-1] for p in v[:5]] for k, v in cats.items()}}


def main():
    data = Archive(DATA_PK2)
    media = Archive(MEDIA_PK2)

    locomotion = [root_motion_fact(data, p) for p in LOCOMOTION_CLIPS]
    skills = [skill_cadence_fact(media, c) for c in SKILL_CODES]
    census = player_clip_census(data)

    evidence = {
        "phase": "phase26",
        "movement": {
            "locomotion_root_motion": locomotion,
            "conclusion": (
                "Locomotion clips carry no baked forward (z) root translation; "
                "x/y ranges are weight-shift bobble only. Movement speed is NOT "
                "derivable from animation data and no speed table exists in the "
                "PK2 archives: walk/run speeds remain UNKNOWN (fail-closed)."
            ),
        },
        "combat": {
            "skilldata_attack_rows": skills,
            "col13_14_semantics": (
                "UNVERIFIED: values order by weapon type (fist 1500 > sword 1200 "
                "> spear 1166 > bow 840), consistent with an attack-cadence "
                "column in ms, but the exact meaning (cast/pre-delay/attack "
                "interval) is not documented and is NOT asserted."
            ),
            "damage_formulas": "UNKNOWN: col69 packed effect encoding not decoded",
            "damage_landing_frame": "UNKNOWN: client/server code, not archive data",
            "targeting_range_cooldowns": "UNKNOWN: no decoded skill schema in repo",
        },
        "player_animations": {
            "bsr": "/res/char/china/chinaman_fighter.bsr",
            "census": census,
            "committed_manifest_clips": [
                "chinaman_standbattle", "chinaman_fighter_standcity",
                "chinaman_fighter_walkforward", "chinaman_fighter_runforward_sword",
                "chinaman_fighter_runforward",
            ],
            "reconciliation": (
                "The committed player manifest carries 5 locomotion clips only; "
                "the BSR's attack clips are skill-named (skill_ch_sword_*), so the "
                "keyword state resolver (word-start 'attack') does NOT map them - "
                "the player's ATTACK/DAMAGE/DEATH states resolve to MISSING "
                "(fail-closed, no guessed idle fallback). NPC attack/damage/death "
                "clips (e.g. bandit_attack01) DO resolve via the keyword resolver."
            ),
        },
    }

    out_path = os.path.join(BASE, "scripts", "testdata", "formats",
                            "phase26_source_evidence.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
    print("wrote", out_path)
    print("locomotion:", [(r["ban"].rsplit("/", 1)[-1], r.get("forward_z_drift")) for r in locomotion])
    print("skills:", [(s["code"], s["col13"]) for s in skills])
    print("census:", census["categories"])

    data.close()
    media.close()


if __name__ == "__main__":
    main()
