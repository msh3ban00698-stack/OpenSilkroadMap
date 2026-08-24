import type { GameCharacter } from "./types";
import { getClass, START_REGION_NAME } from "./game_data";

export interface NpcDialogInfo {
  id: string;
  name: string;
  x: number;
  z: number;
}

export interface HudWorldState {
  hp: number;
  mp: number;
  maxHp: number;
  maxMp: number;
  gold: number;
  level: number;
  name: string;
  className: string;
  dead: boolean;
  respawnIn: number;
  selected: { kind: "npc" | "dummy"; id: string; name: string; x: number; z: number } | null;
  pos: { x: number; y: number; z: number };
  yaw: number;
  npcs: { id: string; name: string; x: number; z: number; selected: boolean }[];
  dummy: { x: number; z: number; alive: boolean; hp: number; maxHp: number; selected: boolean };
  bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
}

export interface HudOptions {
  character: GameCharacter;
  onAttack: () => void;
  onInteract: () => void;
  onMenu: () => void;
  onToggleInventory: () => void;
  onUsePotion: () => boolean;
  getState: () => HudWorldState;
}

export interface Hud {
  root: HTMLElement;
  joystickBase: HTMLElement;
  joystickKnob: HTMLElement;
  log(msg: string): void;
  showNpcDialog(npc: NpcDialogInfo): void;
  dispose(): void;
}

const MINIMAP_SIZE = 160;
const MINIMAP_RADIUS = 250;
const MINIMAP_POLL_MS = 150;

