package com.opensilkroadmap.app.world;

import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/**
 * Real sector terrain heights normalized into the documented {@code .hg}
 * (VSHG v1) container, derived read-only from the real VSRO-R 1.193
 * {@code Map.pk2 /{y}/{x}.m} files during Phase 10.
 *
 * <p>Verified layout (all little-endian):
 * {@code [4B 'VSHG'][u16 version=1][u16 size][f32 step][size*size f32 heights]}.
 * Heights are stored row-major as {@code [z][x]}. A full sector grid is 97x97
 * with a 20.0-unit step and a 1920.0-unit sector side.
 *
 * <p>Sampling is a clamped bilinear interpolation of the real heights; the
 * world-space origin mapping is the verified formula
 * {@code world = (sector - refSector) * 1920 + local}. Values outside the grid
 * are clamped to the nearest edge, never extrapolated.
 */
public final class TerrainHeightGrid {
  /** 'VSHG' as read little-endian from the on-disk 4 magic bytes. */
  public static final int MAGIC = 0x47485356;
  public static final int VERSION = 1;
  public static final int HEADER_BYTES = 12;
  public static final float SECTOR_WORLD = 1920.0f;
  public static final int DEFAULT_SIZE = 97;
  public static final float DEFAULT_STEP = 20.0f;

  private final int size;
  private final float step;
  private final float[] heights;
  private final float min;
  private final float max;

  private TerrainHeightGrid(int size, float step, float[] heights) {
    this.size = size;
    this.step = step;
    this.heights = heights;
    float lo = Float.POSITIVE_INFINITY;
    float hi = Float.NEGATIVE_INFINITY;
    for (float h : heights) {
      lo = Math.min(lo, h);
      hi = Math.max(hi, h);
    }
    this.min = lo;
    this.max = hi;
  }

  public static TerrainHeightGrid load(InputStream in) throws IOException {
    ByteBuffer buf = ByteBuffer.wrap(readAll(in)).order(ByteOrder.LITTLE_ENDIAN);
    if (buf.remaining() < HEADER_BYTES || buf.getInt() != MAGIC) {
      throw new IOException("not a .hg (VSHG v1) height-grid container");
    }
    int version = buf.getShort() & 0xFFFF;
    if (version != VERSION) {
      throw new IOException("unsupported .hg version " + version);
    }
    int size = buf.getShort() & 0xFFFF;
    float step = buf.getFloat();
    if (size <= 0) {
      throw new IOException("invalid .hg grid size " + size);
    }
    int count = size * size;
    if (buf.remaining() < count * 4L) {
      throw new IOException(".hg truncated: expected " + count + " floats");
    }
    float[] heights = new float[count];
    for (int i = 0; i < count; i++) {
      heights[i] = buf.getFloat();
    }
    return new TerrainHeightGrid(size, step, heights);
  }

  private static byte[] readAll(InputStream in) throws IOException {
    java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
    byte[] tmp = new byte[8192];
    int n;
    while ((n = in.read(tmp)) != -1) {
      out.write(tmp, 0, n);
    }
    return out.toByteArray();
  }

  public int size() {
    return size;
  }

  public float step() {
    return step;
  }

  public float min() {
    return min;
  }

  public float max() {
    return max;
  }

  /** Height at grid cell (z, x); z is the row, x the column. */
  public float height(int z, int x) {
    return heights[z * size + x];
  }

  /**
   * Bilinear sample of the real height grid at local sector coordinates
   * {@code (localX, localZ)}. Values are clamped to the grid, never
   * extrapolated beyond its edges.
   */
  public float sampleLocal(float localX, float localZ) {
    float gx = localX / step;
    float gz = localZ / step;
    gx = clamp(gx, 0f, size - 1);
    gz = clamp(gz, 0f, size - 1);
    int x0 = (int) gx;
    int z0 = (int) gz;
    int x1 = Math.min(x0 + 1, size - 1);
    int z1 = Math.min(z0 + 1, size - 1);
    float fx = gx - x0;
    float fz = gz - z0;
    float h00 = height(z0, x0);
    float h10 = height(z0, x1);
    float h01 = height(z1, x0);
    float h11 = height(z1, x1);
    float top = h00 + (h10 - h00) * fx;
    float bottom = h01 + (h11 - h01) * fx;
    return top + (bottom - top) * fz;
  }

  /** Height in world coordinates relative to this sector's origin. */
  public float sampleWorld(float worldX, float worldZ, float originX, float originZ) {
    return sampleLocal(worldX - originX, worldZ - originZ);
  }

  private static float clamp(float v, float lo, float hi) {
    return v < lo ? lo : (v > hi ? hi : v);
  }
}
