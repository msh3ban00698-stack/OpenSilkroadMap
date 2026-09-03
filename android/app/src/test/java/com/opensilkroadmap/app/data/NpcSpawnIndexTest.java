package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.Test;

/**
 * JVM tests for {@link NpcSpawnIndex} (Android-free).
 *
 * <p>Verifies the corrected npcpos column semantics (Phase 13), world/dungeon
 * classification, world-coordinate projection, and sector-window query against
 * both a synthetic table and the committed real {@code npcpos.tsv}
 * (18,457 rows).
 */
public class NpcSpawnIndexTest {

  private static final String SYNTHETIC =
      "1001\t22940\t100.0\t50.0\t200.0\n"
          + "1002\t23196\t300.0\t60.0\t400.0\n"
          + "9999\t-1\t0.0\t0.0\t0.0\n";

  @Test
  public void classifiesWorldAndDungeonSpawns() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.parse(new StringReader(SYNTHETIC));
    assertEquals(2, idx.worldCount());
    assertEquals(1, idx.dungeonCount());
    assertEquals(3, idx.totalCount());
    assertEquals(0, idx.identifiedWorldCount());
    assertEquals(null, idx.worldSpawn(0).identity);
  }

  @Test
  public void projectsWorldCoordinatesFromVerifiedFormula() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.parse(new StringReader(SYNTHETIC));
    List<NpcSpawnIndex.Spawn> w = idx.inWindow(156, 156, 90, 90);
    assertEquals(1, w.size());
    NpcSpawnIndex.Spawn s = w.get(0);
    assertEquals(156, s.sectorX);
    assertEquals(90, s.sectorY);
    assertEquals(300.0f, s.worldX(156), 1e-6f);
    assertEquals(400.0f + 1920.0f, s.worldZ(89), 1e-6f);
    assertTrue(s.isWorld);
  }

  @Test
  public void windowQueryUsesInclusiveSectorBounds() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.parse(new StringReader(SYNTHETIC));
    assertEquals(1, idx.inWindow(156, 156, 89, 89).size());
    assertEquals(1, idx.inWindow(156, 156, 90, 90).size());
    assertEquals(2, idx.inWindow(156, 156, 89, 90).size());
    assertEquals(0, idx.inWindow(0, 0, 0, 0).size());
  }

  @Test
  public void realNpcPosTableMatchesVerifiedCounts() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.parse(open("npcpos.tsv"));
    assertEquals(18457, idx.totalCount());
    assertEquals(14800, idx.worldCount());
    assertEquals(3657, idx.dungeonCount());
    assertEquals(0, idx.identifiedWorldCount());
    assertEquals(3, idx.inWindow(156, 156, 90, 90).size());
    assertEquals(0, idx.inWindow(156, 156, 89, 89).size());
  }

  private static Reader open(String name) throws IOException {
    String[] paths = {
      "android/app/src/main/assets/game/textdata/" + name,
      "app/src/main/assets/game/textdata/" + name,
      "src/main/assets/game/textdata/" + name,
    };
    for (String p : paths) {
      File f = new File(p);
      if (f.isFile()) {
        return new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8);
      }
    }
    throw new IOException(name + " not found via test paths");
  }
}
