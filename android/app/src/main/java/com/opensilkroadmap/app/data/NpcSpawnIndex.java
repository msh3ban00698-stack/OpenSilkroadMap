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
 * window. Optional {@link CharacterIdentityIndex} attach is fail-closed:
 * {@code parse} and {@code loadGeometry} stay identity-null; {@code loadDefault}
 * joins {@code character_identity.tsv} on npcpos col0 (1180/1180 distinct
 * refids, 14800/14800 world rows). Unknown refids and a missing identity
 * asset leave {@code identity == null}. SN_* names, stats, and meshes are
 * not invented. No Android dependencies; pure JVM.
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
    public final CharacterIdentityIndex.Identity identity;

    public Spawn(
        int characterRefId, int regionCode, int sectorX, int sectorY,
        float localX, float heightY, float localZ, boolean isWorld) {
      this(characterRefId, regionCode, sectorX, sectorY, localX, heightY,
          localZ, isWorld, null);
    }

    public Spawn(
        int characterRefId, int regionCode, int sectorX, int sectorY,
        float localX, float heightY, float localZ, boolean isWorld,
        CharacterIdentityIndex.Identity identity) {
      this.characterRefId = characterRefId;
      this.regionCode = regionCode;
      this.sectorX = sectorX;
      this.sectorY = sectorY;
      this.localX = localX;
      this.heightY = heightY;
      this.localZ = localZ;
      this.isWorld = isWorld;
      this.identity = identity;
    }

    /** Proven characterdata code ({@code NPC_*}/{@code MOB_*}/{@code STRUCTURE_*}), or null. */
    public String characterCode() {
      return identity == null ? null : identity.code;
    }

    /** Proven characterdata .bsr model path (or {@code xxx}), or null. */
    public String modelPath() {
      return identity == null ? null : identity.modelPath;
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
  private final int identifiedWorldCount;

  public NpcSpawnIndex(List<Spawn> all) {
    List<Spawn> w = new ArrayList<Spawn>();
    int d = 0;
    int identified = 0;
    for (Spawn s : all) {
      if (s.isWorld) {
        w.add(s);
        if (s.identity != null) {
          identified++;
        }
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
    this.identifiedWorldCount = identified;
  }

  public NpcSpawnIndex(TsvTable table, CharacterIdentityIndex identity) {
    this(fromTable(table, identity));
  }

  public static NpcSpawnIndex parse(Reader reader) throws IOException {
    return new NpcSpawnIndex(fromTable(TsvTable.parse("npcpos.tsv", reader), null));
  }

  /** Geometry-only load; identity stays null even when the asset exists. */
  public static NpcSpawnIndex loadGeometry() throws IOException {
    return new NpcSpawnIndex(fromTable(TsvTable.loadDefault("npcpos.tsv"), null));
  }

  /**
   * Loads npcpos plus optional character identity. A missing identity asset
   * fails closed (geometry still loads; codes/paths stay null).
   */
  public static NpcSpawnIndex loadDefault() throws IOException {
    TsvTable table = TsvTable.loadDefault("npcpos.tsv");
    CharacterIdentityIndex identity = null;
    try {
      identity = CharacterIdentityIndex.loadDefault();
    } catch (IOException ignored) {
      identity = null;
    }
    return new NpcSpawnIndex(fromTable(table, identity));
  }

  private static List<Spawn> fromTable(TsvTable table,
                                       CharacterIdentityIndex identity) {
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
      CharacterIdentityIndex.Identity id =
          identity == null ? null : identity.resolve(refId);
      out.add(new Spawn(refId, region, sx, sy, x, h, z, isWorld, id));
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

  /** World spawns whose npcpos col0 uniquely joined character_identity.tsv. */
  public int identifiedWorldCount() {
    return identifiedWorldCount;
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
