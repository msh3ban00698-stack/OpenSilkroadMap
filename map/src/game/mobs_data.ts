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

export const MOB_CAMPS: { cx: number; cz: number; radius: number; mob: MobDef }[] = [
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
