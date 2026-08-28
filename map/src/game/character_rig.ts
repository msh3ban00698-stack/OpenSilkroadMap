import * as THREE from "three";
import { loadCharacter, type AnimData, type CharacterAssets, type MeshPartData } from "./character_loader";

export interface CharacterRigOptions {
  preset: string;
  scale?: number;
}

export class CharacterRig {
  group: THREE.Group = new THREE.Group();
  skeleton: THREE.Skeleton | null = null;
  meshes: THREE.SkinnedMesh[] = [];

  private preset: string;
  private scale: number;
  private assets: CharacterAssets | null = null;
  private anims: AnimData[] = [];
  private currentAnim: AnimData | null = null;
  private timeMsValue = 0;
  private speed = 1;
  private ready = false;
  private scratchQ = new THREE.Quaternion();

  constructor(opts: CharacterRigOptions) {
    this.preset = opts.preset;
    this.scale = opts.scale ?? 0.15;
  }

  get isReady(): boolean {
    return this.ready;
  }

  get height(): number {
    return this.assets ? this.assets.meta.height * this.scale : 0;
  }

  get name(): string {
    return this.assets ? this.assets.meta.name : this.preset;
  }

  get currentId(): string | null {
    return this.currentAnim ? this.currentAnim.id : null;
  }

  hasAnim(id: string): boolean {
    return this.anims.some((a) => a.id === id);
  }

  animIds(): string[] {
    return this.anims.map((a) => a.id);
  }

  get timeMs(): number {
    return this.timeMsValue;
  }

  get duration(): number {
    return this.currentAnim ? this.currentAnim.dur : 0;
  }

  get isLooping(): boolean {
    return this.currentAnim ? this.currentAnim.loop : true;
  }

  get animations(): { id: string; name: string }[] {
    return this.anims.map((a) => ({ id: a.id, name: a.name }));
  }

  async load(): Promise<void> {
    this.assets = await loadCharacter(this.preset);
    this.scale = this.assets.meta.scale || this.scale;
    this.anims = this.assets.anims;
    const assembled = assembleCharacter(this.assets, this.scale, this.group);
    this.skeleton = assembled.skeleton;
    this.meshes = assembled.meshes;
    if (this.anims.length > 0) {
      this.currentAnim = this.anims[0];
      this.applyPose(0);
    }
    this.ready = true;
  }

  play(id: string): boolean {
    if (!this.ready) return false;
    const anim = this.anims.find((a) => a.id === id);
    if (!anim) return false;
    if (this.currentAnim === anim && anim.loop) return true;
    this.currentAnim = anim;
    this.timeMsValue = 0;
    this.applyPose(0);
    return true;
  }

  update(dt: number): void {
    if (!this.ready || !this.currentAnim) return;
    this.timeMsValue += dt * 1000 * this.speed;
    this.applyPose(this.timeMsValue);
  }

  setSpeed(speed: number): void {
    this.speed = Math.max(0, speed);
  }

  getBoneWorld(index: number): THREE.Vector3 | null {
    if (!this.skeleton || index < 0 || index >= this.skeleton.bones.length) {
      return null;
    }
    const v = new THREE.Vector3();
    this.skeleton.bones[index].getWorldPosition(v);
    return v;
  }

  getBoneQuaternionWorld(index: number): THREE.Quaternion | null {
    if (!this.skeleton || index < 0 || index >= this.skeleton.bones.length) {
      return null;
    }
    const q = new THREE.Quaternion();
    this.skeleton.bones[index].getWorldQuaternion(q);
    return q;
  }

  findPartIndex(id: string): number {
    if (!this.assets) return -1;
    return this.assets.meshes.findIndex((m) => m.id === id);
  }

  setPartVisible(id: string, visible: boolean): void {
    const idx = this.findPartIndex(id);
    if (idx < 0) return;
    const mesh = this.meshes[idx];
    if (mesh) mesh.visible = visible;
  }

  setPartTint(id: string, colorHex: string | null): void {
    const idx = this.findPartIndex(id);
    if (idx < 0) return;
    const mesh = this.meshes[idx];
    if (!mesh) return;
    const mat = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
    if (mat) (mat as THREE.MeshStandardMaterial).color.set(colorHex ?? "#ffffff");
  }

