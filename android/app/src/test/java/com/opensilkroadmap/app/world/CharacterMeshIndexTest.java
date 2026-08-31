package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

import org.junit.Test;

/**
 * JVM structural tests for the committed data-driven character assets against
 * the shared key-based asset store ({@code game/world/characters/}).
 *
 * <p>The bandit character key is {@code res_mob_china_bandit}; its manifest
 * references the shared skeleton slug {@code prim_skel_mob_china_bandit} and
 * the three shared skinned mesh slugs
 * {@code prim_mesh_mob_china_bandit_{sword,part1,part2}}. The skeleton has 35
 * bones (quaternion convention {@code xyzw}, path ending {@code bandit.bsk});
 * the sword part has 76 vertices / 134 triangles / 1 bone and is
 * single-influence (every vertex = R_bone*v + t_bone exactly), part1 has 214
 * vertices / 276 triangles / 18 bones, and part2 has 556 vertices / 766
 * triangles / 17 bones. These counts are the PROVEN Phase 20 values.
 *
 * <p>Executed only where the committed assets are resolvable; never asserts
 * fabricated geometry. Animation playback is NOT asserted (UNKNOWN).
 */
public class CharacterMeshIndexTest {

  private static final String[] ASSET_DIRS = {
    "src/main/assets/game/world/characters",
    "../src/main/assets/game/world/characters",
    "app/src/main/assets/game/world/characters",
    "../app/src/main/assets/game/world/characters",
  };

