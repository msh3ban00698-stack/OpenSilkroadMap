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

/**
 * Phase 9 HUD integration: a native {@link FrameLayout} that hosts the Phase 8
 * {@link NativeMinimapRenderer} plus region/cell/status labels, wired to a real
 * {@link RegionCatalog} (from Data.pk2 RegionInfo.txt) and a
 * {@link NativeMinimapAssetProvider}.
 *
 * <p>When the full manifest ({@code assets/game/manifest.json}) and the
 * converted minimap PNGs are bundled into the APK, {@link #setPlayerCell} loads
 * the minimap for the cell through the verified Phase 8 resolver/loader. When
 * they are not bundled, the HUD degrades to a clear, explicit "assets not
 * bundled" state instead of inventing behavior.
 */
public final class GameHudView extends FrameLayout {
  private final RegionCatalog catalog;
  private final NativeMinimapAssetProvider provider;
  private final NativeMinimapRenderer minimap;
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
}
