package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import com.opensilkroadmap.app.data.TeleportGateIndex;
import com.opensilkroadmap.app.data.WorldMapInstanceIndex;
import com.opensilkroadmap.app.world.CharacterMeshIndex;
import com.opensilkroadmap.app.world.MeshObjectIndex;
import com.opensilkroadmap.app.world.NativeWorldRenderer;
import com.opensilkroadmap.app.world.TerrainHeightGrid;
import com.opensilkroadmap.app.world.WorldTerrainSet;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Instrumented test for the Phase 15 native world runtime host activity.
 *
 * <p>Launches {@link GameActivity} on a device/emulator and verifies the
 * activity renders the verified multi-sector world through
 * {@link NativeWorldRenderer}. The first region whose reference sector has a
 * committed {@code .hg} is Jangan_Field (ref sector 156x89); the activity must
 * load every committed sector in that window (156x89, 156x90) as real 97x97
 * VSHG height fields, not generated geometry.
 *
 * <p>Phase 17 additionally verifies the real object mesh overlay: 32 real
 * {@code .o2} placements resolve to real BMS mesh parts attached to the
 * renderer (not markers).
 *
 * <p>These tests execute on an Android device/emulator only; in this
 * environment (no JDK/Android SDK) they are NOT EXECUTED.
 */
@RunWith(AndroidJUnit4.class)
public class GameActivityTest {

  @Test
  public void rendersVerifiedMultiSectorWorld() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            NativeWorldRenderer world = activity.worldRenderer();
            assertNotNull(world);
            WorldTerrainSet set = world.world();
            assertNotNull(set);
            assertEquals(2, set.sectorCount());
            assertEquals(1920.0f, set.width(), 1e-3f);
            assertEquals(3840.0f, set.height(), 1e-3f);
          });
    }
  }

  @Test
  public void rendersRealObjectMeshes() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            MeshObjectIndex objects = activity.meshObjects();
            assertNotNull("real object index must load", objects);
            assertEquals(32, objects.instanceCount());
            for (MeshObjectIndex.Instance inst : objects.instances()) {
              assertTrue(inst.parts.size() == 3);
              for (MeshObjectIndex.Part part : inst.parts) {
                assertNotNull(part.mesh);
                assertTrue(part.mesh.vertexCount > 0);
                assertNotNull(part.texture);
              }
            }
          });
    }
  }

  @Test
  public void rendersRealSkinnedCharacters() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            com.opensilkroadmap.app.world.CharacterCatalog catalog =
                activity.characterCatalog();
            java.util.Map<String, CharacterMeshIndex> models =
                activity.characterModels();
            assertNotNull("character catalog must load", catalog);
            assertTrue("at least one character model must load", !models.isEmpty());
            for (CharacterMeshIndex model : models.values()) {
              assertTrue(model.skeleton().boneCount > 0);
              assertTrue(model.parts().size() > 0);
              for (CharacterMeshIndex.Part part : model.parts()) {
                assertNotNull(part.mesh);
                assertNotNull(part.texture);
                if (part.skinned) {
                  assertEquals(part.mesh.vertexCount * 3, part.bindPositions.length);
                }
              }
            }
          });
    }
  }

  @Test
  public void terrainHeightsMatchJanganFieldRefSector() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            WorldTerrainSet set = activity.worldRenderer().world();
            assertNotNull(set);
            WorldTerrainSet.Sector ref = set.sectorAt(10f, 10f);
            assertNotNull(ref);
            assertEquals(156, ref.sx);
            assertEquals(89, ref.sy);
            TerrainHeightGrid grid = ref.grid;
            // Real Map.pk2 /89/156.m (Jangan_Field ref sector 156x89).
            assertEquals(866.25f, grid.min(), 0.1f);
            assertEquals(2687.02f, grid.max(), 0.1f);
            assertTrue(grid.min() < grid.max());
          });
    }
  }

  @Test
  public void resolvesSpawnZonesFromCommittedAssets() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            SpawnZoneIndex zones = activity.spawnZones();
            assertNotNull("spawn zone index must load", zones);
            assertEquals(14800, zones.worldCount());
            assertEquals(11597, zones.zoneResolvedCount());
            assertEquals(3203, zones.zoneUnknownCount());
            assertEquals(13, zones.zones().size());
            assertEquals(762, zones.spawnsInZone("1001").size());
            assertEquals("1001", zones.zoneIdOfRegion(25000));
            assertEquals(null, zones.zoneIdOfRegion(-32760));
          });
    }
  }

  @Test
  public void resolvesTeleportGatesFromCommittedAssets() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            TeleportGateIndex gates = activity.teleportGates();
            assertNotNull("teleport gate index must load", gates);
            assertEquals(246, gates.gateCount());
            assertEquals(144, gates.worldCount());
            assertEquals(102, gates.instanceCount());
            assertEquals(104, gates.resolvedWorldCount());
            assertEquals(35, gates.clientOnlyWorldCount());
            assertEquals(5, gates.unresolvedWorldCount());
            assertEquals(12, gates.zones().size());
            assertEquals(25, gates.gatesInZone("1001").size());
            TeleportGateIndex.Gate jangan = gates.gate(0);
            assertEquals("GATE_CH", jangan.gateCode);
            assertEquals(25000, jangan.zoneId);
            assertEquals(168, jangan.sectorX());
            assertEquals(97, jangan.sectorY());
            assertEquals("1001", jangan.serverZone());
            assertEquals("RN_CH_JANGAN", jangan.nameCode());
            assertEquals("STORE_CH_GATE", jangan.storeCode);
            assertEquals("SN_NPC_CH_GATE", jangan.npcCode);
          });
    }
  }

  @Test
  public void resolvesInstancesFromCommittedAssets() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            WorldMapInstanceIndex instances = activity.instances();
            assertNotNull("instance index must load", instances);
            assertEquals(23, instances.instanceCount());
            assertEquals(23, instances.regionResolvedCount());
            WorldMapInstanceIndex.Instance town =
                instances.resolve("Worldmap_THIEFTOWN");
            assertNotNull(town);
            assertEquals("도적마을", town.name);
            assertEquals(182, town.cellX);
            assertEquals(96, town.cellY);
            assertEquals("ThiefTown", town.regionName());
            assertEquals(null, instances.resolve("Worldmap_NOPE"));
          });
    }
  }
}
