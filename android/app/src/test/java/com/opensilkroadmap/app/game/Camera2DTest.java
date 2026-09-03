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

  @Test
  public void worldToViewCentersOnCamera() {
    Camera2D camera = new Camera2D();
    camera.setViewport(200, 100);
    camera.setWorld(1000, 1000);
    camera.setScale(2.0);
    camera.follow(100, 100);
    double[] p = camera.worldToView(100, 100);
    assertEquals(100.0, p[0], 1e-9);
    assertEquals(50.0, p[1], 1e-9);
  }

  @Test
  public void worldToViewUsesTopDownConvention() {
    Camera2D camera = new Camera2D();
    camera.setViewport(200, 200);
    camera.setWorld(1000, 1000);
    camera.setScale(1.0);
    camera.follow(100, 100);
    double[] east = camera.worldToView(110, 100);
    double[] north = camera.worldToView(100, 90);
    assertEquals(110.0, east[0], 1e-9);
    assertEquals(100.0, east[1], 1e-9);
    assertEquals(100.0, north[0], 1e-9);
    assertEquals(110.0, north[1], 1e-9);
  }

  @Test
  public void viewToWorldIsInverseOfWorldToView() {
    Camera2D camera = new Camera2D();
    camera.setViewport(320, 240);
    camera.setWorld(1000, 1000);
    camera.setScale(1.5);
    camera.follow(123, 456);
    double[] view = camera.worldToView(321, 654);
    double[] world = camera.viewToWorld(view[0], view[1]);
    assertEquals(321.0, world[0], 1e-6);
    assertEquals(654.0, world[1], 1e-6);
  }

  @Test
  public void coverScaleFillsLandscapeViewportWithoutSideLetterbox() {
    // Jangan_Field committed set: 1x2 sectors = 1920 x 3840 world units.
    // Landscape phone ~2340 x 1080: hardcoded 0.5 ppu paints the world only
    // 960px wide and leaves black side margins. Cover scale fills width.
    double viewW = 2340.0;
    double viewH = 1080.0;
    double worldW = 1920.0;
    double worldH = 3840.0;
    double letterbox = 0.5;
    assertEquals(960.0, worldW * letterbox, 1e-9);
    double cover = Camera2D.coverScale(viewW, viewH, worldW, worldH);
    assertEquals(viewW / worldW, cover, 1e-9);
    assertEquals(viewW, worldW * cover, 1e-9);
    Camera2D camera = new Camera2D();
    camera.setViewport(viewW, viewH);
    camera.setWorld(worldW, worldH);
    camera.setScale(cover);
    camera.follow(worldW / 2.0, worldH / 2.0);
    double[] left = camera.worldToView(0, worldH / 2.0);
    double[] right = camera.worldToView(worldW, worldH / 2.0);
    assertEquals(0.0, left[0], 1e-6);
    assertEquals(viewW, right[0], 1e-6);
  }

  @Test
  public void coverScaleRejectsNonPositiveExtents() {
    assertEquals(1.0, Camera2D.coverScale(0, 1080, 1920, 3840), 1e-9);
    assertEquals(1.0, Camera2D.coverScale(2340, 1080, 0, 3840), 1e-9);
  }

  @Test
  public void enterRegionAdoptsBoundsAndSnapsCenter() {
    Camera2D camera = new Camera2D();
    camera.setViewport(100, 100);
    camera.setWorld(1000, 1000);
    camera.follow(900, 900);
    assertEquals(900.0, camera.x(), 1e-9);
    assertEquals(900.0, camera.y(), 1e-9);
    camera.enterRegion(10, 10, 500, 500);
    assertEquals(50.0, camera.x(), 1e-9);
    assertEquals(50.0, camera.y(), 1e-9);
  }
}
