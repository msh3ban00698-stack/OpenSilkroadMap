package com.opensilkroadmap.app.world;

import java.io.IOException;

/**
 * One placed character instance in the native runtime: a loaded
 * {@link CharacterMeshIndex} bound to an independent {@link CharacterAnimator}
 * state machine, plus a world position.
 *
 * <p>Every instance owns its own animator, so multiple NPCs of the same model
 * key animate independently. Rendering is Android-side ({@code NativeWorldRenderer})
 * via {@link #pose()}; this class keeps only the state/clock that is safe to
 * exercise in pure-JVM tests.
 */
public final class CharacterEntity {

  private final CharacterMeshIndex index;
  private final CharacterAnimator animator;
  private float worldX;
  private float worldZ;

  public CharacterEntity(CharacterMeshIndex index) {
    if (index == null) {
      throw new NullPointerException("index");
    }
    this.index = index;
    this.animator = index.buildAnimator();
  }

  public CharacterMeshIndex index() {
    return index;
  }

  public CharacterAnimator animator() {
    return animator;
  }

  public float worldX() {
    return worldX;
  }

  public float worldZ() {
    return worldZ;
  }

  public void setPosition(float worldX, float worldZ) {
    this.worldX = worldX;
    this.worldZ = worldZ;
  }

  /** Advances this instance's animation clock. */
  public void update(double dtSeconds) {
    animator.update(dtSeconds);
  }

  /**
   * Samples the active pose, or null when no clip is active (bind pose). Never
   * throws: sampling errors degrade to the bind pose.
   */
  public Pose pose() {
    if (!animator.active()) {
      return null;
    }
    try {
      return index.poseAt(animator.currentClipName(), animator.currentTimeMs());
    } catch (IOException e) {
      return null;
    }
  }
}
