# Building the Android APK (Capacitor)

The game (all of Phase A-H) is unchanged; this adds a thin Capacitor wrapper so
the same Vite web build (`map/dist`) ships as a native Android app. The web app
stays a Deno-managed Vite project (`deno task build`); Capacitor only copies the
production build output into the Android project and packages it.

## How it is structured

- `package.json` / `package-lock.json` — Capacitor CLI + core + Android platform.
- `capacitor.config.ts` — app id `com.opensilkroadmap.app`, app name
  `OpenSilkroadMap`, `webDir: "map/dist"`.
- `android/` — the generated Capacitor native project (committed source).
  Build outputs, Gradle caches and the synced web assets are gitignored
  (`android/.gitignore` + root `.gitignore`).
- `.github/workflows/android-apk.yml` — CI that builds a debug APK on every push
  to `main` (and on `workflow_dispatch`) and uploads it as a workflow artifact.

## Getting the APK from GitHub Actions

1. Open the repository on GitHub.
2. Click the **Actions** tab.
3. Select the **Build Android Debug APK** workflow (left sidebar).
4. Click the latest successful run (the commit that triggered it).
5. Scroll to the **Artifacts** section at the bottom of the run summary.
6. Download **`opensilkroadmap-debug-apk`** — it contains
   `app-debug.apk`.

If you want a build on demand, open the workflow and click
**Run workflow** → **Run workflow** (uses the `workflow_dispatch` trigger).

## Installing the APK on a phone

1. On the Android device, enable **Developer options** and
   **USB debugging**, or just allow installation from unknown sources.
2. Either:
   - Connect the device over USB and run
     `adb install -r app-debug.apk` (from the extracted artifact), or
   - Copy `app-debug.apk` to the phone and open it to install (tap
     **Settings → Allow from this source** if prompted).
3. Launch the **OpenSilkroadMap** app.

Notes:

- The debug APK is signed with the auto-generated Android **debug keystore**;
  it is fine for testing, not for Play Store release.
- Android 6.0+ (API 22+) is required (`minSdkVersion 22`).
- Some map layers / tile data load over the network; an internet connection is
  recommended.

## Building the APK locally

Prerequisites: Deno (for the web build), Node.js 18+ (npm), JDK 17, and the
Android SDK (platform 34 + build-tools 34.0.0) with accepted licenses.

```shell
# 1. install Capacitor tooling
npm ci

# 2. build the production web assets into map/dist
deno task build

# 3. copy web assets into the Android project
npx cap sync android

# 4. compile the debug APK
cd android
./gradlew assembleDebug
# output: android/app/build/outputs/apk/debug/app-debug.apk
```

A single shortcut for steps 2-4:

```shell
npm run apk:build
```

To open the project in Android Studio:

```shell
npx cap open android
```

## Updating the game

Nothing special: change the web app, commit, and the next push to `main` rebuilds
the APK. To regenerate the native project from scratch (e.g. after upgrading
Capacitor), run `npx cap add android` again.

## What is deliberately NOT committed

- `node_modules/` (root and `map/`)
- `map/dist/` (web build output)
- `android/build/`, `android/app/build/`, `android/.gradle/`, `.cxx/`
- `android/app/src/main/assets/public/` (synced web assets)
- `local.properties` (machine-specific SDK path)
- any `*.apk` / `*.aab` binaries
