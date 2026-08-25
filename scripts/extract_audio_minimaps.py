"""Extract authentic audio tracks and region minimap tiles into runtime assets.

Music: every .ogg from Music.pk2 -> map/public/assets/audio/music/
Minimaps: Constantinople-window tiles from Media.pk2 minimap tree
          -> map/public/assets/img/silkroad/game/minimap/

Usage: python3 scripts/extract_audio_minimaps.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/tmp/opencode/vsro")

import pk2reader  # noqa: E402
from extract_ui import load_ddj, parse_listing  # noqa: E402

PK2ROOT = "/tmp/opencode/vsro"
MUSIC_OUT = "map/public/assets/audio/music"
MINIMAP_OUT = "map/public/assets/img/silkroad/game/minimap"

music = pk2reader.PK2(os.path.join(PK2ROOT, "pk2/Music.pk2"))
media = pk2reader.PK2(os.path.join(PK2ROOT, "pk2/Media.pk2"))


def extract_music():
    os.makedirs(MUSIC_OUT, exist_ok=True)
    ok = 0
    for p in parse_listing(os.path.join(PK2ROOT, "listing_music.txt")):
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


def extract_minimaps():
    """CT window tiles: minimap/{76..81}x{103..108}.ddj"""
    os.makedirs(MINIMAP_OUT, exist_ok=True)
    wanted = {}
    for p in parse_listing(os.path.join(PK2ROOT, "listing_media.txt")):
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


if __name__ == "__main__":
    extract_music()
    extract_minimaps()
