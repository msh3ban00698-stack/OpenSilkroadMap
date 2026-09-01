package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.opensilkroadmap.app.world.RegionResolver;
import java.io.IOException;
import java.util.List;
import java.util.TreeSet;
import org.junit.Test;

/**
 * Locks the teleport gate → zone placement pipeline: every gate's zone_id is a
 * packed region code resolved to sector + server zone + client RN_* name, or
 * fails closed.
 *
 * <p>Proven coverage on the committed tables:
 * <ul>
 *   <li>246 total gates → 144 world / 102 instance;</li>
 *   <li>104 world gates are server-attributed to one of 12 server zones (97
 *       distinct zone_ids → 97 distinct sectors); 35 world gates resolve in
 *       the client table only (name + sector proven, server zone UNKNOWN);
 *       5 world gates (zone_ids 0 and 22219) are in neither table and stay
 *       UNKNOWN;</li>
 *   <li>GATE_CH (row 0) zone_id 25000 → sector (168,97), server CHINA/zone
 *       1001, client RN_CH_JANGAN/장안, local (969, 0, 1369);</li>
 *   <li>zone 1001 holds 25 world gates; the RN_CH_JANGAN sector family holds
 *       5 gates;</li>
 *   <li>instance (zone_id &lt; 0) and unknown world codes fail closed with
 *       NaN placement.</li>
 * </ul>
 */
public class TeleportGateIndexTest {

  private TeleportGateIndex load() throws IOException {
    return new TeleportGateIndex(TeleportDataTable.load(),
        RegionResolver.loadDefault(), TeleportBuildingTable.loadDefault());
  }

  @Test
  public void gateCountsAreProven() throws IOException {
    TeleportDataTable raw = TeleportDataTable.load();
    assertEquals("246 total gate rows", 246, raw.gateCount());
    TeleportGateIndex idx = load();
    assertEquals("246 gates indexed", 246, idx.gateCount());
    assertEquals("144 world gates", 144, idx.worldCount());
    assertEquals("102 instance/dungeon gates", 102, idx.instanceCount());
  }

  @Test
  public void zoneCoverageIsProvenAndPartial() throws IOException {
    TeleportGateIndex idx = load();
    assertEquals("144 world gates", 144, idx.worldCount());
    assertEquals("104 server-attributed world gates", 104, idx.resolvedWorldCount());
    assertEquals("35 client-only world gates (name, no server zone)",
        35, idx.clientOnlyWorldCount());
    assertEquals("5 world gates fail closed (in neither table)",
        5, idx.unresolvedWorldCount());
    assertEquals("12 distinct server zones reachable by gate",
        12, idx.zones().size());
    assertEquals("reachable zones sorted",
        "[1001, 1005, 2001, 2002, 2004, 3001, 3002, 3003, 3004, 3005, "
            + "4001, 4002]",
        new TreeSet<String>(idx.zones()).toString());
  }

  @Test
  public void janganGateResolvesToProvenPlacement() throws IOException {
    TeleportGateIndex idx = load();
    TeleportGateIndex.Gate gate = idx.gate(0);
    assertEquals("row 0 is GATE_CH", "GATE_CH", gate.gateCode);
    assertEquals("gate id 2094", 2094, gate.gateId);
    assertEquals("zone code SN_ZONE_22001", "SN_ZONE_22001", gate.zoneCode);
    assertEquals("zone id is the RN_CH_JANGAN region code", 25000, gate.zoneId);
    assertTrue("world gate", gate.isWorld);
    assertEquals("local x from col6", 969.0f, gate.localX, 0.001f);
    assertEquals("height y from col7", 0.0f, gate.heightY, 0.001f);
    assertEquals("local z from col8", 1369.0f, gate.localZ, 0.001f);
    assertEquals("sector 168x97", 168, gate.sectorX());
    assertEquals("sector 168x97", 97, gate.sectorY());
    assertEquals("server zone 1001", "1001", gate.serverZone());
    assertEquals("server name CHINA", "CHINA", gate.serverName());
    assertEquals("client name code RN_CH_JANGAN", "RN_CH_JANGAN",
        gate.nameCode());
    assertEquals("localized name", "장안", gate.localizedName());
    assertEquals("world x relative to own sector", 969.0f,
        gate.worldX(168), 0.001f);
    assertEquals("world z relative to own sector", 1369.0f,
        gate.worldZ(97), 0.001f);
  }

