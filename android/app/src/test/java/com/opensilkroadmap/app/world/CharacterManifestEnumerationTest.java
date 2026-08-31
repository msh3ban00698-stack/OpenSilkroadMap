package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import org.junit.Test;

/**
 * JVM structural enumeration over every committed character manifest
 * ({@code game/world/characters/<key>/manifest.json}, excluding {@code shared}).
 *
 * <p>Asserts the PROVEN ground truth: 473 manifest-bearing model directories,
 * 3,689 total animation entries, exactly one manifest with no animations, and
 * 309 manifests whose clip list resolves an idle/stand state. Every clip must
 * have a non-empty name and positive duration, and every shared asset
 * referenced by every manifest (skeleton/mesh/texture/animation) must be
 * committed. Fail-closed: any missing reference or malformed manifest fails the
 * test.
 */
public class CharacterManifestEnumerationTest {

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

  private static List<IdleAnimResolver.Clip> clipsFor(File root, String key)
      throws IOException {
    byte[] bytes = readAsset(root, key + "/manifest.json");
    return CharacterMeshIndex.parseManifestClips(new InputStreamReader(
        new ByteArrayInputStream(bytes), StandardCharsets.UTF_8));
  }

  private static List<String> assetPathsFor(File root, String key)
      throws IOException {
    byte[] bytes = readAsset(root, key + "/manifest.json");
    return CharacterMeshIndex.parseManifestAssetPaths(new InputStreamReader(
        new ByteArrayInputStream(bytes), StandardCharsets.UTF_8));
  }

  private static File[] manifestDirs(File root) {
    assertNotNull("characters assets root not found", root);
    File[] dirs = root.listFiles();
    assertNotNull(dirs);
    return dirs;
  }

  @Test
  public void everyManifestReferencesCommittedSharedAssets() throws IOException {
    File root = findRoot();
    for (File d : manifestDirs(root)) {
      if (!d.isDirectory() || d.getName().equals("shared")) {
        continue;
      }
      if (!new File(d, "manifest.json").isFile()) {
        continue;
      }
      for (String ref : assetPathsFor(root, d.getName())) {
        assertTrue("missing referenced asset " + ref + " for " + d.getName(),
            new File(root, ref).isFile());
      }
    }
  }

  @Test
  public void everyClipHasNameAndPositiveDuration() throws IOException {
    File root = findRoot();
    for (File d : manifestDirs(root)) {
      if (!d.isDirectory() || d.getName().equals("shared")) {
        continue;
      }
      if (!new File(d, "manifest.json").isFile()) {
        continue;
      }
      for (IdleAnimResolver.Clip c : clipsFor(root, d.getName())) {
        assertTrue("empty clip name in " + d.getName(), c.name.length() > 0);
        assertTrue("non-positive duration in " + d.getName() + ": " + c.name,
            c.durationMs > 0);
      }
    }
  }

  @Test
  public void committedManifestTotalsMatchAudit() throws IOException {
    File root = findRoot();
    int manifestCount = 0;
    int clipCount = 0;
    int zeroAnimManifests = 0;
    int idleManifests = 0;
    for (File d : manifestDirs(root)) {
      if (!d.isDirectory() || d.getName().equals("shared")) {
        continue;
      }
      if (!new File(d, "manifest.json").isFile()) {
        continue;
      }
      manifestCount++;
      List<IdleAnimResolver.Clip> clips = clipsFor(root, d.getName());
      clipCount += clips.size();
      if (clips.isEmpty()) {
        zeroAnimManifests++;
      }
      if (AnimStateResolver.resolve(clips).containsKey(AnimState.IDLE)) {
        idleManifests++;
      }
    }
    assertEquals(473, manifestCount);
    assertEquals(3689, clipCount);
    assertEquals(1, zeroAnimManifests);
    assertEquals(309, idleManifests);
  }
}
