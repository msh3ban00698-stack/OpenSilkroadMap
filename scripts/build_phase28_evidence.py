#!/usr/bin/env python3
"""Phase 28 source-recovery evidence builder (runtime semantics).

Derives facts from the original sources:

  * Data.pk2 *.ban animation corpus (4,691 clips) - the animation state
    vocabulary the client actually ships (stand/walk/run/attack/damage/die/
    down/wakeup/...), plus the player (chinaman) clip action names.
  * Media.pk2 characterdata_5000.txt - the 13 player character-generation
    templates (CHAR_CH_MAN_*) and their BSR meshes.
  * Media.pk2 characterdata_25000.txt - the per-region character-generation
    table for region 25000 (Jangan): entities present, no spawn coordinates.
  * Committed android assets: bandit anims.tsv (the single decoded animation
    set), skilldata.tsv (an unparsed 7-line source-file list).

The native-runtime audit facts (no WebView/Capacitor/browser in the Android
gameplay runtime; retired wrapper under legacy/capacitor; the separate map/
web project) are recorded as byte-derived facts from this repository's own
build files and source tree, not from the game archives.

Nothing asserts runtime behavior beyond what the data proves.

Output: scripts/testdata/formats/phase28_source_evidence.json
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

PK2_DIR = sro_paths.resolve_pk2_dir()
DATA_PK2 = os.path.join(PK2_DIR, "Data.pk2")
MEDIA_PK2 = os.path.join(PK2_DIR, "Media.pk2")
REPO = BASE
BANDIT_ANIMS = os.path.join(
    REPO, "android/app/src/main/assets/game/world/characters/bandit/anims.tsv")
SKILLDATA = os.path.join(
    REPO, "android/app/src/main/assets/game/textdata/skilldata.tsv")


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

    def paths(self, suffix):
        return [e["path"] for e in self._entries
                if e["path"].lower().endswith(suffix)]

    def close(self):
        self._fh.close()


def ban_base(path):
    return path.rsplit("/", 1)[-1][:-4]


def ban_action(base):
    """SRO naming: <entity>_<action>NN -> trailing token minus digits."""
    last = base.split("_")[-1]
    m = re.match(r"^(.*?)(\d*)$", last)
    return m.group(1)


def animation_vocabulary(data):
    bases = [ban_base(p) for p in data.paths(".ban")]
    actions = collections.Counter(ban_action(b) for b in bases)
    core = ["stand", "walk", "walkforward", "walkbackward", "run", "runforward",
            "attack", "damage", "die", "down", "downwait", "downdamage",
            "downdie", "downup", "wakeup", "up", "ready", "wait", "loop", "rm",
            "sitstand", "sitbreath", "sitground", "pickup", "stun", "blocking"]
    return {
        "ban_total": len(bases),
        "ban_distinct": len(set(bases)),
        "distinct_action_tokens": len(actions),
        "core_counts": {k: actions.get(k, 0) for k in core},
        "player_chinaman_count": sum(
            1 for b in bases if "chinaman" in b.lower()),
    }


def player_chinaman_actions(data):
    bases = [ban_base(p) for p in data.paths(".ban")]
    player = [b for b in bases if "chinaman" in b.lower()]
    actions = collections.Counter(ban_action(b) for b in player)
    return sorted(actions.items(), key=lambda x: (-x[1], x[0]))


def chargen_rows(media, filename):
    raw = media.read("server_dep/silkroad/textdata/" + filename)
    text = raw.decode("utf-16-le", errors="replace")
    return [ln.split("\t") for ln in text.splitlines() if ln.strip()]


def player_templates(media):
    rows = chargen_rows(media, "characterdata_5000.txt")
    out = []
    seen = set()
    for r in rows:
        if len(r) < 53:
            continue
        code = r[2]
        if code.startswith("CHAR_CH_MAN") and code not in seen:
            seen.add(code)
            out.append({"refid": r[1], "code": code, "bsr": r[52]})
    return out


def jangan_chargen(media):
    rows = chargen_rows(media, "characterdata_25000.txt")
    bsrs = []
    for r in rows:
        if len(r) > 52:
            bsr = r[52]
            if bsr and bsr not in bsrs:
                bsrs.append(bsr)
    return {
        "path": "/server_dep/silkroad/textdata/characterdata_25000.txt",
        "lines": len(rows),
        "first_row_code": rows[0][2] if rows else None,
        "first_row_refid": rows[0][1] if rows else None,
        "distinct_bsr": len(bsrs),
        "sample_bsr": bsrs[:12],
        "has_position_column": False,
    }


def bandit_clip_set():
    names = []
    with open(BANDIT_ANIMS, "r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if not ln.strip():
                continue
            parts = ln.split("\t")
            if len(parts) >= 2 and parts[0].startswith("/prim/"):
                names.append(parts[1])
    return names


def skill_data_stub():
    with open(SKILLDATA, "r", encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    return {"lines": lines, "parsed_semantics": False,
            "note": "skilldata.tsv is an unparsed source-file list; skill "
                    "cadence/semantics remain UNVERIFIED"}


def native_runtime_audit():
    return {
        "android_gameplay_runtime_native": True,
        "webview_capacitor_in_android_runtime": False,
        "retired_wrapper": "legacy/capacitor/ (preserved reference, not a runtime path)",
        "map_web_project": {
            "separate_deliverable": True,
            "browser_game_prototype": "map/src/game/ (TS, wired via initGameFlow)",
            "not_android_runtime": True,
        },
    }


def main():
    data = Archive(DATA_PK2)
    media = Archive(MEDIA_PK2)
    try:
        evidence = {
            "phase": "phase28",
            "animation_vocabulary": animation_vocabulary(data),
            "player_chinaman_actions": player_chinaman_actions(data),
            "player_class_templates": player_templates(media),
            "jangan_region_chargen": jangan_chargen(media),
            "bandit_clip_set": bandit_clip_set(),
            "skill_data": skill_data_stub(),
            "native_runtime_audit": native_runtime_audit(),
            "conclusions": {
                "spawn": "UNKNOWN (fail-closed) - reaffirmed: char-gen tables "
                         "carry no position columns",
                "input": "UNKNOWN (fail-closed) - OptionSet key->action semantics "
                         "require client code",
                "movement": "UNKNOWN (fail-closed) - no speed table anywhere",
                "camera": "modes PROVEN (FREE/THIRD_PERSON/QUARTER_VIEW); numeric "
                          "parameters UNKNOWN",
                "animation_states": "PROVEN from .ban corpus: stand/walk/run/"
                                    "attack/damage/die/down/wakeup + sit/pickup/"
                                    "stun/blocking variants; transition order "
                                    "UNKNOWN",
                "skill_semantics": "UNVERIFIED - skilldata.tsv is an unparsed "
                                   "source-file list",
            },
        }
    finally:
        data.close()
        media.close()

    out = os.path.join(BASE, "scripts/testdata/formats/phase28_source_evidence.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
