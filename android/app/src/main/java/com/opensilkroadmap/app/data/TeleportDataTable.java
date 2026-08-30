package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code teleportdata.txt} (normalized asset
 * {@code textdata/teleportdata.tsv}). Verified columns:
 *
 * <pre>
 * col2 gate_code   GATE_* codes
 * col3 gate_id     joins teleportbuilding.tsv col1 for 101/135 ids
 * col4 zone_code   SN_ZONE_* codes
 * col5 zone_id     int zone id
 * </pre>
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class TeleportDataTable {
  private final TsvTable table;

  public TeleportDataTable(TsvTable table) {
    this.table = table;
  }

  public static TeleportDataTable load() throws IOException {
    return new TeleportDataTable(TsvTable.loadDefault("teleportdata.tsv"));
  }

  public int gateCount() {
    return table.rowCount();
  }

  public String gateCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 2);
  }

  public int gateId(int row) {
    return TsvTable.intAt(table.rows().get(row), 3);
  }

  public String zoneCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 4);
  }

  public int zoneId(int row) {
    return TsvTable.intAt(table.rows().get(row), 5);
  }

  public TsvTable raw() {
    return table;
  }
}
