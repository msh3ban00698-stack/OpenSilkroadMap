import * as THREE from "three";

export function releaseRenderer(renderer: THREE.WebGLRenderer): void {
  try {
    renderer.forceContextLoss();
  } catch {
    const gl = renderer.getContext();
    try {
      gl?.getExtension("WEBGL_lose_context")?.loseContext();
    } catch {
      // ignore
    }
  }
  renderer.dispose();
}
