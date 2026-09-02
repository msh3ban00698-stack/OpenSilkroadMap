package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.opensilkroadmap.app.world.RegionResolver;
import java.io.IOException;
import java.util.List;
import java.util.TreeSet;
import org.junit.Test;

/**
 * Locks the concrete runtime teleport destination map: every
 * {@code teleportdata.tsv} gate and every {@code refoptionalteleport.tsv}
 * destination becomes one {@link TeleportDestinationMap.Entry} with its proven
 * placement, or fails closed. The map never invents a gate→destination link
 * (teleportlink.tsv semantics stay unproven and are not consumed).
 *
 * <p>Proven coverage on the committed tables:
 * <ul>
 *   <li>290 entries total → 246 gates / 44 optional destinations;</li>
 *   <li>179 entries resolve to a region (139 gates + 40 destinations); 111 fail
 *       closed (102 instance gates + 5 unlisted world gates + 4 instance
 *       destinations);</li>
 *   <li>12 server zones; zone 1001 holds 29 entries (25 gates + 4
 *       destinations);</li>
 *   <li>Jangan sector (168,97) holds 4 entries; the runtime-launch
 *       Jangan_Field window (156–182 × 89–102) holds 20 (16 gates + 4
 *       destinations);</li>
 *   <li>gate entry 0 = GATE_CH (gate_id 2094, STORE_CH_GATE/SN_NPC_CH_GATE)
 *       sector 168x97 zone 1001; destination "Chang'an" (index 26) sector
 *       168x97 zone 1001;</li>
 *   <li>instance and unlisted entries fail closed with -1 sector / null zone /
 *       NaN world coordinates.</li>
 * </ul>
 */
public class TeleportDestinationMapTest {

  private TeleportDestinationMap load() throws IOException {
    return new TeleportDestinationMap(
        new TeleportGateIndex(TeleportDataTable.load(),
            RegionResolver.loadDefault(), TeleportBuildingTable.loadDefault()),
        new OptionalTeleportIndex(OptionalTeleportTable.load(),
            RegionResolver.loadDefault()));
  }

  @Test
  public void mapCountsAreProven() throws IOException {
    TeleportDestinationMap map = load();
    assertEquals("290 entries", 290, map.entryCount());
    assertEquals("246 gate entries", 246, map.gateCount());
    assertEquals("44 destination entries", 44, map.destinationCount());
    assertEquals("179 entries resolve to a region", 179, map.resolvedEntryCount());
    assertEquals("111 entries fail closed", 111, map.unresolvedEntryCount());
  }

  @Test
  public void zoneCoverageMatchesGateAndDestinationAttribution() throws IOException {
    TeleportDestinationMap map = load();
    assertEquals("12 distinct server zones",
        12, map.zones().size());
    assertEquals("reachable zones sorted",
        "[1001, 1005, 2001, 2002, 2004, 3001, 3002, 3003, 3004, 3005, "
            + "4001, 4002]",
        new TreeSet<String>(map.zones()).toString());
    List<TeleportDestinationMap.Entry> zone1001 = map.inZone("1001");
    assertEquals("zone 1001 holds 29 entries", 29, zone1001.size());
    int gates = 0;
    for (TeleportDestinationMap.Entry e : zone1001) {
      if (e.kind == TeleportDestinationMap.Kind.GATE) {
        gates++;
      }
    }
    assertEquals("zone 1001 holds 25 gates", 25, gates);
  }

