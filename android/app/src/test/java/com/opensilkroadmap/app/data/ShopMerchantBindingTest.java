package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.Test;

/**
 * Phase 30 shop-merchant binding tests. Every assertion is against the REAL
 * committed assets under {@code src/main/assets/game/textdata/}:
 *
 * <ul>
 * <li>{@code shopdata.tsv} (client): store_code {@code STORE_CH_SMITH} → merchant
 *     RefCharID 2003 and tab ids 579/580/581;
 * <li>{@code shoptabdata.tsv} (client): tab id → tab_code
 *     {@code STORE_CH_SMITH_TAB1..3} (SN_TAB_WEAPON/SHIELD/ETC);
 * <li>{@code refshop.tsv} / {@code refshopgoods.tsv} (server): store numeric id
 *     966 and per-tab PACKAGE_ITEM_* stock with unique order.
 * </ul>
 */
public class ShopMerchantBindingTest {

  @Test
  public void shopDataLoadsAllRealStores() throws Exception {
    ShopDataTable shop = ShopDataTable.loadDefault();
    assertEquals(57, shop.shopCount());
    // File order preserved: MALL_CONSUME (row 0), STORE_CH_SMITH (row 1).
    assertEquals("MALL_CONSUME", shop.storeCode(0));
    assertFalse(shop.isNpcStore(0));
    assertEquals("STORE_CH_SMITH", shop.storeCode(1));
    assertEquals(2003, shop.merchantRefId(1));
    assertTrue(shop.isNpcStore(1));
  }

  @Test
  public void npcMerchantStoresNumber52() throws Exception {
    ShopDataTable shop = ShopDataTable.loadDefault();
    int npcStores = 0;
    int mallStores = 0;
    for (int i = 0; i < shop.shopCount(); i++) {
      if (shop.isNpcStore(i)) {
        npcStores++;
      } else {
        mallStores++;
      }
    }
    assertEquals(52, npcStores);
    assertEquals(5, mallStores);
  }

  @Test
  public void smithStoreTabIdsResolveInShopTabData() throws Exception {
    ShopDataTable shop = ShopDataTable.loadDefault();
    ShopTabDataTable tabs = ShopTabDataTable.loadDefault();
    List<Integer> ids = shop.tabIds(1);
    assertEquals(3, ids.size());
    assertEquals(Integer.valueOf(579), ids.get(0));
    assertEquals("STORE_CH_SMITH_TAB1", tabCodeFor(tabs, 579));
    assertEquals("STORE_CH_SMITH_TAB3", tabCodeFor(tabs, 581));
    assertEquals("SN_TAB_WEAPON", snCodeFor(tabs, 579));
  }

