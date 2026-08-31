package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class InputControllerTest {

  @Test
  public void dragAccumulatesPan() {
    InputController in = new InputController();
    in.drag(10f, -5f);
    in.drag(2f, 3f);
    assertEquals(12f, in.consumePanX(), 1e-6);
    assertEquals(-2f, in.consumePanY(), 1e-6);
  }

  @Test
  public void consumePanDrainsAndResets() {
    InputController in = new InputController();
    in.drag(4f, 4f);
    assertEquals(4f, in.consumePanX(), 1e-6);
    assertEquals(0f, in.consumePanX(), 1e-6);
  }

  @Test
  public void pinchZoomMultiplies() {
    InputController in = new InputController();
    in.pinchZoom(1.5f);
    in.pinchZoom(2f);
    assertEquals(3f, in.consumeZoom(), 1e-6);
    assertEquals(1f, in.consumeZoom(), 1e-6);
  }

  @Test
  public void pinchZoomIgnoresNonPositive() {
    InputController in = new InputController();
    in.pinchZoom(0f);
    in.pinchZoom(-1f);
    assertEquals(1f, in.consumeZoom(), 1e-6);
  }

  @Test
  public void moveDirectionIsClamped() {
    InputController in = new InputController();
    in.setMove(2f, -3f);
    assertEquals(1f, in.moveX(), 1e-6);
    assertEquals(-1f, in.moveY(), 1e-6);
  }

  @Test
  public void resetClearsAllState() {
    InputController in = new InputController();
    in.drag(5f, 5f);
    in.pinchZoom(2f);
    in.setMove(1f, 1f);
    in.reset();
    assertEquals(0f, in.consumePanX(), 1e-6);
    assertEquals(0f, in.consumePanY(), 1e-6);
    assertEquals(1f, in.consumeZoom(), 1e-6);
    assertEquals(0f, in.moveX(), 1e-6);
    assertEquals(0f, in.moveY(), 1e-6);
  }

  @Test
  public void joystickInsideDeadZoneZerosMove() {
    InputController in = new InputController();
    in.joystick(0.1f * 100f, 0f, 100f);
    assertEquals(0f, in.moveX(), 1e-6);
    assertEquals(0f, in.moveY(), 1e-6);
  }

  @Test
  public void joystickAtRadiusNormalizesDirection() {
    InputController in = new InputController();
    in.joystick(100f, 0f, 100f);
    assertEquals(1f, in.moveX(), 1e-6);
    assertEquals(0f, in.moveY(), 1e-6);
    in.joystick(0f, -100f, 100f);
    assertEquals(0f, in.moveX(), 1e-6);
    assertEquals(-1f, in.moveY(), 1e-6);
  }

  @Test
  public void joystickBeyondRadiusClampsMagnitude() {
    InputController in = new InputController();
    in.joystick(250f, 0f, 100f);
    assertEquals(1f, in.moveX(), 1e-6);
    assertEquals(0f, in.moveY(), 1e-6);
  }

  @Test
  public void joystickInsideRadiusIsAnalog() {
    InputController in = new InputController();
    in.joystick(50f, 0f, 100f);
    assertEquals(0.5f, in.moveX(), 1e-6);
    assertEquals(0f, in.moveY(), 1e-6);
  }

  @Test
  public void joystickDiagonalNormalizesComponents() {
    InputController in = new InputController();
    double c = Math.sqrt(0.5);
    in.joystick((float) (100f * c), (float) (100f * c), 100f);
    assertEquals((float) c, in.moveX(), 1e-4);
    assertEquals((float) c, in.moveY(), 1e-4);
  }
}
