package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Test;

public class IdleAnimResolverTest {

  private static IdleAnimResolver.Clip clip(String name, int ms) {
    return new IdleAnimResolver.Clip(name, ms);
  }

  @Test
  public void picksFirstStandClip() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("bandit_stand01", 2000),
        clip("bandit_stand02", 2000),
        clip("bandit_walk", 1333),
        clip("bandit_run", 833));
    assertEquals(0, IdleAnimResolver.resolve(clips));
  }

  @Test
  public void standMatchIsCaseInsensitive() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("chinaman_StandBattle", 2000),
        clip("chinaman_fighter_walkforward", 1166));
    assertEquals(0, IdleAnimResolver.resolve(clips));
  }

  @Test
  public void noStandReturnsMinusOne() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("bandit_attack01", 1133),
        clip("bandit_die", 2666));
    assertEquals(-1, IdleAnimResolver.resolve(clips));
  }

  @Test
  public void emptyOrNullReturnsMinusOne() {
    assertEquals(-1, IdleAnimResolver.resolve(new ArrayList<IdleAnimResolver.Clip>()));
    assertEquals(-1, IdleAnimResolver.resolve(null));
  }

  @Test
  public void returnsFirstStandRegardlessOfPosition() {
    List<IdleAnimResolver.Clip> clips = Arrays.asList(
        clip("mob_walk", 1000),
        clip("mob_stand", 2000),
        clip("mob_stand02", 2000));
    assertEquals(1, IdleAnimResolver.resolve(clips));
  }
}
