export interface MercenaryDef {
  code: string;
  name: string;
  cost: number;
}

export const MAX_PARTY_MEMBERS = 2;

export const MERCENARIES: MercenaryDef[] = [
  { code: "merc_swordguard", name: "Swordguard Ally", cost: 2000 },
  { code: "merc_longbow_scout", name: "Longbow Scout Ally", cost: 2500 },
];
