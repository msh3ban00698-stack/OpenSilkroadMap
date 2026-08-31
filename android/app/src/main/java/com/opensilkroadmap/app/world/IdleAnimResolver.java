package com.opensilkroadmap.app.world;

import java.util.List;

/**
 * Deterministic idle-clip selection over a character's committed animation
 * metadata (name + real duration). The idle clip is the animation a character
 * plays while standing still in the world; it is derived from the manifest
 * animation names, not invented.
 *
 * <p>Rule (fail-closed): return the index of the first animation whose name
 * contains {@code "stand"} (case-insensitive), or {@code -1} when none does.
 * Characters without a recognizable stand clip (static props, traps, and
 * single-shot NPC poses) keep the bind pose. This avoids guessing a "first"
 * animation that might be an attack, damage, or death clip.
 */
public final class IdleAnimResolver {

  /** Minimal immutable clip descriptor (name + real duration). */
  public static final class Clip {
    public final String name;
    public final int durationMs;

    public Clip(String name, int durationMs) {
      this.name = name;
      this.durationMs = durationMs;
    }
  }

  private IdleAnimResolver() {}

  /** Index of the idle clip, or {@code -1} when no stand clip exists. */
  public static int resolve(List<Clip> clips) {
    if (clips == null || clips.isEmpty()) {
      return -1;
    }
    Clip idle = AnimStateResolver.resolve(clips).get(AnimState.IDLE);
    if (idle == null) {
      return -1;
    }
    for (int i = 0; i < clips.size(); i++) {
      if (idle.name.equals(clips.get(i).name)) {
        return i;
      }
    }
    return -1;
  }
}
