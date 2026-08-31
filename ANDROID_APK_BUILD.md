# Building the Android APK (native)

The Android app is now fully native: `GameActivity` is the launcher and renders
the world with `NativeWorldRenderer` (Canvas) from committed native assets under
`android/app/src/main/assets/game/`. There is no WebView, no Capacitor, and no
`map/dist` web build in the Android runtime. The `map/` Vite app remains a
separate browser product and is not part of the APK.

## How it is structured

- `android/` — the native Android project (committed source). Build outputs,
  Gradle caches and generated assets are gitignored.
- `android/app/src/main/assets/game/` — committed native assets (world terrain,
  textdata tables, character store, manifests). Loaded at runtime by the native
  loaders; nothing is copied from the web build.
- `android/app/src/main/java/com/opensilkroadmap/app/game/GameActivity.java` —
  native launcher; drives a fixed-timestep `GameLoop` heartbeat with a monotonic
  `GameClock`.
- `.github/workflows/android-apk.yml` — CI that builds a debug APK on every push
  to `main` (and on `workflow_dispatch`) and uploads it as a workflow artifact.

The retired Capacitor/WebView wrapper is preserved under `legacy/capacitor/`
(config, lockfile, scaffold gradle files) for reference; it is no longer applied
by any build.

## Getting the APK from GitHub Actions

1. Open the repository on GitHub.
2. Click the **Actions** tab.
3. Select the **Build Android Debug APK** workflow (left sidebar).
4. Click the latest successful run (the commit that triggered it).
5. Scroll to the **Artifacts** section at the bottom of the run summary.
6. Download **`opensilkroadmap-debug-apk`** — it contains `app-debug.apk`.

If you want a build on demand, open the workflow and click
**Run workflow** → **Run workflow** (uses the `workflow_dispatch` trigger).

## Installing the APK on a phone

1. On the Android device, enable **Developer options** and **USB debugging**, or
   allow installation from unknown sources.
2. Either:
   - Connect the device over USB and run
     `adb install -r app-debug.apk` (from the extracted artifact), or
   - Copy `app-debug.apk` to the phone and open it to install (tap
     **Settings → Allow from this source** if prompted).
3. Launch the **OpenSilkroadMap** app (native, no WebView).

Notes:

- The debug APK is signed with the auto-generated Android **debug keystore**;
  it is fine for testing, not for Play Store release.
- Android 6.0+ (API 22+) is required (`minSdkVersion 22`).
- The native app loads bundled assets; no network is required for the world view.

## Building the APK locally

Prerequisites: JDK 17 and the Android SDK (platform 34 + build-tools 34.0.0)
with accepted licenses.

```shell
cd android
./gradlew assembleDebug
# output: android/app/build/outputs/apk/debug/app-debug.apk
```

## Building a signed release APK

The debug APK is convenient for testing but is signed with the shared Android
debug keystore. For an installable release build, create a release keystore and
run `assembleRelease`:

```shell
# 1. generate a release keystore (one-time; keep it safe)
keytool -genkeypair -v \
  -keystore app/release.keystore \
  -alias opensilkroadmap -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=OpenSilkroadMap, OU=Map, O=OpenSilkroadMap, L=Local, ST=Local, C=US"

# 2. store the credentials (gitignored)
#    app/keystore.properties
#    storeFile=release.keystore
#    storePassword=<your-store-password>
#    keyAlias=opensilkroadmap
#    keyPassword=<your-key-password>

# 3. build the signed release APK
cd android
./gradlew assembleRelease
# output: android/app/build/outputs/apk/release/app-release.apk
```

`android/app/build.gradle` wires the release `signingConfig` from
`app/keystore.properties`. Both the keystore and the properties file are
gitignored; when they are absent the release build still compiles but produces
an unsigned APK (fine for CI, not installable on a device). Verify the signature
with:

```shell
$ANDROID_HOME/build-tools/34.0.0/apksigner verify --print-certs \
  app/build/outputs/apk/release/app-release.apk
```

## What is deliberately NOT committed

- `map/node_modules/`
- `map/dist/` (web build output)
- `android/build/`, `android/app/build/`, `android/.gradle/`, `.cxx/`
- `local.properties` (machine-specific SDK path)
- `android/app/release.keystore` + `android/app/keystore.properties` (release signing secrets)
- any `*.apk` / `*.aab` binaries
