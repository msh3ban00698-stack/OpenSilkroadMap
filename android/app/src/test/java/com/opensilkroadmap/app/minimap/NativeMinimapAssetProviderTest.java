package com.opensilkroadmap.app.minimap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import com.opensilkroadmap.app.minimap.ManifestData.MinimapRecord;
import com.opensilkroadmap.app.minimap.ManifestData.ResolvedAsset;
import com.opensilkroadmap.app.minimap.NativeMinimapAssetProvider.AssetReader;
import com.opensilkroadmap.app.minimap.NativeMinimapAssetProvider.ProviderStats;
import com.opensilkroadmap.app.minimap.NativeMinimapAssetProvider.ResolvedMinimap;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.Test;

/** Unit tests for {@link NativeMinimapAssetProvider} (pure JVM, fake assets). */
public class NativeMinimapAssetProviderTest {

  private static final class FakeAsset implements DecodedAsset {
    final String sourcePath;
    final int width;
    final int height;
    final int sizeBytes;
    boolean released;

    FakeAsset(String sourcePath, int width, int height, int sizeBytes) {
      this.sourcePath = sourcePath;
      this.width = width;
      this.height = height;
      this.sizeBytes = sizeBytes;
    }

    @Override
    public String sourcePath() {
      return sourcePath;
    }

    @Override
    public int width() {
      return width;
    }

    @Override
    public int height() {
      return height;
    }

    @Override
    public int sizeBytes() {
      return sizeBytes;
    }

    @Override
    public void release() {
      released = true;
    }
  }

  private static final class FakeDecoder implements AssetDecoder {
    final int width;
    final int height;
    final int sizeBytes;
    final boolean failDecode;

    FakeDecoder(int width, int height, int sizeBytes) {
      this(width, height, sizeBytes, false);
    }

    FakeDecoder(int width, int height, int sizeBytes, boolean failDecode) {
      this.width = width;
      this.height = height;
      this.sizeBytes = sizeBytes;
      this.failDecode = failDecode;
    }

    @Override
    public DecodedAsset decode(String sourcePath, InputStream data) throws IOException {
      if (failDecode) {
        throw new IOException("decode failed for " + sourcePath);
      }
      return new FakeAsset(sourcePath, width, height, sizeBytes);
    }
  }

  private static final class RecordingReader implements AssetReader {
    int opens;
    final List<String> openedPaths = new ArrayList<>();
    final String failingPath;

    RecordingReader() {
      this(null);
    }

    RecordingReader(String failingPath) {
      this.failingPath = failingPath;
    }

    @Override
    public InputStream open(String relativePath) throws IOException {
      if (relativePath.equals(failingPath)) {
        throw new IOException("ENOENT simulated for " + relativePath);
      }
      opens++;
      openedPaths.add(relativePath);
      return new ByteArrayInputStream(new byte[] {1, 2, 3});
    }
  }

  private static MinimapRecord record(String sourcePath, String outputPath) {
    return new MinimapRecord(
        sourcePath,
        outputPath,
        "Media.pk2",
        "phase6",
        "DDJ+DDS(DXT1)",
        256,
        256,
        null,
        null,
        100L,
        "sha",
        "ok",
        "PASS");
  }

  private static ManifestResolver resolverOf(List<String[]> sourceOutputPairs) {
    List<MinimapRecord> records = new ArrayList<>();
    for (String[] pair : sourceOutputPairs) {
      records.add(record(pair[0], pair[1]));
    }
    return new ManifestResolver(
        new ManifestData("sro-android-assets-v2", "Media.pk2", records.size(), records.size(), 0, records));
  }

  private static NativeMinimapAssetProvider provider(
      ManifestResolver resolver, AssetReader reader, AssetDecoder decoder, long maxBytes, int maxEntries) {
    return new NativeMinimapAssetProvider(resolver, reader, decoder, maxBytes, maxEntries);
  }

  @Test
  public void loadsRequestedAssetExactlyOncePerDistinctSource() throws Exception {
    List<String[]> pairs = new ArrayList<>();
    for (int i = 0; i < 40; i++) {
      pairs.add(new String[] {"/minimap/" + i + "x" + i + ".ddj", "maps/minimap/" + i + "x" + i + ".png"});
    }
    ManifestResolver resolver = resolverOf(pairs);
    RecordingReader reader = new RecordingReader();
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(256, 256, 10), 8 * 1024 * 1024, 64);

