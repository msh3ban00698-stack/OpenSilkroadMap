import * as THREE from "three";
import type { EquipSlot, GameCharacter } from "./types";
import { getClass, getClassStats, HP_PER_LEVEL, MP_PER_LEVEL, REGION_NPCS, START_REGION_NAME } from "./game_data";
import { expToNext, MAX_LEVEL } from "./data_loader";
import type { RegionAssets } from "./region_loader";
import { sampleTerrainHeight } from "./region_loader";
import { CharacterRig } from "./character_rig";
import { getItem } from "./items";
import { MOB_CAMPS } from "./mobs_data";
import { loadTeleportPads, type TeleportPad } from "./teleport_data";
import { MAX_PARTY_MEMBERS, type MercenaryDef } from "./party_data";
import { getSkillFull, isHealSkill, loadSkillsFull, skillDamage, skillHeal, skillMpCost } from "./skill_data";

export interface NpcInstance {
  id: string;
  name: string;
  x: number;
  z: number;
  code?: string;
}

export interface GameWorldOptions {
  container: HTMLElement;
  character: GameCharacter;
  assets: RegionAssets;
  onLog: (msg: string) => void;
  onInteractNpc?: (npc: NpcInstance) => void;
  onInteractGate?: (gate: TeleportPad) => void;
  onMobKilled?: (mobCode: string) => void;
  onCharacterMutated?: () => void;
  onLevelUp?: (level: number) => void;
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

// Open-world constants for the real Constantinople region (region 1). The
// terrain spans 11520 x 11520 world units, so the camera + fog must reach far.
const CAM_FAR = 6000;
const FOG_NEAR = 250;
const FOG_FAR = 1800;

const ATTACK_RANGE = 2.4;
const ATTACK_IMPACT_FRACTION = 0.42;
const DUMMY_HP = 100;
const DUMMY_RESPAWN_MS = 5000;

const PLAYER_DEATH_MS = 3500;
const RETALIATE_CHANCE = 0.3;
const RETALIATE_MIN = 6;
const RETALIATE_MAX = 14;
const DUMMY_GOLD_REWARD = { min: 6, max: 18 };
// EXP gain per dummy kill (gameplay tuning; no verified exp reward table exists
// in the package's server_dep textdata). ~6 kills per level at Lv.1.
const DUMMY_EXP_REWARD = 20;

const SWORD_PART_ID = "sword_01";

type AnimState = "idle" | "walk" | "run" | "attack";

interface Selection {
  kind: "npc" | "dummy" | "mob" | "gate";
  id: string;
  name: string;
  x: number;
  z: number;
}

interface NpcGroup {
  group: THREE.Group;
  id: string;
  name: string;
  x: number;
  z: number;
}

interface MobState {
  def: (typeof MOB_CAMPS)[number]["mob"];
  rig: CharacterRig;
  group: THREE.Group;
  hp: number;
  alive: boolean;
  respawnAt: number;
  homeX: number;
  homeZ: number;
  aggro: boolean;
  nextAttackAt: number;
}

export class GameWorld {
  private container: HTMLElement;
  private character: GameCharacter;
  private assets: RegionAssets;
  private onLog: (msg: string) => void;
  private onInteractNpc?: (npc: NpcInstance) => void;
  private onInteractGate?: (gate: TeleportPad) => void;
  private onMobKilled?: (mobCode: string) => void;
  private onCharacterMutated?: () => void;
  private onLevelUp?: (level: number) => void;

  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private clock: THREE.Clock;
  private raf = 0;
  private disposed = false;

  private rig: CharacterRig;
  private rigReady = false;
  private labels: THREE.Group;
  private npcGroups: NpcGroup[] = [];
  private gateGroups: NpcGroup[] = [];
  private gatePads: TeleportPad[] = [];
  private companions: {
    rig: CharacterRig;
    code: string;
    name: string;
    nextAttackAt: number;
  }[] = [];

  private worldNpcCount = 0;
  private npcList = REGION_NPCS;
  private yaw = -1.31;
  private pitch = 0.15;
  private move = { x: 0, z: 0, mag: 0 };
  private moving = false;

  private animState: AnimState = "idle";
  private attacking = false;
  private attackStartedAt = 0;
  private attackHitDone = false;

  private dummy: { group: THREE.Group; alive: boolean; hp: number; maxHp: number; respawnAt: number };
  private dummyHpBar: { sprite: THREE.Sprite; setHp: (frac: number) => void };
  private floaters: { sprite: THREE.Sprite; t: number; life: number; vy: number }[] = [];
  private lastDamage = 0;
  private dummyHits = 0;

  private playerHp = 100;
  private playerMp = 100;
  private playerDead = false;
  private respawnDeadline = 0;
  private selected: Selection | null = null;
  private selectionRing: THREE.Mesh;
  private raycaster = new THREE.Raycaster();

  constructor(opts: GameWorldOptions) {
    this.container = opts.container;
    this.character = opts.character;
    this.assets = opts.assets;
    this.onLog = opts.onLog;
    this.onInteractNpc = opts.onInteractNpc;
    this.onInteractGate = opts.onInteractGate;
    this.onMobKilled = opts.onMobKilled;
    this.onCharacterMutated = opts.onCharacterMutated;
    this.onLevelUp = opts.onLevelUp;

    this.playerHp = this.character.hp;
    this.playerMp = this.character.mp;

    void loadSkillsFull();
    void this.buildGates();
    this.syncCompanions();

    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(this.container.clientWidth || 360, this.container.clientHeight || 640);
    this.container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x9db8d6);
    this.scene.fog = new THREE.Fog(0xb9c8d9, FOG_NEAR, FOG_FAR);

    this.camera = new THREE.PerspectiveCamera(
      62,
      (this.container.clientWidth || 360) / (this.container.clientHeight || 640),
      0.1,
      CAM_FAR,
    );

    this.addLights();
    this.addFloor();
    this.addBounds();
    this.addWorldObjects();
    this.addNpcs();
    void this.populateAuthenticNpcs();
    void this.spawnMobs();

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
    this.dummy = { group: dummyGroup, alive: true, hp: DUMMY_HP, maxHp: DUMMY_HP, respawnAt: 0 };
    this.dummyHpBar = hpBar;

    this.scene.add(this.rig.group);
    this.placePlayerAtSpawn();

    this.selectionRing = this.buildSelectionRing();
    this.selectionRing.visible = false;
    this.scene.add(this.selectionRing);

    const playerLight = new THREE.PointLight(0xffd9a0, 40, 60, 2);
    playerLight.position.set(0, 8, 0);
    this.rig.group.add(playerLight);

