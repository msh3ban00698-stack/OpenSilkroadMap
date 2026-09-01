package com.opensilkroadmap.app.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.HashSet;
import java.util.Set;
import org.junit.Test;

/**
 * Tests for the Phase 12 Android data layer. Every assertion is against the
 * REAL committed assets under {@code src/main/assets/game/textdata/} (derived
 * from Media.pk2 /server_dep/silkroad/textdata/, see TEXTDATA_CATALOG.tsv).
 */
public class TextDataTablesTest {

  @Test
  public void npcposLoadsAllRealSpawns() throws Exception {
    NpcPosTable npc = NpcPosTable.load();
    assertEquals(18457, npc.spawnCount());
    assertEquals(2023, npc.characterRefId(0));
    assertEquals(25257, npc.regionCode(0));
    assertEquals(659.74f, npc.localX(0), 0.001f);
    assertEquals(0f, npc.heightY(0), 0.001f);
    assertEquals(981.13f, npc.localZ(0), 0.001f);
  }

  @Test
  public void npcposCharacterRefIdsRepeatAcrossSpawns() throws Exception {
    // Phase 13 corrected col0 = character_refid (joins characterdata_*.txt
    // col1, 1180/1180 distinct across all 18,457 spawn rows). A spawn-id column
    // does not exist; the old Phase 12 spawnId interpretation was disproven.
    NpcPosTable npc = NpcPosTable.load();
    Set<Integer> refids = new HashSet<>();
    for (int i = 0; i < npc.spawnCount(); i++) {
      refids.add(npc.characterRefId(i));
    }
    assertTrue("character refids repeat across spawns (1180 distinct)",
        refids.size() == 1180);
  }

  @Test
  public void npcposRegionCodesPackBySectorFormula() throws Exception {
    NpcPosTable npc = NpcPosTable.load();
    int world = 0;
    int instances = 0;
    for (int i = 0; i < npc.spawnCount(); i++) {
      int region = npc.regionCode(i);
      if (region < 0) {
        instances++;
      } else {
        world++;
        int[] s = com.opensilkroadmap.app.world.WorldCoordinates.unpackRegion(region);
        assertEquals(region, com.opensilkroadmap.app.world.WorldCoordinates.packRegion(s[0], s[1]));
      }
    }
    assertEquals(14800, world);
    assertEquals(3657, instances);
  }

  @Test
  public void npcposHeightYIsMostlyNonZero() throws Exception {
    // Real data: height_y (col3) is an elevation, not ~0; only 537/18,457
    // rows are exactly zero. The Phase 12 "~0 across records" claim is
    // disproven by the committed table.
    NpcPosTable npc = NpcPosTable.load();
    int exactZero = 0;
    for (int i = 0; i < npc.spawnCount(); i++) {
      if (Math.abs(npc.heightY(i)) < 0.01f) {
        exactZero++;
      }
    }
    assertEquals("537 exact-zero height rows", 537, exactZero);
  }

  @Test
  public void levelDataHasVerifiedLevelColumn() throws Exception {
    LevelDataTable levels = LevelDataTable.load();
    assertEquals(150, levels.levelCount());
    assertEquals(10, levels.columnCount());
    assertEquals(1, levels.level(0));
    assertEquals(150, levels.level(149));
    assertEquals(70875, levels.rawColumn(0, 6));
  }

  @Test
  public void levelGoldHasVerifiedLevelColumn() throws Exception {
    LevelGoldTable gold = LevelGoldTable.load();
    assertEquals(140, gold.levelCount());
    assertEquals(1, gold.level(0));
    assertEquals(140, gold.level(139));
  }

  @Test
  public void teleportDataHasVerifiedGateAndZoneColumns() throws Exception {
    TeleportDataTable tp = TeleportDataTable.load();
    assertEquals(246, tp.gateCount());
    assertEquals("GATE_CH", tp.gateCode(0));
    assertEquals(2094, tp.gateId(0));
    assertEquals("SN_ZONE_22001", tp.zoneCode(0));
    assertEquals(25000, tp.zoneId(0));
  }

  @Test
  public void refShopGoodsHasVerifiedColumns() throws Exception {
    RefShopGoodsTable goods = RefShopGoodsTable.load();
    assertEquals(2282, goods.goodsCount());
    assertEquals(15, goods.shopId(0));
    assertEquals("MALL_ARCHEMY_ASTRAL", goods.categoryCode(0));
    assertEquals("PACKAGE_ITEM_ETC_ARCHEMY_MAGICSTONE_ASTRAL_01", goods.itemCode(0));
  }

  @Test
  public void worldMapInstanceHasVerifiedRegionCells() throws Exception {
    WorldMapInstanceTable wmi = WorldMapInstanceTable.load();
    assertEquals(23, wmi.instanceCount());
    assertEquals("Worldmap_THIEFTOWN", wmi.code(0));
    assertEquals(182, wmi.regionCellX(0));
    assertEquals(96, wmi.regionCellY(0));
    assertEquals("ThiefTown", "ThiefTown");
  }

  @Test
  public void questDataHasVerifiedQuestCodes() throws Exception {
    QuestDataTable q = QuestDataTable.load();
    assertEquals(1004, q.questCount());
    assertEquals("QEVENT_GUIDE", q.questCode(0));
  }

  @Test
  public void worldMapInstanceNameIsUtf8Korean() throws Exception {
    WorldMapInstanceTable wmi = WorldMapInstanceTable.load();
    assertEquals("\ub3c4\uc801\ub9c8\uc744", wmi.name(0));
  }
}
