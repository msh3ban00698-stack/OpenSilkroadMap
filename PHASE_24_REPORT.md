# PHASE 24 REPORT — Player Foundation: Identity, Spawn, Input, Movement, Camera, Locomotion Animation

Branch: `260831-feat-phase24-player-spawn-movement` · Baseline: Phase 23 HEAD `ae1d82547d9b5e96f4e57fb7d977b9d94ee7e7d3`
Date: 2026-08-31

This phase adds the PLAYER increment on top of the verified Phase 23 character/NPC
runtime. It wires a native player foundation — identity resolution, fail-closed
spawn handling, joystick input, movement integration, camera follow, and the
proven IDLE/WALK/RUN locomotion animation — entirely from committed real data.
Nothing is invented: where the original source is absent (player spawn, walk/run
speeds) the runtime fails closed and the record says UNKNOWN. All Phase 23
character/NPC work and NPC architecture is preserved and re-verified.

---

## 1. Scope, baseline, and deliverables

Baseline (verified before this phase): commit `ae1d8254`, branch
`260831-feat-phase23-character-animation`, local==remote==HEAD, clean tree,
69 JVM tests PASS / 0 FAIL (13 classes).

| Task | Deliverable |
|---|---|
| A | Player spawn investigation: exhaustive source search, spawn UNKNOWN + fail-closed |
| B | Player identity resolution from the committed `player` manifest/skeleton chain |
| C | Native input trace + joystick intent (pure math, bounded tests) |
| D | Proven movement subset: direction→displacement integration, speeds UNKNOWN |
| E | Camera follow of the placed player on the existing `Camera2D` |
| F | World/region evidence: Jangan/Jangan_Field windows, runtime region selection, coordinate wiring |
| G | Player IDLE/WALK/RUN integration via `AnimStateResolver`/`CharacterAnimator` |
| H | NPC preservation: Phase 23 suite intact, player never disturbs NPC clocks |
| I | Full bounded JVM suite (112 tests) + evidence report |

## 2. Verification methodology

Pure-JVM harness under `/tmp/opencode/phase24/`: custom `JUnitRunner` + real
`org.junit.Assert` (`junitreal`), JDK 17 (`/usr/bin/javac`, `/usr/bin/java`).
Every run is from `/workspace/android/app` with bounded timeouts. The Android
stubs were extended so `AssetManager.open()` resolves to the real committed
assets under `src/main/assets` (file-backed), letting tests load the REAL player
model chain. Android-bound classes (`GameActivity`, `NativeWorldRenderer`,
`MainActivity`, minimap) remain compile-only against stubs, as in Phase 23.

**112 tests PASS, 0 FAIL** (69 Phase 23 + 43 Phase 24; §11).

## 3. TASK A — player spawn investigation (INVESTIGATED UNKNOWN, fail-closed)

Exhaustive search of the supplied source/data (TASK A in Phase 24 plan):
- Textdata corpus: 159 files under `/tmp/opencode/textdata/` (source
  `/server_dep/silkroad/textdata/` + `/event/`), grepped for `startpos`,
  `start_pos`, `spawnpoint`, `newchar`, `charcreate`, `gamedata`, `.sql`,
  `.bak`, `.ini`, `.cfg`, server/gameserver/shard configs.
- Full inventory (`COMPLETE_SOURCE_INVENTORY.json`, 119,631 files across
  Data/Map/Media/Music/Particles.pk2): no SQL server DB / start table.
- `npcpos.txt` (18,457 rows) is NPC-only; `gameworlddata.txt` (117),
  `gameworldconfigdata.txt` (1,029), `teleportdata.txt` (248),
  `teleportlink.txt` (353), `refoptionalteleport.txt` (46), `worldmap_*.txt`,
  `regioncode.txt` (3,294), `textzonename.txt` (4,251), `specialnpcdata.txt`,
  `usableresobjiddata.txt`, `charactervisualchange.txt` — none contains a
  player start position.

