package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.io.Reader;

/**
 * Parsed {@code shoptabdata.txt} client shop-tab table (normalized asset
 * {@code textdata/shoptabdata.tsv}). Verified columns (Phase 30 shop-merchant
 * binding):
 *
 * <pre>
 * col0 constant '1'
 * col1 tab_id         unique positive id; the tab ids listed in shopdata.tsv
 *                     col6.. resolve here
 * col2 tab_code       STORE_*_TABn / MALL_* codes; NPC-store codes are the same
 *                     values as refshoptab.txt col3 and refshopgoods.tsv col2
 * col3 group_id       tab-group id (shopgroupdata.txt col1; not committed)
 * col4 sn_tab_code    SN_TAB_* string key (language key, unresolved here)
 * </pre>
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class ShopTabDataTable {
  private final TsvTable table;

  public ShopTabDataTable(TsvTable table) {
    this.table = table;
  }

  public static ShopTabDataTable parse(Reader reader) throws IOException {
    return new ShopTabDataTable(TsvTable.parse("shoptabdata.tsv", reader));
  }

  public static ShopTabDataTable loadDefault() throws IOException {
    return new ShopTabDataTable(TsvTable.loadDefault("shoptabdata.tsv"));
  }

  public int tabCount() {
    return table.rowCount();
  }

  public int tabId(int row) {
    return TsvTable.intAt(table.rows().get(row), 1);
  }

  public String tabCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 2);
  }

  public int groupId(int row) {
    return TsvTable.intAt(table.rows().get(row), 3);
  }

  public String snTabCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 4);
  }
}
