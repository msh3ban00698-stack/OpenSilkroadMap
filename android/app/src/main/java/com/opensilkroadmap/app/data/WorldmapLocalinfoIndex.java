package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Fail-closed unique-once {@code SN_ZONE_*} labels over committed
 * {@code worldmap_localinfo.tsv}:
 *
 * <pre>
 * col1 zone_id      int (localinfo's own id, not teleportdata region_id)
 * col3 zone_code    SN_ZONE_* join key
 * col4 name         Korean (or Latin) name
 * col5 description  Korean (or Latin) description
 * </pre>
 *
 * <p>Only {@code SN_ZONE_*} codes that appear exactly once are kept (353 of
 * 450 SN_ZONE rows). Duplicate codes (18 codes / 97 rows, including
 * {@code SN_ZONE_21835_5} and disagreeing {@code SN_ZONE_25800_8} names) and
 * non-SN_ZONE col3 values (ddj paths, {@code STORE_*}, {@code SN_NPC_*}) are
 * omitted. Unknown codes return {@code null}. Names are never invented.
 * {@code teleportlink.tsv} is not consumed. No Android dependencies; pure JVM.
 */
public final class WorldmapLocalinfoIndex {

  /** One unique-once SN_ZONE label (code + localinfo id + name + description). */
  public static final class Label {
    public final int zoneId;
    public final String zoneCode;
    public final String name;
    public final String description;

    public Label(int zoneId, String zoneCode, String name, String description) {
      this.zoneId = zoneId;
      this.zoneCode = zoneCode;
      this.name = name;
      this.description = description;
    }
  }

  private final Map<String, Label> byCode;

  public WorldmapLocalinfoIndex(TsvTable table) {
    Map<String, Integer> counts = new HashMap<String, Integer>();
    Map<String, String[]> first = new LinkedHashMap<String, String[]>();
    for (String[] row : table.rows()) {
      String code = TsvTable.strAt(row, 3);
      if (!code.startsWith("SN_ZONE_")) {
        continue;
      }
      Integer n = counts.get(code);
      counts.put(code, n == null ? 1 : n.intValue() + 1);
      if (!first.containsKey(code)) {
        first.put(code, row);
      }
    }
    Map<String, Label> map = new LinkedHashMap<String, Label>();
    for (Map.Entry<String, String[]> e : first.entrySet()) {
      String code = e.getKey();
      if (counts.get(code).intValue() != 1) {
        continue;
      }
      String[] row = e.getValue();
      map.put(code, new Label(TsvTable.intAt(row, 1), code,
          TsvTable.strAt(row, 4), TsvTable.strAt(row, 5)));
    }
    this.byCode = Collections.unmodifiableMap(map);
  }

  public static WorldmapLocalinfoIndex loadDefault() throws IOException {
    return new WorldmapLocalinfoIndex(TsvTable.loadDefault("worldmap_localinfo.tsv"));
  }

  public int size() {
    return byCode.size();
  }

  /** Unique-once SN_ZONE label, or {@code null} (fail-closed). */
  public Label resolve(String zoneCode) {
    if (zoneCode == null || zoneCode.isEmpty()) {
      return null;
    }
    return byCode.get(zoneCode);
  }
}
