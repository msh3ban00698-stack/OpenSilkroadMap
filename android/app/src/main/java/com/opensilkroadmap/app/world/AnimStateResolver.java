package com.opensilkroadmap.app.world;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Resolves a character's committed animation clip list into its proven
 * animation states. Each state maps to the first clip whose name matches a
 * documented keyword (case-insensitive), in manifest order, or is omitted when
 * the state is not present in the source.
 *
 * <p>Keyword rules (from the real {@code .ban} naming exported to the shared
 * store):
 * <ul>
 *   <li>{@link AnimState#IDLE} — name contains {@code stand}</li>
 *   <li>{@link AnimState#WALK} — name contains {@code walk}</li>
 *   <li>{@link AnimState#RUN} — name contains {@code run}</li>
 *   <li>{@link AnimState#ATTACK} — name contains {@code attack}</li>
 *   <li>{@link AnimState#DAMAGE} — name contains {@code damage} and not
 *       {@code down} (excludes the down-state damage variant)</li>
 *   <li>{@link AnimState#DEATH} — name contains {@code die} and not
 *       {@code down} and not {@code loop} (excludes down-death and the
 *       post-death loop)</li>
 * </ul>
 *
 * <p>Fail-closed: states with no matching clip are simply absent from the
 * result; the caller keeps the bind pose or falls back to idle, never invents a
 * clip.
 */
public final class AnimStateResolver {

  private AnimStateResolver() {}

  /** Resolves each proven state to its clip; absent states are omitted. */
  public static Map<AnimState, IdleAnimResolver.Clip> resolve(
      List<IdleAnimResolver.Clip> clips) {
    Map<AnimState, IdleAnimResolver.Clip> out =
        new LinkedHashMap<AnimState, IdleAnimResolver.Clip>();
    if (clips == null || clips.isEmpty()) {
      return out;
    }
    put(out, clips, AnimState.IDLE, "stand", false, false);
    put(out, clips, AnimState.WALK, "walk", false, false);
    put(out, clips, AnimState.RUN, "run", false, false);
    put(out, clips, AnimState.ATTACK, "attack", false, false);
    put(out, clips, AnimState.DAMAGE, "damage", true, false);
    put(out, clips, AnimState.DEATH, "die", true, true);
    return out;
  }

  private static void put(Map<AnimState, IdleAnimResolver.Clip> out,
                          List<IdleAnimResolver.Clip> clips, AnimState state,
                          String keyword, boolean excludeDown, boolean excludeLoop) {
    for (IdleAnimResolver.Clip c : clips) {
      String n = c.name;
      if (n == null) {
        continue;
      }
      String lower = n.toLowerCase();
      if (!lower.contains(keyword)) {
        continue;
      }
      if (excludeDown && lower.contains("down")) {
        continue;
      }
      if (excludeLoop && lower.contains("loop")) {
        continue;
      }
      out.put(state, c);
      return;
    }
  }
}
