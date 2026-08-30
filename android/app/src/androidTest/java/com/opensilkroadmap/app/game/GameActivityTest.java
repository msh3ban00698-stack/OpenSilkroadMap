package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Instrumented test for the Phase 9 native game host activity.
 *
 * <p>Launches {@link GameActivity} on a device/emulator and verifies the HUD
 * wires the real region catalog to the minimap surface. Because the full
 * manifest is not bundled into the APK in this environment, the minimap panel
 * must degrade to the explicit "assets not bundled" state while the region
 * label must resolve the default cell (182,96) to TOWN ThiefTown.
 *
 * <p>These tests execute on an Android device/emulator only; in this
 * environment (no JDK/Android SDK) they are NOT EXECUTED.
 */
@RunWith(AndroidJUnit4.class)
public class GameActivityTest {

  @Test
  public void launchesNativeHudWithRealRegionCatalog() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            assertNotNull(activity);
            assertTrue(activity.getContentView() instanceof GameHudView);
            GameHudView hud = (GameHudView) activity.getContentView();
            assertEquals("cell " + GameActivity.DEFAULT_PLAYER_CELL_X + "x" + GameActivity.DEFAULT_PLAYER_CELL_Y, hud.cellLabelText());
            assertTrue(hud.regionLabelText().contains("ThiefTown"));
            assertNotNull(hud.minimapRenderer());
          });
    }
  }

  @Test
  public void minimapFallsBackExplicitlyWhenManifestNotBundled() {
    try (ActivityScenario<GameActivity> scenario =
        ActivityScenario.launch(GameActivity.class)) {
      scenario.onActivity(
          activity -> {
            GameHudView hud = (GameHudView) activity.getContentView();
            assertTrue(hud.statusLabelText().contains("MINIMAP ASSETS NOT BUNDLED"));
          });
    }
  }
}
