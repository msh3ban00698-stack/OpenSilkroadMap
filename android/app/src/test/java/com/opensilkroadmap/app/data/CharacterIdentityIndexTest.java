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
 * Locks the spawn-scoped character identity index extracted from live
 * {@code characterdata_*.txt} using only the three Phase 29 proven anchors
 * (col1 refid, col2 code, col52 model path).
 *
 * <p>Proven coverage on the committed table:
 * <ul>
 *   <li>1181 identities: every distinct npcpos.tsv character_refid (1180)
 *       plus STORE_AM_SPECIAL / 7568;</li>
 *   <li>2003 = NPC_CH_SMITH / npc\\npc\\chinashop_smith.bsr;</li>
 *   <li>7568 = NPC_AM_SPECIAL (spawn-less merchant still identified);</li>
 *   <li>unknown refids fail closed.</li>
 * </ul>
 */
public class CharacterIdentityIndexTest {

  private CharacterIdentityIndex load() throws IOException {
    return CharacterIdentityIndex.loadDefault();
  }

  @Test
  public void coversEverySpawnRefidPlusSpawnlessMerchant() throws IOException {
    CharacterIdentityIndex idx = load();
    assertEquals("1180 spawn ids + 7568", 1181, idx.size());
    NpcPosTable npc = NpcPosTable.load();
    Set<Integer> refids = new HashSet<Integer>();
    for (int i = 0; i < npc.spawnCount(); i++) {
      refids.add(Integer.valueOf(npc.characterRefId(i)));
    }
    assertEquals(1180, refids.size());
    int missing = 0;
    for (Integer refid : refids) {
      if (idx.resolve(refid.intValue()) == null) {
        missing++;
      }
    }
    assertEquals("every npcpos refid resolves", 0, missing);
    assertNotNull("spawn-less merchant 7568 still identified", idx.resolve(7568));
  }

  @Test
  public void janganSmithAndSpawnlessSpecialAreProven() throws IOException {
    CharacterIdentityIndex idx = load();
    CharacterIdentityIndex.Identity smith = idx.resolve(2003);
    assertNotNull(smith);
    assertEquals("NPC_CH_SMITH", smith.code);
    assertEquals("npc\\npc\\chinashop_smith.bsr", smith.modelPath);
    CharacterIdentityIndex.Identity special = idx.resolve(7568);
    assertNotNull(special);
    assertEquals("NPC_AM_SPECIAL", special.code);
    assertTrue(special.modelPath.endsWith("AsiaMinor_spacialmerchant.bsr"));
  }

  @Test
  public void unknownRefidFailsClosed() throws IOException {
    CharacterIdentityIndex idx = load();
    assertNull(idx.resolve(-1));
    assertNull(idx.resolve(0));
    assertNull(idx.resolve(999999));
    assertNull(idx.code(999999));
    assertNull(idx.modelPath(999999));
  }

  @Test
  public void everyIdentityHasNpcMobOrStructureCodeAndBsrPath() throws IOException {
    CharacterIdentityIndex idx = load();
    ShopMerchantIndex shops = ShopMerchantIndex.loadDefault();
    int merchantsIdentified = 0;
    for (ShopMerchantIndex.Merchant m : shops.merchants()) {
      CharacterIdentityIndex.Identity id = idx.resolve(m.merchantRefId);
      assertNotNull("merchant " + m.storeCode + " / " + m.merchantRefId, id);
      assertTrue(id.code.startsWith("NPC_"));
      assertTrue(id.modelPath.toLowerCase().endsWith(".bsr"));
      merchantsIdentified++;
    }
    assertEquals(52, merchantsIdentified);
  }
}
