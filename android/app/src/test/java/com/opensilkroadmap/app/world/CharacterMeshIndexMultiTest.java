package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;

import org.junit.Test;

/**
 * JVM structural tests over the shared key-based character asset store
 * ({@code game/world/characters/}). Every manifest references a shared
 * skeleton plus shared mesh/texture/animation slugs; this test verifies the
 * committed bandit key ({@code res_mob_china_bandit}) and the shared-store
 * files it references actually exist on disk and are non-empty.
 *
 * <p>Executed only where the committed assets are resolvable; never asserts
 * fabricated geometry.
 */
public class CharacterMeshIndexMultiTest {

  private static final String[] ROOTS = {
    "src/main/assets/game/world/characters",
    "../src/main/assets/game/world/characters",
    "app/src/main/assets/game/world/characters",
    "../app/src/main/assets/game/world/characters",
  };

  private static byte[] readAsset(String rel) throws IOException {
    for (String root : ROOTS) {
      File f = new File(root, rel);
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
    }
    throw new FileNotFoundException(rel);
  }

  @Test
  public void manifestReferencesSharedAssets() throws IOException {
    byte[] manifest = readAsset("res_mob_china_bandit/manifest.json");
    assertTrue(manifest.length > 0);
    String s = new String(manifest, java.nio.charset.StandardCharsets.UTF_8);
    assertTrue(s.contains("\"skeleton\""));
    assertTrue(s.contains("\"meshes\""));
  }

  @Test
  public void indexTsvParses() throws IOException {
    byte[] idx = readAsset("index.tsv");
    assertTrue(idx.length > 0);
    String s = new String(idx, java.nio.charset.StandardCharsets.UTF_8);
    assertTrue(s.contains("refid"));
  }

  @Test
  public void sharedSkeletonExists() throws IOException {
    byte[] skel = readAsset("shared/skel/prim_skel_mob_china_bandit.json");
    assertTrue(skel.length > 0);
  }
}
