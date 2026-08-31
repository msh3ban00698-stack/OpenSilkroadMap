package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.util.LinkedHashSet;
import java.util.Set;

import org.junit.Test;

import com.opensilkroadmap.app.data.NpcSpawnIndex;
import com.opensilkroadmap.app.data.TsvTable;

/**
 * TASK D: NPC -> spawn linkage over the real committed tables
 * ({@code characters/index.tsv} + {@code textdata/npcpos.tsv}).
 *
 * <p>Proves the bounded, data-driven representation the runtime uses: a world
 * spawn is renderable only when its {@code characterRefId} maps through
 * {@link CharacterCatalog} to a key whose manifest is committed. 14,800 world
 * spawns split as 10,147 renderable and 4,653 skipped (UNKNOWN artifacts,
 * PARTIAL karkadann, and refids absent from the index). No coordinates or
 * identities are fabricated; skipped spawns stay un-drawn.
 */
public class NpcCharacterLinkageTest {

  private static final String[] ASSET_DIRS = {
    "src/main/assets/game/world/characters",
    "../src/main/assets/game/world/characters",
    "app/src/main/assets/game/world/characters",
    "../app/src/main/assets/game/world/characters",
  };

  private static File findRoot() {
    for (String dir : ASSET_DIRS) {
      File f = new File(dir);
      if (f.isDirectory()) {
        return f;
      }
    }
    return null;
  }

  private static Set<Long> refidsWithStatus(String status)
      throws IOException {
    Set<Long> out = new LinkedHashSet<Long>();
    TsvTable idx = indexTable();
    for (String[] row : idx.rows()) {
      String refid = TsvTable.strAt(row, 0).trim();
      if (refid.isEmpty() || !refid.matches("\\d+")) {
        continue;
      }
      if (status.equals(TsvTable.strAt(row, 3))) {
        out.add(Long.valueOf(refid));
      }
    }
    return out;
  }

  private static TsvTable indexTable() throws IOException {
    String[] candidates = {
      "src/main/assets/game/world/characters/index.tsv",
      "../src/main/assets/game/world/characters/index.tsv",
      "app/src/main/assets/game/world/characters/index.tsv",
      "../app/src/main/assets/game/world/characters/index.tsv",
    };
    for (String p : candidates) {
      File f = new File(p);
      if (f.isFile()) {
        return TsvTable.parse("index.tsv",
            new java.io.InputStreamReader(new java.io.FileInputStream(f),
                java.nio.charset.StandardCharsets.UTF_8));
      }
    }
    throw new IOException("index.tsv not found via test paths");
  }

  @Test
  public void worldSpawnRenderableSplitMatchesData() throws IOException {
    NpcSpawnIndex npc = NpcSpawnIndex.loadDefault();
    CharacterCatalog catalog = CharacterCatalog.loadDefault();
    File root = findRoot();
    assertNotNull(root);
    assertEquals(14800, npc.worldCount());

    Set<Long> proven = refidsWithStatus("PROVEN");
    Set<Long> unknown = refidsWithStatus("UNKNOWN");
    Set<Long> partial = refidsWithStatus("PARTIAL");

    int renderable = 0;
    int skipped = 0;
    Set<Long> skippedRefids = new LinkedHashSet<Long>();
    Set<String> renderableKeys = new LinkedHashSet<String>();
    for (NpcSpawnIndex.Spawn sp : npc.inWindow(0, 255, 0, 255)) {
      String key = catalog.keyFor(sp.characterRefId);
      boolean hasModel = key != null
          && new File(root, key + "/manifest.json").isFile();
      if (hasModel) {
        renderable++;
        renderableKeys.add(key);
      } else {
        skipped++;
        skippedRefids.add(Long.valueOf(sp.characterRefId));
      }
    }
    assertEquals(10147, renderable);
    assertEquals(4653, skipped);
    // Every renderable key is a distinct PROVEN character.
    for (String key : renderableKeys) {
      assertTrue("renderable key " + key + " must be PROVEN",
          proven.contains(indexRefidForKey(key)));
    }
    // Every skipped spawn's refid is UNKNOWN, PARTIAL, or absent from index.
    for (Long refid : skippedRefids) {
      assertTrue("skipped refid " + refid + " must not be PROVEN",
          !proven.contains(refid));
      if (!unknown.contains(refid) && !partial.contains(refid)) {
        assertTrue("skipped refid " + refid + " absent from index",
            catalog.keyFor(refid.intValue()) == null);
      }
    }
  }

  private static Long indexRefidForKey(String key) throws IOException {
    TsvTable idx = indexTable();
    for (String[] row : idx.rows()) {
      String refid = TsvTable.strAt(row, 0).trim();
      if (refid.isEmpty() || !refid.matches("\\d+")) {
        continue;
      }
      if (key.equals(TsvTable.strAt(row, 1))) {
        return Long.valueOf(refid);
      }
    }
    return -1L;
  }

  @Test
  public void karkadannAndArtifactSpawnsAreSkipped() throws IOException {
    NpcSpawnIndex npc = NpcSpawnIndex.loadDefault();
    CharacterCatalog catalog = CharacterCatalog.loadDefault();
    File root = findRoot();
    assertNotNull(root);
    // PARTIAL karkadann (refid 43905) and UNKNOWN artifacts map to keys
    // without manifests -> every one of their world spawns is skipped.
    assertSkipped(npc, catalog, root, 43905, 11);
    assertSkipped(npc, catalog, root, 19553, 1);
    assertSkipped(npc, catalog, root, 36033, 52);
    // A PROVEN mob spawns every time.
    String crab = catalog.keyFor(14926);
    assertNotNull(crab);
    assertTrue(new File(root, crab + "/manifest.json").isFile());
  }

  private static void assertSkipped(NpcSpawnIndex npc,
                                    CharacterCatalog catalog, File root,
                                    int refid, int expectedSpawns) {
    int seen = 0;
    for (NpcSpawnIndex.Spawn sp : npc.inWindow(0, 255, 0, 255)) {
      if (sp.characterRefId != refid) {
        continue;
      }
      seen++;
      String key = catalog.keyFor(refid);
      assertTrue("refid " + refid + " must not be renderable",
          key == null || !new File(root, key + "/manifest.json").isFile());
    }
    assertEquals(expectedSpawns, seen);
  }
}
