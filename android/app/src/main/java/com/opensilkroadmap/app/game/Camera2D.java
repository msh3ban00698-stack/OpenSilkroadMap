package com.opensilkroadmap.app.game;

/**
 * Axis-aligned follow camera for the Android camera foundation.
 *
 * <p>Pure math (no game behavior): centers the view on a target position and
 * clamps so the view stays inside the world bounds. When the view is larger
 * than the world it centers on the world instead. World units are generic and
 * UNKNOWN from source; the clamp contract is fully deterministic and tested.
 */
public final class Camera2D {
  private double x;
  private double y;
  private double viewW;
  private double viewH;
  private double worldW;
  private double worldH;

  public void setViewport(double w, double h) {
    this.viewW = Math.max(0, w);
    this.viewH = Math.max(0, h);
    clamp();
  }

  public void setWorld(double w, double h) {
    this.worldW = Math.max(0, w);
    this.worldH = Math.max(0, h);
    clamp();
  }

  public void follow(double targetX, double targetY) {
    x = targetX;
    y = targetY;
    clamp();
  }

  private void clamp() {
    x = clampAxis(x, viewW, worldW);
    y = clampAxis(y, viewH, worldH);
  }

  private static double clampAxis(double center, double view, double world) {
    if (view <= 0 || world <= 0) {
      return 0;
    }
    if (view >= world) {
      return world / 2.0;
    }
    double half = view / 2.0;
    return Math.max(half, Math.min(world - half, center));
  }

  public double x() {
    return x;
  }

  public double y() {
    return y;
  }
}