export function buildHud(opts: HudOptions): Hud {
  const cls = getClass(opts.character.classId);
  const root = document.createElement("div");
  root.className = "game-hud";
  root.innerHTML = `
    <div class="hud-plate">
      <div class="hud-name">${opts.character.name}</div>
      <div class="hud-meta">Lv.${opts.character.level} ${cls ? cls.name : opts.character.classId}</div>
      <div class="hud-bars">
        <div class="hud-bar-row">
          <div class="hud-bar hp"><div class="hud-bar-fill" id="hud-hp-fill"></div></div>
          <div class="hud-bar-num" id="hud-hp-num"></div>
        </div>
        <div class="hud-bar-row">
          <div class="hud-bar mp"><div class="hud-bar-fill" id="hud-mp-fill"></div></div>
          <div class="hud-bar-num" id="hud-mp-num"></div>
        </div>
      </div>
    </div>
    <div class="hud-corner">
      <div class="hud-region">${START_REGION_NAME}</div>
      <div class="hud-gold-row"><span class="hud-coin"></span><span id="hud-gold"></span></div>
      <div class="hud-corner-btns">
        <button class="hud-btn hud-mini" id="hud-inventory">Bag</button>
        <button class="hud-btn hud-mini" id="hud-menu">Menu</button>
      </div>
    </div>
    <div class="hud-minimap-wrap">
      <canvas class="hud-minimap" id="hud-minimap" width="${MINIMAP_SIZE}" height="${MINIMAP_SIZE}"></canvas>
    </div>
    <div class="hud-target" id="hud-target" style="display:none">
      <div class="hud-target-name" id="hud-target-name"></div>
      <div class="hud-bar-row">
        <div class="hud-bar target"><div class="hud-bar-fill" id="hud-target-fill"></div></div>
        <div class="hud-bar-num" id="hud-target-num"></div>
      </div>
      <div class="hud-target-dist" id="hud-target-dist"></div>
    </div>
    <div class="hud-skillbar" id="hud-skillbar">
      <button class="hud-slot" data-skill="atk"><span class="hud-slot-key">1</span>ATK</button>
      <button class="hud-slot" data-skill="potion"><span class="hud-slot-key">2</span>POT</button>
      <button class="hud-slot hud-slot-locked" data-skill="locked"><span class="hud-slot-key">3</span>--</button>
      <button class="hud-slot hud-slot-locked" data-skill="locked"><span class="hud-slot-key">4</span>--</button>
      <button class="hud-slot hud-slot-locked" data-skill="locked"><span class="hud-slot-key">5</span>--</button>
      <button class="hud-slot hud-slot-locked" data-skill="locked"><span class="hud-slot-key">6</span>--</button>
    </div>
    <div class="hud-log" id="hud-log"></div>
    <div class="hud-joystick" id="joy-base">
      <div class="hud-joystick-knob" id="joy-knob"></div>
    </div>
    <div class="hud-actions">
      <button class="hud-btn hud-action" id="hud-attack">ATK</button>
      <button class="hud-btn hud-action" id="hud-interact">TALK</button>
    </div>
    <div class="hud-death" id="hud-death" style="display:none">
      <div class="hud-death-title">You have been defeated</div>
      <div class="hud-death-sub" id="hud-death-sub"></div>
    </div>
  `;

  const logEl = root.querySelector("#hud-log") as HTMLElement;
  const log = (msg: string): void => {
    const line = document.createElement("div");
    line.textContent = msg;
    line.className = "hud-log-line";
    logEl.appendChild(line);
    while (logEl.children.length > 4) {
      logEl.removeChild(logEl.firstChild!);
    }
  };

  const hpFill = root.querySelector("#hud-hp-fill") as HTMLElement;
  const mpFill = root.querySelector("#hud-mp-fill") as HTMLElement;
  const hpNum = root.querySelector("#hud-hp-num") as HTMLElement;
  const mpNum = root.querySelector("#hud-mp-num") as HTMLElement;
  const goldEl = root.querySelector("#hud-gold") as HTMLElement;
  const targetEl = root.querySelector("#hud-target") as HTMLElement;
  const targetNameEl = root.querySelector("#hud-target-name") as HTMLElement;
  const targetFill = root.querySelector("#hud-target-fill") as HTMLElement;
  const targetNum = root.querySelector("#hud-target-num") as HTMLElement;
  const targetDist = root.querySelector("#hud-target-dist") as HTMLElement;
  const deathEl = root.querySelector("#hud-death") as HTMLElement;
  const deathSub = root.querySelector("#hud-death-sub") as HTMLElement;
  const minimap = root.querySelector("#hud-minimap") as HTMLCanvasElement;

  const setBar = (fill: HTMLElement, num: HTMLElement, cur: number, max: number): void => {
    const frac = max > 0 ? Math.max(0, Math.min(1, cur / max)) : 0;
    fill.style.width = `${(frac * 100).toFixed(1)}%`;
    num.textContent = `${Math.round(cur)}/${max}`;
  };

  const drawMinimap = (state: HudWorldState): void => {
    const ctx = minimap.getContext("2d");
    if (!ctx) return;
    const S = minimap.width;
    const c = S / 2;
    ctx.clearRect(0, 0, S, S);
    ctx.fillStyle = "rgba(8, 12, 18, 0.82)";
    ctx.beginPath();
    ctx.arc(c, c, c - 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(120, 160, 210, 0.35)";
    ctx.lineWidth = 1;
    ctx.stroke();

    const scale = (c - 4) / MINIMAP_RADIUS;
    const px = state.pos.x;
    const pz = state.pos.z;
    const toScreen = (wx: number, wz: number): [number, number] => {
      const dx = (wx - px) * scale;
      const dz = (wz - pz) * scale;
      return [c + dx, c + dz];
    };

    const b = state.bounds;
    ctx.strokeStyle = "rgba(140, 170, 210, 0.22)";
    ctx.strokeRect(...toScreen(b.minX, b.minZ), (b.maxX - b.minX) * scale, (b.maxZ - b.minZ) * scale);

    const dot = (wx: number, wz: number, color: string, r: number, sel: boolean): void => {
      const [x, y] = toScreen(wx, wz);
      const d = Math.hypot(x - c, y - c);
      if (d > c - 4) return;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      if (sel) {
        ctx.strokeStyle = "#ffe082";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    };

    for (const npc of state.npcs) dot(npc.x, npc.z, "#4fa3ff", 4, npc.selected);
    if (state.dummy.alive) dot(state.dummy.x, state.dummy.z, "#ff5252", 4, state.dummy.selected);

    ctx.save();
    ctx.translate(c, c);
    ctx.rotate(state.yaw);
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.moveTo(0, -6);
    ctx.lineTo(4, 5);
    ctx.lineTo(0, 2);
    ctx.lineTo(-4, 5);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  };

  const refresh = (): void => {
    const s = opts.getState();
    setBar(hpFill, hpNum, s.hp, s.maxHp);
    setBar(mpFill, mpNum, s.mp, s.maxMp);
    goldEl.textContent = String(s.gold);

    if (s.selected) {
      targetEl.style.display = "block";
      targetNameEl.textContent = s.selected.name;
      if (s.selected.kind === "dummy") {
        setBar(targetFill, targetNum, s.dummy.hp, s.dummy.maxHp);
      } else {
        setBar(targetFill, targetNum, 0, 1);
        targetNum.textContent = "NPC";
      }
      const dist = Math.hypot(s.selected.x - s.pos.x, s.selected.z - s.pos.z);
      targetDist.textContent = `${dist.toFixed(1)}m`;
    } else {
      targetEl.style.display = "none";
    }

    if (s.dead) {
      deathEl.style.display = "flex";
      deathSub.textContent = `Recovering in ${Math.ceil(s.respawnIn / 1000)}s...`;
    } else {
      deathEl.style.display = "none";
    }

    drawMinimap(s);
  };

  root.querySelector("#hud-attack")!.addEventListener("click", opts.onAttack);
  root.querySelector("#hud-interact")!.addEventListener("click", opts.onInteract);
  root.querySelector("#hud-menu")!.addEventListener("click", opts.onMenu);
  root.querySelector("#hud-inventory")!.addEventListener("click", opts.onToggleInventory);

  root.querySelectorAll(".hud-slot[data-skill]").forEach((el) => {
    el.addEventListener("click", () => {
      const skill = (el as HTMLElement).dataset.skill;
      if (skill === "atk") {
        opts.onAttack();
      } else if (skill === "potion") {
        opts.onUsePotion();
      } else {
        log("Skill locked: no skill data is available for this class yet.");
      }
    });
  });

  const pollTimer = window.setInterval(refresh, MINIMAP_POLL_MS);
  refresh();

  let dialogRoot: HTMLElement | null = null;
  const showNpcDialog = (npc: NpcDialogInfo): void => {
    if (dialogRoot) return;
    const dlg = document.createElement("div");
    dlg.className = "hud-dialog";
    dlg.innerHTML = `
      <div class="hud-dialog-panel">
        <div class="hud-dialog-title">${npc.name}</div>
        <div class="hud-dialog-body">
          The doorway before you leads back toward the surface.
          (NPC dialogue is a placeholder; no real quest text data is wired in this phase.)
        </div>
        <div class="hud-dialog-actions">
          <button class="hud-btn hud-mini" id="hd-test">Interact Test</button>
          <button class="hud-btn hud-mini hud-primary" id="hd-close">Close</button>
        </div>
      </div>
    `;
    dlg.addEventListener("click", (e) => {
      if (e.target === dlg) closeDialog();
    });
    dlg.querySelector("#hd-test")!.addEventListener("click", () => {
      log(`[interaction] ${npc.name}: the door is locked in this prototype.`);
    });
    dlg.querySelector("#hd-close")!.addEventListener("click", closeDialog);
    root.appendChild(dlg);
    dialogRoot = dlg;
  };

  const closeDialog = (): void => {
    if (dialogRoot) {
      dialogRoot.remove();
      dialogRoot = null;
    }
  };

  return {
    root,
    joystickBase: root.querySelector("#joy-base")!,
    joystickKnob: root.querySelector("#joy-knob")!,
    log,
    showNpcDialog,
    dispose: () => {
      window.clearInterval(pollTimer);
      closeDialog();
      if (root.parentElement) root.parentElement.removeChild(root);
    },
  };
}
