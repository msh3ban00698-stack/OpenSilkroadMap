import {
  CHARACTERS_KEY,
  getClassStats,
  getStarterKit,
  STARTING_GOLD,
  STARTER_EQUIPMENT,
} from "./game_data";
import type { GameCharacter } from "./types";

export interface Account {
  username: string;
  salt: string;
  hash: string;
  createdAt: number;
}

export const ACCOUNTS_KEY = "silkroad_accounts_v1";
export const SESSION_KEY = "silkroad_session_v1";

async function sha256Hex(text: string): Promise<string> {
  if (globalThis.crypto && typeof crypto.subtle !== "undefined") {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (let i = 0; i < text.length; i++) {
    h1 = Math.imul(h1 ^ text.charCodeAt(i), 0x01000193) >>> 0;
    h2 = (h2 * 31 + text.charCodeAt(i)) >>> 0;
  }
  return `${h1.toString(16)}${h2.toString(16)}`;
}

function loadAccounts(): Account[] {
  try {
    const raw = localStorage.getItem(ACCOUNTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((a) => a && typeof a.username === "string") : [];
  } catch {
    return [];
  }
}

function saveAccounts(list: Account[]): void {
  try {
    localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(list));
  } catch (e) {
    console.warn("Failed to save accounts:", e);
  }
}

export function validateUsername(username: string): string | null {
  const trimmed = username.trim();
  if (!trimmed) return "Username is required.";
  if (trimmed.length < 3) return "Username must be at least 3 characters.";
  if (trimmed.length > 20) return "Username must be at most 20 characters.";
  if (!/^[A-Za-z0-9_]+$/.test(trimmed)) {
    return "Username may contain only letters, digits or underscores.";
  }
  if (loadAccounts().some((a) => a.username.toLowerCase() === trimmed.toLowerCase())) {
    return "That username is already taken.";
  }
  return null;
}

export function validatePassword(password: string): string | null {
  if (!password) return "Password is required.";
  if (password.length < 4) return "Password must be at least 4 characters.";
  return null;
}

export async function createAccount(username: string, password: string): Promise<{ ok: boolean; error?: string }> {
  const uname = username.trim();
  const err = validateUsername(uname) ?? validatePassword(password);
  if (err) return { ok: false, error: err };
  const salt = Math.random().toString(36).slice(2, 10);
  const hash = await sha256Hex(`${salt}::${password}`);
  const list = loadAccounts();
  list.push({ username: uname, salt, hash, createdAt: Date.now() });
  saveAccounts(list);
  setSession(uname);
  return { ok: true };
}

export async function loginAccount(username: string, password: string): Promise<{ ok: boolean; error?: string }> {
  const uname = username.trim();
  const acc = loadAccounts().find((a) => a.username.toLowerCase() === uname.toLowerCase());
  if (!acc) return { ok: false, error: "Account not found." };
  const hash = await sha256Hex(`${acc.salt}::${password}`);
  if (hash !== acc.hash) return { ok: false, error: "Incorrect password." };
  setSession(acc.username);
  return { ok: true };
}

export function setSession(username: string): void {
  try {
    localStorage.setItem(SESSION_KEY, username);
  } catch {
    /* ignore */
  }
}

export function getSession(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

function charactersKey(account: string | null): string {
  return account ? `${CHARACTERS_KEY}_${account.toLowerCase()}` : CHARACTERS_KEY;
}

export function loadCharacters(account?: string | null): GameCharacter[] {
  try {
    const raw = localStorage.getItem(charactersKey(account ?? getSession()));
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
    exp: typeof c.exp === "number" && c.exp > 0 ? c.exp : 0,
    inventory: Array.isArray(c.inventory)
      ? c.inventory.filter((i) => i && typeof i.id === "string")
      : getStarterKit("kit_blade").bag.map((i) => ({ ...i })),
    equipment: c.equipment && typeof c.equipment === "object"
      ? { ...STARTER_EQUIPMENT, ...c.equipment }
      : { ...STARTER_EQUIPMENT },
  };
}

function saveCharacters(list: GameCharacter[], account?: string | null): void {
  try {
    localStorage.setItem(charactersKey(account ?? getSession()), JSON.stringify(list));
  } catch (e) {
    console.warn("Failed to save characters:", e);
  }
}

export function saveCharacter(char: GameCharacter, account?: string | null): void {
  const list = loadCharacters(account);
  const idx = list.findIndex((c) => c.id === char.id);
  if (idx >= 0) {
    list[idx] = char;
  } else {
    list.push(char);
  }
  saveCharacters(list, account);
}

export function deleteCharacter(id: string, account?: string | null): void {
  const list = loadCharacters(account);
  saveCharacters(list.filter((c) => c.id !== id), account);
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
    region: 1,
    position: { x: 1800, y: 0, z: 5350 },
    gold: STARTING_GOLD,
    hp: stats.hp,
    mp: stats.mp,
    maxHp: stats.hp,
    maxMp: stats.mp,
    exp: 0,
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
