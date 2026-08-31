package com.opensilkroadmap.app;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import com.opensilkroadmap.app.game.GameActivity;

/**
 * Legacy entry point retained for compatibility only.
 *
 * <p>The app is now native: {@link GameActivity} is the launcher (see
 * {@code AndroidManifest.xml}). This activity contains no WebView and no Capacitor
 * runtime; it simply forwards to the native game host and finishes, so any stale
 * deep link or shortcut that still resolves to the old name lands in the native
 * game instead of a WebView.
 */
public final class MainActivity extends Activity {
  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    startActivity(new Intent(this, GameActivity.class));
    finish();
  }
}
