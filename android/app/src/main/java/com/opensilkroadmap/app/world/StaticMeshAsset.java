package com.opensilkroadmap.app.world;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.IOException;

/**
 * Parser for the committed "MSH1" mesh asset (Phase 17).
 *
 * <p>The binary container is produced offline from REAL original BMS meshes
 * (scripts/bms_to_asset.py); every field here mirrors that Python writer:
 *
 * <pre>
 *   0   4  magic "MSH1"
 *   4   1  version = 1
 *   5   1  layout    (0 = standard 44-byte, 1 = lightmap 52-byte)
 *   6   2  flags u16 (bit0 = has uv2)
 *   8   4  u32 vertex_count
 *   12  4  u32 triangle_count
 *   16  4  u32 non_static_vertices (informative)
 *   20  2  u16 texture_index
 *   22  2  u16 reserved
 *   24  .. vertex records (32 B or 40 B each)
 *   ..  .. u16 indices (triangle_count * 3)
 * </pre>
 *
 * <p>All geometry is the real decoded BMS geometry (positions, normals, UVs,
 * optional lightmap UV2); no geometry is invented. Pure JVM (no Android).
 */
public final class StaticMeshAsset {

  /** Parsed real mesh asset. Positions/normals/uvs are flat little-endian f32. */
  public static final class Mesh {
    public final int layout;
    public final boolean hasUv2;
    public final int vertexCount;
    public final int triangleCount;
    public final int nonStaticVertices;
    public final int textureIndex;

    /** 3 floats per vertex; element (i) covers vertex i / 3. */
    public final float[] positions;
    public final float[] normals;
    /** 2 floats per vertex. */
    public final float[] uvs;
    /** 2 floats per vertex when hasUv2, else null. */
    public final float[] uv2s;
    /** 3 indices per triangle, referencing positions/normals/uvs. */
    public final int[] indices;

    Mesh(
        int layout, boolean hasUv2, int vertexCount, int triangleCount,
        int nonStaticVertices, int textureIndex,
        float[] positions, float[] normals, float[] uvs, float[] uv2s, int[] indices) {
      this.layout = layout;
      this.hasUv2 = hasUv2;
      this.vertexCount = vertexCount;
      this.triangleCount = triangleCount;
      this.nonStaticVertices = nonStaticVertices;
      this.textureIndex = textureIndex;
      this.positions = positions;
      this.normals = normals;
      this.uvs = uvs;
      this.uv2s = uv2s;
      this.indices = indices;
    }
  }

  private StaticMeshAsset() {}

  /**
   * Parses a committed MSH1 blob, raising {@link IOException} on any structural
   * inconsistency (mirrors the Python reader's strictness).
   */
  public static Mesh parse(byte[] data) throws IOException {
    DataInputStream in =
        new DataInputStream(new ByteArrayInputStream(data));
    byte[] magic = new byte[4];
    in.readFully(magic);
    if (magic[0] != 'M' || magic[1] != 'S' || magic[2] != 'H' || magic[3] != '1') {
      throw new IOException("not an MSH1 blob");
    }
    int version = in.readUnsignedByte();
    if (version != 1) {
      throw new IOException("unsupported MSH version " + version);
    }
    int layout = in.readUnsignedByte();
    int flags = readLeU16(in);
    boolean hasUv2 = (flags & 1) != 0;
    int vertexCount = readLeU32(in);
    int triangleCount = readLeU32(in);
    int nonStatic = readLeU32(in);
    int textureIndex = readLeU16(in);
    readLeU16(in); // reserved
    if (layout != 0 && layout != 1) {
      throw new IOException("unsupported MSH layout " + layout);
    }
    int stride = layout == 0 ? 32 : 40;
    if (vertexCount < 0 || triangleCount < 0) {
      throw new IOException("negative counts");
    }
    long need = 24L + (long) vertexCount * stride + (long) triangleCount * 6L;
    if (need != data.length) {
      throw new IOException(
          "MSH size mismatch " + data.length + " != " + need);
    }
    float[] positions = new float[vertexCount * 3];
    float[] normals = new float[vertexCount * 3];
    float[] uvs = new float[vertexCount * 2];
    float[] uv2s = hasUv2 ? new float[vertexCount * 2] : null;
    for (int i = 0; i < vertexCount; i++) {
      int p = i * 3;
      int u = i * 2;
      positions[p] = readLeF32(in);
      positions[p + 1] = readLeF32(in);
      positions[p + 2] = readLeF32(in);
      normals[p] = readLeF32(in);
      normals[p + 1] = readLeF32(in);
      normals[p + 2] = readLeF32(in);
      uvs[u] = readLeF32(in);
      uvs[u + 1] = readLeF32(in);
      if (hasUv2) {
        uv2s[u] = readLeF32(in);
        uv2s[u + 1] = readLeF32(in);
      }
    }
    int[] indices = new int[triangleCount * 3];
    for (int i = 0; i < indices.length; i++) {
      indices[i] = readLeU16(in);
    }
    for (int i = 0; i < indices.length; i++) {
      if (indices[i] >= vertexCount) {
        throw new IOException("index " + indices[i] + " out of range");
      }
    }
    return new Mesh(
        layout, hasUv2, vertexCount, triangleCount, nonStatic, textureIndex,
        positions, normals, uvs, uv2s, indices);
  }

  private static int readLeU16(DataInputStream in) throws IOException {
    int lo = in.readUnsignedByte();
    int hi = in.readUnsignedByte();
    return lo | (hi << 8);
  }

  private static int readLeU32(DataInputStream in) throws IOException {
    int b0 = in.readUnsignedByte();
    int b1 = in.readUnsignedByte();
    int b2 = in.readUnsignedByte();
    int b3 = in.readUnsignedByte();
    return (b0 | (b1 << 8) | (b2 << 16) | (b3 << 24));
  }

  private static float readLeF32(DataInputStream in) throws IOException {
    return Float.intBitsToFloat(readLeU32(in));
  }
}
