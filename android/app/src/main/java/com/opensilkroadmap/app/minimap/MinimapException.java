package com.opensilkroadmap.app.minimap;

/** Base exception for the native minimap asset layer. */
public class MinimapException extends Exception {
  public MinimapException(String message) {
    super(message);
  }

  public MinimapException(String message, Throwable cause) {
    super(message, cause);
  }

  /** The manifest could not be parsed. */
  public static class ManifestParseException extends MinimapException {
    public ManifestParseException(String message) {
      super(message);
    }

    public ManifestParseException(String message, Throwable cause) {
      super(message, cause);
    }
  }

  /** No manifest record exists for the requested source path. */
  public static class ResolutionException extends MinimapException {
    public ResolutionException(String message) {
      super(message);
    }
  }

  /** The resolved output asset could not be read or decoded. */
  public static class MissingAssetException extends MinimapException {
    public MissingAssetException(String message) {
      super(message);
    }
  }

  /** The decoded asset failed structural or dimensional validation. */
  public static class InvalidAssetException extends MinimapException {
    public InvalidAssetException(String message) {
      super(message);
    }
  }

  /** The decoded asset dimensions do not match the manifest metadata. */
  public static class DimensionMismatchException extends InvalidAssetException {
    public DimensionMismatchException(String message) {
      super(message);
    }
  }
}
