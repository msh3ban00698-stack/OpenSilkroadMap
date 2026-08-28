import { characterBase } from "./character_loader";
import type { RegionDef } from "./regions";

export interface WorldNpc {
  id: string;
  code: string;
  name: string;
  x: number;
  z: number;
  region: number;
  actor: string | null;
  rotY: number;
}

export interface ShopTab {
  tab: string;
  items: string[];
}

export interface NpcShop {
  npc: string;
  shop: string;
  tabs: ShopTab[];
}

interface SpawnRec {
  cid: number;
  code: string;
  kind: string;
  region: number;
  x: number;
  z: number;
}

interface MarkerNpc {
  name: string;
  region: number;
  x: number;
  y: number;
  z: number;
  teleport?: unknown[];
}

const SECTOR_W = 1920;

const ACTOR_BY_CODE: Record<string, string> = {
  NPC_EU_SMITH: "actor/smith_eu",
  NPC_EU_ACCESSORY: "actor/grocery_eu",
  NPC_EU_POTION: "actor/potion_eu",
  NPC_EU_SPECIAL: "actor/special_eu",
  NPC_EU_WAREHOUSE: "actor/warehouse_keeper",
  NPC_EU_MERCHANT: "actor/merchant_union",
  NPC_EU_GUILD: "actor/guild_master",
  NPC_EU_FERRY: "actor/port_manager",
  NPC_EU_SOLDIER_CA1: "actor/soldier_a",
  NPC_EU_SOLDIER_CA2: "actor/soldier_b",
  NPC_EU_SOLDIER_PO1: "actor/soldier_a",
  NPC_EU_SOLDIER_PO2: "actor/soldier_b",
  NPC_EU_PRIEST: "actor/priest",
  NPC_EU_ADVENTURER: "actor/adventurer",
  NPC_EU_ADVICE3: "actor/guide",
};

// Role fallback for non-EU (Chinese/Arab/Jupiter) region NPCs, matched against
// the NPC code before the exact ACTOR_BY_CODE lookup.
const ACTOR_RULES: { match: RegExp; actor: string }[] = [
  { match: /SMITH/, actor: "actor/smith_eu" },
  { match: /ACCESSORY/, actor: "actor/grocery_eu" },
  { match: /POTION|DOCTOR|CHEF/, actor: "actor/potion_eu" },
  { match: /WAREHOUSE/, actor: "actor/warehouse_keeper" },
  { match: /MERCHANT|COMMERCE/, actor: "actor/merchant_union" },
  { match: /GUILD|BIGMAN|FORTRESS_OFFICIAL/, actor: "actor/guild_master" },
  { match: /FERRY|HORSE/, actor: "actor/port_manager" },
  { match: /PRIEST/, actor: "actor/priest" },
  { match: /ADVENTURER|HUNTER|BEGGAR|SLAVE|EUROPE/, actor: "actor/adventurer" },
  { match: /SOLDIER|GENERAL|ARENA|EYPTSOLIDER/, actor: "actor/soldier_a" },
  { match: /ARMOR/, actor: "actor/soldier_a" },
  { match: /GACHA|KISAENG|DESIGNER|EXCHANGER/, actor: "actor/special_eu" },
];

function actorFor(code: string): string | null {
  if (ACTOR_BY_CODE[code]) return ACTOR_BY_CODE[code];
  for (const r of ACTOR_RULES) {
    if (r.match.test(code)) return r.actor;
  }
  return "actor/adventurer";
}

function actorForName(name: string): string {
  const n = name.toUpperCase();
  if (/SMITH|BLACKSMITH/.test(n)) return "actor/smith_eu";
  if (/ACCESSORY|GROCER|JEWEL/.test(n)) return "actor/grocery_eu";
  if (/POTION|DOCTOR|CHEF|HERB/.test(n)) return "actor/potion_eu";
  if (/WAREHOUSE|STORAGE/.test(n)) return "actor/warehouse_keeper";
  if (/MERCHANT|TRADER|COMMERCE/.test(n)) return "actor/merchant_union";
  if (/GUILD/.test(n)) return "actor/guild_master";
  if (/FERRY|HORSE|STABLE/.test(n)) return "actor/port_manager";
  if (/PRIEST|MONK|BUDDHIST/.test(n)) return "actor/priest";
  if (/GUIDE/.test(n)) return "actor/guide";
  if (/SOLDIER|SOLDER|GUARD|GENERAL/.test(n)) return "actor/soldier_a";
  return "actor/adventurer";
}

