package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

/**
 * TASK D: movement integration math. Only the arithmetic is proven here; the
 * authentic VSRO walk/run speeds are UNKNOWN from source, so the default config
 * reports UNKNOWN speed and the mover never fabricates displacement. A
 * positive-speed config (future verified source only) exercises the proven
 * formula {@code displacement = normalized direction * speed * dt}.
 */
public class PlayerMoverTest {

  @Test
  public void unknownSpeedProducesNoDisplacement() {
    PlayerMover.Step step = PlayerMover.step(
        1f, 0f, 0.05, PlayerMovementConfig.unknownSpeed());
    assertFalse(step.moved);
    assertEquals(PlayerMover.REASON_UNKNOWN_SPEED, step.reason);
    assertEquals(0.0, step.dx, 1e-9);
    assertEquals(0.0, step.dz, 1e-9);
    // The normalized direction is still reported (for heading/animation).
    assertEquals(1f, step.dirX, 1e-6f);
    assertEquals(0f, step.dirZ, 1e-6f);
  }

  @Test
  public void zeroDirectionNeverMoves() {
    PlayerMover.Step step = PlayerMover.step(
        0f, 0f, 0.05, PlayerMovementConfig.withWalkSpeed(10.0));
    assertFalse(step.moved);
    assertEquals(PlayerMover.REASON_ZERO_DIRECTION, step.reason);
  }

  @Test
  public void provenSpeedIntegratesDisplacement() {
    PlayerMover.Step step = PlayerMover.step(
        1f, 0f, 0.05, PlayerMovementConfig.withWalkSpeed(10.0));
    assertTrue(step.moved);
    assertEquals(PlayerMover.REASON_MOVED, step.reason);
    assertEquals(0.5, step.dx, 1e-9); // 10 * 0.05
    assertEquals(0.0, step.dz, 1e-9);
  }

  @Test
  public void normalizedDiagonalKeepsUnitLength() {
    double c = Math.sqrt(0.5);
    PlayerMover.Step step = PlayerMover.step(
        (float) c, (float) c, 1.0, PlayerMovementConfig.withWalkSpeed(1.0));
    assertTrue(step.moved);
    assertEquals(1.0, Math.hypot(step.dx, step.dz), 1e-6);
  }

  @Test
  public void headingMatchesProvenPlacementRotation() {
    // worldVertex rotates local +Z by h -> world (sin h, cos h). Heading must
    // therefore be the inverse: atan2(dirX, dirZ).
    for (float[] dir : new float[][] {{1f, 0f}, {0f, 1f}, {0f, -1f}, {-1f, 0f}}) {
      double h = PlayerMover.headingFromDirection(dir[0], dir[1]);
      assertEquals(dir[0], (float) Math.sin(h), 1e-5f);
      assertEquals(dir[1], (float) Math.cos(h), 1e-5f);
    }
    assertEquals(0.0, PlayerMover.headingFromDirection(0f, 0f), 1e-9);
  }

  @Test
  public void configRequiresPositiveSpeed() {
    assertFalse(PlayerMovementConfig.unknownSpeed().speedProven());
    assertTrue(Double.isNaN(PlayerMovementConfig.unknownSpeed()
        .walkSpeedUnitsPerSecond()));
    PlayerMovementConfig c = PlayerMovementConfig.withWalkSpeed(3.5);
    assertTrue(c.speedProven());
    assertEquals(3.5, c.walkSpeedUnitsPerSecond(), 1e-9);
    try {
      PlayerMovementConfig.withWalkSpeed(0.0);
      fail("non-positive speed must be rejected");
    } catch (IllegalArgumentException expected) {
      // fail-closed
    }
  }
}
