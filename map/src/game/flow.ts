import { GameScreens } from "./screens";
import {
  loadCharacters,
  saveCharacter,
  deleteCharacter,
  createCharacter,
  createAccount,
  loginAccount,
} from "./storage";
import { RegionLoader } from "./region_loader";
import { GameWorld } from "./game3d";
import { TouchControls } from "./player_control";
import { buildHud, type Hud, type HudWorldState } from "./hud";
import { buildInventoryPanel, type InventoryPanel } from "./inventory_panel";
import { getClassStats, HP_PER_LEVEL, MP_PER_LEVEL, START_REGION, START_REGION_NAME } from "./game_data";
import { getItem, isEquippable } from "./items";
import type { EquipSlot, GameCharacter } from "./types";

const emptyState: HudWorldState = {
  hp: 0,
  mp: 0,
  maxHp: 1,
  maxMp: 1,
  gold: 0,
  level: 1,
  exp: 0,
  expToNext: 0,
  name: "",
  className: "",
  dead: false,
  respawnIn: 0,
  selected: null,
  selectedTarget: null,
  pos: { x: 0, y: 0, z: 0 },
  yaw: 0,
  npcs: [],
  dummy: { x: 0, z: 0, alive: false, hp: 0, maxHp: 1, selected: false },
  bounds: { minX: 0, maxX: 0, minZ: 0, maxZ: 0 },
};

class GameFlow {
  private screens: GameScreens;
  private world: GameWorld | null = null;
  private controls: TouchControls | null = null;
  private hud: Hud | null = null;
  private currentChar: GameCharacter | null = null;
  private pauseOverlay: HTMLElement | null = null;
  private inventory: InventoryPanel | null = null;

  constructor(
    private menuRoot: HTMLElement,
    private worldContainer: HTMLElement,
  ) {
    this.screens = new GameScreens(menuRoot, {
      onBack: () => this.showLogin(),
      onLogin: (username, password) => this.handleLogin(username, password),
      onOpenAccountCreate: () => this.showCreateAccount(),
      onCreateAccount: (username, password) => this.handleCreateAccount(username, password),
      onCancelAccount: () => this.showLogin(),
      onSelectCharacter: (id) => this.enterWith(id),
      onDeleteCharacter: (id) => {
        deleteCharacter(id);
        this.showSelect();
      },
      onCreateNew: () => this.showCreate(),
      onCancelCreate: () => this.showSelect(),
      onConfirmCreate: (input) => {
        const error = this.checkName(input.name);
        if (error) return;
        createCharacter(input);
        this.showSelect();
      },
    });
  }

  private checkName(name: string): string | null {
    const trimmed = name.trim();
    if (!trimmed) return "Name is required.";
    if (trimmed.length < 3) return "Name must be at least 3 characters.";
    if (trimmed.length > 16) return "Name must be at most 16 characters.";
    if (!/^[A-Za-z0-9_\u4e00-\u9fff]+$/.test(trimmed)) {
      return "Name may contain only letters, digits, underscores or CJK characters.";
    }
    const taken = loadCharacters().some((c) => c.name.toLowerCase() === trimmed.toLowerCase());
    if (taken) return "That name is already in use.";
    return null;
  }

  start(): void {
    this.showLogin();
  }

  private showScreen(render: () => void): void {
    this.teardownWorld();
    this.worldContainer.style.display = "none";
    this.menuRoot.style.display = "block";
    this.setReturnButtonVisible(false);
    render();
  }

  private showLogin(error?: string): void {
    this.teardownWorld();
    this.worldContainer.style.display = "none";
    this.menuRoot.style.display = "block";
    this.setReturnButtonVisible(false);
    this.screens.renderLogin(error);
  }

  private showCreateAccount(error?: string): void {
    this.showScreen(() => this.screens.renderCreateAccount(error));
  }

  private async handleLogin(username: string, password: string): Promise<void> {
    const res = await loginAccount(username, password);
    if (!res.ok) {
      this.showLogin(res.error);
      return;
    }
    this.showSelect();
  }

  private async handleCreateAccount(username: string, password: string): Promise<void> {
    const res = await createAccount(username, password);
    if (!res.ok) {
      this.showCreateAccount(res.error);
      return;
    }
    this.showSelect();
  }

