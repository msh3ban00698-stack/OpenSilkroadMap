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

const TOWN_GATE_CODES: { regionId: number; name: string; code: string }[] = [
  { regionId: 1, name: "Constantinople", code: "STORE_EU_GATE" },
  { regionId: 2, name: "Jangan", code: "STORE_CH_GATE" },
  { regionId: 3, name: "Donwhang", code: "STORE_WC_GATE" },
  { regionId: 4, name: "Hotan", code: "STORE_KT_GATE" },
  { regionId: 5, name: "Samarkand", code: "STORE_CA_GATE" },
  { regionId: 6, name: "Baghdad", code: "STORE_AR_GATE" },
  { regionId: 7, name: "Alexandria", code: "STORE_SD_GATE1" },
  { regionId: 8, name: "Mt. Roc", code: "STORE_RC_TAHOMET_GATE" },
  { regionId: 9, name: "Jupiter Temple", code: "STORE_JUPITER_FIELD_TO_EU_GATE" },
];

let padsPromise: Promise<TeleportPad[]> | null = null;

interface GateRec {
  id: number;
  code: string;
  name: string;
  region: number;
  x: number;
  z: number;
}

interface MarkerTeleport {
  name: string;
  codename: string;
  region: number;
  x: number;
  y: number;
  z: number;
  type: number;
}

const SECTOR_W = 1920;

function unsignedRegion(region: number): number {
  return region < 0 ? region + 65536 : region;
}

function worldFromLocal(region: number, localX: number, localZ: number, def: RegionDef): { x: number; z: number } {
  const id = unsignedRegion(region);
  const rx = id & 0xff;
  const ry = id >> 8;
  return {
    x: localX + (rx - def.sx) * SECTOR_W,
    z: localZ + (ry - def.sy) * SECTOR_W,
  };
}

function padFromGate(g: GateRec, def: RegionDef): TeleportPad {
  const { x, z } = worldFromLocal(g.region, g.x, g.z, def);
  return {
    id: g.id,
    code: g.code,
    name: g.name,
    x,
    z,
    regionId: def.id,
    regionName: def.name,
  };
}

function padFromMarker(t: MarkerTeleport, idx: number, def: RegionDef): TeleportPad {
  const { x, z } = worldFromLocal(t.region, t.x, t.y, def);
  return {
    id: idx + 1,
    code: t.codename,
    name: t.name,
    x,
    z,
    regionId: def.id,
    regionName: def.name,
  };
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function loadAllPads(): Promise<TeleportPad[]> {
  if (!padsPromise) {
    padsPromise = (async () => {
      const full = await fetchJson<{ gates: GateRec[] }>("/assets/gamedata/teleports_full.json");
      if (full?.gates?.length) {
        const out: TeleportPad[] = [];
        for (const g of full.gates) {
          const def = regionForSector(g.region);
          if (!def) continue;
          out.push(padFromGate(g, def));
        }
        if (out.length) return out;
      }
      const markers = await fetchJson<MarkerTeleport[]>("/assets/teleports.json");
      if (!markers) return [];
      const out: TeleportPad[] = [];
      markers.forEach((t, idx) => {
        const region = unsignedRegion(t.region);
        if (region >= 32768) return;
        const def = regionForSector(t.region);
        if (!def) return;
        out.push(padFromMarker(t, idx, def));
      });
      return out;
    })();
  }
  return padsPromise;
}

export async function loadTeleportPads(region: RegionDef): Promise<TeleportPad[]> {
  const all = await loadAllPads();
  const size = region.span * SECTOR_W;
  return all.filter((p) => p.regionId === region.id && p.x >= 0 && p.x <= size && p.z >= 0 && p.z <= size);
}

export async function loadTownGates(): Promise<TeleportPad[]> {
  const all = await loadAllPads();
  const out: TeleportPad[] = [];
  for (const t of TOWN_GATE_CODES) {
    const pad = all.find((p) => p.regionId === t.regionId && p.code === t.code);
    if (pad) out.push({ ...pad, name: t.name });
  }
  return out;
}

export function regionForPad(pad: TeleportPad): RegionDef {
  return REGIONS.find((r) => r.id === pad.regionId) ?? REGIONS[0];
}
