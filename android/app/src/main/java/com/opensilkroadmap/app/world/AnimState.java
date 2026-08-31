package com.opensilkroadmap.app.world;

/**
 * Proven character animation states, derived from the original SRO animation
 * names exported in the committed manifests ({@code stand}, {@code walk},
 * {@code run}, {@code attack}, {@code damage}, {@code die}).
 *
 * <p>Only these states are modeled because only these are proven present in
 * the source {@code .ban} clips. States not present in a character's manifest
 * are resolved to no clip (MISSING) rather than invented. {@link #looping()}
 * classifies a state as a continuous loop (idle/walk/run) or a one-shot
 * (attack/damage/death).
 */
public enum AnimState {
  IDLE(true),
  WALK(true),
  RUN(true),
  ATTACK(false),
  DAMAGE(false),
  DEATH(false);

  private final boolean looping;

  AnimState(boolean looping) {
    this.looping = looping;
  }

  /** True for continuous states, false for one-shot states. */
  public boolean looping() {
    return looping;
  }
}
