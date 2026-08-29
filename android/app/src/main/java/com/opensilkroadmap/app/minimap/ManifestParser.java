package com.opensilkroadmap.app.minimap;

import com.opensilkroadmap.app.minimap.MinimapException.ManifestParseException;
import com.opensilkroadmap.app.minimap.ManifestData.MinimapRecord;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Parses the Phase 6/7 merged manifest JSON into {@link ManifestData}.
 *
 * <p>Resolution semantics are intentionally NOT implemented here; they live in
 * {@link ManifestResolver} and mirror the verified Phase 7 resolver exactly
 * (exact normalized path keys, no basename guessing, later-phase preference
 * for duplicate source paths).
 */
public final class ManifestParser {
  private static final int MAX_MANIFEST_BYTES = 32 * 1024 * 1024;

  private ManifestParser() {}

  /** Reads the entire stream (bounded) and parses it as a manifest. */
  public static ManifestData parse(InputStream in) throws ManifestParseException, IOException {
    StringBuilder sb = new StringBuilder();
    char[] buffer = new char[8192];
    int total = 0;
    InputStreamReader reader = new InputStreamReader(in, StandardCharsets.UTF_8);
    int read;
    while ((read = reader.read(buffer)) != -1) {
      total += read;
      if (total > MAX_MANIFEST_BYTES) {
        throw new ManifestParseException("manifest exceeds " + MAX_MANIFEST_BYTES + " bytes");
      }
      sb.append(buffer, 0, read);
    }
    return parse(sb.toString());
  }

  /** Parses a manifest from its JSON string representation. */
  public static ManifestData parse(String json) throws ManifestParseException {
    try {
      JSONObject root = new JSONObject(json);
      JSONArray rawRecords = root.getJSONArray("records");
      int count = rawRecords.length();
      MinimapRecord[] records = new MinimapRecord[count];
      for (int i = 0; i < count; i++) {
        records[i] = parseRecord(rawRecords.getJSONObject(i), i);
      }
      JSONObject targets = root.optJSONObject("targets");
      int totalTargets = targets == null ? -1 : targets.optInt("total", -1);
      int minimapTargets = targets == null ? -1 : targets.optInt("minimap", -1);
      int minimapDTargets = targets == null ? -1 : targets.optInt("minimap_d", -1);
      return new ManifestData(
          root.optString("schema", ""),
          root.optString("archive", ""),
          totalTargets,
          minimapTargets,
          minimapDTargets,
          java.util.Arrays.asList(records));
    } catch (JSONException e) {
      throw new ManifestParseException("manifest JSON parse failed: " + e.getMessage(), e);
    }
  }

  /** Normalizes a PK2 source path to a single leading-slash canonical form. */
  public static String normalizeSourcePath(String raw) {
    if (raw == null) {
      return "";
    }
    String path = raw.trim();
    while (path.startsWith("/")) {
      path = path.substring(1);
    }
    return "/" + path;
  }

  private static MinimapRecord parseRecord(JSONObject raw, int index)
      throws JSONException, ManifestParseException {
    String sourcePath = normalizeSourcePath(raw.optString("source_path", ""));
    if (sourcePath.isEmpty()) {
      throw new ManifestParseException("record " + index + " is missing 'source_path'");
    }
    String outputPath = raw.optString("output_path", "");
    if (outputPath.isEmpty()) {
      throw new ManifestParseException("record " + index + " is missing 'output_path'");
    }
    String sourcePk2 = raw.optString("source_pk2", "");
    if (sourcePk2.isEmpty()) {
      sourcePk2 = raw.optString("pk2", "");
    }
    String status = raw.optString("status", "");
    if (status.isEmpty()) {
      status = raw.optString("result", "");
    }
    return new MinimapRecord(
        sourcePath,
        outputPath,
        sourcePk2,
        raw.optString("phase", ""),
        raw.optString("detected_format", ""),
        optNullableInt(raw, "width"),
        optNullableInt(raw, "height"),
        optNullableInt(raw, "logical_width"),
        optNullableInt(raw, "logical_height"),
        raw.has("output_size") && !raw.isNull("output_size") ? raw.getLong("output_size") : null,
        raw.optString("output_sha256", ""),
        status,
        raw.optString("validation_status", ""));
  }

  private static Integer optNullableInt(JSONObject raw, String key) throws JSONException {
    if (!raw.has(key) || raw.isNull(key)) {
      return null;
    }
    return raw.getInt(key);
  }
}
