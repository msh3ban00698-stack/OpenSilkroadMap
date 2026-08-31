# PHASE 23 REPORT — Character Animation States + Independent NPC Entities (Increment 2)

Branch: `260831-feat-phase23-character-animation` · Baseline: Phase 23 increment 1 `600c6c0b9868ba554b13b6c54043c82a5285ea62`
Date: 2026-08-31

Increment 1 (committed) added per-character idle clip playback
(`AnimationPlayer` + `IdleAnimResolver`). This increment expands the native
character runtime into a **data-driven animation-state machine with one
independent animator per spawned character**, plus a structural enumeration
test over all committed character manifests.

Nothing is invented: every animation state is derived from the REAL committed
clip names (`stand`/`walk`/`run`/`attack`/`damage`/`die`), and every duration is
the REAL `.ban` duration committed in each manifest.

---

## Status vocabulary

- **PROVEN** — resolved from committed/original data and verified by a run test.
- **COMPILE-ONLY** — Java compiles against Android stubs; no device execution.
- **KNOWN ISSUE** — reproducible defect, documented with evidence.
- **NOT EXECUTED** — not run in this environment (no Gradle/Android SDK/device).

---

## 1. Animation-state architecture (PROVEN)

New pure-JVM components (no Android dependencies), each with passing JVM tests:

| Class | Responsibility |
|---|---|
| `world/AnimState` | The six proven states: `IDLE`, `WALK`, `RUN`, `ATTACK`, `DAMAGE`, `DEATH`, each classified looping vs one-shot. |
| `world/AnimStateResolver` | Maps a character's committed clip list to states by REAL name keywords (case-insensitive): `stand`→IDLE, `walk`→WALK, `run`→RUN, `attack`→ATTACK, `damage` excluding `down`→DAMAGE, `die` excluding `down`/`loop`→DEATH. Missing states are simply absent (fail-closed). |
| `world/CharacterAnimator` | Per-entity state machine bound to one `AnimationPlayer` clock. Starts in IDLE; missing states fall back to IDLE (or bind pose); one-shot `ATTACK`/`DAMAGE` return to IDLE on completion; `DEATH` is terminal; same-state transitions do not restart the clip. |
| `world/CharacterEntity` | One placed character: loaded `CharacterMeshIndex` + its own `CharacterAnimator` + world position + `pose()` sampling. |

`CharacterMeshIndex` gains:
- `buildAnimator()` — resolves a fresh independent animator per call.
- `parseManifestClips(Reader)` — Android-free manifest→clip parsing (enables the JVM enumeration test).
- `parseManifestAssetPaths(Reader)` — Android-free manifest→referenced shared-file paths (skeleton/mesh/texture/animation).

`IdleAnimResolver.resolve` now delegates to `AnimStateResolver` so there is a
single source of truth for the `stand`→IDLE rule (behavior identical; its tests
pass unchanged).

## 2. Independent per-NPC animation (Android, COMPILE-ONLY)

`NativeWorldRenderer` was refactored from a per-`key` clock to a **per-spawn
instance** clock:

- Removed the per-key `AnimationPlayer` map and cached per-key pose map.
- Added `Map<NpcSpawnIndex.Spawn, CharacterEntity>` keyed by spawn identity
  (stable across frames because `NpcSpawnIndex.inWindow` returns references to
  the same `Spawn` objects).
- `advanceAnimations(dt)` advances every entity's independent clock once per
  frame; `drawCharacters` samples each entity's active pose per draw.
- Stale entities (spawns that left the visible sector window) are pruned each
  draw (`pruneEntities`).
- `setCharacterPose` remains as a global fallback; animated poses take
  precedence; a character with no resolved clip renders at the bind pose.

This means two NPCs of the same model key now animate with independent states
and clocks. The renderer remains device-side only (no game logic).

## 3. Pre-existing blocker fixed: skinned-mesh 255 sentinel (PROVEN)

`StaticMeshAsset.parseSkinned` rejected every committed skinned character mesh:
the original SRO mesh data uses `bone = 255` as the "no influence" sentinel for
the second bone slot, and the strict bounds check treated it as an invalid bone.
Because of this, `CharacterMeshIndex.load` returned null for **every skinned
character** — the character runtime could not load any character.

Fix (verified against real bytes): treat bone index `255` as no-influence and
zero its weight; the bounds check now allows the sentinel. Downstream skinning
already guarded `boneIndex < boneNames.length`, so no other change was needed.

