package com.opensilkroadmap.app.minimap;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Immutable data model mirroring {@code android-assets/manifest.json} (schema
 * {@code sro-android-assets-v2}). Semantics match the verified Phase 7
 * TypeScript model in {@code map/src/game/minimap_assets.ts}.
 */
public final class ManifestData {
  public final String schema;
  public final String archive;
  public final int totalTargets;
  public final int minimapTargets;
  public final int minimapDTargets;
  public final List<MinimapRecord> records;

  public ManifestData(
      String schema,
      String archive,
      int totalTargets,
      int minimapTargets,
      int minimapDTargets,
      List<MinimapRecord> records) {
    this.schema = schema == null ? "" : schema;
    this.archive = archive == null ? "" : archive;
    this.totalTargets = totalTargets;
    this.minimapTargets = minimapTargets;
    this.minimapDTargets = minimapDTargets;
    this.records = Collections.unmodifiableList(new ArrayList<>(records));
  }

  /** One normalized manifest record. */
  public static final class MinimapRecord {
    public final String sourcePath;
    public final String outputPath;
    public final String sourcePk2;
    public final String phase;
    public final String detectedFormat;
    public final Integer width;
    public final Integer height;
    public final Integer logicalWidth;
    public final Integer logicalHeight;
    public final Long outputSize;
    public final String outputSha256;
    public final String status;
    public final String validationStatus;

    public MinimapRecord(
        String sourcePath,
        String outputPath,
        String sourcePk2,
        String phase,
        String detectedFormat,
        Integer width,
        Integer height,
        Integer logicalWidth,
        Integer logicalHeight,
        Long outputSize,
        String outputSha256,
        String status,
        String validationStatus) {
      this.sourcePath = sourcePath;
      this.outputPath = outputPath;
      this.sourcePk2 = sourcePk2 == null ? "" : sourcePk2;
      this.phase = phase == null ? "" : phase;
      this.detectedFormat = detectedFormat == null ? "" : detectedFormat;
      this.width = width;
      this.height = height;
      this.logicalWidth = logicalWidth;
      this.logicalHeight = logicalHeight;
      this.outputSize = outputSize;
      this.outputSha256 = outputSha256 == null ? "" : outputSha256;
      this.status = status == null ? "" : status;
      this.validationStatus = validationStatus == null ? "" : validationStatus;
    }
  }

  /** The result of resolving a source path against the manifest. */
  public static final class ResolvedAsset {
    public final MinimapRecord record;
    public final String sourcePath;
    public final String outputPath;

    public ResolvedAsset(MinimapRecord record, String sourcePath, String outputPath) {
      this.record = record;
      this.sourcePath = sourcePath;
      this.outputPath = outputPath;
    }
  }
}
