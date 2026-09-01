package com.opensilkroadmap.app.data;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Instance-world catalog over the committed {@code gameworlddata.tsv}, the
 * client mirror of the server {@code _RefInstance_World} table.
 *
 * <p>Every world carries the proven {@code INS_*} code and, where present, the
 * proven {@code GROUP_*} group name ({@link #hasGroup()}). The
 * {@code code}+{@code group} concatenation is reproduced verbatim by the shard
 * backup's {@code _RefInstance_World} seed rows (see
 * {@link WorldGameTable}), so the pairing is server-authoritative. The numeric
 * {@code world_id} is an opaque unique key (PARTIAL semantics) and is never
 * used to invent placement. Rows without a group hold the client's {@code xxx}
 * placeholder and report {@code hasGroup() == false}.
 * <p>Fail-closed: unknown world ids and codes resolve to {@code null}; nothing
 * is guessed. No Android dependencies; pure JVM.
 */
public final class WorldDataIndex {

  /** One instance world with its proven code and optional group. */
  public static final class World {
    public final int worldId;
    public final String code;
    public final String group;

    World(int worldId, String code, String group) {
      this.worldId = worldId;
      this.code = code;
      this.group = group;
    }

    /** True when a real {@code GROUP_*} code is present (not {@code xxx}). */
    public boolean hasGroup() {
      return !group.isEmpty();
    }
  }

  private static final String NO_GROUP = "xxx";

  private final Map<Integer, World> byWorldId;
  private final Map<String, World> byCode;
  private final int groupCount;

  public WorldDataIndex(WorldGameTable table) {
    Map<Integer, World> byId = new LinkedHashMap<Integer, World>();
    Map<String, World> byCodeMap = new LinkedHashMap<String, World>();
    Set<String> distinctGroups = new HashSet<String>();
    for (int i = 0; i < table.worldCount(); i++) {
      int id = table.worldId(i);
      String code = table.code(i);
      String group = table.group(i);
      boolean realGroup = !group.isEmpty() && !NO_GROUP.equals(group);
      World world = new World(id, code, realGroup ? group : "");
      byId.put(id, world);
      if (!code.isEmpty()) {
        byCodeMap.put(code, world);
      }
      if (realGroup) {
        distinctGroups.add(group);
      }
    }
    this.byWorldId = Collections.unmodifiableMap(byId);
    this.byCode = Collections.unmodifiableMap(byCodeMap);
    this.groupCount = distinctGroups.size();
  }

  public static WorldDataIndex loadDefault() throws java.io.IOException {
    return new WorldDataIndex(WorldGameTable.load());
  }

  public int worldCount() {
    return byWorldId.size();
  }

  /** Distinct {@code GROUP_*} codes present (excluding the {@code xxx} marker). */
  public int groupCount() {
    return groupCount;
  }

  /** World by numeric id, or null (fail-closed). */
  public World byWorldId(int worldId) {
    return byWorldId.get(worldId);
  }

  /** World by {@code INS_*} code, or null (fail-closed). */
  public World byCode(String code) {
    return byCode.get(code);
  }

  public List<World> worlds() {
    return Collections.unmodifiableList(new ArrayList<World>(byWorldId.values()));
  }
}
