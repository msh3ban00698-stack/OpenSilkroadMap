package com.opensilkroadmap.app.world;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.View;

import com.opensilkroadmap.app.game.Camera2D;

/**
 * Android-native renderer of a REAL sector terrain height field.
 *
 * <p>Loads the committed normalized height grid (derived read-only from
 * {@code Map.pk2 /{y}/{x}.m}) and draws it top-down as a colored height-field
 * wireframe: each grid cell is a quad filled with a grayscale ramp of the real
 * height. Camera state (center world x/z and pixels-per-unit) is set from the
 * verified {@link WorldCoordinates} transform; no geometry is invented.
 *
 * <p>Rendering is device-side only; this class has no game logic. Grid quads
 * are drawn every frame from the committed 97x97 heights (fine for a small
 * real-world region slice).
 */
public class NativeWorldRenderer extends View {
  private TerrainHeightGrid grid;
  private float camX;
  private float camZ;
  private float pixelsPerUnit = 0.5f;

  /** Follow/clamp camera that owns the center/scale and the viewport transform. */
  private final Camera2D camera = new Camera2D();

  private final Paint fillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
  private final Paint wirePaint = new Paint();

  public NativeWorldRenderer(Context context) {
    this(context, null);
  }

  public NativeWorldRenderer(Context context, AttributeSet attrs) {
    super(context, attrs);
    wirePaint.setStyle(Paint.Style.STROKE);
    wirePaint.setStrokeWidth(1f);
    wirePaint.setColor(0xFF202020);
  }

  public void setGrid(TerrainHeightGrid grid) {
    this.grid = grid;
    invalidate();
  }

  public void setCamera(float centerWorldX, float centerWorldZ, float ppu) {
    this.camX = centerWorldX;
    this.camZ = centerWorldZ;
    this.pixelsPerUnit = ppu;
    invalidate();
  }

  public TerrainHeightGrid grid() {
    return grid;
  }

  @Override
  protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);
    if (grid == null) {
      return;
    }
    camera.setViewport(getWidth(), getHeight());
    camera.setScale(pixelsPerUnit);
    camera.follow(camX, camZ);
    float step = grid.step();
    int size = grid.size();
    float w = size * step;
    float min = grid.min();
    float max = grid.max();
    canvas.drawColor(0xFF101010);
    Path quad = new Path();
    for (int z = 0; z < size - 1; z++) {
      for (int x = 0; x < size - 1; x++) {
        float x0 = x * step;
        float x1 = x0 + step;
        float z0 = z * step;
        float z1 = z0 + step;
        float h00 = grid.height(z, x);
        float h10 = grid.height(z, x + 1);
        float h01 = grid.height(z + 1, x);
        float h11 = grid.height(z + 1, x + 1);
        float hc = (h00 + h10 + h01 + h11) * 0.25f;
        quad.reset();
        quad.moveTo(vx(x0, z0), vy(x0, z0));
        quad.lineTo(vx(x1, z0), vy(x1, z0));
        quad.lineTo(vx(x1, z1), vy(x1, z1));
        quad.lineTo(vx(x0, z1), vy(x0, z1));
        quad.close();
        fillPaint.setColor(WorldProjection.heightColor(hc, min, max));
        canvas.drawPath(quad, fillPaint);
        if (x % 4 == 0 || z % 4 == 0) {
          canvas.drawPath(quad, wirePaint);
        }
      }
    }
    // Frame the sector edge so the real extent is visible.
    wirePaint.setColor(0xFF000000);
    wirePaint.setStrokeWidth(2f);
    quad.reset();
    quad.moveTo(vx(0, 0), vy(0, 0));
    quad.lineTo(vx(w, 0), vy(w, 0));
    quad.lineTo(vx(w, w), vy(w, w));
    quad.lineTo(vx(0, w), vy(0, w));
    quad.close();
    canvas.drawPath(quad, wirePaint);
  }

  private float vx(float wx, float wz) {
    return (float) ((wx - camera.x()) * camera.scale() + getWidth() / 2.0);
  }

  private float vy(float wx, float wz) {
    return (float) ((camera.y() - wz) * camera.scale() + getHeight() / 2.0);
  }
}
