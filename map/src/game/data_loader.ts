import levelData from "./data/level_progression.json";
import itemData from "./data/items.json";
import skillData from "./data/skills.json";
import masteryData from "./data/masteries.json";

// Phase H: verified VSRO 1.193 data extracted from the external package
// (scripts/generate_phase_h_data.py). Kept small and committed under src/game/data.

export interface LevelEntry {
  level: number;
  expToNext: number;
  spColumn2: number;
  masteryColumn3: number;
  masteryColumn4: number;
}

export interface RealItem {
  id: string;
  refId: number;
  code: string;
  name: string;
  levelReq: number;
  slot: string;
  rawCol13: number;
  rawCol26: number;
  rawCol27: number;
  rawCol28: number;
}

export interface RealSkill {
  id: number | null;
  code: string;
  name: string;
  levelReq: number;
  masteryId: number | null;
  nameKey: string;
}

export interface MasteryEntry {
  id: string;
  code: string;
  name: string;
  officialKey: string | null;
  officialName: string | null;
}

export const MAX_LEVEL = 150;

const LEVELS = (levelData as { levels: LevelEntry[] }).levels;
const ITEMS = (itemData as { items: RealItem[] }).items;
const CLASS_SKILLS = (
  skillData as {
    classes: Record<string, { masteryId: string | null; mastery: string | null; skills: RealSkill[] }>;
  }
).classes;
const MASTERIES = (masteryData as { masteries: MasteryEntry[] }).masteries;

export function expToNext(level: number): number {
  if (level >= MAX_LEVEL) return 0;
  const entry = LEVELS.find((l) => l.level === level);
  return entry ? entry.expToNext : 0;
}

const itemById = new Map(ITEMS.map((i) => [i.id, i]));
export function getRealItem(id: string): RealItem | undefined {
  return itemById.get(id);
}

const masteryById = new Map(MASTERIES.map((m) => [m.id, m]));
export function getMastery(id: string | null): MasteryEntry | undefined {
  return id ? masteryById.get(id) : undefined;
}

export function getClassSkills(classId: string): RealSkill[] {
  return CLASS_SKILLS[classId]?.skills ?? [];
}

export function getClassMasteryName(classId: string): string | null {
  return CLASS_SKILLS[classId]?.mastery ?? null;
}
