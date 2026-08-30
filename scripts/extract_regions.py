#!/usr/bin/env python3
"""Extract sources for multiple authentic world regions from the VSRO packages.

Extends scripts/extract_ct.py (Constantinople-only) to arbitrary sector
windows. For every region in REGIONS it extracts:

  - terrain blocks (Map.pk2 {Y}/{X}.m) + object overlays (Map.pk2 {Y}/{X}.o2)
  - minimap tiles (Media.pk2 minimap/{X}x{Y}.ddj)
  - the full dependency closure of building/NPC/mob bsr + bms + bmt + ddj

All output lands under game_source/CT so scripts/generate_region_ct.py (or its
generalized sibling) can read it with the same layout as the existing
Constantinople assets.

Usage: uv run scripts/extract_regions.py
"""

import argparse
import os
import struct
import sys

import sro_paths

OUT = os.path.join(os.path.dirname(__file__), "..", "game_source", "CT")

# Region windows: 6x6 sector boxes (sx..sx+5, sy..sy+5). Window centres chosen
# from the quest-giver NPC spawn data (see region_design*.py analysis).
REGIONS = {
    "jangan": (164, 94),
    "donwhang": (150, 99),
    "hotan": (132, 89),
    "samarkand": (104, 102),
    "baghdad": (86, 84),
    "alexandria": (45, 90),
    "mtroc": (106, 89),
    "jupiter": (199, 88),
}

data = None
mapk = None
media = None


def find(pk, path):
    e = pk.find(path)
    if e is None:
        return None
    return pk.read_file(e)


def store(pk, path, dest, quiet=True):
    blob = find(pk, path)
    if blob is None:
        if not quiet:
            print("MISSING:", path)
        return False
    fp = os.path.join(OUT, dest)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "wb") as f:
        f.write(blob)
    return True


def parse_bsr(bd):
    """Return (material_path, [bms_paths]) for a .bsr blob, or None."""
    if bd[:12] != b"JMXVRES 0109":
        return None
    num, num2, num3 = struct.unpack_from("<III", bd, 12)
    p = num + 8
    if p + 4 > len(bd):
        return None
    cnt = struct.unpack_from("<I", bd, p)[0]
    p += 4
    if p + cnt > len(bd):
        return None
    mpath = bd[p : p + cnt].decode("ascii", "replace").replace("\\", "/")
    bms = []
    p = num2
    if p + 4 <= len(bd):
        n = struct.unpack_from("<I", bd, p)[0]
        p += 4
        for _ in range(n):
            if p + 4 > len(bd):
                break
            sl = struct.unpack_from("<I", bd, p)[0]
            if sl < 20:
                if p + 8 > len(bd):
                    break
                sl = struct.unpack_from("<I", bd, p + 4)[0]
                p += 8
            else:
                p += 4
            if p + sl > len(bd):
                break
            bms.append(bd[p : p + sl].decode("ascii", "replace").replace("\\", "/"))
            p += sl
    return mpath, bms


def parse_bmt(mt):
    """Return {matname: ddjpath} for a .bmt blob."""
    if mt[:12] != b"JMXVBMT 0102":
        return {}
    p = 12
    if p + 4 > len(mt):
        return {}
    mc = struct.unpack_from("<I", mt, p)[0]
    p += 4
    out = {}
    for _ in range(mc):
        if p + 4 > len(mt):
            break
        nn = struct.unpack_from("<I", mt, p)[0]
        p += 4
        if p + nn > len(mt):
            break
        name = mt[p : p + nn].decode("ascii", "replace")
        p += nn + 0x48
        if p + 4 > len(mt):
            break
        dn = struct.unpack_from("<I", mt, p)[0]
        p += 4
        if p + dn > len(mt):
            break
        ddj = mt[p : p + dn].decode("ascii", "replace")
        p += dn + 7
        out[name] = ddj
    return out


def collect_model(path, seen):
    """Extract bsr + its bms + bmt + ddj closure into OUT/Data, recursive."""
    path = path.replace("\\", "/")
    if path in seen:
        return
    seen.add(path)
    if path.endswith(".bsr"):
        blob = find(data, path)
        if blob is None and not path.startswith("res/"):
            blob = find(data, "res/" + path)
            if blob is not None:
                path = "res/" + path
        if blob is None:
            return
        store(data, path, "Data/" + path)
        r = parse_bsr(blob)
        if r is None:
            return
        mpath, bms = r
        if mpath:
            mt = find(data, mpath)
            if mt is not None:
                store(data, mpath, "Data/" + mpath)
                base = mpath.rsplit("/", 1)[0]
                for ddj in set(v for v in parse_bmt(mt).values() if v.lower().endswith(".ddj")):
                    ddj = ddj.replace("\\", "/")
                    if ddj.startswith("/"):
                        ddj = ddj.lstrip("/")
                    tp = ddj if "/" in ddj else base + "/" + ddj
                    if find(data, tp) is not None:
                        store(data, tp, "Data/" + tp)
                    elif "/" not in ddj and find(data, base + "/" + ddj) is not None:
                        store(data, base + "/" + ddj, "Data/" + base + "/" + ddj)
        for b in bms:
            collect_model(b, seen)
    elif path.endswith(".bms"):
        blob = find(data, path)
        if blob is not None:
            store(data, path, "Data/" + path)


