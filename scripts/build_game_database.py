"""Build the runtime game database from authentic VSRO textdata tables.

Reads the tab-separated game configuration tables under
game_source/Media/server_dep/silkroad/textdata and emits normalized JSON
databases consumed by the map client:

    map/public/assets/gamedata/
        names.json      sn-code -> display string
        items.json      item code -> item record
        chars.json      npc/mob code -> character record
        spawns.json     npcpos placements joined to char ids
        shops.json      npc -> shop tabs -> item codes
        teleports.json  gate network (positions + links)
        quests.json     quest definitions
        levels.json     experience curve

Usage: uv run scripts/build_game_database.py
"""

import glob
import json
import os

BASE = "game_source/Media/server_dep/silkroad/textdata"
OUT = "map/public/assets/gamedata"


def read_table(name):
    """Read a textdata table as a list of rows (UTF-16 TSV)."""
    path = os.path.join(BASE, name)
    rows = []
    with open(path, encoding="utf-16", errors="replace") as f:
        f.readline()
        for line in f:
            line = line.rstrip("\r\n")
            if line:
                rows.append(line.split("\t"))
    return rows


def build_names():
    names = {}
    for fn in [
        "textdataname.txt",
        "textzonename.txt",
        "textquest_queststring.txt",
        "textquest_speech&name.txt",
        "textdata_object.txt",
        "textdata_equip&skill.txt",
        "textuisystem.txt",
    ]:
        path = os.path.join(BASE, fn)
        if not os.path.exists(path):
            continue
        for enc in ("utf-16", "utf-8", "utf-8-sig"):
            try:
                with open(path, encoding=enc) as f:
                    raw = f.read()
                break
            except UnicodeDecodeError:
                continue
        for line in raw.splitlines()[1:]:
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) < 3:
                continue
            sn = parts[1].strip()
            tail = [p.strip() for p in parts[2:] if p.strip()]
            if not tail:
                continue
            txt = tail[-1]
            if sn.startswith(("SN_", "UIC_", "QNO_", "QSP_")):
                names.setdefault(sn, txt)
            elif sn.isdigit():
                names.setdefault("ZONE_" + sn, txt)
    return names


def build_items(names):
    items = {}
    for path in sorted(glob.glob(os.path.join(BASE, "itemdata*.txt"))):
        if "enc" in path.lower():
            continue
        with open(path, encoding="utf-16", errors="replace") as f:
            f.readline()
            for line in f:
                r = line.rstrip("\r\n").split("\t")
                if len(r) < 64 or r[0] != "1":
                    continue
                code = r[2]
                icon = r[54] if len(r) > 54 else ""
                item = {
                    "id": int(r[1]) if r[1].isdigit() else 0,
                    "code": code,
                    "sn": r[5],
                    "name": names.get(r[5], code),
                    "price": _int(r[13]),
                    "stack": _int(r[11]) or 1,
                    "level": _int(r[57]) if len(r) > 57 else 0,
                    "cls": code.split("_")[1] if "_" in code else "",
                    "kind": code.split("_")[0] if "_" in code else "",
                    "icon": os.path.basename(icon).replace(".ddj", "") if icon else "",
                    "model": r[52] if len(r) > 52 else "",
                }
                items[code] = item
    return items


def build_chars(names):
    chars = {}
    with open(os.path.join(BASE, "characterdata_all.txt"), encoding="utf-16", errors="replace") as f:
        f.readline()
        for line in f:
            r = line.rstrip("\r\n").split("\t")
            if len(r) < 60 or r[0] != "1":
                continue
            code = r[2]
            kind = "npc" if code.startswith("NPC") else ("mob" if code.startswith("MOB") else "other")
            cid = _int(r[1])
            rec = {
                "id": cid,
                "code": code,
                "kind": kind,
                "sn": r[5],
                "name": names.get(r[5], code),
                "level": _int(r[57]) if len(r) > 57 else 0,
                "hp": _int(r[59]) if len(r) > 59 else 0,
                "model": r[52] if len(r) > 52 else "",
                "radius": _float(r[48]) if len(r) > 48 else 1.0,
            }
            chars[cid] = rec
            chars[code] = rec
    return chars


def build_spawns(chars):
    spawns = []
    for r in read_table("npcpos.txt"):
        if len(r) < 5:
            continue
        cid = _int(r[0])
        rec = chars.get(cid)
        if not rec:
            continue
        spawns.append(
            {
                "cid": cid,
                "code": rec["code"],
                "kind": rec["kind"],
                "region": _int(r[1]),
                "x": _float(r[2]),
                "z": _float(r[4]),
                "y": _float(r[3]),
            }
        )
    return spawns


SHOP_GROUP_NPC = {}


