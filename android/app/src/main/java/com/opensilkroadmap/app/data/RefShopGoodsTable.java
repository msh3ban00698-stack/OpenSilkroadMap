package com.opensilkroadmap.app.data;

import java.io.IOException;

/**
 * Parsed {@code refshopgoods.txt} shop-goods table (normalized asset
 * {@code textdata/refshopgoods.tsv}). Verified columns:
 *
 * <pre>
 * col1 shop_id       joins refshop.tsv col1
 * col2 category_code joins refshoptab.txt col3 (164/164)
 * col3 item_code     PACKAGE_ITEM_* codes
 * </pre>
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class RefShopGoodsTable {
  private final TsvTable table;

  public RefShopGoodsTable(TsvTable table) {
    this.table = table;
  }

  public static RefShopGoodsTable load() throws IOException {
    return new RefShopGoodsTable(TsvTable.loadDefault("refshopgoods.tsv"));
  }

  public int goodsCount() {
    return table.rowCount();
  }

  public int shopId(int row) {
    return TsvTable.intAt(table.rows().get(row), 1);
  }

  public String categoryCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 2);
  }

  public String itemCode(int row) {
    return TsvTable.strAt(table.rows().get(row), 3);
  }

  public TsvTable raw() {
    return table;
  }
}
