package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import com.opensilkroadmap.app.world.NativeWorldRenderer;
import com.opensilkroadmap.app.world.TerrainHeightGrid;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Instrumented test for the Phase 14 native world runtime host activity.
 *
 * <p>Launches {@link GameActivity} on a device/emulator and verifies the
 * activity renders the verified real terrain through {@link NativeWorldRenderer}.
 * The first region whose reference sector has a committed {@code .hg} is
 * Jangan_Field sector 156x89 (min 866.25, max 2687.02); the grid must load as a
 * real 97x97 VSHG height field, not generated geometry.
 *
 * <p>These tests execute on an Android device/emulator only; in this
 * environment (no JDK/Android SDK) they are NOT EXECUTED.
 */
@RunWith(AndroidJUnit4.class)
public class GameActivityTest {

  @Test
  public void rendersVerifiedTerrainThroughNativeWorldRenderer() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            NativeWorldRenderer world = activity.worldRenderer();
            assertNotNull(world);
            TerrainHeightGrid grid = world.grid();
            assertNotNull(grid);
            assertEquals(97, grid.size());
            assertEquals(20.0f, grid.step(), 1e-6f);
          });
    }
  }

  @Test
  public void terrainHeightsMatchJanganFieldRefSector() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            TerrainHeightGrid grid = activity.worldRenderer().grid();
            assertNotNull(grid);
            // Real Map.pk2 /89/156.m (Jangan_Field ref sector 156x89).
            assertEquals(866.25f, grid.min(), 0.1f);
            assertEquals(2687.02f, grid.max(), 0.1f);
            assertTrue(grid.min() < grid.max());
          });
    }
  }
}
