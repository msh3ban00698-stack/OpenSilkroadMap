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
  { id: "warrior", name: "Warrior", race: "Chinese", desc: "Melee fighter; blade, spear or blade masteries." },
  { id: "rogue", name: "Rogue", race: "Chinese", desc: "Fast physical attacker; knife or bow masteries." },
  { id: "cleric", name: "Cleric", race: "Chinese", desc: "Support caster; healing and buffs." },
  { id: "warlock", name: "Warlock", race: "Chinese", desc: "Curses and dark magic." },
  { id: "wizard", name: "Wizard", race: "European", desc: "Elemental damage magic." },
  { id: "bard", name: "Bard", race: "European", desc: "Song magic; buffs the party." },
];

export function getClass(id: string): ClassDef | undefined {
  return VERIFIED_CLASSES.find((c) => c.id === id);
}

// Region 32785 "Cave of Meditation" - fully verified 3D region (Phase B + D).
// Generated assets: map/public/assets/img/silkroad/game/region32785/
export const START_REGION = 32785;
export const START_REGION_NAME = "Cave of Meditation";
export const START_REGION_URL =
  "/assets/img/silkroad/game/region32785";

export const CHARACTERS_KEY = "silkroad_characters_v1";

// Verified "Dungeon Exit" NPC inside region 32785 (npcs.json).
export const REGION_NPCS = [
  {
    id: "dungeon_exit",
    name: "Dungeon Exit",
    x: 1134.79,
    z: -864.29,
  },
];

// Base combat stats per class. HP/MP numbers are gameplay tuning (not
// extracted game values); regenerations are per second.
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

export const STARTING_GOLD = 100;

// Starter gear. The sword is pre-equipped so the character visibly carries the
// real sword mesh; armor + ring start in the bag so equipping them changes HP.
export const STARTER_EQUIPMENT: Record<"weapon" | "armor" | "accessory", string | null> = {
  weapon: "sword_training",
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
    desc: "Leather Armor + Guard Ring in bag, plus 2 Small HP Potions.",
    bag: [
      { id: "armor_leather", count: 1 },
      { id: "ring_guard", count: 1 },
      { id: "potion_small", count: 2 },
      { id: "potion_hp", count: 1 },
    ],
  },
  {
    id: "kit_survival",
    name: "Survival Kit",
    desc: "No armor or ring, but 4 Small HP Potions + 2 HP Potions.",
    bag: [
      { id: "potion_small", count: 4 },
      { id: "potion_hp", count: 2 },
    ],
  },
];

export function getStarterKit(id: string): StarterKit {
  return STARTER_KITS.find((k) => k.id === id) ?? STARTER_KITS[0];
}
