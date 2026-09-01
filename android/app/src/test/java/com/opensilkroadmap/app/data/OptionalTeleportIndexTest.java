package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.opensilkroadmap.app.world.RegionResolver;
import java.io.IOException;
import java.util.List;
import org.junit.Test;

/**
 * Locks the optional teleport destination → zone placement pipeline: every
 * world destination's region_id is a packed region code resolved to sector +
 * server zone + client RN_* name, or fails closed.
 *
 * <p>Proven coverage on the committed tables:
 * <ul>
 *   <li>44 destinations total → 40 world / 4 instance;</li>
 *   <li>40/40 world region_ids resolve in the client table; 35/40 are
 *       server-attributed, 5 are client-only (Baghdad, Phantom Desert, Arabian
 *       Coast, Sky Temple A/B) and stay UNKNOWN for server zone;</li>
 *   <li>all 40 world rows have local x/z within [0, 1920);</li>
 *   <li>"Chang'an" (index 26) region 25000 → sector (168,97), server CHINA/zone
 *       1001, client RN_CH_JANGAN/장안, local (995, -32, 1132);</li>
 *   <li>instance rows (Dungeon Cave 1F, Jinshi 2F/3F/4F) fail closed with NaN
 *       placement.</li>
 * </ul>
 */
public class OptionalTeleportIndexTest {

  private OptionalTeleportIndex load() throws IOException {
    return new OptionalTeleportIndex(OptionalTeleportTable.load(),
        RegionResolver.loadDefault());
  }

  @Test
  public void destinationCountsAreProven() throws IOException {
    OptionalTeleportTable raw = OptionalTeleportTable.load();
    assertEquals("44 destination rows", 44, raw.destinationCount());
    OptionalTeleportIndex idx = load();
    assertEquals("44 destinations indexed", 44, idx.destinationCount());
    assertEquals("40 world destinations", 40, idx.worldCount());
    assertEquals("4 instance destinations", 4, idx.instanceCount());
    assertEquals("35 server-attributed world destinations", 35,
        idx.resolvedWorldCount());
    assertEquals("5 client-only world destinations", 5,
        idx.clientOnlyWorldCount());
  }

  @Test
  public void worldRowsHaveSectorLocalCoords() throws IOException {
    OptionalTeleportIndex idx = load();
    List<OptionalTeleportIndex.Destination> world = idx.world();
    assertEquals("40 world destinations", 40, world.size());
    for (OptionalTeleportIndex.Destination d : world) {
      assertTrue("world x in [0,1920): " + d.nameLabel,
          d.localX >= 0.0f && d.localX < 1920.0f);
      assertTrue("world z in [0,1920): " + d.nameLabel,
          d.localZ >= 0.0f && d.localZ < 1920.0f);
      assertTrue("world destination resolves (client)",
          d.region != null);
      assertTrue("world x finite", !Float.isNaN(d.worldX(156)));
      assertTrue("world z finite", !Float.isNaN(d.worldZ(89)));
    }
  }

  @Test
  public void changanDestinationResolvesToProvenPlacement() throws IOException {
    OptionalTeleportIndex idx = load();
    OptionalTeleportIndex.Destination d = idx.destination(25);
    assertEquals("row 25 index 26", 26, d.index);
    assertEquals("name label", "Chang'an", d.nameLabel);
    assertEquals("zone code SN_ZONE_22001", "SN_ZONE_22001", d.zoneCode);
    assertEquals("region id is the RN_CH_JANGAN region code", 25000, d.regionId);
    assertTrue("world destination", d.isWorld);
    assertEquals("local x from col5", 995.0f, d.localX, 0.001f);
    assertEquals("height y from col6", -32.0f, d.heightY, 0.001f);
    assertEquals("local z from col7", 1132.0f, d.localZ, 0.001f);
    assertEquals("sector 168x97", 168, d.sectorX());
    assertEquals("sector 168x97", 97, d.sectorY());
    assertEquals("server zone 1001", "1001", d.serverZone());
    assertEquals("server name CHINA", "CHINA", d.serverName());
    assertEquals("client name code RN_CH_JANGAN", "RN_CH_JANGAN", d.nameCode());
    assertEquals("localized name", "장안", d.localizedName());
    assertEquals("world x relative to own sector", 995.0f,
        d.worldX(168), 0.001f);
    assertEquals("world z relative to own sector", 1132.0f,
        d.worldZ(97), 0.001f);
  }

  @Test
  public void clientOnlyDestinationsResolveNameButNotServerZone()
      throws IOException {
    OptionalTeleportIndex idx = load();
    int clientOnly = 0;
    for (int i = 0; i < idx.destinationCount(); i++) {
      OptionalTeleportIndex.Destination d = idx.destination(i);
      if (!d.isWorld || d.serverZone() != null) {
        continue;
      }
      clientOnly++;
      assertNull("server zone fails closed for " + d.nameLabel, d.serverZone());
      assertNull("server name fails closed for " + d.nameLabel, d.serverName());
      assertTrue("client name still resolves for " + d.nameLabel,
          d.nameCode() != null);
    }
    assertEquals("5 client-only world destinations", 5, clientOnly);
    assertEquals("Baghdad resolves as RN_ARABIA_TOWN", "RN_ARABIA_TOWN",
        nameOf(idx, 22618));
    assertEquals("Sky Temple A keeps its client zone code", "RN_OTHER_SKYTEMPLE_A_01",
        zoneOf(idx, 24797));
  }

  @Test
  public void instanceDestinationsFailClosed() throws IOException {
    OptionalTeleportIndex idx = load();
    int instances = 0;
    for (int i = 0; i < idx.destinationCount(); i++) {
      OptionalTeleportIndex.Destination d = idx.destination(i);
      if (d.isWorld) {
        continue;
      }
      instances++;
      assertFalse("instance destination", d.isWorld);
      assertTrue("negative region id", d.regionId < 0);
      assertNull("instance region must fail closed", d.region);
      assertEquals("sector -1", -1, d.sectorX());
      assertNull("server zone must fail closed", d.serverZone());
      assertNull("name code must fail closed", d.nameCode());
      assertTrue("world x is NaN for instance", Float.isNaN(d.worldX(0)));
      assertTrue("world z is NaN for instance", Float.isNaN(d.worldZ(0)));
    }
    assertEquals("4 instance destinations", 4, instances);
    assertEquals("Dunhuang Cave 1F zone code", "SN_ZONE_23002",
        zoneOf(idx, -32767));
  }

  private static String nameOf(OptionalTeleportIndex idx, int regionId) {
    for (int i = 0; i < idx.destinationCount(); i++) {
      if (idx.destination(i).regionId == regionId) {
        return idx.destination(i).nameCode();
      }
    }
    return null;
  }

  private static String zoneOf(OptionalTeleportIndex idx, int regionId) {
    for (int i = 0; i < idx.destinationCount(); i++) {
      if (idx.destination(i).regionId == regionId) {
        return idx.destination(i).zoneCode;
      }
    }
    return null;
  }
}
