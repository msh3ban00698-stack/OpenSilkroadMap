package com.opensilkroadmap.app.data;

import com.opensilkroadmap.app.world.RegionResolver;
import com.opensilkroadmap.app.world.WorldCoordinates;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Teleport gate placement index over the committed {@code teleportdata.tsv}.
 *
 * <p>Composes {@link TeleportDataTable} with {@link RegionResolver} (client RN_*
 * name + server region→zone catalog, both committed and provenance-pinned).
 * Every gate's {@code zone_id} is a packed region code for the destination
 * sector; world gates (zone_id ≥ 0) resolve to sector + server zone + client
 * name, and their local x/z (within [0, 1920) for world rows) project to world
 * coordinates with the proven formula. Instance gates (zone_id &lt; 0) and any
 * unresolvable zone_id stay UNKNOWN and fail closed — never invented.
 *
 * <p>Proven coverage on the committed tables: 246 gates total, 144 world /
 * 102 instance; 104 world gates are server-attributed (97 distinct zone_ids →
 * 97 distinct sectors across 12 server zones); 35 world gates resolve in the
 * client table only (name + sector proven, server zone UNKNOWN); 5 world gates
 * (zone_ids 0 and 22219) are in neither table and fail closed entirely.
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class TeleportGateIndex {

  /** One teleport gate with its proven placement (or fail-closed nulls). */
  public static final class Gate {
    public final int row;
    public final String gateCode;
    public final int gateId;
    public final String zoneCode;
    public final int zoneId;
    public final float localX;
    public final float heightY;
    public final float localZ;
    public final boolean isWorld;
    public final RegionResolver.Entry region;

    Gate(int row, String gateCode, int gateId, String zoneCode, int zoneId,
         float localX, float heightY, float localZ, RegionResolver.Entry region) {
      this.row = row;
      this.gateCode = gateCode;
      this.gateId = gateId;
      this.zoneCode = zoneCode;
      this.zoneId = zoneId;
      this.localX = localX;
      this.heightY = heightY;
      this.localZ = localZ;
      this.region = region;
      this.isWorld = zoneId >= 0;
    }

    /** Sector x of the destination, or -1 when the zone_id is unresolvable. */
    public int sectorX() {
      return region == null ? -1 : region.sectorX();
    }

    /** Sector y of the destination, or -1 when the zone_id is unresolvable. */
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

  private final List<Gate> gates;
  private final Map<String, List<Gate>> byZone;
  private final int instanceCount;
  private final int clientOnlyCount;
  private final int unresolvedWorldCount;

  public TeleportGateIndex(TeleportDataTable table, RegionResolver resolver) {
    List<Gate> all = new ArrayList<Gate>();
    Map<String, List<Gate>> byZone = new LinkedHashMap<String, List<Gate>>();
    int instances = 0;
    int clientOnly = 0;
    int unresolved = 0;
    for (int i = 0; i < table.gateCount(); i++) {
      int zoneId = table.zoneId(i);
      RegionResolver.Entry entry = resolver.resolve(zoneId);
      if (zoneId < 0) {
        instances++;
      } else if (entry == null) {
        unresolved++;
      } else if (entry.zoneId != null) {
        List<Gate> list = byZone.get(entry.zoneId);
        if (list == null) {
          list = new ArrayList<Gate>();
          byZone.put(entry.zoneId, list);
        }
        list.add(new Gate(i, table.gateCode(i), table.gateId(i),
            table.zoneCode(i), zoneId, table.localX(i), table.heightY(i),
            table.localZ(i), entry));
      } else {
        clientOnly++;
      }
      all.add(new Gate(i, table.gateCode(i), table.gateId(i),
          table.zoneCode(i), zoneId, table.localX(i), table.heightY(i),
          table.localZ(i), entry));
    }
    Map<String, List<Gate>> frozen = new LinkedHashMap<String, List<Gate>>();
    for (Map.Entry<String, List<Gate>> e : byZone.entrySet()) {
      frozen.put(e.getKey(), Collections.unmodifiableList(e.getValue()));
    }
    this.gates = Collections.unmodifiableList(all);
    this.byZone = Collections.unmodifiableMap(frozen);
    this.instanceCount = instances;
    this.clientOnlyCount = clientOnly;
    this.unresolvedWorldCount = unresolved;
  }

  public int gateCount() {
    return gates.size();
  }

  public int worldCount() {
    return gateCount() - instanceCount;
  }

  public int instanceCount() {
    return instanceCount;
  }

  /** World gates whose zone_id fails to resolve at all (in neither table). */
  public int unresolvedWorldCount() {
    return unresolvedWorldCount;
  }

  /** World gates resolved in the client table only (name, no server zone). */
  public int clientOnlyWorldCount() {
    return clientOnlyCount;
  }

  /** World gates attributed to a proven server zone. */
  public int resolvedWorldCount() {
    return worldCount() - clientOnlyCount - unresolvedWorldCount;
  }

  public Gate gate(int i) {
    return gates.get(i);
  }

  /** Distinct server zone ids among world gates (empty when none). */
  public Set<String> zones() {
    return byZone.keySet();
  }

  public List<Gate> gatesInZone(String zoneId) {
    List<Gate> list = byZone.get(zoneId);
    return list == null ? Collections.<Gate>emptyList() : list;
  }
}
