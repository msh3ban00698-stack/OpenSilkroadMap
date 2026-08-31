package com.opensilkroadmap.app.game;

/**
 * Player movement speed configuration for the native runtime.
 *
 * <p>Fail-closed: the real VSRO walk/run/combat speeds and tick rules are
 * UNKNOWN from the supplied source (no CharacterData/SkillData movement values
 * exist in the inventory; only real clip durations are proven). The runtime
 * therefore defaults to an UNKNOWN speed: {@link #speedProven()} is false and
 * {@link #walkSpeedUnitsPerSecond()} is {@link #SPEED_UNKNOWN}. Movement
 * transitions still play the proven locomotion clip, but displacement is not
 * fabricated.
 *
 * <p>A speed may only be introduced from a future verified source via
 * {@link #withWalkSpeed(double)}. Pure JVM, no Android.
 */
public final class PlayerMovementConfig {

  /** Sentinel for an unproven walk speed (world units per second). */
  public static final double SPEED_UNKNOWN = Double.NaN;

  private final boolean speedProven;
  private final double walkSpeed;

  private PlayerMovementConfig(boolean speedProven, double walkSpeed) {
    this.speedProven = speedProven;
    this.walkSpeed = walkSpeed;
  }

  /** The only config constructible from the current evidence: UNKNOWN speed. */
  public static PlayerMovementConfig unknownSpeed() {
    return new PlayerMovementConfig(false, SPEED_UNKNOWN);
  }

  /** Builds a speed config from a verified source (world units per second). */
  public static PlayerMovementConfig withWalkSpeed(double unitsPerSecond) {
    if (!(unitsPerSecond > 0.0)) {
      throw new IllegalArgumentException("walk speed must be positive");
    }
    return new PlayerMovementConfig(true, unitsPerSecond);
  }

  public boolean speedProven() {
    return speedProven;
  }

  public double walkSpeedUnitsPerSecond() {
    return walkSpeed;
  }
}
