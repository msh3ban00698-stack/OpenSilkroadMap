package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import com.opensilkroadmap.app.world.WorldCoordinates;
import org.junit.Test;

/**
 * TASK A/D: player spawn fail-closed semantics and the proven world projection.
 *
 * <p>The supplied source/data has NO verified player start position (no SQL
 * server DB / start table in the 119,631-file inventory; npcpos.txt is
 * NPC-only), so the only constructible real spawn is {@code unknown()}: the
 * runtime must never invent a spawn coordinate. The {@code verified(...)}
 * factory exists purely to lock the PROVEN projection arithmetic
 * ({@code world = (sector - ref) * 1920 + local}) so a future verified source
 * lands in the correct world space; tests here use clearly-labeled synthetic
 * sources, never claimed real data.
 */
public class PlayerSpawnTest {

  @Test
  public void unknownSpawnFailsClosed() {
    PlayerSpawn s = PlayerSpawn.unknown("no verified spawn table in source");
    assertFalse(s.isKnown());
    assertEquals(PlayerSpawn.CODE_UNKNOWN, s.regionCode());
    assertEquals(PlayerSpawn.CODE_UNKNOWN, s.sectorX());
    assertTrue(Float.isNaN(s.localX()));
    assertTrue(Float.isNaN(s.worldX(156)));
    assertTrue(Float.isNaN(s.worldZ(89)));
    assertEquals("no verified spawn table in source", s.reason());
    assertEquals("", s.source());
  }

  @Test
  public void verifiedSpawnUnpacksProvenRegionPacking() {
    // region & 0xFF = x sector, region >> 8 = y sector (proven npcpos packing).
    PlayerSpawn s = PlayerSpawn.verified(
        WorldCoordinates.packRegion(156, 89), 10f, 0f, 20f, "SYNTHETIC test source");
    assertTrue(s.isKnown());
    assertEquals(156, s.sectorX());
    assertEquals(89, s.sectorY());
    assertEquals(10f, s.localX(), 1e-4f);
    assertEquals(20f, s.localZ(), 1e-4f);
  }

  @Test
  public void verifiedSpawnProjectsProvenWorldFormula() {
    // world = (sector - ref) * 1920 + local (WorldCoordinates, Phase 10).
    PlayerSpawn s = PlayerSpawn.verified(
        WorldCoordinates.packRegion(167, 96), 0f, 0f, 0f, "SYNTHETIC test source");
    assertEquals((167 - 156) * 1920f, s.worldX(156), 0.001f);
    assertEquals((96 - 89) * 1920f, s.worldZ(89), 0.001f);
    assertEquals(156f, s.worldX(167), 0.001f); // same-sector local is identity
    assertEquals(96f, s.worldZ(96), 0.001f);
  }

  @Test
  public void verifiedSpawnRequiresANamedSource() {
    try {
      PlayerSpawn.verified(0, 0f, 0f, 0f, null);
      fail("verified spawn without a source must throw");
    } catch (IllegalArgumentException expected) {
      // fail-closed
    }
    try {
      PlayerSpawn.verified(0, 0f, 0f, 0f, "   ");
      fail("verified spawn with a blank source must throw");
    } catch (IllegalArgumentException expected) {
      // fail-closed
    }
  }
}