  private static byte[] readAsset(String name) throws IOException {
    for (String dir : ASSET_DIRS) {
      File f = new File(dir, name);
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
    throw new IOException("asset not found: " + name);
  }

  private static CharacterMeshIndex.Skeleton loadSkeleton() throws IOException {
    return CharacterMeshIndex.parseSkeleton(new InputStreamReader(
        new ByteArrayInputStream(readAsset("shared/skel/prim_skel_mob_china_bandit.json")),
        StandardCharsets.UTF_8));
  }

  @Test
  public void skeletonRealBanditBindPose() throws IOException {
    CharacterMeshIndex.Skeleton skel = loadSkeleton();
    assertEquals(35, skel.boneCount);
    assertEquals(35, skel.bones.length);
    assertEquals("xyzw", skel.quaternionConvention);
    assertTrue(skel.path.endsWith("bandit.bsk"));
    assertEquals("Bip01", skel.bone(0).name);
    assertEquals("", skel.bone(0).parent);
    assertEquals("Bip01", skel.bone(skel.boneIndex("Bip01 Pelvis")).parent);
  }

  @Test
  public void skeletonBindPoseAlignsWithMeshBounds() throws IOException {
    CharacterMeshIndex.Skeleton skel = loadSkeleton();
    CharacterMeshIndex.Bone toe = skel.bone(skel.boneIndex("Bip01 L Toe0"));
    CharacterMeshIndex.Bone pelvis = skel.bone(skel.boneIndex("Bip01 Pelvis"));
    CharacterMeshIndex.Bone head = skel.bone(skel.boneIndex("Bip01 Head"));
    // Proven: toes at mesh ground (y ~ 0.02), pelvis mid-body, head above.
    assertEquals(0.02f, toe.bindWorldPos[1], 0.5f);
    assertTrue("pelvis above ground", pelvis.bindWorldPos[1] > 5f);
    assertTrue("head above pelvis", head.bindWorldPos[1] > pelvis.bindWorldPos[1]);
    assertEquals(0f, head.bindWorldPos[0], 0.5f);
    // Left/right hands symmetric about the spine at shoulder height.
    CharacterMeshIndex.Bone lh = skel.bone(skel.boneIndex("Bip01 L Hand"));
    CharacterMeshIndex.Bone rh = skel.bone(skel.boneIndex("Bip01 R Hand"));
    assertEquals(rh.bindWorldPos[0], -lh.bindWorldPos[0], 1e-3f);
    assertEquals(lh.bindWorldPos[1], rh.bindWorldPos[1], 1e-3f);
  }

  @Test
  public void meshesThreeRealParts() throws IOException {
    StaticMeshAsset.SkinnedMesh sword =
        StaticMeshAsset.parseSkinned(readAsset("shared/mesh/prim_mesh_mob_china_bandit_sword.msh"));
    assertEquals(76, sword.vertexCount);
    assertEquals(134, sword.triangleCount);
    assertEquals(76, sword.bone1.length);
    assertEquals(1, sword.boneNames.length);
    assertEquals("Bip01 R Hand", sword.boneNames[0]);
    for (int i = 0; i < sword.vertexCount; i++) {
      assertTrue(sword.bone1[i] == 0);
      assertEquals(0, sword.weight2[i]);
    }
    StaticMeshAsset.SkinnedMesh part1 =
        StaticMeshAsset.parseSkinned(readAsset("shared/mesh/prim_mesh_mob_china_bandit_part1.msh"));
    assertEquals(214, part1.vertexCount);
    assertEquals(276, part1.triangleCount);
    assertEquals(18, part1.boneNames.length);
    StaticMeshAsset.SkinnedMesh part2 =
        StaticMeshAsset.parseSkinned(readAsset("shared/mesh/prim_mesh_mob_china_bandit_part2.msh"));
    assertEquals(556, part2.vertexCount);
    assertEquals(766, part2.triangleCount);
    assertEquals(17, part2.boneNames.length);
  }

  @Test
  public void swordBindPositionsAreRestVertices() throws IOException {
    CharacterMeshIndex.Skeleton skel = loadSkeleton();
    StaticMeshAsset.SkinnedMesh sword =
        StaticMeshAsset.parseSkinned(readAsset("shared/mesh/prim_mesh_mob_china_bandit_sword.msh"));
    float[] out = CharacterMeshIndex.skinnedBindPositions(sword, skel);
    assertEquals(76 * 3, out.length);
    // Rest vertices are stored in character bind pose; bind pose = identity.
    for (int i = 0; i < out.length; i++) {
      assertEquals(sword.positions[i], out[i], 1e-3f);
    }
  }

  @Test
  public void part1BindPositionsAreRestVerticesAndSymmetric() throws IOException {
    CharacterMeshIndex.Skeleton skel = loadSkeleton();
    StaticMeshAsset.SkinnedMesh part1 =
        StaticMeshAsset.parseSkinned(readAsset("shared/mesh/prim_mesh_mob_china_bandit_part1.msh"));
    float[] out = CharacterMeshIndex.skinnedBindPositions(part1, skel);
    assertEquals(214 * 3, out.length);
    float minX = Float.POSITIVE_INFINITY;
    float maxX = Float.NEGATIVE_INFINITY;
    float maxY = Float.NEGATIVE_INFINITY;
    for (int i = 0; i < out.length; i++) {
      assertTrue("finite value", Float.isFinite(out[i]));
      assertEquals(part1.positions[i], out[i], 1e-3f);
    }
    for (int i = 0; i < part1.vertexCount; i++) {
      minX = Math.min(minX, out[i * 3]);
      maxX = Math.max(maxX, out[i * 3]);
      maxY = Math.max(maxY, out[i * 3 + 1]);
    }
    // Real arm mesh: symmetric about the spine at shoulder height.
    assertTrue("maxY at arm slab", maxY > 12f && maxY < 13f);
    assertTrue("left/right symmetric arms", Math.abs(minX + maxX) < 0.5f);
  }

  @Test
  public void skinAtBindPoseReproducesRestVertices() throws IOException {
    CharacterMeshIndex.Skeleton skel = loadSkeleton();
    StaticMeshAsset.SkinnedMesh part1 =
        StaticMeshAsset.parseSkinned(readAsset("shared/mesh/prim_mesh_mob_china_bandit_part1.msh"));
    float[] out = CharacterRenderer.skin(skel, Pose.bind(skel), part1);
    assertEquals(214 * 3, out.length);
    for (int i = 0; i < out.length; i++) {
      assertEquals(part1.positions[i], out[i], 1e-3f);
    }
  }

  @Test
  public void v1MeshRejectedBySkinnedParser() throws IOException {
    byte[] v1 = readAsset("../objects/mesh/tre_tree03_01.msh");
    try {
      StaticMeshAsset.parseSkinned(v1);
      fail("expected IOException for v1 blob");
    } catch (IOException expected) {
      assertTrue(expected.getMessage().contains("MSH version"));
    }
  }
}
