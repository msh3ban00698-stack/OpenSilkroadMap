package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

import java.io.StringReader;
import org.junit.Test;

public class RegionCatalogTest {

  @Test
  public void parsesTownSection() throws Exception {
    RegionCatalog catalog =
        RegionCatalog.parse(
            new StringReader("# comment\nTOWN\tThiefTown\t\t182:96,183:96\n"));
    assertEquals(1, catalog.sectionCount());
    assertEquals(2, catalog.cellCount());
    RegionInfo town = catalog.regions().get(0);
    assertEquals(RegionInfo.Type.TOWN, town.type);
    assertEquals("ThiefTown", town.name);
    assertEquals("", town.code);
    assertEquals(182, town.cells.get(0).x);
    assertEquals(96, town.cells.get(0).y);
    assertEquals("ALL", town.cells.get(0).kind);
    assertEquals(0, town.cells.get(0).extra.length);
  }

  @Test
  public void parsesFieldWithCodeAndRectExtra() throws Exception {
    RegionCatalog catalog =
        RegionCatalog.parse(
            new StringReader("FIELD\tDonwhangCave\tdonwhang\t1:128\nFIELD\tBandit\t\t78:67:R:520:0:1920:1920\n"));
    RegionInfo field = catalog.regions().get(0);
    assertEquals(RegionInfo.Type.FIELD, field.type);
    assertEquals("donwhang", field.code);
    RegionInfo.Cell rect = catalog.regions().get(1).cells.get(0);
    assertEquals("RECT", rect.kind);
    assertEquals(4, rect.extra.length);
    assertEquals(520, rect.extra[0]);
    assertEquals(1920, rect.extra[3]);
  }

  @Test
  public void regionForCellReturnsFirstMatchInFileOrder() throws Exception {
    RegionCatalog catalog =
        RegionCatalog.parse(new StringReader("TOWN\tA\t\t100:100\nTOWN\tB\t\t100:100\n"));
    RegionInfo region = catalog.regionForCell(100, 100);
    assertNotNull(region);
    assertEquals("A", region.name);
  }

  @Test
  public void regionForCellReturnsNullForUnknownCell() throws Exception {
    RegionCatalog catalog = RegionCatalog.parse(new StringReader("TOWN\tA\t\t100:100\n"));
    assertNull(catalog.regionForCell(1, 2));
  }

  @Test
  public void realCommittedCatalogHasVerifiedStructure() throws Exception {
    RegionCatalog catalog = RegionCatalog.loadDefault();
    assertEquals(72, catalog.sectionCount());
    assertEquals(3468, catalog.cellCount());
  }

  @Test
  public void realCommittedCatalogMapsThiefTownCell() throws Exception {
    RegionCatalog catalog = RegionCatalog.loadDefault();
    RegionInfo region = catalog.regionForCell(182, 96);
    assertNotNull(region);
    assertEquals("ThiefTown", region.name);
    assertEquals(RegionInfo.Type.TOWN, region.type);
  }

  @Test
  public void realCommittedCatalogMapsDungeonCode() throws Exception {
    RegionCatalog catalog = RegionCatalog.loadDefault();
    RegionInfo region = catalog.regionForCell(1, 128);
    assertNotNull(region);
    assertEquals("DonwhangCave", region.name);
    assertEquals("donwhang", region.code);
  }

  @Test
  public void realCommittedCatalogSectionCountsMatchInventory() throws Exception {
    RegionCatalog catalog = RegionCatalog.loadDefault();
    int towns = 0;
    int fields = 0;
    for (RegionInfo r : catalog.regions()) {
      if (r.type == RegionInfo.Type.TOWN) {
        towns++;
      } else if (r.type == RegionInfo.Type.FIELD) {
        fields++;
      }
    }
    assertEquals(11, towns);
    assertEquals(61, fields);
  }
}
