package com.opensilkroadmap.app.minimap;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import java.io.IOException;
import java.io.InputStream;

/** Decodes minimap PNG streams with {@link BitmapFactory}. */
public final class BitmapFactoryDecoder implements AssetDecoder {
  @Override
  public DecodedAsset decode(String sourcePath, InputStream data) throws IOException {
    Bitmap bitmap = BitmapFactory.decodeStream(data);
    if (bitmap == null) {
      throw new IOException("BitmapFactory could not decode '" + sourcePath + "'");
    }
    return new BitmapAsset(sourcePath, bitmap);
  }
}
