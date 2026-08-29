package com.opensilkroadmap.app.minimap;

/**
 * Pure layout math for the native minimap renderer: aspect-preserving fit,
 * bounded zoom, and the source sub-rect (viewport/crop) to draw. Kept free of
 * {@code android.*} so the geometry is unit-testable on a plain JVM.
 */
public final class FitMath {
  public static final float MIN_ZOOM = 1f;
  public static final float MAX_ZOOM = 4f;

  private FitMath() {}

  /** Clamps zoom to {@code [MIN_ZOOM, MAX_ZOOM]}. */
  public static float clampZoom(float zoom) {
    return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));
  }

  /** Scale that fits the image into the viewport while preserving aspect ratio. */
  public static float fitScale(int viewWidth, int viewHeight, int imageWidth, int imageHeight) {
    if (viewWidth <= 0 || viewHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
      return 1f;
    }
    return Math.min((float) viewWidth / imageWidth, (float) viewHeight / imageHeight);
  }

  /**
   * Computes the sub-rectangle of the source image (in image pixels) that must
   * be drawn to fill the viewport at the given zoom, centered on a point given
   * in image pixel coordinates.
   */
  public static SourceRect sourceViewport(
      int viewWidth, int viewHeight, int imageWidth, int imageHeight, float zoom, float centerX, float centerY) {
    if (viewWidth <= 0 || viewHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
      return new SourceRect(0, 0, imageWidth, imageHeight);
    }
    float scale = Math.max(1e-6f, fitScale(viewWidth, viewHeight, imageWidth, imageHeight) * clampZoom(zoom));
    float visibleWidth = viewWidth / scale;
    float visibleHeight = viewHeight / scale;

    float left = centerX - visibleWidth / 2f;
    float top = centerY - visibleHeight / 2f;
    float right = left + visibleWidth;
    float bottom = top + visibleHeight;

    if (visibleWidth >= imageWidth) {
      left = 0;
      right = imageWidth;
    } else {
      if (left < 0) {
        left = 0;
        right = visibleWidth;
      } else if (right > imageWidth) {
        right = imageWidth;
        left = right - visibleWidth;
      }
    }
    if (visibleHeight >= imageHeight) {
      top = 0;
      bottom = imageHeight;
    } else {
      if (top < 0) {
        top = 0;
        bottom = visibleHeight;
      } else if (bottom > imageHeight) {
        bottom = imageHeight;
        top = bottom - visibleHeight;
      }
    }
    return new SourceRect(
        Math.round(left), Math.round(top), Math.round(right), Math.round(bottom));
  }

  /** An inclusive-ish integer source rect; {@code left<right} and {@code top<bottom}. */
  public static final class SourceRect {
    public final int left;
    public final int top;
    public final int right;
    public final int bottom;

    public SourceRect(int left, int top, int right, int bottom) {
      this.left = left;
      this.top = top;
      this.right = right;
      this.bottom = bottom;
    }

    public int width() {
      return right - left;
    }

    public int height() {
      return bottom - top;
    }
  }
}
