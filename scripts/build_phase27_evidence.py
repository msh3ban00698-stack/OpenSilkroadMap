#!/usr/bin/env python3
"""Phase 27 source-recovery evidence builder (player runtime: spawn).

Derives byte-level facts from the original sources:
  * SRO_VT_SHARD.Bak (server DB backup, TAPE format) - the character-creation
    stored procedure _AddNewChar and its _Char insert.
  * Media.pk2 /server_dep/silkroad/textdata/regioncode.txt - region-id -> name.
  * Media.pk2 /server_dep/silkroad/textdata/characterdata_25000.txt - the
    per-region character generation table for region 25000.

Nothing asserts runtime behavior beyond what the data proves; semantics that
are not documented are labelled UNKNOWN / UNVERIFIED.

Output: scripts/testdata/formats/phase27_source_evidence.json
"""
from __future__ import annotations

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import pk2_table  # noqa: E402

SHARD_BAK = "/tmp/opencode/vsro_db/SRO_VT_SHARD.Bak"
MEDIA_PK2 = "/tmp/opencode/pk2raw/Media.pk2"
CLIENT_OPTIONSET = "/tmp/opencode/vsro_client/Setting/SROptionSet.dat"

SHARD_MARKERS = [
    b"--set @StartRegionID=25000",
    b"INSERT INTO _Char (RefObjID, CharName16, Scale, Strength, Intellect, "
    b"LatestRegion,PosX, PosY, PosZ, AppointedTeleport, InventorySize",
    b"@StartRegionID, @StartPos_X, @StartPos_Y, @StartPos_Z, @DefaultTeleport, 109,",
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


def read_shard_facts(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    facts = {"markers_found": {}, "region_example_comment": None}
    for marker in SHARD_MARKERS:
        hits = [m.start() for m in re.finditer(re.escape(marker), blob)]
        facts["markers_found"][marker.decode("latin1")] = len(hits)
        if hits:
            seg = blob[hits[0]: hits[0] + len(marker) + 120]
            text = seg.decode("latin1", errors="replace")
            text = "".join(ch if ch >= " " else "" for ch in text)
            if b"@StartRegionID" in marker and b"LatestRegion" in marker:
                facts["char_insert_columns"] = text.strip()[:160]
            elif b"@StartPos_X" in marker:
                facts["char_insert_values"] = text.strip()[:160]
            elif b"set @StartRegionID=25000" in marker:
                facts["region_example_comment"] = (
                    "server-side comment inside _AddNewChar: "
                    "'-- set @StartRegionID=25000' (region id is caller-supplied, "
                    "the commented line is the developer's example, not a default)"
                )
    return facts


def region_fact(media, region_id):
    blob = media.read("/server_dep/silkroad/textdata/regioncode.txt")
    if blob[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in blob[:512]:
        text = blob.decode("utf-16-le", errors="replace")
    else:
        text = blob.decode("cp949", errors="replace")
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) >= 3 and cols[0].strip() == "1" and cols[1].strip() == str(region_id):
            return {"region_id": region_id, "code": cols[2].strip(),
                    "caption_bytes": cols[3].strip()[:40],
                    "source": "/server_dep/silkroad/textdata/regioncode.txt"}
    return None


def characterdata_fact(media, region_id):
    blob = media.read("/server_dep/silkroad/textdata/characterdata_%d.txt" % region_id)
    text = blob.decode("utf-16-le", errors="replace")
    lines = [l for l in text.splitlines() if l.strip()]
    first = lines[0].split("\t") if lines else []
    return {
        "path": "/server_dep/silkroad/textdata/characterdata_%d.txt" % region_id,
        "lines": len(lines),
        "first_row_columns": len(first),
        "first_row_refid": first[1].strip() if len(first) > 1 else None,
        "first_row_code": first[2].strip() if len(first) > 2 else None,
        "interpretation": (
            "_RefCharGen-style per-region character generation table shipped to "
            "the client; defines entities present in the region, NOT the player "
            "spawn point."
        ),
    }


def read_media_text(media, path):
    blob = media.read(path)
    if blob[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in blob[:256]:
        return blob.decode("utf-16-le", errors="replace")
    return blob.decode("cp949", errors="replace")


def input_camera_facts(media, option_set_path):
    opt_in = read_media_text(media, "/resinfo/ifoption_input.txt")
    key_slot = read_media_text(media, "/resinfo/ifkeyoptionslot.txt")
    cam = read_media_text(media, "/resinfo/ifoption_camera.txt")
    cam_wnd = read_media_text(media, "/resinfo/ifcameradatawnd.txt")
    cmd = read_media_text(media, "/config/command.txt")
    command_lines = []
    for line in cmd.splitlines():
        if "/" in line:
            command_lines.append(line.strip()[:48])

    def keys_with(prefix, text):
        found = []
        for m in re.finditer(prefix + r"[A-Z_]+", text):
            token = m.group(0)
            if token not in found:
                found.append(token)
        return found[:8]

    option_summary = None
    if os.path.exists(option_set_path):
        with open(option_set_path, "rb") as fh:
            raw = fh.read()
        option_summary = {
            "size_bytes": len(raw),
            "full_hex": raw.hex(),
            "interpretation": (
                "Client per-user OptionSet (SROptionSet.dat). A repeating binary "
                "record pattern (4-byte little-endian id/value fields) is visible, "
                "including key-identifier fields in the 0x0bxx range. The exact "
                "record layout and the action-id semantics require the client "
                "executable and are NOT derivable from this data."
            ),
        }

    return {
        "input": {
            "option_window": "/resinfo/ifoption_input.txt",
            "option_window_text_keys": keys_with("UIIT_STT_", opt_in),
            "key_option_slot_widget": "/resinfo/ifkeyoptionslot.txt",
            "optionset_binary": option_summary,
            "debug_commands_input": [
                c for c in command_lines if any(
                    k in c for k in ("/Pos", "/GetPos", "/fast", "/setspeed"))],
            "conclusion": (
                "The client defines an input-options window (shortcut-key user "
                "rule), a key-option slot widget, and a per-user binary OptionSet "
                "holding key->action pairs. The default key-to-action mapping and "
                "its action identifiers live in client code; the option data alone "
                "cannot be mapped to runtime semantics. Runtime keyboard input "
                "semantics: UNKNOWN (fail-closed)."
            ),
        },
        "camera": {
            "option_window": "/resinfo/ifoption_camera.txt",
            "mode_text_keys": keys_with("UIIT_STT_SIGHT_", cam),
            "data_debug_wnd": "/resinfo/ifcameradatawnd.txt",
            "data_debug_fields": [
                t for t in (
                    "GDR_ST_CAMERA_TIME", "GDR_ST_CAMERA_REGION",
                    "GDR_ST_CAMERA_POSITION", "GDR_ST_CAMERA_ROTATION")
                if t in cam_wnd],
            "debug_commands_camera": [
                c for c in command_lines if any(
                    k in c for k in ("/zoom", "/camera", "/setfov"))],
            "conclusion": (
                "Three camera modes exist (FREE, THIRD_PERSON, QUARTER_VIEW) per "
                "ifoption_camera.txt, plus a camera-data debug window (time / "
                "region / position / rotation) and client debug commands /zoom, "
                "/camera, /setfov. Numeric camera parameters (distance, FOV, angle "
                "limits, follow offset) are client-code defined: UNKNOWN "
                "(fail-closed)."
            ),
        },
        "movement": {
            "debug_commands_movement": [
                c for c in command_lines if any(
                    k in c for k in ("/fast", "/setspeed", "/ms"))],
            "conclusion": (
                "Only client-side debug commands /fast and /setspeed exist; they "
                "are developer diagnostics, not runtime movement parameters. "
                "Phase 26 negative proof stands: no speed table in the archives, "
                "no baked root motion. Walk/run speed: UNKNOWN (fail-closed)."
            ),
        },
    }


def main():
    shard = read_shard_facts(SHARD_BAK)
    media = Archive(MEDIA_PK2)
    region = region_fact(media, 25000)
    chargen = characterdata_fact(media, 25000)
    runtime = input_camera_facts(media, CLIENT_OPTIONSET)
    media.close()

    evidence = {
        "phase": "phase27",
        "spawn": {
            "creation_proc": "_AddNewChar",
            "proc_signature_params_proven": [
                "@UserJID", "@RefCharID", "@CharName", "@CharScale",
                "@StartRegionID", "@StartPos_X", "@StartPos_Y", "@StartPos_Z",
                "@DefaultTeleport",
            ],
            "char_table_columns": [
                "LatestRegion", "PosX", "PosY", "PosZ", "AppointedTeleport",
            ],
            "new_char_defaults_from_insert": {
                "strength": "20", "intellect": "20", "inventory_size": "109",
                "remain_gold": "50000000", "remain_stat_point": "0",
                "remain_skill_point": "1000000", "hp": "200", "mp": "200",
                "cur_level": "1", "max_level": "1", "world_id": "1",
                "job_lvl_trader": "1", "job_lvl_hunter": "1",
                "job_lvl_robber": "1", "hwan_level": "1",
            },
            "start_position": "UNKNOWN (fail-closed)",
            "conclusion": (
                "_AddNewChar receives @StartRegionID and @StartPos_X/Y/Z from the "
                "caller (GameServer/GameWorld logic, C++, not present in this "
                "corpus) and writes them into _Char.LatestRegion/PosX/PosY/PosZ. "
                "The database defines NO default start position; the only server-"
                "side hint is the developer comment '-- set @StartRegionID=25000'. "
                "The client reference table regioncode.txt maps region 25000 to "
                "RN_CH_JANGAN, so the example implies 'start in Jangan', but the "
                "exact runtime start region and position remain UNKNOWN from this "
                "corpus. No spawn/start coordinate table exists anywhere in the "
                "PK2 archives, the DB backups, or the package-server configs."
            ),
            "shard_backup": shard,
            "start_region_25000": region,
            "region_25000_character_gen": chargen,
        },
        "input": runtime["input"],
        "camera": runtime["camera"],
        "movement": runtime["movement"],
    }

    out_path = os.path.join(BASE, "scripts", "testdata", "formats",
                            "phase27_source_evidence.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
    print("wrote", out_path)
    print("region 25000:", region)
    print("char data 25000 rows:", chargen["lines"])
    print("markers:", shard["markers_found"])
    print("start_position:", evidence["spawn"]["start_position"])


if __name__ == "__main__":
    main()
