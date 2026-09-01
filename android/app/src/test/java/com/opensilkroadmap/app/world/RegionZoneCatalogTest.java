package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.opensilkroadmap.app.data.TsvTable;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import org.junit.Test;

/**
 * Locks the committed server region → zone catalog (region_zone.tsv) into the
 * Android runtime with exact source provenance and fail-closed behavior.
 *
 * <p>Proven facts asserted (all derived from committed data + Phase 10/2
 * verified formulas):
 * <ul>
 *   <li>2,444 world rows sourced from SR_GameRefData/RefRegion.txt with its
 *       sha256 recorded verbatim;</li>
 *   <li>packing {@code regionId == (sectorY << 8) | sectorX} holds for every
 *       committed row and matches {@link WorldCoordinates} round-trips;</li>
 *   <li>region 25000 resolves to sector (168, 97), CHINA, zone 1001 —
 *       the same anchor as RN_CH_JANGAN in regioncode.tsv;</li>
 *   <li>21 server names and 13 zone ids (from the committed header);</li>
 *   <li>2,442/2,444 ids also exist in the client regioncode.tsv;</li>
 *   <li>unknown and instance/dungeon ids fail closed (resolve → null).</li>
 * </ul>
 */
public class RegionZoneCatalogTest {

  private static final String SOURCE_SHA =
      "a3749d9e43719208c0098c145022824ce17d3d86d21458f505ee8d187c1cd4c4";

  @Test
  public void loadsCommittedCatalogWithProvenance() throws IOException {
    RegionZoneCatalog cat = RegionZoneCatalog.loadDefault();
    assertEquals("2,444 world rows must be committed", 2444, cat.rowCount());
    assertEquals("source sha256 must be recorded verbatim",
        SOURCE_SHA, cat.sourceSha256());
    assertTrue("source sha256 must look like a hash",
        cat.sourceSha256().matches("[0-9a-f]{64}"));
  }

  @Test
  public void packingFormulaHoldsForEveryRow() throws IOException {
    RegionZoneCatalog cat = RegionZoneCatalog.loadDefault();
    for (int regionId : cat.regionIds()) {
      RegionZoneCatalog.Entry e = cat.resolve(regionId);
      assertNotNull(e);
      assertEquals(regionId, WorldCoordinates.packRegion(e.sectorX, e.sectorY));
      int[] s = WorldCoordinates.unpackRegion(regionId);
      assertEquals(e.sectorX, s[0]);
      assertEquals(e.sectorY, s[1]);
    }
  }

  @Test
  public void region25000IsChinaZone1001() throws IOException {
    RegionZoneCatalog.Entry e = RegionZoneCatalog.loadDefault().resolve(25000);
    assertNotNull("region 25000 must be committed", e);
    assertEquals(168, e.sectorX);
    assertEquals(97, e.sectorY);
    assertEquals("CHINA", e.serverName);
    assertEquals("1001", e.zoneId);
    assertEquals("0", e.flag);
  }

  @Test
  public void fortressHotanAreaZoneIs2001() throws IOException {
    RegionZoneCatalog.Entry e = RegionZoneCatalog.loadDefault().resolve(14660);
    assertNotNull(e);
    assertEquals(68, e.sectorX);
    assertEquals(57, e.sectorY);
    assertEquals("FORT_HT_AREA", e.serverName);
    assertEquals("2001", e.zoneId);
  }

  @Test
  public void distinctNamesAndZonesMatchCommittedHeader() throws IOException {
    RegionZoneCatalog cat = RegionZoneCatalog.loadDefault();
    assertEquals("21 distinct server names", 21, cat.serverNames().size());
    assertEquals("13 distinct zone ids", 13, cat.zoneIds().size());
  }

  @Test
  public void failClosedForUnknownAndInstanceIds() throws IOException {
    RegionZoneCatalog cat = RegionZoneCatalog.loadDefault();
    assertNull("unknown id must fail closed", cat.resolve(0x7FFFFFFF));
    assertNull("negative instance id must fail closed", cat.resolve(-1));
    assertNull("instance sentinel must fail closed", cat.resolve(-32760));
  }

  @Test
  public void idsOverlapClientRegioncode() throws IOException {
    RegionZoneCatalog cat = RegionZoneCatalog.loadDefault();
    Set<Integer> zoneIds = new HashSet<Integer>(cat.regionIds());
    TsvTable regionCode = TsvTable.loadDefault("regioncode.tsv");
    Set<Integer> client = new HashSet<Integer>();
    for (String[] row : regionCode.rows()) {
      String v = TsvTable.strAt(row, 1).trim();
      if (!v.isEmpty()) {
        client.add(Integer.parseInt(v));
      }
    }
    Set<Integer> overlap = new HashSet<Integer>(zoneIds);
    overlap.retainAll(client);
    assertEquals("2,442/2,444 ids must also be in regioncode.tsv",
        2442, overlap.size());
  }

  @Test
  public void janganTownSectorHasZone1001() throws IOException {
    // Jangan town window is (167..169, 96..99); every one of its sectors that
    // is in the server catalog must be zone 1001 (CHINA).
    RegionZoneCatalog cat = RegionZoneCatalog.loadDefault();
    int checked = 0;
    for (int sx = 167; sx <= 169; sx++) {
      for (int sy = 96; sy <= 99; sy++) {
        RegionZoneCatalog.Entry e = cat.resolve(WorldCoordinates.packRegion(sx, sy));
        if (e != null) {
          assertEquals("1001", e.zoneId);
          checked++;
        }
      }
    }
    assertTrue("at least one Jangan-town sector must be in the catalog",
        checked >= 1);
  }
}
