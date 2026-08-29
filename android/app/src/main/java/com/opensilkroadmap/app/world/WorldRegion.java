package com.opensilkroadmap.app.world;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * A named world region and its sector window, derived read-only from the real
 * {@code Data.pk2 /RegionInfo.txt} during Phase 10 (committed as
 * {@code android/app/src/main/assets/game/world/world_regions.tsv}).
 *
 * <p>Each region exposes its window ({@code sx0..sx1}, {@code sy0..sy1}), its
 * reference sector and the number of cells listed in RegionInfo.txt. Windows
 * are bounding boxes of the real RegionInfo cells and may include water and
 * other non-walkable sectors; nothing here is invented geometry.
 */
public final class WorldRegion {
  public final String type;
  public final String name;
  public final String code;
  public final int sx0;
  public final int sx1;
  public final int sy0;
  public final int sy1;
  public final int refSx;
  public final int refSy;
  public final int cells;

  public WorldRegion(
      String type, String name, String code,
      int sx0, int sx1, int sy0, int sy1,
      int refSx, int refSy, int cells) {
    this.type = type;
    this.name = name;
    this.code = code;
    this.sx0 = sx0;
    this.sx1 = sx1;
    this.sy0 = sy0;
    this.sy1 = sy1;
    this.refSx = refSx;
    this.refSy = refSy;
    this.cells = cells;
  }

  public boolean containsSector(int sx, int sy) {
    return sx >= sx0 && sx <= sx1 && sy >= sy0 && sy <= sy1;
  }

  /** Parse the committed {@code world_regions.tsv}. */
  public static List<WorldRegion> load(ReaderSupplier supplier) throws IOException {
    List<WorldRegion> out = new ArrayList<WorldRegion>();
    BufferedReader br =
        new BufferedReader(new InputStreamReader(supplier.open(), StandardCharsets.UTF_8));
    try {
      String line;
      while ((line = br.readLine()) != null) {
        if (line.isEmpty() || line.startsWith("#")) {
          continue;
        }
        String[] p = line.split("\t");
        if (p.length < 10) {
          continue;
        }
        out.add(new WorldRegion(
            p[0], p[1], p[2],
            Integer.parseInt(p[3]), Integer.parseInt(p[4]),
            Integer.parseInt(p[5]), Integer.parseInt(p[6]),
            Integer.parseInt(p[7]), Integer.parseInt(p[8]),
            Integer.parseInt(p[9])));
      }
    } finally {
      br.close();
    }
    return out;
  }

  /** Read regions from the working directory's committed asset file. */
  public static List<WorldRegion> loadDefault() throws IOException {
    return load(new DefaultReader());
  }

  public static Map<String, WorldRegion> indexByName(List<WorldRegion> regions) {
    Map<String, WorldRegion> map = new HashMap<String, WorldRegion>();
    for (WorldRegion r : regions) {
      map.put(r.name, r);
    }
    return map;
  }

  /** Abstraction so JVM tests can read from the repo without an AssetManager. */
  public interface ReaderSupplier {
    InputStream open() throws IOException;
  }

  private static final class DefaultReader implements ReaderSupplier {
    private static final String[] PATHS = {
      "android/app/src/main/assets/game/world/world_regions.tsv",
      "app/src/main/assets/game/world/world_regions.tsv",
      "src/main/assets/game/world/world_regions.tsv",
      "game/world/world_regions.tsv",
    };

    @Override
    public InputStream open() throws IOException {
      for (String p : PATHS) {
        java.io.File f = new java.io.File(p);
        if (f.isFile()) {
          return new java.io.FileInputStream(f);
        }
      }
      throw new IOException("world_regions.tsv not found via default paths");
    }
  }
}
