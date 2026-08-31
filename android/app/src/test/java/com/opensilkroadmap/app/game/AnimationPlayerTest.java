package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class AnimationPlayerTest {

  @Test
  public void setClipStartsAtZero() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("stand", 2000);
    assertEquals(0, p.currentTimeMs());
    assertEquals("stand", p.name());
    assertEquals(2000, p.durationMs());
    assertTrue(p.looping());
  }

  @Test
  public void advanceAccumulatesMilliseconds() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("stand", 2000);
    p.advance(0.5);
    assertEquals(500, p.currentTimeMs());
  }

  @Test
  public void loopingWrapsAtDuration() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("stand", 2000);
    p.advance(2.5);
    assertEquals(500, p.currentTimeMs());
  }

  @Test
  public void nonLoopingClampsAtDuration() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("die", 2666, false);
    p.advance(5.0);
    assertEquals(2666, p.currentTimeMs());
  }

  @Test
  public void nonLoopingReportsFinishedAtEnd() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("die", 1000, false);
    assertTrue(!p.isFinished());
    p.advance(0.5);
    assertTrue(!p.isFinished());
    p.advance(1.0);
    assertTrue(p.isFinished());
  }

  @Test
  public void loopingNeverReportsFinished() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("stand", 1000, true);
    p.advance(5.0);
    assertTrue(!p.isFinished());
  }

  @Test
  public void clearRemovesActiveClip() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("stand", 2000);
    p.clear();
    assertEquals("", p.name());
    assertEquals(0, p.durationMs());
    assertEquals(0, p.currentTimeMs());
  }

  @Test
  public void ignoresNonPositiveDelta() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("stand", 2000);
    p.advance(0.5);
    p.advance(0.0);
    p.advance(-1.0);
    assertEquals(500, p.currentTimeMs());
  }

  @Test
  public void resetClearsElapsed() {
    AnimationPlayer p = new AnimationPlayer();
    p.setClip("stand", 2000);
    p.advance(1.0);
    p.reset();
    assertEquals(0, p.currentTimeMs());
  }

  @Test(expected = IllegalArgumentException.class)
  public void rejectsNonPositiveDuration() {
    new AnimationPlayer().setClip("stand", 0);
  }
}
