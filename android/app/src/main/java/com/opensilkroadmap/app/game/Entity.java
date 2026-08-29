package com.opensilkroadmap.app.game;

/**
 * Minimal entity state container for the Android entity foundation.
 *
 * <p>This is neutral engine scaffolding, not authentic VSRO behavior: position
 * values are generic world coordinates whose unit is UNKNOWN from the supplied
 * material (no source scale is claimed). It exists so gameplay systems can be
 * structured around a common entity contract; behavior must be added only from
 * verified source evidence.
 */
public class Entity {
  private final String id;
  private final String name;
  private double x;
  private double y;
  private double z;

  public Entity(String id, String name) {
    this.id = id == null ? "" : id;
    this.name = name == null ? "" : name;
  }

  public String id() {
    return id;
  }

  public String name() {
    return name;
  }

  public double x() {
    return x;
  }

  public double y() {
    return y;
  }

  public double z() {
    return z;
  }

  public void setPosition(double x, double y, double z) {
    this.x = x;
    this.y = y;
    this.z = z;
  }
}
