package com.opensilkroadmap.app.world;

import java.io.IOException;

/**
 * Pose-driven character skinning (Phase 19, compile-only target).
 *
 * <p>Chains a {@link Pose} through the {@link CharacterMeshIndex.Skeleton}
 * into per-bone world transforms (mirroring {@code scripts/skeleton.py}
 * {@code bind_world}/{@code chain_world}), then deforms each skinned vertex as
 * {@code sum_i (w_i / sum(w)) * (R_i * v + t_i)}. At the bind pose this is
 * numerically identical to {@link CharacterMeshIndex#skinnedBindPositions},
 * which Phase 19 proved reproduces the stored rest vertices.
 *
 * <p>Quaternion convention is [x,y,z,w] (proven Phase 18/19). Weights are
 * normalized by their vertex sum because Phase 18 proved the raw two-influence
 * sums are not exactly 65535. Fail-closed: a mesh bone absent from the
 * skeleton raises {@link IOException}.
 */
public final class CharacterRenderer {

  private CharacterRenderer() {}

  /** Multiplies two [x,y,z,w] quaternions. */
  public static float[] quatMul(float[] a, float[] b) {
    float ax = a[0];
    float ay = a[1];
    float az = a[2];
    float aw = a[3];
    float bx = b[0];
    float by = b[1];
    float bz = b[2];
    float bw = b[3];
    return new float[]{
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz};
  }

  /** Rotates a vector by a unit [x,y,z,w] quaternion. */
  public static float[] rotate(float[] v, float[] q) {
    float x = q[0];
    float y = q[1];
    float z = q[2];
    float w = q[3];
    float vx = v[0];
    float vy = v[1];
    float vz = v[2];
    float cx = y * vz - z * vy;
    float cy = z * vx - x * vz;
    float cz = x * vy - y * vx;
    float dx = y * cz - z * cy;
    float dy = z * cx - x * cz;
    float dz = x * cy - y * cx;
    return new float[]{
        vx + 2f * w * cx + 2f * dx,
        vy + 2f * w * cy + 2f * dy,
        vz + 2f * w * cz + 2f * dz};
  }

  /**
   * Chains the pose into per-bone world transforms. {@code worldRot} and
   * {@code worldPos} must be pre-allocated to {@code s.boneCount} entries;
   * each entry is replaced with a fresh array.
   */
  public static void chainWorld(CharacterMeshIndex.Skeleton s, Pose pose,
                                float[][] worldRot, float[][] worldPos) {
    int n = s.boneCount;
    for (int i = 0; i < n; i++) {
      String parent = s.bone(i).parent;
      if (parent == null || parent.isEmpty()) {
        worldRot[i] = pose.rot(i).clone();
        worldPos[i] = pose.pos(i).clone();
      } else {
        int p = s.boneIndex(parent);
        if (p < 0) {
          throw new IllegalStateException(
              "parent '" + parent + "' not found for bone " + s.bone(i).name);
        }
        worldRot[i] = quatMul(worldRot[p], pose.rot(i));
        float[] off = rotate(pose.pos(i), worldRot[p]);
        worldPos[i] = new float[]{
            worldPos[p][0] + off[0],
            worldPos[p][1] + off[1],
            worldPos[p][2] + off[2]};
      }
    }
  }

  /**
   * Deforms every mesh vertex at the given pose. Returns a flat
   * {@code [n*3]} positions array (character-local). Fail-closed on a mesh
   * bone absent from the skeleton.
   */
  public static float[] skin(CharacterMeshIndex.Skeleton s, Pose pose,
                             StaticMeshAsset.SkinnedMesh mesh) throws IOException {
    int[] boneMap = new int[mesh.boneNames.length];
    for (int k = 0; k < boneMap.length; k++) {
      int idx = s.boneIndex(mesh.boneNames[k]);
      if (idx < 0) {
        throw new IOException(
            "mesh bone '" + mesh.boneNames[k] + "' not in skeleton");
      }
      boneMap[k] = idx;
    }
    float[][] worldRot = new float[s.boneCount][];
    float[][] worldPos = new float[s.boneCount][];
    chainWorld(s, pose, worldRot, worldPos);

    int n = mesh.vertexCount;
    float[] out = new float[n * 3];
    float[] v = new float[3];
    float[] r = new float[3];
    for (int i = 0; i < n; i++) {
      v[0] = mesh.positions[i * 3];
      v[1] = mesh.positions[i * 3 + 1];
      v[2] = mesh.positions[i * 3 + 2];
      int b1 = mesh.bone1[i];
      int w1 = mesh.weight1[i];
      int b2 = mesh.bone2[i];
      int w2 = mesh.weight2[i];
      int sum = w1 + w2;
      float ox = 0f;
      float oy = 0f;
      float oz = 0f;
      if (b1 < boneMap.length && sum > 0) {
        r = rotate(v, worldRot[boneMap[b1]]);
        float f = (float) w1 / (float) sum;
        ox += f * (r[0] + worldPos[boneMap[b1]][0]);
        oy += f * (r[1] + worldPos[boneMap[b1]][1]);
        oz += f * (r[2] + worldPos[boneMap[b1]][2]);
      }
      if (b2 < boneMap.length && w2 > 0) {
        r = rotate(v, worldRot[boneMap[b2]]);
        float f = (float) w2 / (float) sum;
        ox += f * (r[0] + worldPos[boneMap[b2]][0]);
        oy += f * (r[1] + worldPos[boneMap[b2]][1]);
        oz += f * (r[2] + worldPos[boneMap[b2]][2]);
      }
      out[i * 3] = ox;
      out[i * 3 + 1] = oy;
      out[i * 3 + 2] = oz;
    }
    return out;
  }
}
