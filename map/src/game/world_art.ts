import * as THREE from "three";

const ENV = "/assets/img/silkroad/game/env";

export interface EnvTextures {
  grass: THREE.Texture;
  cobble: THREE.Texture;
  dirt: THREE.Texture;
  water: THREE.Texture;
  path: THREE.Texture;
  wood: THREE.Texture;
  stone: THREE.Texture;
  tree0: THREE.Texture;
  tree1: THREE.Texture;
  tree2: THREE.Texture;
  bush: THREE.Texture;
  cloth: THREE.Texture;
  tuft: THREE.Texture | null;
  barrel: THREE.Texture | null;
  door: THREE.Texture | null;
}

export interface DressingItem {
  t: number;
  x: number;
  z: number;
  ry: number;
}

export interface DressingData {
  types: string[];
  items: [number, number, number, number][];
}

function loadTex(url: string, repeat: boolean, alpha: boolean): Promise<THREE.Texture> {
  return new Promise((resolve, reject) => {
    new THREE.TextureLoader().load(
      url,
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.anisotropy = 8;
        if (repeat) {
          tex.wrapS = THREE.RepeatWrapping;
          tex.wrapT = THREE.RepeatWrapping;
        }
        if (alpha) tex.premultiplyAlpha = false;
        resolve(tex);
      },
      undefined,
      reject,
    );
  });
}

async function loadOptional(url: string, repeat: boolean, alpha: boolean): Promise<THREE.Texture | null> {
  try {
    return await loadTex(url, repeat, alpha);
  } catch {
    return null;
  }
}

export async function loadEnvArt(): Promise<{ textures: EnvTextures; dressing: DressingData | null }> {
  const [grass, cobble, dirt, water, path, wood, stone, tree0, tree1, tree2, bush, cloth, tuft, barrel, door] =
    await Promise.all([
      loadTex(`${ENV}/grass.webp`, true, false),
      loadTex(`${ENV}/cobble.webp`, true, false),
      loadTex(`${ENV}/dirt.webp`, true, false),
      loadTex(`${ENV}/water.webp`, true, false),
      loadTex(`${ENV}/path.webp`, true, false),
      loadTex(`${ENV}/wood.webp`, true, false),
      loadTex(`${ENV}/stone.webp`, true, false),
      loadTex(`${ENV}/tree0.webp`, false, true),
      loadTex(`${ENV}/tree1.webp`, false, true),
      loadTex(`${ENV}/tree2.webp`, false, true),
      loadTex(`${ENV}/bush.webp`, false, true),
      loadTex(`${ENV}/cloth.webp`, true, false),
      loadOptional(`${ENV}/tuft.webp`, false, true),
      loadOptional(`${ENV}/barrel.webp`, false, true),
      loadOptional(`${ENV}/door.webp`, false, true),
    ]);
  let dressing: DressingData | null = null;
  try {
    const res = await fetch(`${ENV}/dressing.json`);
    if (res.ok) dressing = (await res.json()) as DressingData;
  } catch {
    dressing = null;
  }
  return {
    textures: {
      grass,
      cobble,
      dirt,
      water,
      path,
      wood,
      stone,
      tree0,
      tree1,
      tree2,
      bush,
      cloth,
      tuft,
      barrel,
      door,
    },
    dressing,
  };
}

