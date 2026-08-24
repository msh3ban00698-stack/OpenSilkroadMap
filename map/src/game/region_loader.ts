import * as THREE from "three";

export interface RegionBounds {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  minY: number;
  maxY: number;
}

export interface RegionMeshData {
  region: number;
  name: string;
  source: { dof: string; minimap: string };
  vertexCount: number;
  indexCount: number;
  vertices: number[];
  indices: number[];
  bounds: RegionBounds;
  spawn: { x: number; y: number; z: number };
  blocks: { id: number; name: string; floor: number }[];
}

export interface RegionAssets {
  data: RegionMeshData;
  texture: THREE.Texture;
  floorGeometry: THREE.BufferGeometry;
  spawn: THREE.Vector3;
}

// RegionLoader loads a verified 3D region (geometry + texture generated from the
// external package by scripts/generate_region_mesh.py). Currently only Region
// 32785 "Cave of Meditation" is generated.
export class RegionLoader {
  static async load(regionId: number): Promise<RegionAssets> {
    const base = `/assets/img/silkroad/game/region${regionId}`;
    const meshRes = await fetch(`${base}/mesh.json`);
    if (!meshRes.ok) {
      throw new Error(`Region ${regionId} mesh not found (${meshRes.status})`);
    }
    const data = (await meshRes.json()) as RegionMeshData;
    if (data.region !== regionId) {
      throw new Error(`Region asset mismatch: expected ${regionId}, got ${data.region}`);
    }

    const texture = await this.loadTexture(`${base}/floor.webp`);

    const positions = new Float32Array(data.vertices.length / 5 * 3);
    const uvs = new Float32Array(data.vertices.length / 5 * 2);
    for (let i = 0; i < data.vertexCount; i++) {
      const o = i * 5;
      const x = data.vertices[o];
      const y = data.vertices[o + 1];
      const z = data.vertices[o + 2];
      const u = data.vertices[o + 3];
      const v = data.vertices[o + 4];
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      uvs[i * 2] = u;
      uvs[i * 2 + 1] = 1 - v;
    }

    const indices = new Uint32Array(data.indices);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    geometry.computeVertexNormals();

    return {
      data,
      texture,
      floorGeometry: geometry,
      spawn: new THREE.Vector3(data.spawn.x, data.spawn.y, data.spawn.z),
    };
  }

  private static loadTexture(url: string): Promise<THREE.Texture> {
    return new Promise((resolve, reject) => {
      const loader = new THREE.TextureLoader();
      loader.load(
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
}
