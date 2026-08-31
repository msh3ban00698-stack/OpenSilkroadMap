package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import org.junit.Test;

/**
 * TASK A: real-clip state resolution and per-entity clocks over committed
 * character manifests ({@code game/world/characters/<key>/manifest.json}).
 *
 * <p>Resolves actual clip lists (real {@code .ban} names + durations) into
 * {@link AnimState}s and drives {@link CharacterAnimator} instances, proving:
 * (1) every resolved state's clip name starts its keyword at a word boundary
 * across the whole 473-manifest corpus, (2) known full/subsets resolve the
 * verified state sets, and (3) two entities of the SAME model advance
 * independent clocks.
 *
 * <p>All expected clip names/durations below are the PROVEN committed values;
 * never fabricated.
 */
public class CharacterRuntimeDataTest {

  private static final String[] ASSET_DIRS = {
    "src/main/assets/game/world/characters",
    "../src/main/assets/game/world/characters",
    "app/src/main/assets/game/world/characters",
    "../app/src/main/assets/game/world/characters",
  };

  private static File findRoot() {
    for (String dir : ASSET_DIRS) {
      File f = new File(dir);
      if (f.isDirectory()) {
        return f;
      }
    }
    return null;
  }

  private static byte[] readAsset(File root, String name) throws IOException {
    File f = new File(root, name);
    if (f.isFile()) {
      FileInputStream in = new FileInputStream(f);
      try {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = in.read(buf)) != -1) {
          out.write(buf, 0, n);
        }
        return out.toByteArray();
      } finally {
        in.close();
      }
    }
    throw new IOException("asset not found: " + name);
  }

  private static Map<AnimState, IdleAnimResolver.Clip> resolve(String key)
      throws IOException {
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    byte[] bytes = readAsset(root, key + "/manifest.json");
    return AnimStateResolver.resolve(CharacterMeshIndex.parseManifestClips(
        new InputStreamReader(new ByteArrayInputStream(bytes), StandardCharsets.UTF_8)));
  }

  @Test
  public void realCharactersResolveVerifiedStateSets() throws IOException {
    Map<AnimState, IdleAnimResolver.Clip> bandit = resolve("res_mob_china_bandit");
    assertEquals("bandit_stand01", bandit.get(AnimState.IDLE).name);
    assertEquals(2000, bandit.get(AnimState.IDLE).durationMs);
    assertEquals("bandit_walk", bandit.get(AnimState.WALK).name);
    assertEquals(1333, bandit.get(AnimState.WALK).durationMs);
    assertEquals("bandit_run", bandit.get(AnimState.RUN).name);
    assertEquals(833, bandit.get(AnimState.RUN).durationMs);
    assertEquals("bandit_attack01", bandit.get(AnimState.ATTACK).name);
    assertEquals(1133, bandit.get(AnimState.ATTACK).durationMs);
    assertEquals("bandit_damage01", bandit.get(AnimState.DAMAGE).name);
    assertEquals(366, bandit.get(AnimState.DAMAGE).durationMs);
    assertEquals("bandit_die", bandit.get(AnimState.DEATH).name);
    assertEquals(2666, bandit.get(AnimState.DEATH).durationMs);

    Map<AnimState, IdleAnimResolver.Clip> wolf = resolve("res_mob_arabia_baruswolf_adonis1");
    assertEquals("wolf_stand01", wolf.get(AnimState.IDLE).name);
    assertEquals(2666, wolf.get(AnimState.IDLE).durationMs);
    assertEquals("wolf_die", wolf.get(AnimState.DEATH).name);
    assertEquals(3100, wolf.get(AnimState.DEATH).durationMs);

    Map<AnimState, IdleAnimResolver.Clip> smith = resolve("res_npc_npc_arabia_smith");
    assertEquals(1, smith.size());
    assertEquals("arabia_smith_stand01", smith.get(AnimState.IDLE).name);
    assertEquals(12500, smith.get(AnimState.IDLE).durationMs);

    Map<AnimState, IdleAnimResolver.Clip> mustafa = resolve("res_mob_arabia_mustafa");
    assertEquals(5, mustafa.size());
    assertFalse("mustafa has no damage clip", mustafa.containsKey(AnimState.DAMAGE));

    Map<AnimState, IdleAnimResolver.Clip> player = resolve("player");
    assertEquals(3, player.size());
    assertEquals("chinaman_standbattle", player.get(AnimState.IDLE).name);
    assertEquals("chinaman_fighter_walkforward", player.get(AnimState.WALK).name);
    assertEquals("chinaman_fighter_runforward_sword", player.get(AnimState.RUN).name);
    assertFalse("player has no combat states", player.containsKey(AnimState.ATTACK));
    assertFalse("player has no death clip", player.containsKey(AnimState.DEATH));
  }

  @Test
  public void everyResolvedStateMatchesKeywordAtWordStart() throws IOException {
    File root = findRoot();
    assertNotNull(root);
    for (File d : root.listFiles()) {
      if (!d.isDirectory() || d.getName().equals("shared")) {
        continue;
      }
      File manifest = new File(d, "manifest.json");
      if (!manifest.isFile()) {
        continue;
      }
      byte[] bytes = readAsset(root, d.getName() + "/manifest.json");
      Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(
          CharacterMeshIndex.parseManifestClips(new InputStreamReader(
              new ByteArrayInputStream(bytes), StandardCharsets.UTF_8)));
      for (Map.Entry<AnimState, IdleAnimResolver.Clip> e : m.entrySet()) {
        String name = e.getValue().name;
        String lower = name.toLowerCase();
        String kw = keyword(e.getKey());
        assertTrue("state " + e.getKey() + " clip '" + name + "' in "
            + d.getName() + " must start '" + kw + "' at word boundary",
            AnimStateResolver.keywordMatch(lower, kw));
      }
    }
  }

  private static String keyword(AnimState s) {
    switch (s) {
      case IDLE:
        return "stand";
      case WALK:
        return "walk";
      case RUN:
        return "run";
      case ATTACK:
        return "attack";
      case DAMAGE:
        return "damage";
      case DEATH:
        return "die";
      case DOWN:
        return "down";
      case WAKEUP:
        return "wakeup";
      default:
        throw new IllegalArgumentException("unknown state " + s);
    }
  }

  @Test
  public void banditAttackReturnsToIdleUsingRealDuration() throws IOException {
    CharacterAnimator a = new CharacterAnimator(resolve("res_mob_china_bandit"));
    a.setState(AnimState.ATTACK);
    assertEquals("bandit_attack01", a.currentClipName());
    a.update(2.0); // beyond 1133ms non-looping
    assertEquals(AnimState.IDLE, a.state());
    assertEquals("bandit_stand01", a.currentClipName());
    assertEquals(0, a.currentTimeMs());
  }

  @Test
  public void sameModelEntitiesHaveIndependentClocks() throws IOException {
    CharacterAnimator a = new CharacterAnimator(resolve("res_mob_china_bandit"));
    CharacterAnimator b = new CharacterAnimator(resolve("res_mob_china_bandit"));
    a.update(2.5); // idle is 2000ms looping -> wraps to 500
    assertEquals(500, a.currentTimeMs());
    assertEquals(0, b.currentTimeMs());
    b.update(1.0);
    assertEquals(1000, b.currentTimeMs());
    a.setState(AnimState.ATTACK);
    assertEquals(AnimState.ATTACK, a.state());
    assertEquals(AnimState.IDLE, b.state());
  }

  @Test
  public void idleOnlyNpcFallsBackToIdleForMissingStates() throws IOException {
    CharacterAnimator a = new CharacterAnimator(resolve("res_npc_npc_arabia_smith"));
    assertTrue(a.active());
    assertEquals("arabia_smith_stand01", a.currentClipName());
    a.setState(AnimState.RUN); // no run clip -> idle fallback
    assertEquals(AnimState.IDLE, a.state());
    assertEquals("arabia_smith_stand01", a.currentClipName());
  }
}
