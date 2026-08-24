import {
  CHARACTERS_KEY,
  getClassStats,
  getStarterKit,
  STARTING_GOLD,
  STARTER_EQUIPMENT,
} from "./game_data";
import type { GameCharacter } from "./types";

export function loadCharacters(): GameCharacter[] {
  try {
    const raw = localStorage.getItem(CHARACTERS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((c) => c && typeof c.id === "string").map(normalizeCharacter);
  } catch (e) {
    console.warn("Failed to load characters:", e);
    return [];
  }
}

// Backfill fields added in Phase G for characters saved by earlier phases.
function normalizeCharacter(c: GameCharacter): GameCharacter {
  const stats = getClassStats(c.classId);
  const maxHp = typeof c.maxHp === "number" && c.maxHp > 0 ? c.maxHp : stats.hp;
  const maxMp = typeof c.maxMp === "number" && c.maxMp > 0 ? c.maxMp : stats.mp;
  return {
    ...c,
    gold: typeof c.gold === "number" ? c.gold : STARTING_GOLD,
    hp: typeof c.hp === "number" && c.hp > 0 ? Math.min(c.hp, maxHp) : maxHp,
    mp: typeof c.mp === "number" && c.mp > 0 ? Math.min(c.mp, maxMp) : maxMp,
    maxHp,
    maxMp,
    inventory: Array.isArray(c.inventory)
      ? c.inventory.filter((i) => i && typeof i.id === "string")
      : getStarterKit("kit_blade").bag.map((i) => ({ ...i })),
    equipment: c.equipment && typeof c.equipment === "object"
      ? { ...STARTER_EQUIPMENT, ...c.equipment }
      : { ...STARTER_EQUIPMENT },
  };
}

function saveCharacters(list: GameCharacter[]): void {
  try {
    localStorage.setItem(CHARACTERS_KEY, JSON.stringify(list));
  } catch (e) {
    console.warn("Failed to save characters:", e);
  }
}

export function saveCharacter(char: GameCharacter): void {
  const list = loadCharacters();
  const idx = list.findIndex((c) => c.id === char.id);
  if (idx >= 0) {
    list[idx] = char;
  } else {
    list.push(char);
  }
  saveCharacters(list);
}

export function deleteCharacter(id: string): void {
  const list = loadCharacters();
  saveCharacters(list.filter((c) => c.id !== id));
}

export function createCharacter(input: {
  name: string;
  classId: string;
  gender: "male" | "female";
  skinTone: string;
  hairColor: string;
  outfitColor: string;
  kit: string;
}): GameCharacter {
  const now = Date.now();
  const stats = getClassStats(input.classId);
  const kit = getStarterKit(input.kit);
  const char: GameCharacter = {
    id: `ch_${now.toString(36)}_${Math.random().toString(36).slice(2, 7)}`,
    name: input.name,
    classId: input.classId,
    level: 1,
    appearance: {
      gender: input.gender,
      skinTone: input.skinTone,
      hairColor: input.hairColor,
      outfitColor: input.outfitColor,
    },
    createdAt: now,
    lastPlayedAt: now,
    region: 32785,
    position: { x: 1134.79, y: 0, z: -864.29 },
    gold: STARTING_GOLD,
    hp: stats.hp,
    mp: stats.mp,
    maxHp: stats.hp,
    maxMp: stats.mp,
    inventory: kit.bag.map((i) => ({ ...i })),
    equipment: { ...STARTER_EQUIPMENT },
  };
  saveCharacter(char);
  return char;
}

export function validateName(name: string): string | null {
  const trimmed = name.trim();
  if (!trimmed) return "Name is required.";
  if (trimmed.length < 3) return "Name must be at least 3 characters.";
  if (trimmed.length > 16) return "Name must be at most 16 characters.";
  if (!/^[A-Za-z0-9_\u4e00-\u9fff]+$/.test(trimmed)) {
    return "Name may contain only letters, digits, underscores or CJK characters.";
  }
  const taken = loadCharacters().some((c) => c.name.toLowerCase() === trimmed.toLowerCase());
  if (taken) return "That name is already in use.";
  return null;
}