  @Test
  public void gateEntry0IsJanganGateCh() throws IOException {
    TeleportDestinationMap map = load();
    TeleportDestinationMap.Entry e = map.entry(0);
    assertEquals(TeleportDestinationMap.Kind.GATE, e.kind);
    assertEquals("teleportdata row 0", 0, e.sourceRow);
    assertEquals("GATE_CH", e.gateCode);
    assertEquals("gate id 2094", 2094, e.gateId);
    assertEquals("localized label", "장안", e.label);
    assertEquals("zone code SN_ZONE_22001", "SN_ZONE_22001", e.zoneCode);
    assertEquals("region id is the RN_CH_JANGAN region code", 25000, e.regionId);
    assertTrue("world gate", e.isWorld);
    assertEquals("local x from col6", 969.0f, e.localX, 0.001f);
    assertEquals("height y from col7", 0.0f, e.heightY, 0.001f);
    assertEquals("local z from col8", 1369.0f, e.localZ, 0.001f);
    assertEquals("sector 168x97", 168, e.sectorX());
    assertEquals("sector 168x97", 97, e.sectorY());
    assertEquals("server zone 1001", "1001", e.serverZone());
    assertEquals("server name CHINA", "CHINA", e.serverName());
    assertEquals("client name code RN_CH_JANGAN", "RN_CH_JANGAN", e.nameCode());
    assertEquals("localized name", "장안", e.localizedName());
    assertEquals("building store code", "STORE_CH_GATE", e.storeCode);
    assertEquals("building npc code", "SN_NPC_CH_GATE", e.npcCode);
    assertEquals("world x relative to own sector", 969.0f, e.worldX(168), 0.001f);
    assertEquals("world z relative to own sector", 1369.0f, e.worldZ(97), 0.001f);
  }

  @Test
  public void destinationsFollowGatesAndChanganResolves() throws IOException {
    TeleportDestinationMap map = load();
    TeleportDestinationMap.Entry first =
        map.entry(map.gateCount());
    assertEquals(TeleportDestinationMap.Kind.OPTIONAL_DESTINATION, first.kind);
    assertEquals("destination row 0", 0, first.sourceRow);
    assertEquals("destination index 1", 1, first.sourceIndex);
    assertEquals("Constantinople", first.label);
    assertEquals("region id 26959", 26959, first.regionId);

    TeleportDestinationMap.Entry changan = null;
    for (int i = 0; i < map.entryCount(); i++) {
      TeleportDestinationMap.Entry e = map.entry(i);
      if (e.kind == TeleportDestinationMap.Kind.OPTIONAL_DESTINATION
          && e.sourceIndex == 26) {
        changan = e;
        break;
      }
    }
    assertNotNull("destination index 26 present", changan);
    assertEquals("Chang'an", changan.label);
    assertEquals(25000, changan.regionId);
    assertEquals(995.0f, changan.localX, 0.001f);
    assertEquals(1132.0f, changan.localZ, 0.001f);
    assertEquals(168, changan.sectorX());
    assertEquals(97, changan.sectorY());
    assertEquals("1001", changan.serverZone());
    assertEquals("RN_CH_JANGAN", changan.nameCode());
    assertEquals("world x relative to own sector", 995.0f,
        changan.worldX(168), 0.001f);
    assertEquals("world z relative to own sector", 1132.0f,
        changan.worldZ(97), 0.001f);
    assertNull("destination has no gate code", changan.gateCode);
    assertNull("destination has no store code", changan.storeCode);
  }

  @Test
  public void janganWindowsMatchCommittedPlacement() throws IOException {
    TeleportDestinationMap map = load();
    List<TeleportDestinationMap.Entry> sector =
        map.inWindow(168, 168, 97, 97);
    assertEquals("Jangan sector holds 4 map points", 4, sector.size());
    int gates = 0;
    boolean changan = false;
    boolean gateCh = false;
    for (TeleportDestinationMap.Entry e : sector) {
      if (e.kind == TeleportDestinationMap.Kind.GATE) {
        gates++;
        if ("GATE_CH".equals(e.gateCode)) {
          gateCh = true;
        }
      }
      if ("Chang'an".equals(e.label)) {
        changan = true;
      }
    }
    assertEquals("3 gates in Jangan sector", 3, gates);
    assertTrue("GATE_CH in Jangan sector", gateCh);
    assertTrue("Chang'an in Jangan sector", changan);

    List<TeleportDestinationMap.Entry> field =
        map.inWindow(156, 182, 89, 102);
    assertEquals("Jangan_Field window holds 20 map points", 20, field.size());
    int fieldGates = 0;
    for (TeleportDestinationMap.Entry e : field) {
      if (e.kind == TeleportDestinationMap.Kind.GATE) {
        fieldGates++;
      }
    }
    assertEquals("16 gates in Jangan_Field window", 16, fieldGates);
    assertEquals("4 destinations in Jangan_Field window", 4, field.size() - fieldGates);
  }

