package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Merchant shop binding index (Phase 30). Joins four committed tables to bind
 * every NPC-run store in {@code shopdata.tsv} to its merchant RefCharID and to
 * the store's real tab + item stock, in the authoritative shopdata file order:
 *
 * <ol>
 * <li>shopdata.tsv col2 (store_code)      → col5 (merchant_refid, &gt;0) and
 *     col6.. (store_tab_ids)
 * <li>shoptabdata.tsv col1 (tab_id)       → col2 (tab_code)
 * <li>refshop.tsv col3 (store_code)       → col2 (server store numeric id)
 * <li>refshopgoods.tsv col2 (tab_code)    → col3 (PACKAGE_ITEM_* stock code) with
 *     col4 (per-tab unique order; unique within every tab, 164/164)
 * </ol>
 *
 * <p>Proven on the committed set: 57 shopdata stores, 52 NPC-run (positive
 * merchant_refid), every store_code exists in refshop.tsv (57/57), every
 * merchant tab id resolves in shoptabdata.tsv, and 51/52 merchant RefCharIds
 * appear in npcpos.tsv (STORE_AM_SPECIAL/7568 has no npcpos spawn). A store tab
 * may have an empty stock list in refshopgoods.tsv (e.g. STORE_CH_TRADER tabs),
 * which is preserved as an empty list, never invented. No Android
 * dependencies; pure JVM.
 */
public final class ShopMerchantIndex {

  /** One stock row of a store tab (server-authoritative package item code). */
  public static final class StockItem {
    public final String packageCode;
    public final int order;

    public StockItem(String packageCode, int order) {
      this.packageCode = packageCode;
      this.order = order;
    }
  }

  /** One store tab bound to shopdata/shoptabdata/refshopgoods rows. */
  public static final class Tab {
    public final int tabId;
    public final String tabCode;
    public final int groupId;
    public final String snTabCode;
    public final List<StockItem> stock;

    public Tab(int tabId, String tabCode, int groupId, String snTabCode,
               List<StockItem> stock) {
      this.tabId = tabId;
      this.tabCode = tabCode;
      this.groupId = groupId;
      this.snTabCode = snTabCode;
      this.stock = stock;
    }

    public int stockSize() {
      return stock.size();
    }
  }

  /** One NPC-run store bound to its merchant RefCharID. */
  public static final class Merchant {
    public final int storeId;
    public final String storeCode;
    public final int merchantRefId;
    public final List<Tab> tabs;

    public Merchant(int storeId, String storeCode, int merchantRefId,
                    List<Tab> tabs) {
      this.storeId = storeId;
      this.storeCode = storeCode;
      this.merchantRefId = merchantRefId;
      this.tabs = tabs;
    }

    public int stockSize() {
      int n = 0;
      for (Tab t : tabs) {
        n += t.stock.size();
      }
      return n;
    }
  }

  private final List<Merchant> merchants;
  private final Map<Integer, Merchant> byRefId;
  private final Set<Integer> refIds;

  public ShopMerchantIndex(List<Merchant> merchants) {
    this.merchants = Collections.unmodifiableList(new ArrayList<Merchant>(merchants));
    Map<Integer, Merchant> by = new HashMap<Integer, Merchant>();
    Set<Integer> ids = new HashSet<Integer>();
    for (Merchant m : merchants) {
      by.put(m.merchantRefId, m);
      ids.add(m.merchantRefId);
    }
    this.byRefId = Collections.unmodifiableMap(by);
    this.refIds = Collections.unmodifiableSet(ids);
  }

  public static ShopMerchantIndex build(
      ShopDataTable shop, ShopTabDataTable tabs, TsvTable refshop,
      TsvTable refshopGoods) {
    Map<Integer, String> tabIdToCode = new HashMap<Integer, String>();
    Map<Integer, Integer> tabIdToGroup = new HashMap<Integer, Integer>();
    Map<Integer, String> tabIdToSn = new HashMap<Integer, String>();
    for (int i = 0; i < tabs.tabCount(); i++) {
      tabIdToCode.put(tabs.tabId(i), tabs.tabCode(i));
      tabIdToGroup.put(tabs.tabId(i), tabs.groupId(i));
      tabIdToSn.put(tabs.tabId(i), tabs.snTabCode(i));
    }
    Map<String, Integer> storeCodeToId = new HashMap<String, Integer>();
    for (String[] row : refshop.rows()) {
      if (TsvTable.strAt(row, 3).isEmpty()) {
        continue;
      }
      storeCodeToId.put(TsvTable.strAt(row, 3), TsvTable.intAt(row, 2));
    }
    Map<String, List<StockItem>> stockByTab = new LinkedHashMap<String, List<StockItem>>();
    List<String[]> goods = refshopGoods.rows();
    for (int i = 0; i < goods.size(); i++) {
      String[] row = goods.get(i);
      String tabCode = TsvTable.strAt(row, 2);
      String code = TsvTable.strAt(row, 3);
      if (tabCode.isEmpty() || code.isEmpty()) {
        continue;
      }
      int order = TsvTable.intAt(row, 4);
      List<StockItem> list = stockByTab.get(tabCode);
      if (list == null) {
        list = new ArrayList<StockItem>();
        stockByTab.put(tabCode, list);
      }
      list.add(new StockItem(code, order));
    }
    List<Merchant> out = new ArrayList<Merchant>();
    for (int r = 0; r < shop.shopCount(); r++) {
      if (!shop.isNpcStore(r)) {
        continue;
      }
      String storeCode = shop.storeCode(r);
      int refId = shop.merchantRefId(r);
      int storeId = storeCodeToId.containsKey(storeCode)
          ? storeCodeToId.get(storeCode) : 0;
      List<Tab> tabOut = new ArrayList<Tab>();
      for (Integer tabId : shop.tabIds(r)) {
        String tabCode = tabIdToCode.get(tabId);
        if (tabCode == null) {
          continue;
        }
        List<StockItem> stock = stockByTab.get(tabCode);
        if (stock == null) {
          stock = Collections.<StockItem>emptyList();
        } else {
          List<StockItem> sorted =
              new ArrayList<StockItem>(stock);
          Collections.sort(sorted, (a, b) -> Integer.compare(a.order, b.order));
          stock = Collections.unmodifiableList(sorted);
        }
        tabOut.add(new Tab(tabId, tabCode,
            tabIdToGroup.containsKey(tabId) ? tabIdToGroup.get(tabId) : 0,
            tabIdToSn.containsKey(tabId) ? tabIdToSn.get(tabId) : "",
            stock));
      }
      out.add(new Merchant(storeId, storeCode, refId,
          Collections.unmodifiableList(tabOut)));
    }
    return new ShopMerchantIndex(out);
  }

  public static ShopMerchantIndex loadDefault() throws IOException {
    return build(
        ShopDataTable.loadDefault(),
        ShopTabDataTable.loadDefault(),
        TsvTable.loadDefault("refshop.tsv"),
        TsvTable.loadDefault("refshopgoods.tsv"));
  }

  public List<Merchant> merchants() {
    return merchants;
  }

  public int merchantCount() {
    return merchants.size();
  }

  public Merchant merchantForRefId(int refId) {
    return byRefId.get(refId);
  }

  public boolean isMerchantRefId(int refId) {
    return byRefId.containsKey(refId);
  }

  public Set<Integer> merchantRefIds() {
    return refIds;
  }
}
