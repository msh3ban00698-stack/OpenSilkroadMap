package com.opensilkroadmap.app.game;

import android.app.Activity;
import android.os.Bundle;
import com.opensilkroadmap.app.minimap.BitmapFactoryDecoder;
import com.opensilkroadmap.app.minimap.ManifestData;
import com.opensilkroadmap.app.minimap.ManifestParser;
import com.opensilkroadmap.app.minimap.ManifestResolver;
import com.opensilkroadmap.app.minimap.MinimapException;
import com.opensilkroadmap.app.minimap.NativeMinimapAssetProvider;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

/**
 * Phase 9 native game host activity. Loads the real derived region catalog
 * (Data.pk2 RegionInfo.txt), builds the verified Phase 8 minimap provider when
 * {@code assets/game/manifest.json} is bundled, and shows the native HUD.
 *
 * <p>Default camera cell is (182, 96), which RegionInfo.txt places in
 * {@code TOWN ThiefTown} (VERIFIED); this is a default camera position for the
 * HUD, not a gameplay spawn claim. The WebView MainActivity remains the
 * launcher; this activity is reachable once bundled and is the integration
 * point for Phase 10 on-device validation.
 */
public final class GameActivity extends Activity {
  static final int DEFAULT_PLAYER_CELL_X = 182;
  static final int DEFAULT_PLAYER_CELL_Y = 96;

  private GameHudView hud;
  private NativeMinimapAssetProvider provider;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    RegionCatalog catalog = loadCatalog();
    provider = loadProvider();
    GameDataCatalog data = loadDataCatalog();
    hud = new GameHudView(this, catalog, provider, data);
    setContentView(hud);
    hud.setPlayerCell(DEFAULT_PLAYER_CELL_X, DEFAULT_PLAYER_CELL_Y);
  }

  @Override
  protected void onDestroy() {
    if (provider != null) {
      provider.releaseAll();
    }
    super.onDestroy();
  }

  private RegionCatalog loadCatalog() {
    try {
      return RegionCatalog.parse(new InputStreamReader(getAssets().open("game/regions.tsv")));
    } catch (IOException e) {
      throw new IllegalStateException("region catalog missing from assets/game/regions.tsv", e);
    }
  }

  private NativeMinimapAssetProvider loadProvider() {
    InputStream manifestIn;
    try {
      manifestIn = getAssets().open("game/manifest.json");
    } catch (IOException e) {
      return null;
    }
    try {
      ManifestData data = ManifestParser.parse(manifestIn);
      ManifestResolver resolver = new ManifestResolver(data);
      NativeMinimapAssetProvider.AssetReader reader =
          relativePath -> getAssets().open(relativePath);
      return new NativeMinimapAssetProvider(
          resolver,
          reader,
          new BitmapFactoryDecoder(),
          NativeMinimapAssetProvider.DEFAULT_MAX_CACHE_BYTES,
          NativeMinimapAssetProvider.DEFAULT_MAX_CACHE_ENTRIES);
    } catch (IOException | MinimapException e) {
      return null;
    }
  }

  /**
   * Loads the Phase 12 textdata catalog (npcpos/leveldata/teleportdata/
   * worldmap_instanceinfo). Returns {@code null} when the textdata assets are
   * not bundled; the HUD then shows an explicit "assets not bundled" state
   * instead of fabricating data.
   */
  private GameDataCatalog loadDataCatalog() {
    try {
      return GameDataCatalog.loadFrom(
          new InputStreamReader(getAssets().open("game/textdata/npcpos.tsv"), StandardCharsets.UTF_8),
          new InputStreamReader(getAssets().open("game/textdata/leveldata.tsv"), StandardCharsets.UTF_8),
          new InputStreamReader(getAssets().open("game/textdata/teleportdata.tsv"), StandardCharsets.UTF_8),
          new InputStreamReader(
              getAssets().open("game/textdata/worldmap_instanceinfo.tsv"), StandardCharsets.UTF_8));
    } catch (IOException e) {
      return null;
    }
  }
}
