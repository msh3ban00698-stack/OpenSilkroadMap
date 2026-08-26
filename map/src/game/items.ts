import type { EquipSlot } from "./types";
import { getRealItem } from "./data_loader";

export type ItemSlot = EquipSlot | "consumable";

export interface ItemDef {
  id: string;
  code: string;
  refId: number;
  name: string;
  slot: ItemSlot;
  desc: string;
  levelReq: number;
  color: string;
  attack?: number;
  defense?: number;
  hpBonus?: number;
  heal?: number;
  value: number;
  icon: string;
}

function svgIcon(svg: string): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function shieldSvg(fill: string): string {
  return svgIcon(
    `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><path fill="${fill}" stroke="#2a1d10" stroke-width="2" d="M24 4 L40 10 V24 C40 34 33 42 24 44 C15 42 8 34 8 24 V10 Z"/><path fill="#000" opacity="0.35" d="M24 4 L40 10 V24 C40 28 38 32 35 35 L24 4 Z"/></svg>`,
  );
}

function bladeSvg(fill: string): string {
  return svgIcon(
    `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><path fill="${fill}" stroke="#2a1d10" stroke-width="2" d="M30 4 L44 18 L18 44 L4 30 Z"/><rect x="17" y="31" width="18" height="6" rx="2" fill="#6b4a2a" stroke="#2a1d10"/><rect x="32" y="3" width="6" height="18" rx="2" fill="#d8c9a0" stroke="#2a1d10"/></svg>`,
  );
}

function ringSvg(fill: string): string {
  return svgIcon(
    `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><circle cx="24" cy="26" r="14" fill="none" stroke="${fill}" stroke-width="6"/><circle cx="24" cy="26" r="5" fill="#3a5ba0" stroke="#2a1d10" stroke-width="1.5"/><rect x="20" y="6" width="8" height="10" rx="3" fill="${fill}" stroke="#2a1d10"/></svg>`,
  );
}

function potionSvg(fill: string): string {
  return svgIcon(
    `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><path fill="${fill}" stroke="#2a1d10" stroke-width="2" d="M18 6 h12 v8 a10 10 0 0 1 6 9 v13 a6 6 0 0 1 -6 6 h-12 a6 6 0 0 1 -6 -6 v-13 a10 10 0 0 1 6 -9 Z"/><rect x="21" y="3" width="6" height="6" rx="2" fill="#7a3c1d"/><path fill="#000" opacity="0.25" d="M24 14 a10 10 0 0 1 6 9 v13 a6 6 0 0 1 -6 6 Z"/></svg>`,
  );
}

// Items mirror verified entries from itemdata_5000.txt (extracted in
// scripts/generate_phase_h_data.py and loaded via data_loader.ts). Names,
// codes, refId and levelReq come from that file; heal amounts are the
// game's ItemLifeColumn value (rawCol26). Attack/defense/hpBonus/value and
// colors are gameplay tuning; icons are generated SVG placeholders.
const REAL = {
  sword: getRealItem("sword_01_a"),
  armor: getRealItem("m_heavy_01_ba_a"),
  ring: getRealItem("ring_01_a"),
  herb: getRealItem("hp_potion_01"),
  potion: getRealItem("hp_potion_02"),
};

