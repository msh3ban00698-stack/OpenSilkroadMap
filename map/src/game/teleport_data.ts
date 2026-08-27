import { REGIONS, regionForSector, type RegionDef } from "./regions";

export interface TeleportPad {
  id: number;
  code: string;
  name: string;
  x: number;
  z: number;
  regionId: number;
  regionName: string;
}

// Main town gate per region (name match against teleports_full.json gate names).
const TOWN_GATES: { regionId: number; name: string; match: string }[] = [
  { regionId: 1, name: "Constantinople", match: "Constantinople" },
  { regionId: 2, name: "Jangan", match: "Imperial Palace" },
  { regionId: 3, name: "Donwhang", match: "Donwhang" },
  { regionId: 4, name: "Hotan", match: "Hotan" },
  { regionId: 5, name: "Samarkand", match: "Samarkand" },
  { regionId: 6, name: "Baghdad", match: "Baghdad" },
  { regionId: 7, name: "Alexandria", match: "Alexandria (South)" },
  { regionId: 8, name: "Mt. Roc", match: "Roc Mountain" },
  { regionId: 9, name: "Jupiter Temple", match: "Mirror Dimension" },
];

let padsPromise: Promise<TeleportPad[]> | null = null;

function loadAllPads(): Promise<TeleportPad[]> {
  if (!padsPromise) {
    padsPromise = fetch("/assets/gamedata/teleports_full.json")
      .then((r) => r.json() as Promise<{ gates: GateRec[] }>)
      .then(({ gates }) => {
        const out: TeleportPad[] = [];
        for (const g of gates) {
          const def = regionForSector(g.region);
          if (!def) continue;
          const rx = g.region & 0xff;
          const ry = g.region >> 8;
          out.push({
            id: g.id,
            code: g.code,
            name: g.name,
            x: g.x + (rx - def.sx) * 1920,
            z: g.z + (ry - def.sy) * 1920,
            regionId: def.id,
            regionName: def.name,
          });
        }
        return out;
      });
  }
  return padsPromise;
}

// Pads physically placed in a region's world (gates you can walk to).
export async function loadTeleportPads(region: RegionDef): Promise<TeleportPad[]> {
  const all = await loadAllPads();
  const size = region.span * 1920;
  return all.filter(
    (p) =>
      p.regionId === region.id &&
      p.x >= 0 &&
      p.x <= size &&
      p.z >= 0 &&
      p.z <= size,
  );
}

// Inter-region destination list: one town gate per region.
export async function loadTownGates(): Promise<TeleportPad[]> {
  const all = await loadAllPads();
  const out: TeleportPad[] = [];
  for (const t of TOWN_GATES) {
    const pad = all.find((p) => p.regionId === t.regionId && p.name === t.match);
    if (pad) out.push(pad);
  }
  return out;
}

export function regionForPad(pad: TeleportPad): RegionDef {
  return REGIONS.find((r) => r.id === pad.regionId) ?? REGIONS[0];
}

interface GateRec {
  id: number;
  code: string;
  name: string;
  region: number;
  x: number;
  z: number;
}
