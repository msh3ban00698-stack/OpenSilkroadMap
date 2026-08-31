package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
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
 * TASK C: player model chain over the committed {@code player} manifest.
 *
 * <p>PROVEN at file level: 5 animation clips and 16 skinned meshes resolve
 * against the shared store, and the committed {@code chinaman_skel} parses to
 * 38 bones ({@code xyzw}, root {@code Bip01}). The resolved clip list yields
 * only IDLE/WALK/RUN (the player manifest contains no attack/damage/death
 * clips).
 *
 * <p>PARTIAL / UNKNOWN (from provenance, not wired):
 * <ul>
 *   <li>The original {@code chinaman_fighter.bsr} references
 *       {@code europeman_skel} (43 bones), not the committed
 *       {@code chinaman_skel} — model identity is a PARTIAL mismatch.</li>
 *   <li>No static player spawn exists in the archives (npcpos is NPC-only),
 *       so player position/identity in the world stays UNKNOWN; the player is
 *       never spawned by the runtime.</li>
 * </ul>
 */
public class PlayerModelTest {

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

  private static List<IdleAnimResolver.Clip> clipsFor(File root, String key)
      throws IOException {
    byte[] bytes = readAsset(root, key + "/manifest.json");
    return CharacterMeshIndex.parseManifestClips(new InputStreamReader(
        new ByteArrayInputStream(bytes), StandardCharsets.UTF_8));
  }

  @Test
  public void playerManifestAndSharedRefsAreCommitted() throws IOException {
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    assertTrue(new File(root, "player/manifest.json").isFile());
    List<String> refs = assetPathsFor(root, "player");
    // 1 skeleton + 16 meshes + 16 textures + 5 animations.
    assertEquals(38, refs.size());
    boolean hasSkel = false;
    for (String ref : refs) {
      assertTrue("missing player shared ref " + ref,
          new File(root, ref).isFile());
      if (ref.startsWith("shared/skel/")) {
        hasSkel = true;
      }
    }
    assertTrue("player must reference a committed skeleton", hasSkel);
  }

  @Test
  public void playerSkeletonParsesToCommittedBoneCount() throws IOException {
    File root = findRoot();
    CharacterMeshIndex.Skeleton skel = CharacterMeshIndex.parseSkeleton(
        new InputStreamReader(new ByteArrayInputStream(readAsset(root,
            "shared/skel/prim_skel_char_china_chinaman_skel.json")),
            StandardCharsets.UTF_8));
    assertEquals(38, skel.boneCount);
    assertEquals("xyzw", skel.quaternionConvention);
    assertEquals("Bip01", skel.bone(0).name);
  }

  @Test
  public void playerResolvesOnlyLocomotionStates() throws IOException {
    File root = findRoot();
    Map<AnimState, IdleAnimResolver.Clip> m = AnimStateResolver.resolve(
        clipsFor(root, "player"));
    assertEquals(3, m.size());
    assertEquals("chinaman_standbattle", m.get(AnimState.IDLE).name);
    assertEquals("chinaman_fighter_walkforward", m.get(AnimState.WALK).name);
    assertEquals("chinaman_fighter_runforward_sword", m.get(AnimState.RUN).name);
    assertFalse(m.containsKey(AnimState.ATTACK));
    assertFalse(m.containsKey(AnimState.DAMAGE));
    assertFalse(m.containsKey(AnimState.DEATH));
  }
}
