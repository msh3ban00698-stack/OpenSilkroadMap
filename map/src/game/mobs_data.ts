import type { RegionDef } from "./regions";

export interface MobDef {
  code: string;
  name: string;
  actor: string;
  level: number;
  hp: number;
  attack: number;
  expReward: number;
  goldReward: [number, number];
  count: number;
}

export interface MobCamp {
  cx: number;
  cz: number;
  radius: number;
  mob: MobDef;
}

export const MOB_CAMPS: MobCamp[] = [
  {
    cx: 6710,
    cz: 4610,
    radius: 90,
    mob: {
      code: "MOB_EU_BARUSWOLF",
      name: "Wolf",
      actor: "actor/wolf",
      level: 6,
      hp: 114,
      attack: 12,
      expReward: 60,
      goldReward: [40, 90],
      count: 4,
    },
  },
  {
    cx: 7060,
    cz: 5080,
    radius: 110,
    mob: {
      code: "MOB_EU_BAROI",
      name: "Baroi",
      actor: "actor/baroi",
      level: 9,
      hp: 192,
      attack: 18,
      expReward: 95,
      goldReward: [70, 140],
      count: 3,
    },
  },
  {
    cx: 6280,
    cz: 4300,
    radius: 120,
    mob: {
      code: "MOB_EU_DOWB",
      name: "Dowb",
      actor: "actor/dowb",
      level: 12,
      hp: 359,
      attack: 26,
      expReward: 150,
      goldReward: [110, 210],
      count: 3,
    },
  },
];

// Rough per-region danger tier (town difficulty in the original game).
const REGION_TIER: Record<number, number> = {
  2: 8,
  3: 6,
  4: 10,
  5: 12,
  6: 16,
  7: 18,
  8: 20,
  9: 24,
};

const GENERIC_MOBS: { code: string; name: string; actor: string }[] = [
  { code: "MOB_EU_BARUSWOLF", name: "Wolf", actor: "actor/wolf" },
  { code: "MOB_EU_BAROI", name: "Baroi", actor: "actor/baroi" },
  { code: "MOB_EU_DOWB", name: "Dowb", actor: "actor/dowb" },
  { code: "MOB_EU_KYKLOPES", name: "Kyklopes", actor: "actor/kyklopes" },
  { code: "MOB_EU_LION", name: "Lion", actor: "actor/lion" },
  { code: "MOB_EU_BARPOLLE", name: "Barpolle", actor: "actor/barpolle" },
];

// Field mobs for a region: camps ring the spawn at increasing distance, scaled
// by the region's danger tier. Region 1 keeps its verified Constantinople set.
export function mobCampsFor(region: RegionDef, spawn: { x: number; z: number }): MobCamp[] {
  if (region.id === 1) return MOB_CAMPS;
  const tier = REGION_TIER[region.id] ?? 10;
  const camps: MobCamp[] = [];
  GENERIC_MOBS.slice(0, 4).forEach((m, i) => {
    const ang = (i / 4) * Math.PI * 2 + 0.5;
    const dist = 1500 + i * 500;
    const cx = Math.max(700, Math.min(11520 - 700, spawn.x + Math.cos(ang) * dist));
    const cz = Math.max(700, Math.min(11520 - 700, spawn.z + Math.sin(ang) * dist));
    const level = Math.max(1, tier + i * 2 - 2);
    const hp = 110 + (level - 6) * 18;
    const attack = Math.round(11 + (level - 6) * 2.5);
    const exp = 55 + (level - 6) * 22;
    const gold: [number, number] = [30 + (level - 6) * 15, 70 + (level - 6) * 30];
    camps.push({
      cx: Math.round(cx),
      cz: Math.round(cz),
      radius: 90 + i * 15,
      mob: {
        code: m.code,
        name: m.name,
        actor: m.actor,
        level,
        hp,
        attack,
        expReward: exp,
        goldReward: gold,
        count: 3 + (i % 2),
      },
    });
  });
  return camps;
}
