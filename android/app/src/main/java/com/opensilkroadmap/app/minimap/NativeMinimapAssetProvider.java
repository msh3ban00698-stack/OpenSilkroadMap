package com.opensilkroadmap.app.minimap;

import com.opensilkroadmap.app.minimap.ManifestData.MinimapRecord;
import com.opensilkroadmap.app.minimap.ManifestData.ResolvedAsset;
import com.opensilkroadmap.app.minimap.MinimapException.DimensionMismatchException;
import com.opensilkroadmap.app.minimap.MinimapException.MissingAssetException;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Android-side minimap asset provider.
 *
 * <p>Consumes resolved Android assets only. It never touches PK2 archives and
 * never re-resolves assets on its own; {@link ManifestResolver} (fed by the
 * same verified manifest) is the only mapping. A bounded LRU cache of decoded
 * assets keeps memory bounded: it never decodes the full collection, releases
 * evicted payloads via {@link DecodedAsset#release()}, and reports its state
 * through {@link #stats()}.
 */
public final class NativeMinimapAssetProvider {
  public static final long DEFAULT_MAX_CACHE_BYTES = 8L * 1024 * 1024;
  public static final int DEFAULT_MAX_CACHE_ENTRIES = 64;

  /** Opens an InputStream for a resolved relative output path. */
  public interface AssetReader {
    InputStream open(String relativePath) throws IOException;
  }

  private final ManifestResolver resolver;
  private final AssetReader reader;
  private final AssetDecoder decoder;
  private final long maxCacheBytes;
  private final int maxCacheEntries;
  private final Map<String, DecodedAsset> cache;
  private long cacheBytes;
  private long evictions;

  public NativeMinimapAssetProvider(
      ManifestResolver resolver,
      AssetReader reader,
      AssetDecoder decoder,
      long maxCacheBytes,
      int maxCacheEntries) {
    if (maxCacheBytes <= 0 || maxCacheEntries <= 0) {
      throw new IllegalArgumentException("cache limits must be positive");
    }
    this.resolver = resolver;
    this.reader = reader;
    this.decoder = decoder;
    this.maxCacheBytes = maxCacheBytes;
    this.maxCacheEntries = maxCacheEntries;
    this.cache = new LinkedHashMap<String, DecodedAsset>(16, 0.75f, false);
  }

  public ManifestResolver resolver() {
    return resolver;
  }

  /**
   * Loads (or reuses from cache) the minimap for the exact manifest source
   * path. The decoded asset is validated against the manifest record before it
   * is returned; a mismatched asset is released and reported explicitly.
   */
  public ResolvedMinimap load(String sourcePath) throws MinimapException {
    ResolvedAsset resolved = resolver.resolve(sourcePath);
    String key = resolved.sourcePath;

    DecodedAsset cached = cache.remove(key);
    if (cached != null) {
      cache.put(key, cached);
      return new ResolvedMinimap(resolved.record, cached);
    }

    DecodedAsset asset = null;
    try {
      InputStream in = reader.open(resolved.outputPath);
      try {
        asset = decoder.decode(key, in);
      } finally {
        in.close();
      }
    } catch (IOException e) {
      throw new MissingAssetException(
          "minimap asset missing for '" + key + "' (" + resolved.outputPath + "): " + e.getMessage());
    }
    try {
      validate(resolved.record, asset);
    } catch (DimensionMismatchException e) {
      asset.release();
      throw e;
    }
    put(key, asset);
    return new ResolvedMinimap(resolved.record, asset);
  }

  private void validate(MinimapRecord record, DecodedAsset asset) throws DimensionMismatchException {
    if (record.width != null && record.width != asset.width()) {
      throw new DimensionMismatchException(
          "dimension mismatch for '" + record.sourcePath + "': manifest width " + record.width
              + " != asset width " + asset.width());
    }
    if (record.height != null && record.height != asset.height()) {
      throw new DimensionMismatchException(
          "dimension mismatch for '" + record.sourcePath + "': manifest height " + record.height
              + " != asset height " + asset.height());
    }
    if (record.logicalWidth != null
        && (record.logicalWidth <= 0 || record.logicalWidth > asset.width())) {
      throw new DimensionMismatchException(
          "logical width out of range for '" + record.sourcePath + "': " + record.logicalWidth
              + " not in (0, " + asset.width() + "]");
    }
    if (record.logicalHeight != null
        && (record.logicalHeight <= 0 || record.logicalHeight > asset.height())) {
      throw new DimensionMismatchException(
          "logical height out of range for '" + record.sourcePath + "': " + record.logicalHeight
              + " not in (0, " + asset.height() + "]");
    }
  }

  private void put(String key, DecodedAsset asset) {
    cache.put(key, asset);
    cacheBytes += asset.sizeBytes();
    trim();
  }

  private void trim() {
    while ((cacheBytes > maxCacheBytes || cache.size() > maxCacheEntries) && !cache.isEmpty()) {
      String oldest = cache.keySet().iterator().next();
      DecodedAsset evicted = cache.remove(oldest);
      cacheBytes -= evicted.sizeBytes();
      evicted.release();
      evictions++;
    }
  }

  /** Drops and releases a single cached asset. Returns false if absent. */
  public boolean release(String sourcePath) {
    String key = ManifestParser.normalizeSourcePath(sourcePath);
    DecodedAsset removed = cache.remove(key);
    if (removed == null) {
      return false;
    }
    cacheBytes -= removed.sizeBytes();
    removed.release();
    return true;
  }

  /** Drops and releases every cached asset. */
  public void releaseAll() {
    for (DecodedAsset asset : new ArrayList<>(cache.values())) {
      asset.release();
    }
    cache.clear();
    cacheBytes = 0;
  }

  public ProviderStats stats() {
    return new ProviderStats(cache.size(), cacheBytes, evictions, maxCacheBytes, maxCacheEntries);
  }

  /** A validated, loaded minimap ready for rendering. */
  public static final class ResolvedMinimap {
    private final MinimapRecord record;
    private final DecodedAsset asset;

    ResolvedMinimap(MinimapRecord record, DecodedAsset asset) {
      this.record = record;
      this.asset = asset;
    }

    public MinimapRecord record() {
      return record;
    }

    public DecodedAsset asset() {
      return asset;
    }
  }

  /** Snapshot of the bounded cache state. */
  public static final class ProviderStats {
    public final int entries;
    public final long bytes;
    public final long evictions;
    public final long maxBytes;
    public final int maxEntries;

    ProviderStats(int entries, long bytes, long evictions, long maxBytes, int maxEntries) {
      this.entries = entries;
      this.bytes = bytes;
      this.evictions = evictions;
      this.maxBytes = maxBytes;
      this.maxEntries = maxEntries;
    }
  }
}
