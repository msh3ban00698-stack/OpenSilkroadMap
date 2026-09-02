package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.IOException;
import org.junit.Test;

/**
 * Locks the fail-closed unique-once SN_ZONE index over committed
 * {@code worldmap_localinfo.tsv}: only SN_ZONE_* codes that appear exactly
 * once become a label (col4 name / col5 description). Duplicate SN_ZONE
 * codes, non-SN_ZONE col3 values, and unknown codes resolve to {@code null}.
 *
 * <p>Proven coverage on the committed table:
 * <ul>
 *   <li>1116 rows; 353 unique-once {@code SN_ZONE_*} labels;</li>
 *   <li>18 duplicate SN_ZONE codes (97 rows) fail closed, including
 *       {@code SN_ZONE_21835_5} (x12) and {@code SN_ZONE_25800_8}
 *       (disagreeing names);</li>
 *   <li>{@code SN_ZONE_22001} → name 중국 / description 장 안;</li>
 *   <li>29/246 teleportdata rows and 32/44 optional destinations join
 *       uniquely; missing codes stay unlabeled.</li>
 * </ul>
 */
public class WorldmapLocalinfoIndexTest {

  private WorldmapLocalinfoIndex load() throws IOException {
    return WorldmapLocalinfoIndex.loadDefault();
  }

  @Test
  public void uniqueOnceCountIsProven() throws IOException {
    WorldmapLocalinfoIndex idx = load();
    assertEquals("353 unique-once SN_ZONE labels", 353, idx.size());
  }

  @Test
  public void janganWorldmapLabelIsUnique() throws IOException {
    WorldmapLocalinfoIndex idx = load();
    WorldmapLocalinfoIndex.Label lab = idx.resolve("SN_ZONE_22001");
    assertNotNull(lab);
    assertEquals(22001, lab.zoneId);
    assertEquals("SN_ZONE_22001", lab.zoneCode);
    assertEquals("중국", lab.name);
    assertEquals("장 안", lab.description);
  }

  @Test
  public void duplicateAndUnknownCodesFailClosed() throws IOException {
    WorldmapLocalinfoIndex idx = load();
    assertNull(idx.resolve("SN_ZONE_21835_5"));
    assertNull(idx.resolve("SN_ZONE_25800_8"));
    assertNull(idx.resolve("SN_ZONE_DOES_NOT_EXIST"));
    assertNull(idx.resolve("xxx"));
    assertNull(idx.resolve(null));
    assertNull(idx.resolve(""));
    assertNull(idx.resolve("interface\\worldmap\\map\\xy_gate.ddj"));
    assertNull(idx.resolve("STORE_DH_GATE_OUT"));
    assertNull(idx.resolve("SN_NPC_CH_COMMERCE1"));
    assertNull(idx.resolve("SN_JUPITER_B_1_GATE_1ATE"));
  }

  @Test
  public void teleportUniqueJoinCoverage() throws IOException {
    WorldmapLocalinfoIndex idx = load();
    TeleportDataTable gates = TeleportDataTable.load();
    int labeledGates = 0;
    for (int i = 0; i < gates.gateCount(); i++) {
      if (idx.resolve(gates.zoneCode(i)) != null) {
        labeledGates++;
      }
    }
    assertEquals("29 unique-once gate rows", 29, labeledGates);
    assertEquals(246, gates.gateCount());

    OptionalTeleportTable dests = OptionalTeleportTable.load();
    int labeledDests = 0;
    for (int i = 0; i < dests.destinationCount(); i++) {
      if (idx.resolve(dests.zoneCode(i)) != null) {
        labeledDests++;
      }
    }
    assertEquals("32 unique-once destination rows", 32, labeledDests);
    assertEquals(44, dests.destinationCount());
  }

  @Test
  public void smithPoiIsNotTeleportRegionId() throws IOException {
    WorldmapLocalinfoIndex idx = load();
    WorldmapLocalinfoIndex.Label lab = idx.resolve("SN_ZONE_11001");
    assertNotNull(lab);
    assertEquals("장안", lab.name);
    assertEquals("대장간", lab.description);
    assertTrue("localinfo zone_id is not GATE_CH region 25000",
        lab.zoneId != 25000);
  }
}
