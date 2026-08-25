import { characterBase } from "./character_loader";

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

const SX = 76;
const SY = 103;
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

function inWindow(region: number): boolean {
  const x = region & 0xff;
  const y = region >> 8;
  return x >= SX && x < SX + 6 && y >= SY && y < SY + 6;
}

let cache: WorldNpc[] | null = null;

export async function loadWorldNpcs(): Promise<WorldNpc[]> {
  if (cache) return cache;
  const [spawns, chars] = await Promise.all([
    fetch("/assets/gamedata/spawns.json").then((r) => r.json() as Promise<SpawnRec[]>),
    fetch("/assets/gamedata/chars.json").then((r) => r.json() as Promise<Record<string, { name?: string }>>),
  ]);
  const out: WorldNpc[] = [];
  const seen = new Set<string>();
  for (const s of spawns) {
    if (s.kind !== "npc" || !inWindow(s.region)) continue;
    if (seen.has(s.code)) continue;
    seen.add(s.code);
    const wx = s.x + ((s.region & 0xff) - SX) * SECTOR_W;
    const wz = s.z + ((s.region >> 8) - SY) * SECTOR_W;
    if (wx < 0 || wx > 11520 || wz < 0 || wz > 11520) continue;
    out.push({
      id: s.code,
      code: s.code,
      name: chars[String(s.cid)]?.name || s.code,
      x: wx,
      z: wz,
      region: s.region,
      actor: ACTOR_BY_CODE[s.code] || null,
      rotY: Math.PI,
    });
  }
  cache = out;
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

export function itemIconUrl(iconRel: string): string {
  const flat = iconRel.replace(/\\/g, "/").toLowerCase();
  return `/assets/img/silkroad/icons/${flat.split("/").join("_")}.webp`;
}

export async function loadItemInfo(codes: string[]): Promise<Record<string, { name: string; price: number; icon: string; iconUrl: string | null; stack: number; level: number }>> {
  const missing = codes.filter((c) => !itemInfoCache[c]);
  if (missing.length) {
    const all = await fetch("/assets/gamedata/items.json").then((r) => r.json());
    for (const c of Object.keys(all)) {
      const it = all[c];
      itemInfoCache[c] = {
        name: it.name,
        price: it.price,
        icon: it.icon,
        iconUrl: it.icon ? itemIconUrl(it.icon) : null,
        stack: it.stack,
        level: it.level,
      };
    }
  }
  const out: Record<string, { name: string; price: number; icon: string; iconUrl: string | null; stack: number; level: number }> = {};
  for (const c of codes) {
    if (itemInfoCache[c]) out[c] = itemInfoCache[c];
  }
  return out;
}

export { characterBase };