export const ITEMS: Record<string, ItemDef> = {
  sword_01_a: {
    id: "sword_01_a",
    code: REAL.sword?.code ?? "ITEM_CH_SWORD_01_A",
    refId: REAL.sword?.refId ?? 5000,
    name: REAL.sword?.name ?? "Copper Sword",
    slot: "weapon",
    desc: "The copper sword. Reflects on the chinaman_fighter model as its real sword (mesh part 15).",
    color: "#c9a86a",
    attack: 8,
    value: 25,
    levelReq: REAL.sword?.levelReq ?? 1,
    icon: bladeSvg("#c9a86a"),
  },
  m_heavy_01_ba_a: {
    id: "m_heavy_01_ba_a",
    code: REAL.armor?.code ?? "ITEM_CH_M_HEAVY_01_BA_A",
    refId: REAL.armor?.refId ?? 5001,
    name: REAL.armor?.name ?? "Copper Armor",
    slot: "armor",
    desc: "Copper heavy armor. +20 max HP. No distinct 3D model is available, so only stats change.",
    color: "#7a5c2e",
    defense: 4,
    hpBonus: 20,
    value: 30,
    levelReq: REAL.armor?.levelReq ?? 1,
    icon: shieldSvg("#7a5c2e"),
  },
  ring_01_a: {
    id: "ring_01_a",
    code: REAL.ring?.code ?? "ITEM_CH_RING_01_A",
    refId: REAL.ring?.refId ?? 5002,
    name: REAL.ring?.name ?? "Ume Copper Ring",
    slot: "accessory",
    desc: "A simple copper ring. +2 defense. No distinct 3D model is available, so only stats change.",
    color: "#d4a437",
    defense: 2,
    value: 18,
    levelReq: REAL.ring?.levelReq ?? 1,
    icon: ringSvg("#d4a437"),
  },
  hp_potion_01: {
    id: "hp_potion_01",
    code: REAL.herb?.code ?? "ITEM_ETC_HP_POTION_01",
    refId: REAL.herb?.refId ?? 5003,
    name: REAL.herb?.name ?? "HP Recovery Herb",
    slot: "consumable",
    desc: "Restores 60 HP.",
    color: "#e05252",
    heal: REAL.herb?.rawCol26 ?? 60,
    value: 8,
    levelReq: REAL.herb?.levelReq ?? 1,
    icon: potionSvg("#e05252"),
  },
  hp_potion_02: {
    id: "hp_potion_02",
    code: REAL.potion?.code ?? "ITEM_ETC_HP_POTION_02",
    refId: REAL.potion?.refId ?? 5004,
    name: REAL.potion?.name ?? "HP Recovery Potion (Small)",
    slot: "consumable",
    desc: "Restores 110 HP.",
    color: "#ff6b6b",
    heal: REAL.potion?.rawCol26 ?? 110,
    value: 16,
    levelReq: REAL.potion?.levelReq ?? 1,
    icon: potionSvg("#ff6b6b"),
  },
};

const AUTHENTIC = new Map<string, ItemDef>();

export function registerAuthenticItem(code: string, def: ItemDef): void {
  if (!AUTHENTIC.has(code)) AUTHENTIC.set(code, def);
}

export function getItem(id: string): ItemDef | undefined {
  return ITEMS[id] || AUTHENTIC.get(id);
}

const WEAPON_WORDS = ["SWORD", "BLADE", "BOW", "SPEAR", "STAFF", "AXE", "SHIELD", "TSWORD", "DAGGER"];
const ARMOR_WORDS = ["CLOTHES", "HEAVY", "LIGHT", "ROBE", "ARMOR"];
const ACC_WORDS = ["RING", "NECKLACE", "EARRING"];

export function authenticItemDef(
  code: string,
  name: string,
  price: number,
  iconUrl: string | null,
  level: number,
): ItemDef {
  const up = code.toUpperCase();
  let slot: ItemSlot = "consumable";
  if (WEAPON_WORDS.some((w) => up.includes(w))) slot = "weapon";
  else if (ARMOR_WORDS.some((w) => up.includes(w))) slot = "armor";
  else if (ACC_WORDS.some((w) => up.includes(w))) slot = "accessory";
  return {
    id: code,
    code,
    refId: 0,
    name,
    slot,
    desc: level ? `Requires level ${level}.` : "",
    levelReq: level || 1,
    color: "#d8c9a0",
    value: Math.max(1, price),
    icon:
      iconUrl ||
      svgIcon(
        `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><rect width="48" height="48" fill="#3a2d1c"/></svg>`,
      ),
  };
}

export function isEquippable(item: ItemDef | undefined): item is ItemDef & { slot: EquipSlot } {
  return !!item && (item.slot === "weapon" || item.slot === "armor" || item.slot === "accessory");
}
