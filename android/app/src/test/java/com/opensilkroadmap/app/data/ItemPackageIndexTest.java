package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import org.junit.Test;

/**
 * Locks the merchant-scoped itemdata package join: every NPC-store
 * {@code refshopgoods} {@code PACKAGE_ITEM_*} code strips exactly the leading
 * {@code PACKAGE_} prefix to a real {@code ITEM_*} row extracted from live
 * {@code itemdata_*.txt} using only the proven anchors (col1 id, col2 code,
 * col52 model path, col54 icon path).
 *
 * <p>Proven coverage on the committed table:
 * <ul>
 *   <li>784 unique ITEM_* identities covering 1233/1233 merchant stock rows;</li>
 *   <li>{@code PACKAGE_ITEM_CH_BLADE_01_A} → {@code ITEM_CH_BLADE_01_A} id 107
 *       / {@code item\\china\\weapon\\blade_01.bsr};</li>
 *   <li>{@code PACKAGE_ITEM_ETC_AMMO_ARROW_01} → model placeholder {@code xxx}
 *       with a real {@code .ddj} icon;</li>
 *   <li>unknown package/item codes fail closed;</li>
 *   <li>316/318 is the quest-reward join, not merchant stock.</li>
 * </ul>
 */
public class ItemPackageIndexTest {

  private ItemPackageIndex load() throws IOException {
    return ItemPackageIndex.loadDefault();
  }

  @Test
  public void coversEveryMerchantStockPackage() throws IOException {
    ItemPackageIndex idx = load();
    assertEquals("784 unique merchant ITEM_* codes", 784, idx.size());
    ShopMerchantIndex shops = ShopMerchantIndex.loadDefault();
    int resolved = 0;
    Set<String> unique = new HashSet<String>();
    for (ShopMerchantIndex.Merchant m : shops.merchants()) {
      for (ShopMerchantIndex.Tab t : m.tabs) {
        for (ShopMerchantIndex.StockItem s : t.stock) {
          ItemPackageIndex.Identity id = idx.resolvePackage(s.packageCode);
          assertNotNull("package " + s.packageCode, id);
          unique.add(id.itemCode);
          resolved++;
        }
      }
    }
    assertEquals(1233, resolved);
    assertEquals(784, unique.size());
  }

  @Test
  public void smithBladeAndArrowAreProven() throws IOException {
    ItemPackageIndex idx = load();
    ItemPackageIndex.Identity blade =
        idx.resolvePackage("PACKAGE_ITEM_CH_BLADE_01_A");
    assertNotNull(blade);
    assertEquals("ITEM_CH_BLADE_01_A", blade.itemCode);
    assertEquals(107, blade.itemId);
    assertEquals("item\\china\\weapon\\blade_01.bsr", blade.modelPath);
    assertEquals("item\\china\\weapon\\blade_01.ddj", blade.iconPath);
    ItemPackageIndex.Identity sword = idx.resolve("ITEM_CH_SWORD_01_A");
    assertNotNull(sword);
    assertEquals(71, sword.itemId);
    ItemPackageIndex.Identity arrow =
        idx.resolvePackage("PACKAGE_ITEM_ETC_AMMO_ARROW_01");
    assertNotNull(arrow);
    assertEquals("ITEM_ETC_AMMO_ARROW_01", arrow.itemCode);
    assertEquals(62, arrow.itemId);
    assertEquals("xxx", arrow.modelPath);
    assertEquals("item\\etc\\ammo_arrow_01.ddj", arrow.iconPath);
  }

  @Test
  public void unknownCodesFailClosed() throws IOException {
    ItemPackageIndex idx = load();
    assertNull(idx.resolve(null));
    assertNull(idx.resolve(""));
    assertNull(idx.resolve("ITEM_DOES_NOT_EXIST"));
    assertNull(idx.resolvePackage(null));
    assertNull(idx.resolvePackage(""));
    assertNull(idx.resolvePackage("ITEM_CH_BLADE_01_A"));
    assertNull(idx.resolvePackage("PACKAGE_NOT_AN_ITEM"));
    assertNull(idx.resolvePackage("PACKAGE_ITEM_DOES_NOT_EXIST"));
    assertNull(ItemPackageIndex.stripPackage("ITEM_CH_BLADE_01_A"));
    assertEquals("ITEM_CH_BLADE_01_A",
        ItemPackageIndex.stripPackage("PACKAGE_ITEM_CH_BLADE_01_A"));
  }

  @Test
  public void everyIdentityHasItemCodeAndDdjIcon() throws IOException {
    ItemPackageIndex idx = load();
    ShopMerchantIndex shops = ShopMerchantIndex.loadDefault();
    int identified = 0;
    for (ShopMerchantIndex.Merchant m : shops.merchants()) {
      for (ShopMerchantIndex.Tab t : m.tabs) {
        for (ShopMerchantIndex.StockItem s : t.stock) {
          ItemPackageIndex.Identity id = idx.resolvePackage(s.packageCode);
          assertNotNull(id);
          assertTrue(id.itemCode.startsWith("ITEM_"));
          assertTrue(id.iconPath.toLowerCase().endsWith(".ddj"));
          assertTrue(id.modelPath.toLowerCase().endsWith(".bsr")
              || "xxx".equals(id.modelPath));
          identified++;
        }
      }
    }
    assertEquals(1233, identified);
  }
}