function sectorInRegion(region: number, def: RegionDef): boolean {
  const id = region < 0 ? region + 65536 : region;
  const rx = id & 0xff;
  const ry = id >> 8;
  return rx >= def.sx && rx < def.sx + def.span && ry >= def.sy && ry < def.sy + def.span;
}

function localToWorld(region: number, localX: number, localZ: number, def: RegionDef): { x: number; z: number } {
  const id = region < 0 ? region + 65536 : region;
  const rx = id & 0xff;
  const ry = id >> 8;
  return {
    x: localX + (rx - def.sx) * SECTOR_W,
    z: localZ + (ry - def.sy) * SECTOR_W,
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

let cache: Record<number, WorldNpc[]> = {};

export async function loadWorldNpcs(region: RegionDef): Promise<WorldNpc[]> {
  if (cache[region.id]) return cache[region.id];
  const out: WorldNpc[] = [];
  const seen = new Set<string>();
  const size = region.span * SECTOR_W;

  const [spawns, chars] = await Promise.all([
    fetchJson<SpawnRec[]>("/assets/gamedata/spawns.json"),
    fetchJson<Record<string, { name?: string }>>("/assets/gamedata/chars.json"),
  ]);
  if (spawns && chars) {
    for (const s of spawns) {
      if (s.kind !== "npc") continue;
      if (!sectorInRegion(s.region, region)) continue;
      if (seen.has(s.code)) continue;
      seen.add(s.code);
      const { x: wx, z: wz } = localToWorld(s.region, s.x, s.z, region);
      if (wx < 0 || wx > size || wz < 0 || wz > size) continue;
      out.push({
        id: s.code,
        code: s.code,
        name: chars[String(s.cid)]?.name || s.code,
        x: wx,
        z: wz,
        region: s.region,
        actor: actorFor(s.code),
        rotY: Math.PI,
      });
    }
  }

  if (out.length === 0) {
    const markers = await fetchJson<MarkerNpc[]>("/assets/npcs.json");
    if (markers) {
      let i = 0;
      for (const n of markers) {
        const regionId = n.region < 0 ? n.region + 65536 : n.region;
        if (regionId >= 32768) continue;
        if (!sectorInRegion(n.region, region)) continue;
        const { x: wx, z: wz } = localToWorld(n.region, n.x, n.y, region);
        if (wx < 0 || wx > size || wz < 0 || wz > size) continue;
        const id = `npc_marker_${region.id}_${i++}`;
        out.push({
          id,
          code: id,
          name: n.name,
          x: wx,
          z: wz,
          region: n.region,
          actor: actorForName(n.name),
          rotY: Math.PI,
        });
      }
    }
  }

  cache[region.id] = out;
  return out;
}

let shopCache: Record<string, NpcShop> | null = null;

export async function loadShops(): Promise<Record<string, NpcShop>> {
  if (shopCache) return shopCache;
  try {
    const raw = await fetch("/assets/gamedata/shops.json").then(
      (r) => r.json() as Promise<Record<string, { shop: string; tabs: ShopTab[] }>>,
    );
    shopCache = raw as Record<string, NpcShop>;
  } catch {
    shopCache = {};
  }
  return shopCache;
}

const itemInfoCache: Record<
  string,
  { name: string; price: number; icon: string; iconUrl: string | null; stack: number; level: number }
> = {};

const PRICE_SCALE = 1 / 180;

export function itemIconUrl(iconRel: string): string {
  const flat = iconRel.replace(/\\/g, "/").toLowerCase();
  return `/assets/img/silkroad/icons/${flat.split("/").join("_")}.webp`;
}

export async function loadItemInfo(
  codes: string[],
): Promise<
  Record<string, { name: string; price: number; icon: string; iconUrl: string | null; stack: number; level: number }>
> {
  const missing = codes.filter((c) => !itemInfoCache[c]);
  if (missing.length) {
    let all: Record<string, any> = {};
    try {
      all = await fetch("/assets/gamedata/items.json").then((r) => r.json());
    } catch {
      all = {};
    }
    for (const c of Object.keys(all)) {
      const it = all[c];
      itemInfoCache[c] = {
        name: it.name,
        price: Math.max(1, Math.round((it.price || 0) * PRICE_SCALE)),
        icon: it.icon,
        iconUrl: it.icon ? itemIconUrl(it.icon) : null,
        stack: it.stack,
        level: it.level,
      };
    }
  }
  const out: Record<
    string,
    { name: string; price: number; icon: string; iconUrl: string | null; stack: number; level: number }
  > = {};
  for (const c of codes) {
    if (itemInfoCache[c]) out[c] = itemInfoCache[c];
  }
  return out;
}

export { characterBase };
