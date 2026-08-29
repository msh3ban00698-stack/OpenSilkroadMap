package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code npcpos.txt} spawn table (normalized asset
 * {@code textdata/npcpos.tsv}). Verified columns:
 *
 * <pre>
 * col0 spawn_id          int, ascending
 * col1 character_refid   joins characterdata_*.txt col1 for 659/1855 ids
 * col2 coord0            float coordinate
 * col3 coord1            float coordinate, ~0 across records (height axis)
 * col4 coord2            float coordinate
 * </pre>
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class NpcPosTable {
  private final TsvTable table;

  public NpcPosTable(TsvTable table) {
    this.table = table;
  }

  public static NpcPosTable load() throws IOException {
    return new NpcPosTable(TsvTable.loadDefault("npcpos.tsv"));
  }

  public int spawnCount() {
    return table.rowCount();
  }

  public int spawnId(int row) {
    return TsvTable.intAt(table.rows().get(row), 0);
  }

  public int characterRefId(int row) {
    return TsvTable.intAt(table.rows().get(row), 1);
  }

  public float coord0(int row) {
    return TsvTable.floatAt(table.rows().get(row), 2);
  }

  public float coord1(int row) {
    return TsvTable.floatAt(table.rows().get(row), 3);
  }

  public float coord2(int row) {
    return TsvTable.floatAt(table.rows().get(row), 4);
  }

  public TsvTable raw() {
    return table;
  }
}
