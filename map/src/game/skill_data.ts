import { getAllClassSkills } from "./data_loader";

export interface SkillFull {
  id: number;
  code: string;
  name: string;
  reqLevel: number;
  sp: number;
  mp: number;
  cooldown: number;
  icon: string;
}

let fullByCode: Map<string, SkillFull> | null = null;
let fullByFamily: Map<string, SkillFull> | null = null;

export function familyOf(code: string): string {
  const p = code.split("_");
  return p.length >= 4 ? p.slice(2, 4).join("_") : code;
}

export function isHealSkill(code: string): boolean {
  return /HEAL|SELFHEAL|CURE|RECOVERY|VITAL|REGEN/i.test(code);
}

export function skillIconUrl(code: string): string | null {
  const full = getSkillFull(code);
  if (!full || !full.icon) return null;
  return `assets/img/silkroad/icons/${full.icon.replace(/\\/g, "/").replace(/\//g, "_")}.webp`;
}

function seedFromBundled(): void {
  const map = new Map<string, SkillFull>();
  const fam = new Map<string, SkillFull>();
  for (const s of getAllClassSkills()) {
    const full: SkillFull = {
      id: s.id ?? 0,
      code: s.code,
      name: s.name,
      reqLevel: s.levelReq,
      sp: 0,
      mp: 0,
      cooldown: 0,
      icon: "",
    };
    map.set(s.code, full);
    const f = familyOf(s.code);
    if (!fam.has(f)) fam.set(f, full);
  }
  fullByCode = map;
  fullByFamily = fam;
}

seedFromBundled();

export async function loadSkillsFull(): Promise<void> {
  if (!fullByCode) seedFromBundled();
  try {
    const res = await fetch("assets/gamedata/skills_full.json");
    if (!res.ok) return;
    const data = (await res.json()) as Record<string, SkillFull>;
    const map = fullByCode ?? new Map<string, SkillFull>();
    const fam = fullByFamily ?? new Map<string, SkillFull>();
    for (const s of Object.values(data)) {
      map.set(s.code, s);
      const f = familyOf(s.code);
      if (!fam.has(f)) fam.set(f, s);
    }
    fullByCode = map;
    fullByFamily = fam;
  } catch {
    if (!fullByCode) seedFromBundled();
  }
}

export function getSkillFull(code: string): SkillFull | null {
  if (!fullByCode) seedFromBundled();
  return fullByCode!.get(code) ?? fullByFamily?.get(familyOf(code)) ?? null;
}

export function skillMpCost(full: SkillFull, level: number): number {
  if (full.mp <= 1) return Math.max(4, Math.round(level * 0.5));
  return Math.max(4, Math.round(full.mp / 50));
}

export function skillDamage(full: SkillFull, baseAttack: number, level: number): number {
  const tier = full.reqLevel >= 50 ? 3.6 : full.reqLevel >= 30 ? 2.8 : full.reqLevel >= 10 ? 2.0 : 1.4;
  return Math.round(baseAttack * tier * (1 + level * 0.01));
}

export function skillHeal(maxHp: number, level: number): number {
  return Math.round(maxHp * 0.22 + level * 3);
}
