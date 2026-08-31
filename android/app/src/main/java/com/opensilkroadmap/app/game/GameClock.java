package com.opensilkroadmap.app.game;

/**
 * Monotonic frame clock for the native runtime game loop.
 *
 * <p>Pure engine plumbing (no game behavior): converts a monotonic time source
 * (e.g. {@code System.nanoTime()}) into a per-frame delta in seconds. The delta
 * is clamped so a single stalled frame (or a device suspend/resume gap) never
 * produces a huge jump that the fixed-timestep {@link GameLoop} would otherwise
 * have to absorb. The clamp is an engine-safety bound, not an authentic VSRO
 * timing claim; the real server tick rate is UNKNOWN from source.
 */
public final class GameClock {
  public static final double DEFAULT_MAX_DELTA_SECONDS = 0.1;

  private final double maxDeltaSeconds;
  private Long lastNanos;

  public GameClock() {
    this(DEFAULT_MAX_DELTA_SECONDS);
  }

  public GameClock(double maxDeltaSeconds) {
    if (maxDeltaSeconds <= 0) {
      throw new IllegalArgumentException("maxDeltaSeconds must be positive");
    }
    this.maxDeltaSeconds = maxDeltaSeconds;
  }

  /**
   * Returns the elapsed seconds since the previous {@code tick}, clamped to the
   * configured maximum. The first call (or the first call after {@link #reset()})
   * establishes the baseline and returns {@code 0}.
   */
  public double tick(long nowNanos) {
    if (lastNanos == null) {
      lastNanos = nowNanos;
      return 0.0;
    }
    double dt = (nowNanos - lastNanos) / 1_000_000_000.0;
    lastNanos = nowNanos;
    if (dt <= 0) {
      return 0.0;
    }
    return Math.min(dt, maxDeltaSeconds);
  }

  public double maxDeltaSeconds() {
    return maxDeltaSeconds;
  }

  public void reset() {
    lastNanos = null;
  }
}
