package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code RefOptionalTeleport.txt} (normalized asset
 * {@code textdata/refoptionalteleport.tsv}): the client teleport NPC's optional
 * destination list. Columns proven by cross-reference against the committed
 * verified tables (regioncode.tsv, region_zone.tsv, teleportdata.tsv):
 *
 * <pre>
 * col1 index       1..44 unique destination index
 * col2 name_label  destination text label (e.g. "Chang'an")
 * col3 zone_code   SN_ZONE_* codes; 3 rows use RN_OTHER_SKYTEMPLE* client codes
 * col4 region_id   packed region code of the destination sector (e.g. 25000 =
 *                  RN_CH_JANGAN 168x97, server CHINA zone 1001); negative =
 *                  instance space
 * col5 local_x     sector-local x, within [0, 1920) for all 40 world rows
 * col6 height_y    height axis (like npcpos col3; not used for 2D placement)
 * col7 local_z     sector-local z, within [0, 1920) for all 40 world rows
 * </pre>
 *
 * <p>World-space verification on the committed table: 44 rows total, 40 world /
 * 4 instance; world rows have x/z local values in [0, 1920) for 40/40 and
 * 40/40; 40/40 world region_ids resolve in the client table, 35/40 are
 * server-attributed. Instance rows (Dunhuang Cave 1F, Jinshi 2F/3F/4F) live in
 * a separate UNKNOWN coordinate space. No Android dependencies; pure JVM.
 */
public final class OptionalTeleportTable {
  private final TsvTable table;

  public OptionalTeleportTable(TsvTable table) {
    this.table = table;
  }

  public static OptionalTeleportTable load() throws IOException {
    return new OptionalTeleportTable(TsvTable.loadDefault("refoptionalteleport.tsv"));
  }

  public int destinationCount() {
    return table.rowCount();
  }

  public int index(int row) {
    return TsvTable.intAt(table.rows().get(row), 1);
  }

  public String nameLabel(int row) {
    return TsvTable.strAt(table.rows().get(row), 2);
  }

  public String zoneCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 3);
  }

  public int regionId(int row) {
    return TsvTable.intAt(table.rows().get(row), 4);
  }

  public float localX(int row) {
    return TsvTable.floatAt(table.rows().get(row), 5);
  }

  public float heightY(int row) {
    return TsvTable.floatAt(table.rows().get(row), 6);
  }

  public float localZ(int row) {
    return TsvTable.floatAt(table.rows().get(row), 7);
  }

  public TsvTable raw() {
    return table;
  }
}
