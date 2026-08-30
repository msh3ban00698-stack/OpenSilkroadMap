package com.opensilkroadmap.app.world;

import com.opensilkroadmap.app.data.TsvTable;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * Refid -> character key index over the committed {@code characters/index.tsv}
 * (Phase 20). One row per (refid, variant); {@link #keyFor} returns the
 * primary (variant 0) character key for a spawning NPC refid. The player is
 * always key {@code "player"} and is not spawned by npcpos.
 *
 * <p>Pure JVM, no Android. Fail-closed: an unknown refid returns null.
 */
public final class CharacterCatalog {

  public static final String PLAYER_KEY = "player";

  /** (refid, variant) -> key; primary = variant 0. */
  private final Map<Long, String> primaryByRefid = new LinkedHashMap<Long, String>();
  private final Set<String> keys = new LinkedHashSet<String>();
  private final int rowCount;

  private CharacterCatalog(Map<Long, String> primaryByRefid,
                           Set<String> keys, int rowCount) {
    this.primaryByRefid.putAll(primaryByRefid);
    this.keys.addAll(keys);
    this.rowCount = rowCount;
  }

  public static CharacterCatalog parse(Reader reader) throws IOException {
    return fromTable(TsvTable.parse("index.tsv", reader));
  }

  public static CharacterCatalog loadDefault() throws IOException {
    String[] candidates = {
      "src/main/assets/game/world/characters/index.tsv",
      "../src/main/assets/game/world/characters/index.tsv",
      "app/src/main/assets/game/world/characters/index.tsv",
      "../app/src/main/assets/game/world/characters/index.tsv",
    };
    for (String path : candidates) {
      File f = new File(path);
      if (f.isFile()) {
        return parse(new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8));
      }
    }
    throw new IOException("characters/index.tsv not found via default paths");
  }

  private static CharacterCatalog fromTable(TsvTable table) {
    Map<Long, String> primary = new LinkedHashMap<Long, String>();
    Set<String> keys = new LinkedHashSet<String>();
    int rowCount = 0;
    for (String[] row : table.rows()) {
      String refidStr = TsvTable.strAt(row, 0).trim();
      if (refidStr.isEmpty() || !isDigits(refidStr)) {
        continue; // header or blank row
      }
      long refid = Long.parseLong(refidStr);
      String key = TsvTable.strAt(row, 1);
      int variant = TsvTable.intAt(row, 2);
      keys.add(key);
      if (!primary.containsKey(Long.valueOf(refid)) || variant == 0) {
        primary.put(Long.valueOf(refid), key);
      }
      rowCount++;
    }
    return new CharacterCatalog(primary, keys, rowCount);
  }

  private static boolean isDigits(String s) {
    if (s.isEmpty()) {
      return false;
    }
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      if (c < '0' || c > '9') {
        return false;
      }
    }
    return true;
  }

  /** Primary character key for a spawning NPC refid, or null when absent. */
  public String keyFor(int refid) {
    return primaryByRefid.get(Long.valueOf(refid));
  }

  public String playerKey() {
    return PLAYER_KEY;
  }

  public Set<String> characterKeys() {
    return Collections.unmodifiableSet(keys);
  }

  public int count() {
    return rowCount;
  }
}
