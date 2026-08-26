export interface Appearance {
  gender: "male" | "female";
  skinTone: string;
  hairColor: string;
  outfitColor: string;
}

export type EquipSlot = "weapon" | "armor" | "accessory";

export interface InventoryItem {
  id: string;
  count: number;
}

export interface QuestProgress {
  code: string;
  progress: number;
}

export interface PartyMember {
  code: string;
  name: string;
}

export interface GameCharacter {
  id: string;
  name: string;
  classId: string;
  level: number;
  appearance: Appearance;
  createdAt: number;
  lastPlayedAt: number;
  region: number;
  position: { x: number; y: number; z: number };
  gold: number;
  hp: number;
  mp: number;
  maxHp: number;
  maxMp: number;
  exp: number;
  inventory: InventoryItem[];
  equipment: Record<EquipSlot, string | null>;
  questLog?: QuestProgress[];
  questsDone?: string[];
  party?: PartyMember[];
  warehouse?: InventoryItem[];
}

export type GameState = "intro" | "login" | "select" | "create" | "loading" | "in-world" | "paused" | "map";
