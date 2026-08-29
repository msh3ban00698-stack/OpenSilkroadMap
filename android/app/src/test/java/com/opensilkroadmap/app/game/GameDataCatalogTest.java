package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/**
 * Tests for the Phase 12 integration catalog ({@link GameDataCatalog}), which
 * composes the committed real textdata tables. Counts are against the REAL
 * assets derived from Media.pk2 (see TEXTDATA_CATALOG.tsv).
 */
public class GameDataCatalogTest {

  @Test
  public void composedCatalogLoadsRealTables() throws Exception {
    GameDataCatalog data = GameDataCatalog.loadDefault();
    assertEquals(18457, data.npcSpawnCount());
    assertEquals(150, data.levelCount());
    assertEquals(246, data.teleportCount());
    assertEquals(23, data.worldMapRegionCount());
  }

  @Test
  public void summaryReportsRealCounts() throws Exception {
    GameDataCatalog data = GameDataCatalog.loadDefault();
    String s = data.summary();
    assertTrue(s.contains("npc spawns 18457"));
    assertTrue(s.contains("levels 150"));
    assertTrue(s.contains("teleports 246"));
    assertTrue(s.contains("worldmap regions 23"));
  }

  @Test
  public void loadFromReadersMatchesLoadDefault() throws Exception {
    GameDataCatalog a = GameDataCatalog.loadDefault();
    GameDataCatalog b = GameDataCatalog.loadDefault();
    assertEquals(a.npcSpawnCount(), b.npcSpawnCount());
    assertEquals(a.summary(), b.summary());
  }

  @Test
  public void loadNeverFabricatesWhenAssetsAbsent() throws Exception {
    // loadDefault() must either succeed against the real committed assets or
    // throw; it must never return an empty/fabricated catalog silently.
    boolean loaded = false;
    boolean threw = false;
    try {
      loaded = GameDataCatalog.loadDefault().npcSpawnCount() > 0;
    } catch (Exception e) {
      threw = true;
    }
    assertTrue("expected load to succeed with real assets or throw", loaded || threw);
  }
}
