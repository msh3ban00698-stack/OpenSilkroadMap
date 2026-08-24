import type { CapacitorConfig } from "@capacitor/cli";

// The web game lives in map/ and is built with `deno task build` into
// map/dist. Capacitor only wraps that build output; the game itself is
// unchanged. webDir is relative to this file (repo root).
const config: CapacitorConfig = {
  appId: "com.opensilkroadmap.app",
  appName: "OpenSilkroadMap",
  webDir: "map/dist",
  android: {
    // The game fetches map tiles/NPC data over /assets (bundled locally), and
    // Google Fonts over https. No cleartext sources are required, so the
    // default "https" WebView scheme is kept.
    allowMixedContent: false,
  },
};

export default config;
