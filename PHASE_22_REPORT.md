# Phase 22 Report — Native Android Runtime Migration (remove WebView/Capacitor)

Date: 2026-08-31
Branch: `260831-feat-phase22-native-runtime`
Scope: Remove the Capacitor/WebView runtime from the Android app and make the
native `GameActivity` the launcher, with a real fixed-timestep frame loop. No
gameplay is invented; the runtime is a native skeleton that consumes the real
committed assets already produced by Phases 10–21.

---

## 1. Audit (gate before any deletion)

`WEB_RUNTIME_AUDIT.md` classifies every WebView/Capacitor/browser component into
five buckets (SOURCE / REUSABLE / OBSOLETE-WEB / DUPLICATE / DEAD) and corrects
one Phase 21 finding: `QuestDataTable`, `RefShopGoodsTable`, `LevelGoldTable`
are NOT dead — they are referenced by `TextDataTablesTest.java` and remain
SOURCE (native data parsers). They are untouched in Phase 22.

## 2. Changes

### 2.1 Native launcher + manifest
- `android/app/src/main/AndroidManifest.xml` — launcher `MAIN/LAUNCHER`
  intent-filter moved from `MainActivity` to `.game.GameActivity`.
  `MainActivity` is now a non-exported redirect.
- `android/app/src/main/java/com/opensilkroadmap/app/MainActivity.java` — no
  longer extends Capacitor `BridgeActivity`; now a plain `Activity` that starts
  `GameActivity` and finishes. No WebView, no Capacitor.

### 2.2 Capacitor/WebView removal (relocated, not deleted)
- `android/app/build.gradle` — removed `:capacitor-android`,
  `:capacitor-cordova-android-plugins`, `apply from: 'capacitor.build.gradle'`,
  and the capacitor flatDir repo dir.
- `android/settings.gradle` — reduced to `include ':app'`.
- `.github/workflows/android-apk.yml` — removed npm/Deno/cap-sync steps; builds
  directly with `./gradlew assembleDebug`.
- `ANDROID_APK_BUILD.md` — rewritten for the native build.
- The Capacitor artifacts are preserved under `legacy/capacitor/` (move, not
  delete): `capacitor.config.ts`, `package.json`, `package-lock.json`,
  `android/app/capacitor.build.gradle`, `android/capacitor.settings.gradle`, and
  the two `com/getcapacitor/myapp` example tests.

### 2.3 Native runtime core (new, Android-free, unit-tested)
- `.../game/GameClock.java` — monotonic frame clock with a clamped per-frame
  delta (default max 0.1 s); engine-safety bound, not authentic VSRO timing.
- `.../game/InputController.java` — gesture accumulator (drag pan, pinch zoom,
  normalized joystick direction); drained per frame.
- `.../game/GameActivity.java` — drives a `GameLoop` heartbeat fed by
  `GameClock` via a `postOnAnimation` frame callback; `onResume`/`onPause`
  start/stop the loop.
- `.../world/NativeWorldRenderer.java` — touch now feeds `InputController`;
  `applyInput()` drains pan/zoom intents each frame in `onDraw`.

### 2.4 Tests
- `.../game/GameClockTest.java` — 6 tests.
- `.../game/InputControllerTest.java` — 6 tests.

## 3. Verification

Executed in THIS environment:
- `javac 17` compile of pure-JVM game classes (`GameClock`, `InputController`,
  `GameLoop`, `Camera2D`) + their 4 test classes against the JUnit API stubs:
  **COMPILE_OK**.
- A standalone behavioral harness (`/tmp/opencode/phase22/Verify.java`) exercised
  `GameClock`, `InputController`, `GameLoop`, and `Camera2D` with real value
  assertions: **ALL_PASS** (18 checks). One transient harness failure was a
  harness bug (default 0.1 s clamp vs a 0.5 s expected delta), not a code bug.

NOT EXECUTED (no Android SDK / Gradle / emulator in this environment):
- `./gradlew assembleDebug`, `./gradlew test`, `./gradlew connectedAndroidTest`.
- Structural review only for Android-bound classes (`GameActivity`,
  `NativeWorldRenderer`, `MainActivity`, manifest, gradle). No APK was built and
  no instrumented test was run; nothing is claimed as executed.

## 4. What is deliberately preserved

- The `map/` Vite web app (browser product + conversion source) is unchanged.
- All native asset loaders and the `scripts/*.py` conversion pipeline.
- The retired Capacitor wrapper under `legacy/capacitor/` (reference only).

## 5. Blockers / unknowns

- No Android SDK/Gradle/emulator → APK and instrumented tests NOT EXECUTED.
- Real VSRO tick rate, movement speed/world units, and server timing remain
  UNKNOWN from source; `GameClock`/`GameLoop` are engine scaffolding, not
  authentic VSRO timing.
- `InputController.setMove` produces a normalized direction only; the consumer
  that maps it to world movement is a future phase (not invented here).

## 6. Next steps (future phases)

- Implement a native game-state consumer that maps `InputController` movement and
  `GameLoop` fixed steps to player position/simulation.
- Wire real skinned character animation playback into the frame loop
  (`CharacterMeshIndex.poseAt(name, tMs)`), currently only bind-pose/static.
- Add a native HUD/UI layer (Jetpack Compose) to replace the diagnostic
  `TextView` overlay in `GameActivity`.
