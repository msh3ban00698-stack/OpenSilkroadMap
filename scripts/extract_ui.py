#!/usr/bin/env python3
"""Extract authentic Silkroad interface art from Media.pk2 into runtime assets.

Parses listing_media.txt (indentation tree) to resolve full package paths,
extracts a curated set of login/select/loading/button textures, converts them
from .ddj to .png and writes them to map/public/assets/img/silkroad/ui/.
"""
import argparse
import os
import re
import sys
from io import BytesIO

import sro_paths

OUT = os.path.join(
    os.path.dirname(__file__), "..", "map", "public", "assets", "img", "silkroad", "ui"
)

TARGETS = {
    "loading_login_01_2011.ddj": "login_bg.png",
    "loading_login_02_2011.ddj": "login_bg2.png",
    "loading_asiaminor.ddj": "loading_ct.png",
    "title_button_all.ddj": "btn_all.png",
    "title_button_all_focus.ddj": "btn_all_focus.png",
    "title_button_all_press.ddj": "btn_all_press.png",
    "title_button_ok.ddj": "btn_ok.png",
    "title_button_ok_focus.ddj": "btn_ok_focus.png",
    "title_button_ok_press.ddj": "btn_ok_press.png",
    "login_chanel_window_01.ddj": "login_window.png",
    "login_deco_gradation.ddj": "login_gradation.png",
    "pmi_hp.ddj": "hud_hp.png",
    "pmi_mp.ddj": "hud_mp.png",
    "pmi_face.ddj": "hud_face.png",
    "pmi_face_select.ddj": "hud_face_select.png",
    "pmi_window.ddj": "hud_pmi_window.png",
    "pmi_bottom_window.ddj": "hud_pmi_bottom.png",
    "pmi_button.ddj": "hud_btn.png",
    "pmi_button_focus.ddj": "hud_btn_focus.png",
    "pmi_button_press.ddj": "hud_btn_press.png",
    "main_sysbutton_inventory.ddj": "sys_inventory.png",
    "main_sysbutton_inventory_focus.ddj": "sys_inventory_focus.png",
    "main_sysbutton_character.ddj": "sys_character.png",
    "main_sysbutton_character_focus.ddj": "sys_character_focus.png",
    "main_sysbutton_action.ddj": "sys_action.png",
    "main_sysbutton_action_focus.ddj": "sys_action_focus.png",
    "qsl_hriz01_windo.ddj": "qslot_window.png",
    "qsl_hriz01_slot_tile.ddj": "qslot_slot.png",
    "qsl_hriz01_end.ddj": "qslot_end.png",
    "frame_g_action_left_up.ddj": "frm_left_up.png",
    "frame_g_action_mid_up.ddj": "frm_mid_up.png",
    "frame_g_action_right_up.ddj": "frm_right_up.png",
    "frame_g_action_left_side.ddj": "frm_left_side.png",
    "frame_g_action_right_side.ddj": "frm_right_side.png",
    "frame_g_action_left_down.ddj": "frm_left_down.png",
    "frame_g_action_mid_down.ddj": "frm_mid_down.png",
    "frame_g_action_right_down.ddj": "frm_right_down.png",
    "mm_sign_character.ddj": "sign_character.png",
    "mm_sign_npc.ddj": "sign_npc.png",
    "mm_sign_monster.ddj": "sign_monster.png",
}


def parse_listing(path):
    """Yield full package paths from an indentation-tree listing file.

    Folder lines start with '/' and already carry the absolute package path;
    file lines are basenames attached to the nearest shallower folder line.
    """
    stack = []  # list of (indent, abs_folder_path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            name = line.strip()
            while stack and stack[-1][0] >= indent:
                stack.pop()
            if name.startswith("/"):
                folder = name.rstrip("/")
                stack.append((indent, folder))
            else:
                parent = stack[-1][1] if stack else ""
                yield f"{parent}/{name}"


def load_ddj(blob):
    from PIL import Image

    return Image.open(BytesIO(blob[20:])).convert("RGBA")


def main():
    parser = argparse.ArgumentParser(description="Extract Silkroad UI art from Media.pk2")
    sro_paths.add_common_args(parser, pk2=True)
    parser.add_argument("--output-dir", default=None, help="UI output directory")
    args = parser.parse_args()
    try:
        pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
        reader_dir = sro_paths.resolve_reader_dir(args.reader_dir, pk2_dir)
        pk2reader = sro_paths.require_pk2_reader(reader_dir)
    except sro_paths.PipelineConfigError as exc:
        sys.exit("Error: {0}".format(exc))
    media = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Media.pk2"))
    out_dir = args.output_dir or OUT
    os.makedirs(out_dir, exist_ok=True)
    wanted = {os.path.basename(k): k for k in TARGETS}
    found = {}
    for p in parse_listing(sro_paths.listing_path(pk2_dir, "listing_media.txt")):
        base = os.path.basename(p)
        if base in wanted and base not in found:
            found[base] = p
    print(f"resolved {len(found)}/{len(wanted)} targets")
    ok = 0
    for base, pkg_path in sorted(found.items()):
        dest = TARGETS[base]
        entry = media.find(pkg_path)
        if entry is None:
            print("MISSING in pk2:", pkg_path)
            continue
        blob = media.read_file(entry)
        try:
            img = load_ddj(blob)
        except Exception as e:
            print("DECODE FAIL:", pkg_path, e)
            continue
        img.save(os.path.join(out_dir, dest))
        print(f"{dest}: {img.width}x{img.height}  <- {pkg_path}")
        ok += 1
    print(f"extracted {ok}/{len(TARGETS)}")


if __name__ == "__main__":
    main()
