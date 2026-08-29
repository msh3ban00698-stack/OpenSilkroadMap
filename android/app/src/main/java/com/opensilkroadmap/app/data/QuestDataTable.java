package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code questdata.txt} (normalized asset {@code textdata/questdata.tsv}).
 * Only col2 (quest code, {@code Q*} strings) is verified; the other columns are
 * exposed as raw cells without invented semantics.
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class QuestDataTable {
  private final TsvTable table;

  public QuestDataTable(TsvTable table) {
    this.table = table;
  }

  public static QuestDataTable load() throws IOException {
    return new QuestDataTable(TsvTable.loadDefault("questdata.tsv"));
  }

  public int questCount() {
    return table.rowCount();
  }

  public String questCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 2);
  }

  public int id(int row) {
    return TsvTable.intAt(table.rows().get(row), 0);
  }

  public String rawCell(int row, int col) {
    return TsvTable.strAt(table.rows().get(row), col);
  }

  public TsvTable raw() {
    return table;
  }
}