  @Test
  public void merchantIndexBindsSmithStoreToRefid2003() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    assertEquals(52, index.merchantCount());
    assertTrue(index.isMerchantRefId(2003));
    ShopMerchantIndex.Merchant smith = index.merchantForRefId(2003);
    assertNotNull(smith);
    assertEquals("STORE_CH_SMITH", smith.storeCode);
    assertEquals(966, smith.storeId);
    assertEquals(3, smith.tabs.size());
    assertEquals("STORE_CH_SMITH_TAB1", smith.tabs.get(0).tabCode);
    assertEquals("STORE_CH_SMITH_TAB3", smith.tabs.get(2).tabCode);
    assertEquals(19, smith.stockSize());
  }

  @Test
  public void merchantStocksMatchServerGoodsRows() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    assertTrue(index.isMerchantRefId(2004));
    assertEquals(108, index.merchantForRefId(2004).stockSize());
    assertTrue(index.isMerchantRefId(2005));
    assertEquals(29, index.merchantForRefId(2005).stockSize());
    assertTrue(index.isMerchantRefId(2008));
    assertEquals(28, index.merchantForRefId(2008).stockSize());
  }

  @Test
  public void traderStockIsEmptyNotInvented() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    ShopMerchantIndex.Merchant trader = index.merchantForRefId(2027);
    assertNotNull(trader);
    assertEquals("STORE_CH_TRADER", trader.storeCode);
    assertEquals(2, trader.tabs.size());
    for (ShopMerchantIndex.Tab t : trader.tabs) {
      assertEquals(0, t.stock.size());
    }
  }

  @Test
  public void merchantRefIdsJoinNpcPosExceptAmSpecial() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    NpcPosTable npc = NpcPosTable.load();
    Set<Integer> spawned = new HashSet<Integer>();
    for (int i = 0; i < npc.spawnCount(); i++) {
      spawned.add(npc.characterRefId(i));
    }
    Set<Integer> missing = new HashSet<Integer>(index.merchantRefIds());
    missing.removeAll(spawned);
    assertEquals("only STORE_AM_SPECIAL/7568 has no npcpos spawn",
        "[7568]", missing.toString());
    // 7568 is still a real (spawn-less) merchant in the shop catalog.
    assertEquals("STORE_AM_SPECIAL", index.merchantForRefId(7568).storeCode);
  }

  @Test
  public void everyNpcStoreCodeExistsInRefShop() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    for (ShopMerchantIndex.Merchant m : index.merchants()) {
      assertTrue("store id resolved for " + m.storeCode, m.storeId > 0);
    }
  }

  @Test
  public void merchantStockCarriesPackageIdentity() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    int resolved = 0;
    for (ShopMerchantIndex.Merchant m : index.merchants()) {
      assertEquals(m.stockSize(), m.identifiedStockCount());
      for (ShopMerchantIndex.Tab t : m.tabs) {
        for (ShopMerchantIndex.StockItem s : t.stock) {
          assertNotNull("package " + s.packageCode, s.identity);
          assertTrue(s.itemCode().startsWith("ITEM_"));
          assertTrue(s.iconPath().toLowerCase().endsWith(".ddj"));
          assertTrue(s.modelPath().toLowerCase().endsWith(".bsr")
              || "xxx".equals(s.modelPath()));
          resolved++;
        }
      }
    }
    assertEquals(1233, resolved);
    assertEquals(1233, index.identifiedStockCount());
  }

  @Test
  public void smithStockIdentityIsCodesAndIconsOnly() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    ShopMerchantIndex.Merchant smith = index.merchantForRefId(2003);
    assertEquals(19, smith.stockSize());
    assertEquals(19, smith.identifiedStockCount());
    ShopMerchantIndex.StockItem sword = smith.tabs.get(0).stock.get(0);
    assertEquals("PACKAGE_ITEM_CH_SWORD_01_A", sword.packageCode);
    assertEquals("ITEM_CH_SWORD_01_A", sword.itemCode());
    assertEquals(71, sword.itemId());
    assertEquals("item\\china\\weapon\\sword_01.bsr", sword.modelPath());
    assertEquals("item\\china\\weapon\\sword_01.ddj", sword.iconPath());
    ShopMerchantIndex.StockItem blade = null;
    for (ShopMerchantIndex.StockItem s : smith.tabs.get(0).stock) {
      if ("PACKAGE_ITEM_CH_BLADE_01_A".equals(s.packageCode)) {
        blade = s;
      }
    }
    assertNotNull(blade);
    assertEquals("ITEM_CH_BLADE_01_A", blade.itemCode());
    assertEquals(107, blade.itemId());
    ShopMerchantIndex.StockItem arrow = smith.tabs.get(2).stock.get(0);
    assertEquals("PACKAGE_ITEM_ETC_AMMO_ARROW_01", arrow.packageCode);
    assertEquals("ITEM_ETC_AMMO_ARROW_01", arrow.itemCode());
    assertEquals("xxx", arrow.modelPath());
    assertEquals("item\\etc\\ammo_arrow_01.ddj", arrow.iconPath());
  }

  @Test
  public void fourArgBuildLeavesStockIdentityNull() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.build(
        ShopDataTable.loadDefault(),
        ShopTabDataTable.loadDefault(),
        TsvTable.loadDefault("refshop.tsv"),
        TsvTable.loadDefault("refshopgoods.tsv"));
    ShopMerchantIndex.Merchant smith = index.merchantForRefId(2003);
    assertEquals(19, smith.stockSize());
    assertEquals(0, smith.identifiedStockCount());
    assertEquals(0, index.identifiedStockCount());
    ShopMerchantIndex.StockItem sword = smith.tabs.get(0).stock.get(0);
    assertEquals("PACKAGE_ITEM_CH_SWORD_01_A", sword.packageCode);
    assertNull(sword.identity);
    assertNull(sword.itemCode());
    assertNull(sword.iconPath());
    assertNull(sword.modelPath());
  }

  @Test
  public void goodsOrderIsUniqueWithinEachTab() throws Exception {
    ShopMerchantIndex index = ShopMerchantIndex.loadDefault();
    for (ShopMerchantIndex.Merchant m : index.merchants()) {
      for (ShopMerchantIndex.Tab t : m.tabs) {
        Set<Integer> orders = new HashSet<Integer>();
        int prev = Integer.MIN_VALUE;
        for (ShopMerchantIndex.StockItem s : t.stock) {
          assertTrue("ascending order in " + t.tabCode, s.order > prev);
          assertTrue("unique order in " + t.tabCode, orders.add(s.order));
          prev = s.order;
        }
      }
    }
  }

  private static String tabCodeFor(ShopTabDataTable tabs, int id) {
    for (int i = 0; i < tabs.tabCount(); i++) {
      if (tabs.tabId(i) == id) {
        return tabs.tabCode(i);
      }
    }
    return null;
  }

  private static String snCodeFor(ShopTabDataTable tabs, int id) {
    for (int i = 0; i < tabs.tabCount(); i++) {
      if (tabs.tabId(i) == id) {
        return tabs.snTabCode(i);
      }
    }
    return null;
  }
}
