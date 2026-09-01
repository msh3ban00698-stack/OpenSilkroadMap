package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code GameWorldData.txt} (normalized asset
 * {@code textdata/gameworlddata.tsv}). Verified columns:
 *
 * <pre>
 * col0 world_id     opaque unique numeric world id (1..115, sequential)
 * col1 code         INS_* instance-world codes (e.g. INS_FORT_JA)
 * col5 group        GROUP_* group code, or the "xxx" placeholder when none
 * </pre>
 *
 * <p>Columns 2-4 have no verified semantics and are never consumed. The
 * {@code code}+{@code group} pairing is cross-checked against the shard
 * {@code _RefInstance_World} seed rows in {@code SRO_VT_SHARD.Bak} (e.g.
 * {@code INS_FORT_JAGROUP_FORTRESS_JANGAN} at file offset 22,414,002, with the
 * {@code INS_DEFAULTxxx} placeholder at 22,413,954); see
 * {@code scripts/test_worlddata_bak_concordance.py}. {@code world_id} is an
 * opaque key only: the backup's numeric ids do not align with this column, so
 * its exact meaning stays PARTIAL. No Android dependencies; pure JVM.
 */
public final class WorldGameTable {
  private final TsvTable table;

  public WorldGameTable(TsvTable table) {
    this.table = table;
  }

  public static WorldGameTable load() throws IOException {
    return new WorldGameTable(TsvTable.loadDefault("gameworlddata.tsv"));
  }

  public int worldCount() {
    return table.rowCount();
  }

  public int worldId(int row) {
    return TsvTable.intAt(table.rows().get(row), 0);
  }

  public String code(int row) {
    return TsvTable.strAt(table.rows().get(row), 1);
  }

  public String group(int row) {
    return TsvTable.strAt(table.rows().get(row), 5);
  }

  public TsvTable raw() {
    return table;
  }
}
