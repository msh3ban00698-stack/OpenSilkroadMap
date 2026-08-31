package com.opensilkroadmap.app.game;

import com.opensilkroadmap.app.world.WorldCoordinates;

/**
 * Fail-closed player spawn representation for the native runtime.
 *
 * <p>NO verified player start position exists in the supplied source/data: the
 * full inventory (119,631 files across Data/Map/Media/Music/Particles.pk2) has
 * no SQL server database, no {@code startpos}/{@code start_pos}/{@code spawnpoint}
 * table, {@code npcpos.txt} is NPC-only, and the committed {@code "player"}
 * character key carries no static position. A player spawn is therefore
 * {@link #unknown(String) unknown} — never invented.
 *
 * <p>When a future verified source provides one, {@link #verified(int, float, float, float, String)}
 * builds a placed spawn projected into the world coordinate system with the
 * PROVEN formula {@code world = (sector - ref) * 1920 + local}
 * ({@link WorldCoordinates}). The coordinate types (SRO x/z units, heading
 * semantics) remain UNKNOWN from source; only the projection arithmetic is
 * proven. Pure JVM, no Android.
 */
public final class PlayerSpawn {

  /** Sentinel region code for an unknown spawn. */
  public static final int CODE_UNKNOWN = -1;
  /** Sentinel local/height value for an unknown spawn. */
  public static final float COORD_UNKNOWN = Float.NaN;

  private final boolean known;
  private final int regionCode;
  private final int sectorX;
  private final int sectorY;
  private final float localX;
  private final float localY;
  private final float localZ;
  private final String source;
  private final String reason;

  private PlayerSpawn(boolean known, int regionCode, int sectorX, int sectorY,
      float localX, float localY, float localZ, String source, String reason) {
    this.known = known;
    this.regionCode = regionCode;
    this.sectorX = sectorX;
    this.sectorY = sectorY;
    this.localX = localX;
    this.localY = localY;
    this.localZ = localZ;
    this.source = source == null ? "" : source;
    this.reason = reason == null ? "" : reason;
  }

  /** The only spawn constructible from the current evidence: an UNKNOWN spawn. */
  public static PlayerSpawn unknown(String reason) {
    return new PlayerSpawn(false, CODE_UNKNOWN, CODE_UNKNOWN, CODE_UNKNOWN,
        COORD_UNKNOWN, COORD_UNKNOWN, COORD_UNKNOWN, "", reason);
  }

  /**
   * Builds a placed spawn from a VERIFIED source. The region code follows the
   * proven packing {@code region & 0xFF = x sector}, {@code region >> 8 = y
   * sector}; local coordinates are relative to that sector.
   */
  public static PlayerSpawn verified(
      int regionCode, float localX, float localY, float localZ, String source) {
    if (source == null || source.trim().isEmpty()) {
      throw new IllegalArgumentException("verified spawn requires a source");
    }
    int[] s = WorldCoordinates.unpackRegion(regionCode);
    return new PlayerSpawn(true, regionCode, s[0], s[1],
        localX, localY, localZ, source, "");
  }

  /** True only when a verified source provided a real spawn. */
  public boolean isKnown() {
    return known;
  }

  public int regionCode() {
    return regionCode;
  }

  public int sectorX() {
    return sectorX;
  }

  public int sectorY() {
    return sectorY;
  }

  public float localX() {
    return localX;
  }

  public float localY() {
    return localY;
  }

  public float localZ() {
    return localZ;
  }

  /** World x of the spawn relative to a reference sector (proven formula). */
  public float worldX(int refSx) {
    return localX + WorldCoordinates.sectorWorldX(sectorX, refSx);
  }

  /** World z of the spawn relative to a reference sector (proven formula). */
  public float worldZ(int refSy) {
    return localZ + WorldCoordinates.sectorWorldZ(sectorY, refSy);
  }

  public String source() {
    return source;
  }

  public String reason() {
    return reason;
  }
}
