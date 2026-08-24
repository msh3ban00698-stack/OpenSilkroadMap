import type { EquipSlot } from "./types";

export type ItemSlot = EquipSlot | "consumable";

export interface ItemDef {
  id: string;
  name: string;
  slot: ItemSlot;
  desc: string;
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

export const ITEMS: Record<string, ItemDef> = {
  sword_training: {
    id: "sword_training",
    name: "Training Sword",
    slot: "weapon",
    desc: "A worn practice blade. Reflects on the chinaman_fighter model as its real sword (mesh part 15).",
    color: "#c9a86a",
    attack: 8,
    value: 25,
    icon: bladeSvg("#c9a86a"),
  },
  armor_leather: {
    id: "armor_leather",
    name: "Leather Armor",
    slot: "armor",
    desc: "Sturdy leather tunic. +20 max HP. No distinct 3D model is available, so only stats change.",
    color: "#7a5c2e",
    defense: 4,
    hpBonus: 20,
    value: 30,
    icon: shieldSvg("#7a5c2e"),
  },
  ring_guard: {
    id: "ring_guard",
    name: "Guard Ring",
    slot: "accessory",
    desc: "A simple iron ring. +2 defense. No distinct 3D model is available, so only stats change.",
    color: "#d4a437",
    defense: 2,
    value: 18,
    icon: ringSvg("#d4a437"),
  },
  potion_small: {
    id: "potion_small",
    name: "Small HP Potion",
    slot: "consumable",
    desc: "Restores 40 HP.",
    color: "#e05252",
    heal: 40,
    value: 8,
    icon: potionSvg("#e05252"),
  },
  potion_hp: {
    id: "potion_hp",
    name: "HP Potion",
    slot: "consumable",
    desc: "Restores 90 HP.",
    color: "#ff6b6b",
    heal: 90,
    value: 16,
    icon: potionSvg("#ff6b6b"),
  },
};

export function getItem(id: string): ItemDef | undefined {
  return ITEMS[id];
}

export function isEquippable(item: ItemDef | undefined): item is ItemDef & { slot: EquipSlot } {
  return !!item && (item.slot === "weapon" || item.slot === "armor" || item.slot === "accessory");
}
