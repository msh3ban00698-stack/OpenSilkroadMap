export interface ControlsOptions {
  container: HTMLElement;
  joystickBase: HTMLElement;
  joystickKnob: HTMLElement;
  onMove: (x: number, z: number) => void;
  onRotate: (dx: number, dy: number) => void;
  onSelect?: (clientX: number, clientY: number) => void;
}

const JOY_RADIUS = 42;
const TAP_MAX_MOVE = 6;
const INTERACTIVE_SELECTOR = ".game-btn, .hud-btn, .sro-btn, .sro-window, #joy-base, #joy-knob";

export class TouchControls {
  private opts: ControlsOptions;
  private joyPointer: number | null = null;
  private camPointer: number | null = null;
  private lastCamX = 0;
  private lastCamY = 0;
  private tapStartX = 0;
  private tapStartY = 0;
  private tapMoved = false;
  private joyCenter = { x: 0, y: 0 };
  private keys = new Set<string>();

  private joyPointerDown = (e: PointerEvent): void => {
    if (this.joyPointer !== null) return;
    this.joyPointer = e.pointerId;
    this.opts.joystickBase.setPointerCapture(e.pointerId);
    const r = this.opts.joystickBase.getBoundingClientRect();
    this.joyCenter = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    e.preventDefault();
  };

  private joyPointerMove = (e: PointerEvent): void => {
    if (e.pointerId !== this.joyPointer) return;
    const dx = e.clientX - this.joyCenter.x;
    const dy = e.clientY - this.joyCenter.y;
    const len = Math.hypot(dx, dy);
    const clamped = Math.min(len, JOY_RADIUS);
    const nx = len > 0 ? (dx / len) * clamped : 0;
    const ny = len > 0 ? (dy / len) * clamped : 0;
    this.opts.joystickKnob.style.transform = `translate(${nx}px, ${ny}px)`;
    // Screen-up = forward (z+); screen-left = strafe left (x-).
    this.opts.onMove(nx / JOY_RADIUS, -ny / JOY_RADIUS);
  };

  private joyPointerUp = (e: PointerEvent): void => {
    if (e.pointerId !== this.joyPointer) return;
    this.joyPointer = null;
    this.opts.joystickKnob.style.transform = "translate(0px, 0px)";
    this.opts.onMove(0, 0);
  };

  private onPointerDown = (e: PointerEvent): void => {
    const target = e.target as HTMLElement | null;
    const isInteractive = !!target && !!target.closest(INTERACTIVE_SELECTOR);
    if (this.camPointer === null && !isInteractive) {
      // Start a potential tap / camera drag anywhere that isn't a joystick or
      // button. A short press selects a world target; a drag orbits the camera.
      this.camPointer = e.pointerId;
      this.lastCamX = e.clientX;
      this.lastCamY = e.clientY;
      this.tapStartX = e.clientX;
      this.tapStartY = e.clientY;
      this.tapMoved = false;
      this.container.setPointerCapture(e.pointerId);
    }
  };

  private onPointerMove = (e: PointerEvent): void => {
    if (e.pointerId !== this.camPointer) return;
    const dx = e.clientX - this.lastCamX;
    const dy = e.clientY - this.lastCamY;
    this.lastCamX = e.clientX;
    this.lastCamY = e.clientY;
    if (!this.tapMoved) {
      const total = Math.hypot(e.clientX - this.tapStartX, e.clientY - this.tapStartY);
      if (total > TAP_MAX_MOVE) this.tapMoved = true;
    }
    if (this.tapMoved) {
      this.opts.onRotate(dx, dy);
    }
  };

  private onPointerUp = (e: PointerEvent): void => {
    if (e.pointerId !== this.camPointer) return;
    this.camPointer = null;
    if (!this.tapMoved && this.opts.onSelect) {
      this.opts.onSelect(e.clientX, e.clientY);
    }
  };

  private onKeyDown = (e: KeyboardEvent): void => {
    this.keys.add(e.key.toLowerCase());
    this.pushKeys();
  };

  private onKeyUp = (e: KeyboardEvent): void => {
    this.keys.delete(e.key.toLowerCase());
    this.pushKeys();
  };

  private pushKeys(): void {
    let x = 0;
    let z = 0;
    if (this.keys.has("w") || this.keys.has("arrowup")) z += 1;
    if (this.keys.has("s") || this.keys.has("arrowdown")) z -= 1;
    if (this.keys.has("a") || this.keys.has("arrowleft")) x -= 1;
    if (this.keys.has("d") || this.keys.has("arrowright")) x += 1;
    this.opts.onMove(x, z);
  }

  private container: HTMLElement;

  constructor(opts: ControlsOptions) {
    this.opts = opts;
    this.container = opts.container;

    const joyRect = opts.joystickBase.getBoundingClientRect();
    this.joyCenter = { x: joyRect.left + joyRect.width / 2, y: joyRect.top + joyRect.height / 2 };

    opts.joystickBase.addEventListener("pointerdown", this.joyPointerDown);
    opts.joystickBase.addEventListener("pointermove", this.joyPointerMove);
    opts.joystickBase.addEventListener("pointerup", this.joyPointerUp);
    opts.joystickBase.addEventListener("pointercancel", this.joyPointerUp);

    this.container.addEventListener("pointerdown", this.onPointerDown);
    this.container.addEventListener("pointermove", this.onPointerMove);
    this.container.addEventListener("pointerup", this.onPointerUp);
    this.container.addEventListener("pointercancel", this.onPointerUp);
    window.addEventListener("keydown", this.onKeyDown);
    window.addEventListener("keyup", this.onKeyUp);
  }

  dispose(): void {
    this.opts.joystickBase.removeEventListener("pointerdown", this.joyPointerDown);
    this.opts.joystickBase.removeEventListener("pointermove", this.joyPointerMove);
    this.opts.joystickBase.removeEventListener("pointerup", this.joyPointerUp);
    this.opts.joystickBase.removeEventListener("pointercancel", this.joyPointerUp);
    this.container.removeEventListener("pointerdown", this.onPointerDown);
    this.container.removeEventListener("pointermove", this.onPointerMove);
    this.container.removeEventListener("pointerup", this.onPointerUp);
    this.container.removeEventListener("pointercancel", this.onPointerUp);
    window.removeEventListener("keydown", this.onKeyDown);
    window.removeEventListener("keyup", this.onKeyUp);
  }
}
