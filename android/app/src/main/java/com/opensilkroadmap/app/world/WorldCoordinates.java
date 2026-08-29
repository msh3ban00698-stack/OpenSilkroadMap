package com.opensilkroadmap.app.world;

/**
 * Verified VSRO world-coordinate conversions (Phase 10).
 *
 * <p>Verified against real source data:
 * <ul>
 *   <li>sector world size = {@value #SECTOR_WORLD} units (terrain grid 97x97,
 *       step {@value #DEFAULT_STEP}, sector side 6*16*{@value #DEFAULT_STEP});</li>
 *   <li>region packing (npcpos): {@code region & 0xFF} = x sector,
 *       {@code region >> 8} = y sector;</li>
 *   <li>{@code world = (sector - refSector) * 1920 + local} — the reference
 *       formula used by the client reference implementations.</li>
 * </ul>
 *
 * <p>Everything here is pure arithmetic on the verified constants; no
 * world-space origin is invented.
 */
public final class WorldCoordinates {
  public static final float SECTOR_WORLD = 1920.0f;

  private WorldCoordinates() {}

  /** {@code region & 0xFF} = x sector, {@code region >> 8} = y sector. */
  public static int[] unpackRegion(int region) {
    return new int[] {region & 0xFF, region >> 8};
  }

  public static int packRegion(int sx, int sy) {
    return (sy << 8) | (sx & 0xFF);
  }

  /** World-space x of sector {@code sx} relative to reference sector {@code refSx}. */
  public static float sectorWorldX(int sx, int refSx) {
    return (sx - refSx) * SECTOR_WORLD;
  }

  /** World-space z of sector {@code sy} relative to reference sector {@code refSy}. */
  public static float sectorWorldZ(int sy, int refSy) {
    return (sy - refSy) * SECTOR_WORLD;
  }

  /** npcpos local (x, z) + region code -> world (x, z) relative to a ref sector. */
  public static float[] npcToWorld(float x, float z, int region, int refSx, int refSy) {
    int[] s = unpackRegion(region);
    return new float[] {
      x + (s[0] - refSx) * SECTOR_WORLD,
      z + (s[1] - refSy) * SECTOR_WORLD,
    };
  }
}