    this.clock = new THREE.Clock();
    this.rig
      .load()
      .then(() => {
        this.rigReady = true;
        this.rig.play("idle");
        this.applyEquipment(this.character.equipment);
        this.onLog(`Welcome to ${START_REGION_NAME}, ${this.character.name}.`);
        this.onLog("A training dummy stands in front of you. Attack it (ATK) when close.");
      })
      .catch((e) => {
        console.error(e);
        this.onLog("Failed to load real character model.");
      });
    this.loop();

    (window as unknown as Record<string, unknown>).__sro3d = {
      getPlayerPos: () => ({
        x: this.rig.group.position.x,
        y: this.rig.group.position.y,
        z: this.rig.group.position.z,
      }),
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
      setPlayerPos: (x: number, z: number, y?: number) => {
        this.rig.group.position.set(x, y ?? this.assets.spawn.y, z);
      },
      terrainY: (x: number, z: number) => this.terrainHeightAt(x, z),
      setPlayerRotationY: (y: number) => {
        this.rig.group.rotation.y = y;
      },
      attack: () => this.attack(),
      useSkill: (code: string, name?: string) => this.useSkill(code, name ?? code),
      dummy: () => ({
        x: this.dummy.group.position.x,
        z: this.dummy.group.position.z,
        hp: this.dummy.hp,
        maxHp: this.dummy.maxHp,
        alive: this.dummy.alive,
        hits: this.dummyHits,
        lastDamage: this.lastDamage,
      }),
      getState: () => this.getState(),
      worldInfo: () => this.worldInfo(),
      pick: (x: number, y: number) => this.pick(x, y),
      selectTarget: (kind: string, id: string) => this.selectTarget(kind as Selection["kind"], id),
      mobs: () =>
        this.mobs.map((m, i) => ({
          i,
          name: m.def.name,
          alive: m.alive,
          hp: m.hp,
          maxHp: m.def.hp,
          ready: m.rig.isReady,
          aggro: m.aggro,
          cd: Math.max(0, Math.round((m.nextAttackAt - performance.now()) / 100) / 10),
          cur: m.rig.currentId,
          x: m.group.position.x,
          z: m.group.position.z,
        })),
      debugTeleport: (x: number, z: number) => {
        const y = this.terrainHeightAt(x, z);
        this.rig.group.position.set(x, y, z);
      },
      swing: () => ({
        attacking: this.attacking,
        cur: this.rig.currentId,
        tMs: Math.round(this.rig.timeMs),
        dur: Math.round(this.rig.duration),
        loop: this.rig.isLooping,
      }),
      clearTarget: () => this.selectTarget(null, ""),
      interact: () => this.interact(),
      damagePlayer: (amount: number) => this.damagePlayer(amount),
      renderInfo: () => ({
        calls: this.renderer.info.render.calls,
        triangles: this.renderer.info.render.triangles,
      }),
      probeView: () => this.probeRays(),
      skyline: () => this.skyline(),
      setCameraPose: (yaw: number, pitch: number) => {
        this.yaw = yaw;
        this.targetYaw = yaw;
        this.pitch = pitch;
      },
      setTerrainVisible: (v: boolean) => {
        if (this.floorMesh) this.floorMesh.visible = v;
      },
    };
  }

  private skyline(): Record<string, unknown> {
    const ray = new THREE.Raycaster();
    ray.far = 5000;
    const o = this.camera.position.clone();
    this.scene.updateMatrixWorld(true);
    const targets = this.scene.children.filter((c) => c.visible && (c.type === "Mesh" || c.type === "InstancedMesh"));
    const dirs = [
      ["E", 90],
      ["S", 180],
      ["W", 270],
      ["N", 0],
    ] as const;
    const sectors = dirs.map(([name, deg]) => {
      const res: Record<string, number> = {};
      for (const [tag, elev] of [
        ["low", -0.02],
        ["high", 0.18],
      ] as const) {
        const d = new THREE.Vector3(Math.sin((deg * Math.PI) / 180), elev, Math.cos((deg * Math.PI) / 180));
        ray.set(o, d);
        let best: number | null = null;
        outer: for (const child of targets) {
          try {
            const hits = ray.intersectObject(child, false);
            if (hits.length) {
              best = hits[0].distance;
              break outer;
            }
          } catch {
            continue;
          }
        }
        res[tag] = best === null ? -1 : Math.round(best);
      }
      return { dir: name, ...res };
    });
    return { origin: o.toArray().map((v) => Math.round(v)), sectors };
  }

  private probeRays(): Record<string, unknown> {
    const ray = new THREE.Raycaster();
    ray.far = 4000;
    const rays: { ndc: [number, number]; dist: number; kind: string }[] = [];
    for (const nx of [-0.6, 0, 0.6]) {
      for (const ny of [0.45, 0, -0.4]) {
        ray.setFromCamera(new THREE.Vector2(nx, ny), this.camera);
        const hits = ray.intersectObjects(this.scene.children, true);
        const h = hits[0];
        rays.push({ ndc: [nx, ny], dist: h ? Math.round(h.distance) : -1, kind: h ? h.object.type : "none" });
      }
    }
    return {
      camera: this.camera.position,
      player: this.rig.group.position,
      rays,
    };
  }

  // --- Public gameplay API -------------------------------------------------

  getPlayerPos(): { x: number; y: number; z: number } {
    return {
      x: this.rig.group.position.x,
      y: this.rig.group.position.y,
      z: this.rig.group.position.z,
    };
  }

