package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Map;
import org.junit.Test;

public class TerrainHeightGridTest {

  private static final String[] HG_PATHS = {
    "src/main/assets/game/world/76x103.hg",
    "../app/src/main/assets/game/world/76x103.hg",
    "app/src/main/assets/game/world/76x103.hg",
  };

  private static TerrainHeightGrid load76x103() throws IOException {
    for (String p : HG_PATHS) {
      java.io.File f = new java.io.File(p);
      if (f.isFile()) {
        return TerrainHeightGrid.load(new FileInputStream(f));
      }
    }
    throw new IOException("76x103.hg not found via default paths");
  }

  @Test
  public void realCommittedGridHasVerifiedGeometry() throws Exception {
    TerrainHeightGrid grid = load76x103();
    assertEquals(97, grid.size());
    assertEquals(20.0f, grid.step(), 1e-6);
    assertEquals(1920.0f, TerrainHeightGrid.SECTOR_WORLD, 1e-6);
  }

  @Test
  public void realCommittedGridHeightsMatchRealSector() throws Exception {
    TerrainHeightGrid grid = load76x103();
    // Real Map.pk2 /103/76.m (Constantinople): min -369.93 max 75.00.
    assertEquals(-369.93f, grid.min(), 0.1f);
    assertEquals(75.00f, grid.max(), 0.1f);
    assertTrue(grid.min() < grid.max());
  }

  @Test
  public void bilinearSampleIsClampedToGrid() throws Exception {
    TerrainHeightGrid grid = load76x103();
    float near = grid.sampleLocal(10f, 10f);
    // Grid corner must equal the real corner height.
    assertEquals(grid.height(0, 0), grid.sampleLocal(0f, 0f), 1e-4f);
    // Clamped far outside matches the far edge, never extrapolates.
    assertEquals(grid.height(96, 96), grid.sampleLocal(1e9f, 1e9f), 1e-4f);
    assertTrue(near >= grid.min() && near <= grid.max());
  }

  @Test
  public void sampleWorldUsesVerifiedOriginFormula() throws Exception {
    TerrainHeightGrid grid = load76x103();
    float h = grid.sampleWorld(1920f, 1920f, 0f, 0f);
    assertEquals(grid.height(96, 96), h, 1e-4f);
    float origin = grid.sampleWorld(0f, 0f, 0f, 0f);
    assertEquals(grid.height(0, 0), origin, 1e-4f);
  }

  @Test
  public void rejectsNonHgInput() throws Exception {
    try {
      TerrainHeightGrid.load(new java.io.ByteArrayInputStream("not-a-hg".getBytes("UTF-8")));
      fail("expected IOException");
    } catch (IOException expected) {
      assertNotNull(expected.getMessage());
    }
  }

  @Test
  public void worldIndexFilesExistForAllEmittedSectors() throws Exception {
    java.io.File index = new java.io.File("src/main/assets/game/world/world_index.tsv");
    if (!index.isFile()) {
      index = new java.io.File("../app/src/main/assets/game/world/world_index.tsv");
    }
    if (!index.isFile()) {
      return; // asset tree absent in this environment; committed elsewhere
    }
    int rows = 0;
    for (String line : java.nio.file.Files.readAllLines(index.toPath())) {
      if (line.isEmpty() || line.startsWith("#")) {
        continue;
      }
      String[] p = line.split("\t");
      if (p.length < 2) {
        continue;
      }
      java.io.File hg = new java.io.File("src/main/assets/game/world/" + p[0] + "x" + p[1] + ".hg");
      if (!hg.isFile()) {
        hg = new java.io.File("../app/src/main/assets/game/world/" + p[0] + "x" + p[1] + ".hg");
      }
      assertTrue("indexed " + p[0] + "x" + p[1] + ".hg missing", hg.isFile());
      rows++;
    }
    assertTrue(rows >= 8);
  }

  @Test
  public void worldRegionsLoadFromCommittedTsv() throws Exception {
    List<WorldRegion> regions = WorldRegion.loadDefault();
    assertTrue(regions.size() >= 50);
    Map<String, WorldRegion> byName = WorldRegion.indexByName(regions);
    WorldRegion constRegion = byName.get("Constantinople");
    assertNotNull(constRegion);
    assertEquals(81, constRegion.sx1);
    assertTrue(constRegion.containsSector(76, 105));
    assertTrue(!constRegion.containsSector(182, 96));
  }
}
