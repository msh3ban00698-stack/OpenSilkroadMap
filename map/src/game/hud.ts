import type { GameCharacter } from "./types";
import { getClass, START_REGION_NAME } from "./game_data";

export interface HudOptions {
  character: GameCharacter;
  onAttack: () => void;
  onInteract: () => void;
  onMenu: () => void;
}

export interface Hud {
  root: HTMLElement;
  joystickBase: HTMLElement;
  joystickKnob: HTMLElement;
  log(msg: string): void;
  dispose(): void;
}

export function buildHud(opts: HudOptions): Hud {
  const cls = getClass(opts.character.classId);
  const root = document.createElement("div");
  root.className = "game-hud";
  root.innerHTML = `
    <div class="hud-plate">
      <div class="hud-name">${opts.character.name}</div>
      <div class="hud-meta">Lv.${opts.character.level} ${cls ? cls.name : opts.character.classId}</div>
    </div>
    <div class="hud-region">${START_REGION_NAME}</div>
    <button class="hud-btn hud-menu" id="hud-menu">Menu</button>
    <div class="hud-log" id="hud-log"></div>
    <div class="hud-joystick" id="joy-base">
      <div class="hud-joystick-knob" id="joy-knob"></div>
    </div>
    <div class="hud-actions">
      <button class="hud-btn hud-action" id="hud-attack">ATK</button>
      <button class="hud-btn hud-action" id="hud-interact">TALK</button>
    </div>
  `;

  const logEl = root.querySelector("#hud-log") as HTMLElement;
  let logCount = 0;
  const log = (msg: string): void => {
    const line = document.createElement("div");
    line.textContent = msg;
    line.className = "hud-log-line";
    logEl.appendChild(line);
    logCount++;
    while (logEl.children.length > 4) {
      logEl.removeChild(logEl.firstChild!);
    }
  };

  root.querySelector("#hud-attack")!.addEventListener("click", opts.onAttack);
  root.querySelector("#hud-interact")!.addEventListener("click", opts.onInteract);
  root.querySelector("#hud-menu")!.addEventListener("click", opts.onMenu);

  return {
    root,
    joystickBase: root.querySelector("#joy-base")!,
    joystickKnob: root.querySelector("#joy-knob")!,
    log,
    dispose: () => {
      if (root.parentElement) root.parentElement.removeChild(root);
    },
  };
}
