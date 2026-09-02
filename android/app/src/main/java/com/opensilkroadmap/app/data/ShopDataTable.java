package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.List;

/**
 * Parsed {@code shopdata.txt} client shop table (normalized asset
 * {@code textdata/shopdata.tsv}). Verified columns (Phase 30 shop-merchant
 * binding):
 *
 * <pre>
 * col0 constant '1'            (service-like prefix; semantics not proven)
 * col1 store_id                unique 1..61 with gaps (client store key)
 * col2 store_code              MALL_* / STORE_* codes; 57/57 present in refshop.tsv col3
 * col3 'xxx' / col4 '0'        placeholders
 * col5 merchant_refid          NPC RefCharID when &gt; 0 (52 rows); negative
 *                              0xF0000001..0xF0000006 sentinel for MALL cash shops
 * col6..col11 store_tab_ids    tab ids (0 = none); join shoptabdata.tsv col1
 * col16/17 'xxx'               placeholders
 * </pre>
 *
 * <p>The merchant_refid joins characterdata_*.txt col1 and npcpos.tsv col0 for
 * 51/52 NPC shops (STORE_AM_SPECIAL / 7568 has no npcpos spawn). No Android
 * dependencies; pure JVM.
 */
public final class ShopDataTable {
  private final TsvTable table;

  public ShopDataTable(TsvTable table) {
    this.table = table;
  }

  public static ShopDataTable parse(Reader reader) throws IOException {
    return new ShopDataTable(TsvTable.parse("shopdata.tsv", reader));
  }

  public static ShopDataTable loadDefault() throws IOException {
    return new ShopDataTable(TsvTable.loadDefault("shopdata.tsv"));
  }

  public int shopCount() {
    return table.rowCount();
  }

  public int storeId(int row) {
    return TsvTable.intAt(table.rows().get(row), 1);
  }

  public String storeCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 2);
  }

  /** NPC RefCharID for NPC-run stores, or a negative 0xFxxxxxxx MALL sentinel. */
  public int merchantRefId(int row) {
    return TsvTable.intAt(table.rows().get(row), 5);
  }

  public boolean isNpcStore(int row) {
    return merchantRefId(row) > 0;
  }

  /** Store tab ids from col6..col11 (0 = padding); caller sees file order. */
  public List<Integer> tabIds(int row) {
    String[] cells = table.rows().get(row);
    List<Integer> out = new ArrayList<Integer>();
    for (int c = 6; c <= 11 && c < cells.length; c++) {
      int v = TsvTable.intAt(cells, c);
      if (v != 0) {
        out.add(v);
      }
    }
    return out;
  }
}
