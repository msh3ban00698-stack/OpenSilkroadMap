package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code npcpos.txt} spawn table (normalized asset
 * {@code textdata/npcpos.tsv}). Phase 13 corrected columns:
 *
 * <pre>
 * col0 character_refid   joins characterdata_*.txt col1 (1180/1180 distinct)
 * col1 region_code       joins regioncode.txt col1 (1800/1855 distinct);
 *                        region &amp; 0xFF = x sector, region &gt;&gt; 8 = y sector
 * col2 local_x           sector-local x, [0, 1920) for world rows
 * col3 height_y          height axis; ~0 across records
 * col4 local_z           sector-local z, [0, 1920) for world rows
 * </pre>
 *
 * <p>The Phase 12 doc labeled col0 spawn_id / col1 character_refid; live-data
 * joins (characterdata refid 1180/1180 on col0, regioncode id 1800/1855 on
 * col1) disproved that. Negative region codes are dungeon/instance rows.
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

  public int characterRefId(int row) {
    return TsvTable.intAt(table.rows().get(row), 0);
  }

  public int regionCode(int row) {
    return TsvTable.intAt(table.rows().get(row), 1);
  }

  public float localX(int row) {
    return TsvTable.floatAt(table.rows().get(row), 2);
  }

  public float heightY(int row) {
    return TsvTable.floatAt(table.rows().get(row), 3);
  }

  public float localZ(int row) {
    return TsvTable.floatAt(table.rows().get(row), 4);
  }

  public TsvTable raw() {
    return table;
  }
}
