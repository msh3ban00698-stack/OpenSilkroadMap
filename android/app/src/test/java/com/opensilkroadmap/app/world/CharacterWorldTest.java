package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;

/**
 * PHASE 26 Task F: the pure-JVM multi-entity {@link CharacterWorld}.
 *
 * <p>Loads TWO real committed models (the player's animation chain and the
 * bandit's full chain) via {@link CharacterMeshIndex#animationsOnlyIndex} over
 * the committed assets, then proves the multi-entity runtime capability:
 *
 * <ul>
 *   <li>One model key can back many entities; every entity owns an independent
 *       animator clock (advancing one never advances its sibling).</li>
 *   <li>The world clock advances every entity uniformly.</li>
 *   <li>Different model keys resolve different state/clip sets from their own
 *       committed manifests (bandit resolves ATTACK/DAMAGE/DEATH, the player's
 *       skill-named attacks do NOT, per the Phase 26 census).</li>
 *   <li>Spawn is fail-closed: unknown model key or duplicate entity id is a
 *       no-op.</li>
 * </ul>
 */
public class CharacterWorldTest {

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
    if (!f.isFile()) {
      throw new IOException("asset not found: " + name);
    }
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

  private static CharacterMeshIndex animationIndex(String key, String skelPath) {
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    try {
      return CharacterMeshIndex.animationsOnlyIndex(
          key,
          new InputStreamReader(new ByteArrayInputStream(readAsset(
              root, key + "/manifest.json")), StandardCharsets.UTF_8),
          new InputStreamReader(new ByteArrayInputStream(readAsset(
              root, skelPath)), StandardCharsets.UTF_8));
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  private static CharacterWorld realWorld() {
    Map<String, CharacterMeshIndex> models = new LinkedHashMap<String, CharacterMeshIndex>();
    models.put(CharacterCatalog.PLAYER_KEY, animationIndex(
        CharacterCatalog.PLAYER_KEY,
        "shared/skel/prim_skel_char_china_chinaman_skel.json"));
    models.put("res_mob_china_bandit", animationIndex("res_mob_china_bandit",
        "shared/skel/prim_skel_mob_china_bandit.json"));
    return new CharacterWorld(models);
  }

  @Test
  public void differentModelKeysResolveDifferentClipSets() {
    CharacterWorld world = realWorld();
    assertTrue(world.hasModel("res_mob_china_bandit"));
    assertTrue(world.hasModel(CharacterCatalog.PLAYER_KEY));
    assertFalse(world.hasModel("no_such_model"));
    assertSame(world.model("res_mob_china_bandit"), world.model("res_mob_china_bandit"));

    assertTrue(world.spawn("bandit1", "res_mob_china_bandit", 10f, 20f));
    assertTrue(world.spawn("player", CharacterCatalog.PLAYER_KEY, 0f, 0f));

    CharacterAnimator banditAnim = world.entry("bandit1").entity.animator();
    CharacterAnimator playerAnim = world.entry("player").entity.animator();
    // The committed bandit manifest resolves attack/damage/death via the
    // keyword resolver; the player's manifest carries only 5 locomotion clips.
    assertTrue("bandit must resolve ATTACK", banditAnim.hasClip(AnimState.ATTACK));
    assertTrue("bandit must resolve DAMAGE", banditAnim.hasClip(AnimState.DAMAGE));
    assertTrue("bandit must resolve DEATH", banditAnim.hasClip(AnimState.DEATH));
    assertFalse("player ATTACK must be MISSING (skill-named clips)",
        playerAnim.hasClip(AnimState.ATTACK));
  }

  @Test
  public void siblingsOfSameModelHaveIndependentClocks() {
    CharacterWorld world = realWorld();
    assertTrue(world.spawn("bandit1", "res_mob_china_bandit", 10f, 20f));
    assertTrue(world.spawn("bandit2", "res_mob_china_bandit", -5f, 30f));

    CharacterEntity a = world.entry("bandit1").entity;
    CharacterEntity b = world.entry("bandit2").entity;
    assertNotSame("each entity owns its own animator", a.animator(), b.animator());
    assertEquals(10f, a.worldX(), 0f);
    assertEquals(20f, a.worldZ(), 0f);
    assertEquals(-5f, b.worldX(), 0f);
    assertEquals(30f, b.worldZ(), 0f);

    a.animator().setState(AnimState.WALK);
    assertEquals(AnimState.IDLE, b.animator().state());

    a.update(0.5);
    assertTrue("advancing one sibling must not advance the other",
        a.animator().currentTimeMs() > 0);
    assertEquals(0, b.animator().currentTimeMs());
    assertEquals(AnimState.WALK, a.animator().state());
    assertEquals(AnimState.IDLE, b.animator().state());
  }

  @Test
  public void worldClockAdvancesEveryEntityUniformly() {
    CharacterWorld world = realWorld();
    assertTrue(world.spawn("bandit1", "res_mob_china_bandit", 1f, 1f));
    assertTrue(world.spawn("bandit2", "res_mob_china_bandit", 2f, 2f));
    CharacterEntity a = world.entry("bandit1").entity;
    CharacterEntity b = world.entry("bandit2").entity;

    a.animator().setState(AnimState.WALK);
    b.animator().setState(AnimState.WALK);
    world.update(0.25);
    world.update(0.25);

    assertEquals(500, a.animator().currentTimeMs());
    assertEquals(500, b.animator().currentTimeMs());
  }

  @Test
  public void spawnIsFailClosedForUnknownModelAndDuplicateId() {
    CharacterWorld world = realWorld();
    assertFalse(world.spawn("x", "no_such_model", 0f, 0f));
    assertTrue(world.spawn("dup", "res_mob_china_bandit", 0f, 0f));
    assertFalse("duplicate id must be a no-op", world.spawn("dup", "res_mob_china_bandit", 5f, 5f));
    assertEquals(1, world.size());
    assertEquals(0f, world.entry("dup").entity.worldX(), 0f);
    assertEquals(0f, world.entry("dup").entity.worldZ(), 0f);
  }

  @Test
  public void entriesSnapshotIsOrderedAndStable() {
    CharacterWorld world = realWorld();
    assertTrue(world.spawn("a", "res_mob_china_bandit", 0f, 0f));
    assertTrue(world.spawn("b", "res_mob_china_bandit", 0f, 0f));
    assertTrue(world.spawn("c", CharacterCatalog.PLAYER_KEY, 0f, 0f));
    assertEquals(3, world.size());
    assertEquals("a", world.entries().get(0).entityId);
    assertEquals("b", world.entries().get(1).entityId);
    assertEquals("c", world.entries().get(2).entityId);
    assertNotNull(world.entry("a"));
  }
}
