package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class WorldGridTest {

  @Test
  public void verifiedBoundsConstantsMatchInventory() {
    assertEquals(26, WorldGrid.MIN_X);
    assertEquals(252, WorldGrid.MAX_X);
    assertEquals(35, WorldGrid.MIN_Y);
    assertEquals(126, WorldGrid.MAX_Y);
    assertEquals(5523, WorldGrid.MINIMAP_CELL_COUNT);
  }

  @Test
  public void inRangeAcceptsOnlyGridCells() {
    assertTrue(WorldGrid.inRange(26, 35));
    assertTrue(WorldGrid.inRange(252, 126));
    assertTrue(WorldGrid.inRange(182, 96));
    assertFalse(WorldGrid.inRange(25, 35));
    assertFalse(WorldGrid.inRange(253, 35));
    assertFalse(WorldGrid.inRange(26, 34));
    assertFalse(WorldGrid.inRange(26, 127));
  }

  @Test
  public void minimapSourcePathMatchesManifestKeys() {
    assertEquals("/minimap/182x96.ddj", WorldGrid.minimapSourcePath(182, 96));
    assertEquals("/minimap/26x35.ddj", WorldGrid.minimapSourcePath(26, 35));
  }

  @Test
  public void minimapAssetPathMatchesConvertedOutputs() {
    assertEquals("maps/minimap/182x96.png", WorldGrid.minimapAssetPath(182, 96));
  }
}
