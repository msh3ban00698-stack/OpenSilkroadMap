import * as THREE from "three";
import { CharacterRig } from "./character_rig";
import { releaseRenderer } from "./gl_utils";

export interface PreviewAppearance {
  skin?: string | null;
  hair?: string | null;
  outfit?: string | null;
}

const SKIN_PARTS = [
  "man_pelvis",
  "man_torso_lower",
  "man_torso_upper",
  "man_arm_upper",
  "man_arm_lower",
  "man_thigh",
  "man_calf",
  "chinaman_fighter_face",
];
const HAIR_PARTS = ["chinaman_fighter_hair"];
const OUTFIT_PARTS = [
  "clothes_01_aa",
  "clothes_01_ba",
  "clothes_01_fa",
  "clothes_01_ha",
  "clothes_01_la",
  "clothes_01_sa",
];

export class CharacterPreview {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private rig: CharacterRig;
  private clock = new THREE.Clock();
  private raf = 0;
  private disposed = false;
  private loaded = false;
  private resizeObs: ResizeObserver | null = null;
  private pendingAppearance: PreviewAppearance | null = null;

  constructor(
    private container: HTMLElement,
    preset = "chinaman_fighter",
  ) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x000000, 0);
    const startW = Math.max(container.clientWidth, 1);
    const startH = Math.max(container.clientHeight, 1);
    this.renderer.setSize(startW, startH);
    this.renderer.domElement.style.display = "block";
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, startW / startH, 0.05, 60);

    const hemi = new THREE.HemisphereLight(0xcfd8ff, 0x3a2c20, 1.15);
    this.scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffe8c4, 2.2);
    key.position.set(-2.5, 6, -7);
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0x8898ff, 0.55);
    rim.position.set(5, 3, 4);
    this.scene.add(rim);

    this.scene.add(this.makeShadow());

    this.rig = new CharacterRig({ preset });
    this.scene.add(this.rig.group);

    this.loop();
    this.rig
      .load()
      .then(() => {
        if (this.disposed) return;
        this.loaded = true;
        this.rig.play("idle");
        this.rig.update(0);
        if (this.rig.skeleton) this.rig.skeleton.update();
        if (this.pendingAppearance) this.setAppearance(this.pendingAppearance);
        this.resize();
      })
      .catch((e) => console.error("preview load failed:", e));

    const bump = (): void => this.resize();
    requestAnimationFrame(() => {
      bump();
      requestAnimationFrame(bump);
    });
    this.resizeObs = new ResizeObserver(bump);
    this.resizeObs.observe(container);
    window.addEventListener("resize", this.onWindowResize);
  }

  private onWindowResize = (): void => {
    this.resize();
  };

  private frameRig(): void {
    const h = this.rig.height || 1.7;
    const target = new THREE.Vector3(0, h * 0.52, 0);
    const radius = h * 2.15;
    this.camera.position.set(target.x, target.y + radius * 0.16, target.z - radius);
    this.camera.near = Math.max(0.05, radius / 80);
    this.camera.far = Math.max(80, radius * 12);
    this.camera.lookAt(target);
    this.camera.updateProjectionMatrix();
  }

  private makeShadow(): THREE.Mesh {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext("2d")!;
    const grad = ctx.createRadialGradient(128, 128, 14, 128, 128, 124);
    grad.addColorStop(0, "rgba(0,0,0,0.55)");
    grad.addColorStop(0.65, "rgba(0,0,0,0.24)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 256, 256);
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(4.4, 4.4),
      new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthWrite: false }),
    );
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = 0.005;
    return mesh;
  }

  private loop = (): void => {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    const dt = Math.min(this.clock.getDelta(), 0.1);
    if (!this.loaded) return;
    this.rig.group.rotation.y += dt * 0.45;
    this.rig.update(dt);
    if (this.rig.skeleton) this.rig.skeleton.update();
    this.renderer.render(this.scene, this.camera);
  };

  setAppearance(app: PreviewAppearance): void {
    this.pendingAppearance = app;
    if (!this.loaded) return;
    const tintParts = (ids: string[], color: string | null | undefined): void => {
      for (const id of ids) this.rig.setPartTint(id, color ?? null);
    };
    tintParts(SKIN_PARTS, app.skin);
    tintParts(HAIR_PARTS, app.hair);
    tintParts(OUTFIT_PARTS, app.outfit);
  }

  resize(): void {
    if (this.disposed) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (w < 8 || h < 8) return;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    if (this.loaded) this.frameRig();
  }

  dispose(): void {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.resizeObs?.disconnect();
    this.resizeObs = null;
    window.removeEventListener("resize", this.onWindowResize);
    this.rig.dispose();
    releaseRenderer(this.renderer);
    if (this.renderer.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}
