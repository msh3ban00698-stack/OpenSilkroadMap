package com.opensilkroadmap.app.world;

import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * World object index over the committed Phase 17 rendering assets
 * ({@code game/world/objects/models.tsv}, {@code placements.tsv}, {@code mesh/*.msh},
 * {@code tex/*.png}).
 *
 * <p>Every asset is derived offline from the ORIGINAL data chain proven in
 * Phase 17 (sector {@code .o2} placement -> nameI -> {@code object.ifo} ->
 * {@code .bsr} -> {@code .bms} mesh parts + {@code .bmt} material ->
 * {@code .ddj} texture). This index exposes the real placements with world
 * coordinates computed by the proven tail-relative formula and the real mesh
 * parts with their real textures, ready for the native renderer.
 *
 * <p>Loading is strict: a missing mesh or texture asset fails closed (returns
 * null index) rather than silently dropping real objects.
 */
public final class MeshObjectIndex {

  /** One mesh part (real geometry + real texture bitmap). */
  public static final class Part {
    public final int nameI;
    public final int partIdx;
    public final String material;
    public final StaticMeshAsset.Mesh mesh;
    public final Bitmap texture;

    Part(int nameI, int partIdx, String material, StaticMeshAsset.Mesh mesh, Bitmap texture) {
      this.nameI = nameI;
      this.partIdx = partIdx;
      this.material = material;
      this.mesh = mesh;
      this.texture = texture;
    }
  }

  /** One proven object placement with world coordinates (ref-relative). */
  public static final class Instance {
    public final int nameI;
    public final float x;
    public final float y;
    public final float z;
    public final float theta;
    public final int tx;
    public final int tz;
    public final List<Part> parts;

    Instance(int nameI, float x, float y, float z, float theta, int tx, int tz,
             List<Part> parts) {
      this.nameI = nameI;
      this.x = x;
      this.y = y;
      this.z = z;
      this.theta = theta;
      this.tx = tx;
      this.tz = tz;
      this.parts = parts;
    }

    /** World x via the proven formula world = local + (tail - ref) * 1920. */
    public float worldX(int refSx) {
      return x + (tx - refSx) * WorldCoordinates.SECTOR_WORLD;
    }

    /** World z via the proven formula world = local + (tail - ref) * 1920. */
    public float worldZ(int refSy) {
      return z + (tz - refSy) * WorldCoordinates.SECTOR_WORLD;
    }
  }

  private final int refSx;
  private final int refSy;
  private final List<Instance> instances;

  private MeshObjectIndex(int refSx, int refSy, List<Instance> instances) {
    this.refSx = refSx;
    this.refSy = refSy;
    this.instances = Collections.unmodifiableList(instances);
  }

  public int refSx() {
    return refSx;
  }

  public int refSy() {
    return refSy;
  }

  public List<Instance> instances() {
    return instances;
  }

  public int instanceCount() {
    return instances.size();
  }

  /** Loads the committed Phase 17 object assets, or null on any failure. */
  public static MeshObjectIndex load(AssetManager assets, int refSx, int refSy) {
    try {
      List<ModelDef> models = readModels(
          new BufferedReader(new InputStreamReader(
              assets.open("game/world/objects/models.tsv"), StandardCharsets.UTF_8)));
      List<PlacementDef> placements = readPlacements(
          new BufferedReader(new InputStreamReader(
              assets.open("game/world/objects/placements.tsv"), StandardCharsets.UTF_8)));
      return build(assets, models, placements, refSx, refSy);
    } catch (IOException e) {
      return null;
    }
  }

  private static MeshObjectIndex build(
      AssetManager assets, List<ModelDef> models, List<PlacementDef> placements,
      int refSx, int refSy) throws IOException {
    Map<Integer, List<Part>> byNameI = new HashMap<Integer, List<Part>>();
    for (ModelDef m : models) {
      byte[] msh = readBytes(assets.open("game/world/objects/" + m.mshAsset));
      StaticMeshAsset.Mesh mesh = StaticMeshAsset.parse(msh);
      Bitmap tex = BitmapFactory.decodeStream(assets.open("game/world/objects/" + m.texAsset));
      if (tex == null) {
        throw new IOException("texture decode failed: " + m.texAsset);
      }
      List<Part> list = byNameI.get(m.nameI);
      if (list == null) {
        list = new ArrayList<Part>();
        byNameI.put(m.nameI, list);
      }
      list.add(new Part(m.nameI, m.partIdx, m.material, mesh, tex));
    }
    List<Instance> instances = new ArrayList<Instance>();
    for (PlacementDef p : placements) {
      List<Part> modelParts = byNameI.get(p.nameI);
      if (modelParts == null) {
        throw new IOException("placement nameI " + p.nameI + " has no models");
      }
      instances.add(new Instance(
          p.nameI, p.x, p.y, p.z, p.theta, p.tx, p.tz,
          Collections.unmodifiableList(new ArrayList<Part>(modelParts))));
    }
    if (instances.isEmpty()) {
      throw new IOException("no object instances resolved");
    }
    return new MeshObjectIndex(refSx, refSy, instances);
  }

  private static final class ModelDef {
    final int nameI;
    final int partIdx;
    final String mshAsset;
    final String texAsset;
    final String material;

    ModelDef(int nameI, int partIdx, String mshAsset, String texAsset, String material) {
      this.nameI = nameI;
      this.partIdx = partIdx;
      this.mshAsset = mshAsset;
      this.texAsset = texAsset;
      this.material = material;
    }
  }

  private static final class PlacementDef {
    final int nameI;
    final float x;
    final float y;
    final float z;
    final float theta;
    final int tx;
    final int tz;

    PlacementDef(int nameI, float x, float y, float z, float theta, int tx, int tz) {
      this.nameI = nameI;
      this.x = x;
      this.y = y;
      this.z = z;
      this.theta = theta;
      this.tx = tx;
      this.tz = tz;
    }
  }

  private static List<ModelDef> readModels(BufferedReader in) throws IOException {
    if (in.readLine() == null) {
      throw new IOException("empty models.tsv");
    }
    List<ModelDef> out = new ArrayList<ModelDef>();
    String line;
    while ((line = in.readLine()) != null) {
      if (line.trim().isEmpty()) {
        continue;
      }
      String[] c = line.split("\t");
      if (c.length < 14) {
        throw new IOException("short models.tsv row");
      }
      out.add(new ModelDef(
          Integer.parseInt(c[0]),
          Integer.parseInt(c[3]),
          c[7],
          c[8],
          c[5]));
    }
    if (out.isEmpty()) {
      throw new IOException("no models in models.tsv");
    }
    return out;
  }

  private static List<PlacementDef> readPlacements(BufferedReader in) throws IOException {
    if (in.readLine() == null) {
      throw new IOException("empty placements.tsv");
    }
    List<PlacementDef> out = new ArrayList<PlacementDef>();
    String line;
    while ((line = in.readLine()) != null) {
      if (line.trim().isEmpty()) {
        continue;
      }
      String[] c = line.split("\t");
      if (c.length < 9) {
        throw new IOException("short placements.tsv row");
      }
      out.add(new PlacementDef(
          Integer.parseInt(c[2]),
          Float.parseFloat(c[3]),
          Float.parseFloat(c[4]),
          Float.parseFloat(c[5]),
          Float.parseFloat(c[6]),
          Integer.parseInt(c[7]),
          Integer.parseInt(c[8])));
    }
    if (out.isEmpty()) {
      throw new IOException("no placements in placements.tsv");
    }
    return out;
  }

  private static byte[] readBytes(InputStream in) throws IOException {
    try {
      ByteArrayOutputStream out = new ByteArrayOutputStream();
      byte[] buf = new byte[8192];
      int n;
      while ((n = in.read(buf)) != -1) {
        out.write(buf, 0, n);
      }
      return out.toByteArray();
    } finally {
      in.close();
    }
  }
}
