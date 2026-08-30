package com.opensilkroadmap.app.world;

import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Character (skinned NPC) index over the committed Phase 18 rendering assets
 * ({@code game/world/characters/bandit/}: {@code skeleton.json},
 * {@code meshes.tsv}, {@code mesh/*.msh} (MSH v2), {@code tex/*.png},
 * {@code npc_placements.tsv}, {@code anims.tsv}).
 *
 * <p>Every asset is derived offline from the ORIGINAL data chain proven in
 * Phase 18 (characterdata refid -> {@code .bsr} -> {@code .bsk} skeleton +
 * {@code .bms} parts + {@code .ban} animations + {@code .bmt} material ->
 * {@code .ddj} texture; npcpos -> world coordinates). The index exposes the
 * real skeleton (bind pose, [x,y,z,w] quaternions), the real skinned mesh
 * parts with their real textures, and the real NPC world placements.
 *
 * <p>Rendering contract: STATIC BIND POSE only. Per-vertex skinning is
 * {@code sum(w_i / sum(w)) * (R_i * v + t_i)} using each bone's proven bind
 * world rotation/translation from {@code skeleton.json}. Weights are
 * normalized by their vertex sum because Phase 18 proved they are NOT
 * normalized to 65535. Animation playback is UNKNOWN (only the first keyframe
 * is committed per animation); {@link #anims()} exposes the proven metadata.
 * Placement heading is UNKNOWN (npcpos carries no theta), so {@code theta}
 * is 0.
 *
 * <p>Loading is strict and fail-closed: a missing mesh/texture, a mesh bone
 * name absent from the skeleton, or a meshes.tsv/mesh count mismatch returns
 * null from {@link #load} (never a partial index).
 */
public final class CharacterMeshIndex {

  /** One bone of the real character skeleton (bind pose, xyzw quaternions). */
  public static final class Bone {
    public final String name;
    public final String parent;
    public final String[] children;
    /** Local rotation relative to the parent (4 floats, [x,y,z,w]). */
    public final float[] rotParent;
    /** Local translation relative to the parent (3 floats). */
    public final float[] trParent;
    /** World-space bind rotation (4 floats, [x,y,z,w]). */
    public final float[] bindWorldRot;
    /** World-space bind position (3 floats). */
    public final float[] bindWorldPos;

    Bone(String name, String parent, String[] children,
         float[] rotParent, float[] trParent, float[] bindWorldRot, float[] bindWorldPos) {
      this.name = name;
      this.parent = parent;
      this.children = children;
      this.rotParent = rotParent;
      this.trParent = trParent;
      this.bindWorldRot = bindWorldRot;
      this.bindWorldPos = bindWorldPos;
    }
  }

  /** The full character skeleton parsed from {@code skeleton.json}. */
  public static final class Skeleton {
    public final String path;
    public final int boneCount;
    public final String quaternionConvention;
    public final Bone[] bones;
    private final Map<String, Integer> indexByName;

    Skeleton(String path, int boneCount, String quaternionConvention, Bone[] bones) {
      this.path = path;
      this.boneCount = boneCount;
      this.quaternionConvention = quaternionConvention;
      this.bones = bones;
      this.indexByName = new HashMap<String, Integer>();
      for (int i = 0; i < bones.length; i++) {
        indexByName.put(bones[i].name, Integer.valueOf(i));
      }
    }

    public Bone bone(int index) {
      return bones[index];
    }

    /** Index of a bone by name, or -1 when absent. */
    public int boneIndex(String name) {
      Integer v = indexByName.get(name);
      return v == null ? -1 : v.intValue();
    }
  }

  /** One committed skinned mesh part row of {@code meshes.tsv}. */
  public static final class MeshRow {
    public final int partIdx;
    public final String bmsPath;
    public final String material;
    public final String ddjPath;
    public final String mshAsset;
    public final String texAsset;
    public final int vcount;
    public final int tcount;
    public final int skinRecords;
    public final int boneCount;

    MeshRow(int partIdx, String bmsPath, String material, String ddjPath,
            String mshAsset, String texAsset, int vcount, int tcount,
            int skinRecords, int boneCount) {
      this.partIdx = partIdx;
      this.bmsPath = bmsPath;
      this.material = material;
      this.ddjPath = ddjPath;
      this.mshAsset = mshAsset;
      this.texAsset = texAsset;
      this.vcount = vcount;
      this.tcount = tcount;
      this.skinRecords = skinRecords;
      this.boneCount = boneCount;
    }
  }

  /** One real NPC placement row of {@code npc_placements.tsv}. */
  public static final class PlacementDef {
    public final String refid;
    public final int region;
    public final int sectorSx;
    public final int sectorSy;
    public final float localX;
    public final float localZ;
    /** Absolute world X (precomputed at build time with ref sector 156x89). */
    public final float worldX;
    /** Absolute world Z (precomputed at build time with ref sector 156x89). */
    public final float worldZ;
    public final float height;

    PlacementDef(String refid, int region, int sectorSx, int sectorSy,
                 float localX, float localZ, float worldX, float worldZ, float height) {
      this.refid = refid;
      this.region = region;
      this.sectorSx = sectorSx;
      this.sectorSy = sectorSy;
      this.localX = localX;
      this.localZ = localZ;
      this.worldX = worldX;
      this.worldZ = worldZ;
      this.height = height;
    }
  }

  /** One animation row of {@code anims.tsv} (metadata; playback UNKNOWN). */
  public static final class Anim {
    public final String banPath;
    public final String name;
    public final int durationMs;
    public final int keyframes;
    public final int channels;
    /** Committed keyframe JSON asset, or "" when not committed. */
    public final String animAsset;

    Anim(String banPath, String name, int durationMs, int keyframes,
         int channels, String animAsset) {
      this.banPath = banPath;
      this.name = name;
      this.durationMs = durationMs;
      this.keyframes = keyframes;
      this.channels = channels;
      this.animAsset = animAsset;
    }
  }

  /** One skinned mesh part (real geometry + real texture + bind positions). */
  public static final class Part {
    public final int partIdx;
    public final String material;
    public final String ddjPath;
    public final StaticMeshAsset.SkinnedMesh mesh;
    public final Bitmap texture;
    /** 3 floats per vertex: bind-pose skinned position (character-local). */
    public final float[] bindPositions;

    Part(int partIdx, String material, String ddjPath,
         StaticMeshAsset.SkinnedMesh mesh, Bitmap texture, float[] bindPositions) {
      this.partIdx = partIdx;
      this.material = material;
      this.ddjPath = ddjPath;
      this.mesh = mesh;
      this.texture = texture;
      this.bindPositions = bindPositions;
    }
  }

  /** One character instance at a real NPC world placement. */
  public static final class Instance {
    public final String refid;
    public final int region;
    public final int sectorSx;
    public final int sectorSy;
    public final float localX;
    public final float localZ;
    public final float worldX;
    public final float worldZ;
    public final float height;
    public final List<Part> parts;

    Instance(PlacementDef p, List<Part> parts) {
      this.refid = p.refid;
      this.region = p.region;
      this.sectorSx = p.sectorSx;
      this.sectorSy = p.sectorSy;
      this.localX = p.localX;
      this.localZ = p.localZ;
      this.worldX = p.worldX;
      this.worldZ = p.worldZ;
      this.height = p.height;
      this.parts = parts;
    }

    /** Placement heading. UNKNOWN in npcpos (no theta column); always 0. */
    public float theta() {
      return 0f;
    }
  }

  private static final String CHARACTER_DIR = "game/world/characters/bandit/";

  private final Skeleton skeleton;
  private final List<Part> parts;
  private final List<Instance> instances;
  private final List<Anim> anims;

  private CharacterMeshIndex(
      Skeleton skeleton, List<Part> parts, List<Instance> instances, List<Anim> anims) {
    this.skeleton = skeleton;
    this.parts = Collections.unmodifiableList(parts);
    this.instances = Collections.unmodifiableList(instances);
    this.anims = Collections.unmodifiableList(anims);
  }

  public Skeleton skeleton() {
    return skeleton;
  }

  public List<Part> parts() {
    return parts;
  }

  public List<Instance> instances() {
    return instances;
  }

  public int instanceCount() {
    return instances.size();
  }

  public List<Anim> anims() {
    return anims;
  }

  /**
   * Loads the committed bandit character assets, or null on any failure.
   *
   * <p>{@code refSx}/{@code refSy} mirror the {@link MeshObjectIndex#load}
   * signature for parity; the committed placements carry absolute world
   * coordinates precomputed offline with ref sector 156x89, so the values are
   * not re-derived here.
   */
  public static CharacterMeshIndex load(AssetManager assets, int refSx, int refSy) {
    try {
      return build(assets);
    } catch (IOException e) {
      return null;
    }
  }

  private static CharacterMeshIndex build(AssetManager assets) throws IOException {
    Skeleton skeleton = parseSkeleton(
        new InputStreamReader(assets.open(CHARACTER_DIR + "skeleton.json"), StandardCharsets.UTF_8));
    List<MeshRow> rows = parseMeshes(new BufferedReader(
        new InputStreamReader(assets.open(CHARACTER_DIR + "meshes.tsv"), StandardCharsets.UTF_8)));
    List<PlacementDef> placements = parsePlacements(new BufferedReader(
        new InputStreamReader(assets.open(CHARACTER_DIR + "npc_placements.tsv"),
            StandardCharsets.UTF_8)));
    List<Anim> anims = parseAnims(new BufferedReader(
        new InputStreamReader(assets.open(CHARACTER_DIR + "anims.tsv"), StandardCharsets.UTF_8)));

    List<Part> parts = new ArrayList<Part>();
    for (MeshRow r : rows) {
      byte[] msh = readBytes(assets.open(CHARACTER_DIR + r.mshAsset));
      StaticMeshAsset.SkinnedMesh mesh = StaticMeshAsset.parseSkinned(msh);
      if (mesh.vertexCount != r.vcount || mesh.triangleCount != r.tcount
          || mesh.boneNames.length != r.boneCount) {
        throw new IOException("meshes.tsv/mesh mismatch for " + r.mshAsset);
      }
      Bitmap tex = BitmapFactory.decodeStream(assets.open(CHARACTER_DIR + r.texAsset));
      if (tex == null) {
        throw new IOException("texture decode failed: " + r.texAsset);
      }
      parts.add(new Part(r.partIdx, r.material, r.ddjPath, mesh, tex,
          skinnedBindPositions(mesh, skeleton)));
    }
    if (parts.isEmpty()) {
      throw new IOException("no character mesh parts");
    }
    List<Part> shared = Collections.unmodifiableList(new ArrayList<Part>(parts));
    List<Instance> instances = new ArrayList<Instance>();
    for (PlacementDef p : placements) {
      instances.add(new Instance(p, shared));
    }
    if (instances.isEmpty()) {
      throw new IOException("no character placements");
    }
    return new CharacterMeshIndex(skeleton, parts, instances, anims);
  }

  /**
   * Computes the bind-pose skinned position of every vertex:
   * {@code sum_i (w_i / sum(w)) * (R_i * v + t_i)} with the bone's bind world
   * rotation/translation. Fail-closed when a mesh bone is absent from the
   * skeleton (Phase 18 proved mesh bones are always a subset).
   */
  public static float[] skinnedBindPositions(
      StaticMeshAsset.SkinnedMesh mesh, Skeleton skeleton) throws IOException {
    int[] boneMap = new int[mesh.boneNames.length];
    for (int k = 0; k < boneMap.length; k++) {
      int idx = skeleton.boneIndex(mesh.boneNames[k]);
      if (idx < 0) {
        throw new IOException("mesh bone '" + mesh.boneNames[k]
            + "' not in skeleton");
      }
      boneMap[k] = idx;
    }
    int n = mesh.vertexCount;
    float[] out = new float[n * 3];
    float[] rot = new float[3];
    float[] p = new float[3];
    for (int i = 0; i < n; i++) {
      p[0] = mesh.positions[i * 3];
      p[1] = mesh.positions[i * 3 + 1];
      p[2] = mesh.positions[i * 3 + 2];
      int b1 = mesh.bone1[i];
      int w1 = mesh.weight1[i];
      int b2 = mesh.bone2[i];
      int w2 = mesh.weight2[i];
      int sum = w1 + w2;
      float ox = 0f;
      float oy = 0f;
      float oz = 0f;
      if (b1 < boneMap.length && sum > 0) {
        Bone bone = skeleton.bone(boneMap[b1]);
        rotate(p, bone.bindWorldRot, rot);
        float f = (float) w1 / (float) sum;
        ox += f * (rot[0] + bone.bindWorldPos[0]);
        oy += f * (rot[1] + bone.bindWorldPos[1]);
        oz += f * (rot[2] + bone.bindWorldPos[2]);
      }
      if (b2 < boneMap.length && w2 > 0) {
        Bone bone = skeleton.bone(boneMap[b2]);
        rotate(p, bone.bindWorldRot, rot);
        float f = (float) w2 / (float) sum;
        ox += f * (rot[0] + bone.bindWorldPos[0]);
        oy += f * (rot[1] + bone.bindWorldPos[1]);
        oz += f * (rot[2] + bone.bindWorldPos[2]);
      }
      out[i * 3] = ox;
      out[i * 3 + 1] = oy;
      out[i * 3 + 2] = oz;
    }
    return out;
  }

  /** Rotates a vector by a unit quaternion [x,y,z,w] (xyzw convention). */
  private static void rotate(float[] v, float[] q, float[] out) {
    float x = q[0];
    float y = q[1];
    float z = q[2];
    float w = q[3];
    float vx = v[0];
    float vy = v[1];
    float vz = v[2];
    float cx = y * vz - z * vy;
    float cy = z * vx - x * vz;
    float cz = x * vy - y * vx;
    float dx = y * cz - z * cy;
    float dy = z * cx - x * cz;
    float dz = x * cy - y * cx;
    out[0] = vx + 2f * w * cx + 2f * dx;
    out[1] = vy + 2f * w * cy + 2f * dy;
    out[2] = vz + 2f * w * cz + 2f * dz;
  }

  public static Skeleton parseSkeleton(Reader in) throws IOException {
    Map<String, Object> root = (Map<String, Object>) new JsonParser(readAll(in)).parse();
    String path = asString(root.get("path"));
    int boneCount = asInt(root.get("bone_count"));
    String convention = asString(root.get("quaternion_convention"));
    List<?> bones = (List<?>) root.get("bones");
    if (bones == null || bones.size() != boneCount) {
      throw new IOException("skeleton bone_count mismatch");
    }
    Bone[] arr = new Bone[boneCount];
    for (int i = 0; i < boneCount; i++) {
      Map<String, Object> b = (Map<String, Object>) bones.get(i);
      arr[i] = new Bone(
          asString(b.get("name")),
          asString(b.get("parent")),
          asStringArray(b.get("children")),
          asFloatArray(b.get("rot_parent"), 4),
          asFloatArray(b.get("tr_parent"), 3),
          asFloatArray(b.get("bind_world_rot"), 4),
          asFloatArray(b.get("bind_world_pos"), 3));
    }
    return new Skeleton(path, boneCount, convention, arr);
  }

  public static List<MeshRow> parseMeshes(BufferedReader in) throws IOException {
    if (in.readLine() == null) {
      throw new IOException("empty meshes.tsv");
    }
    List<MeshRow> out = new ArrayList<MeshRow>();
    String line;
    while ((line = in.readLine()) != null) {
      if (line.trim().isEmpty()) {
        continue;
      }
      String[] c = line.split("\t");
      if (c.length < 10) {
        throw new IOException("short meshes.tsv row");
      }
      out.add(new MeshRow(
          Integer.parseInt(c[0]), c[1], c[2], c[3], c[4], c[5],
          Integer.parseInt(c[6]), Integer.parseInt(c[7]),
          Integer.parseInt(c[8]), Integer.parseInt(c[9])));
    }
    if (out.isEmpty()) {
      throw new IOException("no meshes in meshes.tsv");
    }
    return out;
  }

  public static List<PlacementDef> parsePlacements(BufferedReader in) throws IOException {
    if (in.readLine() == null) {
      throw new IOException("empty npc_placements.tsv");
    }
    List<PlacementDef> out = new ArrayList<PlacementDef>();
    String line;
    while ((line = in.readLine()) != null) {
      if (line.trim().isEmpty()) {
        continue;
      }
      String[] c = line.split("\t");
      if (c.length < 8) {
        throw new IOException("short npc_placements.tsv row");
      }
      String[] sector = c[2].split("x");
      if (sector.length != 2) {
        throw new IOException("bad sector cell: " + c[2]);
      }
      out.add(new PlacementDef(
          c[0],
          Integer.parseInt(c[1]),
          Integer.parseInt(sector[0]),
          Integer.parseInt(sector[1]),
          Float.parseFloat(c[3]),
          Float.parseFloat(c[4]),
          Float.parseFloat(c[5]),
          Float.parseFloat(c[6]),
          Float.parseFloat(c[7])));
    }
    if (out.isEmpty()) {
      throw new IOException("no placements in npc_placements.tsv");
    }
    return out;
  }

  public static List<Anim> parseAnims(BufferedReader in) throws IOException {
    if (in.readLine() == null) {
      throw new IOException("empty anims.tsv");
    }
    List<Anim> out = new ArrayList<Anim>();
    String line;
    while ((line = in.readLine()) != null) {
      if (line.trim().isEmpty()) {
        continue;
      }
      String[] c = line.split("\t");
      if (c.length < 6) {
        throw new IOException("short anims.tsv row");
      }
      out.add(new Anim(c[0], c[1], Integer.parseInt(c[2]),
          Integer.parseInt(c[3]), Integer.parseInt(c[4]), c[5]));
    }
    return out;
  }

  private static String asString(Object o) throws IOException {
    if (!(o instanceof String)) {
      throw new IOException("expected string, got " + (o == null ? "null" : o.getClass().getSimpleName()));
    }
    return (String) o;
  }

  private static int asInt(Object o) throws IOException {
    if (!(o instanceof Number)) {
      throw new IOException("expected number");
    }
    return ((Number) o).intValue();
  }

  private static String[] asStringArray(Object o) throws IOException {
    if (!(o instanceof List)) {
      throw new IOException("expected array");
    }
    List<?> list = (List<?>) o;
    String[] arr = new String[list.size()];
    for (int i = 0; i < arr.length; i++) {
      if (!(list.get(i) instanceof String)) {
        throw new IOException("expected string element");
      }
      arr[i] = (String) list.get(i);
    }
    return arr;
  }

  private static float[] asFloatArray(Object o, int expected) throws IOException {
    if (!(o instanceof List)) {
      throw new IOException("expected array");
    }
    List<?> list = (List<?>) o;
    if (list.size() != expected) {
      throw new IOException("expected " + expected + " floats");
    }
    float[] arr = new float[expected];
    for (int i = 0; i < expected; i++) {
      if (!(list.get(i) instanceof Number)) {
        throw new IOException("expected number element");
      }
      arr[i] = ((Number) list.get(i)).floatValue();
    }
    return arr;
  }

  private static String readAll(Reader in) throws IOException {
    StringBuilder sb = new StringBuilder();
    char[] buf = new char[8192];
    int n;
    while ((n = in.read(buf)) != -1) {
      sb.append(buf, 0, n);
    }
    return sb.toString();
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

  /**
   * Minimal structural JSON parser covering the committed asset JSON (objects,
   * arrays, strings, numbers incl. scientific notation, booleans, null).
   * Android-free so the committed assets can be parsed in JVM tests.
   */
  private static final class JsonParser {
    private final String s;
    private int i;

    JsonParser(String s) {
      this.s = s;
      this.i = 0;
    }

    Object parse() throws IOException {
      skipWs();
      Object v = value();
      skipWs();
      if (i != s.length()) {
        throw err("trailing data");
      }
      return v;
    }

    private Object value() throws IOException {
      if (i >= s.length()) {
        throw err("unexpected end of input");
      }
      char c = s.charAt(i);
      switch (c) {
        case '{':
          return object();
        case '[':
          return array();
        case '"':
          return string();
        case 't':
          expect("true");
          return Boolean.TRUE;
        case 'f':
          expect("false");
          return Boolean.FALSE;
        case 'n':
          expect("null");
          return null;
        default:
          return number();
      }
    }

    private Map<String, Object> object() throws IOException {
      Map<String, Object> m = new HashMap<String, Object>();
      i++; // '{'
      skipWs();
      if (peek() == '}') {
        i++;
        return m;
      }
      while (true) {
        skipWs();
        String key = string();
        skipWs();
        if (peek() != ':') {
          throw err("expected ':'");
        }
        i++;
        skipWs();
        m.put(key, value());
        skipWs();
        char c = peek();
        if (c == ',') {
          i++;
          continue;
        }
        if (c == '}') {
          i++;
          return m;
        }
        throw err("expected ',' or '}'");
      }
    }

    private List<Object> array() throws IOException {
      List<Object> l = new ArrayList<Object>();
      i++; // '['
      skipWs();
      if (peek() == ']') {
        i++;
        return l;
      }
      while (true) {
        skipWs();
        l.add(value());
        skipWs();
        char c = peek();
        if (c == ',') {
          i++;
          continue;
        }
        if (c == ']') {
          i++;
          return l;
        }
        throw err("expected ',' or ']'");
      }
    }

    private String string() throws IOException {
      if (peek() != '"') {
        throw err("expected string");
      }
      i++;
      StringBuilder sb = new StringBuilder();
      while (true) {
        if (i >= s.length()) {
          throw err("unterminated string");
        }
        char c = s.charAt(i++);
        if (c == '"') {
          return sb.toString();
        }
        if (c == '\\') {
          if (i >= s.length()) {
            throw err("bad escape");
          }
          char e = s.charAt(i++);
          switch (e) {
            case '"':
              sb.append('"');
              break;
            case '\\':
              sb.append('\\');
              break;
            case '/':
              sb.append('/');
              break;
            case 'b':
              sb.append('\b');
              break;
            case 'f':
              sb.append('\f');
              break;
            case 'n':
              sb.append('\n');
              break;
            case 'r':
              sb.append('\r');
              break;
            case 't':
              sb.append('\t');
              break;
            default:
              throw err("bad escape");
          }
        } else {
          sb.append(c);
        }
      }
    }

    private Double number() throws IOException {
      int start = i;
      while (i < s.length()) {
        char c = s.charAt(i);
        if (c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E'
            || (c >= '0' && c <= '9')) {
          i++;
        } else {
          break;
        }
      }
      if (start == i) {
        throw err("bad number");
      }
      String tok = s.substring(start, i);
      try {
        return Double.valueOf(tok);
      } catch (NumberFormatException e) {
        throw err("bad number");
      }
    }

    private void expect(String token) throws IOException {
      if (i + token.length() > s.length()
          || !s.startsWith(token, i)) {
        throw err("expected " + token);
      }
      i += token.length();
    }

    private void skipWs() {
      while (i < s.length()) {
        char c = s.charAt(i);
        if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
          i++;
        } else {
          break;
        }
      }
    }

    private char peek() throws IOException {
      if (i >= s.length()) {
        throw err("unexpected end of input");
      }
      return s.charAt(i);
    }

    private IOException err(String msg) {
      return new IOException("skeleton.json: " + msg);
    }
  }
}
