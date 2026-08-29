package com.opensilkroadmap.app.game;

/**
 * Player state container for the Android player foundation.
 *
 * <p>Neutral scaffolding. Defaults reflect no claimed game behavior: level 1,
 * empty state, not dead. Any damage/stat/leveling behavior must be introduced
 * only from verified source evidence (the web prototype currently treats such
 * values as tuning; the bundled Phase H data provides the real level curve and
 * starter item names).
 */
public final class PlayerState extends Entity {
  private int level = 1;
  private int hp;
  private int maxHp = 1;
  private int mp;
  private int maxMp = 1;
  private long gold;
  private String className = "";
  private boolean dead;

  public PlayerState(String id, String name) {
    super(id, name);
  }

  public int level() {
    return level;
  }

  public void setLevel(int level) {
    this.level = Math.max(1, level);
  }

  public int hp() {
    return hp;
  }

  public int maxHp() {
    return maxHp;
  }

  public void setHp(int hp) {
    this.hp = Math.max(0, hp);
  }

  public void setMaxHp(int maxHp) {
    this.maxHp = Math.max(1, maxHp);
  }

  public int mp() {
    return mp;
  }

  public int maxMp() {
    return maxMp;
  }

  public void setMp(int mp) {
    this.mp = Math.max(0, mp);
  }

  public void setMaxMp(int maxMp) {
    this.maxMp = Math.max(1, maxMp);
  }

  public long gold() {
    return gold;
  }

  public void setGold(long gold) {
    this.gold = Math.max(0, gold);
  }

  public String className() {
    return className;
  }

  public void setClassName(String className) {
    this.className = className == null ? "" : className;
  }

  public boolean dead() {
    return dead;
  }

  public void setDead(boolean dead) {
    this.dead = dead;
  }

  public boolean isAlive() {
    return !dead && hp > 0;
  }
}
