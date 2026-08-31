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
