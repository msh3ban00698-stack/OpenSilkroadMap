package com.opensilkroadmap.app.world;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
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
 * Inventory of the committed real terrain height grids, parsed from
 * {@code android/app/src/main/assets/game/world/world_index.tsv} (VSHG v1
 * inventory produced by the Phase 10 pipeline from the real
 * {@code Map.pk2 /{sy}/{sx}.m} sectors).
 *
 * <p>Each entry records the sector coordinates, the grid size, the real height
 * range and the source {@code .hg} sha256. The index is the single
 * source of truth for "which real sector has a verified Android terrain asset";
 * a sector NOT in this index has no verified terrain asset and must fail
 * closed (never substituted).
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class WorldTerrainIndex {

  /** One committed real height-grid sector. */
  public static final class Entry {
    public final int sx;
    public final int sy;
    public final int size;
    public final float minH;
    public final float maxH;
    public final String sha256;

    public Entry(int sx, int sy, int size, float minH, float maxH, String sha256) {
      this.sx = sx;
      this.sy = sy;
      this.size = size;
      this.minH = minH;
      this.maxH = maxH;
      this.sha256 = sha256 == null ? "" : sha256;
    }
  }

  private final List<Entry> entries;
  private final Map<String, Entry> bySector;

  public WorldTerrainIndex(List<Entry> entries) {
    List<Entry> copy = new ArrayList<Entry>(entries);
    Collections.sort(copy, (a, b) ->
        a.sx != b.sx ? Integer.compare(a.sx, b.sx) : Integer.compare(a.sy, b.sy));
    this.entries = Collections.unmodifiableList(copy);
    Map<String, Entry> m = new HashMap<String, Entry>();
    for (Entry e : copy) {
      m.put(key(e.sx, e.sy), e);
    }
    this.bySector = Collections.unmodifiableMap(m);
  }

  public static WorldTerrainIndex parse(Reader reader) throws IOException {
    List<Entry> out = new ArrayList<Entry>();
    BufferedReader br = new BufferedReader(reader);
    String line;
    int lineNo = 0;
    while ((line = br.readLine()) != null) {
      lineNo++;
      if (line.isEmpty() || line.startsWith("#")) {
        continue;
      }
      String[] p = line.split("\t", -1);
      if (p.length < 6) {
        throw new IOException("invalid world_index line " + lineNo);
      }
      int sx = Integer.parseInt(p[0].trim());
      int sy = Integer.parseInt(p[1].trim());
      int size = Integer.parseInt(p[2].trim());
      float minH = Float.parseFloat(p[3].trim());
      float maxH = Float.parseFloat(p[4].trim());
      String sha = p[5].trim();
      out.add(new Entry(sx, sy, size, minH, maxH, sha));
    }
    return new WorldTerrainIndex(out);
  }

  public List<Entry> entries() {
    return entries;
  }

  public int size() {
    return entries.size();
  }

  public Entry find(int sx, int sy) {
    return bySector.get(key(sx, sy));
  }

  public boolean contains(int sx, int sy) {
    return bySector.containsKey(key(sx, sy));
  }

  /** First indexed entry (in sector order) inside the given sector window. */
  public Entry firstInWindow(int sx0, int sx1, int sy0, int sy1) {
    for (Entry e : entries) {
      if (e.sx >= sx0 && e.sx <= sx1 && e.sy >= sy0 && e.sy <= sy1) {
        return e;
      }
    }
    return null;
  }

  /** Android asset path of a committed height grid, e.g. {@code game/world/156x89.hg}. */
  public static String hgAssetPath(int sx, int sy) {
    return "game/world/" + sx + "x" + sy + ".hg";
  }

  private static String key(int sx, int sy) {
    return sx + "x" + sy;
  }

  /** Loads the committed {@code world_index.tsv} from a conventional Gradle cwd. */
  public static WorldTerrainIndex loadDefault() throws IOException {
    String[] paths = {
      "android/app/src/main/assets/game/world/world_index.tsv",
      "app/src/main/assets/game/world/world_index.tsv",
      "src/main/assets/game/world/world_index.tsv",
      "game/world/world_index.tsv",
    };
    for (String p : paths) {
      File f = new File(p);
      if (f.isFile()) {
        InputStream in = new FileInputStream(f);
        try {
          return parse(new InputStreamReader(in, StandardCharsets.UTF_8));
        } finally {
          in.close();
        }
      }
    }
    throw new IOException("world_index.tsv not found via default paths");
  }
}
