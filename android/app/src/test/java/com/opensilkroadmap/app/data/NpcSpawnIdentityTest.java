package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.IOException;
import java.io.StringReader;
import java.util.List;
import org.junit.Test;

/**
 * Locks optional {@link CharacterIdentityIndex} attach on
 * {@link NpcSpawnIndex}: every world spawn whose npcpos col0 refid uniquely
 * joins {@code character_identity.tsv} carries the proven NPC_/MOB_/
 * STRUCTURE_ code and .bsr (or {@code xxx}) path. Geometry is unchanged.
 * {@code parse} stays identity-null. Unknown refids fail closed.
 *
 * <p>Proven coverage:
 * <ul>
 *   <li>14800/14800 world spawns identified;</li>
 *   <li>Jangan 168x97 smith 2003 = NPC_CH_SMITH;</li>
 *   <li>156x90 bandit 1949 real .bsr; archer 1944 model xxx;</li>
 *   <li>7568 identified but never placed (no world spawn).</li>
 * </ul>
 */
public class NpcSpawnIdentityTest {

  @Test
  public void parseLeavesIdentityNull() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.loadGeometry();
    assertEquals(14800, idx.worldCount());
    assertEquals(0, idx.identifiedWorldCount());
    NpcSpawnIndex.Spawn first = idx.worldSpawn(0);
    assertNull(first.identity);
    assertNull(first.characterCode());
    assertNull(first.modelPath());
  }

  @Test
  public void loadDefaultIdentifiesEveryWorldSpawn() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.loadDefault();
    assertEquals(14800, idx.worldCount());
    assertEquals(3657, idx.dungeonCount());
    assertEquals(18457, idx.totalCount());
    assertEquals("14800 world spawns identified", 14800, idx.identifiedWorldCount());
  }

  @Test
  public void janganSmithIsNpcChSmith() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.loadDefault();
    NpcSpawnIndex.Spawn smith = null;
    for (NpcSpawnIndex.Spawn s : idx.inWindow(168, 168, 97, 97)) {
      if (s.characterRefId == 2003) {
        smith = s;
        break;
      }
    }
    assertNotNull(smith);
    assertEquals("NPC_CH_SMITH", smith.characterCode());
    assertEquals("npc\\npc\\chinashop_smith.bsr", smith.modelPath());
    assertEquals(332.73f, smith.localX, 0.01f);
    assertEquals(1406.7f, smith.localZ, 0.01f);
  }

  @Test
  public void banditHasBsrAndArcherIsXxx() throws IOException {
    NpcSpawnIndex idx = NpcSpawnIndex.loadDefault();
    List<NpcSpawnIndex.Spawn> window = idx.inWindow(156, 156, 90, 90);
    assertEquals(3, window.size());
    int bandits = 0;
    boolean archer = false;
    for (NpcSpawnIndex.Spawn s : window) {
      assertNotNull(s.identity);
      if (s.characterRefId == 1949) {
        assertEquals("MOB_CH_BANDIT", s.characterCode());
        assertEquals("mob\\china\\bandit.bsr", s.modelPath());
        bandits++;
      }
      if (s.characterRefId == 1944) {
        assertEquals("MOB_CH_BANDITARCHER_CLON", s.characterCode());
        assertEquals("xxx", s.modelPath());
        archer = true;
      }
    }
    assertEquals(2, bandits);
    assertTrue(archer);
  }

  @Test
  public void unknownRefidStaysNullWhenIdentityAttached() throws IOException {
    CharacterIdentityIndex ident = CharacterIdentityIndex.loadDefault();
    NpcSpawnIndex idx = new NpcSpawnIndex(
        TsvTable.parse("npcpos.tsv",
            new StringReader("999999\t22940\t1.0\t2.0\t3.0\n")),
        ident);
    assertEquals(1, idx.worldCount());
    assertEquals(0, idx.identifiedWorldCount());
    assertEquals(null, idx.worldSpawn(0).identity);
    assertEquals(null, idx.worldSpawn(0).characterCode());
    assertEquals(null, idx.worldSpawn(0).modelPath());
  }

  @Test
  public void spawnlessMerchantIsIdentifiedButNotPlaced() throws IOException {
    CharacterIdentityIndex ident = CharacterIdentityIndex.loadDefault();
    assertEquals("NPC_AM_SPECIAL", ident.code(7568));
    NpcSpawnIndex idx = NpcSpawnIndex.loadDefault();
    int placed = 0;
    for (int i = 0; i < idx.worldCount(); i++) {
      if (idx.worldSpawn(i).characterRefId == 7568) {
        placed++;
      }
    }
    assertEquals(0, placed);
  }
}