def build_shops(items):
    group_npc = {}
    for r in read_table("refshopgroup.txt"):
        if len(r) > 4:
            group_npc[r[3]] = r[4]
    shop_group = {}
    for r in read_table("refshop.txt"):
        if len(r) > 3:
            shop_group[r[3]] = r[3]
    tabgroup_of_shop = {}
    for r in read_table("refmappingshopwithtab.txt"):
        if len(r) > 3:
            tabgroup_of_shop[r[2]] = r[3]
    tabs_in_group = {}
    for r in read_table("refshoptab.txt"):
        if len(r) > 3:
            tabs_in_group.setdefault(r[4], []).append(r[3])
    goods_by_tab = {}
    for r in read_table("refshopgoods.txt"):
        if len(r) > 3:
            goods_by_tab.setdefault(r[2], []).append(r[3])

    def resolve_package(pkg):
        code = pkg.replace("PACKAGE_", "")
        if code in items:
            return code
        base_code = code.rsplit("_", 1)[0]
        for cand in (base_code, code[:-2]):
            if cand in items:
                return cand
        return None

    shops = {}
    for shop, _sg in shop_group.items():
        tg = tabgroup_of_shop.get(shop)
        if not tg:
            continue
        tabs = []
        for tab in tabs_in_group.get(tg, []):
            codes = []
            seen = set()
            for pkg in goods_by_tab.get(tab, []):
                c = resolve_package(pkg)
                if c and c in items and c not in seen:
                    seen.add(c)
                    codes.append(c)
            if codes:
                tabs.append({"tab": tab, "items": codes})
        # attach to an NPC via group naming fallback GROUP_<SHOP>
        npc = group_npc.get("GROUP_" + shop)
        if npc:
            shops[npc] = {"shop": shop, "tabs": tabs}
    return shops


def build_teleports(names):
    gates = {}
    for r in read_table("teleportdata.txt"):
        if len(r) < 10 or r[0] != "1":
            continue
        gid = _int(r[1])
        gates[gid] = {
            "id": gid,
            "linkId": _int(r[3]),
            "code": r[2],
            "sn": r[4],
            "name": names.get(r[4], r[2]),
            "region": _int(r[5]),
            "x": _float(r[6]),
            "y": _float(r[7]),
            "z": _float(r[8]),
        }
    links = []
    for r in read_table("teleportlink.txt"):
        if len(r) < 3:
            continue
        a, b = _int(r[1]), _int(r[2])
        if a in gates and b in gates:
            links.append([a, b])
    buildings = {}
    for r in read_table("teleportbuilding.txt"):
        if len(r) > 5:
            buildings[r[2]] = r[5]
    return {"gates": list(gates.values()), "links": links, "buildings": buildings}


def build_quests(names):
    quests = []
    for r in read_table("questdata.txt"):
        if len(r) < 11 or r[0] != "1":
            continue
        qno = r[2]
        quests.append(
            {
                "code": qno,
                "titleSn": r[5],
                "paySn": r[6],
                "nn": r[9],
                "nc": r[10],
                "contents": [],
            }
        )
    by_code = {q["code"]: q for q in quests}
    for r in read_table("questcontentsdata.txt"):
        if len(r) < 6:
            continue
        q = by_code.get(r[0])
        if not q:
            continue
        con = {
            "sn": next((c for c in r if c.startswith("SN_CON_")), ""),
            "state": _int(r[2]) if len(r) > 2 and r[2].isdigit() else 0,
        }
        q["contents"].append(con)
    out = [q for q in quests if q["code"].startswith("QNO_")]
    return out


def build_skills(names):
    skills = {}
    for r in read_table("skilldata_10000.txt"):
        if len(r) < 66 or r[0] != "1":
            continue
        code = r[3]
        if not code.startswith("SKILL_CH"):
            continue
        sn = r[62] if len(r) > 62 else ""
        icon = r[61] if len(r) > 61 else ""
        skills[code] = {
            "id": _int(r[1]),
            "code": code,
            "sn": sn,
            "name": names.get(sn, code),
            "reqLevel": _int(r[7]),
            "sp": _int(r[8]),
            "mp": _int(r[12]),
            "cooldown": _int(r[14]),
            "icon": os.path.basename(icon).replace(".ddj", "") if icon else "",
        }
    return skills


def build_levels():
    levels = []
    for r in read_table("leveldata.txt"):
        if len(r) < 8:
            continue
        levels.append({"level": _int(r[2]), "exp": _int(r[6])})
    levels.sort(key=lambda e: e["level"])
    return levels


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main():
    os.makedirs(OUT, exist_ok=True)
    print("names...")
    names = build_names()
    json_dump("names.json", names)
    print(f"  {len(names)} strings")
    print("items...")
    items = build_items(names)
    json_dump("items.json", items)
    print(f"  {len(items)} items")
    print("chars...")
    chars = build_chars(names)
    json_dump("chars.json", {k: v for k, v in chars.items() if isinstance(k, int)})
    print(f"  {sum(1 for k in chars if isinstance(k, int))} characters")
    print("spawns...")
    spawns = build_spawns(chars)
    json_dump("spawns.json", spawns)
    print(f"  {len(spawns)} spawn points")
    print("shops...")
    shops = build_shops(items)
    json_dump("shops.json", shops)
    print(f"  {len(shops)} npc shops")
    print("teleports...")
    teleports = build_teleports(names)
    json_dump("teleports_full.json", teleports)
    print(f"  {len(teleports['gates'])} gates / {len(teleports['links'])} links")
    print("quests...")
    quests = build_quests(names)
    json_dump("quests.json", quests)
    print(f"  {len(quests)} quests")
    print("skills...")
    skills = build_skills(names)
    json_dump("skills_full.json", skills)
    print(f"  {len(skills)} skills")
    print("levels...")
    json_dump("levels.json", build_levels())
    print("done")


def json_dump(name, data):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
