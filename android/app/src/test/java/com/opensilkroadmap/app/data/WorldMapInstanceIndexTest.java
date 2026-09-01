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
 * Locks the instance navigation pipeline: every {@code Worldmap_*} instance
 * resolves to its proven anchor sector (verified 23/23 join to
 * {@code regions.tsv} cells) and the containing region section.
 *
 * <p>Proven coverage on the committed tables:
 * <ul>
 *   <li>23 instance maps, each anchored at a sector that exists in the region
 *       catalog (23/23) — e.g. ThiefTown 182:96, JanganCave456 2:128,
 *       Jangan_Field 182:89, Roc_Mountain 189:100;</li>
 *   <li>anchor world positions use the proven 1920-unit sector formula;</li>
 *   <li>local position columns (cols 4-10) have no verified semantics and stay
 *       UNKNOWN; unknown codes fail closed.</li>
 * </ul>
 */
public class WorldMapInstanceIndexTest {

  private WorldMapInstanceIndex load() throws IOException {
    return WorldMapInstanceIndex.loadDefault();
  }

  @Test
  public void allInstancesResolveToRegionSections() throws IOException {
    WorldMapInstanceIndex idx = load();
    assertEquals("23 instance maps", 23, idx.instanceCount());
    assertEquals("23/23 anchored in a known region section",
        23, idx.regionResolvedCount());
    Set<String> codes = new HashSet<String>();
    for (WorldMapInstanceIndex.Instance in : idx.instances()) {
      codes.add(in.code);
      assertTrue("instance name must be non-empty", !in.name.isEmpty());
      assertNotNull("instance must have a resolved region", in.region);
    }
    assertEquals("every instance carries a unique Worldmap_* code",
        23, codes.size());
  }

  @Test
  public void thiefTownResolvesToAnchorAndRegion() throws IOException {
    WorldMapInstanceIndex.Instance town = load().resolve("Worldmap_THIEFTOWN");
    assertEquals("도적마을", town.name);
    assertEquals("anchor sector 182:96", 182, town.cellX);
    assertEquals("anchor sector 182:96", 96, town.cellY);
    assertEquals("region section ThiefTown", "ThiefTown", town.regionName());
    assertEquals("world anchor x vs Jangan_Field ref 156", 49920.0f,
        town.worldAnchorX(156), 0.001f);
    assertEquals("world anchor y vs Jangan_Field ref 89", 13440.0f,
        town.worldAnchorY(89), 0.001f);
  }

  @Test
  public void dungeonInstancesResolveToTheirFieldRegions() throws IOException {
    WorldMapInstanceIndex idx = load();
    WorldMapInstanceIndex.Instance donwhang = idx.resolve("Worldmap_DONWHANG");
    assertEquals("돈황석굴던전", donwhang.name);
    assertEquals("anchor sector 1:128", 1, donwhang.cellX);
    assertEquals("anchor sector 1:128", 128, donwhang.cellY);
    assertEquals("region section DonwhangCave", "DonwhangCave",
        donwhang.regionName());

    WorldMapInstanceIndex.Instance jinsi = idx.resolve("Worldmap_JINSI");
    assertEquals("진시황릉던전", jinsi.name);
    assertEquals("anchor sector 2:128", 2, jinsi.cellX);
    assertEquals("anchor sector 2:128", 128, jinsi.cellY);
    assertEquals("region section JanganCave456", "JanganCave456",
        jinsi.regionName());

    WorldMapInstanceIndex.Instance pharaoh = idx.resolve("Worldmap_PHARAOH_1");
    assertEquals("파라오 하급", pharaoh.name);
    assertEquals("anchor sector 191:113", 191, pharaoh.cellX);
    assertEquals("anchor sector 191:113", 113, pharaoh.cellY);
    assertEquals("region section Pharaoh_Novice", "Pharaoh_Novice",
        pharaoh.regionName());
  }

  @Test
  public void unknownCodeFailsClosed() throws IOException {
    WorldMapInstanceIndex idx = load();
    assertNull("unknown code fails closed", idx.resolve("Worldmap_NOPE"));
    assertNull("empty code fails closed", idx.resolve(""));
  }
}
