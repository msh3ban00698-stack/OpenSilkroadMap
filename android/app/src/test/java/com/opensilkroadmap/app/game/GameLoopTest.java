package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class GameLoopTest {

  @Test
  public void runsFixedStepsForExactDelta() {
    GameLoop loop = new GameLoop(0.05, 0.25);
    assertEquals(2, loop.advance(0.10));
    assertEquals(2, loop.steps());
    assertEquals(0.10, loop.elapsedSeconds(), 1e-9);
  }

  @Test
  public void carriesAccumulatorAcrossFrames() {
    GameLoop loop = new GameLoop(0.05, 0.25);
    assertEquals(0, loop.advance(0.03));
    assertEquals(1, loop.advance(0.04));
    assertEquals(0, loop.advance(0.01));
    assertEquals(2, loop.advance(0.05));
  }

  @Test
  public void boundsCatchUpOnStall() {
    GameLoop loop = new GameLoop(0.05, 0.25);
    int steps = loop.advance(10.0);
    assertEquals(5, steps);
    assertEquals(5, loop.steps());
  }

  @Test
  public void ignoresNonPositiveDelta() {
    GameLoop loop = new GameLoop();
    assertEquals(0, loop.advance(0));
    assertEquals(0, loop.advance(-1));
    assertEquals(0, loop.steps());
  }

  @Test
  public void resetClearsState() {
    GameLoop loop = new GameLoop();
    loop.advance(0.5);
    loop.reset();
    assertEquals(0, loop.steps());
    assertEquals(0.0, loop.elapsedSeconds(), 1e-9);
  }

  @Test(expected = IllegalArgumentException.class)
  public void rejectsNonPositiveFixedDt() {
    new GameLoop(0.0, 0.25);
  }
}
