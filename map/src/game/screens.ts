import { VERIFIED_CLASSES, getClass, STARTER_KITS } from "./game_data";
import type { GameCharacter } from "./types";

export interface ScreensCallbacks {
  onStartGame: () => void;
  onOpenMap: () => void;
  onOpenCharacterViewer: () => void;
  onBack: () => void;
  onSelectCharacter: (id: string) => void;
  onDeleteCharacter: (id: string) => void;
  onCreateNew: () => void;
  onCancelCreate: () => void;
  onConfirmCreate: (input: {
    name: string;
    classId: string;
    gender: "male" | "female";
    skinTone: string;
    hairColor: string;
    outfitColor: string;
    kit: string;
  }) => void;
}

const SKIN_TONES = ["#f5d0a9", "#e0ac69", "#c68642", "#8d5524"];
const HAIR_COLORS = ["#1a1a1a", "#3b2f2f", "#6b4226", "#d4a437"];
const OUTFIT_COLORS = ["#8b0000", "#1f4e79", "#3a6b35", "#5b3a8c", "#7a5c2e"];

export class GameScreens {
  private root: HTMLElement;
  private cb: ScreensCallbacks;

  constructor(root: HTMLElement, cb: ScreensCallbacks) {
    this.root = root;
    this.cb = cb;
  }

  private clear(): void {
    this.root.innerHTML = "";
  }

  private shell(title: string, body: string, footer: string): void {
    this.clear();
    this.root.innerHTML = `
      <div class="game-screen">
        <div class="game-panel">
          <div class="game-title">${title}</div>
          <div class="game-body">${body}</div>
          <div class="game-footer">${footer}</div>
        </div>
      </div>
    `;
  }

  renderIntro(): void {
    this.shell(
      "SILKROAD",
      `
        <div class="game-subtitle">OpenSilkroad 3D Client</div>
        <div class="game-note">Single-player prototype built on the verified
          OpenSilkroadMap data pipeline (Phase A/B/C).</div>
        <div class="game-logostripe"></div>
      `,
      `
        <button id="gs-start" class="game-btn game-btn-primary">Start Game</button>
        <button id="gs-charview" class="game-btn game-btn-ghost">Character Viewer</button>
        <button id="gs-map" class="game-btn game-btn-ghost">Open World Map</button>
      `,
    );
    this.root.querySelector("#gs-start")!.addEventListener("click", () => this.cb.onStartGame());
    this.root.querySelector("#gs-charview")!.addEventListener("click", () => this.cb.onOpenCharacterViewer());
    this.root.querySelector("#gs-map")!.addEventListener("click", () => this.cb.onOpenMap());
  }

  renderSelect(characters: GameCharacter[]): void {
    let listHtml: string;
    if (characters.length === 0) {
      listHtml = `<div class="game-empty">No characters yet.<br>Create your first adventurer.</div>`;
    } else {
      listHtml = characters
        .map((c) => {
          const cls = getClass(c.classId);
          return `
            <div class="game-char" data-id="${c.id}">
              <div class="game-char-info">
                <div class="game-char-name">${c.name}</div>
                <div class="game-char-meta">Lv.${c.level} · ${cls ? cls.name : c.classId}${
                  cls ? ` <span class="game-inferred">(${cls.race}, inferred)</span>` : ""
                }</div>
              </div>
              <div class="game-char-actions">
                <button class="game-btn game-btn-primary game-btn-sm" data-enter="${c.id}">Enter</button>
                <button class="game-btn game-btn-danger game-btn-sm" data-del="${c.id}">Delete</button>
              </div>
            </div>
          `;
        })
        .join("");
    }

    this.shell(
      "Select Character",
      `<div class="game-char-list">${listHtml}</div>`,
      `
        <button id="gs-new" class="game-btn game-btn-primary">Create New Character</button>
        <button id="gs-back" class="game-btn game-btn-ghost">Back</button>
      `,
    );

    this.root.querySelectorAll("[data-enter]").forEach((el) => {
      el.addEventListener("click", () => this.cb.onSelectCharacter((el as HTMLElement).dataset.enter!));
    });
    this.root.querySelectorAll("[data-del]").forEach((el) => {
      el.addEventListener("click", () => {
        const id = (el as HTMLElement).dataset.del!;
        const char = characters.find((c) => c.id === id);
        if (confirm(`Delete character "${char ? char.name : id}"? This cannot be undone.`)) {
          this.cb.onDeleteCharacter(id);
        }
      });
    });
    this.root.querySelector("#gs-new")!.addEventListener("click", () => this.cb.onCreateNew());
    this.root.querySelector("#gs-back")!.addEventListener("click", () => this.cb.onBack());
  }

