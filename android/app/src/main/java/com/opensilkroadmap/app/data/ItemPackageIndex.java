package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Merchant-scoped item identity over the committed
 * {@code item_package_identity.tsv}, extracted from live Media.pk2
 * {@code itemdata_*.txt} using only the proven anchors:
 *
 * <pre>
 * col1 item id      unique numeric id
 * col2 item code    ITEM_* join key after stripping PACKAGE_ from
 *                   refshopgoods.tsv col3 (1233/1233 merchant stock rows,
 *                   784 unique)
 * col52 model_path  backslash .bsr path, or the literal placeholder xxx
 * col54 icon_path   backslash .ddj path (784/784)
 * </pre>
 *
 * <p>The committed table covers every distinct ITEM_* code sold by the 52
 * NPC-run stores. Unproven itemdata columns (SN_* language keys, prices,
 * stats) are not present. {@code refscrapofpackageitem} is not used: scrap
 * contents are a different ITEM_* for 854/1233 merchant stock rows, so they
 * remain UNKNOWN. Fail-closed: unknown package or item codes return
 * {@code null}. No Android dependencies; pure JVM.
 *
 * <p>316/318 is the {@code refquestrewarditems.tsv} → itemdata col2 join
 * (2 unmatched: {@code ITEM_QNO_EU_CONS_12_02} and the {@code xxx}
 * placeholder) and is not merchant-stock coverage.
 */
public final class ItemPackageIndex {

  public static final String PACKAGE_PREFIX = "PACKAGE_";

  /** One proven item identity (code + id + model path + icon path). */
  public static final class Identity {
    public final String itemCode;
    public final int itemId;
    public final String modelPath;
    public final String iconPath;

    public Identity(String itemCode, int itemId, String modelPath, String iconPath) {
      this.itemCode = itemCode;
      this.itemId = itemId;
      this.modelPath = modelPath;
      this.iconPath = iconPath;
    }
  }

  private final Map<String, Identity> byItemCode;

  public ItemPackageIndex(TsvTable table) {
    Map<String, Identity> map = new LinkedHashMap<String, Identity>();
    for (String[] row : table.rows()) {
      String code = TsvTable.strAt(row, 0);
      int itemId = TsvTable.intAt(row, 1);
      String model = TsvTable.strAt(row, 2);
      String icon = TsvTable.strAt(row, 3);
      if (code.isEmpty() || !code.startsWith("ITEM_")) {
        continue;
      }
      if (!map.containsKey(code)) {
        map.put(code, new Identity(code, itemId, model, icon));
      }
    }
    this.byItemCode = Collections.unmodifiableMap(map);
  }

  public static ItemPackageIndex loadDefault() throws IOException {
    return new ItemPackageIndex(TsvTable.loadDefault("item_package_identity.tsv"));
  }

  /**
   * Drop exactly the leading {@code PACKAGE_} prefix when the remainder is an
   * {@code ITEM_*} code; otherwise {@code null} (fail-closed).
   */
  public static String stripPackage(String packageCode) {
    if (packageCode == null || !packageCode.startsWith(PACKAGE_PREFIX)) {
      return null;
    }
    String stripped = packageCode.substring(PACKAGE_PREFIX.length());
    if (!stripped.startsWith("ITEM_")) {
      return null;
    }
    return stripped;
  }

  public int size() {
    return byItemCode.size();
  }

  /** Identity for an ITEM_* code, or {@code null} (fail-closed). */
  public Identity resolve(String itemCode) {
    if (itemCode == null || itemCode.isEmpty()) {
      return null;
    }
    return byItemCode.get(itemCode);
  }

  /**
   * Identity for a PACKAGE_ITEM_* goods code via prefix-strip, or {@code null}
   * (fail-closed).
   */
  public Identity resolvePackage(String packageCode) {
    return resolve(stripPackage(packageCode));
  }
}
