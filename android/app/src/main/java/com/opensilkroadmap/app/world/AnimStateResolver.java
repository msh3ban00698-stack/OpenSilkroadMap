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
 * store). A keyword matches only at a word start ({@code [a-z0-9]} run after a
 * non-word delimiter or the string start), never as a substring: the data
 * shows {@code die} inside {@code soldier} and {@code run} inside
 * {@code trunk}/{@code union} would otherwise fabricate states, and
 * {@code standbattle}/{@code walkforward}/{@code runforward} (player clips)
 * must still match:
 * <ul>
 *   <li>{@link AnimState#IDLE} — word starting with {@code stand}</li>
 *   <li>{@link AnimState#WALK} — word starting with {@code walk}</li>
 *   <li>{@link AnimState#RUN} — word starting with {@code run}</li>
 *   <li>{@link AnimState#ATTACK} — word starting with {@code attack}</li>
 *   <li>{@link AnimState#DAMAGE} — word starting with {@code damage} and not
 *       {@code down} (excludes the down-state damage variant)</li>
 *   <li>{@link AnimState#DEATH} — word starting with {@code die} and not
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
      if (!keywordMatch(lower, keyword)) {
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

  /**
   * True when {@code lower} contains {@code keyword} starting a word:
   * the character before the match is not {@code [a-z0-9]} (or it is the
   * string start). Proven by the committed clip names: {@code stand01},
   * {@code walkforward}, {@code standbattle} match; {@code soldier},
   * {@code trunkz}, {@code hunterunion} do not.
   */
  static boolean keywordMatch(String lower, String keyword) {
    int n = lower.length();
    int k = keyword.length();
    for (int i = 0; i + k <= n; i++) {
      if (i > 0 && isWordChar(lower.charAt(i - 1))) {
        continue;
      }
      if (lower.regionMatches(i, keyword, 0, k)) {
        return true;
      }
    }
    return false;
  }

  private static boolean isWordChar(char c) {
    return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9');
  }
}
