package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.opensilkroadmap.app.world.RegionResolver;
import java.io.IOException;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.Test;

/**
 * Locks the NPC spawn → zone pipeline: every world spawn's packed region code
 * is attributed to its proven server zone (or fails closed).
 *
 * <p>Proven coverage on the committed tables:
 * <ul>
 *   <li>18,457 total spawn rows → 14,800 world / 3,657 instance;</li>
 *   <li>11,597 world spawns resolve to one of the 13 server zones; the
 *       remaining 3,203 world spawns' region codes are absent from the zone
 *       catalog and stay UNKNOWN (never invented);</li>
 *   <li>zone 1001 (CHINA) holds 762 world spawns across 85 distinct NPC refids
 *       — the same anchor as RN_CH_JANGAN;</li>
 *   <li>instance and unknown world codes fail closed at the region level.</li>
 * </ul>
 */
public class SpawnZoneIndexTest {

  private SpawnZoneIndex load() throws IOException {
    return new SpawnZoneIndex(NpcSpawnIndex.loadDefault(), RegionResolver.loadDefault());
  }

  @Test
  public void worldAndInstanceSpawnCounts() throws IOException {
    NpcSpawnIndex index = NpcSpawnIndex.loadDefault();
    assertEquals("18,457 total spawn rows", 18457, index.totalCount());
    assertEquals("14,800 world rows", 14800, index.worldCount());
    assertEquals("3,657 instance/dungeon rows", 3657, index.dungeonCount());
  }

  @Test
  public void zoneCoverageIsProvenAndPartial() throws IOException {
    SpawnZoneIndex idx = load();
    assertEquals("14,800 world spawns", 14800, idx.worldCount());
    assertEquals("11,597 resolve to a known zone", 11597, idx.zoneResolvedCount());
    assertEquals("3,203 world spawns fail closed (zone UNKNOWN)",
        3203, idx.zoneUnknownCount());
    assertEquals("13 distinct server zones", 13, idx.zones().size());
  }

  @Test
  public void zone1001IsJanganAnchor() throws IOException {
    SpawnZoneIndex idx = load();
    List<NpcSpawnIndex.Spawn> china = idx.spawnsInZone("1001");
    assertEquals("zone 1001 has 762 world spawns", 762, china.size());
    Set<Integer> refids = new HashSet<Integer>();
    for (NpcSpawnIndex.Spawn s : china) {
      refids.add(s.characterRefId);
    }
    assertEquals("zone 1001 covers 85 distinct NPC refids", 85, refids.size());
    assertEquals("zone 1001 server name is CHINA",
        "CHINA", idx.serverNameOfRegion(25000));
    assertEquals("RN_CH_JANGAN name code resolves through zone 1001",
        "RN_CH_JANGAN", idx.nameCodeOfRegion(25000));
  }

  @Test
  public void everyResolvedZoneSpawnHasNonNegativeRegion() throws IOException {
    SpawnZoneIndex idx = load();
    for (String zone : idx.zones()) {
      for (NpcSpawnIndex.Spawn s : idx.spawnsInZone(zone)) {
        assertTrue("zone spawn must be a world row", s.isWorld);
        assertTrue("zone spawn region code must be non-negative", s.regionCode >= 0);
      }
    }
  }

  @Test
  public void unknownAndInstanceRegionsFailClosed() throws IOException {
    SpawnZoneIndex idx = load();
    assertNull("instance region must fail closed", idx.zoneIdOfRegion(-32760));
    assertNull("unlisted world region must fail closed", idx.zoneIdOfRegion(22217));
    assertNull("server name must fail closed with the zone",
        idx.serverNameOfRegion(22217));
    assertNull("name code must fail closed with the zone",
        idx.nameCodeOfRegion(-1));
  }
}
