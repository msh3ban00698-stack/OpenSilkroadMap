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

  @Test
  public void embeddedKeywordDoesNotFabricateStates() {
    // Real false positives in the committed data: "die" inside "soldier" and
    // "run" inside "trunk"/"union" must not resolve DEATH/RUN.
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("soldierearthghost_stand02", 2000),
        clip("deserttrunkz_stand01", 2000),
        clip("hunterunion_stand01", 2000));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals(1, m.size());
    assertTrue(m.containsKey(AnimState.IDLE));
    assertFalse(m.containsKey(AnimState.DEATH));
    assertFalse(m.containsKey(AnimState.RUN));
  }

  @Test
  public void wordStartMatchesPlayerClipPrefixes() {
    // Player clips: "standbattle"/"standcity"/"walkforward"/"runforward_sword".
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("chinaman_fighter_standcity", 2333),
        clip("chinaman_fighter_walkforward", 1166),
        clip("chinaman_fighter_runforward_sword", 666),
        clip("chinaman_fighter_attack01", 1000));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals("chinaman_fighter_standcity", m.get(AnimState.IDLE).name);
    assertEquals("chinaman_fighter_walkforward", m.get(AnimState.WALK).name);
    assertEquals("chinaman_fighter_runforward_sword", m.get(AnimState.RUN).name);
    assertEquals("chinaman_fighter_attack01", m.get(AnimState.ATTACK).name);
  }

  @Test
  public void deathPrefersRealDieClipOverShadowedWord() {
    // "tombsoldier" embeds "die", but the real "_die" clip must win.
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("tombsoldier_stand01", 2000),
        clip("tombsoldier_die", 2666));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals("tombsoldier_die", m.get(AnimState.DEATH).name);
  }

  @Test
  public void downAndWakeupResolveFromProvenClips() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("mob_stand", 2000),
        clip("mob_down", 833),
        clip("mob_wakeup", 1333));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals("mob_down", m.get(AnimState.DOWN).name);
    assertEquals("mob_wakeup", m.get(AnimState.WAKEUP).name);
    assertFalse(m.get(AnimState.DOWN).name.equals("mob_wakeup"));
  }

  @Test
  public void downFamilyGroupsUnderDownNotDamageOrDeath() {
    // downdamage/downdie/downwait are down-family; the canonical "down" clip wins.
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("bandit_down", 833),
        clip("bandit_downwait", 2000),
        clip("bandit_downdamage", 833),
        clip("bandit_downdie", 300));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals("bandit_down", m.get(AnimState.DOWN).name);
    assertFalse(m.containsKey(AnimState.DAMAGE));
    assertFalse(m.containsKey(AnimState.DEATH));
  }

  @Test
  public void fullBanditManifestResolvesEightStates() {
    // The committed bandit anims.tsv clip names in manifest order.
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("bandit_stand01", 2000),
        clip("bandit_stand02", 2000),
        clip("bandit_walk", 1333),
        clip("bandit_run", 833),
        clip("bandit_attack01", 1133),
        clip("bandit_attack02", 1500),
        clip("bandit_damage01", 366),
        clip("bandit_damage02", 1666),
        clip("bandit_die", 2666),
        clip("bandit_die_loop", 333),
        clip("bandit_down", 833),
        clip("bandit_downwait", 2000),
        clip("bandit_downdamage", 833),
        clip("bandit_wakeup", 1333),
        clip("bandit_downdie", 300),
        clip("bandit_attack03", 1166));
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(clips);
    assertEquals(8, m.size());
    assertEquals("bandit_stand01", m.get(AnimState.IDLE).name);
    assertEquals("bandit_walk", m.get(AnimState.WALK).name);
    assertEquals("bandit_run", m.get(AnimState.RUN).name);
    assertEquals("bandit_attack01", m.get(AnimState.ATTACK).name);
    assertEquals("bandit_damage01", m.get(AnimState.DAMAGE).name);
    assertEquals("bandit_die", m.get(AnimState.DEATH).name);
    assertEquals("bandit_down", m.get(AnimState.DOWN).name);
    assertEquals("bandit_wakeup", m.get(AnimState.WAKEUP).name);
  }

  @Test
  public void keywordMatchWordStartSemantics() {
    assertTrue(AnimStateResolver.keywordMatch("bandit_stand01", "stand"));
    assertTrue(AnimStateResolver.keywordMatch("chinaman_fighter_walkforward", "walk"));
    assertTrue(AnimStateResolver.keywordMatch("chinaman_standbattle", "stand"));
    assertTrue(AnimStateResolver.keywordMatch("mob_die", "die"));
    assertFalse(AnimStateResolver.keywordMatch("soldier_stand01", "die"));
    assertFalse(AnimStateResolver.keywordMatch("deserttrunkz_stand01", "run"));
    assertFalse(AnimStateResolver.keywordMatch("hunterunion", "run"));
    assertFalse(AnimStateResolver.keywordMatch("stand", "standoff"));
  }
}
