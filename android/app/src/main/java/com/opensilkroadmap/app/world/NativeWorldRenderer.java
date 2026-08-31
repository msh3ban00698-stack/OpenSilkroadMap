package com.opensilkroadmap.app.world;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapShader;
import android.graphics.Canvas;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Shader;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

import com.opensilkroadmap.app.data.NpcSpawnIndex;
import com.opensilkroadmap.app.game.Camera2D;
import com.opensilkroadmap.app.game.InputController;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

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
 * <p>When a {@link MeshObjectIndex} is attached (Phase 17), each REAL object
 * placement's REAL mesh geometry (converted from original {@code .bms} parts)
 * is drawn triangle-by-triangle, textured with the REAL converted texture and
 * rotated by the REAL placement heading (theta) at the VERIFIED world
 * coordinate. No placeholder geometry is ever drawn.
 *
 * <p>When a {@link CharacterCatalog} and its loaded models are attached, the
 * renderer instances real NPCs by refid via the catalog and draws each real
 * character's mesh parts at their verified world coordinate. Each character
 * that has a committed stand/idle clip is animated in a loop via
 * {@link #advanceAnimations}; characters without a stand clip stay at the bind
 * pose.
 *
 * <p>Rendering is device-side only; this class has no game logic.
 */
public class NativeWorldRenderer extends View {
  private WorldTerrainSet world;
  private NpcSpawnIndex npc;
  private MeshObjectIndex meshObjects;
  private CharacterCatalog characterCatalog;
  private Map<String, CharacterMeshIndex> characterModels =
      new HashMap<String, CharacterMeshIndex>();
  private Pose characterPose;
  private final Map<NpcSpawnIndex.Spawn, CharacterEntity> characterEntities =
      new HashMap<NpcSpawnIndex.Spawn, CharacterEntity>();
  private boolean objectsVisible = true;
  private boolean charactersVisible = true;
  private float worldMinH;
  private float worldMaxH;

  /** The player entity, drawn separately from spawned NPCs (Phase 24). */
  private CharacterEntity playerEntity;
  private float playerHeading;
  private boolean playerVisible;

  private float camX;
  private float camZ;
  private float pixelsPerUnit = 0.5f;

  /** Follow/clamp camera that owns the center/scale and the viewport transform. */
  private final Camera2D camera = new Camera2D();

  /** Engine-agnostic input accumulator (drag pan + pinch zoom); drained per frame. */
  private final InputController input = new InputController();

  private final Paint fillPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
  private final Paint wirePaint = new Paint();
  private final Paint markerPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

  private final Paint objectPaint = new Paint();
  private final Path triPath = new Path();
  private final Matrix uvMatrix = new Matrix();
  private final float[] uvSrc = new float[6];
  private final float[] uvDst = new float[6];
  private final float[] worldV = new float[3];
  private final Map<Bitmap, BitmapShader> shaderCache =
      new HashMap<Bitmap, BitmapShader>();

  private float lastTouchX;
  private float lastTouchY;
  private boolean panning;
  private float pinchStartDistance;

  private boolean joystickActive;
  private float joystickOriginX;
  private float joystickOriginY;
  private static final float JOYSTICK_RADIUS_DP = 56f;

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

  /** Attaches the real object mesh index (Phase 17); null hides objects. */
  public void setMeshObjects(MeshObjectIndex meshObjects) {
    this.meshObjects = meshObjects;
    shaderCache.clear();
    invalidate();
  }

  /** Attaches the character catalog (refid -> key) and loaded models. */
  public void setCharacters(CharacterCatalog catalog,
                            Map<String, CharacterMeshIndex> models) {
    this.characterCatalog = catalog;
    this.characterModels = (models == null)
        ? new HashMap<String, CharacterMeshIndex>() : models;
    characterEntities.clear();
    shaderCache.clear();
    invalidate();
  }

  public void setCharacterCatalog(CharacterCatalog catalog) {
    this.characterCatalog = catalog;
    characterEntities.clear();
    invalidate();
  }

  public void setCharacterModels(Map<String, CharacterMeshIndex> models) {
    this.characterModels = (models == null)
        ? new HashMap<String, CharacterMeshIndex>() : models;
    characterEntities.clear();
    shaderCache.clear();
    invalidate();
  }

  /**
   * Attaches the player entity. The player is drawn at its own world position
   * rotated by its facing heading (the PROVEN placement rotation). Visible only
   * after a verified spawn was placed (fail-closed: no invented position).
   */
  public void setPlayer(CharacterEntity player, float headingRadians,
                        boolean visible) {
    this.playerEntity = player;
    this.playerHeading = headingRadians;
    this.playerVisible = visible;
    invalidate();
  }

  /** The shared input accumulator (joystick move axis + pan/zoom). */
  public InputController input() {
    return input;
  }

  /** Current pixels-per-world-unit zoom, for frame-consistent camera updates. */
  public float pixelsPerUnit() {
    return pixelsPerUnit;
  }

  /**
   * Advances every spawned character's independent animation clock. Called once
   * per frame from the game-loop host. Poses are re-sampled per draw from each
   * entity's active clip; characters without a clip stay at the bind pose.
   */
  public void advanceAnimations(double dtSeconds) {
    for (CharacterEntity e : characterEntities.values()) {
      e.update(dtSeconds);
    }
  }

  /**
   * Attaches an optional global fallback pose. When non-null, characters with
   * no active animation clip are skinned at this pose instead of the static
   * bind pose. Null restores the bind-pose fallback. Per-instance animated
   * poses (from {@link #advanceAnimations}) always take precedence.
   */
  public void setCharacterPose(Pose pose) {
    this.characterPose = pose;
    invalidate();
  }

  /** Toggles the real object mesh overlay. */
  public void setObjectsVisible(boolean visible) {
    this.objectsVisible = visible;
    invalidate();
  }

  /** Toggles the real character overlay. */
  public void setCharactersVisible(boolean visible) {
    this.charactersVisible = visible;
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
        // Left half = movement joystick; right half = drag pan.
        if (event.getX() < getWidth() / 2f) {
          joystickActive = true;
          joystickOriginX = event.getX();
          joystickOriginY = event.getY();
          input.joystick(0f, 0f, joystickRadiusPx());
        } else {
          lastTouchX = event.getX();
          lastTouchY = event.getY();
          panning = true;
        }
        return true;
      case MotionEvent.ACTION_POINTER_DOWN:
        if (event.getPointerCount() == 2) {
          joystickActive = false;
          input.joystick(0f, 0f, joystickRadiusPx());
          panning = false;
          pinchStartDistance = distance(event);
        }
        return true;
      case MotionEvent.ACTION_MOVE:
        if (joystickActive && event.getPointerCount() == 1) {
          input.joystick(
              event.getX() - joystickOriginX,
              event.getY() - joystickOriginY,
              joystickRadiusPx());
        } else if (event.getPointerCount() >= 2 && pinchStartDistance > 0f) {
          float d = distance(event);
          if (d > 0f) {
            input.pinchZoom(d / pinchStartDistance);
            pinchStartDistance = d;
          }
        } else if (panning && event.getPointerCount() == 1) {
          float dx = event.getX() - lastTouchX;
          float dy = event.getY() - lastTouchY;
          lastTouchX = event.getX();
          lastTouchY = event.getY();
          input.drag(dx, dy);
        }
        return true;
      case MotionEvent.ACTION_POINTER_UP:
        joystickActive = false;
        input.joystick(0f, 0f, joystickRadiusPx());
        panning = false;
        pinchStartDistance = 0f;
        return true;
      case MotionEvent.ACTION_UP:
      case MotionEvent.ACTION_CANCEL:
        joystickActive = false;
        input.joystick(0f, 0f, joystickRadiusPx());
        panning = false;
        pinchStartDistance = 0f;
        return true;
      default:
        return super.onTouchEvent(event);
    }
  }

  private float joystickRadiusPx() {
    return JOYSTICK_RADIUS_DP * getResources().getDisplayMetrics().density;
  }

  private static float distance(MotionEvent e) {
    float dx = e.getX(0) - e.getX(1);
    float dy = e.getY(0) - e.getY(1);
    return (float) Math.sqrt(dx * dx + dy * dy);
  }

  /** Drains accumulated pan/zoom intents into the camera (frame-consistent). */
  public void applyInput() {
    float px = input.consumePanX();
    float py = input.consumePanY();
    if (px != 0f || py != 0f) {
      panByPixels(px, py);
    }
    float z = input.consumeZoom();
    if (z != 1f) {
      zoomBy(z);
    }
  }

  @Override
  protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);
    applyInput();
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
    drawMeshObjects(canvas);
    drawCharacters(canvas);
    drawPlayer(canvas);
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

  private void drawMeshObjects(Canvas canvas) {
    if (!objectsVisible || meshObjects == null || world == null) {
      return;
    }
    for (MeshObjectIndex.Instance inst : meshObjects.instances()) {
      float wx = inst.worldX(meshObjects.refSx());
      float wz = inst.worldZ(meshObjects.refSy());
      for (MeshObjectIndex.Part part : inst.parts) {
        drawMeshPart(canvas, part, wx, wz, inst.theta);
      }
    }
  }

  private void drawMeshPart(
      Canvas canvas, MeshObjectIndex.Part part, float wx, float wz, float theta) {
    StaticMeshAsset.Mesh mesh = part.mesh;
    if (mesh == null || mesh.triangleCount == 0) {
      return;
    }
    Bitmap tex = part.texture;
    if (tex == null) {
      return;
    }
    float cos = (float) Math.cos(theta);
    float sin = (float) Math.sin(theta);
    drawTexturedTriangles(
        canvas, mesh.positions, mesh.uvs, mesh.indices, mesh.triangleCount,
        tex, wx, wz, cos, sin);
  }

  private void drawCharacters(Canvas canvas) {
    if (!charactersVisible || characterCatalog == null
        || characterModels.isEmpty() || world == null || npc == null) {
      return;
    }
    int sx0 = Integer.MAX_VALUE, sy0 = Integer.MAX_VALUE;
    int sx1 = Integer.MIN_VALUE, sy1 = Integer.MIN_VALUE;
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
    for (NpcSpawnIndex.Spawn sp : spawns) {
      String key = characterCatalog.keyFor(sp.characterRefId);
      CharacterMeshIndex model = key == null ? null : characterModels.get(key);
      if (model == null) {
        continue; // fail-closed: unloaded/unknown character stays a marker
      }
      CharacterEntity entity = entityFor(sp, model);
      Pose pose = poseFor(entity);
      if (pose == null) {
        pose = characterPose;
      }
      float wx = sp.worldX(refSx);
      float wz = sp.worldZ(refSy);
      for (CharacterMeshIndex.Part part : model.parts()) {
        float[] positions = part.bindPositions;
        if (part.skinned && pose != null) {
          try {
            positions = CharacterRenderer.skin(
                model.skeleton(), pose,
                (StaticMeshAsset.SkinnedMesh) part.mesh);
          } catch (IOException e) {
            positions = part.bindPositions;
          }
        } else if (!part.skinned) {
          positions = part.mesh.positions;
        }
        drawTexturedTriangles(canvas, positions, part.mesh.uvs, part.mesh.indices,
            part.mesh.triangleCount, part.texture, wx, wz, 1f, 0f);
      }
    }
    pruneEntities(spawns);
  }

  /**
   * Returns the persistent per-spawn entity, creating it on first sight and
   * replacing it if the resolved model changed.
   */
  private CharacterEntity entityFor(NpcSpawnIndex.Spawn sp, CharacterMeshIndex model) {
    CharacterEntity e = characterEntities.get(sp);
    if (e == null || e.index() != model) {
      e = new CharacterEntity(model);
      characterEntities.put(sp, e);
    }
    return e;
  }

  /** Samples an entity's active pose; null means bind pose (or sampling error). */
  private Pose poseFor(CharacterEntity e) {
    return e.pose();
  }

  /** Drops entities whose spawn fell out of the visible sector window. */
  private void pruneEntities(List<NpcSpawnIndex.Spawn> visible) {
    if (characterEntities.isEmpty()) {
      return;
    }
    characterEntities.keySet().retainAll(visible);
  }

  /**
   * Draws the player entity (Phase 24) at its own world position, rotated by
   * its facing heading using the PROVEN placement rotation. Skipped until a
   * verified spawn has placed the player (fail-closed: never a fabricated
   * position). Uses the same skin/pose path as spawned NPCs.
   */
  private void drawPlayer(Canvas canvas) {
    if (!playerVisible || playerEntity == null || world == null) {
      return;
    }
    CharacterMeshIndex model = playerEntity.index();
    Pose pose = playerEntity.pose();
    if (pose == null) {
      pose = characterPose;
    }
    float wx = playerEntity.worldX();
    float wz = playerEntity.worldZ();
    float cos = (float) Math.cos(playerHeading);
    float sin = (float) Math.sin(playerHeading);
    for (CharacterMeshIndex.Part part : model.parts()) {
      float[] positions = part.bindPositions;
      if (part.skinned && pose != null) {
        try {
          positions = CharacterRenderer.skin(
              model.skeleton(), pose,
              (StaticMeshAsset.SkinnedMesh) part.mesh);
        } catch (IOException e) {
          positions = part.bindPositions;
        }
      } else if (!part.skinned) {
        positions = part.mesh.positions;
      }
      drawTexturedTriangles(canvas, positions, part.mesh.uvs, part.mesh.indices,
          part.mesh.triangleCount, part.texture, wx, wz, cos, sin);
    }
  }

  /**
   * Draws a triangle list with a bitmap shader. Positions are already in
   * character/world-local space; {@code (cos, sin)} is the placement heading
   * rotation ({@code 1,0} = no heading).
   */
  private void drawTexturedTriangles(
      Canvas canvas, float[] positions, float[] uvs, int[] indices,
      int triangleCount, Bitmap tex, float wx, float wz, float cos, float sin) {
    if (positions == null || uvs == null || indices == null
        || triangleCount == 0 || tex == null) {
      return;
    }
    float texW = tex.getWidth();
    float texH = tex.getHeight();
    BitmapShader shader = shaderCache.get(tex);
    if (shader == null) {
      shader = new BitmapShader(tex, Shader.TileMode.CLAMP, Shader.TileMode.CLAMP);
      shaderCache.put(tex, shader);
    }
    objectPaint.setShader(shader);
    for (int t = 0; t < triangleCount; t++) {
      int i0 = indices[t * 3];
      int i1 = indices[t * 3 + 1];
      int i2 = indices[t * 3 + 2];
      uvSrc[0] = uvs[i0 * 2] * texW;
      uvSrc[1] = uvs[i0 * 2 + 1] * texH;
      uvSrc[2] = uvs[i1 * 2] * texW;
      uvSrc[3] = uvs[i1 * 2 + 1] * texH;
      uvSrc[4] = uvs[i2 * 2] * texW;
      uvSrc[5] = uvs[i2 * 2 + 1] * texH;
      worldVertex(positions, i0, wx, wz, cos, sin, worldV);
      uvDst[0] = vx(worldV[0], worldV[2]);
      uvDst[1] = vy(worldV[0], worldV[2]);
      worldVertex(positions, i1, wx, wz, cos, sin, worldV);
      uvDst[2] = vx(worldV[0], worldV[2]);
      uvDst[3] = vy(worldV[0], worldV[2]);
      worldVertex(positions, i2, wx, wz, cos, sin, worldV);
      uvDst[4] = vx(worldV[0], worldV[2]);
      uvDst[5] = vy(worldV[0], worldV[2]);
      uvMatrix.setPolyToPoly(uvSrc, 0, uvDst, 0, 3);
      shader.setLocalMatrix(uvMatrix);
      triPath.reset();
      triPath.moveTo(uvDst[0], uvDst[1]);
      triPath.lineTo(uvDst[2], uvDst[3]);
      triPath.lineTo(uvDst[4], uvDst[5]);
      triPath.close();
      canvas.drawPath(triPath, objectPaint);
    }
  }

  private void worldVertex(
      float[] positions, int idx, float wx, float wz, float cos, float sin, float[] out) {
    float lx = positions[idx * 3];
    float lz = positions[idx * 3 + 2];
    out[0] = wx + lx * cos + lz * sin;
    out[1] = positions[idx * 3 + 1];
    out[2] = wz - lx * sin + lz * cos;
  }

  private float vx(float wx, float wz) {
    return (float) ((wx - camera.x()) * camera.scale() + getWidth() / 2.0);
  }

  private float vy(float wx, float wz) {
    return (float) ((camera.y() - wz) * camera.scale() + getHeight() / 2.0);
  }
}
