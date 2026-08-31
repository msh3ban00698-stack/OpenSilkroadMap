package com.opensilkroadmap.app.world;

/**
 * Proven character animation states, derived from the original SRO animation
 * names in the source {@code .ban} corpus (Data.pk2, 4,691 clips) and the
 * committed manifests ({@code stand}, {@code walk}, {@code run},
 * {@code attack}, {@code damage}, {@code die}, {@code down}, {@code wakeup}).
 *
 * <p>Only these states are modeled because only these are proven present in
 * the source {@code .ban} clips. States not present in a character's manifest
 * are resolved to no clip (MISSING) rather than invented. {@link #looping()}
 * classifies a state as a continuous loop (idle/walk/run) or a one-shot
 * (attack/damage/death/down/wakeup).
 *
 * <p>DOWN (knockdown) and WAKEUP (recovery) are proven by the {@code down}
 * (131 clips), {@code downwait} (30), {@code downup} (19) and {@code wakeup}
 * (17) animation name groups. The transition order among down/downwait/wakeup
 * is client code and UNKNOWN; only the state existence and its clip are
 * modeled.
 */
public enum AnimState {
  IDLE(true),
  WALK(true),
  RUN(true),
  ATTACK(false),
  DAMAGE(false),
  DEATH(false),
  DOWN(false),
  WAKEUP(false);

  private final boolean looping;

  AnimState(boolean looping) {
    this.looping = looping;
  }

  /** True for continuous states, false for one-shot states. */
  public boolean looping() {
    return looping;
  }
}
