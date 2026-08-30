package com.opensilkroadmap.app.game;

/**
 * Fixed-timestep accumulator for the Android runtime/game-loop foundation.
 *
 * <p>Pure engine plumbing (no game behavior): consumes a varying frame delta
 * and reports how many fixed updates to run. Catch-up is bounded so a stalled
 * frame never floods the update step.
 */
public final class GameLoop {
  public static final double DEFAULT_FIXED_DT_SECONDS = 0.05;
  public static final double DEFAULT_MAX_CATCH_UP_SECONDS = 0.25;

  private final double fixedDt;
  private final double maxCatchUp;
  private double accumulator;
  private long steps;
  private double elapsed;

  public GameLoop() {
    this(DEFAULT_FIXED_DT_SECONDS, DEFAULT_MAX_CATCH_UP_SECONDS);
  }

  public GameLoop(double fixedDtSeconds, double maxCatchUpSeconds) {
    if (fixedDtSeconds <= 0) {
      throw new IllegalArgumentException("fixedDtSeconds must be positive");
    }
    this.fixedDt = fixedDtSeconds;
    this.maxCatchUp = Math.max(fixedDtSeconds, maxCatchUpSeconds);
  }

  public double fixedDtSeconds() {
    return fixedDt;
  }

  /** Feeds a frame delta; returns the number of fixed updates to run. */
  public int advance(double deltaSeconds) {
    if (deltaSeconds <= 0) {
      return 0;
    }
    elapsed += deltaSeconds;
    accumulator = Math.min(accumulator + deltaSeconds, maxCatchUp);
    int n = 0;
    while (accumulator >= fixedDt) {
      accumulator -= fixedDt;
      n++;
    }
    steps += n;
    return n;
  }

  public long steps() {
    return steps;
  }

  public double elapsedSeconds() {
    return elapsed;
  }

  public void reset() {
    accumulator = 0;
    steps = 0;
    elapsed = 0;
  }
}
