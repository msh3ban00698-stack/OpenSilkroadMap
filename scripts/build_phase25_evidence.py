#!/usr/bin/env python3
"""Phase 25 source-recovery evidence builder (vSRO 1.193 archives).

Derives byte-level facts from the original PK2 archives into a single
machine-readable evidence file. Nothing here asserts runtime behavior;
every field is either read verbatim from a source file or derived with the
same proven decoders used in earlier phases.

Output: scripts/testdata/formats/phase25_source_evidence.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import animation_pose as AP  # noqa: E402
import bms_decoder as BMS  # noqa: E402
import bsr_decoder  # noqa: E402
import bsk_decoder  # noqa: E402
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

PK2_DIR = sro_paths.resolve_pk2_dir()
DATA_PK2 = os.path.join(PK2_DIR, "Data.pk2")
MEDIA_PK2 = os.path.join(PK2_DIR, "Media.pk2")

CHINA_CHAR_BSR_PREFIX = "/res/char/china/"
CHARACTER_SKELETONS = {
    "europeman_skel": "/prim/skel/char/europe/europeman_skel.bsk",
    "europewoman_skel": "/prim/skel/char/europe/europewoman_skel.bsk",
    "chinaman_skel": "/prim/skel/char/china/chinaman_skel.bsk",
    "chinawoman_skel": "/prim/skel/char/china/chinawoman_skel.bsk",
}
ITEM_SKELETONS = {
    "clothes_sa": "/prim/skel/item/china/clothes_sa.bsk",
    "sword_01": "/prim/skel/item/china/weapon/sword_01.bsk",
}

GEAR_MESHES = {
    "clothes_01_aa": "/prim/mesh/item/china/man_item/clothes_01_aa.bms",
    "clothes_01_ba": "/prim/mesh/item/china/man_item/clothes_01_ba.bms",
    "clothes_01_fa": "/prim/mesh/item/china/man_item/clothes_01_fa.bms",
    "clothes_01_ha": "/prim/mesh/item/china/man_item/clothes_01_ha.bms",
    "clothes_01_la": "/prim/mesh/item/china/man_item/clothes_01_la.bms",
    "clothes_01_sa": "/prim/mesh/item/china/man_item/clothes_01_sa.bms",
    "sword_01": "/prim/mesh/item/china/weapon/sword_01.bms",
}

PLAYER_ANIMS = [
    "/prim/ani/char/china/man/chinaman_standbattle.ban",
    "/prim/ani/char/china/man/chinaman_fighter_standcity.ban",
    "/prim/ani/char/china/man/chinaman_fighter_walkforward.ban",
    "/prim/ani/char/china/man/chinaman_fighter_runforward_sword.ban",
    "/prim/ani/char/china/man/chinaman_fighter_runforward.ban",
]


class Archive:
    def __init__(self, path):
        self.path = path
        self._entries, _ = pk2_table.inventory(path)
        self._by_path = {e["path"].lower(): e for e in self._entries}
        self._fh = open(path, "rb")

    def has(self, path):
        return ("/" + path.lstrip("/")).lower() in self._by_path

    def read(self, path):
        key = ("/" + path.lstrip("/")).lower()
        e = self._by_path.get(key)
        if e is None:
            raise KeyError(path)
        self._fh.seek(e["pos"])
        return self._fh.read(e["size"])

    def paths(self, sub):
        sub = sub.lower()
        return sorted(e["path"] for e in self._entries if sub in e["path"].lower())

    def sha(self, path):
        return hashlib.sha256(self.read(path)).hexdigest()

    def close(self):
        self._fh.close()


def build_bsr_table(data):
    rows = []
    for p in data.paths(CHINA_CHAR_BSR_PREFIX):
        if not p.lower().endswith(".bsr"):
            continue
        blob = data.read(p)
        parsed = bsr_decoder.parse_bsr_references(blob)
        rows.append({
            "bsr": p,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "is_character": parsed.get("is_character", False),
            "skeleton": parsed.get("skeleton", []),
            "meshes": len(parsed.get("meshes", [])),
            "materials": len(parsed.get("materials", [])),
            "animations": len(parsed.get("animations", [])),
            "skeleton_less": len(parsed.get("skeleton", [])) == 0,
        })
    return rows


def build_skeleton_info(data, skeletons):
    info = {}
    for name, path in skeletons.items():
        parsed = bsk_decoder.parse_bsk(data.read(path))
        bones = parsed["bones"]
        info[name] = {
            "path": path,
            "sha256": data.sha(path),
            "exact": parsed.get("exact"),
            "bone_count": len(bones),
            "bone_names": [b["name"] for b in bones],
        }
    return info


def mesh_bone_names(data, path):
    blob = data.read(path)
    header = BMS.parse_bms_header(blob)
    return BMS.parse_bone_table(blob, header)["bone_names"]


def build_gear_chain(data, skel_info):
    skel_sets = {k: set(v["bone_names"]) for k, v in skel_info.items()}
    items = {}
    for part, path in GEAR_MESHES.items():
        bones = mesh_bone_names(data, path)
        items[part] = {
            "bms": path,
            "sha256": data.sha(path),
            "bones": bones,
            "membership": {k: all(b in s for b in bones) for k, s in skel_sets.items()},
        }
    return items


def build_anim_channels(data, skel_info):
    skel_sets = {k: set(v["bone_names"]) for k, v in skel_info.items()}
    out = []
    for path in PLAYER_ANIMS:
        key = ("/" + path.lstrip("/")).lower()
        if key not in data._by_path:
            continue
        anim = AP.load_keyframes(data.read(path))
        names = list(anim["channels"].keys())
        out.append({
            "ban": path,
            "sha256": data.sha(path),
            "channels": len(names),
            "channel_names": names,
            "europeman_only_channels": [n for n in names if n not in skel_sets["chinaman_skel"]],
        })
    return out


def media_text(media, path, enc="latin-1"):
    return media.read(path).decode(enc, errors="replace")


def find_item_rows(rows, predicate):
    return [r for r in rows if predicate(r)]


def main():
    data = Archive(DATA_PK2)
    media = Archive(MEDIA_PK2)

    bsr_rows = build_bsr_table(data)
    histogram = {}
    for r in bsr_rows:
        for s in r["skeleton"]:
            histogram[s] = histogram.get(s, 0) + 1

    skel_info = build_skeleton_info(data, CHARACTER_SKELETONS)
    item_skel_info = build_skeleton_info(data, ITEM_SKELETONS)
    gear = build_gear_chain(data, {**skel_info, **item_skel_info})
    anims = build_anim_channels(data, skel_info)

    option_txt = media_text(media, "/config/option.txt")
    cameradata = media_text(media, "/config/cameradata.txt")
    command_txt = media_text(media, "/config/command.txt")

    char_rows = [
        l.split("\t") for l in
        media_text(media, "/server_dep/silkroad/textdata/characterdata_5000.txt",
                   enc="utf-16-le").split("\n") if "\t" in l
    ]
    item_rows = [
        l.split("\t") for l in
        media_text(media, "/server_dep/silkroad/textdata/itemdata_5000.txt",
                   enc="utf-16-le").split("\n") if "\t" in l
    ]

    start_row = next(r for r in char_rows if len(r) > 1 and r[1].strip() == "1907")
    clothes_rows = {}
    for code, part in {
        "ITEM_CH_M_CLOTHES_01_AA_A": "clothes_01_aa",
        "ITEM_CH_M_CLOTHES_01_BA_A": "clothes_01_ba",
        "ITEM_CH_M_CLOTHES_01_FA_A": "clothes_01_fa",
        "ITEM_CH_M_CLOTHES_01_HA_A": "clothes_01_ha",
        "ITEM_CH_M_CLOTHES_01_LA_A": "clothes_01_la",
        "ITEM_CH_M_CLOTHES_01_SA_A": "clothes_01_sa",
    }.items():
        r = next(x for x in item_rows if len(x) > 2 and x[2].strip() == code)
        clothes_rows[part] = {
            "id": r[1].strip(),
            "code": code,
            "bsr": r[52].strip() if len(r) > 52 else None,
            "ddj": r[54].strip() if len(r) > 54 else None,
        }
    sword_row = next(r for r in item_rows if len(r) > 2 and r[2].strip() == "ITEM_CH_SWORD_01_A")
    sword_info = {
        "id": sword_row[1].strip(),
        "code": "ITEM_CH_SWORD_01_A",
        "bsr": sword_row[52].strip() if len(sword_row) > 52 else None,
        "ddj": sword_row[54].strip() if len(sword_row) > 54 else None,
    }

    def line_fields(txt, key):
        for line in txt.split("\n"):
            if line.strip().startswith(key):
                return line.strip()
        return None

    evidence = {
        "phase": "phase25",
        "player_identity": {
            "option_start_character": line_fields(option_txt, "StartCharacter"),
            "option_map": line_fields(option_txt, "Map"),
            "option_intro_name": line_fields(option_txt, "IntroName"),
            "start_character_row": {
                "refid": start_row[1].strip(),
                "code": start_row[2].strip(),
                "model": start_row[52].strip() if len(start_row) > 52 else None,
                "radius": start_row[48].strip() if len(start_row) > 48 else None,
                "level": start_row[57].strip() if len(start_row) > 57 else None,
                "cols41_48": [start_row[i].strip() for i in range(41, 49)] if len(start_row) > 48 else None,
            },
        },
        "china_bsr_skeletons": bsr_rows,
        "china_bsr_skeleton_histogram": histogram,
        "character_skeletons": skel_info,
        "item_skeletons": item_skel_info,
        "gear_chain": gear,
        "itemdata_clothes": clothes_rows,
        "itemdata_sword": sword_info,
        "player_anims": anims,
        "cameradata": {
            "file": "/config/cameradata.txt",
            "first_line": cameradata.split("\n")[0].strip(),
            "rows": [line.split() for line in cameradata.split("\n")[1:] if line.strip()],
            "schema_semantics": "UNKNOWN (9 numeric fields; near/far/distance/fov/height/angle candidates NOT asserted)",
        },
        "command_verbs": {
            "setspeed": line_fields(command_txt, "/setspeed"),
            "setfov": line_fields(command_txt, "/setfov"),
            "camera": line_fields(command_txt, "/camera"),
            "zoom": line_fields(command_txt, "/zoom"),
            "fast": line_fields(command_txt, "/fast"),
            "getpos": line_fields(command_txt, "/getpos"),
        },
        "spawn": {
            "status": "UNKNOWN",
            "searched_media_substrings": ["start", "birth", "spawn", "login", "newchar", "create"],
            "searched_data_substrings": ["startpos", "spawn", "birth", "newchar", "login"],
            "searched_map_substrings": ["startpos", "spawn", "birth", "newchar", "login"],
            "conclusion": (
                "No static server-side start/spawn table exists in Data.pk2, "
                "Map.pk2 or Media.pk2. The only start evidence is client config "
                "(option.txt StartCharacter=1907, Map=0) and cinematic intro "
                "S_CameraInsert coordinates, neither of which is a spawn table. "
                "Player start location is set by the server runtime: UNKNOWN "
                "from client data, fail-closed."
            ),
        },
    }

    out_path = os.path.join(BASE, "scripts", "testdata", "formats",
                            "phase25_source_evidence.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
    print("wrote", out_path)
    print("bsr rows:", len(bsr_rows), "histogram:", histogram)
    print("player anims:", [(a["ban"].rsplit("/", 1)[-1], a["channels"]) for a in anims])

    data.close()
    media.close()


if __name__ == "__main__":
    main()
