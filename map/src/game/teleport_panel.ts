import type { TeleportPad } from "./teleport_data.js";

export interface TeleportPanelOpts {
  root: HTMLElement;
  pads: TeleportPad[];
  currentPadId: string;
  playerPos: { x: number; z: number };
  onTravel: (pad: TeleportPad) => void;
}

export function openTeleportPanel(root: HTMLElement, opts: TeleportPanelOpts): void {
  root.querySelectorAll(":scope > .shop-panel").forEach((el) => el.remove());
  const sheet = document.createElement("div");
  sheet.className = "shop-panel";
  const backdrop = document.createElement("div");
  backdrop.className = "shop-backdrop";
  const panel = document.createElement("div");
  panel.className = "sro-window shop-sheet";
  const current = opts.pads.find((g) => String(g.id) === opts.currentPadId);
  panel.innerHTML = `
    <div class="sro-window-title">Teleport — ${current ? current.name : "Gate"}</div>
    <div class="tp-list"></div>
    <button class="sro-btn sro-btn-secondary tp-close-btn" type="button">Close</button>
  `;
  sheet.appendChild(backdrop);
  sheet.appendChild(panel);
  root.appendChild(sheet);

  const close = (): void => sheet.remove();
  backdrop.addEventListener("click", close);
  panel.querySelector(".tp-close-btn")!.addEventListener("click", close);

  const list = panel.querySelector<HTMLElement>(".tp-list")!;
  const destinations = opts.pads.filter((p) => String(p.id) !== opts.currentPadId);
  for (const pad of destinations) {
    const dist = Math.round(Math.hypot(pad.x - opts.playerPos.x, pad.z - opts.playerPos.z));
    const row = document.createElement("button");
    row.type = "button";
    row.className = "sro-btn sro-btn-secondary tp-row";
    const label = document.createElement("span");
    label.textContent = pad.name;
    const meta = document.createElement("small");
    meta.textContent = `${dist}m`;
    row.appendChild(label);
    row.appendChild(meta);
    row.addEventListener("click", () => {
      close();
      opts.onTravel(pad);
    });
    list.appendChild(row);
  }
  if (destinations.length === 0) {
    const empty = document.createElement("div");
    empty.className = "quest-empty";
    empty.textContent = "No other destinations attuned.";
    list.appendChild(empty);
  }
}
