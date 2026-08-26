import type { GameCharacter } from "./types.js";
import { MERCENARIES, MAX_PARTY_MEMBERS } from "./party_data.js";

export interface PartyPanelOpts {
  root: HTMLElement;
  character: GameCharacter;
  onMutate: () => void;
  log: (msg: string) => void;
  onHire: (def: { code: string; name: string; cost: number }) => boolean;
  onDismiss: (code: string) => boolean;
}

export function openPartyPanel(root: HTMLElement, opts: PartyPanelOpts): void {
  root.querySelectorAll(":scope > .shop-panel").forEach((el) => el.remove());
  const sheet = document.createElement("div");
  sheet.className = "shop-panel";
  const backdrop = document.createElement("div");
  backdrop.className = "shop-backdrop";
  const panel = document.createElement("div");
  panel.className = "sro-window shop-sheet";
  panel.innerHTML = `
    <div class="sro-window-title">Party</div>
    <div class="party-list"></div>
    <button class="sro-btn sro-btn-secondary party-close-btn" type="button">Close</button>
  `;
  sheet.appendChild(backdrop);
  sheet.appendChild(panel);
  root.appendChild(sheet);

  const close = (): void => sheet.remove();
  backdrop.addEventListener("click", close);
  panel.querySelector(".party-close-btn")!.addEventListener("click", close);

  const list = panel.querySelector<HTMLElement>(".party-list")!;
  const members = opts.character.party || [];

  for (const m of members) {
    const row = document.createElement("div");
    row.className = "party-row";
    const label = document.createElement("span");
    label.className = "party-name";
    label.textContent = m.name;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "sro-btn sro-btn-secondary";
    btn.textContent = "Dismiss";
    btn.addEventListener("click", () => {
      if (opts.onDismiss(m.code)) close();
    });
    row.appendChild(label);
    row.appendChild(btn);
    list.appendChild(row);
  }
  if (members.length === 0) {
    const empty = document.createElement("div");
    empty.className = "quest-empty";
    empty.textContent = `Your party is empty. Hire up to ${MAX_PARTY_MEMBERS} allies.`;
    list.appendChild(empty);
  }

  if (members.length < MAX_PARTY_MEMBERS) {
    const hireTitle = document.createElement("div");
    hireTitle.className = "party-section";
    hireTitle.textContent = "Available allies";
    list.appendChild(hireTitle);
    for (const def of MERCENARIES) {
      const row = document.createElement("div");
      row.className = "party-row";
      const label = document.createElement("span");
      label.className = "party-name";
      label.textContent = def.name;
      const cost = document.createElement("small");
      cost.textContent = `${def.cost}g`;
      label.appendChild(cost);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sro-btn sro-btn-primary";
      btn.textContent = "Hire";
      btn.disabled = opts.character.gold < def.cost;
      btn.addEventListener("click", () => {
        if (opts.onHire(def)) close();
      });
      row.appendChild(label);
      row.appendChild(btn);
      list.appendChild(row);
    }
  }
}
