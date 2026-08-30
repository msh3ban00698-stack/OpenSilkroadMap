package com.opensilkroadmap.app.game;

import android.content.Context;
import android.graphics.Color;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import com.opensilkroadmap.app.minimap.MinimapException;
import com.opensilkroadmap.app.minimap.NativeMinimapAssetProvider;
import com.opensilkroadmap.app.minimap.NativeMinimapRenderer;
import com.opensilkroadmap.app.world.NativeWorldRenderer;
import com.opensilkroadmap.app.world.TerrainHeightGrid;

/**
 * Native game HUD host. The world renderer occupies the full viewport and the
 * existing HUD/minimap are layered above it. Real terrain is optional: when a
 * matching .hg asset is not bundled, the renderer remains empty and the HUD
 * reports that exact state rather than inventing geometry.
 */
public final class GameHudView extends FrameLayout {
  private final RegionCatalog catalog;
  private final NativeMinimapAssetProvider provider;
  private final NativeMinimapRenderer minimap;
  private final NativeWorldRenderer world;
  private final TextView regionLabel;
  private final TextView cellLabel;
  private final TextView statusLabel;
  private final TextView dataLabel;

  public GameHudView(
      Context context,
      RegionCatalog catalog,
      NativeMinimapAssetProvider provider,
      GameDataCatalog data) {
    super(context);
    this.catalog = catalog;
    this.provider = provider;

    setBackgroundColor(Color.rgb(16, 16, 20));

    world = new NativeWorldRenderer(context);
    FrameLayout.LayoutParams worldParams =
        new FrameLayout.LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT);
    addView(world, worldParams);

    LinearLayout labels = new LinearLayout(context);
    labels.setOrientation(LinearLayout.VERTICAL);
    labels.setPadding(dp(16), dp(16), dp(16), dp(16));
    regionLabel = label(context, 18f, Color.WHITE);
    cellLabel = label(context, 14f, Color.rgb(200, 200, 210));
    statusLabel = label(context, 13f, Color.rgb(255, 200, 90));
    dataLabel = label(context, 12f, Color.rgb(150, 220, 150));
    labels.addView(regionLabel);
    labels.addView(cellLabel);
    labels.addView(statusLabel);
    if (data != null) {
      dataLabel.setText(data.summary());
      labels.addView(dataLabel);
    } else {
      dataLabel.setText("TEXTDATA ASSETS NOT BUNDLED (game/textdata/*.tsv absent)");
      dataLabel.setTextColor(Color.rgb(150, 150, 150));
      labels.addView(dataLabel);
    }
    FrameLayout.LayoutParams labelParams =
        new FrameLayout.LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT);
    labelParams.gravity = Gravity.TOP | Gravity.START;
    addView(labels, labelParams);

    minimap = new NativeMinimapRenderer(context);
    FrameLayout.LayoutParams minimapParams = new FrameLayout.LayoutParams(dp(240), dp(240));
    minimapParams.gravity = Gravity.BOTTOM | Gravity.END;
    minimapParams.setMargins(dp(16), dp(16), dp(16), dp(16));
    addView(minimap, minimapParams);
  }

  private static TextView label(Context context, float sp, int color) {
    TextView tv = new TextView(context);
    tv.setTextSize(sp);
    tv.setTextColor(color);
    return tv;
  }

  private int dp(int value) {
    return Math.round(value * getResources().getDisplayMetrics().density);
  }

  public NativeMinimapRenderer minimapRenderer() {
    return minimap;
  }

  public NativeWorldRenderer worldRenderer() {
    return world;
  }

  public String regionLabelText() {
    return regionLabel.getText().toString();
  }

  public String cellLabelText() {
    return cellLabel.getText().toString();
  }

  public String statusLabelText() {
    return statusLabel.getText().toString();
  }

  public String dataLabelText() {
    return dataLabel.getText().toString();
  }

  /**
   * Moves the player to a grid cell: updates region/cell labels and, when the
   * provider has a manifest, loads and shows the cell minimap. The marker is
   * TEST ONLY and centered on the decoded image.
   */
  public void setPlayerCell(int x, int y) {
    cellLabel.setText("cell " + x + "x" + y);
    RegionInfo region = catalog.regionForCell(x, y);
    regionLabel.setText(region != null ? region.name + " (" + region.type + ")" : "unlisted cell");
    if (provider == null) {
      statusLabel.setText("MINIMAP ASSETS NOT BUNDLED (assets/game/manifest.json absent)");
      minimap.reset();
      return;
    }
    try {
      NativeMinimapAssetProvider.ResolvedMinimap resolved =
          provider.load(WorldGrid.minimapSourcePath(x, y));
      minimap.setMinimap(resolved);
      minimap.setPlayerPosition(resolved.asset().width() / 2f, resolved.asset().height() / 2f);
      minimap.setTestMarkerVisible(true);
      statusLabel.setText("TEST ONLY marker at image center");
    } catch (MinimapException e) {
      minimap.reset();
      statusLabel.setText("no minimap for cell " + x + "x" + y + ": " + e.getMessage());
    }
  }

  /** Install a verified real height grid and center the camera on the sector. */
  public void setTerrain(TerrainHeightGrid grid) {
    world.setGrid(grid);
    if (grid != null) {
      float center = (grid.size() - 1) * grid.step() * 0.5f;
      world.setCamera(center, center, 0.45f);
    }
  }

  /** Update the terrain status without changing the minimap status. */
  public void setTerrainStatus(String message) {
    statusLabel.setText(message);
  }
}
