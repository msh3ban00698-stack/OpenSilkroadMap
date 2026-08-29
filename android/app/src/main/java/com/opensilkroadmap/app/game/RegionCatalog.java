package com.opensilkroadmap.app.game;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Parses the derived region catalog TSV produced by
 * {@code scripts/build_region_catalog.py}. Line format:
 *
 * <pre>
 * # comment lines are ignored
 * &lt;FIELD|TOWN&gt;\t&lt;name&gt;\t&lt;code&gt;\t&lt;cell tokens&gt;
 * </pre>
 *
 * <p>Each cell token is {@code x:y} (ALL) or {@code x:y:R:x0:y0:x1:y1}
 * (RECT, parameters preserved verbatim). No Android dependencies; pure JVM.
 */
public final class RegionCatalog {
  private final List<RegionInfo> regions;
  private final int cellCount;

  public RegionCatalog(List<RegionInfo> regions) {
    this.regions = Collections.unmodifiableList(new ArrayList<>(regions));
    int n = 0;
    for (RegionInfo r : regions) {
      n += r.cells.size();
    }
    this.cellCount = n;
  }

  public static RegionCatalog parse(Reader reader) throws IOException {
    List<RegionInfo> out = new ArrayList<>();
    BufferedReader br = new BufferedReader(reader);
    String line;
    int lineNo = 0;
    while ((line = br.readLine()) != null) {
      lineNo++;
      if (line.isEmpty() || line.startsWith("#")) {
        continue;
      }
      String[] parts = line.split("\t", -1);
      if (parts.length < 4) {
        throw new IOException("invalid region catalog line " + lineNo);
      }
      RegionInfo.Type type = RegionInfo.Type.parse(parts[0].trim());
      String name = parts[1].trim();
      String code = parts[2].trim();
      List<RegionInfo.Cell> cells = new ArrayList<>();
      for (String token : parts[3].split(",")) {
        cells.add(parseCell(token));
      }
      out.add(new RegionInfo(type, name, code, cells));
    }
    return new RegionCatalog(out);
  }

  private static RegionInfo.Cell parseCell(String token) throws IOException {
    String[] p = token.split(":");
    int x = Integer.parseInt(p[0]);
    int y = Integer.parseInt(p[1]);
    String kind = "ALL";
    int[] extra = new int[0];
    if (p.length >= 3 && p[2].equals("R")) {
      kind = "RECT";
      int[] e = new int[p.length - 3];
      for (int i = 3; i < p.length; i++) {
        e[i - 3] = Integer.parseInt(p[i]);
      }
      extra = e;
    }
    return new RegionInfo.Cell(x, y, kind, extra);
  }

  public List<RegionInfo> regions() {
    return regions;
  }

  /** First region (in file order) that contains the given cell, or null. */
  public RegionInfo regionForCell(int x, int y) {
    for (RegionInfo r : regions) {
      for (RegionInfo.Cell c : r.cells) {
        if (c.x == x && c.y == y) {
          return r;
        }
      }
    }
    return null;
  }

  public int sectionCount() {
    return regions.size();
  }

  public int cellCount() {
    return cellCount;
  }

  /** Loads the committed catalog from a conventional Gradle working directory. */
  public static RegionCatalog loadDefault() throws IOException {
    String[] candidates = {
      "src/main/assets/game/regions.tsv",
      "../src/main/assets/game/regions.tsv",
      "app/src/main/assets/game/regions.tsv",
      "../app/src/main/assets/game/regions.tsv",
    };
    for (String path : candidates) {
      java.io.File f = new java.io.File(path);
      if (f.isFile()) {
        return parse(new java.io.FileReader(f));
      }
    }
    throw new IOException("regions.tsv not found via default paths");
  }
}
