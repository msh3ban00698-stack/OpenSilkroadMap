package com.opensilkroadmap.app.minimap;

/**
 * A decoded asset held by the bounded cache. Implementations own a concrete
 * native payload (e.g. an {@link android.graphics.Bitmap}) and free it in
 * {@link #release()}.
 */
public interface DecodedAsset {
  String sourcePath();

  int width();

  int height();

  int sizeBytes();

  void release();
}
