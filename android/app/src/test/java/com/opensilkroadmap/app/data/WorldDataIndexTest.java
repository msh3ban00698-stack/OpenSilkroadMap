package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import org.junit.Test;

/**
 * Locks the instance-world catalog: every row of the committed
 * {@code gameworlddata.tsv} exposes a unique numeric world id and an
 * {@code INS_*} code, and the proven {@code code}+{@code group} pair matches the
 * server {@code _RefInstance_World} seed rows byte-for-byte (verified
 * independently in {@code scripts/test_worlddata_bak_concordance.py}).
 *
 * <p>Proven coverage on the committed tables:
 * <ul>
 *   <li>115 instance worlds with unique sequential ids 1..115;</li>
 *   <li>84 worlds carry a real {@code GROUP_*} code (74 distinct), 31 hold the
 *       {@code xxx} placeholder and report no group;</li>
 *   <li>fortress worlds: WorldID 2 = {@code INS_FORT_JA} /
 *       {@code GROUP_FORTRESS_JANGAN}, WorldID 3 = {@code INS_FORT_DW} /
 *       {@code GROUP_FORTRESS_DONWHANG} (backup concordant);</li>
 *   <li>world id semantics are PARTIAL (opaque key only); unknown ids and codes
 *       fail closed.</li>
 * </ul>
 */
public class WorldDataIndexTest {

  private WorldDataIndex load() throws IOException {
    return WorldDataIndex.loadDefault();
  }

  @Test
  public void allWorldsHaveUniqueSequentialIdsAndCodes() throws IOException {
    WorldDataIndex idx = load();
    assertEquals("115 instance worlds", 115, idx.worldCount());
    Set<Integer> ids = new HashSet<Integer>();
    Set<String> codes = new HashSet<String>();
    int maxId = 0;
    for (WorldDataIndex.World w : idx.worlds()) {
      ids.add(w.worldId);
      codes.add(w.code);
      assertTrue("code must be a non-empty INS_* code", w.code.startsWith("INS_"));
      maxId = Math.max(maxId, w.worldId);
    }
    assertEquals("ids unique", 115, ids.size());
    assertEquals("codes unique", 115, codes.size());
    assertEquals("ids are 1..115", 115, maxId);
  }

  @Test
  public void groupCountMatchesCommittedCatalog() throws IOException {
    WorldDataIndex idx = load();
    assertEquals("74 distinct GROUP_* codes", 74, idx.groupCount());
  }

  @Test
  public void fortressWorldsCarryServerConcordantGroups() throws IOException {
    WorldDataIndex idx = load();
    WorldDataIndex.World jangan = idx.byWorldId(2);
    assertNotNull(jangan);
    assertEquals("INS_FORT_JA", jangan.code);
    assertEquals("GROUP_FORTRESS_JANGAN", jangan.group);
    assertTrue(jangan.hasGroup());

    WorldDataIndex.World dw = idx.byCode("INS_FORT_DW");
    assertNotNull("code lookup by INS_FORT_DW", dw);
    assertEquals(3, dw.worldId);
    assertEquals("GROUP_FORTRESS_DONWHANG", dw.group);

    WorldDataIndex.World ht = idx.byWorldId(4);
    assertEquals("GROUP_FORTRESS_HOTAN", ht.group);
    WorldDataIndex.World ct = idx.byWorldId(5);
    assertEquals("GROUP_FORTRESS_CONSTANTINOPLE", ct.group);
  }

  @Test
  public void placeholderRowsReportNoGroup() throws IOException {
    WorldDataIndex idx = load();
    WorldDataIndex.World def = idx.byWorldId(1);
    assertNotNull(def);
    assertEquals("INS_DEFAULT", def.code);
    assertFalse("xxx placeholder carries no group", def.hasGroup());
    assertEquals("group is empty for placeholder", "", def.group);
  }

  @Test
  public void unknownKeysFailClosed() throws IOException {
    WorldDataIndex idx = load();
    assertNull("unknown world id fails closed", idx.byWorldId(99999));
    assertNull("unknown code fails closed", idx.byCode("INS_NOPE"));
    assertNull("empty code fails closed", idx.byCode(""));
  }
}
