package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.junit.Test;

/**
 * JVM structural tests for the Phase 18 character assets (the committed
 * bandit NPC chain) against the COMMITTED assets: {@code skeleton.json},
 * {@code meshes.tsv}, the three MSH v2 {@code mesh/*.msh}, the bind-pose
 * skinning math, {@code npc_placements.tsv} and {@code anims.tsv}.
 *
 * <p>Counts are the PROVEN Phase 18 values (35 skeleton bones, 3 mesh parts,
 * 60 placements across 31 regions, 16 animations). The sword part is
 * single-influence (every vertex = R_bone*v + t_bone exactly), so its
 * skinned positions are asserted exactly against the skeleton's bind world
 * transform.
 *
 * <p>Executed only where the committed assets are resolvable; never asserts
 * fabricated geometry. Animation playback is NOT asserted (UNKNOWN).
 */
public class CharacterMeshIndexTest {

  private static final String[] ASSET_DIRS = {
    "src/main/assets/game/world/characters/bandit",
    "../src/main/assets/game/world/characters/bandit",
    "app/src/main/assets/game/world/characters/bandit",
    "../app/src/main/assets/game/world/characters/bandit",
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

  private static BufferedReader openTsv(String name) throws IOException {
    return new BufferedReader(new InputStreamReader(
        new ByteArrayInputStream(readAsset(name)), StandardCharsets.UTF_8));
  }

  private static CharacterMeshIndex.Skeleton loadSkeleton() throws IOException {
    return CharacterMeshIndex.parseSkeleton(new InputStreamReader(
        new ByteArrayInputStream(readAsset("skeleton.json")), StandardCharsets.UTF_8));
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
  public void meshesTsvThreeRealParts() throws IOException {
    List<CharacterMeshIndex.MeshRow> rows = CharacterMeshIndex.parseMeshes(openTsv("meshes.tsv"));
    assertEquals(3, rows.size());
    CharacterMeshIndex.MeshRow sword = rows.get(0);
    assertEquals(0, sword.partIdx);
    assertEquals("Bandit1", sword.material);
    assertEquals(76, sword.vcount);
    assertEquals(134, sword.tcount);
    assertEquals(76, sword.skinRecords);
    assertEquals(1, sword.boneCount);
    CharacterMeshIndex.MeshRow part1 = rows.get(1);
    assertEquals(214, part1.vcount);
    assertEquals(276, part1.tcount);
    assertEquals(18, part1.boneCount);
    CharacterMeshIndex.MeshRow part2 = rows.get(2);
    assertEquals(556, part2.vcount);
    assertEquals(766, part2.tcount);
    assertEquals(17, part2.boneCount);
  }

  @Test
  public void mshV2MeshesParseWithSkin() throws IOException {
    StaticMeshAsset.SkinnedMesh sword =
        StaticMeshAsset.parseSkinned(readAsset("mesh/bandit_sword.msh"));
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
        StaticMeshAsset.parseSkinned(readAsset("mesh/bandit_part1.msh"));
    assertEquals(214, part1.vertexCount);
    assertEquals(214, part1.skinRecords);
    assertEquals(18, part1.boneNames.length);
    StaticMeshAsset.SkinnedMesh part2 =
        StaticMeshAsset.parseSkinned(readAsset("mesh/bandit_part2.msh"));
    assertEquals(556, part2.vertexCount);
    assertEquals(17, part2.boneNames.length);
  }

  @Test
  public void swordSkinnedPositionsMatchSingleBoneTransform() throws IOException {
    CharacterMeshIndex.Skeleton skel = loadSkeleton();
    StaticMeshAsset.SkinnedMesh sword =
        StaticMeshAsset.parseSkinned(readAsset("mesh/bandit_sword.msh"));
    float[] out = CharacterMeshIndex.skinnedBindPositions(sword, skel);
    assertEquals(76 * 3, out.length);
    CharacterMeshIndex.Bone bone =
        skel.bone(skel.boneIndex(sword.boneNames[0]));
    float[] rot = new float[3];
    for (int i = 0; i < sword.vertexCount; i++) {
      rotate(
          new float[] {
            sword.positions[i * 3], sword.positions[i * 3 + 1], sword.positions[i * 3 + 2]
          },
          bone.bindWorldRot, rot);
      // Single influence: expected = R*v + t for the mapped bone.
      assertEquals(rot[0] + bone.bindWorldPos[0], out[i * 3], 1e-3f);
      assertEquals(rot[1] + bone.bindWorldPos[1], out[i * 3 + 1], 1e-3f);
      assertEquals(rot[2] + bone.bindWorldPos[2], out[i * 3 + 2], 1e-3f);
    }
  }

  @Test
  public void skinnedBindPositionsFiniteAndPlausible() throws IOException {
    CharacterMeshIndex.Skeleton skel = loadSkeleton();
    StaticMeshAsset.SkinnedMesh part1 =
        StaticMeshAsset.parseSkinned(readAsset("mesh/bandit_part1.msh"));
    float[] out = CharacterMeshIndex.skinnedBindPositions(part1, skel);
    assertEquals(214 * 3, out.length);
    float minX = Float.POSITIVE_INFINITY;
    float maxX = Float.NEGATIVE_INFINITY;
    float maxY = Float.NEGATIVE_INFINITY;
    for (int i = 0; i < out.length; i++) {
      assertTrue("finite value", Float.isFinite(out[i]));
    }
    for (int i = 0; i < part1.vertexCount; i++) {
      minX = Math.min(minX, out[i * 3]);
      maxX = Math.max(maxX, out[i * 3]);
      maxY = Math.max(maxY, out[i * 3 + 1]);
    }
    assertTrue("maxY within body+arm extent", maxY > 15f && maxY < 25f);
    assertTrue("left/right symmetric arms", Math.abs(minX + maxX) < 0.5f);
  }

  @Test
  public void placementsSixtyRealWorldCoords() throws IOException {
    List<CharacterMeshIndex.PlacementDef> placements =
        CharacterMeshIndex.parsePlacements(openTsv("npc_placements.tsv"));
    assertEquals(60, placements.size());
    Set<String> sectors = new HashSet<String>();
    int on156x90 = 0;
    for (CharacterMeshIndex.PlacementDef p : placements) {
      sectors.add(p.sectorSx + "x" + p.sectorSy);
      if (p.sectorSx == 156 && p.sectorSy == 90) {
        on156x90++;
      }
    }
    assertEquals(31, sectors.size());
    assertEquals(2, on156x90);
  }

  @Test
  public void placementsOnCommittedTerrainSector() throws IOException {
    List<CharacterMeshIndex.PlacementDef> placements =
        CharacterMeshIndex.parsePlacements(openTsv("npc_placements.tsv"));
    int found = 0;
    for (CharacterMeshIndex.PlacementDef p : placements) {
      if (p.sectorSx == 156 && p.sectorSy == 90) {
        found++;
        if (found == 1) {
          assertEquals(1592.44f, p.worldX, 1e-2f);
          assertEquals(3321.47f, p.worldZ, 1e-2f);
        } else {
          assertEquals(724.69f, p.worldX, 1e-2f);
          assertEquals(3583.85f, p.worldZ, 1e-2f);
        }
      }
    }
    assertEquals(2, found);
  }

  @Test
  public void animsTsvSixteenRowsWithStandAndWalk() throws IOException {
    List<CharacterMeshIndex.Anim> anims =
        CharacterMeshIndex.parseAnims(openTsv("anims.tsv"));
    assertEquals(16, anims.size());
    CharacterMeshIndex.Anim stand = null;
    CharacterMeshIndex.Anim walk = null;
    for (CharacterMeshIndex.Anim a : anims) {
      if ("bandit_stand01".equals(a.name)) {
        stand = a;
      }
      if ("bandit_walk".equals(a.name)) {
        walk = a;
      }
    }
    assertNotNull(stand);
    assertEquals(2000, stand.durationMs);
    assertEquals(5, stand.keyframes);
    assertEquals(34, stand.channels);
    assertEquals("anim/bandit_stand01.json", stand.animAsset);
    assertNotNull(walk);
    assertEquals(1333, walk.durationMs);
    assertEquals("anim/bandit_walk.json", walk.animAsset);
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

  private static void rotate(float[] v, float[] q, float[] out) {
    float x = q[0];
    float y = q[1];
    float z = q[2];
    float w = q[3];
    float vx = v[0];
    float vy = v[1];
    float vz = v[2];
    float cx = y * vz - z * vy;
    float cy = z * vx - x * vz;
    float cz = x * vy - y * vx;
    float dx = y * cz - z * cy;
    float dy = z * cx - x * cz;
    float dz = x * cy - y * cx;
    out[0] = vx + 2f * w * cx + 2f * dx;
    out[1] = vy + 2f * w * cy + 2f * dy;
    out[2] = vz + 2f * w * cz + 2f * dz;
  }
}