  @Test
  public void instanceAndUnlistedEntriesFailClosed() throws IOException {
    TeleportDestinationMap map = load();
    TeleportDestinationMap.Entry instanceGate = map.entry(8);
    assertEquals(TeleportDestinationMap.Kind.GATE, instanceGate.kind);
    assertFalse("instance gate is not a world row", instanceGate.isWorld);
    assertEquals("instance zone_id -32767", -32767, instanceGate.regionId);
    assertNull("instance region must fail closed", instanceGate.region);
    assertEquals("sector -1", -1, instanceGate.sectorX());
    assertNull("server zone must fail closed", instanceGate.serverZone());
    assertTrue("world x is NaN for instance", Float.isNaN(instanceGate.worldX(0)));
    assertTrue("world z is NaN for instance", Float.isNaN(instanceGate.worldZ(0)));

    int instanceDests = 0;
    for (int i = 0; i < map.entryCount(); i++) {
      TeleportDestinationMap.Entry e = map.entry(i);
      if (e.kind == TeleportDestinationMap.Kind.OPTIONAL_DESTINATION
          && !e.isWorld) {
        instanceDests++;
        assertNull("instance destination must fail closed", e.region);
        assertEquals("sector -1", -1, e.sectorX());
        assertNull("server zone must fail closed", e.serverZone());
      }
    }
    assertEquals("4 instance destinations", 4, instanceDests);

    assertEquals("no gate attributed to zone 22219", 0,
        map.inZone("22219").size());
  }

  @Test
  public void twoArgConstructorLeavesLocalinfoNull() throws IOException {
    TeleportDestinationMap map = load();
    assertEquals("no localinfo without attach", 0, map.labeledEntryCount());
    assertNull("GATE_CH localinfo stays null", map.entry(0).localinfo);
    assertEquals("existing GATE_CH label unchanged", "장안", map.entry(0).label);
    TeleportDestinationMap.Entry changan = map.entry(map.gateCount() + 25);
    assertEquals("Chang'an", changan.label);
    assertNull(changan.localinfo);
  }

  @Test
  public void uniqueOnceLocalinfoAttachesWithoutReplacingLabel() throws IOException {
    TeleportDestinationMap map = new TeleportDestinationMap(
        new TeleportGateIndex(TeleportDataTable.load(),
            RegionResolver.loadDefault(), TeleportBuildingTable.loadDefault()),
        new OptionalTeleportIndex(OptionalTeleportTable.load(),
            RegionResolver.loadDefault()),
        WorldmapLocalinfoIndex.loadDefault());
    assertEquals("290 entries unchanged", 290, map.entryCount());
    assertEquals("61 unique-once SN_ZONE labels", 61, map.labeledEntryCount());
    TeleportDestinationMap.Entry gateCh = map.entry(0);
    assertEquals("existing GATE_CH label unchanged", "장안", gateCh.label);
    assertEquals("SN_ZONE_22001", gateCh.zoneCode);
    assertNotNull(gateCh.localinfo);
    assertEquals("중국", gateCh.localinfo.name);
    assertEquals("장 안", gateCh.localinfo.description);
    assertEquals(22001, gateCh.localinfo.zoneId);

    TeleportDestinationMap.Entry changan = null;
    for (int i = 0; i < map.entryCount(); i++) {
      TeleportDestinationMap.Entry e = map.entry(i);
      if (e.kind == TeleportDestinationMap.Kind.OPTIONAL_DESTINATION
          && e.sourceIndex == 26) {
        changan = e;
        break;
      }
    }
    assertNotNull(changan);
    assertEquals("Chang'an label unchanged", "Chang'an", changan.label);
    assertNotNull(changan.localinfo);
    assertEquals("중국", changan.localinfo.name);
    assertEquals("장 안", changan.localinfo.description);

    TeleportDestinationMap.Entry instanceGate = map.entry(8);
    assertNull("unmatched SN_ZONE stays unlabeled", instanceGate.localinfo);
  }
}
