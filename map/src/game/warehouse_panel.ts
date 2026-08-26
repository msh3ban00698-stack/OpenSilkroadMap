import type { GameCharacter, InventoryItem } from "./types.js";
import { getItem } from "./items.js";

export interface WarehousePanelOpts {
  root: HTMLElement;
  character: GameCharacter;
  onMutate: () => void;
  log: (msg: string) => void;
}

function itemLabel(id: string): string {
  return getItem(id)?.name ?? id;
}

function itemIcon(id: string): string {
  return getItem(id)?.icon ?? "";
}

export function openWarehousePanel(root: HTMLElement, opts: WarehousePanelOpts): void {
  root.querySelectorAll(":scope > .shop-panel").forEach((el) => el.remove());
  const char = opts.character;
  if (!char.warehouse) char.warehouse = [];
  const store = char.warehouse;
  const sheet = document.createElement("div");
  sheet.className = "shop-panel";
  const backdrop = document.createElement("div");
  backdrop.className = "shop-backdrop";
  const panel = document.createElement("div");
  panel.className = "sro-window shop-sheet";
  panel.innerHTML = `
    <div class="sro-window-title">Warehouse Exchange</div>
    <div class="wh-section">Bag — tap to deposit</div>
    <div class="wh-grid wh-bag"></div>
    <div class="wh-section">Warehouse — tap to withdraw</div>
    <div class="wh-grid wh-store"></div>
    <button class="sro-btn sro-btn-secondary wh-close-btn" type="button">Close</button>
  `;
  sheet.appendChild(backdrop);
  sheet.appendChild(panel);
  root.appendChild(sheet);

  const close = (): void => sheet.remove();
  backdrop.addEventListener("click", close);
  panel.querySelector(".wh-close-btn")!.addEventListener("click", close);

  const bagGrid = panel.querySelector<HTMLElement>(".wh-bag")!;
  const storeGrid = panel.querySelector<HTMLElement>(".wh-store")!;

  const render = (): void => {
    bagGrid.innerHTML = "";
    storeGrid.innerHTML = "";
    for (const stack of char.inventory) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "wh-cell";
      const icon = itemIcon(stack.id);
      cell.innerHTML = `${icon ? `<img src="${icon}" alt="" />` : "<span>-</span>"}<i></i><em>x${stack.count}</em>`;
      cell.querySelector("i")!.textContent = itemLabel(stack.id);
      cell.addEventListener("click", () => {
        deposit(stack);
      });
      bagGrid.appendChild(cell);
    }
    if (char.inventory.length === 0) {
      const empty = document.createElement("div");
      empty.className = "quest-empty";
      empty.textContent = "Bag is empty.";
      bagGrid.appendChild(empty);
    }
    for (const stack of store) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "wh-cell";
      const icon = itemIcon(stack.id);
      cell.innerHTML = `${icon ? `<img src="${icon}" alt="" />` : "<span>-</span>"}<i></i><em>x${stack.count}</em>`;
      cell.querySelector("i")!.textContent = itemLabel(stack.id);
      cell.addEventListener("click", () => {
        withdraw(stack);
      });
      storeGrid.appendChild(cell);
    }
    if (store.length === 0) {
      const empty = document.createElement("div");
      empty.className = "quest-empty";
      empty.textContent = "Warehouse is empty.";
      storeGrid.appendChild(empty);
    }
  };

  const deposit = (stack: InventoryItem): void => {
    char.inventory = char.inventory.filter((it) => it.id !== stack.id);
    const existing = store.find((it) => it.id === stack.id);
    if (existing) existing.count += stack.count;
    else store.push({ ...stack });
    opts.log(`Deposited ${itemLabel(stack.id)} x${stack.count}.`);
    opts.onMutate();
    render();
  };

  const withdraw = (stack: InventoryItem): void => {
    char.warehouse = store.filter((it) => it.id !== stack.id);
    const existing = char.inventory.find((it) => it.id === stack.id);
    if (existing) existing.count += stack.count;
    else char.inventory.push({ ...stack });
    opts.log(`Withdrew ${itemLabel(stack.id)} x${stack.count}.`);
    opts.onMutate();
    render();
  };

  render();
}