  getState(): Record<string, unknown> {
    const cls = getClass(this.character.classId);
    const target = this.selected
      ? {
          kind: this.selected.kind,
          id: this.selected.id,
          name: this.selected.name,
          x: this.selected.x,
          z: this.selected.z,
        }
      : null;
    return {
      hp: Math.max(0, Math.round(this.playerHp)),
      mp: Math.max(0, Math.round(this.playerMp)),
      maxHp: this.character.maxHp,
      maxMp: this.character.maxMp,
      gold: this.character.gold,
      level: this.character.level,
      exp: this.character.exp,
      expToNext: expToNext(this.character.level),
      name: this.character.name,
      classId: this.character.classId,
      className: cls ? cls.name : this.character.classId,
      dead: this.playerDead,
      respawnIn: Math.max(0, Math.round(this.respawnDeadline - performance.now())),
      selected: target,
      pos: { x: this.rig.group.position.x, y: this.rig.group.position.y, z: this.rig.group.position.z },
      yaw: this.rig.group.rotation.y,
      npcs: this.npcList.map((n) => ({
        id: n.id,
        name: n.name,
        x: n.x,
        z: n.z,
        selected: this.selected?.kind === "npc" && this.selected.id === n.id,
      })),
      gates: this.gatePads.map((g) => ({
        id: String(g.id),
        code: g.code,
        name: g.name,
        x: g.x,
        z: g.z,
        selected: this.selected?.kind === "gate" && this.selected.id === String(g.id),
      })),
      companions: this.companions.map((c) => ({
        code: c.code,
        name: c.name,
        x: c.rig.group.position.x,
        z: c.rig.group.position.z,
      })),
      world: this.worldInfo(),
      dummy: {
        x: this.dummy.group.position.x,
        z: this.dummy.group.position.z,
        alive: this.dummy.alive,
        hp: this.dummy.hp,
        maxHp: this.dummy.maxHp,
        selected: this.selected?.kind === "dummy",
      },
      bounds: this.boundsBox,
      selectedTarget:
        this.selected?.kind === "dummy"
          ? { hp: this.dummy.hp, maxHp: this.dummy.maxHp }
          : this.selected?.kind === "mob"
            ? (() => {
                const m = this.mobs[Number(this.selected.id)];
                return m ? { hp: m.hp, maxHp: m.def.hp } : null;
              })()
            : null,
      weaponsInWorld: this.character.equipment.weapon ? 1 : 0,
      skills: Array.from(this.skillCds.entries()).map(([code, at]) => ({
        code,
        remaining: Math.max(0, Math.round((at + (getSkillFull(code)?.cooldown ?? 0) - performance.now()) / 1000)),
      })),
    };
  }

  private worldInfo(): Record<string, number> {
    const wb = this.assets.buildings;
    return {
      buildings: wb ? wb.manifest.instances.length : 0,
      geoms: wb ? wb.manifest.geoms.length : 0,
      npcInstances: this.worldNpcCount,
      atlasPages: wb ? wb.manifest.atlas.length : 0,
    };
  }

