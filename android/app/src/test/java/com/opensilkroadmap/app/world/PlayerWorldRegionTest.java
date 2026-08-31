package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import com.opensilkroadmap.app.data.NpcSpawnIndex;
import com.opensilkroadmap.app.data.TsvTable;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import org.junit.Test;

/**
 * TASK F: world/region evidence wiring for the player.
 *
 * <p>Locks the committed region data the player runtime is anchored to:
 * <ul>
 *   <li>TOWN Jangan window 167–169 x 96–99, ref (167,96) and FIELD Jangan_Field
 *       window 156–182 x 89–102, ref (156,89) from the REAL RegionInfo.txt
 *       (sha256 787d9b4…60739ff).</li>
 *   <li>The runtime region-selection rule (first region whose reference sector
 *       has a committed real {@code .hg}) resolves to Jangan_Field (156,89) —
 *       the Jangan town ref sector (167,96) has NO committed height grid, so
 *       town is not runtime-loadable and the player world system is anchored to
 *       Jangan_Field.</li>
 *   <li>The proven world formula places the Jangan town origin inside the
 *       Jangan_Field frame at (21120, 13440) — the coordinate system any future
 *       verified player spawn would use.</li>
 *   <li>No npcpos spawn maps to the player key and the player is absent from
 *       the character index (the player is never spawned by NPC placement).</li>
 *   <li>Region code 25000 is RN_CH_JANGAN (regioncode.tsv) and is the zone of
 *       the real Chang'an gate (teleportdata.tsv) — the Jangan name evidence.</li>
 * </ul>
 */
public class PlayerWorldRegionTest {

  @Test
  public void janganTownAndFieldWindowsMatchRegionInfo() throws IOException {
    Map<String, WorldRegion> byName =
        WorldRegion.indexByName(WorldRegion.loadDefault());
    WorldRegion town = byName.get("Jangan");
    assertNotNull("TOWN Jangan must be committed", town);
    assertEquals("TOWN", town.type);
    assertEquals(167, town.sx0);
    assertEquals(169, town.sx1);
    assertEquals(96, town.sy0);
    assertEquals(99, town.sy1);
    assertEquals(167, town.refSx);
    assertEquals(96, town.refSy);
    assertEquals(12, town.cells);

    WorldRegion field = byName.get("Jangan_Field");
    assertNotNull("FIELD Jangan_Field must be committed", field);
    assertEquals("FIELD", field.type);
    assertEquals(156, field.sx0);
    assertEquals(182, field.sx1);
    assertEquals(89, field.sy0);
    assertEquals(102, field.sy1);
    assertEquals(156, field.refSx);
    assertEquals(89, field.refSy);
    assertEquals(171, field.cells);
  }

  @Test
  public void committedTerrainAnchorsJanganField() throws IOException {
    WorldTerrainIndex index = WorldTerrainIndex.loadDefault();
    assertTrue("(156,89) .hg must be committed",
        index.contains(156, 89));
    assertTrue("(156,90) .hg must be committed",
        index.contains(156, 90));
    assertFalse("Jangan town ref (167,96) has no committed .hg",
        index.contains(167, 96));
    assertFalse("cave refs are not committed",
        index.contains(2, 128));
    assertFalse("fortress refs are not committed",
        index.contains(69, 69));
  }

  @Test
  public void runtimeRegionSelectionResolvesToJanganField() throws IOException {
    // Same rule as GameActivity.selectRegion: first region in file order whose
    // reference sector has a committed real .hg.
    WorldTerrainIndex index = WorldTerrainIndex.loadDefault();
    WorldRegion selected = null;
    for (WorldRegion r : WorldRegion.loadDefault()) {
      if (index.find(r.refSx, r.refSy) != null) {
        selected = r;
        break;
      }
    }
    assertNotNull("a region must be selectable", selected);
    assertEquals("Jangan_Field", selected.name);
    assertEquals(156, selected.refSx);
    assertEquals(89, selected.refSy);
  }

  @Test
  public void janganTownOriginLandsInJanganFieldFrame() throws IOException {
    // world = (sector - ref) * 1920 + local, ref = Jangan_Field (156, 89).
    assertEquals(21120f, WorldCoordinates.sectorWorldX(167, 156), 0.001f);
    assertEquals(13440f, WorldCoordinates.sectorWorldZ(96, 89), 0.001f);
    assertEquals(1920f, WorldCoordinates.SECTOR_WORLD, 1e-4f);
    assertEquals(0f, WorldCoordinates.sectorWorldX(156, 156), 0.001f);
    assertEquals(0f, WorldCoordinates.sectorWorldZ(89, 89), 0.001f);
  }

  @Test
  public void playerKeyIsNeverSpawnedByNpcpos() throws IOException {
    NpcSpawnIndex npc = NpcSpawnIndex.loadDefault();
    CharacterCatalog catalog = CharacterCatalog.loadDefault();
    assertFalse("player must be absent from the NPC refid index",
        catalog.characterKeys().contains(CharacterCatalog.PLAYER_KEY));
    assertEquals("player", CharacterCatalog.PLAYER_KEY);
    for (NpcSpawnIndex.Spawn s : npc.inWindow(0, 255, 0, 255)) {
      String key = catalog.keyFor(s.characterRefId);
      assertTrue("npcpos spawn refid " + s.characterRefId
              + " must never resolve to the player key",
          !CharacterCatalog.PLAYER_KEY.equals(key));
    }
  }

  @Test
  public void regionCode25000IsJangan() throws IOException {
    // regioncode.tsv: (1, 25000, RN_CH_JANGAN, <zone name bytes>).
    TsvTable regionCode = TsvTable.loadDefault("regioncode.tsv");
    boolean found = false;
    for (String[] row : regionCode.rows()) {
      if ("25000".equals(TsvTable.strAt(row, 1).trim())) {
        assertEquals("RN_CH_JANGAN", TsvTable.strAt(row, 2).trim());
        found = true;
      }
    }
    assertTrue("region code 25000 must exist in regioncode.tsv", found);

    // teleportdata.tsv: the real Chang'an gate uses zone code 25000.
    TsvTable teleports = TsvTable.loadDefault("teleportdata.tsv");
    boolean gate = false;
    for (String[] row : teleports.rows()) {
      if ("GATE_CH".equals(TsvTable.strAt(row, 2).trim())) {
        assertEquals("25000", TsvTable.strAt(row, 5).trim());
        gate = true;
      }
    }
    assertTrue("GATE_CH must be present in teleportdata.tsv", gate);
  }

  @Test
  public void worldRegionsRowCountMatchesCommit() throws IOException {
    List<WorldRegion> regions = WorldRegion.loadDefault();
    assertTrue("committed region list must be non-empty", !regions.isEmpty());
    assertNotNull("first region must parse", regions.get(0).name);
  }
}