  private showSelect(): void {
    this.showScreen(() => this.screens.renderSelect(loadCharacters()));
  }

  private showCreate(): void {
    this.worldContainer.style.display = "none";
    this.menuRoot.style.display = "block";
    this.screens.renderCreate();
  }

  private setReturnButtonVisible(visible: boolean): void {
    const btn = document.getElementById("return-to-game");
    if (btn) btn.style.display = visible ? "block" : "none";
  }

  private enterWith(charId: string): void {
    const char = loadCharacters().find((c) => c.id === charId);
    if (!char) {
      this.screens.renderError("Character Not Found", "The selected character could not be loaded.", "Back");
      return;
    }
    this.currentChar = char;
    this.enterWorld(char);
  }

  private async enterWorld(char: GameCharacter): Promise<void> {
    this.menuRoot.style.display = "block";
    this.screens.renderLoading(`Loading ${START_REGION_NAME} (region ${START_REGION})...`);
    this.worldContainer.style.display = "none";

    try {
      const assets = await RegionLoader.load(START_REGION);
      this.screens.setLoadingMessage("Building world...");
      await new Promise((r) => setTimeout(r, 100));

      this.menuRoot.style.display = "none";
      this.worldContainer.style.display = "block";

      const persist = (): void => {
        if (this.currentChar) {
          this.recomputeStats(this.currentChar);
          saveCharacter(this.currentChar);
        }
      };

      this.hud = buildHud({
        character: char,
        onAttack: () => this.world?.attack(),
        onInteract: () => this.world?.interact(),
        onMenu: () => this.showPause(),
        onToggleInventory: () => this.toggleInventory(),
        onUsePotion: () => this.useBestPotion(),
        onUseSkill: (code, name) => this.world?.useSkill(code, name),
        onLevelUp: (level) => {
          this.hud?.log(`Level up! You reached level ${level}.`);
          this.hud?.showLevelUp(level);
        },
        onCharacterMutated: () => persist(),
        getState: () => (this.world ? (this.world.getState() as unknown as HudWorldState) : emptyState),
      });
      document.getElementById("game-root")!.appendChild(this.hud.root);

      this.inventory = buildInventoryPanel({
        parent: this.hud.root,
        character: char,
        onEquip: (itemId) => this.equipItem(itemId),
        onUnequip: (slot) => this.unequipItem(slot),
        onUse: (itemId) => {
          if (this.world?.usePotion(itemId)) {
            persist();
            this.inventory?.refresh();
          }
        },
        onClose: () => this.closeInventory(),
      });

      this.world = new GameWorld({
        container: this.worldContainer,
        character: char,
        assets,
        onLog: (msg) => this.hud?.log(msg),
        onInteractNpc: (npc) => this.hud?.showNpcDialog(npc),
        onCharacterMutated: persist,
      });
      this.world.resize();

      this.controls = new TouchControls({
        container: this.worldContainer,
        joystickBase: this.hud.joystickBase,
        joystickKnob: this.hud.joystickKnob,
        onMove: (x, z) => this.world?.setMovement(x, z),
        onRotate: (dx, dy) => this.world?.rotateCamera(dx, dy),
        onSelect: (clientX, clientY) => this.world?.pick(clientX, clientY),
      });

      window.addEventListener("resize", this.onResize);

      char.lastPlayedAt = Date.now();
      saveCharacter(char);

      this.hud.log(`Welcome to ${START_REGION}, ${char.name}.`);
      this.hud.log("Move with the left joystick; drag to look around; tap a target.");
    } catch (e) {
      console.error(e);
      this.screens.renderError(
        "Failed to Enter World",
        e instanceof Error ? e.message : String(e),
        "Back to Character Select",
      );
    }
  }

  private toggleInventory(): void {
    if (this.inventory?.isOpen()) {
      this.closeInventory();
    } else {
      this.inventory?.show();
    }
  }

  private closeInventory(): void {
    this.inventory?.hide();
  }

  private recomputeStats(char: GameCharacter): void {
    const base = getClassStats(char.classId);
    let maxHp = base.hp + (char.level - 1) * HP_PER_LEVEL;
    let maxMp = base.mp + (char.level - 1) * MP_PER_LEVEL;
    for (const slot of ["weapon", "armor", "accessory"] as const) {
      const id = char.equipment[slot];
      if (!id) continue;
      const item = getItem(id);
      if (item?.hpBonus) maxHp += item.hpBonus;
    }
    char.maxHp = maxHp;
    char.maxMp = maxMp;
    if (char.hp > maxHp) char.hp = maxHp;
    if (char.mp > maxMp) char.mp = maxMp;
  }