  pick(clientX: number, clientY: number): boolean {
    const rect = this.renderer.domElement.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return false;
    const ndc = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -(((clientY - rect.top) / rect.height) * 2 - 1),
    );
    this.raycaster.setFromCamera(ndc, this.camera);
    const pickables: { object: THREE.Object3D; sel: Selection }[] = [];
    for (const npc of this.npcGroups) {
      pickables.push({
        object: npc.group,
        sel: { kind: "npc", id: npc.id, name: npc.name, x: npc.x, z: npc.z },
      });
    }
    for (const gate of this.gateGroups) {
      pickables.push({
        object: gate.group,
        sel: { kind: "gate", id: gate.id, name: gate.name, x: gate.x, z: gate.z },
      });
    }
    pickables.push({
      object: this.dummy.group,
      sel: {
        kind: "dummy",
        id: "dummy",
        name: "Training Dummy",
        x: this.dummy.group.position.x,
        z: this.dummy.group.position.z,
      },
    });
    this.mobs.forEach((m, i) => {
      if (!m.alive) return;
      pickables.push({
        object: m.group,
        sel: { kind: "mob", id: String(i), name: m.def.name, x: m.group.position.x, z: m.group.position.z },
      });
    });
    const hits = this.raycaster.intersectObjects(
      pickables.map((p) => p.object),
      true,
    );
    if (hits.length === 0) {
      this.selectTarget(null, "");
      return false;
    }
    const hit = hits[0];
    let root: THREE.Object3D | null = hit.object;
    while (root && root.parent && root.parent !== this.scene) root = root.parent;
    const found = pickables.find((p) => p.object === root);
    if (found) {
      this.selectTarget(found.sel.kind, found.sel.id, found.sel.name);
      return true;
    }
    this.selectTarget(null, "");
    return false;
  }

  selectTarget(kind: Selection["kind"] | null, id: string, name?: string): void {
    if (!kind) {
      this.selected = null;
      this.selectionRing.visible = false;
      return;
    }
    if (kind === "npc") {
      const reg = REGION_NPCS.find((n) => n.id === id);
      const grp = this.npcGroups.find((n) => n.id === id);
      if (!reg && !grp) return;
      const src = reg ?? grp!;
      this.selected = { kind: "npc", id: src.id, name: src.name, x: src.x, z: src.z };
    } else if (kind === "gate") {
      const pad = this.gatePads.find((g) => String(g.id) === id);
      if (!pad) return;
      this.selected = { kind: "gate", id: String(pad.id), name: pad.name, x: pad.x, z: pad.z };
    } else if (kind === "mob") {
      const m = this.mobs[Number(id)];
      if (!m || !m.alive) return;
      this.selected = { kind: "mob", id, name: name ?? m.def.name, x: m.group.position.x, z: m.group.position.z };
    } else {
      this.selected = {
        kind: "dummy",
        id: "dummy",
        name: name ?? "Training Dummy",
        x: this.dummy.group.position.x,
        z: this.dummy.group.position.z,
      };
    }
    this.selectionRing.visible = true;
    this.selectionRing.position.set(this.selected.x, 0.05, this.selected.z);
  }

  usePotion(itemId: string): boolean {
    const item = getItem(itemId);
    if (!item || item.slot !== "consumable" || !item.heal) return false;
    if (this.playerDead) return false;
    const heal = Math.min(item.heal, this.character.maxHp - this.playerHp);
    if (heal <= 0) return false;
    this.playerHp += heal;
    this.makeFloatingText(`+${Math.round(heal)}`, "#7fe07f");
    this.onLog(`You drink ${item.name} and recover ${Math.round(heal)} HP.`);
    this.consumeItem(itemId);
    return true;
  }

  private consumeItem(itemId: string): void {
    const stack = this.character.inventory.find((i) => i.id === itemId);
    if (stack) {
      stack.count -= 1;
      if (stack.count <= 0) {
        this.character.inventory = this.character.inventory.filter((i) => i.id !== itemId);
      }
      this.onCharacterMutated?.();
    }
  }

  applyEquipment(equipment: Record<EquipSlot, string | null>): void {
    const weaponId = equipment.weapon;
    if (!this.rigReady) return;
    if (weaponId) {
      this.rig.setPartVisible(SWORD_PART_ID, true);
      const item = getItem(weaponId);
      this.rig.setPartTint(SWORD_PART_ID, item ? item.color : null);
    } else {
      this.rig.setPartVisible(SWORD_PART_ID, false);
    }
  }

  damagePlayer(amount: number): void {
    if (this.playerDead) return;
    this.playerHp = Math.max(0, this.playerHp - amount);
    this.character.hp = Math.round(this.playerHp);
    this.onCharacterMutated?.();
    if (this.playerHp <= 0) this.die();
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

  private floorMesh: THREE.Mesh | null = null;

  private addFloor(): void {
    const material = new THREE.MeshLambertMaterial({
      map: this.assets.texture,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(this.assets.floorGeometry, material);
    this.scene.add(mesh);
    this.floorMesh = mesh;
  }

  private terrainHeightAt(x: number, z: number): number {
    return sampleTerrainHeight(this.assets.data, x, z);
  }

  private addWorldObjects(): void {
    const wb = this.assets.buildings;
    if (!wb) return;
    const { manifest, geometry, atlasTextures } = wb;

    const mats = atlasTextures.map(
      (tex) =>
        new THREE.MeshLambertMaterial({
          map: tex,
          side: THREE.DoubleSide,
          alphaTest: 0.4,
        }),
    );

    const geomGeos = manifest.geoms.map((slice) => this.buildGeomGeometry(geometry, slice));

    const matrix = new THREE.Matrix4();
    const quat = new THREE.Quaternion();
    const compose = (x: number, y: number, z: number, ry: number): THREE.Matrix4 =>
      matrix.makeRotationFromQuaternion(quat.setFromEuler(new THREE.Euler(0, ry, 0, "YZX"))).setPosition(x, y, z);

    // Buildings: one InstancedMesh per geometry.
    for (let gi = 0; gi < manifest.geoms.length; gi++) {
      const insts = manifest.instances.filter((i) => i.g === gi);
      if (!insts.length) continue;
      const slice = manifest.geoms[gi];
      const mat = mats[slice.page] ?? mats[0];
      if (!mat) continue;
      const mesh = new THREE.InstancedMesh(geomGeos[gi], mat, insts.length);
      for (let k = 0; k < insts.length; k++) {
        const i = insts[k];
        mesh.setMatrixAt(k, compose(i.x, i.y, i.z, i.ry));
      }
      mesh.instanceMatrix.needsUpdate = true;
      mesh.frustumCulled = false;
      this.scene.add(mesh);
    }

    // NPCs / monsters: one InstancedMesh per model group, placed on terrain.
    for (const grp of manifest.npcGroups) {
      if (!grp.instances.length) continue;
      const slice = manifest.geoms[grp.geom];
      if (!slice) continue;
      const mat = mats[slice.page] ?? mats[0];
      if (!mat) continue;
      const mesh = new THREE.InstancedMesh(geomGeos[grp.geom], mat, grp.instances.length);
      for (let k = 0; k < grp.instances.length; k++) {
        const p = grp.instances[k];
        const h = this.terrainHeightAt(p.x, p.z) + 0.8;
        mesh.setMatrixAt(k, compose(p.x, h, p.z, (k * 0.6) % (Math.PI * 2)));
      }
      mesh.instanceMatrix.needsUpdate = true;
      mesh.frustumCulled = false;
      this.scene.add(mesh);
      this.worldNpcCount += grp.instances.length;
    }
  }

  private buildGeomGeometry(
    merged: THREE.BufferGeometry,
    slice: {
      v0: number;
      vCount: number;
      i0: number;
      iCount: number;
    },
  ): THREE.BufferGeometry {
    const srcPos = merged.getAttribute("position") as THREE.BufferAttribute;
    const srcUv = merged.getAttribute("uv") as THREE.BufferAttribute;
    const srcIdx = merged.getIndex() as THREE.BufferAttribute;
    const pos = new Float32Array(slice.vCount * 3);
    const uv = new Float32Array(slice.vCount * 2);
    const idx = new Uint32Array(slice.iCount);
    for (let i = 0; i < slice.vCount; i++) {
      pos[i * 3] = srcPos.getX(slice.v0 + i);
      pos[i * 3 + 1] = srcPos.getY(slice.v0 + i);
      pos[i * 3 + 2] = srcPos.getZ(slice.v0 + i);
      uv[i * 2] = srcUv.getX(slice.v0 + i);
      uv[i * 2 + 1] = srcUv.getY(slice.v0 + i);
    }
    for (let j = 0; j < slice.iCount; j++) {
      idx[j] = srcIdx.getX(slice.i0 + j) - slice.v0;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    g.computeVertexNormals();
    return g;
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
    if (this.assets.buildings) {
      this.buildManifestNpcs();
      return;
    }
    for (const npc of REGION_NPCS) {
      const group = this.buildNpc(npc.name);
      group.position.set(npc.x, 0, npc.z);
      this.scene.add(group);
      this.npcGroups.push({ group, id: npc.id, name: npc.name, x: npc.x, z: npc.z });
    }
  }

  private buildManifestNpcs(): void {
    const wb = this.assets.buildings;
    if (!wb) return;
    const list: typeof REGION_NPCS = [];
    wb.manifest.npcGroups.forEach((grp, gi) => {
      if (grp.kind !== "npc" || !grp.instances.length) return;
      const p = grp.instances[0];
      const id = `npc_${grp.name}_${gi}`;
      const group = this.buildNpcCollider(grp.name);
      group.position.set(p.x, this.terrainHeightAt(p.x, p.z) + 0.5, p.z);
      this.scene.add(group);
      this.npcGroups.push({ group, id, name: grp.name, x: p.x, z: p.z });
      list.push({ id, name: grp.name, x: p.x, z: p.z });
    });
    if (list.length) this.npcList = list;
  }

  private npcRigs: { rig: CharacterRig; group: THREE.Group }[] = [];
  private mobs: MobState[] = [];
  private skillCds = new Map<string, number>();
  private pendingNpcRigs: { x: number; z: number; actor: string; group: THREE.Group; y: number }[] = [];

  private async spawnMobs(): Promise<void> {
    for (const camp of MOB_CAMPS) {
      for (let i = 0; i < camp.mob.count; i++) {
        const ang = (i / camp.mob.count) * Math.PI * 2;
        const x = camp.cx + Math.cos(ang) * camp.radius * (0.5 + ((i * 37) % 50) / 100);
        const z = camp.cz + Math.sin(ang) * camp.radius * (0.5 + ((i * 53) % 50) / 100);
        const y = this.terrainHeightAt(x, z);
        const rig = new CharacterRig({ preset: camp.mob.actor, scale: CHAR_SCALE });
        const group = new THREE.Group();
        group.position.set(x, y + 0.15, z);
        const box = new THREE.Mesh(
          new THREE.BoxGeometry(1.8, 2.4, 1.8),
          new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
        );
        box.position.y = 1.2;
        group.add(box);
        this.scene.add(group);
        void rig.load().then(() => {
          rig.group.position.set(x, y + 0.15, z);
          rig.play("idle");
          group.add(rig.group);
        });
        const st: MobState = {
          def: camp.mob,
          rig,
          group,
          hp: camp.mob.hp,
          alive: true,
          respawnAt: 0,
          homeX: x,
          homeZ: z,
          aggro: false,
          nextAttackAt: 0,
        };
        this.mobs.push(st);
      }
    }
    this.onLog("Wild creatures roam the fields beyond the gates.");
  }

  private updateMobs(dt: number): void {
    if (!this.rigReady) return;
    const p = this.rig.group.position;
    for (const m of this.mobs) {
      if (!m.alive) {
        if (performance.now() >= m.respawnAt && m.rig.isReady) {
          m.alive = true;
          m.hp = m.def.hp;
          m.aggro = false;
          m.group.position.set(m.homeX, this.terrainHeightAt(m.homeX, m.homeZ) + 0.15, m.homeZ);
          m.rig.play("idle");
        }
        continue;
      }
      if (!m.rig.isReady) continue;
      const dx = p.x - m.group.position.x;
      const dz = p.z - m.group.position.z;
      const dist = Math.hypot(dx, dz);
      if (this.selected?.kind === "mob" && this.selected.id === String(this.mobs.indexOf(m))) {
        this.selected.x = m.group.position.x;
        this.selected.z = m.group.position.z;
      }
      if (dist < 30 && !this.playerDead) m.aggro = true;
      if (dist > 220) m.aggro = false;
      if (m.aggro && dist > 6) {
        const speed = 34;
        const nx = m.group.position.x + (dx / dist) * speed * dt;
        const nz = m.group.position.z + (dz / dist) * speed * dt;
        m.group.position.set(nx, this.terrainHeightAt(nx, nz) + 0.15, nz);
        m.rig.group.rotation.y = Math.atan2(-dx, -dz);
        const animId = m.rig.hasAnim("run") ? "run" : m.rig.hasAnim("walk") ? "walk" : null;
        if (animId && m.rig.currentId !== animId) m.rig.play(animId);
        else if (!animId && m.rig.currentId !== "walk") m.rig.play("walk");
      } else {
        if (dist <= 6 && dist > 4.2) {
          m.rig.group.lookAt(p.x, m.group.position.y, p.z);
        }
        if (m.aggro && dist <= 6 && !this.playerDead) {
          if (performance.now() >= m.nextAttackAt) {
            m.nextAttackAt = performance.now() + 2000;
            const hasAttack = m.rig.hasAnim("attack");
            if (hasAttack) {
              m.rig.play("attack");
              setTimeout(() => {
                if (m.alive && m.rig.currentId === "attack") m.rig.play("idle");
              }, 700);
            }
            this.damagePlayer(m.def.attack + Math.floor(Math.random() * 7));
            this.makeFloatingTextAtPlayer(`-${Math.round(m.def.attack + Math.random() * 7)}`, "#ff8a80");
          }
        } else if (m.rig.currentId !== "idle") {
          m.rig.play("idle");
        }
      }
    }
  }

  private async populateAuthenticNpcs(): Promise<void> {
    try {
      const { loadWorldNpcs } = await import("./world_npcs");
      const npcs = await loadWorldNpcs();
      for (const npc of npcs) {
        const dupes = this.npcGroups.filter((g) => g.id.startsWith("npc_") && Math.hypot(g.x - npc.x, g.z - npc.z) < 4);
        if (dupes.length > 0) {
          for (const d of dupes) this.scene.remove(d.group);
          this.npcGroups = this.npcGroups.filter((g) => !dupes.includes(g));
          this.npcList = this.npcList.filter((n) => !dupes.some((d) => d.id === n.id));
        }
        const group = this.buildNpcCollider(npc.name);
        const y = this.terrainHeightAt(npc.x, npc.z);
        group.position.set(npc.x, y + 0.2, npc.z);
        this.scene.add(group);
        this.npcGroups.push({ group, id: npc.id, name: npc.name, x: npc.x, z: npc.z });
        if (npc.actor) {
          this.pendingNpcRigs.push({ x: npc.x, z: npc.z, actor: npc.actor, group, y });
        }
        const existing = this.npcList.find((n) => n.id === npc.id);
        if (!existing) {
          this.npcList = [
            ...this.npcList.filter((n) => n.id !== `npc_${npc.code}_0`),
            { id: npc.id, name: npc.name, x: npc.x, z: npc.z },
          ];
        } else {
          existing.name = npc.name;
        }
      }
      this.buildLabels();
    } catch {
      this.onLog("NPC data unavailable");
    }
  }

  private buildNpcCollider(name: string): THREE.Group {
    const group = new THREE.Group();
    const geo = new THREE.BoxGeometry(1.6, 3, 1.6);
    const mat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
    const box = new THREE.Mesh(geo, mat);
    box.position.y = 1.5;
    group.add(box);
    const sprite = this.makeLabel(name, 0x9ad7ff, 0.8);
    sprite.position.y = 3.4;
    group.add(sprite);
    return group;
  }

  private buildSelectionRing(): THREE.Mesh {
    const geo = new THREE.RingGeometry(0.55, 0.8, 24);
    const mat = new THREE.MeshBasicMaterial({
      color: 0xffe082,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
      depthTest: false,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = -Math.PI / 2;
    return mesh;
  }

  private buildNpc(name: string): THREE.Group {
    const group = new THREE.Group();
    const mat = new THREE.MeshLambertMaterial({ color: 0x2f7bbf });
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.5, 1.1, 10), mat);
    body.position.y = 0.55;
    group.add(body);
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.3, 12, 10),
      new THREE.MeshLambertMaterial({ color: 0xe8c39a }),
    );
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

  private makeFloatingTextAtPlayer(text: string, color: string): THREE.Sprite {
    const sprite = this.makeFloatingText(text, color);
    const p = this.rig.group.position;
    sprite.position.set(p.x, p.y + 2.4, p.z);
    this.scene.add(sprite);
    this.floaters.push({ sprite, t: 0, life: 1.2, vy: 2 });
    return sprite;
  }

  private makeFloatingText(text: string, color: string, at?: THREE.Vector3): THREE.Sprite {
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
    const base = at ?? this.dummy.group.position;
    sprite.position.set(base.x, base.y + 2.6, base.z);
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
    if (!this.rigReady || this.attacking || this.playerDead) return;
    if (this.selected?.kind === "npc") {
      this.onLog(`You cannot attack ${this.selected.name}.`);
      return;
    }
    const sel = this.selected;
    if (sel && sel.kind === "mob") {
      const m = this.mobs[Number(sel.id)];
      if (m && m.alive) {
        const dx = m.group.position.x - this.rig.group.position.x;
        const dz = m.group.position.z - this.rig.group.position.z;
        if (Math.hypot(dx, dz) < ATTACK_RANGE + 6) {
          this.rig.group.rotation.y = Math.atan2(-dx, -dz);
        }
      }
    }
    this.attacking = true;
    this.attackStartedAt = performance.now();
    this.attackHitDone = false;
    this.animState = "attack";
    this.rig.play("attack");
    this.onLog(`${this.character.name} attacks!`);
  }

  interact(): void {
    const p = this.rig.group.position;
    let best: { npc: NpcGroup; d: number } | null = null;
    let bestGate: { gate: NpcGroup; d: number } | null = null;

    if (this.selected?.kind === "npc") {
      const npc = this.npcGroups.find((n) => n.id === this.selected!.id);
      const d = npc ? Math.hypot(npc.x - p.x, npc.z - p.z) : Infinity;
      if (npc && d <= 16) {
        this.selectTarget("npc", npc.id, npc.name);
        this.onInteractNpc?.({ id: npc.id, code: npc.id, name: npc.name, x: npc.x, z: npc.z });
        return;
      }
      if (npc) best = { npc, d };
    }
    if (this.selected?.kind === "gate") {
      const gate = this.gateGroups.find((n) => n.id === this.selected!.id);
      const d = gate ? Math.hypot(gate.x - p.x, gate.z - p.z) : Infinity;
      if (gate && d <= 16) {
        this.selectTarget("gate", gate.id, gate.name);
        const pad = this.gatePads.find((g) => String(g.id) === gate.id);
        if (pad) this.onInteractGate?.(pad);
        return;
      }
      if (gate) bestGate = { gate, d };
    }
    if (!best || best.d > 16) {
      for (const npc of this.npcGroups) {
        const d = Math.hypot(npc.x - p.x, npc.z - p.z);
        if (d <= 16 && (!best || d < best.d)) {
          best = { npc, d };
        }
      }
    }
    if (!bestGate || bestGate.d > 16) {
      for (const gate of this.gateGroups) {
        const d = Math.hypot(gate.x - p.x, gate.z - p.z);
        if (d <= 16 && (!bestGate || d < bestGate.d)) {
          bestGate = { gate, d };
        }
      }
    }
    if (bestGate && (!best || bestGate.d < best.d)) {
      this.selectTarget("gate", bestGate.gate.id, bestGate.gate.name);
      const pad = this.gatePads.find((g) => String(g.id) === bestGate!.gate.id);
      if (pad) this.onInteractGate?.(pad);
      return;
    }
    if (best) {
      this.selectTarget("npc", best.npc.id, best.npc.name);
      this.onInteractNpc?.({ id: best.npc.id, code: best.npc.id, name: best.npc.name, x: best.npc.x, z: best.npc.z });
    } else {
      this.onLog("Nothing to interact with nearby.");
    }
  }

  private die(): void {
    this.playerDead = true;
    this.respawnDeadline = performance.now() + PLAYER_DEATH_MS;
    this.animState = "idle";
    this.rig.play("idle");
    this.onLog("You have been defeated. Recovering...");
  }

  private respawn(): void {
    this.playerDead = false;
    this.respawnDeadline = 0;
    this.playerHp = this.character.maxHp;
    this.playerMp = this.character.maxMp;
    this.character.hp = this.playerHp;
    this.character.mp = this.playerMp;
    this.placePlayerAtSpawn();
    this.onCharacterMutated?.();
    this.onLog("You have recovered and returned to the entrance.");
  }

  private updateRegen(dt: number): void {
    if (this.playerDead) return;
    const stats = getClassStats(this.character.classId);
    this.playerHp = Math.min(this.character.maxHp, this.playerHp + stats.regenHp * dt);
    this.playerMp = Math.min(this.character.maxMp, this.playerMp + stats.regenMp * dt);
    this.character.hp = Math.round(this.playerHp);
    this.character.mp = Math.round(this.playerMp);
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

    if (this.playerDead) {
      if (performance.now() >= this.respawnDeadline) this.respawn();
      return;
    }

    if (this.attacking) {
      const elapsed = performance.now() - this.attackStartedAt;
      const impactMs = this.rig.duration * ATTACK_IMPACT_FRACTION;
      if (!this.attackHitDone && elapsed >= impactMs) {
        this.attackHitDone = true;
        this.tryHitTarget();
      }
      if (elapsed >= this.rig.duration) {
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
      p.y = this.terrainHeightAt(p.x, p.z);

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
    const sel = this.selected;
    if (sel && sel.kind === "mob") {
      this.hitMob(sel.id);
      return;
    }
    if (sel && sel.kind === "npc") {
      this.onLog("You cannot attack townsfolk.");
      return;
    }
    const d = this.dummy;
    if (!d.alive) {
      this.onLog("Your target is out of reach.");
      return;
    }
    const p = this.rig.group.position;
    const dx = d.group.position.x - p.x;
    const dz = d.group.position.z - p.z;
    const dist = Math.hypot(dx, dz);
    if (dist > ATTACK_RANGE) {
      this.onLog("Your target is out of reach.");
      return;
    }
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
      d.respawnAt = performance.now() + DUMMY_RESPAWN_MS;
      const reward =
        DUMMY_GOLD_REWARD.min + Math.floor(Math.random() * (DUMMY_GOLD_REWARD.max - DUMMY_GOLD_REWARD.min));
      this.character.gold += reward;
      this.gainExp(DUMMY_EXP_REWARD);
      this.onCharacterMutated?.();
      this.onLog(
        `The training dummy has been defeated (${this.dummyHits} hits)! +${reward} gold, +${DUMMY_EXP_REWARD} exp.`,
      );
      return;
    }
    this.onLog(`You hit the training dummy for ${damage} damage. (${d.hp}/${d.maxHp})`);
    this.maybeRetaliate();
  }

  private gainExp(amount: number): void {
    if (this.character.level >= MAX_LEVEL) return;
    this.character.exp += amount;
    let leveled = false;
    while (this.character.level < MAX_LEVEL && this.character.exp >= expToNext(this.character.level)) {
      this.character.exp -= expToNext(this.character.level);
      this.character.level += 1;
      leveled = true;
    }
    if (this.character.level >= MAX_LEVEL) this.character.exp = 0;
    if (leveled) {
      this.character.maxHp += HP_PER_LEVEL;
      this.character.maxMp += MP_PER_LEVEL;
      this.playerHp = this.character.maxHp;
      this.playerMp = this.character.maxMp;
      this.onCharacterMutated?.();
      this.onLevelUp?.(this.character.level);
      this.makeFloatingText("LEVEL UP!", "#ffe082");
    }
  }

  useSkill(code: string, name: string): void {
    if (!this.rigReady || this.playerDead) return;
    const full = getSkillFull(code);
    if (!full) {
      this.attack();
      this.onLog(`${name} has no combat data in this build yet; basic attack used instead.`);
      return;
    }
    const now = performance.now();
    const last = this.skillCds.get(code) ?? 0;
    if (now - last < full.cooldown) {
      this.onLog(`${full.name} is on cooldown (${Math.ceil((full.cooldown - (now - last)) / 1000)}s).`);
      return;
    }
    const cost = skillMpCost(full, this.character.level);
    if (this.playerMp < cost) {
      this.onLog(`Not enough MP for ${full.name} (need ${cost}).`);
      return;
    }
    this.playerMp -= cost;
    this.character.mp = Math.round(this.playerMp);
    this.skillCds.set(code, now);
    if (isHealSkill(code)) {
      const heal = skillHeal(this.character.maxHp, this.character.level);
      this.playerHp = Math.min(this.character.maxHp, this.playerHp + heal);
      this.character.hp = Math.round(this.playerHp);
      this.makeFloatingText(`+${heal}`, "#7fe07f");
      this.rig.play("attack");
      this.onLog(`${full.name} heals you for ${heal} HP.`);
      this.onCharacterMutated?.();
      return;
    }
    const sel = this.selected;
    if (!sel || sel.kind !== "mob") {
      this.onLog("Select a monster to use a combat skill.");
      return;
    }
    const mob = this.mobs[Number(sel.id)];
    if (!mob || !mob.alive) {
      this.onLog("Your target is out of reach.");
      return;
    }
    const p = this.rig.group.position;
    const dx = mob.group.position.x - p.x;
    const dz = mob.group.position.z - p.z;
    const dist = Math.hypot(dx, dz);
    if (dist > ATTACK_RANGE + 6) {
      this.onLog("Your target is out of reach.");
      return;
    }
    this.rig.group.rotation.y = Math.atan2(-dx, -dz);
    const base = 18 + Math.floor(Math.random() * 12);
    const dmg = skillDamage(full, base, this.character.level);
    mob.hp = Math.max(0, mob.hp - dmg);
    this.lastDamage = dmg;
    this.makeFloatingText(`-${dmg}`, "#ff7043", mob.group.position);
    this.onLog(`${full.name} hits ${mob.def.name} for ${dmg} damage.`);
    if (!mob.aggro) {
      mob.aggro = true;
    }
    if (!this.attacking) {
      this.attacking = true;
      this.attackStartedAt = performance.now();
      this.attackHitDone = true;
      this.rig.play("attack");
    }
    if (mob.hp <= 0) {
      this.killMob(mob);
    }
    this.onCharacterMutated?.();
  }

  private maybeRetaliate(): void {
    if (Math.random() >= RETALIATE_CHANCE) return;
    const dmg = RETALIATE_MIN + Math.floor(Math.random() * (RETALIATE_MAX - RETALIATE_MIN));
    this.makeFloatingText(`-${dmg}`, "#ff8a80");
    this.damagePlayer(dmg);
    this.onLog(`The training dummy swings back and hits you for ${dmg} damage.`);
  }

  private hitMob(id: string): void {
    const mob = this.mobs[Number(id)];
    if (!mob) return;
    if (!mob.alive) {
      this.onLog("Your target is out of reach.");
      return;
    }
    const p = this.rig.group.position;
    const dx = mob.group.position.x - p.x;
    const dz = mob.group.position.z - p.z;
    const dist = Math.hypot(dx, dz);
    if (dist > ATTACK_RANGE + 2) {
      this.onLog("Your target is out of reach.");
      return;
    }
    const ry = this.rig.group.rotation.y;
    const facing = (-Math.sin(ry) * dx - Math.cos(ry) * dz) / (dist || 1);
    if (facing < 0.2) {
      this.onLog("Face your target to attack.");
      return;
    }
    const damage = 18 + Math.floor(Math.random() * 12);
    mob.hp = Math.max(0, mob.hp - damage);
    this.lastDamage = damage;
    this.makeFloatingText(`-${damage}`, "#ffd54f", mob.group.position);
    if (!mob.aggro) {
      mob.aggro = true;
    }
    if (mob.hp <= 0) {
      this.killMob(mob);
    }
  }

  private killMob(mob: MobState): void {
    mob.alive = false;
    mob.respawnAt = performance.now() + DUMMY_RESPAWN_MS;
    mob.group.visible = true;
    const death = mob.rig.hasAnim("death") ? { id: "death" } : null;
    if (death) {
      mob.rig.play("death");
      setTimeout(() => {
        mob.group.visible = false;
      }, 1600);
    } else {
      mob.group.visible = false;
    }
    if (this.selected && this.selected.kind === "mob") this.selectTarget(null, "");
    const reward = mob.def.goldReward[0] + Math.floor(Math.random() * (mob.def.goldReward[1] - mob.def.goldReward[0]));
    this.character.gold += reward;
    this.gainExp(mob.def.expReward);
    this.onCharacterMutated?.();
    this.onMobKilled?.(mob.def.code);
    this.onLog(`${mob.def.name} defeated! +${reward} gold, +${mob.def.expReward} exp.`);
  }

  private updateDummy(dt: number): void {
    const d = this.dummy;
    if (!d.alive) {
      d.group.rotation.z = Math.min(Math.PI / 2, d.group.rotation.z + dt * 3);
      if (performance.now() >= d.respawnAt) {
        d.alive = true;
        d.hp = d.maxHp;
        this.dummyHits = 0;
        this.dummyHpBar.setHp(1);
        this.onLog("The training dummy has been repaired.");
      }
    } else {
      d.group.rotation.z = Math.max(0, d.group.rotation.z - dt * 3);
    }
  }

  private async buildGates(): Promise<void> {
    const pads = await loadTeleportPads();
    for (const pad of pads) {
      const group = new THREE.Group();
      const ringGeo = new THREE.TorusGeometry(2.2, 0.28, 8, 32);
      const ringMat = new THREE.MeshStandardMaterial({
        color: 0x4fc3f7,
        emissive: 0x1a6da8,
        emissiveIntensity: 0.9,
        metalness: 0.4,
        roughness: 0.35,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 0.35;
      group.add(ring);
      const beamGeo = new THREE.CylinderGeometry(0.5, 0.5, 7, 12, 1, true);
      const beamMat = new THREE.MeshBasicMaterial({
        color: 0x7fd8ff,
        transparent: true,
        opacity: 0.22,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      const beam = new THREE.Mesh(beamGeo, beamMat);
      beam.position.y = 3.5;
      group.add(beam);
      const y = this.terrainHeightAt(pad.x, pad.z);
      group.position.set(pad.x, y, pad.z);
      this.scene.add(group);
      this.gateGroups.push({ group, id: String(pad.id), name: pad.name, x: pad.x, z: pad.z });
      this.gatePads.push(pad);
    }
    if (pads.length > 0) {
      this.onLog(`Teleport pads attuned: ${pads.map((g) => g.name).join(", ")}.`);
    }
  }

  teleportTo(x: number, z: number): void {
    const y = this.terrainHeightAt(x, z);
    this.rig.group.position.set(x, y, z);
    this.selectTarget(null, "");
  }

  syncCompanions(): void {
    const party = this.character.party || [];
    for (let i = this.companions.length - 1; i >= 0; i--) {
      if (!party.some((m) => m.code === this.companions[i].code)) {
        this.scene.remove(this.companions[i].rig.group);
        this.companions.splice(i, 1);
      }
    }
    party.forEach((member, idx) => {
      if (this.companions.some((c) => c.code === member.code)) return;
      const rig = new CharacterRig({ preset: "chinaman_fighter", scale: CHAR_SCALE * 0.94 });
      const p = this.rig.group.position;
      rig.group.position.set(p.x + 2 + idx * 1.5, p.y, p.z - 1.5);
      this.scene.add(rig.group);
      void rig.load().then(() => rig.play("idle"));
      this.companions.push({
        rig,
        code: member.code,
        name: member.name,
        nextAttackAt: 0,
      });
    });
  }

  hireCompanion(def: MercenaryDef): boolean {
    if (this.playerDead) return false;
    if (this.companions.length >= MAX_PARTY_MEMBERS) {
      this.onLog(`Your party is full (max ${MAX_PARTY_MEMBERS}).`);
      return false;
    }
    if (this.character.gold < def.cost) {
      this.onLog(`Not enough gold to hire ${def.name} (${def.cost} gold).`);
      return false;
    }
    this.character.gold -= def.cost;
    if (!this.character.party) this.character.party = [];
    this.character.party.push({ code: def.code, name: def.name });
    this.syncCompanions();
    this.onCharacterMutated?.();
    this.onLog(`${def.name} joins your party.`);
    return true;
  }

  dismissCompanion(code: string): boolean {
    if (!this.character.party) return false;
    const member = this.character.party.find((m) => m.code === code);
    if (!member) return false;
    this.character.party = this.character.party.filter((m) => m.code !== code);
    this.syncCompanions();
    this.onCharacterMutated?.();
    this.onLog(`${member.name} leaves your party.`);
    return true;
  }

  private updateCompanions(dt: number): void {
    const p = this.rig.group.position;
    this.companions.forEach((c, idx) => {
      const cp = c.rig.group.position;
      const dx = p.x + 2 + idx * 1.5 - cp.x;
      const dz = p.z - 1.5 - cp.z;
      const dist = Math.hypot(dx, dz);
      if (dist > 60) {
        cp.x = p.x + 2 + idx * 1.5;
        cp.z = p.z - 1.5;
        cp.y = this.terrainHeightAt(cp.x, cp.z);
      } else if (dist > 4) {
        const speed = Math.min(120, dist * 2.2) * dt;
        cp.x += (dx / dist) * speed;
        cp.z += (dz / dist) * speed;
        cp.y = this.terrainHeightAt(cp.x, cp.z);
        c.rig.group.rotation.y = Math.atan2(dx, dz);
        c.rig.play("run");
      } else if (c.rig.currentId !== "attack" && c.rig.currentId !== "idle") {
        c.rig.play("idle");
      }
      const now = performance.now();
      if (now < c.nextAttackAt) return;
      let target: { x: number; z: number; index: number; hp: number } | null = null;
      if (this.selected?.kind === "mob") {
        const m = this.mobs[Number(this.selected.id)];
        if (m && m.alive && Math.hypot(m.group.position.x - cp.x, m.group.position.z - cp.z) < 9) {
          target = { x: m.group.position.x, z: m.group.position.z, index: Number(this.selected.id), hp: m.hp };
        }
      }
      if (!target) {
        this.mobs.forEach((m, mi) => {
          if (!m.alive || target) return;
          const d = Math.hypot(m.group.position.x - cp.x, m.group.position.z - cp.z);
          if (d < 7) {
            target = { x: m.group.position.x, z: m.group.position.z, index: mi, hp: m.hp };
          }
        });
      }
      if (target) {
        c.nextAttackAt = now + 2000;
        const t = target as { x: number; z: number; index: number; hp: number };
        c.rig.group.rotation.y = Math.atan2(t.x - cp.x, t.z - cp.z);
        c.rig.play("attack");
        const dmg = 8 + Math.round(Math.random() * 6);
        const m = this.mobs[t.index];
        m.hp -= dmg;
        this.makeFloatingText(`${dmg}`, "#ffd479", new THREE.Vector3(t.x, 2.4, t.z));
        if (m.hp <= 0) {
          this.killMob(m);
        }
      }
    });
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

  private targetYaw = -1.31;

  private loop = (): void => {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    const dt = Math.min(this.clock.getDelta(), 0.05);
    this.updateRegen(dt);
    this.updatePlayer(dt);
    this.rig.update(dt);
    if (this.rig.skeleton) {
      this.rig.skeleton.update();
    }
    this.updateDummy(dt);
    this.updateMobs(dt);
    this.updateCompanions(dt);
    const px = this.rig.group.position.x;
    const pz = this.rig.group.position.z;
    for (let i = this.pendingNpcRigs.length - 1; i >= 0; i--) {
      const p = this.pendingNpcRigs[i];
      const dx = p.x - px;
      const dz = p.z - pz;
      if (dx * dx + dz * dz < -1) {
        const rig = new CharacterRig({ preset: p.actor, scale: CHAR_SCALE });
        rig.group.position.set(p.x, p.y + 0.15, p.z);
        rig.group.rotation.y = Math.PI;
        this.scene.add(rig.group);
        void rig.load().then(() => rig.play("idle"));
        this.npcRigs.push({ rig, group: p.group });
        this.pendingNpcRigs.splice(i, 1);
      }
    }
    for (const nr of this.npcRigs) {
      const dx = nr.group.position.x - px;
      const dz = nr.group.position.z - pz;
      const near = dx * dx + dz * dz < 22500;
      nr.rig.group.visible = near;
      if (near) {
        nr.rig.update(dt);
        if (nr.rig.skeleton) nr.rig.skeleton.update();
      }
    }
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
