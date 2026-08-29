package com.opensilkroadmap.app.minimap;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.util.AttributeSet;
import android.view.View;

/**
 * Native Android minimap surface. All pixels are produced by native Android
 * code drawing a {@link Bitmap} onto an {@link android.graphics.Canvas}; no
 * HTML/DOM/JavaScript rendering is involved.
 *
 * <p>The renderer knows nothing about PK2 archives, world coordinates, or
 * gameplay. It consumes validated {@link NativeMinimapAssetProvider.ResolvedMinimap}
 * values keyed by exact manifest source path, preserves aspect ratio, applies
 * bounded zoom, and exposes a player-position API for future gameplay code.
 *
 * <p>Bitmap lifecycle: the renderer does not own or release bitmaps. The
 * caller owns the {@link NativeMinimapAssetProvider} and releases resources
 * through {@code provider.release(...)} / {@code provider.releaseAll()}.
 */
public final class NativeMinimapRenderer extends View {
  private NativeMinimapAssetProvider.ResolvedMinimap current;
  private float zoom = 1f;
  private boolean playerPositionSet;
  private float playerX;
  private float playerY;
  private boolean testMarkerVisible;

  private final Paint bitmapPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
  private final Paint markerPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
  private final Paint labelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
  private final Rect dstRect = new Rect();

  public NativeMinimapRenderer(Context context) {
    super(context);
    init();
  }

  public NativeMinimapRenderer(Context context, AttributeSet attrs) {
    super(context, attrs);
    init();
  }

  private void init() {
    markerPaint.setColor(Color.rgb(255, 224, 130));
    markerPaint.setStyle(Paint.Style.STROKE);
    markerPaint.setStrokeWidth(3f);
    labelPaint.setColor(Color.rgb(255, 224, 130));
    labelPaint.setTextSize(28f);
  }

  /** Sets the active minimap. The caller retains ownership of the asset. */
  public void setMinimap(NativeMinimapAssetProvider.ResolvedMinimap minimap) {
    this.current = minimap;
    invalidate();
  }

  public boolean hasMinimap() {
    return current != null;
  }

  /** Sets bounded zoom in {@code [FitMath.MIN_ZOOM, FitMath.MAX_ZOOM]}. */
  public void setZoom(float requested) {
    this.zoom = FitMath.clampZoom(requested);
    invalidate();
  }

  public float getZoom() {
    return zoom;
  }

  /**
   * Sets the player marker position in image pixel coordinates of the current
   * minimap. API-only for future gameplay; no world coordinates are used.
   */
  public void setPlayerPosition(float x, float y) {
    this.playerX = x;
    this.playerY = y;
    this.playerPositionSet = true;
    invalidate();
  }

  /**
   * TEST ONLY: enables the temporary player marker so the development/test
   * screen can prove the future-marker API renders native pixels.
   */
  public void setTestMarkerVisible(boolean visible) {
    this.testMarkerVisible = visible;
    invalidate();
  }

  /** Clears the active minimap and resets zoom/position state. */
  public void reset() {
    this.current = null;
    this.zoom = 1f;
    this.playerPositionSet = false;
    this.testMarkerVisible = false;
    invalidate();
  }

  @Override
  protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);
    canvas.drawColor(Color.rgb(16, 16, 20));
    if (current == null || !(current.asset() instanceof BitmapAsset)) {
      return;
    }
    BitmapAsset bitmapAsset = (BitmapAsset) current.asset();
    Bitmap bitmap;
    try {
      bitmap = bitmapAsset.bitmap();
    } catch (IllegalStateException e) {
      return;
    }
    int viewWidth = getWidth();
    int viewHeight = getHeight();
    int imageWidth = bitmap.getWidth();
    int imageHeight = bitmap.getHeight();
    if (viewWidth <= 0 || viewHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
      return;
    }

    FitMath.SourceRect source =
        FitMath.sourceViewport(viewWidth, viewHeight, imageWidth, imageHeight, zoom, imageWidth / 2f, imageHeight / 2f);
    Rect srcRect = new Rect(source.left, source.top, source.right, source.bottom);
    dstRect.set(0, 0, viewWidth, viewHeight);
    canvas.drawBitmap(bitmap, srcRect, dstRect, bitmapPaint);

    if (testMarkerVisible && playerPositionSet) {
      drawTestMarker(canvas, viewWidth, viewHeight, source, imageWidth, imageHeight);
    }
  }

  private void drawTestMarker(
      Canvas canvas, int viewWidth, int viewHeight, FitMath.SourceRect source, int imageWidth, int imageHeight) {
    if (playerX < 0 || playerX > imageWidth || playerY < 0 || playerY > imageHeight) {
      return;
    }
    float viewX = viewWidth * (playerX - source.left) / (float) Math.max(1, source.width());
    float viewY = viewHeight * (playerY - source.top) / (float) Math.max(1, source.height());
    canvas.drawCircle(viewX, viewY, 14f, markerPaint);
    canvas.drawCircle(viewX, viewY, 3f, markerPaint);
    canvas.drawText("TEST ONLY", viewX + 18f, viewY - 8f, labelPaint);
  }
}
