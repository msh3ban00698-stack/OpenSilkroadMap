"""Generate the world basemap tile pyramid and world.pmtiles archive.

Input : game_source/Media/minimap/{secX}x{secY}.ddj  (extracted by extract_world.py)
Output: map/public/assets/world.pmtiles              (committed runtime asset)

The pyramid reuses the repo's coordinate conventions (verified in Phase B for the
dungeon layers and identical for the world layer in the runtime):

  - z8 (native):  one 256x256 webp per sector  {secX}x{secY}.webp  (top level)
  - z6 (region):  4x4 sectors merged into 256px (64px/sector)
  - z3 (overview): 32x32 sectors merged into 256px (8px/sector)

z8 is the native-resolution top level (1px per sector pixel). The runtime's
tileGrid resolves to z3/z6/z8 (resolutions [1/8, 1/64, 1/256]); zooming beyond
z8 is handled by OpenLayers by scaling the native tiles. This keeps the archive
small (native tiles only, no upscaled 2x z9 level) and mobile-friendly (fewer,
sharper tiles at max detail). z8 is encoded at quality 60 (about 8 KB/sector);
z6/z3 stay at quality 80 because they cover many sectors per tile.

Unlike generate_tiles.py (which holds every z8 tile in RAM), this builder is
streaming: it converts each DDJ once to a z8 webp on disk, then assembles each
z3/z6 tile by loading only the sectors it needs. This keeps peak memory at a
handful of tiles, which is required for the full world (5,523 sectors).

The committed archive contains only z3/z6/z8 (the three levels the runtime's
tileGrid requests). Intermediates stay under the gitignored game_source/out/ tree.

Usage:
    python3 scripts/generate_world.py [--quality 60] [--z8-quality 60]
"""

# /// script
# dependencies = [
#   "pillow",
#   "pmtiles",
# ]
# ///

import argparse
import io
import os
import re
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from convert_ddjs import convert_ddj_to_webp  # noqa: E402  (reuse DDJ converter)

from pmtiles.writer import write  # noqa: E402
from pmtiles.tile import zxy_to_tileid, TileType, Compression  # noqa: E402

TILE_SIZE = 256
WORLD_MM_RE = re.compile(r"^(\d+)x(\d+)\.ddj$", re.IGNORECASE)
WORLD_WP_RE = re.compile(r"^(\d+)x(\d+)\.webp$", re.IGNORECASE)
SRC_DIR = os.path.join("game_source", "Media", "minimap")
OUT_DIR = os.path.join("game_source", "out", "minimap")
PMTILES_OUT = os.path.join("map", "public", "assets", "world.pmtiles")


def load_webp(path):
    if not os.path.exists(path):
        return None
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        return None


def save_webp(img, path, quality):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "WEBP", quality=quality)


def convert_all_ddjs(quality, force=False):
    """Convert every world DDJ to a z8 webp under OUT_DIR/8/ (streaming)."""
    z8_dir = os.path.join(OUT_DIR, "8")
    os.makedirs(z8_dir, exist_ok=True)
    done = 0
    for fname in sorted(os.listdir(SRC_DIR)):
        if not WORLD_MM_RE.match(fname):
            continue
        dst = os.path.join(z8_dir, fname.replace(".ddj", ".webp"))
        if os.path.exists(dst) and not force:
            done += 1
            continue
        if convert_ddj_to_webp(os.path.join(SRC_DIR, fname), dst, quality=quality):
            done += 1
        if done % 1000 == 0:
            print(f"  converted {done}...")
    print(f"z8 tiles on disk: {done}")


def _compose(tile_x, tile_y, span_x, span_y, sector_scale, quality, z_dir, z):
    """Assemble one merged tile from its source sectors.

    tile_x/tile_y: tile index at zoom z.
    span_x/span_y: sectors per tile (e.g. 4/4 for z6, 32/32 for z3).
    sector_scale:  pixels per sector inside the 256px tile.
    y mapping matches generate_tiles.py: sector rows run north (larger secY) to top.
    """
    z8_dir = os.path.join(OUT_DIR, "8")
    canvas = Image.new("RGB", (TILE_SIZE, TILE_SIZE))
    has_any = False
    # sector x range: [tile_x*span_x, tile_x*span_x + span_x)
    # sector y range: [tile_y*span_y - (span_y-1), tile_y*span_y]
    x0 = tile_x * span_x
    y_top = tile_y * span_y
    for sx in range(x0, x0 + span_x):
        for sy in range(y_top - (span_y - 1), y_top + 1):
            img = load_webp(os.path.join(z8_dir, f"{sx}x{sy}.webp"))
            if img is None:
                continue
            has_any = True
            small = img.resize((sector_scale, sector_scale), Image.LANCZOS)
            canvas.paste(small, ((sx - x0) * sector_scale, (y_top - sy) * sector_scale))
            small.close()
            img.close()
    if has_any:
        save_webp(canvas, os.path.join(z_dir, f"{tile_x}x{tile_y}.webp"), quality)
    canvas.close()


