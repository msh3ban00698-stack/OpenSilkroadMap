package com.opensilkroadmap.app.data;

import com.opensilkroadmap.app.world.WorldCoordinates;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * World placement index over the verified {@code npcpos.tsv} spawn table
 * (18,457 real rows, Phase 11/13).
 *
 * <p>Phase 13 corrected the column semantics: col0 = character_refid,
 * col1 = region_code (packed {@code region & 0xFF = x sector, region >> 8 = y
 * sector}), col2 = local_x, col3 = height_y, col4 = local_z. World rows have a
 * non-negative region code; negative codes are dungeon/instance rows in a
 * separate UNKNOWN space and are never projected into world coordinates.
 *
 * <p>This index exposes world spawns (with world coordinates computed by the
 * proven formula) and lets callers query the spawns that fall inside a sector
 * window. No Android dependencies; pure JVM.
 */
public final class NpcSpawnIndex {

  /** One real NPC spawn row with resolved sector and world coordinates. */
  public static final class Spawn {
    public final int characterRefId;
    public final int regionCode;
    public final int sectorX;
    public final int sectorY;
    public final float localX;
    public final float heightY;
    public final float localZ;
    public final boolean isWorld;

    public Spawn(
        int characterRefId, int regionCode, int sectorX, int sectorY,
        float localX, float heightY, float localZ, boolean isWorld) {
      this.characterRefId = characterRefId;
      this.regionCode = regionCode;
      this.sectorX = sectorX;
      this.sectorY = sectorY;
      this.localX = localX;
      this.heightY = heightY;
      this.localZ = localZ;
      this.isWorld = isWorld;
    }

    /** World x relative to a reference sector via the proven formula. */
    public float worldX(int refSx) {
      return localX + (sectorX - refSx) * WorldCoordinates.SECTOR_WORLD;
    }

    /** World z relative to a reference sector via the proven formula. */
    public float worldZ(int refSy) {
      return localZ + (sectorY - refSy) * WorldCoordinates.SECTOR_WORLD;
    }
  }

  private final List<Spawn> world;
  private final int dungeonCount;

  public NpcSpawnIndex(List<Spawn> all) {
    List<Spawn> w = new ArrayList<Spawn>();
    int d = 0;
    for (Spawn s : all) {
      if (s.isWorld) {
        w.add(s);
      } else {
        d++;
      }
    }
    Collections.sort(w, (a, b) ->
        a.sectorY != b.sectorY ? Integer.compare(a.sectorY, b.sectorY)
            : a.sectorX != b.sectorX ? Integer.compare(a.sectorX, b.sectorX)
                : Integer.compare(a.characterRefId, b.characterRefId));
    this.world = Collections.unmodifiableList(w);
    this.dungeonCount = d;
  }

  public static NpcSpawnIndex parse(Reader reader) throws IOException {
    return new NpcSpawnIndex(fromTable(TsvTable.parse("npcpos.tsv", reader)));
  }

  public static NpcSpawnIndex loadDefault() throws IOException {
    return new NpcSpawnIndex(fromTable(TsvTable.loadDefault("npcpos.tsv")));
  }

  private static List<Spawn> fromTable(TsvTable table) {
    List<Spawn> out = new ArrayList<Spawn>();
    for (String[] row : table.rows()) {
      int refId = TsvTable.intAt(row, 0);
      int region = TsvTable.intAt(row, 1);
      float x = TsvTable.floatAt(row, 2);
      float h = TsvTable.floatAt(row, 3);
      float z = TsvTable.floatAt(row, 4);
      boolean isWorld = region >= 0;
      int sx = -1;
      int sy = -1;
      if (isWorld) {
        int[] s = WorldCoordinates.unpackRegion(region);
        sx = s[0];
        sy = s[1];
      }
      out.add(new Spawn(refId, region, sx, sy, x, h, z, isWorld));
    }
    return out;
  }

  public int worldCount() {
    return world.size();
  }

  /** World spawn at the given index (indexes 0 .. worldCount()-1). */
  public Spawn worldSpawn(int i) {
    return world.get(i);
  }

  public int dungeonCount() {
    return dungeonCount;
  }

  public int totalCount() {
    return world.size() + dungeonCount;
  }

  /** World spawns whose sector lies inside the given inclusive sector window. */
  public List<Spawn> inWindow(int sx0, int sx1, int sy0, int sy1) {
    List<Spawn> out = new ArrayList<Spawn>();
    for (Spawn s : world) {
      if (s.sectorX >= sx0 && s.sectorX <= sx1 && s.sectorY >= sy0 && s.sectorY <= sy1) {
        out.add(s);
      }
    }
    return out;
  }
}
