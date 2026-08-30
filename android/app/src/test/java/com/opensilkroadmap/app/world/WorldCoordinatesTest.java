package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class WorldCoordinatesTest {

  @Test
  public void verifiedSectorWorldConstant() {
    assertEquals(1920.0f, WorldCoordinates.SECTOR_WORLD, 1e-6f);
  }

  @Test
  public void regionPackUnpackIsBijective() {
    int[] cases = {0, 1, 0x64, 0x6401, 0xFFFF, 0x64FF};
    for (int code : cases) {
      int[] s = WorldCoordinates.unpackRegion(code);
      assertEquals(code, WorldCoordinates.packRegion(s[0], s[1]));
    }
  }

  @Test
  public void unpackRegionMatchesVerifiedNpcposSemantics() {
    int[] s = WorldCoordinates.unpackRegion(0x6441);
    assertEquals(0x41, s[0]);
    assertEquals(0x64, s[1]);
  }

  @Test
  public void sectorWorldOriginUsesVerifiedFormula() {
    assertEquals(3 * 1920.0f, WorldCoordinates.sectorWorldX(103, 100), 1e-4f);
    assertEquals(0.0f, WorldCoordinates.sectorWorldZ(76, 76), 1e-4f);
  }

  @Test
  public void npcToWorldMatchesVerifiedReference() {
    float[] w = WorldCoordinates.npcToWorld(500f, 300f, WorldCoordinates.packRegion(103, 76), 100, 76);
    assertEquals(500f + 3 * 1920.0f, w[0], 1e-3f);
    assertEquals(300f, w[1], 1e-3f);
  }
}
