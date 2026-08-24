import * as THREE from "three";
import type { GameCharacter } from "./types";
import { getClass, REGION_NPCS } from "./game_data";
import type { RegionAssets } from "./region_loader";

export interface GameWorldOptions {
  container: HTMLElement;
  character: GameCharacter;
  assets: RegionAssets;
  onLog: (msg: string) => void;
}

const WALK_SPEED = 70;
const CAM_DIST = 14;
const CAM_MIN_PITCH = 0.12;
const CAM_MAX_PITCH = 1.15;

export class GameWorld {
  private container: HTMLElement;
  private character: GameCharacter;
  private assets: RegionAssets;
  private onLog: (msg: string) => void;

  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock: THREE.Clock;
  private raf = 0;
  private disposed = false;

  private player: THREE.Group;
  private legL!: THREE.Object3D;
  private legR!: THREE.Object3D;
  private armL!: THREE.Object3D;
  private armR!: THREE.Object3D;
  private npcGroups: { group: THREE.Group; name: string; x: number; z: number }[] = [];

  private yaw = 0.5;
  private pitch = 0.32;
  private move = { x: 0, z: 0 };
  private moving = false;
  private walkPhase = 0;
  private attacking = false;
  private attackT = 0;

  constructor(opts: GameWorldOptions) {
    this.container = opts.container;
    this.character = opts.character;
    this.assets = opts.assets;
    this.onLog = opts.onLog;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(this.container.clientWidth || 360, this.container.clientHeight || 640);
    this.container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0b10);
    this.scene.fog = new THREE.Fog(0x1a1620, 140, 360);

    this.camera = new THREE.PerspectiveCamera(
      62,
      (this.container.clientWidth || 360) / (this.container.clientHeight || 640),
      0.1,
      800,
    );

    this.addLights();
    this.addFloor();
    this.addBounds();
    this.addNpcs();

    this.player = this.buildPlayer();
    const spawn = this.assets.spawn;
    this.player.position.set(spawn.x, spawn.y, spawn.z);

    const playerLight = new THREE.PointLight(0xffd9a0, 30, 42, 2);
    playerLight.position.set(0, 8, 0);
    this.player.add(playerLight);

    this.scene.add(this.player);

    this.targetYaw = this.yaw;
    this.clock = new THREE.Clock();
    this.loop();

