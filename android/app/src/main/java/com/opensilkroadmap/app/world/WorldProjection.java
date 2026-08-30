package com.opensilkroadmap.app.world;

/**
 * Pure view/world projection math for the native terrain renderer.
 *
 * <p>View space is a top-down camera: world +X maps to screen +X and world +Z
 * maps to screen -Y, scaled by {@code pixelsPerUnit}. Height is rendered as a
 * monotonic grayscale ramp between a region's real min and max so that higher
 * terrain is visibly brighter with no invented palette.
 */
public final class WorldProjection {
  private WorldProjection() {}

  /** Top-down camera: world (x, z) -> view (px, py). */
  public static float[] worldToView(float worldX, float worldZ, float camX, float camZ, float ppu) {
    return new float[] {(worldX - camX) * ppu, (camZ - worldZ) * ppu};
  }

  /** Monotonic grayscale ramp over [min, max]; clamped, ARGB opaque. */
  public static int heightColor(float h, float min, float max) {
    float t = 0f;
    if (max > min) {
      t = (h - min) / (max - min);
    }
    t = t < 0f ? 0f : (t > 1f ? 1f : t);
    int g = (int) (0xFF * t);
    return 0xFF000000 | (g << 16) | (g << 8) | g;
  }

  /** Opaque RGB from a packed ARGB color. */
  public static int opaque(int argb) {
    return argb | 0xFF000000;
  }
}