  renderCreate(): void {
    const classOptions = VERIFIED_CLASSES.map(
      (c) => `
        <button class="game-class-btn" data-class="${c.id}">
          <div class="game-class-name">${c.name}</div>
          <div class="game-class-race">${c.race} <span class="game-inferred">(inferred)</span></div>
          <div class="game-class-desc">${c.desc}</div>
        </button>
      `,
    ).join("");

    const skinOptions = SKIN_TONES.map(
      (c, i) => `<button class="game-color-btn" data-skin="${c}" data-i="${i}"></button>`,
    ).join("");
    const hairOptions = HAIR_COLORS.map(
      (c, i) => `<button class="game-color-btn" data-hair="${c}" data-i="${i}"></button>`,
    ).join("");
    const outfitOptions = OUTFIT_COLORS.map(
      (c, i) => `<button class="game-color-btn" data-outfit="${c}" data-i="${i}"></button>`,
    ).join("");
    const kitOptions = STARTER_KITS.map(
      (k) => `
        <button class="game-kit-btn" data-kit="${k.id}">
          <div class="game-kit-name">${k.name}</div>
          <div class="game-kit-desc">${k.desc}</div>
        </button>
      `,
    ).join("");

    this.shell(
      "Create Character",
      `
        <div class="game-field">
          <label>Character Name</label>
          <input id="gc-name" class="game-input" type="text" maxlength="16" placeholder="3-16 letters/digits" autocomplete="off" />
          <div id="gc-name-error" class="game-error"></div>
        </div>
        <div class="game-field">
          <label>Class</label>
          <div class="game-class-grid">${classOptions}</div>
        </div>
        <div class="game-field">
          <label>Starter Kit <span class="game-inferred">(inventory choice)</span></label>
          <div class="game-kit-grid">${kitOptions}</div>
        </div>
        <div class="game-field">
          <label>Gender <span class="game-inferred">(visual only)</span></label>
          <div class="game-row">
            <button class="game-btn game-btn-sm game-gender-btn active" data-gender="male">Male</button>
            <button class="game-btn game-btn-sm game-gender-btn" data-gender="female">Female</button>
          </div>
        </div>
        <div class="game-field">
          <label>Skin Tone <span class="game-inferred">(temporary)</span></label>
          <div class="game-row">${skinOptions}</div>
        </div>
        <div class="game-field">
          <label>Hair Color <span class="game-inferred">(temporary)</span></label>
          <div class="game-row">${hairOptions}</div>
        </div>
        <div class="game-field">
          <label>Outfit Color <span class="game-inferred">(temporary)</span></label>
          <div class="game-row">${outfitOptions}</div>
        </div>
        <div class="game-note">Appearance uses a temporary technical-preview model;
          no verified character mesh is parsed yet in this phase.</div>
      `,
      `
        <button id="gc-confirm" class="game-btn game-btn-primary">Confirm</button>
        <button id="gc-cancel" class="game-btn game-btn-ghost">Back</button>
      `,
    );

    const nameInput = this.root.querySelector("#gc-name") as HTMLInputElement;
    const errorEl = this.root.querySelector("#gc-name-error") as HTMLElement;
    let classId = VERIFIED_CLASSES[0].id;
    let kit = STARTER_KITS[0].id;
    let gender: "male" | "female" = "male";
    let skinTone = SKIN_TONES[0];
    let hairColor = HAIR_COLORS[0];
    let outfitColor = OUTFIT_COLORS[0];

    const markClass = (id: string) => {
      this.root.querySelectorAll(".game-class-btn").forEach((el) => {
        (el as HTMLElement).classList.toggle("active", (el as HTMLElement).dataset.class === id);
      });
    };
    const markKit = (id: string) => {
      this.root.querySelectorAll(".game-kit-btn").forEach((el) => {
        (el as HTMLElement).classList.toggle("active", (el as HTMLElement).dataset.kit === id);
      });
    };
    const markColor = (selector: string, value: string) => {
      this.root.querySelectorAll(selector).forEach((el) => {
        (el as HTMLElement).classList.toggle("active", (el as HTMLElement).dataset.i === value);
      });
    };
    markClass(classId);
    markKit(kit);

    this.root.querySelectorAll(".game-class-btn").forEach((el) => {
      el.addEventListener("click", () => {
        classId = (el as HTMLElement).dataset.class!;
        markClass(classId);
      });
    });
    this.root.querySelectorAll(".game-kit-btn").forEach((el) => {
      el.addEventListener("click", () => {
        kit = (el as HTMLElement).dataset.kit!;
        markKit(kit);
      });
    });
    this.root.querySelectorAll(".game-gender-btn").forEach((el) => {
      el.addEventListener("click", () => {
        gender = (el as HTMLElement).dataset.gender as "male" | "female";
        this.root.querySelectorAll(".game-gender-btn").forEach((b) => b.classList.toggle("active", b === el));
      });
    });
    const bindColor = (selector: string, set: (v: string) => void) => {
      this.root.querySelectorAll(selector).forEach((el) => {
        el.addEventListener("click", () => {
          const v = (el as HTMLElement).dataset.skin || (el as HTMLElement).dataset.hair || (el as HTMLElement).dataset.outfit;
          set(v!);
          markColor(selector, (el as HTMLElement).dataset.i!);
        });
      });
    };
    bindColor("[data-skin]", (v) => (skinTone = v));
    bindColor("[data-hair]", (v) => (hairColor = v));
    bindColor("[data-outfit]", (v) => (outfitColor = v));

    this.root.querySelector("#gc-confirm")!.addEventListener("click", () => {
      const name = nameInput.value;
      const error = this.validateName(name);
      if (error) {
        errorEl.textContent = error;
        return;
      }
      this.cb.onConfirmCreate({ name: name.trim(), classId, kit, gender, skinTone, hairColor, outfitColor });
    });
    this.root.querySelector("#gc-cancel")!.addEventListener("click", () => this.cb.onCancelCreate());
  }

  private validateName(name: string): string | null {
    const trimmed = name.trim();
    if (!trimmed) return "Name is required.";
    if (trimmed.length < 3) return "Name must be at least 3 characters.";
    if (trimmed.length > 16) return "Name must be at most 16 characters.";
    if (!/^[A-Za-z0-9_\u4e00-\u9fff]+$/.test(trimmed)) {
      return "Name may contain only letters, digits, underscores or CJK characters.";
    }
    return null;
  }

  renderLoading(message: string): void {
    this.shell(
      "Entering the World",
      `
        <div class="game-loading">
          <div class="game-loading-spinner"></div>
          <div id="gl-message" class="game-note">${message}</div>
        </div>
      `,
      "",
    );
  }

  setLoadingMessage(message: string): void {
    const el = this.root.querySelector("#gl-message");
    if (el) el.textContent = message;
  }

  renderError(title: string, message: string, buttonText: string): void {
    this.shell(
      title,
      `<div class="game-note game-error-msg">${message}</div>`,
      `<button id="gs-ok" class="game-btn game-btn-primary">${buttonText}</button>`,
    );
    this.root.querySelector("#gs-ok")!.addEventListener("click", () => this.cb.onBack());
  }
}
