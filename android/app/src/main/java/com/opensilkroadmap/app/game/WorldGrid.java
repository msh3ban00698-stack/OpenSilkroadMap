package com.opensilkroadmap.app.game;

/**
 * Verified world/minimap grid bounds for the Android map/world foundation.
 *
 * <p>The constants come from the Media.pk2 minimap inventory (VERIFIED): the
 * world minimap assets {@code maps/minimap/{x}x{y}.png} exist for
 * {@code x in [26,252]} and {@code y in [35,126]} (5,523 files). Cells in this
 * grid correspond 1:1 to {@code Data.pk2 /RegionInfo.txt} cells (verified: of
 * the 3,387 unique RegionInfo cells, 3,267 exist as committed minimaps; the
 * remainder fall outside the grid or are dungeon cells served by
 * {@code maps/minimap_d/{code}/}).
 *
 * <p>The conversion from SRO world coordinates to grid cells is UNKNOWN from
 * the supplied material; this class only exposes the verified grid geometry
 * and key formatting.
 */
public final class WorldGrid {
  public static final int MIN_X = 26;
  public static final int MAX_X = 252;
  public static final int MIN_Y = 35;
  public static final int MAX_Y = 126;
  public static final int MINIMAP_CELL_COUNT = 5523;

  private WorldGrid() {}

  public static boolean inRange(int x, int y) {
    return x >= MIN_X && x <= MAX_X && y >= MIN_Y && y <= MAX_Y;
  }

  /** Manifest source path, e.g. {@code /minimap/182x96.ddj}. */
  public static String minimapSourcePath(int x, int y) {
    return "/minimap/" + x + "x" + y + ".ddj";
  }

  /** Converted Android asset path, e.g. {@code maps/minimap/182x96.png}. */
  public static String minimapAssetPath(int x, int y) {
    return "maps/minimap/" + x + "x" + y + ".png";
  }
}
