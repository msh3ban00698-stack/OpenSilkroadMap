package com.opensilkroadmap.app.data;

import com.opensilkroadmap.app.world.RegionResolver;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Zone attribution index over the verified NPC spawn table.
 *
 * <p>Composes {@link NpcSpawnIndex} (npcpos.tsv placements, Phase 13) with
 * {@link RegionResolver} (client RN_* name + server zone id, both committed and
 * provenance-pinned). Every WORLD spawn whose packed region code resolves to a
 * known server zone is indexed by zone; spawns whose region code is absent from
 * the server region→zone catalog stay UNKNOWN and are counted separately —
 * never invented.
 *
 * <p>Proven coverage on the committed tables: 18,457 total spawn rows split
 * into 14,800 world (region ≥ 0) and 3,657 instance/dungeon (region &lt; 0);
 * of the world spawns 11,597 resolve to one of the 13 server zones while 3,203
 * fail closed (their region code is not in region_zone.tsv). Zone ids come
 * verbatim from RefRegion.txt (e.g. 1001 = CHINA including RN_CH_JANGAN's
 * sectors and the Beijing/Jangan fort areas).
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class SpawnZoneIndex {

  private final NpcSpawnIndex spawns;
  private final RegionResolver resolver;
  private final Map<String, List<NpcSpawnIndex.Spawn>> byZone;
  private final int unknownWorldCount;

  public SpawnZoneIndex(NpcSpawnIndex spawns, RegionResolver resolver) {
    this.spawns = spawns;
    this.resolver = resolver;
    Map<String, List<NpcSpawnIndex.Spawn>> byZone =
        new LinkedHashMap<String, List<NpcSpawnIndex.Spawn>>();
    int unknown = 0;
    for (int i = 0; i < spawns.worldCount(); i++) {
      NpcSpawnIndex.Spawn s = spawns.worldSpawn(i);
      String zone = zoneOf(s);
      if (zone == null) {
        unknown++;
      } else {
        List<NpcSpawnIndex.Spawn> list = byZone.get(zone);
        if (list == null) {
          list = new ArrayList<NpcSpawnIndex.Spawn>();
          byZone.put(zone, list);
        }
        list.add(s);
      }
    }
    Map<String, List<NpcSpawnIndex.Spawn>> frozen =
        new LinkedHashMap<String, List<NpcSpawnIndex.Spawn>>();
    for (Map.Entry<String, List<NpcSpawnIndex.Spawn>> e : byZone.entrySet()) {
      frozen.put(e.getKey(), Collections.unmodifiableList(e.getValue()));
    }
    this.byZone = Collections.unmodifiableMap(frozen);
    this.unknownWorldCount = unknown;
  }

  /** Zone id for a world spawn's region code, or {@code null} (fail-closed). */
  public String zoneOf(NpcSpawnIndex.Spawn spawn) {
    if (!spawn.isWorld) {
      return null;
    }
    RegionResolver.Entry e = resolver.resolve(spawn.regionCode);
    return e == null ? null : e.zoneId;
  }

  /** Zone id for a packed region code, or {@code null} (fail-closed). */
  public String zoneIdOfRegion(int regionCode) {
    RegionResolver.Entry e = resolver.resolve(regionCode);
    return e == null ? null : e.zoneId;
  }

  /** Server name for a packed region code, or {@code null} (fail-closed). */
  public String serverNameOfRegion(int regionCode) {
    RegionResolver.Entry e = resolver.resolve(regionCode);
    return e == null ? null : e.serverName;
  }

  /** Client RN_* name code for a packed region code, or {@code null}. */
  public String nameCodeOfRegion(int regionCode) {
    RegionResolver.Entry e = resolver.resolve(regionCode);
    return e == null ? null : e.nameCode;
  }

  public int worldCount() {
    return spawns.worldCount();
  }

  /** World spawns whose region code resolves to a known server zone. */
  public int zoneResolvedCount() {
    return worldCount() - unknownWorldCount;
  }

  /** World spawns whose region code is absent from the zone catalog. */
  public int zoneUnknownCount() {
    return unknownWorldCount;
  }

  /** Distinct server zone ids present among world spawns (13 on committed data). */
  public Set<String> zones() {
    return byZone.keySet();
  }

  public List<NpcSpawnIndex.Spawn> spawnsInZone(String zoneId) {
    List<NpcSpawnIndex.Spawn> list = byZone.get(zoneId);
    return list == null ? Collections.<NpcSpawnIndex.Spawn>emptyList() : list;
  }
}
