package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class GameClockTest {

  private static final long NS = 1_000_000_000L;

  @Test
  public void firstTickEstablishesBaseline() {
    GameClock clock = new GameClock();
    assertEquals(0.0, clock.tick(5 * NS), 1e-9);
  }

  @Test
  public void tickReturnsElapsedSeconds() {
    // Max delta raised above 0.5 so the clamp (default 0.1) cannot mask the
    // elapsed-seconds return value.
    GameClock clock = new GameClock(1.0);
    clock.tick(NS);
    assertEquals(0.5, clock.tick((long) (1.5 * NS)), 1e-9);
  }

  @Test
  public void clampsOversizedDelta() {
    GameClock clock = new GameClock(0.1);
    clock.tick(0);
    assertEquals(0.1, clock.tick((long) (10.0 * NS)), 1e-9);
  }

  @Test
  public void ignoresBackwardsClock() {
    GameClock clock = new GameClock();
    clock.tick(NS);
    assertEquals(0.0, clock.tick(NS - 1), 1e-9);
  }

  @Test
  public void resetClearsBaseline() {
    GameClock clock = new GameClock();
    clock.tick(NS);
    clock.reset();
    assertEquals(0.0, clock.tick(NS + 7), 1e-9);
  }

  @Test(expected = IllegalArgumentException.class)
  public void rejectsNonPositiveMaxDelta() {
    new GameClock(0.0);
  }
}
