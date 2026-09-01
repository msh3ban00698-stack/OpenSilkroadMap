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
 * col5 zone_id     packed region code of the destination sector (e.g. 25000
 *                  = RN_CH_JANGAN 168x97; negative = instance space)
 * col6 local_x     sector-local x, within [0, 1920) for world gates
 * col7 height_y    height axis (like npcpos col3; not used for 2D placement)
 * col8 local_z     sector-local z, within [0, 1920) for world gates
 * </pre>
 *
 * <p>World-space verification: on the committed table, world gates (zone_id
 * &ge; 0) have x/z local values in [0, 1920) for 143/144 and 144/144 rows
 * respectively (one x = -20 edge gate). Instance gates (zone_id &lt; 0) live in
 * a separate UNKNOWN coordinate space and are never projected. No Android
 * dependencies; pure JVM.
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

  public float localX(int row) {
    return TsvTable.floatAt(table.rows().get(row), 6);
  }

  public float heightY(int row) {
    return TsvTable.floatAt(table.rows().get(row), 7);
  }

  public float localZ(int row) {
    return TsvTable.floatAt(table.rows().get(row), 8);
  }

  public TsvTable raw() {
    return table;
  }
}
