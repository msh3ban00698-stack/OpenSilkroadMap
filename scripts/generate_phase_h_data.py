import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = "game_source/Media/server_dep/silkroad/textdata"
OUT = "map/src/game/data"


def read_utf16(name):
    with open(os.path.join(BASE, name), "rb") as f:
        return f.read().decode("utf-16", "replace")


def rows_of(name):
    data = read_utf16(name)
    return [l.split("\t") for l in data.splitlines() if l.strip()]


def build_translations(filenames):
    tr = {}
    for fn in filenames:
        for r in rows_of(fn):
            if len(r) > 8 and r[0] == "1" and r[1]:
                val = r[8].strip()
                if val and val not in ("0", "xxx"):
                    tr[r[1]] = val
    return tr


def main():
    os.makedirs(OUT, exist_ok=True)
    trans = build_translations(["textdata_equip&skill.txt", "textdata_object.txt"])

    # ------------------------------------------------------------------ levels
    levels = []
    for r in rows_of("leveldata.txt"):
        if len(r) >= 9 and r[0].isdigit():
            levels.append(
                {
                    "level": int(r[0]),
                    "expToNext": int(float(r[1])),
                    "spColumn2": int(float(r[2])),
                    "masteryColumn3": int(float(r[3])),
                    "masteryColumn4": int(float(r[4])),
                }
            )
    level_out = {
        "source": BASE + "/leveldata.txt",
        "note": "expToNext = leveldata col1 (official level EXP requirement to advance from this level).",
        "levels": levels,
    }
    with open(os.path.join(OUT, "level_progression.json"), "w", encoding="utf-8") as f:
        json_dump(level_out, f)
    print("level_progression.json:", len(levels), "levels")

    # ------------------------------------------------------------------ items
    # Selected verified level-1 starter items from itemdata_5000.
    wanted = [
        "ITEM_CH_SWORD_01_A",  # Copper Sword
        "ITEM_CH_BLADE_01_A",  # Copper Blade
        "ITEM_CH_SPEAR_01_A",  # Crescent
        "ITEM_CH_M_HEAVY_01_BA_A",  # Copper Armor (male chest)
        "ITEM_CH_RING_01_A",  # Ume Copper Ring
        "ITEM_ETC_HP_POTION_01",  # HP Recovery Herb
        "ITEM_ETC_HP_POTION_02",  # HP Recovery Potion (Small)
    ]
    items = []
    for r in rows_of("itemdata_5000.txt"):
        if len(r) < 35 or not r[0].isdigit():
            continue
        code = r[2]
        if code not in wanted:
            continue
        # Slot is derived from the item code prefix (verified naming scheme);
        # the itemdata slotcode column (col12) overlaps between weapons and
        # armor pieces, so the code prefix is the reliable discriminator.
        if code.startswith(("ITEM_CH_SWORD", "ITEM_CH_BLADE", "ITEM_CH_SPEAR", "ITEM_CH_TBLADE", "ITEM_CH_BOW")):
            slot = "weapon"
        elif code.startswith(("ITEM_CH_RING", "ITEM_CH_NECKLACE")):
            slot = "accessory"
        elif code.startswith(("ITEM_CH_M_HEAVY", "ITEM_CH_W_HEAVY", "ITEM_CH_M_LIGHT", "ITEM_CH_M_CLOTHES")):
            slot = "armor"
        else:
            slot = "consumable"
        items.append(
            {
                "id": slug(code),
                "refId": int(r[1]),
                "code": code,
                "name": trans.get(r[5], r[5]),
                "levelReq": int(r[33]) if r[33].isdigit() else 0,
                "slot": slot,
                "rawCol13": int(float(r[13])),
                "rawCol26": int(float(r[26])),
                "rawCol27": int(float(r[27])),
                "rawCol28": int(float(r[28])),
            }
        )
    items.sort(key=lambda i: i["refId"])
    item_out = {
        "source": BASE + "/itemdata_5000.txt + textdata_equip&skill.txt + textdata_object.txt",
        "note": "Level-1 starter items with names resolved from the official translations. "
        "rawCol13 / rawCol26 / rawCol27 / rawCol28 are direct itemdata_5000 columns; their "
        "meaning is item-type specific (for HP potions, rawCol26 is the restore amount per SRO "
        "convention). Gameplay tuning lives in the client item defs.",
        "items": items,
    }
    with open(os.path.join(OUT, "items.json"), "w", encoding="utf-8") as f:
        json_dump(item_out, f)
    print("items.json:", len(items), "items")

    # ---------------------------------------------------------------- masteries
    mastery_names = {}
    for r in rows_of("skillmasterydata.txt"):
        if len(r) >= 3 and r[0].isdigit():
            mastery_names[r[0]] = r[2]
    # Mastery id -> code prefix observed in SKILL_CH_* / SKILL_EU_* skill codes.
    code_of = {
        "257": "SWORD",
        "258": "SPEAR",
        "259": "BOW",
        "273": "COLD",
        "274": "LIGHTNING",
        "275": "FIRE",
        "276": "WATER",
        "513": "EU_WARRIOR",
        "514": "EU_WIZARD",
        "515": "EU_ROGUE",
    }
    learnable = []
    for r in rows_of("learnablemastery.txt"):
        if len(r) >= 2 and r[0].isdigit():
            learnable.append({"charRefId": r[0], "masteryId": r[1]})
    masteries = [
        {
            "id": mid,
            "code": code_of[mid],
            "name": code_of[mid].replace("EU_", "European "),
            "officialKey": mastery_names.get(mid),
            "officialName": trans.get(mastery_names.get(mid, "")),
        }
        for mid in code_of
    ]
    mastery_out = {
        "source": BASE + "/skillmasterydata.txt + learnablemastery.txt",
        "note": "The official mastery name strings (UIIT_STT_MASTERY_*) are not present in the "
        "server_dep textdata translations; names are derived from the verified skill-code grouping. "
        "learnablemastery maps character refs 1831/1832/1833/1838 (Chinese) and 1873-1876 (European) "
        "to the mastery ids below.",
        "masteries": masteries,
        "learnableMastery": learnable,
    }
    with open(os.path.join(OUT, "masteries.json"), "w", encoding="utf-8") as f:
        json_dump(mastery_out, f)
    print("masteries.json:", len(masteries), "masteries")

    # ------------------------------------------------------------------ skills
    # Class -> level-1 skills chosen from the verified level-1 skill pool.
    # (Level-1 CH skills come from skilldata_5000; EU from skilldata_10000.)
    class_skills = {
        "warrior": {"masteryId": "257", "mastery": "Sword", "patterns": ["SWORD_SMASH_A", "SWORD_SMASH_B", "SWORD_SMASH_C"]},
        "rogue": {"masteryId": "258", "mastery": "Spear", "patterns": ["SPEAR_PIERCE_A", "SPEAR_CHAIN_A", "SPEAR_FRONTAREA_A"]},
        "cleric": {"masteryId": "276", "mastery": "Water", "patterns": ["WATER_HEAL_A", "WATER_SELFHEAL_A", "WATER_CURE_A"]},
        "wizard": {
            "masteryId": "514",
            "mastery": "European Wizard",
            "patterns": ["WIZARD_MENTALA_DAMAGEUP_A", "WIZARD_MANAP_RANGE_A", "WIZARD_SPIRITP_EARTH_A", "WIZARD_MANAP_DECREASE_A"],
        },
    }

    skill_pool = []
    for fn in ("skilldata_5000.txt", "skilldata_10000.txt"):
        for r in rows_of(fn):
            if len(r) < 63 or not r[0].isdigit():
                continue
            if r[3].startswith(("SKILL_CH", "SKILL_EU")):
                skill_pool.append(r)

    def find_skill(patterns):
        for pat in patterns:
            for r in skill_pool:
                if pat in r[3] and r[7] == "1" and r[62].startswith("SN_SKILL"):
                    return {
                        "id": int(r[2]) if r[2].isdigit() else None,
                        "code": r[3],
                        "name": trans.get(r[62], r[62]),
                        "levelReq": int(r[7]),
                        "masteryId": int(r[34]) if r[34].isdigit() else None,
                        "nameKey": r[62],
                    }
        return None

    classes_out = {}
    for cls, spec in class_skills.items():
        skills = []
        for pat in spec["patterns"]:
            s = find_skill([pat])
            if s:
                skills.append(s)
        classes_out[cls] = {
            "masteryId": spec["masteryId"],
            "mastery": spec["mastery"],
            "skills": skills,
        }
    # Warlock / Bard: no verified mastery data in this package.
    for cls in ("warlock", "bard"):
        classes_out[cls] = {"masteryId": None, "mastery": None, "skills": []}

    skill_out = {
        "source": BASE + "/skilldata_5000.txt + skilldata_10000.txt + textdata_equip&skill.txt",
        "note": "Level-1 skills per class, resolved from verified skill codes and official names. "
        "warlock and bard have no mastery/skill data in this package (their class names exist only "
        "in the UI strings).",
        "classes": classes_out,
    }
    with open(os.path.join(OUT, "skills.json"), "w", encoding="utf-8") as f:
        json_dump(skill_out, f)
    print("skills.json:", {k: len(v["skills"]) for k, v in classes_out.items()})

    print("Done. Wrote", sorted(os.listdir(OUT)))


def slug(code):
    return code.replace("ITEM_CH_", "").replace("ITEM_ETC_", "").replace("ITEM_", "").lower()


def json_dump(obj, f):
    import json

    json.dump(obj, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