  private equipItem(itemId: string): void {
    const char = this.currentChar;
    if (!char) return;
    const item = getItem(itemId);
    if (!item || !isEquippable(item)) return;
    const stack = char.inventory.find((s) => s.id === itemId);
    if (!stack) return;
    const current = char.equipment[item.slot];
    stack.count -= 1;
    if (stack.count <= 0) {
      char.inventory = char.inventory.filter((s) => s.id !== itemId);
    }
    if (current) {
      const existing = char.inventory.find((s) => s.id === current);
      if (existing) existing.count += 1;
      else char.inventory.push({ id: current, count: 1 });
    }
    char.equipment[item.slot] = itemId;
    this.recomputeStats(char);
    this.world?.applyEquipment(char.equipment);
    saveCharacter(char);
    this.inventory?.refresh();
    this.hud?.log(`Equipped ${item.name}.`);
  }

  private unequipItem(slot: EquipSlot): void {
    const char = this.currentChar;
    if (!char) return;
    const id = char.equipment[slot];
    if (!id) return;
    const existing = char.inventory.find((s) => s.id === id);
    if (existing) existing.count += 1;
    else char.inventory.push({ id, count: 1 });
    char.equipment[slot] = null;
    this.recomputeStats(char);
    this.world?.applyEquipment(char.equipment);
    saveCharacter(char);
    const item = getItem(id);
    this.hud?.log(`Unequipped ${item ? item.name : id}.`);
    this.inventory?.refresh();
  }

  private useBestPotion(): boolean {
    const char = this.currentChar;
    if (!char) return false;
    for (const id of ["hp_potion_02", "hp_potion_01"]) {
      const stack = char.inventory.find((s) => s.id === id && s.count > 0);
      if (stack) {
        const ok = this.world?.usePotion(id);
        if (ok) {
          saveCharacter(char);
          this.inventory?.refresh();
          return true;
        }
        return false;
      }
    }
    this.hud?.log("No HP potions in your bag.");
    return false;
  }

  private onResize = (): void => {
    this.world?.resize();
  };

  private showPause(): void {
    if (this.pauseOverlay) return;
    this.closeInventory();
    const overlay = document.createElement("div");
    overlay.className = "sro-screen sro-pause";
    overlay.innerHTML = `
      <div class="sro-window sro-center-panel">
        <div class="sro-window-title">Menu</div>
        ${this.currentChar ? `<div class="sro-note">${escapeHtml(this.currentChar.name)} · Lv.${this.currentChar.level}</div>` : ""}
        <button class="sro-btn sro-btn-primary" id="gp-resume">Resume</button>
        <button class="sro-btn sro-btn-secondary" id="gp-select">Character Select</button>
        <button class="sro-btn sro-btn-secondary" id="gp-logout">Log Out</button>
      </div>
    `;
    document.getElementById("game-root")!.appendChild(overlay);
    this.pauseOverlay = overlay;

    overlay.querySelector("#gp-resume")!.addEventListener("click", () => this.hidePause());
    overlay.querySelector("#gp-select")!.addEventListener("click", () => this.showSelect());
    overlay.querySelector("#gp-logout")!.addEventListener("click", () => this.showLogin());
  }

  private hidePause(): void {
    if (this.pauseOverlay) {
      this.pauseOverlay.remove();
      this.pauseOverlay = null;
    }
  }

  private teardownWorld(): void {
    this.hidePause();
    this.closeInventory();
    window.removeEventListener("resize", this.onResize);
    this.controls?.dispose();
    this.controls = null;
    this.world?.dispose();
    this.world = null;
    this.hud?.dispose();
    this.hud = null;
    this.inventory?.dispose();
    this.inventory = null;
  }
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function initGameFlow(): void {
  const menuRoot = document.getElementById("game-menus")!;
  const worldContainer = document.getElementById("game-container")!;
  const flow = new GameFlow(menuRoot, worldContainer);
  flow.start();

  const returnBtn = document.getElementById("return-to-game");
  returnBtn?.addEventListener("click", () => flow.start());
}
