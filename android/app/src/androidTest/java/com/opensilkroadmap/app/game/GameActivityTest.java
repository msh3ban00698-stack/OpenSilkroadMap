package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
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
            CharacterMeshIndex characters = activity.characters();
            assertNotNull("real character index must load", characters);
            assertEquals(60, characters.instanceCount());
            assertEquals(35, characters.skeleton().boneCount);
            assertEquals(3, characters.parts().size());
            for (CharacterMeshIndex.Part part : characters.parts()) {
              assertNotNull(part.mesh);
              assertTrue(part.mesh.boneNames.length > 0);
              assertEquals(part.mesh.vertexCount, part.mesh.bone1.length);
              assertNotNull(part.texture);
              assertEquals(part.mesh.vertexCount * 3, part.bindPositions.length);
            }
            assertTrue(characters.anims().size() == 16);
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
}
