package com.opensilkroadmap.app.world;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Server region → zone lookup over the committed derived catalog
 * {@code android/app/src/main/assets/game/world/region_zone.tsv}.
 *
 * <p>The TSV is produced by {@code scripts/build_region_ref_catalog.py} from
 * the real server table {@code SR_GameRefData/RefRegion.txt} (UTF-16LE, 21
 * columns, no header row). Every row is one world region id:
 *
 * <pre>
 * # format: &lt;region_id&gt;\t&lt;sector_x&gt;\t&lt;sector_y&gt;\t&lt;name&gt;\t&lt;flag&gt;\t&lt;zone_id&gt;
 * 14660  68  57  FORT_HT_AREA  1  2001
 * </pre>
 *
 * <p>Proven facts encoded by the catalog (verified on the real file):
 * <ul>
 *   <li>region id packing {@code regionId == (sectorY << 8) | sectorX} holds
 *       for every one of the 2,444 non-negative rows (0 mismatches); the 17
 *       negative rows are dungeon/instance sentinels and are omitted;</li>
 *   <li>sector (x, y) is the same space as the client regioncode.tsv
 *       (2,442/2,444 ids) and the RegionInfo grid (2,396/2,444 sectors);</li>
 *   <li>col3 = server region name (e.g. West_China, FORT_HT_AREA), col4 is a
 *       flag (2,363 × 1, 81 × 0), col5 = zone id (13 distinct zone ids).</li>
 * </ul>
 *
 * <p>Fail-closed behavior: {@link #resolve(int)} returns {@code null} for any
 * region id not present in the committed table (including all dungeon/instance
 * ids, whose coordinate space is UNKNOWN and never derived here). Loading
 * refuses a row that violates the proven packing formula. No Android
 * dependencies; pure JVM.
 */
public final class RegionZoneCatalog {

  /** One committed region_zone.tsv row. */
  public static final class Entry {
    public final int regionId;
    public final int sectorX;
    public final int sectorY;
    public final String serverName;
    public final String flag;
    public final String zoneId;

    Entry(int regionId, int sectorX, int sectorY,
          String serverName, String flag, String zoneId) {
      this.regionId = regionId;
      this.sectorX = sectorX;
      this.sectorY = sectorY;
      this.serverName = serverName;
      this.flag = flag;
      this.zoneId = zoneId;
    }
  }

  private static final Pattern SOURCE_SHA =
      Pattern.compile("sha256 ([0-9a-f]{64})");

  private final Map<Integer, Entry> byId;
  private final String sourceSha256;
  private final int rowCount;
  private final Set<String> serverNames;
  private final Set<String> zoneIds;

  private RegionZoneCatalog(
      List<Entry> entries, String sourceSha256,
      Set<String> serverNames, Set<String> zoneIds) {
    Map<Integer, Entry> m = new HashMap<Integer, Entry>();
    for (Entry e : entries) {
      m.put(e.regionId, e);
    }
    this.byId = Collections.unmodifiableMap(m);
    this.sourceSha256 = sourceSha256;
    this.rowCount = entries.size();
    this.serverNames = Collections.unmodifiableSet(
        new HashSet<String>(serverNames));
    this.zoneIds = Collections.unmodifiableSet(new HashSet<String>(zoneIds));
  }

  /**
   * Resolve a packed region id to its server entry, or {@code null} when the
   * id is absent from the committed table (fail-closed; instance/dungeon ids
   * always resolve to {@code null}).
   */
  public Entry resolve(int regionId) {
    return byId.get(regionId);
  }

  /** Source provenance: sha256 of the real {@code RefRegion.txt}. */
  public String sourceSha256() {
    return sourceSha256;
  }

  public int rowCount() {
    return rowCount;
  }

  public Set<String> serverNames() {
    return serverNames;
  }

  public Set<String> zoneIds() {
    return zoneIds;
  }

  public Set<Integer> regionIds() {
    return Collections.unmodifiableSet(byId.keySet());
  }

  /** Parse the committed {@code region_zone.tsv}. */
  public static RegionZoneCatalog load(ReaderSupplier supplier) throws IOException {
    BufferedReader br = new BufferedReader(
        new InputStreamReader(supplier.open(), StandardCharsets.UTF_8));
    try {
      List<Entry> entries = new ArrayList<Entry>();
      Set<String> names = new HashSet<String>();
      Set<String> zones = new HashSet<String>();
      String sha = null;
      String line;
      while ((line = br.readLine()) != null) {
        if (line.startsWith("#")) {
          Matcher m = SOURCE_SHA.matcher(line);
          if (m.find()) {
            sha = m.group(1);
          }
          continue;
        }
        if (line.isEmpty()) {
          continue;
        }
        String[] p = line.split("\t", -1);
        if (p.length < 6) {
          throw new IOException("region_zone.tsv row with <6 columns: " + line);
        }
        int regionId = Integer.parseInt(p[0].trim());
        int sectorX = Integer.parseInt(p[1].trim());
        int sectorY = Integer.parseInt(p[2].trim());
        if (regionId != WorldCoordinates.packRegion(sectorX, sectorY)) {
          throw new IOException(
              "region_zone.tsv packing violation regionId=" + regionId
                  + " sector=(" + sectorX + "," + sectorY + ")");
        }
        entries.add(new Entry(regionId, sectorX, sectorY,
            p[3], p[4], p[5]));
        names.add(p[3]);
        zones.add(p[5]);
      }
      return new RegionZoneCatalog(entries, sha, names, zones);
    } finally {
      br.close();
    }
  }

  /** Read the catalog from the working directory's committed asset file. */
  public static RegionZoneCatalog loadDefault() throws IOException {
    return load(new DefaultReader());
  }

  /** Abstraction so JVM tests can read from the repo without an AssetManager. */
  public interface ReaderSupplier {
    InputStream open() throws IOException;
  }

  private static final class DefaultReader implements ReaderSupplier {
    private static final String[] PATHS = {
      "android/app/src/main/assets/game/world/region_zone.tsv",
      "app/src/main/assets/game/world/region_zone.tsv",
      "src/main/assets/game/world/region_zone.tsv",
      "game/world/region_zone.tsv",
    };

    @Override
    public InputStream open() throws IOException {
      for (String p : PATHS) {
        java.io.File f = new java.io.File(p);
        if (f.isFile()) {
          return new java.io.FileInputStream(f);
        }
      }
      throw new IOException("region_zone.tsv not found via default paths");
    }
  }
}