export function makeTerrainMaterial(
  minimap: THREE.Texture,
  env: EnvTextures,
  time: { value: number },
): THREE.MeshPhongMaterial {
  const mat = new THREE.MeshPhongMaterial({
    map: minimap,
    shininess: 12,
    specular: new THREE.Color(0x2a2418),
    side: THREE.DoubleSide,
  });
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.tGrass = { value: env.grass };
    shader.uniforms.tCobble = { value: env.cobble };
    shader.uniforms.tDirt = { value: env.dirt };
    shader.uniforms.tWater = { value: env.water };
    shader.uniforms.tPath = { value: env.path };
    shader.uniforms.tStone = { value: env.stone };
    shader.uniforms.uTime = time;
    shader.vertexShader = `varying vec3 vWp;\n${shader.vertexShader}`.replace(
      "#include <begin_vertex>",
      "#include <begin_vertex>\nvWp = transformed;",
    );
    shader.fragmentShader = `varying vec3 vWp;
uniform sampler2D tGrass;
uniform sampler2D tCobble;
uniform sampler2D tDirt;
uniform sampler2D tWater;
uniform sampler2D tPath;
uniform sampler2D tStone;
uniform float uTime;
${shader.fragmentShader}`.replace(
      "#include <map_fragment>",
      `#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	vec3 mini = sampledDiffuseColor.rgb;
	float lum = dot(mini, vec3(0.299, 0.587, 0.114));
	float waterM = smoothstep(0.05, 0.18, mini.b - mini.r);
	float grassM = smoothstep(0.02, 0.12, mini.g - max(mini.r, mini.b * 0.8));
	float gray = 1.0 - clamp(abs(mini.r - mini.g) * 6.0 + abs(mini.g - mini.b) * 6.0, 0.0, 1.0);
	float roadM = gray * smoothstep(0.16, 0.58, lum) * (1.0 - waterM);
	float marbleM = smoothstep(0.72, 0.9, lum) * (1.0 - waterM) * (1.0 - roadM * 0.4);
	float dirtM = smoothstep(0.03, 0.14, mini.r - mini.g) * (1.0 - waterM);
	vec2 wu = vWp.xz * 0.14;
	vec2 wu2 = vWp.xz * 0.067 + 19.1;
	vec3 grass = mix(texture2D(tGrass, wu).rgb, texture2D(tGrass, wu2).rgb, 0.4);
	vec3 cobble = mix(texture2D(tCobble, vWp.xz * 0.16).rgb, texture2D(tStone, vWp.xz * 0.09).rgb, 0.18);
	vec3 dirt = texture2D(tDirt, vWp.xz * 0.11).rgb;
	vec3 path = texture2D(tPath, vWp.xz * 0.13).rgb;
	vec2 wuv = vWp.xz * 0.05 + vec2(uTime * 0.016, uTime * 0.01);
	vec3 water = texture2D(tWater, wuv).rgb * vec3(0.7, 0.86, 1.04);
	vec3 ground = mix(dirt, grass, clamp(grassM + 0.22, 0.0, 1.0));
	ground = mix(ground, path, dirtM * 0.7);
	ground = mix(ground, cobble, clamp(roadM, 0.0, 1.0));
	ground = mix(ground, cobble * vec3(0.92, 0.9, 0.84), marbleM);
	ground = mix(ground, water, waterM);
	ground *= mix(vec3(1.0), mini * 1.22, 0.28);
	diffuseColor *= vec4(ground, 1.0);
#endif`,
    );
  };
  mat.customProgramCacheKey = () => "sro-terrain-splat-v3";
  return mat;
}

function crossBillboard(w: number, h: number): THREE.BufferGeometry {
  const hw = w * 0.5;
  const pos = new Float32Array([
    -hw, 0, 0, hw, 0, 0, hw, h, 0, -hw, 0, 0, hw, h, 0, -hw, h, 0, 0, 0, -hw, 0, 0, hw, 0, h, hw, 0, 0, -hw, 0, h, hw, 0, h, -hw,
  ]);
  const uv = new Float32Array([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]);
  const nrm = new Float32Array([
    0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0,
  ]);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  g.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
  return g;
}

