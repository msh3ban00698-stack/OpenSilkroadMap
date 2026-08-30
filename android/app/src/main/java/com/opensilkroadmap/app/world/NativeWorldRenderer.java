package com.opensilkroadmap.app.world;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

import com.opensilkroadmap.app.data.NpcSpawnIndex;
import com.opensilkroadmap.app.game.Camera2D;

import java.util.List;

/**
 * Android-native renderer of a REAL multi-sector world height field.
 *
 * <p>Loads a {@link WorldTerrainSet} (committed normalized height grids derived
 * read-only from {@code Map.pk2 /{y}/{x}.m}) and draws each sector top-down as
 * a grayscale height-field wireframe with correct world origins (the proven
 * {@code world = (sector - ref) * 1920 + local} formula). When a
 * {@link NpcSpawnIndex} is attached, verified NPC world placements are drawn as
 * small diagnostic markers (real {@code npcpos} coordinates, NOT models).
 *
 * <p>Rendering is device-side only; this class has no game logic. The renderer
 * remains a DIAGNOSTIC TERRAIN/PLACEMENT renderer: no models, materials,
 * normals, or textures are invented.
 */
public class NativeWorldRenderer extends View {
  private WorldTerrainSet world;
  private NpcSpawnIndex npc;
  private float worldMinH;
  private float worldMaxH;

  private float camX;
  private float camZ;
  private float pixelsPerUnit = 0.5f;

  /** Follow/clamp camera that owns the center/scale and the viewport transform. */
  private final Camera2D camera = new Camera2D();

  private final Paint fillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
  private final Paint wirePaint = new Paint();
  private final Paint markerPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

  private float lastTouchX;
  private float lastTouchY;
  private boolean panning;
  private float pinchStartDistance;
  private float pinchStartScale;

  public NativeWorldRenderer(Context context) {
    this(context, null);
  }

  public NativeWorldRenderer(Context context, AttributeSet attrs) {
    super(context, attrs);
    wirePaint.setStyle(Paint.Style.STROKE);
    wirePaint.setStrokeWidth(1f);
    wirePaint.setColor(0xFF202020);
    markerPaint.setColor(0xFFFFC107);
  }

  /** Installs the multi-sector world and derives camera bounds + height range. */
  public void setWorld(WorldTerrainSet world) {
    this.world = world;
    this.worldMinH = Float.POSITIVE_INFINITY;
    this.worldMaxH = Float.NEGATIVE_INFINITY;
    if (world != null) {
      camera.setWorld(world.width(), world.height());
      for (WorldTerrainSet.Sector s : world.sectors()) {
        worldMinH = Math.min(worldMinH, s.grid.min());
        worldMaxH = Math.max(worldMaxH, s.grid.max());
      }
    }
    invalidate();
  }

  /** Attaches the verified NPC placement index (optional diagnostic overlay). */
  public void setNpcSpawns(NpcSpawnIndex npc) {
    this.npc = npc;
    invalidate();
  }

  /** Sets a single sector as the world (backward-compatible with Phase 14). */
  public void setGrid(TerrainHeightGrid grid) {
    if (grid == null) {
      setWorld(null);
      return;
    }
    WorldTerrainSet.Sector s =
        WorldTerrainSet.sector(0, 0, 0, 0, grid);
    java.util.List<WorldTerrainSet.Sector> one =
        java.util.Collections.singletonList(s);
    setWorld(new WorldTerrainSet(one));
  }

  public void setCamera(float centerWorldX, float centerWorldZ, float ppu) {
    this.camX = centerWorldX;
    this.camZ = centerWorldZ;
    this.pixelsPerUnit = ppu > 0f ? ppu : 0.5f;
    invalidate();
  }

  public WorldTerrainSet world() {
    return world;
  }

  /** Drag pan in viewport pixels; positive dx moves the world right (camera left). */
  public void panByPixels(float dx, float dy) {
    if (pixelsPerUnit <= 0f) {
      return;
    }
    camX -= dx / pixelsPerUnit;
    camZ += dy / pixelsPerUnit;
    invalidate();
  }

  /** Multiplicative zoom around the current camera center. */
  public void zoomBy(float factor) {
    if (factor <= 0f) {
      return;
    }
    pixelsPerUnit *= factor;
    invalidate();
  }