Result: **no verified player spawn exists**. The committed `player` key has no
static position and is never spawned by npcpos (TASK F). The runtime therefore
defaults to `PlayerSpawn.unknown(...)` and the `PlayerController` never places
the player, never fabricates a coordinate, and reports `UNKNOWN_SPAWN` (§5/§8).

The `PlayerSpawn.verified(...)` factory exists ONLY to lock the proven world
projection formula (`world = (sector − ref)·1920 + local`, Phase 10); tests use
clearly-labeled synthetic sources, never claimed real data.

## 4. TASK B — player identity (PARTIAL; manifest/skeleton chain PROVEN)

`PlayerIdentity` resolves the committed `player` chain
(`game/world/characters/player/manifest.json` + `chinaman_skel`), and
`PlayerIdentityTest` (5 tests) locks it:

- The player key is `CharacterCatalog.PLAYER_KEY` (`"player"`), absent from the
  NPC refid index (never spawned).
- Manifest resolves 5 real clips → **IDLE/WALK/RUN only**, real names and
  durations: `chinaman_standbattle` 2000 ms, `chinaman_fighter_walkforward`
  1166 ms, `chinaman_fighter_runforward_sword` 666 ms (real `.ban` durations).
- Committed skeleton parses to **38 bones** (`xyzw`, root `Bip01`,
  `chinaman_skel.bsk`).

PARTIAL (kept visible, never hidden):
- Provenance records the original `chinaman_fighter.bsr` referencing
  `europeman_skel` (43 bones), not the committed `chinaman_skel`.
- NEW Phase 24 finding: `CharacterMeshIndex.load(assets, "player")` **fails
  closed** — 2 of the 16 skinned parts (`clothes_01_sa`, `sword_01`) reference
  bones `Bone01`/`Bone03`/`Bone05` that do NOT exist in the committed 38-bone
  skeleton (chinaman_skel uses `Bip01*` naming; the gear parts were authored
  against the european skeleton). This is the concrete data manifestation of
  the PARTIAL identity and is asserted by
  `PlayerControllerTest#fullPlayerModelLoadIsPartialAndFailsClosed`.
- Because the ANIMATION chain is fully committed, the phase adds
  `CharacterMeshIndex.animationsOnlyIndex(...)` (pure-JVM, no mesh parts) so the
  real player animator and pose sampling are exercised against real data even
  though the full mesh chain is PARTIAL. The strict NPC loader is unchanged.

## 5. TASK C — native input trace + joystick (IMPLEMENTED PROVEN, structural)

Trace: `MainActivity` (retired redirect) → `GameActivity` (native launcher) →
`GameLoop`/`GameClock` fixed-timestep heartbeat → `NativeWorldRenderer.onTouchEvent`
feeds the shared `InputController` (pure intent accumulator) → `PlayerController`
consumes the move axis; the renderer drains pan/zoom each frame. No gameplay
logic lives in Android UI callbacks.

Phase 24 additions (structural, not claimed authentic SRO input):
- `InputController.joystick(dxPx, dyPx, radiusPx)`: normalized direction with an
  analog magnitude inside the radius, clamped to 1 outside, dead zone 0.15.
- `NativeWorldRenderer.onTouchEvent`: left-half single-finger = movement
  joystick (radius 56 dp), right-half single-finger = pan, two-finger = pinch.
- `InputControllerTest` now runs (11 tests, 5 new joystick cases): dead zone,
  normalization, clamp, analog magnitude, diagonal normalization.

## 6. TASK D — proven movement subset (IMPLEMENTED PROVEN math; speeds UNKNOWN)

`PlayerMover` integrates a normalized input direction into world x/z
displacement and a facing heading:

- World axes follow the proven projection convention (screen +X = world +X,
  screen +Y = world −Z), so a joystick push up moves world −Z.
