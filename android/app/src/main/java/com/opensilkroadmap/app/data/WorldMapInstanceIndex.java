package com.opensilkroadmap.app.data;

import com.opensilkroadmap.app.game.RegionCatalog;
import com.opensilkroadmap.app.game.RegionInfo;
import com.opensilkroadmap.app.world.WorldCoordinates;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Instance navigation index over the committed {@code worldmap_instanceinfo.tsv}
 * resolved onto the committed {@code regions.tsv} region catalog.
 *
 * <p>Every instance map's anchor cell (verified {@code region_cell_x/y}, joined
 * 23/23 to {@code regions.tsv} cells) is a sector in the same 1920-unit grid as
 * the region catalog and the teleport gate placement. Each {@link Instance}
 * exposes the proven Korean name, anchor sector, and the containing region
 * section (e.g. ThiefTown, DonwhangCave, Jangan_Field, Roc_Mountain). Local
 * position columns (cols 4-10) have no verified semantics and stay UNKNOWN.
 *
 * <p>Fail-closed: unknown codes return {@code null} and never guess a sector or
 * name. No Android dependencies; pure JVM.
 */
public final class WorldMapInstanceIndex {

  /** One instance map with its proven anchor and region resolution. */
  public static final class Instance {
    public final String code;
    public final String name;
    public final int cellX;
    public final int cellY;
    public final RegionInfo region;

    Instance(String code, String name, int cellX, int cellY, RegionInfo region) {
      this.code = code;
      this.name = name;
      this.cellX = cellX;
      this.cellY = cellY;
      this.region = region;
    }

    /** Name of the containing region section, or null (fail-closed). */
    public String regionName() {
      return region == null ? null : region.name;
    }

    /** World anchor x (at local origin) relative to a reference sector. */
    public float worldAnchorX(int refSx) {
      return (cellX - refSx) * WorldCoordinates.SECTOR_WORLD;
    }

    /** World anchor y (at local origin) relative to a reference sector. */
    public float worldAnchorY(int refSy) {
      return (cellY - refSy) * WorldCoordinates.SECTOR_WORLD;
    }
  }

  private final Map<String, Instance> byCode;
  private final int regionResolvedCount;

  public WorldMapInstanceIndex(WorldMapInstanceTable table, RegionCatalog regions) {
    Map<String, Instance> map = new LinkedHashMap<String, Instance>();
    int resolved = 0;
    for (int i = 0; i < table.instanceCount(); i++) {
      int x = table.regionCellX(i);
      int y = table.regionCellY(i);
      RegionInfo region = regions.regionForCell(x, y);
      if (region != null) {
        resolved++;
      }
      map.put(table.code(i),
          new Instance(table.code(i), table.name(i), x, y, region));
    }
    this.byCode = Collections.unmodifiableMap(map);
    this.regionResolvedCount = resolved;
  }

  public static WorldMapInstanceIndex loadDefault() throws java.io.IOException {
    return new WorldMapInstanceIndex(WorldMapInstanceTable.load(),
        RegionCatalog.loadDefault());
  }

  public int instanceCount() {
    return byCode.size();
  }

  /** Instances whose anchor cell joins a known region section. */
  public int regionResolvedCount() {
    return regionResolvedCount;
  }

  /** Instance by {@code Worldmap_*} code, or null (fail-closed). */
  public Instance resolve(String code) {
    return byCode.get(code);
  }

  public List<Instance> instances() {
    return Collections.unmodifiableList(new ArrayList<Instance>(byCode.values()));
  }
}
