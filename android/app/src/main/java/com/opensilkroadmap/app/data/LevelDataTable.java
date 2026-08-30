package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code leveldata.txt} level table (normalized asset
 * {@code textdata/leveldata.tsv}). Only col0 (level, 1..150 ascending) is
 * verified; the remaining integer columns are exposed as raw ints without
 * invented semantics.
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class LevelDataTable {
  private final TsvTable table;

  public LevelDataTable(TsvTable table) {
    this.table = table;
  }

  public static LevelDataTable load() throws IOException {
    return new LevelDataTable(TsvTable.loadDefault("leveldata.tsv"));
  }

  public int levelCount() {
    return table.rowCount();
  }

  public int level(int row) {
    return TsvTable.intAt(table.rows().get(row), 0);
  }

  public int rawColumn(int row, int col) {
    return TsvTable.intAt(table.rows().get(row), col);
  }

  public int columnCount() {
    return table.rows().get(0).length;
  }

  public TsvTable raw() {
    return table;
  }
}
