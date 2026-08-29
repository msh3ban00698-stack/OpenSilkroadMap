package com.opensilkroadmap.app.minimap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import com.opensilkroadmap.app.minimap.ManifestData.MinimapRecord;
import com.opensilkroadmap.app.minimap.ManifestData.ResolvedAsset;
import com.opensilkroadmap.app.minimap.MinimapException.ResolutionException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.Test;

/** Unit tests for {@link ManifestResolver} (pure JVM, no Android framework). */
public class ManifestResolverTest {
  private static MinimapRecord record(String phase, String sourcePath, String outputPath) {
    return new MinimapRecord(
        sourcePath,
        outputPath,
        "Media.pk2",
        phase,
        "DDJ+DDS(DXT1)",
        256,
        256,
        100,
        100,
        89623L,
        "abc123",
        "ok",
        "PASS");
  }

  private static ManifestData manifestOf(List<MinimapRecord> records) {
    return new ManifestData("sro-android-assets-v2", "Media.pk2", records.size(), records.size(), 0, records);
  }

  @Test
  public void resolvesExactPath() throws Exception {
    ManifestResolver resolver =
        new ManifestResolver(
            manifestOf(
                Arrays.asList(
                    record("phase6", "/minimap/100x100.ddj", "maps/minimap/100x100.png"))));
    ResolvedAsset resolved = resolver.resolve("/minimap/100x100.ddj");
    assertEquals("maps/minimap/100x100.png", resolved.outputPath);
    assertEquals("/minimap/100x100.ddj", resolved.sourcePath);
    assertEquals(100, resolved.record.logicalWidth.intValue());
  }

  @Test
  public void leadingSlashNormalization() throws Exception {
    ManifestResolver resolver =
        new ManifestResolver(
            manifestOf(
                Arrays.asList(record("phase6", "/minimap/100x100.ddj", "maps/minimap/100x100.png"))));
    assertEquals("maps/minimap/100x100.png", resolver.resolve("minimap/100x100.ddj").outputPath);
    assertTrue(resolver.has("minimap/100x100.ddj"));
  }

  @Test
  public void missingSourceFailsExplicitly() throws Exception {
    ManifestResolver resolver =
        new ManifestResolver(
            manifestOf(
                Arrays.asList(record("phase6", "/minimap/100x100.ddj", "maps/minimap/100x100.png"))));
    assertFalse(resolver.has("/minimap/does_not_exist.ddj"));
    try {
      resolver.resolve("/minimap/does_not_exist.ddj");
      fail("expected ResolutionException");
    } catch (ResolutionException expected) {
      assertTrue(expected.getMessage().contains("does_not_exist.ddj"));
    }
    assertEquals(0, resolver.resolveAll("/minimap/does_not_exist.ddj").size());
  }

  @Test
  public void duplicateSourcesPreferLaterPhase() throws Exception {
    List<MinimapRecord> records = new ArrayList<>();
    records.add(record("phase5", "/minimap/100x100.ddj", "maps/minimap_100x100.png"));
    records.add(record("phase6", "/minimap/100x100.ddj", "maps/minimap/100x100.png"));
    ManifestResolver resolver = new ManifestResolver(manifestOf(records));

    assertEquals(1, resolver.duplicateSources().size());
    assertEquals("/minimap/100x100.ddj", resolver.duplicateSources().get(0));

    ResolvedAsset resolved = resolver.resolve("/minimap/100x100.ddj");
    assertEquals("phase6", resolved.record.phase);
    assertEquals("maps/minimap/100x100.png", resolved.outputPath);

    List<ResolvedAsset> all = resolver.resolveAll("/minimap/100x100.ddj");
    assertEquals(2, all.size());
    List<String> phases = new ArrayList<>();
    for (ResolvedAsset asset : all) {
      phases.add(asset.record.phase);
    }
    java.util.Collections.sort(phases);
    assertEquals(Arrays.asList("phase5", "phase6"), phases);
  }

  @Test
  public void resolutionKeysByExactPathNotBasename() throws Exception {
    ManifestResolver resolver =
        new ManifestResolver(
            manifestOf(
                Arrays.asList(
                    record("phase6", "/minimap_d/x/same.ddj", "maps/minimap_d/x/same.png"),
                    record("phase6", "/minimap/same.ddj", "maps/minimap/same.png"))));
    assertEquals("maps/minimap/same.png", resolver.resolve("/minimap/same.ddj").outputPath);
    assertEquals("maps/minimap_d/x/same.png", resolver.resolve("/minimap_d/x/same.ddj").outputPath);
  }

  @Test
  public void reverseLookupByOutputPath() throws Exception {
    ManifestResolver resolver =
        new ManifestResolver(
            manifestOf(
                Arrays.asList(record("phase6", "/minimap/100x100.ddj", "maps/minimap/100x100.png"))));
    ResolvedAsset resolved = resolver.resolveByOutputPath("maps/minimap/100x100.png");
    assertNotNull(resolved);
    assertEquals("/minimap/100x100.ddj", resolved.sourcePath);
    assertEquals(null, resolver.resolveByOutputPath("maps/not-there.png"));
  }

  @Test
  public void resolutionIsDeterministicAcrossInstances() throws Exception {
    List<MinimapRecord> records = new ArrayList<>();
    records.add(record("phase5", "/minimap/100x100.ddj", "maps/minimap_100x100.png"));
    records.add(record("phase6", "/minimap/100x100.ddj", "maps/minimap/100x100.png"));
    records.add(record("phase6", "/minimap/27x53.ddj", "maps/minimap/27x53.png"));
    ManifestResolver first = new ManifestResolver(manifestOf(records));
    ManifestResolver second = new ManifestResolver(manifestOf(records));
    for (String source : Arrays.asList("/minimap/100x100.ddj", "/minimap/27x53.ddj")) {
      ResolvedAsset a = first.resolve(source);
      ResolvedAsset b = second.resolve(source);
      assertEquals(a.outputPath, b.outputPath);
      assertEquals(a.record.phase, b.record.phase);
    }
  }

  @Test
  public void countsExcludeOtherKinds() throws Exception {
    List<MinimapRecord> records = new ArrayList<>();
    records.add(record("phase6", "/minimap/100x100.ddj", "maps/minimap/100x100.png"));
    records.add(record("phase6", "/minimap_d/Arabia/x.ddj", "maps/minimap_d/Arabia/x.png"));
    records.add(record("phase5", "/tile2d/tex.ddj", "maps/tile2d_tex.png"));
    ManifestResolver resolver = new ManifestResolver(manifestOf(records));
    assertEquals(2, resolver.minimapSourceCount());
    assertEquals(3, resolver.uniqueSourceCount());
    assertEquals(3, resolver.uniqueOutputCount());
  }
}