- `PlayerMover.step(dir, dt, config)`: zero direction → `ZERO_DIRECTION`;
  unproven speed → `UNKNOWN_SPEED` (no displacement fabricated); proven speed →
  `displacement = dir·speed·dt`.
- Heading `atan2(dirX, dirZ)` is the exact inverse of the PROVEN placement
  rotation (`NativeWorldRenderer.worldVertex`: local +Z rotated by h maps to
  world `(sin h, cos h)`), verified in `PlayerMoverTest` over four axes.

Speeds remain UNKNOWN: the inventory has no `CharacterData`/`SkillData`
movement values (Phase 21 audit F — MISSING). The runtime uses
`PlayerMovementConfig.unknownSpeed()`, so the player plays the real walk clip
without fabricated movement and reports `UNKNOWN_SPEED` (§8). A speed can only
be introduced from a future verified source via `withWalkSpeed`.

## 7. TASK E — camera follow (IMPLEMENTED PROVEN, on existing Camera2D)

- `PlayerController.cameraTarget()` returns the player's world position once a
  verified spawn has been placed, else null. `GameActivity` per frame calls
  `world.setCamera(target, ppu)` → `Camera2D.follow` (existing clamp math).
- No follow while the spawn is UNKNOWN (fail-closed).
- Supporting evidence: the real `Media/config/cameradata.txt` exists in the
  corpus (e.g. `79 107 1205 80 396 30 10 0 50`) but its field semantics are
  UNKNOWN — no authentic camera values are wired. `camera_path.txt` in the
  Phase 10 workspace is a synthetic test fixture, not game data.
- Camera distance/zoom remain the existing generic pixels-per-unit (0.5), not
  claimed authentic.

## 8. TASK G — player IDLE/WALK/RUN integration (IMPLEMENTED PROVEN)

`PlayerController` binds input → state → entity → the proven animator
(`AnimStateResolver` → `CharacterAnimator`), fail-closed in this order:

1. no entity → `NO_ENTITY`; 2. unresolved identity → `UNRESOLVED_IDENTITY`;
3. no verified spawn → `UNKNOWN_SPAWN` (player never placed, never drawn);
4. else place once at the proven projected coordinate, then:
   - zero input → IDLE (`chinaman_standbattle`);
   - non-zero input → locomotion clip, **WALK preferred** (RUN fallback, IDLE
     last — the walk/run speed split is UNKNOWN, so the selection is explicit
     and documented, not invented); heading faces the direction;
   - displacement applied only with a proven speed (currently UNKNOWN → reason
     `UNKNOWN_SPEED`, the real walk clip still plays).

Each entity owns its own animation clock: the controller advances ONLY the
player entity — `controllerNeverTouchesAnotherEntityClock` proves a bystander
entity stays IDLE at time 0 while the player's clock advances. NPC clocks are
untouched (Phase 23 preservation, TASK H).

## 9. TASK F — world/region evidence + coordinate wiring (IMPLEMENTED PROVEN)

Locked by `PlayerWorldRegionTest` (7 tests) against the committed
`world_regions.tsv` (real `Data.pk2 /RegionInfo.txt`, sha256
`787d9b417cf3044ff9260f484656002089f7406afd57f229a3c5ac85460739ff`):

- TOWN `Jangan` window 167–169 × 96–99, ref (167,96), 12 cells.
- FIELD `Jangan_Field` window 156–182 × 89–102, ref (156,89), 171 cells.
- Committed real `.hg` sectors: (156,89), (156,90). The Jangan town ref
  (167,96) has NO committed `.hg`, so the runtime region-selection rule (first
  region whose ref sector has a committed `.hg`) resolves to **Jangan_Field
  (156,89)** — the anchor for any player world coordinate.
- Proven formula places the Jangan town origin inside the Jangan_Field frame at
  (21120, 13440) — the coordinate system a future verified player spawn uses.
- The player key is never spawned by npcpos (no npcpos refid resolves to
  `"player"`); region code 25000 = `RN_CH_JANGAN` (regioncode.tsv) and is the
  zone of the real Chang'an gate (teleportdata.tsv GATE_CH).

