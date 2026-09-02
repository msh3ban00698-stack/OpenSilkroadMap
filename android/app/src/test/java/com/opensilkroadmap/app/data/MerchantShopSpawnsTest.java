package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.IOException;
import java.util.List;
import org.junit.Test;

/**
 * Locks the concrete runtime merchant shop placement index: every NPC-run store
 * whose merchant RefCharID spawns exactly once in {@code npcpos.tsv} becomes one
 * {@link MerchantShopSpawns.Entry} carrying the store code plus the spawn's
 * verified sector + local geometry. Fail-closed: spawn-less stores (only
 * STORE_AM_SPECIAL / 7568) are never given coordinates.
 *
 * <p>Proven coverage on the committed tables (Phase 30):
 * <ul>
 *   <li>52 NPC-run stores → 51 placed, 1 spawnless (7568);</li>
 *   <li>placed(0) = STORE_CH_SMITH (server store 966, merchant 2003) spawn
 *       sector 168x97 at local (332.73, 1406.7);</li>
 *   <li>Jangan sector (168,97) holds 7 placed merchants; the Jangan_Field
 *       region window (156–182 × 89–102) holds 12;</li>
 *   <li>the rendered default launch window (committed sectors 156x89–156x90)
 *       holds 0 placed merchants;</li>
 *   <li>every placed merchant's spawn sector falls inside the entry and world
 *       coordinates follow the proven formula.</li>
 * </ul>
 */
public class MerchantShopSpawnsTest {

  private MerchantShopSpawns load() throws IOException {
    return MerchantShopSpawns.loadDefault();
  }

  @Test
  public void countsAreProven() throws IOException {
    MerchantShopSpawns map = load();
    assertEquals("52 NPC-run stores", 52, map.merchantCount());
    assertEquals("51 placed merchants", 51, map.placedCount());
    assertEquals("1 spawnless merchant", 1, map.spawnlessCount());
  }

  @Test
  public void firstPlacedMerchantIsJanganSmith() throws IOException {
    MerchantShopSpawns map = load();
    MerchantShopSpawns.Entry smith = map.placed(0);
    assertEquals("shopdata row 1 order preserved", 2003, smith.merchantRefId());
    assertEquals("STORE_CH_SMITH", smith.storeCode());
    assertEquals("server store 966", 966, smith.serverStoreId());
    assertEquals("sector 168x97", 168, smith.sectorX());
    assertEquals("sector 168x97", 97, smith.sectorY());
    assertEquals("local x from npcpos col2", 332.73f, smith.localX(), 0.001f);
    assertEquals("local z from npcpos col4", 1406.7f, smith.localZ(), 0.001f);
    assertEquals("world x relative to own sector", 332.73f,
        smith.worldX(168), 0.001f);
    assertEquals("world z relative to own sector", 1406.7f,
        smith.worldZ(97), 0.001f);
  }

  @Test
  public void janganWindowsMatchCommittedPlacement() throws IOException {
    MerchantShopSpawns map = load();
    List<MerchantShopSpawns.Entry> sector =
        map.inWindow(168, 168, 97, 97);
    assertEquals("Jangan sector holds 7 placed merchants", 7, sector.size());
    List<MerchantShopSpawns.Entry> field =
        map.inWindow(156, 182, 89, 102);
    assertEquals("Jangan_Field window holds 12 placed merchants", 12, field.size());
    List<MerchantShopSpawns.Entry> rendered =
        map.inWindow(156, 156, 89, 90);
    assertEquals("default committed launch window holds 0", 0, rendered.size());
  }

  @Test
  public void smithStoreIsBoundToSpawnInJanganWindow() throws IOException {
    MerchantShopSpawns map = load();
    List<MerchantShopSpawns.Entry> field =
        map.inWindow(156, 182, 89, 102);
    boolean smith = false;
    boolean trader = false;
    for (MerchantShopSpawns.Entry e : field) {
      if ("STORE_CH_SMITH".equals(e.storeCode())) {
        smith = true;
        assertEquals(168, e.sectorX());
        assertEquals(97, e.sectorY());
      }
      if ("STORE_CH_TRADER".equals(e.storeCode())) {
        trader = true;
      }
    }
    assertTrue("STORE_CH_SMITH placed in Jangan_Field window", smith);
    assertTrue("STORE_CH_TRADER placed in Jangan_Field window", trader);
  }

  @Test
  public void amSpecialFailsClosedWithoutCoordinates() throws IOException {
    MerchantShopSpawns map = load();
    for (MerchantShopSpawns.Entry e : map.entries()) {
      assertNotNull("placed merchant must carry a spawn", e.spawn);
      assertTrue("store id must resolve", e.serverStoreId() > 0);
    }
    assertEquals("no placed entry for the spawnless merchant 7568",
        false, containsRefId(map, 7568));
    assertEquals("spawnless count matches 7568 only", 1, map.spawnlessCount());
  }

  private static boolean containsRefId(MerchantShopSpawns map, int refId) {
    for (MerchantShopSpawns.Entry e : map.entries()) {
      if (e.merchantRefId() == refId) {
        return true;
      }
    }
    return false;
  }
}
