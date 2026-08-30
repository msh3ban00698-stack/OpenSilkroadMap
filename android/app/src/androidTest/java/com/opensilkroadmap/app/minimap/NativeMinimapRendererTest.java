package com.opensilkroadmap.app.minimap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import com.opensilkroadmap.app.minimap.NativeMinimapAssetProvider.AssetReader;
import com.opensilkroadmap.app.minimap.NativeMinimapAssetProvider.ResolvedMinimap;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Instrumented tests for the native minimap renderer against REAL verified
 * minimap assets. Requires the on-device assets prepared by
 * {@code scripts/prepare_phase8_proof_assets.py} (manifest + 5 representative
 * PNGs under {@code app/src/main/assets/minimap_proof/}).
 *
 * <p>These tests execute on an Android device/emulator only; in this
 * environment (no JDK/Android SDK) they are NOT EXECUTED.
 */
@RunWith(AndroidJUnit4.class)
public class NativeMinimapRendererTest {
  private static final String[] PROOF_SOURCES = {
    "/minimap/27x53.ddj",
    "/minimap/100x100.ddj",
    "/minimap/105x101.ddj",
    "/minimap/237x124.ddj",
    "/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
  };

  private static final int BACKGROUND = 0xFF101014;

  private Context context;

  @Before
  public void setUp() {
    context = InstrumentationRegistry.getInstrumentation().getTargetContext();
  }

  private NativeMinimapAssetProvider providerWith(final AssetReader reader) throws Exception {
    InputStream manifest = context.getAssets().open("minimap_proof/manifest.json");
    try {
      ManifestData data = ManifestParser.parse(manifest);
      ManifestResolver resolver = new ManifestResolver(data);
      return new NativeMinimapAssetProvider(
          resolver, reader, new BitmapFactoryDecoder(), 4 * 1024 * 1024, 32);
    } finally {
      manifest.close();
    }
  }

  private static final class AssetsReader implements AssetReader {
    final Context context;
    final List<String> opened = new ArrayList<>();

    AssetsReader(Context context) {
      this.context = context;
    }

    @Override
    public InputStream open(String relativePath) throws IOException {
      opened.add(relativePath);
      return context.getAssets().open("minimap_proof/" + relativePath);
    }
  }

  private NativeMinimapRenderer newRenderer() {
    return new NativeMinimapRenderer(context);
  }

  @Test
  public void initializationCreatesCleanRenderer() {
    NativeMinimapRenderer renderer = newRenderer();
    assertFalse(renderer.hasMinimap());
    assertEquals(FitMath.MIN_ZOOM, renderer.getZoom(), 0f);
  }

  @Test
  public void validManifestLookup() throws Exception {
    NativeMinimapAssetProvider provider =
        providerWith(new AssetsReader(context));
    assertEquals(7755, provider.resolver().recordCount());
    assertEquals(7737, provider.resolver().minimapSourceCount());
    assertEquals(2, provider.resolver().duplicateSources().size());
    assertEquals("maps/minimap/100x100.png", provider.resolver().resolve("/minimap/100x100.ddj").outputPath);
    provider.releaseAll();
  }

