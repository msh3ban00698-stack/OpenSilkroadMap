package com.opensilkroadmap.app.minimap;

import java.io.IOException;
import java.io.InputStream;

/**
 * Decodes a resolved output asset stream into a {@link DecodedAsset}.
 * Implementations are free to use native codecs (e.g.
 * {@link android.graphics.BitmapFactory}); the provider does not care how.
 */
public interface AssetDecoder {
  DecodedAsset decode(String sourcePath, InputStream data) throws IOException;
}
