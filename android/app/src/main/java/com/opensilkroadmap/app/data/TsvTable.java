package com.opensilkroadmap.app.data;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Generic tab-separated data loader for the normalized Phase 11/12 game TSV
 * assets under {@code src/main/assets/game/textdata/}.
 *
 * <p>Source textdata files have no header row; columns are positional. This
 * loader preserves every cell verbatim (no trimming, no re-encoding) and skips
 * blank lines plus {@code #} / {@code //} comment lines (both are present in
 * the real source data). Column semantics are documented per dataset by the
 * typed readers in this package and in {@code TEXTDATA_SCHEMAS.json}; unverified
 * columns are reachable only as raw cells. No Android dependencies; pure JVM.
 */
public final class TsvTable {
  private final String name;
  private final List<String[]> rows;

  public TsvTable(String name, List<String[]> rows) {
    this.name = name;
    this.rows = Collections.unmodifiableList(new ArrayList<>(rows));
  }

  public static TsvTable parse(String name, Reader reader) throws IOException {
    List<String[]> out = new ArrayList<>();
    BufferedReader br = new BufferedReader(reader);
    String line;
    while ((line = br.readLine()) != null) {
      String trimmed = line.trim();
      if (trimmed.isEmpty() || trimmed.startsWith("#") || trimmed.startsWith("//")) {
        continue;
      }
      out.add(line.split("\t", -1));
    }
    return new TsvTable(name, out);
  }

  public static TsvTable loadDefault(String assetName) throws IOException {
    String[] candidates = {
      "src/main/assets/game/textdata/" + assetName,
      "../src/main/assets/game/textdata/" + assetName,
      "app/src/main/assets/game/textdata/" + assetName,
      "../app/src/main/assets/game/textdata/" + assetName,
    };
    for (String path : candidates) {
      File f = new File(path);
      if (f.isFile()) {
        return parse(assetName, new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8));
      }
    }
    throw new IOException(assetName + " not found via default paths");
  }

  public String name() {
    return name;
  }

  public int rowCount() {
    return rows.size();
  }

  public List<String[]> rows() {
    return rows;
  }

  public static String strAt(String[] row, int i) {
    return i < row.length ? row[i] : "";
  }

  public static int intAt(String[] row, int i) {
    String v = strAt(row, i).trim();
    return v.isEmpty() ? 0 : Integer.parseInt(v);
  }

  public static float floatAt(String[] row, int i) {
    String v = strAt(row, i).trim();
    return v.isEmpty() ? 0f : Float.parseFloat(v);
  }
}
