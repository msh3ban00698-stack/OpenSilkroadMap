package com.opensilkroadmap.app.game;

/**
 * Axis-aligned follow camera for the Android camera foundation.
 *
 * <p>Pure math (no game behavior): centers the view on a target position and
 * clamps so the view stays inside the world bounds. When the view is larger
 * than the world it centers on the world instead. World units are generic and
 * UNKNOWN from source; the clamp and projection contracts are fully
 * deterministic and tested.
 *
 * <p>This is GENERIC 2D camera mechanics (not claimed to be authentic Silkroad
 * camera math): a top-down projection where world +X maps to screen +X and
 * world +Y maps to screen -Y, scaled by a pixels-per-unit zoom. The projection
 * convention matches {@code WorldProjection.worldToView} so the native world
 * renderer can delegate to this single source of truth.
 */
public final class Camera2D {
  private double x;
  private double y;
  private double viewW;
  private double viewH;
  private double worldW;
  private double worldH;
  private double scale = 1.0;

  /** Viewport size in screen pixels (>= 0). */
  public void setViewport(double w, double h) {
    this.viewW = Math.max(0, w);
    this.viewH = Math.max(0, h);
    clamp();
  }

  /** World bounds in world units (>= 0). */
  public void setWorld(double w, double h) {
    this.worldW = Math.max(0, w);
    this.worldH = Math.max(0, h);
    clamp();
  }

  /** Zoom: pixels per world unit (> 0). */
  public void setScale(double pixelsPerUnit) {
    this.scale = pixelsPerUnit > 0 ? pixelsPerUnit : 1.0;
    clamp();
  }

  /**
   * Pixels-per-world-unit that covers the viewport (no letterbox). Uses the
   * larger of width/height ratios so the world fills the surface; the taller
   * or wider axis is cropped rather than padded.
   */
  public static double coverScale(double viewW, double viewH, double worldW, double worldH) {
    if (viewW <= 0 || viewH <= 0 || worldW <= 0 || worldH <= 0) {
      return 1.0;
    }
    return Math.max(viewW / worldW, viewH / worldH);
  }

  public double scale() {
    return scale;
  }

  /** Follow a world-space target; the center is clamped to world bounds. */
  public void follow(double targetX, double targetY) {
    x = targetX;
    y = targetY;
    clamp();
  }

  /**
   * Region transition: adopt new world bounds and snap the center to the new
   * region's origin, then re-clamp. Generic: the caller supplies the region's
   * world bounds; no region semantics are invented here.
   */
  public void enterRegion(double centerX, double centerY, double w, double h) {
    this.worldW = Math.max(0, w);
    this.worldH = Math.max(0, h);
    this.x = centerX;
    this.y = centerY;
    clamp();
  }

  /** World point to viewport pixel offset from the top-left of the view. */
  public double[] worldToView(double worldX, double worldY) {
    double px = (worldX - x) * scale + viewW / 2.0;
    double py = (y - worldY) * scale + viewH / 2.0;
    return new double[] {px, py};
  }

  /** Viewport pixel (top-left origin) back to world point. */
  public double[] viewToWorld(double px, double py) {
    double worldX = x + (px - viewW / 2.0) / scale;
    double worldY = y - (py - viewH / 2.0) / scale;
    return new double[] {worldX, worldY};
  }

  private void clamp() {
    x = clampAxis(x, viewW, worldW);
    y = clampAxis(y, viewH, worldH);
  }

  private double clampAxis(double center, double view, double world) {
    if (scale <= 0 || view <= 0 || world <= 0) {
      return 0;
    }
    double viewWorld = view / scale;
    if (viewWorld >= world) {
      return world / 2.0;
    }
    double half = viewWorld / 2.0;
    return Math.max(half, Math.min(world - half, center));
  }

  public double x() {
    return x;
  }

  public double y() {
    return y;
  }
}
