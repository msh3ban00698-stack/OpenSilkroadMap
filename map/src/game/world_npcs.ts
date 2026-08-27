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

let cache: Record<number, WorldNpc[]> = {};

export async function loadWorldNpcs(region: RegionDef): Promise<WorldNpc[]> {
  if (cache[region.id]) return cache[region.id];
  const [spawns, chars] = await Promise.all([
    fetch("/assets/gamedata/spawns.json").then((r) => r.json() as Promise<SpawnRec[]>),
    fetch("/assets/gamedata/chars.json").then((r) => r.json() as Promise<Record<string, { name?: string }>>),
  ]);
  const out: WorldNpc[] = [];
  const seen = new Set<string>();
  for (const s of spawns) {
    if (s.kind !== "npc") continue;
    const rx = s.region & 0xff;
    const ry = s.region >> 8;
    if (rx < region.sx || rx >= region.sx + region.span || ry < region.sy || ry >= region.sy + region.span) continue;
    if (seen.has(s.code)) continue;
    seen.add(s.code);
    const wx = s.x + (rx - region.sx) * SECTOR_W;
    const wz = s.z + (ry - region.sy) * SECTOR_W;
    const size = region.span * SECTOR_W;
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
  cache[region.id] = out;
  return out;
}

let shopCache: Record<string, NpcShop> | null = null;

export async function loadShops(): Promise<Record<string, NpcShop>> {
  if (shopCache) return shopCache;
  const raw = await fetch("/assets/gamedata/shops.json").then(
    (r) => r.json() as Promise<Record<string, { shop: string; tabs: ShopTab[] }>>,
  );
  shopCache = raw as Record<string, NpcShop>;
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
    const all = await fetch("/assets/gamedata/items.json").then((r) => r.json());
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