  @Test
  public void buildingJoinGivesStoreAndNpcCodes() throws IOException {
    TeleportGateIndex idx = load();
    assertEquals("106 teleport buildings", 106, idx.buildings().buildingCount());
    int joined = 0;
    java.util.HashSet<Integer> seen = new java.util.HashSet<Integer>();
    for (int i = 0; i < idx.gateCount(); i++) {
      int gateId = idx.gate(i).gateId;
      if (seen.add(gateId) && idx.buildings().storeCode(gateId) != null) {
        joined++;
      }
    }
    assertEquals("101 / 135 distinct gate ids join the building table",
        101, joined);
    TeleportGateIndex.Gate gate = idx.gate(0);
    assertEquals("GATE_CH building store code", "STORE_CH_GATE", gate.storeCode);
    assertEquals("GATE_CH building npc code", "SN_NPC_CH_GATE", gate.npcCode);
    assertEquals("STORE_WC_GATE belongs to gate 2095", "STORE_WC_GATE",
        idx.buildings().storeCode(2095));
    assertEquals("SN_NPC_WC_GATE belongs to gate 2095", "SN_NPC_WC_GATE",
        idx.buildings().npcCode(2095));
    assertNull("unknown gate id fails closed", idx.buildings().storeCode(-1));
    assertNull("unknown gate id fails closed", idx.buildings().npcCode(999999));
  }

  @Test
  public void zone1001IsJanganAnchor() throws IOException {
    TeleportGateIndex idx = load();
    List<TeleportGateIndex.Gate> china = idx.gatesInZone("1001");
    assertEquals("zone 1001 holds 25 world gates", 25, china.size());
    int jangan = 0;
    for (TeleportGateIndex.Gate g : china) {
      assertTrue("zone gate must be a world row", g.isWorld);
      assertTrue("zone gate must resolve", g.region != null);
      if ("RN_CH_JANGAN".equals(g.nameCode())) {
        jangan++;
      }
    }
    assertEquals("RN_CH_JANGAN sector family holds 5 gates", 5, jangan);
  }

  @Test
  public void instanceAndUnknownGatesFailClosed() throws IOException {
    TeleportGateIndex idx = load();
    TeleportGateIndex.Gate instance = idx.gate(8);
    assertFalse("instance gate row 8", instance.isWorld);
    assertEquals("zone_id -32767", -32767, instance.zoneId);
    assertNull("instance region must fail closed", instance.region);
    assertEquals("sector -1", -1, instance.sectorX());
    assertNull("server zone must fail closed", instance.serverZone());
    assertNull("server name must fail closed", instance.serverName());
    assertNull("name code must fail closed", instance.nameCode());
    assertTrue("world x is NaN for instance", Float.isNaN(instance.worldX(0)));
    assertTrue("world z is NaN for instance", Float.isNaN(instance.worldZ(0)));

    TeleportGateIndex.Gate unlisted = idx.gate(30);
    assertTrue("row 30 is a world row", unlisted.isWorld);
    assertEquals("zone_id 0 is in neither table", 0, unlisted.zoneId);
    assertNull("unlisted region must fail closed", unlisted.region);
    assertNull("server zone must fail closed", unlisted.serverZone());
    assertTrue("world x is NaN for unlisted", Float.isNaN(unlisted.worldX(0)));

    int zone22219 = 0;
    for (int i = 0; i < idx.gateCount(); i++) {
      if (idx.gate(i).zoneId == 22219) {
        zone22219++;
        assertNull("zone 22219 must fail closed", idx.gate(i).region);
      }
    }
    assertEquals("zone_id 22219 gate fails closed", 1, zone22219);
    assertEquals("no gate attributed to zone 22219", 0,
        idx.gatesInZone("22219").size());
  }
}
