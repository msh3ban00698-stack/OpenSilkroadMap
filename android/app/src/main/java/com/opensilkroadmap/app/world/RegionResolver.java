package com.opensilkroadmap.app.world;

import com.opensilkroadmap.app.data.TsvTable;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Proven region code resolver combining the committed client region table
 * ({@code regioncode.tsv}, from Media.pk2 textdata) and the committed server
 * region→zone catalog ({@code region_zone.tsv}, from SR_GameRefData/RefRegion.txt).
 * Mirrors the verified Python {@code scripts/region_resolver.py} exactly.
 *
 * <p>One packed region code resolves to everything proven about that world
 * region:
 * <ul>
 *   <li>client side: RN_* name code + localized name ({@code regioncode.tsv}
 *       col1 = id, col2 = RN_* code, col3 = localized name; 3,287 distinct
 *       ids; duplicate rows 22478 / 25289–25294 collapse first-row-wins);</li>
 *   <li>server side: sector (x, y), server region name, flag, zone id
 *       ({@code region_zone.tsv}, 2,444 ids, packing
 *       {@code id == (y << 8) | x} verified);</li>
 * </ul>
 *
 * <p>Fail-closed: {@link #resolve(int)} returns {@code null} when the id is in
 * neither committed table (instance/dungeon codes and world codes absent from
 * both). Sector coordinates for instance ids are never derived (sector access
 * returns -1). No Android dependencies; pure JVM.
 */
public final class RegionResolver {

  /** Client regioncode.tsv name pair: RN_* code + localized name. */
  public static final class NamePair {
    public final String nameCode;
    public final String localizedName;

    public NamePair(String nameCode, String localizedName) {
      this.nameCode = nameCode;
      this.localizedName = localizedName;
    }
  }

  /** Everything proven about one packed region code (nulls when unknown). */
  public static final class Entry {
    public final int regionId;
    public final String nameCode;
    public final String localizedName;
    public final String serverName;
    public final String zoneId;
    public final String flag;
    public final boolean isInstance;

    Entry(int regionId, String nameCode, String localizedName,
          String serverName, String zoneId, String flag) {
      this.regionId = regionId;
      this.nameCode = nameCode;
      this.localizedName = localizedName;
      this.serverName = serverName;
      this.zoneId = zoneId;
      this.flag = flag;
      this.isInstance = regionId < 0;
    }

    /** Sector x via the proven formula, or -1 for instance ids. */
    public int sectorX() {
      return isInstance ? -1 : (regionId & 0xFF);
    }

    /** Sector y via the proven formula, or -1 for instance ids. */
    public int sectorY() {
      return isInstance ? -1 : (regionId >> 8);
    }
  }

  private final Map<Integer, NamePair> client;
  private final RegionZoneCatalog server;

  public RegionResolver(Map<Integer, NamePair> client, RegionZoneCatalog server) {
    this.client = Collections.unmodifiableMap(
        new LinkedHashMap<Integer, NamePair>(client));
    this.server = server;
  }

  /**
   * Resolve a packed region code, or {@code null} when it is in neither the
   * committed client nor server table (fail-closed; never guessed).
   */
  public Entry resolve(int regionId) {
    NamePair c = client.get(regionId);
    RegionZoneCatalog.Entry s = server.resolve(regionId);
    if (c == null && s == null) {
      return null;
    }
    return new Entry(
        regionId,
        c == null ? null : c.nameCode,
        c == null ? null : c.localizedName,
        s == null ? null : s.serverName,
        s == null ? null : s.zoneId,
        s == null ? null : s.flag);
  }

  /** All client region ids whose RN_* code equals the given code (file order). */
  public List<Entry> byNameCode(String code) {
    List<Entry> out = new ArrayList<Entry>();
    for (Map.Entry<Integer, NamePair> e : client.entrySet()) {
      if (code.equals(e.getValue().nameCode)) {
        Entry entry = resolve(e.getKey());
        if (entry != null) {
          out.add(entry);
        }
      }
    }
    return Collections.unmodifiableList(out);
  }

  /** Union of client and server region ids. */
  public Set<Integer> regionIds() {
    java.util.HashSet<Integer> all = new java.util.HashSet<Integer>();
    all.addAll(client.keySet());
    all.addAll(server.regionIds());
    return Collections.unmodifiableSet(all);
  }

  public int clientCount() {
    return client.size();
  }

  public int serverCount() {
    return server.rowCount();
  }

  /** Builds from a parsed client regioncode table + committed server catalog. */
  public static RegionResolver load(TsvTable regionCode, RegionZoneCatalog server) {
    Map<Integer, NamePair> client = new LinkedHashMap<Integer, NamePair>();
    for (String[] row : regionCode.rows()) {
      String id = TsvTable.strAt(row, 1).trim();
      if (id.isEmpty() || !id.matches("-?\\d+")) {
        continue;
      }
      int rid = Integer.parseInt(id);
      if (!client.containsKey(rid)) {
        client.put(rid, new NamePair(TsvTable.strAt(row, 2), TsvTable.strAt(row, 3)));
      }
    }
    return new RegionResolver(client, server);
  }

  /** Loads both committed tables from a conventional Gradle working directory. */
  public static RegionResolver loadDefault() throws IOException {
    return load(TsvTable.loadDefault("regioncode.tsv"), RegionZoneCatalog.loadDefault());
  }
}
