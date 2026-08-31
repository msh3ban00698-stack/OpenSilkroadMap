package com.opensilkroadmap.app.game;

/**
 * Per-character animation clock for the native character runtime.
 *
 * <p>Tracks elapsed time against a single named clip and reports the sample
 * timestamp ({@link #currentTimeMs}) to feed into
 * {@code CharacterMeshIndex.poseAt(name, tMs)}. Pure engine plumbing with no
 * game behavior: the clip name, duration, and loop flag all come from a
 * character's committed manifest animation metadata (real {@code .ban}
 * durations), never from an invented table.
 *
 * <p>Looping wraps elapsed time back into {@code [0, durationMs)} so a stand or
 * idle clip repeats seamlessly; a non-looping clip clamps at its final frame.
 * The wrap is a modulo over real milliseconds only, so no sampling offset is
 * fabricated.
 */
public final class AnimationPlayer {

  private String name = "";
  private int durationMs;
  private boolean looping = true;
  private double elapsedMs;

  public AnimationPlayer() {}

  /** Selects a looping clip (stand/idle default) and resets elapsed time. */
  public void setClip(String name, int durationMs) {
    setClip(name, durationMs, true);
  }

  /** Selects a clip and resets elapsed time. */
  public void setClip(String name, int durationMs, boolean looping) {
    if (durationMs <= 0) {
      throw new IllegalArgumentException("durationMs must be positive");
    }
    this.name = name == null ? "" : name;
    this.durationMs = durationMs;
    this.looping = looping;
    this.elapsedMs = 0.0;
  }

  /** Advances the clock by a frame delta; ignores non-positive deltas. */
  public void advance(double dtSeconds) {
    if (dtSeconds <= 0.0 || durationMs <= 0) {
      return;
    }
    elapsedMs += dtSeconds * 1000.0;
    if (looping) {
      elapsedMs %= durationMs;
    } else if (elapsedMs > durationMs) {
      elapsedMs = durationMs;
    }
  }

  /** Current sample timestamp in milliseconds, clamped to the clip. */
  public int currentTimeMs() {
    if (durationMs <= 0) {
      return 0;
    }
    return (int) elapsedMs;
  }

  public String name() {
    return name;
  }

  public int durationMs() {
    return durationMs;
  }

  public boolean looping() {
    return looping;
  }

  /** True when a non-looping clip has reached its final frame. */
  public boolean isFinished() {
    return !looping && durationMs > 0 && elapsedMs >= durationMs;
  }

  /** Clears any active clip; the player then reports no animation. */
  public void clear() {
    name = "";
    durationMs = 0;
    looping = true;
    elapsedMs = 0.0;
  }

  public void reset() {
    elapsedMs = 0.0;
  }
}
