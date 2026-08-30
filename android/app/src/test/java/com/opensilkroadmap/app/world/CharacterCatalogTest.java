package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.StringReader;
import org.junit.Test;

public class CharacterCatalogTest {
  private static final String TSV =
      "refid\tkey\tvariant\tstatus\tspawn_count\n"
          + "1949\tmob_china_bandit\t0\tPROVEN\t60\n"
          + "26738\tmob_sd_seth\t0\tPROVEN\t3\n"
          + "26738\tmob_sd_seth_t2\t1\tPROVEN\t3\n"
          + "12345\tart_guild_pulley\t0\tUNKNOWN\t1\n";

  @Test
  public void keyFor_primary_variant() throws Exception {
    CharacterCatalog c = CharacterCatalog.parse(new StringReader(TSV));
    assertEquals("mob_china_bandit", c.keyFor(1949));
    assertEquals("mob_sd_seth", c.keyFor(26738));
  }

  @Test
  public void keyFor_unknown_refid_is_null() throws Exception {
    CharacterCatalog c = CharacterCatalog.parse(new StringReader(TSV));
    assertNull(c.keyFor(0));
  }

  @Test
  public void playerKey_and_keys() throws Exception {
    CharacterCatalog c = CharacterCatalog.parse(new StringReader(TSV));
    assertEquals("player", c.playerKey());
    assertTrue(c.characterKeys().contains("mob_china_bandit"));
    assertEquals(4, c.count());
  }
}
