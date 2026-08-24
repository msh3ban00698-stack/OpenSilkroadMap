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
