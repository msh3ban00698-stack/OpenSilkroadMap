"""Extract the world-map source files from the external vSRO Media.pk2.

Extracts into the gitignored game_source/ layout expected by the existing
converter scripts:

    game_source/Media/minimap/{secX}x{secY}.ddj                 -> world tiles
    game_source/Media/server_dep/silkroad/textdata/*.txt         -> generate_game_data.py

The world minimaps are per-sector 256x256 minimaps covering every land sector
of the Silkroad world map (sector X 26..252, Y 35..126).

Usage:
    python3 scripts/extract_world.py --pk2-dir /path/to/pk2s [--root game_source]

No original game data leaves this machine: outputs stay under the (gitignored)
game_source/ tree and are never staged.
"""

import argparse
import os
import re
import sys

import sro_paths

WORLD_MM_RE = re.compile(r"^(\d+)x(\d+)\.ddj$", re.IGNORECASE)

TEXTDATA_DIRS = ["event", "textdata"]


def main():
    parser = argparse.ArgumentParser(description="Extract world minimaps + textdata from external vSRO Media.pk2")
    parser.add_argument("--pk2-dir", default=None, help="Directory containing Media.pk2 or a parent with pk2/")
    parser.add_argument("--reader-dir", default=None, help="Directory with pk2reader.py/jmblowfish.py (default: pk2-dir)")
    parser.add_argument("--root", default=None, help="Output root (gitignored), default: game_source")
    parser.add_argument("--minimaps", action="store_true", default=True, help="Extract world minimap DDJs (default)")
    parser.add_argument("--textdata", action="store_true", default=True, help="Extract server textdata (default)")
    args = parser.parse_args()

    try:
        pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
        reader_dir = sro_paths.resolve_reader_dir(args.reader_dir, pk2_dir)
        pk2reader = sro_paths.require_pk2_reader(reader_dir)
    except sro_paths.PipelineConfigError as exc:
        sys.exit("Error: {0}".format(exc))

    media_pk2 = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Media.pk2"))
    root = args.root or sro_paths.resolve_source_dir()
    extracted = []
    missing = []

    def extract(relpath, entry):
        out = os.path.join(root, "Media", *relpath.split("/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(media_pk2.read_file(entry))
        extracted.append((relpath, entry["size"]))

    if args.minimaps:
        for full, entry in media_pk2.walk():
            if not full.lower().startswith("minimap/"):
                continue
            name = full.rsplit("/", 1)[-1]
            if not WORLD_MM_RE.match(name):
                continue
            extract(full, entry)

    if args.textdata:
        for full, entry in media_pk2.walk():
            if not full.lower().startswith("server_dep/silkroad/textdata/"):
                continue
            extract(full, entry)

    print(f"Extracted {len(extracted)} files ({sum(s for _, s in extracted):,} bytes)")
    if missing:
        print("MISSING:")
        for m in missing:
            print("  " + m)
        sys.exit(1)


if __name__ == "__main__":
    main()
