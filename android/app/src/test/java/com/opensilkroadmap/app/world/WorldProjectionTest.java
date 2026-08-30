package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class WorldProjectionTest {

  @Test
  public void cameraCenteredWorldAtScreenCenter() {
    float[] p = WorldProjection.worldToView(100f, 100f, 100f, 100f, 0.5f);
    assertEquals(0f, p[0], 1e-6f);
    assertEquals(0f, p[1], 1e-6f);
  }

  @Test
  public void eastAndNorthAxesAreOrthogonalTopDown() {
    float[] east = WorldProjection.worldToView(110f, 100f, 100f, 100f, 0.5f);
    float[] north = WorldProjection.worldToView(100f, 90f, 100f, 100f, 0.5f);
    assertEquals(5f, east[0], 1e-6f);
    assertEquals(0f, east[1], 1e-6f);
    assertEquals(0f, north[0], 1e-6f);
    assertEquals(5f, north[1], 1e-6f);
  }

  @Test
  public void heightColorRampIsMonotonicAndClamped() {
    int low = WorldProjection.heightColor(0f, 0f, 100f);
    int high = WorldProjection.heightColor(100f, 0f, 100f);
    int below = WorldProjection.heightColor(-50f, 0f, 100f);
    int above = WorldProjection.heightColor(150f, 0f, 100f);
    assertEquals(below, low);
    assertEquals(above, high);
    assertEquals(0xFF000000, low);
    assertEquals(0xFFFFFFFF, high);
    assertEquals(0xFFFFFFFF, WorldProjection.opaque(high));
  }
}