  applyPose(timeMs: number): void {
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
      const qa = this.scratchQ.set(b.rot[q0], b.rot[q0 + 1], b.rot[q0 + 2], b.rot[q0 + 3]);
      const qb = new THREE.Quaternion(b.rot[q1], b.rot[q1 + 1], b.rot[q1 + 2], b.rot[q1 + 3]);
      bone.quaternion.copy(qa.slerp(qb, f));
      bone.position.set(
        b.pos[p0] + (b.pos[p1] - b.pos[p0]) * f,
        b.pos[p0 + 1] + (b.pos[p1 + 1] - b.pos[p0 + 1]) * f,
        b.pos[p0 + 2] + (b.pos[p1 + 2] - b.pos[p0 + 2]) * f,
      );
    }
  }

  dispose(): void {
    for (const mesh of this.meshes) {
      mesh.geometry.dispose();
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of mats) m.dispose();
    }
    this.meshes = [];
    if (this.assets) {
      for (const tex of this.assets.textures.values()) tex.dispose();
    }
  }
}

export function assembleCharacter(
  assets: CharacterAssets,
  scale: number,
  root: THREE.Group = new THREE.Group(),
): { group: THREE.Group; skeleton: THREE.Skeleton; meshes: THREE.SkinnedMesh[] } {
  root.scale.setScalar(1);
  const skeleton = buildSkeleton(assets, root);
  const meshes: THREE.SkinnedMesh[] = [];
  for (const part of assets.meshes) {
    const mesh = buildMesh(part, assets);
    meshes.push(mesh);
    root.add(mesh);
  }
  root.updateMatrixWorld(true);
  promoteBoneLocalMeshes(assets, skeleton, meshes);
  skeleton.calculateInverses();
  for (const mesh of meshes) {
    mesh.bind(skeleton);
  }
  root.scale.setScalar(scale);
  return { group: root, skeleton, meshes };
}

function exclusiveBoneIndex(part: MeshPartData): number {
  const { sk, sw } = part;
  const n = sk.length / 4;
  if (n === 0) return -1;
  const bone = sk[0];
  for (let i = 0; i < n; i++) {
    for (let k = 0; k < 4; k++) {
      if (sw[i * 4 + k] > 1e-5 && sk[i * 4 + k] !== bone) return -1;
    }
  }
  return bone;
}

function promoteBoneLocalMeshes(
  assets: CharacterAssets,
  skeleton: THREE.Skeleton,
  meshes: THREE.SkinnedMesh[],
): void {
  const boneWorld = new THREE.Vector3();
  for (let i = 0; i < assets.meshes.length; i++) {
    const part = assets.meshes[i];
    const boneIndex = exclusiveBoneIndex(part);
    if (boneIndex < 0 || boneIndex >= skeleton.bones.length) continue;
    const pos = part.pos;
    const n = pos.length / 3;
    if (n === 0) continue;
    let cx = 0;
    let cy = 0;
    let cz = 0;
    for (let v = 0; v < n; v++) {
      cx += pos[v * 3];
      cy += pos[v * 3 + 1];
      cz += pos[v * 3 + 2];
    }
    cx /= n;
    cy /= n;
    cz /= n;
    skeleton.bones[boneIndex].getWorldPosition(boneWorld);
    const distOrigin = Math.hypot(cx, cy, cz);
    const distBone = Math.hypot(cx - boneWorld.x, cy - boneWorld.y, cz - boneWorld.z);
    if (distOrigin >= distBone * 0.45) continue;
    meshes[i].geometry.applyMatrix4(skeleton.bones[boneIndex].matrixWorld);
  }
}

function buildSkeleton(assets: CharacterAssets, root: THREE.Object3D): THREE.Skeleton {
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
      root.add(bone);
    }
  }
  return new THREE.Skeleton(bones);
}

function buildMesh(part: MeshPartData, assets: CharacterAssets): THREE.SkinnedMesh {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(part.pos, 3));
  geometry.setAttribute("normal", new THREE.Float32BufferAttribute(part.nrm, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(part.uv, 2));
  geometry.setAttribute("skinIndex", new THREE.Uint16BufferAttribute(part.sk, 4));
  geometry.setAttribute("skinWeight", new THREE.Float32BufferAttribute(part.sw, 4));
  geometry.setIndex(part.idx);

  const map = part.tex ? assets.textures.get(part.tex) : undefined;
  const base = { roughness: 0.92, metalness: 0.05, ...(map ? { map } : {}) };
  let material: THREE.MeshStandardMaterial;
  if (part.render === "alpha") {
    material = new THREE.MeshStandardMaterial({
      ...base,
      alphaTest: 0.5,
      side: THREE.DoubleSide,
    });
  } else if (part.render === "translucent") {
    material = new THREE.MeshStandardMaterial({
      ...base,
      roughness: 0.6,
      metalness: 0.2,
      transparent: true,
      side: THREE.DoubleSide,
    });
  } else {
    material = new THREE.MeshStandardMaterial(base);
  }

  return new THREE.SkinnedMesh(geometry, material);
}
