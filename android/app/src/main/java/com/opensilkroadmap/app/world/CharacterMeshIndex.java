package com.opensilkroadmap.app.world;

import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

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
 * Character (skinned NPC) index over the committed data-driven character
 * assets. Each character is described by a manifest
 * ({@code game/world/characters/<key>/manifest.json}) that references a
 * skeleton plus a set of mesh parts and animations, with the underlying
 * binaries stored in a shared key-based asset store:
 * {@code game/world/characters/shared/{skel,mesh,tex,anim}/}.
 *
 * <p>Every asset is derived offline from the ORIGINAL SRO data chain
 * (characterdata refid -> {@code .bsr} -> {@code .bsk} skeleton +
 * {@code .bms} parts + {@code .ban} animations + {@code .bmt} material ->
 * {@code .ddj} texture). The index exposes the real skeleton (bind pose,
 * [x,y,z,w] quaternions), the real mesh parts (skinned or static) with their
 * real textures, and the real animations (sampled on demand via
 * {@link #poseAt}).
 *
 * <p>Rendering contract: STATIC BIND POSE only. Per-vertex skinning is
 * {@code sum(w_i / sum(w)) * (R_i * v + t_i)} using each bone's proven bind
 * world rotation/translation from the skeleton. Weights are normalized by
 * their vertex sum because Phase 18 proved they are NOT normalized to 65535.
 *
 * <p>Loading is strict and fail-closed: a missing manifest, a missing
 * mesh/texture, a mesh bone name absent from the skeleton, or an unknown
 * animation returns null from {@link #load} (never a partial index).
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

  /** One animation row (metadata). */
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

  /** One character mesh part (real geometry + texture + optional skinning). */
  public static final class Part {
    public final int partIdx;
    public final String material;
    public final String ddjPath;
    public final boolean skinned;
    public final StaticMeshAsset.Mesh mesh;
    public final Bitmap texture;
    /** Bind-pose skinned positions (skinned parts only); null for static parts. */
    public final float[] bindPositions;

    Part(int partIdx, String material, String ddjPath, boolean skinned,
         StaticMeshAsset.Mesh mesh, Bitmap texture, float[] bindPositions) {
      this.partIdx = partIdx;
      this.material = material;
      this.ddjPath = ddjPath;
      this.skinned = skinned;
      this.mesh = mesh;
      this.texture = texture;
      this.bindPositions = bindPositions;
    }
  }

  private static final String CHARACTERS_ROOT = "game/world/characters/";
  private static final String SHARED = "shared/";

  private final AssetManager assets;
  private final String key;
  private final Skeleton skeleton;
  private final List<Part> parts;
  private final List<Anim> anims;
  private final Map<String, String> animSlugByName;
  private final Map<String, Map<String, Object>> animJsonCache =
      new HashMap<String, Map<String, Object>>();

  private CharacterMeshIndex(AssetManager assets, String key, Skeleton skeleton,
      List<Part> parts, List<Anim> anims, Map<String, String> animSlugByName) {
    this.assets = assets;
    this.key = key;
    this.skeleton = skeleton;
    this.parts = Collections.unmodifiableList(parts);
    this.anims = Collections.unmodifiableList(anims);
    this.animSlugByName = animSlugByName;
  }

  public Skeleton skeleton() {
    return skeleton;
  }

  public List<Part> parts() {
    return parts;
  }

  public List<Anim> anims() {
    return anims;
  }

  /**
   * Samples the committed animation JSON ({@code shared/anim/<slug>.json})
   * into a {@link Pose} at {@code tMs}. Unknown animation names fail closed
   * with {@link IOException}.
   */
  public Pose poseAt(String animName, int tMs) throws IOException {
    String slug = animSlugByName.get(animName);
    if (slug == null) {
      throw new IOException("unknown animation: " + animName);
    }
    Map<String, Object> root = animJsonCache.get(slug);
    if (root == null) {
      String path = CHARACTERS_ROOT + SHARED + "anim/" + slug + ".json";
      String text = readAll(
          new InputStreamReader(assets.open(path), StandardCharsets.UTF_8));
      root = (Map<String, Object>) new JsonParser(text).parse();
      animJsonCache.put(slug, root);
    }
    return Pose.sample(skeleton, root, tMs);
  }

  /**
   * The character's idle/stand animation (for standing still in the world), or
   * null when the manifest has no recognizable stand clip. Selection is
   * delegated to {@link IdleAnimResolver}; a null result keeps the bind pose.
   */
  public Anim idleAnim() {
    int idx = IdleAnimResolver.resolve(clipList());
    return idx < 0 ? null : anims.get(idx);
  }

  /**
   * Builds a per-entity animation state machine resolved from this character's
   * committed clip list. Each returned animator is independent, so multiple
   * characters of the same key animate with their own state and clock.
   */
  public CharacterAnimator buildAnimator() {
    return new CharacterAnimator(AnimStateResolver.resolve(clipList()));
  }

  private List<IdleAnimResolver.Clip> clipList() {
    List<IdleAnimResolver.Clip> clips = new ArrayList<IdleAnimResolver.Clip>();
    for (Anim a : anims) {
      clips.add(new IdleAnimResolver.Clip(a.name, a.durationMs));
    }
    return clips;
  }

  /**
   * Parses a committed manifest's animation list into clip descriptors (name +
   * real duration). Pure JVM, Android-free, so tests can enumerate every
   * committed manifest without an {@link AssetManager}.
   */
  public static List<IdleAnimResolver.Clip> parseManifestClips(Reader manifestReader)
      throws IOException {
    Map<String, Object> manifest = (Map<String, Object>)
        new JsonParser(readAll(manifestReader)).parse();
    List<?> animList = (List<?>) manifest.get("anims");
    List<IdleAnimResolver.Clip> clips = new ArrayList<IdleAnimResolver.Clip>();
    if (animList != null) {
      for (Object ao : animList) {
        Map<String, Object> a = (Map<String, Object>) ao;
        clips.add(new IdleAnimResolver.Clip(
            asString(a.get("name")), asInt(a.get("duration_ms"))));
      }
    }
    return clips;
  }

  /**
   * Returns the shared asset paths referenced by a committed manifest
   * (skeleton, meshes, textures, animations) as relative paths under
   * {@code game/world/characters/}. Pure JVM, Android-free, so the
   * enumeration test can verify every referenced file is committed.
   */
  public static List<String> parseManifestAssetPaths(Reader manifestReader)
      throws IOException {
    Map<String, Object> manifest = (Map<String, Object>)
        new JsonParser(readAll(manifestReader)).parse();
    List<String> refs = new ArrayList<String>();
    Object skel = manifest.get("skeleton");
    if (skel != null) {
      refs.add("shared/skel/" + asString(skel) + ".json");
    }
    List<?> meshes = (List<?>) manifest.get("meshes");
    if (meshes != null) {
      for (Object mo : meshes) {
        Map<String, Object> m = (Map<String, Object>) mo;
        refs.add("shared/mesh/" + asString(m.get("msh")) + ".msh");
        refs.add("shared/tex/" + asString(m.get("tex")) + ".png");
      }
    }
    List<?> animList = (List<?>) manifest.get("anims");
    if (animList != null) {
      for (Object ao : animList) {
        Map<String, Object> a = (Map<String, Object>) ao;
        refs.add("shared/anim/" + asString(a.get("anim")) + ".json");
      }
    }
    return refs;
  }

  /**
   * Loads a character by key, or null on any failure (fail-closed).
   */
  public static CharacterMeshIndex load(AssetManager assets, String key) {
    try {
      return build(assets, key);
    } catch (IOException e) {
      return null;
    }
  }

  public static CharacterMeshIndex load(AssetManager assets, String key,
                                        int refSx, int refSy) {
    return load(assets, key);
  }

  private static CharacterMeshIndex build(AssetManager assets, String key)
      throws IOException {
    String root = CHARACTERS_ROOT + key + "/";
    Map<String, Object> manifest = (Map<String, Object>)
        new JsonParser(readAll(new InputStreamReader(
            assets.open(root + "manifest.json"), StandardCharsets.UTF_8))).parse();

    String skelSlug = asString(manifest.get("skeleton"));
    Skeleton skeleton = parseSkeleton(new InputStreamReader(
        assets.open(CHARACTERS_ROOT + SHARED + "skel/" + skelSlug + ".json"),
        StandardCharsets.UTF_8));

    List<?> meshes = (List<?>) manifest.get("meshes");
    List<Part> parts = new ArrayList<Part>();
    int partIdx = 0;
    for (Object mo : meshes) {
      Map<String, Object> m = (Map<String, Object>) mo;
      String mshSlug = asString(m.get("msh"));
      String texSlug = asString(m.get("tex"));
      boolean skinned = m.get("skinned") == Boolean.TRUE;
      byte[] msh = readBytes(assets.open(
          CHARACTERS_ROOT + SHARED + "mesh/" + mshSlug + ".msh"));
      Bitmap tex = BitmapFactory.decodeStream(assets.open(
          CHARACTERS_ROOT + SHARED + "tex/" + texSlug + ".png"));
      if (tex == null) {
        throw new IOException("texture decode failed: " + texSlug);
      }
      float[] bindPositions = null;
      if (skinned) {
        StaticMeshAsset.SkinnedMesh sm = StaticMeshAsset.parseSkinned(msh);
        bindPositions = skinnedBindPositions(sm, skeleton);
        parts.add(new Part(partIdx++, asString(m.get("material")),
            asString(m.get("ddj_path")), true, sm, tex, bindPositions));
      } else {
        StaticMeshAsset.Mesh mesh = StaticMeshAsset.parse(msh);
        parts.add(new Part(partIdx++, asString(m.get("material")),
            asString(m.get("ddj_path")), false, mesh, tex, null));
      }
    }
    if (parts.isEmpty()) {
      throw new IOException("no character mesh parts");
    }

    List<?> animList = (List<?>) manifest.get("anims");
    List<Anim> anims = new ArrayList<Anim>();
    Map<String, String> animSlugByName = new HashMap<String, String>();
    for (Object ao : animList) {
      Map<String, Object> a = (Map<String, Object>) ao;
      String name = asString(a.get("name"));
      String animSlug = asString(a.get("anim"));
      animSlugByName.put(name, animSlug);
      anims.add(new Anim(asString(a.get("ban_path")), name,
          asInt(a.get("duration_ms")), asInt(a.get("keyframes")),
          asInt(a.get("channels")), animSlug));
    }

    return new CharacterMeshIndex(assets, key, skeleton, parts, anims, animSlugByName);
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
