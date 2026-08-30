package com.opensilkroadmap.app.game;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.widget.TextView;
import com.opensilkroadmap.app.world.NativeWorldRenderer;
import com.opensilkroadmap.app.world.TerrainHeightGrid;
import com.opensilkroadmap.app.world.WorldRegion;
import com.opensilkroadmap.app.world.WorldTerrainIndex;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Phase 14 native world runtime host. Loads the verified world region windows
 * ({@code world_regions.tsv}) and the verified terrain inventory
 * ({@code world_index.tsv}), selects the first region whose reference sector
 * has a committed real {@code .hg} height grid, and renders that real terrain
 * through {@link NativeWorldRenderer}.
 *
 * <p>The renderer is a DIAGNOSTIC TERRAIN RENDERER (verified heightfield
 * wireframe), not a production 3D terrain renderer: no models, materials,
 * normals, or textures are invented. When the terrain asset is missing the
 * screen fails closed with an explicit message; no other region is substituted.
 *
 * <p>The WebView {@code MainActivity} (Capacitor) remains the app launcher;
 * this native activity is reachable independently and uses no WebView.
 */
public final class GameActivity extends Activity {

  private static final String WORLD_REGIONS_ASSET = "game/world/world_regions.tsv";
  private static final String WORLD_INDEX_ASSET = "game/world/world_index.tsv";

  private NativeWorldRenderer world;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    RegionCatalog catalog = loadCatalog();
    GameDataCatalog data = loadDataCatalog();
    WorldTerrainIndex index = loadTerrainIndex();
    List<WorldRegion> regions = loadWorldRegions();

    TerrainHeightGrid grid = null;
    WorldRegion region = null;
    WorldTerrainIndex.Entry sector = null;
    if (index != null && regions != null) {
      for (WorldRegion r : regions) {
        WorldTerrainIndex.Entry e = index.find(r.refSx, r.refSy);
        if (e != null) {
          region = r;
          sector = e;
          break;
        }
      }
      if (sector != null) {
        try {
          grid = TerrainHeightGrid.load(
              getAssets().open(WorldTerrainIndex.hgAssetPath(sector.sx, sector.sy)));
        } catch (IOException e) {
          grid = null;
        }
      }
    }

    FrameLayout root = new FrameLayout(this);
    root.setBackgroundColor(Color.rgb(16, 16, 20));

    world = new NativeWorldRenderer(this);
    if (grid != null) {
      world.setGrid(grid);
      float extent = grid.size() * grid.step();
      world.setCamera(extent / 2f, extent / 2f, 0.5f);
    }
    root.addView(world, new FrameLayout.LayoutParams(
        FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

    TextView overlay = new TextView(this);
    overlay.setTextSize(13f);
    overlay.setTextColor(Color.rgb(230, 230, 235));
    overlay.setPadding(dp(16), dp(16), dp(16), dp(16));
    overlay.setText(describe(region, sector, grid, catalog, data));
    FrameLayout.LayoutParams labelParams =
        new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
    labelParams.gravity = Gravity.TOP | Gravity.START;
    root.addView(overlay, labelParams);

    setContentView(root);
  }

  private String describe(
      WorldRegion region,
      WorldTerrainIndex.Entry sector,
      TerrainHeightGrid grid,
      RegionCatalog catalog,
      GameDataCatalog data) {
    StringBuilder sb = new StringBuilder();
    if (grid != null && region != null && sector != null) {
      sb.append(region.name).append(" (").append(region.type).append(")\n");
      sb.append("sector ").append(sector.sx).append('x').append(sector.sy);
      sb.append(" · ref ").append(region.refSx).append('x').append(region.refSy);
      sb.append('\n');
      sb.append("terrain ").append(grid.size()).append('x').append(grid.size());
      sb.append(" step ").append(grid.step());
      sb.append(" · heights ").append(grid.size() * grid.size());
      sb.append('\n');
      sb.append("min ").append(grid.min()).append(" max ").append(grid.max());
      if (data != null) {
        sb.append("\n").append(data.summary());
      }
      sb.append("\nDIAGNOSTIC TERRAIN RENDERER");
    } else {
      sb.append("TERRAIN ASSET MISSING (verified .hg absent)\n");
      sb.append("no real terrain loaded; no region substituted");
      if (data != null) {
        sb.append('\n').append(data.summary());
      }
    }
    return sb.toString();
  }

  /** Package-private for the instrumented test (same package). */
  NativeWorldRenderer worldRenderer() {
    return world;
  }

  private int dp(int value) {
    return Math.round(value * getResources().getDisplayMetrics().density);
  }

  private RegionCatalog loadCatalog() {
    try {
      return RegionCatalog.parse(
          new InputStreamReader(getAssets().open("game/regions.tsv"), StandardCharsets.UTF_8));
    } catch (IOException e) {
      return null;
    }
  }

  private WorldTerrainIndex loadTerrainIndex() {
    try {
      return WorldTerrainIndex.parse(
          new InputStreamReader(getAssets().open(WORLD_INDEX_ASSET), StandardCharsets.UTF_8));
    } catch (IOException e) {
      return null;
    }
  }

  private List<WorldRegion> loadWorldRegions() {
    try {
      return WorldRegion.load(() -> getAssets().open(WORLD_REGIONS_ASSET));
    } catch (IOException e) {
      return null;
    }
  }

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
