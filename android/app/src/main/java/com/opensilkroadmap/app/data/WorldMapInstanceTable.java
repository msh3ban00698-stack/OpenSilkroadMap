package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code worldmap_instanceinfo.txt} (normalized asset
 * {@code textdata/worldmap_instanceinfo.tsv}). Verified columns:
 *
 * <pre>
 * col0 code           Worldmap_* codes
 * col1 name           Korean name
 * col2 region_cell_x  joins regions.tsv cell x (23/23 matched)
 * col3 region_cell_y  joins regions.tsv cell y (23/23 matched)
 * </pre>
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class WorldMapInstanceTable {
  private final TsvTable table;

  public WorldMapInstanceTable(TsvTable table) {
    this.table = table;
  }

  public static WorldMapInstanceTable load() throws IOException {
    return new WorldMapInstanceTable(TsvTable.loadDefault("worldmap_instanceinfo.tsv"));
  }

  public int instanceCount() {
    return table.rowCount();
  }

  public String code(int row) {
    return TsvTable.strAt(table.rows().get(row), 0);
  }

  public String name(int row) {
    return TsvTable.strAt(table.rows().get(row), 1);
  }

  public int regionCellX(int row) {
    return TsvTable.intAt(table.rows().get(row), 2);
  }

  public int regionCellY(int row) {
    return TsvTable.intAt(table.rows().get(row), 3);
  }

  public TsvTable raw() {
    return table;
  }
}
