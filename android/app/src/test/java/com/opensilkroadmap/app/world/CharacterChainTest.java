package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.Test;

/**
 * TASK B: the full refid -> key -> manifest -> shared skeleton/mesh/anim ->
 * runtime state chain over the REAL committed index
 * ({@code characters/index.tsv}, {@code coverage.json} semantics, and the
 * shared asset store).
 *
 * <p>Proven ground truth locked here:
 * <ul>
 *   <li>1,094 index rows: 1,078 PROVEN / 15 UNKNOWN / 1 PARTIAL; 472 distinct
 *       PROVEN keys (the {@code player} manifest is the 473rd, absent from the
 *       index because the player is never spawned by npcpos).</li>
 *   <li>Every PROVEN key has a manifest whose every shared reference is
 *       committed; every UNKNOWN/PARTIAL key has NO manifest (fail-closed).</li>
 *   <li>PARTIAL {@code res_mob_arabia_karkadann} (refid 43905): conversion
 *       failed, no manifest, only its shared skeleton + one mesh are committed —
 *       so it stays PARTIAL and is NOT runtime-loadable.</li>
 *   <li>UNKNOWN artifacts (gate pulley / property recall / quest teleport): no
 *       {@code .bsk}, zero committed assets, not characters.</li>
 * </ul>
 */
public class CharacterChainTest {

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

