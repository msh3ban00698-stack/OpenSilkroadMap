import type { EquipSlot, GameCharacter } from "./types";
import { getItem } from "./items";

export interface InventoryPanelOptions {
  parent: HTMLElement;
  character: GameCharacter;
  onEquip: (itemId: string) => void;
  onUnequip: (slot: EquipSlot) => void;
  onUse: (itemId: string) => void;
  onClose: () => void;
}

export interface InventoryPanel {
  show(): void;
  hide(): void;
  isOpen(): boolean;
  refresh(): void;
  dispose(): void;
}

const EQUIP_ORDER: EquipSlot[] = ["weapon", "armor", "accessory"];
const BAG_SLOTS = 12;

export function buildInventoryPanel(opts: InventoryPanelOptions): InventoryPanel {
  const overlay = document.createElement("div");
  overlay.className = "inv-overlay";
  overlay.style.display = "none";

  let selectedItemId: string | null = null;
  let selectedSlot: "bag" | EquipSlot | null = null;
  let open = false;

  const render = (): void => {
    const char = opts.character;
    const equipHtml = EQUIP_ORDER.map((slot) => {
      const itemId = char.equipment[slot];
      const item = itemId ? getItem(itemId) : undefined;
      const label = slot.charAt(0).toUpperCase() + slot.slice(1);
      const sel = selectedSlot === slot ? " sel" : "";
      return `
        <div class="inv-equip-slot${sel}" data-slot="${slot}">
          <div class="inv-slot-icon">${item ? `<img src="${item.icon}" alt="" />` : `<span class="inv-empty">-</span>`}</div>
          <div class="inv-slot-label">${item ? item.name : `Empty ${label}`}</div>
        </div>
      `;
    }).join("");

    const bagHtml: string[] = [];
    for (let i = 0; i < BAG_SLOTS; i++) {
      const stack = char.inventory[i];
      const item = stack ? getItem(stack.id) : undefined;
      const sel = selectedSlot === "bag" && selectedItemId === (stack ? stack.id : "") ? " sel" : "";
      if (stack && item) {
        bagHtml.push(`
          <div class="inv-bag-slot${sel}" data-item="${stack.id}">
            <img src="${item.icon}" alt="" />
            <span class="inv-count">${stack.count}</span>
          </div>
        `);
      } else {
        bagHtml.push(`<div class="inv-bag-slot inv-empty">-</div>`);
      }
    }

    let detail = "";
    if (selectedItemId) {
      const item = getItem(selectedItemId);
      const stack = char.inventory.find((s) => s.id === selectedItemId);
      if (item) {
        const inBag = !!stack;
        const equippedIn = (Object.entries(char.equipment) as [EquipSlot, string | null][]).find(
          ([, id]) => id === item.id,
        )?.[0];
        const stats: string[] = [];
        if (item.attack) stats.push(`Attack +${item.attack}`);
        if (item.defense) stats.push(`Defense +${item.defense}`);
        if (item.hpBonus) stats.push(`Max HP +${item.hpBonus}`);
        if (item.heal) stats.push(`Heals ${item.heal} HP`);
        const actions = equippedIn
          ? `<button class="hud-btn hud-mini" id="inv-action-unequip">Unequip</button>`
          : inBag && item.slot === "consumable"
          ? `<button class="hud-btn hud-mini hud-primary" id="inv-action-use">Use</button>`
          : inBag
          ? `<button class="hud-btn hud-mini hud-primary" id="inv-action-equip">Equip</button>`
          : "";
        detail = `
          <div class="inv-detail">
            <img src="${item.icon}" alt="" />
            <div class="inv-detail-info">
              <div class="inv-detail-name">${item.name}</div>
              <div class="inv-detail-stats">${stats.join(" · ") || item.slot}</div>
              <div class="inv-detail-desc">${item.desc}</div>
              <div class="inv-detail-actions">${actions}</div>
            </div>
          </div>
        `;
      }
    }

    overlay.innerHTML = `
      <div class="inv-panel">
        <div class="inv-header">
          <div class="inv-title">Inventory</div>
          <button class="hud-btn hud-mini" id="inv-close">Close</button>
        </div>
        <div class="inv-body">
          <div class="inv-equip">${equipHtml}</div>
          <div class="inv-bag">${bagHtml.join("")}</div>
        </div>
        <div class="inv-footer">${detail || `<div class="inv-detail-empty">Select an item to see details.</div>`}</div>
      </div>
    `;

    overlay.querySelectorAll(".inv-equip-slot").forEach((el) => {
      el.addEventListener("click", () => {
        const slot = (el as HTMLElement).dataset.slot as EquipSlot;
        selectedSlot = slot;
        selectedItemId = char.equipment[slot] ?? null;
        render();
      });
    });
    overlay.querySelectorAll(".inv-bag-slot[data-item]").forEach((el) => {
      el.addEventListener("click", () => {
        selectedSlot = "bag";
        selectedItemId = (el as HTMLElement).dataset.item ?? null;
        render();
      });
    });
    overlay.querySelector("#inv-close")?.addEventListener("click", () => opts.onClose());
    overlay.querySelector("#inv-action-equip")?.addEventListener("click", () => {
      if (selectedItemId) {
        opts.onEquip(selectedItemId);
        selectedSlot = "bag";
        render();
      }
    });
    overlay.querySelector("#inv-action-unequip")?.addEventListener("click", () => {
      if (selectedSlot && selectedSlot !== "bag") {
        opts.onUnequip(selectedSlot);
        selectedSlot = "bag";
        selectedItemId = null;
        render();
      }
    });
    overlay.querySelector("#inv-action-use")?.addEventListener("click", () => {
      if (selectedItemId) opts.onUse(selectedItemId);
    });
  };

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) opts.onClose();
  });

  opts.parent.appendChild(overlay);

  return {
    show: () => {
      open = true;
      overlay.style.display = "flex";
      render();
    },
    hide: () => {
      open = false;
      overlay.style.display = "none";
    },
    isOpen: () => open,
    refresh: render,
    dispose: () => {
      if (overlay.parentElement) overlay.parentElement.removeChild(overlay);
    },
  };
}