## 10. TASK H — NPC preservation (VERIFIED)

All 13 Phase 23 test classes (69 tests) pass unchanged. The player integration
adds a SEPARATE player entity path (`setPlayer` + `drawPlayer` in
`NativeWorldRenderer`, `PlayerController` in `GameActivity`); NPC spawning,
entity maps, per-spawn clocks, and the strict character loader are untouched.
The strict loader's fail-closed behavior is preserved (and the player's PARTIAL
load now proves it: it returns null rather than a partial model).

## 11. JVM test matrix (all PASS, JDK 17, bounded timeouts)

| Test class | Count |
|---|---|
| Phase 23 classes (13 classes: AnimationPlayer, IdleAnimResolver, AnimStateResolver, CharacterAnimator, CharacterRuntimeData, CharacterManifestEnumeration, CharacterMeshIndex, CharacterMeshIndexMulti, CharacterChain, PlayerModel, NpcCharacterLinkage, CharacterCatalog, NpcSpawnIndex) | 69 |
| `PlayerSpawnTest` (TASK A/D) | 4 |
| `PlayerIdentityTest` (TASK B) | 5 |
| `PlayerMoverTest` (TASK D) | 6 |
| `PlayerControllerTest` (TASK C/D/E/G) | 10 |
| `InputControllerTest` (TASK C, incl. 5 new joystick) | 11 |
| `PlayerWorldRegionTest` (TASK F) | 7 |
| **TOTAL** | **112** |

## 12. NOT EXECUTED

- Android APK build, `./gradlew test`, instrumented/device tests: no Android
  SDK/Gradle/emulator (`sdkmanager`/`adb`/`gradle` absent from PATH). No device
  claim is made; `GameActivity`/`NativeWorldRenderer` changes are compile-only
  against Android stubs.
- `Media/config/cameradata.txt` semantics: not parsed (UNKNOWN fields).

## 13. Blockers / unknowns / next steps

- **Player spawn**: BLOCKED BY MISSING ORIGINAL SOURCE (no SQL `.Bak`/start
  table in the 119,631-file inventory). Stays UNKNOWN and fail-closed; the
  runtime never invents a spawn.
- **Player model**: PARTIAL — 2/16 gear parts reference europeman-skeleton
  bones absent from the committed 38-bone chinaman_skel; strict load returns
  null. Animation chain fully loadable via the animation-only index.
- **Walk/run/combat speeds and transition rules**: UNKNOWN/BLOCKED (no
  CharacterData/SkillData values; only real clip durations are proven).
- **Android verification**: NOT EXECUTED until an SDK is available.
- Next: parse `CharacterData`/`SkillData` (or the SQL `.Bak`) to prove movement
  values; resolve the player mesh/skeleton mismatch to promote the model from
  PARTIAL; APK + instrumented verification once tooling exists.

---

## Classification matrix (5-way)

| Item | Classification |
|---|---|
| Player spawn (no verified source) | INVESTIGATED UNKNOWN — fail-closed |
| Player identity manifest/skeleton chain + IDLE/WALK/RUN | IMPLEMENTED PROVEN |
| Player full model load (gear parts vs 38-bone skeleton) | INVESTIGATED PARTIAL |
| Native joystick input intent + touch wiring | IMPLEMENTED PROVEN (structural) |
| Movement direction→displacement math + heading | IMPLEMENTED PROVEN (math) |
| Walk/run/combat speeds + transition rules | BLOCKED BY MISSING SOURCE |
| Camera follow of placed player (`Camera2D.follow`) | IMPLEMENTED PROVEN (generic) |
| World/region evidence + Jangan_Field anchor | IMPLEMENTED PROVEN |
| NPC runtime / Phase 23 suite preservation | IMPLEMENTED PROVEN |
| APK build / instrumented / device run | NOT EXECUTED |
