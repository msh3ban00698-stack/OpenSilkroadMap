package com.opensilkroadmap.app.game;

/**
 * Pure movement integration for the player (world x/z only).
 *
 * <p>Transforms a normalized input direction into a world displacement. The
 * world axes follow the proven projection convention of
 * {@code Camera2D}/{@code WorldProjection}: screen +X is world +X, screen +Y is
 * world -Z, so a joystick pushed up (moveY = -1 in the renderer's
 * top-left-origin view) faces world -Z.
 *
 * <p>Fail-closed: without a proven speed ({@link PlayerMovementConfig#speedProven()})
 * the step reports {@code moved=false} with reason {@code UNKNOWN_SPEED} — no
 * displacement is fabricated. A zero input direction reports
 * {@code ZERO_DIRECTION}. The heading is the inverse of the PROVEN placement
 * rotation used by {@code NativeWorldRenderer.worldVertex}
 * ({@code local +Z -> (sin h, cos h) world}), so a heading h faces the world
 * direction {@code (sin h, cos h)}.
 *
 * <p>Pure JVM, no Android. Movement is structural math; no authentic speed is
 * claimed.
 */
public final class PlayerMover {

  /** Reason a step produced no displacement. */
  public static final String REASON_ZERO_DIRECTION = "ZERO_DIRECTION";
  /** Reason a step produced no displacement: speed not proven from source. */
  public static final String REASON_UNKNOWN_SPEED = "UNKNOWN_SPEED";
  /** Reason a step applied the proven displacement. */
  public static final String REASON_MOVED = "MOVED";

  /** One integration step result. */
  public static final class Step {
    /** Normalized world direction (unit length when direction was non-zero). */
    public final float dirX;
    public final float dirZ;
    /** Applied world displacement in world units (0 when not moved). */
    public final double dx;
    public final double dz;
    public final boolean moved;
    public final String reason;

    Step(float dirX, float dirZ, double dx, double dz, boolean moved, String reason) {
      this.dirX = dirX;
      this.dirZ = dirZ;
      this.dx = dx;
      this.dz = dz;
      this.moved = moved;
      this.reason = reason;
    }
  }

  private PlayerMover() {}

  /** Integrates a direction over a frame; never throws on degenerate input. */
  public static Step step(float dirX, float dirZ, double dt, PlayerMovementConfig cfg) {
    double len = Math.hypot(dirX, dirZ);
    if (!(len > 1e-9)) {
      return new Step(0f, 0f, 0.0, 0.0, false, REASON_ZERO_DIRECTION);
    }
    float nx = (float) (dirX / len);
    float nz = (float) (dirZ / len);
    if (cfg == null || !cfg.speedProven()) {
      return new Step(nx, nz, 0.0, 0.0, false, REASON_UNKNOWN_SPEED);
    }
    double speed = cfg.walkSpeedUnitsPerSecond();
    if (!(speed > 0.0) || !(dt > 0.0)) {
      return new Step(nx, nz, 0.0, 0.0, false, REASON_UNKNOWN_SPEED);
    }
    double dist = speed * dt;
    return new Step(nx, nz, nx * dist, nz * dist, true, REASON_MOVED);
  }

  /**
   * Heading (radians) that faces the given world direction, consistent with the
   * proven placement rotation {@code worldVertex}: rotating local +Z by h maps
   * to world {@code (sin h, cos h)}. {@code atan2(0, 0)} is 0 (no turn).
   */
  public static double headingFromDirection(float dirX, float dirZ) {
    return Math.atan2(dirX, dirZ);
  }
}