def build_z6(quality):
    z6_dir = os.path.join(OUT_DIR, "6")
    count = 0
    z8_dir = os.path.join(OUT_DIR, "8")
    xs = set()
    ys = set()
    for fname in os.listdir(z8_dir):
        m = WORLD_WP_RE.match(fname)
        if m:
            xs.add(int(m.group(1)))
            ys.add(int(m.group(2)))
    # z6 tile x spans 4 sectors (floor for x), y spans 4 sectors (ceil chain)
    for tx in range(min(xs) // 4, max(xs) // 4 + 1):
        for ty in range((min(ys) + 3) // 4, (max(ys) + 3) // 4 + 1):
            _compose(tx, ty, 4, 4, 64, quality, z6_dir, 6)
            count += 1
    print(f"z6 tiles: {count}")


def build_z3(quality):
    z3_dir = os.path.join(OUT_DIR, "3")
    count = 0
    z8_dir = os.path.join(OUT_DIR, "8")
    xs = set()
    ys = set()
    for fname in os.listdir(z8_dir):
        m = WORLD_WP_RE.match(fname)
        if m:
            xs.add(int(m.group(1)))
            ys.add(int(m.group(2)))
    # z3 tile x spans 32 sectors (floor), y spans 32 sectors (ceil chain)
    for tx in range(min(xs) // 32, max(xs) // 32 + 1):
        for ty in range((min(ys) + 31) // 32, (max(ys) + 31) // 32 + 1):
            _compose(tx, ty, 32, 32, 8, quality, z3_dir, 3)
            count += 1
    print(f"z3 tiles: {count}")


def build_pmtiles():
    tiles = []
    for z in ("3", "6", "8"):
        z_dir = os.path.join(OUT_DIR, z)
        if not os.path.isdir(z_dir):
            continue
        for fname in os.listdir(z_dir):
            m = WORLD_WP_RE.match(fname)
            if not m:
                continue
            x, y = int(m.group(1)), int(m.group(2))
            tiles.append((zxy_to_tileid(int(z), x, y), os.path.join(z_dir, fname), int(z)))
    tiles.sort(key=lambda t: t[0])
    print(f"packing {len(tiles)} tiles into {PMTILES_OUT}...")
    with write(PMTILES_OUT) as w:
        for tile_id, path, _ in tiles:
            with open(path, "rb") as f:
                w.write_tile(tile_id, f.read())
        w.finalize(
            {
                "tile_type": TileType.WEBP,
                "tile_compression": Compression.NONE,
                "min_zoom": 3,
                "max_zoom": 8,
            },
            {"name": "world.pmtiles", "description": "Silkroad World Map Background Tiles"},
        )
    size_mb = os.path.getsize(PMTILES_OUT) / 1024 / 1024
    print(f"world.pmtiles written: {size_mb:.1f} MB")


def main():
    parser = argparse.ArgumentParser(description="Generate world basemap pyramid + world.pmtiles")
    parser.add_argument("--quality", type=int, default=80, help="WEBP quality for z3/z6 tiles (default 80)")
    parser.add_argument(
        "--z8-quality", type=int, default=60, help="WEBP quality for native z8 tiles (default 60)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-encode z8 tiles even if already on disk"
    )
    args = parser.parse_args()

    if not os.path.isdir(SRC_DIR):
        print(f"Error: {SRC_DIR} not found. Run scripts/extract_world.py first.")
        sys.exit(1)

    convert_all_ddjs(args.z8_quality, force=args.force)
    build_z6(args.quality)
    build_z3(args.quality)
    build_pmtiles()
    print("World basemap generation complete.")


if __name__ == "__main__":
    main()
