package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import org.junit.Test;

public class AnimStateResolverTest {

  private static IdleAnimResolver.Clip clip(String name, int ms) {
    return new IdleAnimResolver.Clip(name, ms);
  }

  private static List<IdleAnimResolver.Clip> fullSet() {
    return Arrays.asList(
        clip("mob_stand", 2000),
        clip("mob_walk", 1333),
        clip("mob_run", 833),
        clip("mob_attack01", 1133),
        clip("mob_damage", 1000),
        clip("mob_die", 2666));
  }

  @Test
  public void resolvesAllProvenStates() {
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(fullSet());
    assertEquals(6, m.size());
    assertEquals("mob_stand", m.get(AnimState.IDLE).name);
    assertEquals("mob_walk", m.get(AnimState.WALK).name);
    assertEquals("mob_run", m.get(AnimState.RUN).name);
    assertEquals("mob_attack01", m.get(AnimState.ATTACK).name);
    assertEquals("mob_damage", m.get(AnimState.DAMAGE).name);
    assertEquals("mob_die", m.get(AnimState.DEATH).name);
  }

  @Test
  public void idleOnlyCharacterResolvesSingleState() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(clip("prop_stand", 1000));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals(1, m.size());
    assertTrue(m.containsKey(AnimState.IDLE));
    assertFalse(m.containsKey(AnimState.ATTACK));
  }

  @Test
  public void damageExcludesDownVariant() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("mob_damage_down", 1000),
        clip("mob_damage", 1000));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals("mob_damage", m.get(AnimState.DAMAGE).name);
  }

  @Test
  public void deathExcludesDownAndLoopVariants() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("mob_die_down", 2666),
        clip("mob_die_loop", 2666),
        clip("mob_die", 2666));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals("mob_die", m.get(AnimState.DEATH).name);
  }

  @Test
  public void emptyOrNullResolvesNothing() {
    assertEquals(0, AnimStateResolver.resolve(new ArrayList<IdleAnimResolver.Clip>()).size());
    assertEquals(0, AnimStateResolver.resolve(null).size());
  }

  @Test
  public void runKeywordDoesNotMatchStandOrWalk() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("mob_stand", 2000),
        clip("mob_run", 833));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertFalse(m.containsKey(AnimState.WALK));
    assertEquals("mob_run", m.get(AnimState.RUN).name);
  }
}
