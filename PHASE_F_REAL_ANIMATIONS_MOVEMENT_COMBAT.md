# Phase F: Real Animations, Movement, and Combat

Status: COMPLETE — the real chinaman_fighter character (41-bone skinned rig from
Phase E) is now the in-world player inside the Phase D region 32785 mobile
client. It runs a real animation state machine (idle / walk / run / attack)
driven by joystick + keyboard, rotates toward movement direction, and fights a
training dummy in a combat vertical slice (attack anim, impact timing, damage,
HP bar, death, respawn). A critical rendering bug was also fixed: the Phase E
viewer refactor never added the skinned meshes to the scene, so the character
was invisible everywhere; it now renders correctly in both the viewer and the
world.

## Goal

```
Phase D world (region 32785)  ->  real CharacterRig player
  -> state machine: idle / walk / run / attack
  -> keyboard (WASD) + virtual joystick movement, camera-relative
  -> yaw rotation toward movement direction (and toward attack target)
  -> combat vs training dummy: attack anim -> impact at 42% -> damage -> HP bar
```

Reuses the Phase E character pipeline (`character_loader.ts` + extracted
assets); no new PK2 parsing was needed for this phase. The animation set is the
real chinaman_fighter BAN data already exported in Phase E (idle, idle_city,
walk, run, attack, attack2).

## Runtime (`map/src/game/`)

### New: `character_rig.ts` — shared CharacterRig

One skinned rig used by both the Phase E viewer and the Phase F world:

- `load()` fetches skeleton/meshes/anims/meta + textures, builds the 41-bone
  `THREE.Skeleton` from bind data (`calculateInverses`), creates the 16
  `SkinnedMesh` parts with per-texture render modes, **adds them to the rig
  group**, and applies the bind pose.
- Per-bone keyframe interpolation: `Quaternion.slerp` + position lerp with a
  single global time index (all bones share equal keyframe counts).
- `play(id)`, `update(dt)`, `applyPose(t)`, `getBoneWorld(i)`,
  `getBoneQuaternionWorld(i)`, `dispose()`, `skeleton`/`meshes`/`group`.
- Scale 0.15, `height`/`name` getters. The rig group holds the skeleton bones
  and all meshes, so a single object is dropped into any scene.

### Fixed: meshes were never added to the scene

The Phase E viewer refactor built the `SkinnedMesh` parts but omitted
`group.add(mesh)`; bones were in the scene but the character was invisible in
both the viewer and the world. CharacterRig now adds every mesh to its group.
This is the primary visual fix of this phase (viewer lit pixels went from
<1% to 18%; world now shows the character too). Foot bones render at y≈0
relative to the rig root, so the world places the root at `spawn.y` (terrain
surface is y≈0 at spawn in region 32785); the previous `FOOT_GROUND_Y`
constant was removed to stop the character sinking ~0.19 units into the floor.

### Rewritten: `game3d.ts` — playable in-world character

- Player is a real `CharacterRig` (scale 0.15) at the region spawn
  (1134.79, ~0, -864.29).
- `AnimState = "idle" | "walk" | "run" | "attack"` driven by `setMovement(x, z)`
  (normalized, camera-relative world-space input) and `attack()`.
  - walk 70 u/s, run 125 u/s; run threshold magnitude > 0.55.
  - The model faces -Z locally, so forward = `(-sin(yaw), -cos(yaw))` and the
    target rotation = `atan2(-wx, -wz)`; yaw lerps at 10/s.
  - Run/walk BAN root `Bip01` keyframes are pose-only (no baked forward
    translation), so the client applies forward displacement at the movement
    speed; real ground contact is preserved because the feet stay planted in the
    anim.
- Combat vertical slice:
  - `attack()` plays the real `attack` anim (1133 ms); impact is applied at
    42% of the duration (verified the R Hand reaches max reach by then).
  - Damage 15-25 vs the training dummy (2.4 range + >25 degree facing check).
  - Dummy: 100 HP, canvas-drawn HP bar sprite, death/destroy + 5 s respawn,
    floating damage text, "You hit the training dummy for N damage (hp/100)"
    log lines. No real NPC data was needed for the slice; the real Dungeon Exit
    NPC at the spawn is untouched.
- Third-person camera (CAM_DIST 11, pitch clamped 0.12-1.15) follows and
  rotates with the player.
- `window.__sro3d` debug API on GameWorld: `getPlayerPos`, `getPlayerRotation`,
  `getCameraPos`, `yaw`, `pitch`, `rigReady`, `anim`, `rigAnim`, `rigStats`
  ({bones, meshes, height, scale}), `getBoneWorld`, `setMove`, `setPlayerPos`,
  `setPlayerRotationY`, `attack`, `dummy` ({x, z, hp, maxHp, alive, hits,
  lastDamage}).

### Viewer (`character_viewer.ts`) — refactored onto CharacterRig

- Same debug API + UI preserved (`__charviewer` camPos/target/yaw/project/
  groupScale/resetView/getBoneWorld/setPose/getTime/isPlaying/animId).
- Two-sided lighting so the orbiting camera always sees a lit side of the
  model (which faces -Z).

## Validation (all real, headless Chromium + SwiftShader)

- Build: `deno task build` (tsc 0 errors + vite) passes; `index-*.js` ~960 kB
  (gzip ~265 kB; benign >500 kB chunk warning only).
- **Phase F: 15/15 pass** (`/tmp/opencode/validate_phase_f.js`) — intro -> create
  "PhaseFTest" warrior -> enter world -> real rig (41 bones, 16 meshes, 2.39 m)
  -> idle -> spawn at verified point -> keyboard RUN + rotation.y ~0.49 ->
  idle after stop -> joystick WALK -> approach dummy -> attack anim (state
  machine + rig) -> dummy HP 100 -> 78 with damage log -> idle after attack ->
  WebGL canvas shows the character (litPct ~3%) -> no console/page errors.
- **Phase E regression: 9/9 pass** (`/tmp/opencode/validate_phase_e.js`) —
  viewer renders the real character (litPct ~18%, brightPct ~6%) and all
  animation/UI checks stay green after the CharacterRig refactor.
- Ground placement verified: feet bones at y≈0, head at y≈2.25 with the root at
  spawn.y; terrain surface at spawn is y≈0.

## Files Changed (Phase F)

- `map/src/game/character_rig.ts` (new) — shared skinned rig + animation state.
- `map/src/game/character_viewer.ts` (modified) — refactored onto CharacterRig;
  fixed invisible meshes; two-sided lighting; `__charviewer` preserved.
- `map/src/game/game3d.ts` (rewritten) — real player, anim state machine,
  camera-relative movement, rotation, combat dummy + HP bar + damage text,
  `__sro3d` debug API; removed stale `FOOT_GROUND_Y` sink offset.
- `PHASE_F_REAL_ANIMATIONS_MOVEMENT_COMBAT.md` (this file).

`game_source/` stays untracked; no PK2/archive/database/server files committed.

## Remaining Limitations

- Only `chinaman_fighter` is playable; other presets need the Phase E `PRESETS`
  list + `extract_character.py` re-run.
- Combat is a training-dummy slice (no real NPC AI/aggro, no player HP, no
  loot); the attack anim is used for the hit regardless of weapon type.
- `attack2` (combo) and `idle_city` are exported and in the anim set but not
  wired into gameplay; knockback/skill BAN variants exist but no dedicated
  hit/damage BAN was found in the extracted set.
- The hit window uses a fixed 42% fraction of the attack duration rather than a
  frame-accurate impact marker from the BAN data.
- SwiftShader headless is ~3 fps; real GPUs run at 60 fps.