function mergeGeos(parts: THREE.BufferGeometry[]): THREE.BufferGeometry {
  const pos: number[] = [];
  const nrm: number[] = [];
  const uv: number[] = [];
  const tmp = new THREE.Vector3();
  const nrmT = new THREE.Vector3();
  for (const g of parts) {
    g.computeVertexNormals();
    const p = g.getAttribute("position");
    const n = g.getAttribute("normal");
    const u = g.getAttribute("uv");
    const idx = g.getIndex();
    const push = (i: number) => {
      tmp.fromBufferAttribute(p, i);
      pos.push(tmp.x, tmp.y, tmp.z);
      if (n) {
        nrmT.fromBufferAttribute(n, i);
        nrm.push(nrmT.x, nrmT.y, nrmT.z);
      } else nrm.push(0, 1, 0);
      if (u) uv.push(u.getX(i), u.getY(i));
      else uv.push(0, 0);
    };
    if (idx) {
      for (let i = 0; i < idx.count; i++) push(idx.getX(i));
    } else {
      for (let i = 0; i < p.count; i++) push(i);
    }
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  out.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  return out;
}

function stallGeo(): THREE.BufferGeometry {
  const counter = new THREE.BoxGeometry(2.6, 0.95, 1.35);
  counter.translate(0, 0.48, 0);
  const postL = new THREE.BoxGeometry(0.1, 1.7, 0.1);
  postL.translate(-1.2, 1.35, -0.55);
  const postR = new THREE.BoxGeometry(0.1, 1.7, 0.1);
  postR.translate(1.2, 1.35, -0.55);
  const awning = new THREE.BoxGeometry(2.7, 0.08, 1.6);
  awning.rotateX(-0.22);
  awning.translate(0, 2.05, -0.05);
  const shelf = new THREE.BoxGeometry(2.4, 0.08, 0.7);
  shelf.translate(0, 1.05, 0.15);
  return mergeGeos([counter, postL, postR, awning, shelf]);
}

function cartGeo(): THREE.BufferGeometry {
  const bed = new THREE.BoxGeometry(2.2, 0.28, 1.15);
  bed.translate(0, 0.72, 0);
  const railL = new THREE.BoxGeometry(2.15, 0.35, 0.08);
  railL.translate(0, 1.0, 0.52);
  const railR = new THREE.BoxGeometry(2.15, 0.35, 0.08);
  railR.translate(0, 1.0, -0.52);
  const shaft = new THREE.BoxGeometry(1.4, 0.08, 0.08);
  shaft.translate(1.6, 0.7, 0);
  const w1 = new THREE.CylinderGeometry(0.38, 0.38, 0.12, 10);
  w1.rotateZ(Math.PI / 2);
  w1.translate(-0.7, 0.38, 0.62);
  const w2 = new THREE.CylinderGeometry(0.38, 0.38, 0.12, 10);
  w2.rotateZ(Math.PI / 2);
  w2.translate(-0.7, 0.38, -0.62);
  const w3 = new THREE.CylinderGeometry(0.38, 0.38, 0.12, 10);
  w3.rotateZ(Math.PI / 2);
  w3.translate(0.7, 0.38, 0.62);
  const w4 = new THREE.CylinderGeometry(0.38, 0.38, 0.12, 10);
  w4.rotateZ(Math.PI / 2);
  w4.translate(0.7, 0.38, -0.62);
  return mergeGeos([bed, railL, railR, shaft, w1, w2, w3, w4]);
}

function barrelGeo(): THREE.BufferGeometry {
  const body = new THREE.CylinderGeometry(0.42, 0.46, 0.95, 10);
  body.translate(0, 0.48, 0);
  const rim = new THREE.TorusGeometry(0.44, 0.035, 6, 12);
  rim.rotateX(Math.PI / 2);
  rim.translate(0, 0.9, 0);
  const rim2 = new THREE.TorusGeometry(0.45, 0.035, 6, 12);
  rim2.rotateX(Math.PI / 2);
  rim2.translate(0, 0.12, 0);
  return mergeGeos([body, rim, rim2]);
}

function crateGeo(): THREE.BufferGeometry {
  const box = new THREE.BoxGeometry(0.95, 0.78, 0.95);
  box.translate(0, 0.39, 0);
  const band = new THREE.BoxGeometry(1.02, 0.08, 1.02);
  band.translate(0, 0.39, 0);
  return mergeGeos([box, band]);
}

function lanternGeo(): THREE.BufferGeometry {
  const pole = new THREE.CylinderGeometry(0.055, 0.08, 2.15, 6);
  pole.translate(0, 1.08, 0);
  const arm = new THREE.BoxGeometry(0.55, 0.06, 0.06);
  arm.translate(0.22, 2.05, 0);
  const cage = new THREE.BoxGeometry(0.28, 0.34, 0.28);
  cage.translate(0.48, 1.82, 0);
  return mergeGeos([pole, arm, cage]);
}

function rockGeo(): THREE.BufferGeometry {
  const g = new THREE.DodecahedronGeometry(0.55, 0);
  g.scale(1.15, 0.62, 0.95);
  g.translate(0, 0.28, 0);
  g.computeVertexNormals();
  return g;
}

export class DressingStreamer {
  private chunks: {
    x: number;
    z: number;
    items: DressingItem[];
    meshes: THREE.Object3D[];
  }[] = [];
  private geos: THREE.BufferGeometry[] = [];
  private mats: THREE.Material[] = [];
  private cell = 192;
  private draw = 280 * 280;
  private unload = 380 * 380;
  private typeCount = 10;

  constructor(
    private scene: THREE.Scene,
    env: EnvTextures,
    data: DressingData,
    private heightAt: (x: number, z: number) => number,
  ) {
    this.geos = [
      crossBillboard(7.6, 9.4),
      crossBillboard(3.4, 2.7),
      barrelGeo(),
      crateGeo(),
      lanternGeo(),
      new THREE.PlaneGeometry(1.15, 1.85),
      stallGeo(),
      crossBillboard(1.35, 1.15),
      rockGeo(),
      cartGeo(),
    ];
    const treeMat = (map: THREE.Texture, cut = 0.28) =>
      new THREE.MeshLambertMaterial({ map, alphaTest: cut, side: THREE.DoubleSide, transparent: false });
    const woodMat = new THREE.MeshPhongMaterial({
      map: env.wood,
      color: 0xc8a070,
      shininess: 18,
      specular: 0x2a1c10,
    });
    this.mats = [
      treeMat(env.tree0),
      treeMat(env.bush),
      new THREE.MeshPhongMaterial({
        map: env.wood,
        color: 0xb8925a,
        shininess: 22,
        specular: 0x332211,
      }),
      new THREE.MeshPhongMaterial({
        map: env.wood,
        color: 0x9a7448,
        shininess: 16,
        specular: 0x22180e,
      }),
      new THREE.MeshPhongMaterial({ color: 0x4a3a28, shininess: 8, emissive: 0x3a2208, emissiveIntensity: 0.28 }),
      new THREE.MeshLambertMaterial({ map: env.cloth, side: THREE.DoubleSide, alphaTest: 0.12 }),
      woodMat,
      env.tuft
        ? treeMat(env.tuft, 0.48)
        : new THREE.MeshLambertMaterial({ color: 0x4a7a28, alphaTest: 0.2, side: THREE.DoubleSide }),
      new THREE.MeshPhongMaterial({ map: env.stone, color: 0xb0a898, shininess: 10, specular: 0x222018 }),
      new THREE.MeshPhongMaterial({ map: env.wood, color: 0xa07848, shininess: 14 }),
    ];
    const extraTree = treeMat(env.tree1);
    const extraTree2 = treeMat(env.tree2);
    const buckets = new Map<string, DressingItem[]>();
    for (const raw of data.items) {
      const item: DressingItem = { t: raw[0], x: raw[1], z: raw[2], ry: raw[3] };
      if (item.t === 7 && (item.x - 5000) * (item.x - 5000) + (item.z - 5800) * (item.z - 5800) < 12 * 12) continue;
      const key = `${Math.floor(item.x / this.cell)}:${Math.floor(item.z / this.cell)}`;
      let list = buckets.get(key);
      if (!list) {
        list = [];
        buckets.set(key, list);
      }
      list.push(item);
    }
    for (const list of buckets.values()) {
      let sx = 0;
      let sz = 0;
      for (const i of list) {
        sx += i.x;
        sz += i.z;
      }
      this.chunks.push({ x: sx / list.length, z: sz / list.length, items: list, meshes: [] });
    }
    this.mats.push(extraTree, extraTree2);
  }

  update(px: number, pz: number): void {
    for (const chunk of this.chunks) {
      const dx = chunk.x - px;
      const dz = chunk.z - pz;
      const d2 = dx * dx + dz * dz;
      if (d2 < this.draw) this.mount(chunk);
      else if (d2 > this.unload) this.unmount(chunk);
    }
  }

  private mount(chunk: (typeof this.chunks)[number]): void {
    if (chunk.meshes.length) return;
    const byType: DressingItem[][] = Array.from({ length: this.typeCount }, () => []);
    for (const it of chunk.items) {
      if (it.t >= 0 && it.t < this.typeCount) byType[it.t].push(it);
    }
    const quat = new THREE.Quaternion();
    const pos = new THREE.Vector3();
    const scl = new THREE.Vector3();
    const matrix = new THREE.Matrix4();
    const yAxis = new THREE.Vector3(0, 1, 0);
    const place = (t: number, list: DressingItem[], mat: THREE.Material): void => {
      const mesh = new THREE.InstancedMesh(this.geos[t], mat, list.length);
      for (let i = 0; i < list.length; i++) {
        const it = list[i];
        const y = this.heightAt(it.x, it.z);
        pos.set(it.x, y, it.z);
        quat.setFromAxisAngle(yAxis, it.ry);
        let s = 1;
        if (t === 0) s = 0.88 + ((Math.abs(it.x * 0.13 + it.z) * 10) % 50) / 100;
        else if (t === 1) s = 0.78 + (i % 6) * 0.07;
        else if (t === 7) s = 0.7 + (i % 5) * 0.12;
        else if (t === 8) s = 0.7 + (i % 8) * 0.12;
        else if (t === 6) s = 0.92 + (i % 4) * 0.05;
        scl.set(s, s, s);
        matrix.compose(pos, quat, scl);
        mesh.setMatrixAt(i, matrix);
      }
      mesh.instanceMatrix.needsUpdate = true;
      mesh.frustumCulled = false;
      this.scene.add(mesh);
      chunk.meshes.push(mesh);
    };
    for (let t = 0; t < this.typeCount; t++) {
      const list = byType[t];
      if (!list.length) continue;
      if (t === 0) {
        const groups: DressingItem[][] = [[], [], []];
        for (const it of list) groups[Math.abs(Math.floor(it.x + it.z * 3)) % 3].push(it);
        const treeMats = [this.mats[0], this.mats[10], this.mats[11]];
        groups.forEach((g, i) => {
          if (g.length) place(0, g, treeMats[i]);
        });
        continue;
      }
      place(t, list, this.mats[t]);
      if (t === 4) {
        const lamps = new THREE.InstancedMesh(
          new THREE.SphereGeometry(0.14, 8, 6),
          new THREE.MeshBasicMaterial({ color: 0xffd089 }),
          list.length,
        );
        for (let i = 0; i < list.length; i++) {
          const it = list[i];
          pos.set(it.x + Math.cos(it.ry) * 0.48, this.heightAt(it.x, it.z) + 1.82, it.z + Math.sin(it.ry) * 0.48);
          quat.identity();
          scl.set(1, 1, 1);
          matrix.compose(pos, quat, scl);
          lamps.setMatrixAt(i, matrix);
        }
        lamps.instanceMatrix.needsUpdate = true;
        lamps.frustumCulled = false;
        this.scene.add(lamps);
        chunk.meshes.push(lamps);
      }
    }
  }

  private unmount(chunk: (typeof this.chunks)[number]): void {
    for (const m of chunk.meshes) {
      this.scene.remove(m);
      (m as THREE.InstancedMesh).dispose();
    }
    chunk.meshes = [];
  }

  dispose(): void {
    for (const chunk of this.chunks) this.unmount(chunk);
  }
}
