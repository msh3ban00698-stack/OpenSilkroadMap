package com.opensilkroadmap.app.data;

import com.opensilkroadmap.app.world.RegionResolver;
import com.opensilkroadmap.app.world.WorldCoordinates;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Concrete runtime teleport destination map composed from the committed
 * verified teleport indices: every {@code teleportdata.tsv} gate
 * ({@link TeleportGateIndex}) and every {@code refoptionalteleport.tsv} optional
 * destination ({@link OptionalTeleportIndex}) becomes one entry with its proven
 * placement. The map is strictly fail-closed and NEVER invents a
 * gate→destination link: the {@code teleportlink.tsv} row semantics are
 * unproven and are NOT consumed here.
 *
 * <p>Entry provenance (all committed assets under
 * {@code game/textdata/}):
 * <ul>
 *   <li>{@code GATE} entries: {@code teleportdata.tsv} row (col2 {@code GATE_*}
 *       code, col3 gate_id, col4 {@code SN_ZONE_*} code, col5 zone_id, col6/7/8
 *       local x/y/z); col3 joins {@code teleportbuilding.tsv} col1 for the
 *       {@code STORE_*} (col2) / {@code SN_NPC_*} (col5) gate codes.</li>
 *   <li>{@code OPTIONAL_DESTINATION} entries: {@code refoptionalteleport.tsv}
 *       row (col1 destination index, col2 label, col3 {@code SN_ZONE_*} code,
 *       col4 region_id, col5/6/7 local x/y/z).</li>
 *   <li>placement: every world region_id resolves via
 *       {@link RegionResolver} to sector + server zone + client name
 *       ({@code regioncode.tsv} + {@code region_zone.tsv}); instance rows and
 *       region ids in neither table fail closed with -1 sector / null zone /
 *       NaN world coordinates.</li>
 * </ul>
 *
 * <p>Proven coverage on the committed tables: 290 entries total (246 gates /
 * 44 optional destinations), 179 resolve to a region (139 gates + 40
 * destinations), 111 fail closed (102 instance gates + 5 unlisted world gates
 * + 4 instance destinations). Gate zones span 12 server zones; the optional
 * destinations add none. The Jangan sector (168,97) holds 4 entries and the
 * runtime-launch Jangan_Field window (156–182 × 89–102) holds 20 (16 gates +
 * 4 destinations).
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class TeleportDestinationMap {

  /** Entry kind: a teleport gate point or an optional teleport destination. */
  public enum Kind { GATE, OPTIONAL_DESTINATION }

  /** One verified teleport point with its proven placement (or fail-closed nulls). */
  public static final class Entry {
    public final Kind kind;
    public final int sourceRow;
    public final String label;
    public final String gateCode;
    public final int gateId;
    public final int sourceIndex;
    public final String zoneCode;
    public final int regionId;
    public final boolean isWorld;
    public final float localX;
    public final float heightY;
    public final float localZ;
    public final RegionResolver.Entry region;
    public final String storeCode;
    public final String npcCode;

    Entry(Kind kind, int sourceRow, String label, String gateCode, int gateId,
          int sourceIndex, String zoneCode, int regionId, float localX,
          float heightY, float localZ, RegionResolver.Entry region,
          String storeCode, String npcCode) {
      this.kind = kind;
      this.sourceRow = sourceRow;
      this.label = label;
      this.gateCode = gateCode;
      this.gateId = gateId;
      this.sourceIndex = sourceIndex;
      this.zoneCode = zoneCode;
      this.regionId = regionId;
      this.isWorld = regionId >= 0;
      this.localX = localX;
      this.heightY = heightY;
      this.localZ = localZ;
      this.region = region;
      this.storeCode = storeCode;
      this.npcCode = npcCode;
    }

    /** Sector x of the placement, or -1 when the region_id is unresolvable. */
    public int sectorX() {
      return region == null ? -1 : region.sectorX();
    }

    /** Sector y of the placement, or -1 when the region_id is unresolvable. */
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

  private final List<Entry> entries;
  private final Map<String, List<Entry>> byZone;
  private final Set<String> zones;
  private final TeleportGateIndex gates;
  private final OptionalTeleportIndex destinations;
  private final int gateCount;
  private final int resolvedCount;

  public TeleportDestinationMap(TeleportGateIndex gates, OptionalTeleportIndex destinations) {
    this.gates = gates;
    this.destinations = destinations;
    List<Entry> all = new ArrayList<Entry>();
    Map<String, List<Entry>> byZone = new LinkedHashMap<String, List<Entry>>();
    Set<String> zoneSet = new LinkedHashSet<String>();
    int resolved = 0;
    for (int i = 0; i < gates.gateCount(); i++) {
      TeleportGateIndex.Gate g = gates.gate(i);
      String label = g.localizedName();
      if (label == null) {
        label = g.nameCode();
      }
      if (label == null) {
        label = g.gateCode;
      }
      Entry e = new Entry(Kind.GATE, g.row, label, g.gateCode, g.gateId, -1,
          g.zoneCode, g.zoneId, g.localX, g.heightY, g.localZ, g.region,
          g.storeCode, g.npcCode);
      all.add(e);
      if (g.region != null && g.region.zoneId != null) {
        zoneSet.add(g.region.zoneId);
        addZone(byZone, g.region.zoneId, e);
      }
      if (g.region != null) {
        resolved++;
      }
    }
    this.gateCount = all.size();
    for (int i = 0; i < destinations.destinationCount(); i++) {
      OptionalTeleportIndex.Destination d = destinations.destination(i);
      Entry e = new Entry(Kind.OPTIONAL_DESTINATION, d.row, d.nameLabel, null,
          -1, d.index, d.zoneCode, d.regionId, d.localX, d.heightY, d.localZ,
          d.region, null, null);
      all.add(e);
      if (d.region != null && d.region.zoneId != null) {
        zoneSet.add(d.region.zoneId);
        addZone(byZone, d.region.zoneId, e);
      }
      if (d.region != null) {
        resolved++;
      }
    }
    Map<String, List<Entry>> frozen = new LinkedHashMap<String, List<Entry>>();
    for (Map.Entry<String, List<Entry>> e : byZone.entrySet()) {
      frozen.put(e.getKey(), Collections.unmodifiableList(e.getValue()));
    }
    this.entries = Collections.unmodifiableList(all);
    this.byZone = Collections.unmodifiableMap(frozen);
    this.zones = Collections.unmodifiableSet(zoneSet);
    this.resolvedCount = resolved;
  }

  private static void addZone(Map<String, List<Entry>> byZone, String zoneId, Entry e) {
    List<Entry> list = byZone.get(zoneId);
    if (list == null) {
      list = new ArrayList<Entry>();
      byZone.put(zoneId, list);
    }
    list.add(e);
  }

  public int entryCount() {
    return entries.size();
  }

  /** Teleport gate entries ({@code teleportdata.tsv} rows). */
  public int gateCount() {
    return gateCount;
  }

  /** Optional teleport destination entries ({@code refoptionalteleport.tsv} rows). */
  public int destinationCount() {
    return entries.size() - gateCount;
  }

  /** Entries whose region_id resolves (client name + sector proven). */
  public int resolvedEntryCount() {
    return resolvedCount;
  }

  /** Entries with no placement (instance rows / unlisted region ids). */
  public int unresolvedEntryCount() {
    return entries.size() - resolvedCount;
  }

  public Entry entry(int i) {
    return entries.get(i);
  }

  /** Entries whose placement sector falls in the window (inclusive). */
  public List<Entry> inWindow(int sx0, int sx1, int sy0, int sy1) {
    List<Entry> out = new ArrayList<Entry>();
    for (Entry e : entries) {
      if (e.region != null && e.sectorX() >= sx0 && e.sectorX() <= sx1
          && e.sectorY() >= sy0 && e.sectorY() <= sy1) {
        out.add(e);
      }
    }
    return out;
  }

  /** Entries attributed to a proven server zone (empty when none). */
  public List<Entry> inZone(String zoneId) {
    List<Entry> list = byZone.get(zoneId);
    return list == null ? Collections.<Entry>emptyList() : list;
  }

  /** Distinct server zone ids among placed entries (empty when none). */
  public Set<String> zones() {
    return zones;
  }

  /** The composed gate index (provenance). */
  public TeleportGateIndex gates() {
    return gates;
  }

  /** The composed optional teleport index (provenance). */
  public OptionalTeleportIndex destinations() {
    return destinations;
  }
}
