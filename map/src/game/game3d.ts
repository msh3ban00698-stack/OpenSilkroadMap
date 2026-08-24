import * as THREE from "three";
import type { GameCharacter } from "./types";
import { getClass, REGION_NPCS, START_REGION_NAME } from "./game_data";
import type { RegionAssets } from "./region_loader";
import { CharacterRig } from "./character_rig";

export interface GameWorldOptions {
  container: HTMLElement;
  character: GameCharacter;
  assets: RegionAssets;
  onLog: (msg: string) => void;
}

// Character visual scale (0.15 => ~2.4 world units, the Phase E viewer scale).
// The world keeps the Phase D region 32785 at 1:1 SRO coordinates.
const CHAR_SCALE = 0.15;

const WALK_SPEED = 70;
const RUN_SPEED = 125;
const RUN_MAGNITUDE = 0.55;

const CAM_DIST = 11;
const CAM_MIN_PITCH = 0.12;
const CAM_MAX_PITCH = 1.15;

const ATTACK_RANGE = 2.4;
const ATTACK_IMPACT_FRACTION = 0.42;
const DUMMY_HP = 100;
const DUMMY_RESPAWN_MS = 5000;

type AnimState = "idle" | "walk" | "run" | "attack";

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

  private rig: CharacterRig;
  private rigReady = false;
  private labels: THREE.Group;
  private npcGroups: { group: THREE.Group; name: string; x: number; z: number }[] = [];

  private yaw = 0.5;
  private pitch = 0.32;
  private move = { x: 0, z: 0, mag: 0 };
  private moving = false;

  private animState: AnimState = "idle";
  private attacking = false;
  private attackHitDone = false;

  private dummy: { group: THREE.Group; alive: boolean; hp: number; maxHp: number; respawnT: number };
  private dummyHpBar: { sprite: THREE.Sprite; setHp: (frac: number) => void };
  private floaters: { sprite: THREE.Sprite; t: number; life: number; vy: number }[] = [];
  private lastDamage = 0;
  private dummyHits = 0;

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
    this.scene.fog = new THREE.Fog(0x1a1620, 160, 420);

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

    this.rig = new CharacterRig({ preset: "chinaman_fighter", scale: CHAR_SCALE });
    this.labels = new THREE.Group();
    this.scene.add(this.labels);
    this.buildLabels();

    const spawn = this.assets.spawn;
    const dummyGroup = this.buildDummy();
    dummyGroup.position.set(spawn.x, spawn.y, spawn.z - 6);
    this.scene.add(dummyGroup);
    const hpBar = this.makeHpBar();
    hpBar.sprite.position.set(0, 3.1, 0);
    dummyGroup.add(hpBar.sprite);
    this.dummy = { group: dummyGroup, alive: true, hp: DUMMY_HP, maxHp: DUMMY_HP, respawnT: 0 };
    this.dummyHpBar = hpBar;

    this.scene.add(this.rig.group);
    this.placePlayerAtSpawn();

    const playerLight = new THREE.PointLight(0xffd9a0, 40, 60, 2);
    playerLight.position.set(0, 8, 0);
    this.rig.group.add(playerLight);

    this.clock = new THREE.Clock();
    this.rig.load()
      .then(() => {
        this.rigReady = true;
        this.rig.play("idle");
        this.onLog(`Welcome to ${START_REGION_NAME}, ${this.character.name}.`);
        this.onLog("A training dummy stands in front of you. Attack it (ATK) when close.");
      })
      .catch((e) => {
        console.error(e);
        this.onLog("Failed to load real character model.");
      });
    this.loop();

    (window as unknown as Record<string, unknown>).__sro3d = {
      getPlayerPos: () => ({ x: this.rig.group.position.x, y: this.rig.group.position.y, z: this.rig.group.position.z }),
      getPlayerRotation: () => ({ y: this.rig.group.rotation.y }),
      getCameraPos: () => ({ x: this.camera.position.x, y: this.camera.position.y, z: this.camera.position.z }),
      yaw: () => this.yaw,
      pitch: () => this.pitch,
      rigReady: () => this.rig.isReady,
      anim: () => this.animState,
      rigAnim: () => this.rig.currentId,
      rigStats: () => ({
        bones: this.rig.skeleton ? this.rig.skeleton.bones.length : 0,
        meshes: this.rig.meshes.length,
        height: this.rig.height,
        scale: CHAR_SCALE,
      }),
      getBoneWorld: (i: number) => {
        const v = this.rig.getBoneWorld(i);
        return v ? { x: v.x, y: v.y, z: v.z } : null;
      },
      setMove: (x: number, z: number) => this.setMovement(x, z),
      setPlayerPos: (x: number, z: number) => {
        this.rig.group.position.set(x, this.assets.spawn.y, z);
      },
      setPlayerRotationY: (y: number) => {
        this.rig.group.rotation.y = y;
      },
      attack: () => this.attack(),
      dummy: () => ({
        x: this.dummy.group.position.x,
        z: this.dummy.group.position.z,
        hp: this.dummy.hp,
        maxHp: this.dummy.maxHp,
        alive: this.dummy.alive,
        hits: this.dummyHits,
        lastDamage: this.lastDamage,
      }),
    };
  }

  private placePlayerAtSpawn(): void {
    const spawn = this.assets.spawn;
    this.rig.group.position.set(spawn.x, spawn.y, spawn.z);
    this.rig.group.rotation.y = 0;
  }

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

  private buildLabels(): void {
    const cls = getClass(this.character.classId);
    const nameSprite = this.makeLabel(this.character.name, 0xffffff, 1);
    nameSprite.position.y = 1.05;
    nameSprite.scale.set(2.2, 0.55, 1);
    this.labels.add(nameSprite);
    const classSprite = this.makeLabel(cls ? cls.name : this.character.classId, 0xbb86fc, 0.7);
    classSprite.position.y = 0.55;
    classSprite.scale.set(1.5, 0.38, 1);
    this.labels.add(classSprite);
  }

  private buildDummy(): THREE.Group {
    const group = new THREE.Group();
    const wood = new THREE.MeshLambertMaterial({ color: 0x9a7448 });
    const dark = new THREE.MeshLambertMaterial({ color: 0x5a3f28 });
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.32, 2.1, 12), wood);
    post.position.y = 1.05;
    group.add(post);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.16, 0.16), dark);
    arm.position.y = 1.75;
    group.add(arm);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 10), wood);
    head.position.y = 2.3;
    group.add(head);
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.3, 0.46, 18),
      new THREE.MeshBasicMaterial({ color: 0xcc3344, side: THREE.DoubleSide }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.04;
    group.add(ring);
    return group;
  }

  private makeHpBar(): { sprite: THREE.Sprite; setHp: (frac: number) => void } {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 16;
    const ctx = canvas.getContext("2d")!;
    const draw = (frac: number) => {
      ctx.clearRect(0, 0, 128, 16);
      ctx.fillStyle = "rgba(0,0,0,0.75)";
      ctx.fillRect(0, 0, 128, 16);
      ctx.fillStyle = "#3f9b3f";
      ctx.fillRect(2, 2, Math.max(0, Math.round((128 - 4) * frac)), 12);
    };
    draw(1);
    const tex = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: tex, depthTest: false, depthWrite: false });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(1.6, 0.2, 1);
    return {
      sprite,
      setHp: (frac: number) => {
        draw(Math.max(0, Math.min(1, frac)));
        tex.needsUpdate = true;
      },
    };
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

  private makeFloatingText(text: string, color: string): THREE.Sprite {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 64;
    const ctx = canvas.getContext("2d")!;
    ctx.font = "bold 40px Roboto, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.strokeStyle = "rgba(0,0,0,0.9)";
    ctx.lineWidth = 6;
    ctx.strokeText(text, 64, 32);
    ctx.fillStyle = color;
    ctx.fillText(text, 64, 32);
    const tex = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, depthWrite: false }));
    sprite.scale.set(1.8, 0.9, 1);
    sprite.position.set(
      this.dummy.group.position.x,
      this.dummy.group.position.y + 2.6,
      this.dummy.group.position.z,
    );
    this.scene.add(sprite);
    this.floaters.push({ sprite, t: 0, life: 0.8, vy: 1.6 });
    return sprite;
  }

  setMovement(x: number, z: number): void {
    const len = Math.hypot(x, z);
    this.moving = len > 0.05;
    if (this.moving) {
      this.move.x = x / len;
      this.move.z = z / len;
      this.move.mag = Math.min(1, len);
    } else {
      this.move.x = 0;
      this.move.z = 0;
      this.move.mag = 0;
    }
  }

  rotateCamera(dx: number, dy: number): void {
    this.yaw -= dx * 0.008;
    this.pitch = Math.max(CAM_MIN_PITCH, Math.min(CAM_MAX_PITCH, this.pitch + dy * 0.006));
  }

  attack(): void {
    if (!this.rigReady || this.attacking) return;
    this.attacking = true;
    this.attackHitDone = false;
    this.animState = "attack";
    this.rig.play("attack");
    this.onLog(`${this.character.name} attacks!`);
  }

  interact(): void {
    const p = this.rig.group.position;
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

  private getMovementWorld(): { wx: number; wz: number } {
    const yaw = this.yaw;
    const fx = -Math.sin(yaw);
    const fz = -Math.cos(yaw);
    const rx = Math.cos(yaw);
    const rz = -Math.sin(yaw);
    return {
      wx: this.move.x * rx + this.move.z * fx,
      wz: this.move.x * rz + this.move.z * fz,
    };
  }

  private updatePlayer(dt: number): void {
    if (!this.rigReady) return;
    const p = this.rig.group.position;

    if (this.attacking) {
      const impactMs = this.rig.duration * ATTACK_IMPACT_FRACTION;
      if (!this.attackHitDone && this.rig.timeMs >= impactMs) {
        this.attackHitDone = true;
        this.tryHitTarget();
      }
      if (!this.rig.isLooping && this.rig.timeMs >= this.rig.duration) {
        this.attacking = false;
      }
      return;
    }

    if (this.moving) {
      const { wx, wz } = this.getMovementWorld();
      const useRun = this.move.mag > RUN_MAGNITUDE;
      const speed = (useRun ? RUN_SPEED : WALK_SPEED) * Math.max(0.35, this.move.mag);
      const nx = p.x + wx * speed * dt;
      const nz = p.z + wz * speed * dt;
      const b = this.boundsBox;
      p.x = Math.max(b.minX + 2, Math.min(b.maxX - 2, nx));
      p.z = Math.max(b.minZ + 2, Math.min(b.maxZ - 2, nz));

      const targetAngle = Math.atan2(-wx, -wz);
      const cur = this.rig.group.rotation.y;
      let diff = targetAngle - cur;
      while (diff > Math.PI) diff -= Math.PI * 2;
      while (diff < -Math.PI) diff += Math.PI * 2;
      this.rig.group.rotation.y = cur + diff * Math.min(1, dt * 10);

      this.animState = useRun ? "run" : "walk";
      this.rig.play(this.animState);
    } else {
      this.animState = "idle";
      this.rig.play("idle");
    }
  }

  private tryHitTarget(): void {
    const d = this.dummy;
    if (!d.alive) return;
    const p = this.rig.group.position;
    const dx = d.group.position.x - p.x;
    const dz = d.group.position.z - p.z;
    const dist = Math.hypot(dx, dz);
    if (dist <= ATTACK_RANGE) {
      const ry = this.rig.group.rotation.y;
      const fx = -Math.sin(ry);
      const fz = -Math.cos(ry);
      const facing = (fx * dx + fz * dz) / (dist || 1);
      if (facing < 0.25) {
        this.onLog("Your target is out of reach.");
        return;
      }
      const damage = 15 + Math.floor(Math.random() * 11);
      this.lastDamage = damage;
      this.dummyHits++;
      d.hp = Math.max(0, d.hp - damage);
      this.dummyHpBar.setHp(d.hp / d.maxHp);
      this.makeFloatingText(`-${damage}`, "#ffd54f");
      if (d.hp <= 0) {
        d.alive = false;
        d.respawnT = DUMMY_RESPAWN_MS;
        this.onLog(`The training dummy has been defeated (${this.dummyHits} hits)!`);
      } else {
        this.onLog(`You hit the training dummy for ${damage} damage. (${d.hp}/${d.maxHp})`);
      }
    } else {
      this.onLog("Your target is out of reach.");
    }
  }

  private updateDummy(dt: number): void {
    const d = this.dummy;
    if (!d.alive) {
      d.respawnT -= dt * 1000;
      d.group.rotation.z = Math.min(Math.PI / 2, d.group.rotation.z + dt * 3);
      if (d.respawnT <= 0) {
        d.alive = true;
        d.hp = d.maxHp;
        this.dummyHits = 0;
        d.respawnT = 0;
        this.dummyHpBar.setHp(1);
        this.onLog("The training dummy has been repaired.");
      }
    } else {
      d.group.rotation.z = Math.max(0, d.group.rotation.z - dt * 3);
    }
  }

  private updateFloaters(dt: number): void {
    for (let i = this.floaters.length - 1; i >= 0; i--) {
      const f = this.floaters[i];
      f.t += dt;
      f.sprite.position.y += f.vy * dt;
      f.sprite.material.opacity = 1 - f.t / f.life;
      (f.sprite.material as THREE.SpriteMaterial).transparent = true;
      if (f.t >= f.life) {
        this.scene.remove(f.sprite);
        f.sprite.material.dispose();
        (f.sprite.material.map as THREE.Texture | null)?.dispose();
        this.floaters.splice(i, 1);
      }
    }
  }

  private updateLabels(): void {
    if (!this.rigReady) return;
    const head = this.rig.getBoneWorld(7);
    if (!head) return;
    this.labels.position.set(head.x, head.y, head.z);
  }

  private updateCamera(dt: number): void {
    const p = this.rig.group.position;
    this.targetYaw += (this.yaw - this.targetYaw) * Math.min(1, dt * 8);
    const y = this.targetYaw;
    const cp = Math.cos(this.pitch);
    const sp = Math.sin(this.pitch);
    this.camera.position.set(
      p.x + CAM_DIST * cp * Math.sin(y),
      p.y + CAM_DIST * sp + 1.6,
      p.z + CAM_DIST * cp * Math.cos(y),
    );
    this.camera.lookAt(p.x, p.y + 1.6, p.z);
  }

  private targetYaw = 0.5;

  private loop = (): void => {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    const dt = Math.min(this.clock.getDelta(), 0.05);
    this.updatePlayer(dt);
    this.rig.update(dt);
    if (this.rig.skeleton) {
      this.rig.skeleton.update();
    }
    this.updateDummy(dt);
    this.updateFloaters(dt);
    this.updateLabels();
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
    this.rig.dispose();
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}
