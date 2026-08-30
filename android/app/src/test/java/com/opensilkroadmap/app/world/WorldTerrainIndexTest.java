package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.List;
import org.junit.Test;

public class WorldTerrainIndexTest {

  @Test
  public void loadsCommittedIndexWithAllSectors() throws Exception {
    WorldTerrainIndex index = WorldTerrainIndex.loadDefault();
    assertTrue(index.size() >= 23);
  }

  @Test
  public void janganFieldRefSectorHasVerifiedMetadata() throws Exception {
    WorldTerrainIndex index = WorldTerrainIndex.loadDefault();
    WorldTerrainIndex.Entry e = index.find(156, 89);
    assertNotNull(e);
    assertEquals(97, e.size);
    assertEquals(866.25f, e.minH, 0.1f);
    assertEquals(2687.02f, e.maxH, 0.1f);
    assertEquals("53c5fe1ae346e60573e3ad823543f8800ce925e9d5d9ff10d3579f967bcb709e", e.sha256);
  }

  @Test
  public void missingSectorFailsClosed() throws Exception {
    WorldTerrainIndex index = WorldTerrainIndex.loadDefault();
    assertNull(index.find(182, 96));
    assertTrue(!index.contains(182, 96));
  }

  @Test
  public void firstInWindowSelectsDeterministicSector() throws Exception {
    WorldTerrainIndex index = WorldTerrainIndex.loadDefault();
    WorldTerrainIndex.Entry e = index.firstInWindow(156, 182, 89, 102);
    assertNotNull(e);
    assertEquals(156, e.sx);
    assertEquals(89, e.sy);
  }

  @Test
  public void hgAssetPathIsDeterministic() {
    assertEquals("game/world/156x89.hg", WorldTerrainIndex.hgAssetPath(156, 89));
  }

  @Test
  public void entriesAreSortedBySector() throws Exception {
    WorldTerrainIndex index = WorldTerrainIndex.loadDefault();
    List<WorldTerrainIndex.Entry> entries = index.entries();
    for (int i = 1; i < entries.size(); i++) {
      WorldTerrainIndex.Entry a = entries.get(i - 1);
      WorldTerrainIndex.Entry b = entries.get(i);
      assertTrue(a.sx < b.sx || (a.sx == b.sx && a.sy < b.sy));
    }
  }
}
