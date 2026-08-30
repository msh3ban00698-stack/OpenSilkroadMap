package com.opensilkroadmap.app.minimap;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

/** Unit tests for {@link FitMath} geometry (pure JVM, no Android framework). */
public class FitMathTest {
  @Test
  public void fitScalePreservesAspectRatio() {
    assertEquals(2f, FitMath.fitScale(200, 100, 100, 50), 1e-6f);
    assertEquals(1f, FitMath.fitScale(100, 100, 100, 100), 1e-6f);
    assertEquals(0.5f, FitMath.fitScale(50, 100, 100, 200), 1e-6f);
  }

  @Test
  public void zoomIsBounded() {
    assertEquals(FitMath.MIN_ZOOM, FitMath.clampZoom(-5f), 1e-6f);
    assertEquals(FitMath.MAX_ZOOM, FitMath.clampZoom(99f), 1e-6f);
    assertEquals(2.5f, FitMath.clampZoom(2.5f), 1e-6f);
  }

  @Test
  public void zoomOneShowsFullImageWhenAspectMatches() {
    FitMath.SourceRect rect = FitMath.sourceViewport(256, 256, 256, 256, 1f, 128f, 128f);
    assertEquals(0, rect.left);
    assertEquals(0, rect.top);
    assertEquals(256, rect.right);
    assertEquals(256, rect.bottom);
  }

  @Test
  public void zoomTwoCropsAroundCenter() {
    FitMath.SourceRect rect = FitMath.sourceViewport(256, 256, 256, 256, 2f, 128f, 128f);
    assertEquals(64, rect.left);
    assertEquals(64, rect.top);
    assertEquals(192, rect.right);
    assertEquals(192, rect.bottom);
    assertEquals(128, rect.width());
    assertEquals(128, rect.height());
  }

  @Test
  public void zoomCropClampsAtImageEdge() {
    FitMath.SourceRect rect = FitMath.sourceViewport(256, 256, 256, 256, 2f, 0f, 0f);
    assertEquals(0, rect.left);
    assertEquals(0, rect.top);
    assertEquals(128, rect.right);
    assertEquals(128, rect.bottom);
  }

  @Test
  public void letterboxedImageFillsViewportAtZoomOne() {
    // 100x100 image in a 200x100 viewport: fit scale 1, visible width equals image.
    FitMath.SourceRect rect = FitMath.sourceViewport(200, 100, 100, 100, 1f, 50f, 50f);
    assertEquals(0, rect.left);
    assertEquals(0, rect.top);
    assertEquals(100, rect.right);
    assertEquals(100, rect.bottom);
  }

  @Test
  public void zeroSizedInputsAreGuarded() {
    FitMath.SourceRect zeroView = FitMath.sourceViewport(0, 100, 100, 100, 1f, 50f, 50f);
    assertEquals(100, zeroView.width());
    FitMath.SourceRect zeroImage = FitMath.sourceViewport(200, 100, 0, 0, 1f, 0f, 0f);
    assertEquals(0, zeroImage.width());
  }
}
