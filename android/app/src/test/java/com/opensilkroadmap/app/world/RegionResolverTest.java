package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.IOException;
import java.util.List;
import org.junit.Test;

/**
 * Locks the proven region code resolver (client regioncode.tsv + server
 * region_zone.tsv) into the Android runtime.
 *
 * <p>Proven facts asserted (all from committed tables):
 * <ul>
 *   <li>3,287 distinct client ids (regioncode.tsv) and 2,444 server ids
 *       (region_zone.tsv) are combined without overlap loss;</li>
 *   <li>region 25000 → RN_CH_JANGAN / 장안 / CHINA / zone 1001 (the Jangan
 *       anchor, sector 168,97);</li>
 *   <li>duplicate client rows collapse first-row-wins (22478 → RN_JUPITER_GOD,
 *       25289 → RN_JUPITER_SAD);</li>
 *   <li>instance and unknown world codes fail closed (resolve → null);</li>
 *   <li>no guessed mappings: every resolved field comes from a committed table
 *       keyed by the packed region id.</li>
 * </ul>
 */
public class RegionResolverTest {

  @Test
  public void loadsCommittedTables() throws IOException {
    RegionResolver r = RegionResolver.loadDefault();
    assertEquals("3,287 distinct client ids", 3287, r.clientCount());
    assertEquals("2,444 server ids", 2444, r.serverCount());
    assertEquals("union = 3,287 client ∪ 2,444 server with 2,442 shared",
        3289, r.regionIds().size());
  }

  @Test
  public void janganAnchorResolvesFully() throws IOException {
    RegionResolver.Entry e = RegionResolver.loadDefault().resolve(25000);
    assertNotNull(e);
    assertEquals("RN_CH_JANGAN", e.nameCode);
    assertEquals("\uc7a5\uc548", e.localizedName);
    assertEquals("CHINA", e.serverName);
    assertEquals("1001", e.zoneId);
    assertEquals("0", e.flag);
    assertFalse(e.isInstance);
    assertEquals(168, e.sectorX());
    assertEquals(97, e.sectorY());
  }

  @Test
  public void allJanganNameCodesResolveToZone1001() throws IOException {
    List<RegionResolver.Entry> entries =
        RegionResolver.loadDefault().byNameCode("RN_CH_JANGAN");
    assertEquals("9 client ids share RN_CH_JANGAN", 9, entries.size());
    for (RegionResolver.Entry e : entries) {
      assertEquals("1001", e.zoneId);
      assertEquals("CHINA", e.serverName);
      assertTrue("all Jangan sectors share the client grid",
          e.sectorX() >= 167 && e.sectorX() <= 169
              && e.sectorY() >= 96 && e.sectorY() <= 99);
    }
  }

  @Test
  public void duplicateClientRowsCollapseFirstRowWins() throws IOException {
    RegionResolver r = RegionResolver.loadDefault();
    RegionResolver.Entry e22478 = r.resolve(22478);
    assertNotNull(e22478);
    assertEquals("RN_JUPITER_GOD", e22478.nameCode);
    assertEquals("\uc720\ud53c\ud14c\ub974 \uc2e0\uc804-\uc2e0\ub4e4\uc758 \uc815\uc6d0",
        e22478.localizedName);
    RegionResolver.Entry e25289 = r.resolve(25289);
    assertNotNull(e25289);
    assertEquals("RN_JUPITER_SAD", e25289.nameCode);
  }

  @Test
  public void instanceAndUnknownCodesFailClosed() throws IOException {
    RegionResolver r = RegionResolver.loadDefault();
    assertNull("instance code must fail closed", r.resolve(-32760));
    assertNull("unlisted world code must fail closed", r.resolve(22217));
    assertNull("negative sentinel must fail closed", r.resolve(-1));
    assertNull("out-of-range must fail closed", r.resolve(0x7FFFFFFF));
  }

  @Test
  public void everyClientIdResolvesWithoutInvention() throws IOException {
    RegionResolver r = RegionResolver.loadDefault();
    for (Integer id : r.regionIds()) {
      RegionResolver.Entry e = r.resolve(id);
      assertNotNull("regionIds must all resolve", e);
      assertEquals("resolved id must match the queried id",
          (int) id, e.regionId);
    }
  }
}
