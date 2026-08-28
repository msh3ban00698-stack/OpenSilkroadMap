/// <reference lib="deno.ns" />
import { assert, assertAlmostEquals } from "jsr:@std/assert@1";
import * as THREE from "three";
import type { CharacterAssets } from "./character_loader.ts";
import { assembleCharacter } from "./character_rig.ts";

function fakeAssets(): CharacterAssets {
  return {
    skeleton: {
      names: ["root", "child"],
      parents: [-1, 0],
      bindRot: [0, 0, 0, 1, 0, 0, 0, 1],
      bindPos: [0, 10, 0, 0, 5, 0],
    },
    meshes: [
      {
        id: "body",
        tex: null,
        render: "opaque",
        pos: [0, 0, 0, 1, 0, 0, 0, 10, 0],
        nrm: [0, 1, 0, 0, 1, 0, 0, 1, 0],
        uv: [0, 0, 1, 0, 0, 1],
        sk: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        sw: [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        idx: [0, 1, 2],
      },
    ],
    anims: [],
    meta: {
      preset: "test",
      name: "test",
      bones: 2,
      meshes: 1,
      height: 15,
      scale: 0.15,
    },
    textures: new Map(),
  };
}

function matrixUniformScale(m: THREE.Matrix4): number {
  const e = m.elements;
  return Math.hypot(e[0], e[1], e[2]);
}

Deno.test("character bind inverses stay in unscaled bind space", () => {
  const { group, skeleton } = assembleCharacter(fakeAssets(), 0.15);
  assert(skeleton);
  const invScale = matrixUniformScale(skeleton.boneInverses[0]);
  assertAlmostEquals(invScale, 1, 1e-5);
  assertAlmostEquals(group.scale.x, 0.15, 1e-6);
  const root = skeleton.bones[0];
  const world = new THREE.Vector3();
  group.updateMatrixWorld(true);
  root.getWorldPosition(world);
  assertAlmostEquals(world.y, 1.5, 1e-5);
});

Deno.test("bone-local exclusive meshes are promoted into model space before bind", () => {
  const assets = fakeAssets();
  assets.skeleton.names = ["root", "hand"];
  assets.skeleton.parents = [-1, 0];
  assets.skeleton.bindPos = [0, 10, 0, 0, 5, 0];
  assets.meshes.push({
    id: "sword",
    tex: null,
    render: "opaque",
    pos: [0, 0, 0, 0, 0, -2, 0, 0.2, -1],
    nrm: [0, 1, 0, 0, 1, 0, 0, 1, 0],
    uv: [0, 0, 1, 0, 0, 1],
    sk: [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    sw: [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    idx: [0, 1, 2],
  });
  const { meshes, group } = assembleCharacter(assets, 0.15);
  const pos = meshes[1].geometry.getAttribute("position");
  const y0 = pos.getY(0);
  assert(y0 > 10, `sword vertex should sit at the hand, got y=${y0}`);
  group.updateMatrixWorld(true);
  const v = new THREE.Vector3().fromBufferAttribute(pos, 0);
  meshes[1].localToWorld(v);
  assertAlmostEquals(v.y, 2.25, 1e-4);
});
