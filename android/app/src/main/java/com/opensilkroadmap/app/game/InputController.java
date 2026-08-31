package com.opensilkroadmap.app.game;

/**
 * Pure-JVM input intent accumulator for the native runtime.
 *
 * <p>Translates raw input gestures into per-frame intents consumed by the game
 * host: a one-finger drag pans the camera, a two-finger pinch zooms it, and a
 * virtual joystick produces a movement direction. This class is Android-free so
 * the intent math is unit-testable; the native {@code View} feeds it from
 * {@code MotionEvent} and drains it each frame.
 *
 * <p>Movement is a NORMALIZED direction only (components in [-1, 1], generic
 * units). Speed and world-unit conversion are deliberately NOT encoded here:
 * the real VSRO movement/tick rules are UNKNOWN from source and are applied by
 * the game-state consumer, not invented in the input layer.
 */
public final class InputController {
  /** Joystick dead zone as a fraction of the joystick radius. */
  public static final float JOYSTICK_DEAD_ZONE = 0.15f;

  private float panX;
  private float panY;
  private float zoom = 1f;
  private float moveX;
  private float moveY;

  /** Accumulates a one-finger drag in view pixels (positive dx = drag right). */
  public void drag(float dxPixels, float dyPixels) {
    panX += dxPixels;
    panY += dyPixels;
  }

  /** Accumulates a pinch as a multiplicative zoom factor (> 0). */
  public void pinchZoom(float factor) {
    if (factor > 0f) {
      zoom *= factor;
    }
  }

  /** Sets the joystick movement direction; components are clamped to [-1, 1]. */
  public void setMove(float x, float y) {
    moveX = clampUnit(x);
    moveY = clampUnit(y);
  }

  /**
   * Maps a joystick drag (pixels from the touch origin) to a normalized move
   * intent. The direction is normalized; the magnitude is analog up to the
   * radius (beyond it clamps to 1). Drags inside the dead zone zero the move.
   * Generic structural math — no authentic VSRO joystick curve is claimed.
   */
  public void joystick(float dxPixels, float dyPixels, float radiusPixels) {
    float r = radiusPixels > 0f ? radiusPixels : 1f;
    float nx = dxPixels / r;
    float ny = dyPixels / r;
    float len = (float) Math.sqrt(nx * nx + ny * ny);
    if (len <= JOYSTICK_DEAD_ZONE) {
      moveX = 0f;
      moveY = 0f;
      return;
    }
    float mag = Math.min(1f, len);
    moveX = clampUnit((nx / len) * mag);
    moveY = clampUnit((ny / len) * mag);
  }

  /** Drains and resets the accumulated pan (view pixels, x axis). */
  public float consumePanX() {
    float v = panX;
    panX = 0f;
    return v;
  }

  /** Drains and resets the accumulated pan (view pixels, y axis). */
  public float consumePanY() {
    float v = panY;
    panY = 0f;
    return v;
  }

  /** Drains and resets the accumulated zoom factor (multiplicative, >= 1 or < 1). */
  public float consumeZoom() {
    float v = zoom;
    zoom = 1f;
    return v;
  }

  public float moveX() {
    return moveX;
  }

  public float moveY() {
    return moveY;
  }

  public void reset() {
    panX = 0f;
    panY = 0f;
    zoom = 1f;
    moveX = 0f;
    moveY = 0f;
  }

  private static float clampUnit(float v) {
    return Math.max(-1f, Math.min(1f, v));
  }
}
