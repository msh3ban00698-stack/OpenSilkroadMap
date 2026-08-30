package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code levelgold.txt} (normalized asset
 * {@code textdata/levelgold.tsv}). Only col0 (level, 1..140 ascending) is
 * verified; cols 1-2 are exposed as raw ints.
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class LevelGoldTable {
  private final TsvTable table;

  public LevelGoldTable(TsvTable table) {
    this.table = table;
  }

  public static LevelGoldTable load() throws IOException {
    return new LevelGoldTable(TsvTable.loadDefault("levelgold.tsv"));
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

  public TsvTable raw() {
    return table;
  }
}
