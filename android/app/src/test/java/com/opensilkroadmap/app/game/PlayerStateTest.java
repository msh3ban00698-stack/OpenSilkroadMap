package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class PlayerStateTest {

  @Test
  public void defaultsToLevelOneInertState() {
    PlayerState player = new PlayerState("p1", "Hero");
    assertEquals(1, player.level());
    assertEquals(0, player.hp());
    assertEquals(1, player.maxHp());
    assertFalse(player.dead());
    assertFalse(player.isAlive());
  }

  @Test
  public void aliveOnlyWhenNotDeadAndHasHp() {
    PlayerState player = new PlayerState("p1", "Hero");
    player.setMaxHp(100);
    player.setHp(50);
    assertTrue(player.isAlive());
    player.setHp(0);
    assertFalse(player.isAlive());
    player.setHp(50);
    player.setDead(true);
    assertFalse(player.isAlive());
  }

  @Test
  public void levelClampsToAtLeastOne() {
    PlayerState player = new PlayerState("p1", "Hero");
    player.setLevel(0);
    assertEquals(1, player.level());
    player.setLevel(40);
    assertEquals(40, player.level());
  }

  @Test
  public void hpMpAndGoldDoNotGoNegative() {
    PlayerState player = new PlayerState("p1", "Hero");
    player.setHp(-5);
    player.setMp(-5);
    player.setGold(-10);
    assertEquals(0, player.hp());
    assertEquals(0, player.mp());
    assertEquals(0L, player.gold());
  }

  @Test
  public void positionIsNeutralWorldCoordinates() {
    PlayerState player = new PlayerState("p1", "Hero");
    player.setPosition(1.5, 2.5, 3.5);
    assertEquals(1.5, player.x(), 1e-9);
    assertEquals(2.5, player.y(), 1e-9);
    assertEquals(3.5, player.z(), 1e-9);
  }
}