    for (String[] pair : pairs) {
      ResolvedMinimap loaded = provider.load(pair[0]);
      assertEquals(pair[1], loaded.record().outputPath);
    }
    assertEquals(40, reader.opens);
    assertEquals(40, reader.openedPaths.size());
    provider.releaseAll();
  }

  @Test
  public void boundedCacheStaysWithinLimits() throws Exception {
    List<String[]> pairs = new ArrayList<>();
    for (int i = 0; i < 40; i++) {
      pairs.add(new String[] {"/minimap/" + i + "x" + i + ".ddj", "maps/minimap/" + i + "x" + i + ".png"});
    }
    ManifestResolver resolver = resolverOf(pairs);
    RecordingReader reader = new RecordingReader();
    // 10KB per asset; 100KB max bytes or 8 max entries forces eviction.
    NativeMinimapAssetProvider provider = provider(resolver, reader, new FakeDecoder(256, 256, 10 * 1024), 100 * 1024, 8);

    for (String[] pair : pairs) {
      provider.load(pair[0]);
    }
    ProviderStats stats = provider.stats();
    assertTrue(stats.entries <= 8);
    assertTrue(stats.bytes <= 100 * 1024);
    assertTrue(stats.evictions > 0);
    provider.releaseAll();
  }

  @Test
  public void repeatedLoadHitsCacheWithoutRereading() throws Exception {
    ManifestResolver resolver =
        resolverOf(Arrays.asList(new String[] {"/minimap/100x100.ddj", "maps/minimap/100x100.png"}));
    RecordingReader reader = new RecordingReader();
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(256, 256, 10), 8 * 1024 * 1024, 64);
    provider.load("/minimap/100x100.ddj");
    provider.load("/minimap/100x100.ddj");
    assertEquals(1, reader.opens);
    assertEquals(1, provider.stats().entries);
    provider.releaseAll();
  }

  @Test
  public void releaseDropsSingleEntry() throws Exception {
    ManifestResolver resolver =
        resolverOf(Arrays.asList(new String[] {"/minimap/100x100.ddj", "maps/minimap/100x100.png"}));
    RecordingReader reader = new RecordingReader();
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(256, 256, 10), 8 * 1024 * 1024, 64);
    provider.load("/minimap/100x100.ddj");
    assertTrue(provider.release("/minimap/100x100.ddj"));
    assertFalse(provider.release("/minimap/100x100.ddj"));
    assertEquals(0, provider.stats().entries);
    assertEquals(0, provider.stats().bytes);
  }

  @Test
  public void releaseAllClearsEverything() throws Exception {
    ManifestResolver resolver =
        resolverOf(
            Arrays.asList(
                new String[] {"/minimap/100x100.ddj", "maps/minimap/100x100.png"},
                new String[] {"/minimap/27x53.ddj", "maps/minimap/27x53.png"}));
    RecordingReader reader = new RecordingReader();
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(256, 256, 10), 8 * 1024 * 1024, 64);
    provider.load("/minimap/100x100.ddj");
    provider.load("/minimap/27x53.ddj");
    provider.releaseAll();
    assertEquals(0, provider.stats().entries);
    assertEquals(0, provider.stats().bytes);
  }

  @Test
  public void missingOutputFileRaisesMissingAsset() throws Exception {
    ManifestResolver resolver =
        resolverOf(Arrays.asList(new String[] {"/minimap/100x100.ddj", "maps/minimap/100x100.png"}));
    RecordingReader reader = new RecordingReader("maps/minimap/100x100.png");
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(256, 256, 10), 8 * 1024 * 1024, 64);
    try {
      provider.load("/minimap/100x100.ddj");
      fail("expected MissingAssetException");
    } catch (MinimapException.MissingAssetException expected) {
      assertTrue(expected.getMessage().contains("100x100"));
    }
  }

  @Test
  public void undecodableAssetRaisesMissingAsset() throws Exception {
    ManifestResolver resolver =
        resolverOf(Arrays.asList(new String[] {"/minimap/100x100.ddj", "maps/minimap/100x100.png"}));
    RecordingReader reader = new RecordingReader();
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(256, 256, 10, true), 8 * 1024 * 1024, 64);
    try {
      provider.load("/minimap/100x100.ddj");
      fail("expected MissingAssetException");
    } catch (MinimapException.MissingAssetException expected) {
      assertTrue(expected.getMessage().contains("100x100"));
    }
  }

  @Test
  public void dimensionMismatchRaisesAndReleasesAsset() throws Exception {
    ManifestResolver resolver =
        resolverOf(Arrays.asList(new String[] {"/minimap/100x100.ddj", "maps/minimap/100x100.png"}));
    RecordingReader reader = new RecordingReader();
    // Manifest declares 256x256 but the decoded asset is 10x10.
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(10, 10, 400), 8 * 1024 * 1024, 64);
    try {
      provider.load("/minimap/100x100.ddj");
      fail("expected DimensionMismatchException");
    } catch (MinimapException.DimensionMismatchException expected) {
      assertTrue(expected.getMessage().contains("256"));
    }
    assertEquals(0, provider.stats().entries);
    assertEquals(0, provider.stats().bytes);
  }

  @Test
  public void missingSourceRaisesResolutionError() throws Exception {
    ManifestResolver resolver =
        resolverOf(Arrays.asList(new String[] {"/minimap/100x100.ddj", "maps/minimap/100x100.png"}));
    RecordingReader reader = new RecordingReader();
    NativeMinimapAssetProvider provider =
        provider(resolver, reader, new FakeDecoder(256, 256, 10), 8 * 1024 * 1024, 64);
    try {
      provider.load("/minimap/not_there.ddj");
      fail("expected ResolutionException");
    } catch (MinimapException.ResolutionException expected) {
      assertTrue(expected.getMessage().contains("not_there.ddj"));
    }
    assertEquals(0, reader.opens);
  }

  @Test
  public void sequentialAssetChangesRemainBounded() throws Exception {
    List<String[]> pairs = new ArrayList<>();
    for (int i = 0; i < 20; i++) {
      pairs.add(new String[] {"/minimap/" + i + "x" + i + ".ddj", "maps/minimap/" + i + "x" + i + ".png"});
    }
    ManifestResolver resolver = resolverOf(pairs);
    RecordingReader reader = new RecordingReader();
    NativeMinimapAssetProvider provider = provider(resolver, reader, new FakeDecoder(256, 256, 4 * 1024), 32 * 1024, 8);

    for (int round = 0; round < 3; round++) {
      for (String[] pair : pairs) {
        provider.load(pair[0]);
      }
    }
    ProviderStats stats = provider.stats();
    assertTrue(stats.entries <= 8);
    assertTrue(stats.bytes <= 32 * 1024);
    assertTrue(stats.evictions > 0);
    // No full-directory preload: reader opened exactly the 20 distinct paths once each.
    assertEquals(20, reader.opens);
    assertEquals(20, reader.openedPaths.size());
    provider.releaseAll();
  }
}
