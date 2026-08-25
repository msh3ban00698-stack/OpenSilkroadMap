import * as THREE from "three";

export interface SkeletonData {
  names: string[];
  parents: number[];
  bindRot: number[];
  bindPos: number[];
}

export interface MeshPartData {
  id: string;
  tex: string | null;
  render: "opaque" | "alpha" | "translucent";
  pos: number[];
  nrm: number[];
  uv: number[];
  sk: number[];
  sw: number[];
  idx: number[];
}

export interface AnimBoneData {
  i: number;
  rot: number[];
  pos: number[];
}

export interface AnimData {
  id: string;
  name: string;
  dur: number;
  loop: boolean;
  times: number[];
  bones: AnimBoneData[];
}

export interface CharacterMeta {
  preset: string;
  name: string;
  race?: string;
  class?: string;
  bones: number;
  meshes: number;
  height: number;
  scale: number;
}

export interface CharacterAssets {
  skeleton: SkeletonData;
  meshes: MeshPartData[];
  anims: AnimData[];
  meta: CharacterMeta;
  textures: Map<string, THREE.Texture>;
}

export function characterBase(preset: string): string {
  if (preset.startsWith("actor/") || preset.includes("/")) {
    return `/assets/img/silkroad/game/${preset}`;
  }
  return `/assets/img/silkroad/game/character/${preset}`;
}

async function loadJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Character asset not found: ${url} (${res.status})`);
  }
  return (await res.json()) as T;
}

function loadTexture(url: string): Promise<THREE.Texture> {
  return new Promise((resolve, reject) => {
    new THREE.TextureLoader().load(
      url,
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        resolve(tex);
      },
      undefined,
      (err) => reject(err),
    );
  });
}

export async function loadCharacter(preset: string): Promise<CharacterAssets> {
  const base = characterBase(preset);
  const [skeleton, meshes, anims, meta] = await Promise.all([
    loadJson<SkeletonData>(`${base}/skeleton.json`),
    loadJson<{ meshes: MeshPartData[] }>(`${base}/meshes.json`),
    loadJson<{ anims: AnimData[] }>(`${base}/anims.json`),
    loadJson<CharacterMeta>(`${base}/meta.json`),
  ]);

  const textures = new Map<string, THREE.Texture>();
  const texSet = new Set<string>();
  for (const m of meshes.meshes) {
    if (m.tex) texSet.add(m.tex);
  }
  await Promise.all(
    [...texSet].map(async (name) => {
      textures.set(name, await loadTexture(`${base}/${name}`));
    }),
  );

  return {
    skeleton,
    meshes: meshes.meshes,
    anims: anims.anims,
    meta,
    textures,
  };
}
