export interface ClassDef {
  id: string;
  name: string;
  race: string;
  desc: string;
}

// Class names verified from the external package textdata:
// Media.pk2 server_dep/silkroad/textdata/textdata_equip&skill.txt
//   UIIT_STT_WARRIOR => Warrior, UIIT_STT_ROG => Rogue,
//   UIIT_STT_CLERIC => Cleric, UIIT_STT_WARLOCK => Warlock,
//   UIIT_STT_WIZARD => Wizard, UIIT_STT_BARD => Bard
// Race assignment per class is inferred from the class set (not a verified
// translation); the UI marks it "(inferred)".
export const VERIFIED_CLASSES: ClassDef[] = [
  {
    id: "warrior",
    name: "Warrior",
    race: "Chinese",
    desc: "Chinese melee fighter. Verified masteries: Sword + Lightning.",
  },
  { id: "rogue", name: "Rogue", race: "Chinese", desc: "Chinese physical fighter. Verified masteries: Spear + Cold." },
  {
    id: "cleric",
    name: "Cleric",
    race: "Chinese",
    desc: "Chinese support caster. Verified masteries: Bow + Fire, plus the Water healing line.",
  },
  {
    id: "warlock",
    name: "Warlock",
    race: "European",
    desc: "European caster. No skill data for this class exists in the package.",
  },
  {
    id: "wizard",
    name: "Wizard",
    race: "European",
    desc: "European elemental caster. Verified mastery: European Wizard (Force).",
  },
  {
    id: "bard",
    name: "Bard",
    race: "European",
    desc: "European support class. No skill data for this class exists in the package.",
  },
];

export function getClass(id: string): ClassDef | undefined {
  return VERIFIED_CLASSES.find((c) => c.id === id);
}

// Region 1 Constantinople - real 3D world generated from the original VSRO
// packages (scripts/extract_ct.py + scripts/generate_region_ct.py).
// Assets: map/public/assets/img/silkroad/game/region1/
export const START_REGION = 1;
export const START_REGION_NAME = "Constantinople";
export const START_REGION_URL = "/assets/img/silkroad/game/region1";

export const CHARACTERS_KEY = "silkroad_characters_v1";

// Verified "Dungeon Exit" NPC inside region 32785 (npcs.json). Used only when a
// region has no generated buildings manifest (region 1 supplies real npcpos
// placements through buildings.json instead).
export const REGION_NPCS = [
  {
    id: "dungeon_exit",
    name: "Dungeon Exit",
    x: 1134.79,
    z: -864.29,
  },
];

// Base combat stats per class. HP/MP numbers are gameplay tuning (not
// extracted game values); no verified player-stat table is present in the
// package's server_dep textdata (characterdata_all contains only NPC/mob/COS
// templates). Regenerations are per second.
export interface ClassStats {
  hp: number;
  mp: number;
  regenHp: number;
  regenMp: number;
}

export const CLASS_STATS: Record<string, ClassStats> = {
  warrior: { hp: 140, mp: 60, regenHp: 2.4, regenMp: 1.2 },
  rogue: { hp: 110, mp: 80, regenHp: 2.0, regenMp: 1.5 },
  cleric: { hp: 100, mp: 90, regenHp: 1.8, regenMp: 1.8 },
  warlock: { hp: 90, mp: 100, regenHp: 1.6, regenMp: 2.0 },
  wizard: { hp: 80, mp: 110, regenHp: 1.4, regenMp: 2.2 },
  bard: { hp: 90, mp: 90, regenHp: 1.6, regenMp: 1.8 },
};

export function getClassStats(classId: string): ClassStats {
  return CLASS_STATS[classId] ?? CLASS_STATS.warrior;
}

// Per-level stat growth (gameplay tuning; no verified player table exists).
export const HP_PER_LEVEL = 6;
export const MP_PER_LEVEL = 3;

export const STARTING_GOLD = 10000;

// Starter gear, using verified level-1 items from itemdata_5000.txt:
//   sword_01_a        ITEM_CH_SWORD_01_A        Copper Sword
//   m_heavy_01_ba_a   ITEM_CH_M_HEAVY_01_BA_A  Copper Armor
//   ring_01_a         ITEM_CH_RING_01_A        Ume Copper Ring
//   hp_potion_01      ITEM_ETC_HP_POTION_01    HP Recovery Herb
//   hp_potion_02      ITEM_ETC_HP_POTION_02    HP Recovery Potion (Small)
// The sword is pre-equipped so the character visibly carries the real sword
// mesh; armor + ring start in the bag so equipping them changes HP.
export const STARTER_EQUIPMENT: Record<"weapon" | "armor" | "accessory", string | null> = {
  weapon: "sword_01_a",
  armor: null,
  accessory: null,
};

export interface StarterKit {
  id: string;
  name: string;
  desc: string;
  bag: { id: string; count: number }[];
}

// The blade kit is the "balanced" start; the survival kit trades armor/ring for
// extra potions. Only the sword has a real 3D appearance (see items.ts).
export const STARTER_KITS: StarterKit[] = [
  {
    id: "kit_blade",
    name: "Blade Kit",
    desc: "Copper Armor + Ume Copper Ring in bag, plus 2 HP Recovery Herbs and 1 Small HP Potion.",
    bag: [
      { id: "m_heavy_01_ba_a", count: 1 },
      { id: "ring_01_a", count: 1 },
      { id: "hp_potion_01", count: 2 },
      { id: "hp_potion_02", count: 1 },
    ],
  },
  {
    id: "kit_survival",
    name: "Survival Kit",
    desc: "No armor or ring, but 4 HP Recovery Herbs + 2 Small HP Potions.",
    bag: [
      { id: "hp_potion_01", count: 4 },
      { id: "hp_potion_02", count: 2 },
    ],
  },
];

export function getStarterKit(id: string): StarterKit {
  return STARTER_KITS.find((k) => k.id === id) ?? STARTER_KITS[0];
}
