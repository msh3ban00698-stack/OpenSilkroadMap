package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Parsed {@code teleportbuilding.txt} (normalized asset
 * {@code textdata/teleportbuilding.tsv}). Verified columns:
 *
 * <pre>
 * col1 gate_id     joins teleportdata.tsv col3 (101 / 135 distinct teleport
 *                  gate ids)
 * col2 store_code  STORE_* gate store codes (e.g. STORE_CH_GATE for Jangan)
 * col5 npc_code    SN_NPC_* gate NPC codes
 * </pre>
 *
 * <p>Comment rows (source {@code //...} private-server edit lines) are skipped
 * by {@link TsvTable}. On the committed table: 106 buildings, 101 gate ids
 * joined to {@code teleportdata.tsv}, 106 distinct store codes, 68 distinct
 * NPC codes. Lookups fail closed (null) for unknown gate ids. No Android
 * dependencies; pure JVM.
 */
public final class TeleportBuildingTable {

  private final Map<Integer, String[]> byGateId;

  public TeleportBuildingTable(TsvTable table) {
    Map<Integer, String[]> map = new LinkedHashMap<Integer, String[]>();
    for (String[] row : table.rows()) {
      map.put(TsvTable.intAt(row, 1), row);
    }
    this.byGateId = Collections.unmodifiableMap(map);
  }

  public static TeleportBuildingTable loadDefault() throws IOException {
    return new TeleportBuildingTable(TsvTable.loadDefault("teleportbuilding.tsv"));
  }

  public int buildingCount() {
    return byGateId.size();
  }

  /** STORE_* gate store code, or null when the gate id is unlisted. */
  public String storeCode(int gateId) {
    String[] row = byGateId.get(gateId);
    return row == null ? null : TsvTable.strAt(row, 2);
  }

  /** SN_NPC_* gate NPC code, or null when the gate id is unlisted. */
  public String npcCode(int gateId) {
    String[] row = byGateId.get(gateId);
    return row == null ? null : TsvTable.strAt(row, 5);
  }

  public Set<Integer> gateIds() {
    return byGateId.keySet();
  }
}