  private static byte[] readAsset(File root, String name) throws IOException {
    File f = new File(root, name);
    if (f.isFile()) {
      FileInputStream in = new FileInputStream(f);
      try {
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = in.read(buf)) != -1) {
          out.write(buf, 0, n);
        }
        return out.toByteArray();
      } finally {
        in.close();
      }
    }
    throw new IOException("asset not found: " + name);
  }

  private static List<String> assetPathsFor(File root, String key)
      throws IOException {
    byte[] bytes = readAsset(root, key + "/manifest.json");
    return CharacterMeshIndex.parseManifestAssetPaths(new InputStreamReader(
        new ByteArrayInputStream(bytes), StandardCharsets.UTF_8));
  }

  /** (status -> distinct keys) over the real index.tsv. */
  private static Map<String, Set<String>> indexStatusKeys()
      throws IOException {
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    com.opensilkroadmap.app.data.TsvTable t =
        com.opensilkroadmap.app.data.TsvTable.parse("index.tsv",
            new InputStreamReader(
                new ByteArrayInputStream(readAsset(root, "index.tsv")),
                StandardCharsets.UTF_8));
    Map<String, Set<String>> byStatus =
        new LinkedHashMap<String, Set<String>>();
    for (String[] row : t.rows()) {
      String refid = com.opensilkroadmap.app.data.TsvTable.strAt(row, 0).trim();
      if (refid.isEmpty()
          || !refid.matches("\\d+")) {
        continue; // header
      }
      String key = com.opensilkroadmap.app.data.TsvTable.strAt(row, 1);
      String status = com.opensilkroadmap.app.data.TsvTable.strAt(row, 3);
      Set<String> s = byStatus.get(status);
      if (s == null) {
        s = new LinkedHashSet<String>();
        byStatus.put(status, s);
      }
      s.add(key);
    }
    return byStatus;
  }

  /** (status -> row count) over the real index.tsv. */
  private static Map<String, Integer> indexStatusRows()
      throws IOException {
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    com.opensilkroadmap.app.data.TsvTable t =
        com.opensilkroadmap.app.data.TsvTable.parse("index.tsv",
            new InputStreamReader(
                new ByteArrayInputStream(readAsset(root, "index.tsv")),
                StandardCharsets.UTF_8));
    Map<String, Integer> rows = new LinkedHashMap<String, Integer>();
    for (String[] row : t.rows()) {
      String refid = com.opensilkroadmap.app.data.TsvTable.strAt(row, 0).trim();
      if (refid.isEmpty()
          || !refid.matches("\\d+")) {
        continue; // header
      }
      String status = com.opensilkroadmap.app.data.TsvTable.strAt(row, 3);
      Integer n = rows.get(status);
      rows.put(status, n == null ? 1 : n + 1);
    }
    return rows;
  }

  @Test
  public void catalogMapsProvenAndSpecialRefids() throws IOException {
    CharacterCatalog c = CharacterCatalog.loadDefault();
    assertEquals(1094, c.count());
    assertEquals("res_mob_asiam_crab", c.keyFor(14926));
    assertEquals("res_mob_arabia_karkadann", c.keyFor(43905));
    assertEquals("res_artifact_guild_pulley_gate_pulley", c.keyFor(19553));
    assertEquals("res_dun_property_com_property_recall", c.keyFor(36033));
    assertEquals("res_quest_ins_quest_teleport", c.keyFor(36031));
    assertNull("unknown refid fails closed", c.keyFor(999999));
  }

  @Test
  public void indexStatusCountsMatchAudit() throws IOException {
    Map<String, Set<String>> byStatus = indexStatusKeys();
    Map<String, Integer> rows = indexStatusRows();
    assertEquals(Integer.valueOf(1078), rows.get("PROVEN"));
    assertEquals(Integer.valueOf(15), rows.get("UNKNOWN"));
    assertEquals(Integer.valueOf(1), rows.get("PARTIAL"));
    assertEquals(472, byStatus.get("PROVEN").size());
    assertEquals(3, byStatus.get("UNKNOWN").size());
    assertEquals(1, byStatus.get("PARTIAL").size());
  }

  @Test
  public void everyProvenKeyHasManifestAndCommittedRefs() throws IOException {
    File root = findRoot();
    Map<String, Set<String>> byStatus = indexStatusKeys();
    int provenWithManifest = 0;
    for (String key : byStatus.get("PROVEN")) {
      assertTrue("PROVEN key " + key + " must have a manifest",
          new File(root, key + "/manifest.json").isFile());
      provenWithManifest++;
      for (String ref : assetPathsFor(root, key)) {
        assertTrue("missing shared ref " + ref + " for " + key,
            new File(root, ref).isFile());
      }
    }
    // The 473rd manifest is the player (never spawned, absent from index).
    assertEquals(472, provenWithManifest);
    assertTrue(new File(root, "player/manifest.json").isFile());
    for (String ref : assetPathsFor(root, "player")) {
      assertTrue("missing player shared ref " + ref,
          new File(root, ref).isFile());
    }
  }

  @Test
  public void partialAndUnknownKeysHaveNoManifest() throws IOException {
    File root = findRoot();
    Map<String, Set<String>> byStatus = indexStatusKeys();
    for (String key : byStatus.get("PARTIAL")) {
      assertFalse2(key);
    }
    for (String key : byStatus.get("UNKNOWN")) {
      assertFalse2(key);
    }
    assertFalse2("res_mob_arabia_karkadann");
    assertFalse2("res_artifact_guild_pulley_gate_pulley");
    assertFalse2("res_dun_property_com_property_recall");
    assertFalse2("res_quest_ins_quest_teleport");
  }

  private static void assertFalse2(String key) {
    File root = findRoot();
    assertTrue(key + " must NOT be runtime-loadable (no manifest)",
        !new File(root, key + "/manifest.json").isFile());
  }

  @Test
  public void karkadannPartialKeepsOnlyProvenSkeletonInStore()
      throws IOException {
    File root = findRoot();
    // Skeleton conversion was PROVEN and is committed; the rest of the
    // character (manifest, full mesh set, animations) is NOT.
    assertTrue("karkadann shared skeleton must be committed",
        new File(root,
            "shared/skel/prim_skel_mob_arabia_karkadann.json").isFile());
    // No committed anim clips -> the character cannot animate at runtime.
    assertNoSharedSlug(root, "anim", "karkadann");
  }

  @Test
  public void unknownArtifactsCommitZeroAssets() throws IOException {
    File root = findRoot();
    String[] slugs = {"gate_pulley", "property_recall", "quest_teleport"};
    for (String slug : slugs) {
      assertNoSharedSlug(root, "skel", slug);
      assertNoSharedSlug(root, "mesh", slug);
      assertNoSharedSlug(root, "anim", slug);
    }
  }

  private static void assertNoSharedSlug(File root, String kind, String slug) {
    File dir = new File(root, "shared/" + kind);
    File[] files = dir.listFiles();
    assertNotNull("shared/" + kind + " must exist", files);
    for (File f : files) {
      assertTrue("unexpected committed asset " + f.getName() + " for " + slug,
          !f.getName().contains(slug));
    }
  }
}
