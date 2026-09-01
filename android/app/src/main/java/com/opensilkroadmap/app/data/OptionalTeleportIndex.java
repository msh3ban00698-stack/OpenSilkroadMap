package com.opensilkroadmap.app.data;

import com.opensilkroadmap.app.world.RegionResolver;
import com.opensilkroadmap.app.world.WorldCoordinates;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Optional teleport destination index over the committed
 * {@code refoptionalteleport.tsv}.
 *
 * <p>Composes {@link OptionalTeleportTable} with {@link RegionResolver} (client
 * RN_* name + server region→zone catalog, both committed and
 * provenance-pinned). Each world destination's {@code region_id} resolves to
 * sector + server zone + client name; its local x/z (within [0, 1920) for all
 * world rows) project to world coordinates with the proven formula. Instance
 * destinations (region_id &lt; 0) and any unresolvable region_id stay UNKNOWN
 * and fail closed — never invented.
 *
 * <p>Proven coverage on the committed tables: 44 destinations total, 40 world /
 * 4 instance; 40/40 world region_ids resolve in the client table, 35/40 are
 * server-attributed (across the 13 server zones), 5 are client-only (Baghdad,
 * Phantom Desert, Arabian Coast, Sky Temple A/B).
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class OptionalTeleportIndex {

  /** One optional teleport destination with its proven placement (or fail-closed nulls). */
  public static final class Destination {
    public final int row;
    public final int index;
    public final String nameLabel;
    public final String zoneCode;
    public final int regionId;
    public final float localX;
    public final float heightY;
    public final float localZ;
    public final boolean isWorld;
    public final RegionResolver.Entry region;

    Destination(int row, int index, String nameLabel, String zoneCode, int regionId,
                float localX, float heightY, float localZ, RegionResolver.Entry region) {
      this.row = row;
      this.index = index;
      this.nameLabel = nameLabel;
      this.zoneCode = zoneCode;
      this.regionId = regionId;
      this.localX = localX;
      this.heightY = heightY;
      this.localZ = localZ;
      this.region = region;
      this.isWorld = regionId >= 0;
    }

    /** Sector x of the destination, or -1 when the region_id is unresolvable. */
    public int sectorX() {
      return region == null ? -1 : region.sectorX();
    }

    /** Sector y of the destination, or -1 when the region_id is unresolvable. */
    public int sectorY() {
      return region == null ? -1 : region.sectorY();
    }

    /** Server zone id (e.g. "1001"), or null (fail-closed). */
    public String serverZone() {
      return region == null ? null : region.zoneId;
    }

    /** Server region name (e.g. "CHINA"), or null (fail-closed). */
    public String serverName() {
      return region == null ? null : region.serverName;
    }

    /** Client RN_* name code, or null (fail-closed). */
    public String nameCode() {
      return region == null ? null : region.nameCode;
    }

    /** Client localized name, or null (fail-closed). */
    public String localizedName() {
      return region == null ? null : region.localizedName;
    }

    /** World x relative to a reference sector (proven formula); NaN if null. */
    public float worldX(int refSx) {
      return region == null ? Float.NaN
          : localX + (region.sectorX() - refSx) * WorldCoordinates.SECTOR_WORLD;
    }

    /** World z relative to a reference sector (proven formula); NaN if null. */
    public float worldZ(int refSy) {
      return region == null ? Float.NaN
          : localZ + (region.sectorY() - refSy) * WorldCoordinates.SECTOR_WORLD;
    }
  }

  private final List<Destination> destinations;
  private final int instanceCount;
  private final int clientOnlyCount;

  public OptionalTeleportIndex(OptionalTeleportTable table, RegionResolver resolver) {
    List<Destination> all = new ArrayList<Destination>();
    int instances = 0;
    int clientOnly = 0;
    for (int i = 0; i < table.destinationCount(); i++) {
      int regionId = table.regionId(i);
      RegionResolver.Entry entry = resolver.resolve(regionId);
      if (regionId < 0) {
        instances++;
      } else if (entry == null) {
        // Not reached on the committed table (40/40 world rows resolve in the
        // client table); kept for provenance-fail-closed integrity.
      } else if (entry.zoneId == null) {
        clientOnly++;
      }
      all.add(new Destination(i, table.index(i), table.nameLabel(i),
          table.zoneCode(i), regionId, table.localX(i), table.heightY(i),
          table.localZ(i), entry));
    }
    this.destinations = Collections.unmodifiableList(all);
    this.instanceCount = instances;
    this.clientOnlyCount = clientOnly;
  }

  public int destinationCount() {
    return destinations.size();
  }

  public int worldCount() {
    return destinationCount() - instanceCount;
  }

  public int instanceCount() {
    return instanceCount;
  }

  /** World destinations resolved in the client table only (name, no server zone). */
  public int clientOnlyWorldCount() {
    return clientOnlyCount;
  }

  /** World destinations attributed to a proven server zone. */
  public int resolvedWorldCount() {
    return worldCount() - clientOnlyCount;
  }

  public Destination destination(int i) {
    return destinations.get(i);
  }

  /** All world destinations in destination-index order (instance rows excluded). */
  public List<Destination> world() {
    List<Destination> out = new ArrayList<Destination>();
    for (Destination d : destinations) {
      if (d.isWorld) {
        out.add(d);
      }
    }
    return out;
  }
}
