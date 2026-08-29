package com.opensilkroadmap.app.game;

import com.opensilkroadmap.app.data.LevelDataTable;
import com.opensilkroadmap.app.data.NpcPosTable;
import com.opensilkroadmap.app.data.TeleportDataTable;
import com.opensilkroadmap.app.data.TsvTable;
import com.opensilkroadmap.app.data.WorldMapInstanceTable;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.Reader;

/**
 * Phase 12 integration catalog: composes the committed real textdata tables
 * (android/app/src/main/assets/game/textdata/*.tsv, derived from the original
 * Media.pk2 /server_dep/silkroad/textdata files) into a single read-only view.
 *
 * <p>Android-free: callers open the asset (e.g. via {@code AssetManager.open})
 * and pass a {@link Reader}. {@link #loadDefault()} resolves the committed TSVs
 * from a conventional Gradle working directory for JVM tests.
 *
 * <p>Only proven column semantics are surfaced (see TEXTDATA_SCHEMAS.json);
 * nothing is inferred.
 */
public final class GameDataCatalog {
  private final NpcPosTable npcPos;
  private final LevelDataTable levelData;
  private final TeleportDataTable teleportData;
  private final WorldMapInstanceTable worldMapInstance;

  public GameDataCatalog(
      NpcPosTable npcPos,
      LevelDataTable levelData,
      TeleportDataTable teleportData,
      WorldMapInstanceTable worldMapInstance) {
    this.npcPos = npcPos;
    this.levelData = levelData;
    this.teleportData = teleportData;
    this.worldMapInstance = worldMapInstance;
  }

  public int npcSpawnCount() {
    return npcPos.spawnCount();
  }

  public int levelCount() {
    return levelData.levelCount();
  }

  public int teleportCount() {
    return teleportData.gateCount();
  }

  public int worldMapRegionCount() {
    return worldMapInstance.instanceCount();
  }

  public String summary() {
    return "npc spawns " + npcSpawnCount()
        + " · levels " + levelCount()
        + " · teleports " + teleportCount()
        + " · worldmap regions " + worldMapRegionCount();
  }

  /** Composes tables parsed from the four committed TSV readers (assets). */
  public static GameDataCatalog loadFrom(
      Reader npcPos, Reader levelData, Reader teleportData, Reader worldMapInstance)
      throws IOException {
    return new GameDataCatalog(
        new NpcPosTable(TsvTable.parse("npcpos.tsv", npcPos)),
        new LevelDataTable(TsvTable.parse("leveldata.tsv", levelData)),
        new TeleportDataTable(TsvTable.parse("teleportdata.tsv", teleportData)),
        new WorldMapInstanceTable(TsvTable.parse("worldmap_instanceinfo.tsv", worldMapInstance)));
  }

  /** Loads the committed TSVs from a conventional Gradle working directory. */
  public static GameDataCatalog loadDefault() throws IOException {
    String[] dirs = {
      "src/main/assets/game/textdata",
      "../src/main/assets/game/textdata",
      "app/src/main/assets/game/textdata",
      "../app/src/main/assets/game/textdata",
    };
    String[] names = {
      "npcpos.tsv",
      "leveldata.tsv",
      "teleportdata.tsv",
      "worldmap_instanceinfo.tsv",
    };
    for (String dir : dirs) {
      File base = new File(dir);
      if (!base.isDirectory()) {
        continue;
      }
      File[] files = new File[names.length];
      boolean allPresent = true;
      for (int i = 0; i < names.length; i++) {
        files[i] = new File(base, names[i]);
        allPresent &= files[i].isFile();
      }
      if (!allPresent) {
        continue;
      }
      return loadFrom(
          new FileReader(files[0]),
          new FileReader(files[1]),
          new FileReader(files[2]),
          new FileReader(files[3]));
    }
    throw new IOException("textdata assets not found via default paths");
  }
}
