import { CHARACTERS_KEY } from "./game_data";
import type { GameCharacter } from "./types";

export function loadCharacters(): GameCharacter[] {
  try {
    const raw = localStorage.getItem(CHARACTERS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((c) => c && typeof c.id === "string");
  } catch (e) {
    console.warn("Failed to load characters:", e);
    return [];
  }
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
}): GameCharacter {
  const now = Date.now();
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
