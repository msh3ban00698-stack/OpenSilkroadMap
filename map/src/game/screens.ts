import { VERIFIED_CLASSES, getClass, STARTER_KITS } from "./game_data";
import type { GameCharacter } from "./types";
import { CharacterPreview } from "./character_preview";

export interface ScreensCallbacks {
  onBack: () => void;
  onLogin: (username: string, password: string) => void;
  onOpenAccountCreate: () => void;
  onCreateAccount: (username: string, password: string) => void;
  onCancelAccount: () => void;
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

const RACES = ["Chinese", "European"];
const SKIN_TONES = ["#f5d0a9", "#e0ac69", "#c68642", "#8d5524"];
const HAIR_COLORS = ["#1a1a1a", "#3b2f2f", "#6b4226", "#d4a437"];
const OUTFIT_COLORS = ["#8b0000", "#1f4e79", "#3a6b35", "#5b3a8c", "#7a5c2e"];

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export class GameScreens {
  private root: HTMLElement;
  private cb: ScreensCallbacks;
  private preview: CharacterPreview | null = null;

  constructor(root: HTMLElement, cb: ScreensCallbacks) {
    this.root = root;
    this.cb = cb;
  }

  private clear(): void {
    if (this.preview) {
      this.preview.dispose();
      this.preview = null;
    }
    this.root.innerHTML = "";
  }

  private mountPreview(
    hostId: string,
    appearance?: { skinTone?: string | null; hairColor?: string | null; outfitColor?: string | null },
  ): void {
    const host = this.root.querySelector(`#${hostId}`) as HTMLElement | null;
    if (!host) return;
    this.preview = new CharacterPreview(host);
    if (appearance) {
      setTimeout(() => {
        this.preview?.setAppearance({
          skin: appearance.skinTone,
          hair: appearance.hairColor,
          outfit: appearance.outfitColor,
        });
      }, 400);
    }
  }

  private bg(layer: string): string {
    return `<div class="sro-bg ${layer}"></div>`;
  }

  renderLogin(error?: string): void {
    this.clear();
    this.root.innerHTML = `
      <div class="sro-screen sro-login">
        ${this.bg("bg-login")}
        <div class="sro-logo">SILKROAD</div>
        <div class="sro-window sro-login-panel">
          <div class="sro-window-title">Log In</div>
          <div class="sro-field">
            <label>Username</label>
            <input id="gl-user" class="sro-input" type="text" maxlength="20" placeholder="Your account username" autocomplete="off" />
          </div>
          <div class="sro-field">
            <label>Password</label>
            <input id="gl-pass" class="sro-input" type="password" maxlength="64" placeholder="Your password" autocomplete="off" />
          </div>
          <div id="gl-error" class="sro-error">${error ? escapeHtml(error) : ""}</div>
          <button id="gl-submit" class="sro-btn sro-btn-primary">Log In</button>
          <button id="gs-register" class="sro-btn sro-btn-secondary">Create Account</button>
        </div>
      </div>
    `;
    const user = this.root.querySelector("#gl-user") as HTMLInputElement;
    const pass = this.root.querySelector("#gl-pass") as HTMLInputElement;
    const errEl = this.root.querySelector("#gl-error") as HTMLElement;
    const submit = (): void => {
      const err = this.validateCredentials(user.value, pass.value);
      if (err) {
        errEl.textContent = err;
        return;
      }
      this.cb.onLogin(user.value.trim(), pass.value);
    };
    this.root.querySelector("#gl-submit")!.addEventListener("click", submit);
    pass.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submit();
    });
    user.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submit();
    });
    this.root.querySelector("#gs-register")!.addEventListener("click", () => this.cb.onOpenAccountCreate());
  }

  renderCreateAccount(error?: string): void {
    this.clear();
    this.root.innerHTML = `
      <div class="sro-screen">
        ${this.bg("bg-login")}
        <div class="sro-logo sro-logo-sm">SILKROAD</div>
        <div class="sro-window sro-center-panel">
          <div class="sro-window-title">Create Account</div>
          <div class="sro-field">
            <label>Username</label>
            <input id="ga-user" class="sro-input" type="text" maxlength="20" placeholder="3-20 letters/digits/_" autocomplete="off" />
          </div>
          <div class="sro-field">
            <label>Password</label>
            <input id="ga-pass" class="sro-input" type="password" maxlength="64" placeholder="At least 4 characters" autocomplete="off" />
          </div>
          <div class="sro-field">
            <label>Confirm Password</label>
            <input id="ga-pass2" class="sro-input" type="password" maxlength="64" placeholder="Repeat password" autocomplete="off" />
          </div>
          <div id="ga-error" class="sro-error">${error ? escapeHtml(error) : ""}</div>
          <button id="ga-submit" class="sro-btn sro-btn-primary">Create Account</button>
          <button id="ga-back" class="sro-btn sro-btn-secondary">Back</button>
        </div>
      </div>
    `;
    const user = this.root.querySelector("#ga-user") as HTMLInputElement;
    const pass = this.root.querySelector("#ga-pass") as HTMLInputElement;
    const pass2 = this.root.querySelector("#ga-pass2") as HTMLInputElement;
    const errEl = this.root.querySelector("#ga-error") as HTMLElement;
    this.root.querySelector("#ga-submit")!.addEventListener("click", () => {
      const err = this.validateCredentials(user.value, pass.value);
      if (err) {
        errEl.textContent = err;
        return;
      }
      if (pass.value !== pass2.value) {
        errEl.textContent = "Passwords do not match.";
        return;
      }
      this.cb.onCreateAccount(user.value.trim(), pass.value);
    });
    this.root.querySelector("#ga-back")!.addEventListener("click", () => this.cb.onCancelAccount());
  }

  private validateCredentials(user: string, pass: string): string | null {
    if (!user.trim()) return "Username is required.";
    if (!pass) return "Password is required.";
    return null;
  }

  renderSelect(characters: GameCharacter[]): void {
    this.clear();
    let selected = characters.length > 0 ? characters[0].id : null;

    const items = characters
      .map((c) => {
        const cls = getClass(c.classId);
        return `
          <div class="sro-char${c.id === selected ? " active" : ""}" data-id="${c.id}">
            <img class="sro-char-face" src="assets/img/silkroad/ui/hud_face.png" alt="" />
            <div class="sro-char-info">
              <div class="game-char-name">${escapeHtml(c.name)}</div>
              <div class="sro-char-meta">Lv.${c.level} · ${cls ? escapeHtml(cls.name) : escapeHtml(c.classId)}</div>
            </div>
            <button class="sro-iconbtn" data-del="${c.id}" title="Delete">✕</button>
          </div>
        `;
      })
      .join("");

    this.root.innerHTML = `
      <div class="sro-screen sro-select">
        ${this.bg("bg-select")}
        <div class="sro-logo sro-logo-sm">SILKROAD</div>
        <div class="sro-split">
          <div class="sro-window sro-list-panel">
            <div class="sro-window-title">Select Character</div>
            <div class="sro-char-list">
              ${
                characters.length === 0
                  ? `<div class="sro-empty">No characters yet.<br>Create your first adventurer.</div>`
                  : items
              }
            </div>
            <button id="gs-new" class="sro-btn sro-btn-secondary">Create New Character</button>
            <button id="gs-enter" class="sro-btn sro-btn-primary"${selected ? ` data-enter="${selected}"` : " disabled"}>Enter World</button>
          </div>
          <div class="sro-preview-panel">
            <div id="select-preview" class="sro-preview"></div>
          </div>
        </div>
      </div>
    `;
    this.mountPreview("select-preview", characters.find((c) => c.id === selected)?.appearance);

    const syncSelection = (id: string): void => {
      selected = id;
      this.root.querySelectorAll(".sro-char").forEach((el) => {
        el.classList.toggle("active", (el as HTMLElement).dataset.id === id);
      });
      const enterBtn = this.root.querySelector("#gs-enter") as HTMLButtonElement;
      enterBtn.disabled = false;
      enterBtn.dataset.enter = id;
      const app = characters.find((ch) => ch.id === id)?.appearance;
      this.preview?.setAppearance({ skin: app?.skinTone, hair: app?.hairColor, outfit: app?.outfitColor });
    };

    this.root.querySelectorAll(".sro-char").forEach((el) => {
      el.addEventListener("click", () => syncSelection((el as HTMLElement).dataset.id!));
    });
    this.root.querySelectorAll("[data-del]").forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const id = (el as HTMLElement).dataset.del!;
        const char = characters.find((c) => c.id === id);
        if (confirm(`Delete character "${char ? char.name : id}"? This cannot be undone.`)) {
          this.cb.onDeleteCharacter(id);
        }
      });
    });
    this.root.querySelector("#gs-enter")!.addEventListener("click", (ev) => {
      const id = (ev.currentTarget as HTMLElement).dataset.enter;
      if (id) this.cb.onSelectCharacter(id);
    });
    this.root.querySelector("#gs-new")!.addEventListener("click", () => this.cb.onCreateNew());
  }

  renderCreate(): void {
    this.clear();
    const raceOptions = RACES.map((r) => `<button class="sro-seg" data-race="${r}">${r}</button>`).join("");
    const classFor = (race: string) =>
      VERIFIED_CLASSES.filter((c) => c.race === race)
        .map(
          (c) => `
            <button class="sro-option" data-class="${c.id}">
              <span class="sro-option-name">${escapeHtml(c.name)}</span>
              <span class="sro-option-desc">${escapeHtml(c.desc)}</span>
            </button>
          `,
        )
        .join("");

    const colorRow = (attr: string, colors: string[]) =>
      colors
        .map((c, i) => `<button class="sro-color" style="--c:${c}" data-${attr}="${c}" data-i="${i}"></button>`)
        .join("");
    const kitOptions = STARTER_KITS.map(
      (k) => `
        <button class="sro-option" data-kit="${k.id}">
          <span class="sro-option-name">${escapeHtml(k.name)}</span>
          <span class="sro-option-desc">${escapeHtml(k.desc)}</span>
        </button>
      `,
    ).join("");

    this.root.innerHTML = `
      <div class="sro-screen sro-create">
        ${this.bg("bg-create")}
        <div class="sro-split sro-split-create">
          <div class="sro-window sro-form-panel">
            <div class="sro-window-title">Create Character</div>
            <div class="sro-form-scroll">
              <div class="sro-field">
                <label>Character Name</label>
                <input id="gc-name" class="sro-input" type="text" maxlength="16" placeholder="3-16 letters/digits" autocomplete="off" />
                <div id="gc-name-error" class="sro-error"></div>
              </div>
              <div class="sro-field">
                <label>Race</label>
                <div class="sro-row">${raceOptions}</div>
              </div>
              <div class="sro-field">
                <label>Class</label>
                <div id="gc-class-grid" class="sro-options">${classFor(RACES[0])}</div>
              </div>
              <div class="sro-field">
                <label>Starter Kit</label>
                <div class="sro-options">${kitOptions}</div>
              </div>
              <div class="sro-field">
                <label>Gender</label>
                <div class="sro-row">
                  <button class="sro-seg sro-gender active" data-gender="male">Male</button>
                  <button class="sro-seg sro-gender" data-gender="female">Female</button>
                </div>
              </div>
              <div class="sro-field"><label>Skin Tone</label><div class="sro-row">${colorRow("skin", SKIN_TONES)}</div></div>
              <div class="sro-field"><label>Hair Color</label><div class="sro-row">${colorRow("hair", HAIR_COLORS)}</div></div>
              <div class="sro-field"><label>Outfit Color</label><div class="sro-row">${colorRow("outfit", OUTFIT_COLORS)}</div></div>
            </div>
          </div>
          <div class="sro-preview-col">
            <div class="sro-preview-panel sro-preview-tall">
              <div id="create-preview" class="sro-preview"></div>
            </div>
            <div class="sro-create-actions">
              <button id="gc-cancel" class="sro-btn sro-btn-secondary">Back</button>
              <button id="gc-confirm" class="sro-btn sro-btn-primary">Confirm</button>
            </div>
          </div>
        </div>
      </div>
    `;
    this.mountPreview("create-preview", {
      skinTone: SKIN_TONES[0],
      hairColor: HAIR_COLORS[0],
      outfitColor: OUTFIT_COLORS[0],
    });

    const nameInput = this.root.querySelector("#gc-name") as HTMLInputElement;
    const errorEl = this.root.querySelector("#gc-name-error") as HTMLElement;
    let race = RACES[0];
    let classId = VERIFIED_CLASSES[0].id;
    let kit = STARTER_KITS[0].id;
    let gender: "male" | "female" = "male";
    let skinTone = SKIN_TONES[0];
    let hairColor = HAIR_COLORS[0];
    let outfitColor = OUTFIT_COLORS[0];

    const pushAppearance = (): void => {
      this.preview?.setAppearance({ skin: skinTone, hair: hairColor, outfit: outfitColor });
    };

    const classGrid = this.root.querySelector("#gc-class-grid") as HTMLElement;
    const markClass = (id: string) => {
      this.root.querySelectorAll("[data-class]").forEach((el) => {
        el.classList.toggle("active", (el as HTMLElement).dataset.class === id);
      });
    };
    const setRace = (r: string) => {
      race = r;
      this.root.querySelectorAll("[data-race]").forEach((el) => {
        el.classList.toggle("active", (el as HTMLElement).dataset.race === r);
      });
      classGrid.innerHTML = classFor(r);
      classId = VERIFIED_CLASSES.find((c) => c.race === r)!.id;
      markClass(classId);
      classGrid.querySelectorAll("[data-class]").forEach((el) => {
        el.addEventListener("click", () => {
          classId = (el as HTMLElement).dataset.class!;
          markClass(classId);
        });
      });
    };
    const bindGroup = (selector: string, set: (v: string) => void) => {
      this.root.querySelectorAll(selector).forEach((el) => {
        el.addEventListener("click", () => {
          const v =
            (el as HTMLElement).dataset.skin ||
            (el as HTMLElement).dataset.hair ||
            (el as HTMLElement).dataset.outfit ||
            (el as HTMLElement).dataset.kit!;
          set(v);
        });
      });
    };
    setRace(race);
    this.root.querySelectorAll('[data-kit="' + kit + '"]').forEach((el) => el.classList.add("active"));
    this.root.querySelectorAll("[data-race]").forEach((el) => {
      el.addEventListener("click", () => setRace((el as HTMLElement).dataset.race!));
    });
    bindGroup("[data-kit]", (v) => {
      kit = v;
      this.root
        .querySelectorAll("[data-kit]")
        .forEach((b) => b.classList.toggle("active", (b as HTMLElement).dataset.kit === v));
    });
    this.root.querySelectorAll(".sro-gender").forEach((el) => {
      el.addEventListener("click", () => {
        gender = (el as HTMLElement).dataset.gender as "male" | "female";
        this.root.querySelectorAll(".sro-gender").forEach((b) => b.classList.toggle("active", b === el));
      });
    });
    const bindColor = (selector: string, set: (v: string) => void) => {
      this.root.querySelectorAll(selector).forEach((el) => {
        el.addEventListener("click", () => {
          set((el as HTMLElement).dataset.i!);
          this.root.querySelectorAll(selector).forEach((b) => b.classList.toggle("active", b === el));
          pushAppearance();
        });
      });
    };
    bindColor("[data-skin]", (i) => (skinTone = SKIN_TONES[Number(i)]));
    bindColor("[data-hair]", (i) => (hairColor = HAIR_COLORS[Number(i)]));
    bindColor("[data-outfit]", (i) => (outfitColor = OUTFIT_COLORS[Number(i)]));

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
    this.clear();
    this.root.innerHTML = `
      <div class="sro-screen sro-loading">
        ${this.bg("bg-loading")}
        <div class="sro-loading-bottom">
          <div id="gl-message" class="sro-loading-text">${escapeHtml(message)}</div>
          <div class="sro-loading-bar"><div class="sro-loading-fill"></div></div>
        </div>
      </div>
    `;
  }

  setLoadingMessage(message: string): void {
    const el = this.root.querySelector("#gl-message");
    if (el) el.textContent = message;
  }

  renderError(title: string, message: string, buttonText: string): void {
    this.clear();
    this.root.innerHTML = `
      <div class="sro-screen">
        ${this.bg("bg-login")}
        <div class="sro-window sro-center-panel">
          <div class="sro-window-title">${escapeHtml(title)}</div>
          <div class="sro-note sro-error-msg">${escapeHtml(message)}</div>
          <button id="gs-ok" class="sro-btn sro-btn-primary">${escapeHtml(buttonText)}</button>
        </div>
      </div>
    `;
    this.root.querySelector("#gs-ok")!.addEventListener("click", () => this.cb.onBack());
  }
}
