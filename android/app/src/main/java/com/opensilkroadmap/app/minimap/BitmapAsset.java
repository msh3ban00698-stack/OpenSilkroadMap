package com.opensilkroadmap.app.minimap;

import android.graphics.Bitmap;

/** {@link DecodedAsset} wrapping a native {@link Bitmap}; release recycles it. */
public final class BitmapAsset implements DecodedAsset {
  private final String sourcePath;
  private Bitmap bitmap;
  private boolean released;

  public BitmapAsset(String sourcePath, Bitmap bitmap) {
    if (bitmap == null) {
      throw new IllegalArgumentException("bitmap must not be null");
    }
    this.sourcePath = sourcePath;
    this.bitmap = bitmap;
  }

  public Bitmap bitmap() {
    if (released) {
      throw new IllegalStateException("asset '" + sourcePath + "' has been released");
    }
    return bitmap;
  }

  @Override
  public String sourcePath() {
    return sourcePath;
  }

  @Override
  public int width() {
    return bitmap.getWidth();
  }

  @Override
  public int height() {
    return bitmap.getHeight();
  }

  @Override
  public int sizeBytes() {
    return bitmap.getByteCount();
  }

  @Override
  public void release() {
    if (released) {
      return;
    }
    released = true;
    bitmap.recycle();
    bitmap = null;
  }
}
