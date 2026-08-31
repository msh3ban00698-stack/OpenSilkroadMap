package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.Test;

public class CharacterAnimatorTest {

  private static IdleAnimResolver.Clip clip(String name, int ms) {
    return new IdleAnimResolver.Clip(name, ms);
  }

  private static Map<AnimState, IdleAnimResolver.Clip> clips() {
    Map<AnimState, IdleAnimResolver.Clip> m =
        new LinkedHashMap<AnimState, IdleAnimResolver.Clip>();
    m.put(AnimState.IDLE, clip("mob_stand", 2000));
    m.put(AnimState.WALK, clip("mob_walk", 1333));
    m.put(AnimState.RUN, clip("mob_run", 833));
    m.put(AnimState.ATTACK, clip("mob_attack01", 1133));
    m.put(AnimState.DAMAGE, clip("mob_damage", 1000));
    m.put(AnimState.DEATH, clip("mob_die", 2666));
    return m;
  }

  @Test
  public void startsInIdleAtZero() {
    CharacterAnimator a = new CharacterAnimator(clips());
    assertEquals(AnimState.IDLE, a.state());
    assertTrue(a.active());
    assertEquals("mob_stand", a.currentClipName());
    assertEquals(0, a.currentTimeMs());
  }

  @Test
  public void idleLoopsIndependently() {
    CharacterAnimator a = new CharacterAnimator(clips());
    a.update(2.5);
    assertEquals(500, a.currentTimeMs());
    assertFalse(a.isFinished());
  }

  @Test
  public void attackReturnsToIdleWhenFinished() {
    CharacterAnimator a = new CharacterAnimator(clips());
    a.setState(AnimState.ATTACK);
    assertEquals("mob_attack01", a.currentClipName());
    a.update(2.0); // beyond 1133ms non-looping
    assertEquals(AnimState.IDLE, a.state());
    assertEquals("mob_stand", a.currentClipName());
    assertEquals(0, a.currentTimeMs());
  }

  @Test
  public void deathIsTerminal() {
    CharacterAnimator a = new CharacterAnimator(clips());
    a.setState(AnimState.DEATH);
    a.update(5.0);
    assertEquals(AnimState.DEATH, a.state());
    assertTrue(a.isFinished());
  }

  @Test
  public void missingStateFallsBackToIdle() {
    CharacterAnimator a = new CharacterAnimator(clips());
    a.setState(AnimState.IDLE);
    a.setState(AnimState.RUN);
    assertEquals("mob_run", a.currentClipName());
    Map<AnimState, IdleAnimResolver.Clip> idleOnly =
        new LinkedHashMap<AnimState, IdleAnimResolver.Clip>();
    idleOnly.put(AnimState.IDLE, clip("mob_stand", 2000));
    CharacterAnimator b = new CharacterAnimator(idleOnly);
    b.setState(AnimState.RUN); // RUN missing -> idle fallback
    assertEquals(AnimState.IDLE, b.state());
    assertEquals("mob_stand", b.currentClipName());
  }

  @Test
  public void noClipsMeansInactiveBindPose() {
    CharacterAnimator a = new CharacterAnimator(
        Collections.<AnimState, IdleAnimResolver.Clip>emptyMap());
    assertFalse(a.active());
    assertEquals("", a.currentClipName());
    assertEquals(AnimState.IDLE, a.state());
  }

  @Test
  public void twoInstancesAreIndependent() {
    CharacterAnimator a = new CharacterAnimator(clips());
    CharacterAnimator b = new CharacterAnimator(clips());
    a.update(1.0);
    b.update(0.5);
    assertEquals(1000, a.currentTimeMs());
    assertEquals(500, b.currentTimeMs());
    a.setState(AnimState.ATTACK);
    assertEquals(AnimState.IDLE, b.state());
    assertEquals(AnimState.ATTACK, a.state());
  }

  @Test
  public void sameStateTransitionDoesNotRestart() {
    CharacterAnimator a = new CharacterAnimator(clips());
    a.update(1.0);
    a.setState(AnimState.IDLE); // already idle -> no-op
    assertEquals(1000, a.currentTimeMs());
  }
}