Evidence: the three committed bandit meshes all carry `bone2=255` sentinels
(`bone1=[0]`, `bone2=[255]`, `w2=0` for the sword; part1/part2 contain mixed
`255` in `bone2`). After the fix, `CharacterMeshIndexTest#meshesThreeRealParts`
(76/134/1, 214/276/18, 556/766/17 — the proven Phase 20 counts) and
`swordSkinnedPositionsMatchSingleBoneTransform` PASS.

## 4. Structural enumeration of all committed manifests (PROVEN)

`CharacterManifestEnumerationTest` parses every committed manifest and asserts
the measured ground truth (all values read from the committed store):

| Metric | Value |
|---|---|
| Manifest-bearing model dirs | 473 |
| Total animation entries across manifests | 3,689 |
| Manifests with zero animations | 1 |
| Manifests resolving an IDLE/stand state | 309 |
| Manifests referencing a missing shared file | 0 |
| Clips with empty name or non-positive duration | 0 |

The test also verifies every shared file referenced by every manifest
(`skel/*.json`, `mesh/*.msh`, `tex/*.png`, `anim/*.json`) exists.

## 5. Verification evidence (all run in JVM, JDK 17)

Test runner: custom `JUnitRunner` + real `org.junit.Assert` under
`/tmp/opencode/phase23/` (the project `org.junit` stubs are compile-only).

| Test class | Result |
|---|---|
| `AnimationPlayerTest` (incl. new `clear()`/`isFinished()` cases) | PASS (10) |
| `IdleAnimResolverTest` | PASS (5) |
| `AnimStateResolverTest` | PASS (6) |
| `CharacterAnimatorTest` | PASS (8) |
| `CharacterManifestEnumerationTest` | PASS (3) |
| `CharacterMeshIndexMultiTest` | PASS (3) |
| `CharacterMeshIndexTest` (skeleton/parse/bind-single-bone) | PASS (5) |
| `CharacterMeshIndexTest#skinnedBindPositionsFiniteAndPlausible` | **FAIL** (KNOWN ISSUE) |
| `Verify.java` harness (increment 1 regression) | ALL_PASS |

Android-side classes (`CharacterEntity`, `CharacterMeshIndex`, `NativeWorldRenderer`)
compile against Android stubs; device execution NOT EXECUTED.

## 6. Known issue: bind-pose skinning mismatch on real assets (pre-existing)

`CharacterMeshIndexTest#skinnedBindPositionsFiniteAndPlausible` FAILS. This is a
**pre-existing** Phase 18/19 defect (that phase was committed "compile-only");
it is not caused by this increment and is not an animation-state defect.

Evidence (measured from committed `prim_skel_mob_china_bandit.json` +
`prim_mesh_mob_china_bandit_part1.msh`):
- Raw part1 local positions are symmetric: `minX=-11.53`, `maxX=+11.53`.
- After `skinnedBindPositions`, output is `minX=0.43`, `maxX=23.43` — all
  positive X, so the arm-symmetry assertion fails.
- A right-fingertip vertex (raw `X=-11.53`, influenced 100% by
  `Bip01 R Finger21`, whose bind world pos is `X=-10.74`) maps to bind
  `X=+0.66`; the left fingertip maps to `X=+22.14`.

The `R_bind * v + t_bind` mapping therefore does not reproduce the bind pose for
the real mesh data (the raw mesh appears to already be in bind pose; applying
the bind rotation over-rotates it). Impact: bind-pose and animated skinned
characters would render incorrectly. Resolution requires a dedicated
investigation of the original `BSK` bind-matrix semantics (inverse/rest-pose
handling) — tracked as a follow-up, NOT resolved here.

## 7. Status matrix

| Item | Status |
|---|---|
| Animation states from real clip names/durations | PROVEN (tests) |
| Per-NPC independent animators | COMPILE-ONLY (renderer) |
| State fallback rules (idle fallback, one-shot return, terminal death) | PROVEN (tests) |
| Skinned-mesh 255-sentinel parse | PROVEN (tests) |
| Full-manifest structural enumeration | PROVEN (tests) |
| Bind-pose skinning on real assets | KNOWN ISSUE (pre-existing) |
| APK / instrumented / device run | NOT EXECUTED |
| Player spawn, movement, combat | NOT STARTED (UNKNOWN until source-proven) |