  @Test
  public void validRealAssetLoading() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    for (String source : PROOF_SOURCES) {
      ResolvedMinimap loaded = provider.load(source);
      assertEquals(256, loaded.asset().width());
      assertEquals(256, loaded.asset().height());
      assertTrue(loaded.asset() instanceof BitmapAsset);
    }
    assertEquals(PROOF_SOURCES.length, reader.opened.size());
    provider.releaseAll();
  }

  @Test
  public void missingAssetFailsExplicitly() throws Exception {
    NativeMinimapAssetProvider provider = providerWith(new AssetsReader(context));
    try {
      provider.load("/minimap/does_not_exist.ddj");
      fail("expected ResolutionException");
    } catch (MinimapException.ResolutionException expected) {
      assertTrue(expected.getMessage().contains("does_not_exist"));
    }
    provider.releaseAll();
  }

  @Test
  public void invalidAssetFailsExplicitly() throws Exception {
    AssetReader garbageReader =
        new AssetReader() {
          @Override
          public InputStream open(String relativePath) {
            return new ByteArrayInputStream(new byte[] {0, 1, 2, 3, 4, 5});
          }
        };
    NativeMinimapAssetProvider provider = providerWith(garbageReader);
    try {
      provider.load("/minimap/100x100.ddj");
      fail("expected MissingAssetException");
    } catch (MinimapException.MissingAssetException expected) {
      assertTrue(expected.getMessage().contains("100x100"));
    }
    provider.releaseAll();
  }

  @Test
  public void assetReplacementReleasesPreviousViaProvider() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    ResolvedMinimap first = provider.load(PROOF_SOURCES[0]);
    ResolvedMinimap second = provider.load(PROOF_SOURCES[1]);
    assertEquals(2, provider.stats().entries);
    assertTrue(provider.release(first.record().sourcePath));
    assertEquals(1, provider.stats().entries);
    assertTrue(provider.release(second.record().sourcePath));
    assertEquals(0, provider.stats().entries);
    provider.releaseAll();
  }

  @Test
  public void resourceReleaseClearsCache() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    for (String source : PROOF_SOURCES) {
      provider.load(source);
    }
    assertTrue(provider.stats().entries > 0);
    provider.releaseAll();
    assertEquals(0, provider.stats().entries);
    assertEquals(0, provider.stats().bytes);
  }

  @Test
  public void boundedCacheStaysWithinLimits() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    for (int i = 0; i < 3; i++) {
      for (String source : PROOF_SOURCES) {
        provider.load(source);
      }
    }
    assertTrue(provider.stats().entries <= 32);
    assertTrue(provider.stats().bytes <= 4 * 1024 * 1024);
    assertTrue(reader.opened.size() <= PROOF_SOURCES.length * 3);
    provider.releaseAll();
  }

  @Test
  public void multipleSequentialMinimapChangesRender() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    NativeMinimapRenderer renderer = newRenderer();
    renderer.setMeasuredDimension(256, 256);
    renderer.layout(0, 0, 256, 256);
    for (String source : PROOF_SOURCES) {
      renderer.setMinimap(provider.load(source));
      Bitmap out = Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888);
      renderer.draw(new Canvas(out));
      assertHasDrawnPixels(out);
      out.recycle();
    }
    provider.releaseAll();
  }

  @Test
  public void aspectRatioPreservedAtZoomOne() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    NativeMinimapRenderer renderer = newRenderer();
    renderer.setMeasuredDimension(256, 256);
    renderer.layout(0, 0, 256, 256);
    ResolvedMinimap loaded = provider.load("/minimap/100x100.ddj");
    renderer.setMinimap(loaded);
    FitMath.SourceRect expected = FitMath.sourceViewport(256, 256, 256, 256, 1f, 128f, 128f);
    assertEquals(0, expected.left);
    assertEquals(0, expected.top);
    assertEquals(256, expected.right);
    assertEquals(256, expected.bottom);
    provider.releaseAll();
  }

  @Test
  public void zoomIsBounded() throws Exception {
    NativeMinimapRenderer renderer = newRenderer();
    renderer.setZoom(99f);
    assertEquals(FitMath.MAX_ZOOM, renderer.getZoom(), 0f);
    renderer.setZoom(-5f);
    assertEquals(FitMath.MIN_ZOOM, renderer.getZoom(), 0f);
    renderer.setZoom(2.5f);
    assertEquals(2.5f, renderer.getZoom(), 0f);
  }

  @Test
  public void rendererStateResetClearsEverything() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    NativeMinimapRenderer renderer = newRenderer();
    renderer.setMinimap(provider.load(PROOF_SOURCES[0]));
    renderer.setZoom(3f);
    renderer.setPlayerPosition(100f, 100f);
    renderer.setTestMarkerVisible(true);
    assertTrue(renderer.hasMinimap());
    renderer.reset();
    assertFalse(renderer.hasMinimap());
    assertEquals(FitMath.MIN_ZOOM, renderer.getZoom(), 0f);
    provider.releaseAll();
  }

  @Test
  public void noFullDirectoryPreload() throws Exception {
    AssetsReader reader = new AssetsReader(context);
    NativeMinimapAssetProvider provider = providerWith(reader);
    provider.load(PROOF_SOURCES[0]);
    provider.load(PROOF_SOURCES[1]);
    assertEquals(2, reader.opened.size());
    for (String path : reader.opened) {
      assertTrue(path.startsWith("maps/minimap") || path.startsWith("maps/minimap_d"));
    }
    provider.releaseAll();
  }

  private static void assertHasDrawnPixels(Bitmap bitmap) {
    int differing = 0;
    for (int y = 0; y < bitmap.getHeight(); y += 16) {
      for (int x = 0; x < bitmap.getWidth(); x += 16) {
        if (bitmap.getPixel(x, y) != BACKGROUND) {
          differing++;
        }
      }
    }
    assertTrue("expected non-background pixels drawn", differing > 0);
  }
}
