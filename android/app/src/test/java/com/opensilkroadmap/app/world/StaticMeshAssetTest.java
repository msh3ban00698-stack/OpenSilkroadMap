package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.Arrays;

import org.junit.Test;

/**
 * JVM tests for the Phase 17 MSH1 mesh-asset parser against the COMMITTED
 * real tree assets (derived from original {@code .bms} parts). Geometry
 * counts are the proven Phase 17 values for tre_tree02/03.
 *
 * <p>Executed only where the committed assets are resolvable; never asserts
 * fabricated geometry.
 */
public class StaticMeshAssetTest {

  private static final String[] ASSET_DIRS = {
    "src/main/assets/game/world/objects",
    "../src/main/assets/game/world/objects",
    "app/src/main/assets/game/world/objects",
    "../app/src/main/assets/game/world/objects",
  };

  private static byte[] readAsset(String name) throws IOException {
    for (String dir : ASSET_DIRS) {
      File f = new File(dir, name);
      if (f.isFile()) {
        FileInputStream in = new FileInputStream(f);
        try {
          ByteArrayOutputStream2 out = new ByteArrayOutputStream2();
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

  private static final class ByteArrayOutputStream2 extends java.io.ByteArrayOutputStream {
  }

  @Test
  public void treTree03_01_realGeometry() throws IOException {
    StaticMeshAsset.Mesh mesh = StaticMeshAsset.parse(readAsset("mesh/tre_tree03_01.msh"));
    assertEquals(0, mesh.layout);
    assertFalse(mesh.hasUv2);
    assertEquals(216, mesh.vertexCount);
    assertEquals(108, mesh.triangleCount);
    assertEquals(0, mesh.nonStaticVertices);
    assertEquals(216 * 3, mesh.positions.length);
    assertEquals(216 * 3, mesh.normals.length);
    assertEquals(216 * 2, mesh.uvs.length);
    assertNull(mesh.uv2s);
    assertEquals(108 * 3, mesh.indices.length);
    for (int i = 0; i < mesh.indices.length; i++) {
      assertTrue(mesh.indices[i] < mesh.vertexCount);
    }
  }

  @Test
  public void treTree03_02_realGeometryAndCanopyVertices() throws IOException {
    StaticMeshAsset.Mesh mesh = StaticMeshAsset.parse(readAsset("mesh/tre_tree03_02.msh"));
    assertEquals(154, mesh.vertexCount);
    assertEquals(192, mesh.triangleCount);
    assertEquals(50, mesh.nonStaticVertices);
  }

  @Test
  public void treTree02_01_realGeometry() throws IOException {
    StaticMeshAsset.Mesh mesh = StaticMeshAsset.parse(readAsset("mesh/tre_tree02_01.msh"));
    assertEquals(304, mesh.vertexCount);
    assertEquals(152, mesh.triangleCount);
    assertEquals(0, mesh.nonStaticVertices);
  }

  @Test
  public void allSixTreePartsPresent() throws IOException {
    String[] names = {
      "mesh/tre_tree03_01.msh", "mesh/tre_tree03_02.msh", "mesh/tre_tree03_03.msh",
      "mesh/tre_tree02_01.msh", "mesh/tre_tree02_02.msh", "mesh/tre_tree02_03.msh",
    };
    for (String name : names) {
      StaticMeshAsset.Mesh mesh = StaticMeshAsset.parse(readAsset(name));
      assertNotNull(mesh);
      assertTrue(mesh.vertexCount > 0);
      assertTrue(mesh.triangleCount > 0);
    }
  }

  @Test
  public void badMagicRejected() {
    try {
      StaticMeshAsset.parse("XXXX".getBytes(java.nio.charset.StandardCharsets.US_ASCII));
      org.junit.Assert.fail("expected IOException");
    } catch (IOException expected) {
      assertTrue(expected.getMessage().contains("MSH1"));
    }
  }

  @Test
  public void sizeMismatchRejected() throws IOException {
    byte[] data = readAsset("mesh/tre_tree03_01.msh");
    byte[] truncated = Arrays.copyOf(data, data.length - 1);
    try {
      StaticMeshAsset.parse(truncated);
      org.junit.Assert.fail("expected IOException");
    } catch (IOException expected) {
      assertTrue(expected.getMessage().contains("size mismatch"));
    }
  }
}
