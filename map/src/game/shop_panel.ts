import type { GameCharacter } from "./types";
import { loadShops, loadItemInfo } from "./world_npcs";
import { registerAuthenticItem, authenticItemDef } from "./items";

export interface ShopHandle {
  close(): void;
}

export interface ShopOptions {
  npcCode: string;
  npcName: string;
  character: GameCharacter;
  onMutate(): void;
  log(msg: string): void;
}

interface Info {
  name: string;
  price: number;
  iconUrl: string | null;
}

export async function openShop(root: HTMLElement, opts: ShopOptions): Promise<ShopHandle> {
  root.querySelectorAll(":scope > .shop-panel").forEach((el) => el.remove());
  const shops = await loadShops();
  const entry = shops[opts.npcCode];
  const panel = document.createElement("div");
  panel.className = "sro-window shop-panel";
  panel.innerHTML = `
    <div class="sro-window-title">${opts.npcName} - Shop</div>
    <div class="shop-tabs"></div>
    <div class="shop-gold">Gold: <b>${Math.floor(opts.character.gold).toLocaleString()}</b></div>
    <div class="shop-grid"></div>
    <div class="shop-inv-title">Your items (tap to sell)</div>
    <div class="shop-inv"></div>
    <div class="hud-dialog-actions"><button class="sro-btn sro-btn-primary" id="shop-close">Close</button></div>
  `;
  root.appendChild(panel);

  const tabsEl = panel.querySelector(".shop-tabs") as HTMLElement;
  const gridEl = panel.querySelector(".shop-grid") as HTMLElement;
  const invEl = panel.querySelector(".shop-inv") as HTMLElement;
  const goldEl = panel.querySelector(".shop-gold b") as HTMLElement;

  const infoCache = new Map<string, Info>();
  const ensureInfo = async (codes: string[]): Promise<Map<string, Info>> => {
    const need = codes.filter((c) => !infoCache.has(c));
    if (need.length) {
      const got = await loadItemInfo(need);
      for (const [c, v] of Object.entries(got)) {
        infoCache.set(c, { name: v.name || c, price: v.price || 100, iconUrl: v.iconUrl });
      }
      for (const c of need) {
        if (!infoCache.has(c)) infoCache.set(c, { name: c, price: 100, iconUrl: null });
      }
      for (const c of need) {
        const inf = infoCache.get(c)!;
        registerAuthenticItem(c, authenticItemDef(c, inf.name, inf.price, inf.iconUrl, 0));
      }
    }
    return new Map(codes.map((c) => [c, infoCache.get(c)!]));
  };

  const renderInv = async () => {
    invEl.innerHTML = "";
    const codes = opts.character.inventory.map((i) => i.id);
    const infos = await ensureInfo([...new Set(codes)]);
    for (const it of opts.character.inventory) {
      const inf = infos.get(it.id);
      const cell = document.createElement("button");
      cell.className = "shop-cell";
      cell.innerHTML = `${inf?.iconUrl ? `<img src="${inf.iconUrl}" alt="">` : "<span class='shop-noicon'></span>"}<em>${it.count > 1 ? it.count : ""}</em>`;
      cell.title = `${inf?.name || it.id} - sell ${Math.max(1, Math.floor((inf?.price || 0) / 10))}g`;
      cell.addEventListener("click", () => {
        const sellPrice = Math.max(1, Math.floor((infoCache.get(it.id)?.price || 0) / 10));
        opts.character.gold += sellPrice;
        it.count -= 1;
        if (it.count <= 0) {
          opts.character.inventory = opts.character.inventory.filter((x) => x !== it);
        }
        goldEl.textContent = Math.floor(opts.character.gold).toLocaleString();
        opts.log(`Sold ${inf?.name || it.id} for ${sellPrice} gold`);
        opts.onMutate();
        void renderInv();
      });
      invEl.appendChild(cell);
    }
  };

  const showTab = async (tabIdx: number) => {
    if (!entry) return;
    tabsEl.querySelectorAll("button").forEach((b, i) => b.classList.toggle("active", i === tabIdx));
    const codes = entry.tabs[tabIdx]?.items || [];
    const infos = await ensureInfo(codes);
    gridEl.innerHTML = "";
    for (const code of codes) {
      const inf = infos.get(code)!;
      const cell = document.createElement("button");
      cell.className = "shop-cell";
      cell.innerHTML = `${inf.iconUrl ? `<img src="${inf.iconUrl}" alt="">` : "<span class='shop-noicon'></span>"}<i>${inf.name}</i><u>${inf.price.toLocaleString()}g</u>`;
      cell.addEventListener("click", () => {
        if (opts.character.gold < inf.price) {
          opts.log(`Not enough gold for ${inf.name}`);
          return;
        }
        opts.character.gold -= inf.price;
        const stackMax = 200;
        const have = opts.character.inventory.find((x) => x.id === code && x.count < stackMax);
        if (have) have.count += 1;
        else opts.character.inventory.push({ id: code, count: 1 });
        goldEl.textContent = Math.floor(opts.character.gold).toLocaleString();
        opts.log(`Bought ${inf.name} for ${inf.price} gold`);
        opts.onMutate();
        void renderInv();
      });
      gridEl.appendChild(cell);
    }
  };

  if (!entry || !entry.tabs.length) {
    gridEl.innerHTML = "<div class='shop-empty'>This merchant has no goods.</div>";
  } else {
    entry.tabs.forEach((t, i) => {
      const b = document.createElement("button");
      b.className = "sro-btn sro-btn-secondary" + (i === 0 ? " active" : "");
      b.textContent = t.tab.replace(/^STORE_[A-Z]+_/, "").replace(/_TAB\d+$/, "") || `Tab ${i + 1}`;
      b.addEventListener("click", () => void showTab(i));
      tabsEl.appendChild(b);
    });
    await showTab(0);
  }
  await renderInv();

  const close = () => panel.remove();
  panel.querySelector("#shop-close")!.addEventListener("click", close);
  return { close };
}
