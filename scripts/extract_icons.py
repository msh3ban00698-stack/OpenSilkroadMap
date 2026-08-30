"""Batch-extract authentic item and skill icons from Media.pk2.

Reads the runtime gamedata databases (items.json / skills_full.json),
resolves every referenced icon path inside the Media.pk2 icon/icon64
trees via listing_media.txt, converts each .ddj to .webp and stores it
under map/public/assets/img/silkroad/icons/<flat-name>.webp.

Usage: python3 scripts/extract_icons.py
"""

import argparse
import json
import os
import sys

import sro_paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_ui import load_ddj, parse_listing  # noqa: E402

OUT = "map/public/assets/img/silkroad/icons"
GAMEDATA = "map/public/assets/gamedata"


def wanted_icons():
    wanted = set()
    with open(os.path.join(GAMEDATA, "items.json"), encoding="utf-8") as f:
        items = json.load(f)
    for it in items.values():
        if it.get("icon"):
            wanted.add(it["icon"].replace("\\", "/"))
    sp = os.path.join(GAMEDATA, "skills_full.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            skills = json.load(f)
        for sk in skills.values():
            if sk.get("icon"):
                wanted.add("skill/" + sk["icon"])
    return sorted(wanted)


def resolve_candidates(rel):
    name = rel.split("/")[-1]
    return [
        f"icon64/{rel}.ddj",
        f"icon/{rel}.ddj",
        f"icon64/{name}.ddj",
        f"icon/{name}.ddj",
    ]


def main():
    parser = argparse.ArgumentParser(description="Extract item/skill icons from Media.pk2")
    sro_paths.add_common_args(parser, pk2=True, output=True)
    args = parser.parse_args()
    try:
        pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
        reader_dir = sro_paths.resolve_reader_dir(args.reader_dir, pk2_dir)
        pk2reader = sro_paths.require_pk2_reader(reader_dir)
    except sro_paths.PipelineConfigError as exc:
        sys.exit("Error: {0}".format(exc))
    media = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Media.pk2"))
    os.makedirs(OUT, exist_ok=True)

    wanted = wanted_icons()
    print(f"{len(wanted)} unique icons referenced")

    index = {}
    for p in parse_listing(sro_paths.listing_path(pk2_dir, "listing_media.txt")):
        low = p.lower()
        for root in ("icon64/", "icon/", "skill/", "pet2/", "item/", "legendrpet/"):
            if root == "icon64/" or root == "icon/":
                continue
        norm = low.lstrip("/")
        for prefix in ("icon64/", "icon/"):
            if norm.startswith(prefix):
                rel = norm[len(prefix) :].rsplit(".", 1)[0]
                index.setdefault(rel, p)
    print(f"icon index: {len(index)} files")

    ok, miss = 0, []
    for rel in wanted:
        dest = os.path.join(OUT, rel.replace("/", "_") + ".webp")
        if os.path.exists(dest):
            ok += 1
            continue
        key = rel.lower()
        entry_path = index.get(key)
        if not entry_path:
            base_name = key.split("/")[-1]
            for k, v in index.items():
                if k.endswith("/" + base_name) or k == base_name:
                    entry_path = v
                    break
        if not entry_path:
            miss.append(rel)
            continue
        try:
            entry = media.find(entry_path)
            blob = media.read_file(entry)
            img = load_ddj(blob)
            img.save(dest, quality=80)
            ok += 1
        except Exception as e:
            print("FAIL", rel, e)
            miss.append(rel)
    print(f"extracted/present {ok}/{len(wanted)}, missing {len(miss)}")
    if miss:
        print("sample missing:", miss[:10])


if __name__ == "__main__":
    main()
