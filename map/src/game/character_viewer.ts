import * as THREE from "three";
import { loadCharacter, type AnimData, type CharacterAssets, type MeshPartData } from "./character_loader";

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

  private assets: CharacterAssets | null = null;
  private skeleton: THREE.Skeleton | null = null;
  private group: THREE.Group = new THREE.Group();
  private meshes: THREE.SkinnedMesh[] = [];

  private yaw = Math.PI;
  private pitch = 0.28;
  private radius = 4.5;
  private target = new THREE.Vector3(0, 1.15, 0);
  private autoRotate = true;
  private rotating = false;
  private pointer = { x: 0, y: 0, down: false };
  private lastPointer = { x: 0, y: 0 };

  private anims: AnimData[] = [];
  private currentAnim: AnimData | null = null;
  private timeMs = 0;
  private playing = true;
  private speed = 1;
  private scale = 0.15;
  private height = 2.4;

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
    this.scene.add(this.group);

    this.bindInput();
    this.loop();
    this.load().catch((e) => {
      console.error(e);
      this.onError?.(e instanceof Error ? e.message : String(e));
    });

    (window as unknown as Record<string, unknown>).__charviewer = {
      getTime: () => this.timeMs,
      isPlaying: () => this.playing,
      animId: () => this.currentAnim?.id ?? null,
      getBoneWorld: (i: number) => {
        if (!this.skeleton) return null;
        const bone = this.skeleton.bones[i];
        const v = new THREE.Vector3();
        bone.getWorldPosition(v);
        return { x: v.x, y: v.y, z: v.z };
      },
      setPose: (t: number) => this.applyPose(t),
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
        this.group.getWorldPosition(p);
        return { x: p.x, y: p.y, z: p.z, s: this.group.scale.x };
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
    const hemi = new THREE.HemisphereLight(0xbdd0ff, 0x352818, 1.1);
    this.scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffe2b8, 2.0);
    key.position.set(4, 8, 3);
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0x8898ff, 0.8);
    rim.position.set(-5, 3, -4);
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
    this.assets = await loadCharacter(this.preset);
    this.scale = this.assets.meta.scale || 0.15;
    this.height = this.assets.meta.height * this.scale;
    this.anims = this.assets.anims;
    this.target.set(0, this.height * 0.48, 0);
    this.radius = this.height * 1.9;

    this.skeleton = this.buildSkeleton(this.assets);
    this.group.scale.setScalar(this.scale);

    for (const part of this.assets.meshes) {
      const mesh = this.buildMesh(part, this.assets);
      this.meshes.push(mesh);
    }

    if (this.anims.length > 0) {
      this.currentAnim = this.anims[0];
      this.applyPose(0);
    }

    this.onReady?.({
      preset: this.preset,
      name: this.assets.meta.name,
      height: this.height,
      anims: this.anims.map((a) => a.id),
    });
  }

  private buildSkeleton(assets: CharacterAssets): THREE.Skeleton {
    const names = assets.skeleton.names;
    const bones: THREE.Bone[] = names.map(() => new THREE.Bone());
    for (let i = 0; i < names.length; i++) {
      const bone = bones[i];
      bone.position.set(
        assets.skeleton.bindPos[i * 3],
        assets.skeleton.bindPos[i * 3 + 1],
        assets.skeleton.bindPos[i * 3 + 2],
      );
      bone.quaternion.set(
        assets.skeleton.bindRot[i * 4],
        assets.skeleton.bindRot[i * 4 + 1],
        assets.skeleton.bindRot[i * 4 + 2],
        assets.skeleton.bindRot[i * 4 + 3],
      );
      const parent = assets.skeleton.parents[i];
      if (parent >= 0) {
        bones[parent].add(bone);
      } else {
        this.group.add(bone);
      }
    }
    const skeleton = new THREE.Skeleton(bones);
    skeleton.calculateInverses();
    return skeleton;
  }

  private buildMesh(part: MeshPartData, assets: CharacterAssets): THREE.SkinnedMesh {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(part.pos, 3));
    geometry.setAttribute("normal", new THREE.Float32BufferAttribute(part.nrm, 3));
    geometry.setAttribute("uv", new THREE.Float32BufferAttribute(part.uv, 2));
    geometry.setAttribute("skinIndex", new THREE.Uint16BufferAttribute(part.sk, 4));
    geometry.setAttribute("skinWeight", new THREE.Float32BufferAttribute(part.sw, 4));
    geometry.setIndex(part.idx);

    const map = part.tex ? assets.textures.get(part.tex) : undefined;
    let material: THREE.MeshStandardMaterial;
    if (part.render === "alpha") {
      material = new THREE.MeshStandardMaterial({
        map,
        alphaTest: 0.5,
        roughness: 0.92,
        metalness: 0.05,
        side: THREE.DoubleSide,
      });
    } else if (part.render === "translucent") {
      material = new THREE.MeshStandardMaterial({
        map,
        transparent: true,
        roughness: 0.6,
        metalness: 0.2,
        side: THREE.DoubleSide,
      });
    } else {
      material = new THREE.MeshStandardMaterial({
        map,
        roughness: 0.92,
        metalness: 0.05,
      });
    }

    const mesh = new THREE.SkinnedMesh(geometry, material);
    if (this.skeleton) {
      mesh.bind(this.skeleton);
    }
    this.group.add(mesh);
    return mesh;
  }

  private loop = (): void => {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    const elapsed = Math.min(this.clock.getDelta(), 0.5);
    this.updateOrbit(elapsed);
    if (this.playing && this.currentAnim) {
      this.timeMs += elapsed * 1000 * this.speed;
      this.applyPose(this.timeMs);
    }
    if (this.skeleton) {
      this.skeleton.update();
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

  private applyPose(timeMs: number): void {
    const anim = this.currentAnim;
    if (!anim || !this.skeleton) return;
    const t = anim.loop ? timeMs % anim.dur : Math.min(timeMs, anim.dur);
    const times = anim.times;
    const last = times.length - 1;
    const bones = this.skeleton.bones;

    for (const b of anim.bones) {
      const bone = bones[b.i];
      const kfCount = b.pos.length / 3;
      if (kfCount === 0) continue;
      if (kfCount === 1 || t <= times[0]) {
        bone.position.set(b.pos[0], b.pos[1], b.pos[2]);
        bone.quaternion.set(b.rot[0], b.rot[1], b.rot[2], b.rot[3]);
        continue;
      }
      if (t >= times[last]) {
        const o = last * 3;
        const q = last * 4;
        bone.position.set(b.pos[o], b.pos[o + 1], b.pos[o + 2]);
        bone.quaternion.set(b.rot[q], b.rot[q + 1], b.rot[q + 2], b.rot[q + 3]);
        continue;
      }
      let i = 0;
      while (i < last && times[i + 1] < t) i++;
      const f = (t - times[i]) / (times[i + 1] - times[i]);
      const p0 = i * 3;
      const p1 = (i + 1) * 3;
      const q0 = i * 4;
      const q1 = (i + 1) * 4;
      const qa = new THREE.Quaternion(b.rot[q0], b.rot[q0 + 1], b.rot[q0 + 2], b.rot[q0 + 3]);
      const qb = new THREE.Quaternion(b.rot[q1], b.rot[q1 + 1], b.rot[q1 + 2], b.rot[q1 + 3]);
      const q = qa.slerp(qb, f);
      bone.quaternion.copy(q);
      bone.position.set(
        b.pos[p0] + (b.pos[p1] - b.pos[p0]) * f,
        b.pos[p0 + 1] + (b.pos[p1 + 1] - b.pos[p0 + 1]) * f,
        b.pos[p0 + 2] + (b.pos[p1 + 2] - b.pos[p0 + 2]) * f,
      );
    }
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
    const anim = this.anims.find((a) => a.id === id);
    if (!anim) return;
    this.currentAnim = anim;
    this.timeMs = 0;
  }

  getAnimations(): { id: string; name: string }[] {
    return this.anims.map((a) => ({ id: a.id, name: a.name }));
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
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}
