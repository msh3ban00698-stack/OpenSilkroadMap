#!/usr/bin/env python3
"""Extract Constantinople (region 1) sources from the VSRO packages into game_source/CT/.

Extracts:
  - 36 terrain blocks (Map.pk2 {Y}/{X}.m) and 36 object overlays (Map.pk2 {Y}/{X}.o2)
  - 36 minimap tiles (Media.pk2 minimap/{X}x{Y}.ddj)
  - object.ifo + RegionInfo.txt (Data.pk2)
  - npcpos.txt + characterdata_*.txt (Media.pk2)
  - full dependency closure of building/NPC/mob bsr + bms + bmt + ddj textures
"""
import os
import struct
import sys

PK2ROOT = "/tmp/opencode/vsro"
sys.path.insert(0, PK2ROOT)
import pk2reader  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "game_source", "CT")
SECTORS = [(x, y) for y in range(103, 109) for x in range(76, 82)]

data = pk2reader.PK2(os.path.join(PK2ROOT, "pk2/Data.pk2"))
mapk = pk2reader.PK2(os.path.join(PK2ROOT, "pk2/Map.pk2"))
media = pk2reader.PK2(os.path.join(PK2ROOT, "pk2/Media.pk2"))


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


def gbk(s):
    return s.decode("gbk", "replace").replace("\\", "/")


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


def collect_model(dst_prefix, path, seen):
    """Extract bsr + its bms + bmt + ddj closure into OUT/Data, recursive through bms->?."""
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
            print("  missing bsr:", path)
            return
        store(data, path, "Data/" + path)
        r = parse_bsr(blob)
        if r is None:
            return
        mpath, bms = r
        if mpath:
            mt = find(data, mpath)
            if mt is None:
                print("  missing bmt:", mpath)
            else:
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
                    else:
                        print("  missing ddj:", tp)
        for b in bms:
            collect_model(dst_prefix, b, seen)
    elif path.endswith(".bms"):
        blob = find(data, path)
        if blob is None:
            print("  missing bms:", path)
        else:
            store(data, path, "Data/" + path)


def main():
    # --- terrain / overlays (Map.pk2) ---
    for x, y in SECTORS:
        store(mapk, f"{y}/{x}.m", f"Map/{y}/{x}.m")
        store(mapk, f"{y}/{x}.o2", f"Map/{y}/{x}.o2")
    # --- minimap tiles (Media.pk2) ---
    for x, y in SECTORS:
        store(media, f"minimap/{x}x{y}.ddj", f"Media/minimap/{x}x{y}.ddj")
    # --- text / index files ---
    store(data, "RegionInfo.txt", "Data/RegionInfo.txt")
    store(data, "navmesh/object.ifo", "Data/navmesh/object.ifo")
    store(media, "server_dep/silkroad/textdata/npcpos.txt", "Media/npcpos.txt")

    # characterdata file list
    cd_list = find(media, "server_dep/silkroad/textdata/characterdata.txt")
    if cd_list is not None:
        store(media, "server_dep/silkroad/textdata/characterdata.txt", "Media/characterdata.txt")
        for fn in cd_list.decode("utf-16-le", "replace").replace("\r", "").split():
            fn = fn.strip()
            if fn:
                store(media, f"server_dep/silkroad/textdata/{fn}", f"Media/{fn}")

    # --- object index (bsr paths for CT) ---
    ifo = find(data, "navmesh/object.ifo").decode("gbk", "replace")
    objects = []
    for ln in ifo.splitlines():
        i = ln.find('"')
        j = ln.rfind('"')
        objects.append(ln[i + 1 : j].replace("\\", "/"))

    # --- all bsrs referenced by CT .o2 files ---
    bsrset = set()
    for x, y in SECTORS:
        blob = find(mapk, f"{y}/{x}.o2")
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
    print("CT bsr set:", len(bsrset))
    seen = set()
    for path in sorted(bsrset):
        collect_model("Data/", path, seen)
    print("extracted model files:", len(seen))

    # --- CT npc/mob models from characterdata (only refchars that spawn in CT) ---
    ct_refs = set()
    npc_path = os.path.join(OUT, "Media", "npcpos.txt")
    if os.path.exists(npc_path):
        with open(npc_path, encoding="utf-16-le") as f:
            for ln in f:
                cols = ln.rstrip("\r\n").split("\t")
                if len(cols) < 2:
                    continue
                try:
                    region = int(cols[1].strip())
                except ValueError:
                    continue
                if 103 <= (region >> 8) <= 108:
                    try:
                        ct_refs.add(int(cols[0].strip()))
                    except ValueError:
                        pass
    print("CT refchars from npcpos:", len(ct_refs))
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
                if ref not in ct_refs:
                    continue
                model = ""
                for col in parts[3:]:
                    col = col.replace("\\", "/").replace("\\\\", "/")
                    if col.lower().endswith(".bsr"):
                        model = col
                        break
                if model:
                    refchars[ref] = model
    print("CT refchars resolved to models:", len(refchars))
    for ref, model in sorted(refchars.items()):
        collect_model("Data/", model, seen)
    print("after npc models:", len(seen))

    # --- summary of extracted sizes ---
    total = 0
    n = 0
    for root, _, files in os.walk(OUT):
        for fn in files:
            sz = os.path.getsize(os.path.join(root, fn))
            total += sz
            n += 1
    print(f"extracted {n} files, {total / 1048576:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
