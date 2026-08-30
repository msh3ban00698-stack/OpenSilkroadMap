package com.opensilkroadmap.app.world;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * A world-space set of committed real terrain sectors, each a verified
 * {@code TerrainHeightGrid} positioned by the proven sector-world formula
 * ({@code world = (sector - refSector) * 1920 + local}, Phase 10).
 *
 * <p>The set exposes the union of the sector extents as world bounds and
 * samples the real height at any world point by locating the containing sector
 * and delegating to that sector's bilinear sampler. Points outside every
 * loaded sector return {@link Float#NaN} (fail-closed; no extrapolation, no
 * substituted sector).
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class WorldTerrainSet {

  /** One sector's real height grid placed in world space. */
  public static final class Sector {
    public final int sx;
    public final int sy;
    public final float originX;
    public final float originZ;
    public final TerrainHeightGrid grid;

    public Sector(int sx, int sy, float originX, float originZ, TerrainHeightGrid grid) {
      this.sx = sx;
      this.sy = sy;
      this.originX = originX;
      this.originZ = originZ;
      this.grid = grid;
    }

    public float extent() {
      return grid.size() * grid.step();
    }
  }

  private final List<Sector> sectors;
  private final float minX;
  private final float minZ;
  private final float maxX;
  private final float maxZ;

  public WorldTerrainSet(List<Sector> sectors) {
    List<Sector> copy = new ArrayList<Sector>(sectors);
    Collections.sort(copy, (a, b) ->
        a.sy != b.sy ? Integer.compare(a.sy, b.sy)
            : Integer.compare(a.sx, b.sx));
    this.sectors = Collections.unmodifiableList(copy);
    float loX = Float.POSITIVE_INFINITY;
    float loZ = Float.POSITIVE_INFINITY;
    float hiX = Float.NEGATIVE_INFINITY;
    float hiZ = Float.NEGATIVE_INFINITY;
    for (Sector s : copy) {
      loX = Math.min(loX, s.originX);
      loZ = Math.min(loZ, s.originZ);
      hiX = Math.max(hiX, s.originX + s.extent());
      hiZ = Math.max(hiZ, s.originZ + s.extent());
    }
    this.minX = loX;
    this.minZ = loZ;
    this.maxX = hiX;
    this.maxZ = hiZ;
  }

  /** Builds a sector placed by the verified formula relative to a ref sector. */
  public static Sector sector(int sx, int sy, int refSx, int refSy, TerrainHeightGrid grid) {
    return new Sector(
        sx, sy,
        (sx - refSx) * TerrainHeightGrid.SECTOR_WORLD,
        (sy - refSy) * TerrainHeightGrid.SECTOR_WORLD,
        grid);
  }

  public List<Sector> sectors() {
    return sectors;
  }

  public int sectorCount() {
    return sectors.size();
  }

  public float minX() {
    return minX;
  }

  public float minZ() {
    return minZ;
  }

  public float maxX() {
    return maxX;
  }

  public float maxZ() {
    return maxZ;
  }

  public float width() {
    return maxX - minX;
  }

  public float height() {
    return maxZ - minZ;
  }

  /** Locates the sector whose extent contains the world point, or null. */
  public Sector sectorAt(float worldX, float worldZ) {
    for (Sector s : sectors) {
      if (worldX >= s.originX && worldX <= s.originX + s.extent()
          && worldZ >= s.originZ && worldZ <= s.originZ + s.extent()) {
        return s;
      }
    }
    return null;
  }

  /** Real height at a world point; NaN when outside every loaded sector. */
  public float sampleWorld(float worldX, float worldZ) {
    Sector s = sectorAt(worldX, worldZ);
    if (s == null) {
      return Float.NaN;
    }
    return s.grid.sampleWorld(worldX, worldZ, s.originX, s.originZ);
  }
}
