package com.opensilkroadmap.app.minimap;

import com.opensilkroadmap.app.minimap.ManifestData.MinimapRecord;
import com.opensilkroadmap.app.minimap.ManifestData.ResolvedAsset;
import com.opensilkroadmap.app.minimap.MinimapException.ResolutionException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Manifest-driven resolver mirroring the verified Phase 7
 * {@code MinimapManifestResolver} semantics exactly:
 *
 * <ul>
 *   <li>keys are the exact normalized PK2 source path (no basename matching),</li>
 *   <li>duplicate source records resolve deterministically to the later phase
 *       (tie-break: lexicographic output path),</li>
 *   <li>missing sources fail with an explicit {@link ResolutionException}.</li>
 * </ul>
 */
public final class ManifestResolver {
  private final ManifestData manifest;
  private final Map<String, List<MinimapRecord>> bySource = new HashMap<>();
  private final Map<String, MinimapRecord> preferred = new HashMap<>();
  private final Map<String, MinimapRecord> byOutput = new HashMap<>();

  public ManifestResolver(ManifestData manifest) {
    this.manifest = manifest;
    for (MinimapRecord record : manifest.records) {
      List<MinimapRecord> existing = bySource.get(record.sourcePath);
      if (existing == null) {
        existing = new ArrayList<>();
        bySource.put(record.sourcePath, existing);
      }
      existing.add(record);
      if (!byOutput.containsKey(record.outputPath)) {
        byOutput.put(record.outputPath, record);
      }
    }
    for (Map.Entry<String, List<MinimapRecord>> entry : bySource.entrySet()) {
      preferred.put(entry.getKey(), pickPreferred(entry.getValue()));
    }
  }

  public ManifestData manifest() {
    return manifest;
  }

  public int recordCount() {
    return manifest.records.size();
  }

  public int uniqueSourceCount() {
    return bySource.size();
  }

  public int uniqueOutputCount() {
    return byOutput.size();
  }

  public boolean has(String sourcePath) {
    return preferred.containsKey(ManifestParser.normalizeSourcePath(sourcePath));
  }

  /** Returns the single deterministic record for the source path. */
  public ResolvedAsset resolve(String sourcePath) throws ResolutionException {
    String key = ManifestParser.normalizeSourcePath(sourcePath);
    MinimapRecord record = preferred.get(key);
    if (record == null) {
      throw new ResolutionException("no manifest record for minimap source '" + key + "'");
    }
    return new ResolvedAsset(record, key, record.outputPath);
  }

  /** Returns every record for the source path (diagnostics/collision checks). */
  public List<ResolvedAsset> resolveAll(String sourcePath) {
    String key = ManifestParser.normalizeSourcePath(sourcePath);
    List<MinimapRecord> records = bySource.get(key);
    if (records == null) {
      return Collections.emptyList();
    }
    List<ResolvedAsset> result = new ArrayList<>(records.size());
    for (MinimapRecord record : records) {
      result.add(new ResolvedAsset(record, key, record.outputPath));
    }
    return result;
  }

  /** Reverse lookup by output path. */
  public ResolvedAsset resolveByOutputPath(String outputPath) {
    MinimapRecord record = byOutput.get(outputPath);
    if (record == null) {
      return null;
    }
    return new ResolvedAsset(record, record.sourcePath, record.outputPath);
  }

  /** Source paths that have more than one manifest record. */
  public List<String> duplicateSources() {
    List<String> duplicates = new ArrayList<>();
    for (Map.Entry<String, List<MinimapRecord>> entry : bySource.entrySet()) {
      if (entry.getValue().size() > 1) {
        duplicates.add(entry.getKey());
      }
    }
    Collections.sort(duplicates);
    return duplicates;
  }

  /** Number of distinct non-"other" (minimap / minimap_d) sources. */
  public int minimapSourceCount() {
    int count = 0;
    for (MinimapRecord record : preferred.values()) {
      if (kindOfSourcePath(record.sourcePath) != 0) {
        count++;
      }
    }
    return count;
  }

  /** Returns 0 for "other", 1 for minimap, 2 for minimap_d. */
  static int kindOfSourcePath(String sourcePath) {
    String normalized = ManifestParser.normalizeSourcePath(sourcePath).toLowerCase();
    if (normalized.startsWith("/minimap_d/")) {
      return 2;
    }
    if (normalized.startsWith("/minimap/")) {
      return 1;
    }
    return 0;
  }

  static int phaseRank(String phase) {
    String trimmed = phase.replaceFirst("^phase", "");
    try {
      return Integer.parseInt(trimmed);
    } catch (NumberFormatException e) {
      return 0;
    }
  }

  private static MinimapRecord pickPreferred(List<MinimapRecord> records) {
    List<MinimapRecord> sorted = new ArrayList<>(records);
    Collections.sort(
        sorted,
        new Comparator<MinimapRecord>() {
          @Override
          public int compare(MinimapRecord a, MinimapRecord b) {
            int rankA = phaseRank(a.phase);
            int rankB = phaseRank(b.phase);
            if (rankA != rankB) {
              return rankB - rankA;
            }
            return a.outputPath.compareTo(b.outputPath);
          }
        });
    return sorted.get(0);
  }
}