    // Debug hook used by the headless validation harness.
    (window as unknown as Record<string, unknown>).__sro3d = {
      getPlayerPos: () => ({ x: this.player.position.x, y: this.player.position.y, z: this.player.position.z }),
      getCameraPos: () => ({ x: this.camera.position.x, y: this.camera.position.y, z: this.camera.position.z }),
      yaw: () => this.yaw,
      pitch: () => this.pitch,
    };
  }

  private targetYaw: number;

  private addLights(): void {
    const hemi = new THREE.HemisphereLight(0xbfd0ff, 0x302418, 0.9);
    this.scene.add(hemi);
    const dir = new THREE.DirectionalLight(0xffe8c8, 1.1);
    dir.position.set(60, 120, 40);
    this.scene.add(dir);
    const fill = new THREE.DirectionalLight(0x8890ff, 0.35);
    fill.position.set(-60, 40, -80);
    this.scene.add(fill);
  }

  private addFloor(): void {
    const material = new THREE.MeshLambertMaterial({
      map: this.assets.texture,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(this.assets.floorGeometry, material);
    this.scene.add(mesh);
  }

  private addBounds(): void {
    const b = this.assets.data.bounds;
    const cx = (b.minX + b.maxX) / 2;
    const cz = (b.minZ + b.maxZ) / 2;
    const w = b.maxX - b.minX;
    const h = b.maxZ - b.minZ;
    const geo = new THREE.BoxGeometry(w, 1, h);
    const mat = new THREE.MeshBasicMaterial({ color: 0x1a2230, transparent: true, opacity: 0.0 });
    const box = new THREE.Mesh(geo, mat);
    box.position.set(cx, -0.6, cz);
    this.scene.add(box);
    this.boundsBox = { minX: b.minX, maxX: b.maxX, minZ: b.minZ, maxZ: b.maxZ };
  }

  private boundsBox!: { minX: number; maxX: number; minZ: number; maxZ: number };

  private addNpcs(): void {
    for (const npc of REGION_NPCS) {
      const group = this.buildNpc(npc.name);
      group.position.set(npc.x, 0, npc.z);
      this.scene.add(group);
      this.npcGroups.push({ group, name: npc.name, x: npc.x, z: npc.z });
    }
  }

  private buildPlayer(): THREE.Group {
    const a = this.character.appearance;
    const group = new THREE.Group();

    const outfit = new THREE.MeshLambertMaterial({ color: new THREE.Color(a.outfitColor) });
    const skin = new THREE.MeshLambertMaterial({ color: new THREE.Color(a.skinTone) });
    const hair = new THREE.MeshLambertMaterial({ color: new THREE.Color(a.hairColor) });

    const torso = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.78, 0.36), outfit);
    torso.position.y = 1.22;
    group.add(torso);

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 16, 12), skin);
    head.position.y = 1.82;
    group.add(head);

    const hairCap = new THREE.Mesh(new THREE.SphereGeometry(0.245, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.5), hair);
    hairCap.position.y = 1.82;
    group.add(hairCap);

    const mk = (w: number, h: number, d: number, mat: THREE.Material, y: number, x: number) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
      m.position.set(x, y, 0);
      group.add(m);
      return m;
    };

    const legL = mk(0.24, 0.62, 0.24, outfit, 0.31, -0.15);
    const legR = mk(0.24, 0.62, 0.24, outfit, 0.31, 0.15);
    const armL = mk(0.17, 0.6, 0.17, outfit, 1.18, -0.42);
    const armR = mk(0.17, 0.6, 0.17, outfit, 1.18, 0.42);

    const pivot = new THREE.Group();
    pivot.position.y = 1.82;
    head.add(pivot);
    const nameSprite = this.makeLabel(this.character.name, 0xffffff);
    nameSprite.position.y = 0.42;
    pivot.add(nameSprite);

    const cls = getClass(this.character.classId);
    const classSprite = this.makeLabel(cls ? cls.name : this.character.classId, 0xbb86fc, 0.7);
    classSprite.position.y = 0.3;
    pivot.add(classSprite);

    this.legL = legL;
    this.legR = legR;
    this.armL = armL;
    this.armR = armR;

    return group;
  }

  private buildNpc(name: string): THREE.Group {
    const group = new THREE.Group();
    const mat = new THREE.MeshLambertMaterial({ color: 0x2f7bbf });
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.5, 1.1, 10), mat);
    body.position.y = 0.55;
    group.add(body);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 10), new THREE.MeshLambertMaterial({ color: 0xe8c39a }));
    head.position.y = 1.35;
    group.add(head);
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.42, 0.55, 20),
      new THREE.MeshBasicMaterial({ color: 0x7ce6c8, side: THREE.DoubleSide }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.02;
    group.add(ring);

    const sprite = this.makeLabel(name, 0x9ad7ff, 0.8);
    sprite.position.y = 1.95;
    group.add(sprite);
    return group;
  }

  private makeLabel(text: string, color: number, scale = 1): THREE.Sprite {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext("2d")!;
    ctx.font = "bold 56px Roboto, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.strokeStyle = "rgba(0,0,0,0.85)";
    ctx.lineWidth = 8;
    ctx.strokeText(text, 256, 64);
    ctx.fillStyle = "#" + color.toString(16).padStart(6, "0");
    ctx.fillText(text, 256, 64);

    const tex = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: tex, depthWrite: false });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(3.2 * scale, 0.8 * scale, 1);
    return sprite;
  }

  setMovement(x: number, z: number): void {
    this.move.x = x;
    this.move.z = z;
    const len = Math.hypot(x, z);
    this.moving = len > 0.05;
    if (this.moving) {
      this.move.x /= len;
      this.move.z /= len;
    }
  }

  rotateCamera(dx: number, dy: number): void {
    this.yaw -= dx * 0.008;
    this.pitch = Math.max(CAM_MIN_PITCH, Math.min(CAM_MAX_PITCH, this.pitch + dy * 0.006));
  }

  attack(): void {
    if (this.attacking) return;
    this.attacking = true;
    this.attackT = 0;
    this.onLog(`${this.character.name} attacks! (placeholder action)`);
  }

  interact(): void {
    const p = this.player.position;
    let best: { name: string; d: number } | null = null;
    for (const npc of this.npcGroups) {
      const d = Math.hypot(npc.x - p.x, npc.z - p.z);
      if (d < 16 && (!best || d < best.d)) {
        best = { name: npc.name, d };
      }
    }
    if (best) {
      this.onLog(`You speak with ${best.name}. (interaction placeholder)`);
    } else {
      this.onLog("Nothing to interact with nearby.");
    }
  }

  private updatePlayer(dt: number): void {
    const p = this.player.position;
    if (this.moving) {
      const yaw = this.yaw;
      const fx = -Math.sin(yaw);
      const fz = -Math.cos(yaw);
      const rx = Math.cos(yaw);
      const rz = -Math.sin(yaw);
      const wx = this.move.x * rx + this.move.z * fx;
      const wz = this.move.x * rz + this.move.z * fz;
      const nx = p.x + wx * WALK_SPEED * dt;
      const nz = p.z + wz * WALK_SPEED * dt;
      const b = this.boundsBox;
      p.x = Math.max(b.minX + 2, Math.min(b.maxX - 2, nx));
      p.z = Math.max(b.minZ + 2, Math.min(b.maxZ - 2, nz));

      const targetAngle = Math.atan2(wx, wz);
      const cur = this.player.rotation.y;
      let diff = targetAngle - cur;
      while (diff > Math.PI) diff -= Math.PI * 2;
      while (diff < -Math.PI) diff += Math.PI * 2;
      this.player.rotation.y = cur + diff * Math.min(1, dt * 10);

      this.walkPhase += dt * 9;
      const swing = Math.sin(this.walkPhase) * 0.5;
      this.legL.rotation.x = swing;
      this.legR.rotation.x = -swing;
      this.armL.rotation.x = -swing * 0.8;
      this.armR.rotation.x = swing * 0.8;
      p.y = this.assets.spawn.y + Math.abs(Math.sin(this.walkPhase)) * 0.06;
    } else {
      this.legL.rotation.x *= 1 - Math.min(1, dt * 10);
      this.legR.rotation.x *= 1 - Math.min(1, dt * 10);
      this.armL.rotation.x *= 1 - Math.min(1, dt * 10);
      this.armR.rotation.x *= 1 - Math.min(1, dt * 10);
      p.y += (this.assets.spawn.y - p.y) * Math.min(1, dt * 6);
    }

    if (this.attacking) {
      this.attackT += dt;
      this.armR.rotation.x = -2.4 * Math.sin(Math.min(1, this.attackT / 0.35) * Math.PI);
      if (this.attackT > 0.45) {
        this.attacking = false;
        this.armR.rotation.x = 0;
      }
    }
  }

  private updateCamera(dt: number): void {
    const p = this.player.position;
    this.targetYaw += (this.yaw - this.targetYaw) * Math.min(1, dt * 8);
    const y = this.targetYaw;
    const cp = Math.cos(this.pitch);
    const sp = Math.sin(this.pitch);
    this.camera.position.set(
      p.x + CAM_DIST * cp * Math.sin(y),
      p.y + CAM_DIST * sp + 1.4,
      p.z + CAM_DIST * cp * Math.cos(y),
    );
    this.camera.lookAt(p.x, p.y + 1.5, p.z);
  }

  private loop = (): void => {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    const dt = Math.min(this.clock.getDelta(), 0.05);
    this.updatePlayer(dt);
    this.updateCamera(dt);
    this.renderer.render(this.scene, this.camera);
  };

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
