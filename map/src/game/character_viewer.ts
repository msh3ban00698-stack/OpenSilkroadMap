import * as THREE from "three";
import { CharacterRig } from "./character_rig";

export interface CharacterViewerOptions {
  container: HTMLElement;
  preset: string;
  onReady?: (info: { preset: string; name: string; height: number; anims: string[] }) => void;
  onError?: (message: string) => void;
}

export class CharacterViewer {
  private container: HTMLElement;
  private preset: string;
  private onReady?: CharacterViewerOptions["onReady"];
  private onError?: CharacterViewerOptions["onError"];

  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock = new THREE.Clock();
  private raf = 0;
  private disposed = false;

  private rig: CharacterRig;
  private height = 2.4;

  private yaw = Math.PI;
  private pitch = 0.28;
  private radius = 4.5;
  private target = new THREE.Vector3(0, 1.15, 0);
  private autoRotate = true;
  private rotating = false;
  private pointer = { x: 0, y: 0, down: false };
  private lastPointer = { x: 0, y: 0 };

  private playing = true;
  private speed = 1;

  constructor(opts: CharacterViewerOptions) {
    this.container = opts.container;
    this.preset = opts.preset;
    this.onReady = opts.onReady;
    this.onError = opts.onError;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(this.container.clientWidth || 360, this.container.clientHeight || 640);
    this.container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x14151c);

    this.camera = new THREE.PerspectiveCamera(
      42,
      (this.container.clientWidth || 360) / (this.container.clientHeight || 640),
      0.05,
      200,
    );

    this.addLights();
    this.addGround();

    this.rig = new CharacterRig({ preset: this.preset });
    this.scene.add(this.rig.group);

    this.bindInput();
    this.loop();
    this.load().catch((e) => {
      console.error(e);
      this.onError?.(e instanceof Error ? e.message : String(e));
    });

    (window as unknown as Record<string, unknown>).__charviewer = {
      getTime: () => this.rig.timeMs,
      isPlaying: () => this.playing,
      animId: () => this.rig.currentId,
      getBoneWorld: (i: number) => {
        const v = this.rig.getBoneWorld(i);
        return v ? { x: v.x, y: v.y, z: v.z } : null;
      },
      setPose: (t: number) => this.rig.applyPose(t),
      camPos: () => ({
        x: this.camera.position.x,
        y: this.camera.position.y,
        z: this.camera.position.z,
      }),
      target: () => ({ x: this.target.x, y: this.target.y, z: this.target.z }),
      yaw: () => this.yaw,
      project: (x: number, y: number, z: number) => {
        const v = new THREE.Vector3(x, y, z).project(this.camera);
        return { nx: v.x, ny: v.y, nz: v.z };
      },
      groupScale: () => {
        const p = new THREE.Vector3();
        this.rig.group.getWorldPosition(p);
        return { x: p.x, y: p.y, z: p.z, s: this.rig.group.scale.x };
      },
      resetView: () => {
        this.yaw = Math.PI;
        this.pitch = 0.28;
        this.radius = this.height * 1.9;
        this.autoRotate = false;
      },
    };
  }

  private addLights(): void {
    const hemi = new THREE.HemisphereLight(0xbdd0ff, 0x352818, 1.3);
    this.scene.add(hemi);
    // The model faces -Z and the camera orbits, so light both sides of the
    // character so the visible side is always well lit.
    const back = new THREE.DirectionalLight(0xffe2b8, 2.5);
    back.position.set(0, 7, -7);
    this.scene.add(back);
    const front = new THREE.DirectionalLight(0xffe2b8, 1.2);
    front.position.set(0, 5, 8);
    this.scene.add(front);
    const rim = new THREE.DirectionalLight(0x8898ff, 0.7);
    rim.position.set(-6, 3, 0);
    this.scene.add(rim);
  }

  private addGround(): void {
    const grid = new THREE.GridHelper(10, 20, 0x3a3f52, 0x262a38);
    grid.position.y = -0.01;
    this.scene.add(grid);

    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext("2d")!;
    const grad = ctx.createRadialGradient(128, 128, 16, 128, 128, 126);
    grad.addColorStop(0, "rgba(0,0,0,0.5)");
    grad.addColorStop(0.6, "rgba(0,0,0,0.22)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 256, 256);
    const tex = new THREE.CanvasTexture(canvas);
    const shadow = new THREE.Mesh(
      new THREE.PlaneGeometry(5, 5),
      new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }),
    );
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = 0.002;
    this.scene.add(shadow);
  }

  private async load(): Promise<void> {
    await this.rig.load();
    this.height = this.rig.height;
    this.target.set(0, this.height * 0.48, 0);
    this.radius = this.height * 1.9;

    this.onReady?.({
      preset: this.preset,
      name: this.rig.name,
      height: this.height,
      anims: this.rig.animations.map((a) => a.id),
    });
  }

  private loop = (): void => {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    const elapsed = Math.min(this.clock.getDelta(), 0.5);
    this.updateOrbit(elapsed);
    if (this.playing) {
      this.rig.setSpeed(this.speed);
      this.rig.update(elapsed);
    }
    if (this.rig.skeleton) {
      this.rig.skeleton.update();
    }
    this.renderer.render(this.scene, this.camera);
  };

  private updateOrbit(dt: number): void {
    if (this.autoRotate && !this.rotating) {
      this.yaw += dt * 0.12;
    }
    const cp = Math.cos(this.pitch);
    const sp = Math.sin(this.pitch);
    this.camera.position.set(
      this.target.x + this.radius * cp * Math.sin(this.yaw),
      this.target.y + this.radius * sp,
      this.target.z + this.radius * cp * Math.cos(this.yaw),
    );
    this.camera.lookAt(this.target);
  }

  private bindInput(): void {
    const el = this.renderer.domElement;
    el.addEventListener("pointerdown", (e) => {
      this.rotating = true;
      this.pointer.down = true;
      this.pointer.x = e.clientX;
      this.pointer.y = e.clientY;
      this.lastPointer.x = e.clientX;
      this.lastPointer.y = e.clientY;
    });
    window.addEventListener("pointermove", (e) => {
      if (!this.pointer.down) return;
      const dx = e.clientX - this.lastPointer.x;
      const dy = e.clientY - this.lastPointer.y;
      this.lastPointer.x = e.clientX;
      this.lastPointer.y = e.clientY;
      this.yaw -= dx * 0.008;
      this.pitch = Math.max(0.05, Math.min(1.35, this.pitch + dy * 0.006));
    });
    window.addEventListener("pointerup", () => {
      this.pointer.down = false;
      this.rotating = false;
    });
    el.addEventListener("wheel", (e) => {
      e.preventDefault();
      this.radius *= 1 + Math.sign(e.deltaY) * 0.09;
      this.radius = Math.max(this.height * 0.6, Math.min(this.height * 6, this.radius));
    });
  }

  setAnimation(id: string): void {
    this.rig.play(id);
  }

  getAnimations(): { id: string; name: string }[] {
    return this.rig.animations;
  }

  getHeight(): number {
    return this.height;
  }

  setPlaying(playing: boolean): void {
    this.playing = playing;
  }

  isPlaying(): boolean {
    return this.playing;
  }

  setSpeed(speed: number): void {
    this.speed = Math.max(0.1, Math.min(4, speed));
  }

  setAutoRotate(auto: boolean): void {
    this.autoRotate = auto;
  }

  resize(): void {
    const w = this.container.clientWidth || 360;
    const h = this.container.clientHeight || 640;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  dispose(): void {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.rig.dispose();
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}
