"""Extract the source files for one playable region from the external vSRO PK2s.

Only extracts the exact files needed by a single region (verified dependency
closure), into the gitignored game_source/ layout expected by the existing
converter scripts:

    game_source/Media/minimap_d/<mapdir>/<name>.ddj   -> convert_ddjs.py
    game_source/Data/Dungeon/<...>.dof                -> generate_navmesh.py
    game_source/Data/Dungeon/DungeonInfo.txt          -> generate_navmesh.py
    game_source/Data/res/.../*.bsr                    -> generate_navmesh.py
    game_source/Data/prim/mesh/.../*.bms              -> generate_navmesh.py
    game_source/Data/navmesh/ainavdata_*.dat          -> provenance

Region 32785 "Cave of Meditation" (Fortress Dungeon):
  - Media.pk2 minimap_d/fort_dungeon/fort_dungeon01_{127..129}x{126..128}.ddj
  - Data.pk2 Dungeon/wchina/fortress_dungeon.dof
  - Data.pk2 res/dun/wchina/donhwang_cv_clone/floor_1/*.bsr (13)
  - Data.pk2 prim/mesh/dun/wchina/donhwang_cv_clone/floor_1/**/*.bms (13)
  - Data.pk2 navmesh/ainavdata_32785.dat

Usage:
    python3 scripts/extract_region.py --pk2-dir /path/to/pk2s [--root game_source]

No original game data leaves this machine: outputs stay under the (gitignored)
game_source/ tree and are never staged.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from generate_navmesh import parse_navmesh_obj_bsr  # noqa: E402  (reuse repo parser)

REGIONS = {
    # dungeon_id == index of the dungeon in DungeonInfo.txt (1-based)
    32785: {
        "name": "Cave of Meditation (Fortress Dungeon)",
        "dungeon_id": 17,
        "dof": "Dungeon/wchina/fortress_dungeon.dof",
        "minimap": {
            "dir": "minimap_d/fort_dungeon",
            "prefix": "fort_dungeon01",
            "x": range(127, 130),
            "y": range(126, 129),
        },
        "bsrs": [
            "res/dun/wchina/donhwang_cv_clone/floor_1/entroom_fortress.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_01.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_02.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_03.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_04.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_05.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_06.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_07.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_08.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passage01_09.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/passent01.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/room101.bsr",
            "res/dun/wchina/donhwang_cv_clone/floor_1/room102.bsr",
        ],
        "ainavdata": "navmesh/ainavdata_32785.dat",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Extract one region's source files from external vSRO PK2s")
    parser.add_argument("--pk2-dir", required=True, help="Directory containing Data.pk2 and Media.pk2")
    parser.add_argument("--reader-dir", default=None, help="Directory with pk2reader.py/jmblowfish.py (default: pk2-dir)")
    parser.add_argument("--root", default="game_source", help="Output root (gitignored), default: game_source")
    parser.add_argument("--region", type=int, default=32785, help="Region ID to extract (default: 32785)")
    args = parser.parse_args()

    if args.region not in REGIONS:
        sys.exit(f"Region {args.region} is not configured (available: {sorted(REGIONS)})")

    reader_dir = args.reader_dir or args.pk2_dir
    sys.path.insert(0, reader_dir)
    from pk2reader import PK2  # noqa: E402  (custom reader lives next to the PK2s)

    data_pk2 = PK2(os.path.join(args.pk2_dir, "Data.pk2"))
    media_pk2 = PK2(os.path.join(args.pk2_dir, "Media.pk2"))

    cfg = REGIONS[args.region]
    root = args.root
    extracted = []
    missing = []

    def extract(pk, relpath, outpath):
        entry = pk.find(relpath)
        if entry is None:
            missing.append(relpath)
            return
        out = os.path.join(outpath, *relpath.split("/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(pk.read_file(entry))
        extracted.append((relpath, entry["size"]))

    print(f"Region {args.region}: {cfg['name']}")

    # Minimap DDJs -> game_source/Media/minimap_d/<dir>/
    mm = cfg["minimap"]
    for x in mm["x"]:
        for y in mm["y"]:
            rel = f"{mm['dir']}/{mm['prefix']}_{x}x{y}.ddj"
            extract(media_pk2, rel, os.path.join(root, "Media"))

    # Dungeon .dof -> game_source/Data/Dungeon/...
    extract(data_pk2, cfg["dof"], os.path.join(root, "Data"))

    # Navmesh objects: .bsr -> .bms chain
    for bsr in cfg["bsrs"]:
        extract(data_pk2, bsr, os.path.join(root, "Data"))
        entry = data_pk2.find(bsr)
        if entry is None:
            continue
        bms = parse_navmesh_obj_bsr(data_pk2.read_file(entry))
        if bms:
            extract(data_pk2, bms.replace("\\", "/"), os.path.join(root, "Data"))

    # AINavData dungeon navmesh (provenance only)
    extract(data_pk2, cfg["ainavdata"], os.path.join(root, "Data"))

    # Filtered DungeonInfo.txt (only this region) so generate_navmesh.py renders just it
    dof_info = os.path.join(root, "Data", "Dungeon")
    os.makedirs(dof_info, exist_ok=True)
    with open(os.path.join(dof_info, "DungeonInfo.txt"), "w", encoding="ascii") as f:
        dof_windows = cfg["dof"].replace("/", "\\")
        f.write(f'1\t{cfg["dungeon_id"]}\t"{dof_windows}"\n')

    print(f"Extracted {len(extracted)} files ({sum(s for _, s in extracted):,} bytes)")
    if missing:
        print("MISSING (aborting):")
        for m in missing:
            print("  " + m)
        sys.exit(1)


if __name__ == "__main__":
    main()
