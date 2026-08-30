package com.opensilkroadmap.app.game;

import java.util.Collections;
import java.util.List;

/**
 * One named region section parsed from the derived region catalog
 * {@code android/app/src/main/assets/game/regions.tsv} (itself derived from
 * the real {@code Data.pk2 /RegionInfo.txt}, sha256-verified by
 * {@code scripts/build_region_catalog.py}).
 *
 * <p>The catalog preserves the original file semantics: a section is either a
 * TOWN or a FIELD and groups grid cells {@code (x, y)} in the same coordinate
 * space as the converted minimap assets {@code maps/minimap/{x}x{y}.png}. The
 * optional {@code code} column (FIELD sections) matches the dungeon minimap
 * folders under {@code maps/minimap_d/{code}/}. {@code RECT} cells carry the
 * original numeric parameters verbatim; their meaning is UNKNOWN and is not
 * interpreted.
 */
public final class RegionInfo {
  public enum Type {
    FIELD,
    TOWN,
    UNKNOWN;

    public static Type parse(String raw) {
      if (raw == null) {
        return UNKNOWN;
      }
      if (raw.equals("FIELD")) {
        return FIELD;
      }
      if (raw.equals("TOWN")) {
        return TOWN;
      }
      return UNKNOWN;
    }
  }

  /** A single grid cell with its original parameters. */
  public static final class Cell {
    public final int x;
    public final int y;
    public final String kind;
    public final int[] extra;

    public Cell(int x, int y, String kind, int[] extra) {
      this.x = x;
      this.y = y;
      this.kind = kind == null ? "ALL" : kind;
      this.extra = extra == null ? new int[0] : extra.clone();
    }
  }

  public final Type type;
  public final String name;
  public final String code;
  public final List<Cell> cells;

  public RegionInfo(Type type, String name, String code, List<Cell> cells) {
    this.type = type == null ? Type.UNKNOWN : type;
    this.name = name == null ? "" : name;
    this.code = code == null ? "" : code;
    this.cells = Collections.unmodifiableList(new java.util.ArrayList<>(cells));
  }
}
