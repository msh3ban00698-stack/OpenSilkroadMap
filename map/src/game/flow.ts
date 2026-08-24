import { GameScreens } from "./screens";
import {
  loadCharacters,
  saveCharacter,
  deleteCharacter,
  createCharacter,
} from "./storage";
import { RegionLoader } from "./region_loader";
import { GameWorld } from "./game3d";
import { TouchControls } from "./player_control";
import { buildHud, type Hud } from "./hud";
import { START_REGION } from "./game_data";
import type { GameCharacter } from "./types";

class GameFlow {
  private screens: GameScreens;
  private world: GameWorld | null = null;
  private controls: TouchControls | null = null;
  private hud: Hud | null = null;
  private currentChar: GameCharacter | null = null;
  private pauseOverlay: HTMLElement | null = null;

  constructor(
    private menuRoot: HTMLElement,
    private worldContainer: HTMLElement,
  ) {
    this.screens = new GameScreens(menuRoot, {
      onStartGame: () => this.showSelect(),
      onOpenMap: () => this.showMap(),
      onBack: () => this.showIntro(),
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
        const char = createCharacter(input);
        this.enterWith(char.id);
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
    this.showIntro();
  }

  private showIntro(): void {
    this.teardownWorld();
    this.worldContainer.style.display = "none";
    this.menuRoot.style.display = "block";
    this.setReturnButtonVisible(false);
    this.screens.renderIntro();
  }

  private showSelect(): void {
    this.teardownWorld();
    this.worldContainer.style.display = "none";
    this.menuRoot.style.display = "block";
    this.setReturnButtonVisible(false);
    this.screens.renderSelect(loadCharacters());
  }

  private showCreate(): void {
    this.worldContainer.style.display = "none";
    this.menuRoot.style.display = "block";
    this.screens.renderCreate();
  }

  private showMap(): void {
    this.teardownWorld();
    this.menuRoot.style.display = "none";
    this.worldContainer.style.display = "none";
    this.setReturnButtonVisible(true);
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
    this.screens.renderLoading(`Loading region ${START_REGION}...`);
    this.worldContainer.style.display = "none";

    try {
      const assets = await RegionLoader.load(START_REGION);
      this.screens.setLoadingMessage("Building world...");
      await new Promise((r) => setTimeout(r, 100));

      this.menuRoot.style.display = "none";
      this.worldContainer.style.display = "block";

      this.hud = buildHud({
        character: char,
        onAttack: () => this.world?.attack(),
        onInteract: () => this.world?.interact(),
        onMenu: () => this.showPause(),
      });
      document.getElementById("game-root")!.appendChild(this.hud.root);

      this.world = new GameWorld({
        container: this.worldContainer,
        character: char,
        assets,
        onLog: (msg) => this.hud?.log(msg),
      });
      this.world.resize();

      this.controls = new TouchControls({
        container: this.worldContainer,
        joystickBase: this.hud.joystickBase,
        joystickKnob: this.hud.joystickKnob,
        onMove: (x, z) => this.world?.setMovement(x, z),
        onRotate: (dx, dy) => this.world?.rotateCamera(dx, dy),
      });

      window.addEventListener("resize", this.onResize);

      char.lastPlayedAt = Date.now();
      saveCharacter(char);

      this.hud.log(`Welcome to ${START_REGION}, ${char.name}.`);
      this.hud.log("Move with the left joystick; drag to look around.");
    } catch (e) {
      console.error(e);
      this.screens.renderError(
        "Failed to Enter World",
        e instanceof Error ? e.message : String(e),
        "Back to Character Select",
      );
    }
  }

  private onResize = (): void => {
    this.world?.resize();
  };

  private showPause(): void {
    if (this.pauseOverlay) return;
    const overlay = document.createElement("div");
    overlay.className = "game-screen";
    overlay.innerHTML = `
      <div class="game-panel">
        <div class="game-title">Menu</div>
        <div class="game-body">
          <div class="game-note">${this.currentChar ? `${this.currentChar.name} · Lv.${this.currentChar.level}` : ""}</div>
        </div>
        <div class="game-footer">
          <button class="game-btn game-btn-primary" id="gp-resume">Resume</button>
          <button class="game-btn game-btn-ghost" id="gp-select">Character Select</button>
          <button class="game-btn game-btn-ghost" id="gp-map">Open World Map</button>
        </div>
      </div>
    `;
    document.getElementById("game-root")!.appendChild(overlay);
    this.pauseOverlay = overlay;

    overlay.querySelector("#gp-resume")!.addEventListener("click", () => this.hidePause());
    overlay.querySelector("#gp-select")!.addEventListener("click", () => this.showSelect());
    overlay.querySelector("#gp-map")!.addEventListener("click", () => this.showMap());
  }

  private hidePause(): void {
    if (this.pauseOverlay) {
      this.pauseOverlay.remove();
      this.pauseOverlay = null;
    }
  }

  private teardownWorld(): void {
    this.hidePause();
    window.removeEventListener("resize", this.onResize);
    this.controls?.dispose();
    this.controls = null;
    this.world?.dispose();
    this.world = null;
    this.hud?.dispose();
    this.hud = null;
  }
}

export function initGameFlow(): void {
  const menuRoot = document.getElementById("game-menus")!;
  const worldContainer = document.getElementById("game-container")!;
  const flow = new GameFlow(menuRoot, worldContainer);
  flow.start();

  const returnBtn = document.getElementById("return-to-game");
  returnBtn?.addEventListener("click", () => flow.start());
}