def main():
    parser = argparse.ArgumentParser(description="Extract world-region sources from vSRO PK2s")
    sro_paths.add_common_args(parser, pk2=True, source=True)
    args = parser.parse_args()
    try:
        pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
        reader_dir = sro_paths.resolve_reader_dir(args.reader_dir, pk2_dir)
        pk2reader = sro_paths.require_pk2_reader(reader_dir)
    except sro_paths.PipelineConfigError as exc:
        sys.exit("Error: {0}".format(exc))
    global data, mapk, media, OUT
    data = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Data.pk2"))
    mapk = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Map.pk2"))
    media = pk2reader.PK2(sro_paths.pk2_archive(pk2_dir, "Media.pk2"))
    OUT = os.path.join(sro_paths.resolve_source_dir(args.source_dir), "CT")
    all_sectors = set()
    for name, (sx, sy) in REGIONS.items():
        for x in range(sx, sx + 6):
            for y in range(sy, sy + 6):
                all_sectors.add((x, y))
    print(f"{len(all_sectors)} sectors across {len(REGIONS)} regions")

    # --- terrain / overlays (Map.pk2) ---
    for x, y in sorted(all_sectors):
        store(mapk, f"{y}/{x}.m", f"Map/{y}/{x}.m")
        store(mapk, f"{y}/{x}.o2", f"Map/{y}/{x}.o2")
    # --- minimap tiles (Media.pk2) ---
    for x, y in sorted(all_sectors):
        store(media, f"minimap/{x}x{y}.ddj", f"Media/minimap/{x}x{y}.ddj")

    # --- text / index files (idempotent) ---
    store(data, "RegionInfo.txt", "Data/RegionInfo.txt")
    store(data, "navmesh/object.ifo", "Data/navmesh/object.ifo")
    store(media, "server_dep/silkroad/textdata/npcpos.txt", "Media/npcpos.txt")
    cd_list = find(media, "server_dep/silkroad/textdata/characterdata.txt")
    if cd_list is not None:
        store(media, "server_dep/silkroad/textdata/characterdata.txt", "Media/characterdata.txt")
        for fn in cd_list.decode("utf-16-le", "replace").replace("\r", "").split():
            fn = fn.strip()
            if fn:
                store(media, f"server_dep/silkroad/textdata/{fn}", f"Media/{fn}")

    # --- object index (bsr paths for .o2 nameI) ---
    ifo = find(data, "navmesh/object.ifo").decode("gbk", "replace")
    objects = []
    for ln in ifo.splitlines():
        i = ln.find('"')
        j = ln.rfind('"')
        objects.append(ln[i + 1 : j].replace("\\", "/"))

    # --- bsr set from all region .o2 files ---
    bsrset = set()
    for x, y in all_sectors:
        blob = find(mapk, f"{y}/{x}.o2")
        if blob is None:
            continue
        pos = 16
        while pos < len(blob):
            cnt = struct.unpack_from("<H", blob, pos)[0]
            pos += 2
            if cnt == 0:
                continue
            for _ in range(cnt):
                if pos + 32 > len(blob):
                    break
                nameI = struct.unpack_from("<I", blob, pos)[0]
                pos += 32
                if nameI < len(objects):
                    bsrset.add(objects[nameI])
    print("region bsr set:", len(bsrset))
    seen = set()
    for path in sorted(bsrset):
        collect_model(path, seen)
    print("after region buildings:", len(seen))

    # --- npc/mob models from characterdata (refchars spawning in regions) ---
    refs = set()
    npc_path = os.path.join(OUT, "Media", "npcpos.txt")
    with open(npc_path, encoding="utf-16-le") as f:
        for ln in f:
            cols = ln.rstrip("\r\n").split("\t")
            if len(cols) < 2:
                continue
            try:
                region = int(cols[1].strip())
            except ValueError:
                continue
            rx, ry = region & 0xFF, region >> 8
            inwin = any(
                sx <= rx < sx + 6 and sy <= ry < sy + 6 for sx, sy in REGIONS.values()
            )
            if not inwin:
                continue
            try:
                refs.add(int(cols[0].strip()))
            except ValueError:
                pass
    print("region refchars:", len(refs))
    refchars = {}
    for fn in os.listdir(os.path.join(OUT, "Media")):
        if not fn.lower().startswith("characterdata_"):
            continue
        with open(os.path.join(OUT, "Media", fn), encoding="utf-16-le") as f:
            for ln in f:
                parts = ln.rstrip("\n").rstrip("\r").split("\t")
                if len(parts) < 3:
                    continue
                try:
                    ref = int(parts[1].strip())
                except ValueError:
                    continue
                if ref not in refs:
                    continue
                model = ""
                for col in parts[3:]:
                    col = col.replace("\\", "/").replace("\\\\", "/")
                    if col.lower().endswith(".bsr"):
                        model = col
                        break
                if model:
                    refchars[ref] = model
    print("region refchars resolved to models:", len(refchars))
    for ref, model in sorted(refchars.items()):
        collect_model(model, seen)
    print("after npc models:", len(seen))

    total = 0
    n = 0
    for root, _, files in os.walk(OUT):
        for fn in files:
            total += os.path.getsize(os.path.join(root, fn))
            n += 1
    print(f"extracted {n} files, {total / 1048576:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
