package com.opensilkroadmap.app.world;

import java.util.List;
import java.util.Map;

/**
 * A character pose: one per-bone local rotation ([x,y,z,w] quaternion) and
 * translation, matching the proven BAN channel space (Phase 19) where the
 * channel replaces the bind {@code rot_parent}/{@code tr_parent}.
 *
 * <p>Two factories:
 * <ul>
 *   <li>{@link #bind(CharacterMeshIndex.Skeleton)} — the bind pose (bone
 *       {@code rotParent}/{@code trParent}); skinning with it reproduces the
 *       stored rest vertices (Phase 18/19 proven).</li>
 *   <li>{@link #sample(CharacterMeshIndex.Skeleton, Map, int)} — a pose
 *       sampled from a committed animation JSON ({@code anim/*.json}) at a
 *       millisecond timestamp, using slerp(quat) + lerp(pos). Bones absent
 *       from the clip keep their bind local transform.</li>
 * </ul>
 *
 * <p>Pure data + math; no Android, no rendering.
 */
public final class Pose {

  public final int boneCount;
  private final float[][] rot;
  private final float[][] pos;

  private Pose(int boneCount, float[][] rot, float[][] pos) {
    this.boneCount = boneCount;
    this.rot = rot;
    this.pos = pos;
  }

  /** Local rotation of bone {@code i} (4 floats, [x,y,z,w]). */
  public float[] rot(int i) {
    return rot[i];
  }

  /** Local translation of bone {@code i} (3 floats). */
  public float[] pos(int i) {
    return pos[i];
  }

  /** The bind pose: every bone at its {@code rotParent}/{@code trParent}. */
  public static Pose bind(CharacterMeshIndex.Skeleton s) {
    int n = s.boneCount;
    float[][] r = new float[n][];
    float[][] p = new float[n][];
    for (int i = 0; i < n; i++) {
      r[i] = s.bone(i).rotParent.clone();
      p[i] = s.bone(i).trParent.clone();
    }
    return new Pose(n, r, p);
  }

  /**
   * Samples a pose from a committed animation JSON at {@code tMs} (clamped).
   * The JSON shape is the Phase 19 full-keyframe export:
   * {@code {"timestamps": [...], "channels": {boneName: [[q(4), p(3)], ...]}}}
   * where each channel has exactly {@code timestamps.length} keyframes.
   */
  public static Pose sample(CharacterMeshIndex.Skeleton s,
                            Map<String, Object> animJson, int tMs) {
    List<?> tsList = (List<?>) animJson.get("timestamps");
    int kf = tsList.size();
    float[] ts = new float[kf];
    for (int i = 0; i < kf; i++) {
      ts[i] = ((Number) tsList.get(i)).floatValue();
    }
    Map<String, Object> channels = (Map<String, Object>) animJson.get("channels");
    int n = s.boneCount;
    float[][] r = new float[n][];
    float[][] p = new float[n][];
    for (int i = 0; i < n; i++) {
      String name = s.bone(i).name;
      Object chObj = channels.get(name);
      if (chObj == null) {
        r[i] = s.bone(i).rotParent.clone();
        p[i] = s.bone(i).trParent.clone();
        continue;
      }
      List<?> ch = (List<?>) chObj;
      float[] q;
      float[] pos;
      float t = (float) tMs;
      if (t <= ts[0]) {
        q = keyQ(ch.get(0));
        pos = keyP(ch.get(0));
      } else if (t >= ts[kf - 1]) {
        q = keyQ(ch.get(kf - 1));
        pos = keyP(ch.get(kf - 1));
      } else {
        int hi = 0;
        while (hi < kf - 1 && ts[hi] < t) {
          hi++;
        }
        int lo = hi > 0 ? hi - 1 : 0;
        float t0 = ts[lo];
        float t1 = ts[hi];
        float f = (t1 == t0) ? 0f : (t - t0) / (t1 - t0);
        if (f <= 0f) {
          q = keyQ(ch.get(lo));
          pos = keyP(ch.get(lo));
        } else if (f >= 1f) {
          q = keyQ(ch.get(hi));
          pos = keyP(ch.get(hi));
        } else {
          float[] q0 = keyQ(ch.get(lo));
          float[] q1 = keyQ(ch.get(hi));
          float[] p0 = keyP(ch.get(lo));
          float[] p1 = keyP(ch.get(hi));
          q = slerp(q0, q1, f);
          pos = new float[]{
              p0[0] + f * (p1[0] - p0[0]),
              p0[1] + f * (p1[1] - p0[1]),
              p0[2] + f * (p1[2] - p0[2])};
        }
      }
      r[i] = q;
      p[i] = pos;
    }
    return new Pose(n, r, p);
  }

  private static float[] keyQ(Object kf) {
    List<?> k = (List<?>) kf;
    List<?> q = (List<?>) k.get(0);
    return new float[]{
        ((Number) q.get(0)).floatValue(),
        ((Number) q.get(1)).floatValue(),
        ((Number) q.get(2)).floatValue(),
        ((Number) q.get(3)).floatValue()};
  }

  private static float[] keyP(Object kf) {
    List<?> k = (List<?>) kf;
    List<?> p = (List<?>) k.get(1);
    return new float[]{
        ((Number) p.get(0)).floatValue(),
        ((Number) p.get(1)).floatValue(),
        ((Number) p.get(2)).floatValue()};
  }

  /** Spherical interpolation between [x,y,z,w] quaternions (short arc). */
  static float[] slerp(float[] a, float[] b, float t) {
    float dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
    float bx = b[0];
    float by = b[1];
    float bz = b[2];
    float bw = b[3];
    if (dot < 0f) {
      bx = -bx;
      by = -by;
      bz = -bz;
      bw = -bw;
      dot = -dot;
    }
    float[] out = new float[4];
    if (dot > 0.9995f) {
      out[0] = a[0] + t * (bx - a[0]);
      out[1] = a[1] + t * (by - a[1]);
      out[2] = a[2] + t * (bz - a[2]);
      out[3] = a[3] + t * (bw - a[3]);
      float n = (float) Math.sqrt(
          out[0] * out[0] + out[1] * out[1] + out[2] * out[2] + out[3] * out[3]);
      if (n > 0f) {
        out[0] /= n;
        out[1] /= n;
        out[2] /= n;
        out[3] /= n;
      }
      return out;
    }
    double theta = Math.acos(Math.max(-1.0, Math.min(1.0, dot)));
    double sinTheta = Math.sin(theta);
    double s0 = Math.sin((1.0 - t) * theta) / sinTheta;
    double s1 = Math.sin(t * theta) / sinTheta;
    out[0] = (float) (s0 * a[0] + s1 * bx);
    out[1] = (float) (s0 * a[1] + s1 * by);
    out[2] = (float) (s0 * a[2] + s1 * bz);
    out[3] = (float) (s0 * a[3] + s1 * bw);
    return out;
  }
}
