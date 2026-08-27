package com.opensilkroadmap.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
  @Override
  public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    // Android WebView scales text with the system font size setting, which
    // breaks fixed mobile layouts on devices using non-default font scale.
    // Pin the WebView text zoom so CSS pixel sizes render exactly as designed.
    if (this.bridge != null && this.bridge.getWebView() != null) {
        this.bridge.getWebView().getSettings().setTextZoom(100);
    }
  }

  @Override
  public void onResume() {
    super.onResume();
    if (this.bridge != null && this.bridge.getWebView() != null) {
        this.bridge.getWebView().getSettings().setTextZoom(100);
    }
  }
}
