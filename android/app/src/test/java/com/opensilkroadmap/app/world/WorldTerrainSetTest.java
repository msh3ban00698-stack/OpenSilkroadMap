package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import org.junit.Test;

/**
 * JVM tests for {@link WorldTerrainSet} (Android-free).
 *
 * <p>Verifies the proven sector-world origin formula, world bounds, sector
 * lookup, fail-closed out-of-bounds sampling, and real boundary continuity
 * between the committed Jangan_Field sectors (156x89 / 156x90).
 */
public class WorldTerrainSetTest {

  private static TerrainHeightGrid grid(float[][] heights, float step) throws IOException {
    int size = heights.length;
    ByteBuffer buf = ByteBuffer.allocate(12 + size * size * 4).order(ByteOrder.LITTLE_ENDIAN);
    buf.putInt(TerrainHeightGrid.MAGIC);
    buf.putShort((short) TerrainHeightGrid.VERSION);
    buf.putShort((short) size);
    buf.putFloat(step);
    for (float[] row : heights) {
      for (float h : row) {
        buf.putFloat(h);
      }
    }
    return TerrainHeightGrid.load(new ByteArrayInputStream(buf.array()));
  }

  private static float[][] constant(int size, float value) {
    float[][] g = new float[size][size];
    for (float[] row : g) {
      Arrays.fill(row, value);
    }
    return g;
  }

  @Test
  public void worldBoundsAndSectorAt() throws IOException {
    WorldTerrainSet.Sector a = WorldTerrainSet.sector(156, 89, 156, 89, grid(constant(97, 100f), 20f));
    WorldTerrainSet.Sector b = WorldTerrainSet.sector(156, 90, 156, 89, grid(constant(97, 200f), 20f));
    WorldTerrainSet set = new WorldTerrainSet(Arrays.asList(a, b));

    assertEquals(2, set.sectorCount());
    assertEquals(0f, set.minX(), 1e-6f);
    assertEquals(0f, set.minZ(), 1e-6f);
    assertEquals(1920f, set.maxX(), 1e-6f); // 97 * 20
    assertEquals(3840f, set.maxZ(), 1e-6f); // 2 sectors * 1920
    assertEquals(1920f, set.width(), 1e-6f);
    assertEquals(3840f, set.height(), 1e-6f);

    WorldTerrainSet.Sector s = set.sectorAt(10f, 2000f);
    assertEquals(156, s.sx);
    assertEquals(90, s.sy);
  }

  @Test
  public void sampleWorldUsesSectorLocalCoordinates() throws IOException {
    WorldTerrainSet.Sector a = WorldTerrainSet.sector(156, 89, 156, 89, grid(constant(97, 100f), 20f));
    WorldTerrainSet.Sector b = WorldTerrainSet.sector(156, 90, 156, 89, grid(constant(97, 200f), 20f));
    WorldTerrainSet set = new WorldTerrainSet(Arrays.asList(a, b));

    assertEquals(100f, set.sampleWorld(10f, 10f), 1e-6f);
    assertEquals(200f, set.sampleWorld(10f, 2000f), 1e-6f); // sector 90 local z=80
  }

  @Test
  public void sampleOutsideIsNaN() throws IOException {
    WorldTerrainSet.Sector a = WorldTerrainSet.sector(156, 89, 156, 89, grid(constant(97, 100f), 20f));
    WorldTerrainSet set = new WorldTerrainSet(Arrays.asList(a));

    assertTrue(Float.isNaN(set.sampleWorld(-1f, -1f)));
    assertTrue(Float.isNaN(set.sampleWorld(5000f, 5000f)));
    assertNull(set.sectorAt(5000f, 5000f));
  }

  @Test
  public void realCommittedSectorsAreBoundaryContinuous() throws IOException {
    String base = "android/app/src/main/assets/game/world/";
    if (!new File(base + "156x89.hg").isFile()) {
      base = "app/src/main/assets/game/world/";
    }
    TerrainHeightGrid g1 = TerrainHeightGrid.load(open(base + "156x89.hg"));
    TerrainHeightGrid g2 = TerrainHeightGrid.load(open(base + "156x90.hg"));

    WorldTerrainSet set = new WorldTerrainSet(Arrays.asList(
        WorldTerrainSet.sector(156, 89, 156, 89, g1),
        WorldTerrainSet.sector(156, 90, 156, 89, g2)));

    assertEquals(2, set.sectorCount());
    assertEquals(1920f, set.width(), 1e-3f);
    assertEquals(3840f, set.height(), 1e-3f);
    // The shared edge row g1[size-1][x] must equal g2[0][x] (Phase 15 verified).
    for (int x = 0; x < 97; x += 16) {
      float south = g1.height(96, x);
      float north = g2.height(0, x);
      assertEquals("edge continuity at column " + x, south, north, 1e-2f);
    }
    float fromSouth = set.sampleWorld(960f, 1920f - 1f);
    float fromNorth = set.sampleWorld(960f, 1920f + 1f);
    assertTrue(Math.abs(fromSouth - fromNorth) < 10f);
  }

  private static InputStream open(String path) throws IOException {
    return new FileInputStream(path);
  }
}
