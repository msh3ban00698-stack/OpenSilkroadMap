import type { TeleportPad } from "./teleport_data.js";

export interface TeleportPanelOpts {
  root: HTMLElement;
  pads: TeleportPad[];
  townGates: TeleportPad[];
  currentPadId: string;
  playerPos: { x: number; z: number };
  currentRegionId: number;
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
  const knownIds = new Set<string>();

  const renderRow = (pad: TeleportPad): void => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "sro-btn sro-btn-secondary tp-row";
    const label = document.createElement("span");
    label.textContent = pad.name;
    const meta = document.createElement("small");
    if (pad.regionId === opts.currentRegionId) {
      const dist = Math.round(Math.hypot(pad.x - opts.playerPos.x, pad.z - opts.playerPos.z));
      meta.textContent = `${dist}m`;
    } else {
      meta.textContent = pad.regionName;
    }
    row.appendChild(label);
    row.appendChild(meta);
    row.addEventListener("click", () => {
      close();
      opts.onTravel(pad);
    });
    list.appendChild(row);
  };

  const renderHeader = (title: string): void => {
    const h = document.createElement("div");
    h.className = "tp-group";
    h.textContent = title;
    list.appendChild(h);
  };

  renderHeader("Towns");
  for (const pad of opts.townGates) {
    if (String(pad.id) === opts.currentPadId) continue;
    knownIds.add(String(pad.id));
    renderRow(pad);
  }

  const locals = opts.pads.filter(
    (p) => String(p.id) !== opts.currentPadId && !knownIds.has(String(p.id)) && p.regionId === opts.currentRegionId,
  );
  if (locals.length > 0) {
    renderHeader("Local");
    for (const pad of locals) renderRow(pad);
  }

  if (knownIds.size === 0 && locals.length === 0) {
    const empty = document.createElement("div");
    empty.className = "quest-empty";
    empty.textContent = "No other destinations attuned.";
    list.appendChild(empty);
  }
}
