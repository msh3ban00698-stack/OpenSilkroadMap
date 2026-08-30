"""Extract authentic audio tracks and region minimap tiles into runtime assets.

Music: every .ogg from Music.pk2 -> map/public/assets/audio/music/
Minimaps: Constantinople-window tiles from Media.pk2 minimap tree
          -> map/public/assets/img/silkroad/game/minimap/

Usage: python3 scripts/extract_audio_minimaps.py
"""

import argparse
import os
import sys

import sro_paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_ui import load_ddj, parse_listing  # noqa: E402

MUSIC_OUT = "map/public/assets/audio/music"
MINIMAP_OUT = "map/public/assets/img/silkroad/game/minimap"


def extract_music(music, pk2_dir):
    os.makedirs(MUSIC_OUT, exist_ok=True)
    ok = 0
    for p in parse_listing(sro_paths.listing_path(pk2_dir, "listing_music.txt")):
        name = os.path.basename(p)
        dest = os.path.join(MUSIC_OUT, name.lower())
        if os.path.exists(dest):
            ok += 1
            continue
        try:
            entry = music.find(p)
            blob = music.read_file(entry)
            with open(dest, "wb") as f:
                f.write(blob)
            ok += 1
        except Exception as e:
            print("music FAIL", p, e)
    print(f"music: {ok} tracks")


def extract_minimaps(media, pk2_dir):
    """CT window tiles: minimap/{76..81}x{103..108}.ddj"""
    os.makedirs(MINIMAP_OUT, exist_ok=True)
    wanted = {}
    for p in parse_listing(sro_paths.listing_path(pk2_dir, "listing_media.txt")):
        low = p.lower()
        if "/minimap/" not in low:
            continue
        base = os.path.basename(low)
        stem = base.rsplit(".", 1)[0]
        if "x" in stem:
            xs, ys = stem.split("x")
            if xs.isdigit() and ys.isdigit() and 76 <= int(xs) <= 81 and 103 <= int(ys) <= 108:
                wanted[stem] = p
    ok = 0
    for stem, path in sorted(wanted.items()):
        dest = os.path.join(MINIMAP_OUT, f"tile_{stem}.webp")
        if os.path.exists(dest):
            ok += 1
            continue
        try:
            entry = media.find(path)
            img = load_ddj(media.read_file(entry))
            img.save(dest, quality=82)
            ok += 1
        except Exception as e:
            print("minimap FAIL", path, e)
    print(f"minimaps: {ok}/{len(wanted)} tiles")


def main():
    parser = argparse.ArgumentParser(description="Extract audio tracks and CT minimap tiles")
    sro_paths.add_common_args(parser, pk2=True)
    args = parser.parse_args()
    try:
        pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
        reader_dir = sro_paths.resolve_reader_dir(args.reader_dir, pk2_dir)
        pk2reader = sro_paths.require_pk2_reader(reader_dir)
    except sro_paths.PipelineConfigError as exc:
        sys.exit("Error: {0}".format(exc))
    music = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Music.pk2"))
    media = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Media.pk2"))
    extract_music(music, pk2_dir)
    extract_minimaps(media, pk2_dir)


if __name__ == "__main__":
    main()
