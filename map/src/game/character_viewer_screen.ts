import { CharacterViewer } from "./character_viewer";

export interface CharacterViewerScreenOptions {
  root: HTMLElement;
  onBack: () => void;
}

const PRESET = "chinaman_fighter";

export class CharacterViewerScreen {
  private root: HTMLElement;
  private onBack: () => void;
  private viewer: CharacterViewer | null = null;

  constructor(opts: CharacterViewerScreenOptions) {
    this.root = opts.root;
    this.onBack = opts.onBack;
  }

  show(): void {
    this.root.style.display = "block";
    this.root.innerHTML = `
      <div class="cv-root">
        <div class="cv-canvas"></div>
        <div class="cv-bar">
          <div class="cv-head">
            <div>
              <div class="cv-title">Character Viewer</div>
              <div class="cv-subtitle" id="cv-meta">Loading ${PRESET}...</div>
            </div>
            <button id="cv-back" class="game-btn game-btn-ghost">Back</button>
          </div>
          <div class="cv-anims" id="cv-anims"></div>
          <div class="cv-controls">
            <button id="cv-play" class="game-btn game-btn-primary game-btn-sm">Pause</button>
            <label class="cv-label">Speed
              <input id="cv-speed" type="range" min="0.1" max="4" step="0.1" value="1" />
              <span id="cv-speed-val">1.0x</span>
            </label>
            <label class="cv-label cv-check">
              <input id="cv-rotate" type="checkbox" checked /> Auto-rotate
            </label>
          </div>
          <div class="cv-note">Real skeleton, mesh and animation data from Data.pk2 (BSK/BMS/BAN).
            Drag to orbit · Scroll to zoom.</div>
        </div>
      </div>
    `;

    const canvasEl = this.root.querySelector<HTMLElement>(".cv-canvas")!;
    this.viewer = new CharacterViewer({
      container: canvasEl,
      preset: PRESET,
      onReady: (info) => {
        this.buildAnimButtons(info.anims);
        const meta = document.getElementById("cv-meta");
        if (meta) meta.textContent = `${info.name} · ${info.height.toFixed(2)} m`;
      },
      onError: (msg) => {
        const meta = document.getElementById("cv-meta");
        if (meta) meta.textContent = `Failed to load character: ${msg}`;
      },
    });

    this.root.querySelector("#cv-back")!.addEventListener("click", () => this.onBack());
    this.root.querySelector("#cv-play")!.addEventListener("click", () => {
      if (!this.viewer) return;
      const playing = this.viewer.isPlaying();
      this.viewer.setPlaying(!playing);
      const btn = this.root.querySelector<HTMLButtonElement>("#cv-play");
      if (btn) btn.textContent = playing ? "Play" : "Pause";
    });
    const speed = this.root.querySelector<HTMLInputElement>("#cv-speed")!;
    speed.addEventListener("input", () => {
      const v = parseFloat(speed.value);
      this.viewer?.setSpeed(v);
      const label = this.root.querySelector("#cv-speed-val");
      if (label) label.textContent = `${v.toFixed(1)}x`;
    });
    const rotate = this.root.querySelector<HTMLInputElement>("#cv-rotate")!;
    rotate.addEventListener("change", () => this.viewer?.setAutoRotate(rotate.checked));

    requestAnimationFrame(() => this.viewer?.resize());
    window.addEventListener("resize", this.onResize);
  }

  private buildAnimButtons(animIds: string[]): void {
    if (!this.viewer) return;
    const wrap = this.root.querySelector<HTMLElement>("#cv-anims");
    if (!wrap) return;
    const anims = this.viewer.getAnimations();
    const labels = new Map(anims.map((a) => [a.id, a.name]));
    wrap.innerHTML = animIds
      .map(
        (id, i) => `
          <button class="cv-anim-btn ${i === 0 ? "active" : ""}" data-anim="${id}">
            ${labels.get(id) ?? id}
          </button>`,
      )
      .join("");
    wrap.querySelectorAll(".cv-anim-btn").forEach((el) => {
      el.addEventListener("click", () => {
        const id = (el as HTMLElement).dataset.anim!;
        this.viewer?.setAnimation(id);
        wrap.querySelectorAll(".cv-anim-btn").forEach((b) => b.classList.toggle("active", b === el));
      });
    });
  }

  private onResize = (): void => {
    this.viewer?.resize();
  };

  hide(): void {
    window.removeEventListener("resize", this.onResize);
    this.viewer?.dispose();
    this.viewer = null;
    this.root.style.display = "none";
    this.root.innerHTML = "";
  }
}
