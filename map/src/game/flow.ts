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
import { getClassStats, HP_PER_LEVEL, MP_PER_LEVEL } from "./game_data";
import { REGIONS, regionById, START_REGION as START_REGION_DEF, type RegionDef } from "./regions";
import { regionForPad, type TeleportPad } from "./teleport_data";
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
  skills: [],
};

class GameFlow {
  private screens: GameScreens;
  private world: GameWorld | null = null;
  private controls: TouchControls | null = null;
  private hud: Hud | null = null;
  private currentChar: GameCharacter | null = null;
  private currentRegion: RegionDef = START_REGION_DEF;
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
    this.installAuditHook();
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
    const entryRegion = REGIONS.some((r) => r.id === char.region) ? regionById(char.region) : START_REGION_DEF;
    this.screens.renderLoading(`Loading ${entryRegion.name} (region ${entryRegion.id})...`);
    this.worldContainer.style.display = "none";

    try {
      const persist = (): void => this.persistCurrent();

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
        onOpenParty: () => this.openPartyPanel(),
        onOpenWarehouse: () => this.openWarehousePanel(),
        getNpcPos: (npcCode) => {
          if (!this.world) return null;
          const st = this.world.getState() as unknown as HudWorldState;
          const n = st.npcs.find((p) => p.id === npcCode);
          return n ? { x: n.x, z: n.z } : null;
        },
        getCamps: () => this.world?.getCamps() ?? [],
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

      const arrival = this.currentRegion ? { x: char.position.x, z: char.position.z } : undefined;
      await this.buildWorld(entryRegion, char, arrival);
      this.currentRegion = entryRegion;

      window.addEventListener("resize", this.onResize);

      this.menuRoot.style.display = "none";
      this.worldContainer.style.display = "block";
      this.world?.resize();

      char.lastPlayedAt = Date.now();
      saveCharacter(char);

      this.hud.log(`Welcome to ${entryRegion.name}, ${char.name}.`);
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

  // Rebuild the 3D world for a region. Keeps the existing HUD/inventory alive;
  // used both for initial entry and for inter-region teleport travel.
  private async buildWorld(region: RegionDef, char: GameCharacter, arrival?: { x: number; z: number }): Promise<void> {
    this.screens.setLoadingMessage(`Loading ${region.name}...`);
    this.teardownWorldScene();
    const assets = await RegionLoader.load(region.id);
    this.currentRegion = region;

    this.world = new GameWorld({
      container: this.worldContainer,
      character: char,
      assets,
      region,
      onLog: (msg) => this.hud?.log(msg),
      onInteractNpc: (npc) => {
        void import("./quest_runtime").then(({ onNpcTalked }) => {
          if (onNpcTalked(char, npc.name, (msg) => this.hud?.log(msg))) {
            if (this.currentChar) saveCharacter(this.currentChar);
          }
        });
        this.hud?.showNpcDialog(npc);
      },
      onInteractGate: (gate) => this.showTeleportPanel(gate),
      onMobKilled: (mobCode) => {
        void import("./quest_runtime").then(({ onMobKilled }) => {
          if (onMobKilled(char, mobCode, (msg) => this.hud?.log(msg))) {
            if (this.currentChar) saveCharacter(this.currentChar);
          }
        });
      },
      onCharacterMutated: () => {
        if (this.currentChar) {
          this.recomputeStats(this.currentChar);
          saveCharacter(this.currentChar);
        }
      },
    });
    this.world.resize();
    if (arrival) {
      this.world.teleportTo(arrival.x, arrival.z);
    }

    this.controls = new TouchControls({
      container: this.worldContainer,
      joystickBase: this.hud!.joystickBase,
      joystickKnob: this.hud!.joystickKnob,
      onMove: (x, z) => this.world?.setMovement(x, z),
      onRotate: (dx, dy) => this.world?.rotateCamera(dx, dy),
      onSelect: (clientX, clientY) => this.world?.pick(clientX, clientY),
    });

    if (this.currentChar) {
      this.currentChar.region = region.id;
      const p = this.world.getPlayerPos();
      this.currentChar.position = { x: p.x, y: p.y, z: p.z };
      saveCharacter(this.currentChar);
    }
  }

  private teardownWorldScene(): void {
    window.removeEventListener("resize", this.onResize);
    this.controls?.dispose();
    this.controls = null;
    this.world?.dispose();
    this.world = null;
  }

  private toggleInventory(): void {
    if (this.inventory?.isOpen()) {
      this.closeInventory();
    } else {
      this.inventory?.show();
    }
  }

  private showTeleportPanel(gate: { id: string | number; name: string; x: number; z: number }): void {
    if (!this.world) return;
    this.hud?.closeDialog();
    void import("./teleport_data")
      .then(async ({ loadTeleportPads, loadTownGates }) => {
        const [regionPads, townGates] = await Promise.all([loadTeleportPads(this.currentRegion), loadTownGates()]);
        const pos = this.world!.getPlayerPos();
        void import("./teleport_panel").then(({ openTeleportPanel }) => {
          openTeleportPanel(this.hud!.root, {
            root: this.hud!.root,
            pads: regionPads,
            townGates,
            currentPadId: String(gate.id),
            playerPos: pos,
            currentRegionId: this.currentRegion.id,
            onTravel: (pad) => this.travelTo(pad),
          });
        });
      })
      .catch(() => {
        this.hud?.log("Teleport data unavailable.");
      });
  }

  private async travelTo(pad: TeleportPad): Promise<void> {
    if (!this.world) return;
    const destRegion = regionForPad(pad);
    this.hud?.closeDialog();
    this.menuRoot.style.display = "block";
    this.screens.renderLoading(`Traveling to ${pad.name}...`);
    this.worldContainer.style.display = "none";
    await new Promise((r) => setTimeout(r, 900));

    if (destRegion.id === this.currentRegion.id) {
      this.world.teleportTo(pad.x, pad.z);
    } else {
      try {
        await this.buildWorld(destRegion, this.currentChar!, { x: pad.x, z: pad.z });
      } catch (e) {
        console.error(e);
        this.hud?.log("Travel failed — the destination region could not be loaded.");
        this.world?.teleportTo(pad.x, pad.z);
      }
    }
    this.menuRoot.style.display = "none";
    this.worldContainer.style.display = "block";
    this.world.resize();
    if (this.currentChar) {
      const p = this.world.getPlayerPos();
      this.currentChar.position = { x: p.x, y: p.y, z: p.z };
      saveCharacter(this.currentChar);
    }
    this.hud?.log(`You arrive at ${pad.name}, ${destRegion.name}.`);
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

  private persistCurrent(): void {
    if (this.currentChar) {
      this.recomputeStats(this.currentChar);
      saveCharacter(this.currentChar);
    }
  }

  private openPartyPanel(): void {
    const char = this.currentChar;
    if (!char || !this.hud) return;
    void import("./party_panel").then(({ openPartyPanel }) => {
      openPartyPanel(this.hud!.root, {
        root: this.hud!.root,
        character: char,
        onMutate: () => {
          this.persistCurrent();
          this.inventory?.refresh();
        },
        log: (msg) => this.hud?.log(msg),
        onHire: (def) => this.world?.hireCompanion(def) ?? false,
        onDismiss: (code) => this.world?.dismissCompanion(code) ?? false,
      });
    });
  }

  private openWarehousePanel(): void {
    const char = this.currentChar;
    if (!char || !this.hud) return;
    void import("./warehouse_panel").then(({ openWarehousePanel }) => {
      openWarehousePanel(this.hud!.root, {
        root: this.hud!.root,
        character: char,
        onMutate: () => {
          this.persistCurrent();
          this.inventory?.refresh();
        },
        log: (msg) => this.hud?.log(msg),
      });
    });
  }

  private installAuditHook(): void {
    if (!new URLSearchParams(location.search).has("audit")) return;
    const api: Record<string, unknown> = {
      screen: (): string => {
        if (this.worldContainer.style.display !== "none" && this.menuRoot.style.display === "none") return "world";
        if (this.menuRoot.querySelector(".sro-login")) return "login";
        if (this.menuRoot.querySelector("#ga-user")) return "create-account";
        if (this.menuRoot.querySelector(".sro-select")) return "select";
        if (this.menuRoot.querySelector(".sro-create")) return "create";
        if (this.menuRoot.querySelector(".sro-loading")) return "loading";
        if (this.menuRoot.querySelector(".sro-error")) return "error";
        return "menu";
      },
      showLogin: (): void => this.showLogin(),
      showSelect: (): void => this.showSelect(),
      showCreate: (): void => this.showCreate(),
      showCreateAccount: (): void => this.showCreateAccount(),
      login: (u: string, p: string): Promise<void> => this.handleLogin(u, p),
      createAccount: (u: string, p: string): Promise<void> => this.handleCreateAccount(u, p),
      setup: async (username: string): Promise<{ account: boolean; chars: string[] }> => {
        const res = await createAccount(username, "test1234");
        if (loadCharacters().length === 0) {
          createCharacter({
            name: "Auditor",
            classId: "warrior",
            gender: "male",
            skinTone: "#f5d0a9",
            hairColor: "#1a1a1a",
            outfitColor: "#8b0000",
            kit: "kit_blade",
          });
        }
        this.showSelect();
        return { account: res.ok, chars: loadCharacters().map((c) => c.id) };
      },
      enter: (id: string): void => this.enterWith(id),
      inventory: (): void => this.toggleInventory(),
      inventoryOpen: (): boolean => this.inventory?.isOpen() ?? false,
      pause: (): void => this.showPause(),
      pauseOpen: (): boolean => this.pauseOverlay !== null,
      npcDialog: (code: string): void => {
        this.hud?.showNpcDialog({ id: code, name: code, x: 0, z: 0, code });
      },
      closeDialog: (): void => this.hud?.closeDialog(),
      shop: (code: string): void => {
        const char = this.currentChar;
        if (!char || !this.hud) return;
        void import("./shop_panel").then(({ openShop }) =>
          openShop(this.hud!.root, {
            npcCode: code,
            npcName: code,
            character: char,
            onMutate: () => this.persistCurrent(),
            log: (msg) => this.hud?.log(msg),
          }),
        );
      },
      quest: (code: string): void => {
        const char = this.currentChar;
        if (!char || !this.hud) return;
        void import("./quest_runtime").then(({ openQuestPanel }) =>
          openQuestPanel(this.hud!.root, {
            root: this.hud!.root,
            character: char,
            onMutate: () => this.persistCurrent(),
            log: (msg) => this.hud?.log(msg),
            npcCode: code,
            npcName: code,
            getNpcPos: () => null,
            camps: [],
          }),
        );
      },
      party: (): void => this.openPartyPanel(),
      warehouse: (): void => this.openWarehousePanel(),
      teleport: (): void => {
        if (!this.world) return;
        this.showTeleportPanel({ id: "audit", name: "Audit Gate", x: 0, z: 0 });
      },
      worldState: (): unknown => this.world?.getState() ?? null,
    };
    (globalThis as { __sroAudit?: Record<string, unknown> }).__sroAudit = api;
  }

  private teardownWorld(): void {
    this.hidePause();
    this.closeInventory();
    this.teardownWorldScene();
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
  document.body.classList.add("game-mode");
  const menuRoot = document.getElementById("game-menus")!;
  const worldContainer = document.getElementById("game-container")!;
  const flow = new GameFlow(menuRoot, worldContainer);
  flow.start();

  const returnBtn = document.getElementById("return-to-game");
  returnBtn?.addEventListener("click", () => flow.start());
}