  @Override
  public boolean onTouchEvent(MotionEvent event) {
    switch (event.getActionMasked()) {
      case MotionEvent.ACTION_DOWN:
        lastTouchX = event.getX();
        lastTouchY = event.getY();
        panning = true;
        return true;
      case MotionEvent.ACTION_POINTER_DOWN:
        if (event.getPointerCount() == 2) {
          panning = false;
          pinchStartDistance = distance(event);
          pinchStartScale = pixelsPerUnit;
        }
        return true;
      case MotionEvent.ACTION_MOVE:
        if (event.getPointerCount() >= 2 && pinchStartDistance > 0f) {
          float d = distance(event);
          if (d > 0f) {
            float next = pinchStartScale * (d / pinchStartDistance);
            if (next > 0f) {
              pixelsPerUnit = next;
              invalidate();
            }
          }
        } else if (panning && event.getPointerCount() == 1) {
          float dx = event.getX() - lastTouchX;
          float dy = event.getY() - lastTouchY;
          lastTouchX = event.getX();
          lastTouchY = event.getY();
          panByPixels(dx, dy);
        }
        return true;
      case MotionEvent.ACTION_POINTER_UP:
        panning = false;
        pinchStartDistance = 0f;
        return true;
      case MotionEvent.ACTION_UP:
      case MotionEvent.ACTION_CANCEL:
        panning = false;
        pinchStartDistance = 0f;
        return true;
      default:
        return super.onTouchEvent(event);
    }
  }

  private static float distance(MotionEvent e) {
    float dx = e.getX(0) - e.getX(1);
    float dy = e.getY(0) - e.getY(1);
    return (float) Math.sqrt(dx * dx + dy * dy);
  }

  @Override
  protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);
    if (world == null) {
      return;
    }
    camera.setViewport(getWidth(), getHeight());
    camera.setScale(pixelsPerUnit);
    camera.follow(camX, camZ);
    canvas.drawColor(0xFF101010);
    Path quad = new Path();
    for (WorldTerrainSet.Sector s : world.sectors()) {
      drawSector(canvas, s, quad);
    }
    drawNpcMarkers(canvas);
  }

  private void drawSector(Canvas canvas, WorldTerrainSet.Sector s, Path quad) {
    TerrainHeightGrid grid = s.grid;
    float step = grid.step();
    int size = grid.size();
    for (int z = 0; z < size - 1; z++) {
      for (int x = 0; x < size - 1; x++) {
        float x0 = s.originX + x * step;
        float x1 = x0 + step;
        float z0 = s.originZ + z * step;
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
        fillPaint.setColor(WorldProjection.heightColor(hc, worldMinH, worldMaxH));
        canvas.drawPath(quad, fillPaint);
        if (x % 4 == 0 || z % 4 == 0) {
          canvas.drawPath(quad, wirePaint);
        }
      }
    }
  }

  private void drawNpcMarkers(Canvas canvas) {
    if (npc == null || world == null) {
      return;
    }
    // Draw real npcpos placements within the loaded world bounds as markers.
    int sx0 = Integer.MAX_VALUE;
    int sy0 = Integer.MAX_VALUE;
    int sx1 = Integer.MIN_VALUE;
    int sy1 = Integer.MIN_VALUE;
    for (WorldTerrainSet.Sector s : world.sectors()) {
      sx0 = Math.min(sx0, s.sx);
      sy0 = Math.min(sy0, s.sy);
      sx1 = Math.max(sx1, s.sx);
      sy1 = Math.max(sy1, s.sy);
    }
    if (sx0 > sx1 || sy0 > sy1) {
      return;
    }
    int refSx = sx0;
    int refSy = sy0;
    List<NpcSpawnIndex.Spawn> spawns = npc.inWindow(sx0, sx1, sy0, sy1);
    float r = 3f * getResources().getDisplayMetrics().density;
    for (NpcSpawnIndex.Spawn sp : spawns) {
      float wx = sp.worldX(refSx);
      float wz = sp.worldZ(refSy);
      canvas.drawCircle(vx(wx, wz), vy(wx, wz), r, markerPaint);
    }
  }

  private float vx(float wx, float wz) {
    return (float) ((wx - camera.x()) * camera.scale() + getWidth() / 2.0);
  }

  private float vy(float wx, float wz) {
    return (float) ((camera.y() - wz) * camera.scale() + getHeight() / 2.0);
  }
}
