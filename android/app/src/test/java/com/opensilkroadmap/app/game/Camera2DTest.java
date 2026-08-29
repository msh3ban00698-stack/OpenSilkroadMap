package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class Camera2DTest {

  @Test
  public void clampsToWorldBounds() {
    Camera2D camera = new Camera2D();
    camera.setViewport(100, 100);
    camera.setWorld(1000, 1000);
    camera.follow(50, 50);
    assertEquals(50.0, camera.x(), 1e-9);
    assertEquals(50.0, camera.y(), 1e-9);
    camera.follow(-500, -500);
    assertEquals(50.0, camera.x(), 1e-9);
    assertEquals(50.0, camera.y(), 1e-9);
    camera.follow(1500, 1500);
    assertEquals(950.0, camera.x(), 1e-9);
    assertEquals(950.0, camera.y(), 1e-9);
  }

  @Test
  public void centersWhenViewLargerThanWorld() {
    Camera2D camera = new Camera2D();
    camera.setViewport(2000, 2000);
    camera.setWorld(1000, 1000);
    camera.follow(0, 0);
    assertEquals(500.0, camera.x(), 1e-9);
    assertEquals(500.0, camera.y(), 1e-9);
  }

  @Test
  public void freeMovementInsideWorld() {
    Camera2D camera = new Camera2D();
    camera.setViewport(100, 100);
    camera.setWorld(1000, 1000);
    camera.follow(300, 700);
    assertEquals(300.0, camera.x(), 1e-9);
    assertEquals(700.0, camera.y(), 1e-9);
  }

  @Test
  public void zeroBoundsYieldZero() {
    Camera2D camera = new Camera2D();
    camera.setViewport(0, 0);
    camera.setWorld(0, 0);
    camera.follow(10, 10);
    assertEquals(0.0, camera.x(), 1e-9);
    assertEquals(0.0, camera.y(), 1e-9);
  }

  @Test
  public void clampingClampsOnlyTheTargetAxis() {
    Camera2D camera = new Camera2D();
    camera.setViewport(100, 100);
    camera.setWorld(1000, 1000);
    camera.follow(1500, 300);
    assertEquals(950.0, camera.x(), 1e-9);
    assertEquals(300.0, camera.y(), 1e-9);
  }
}
