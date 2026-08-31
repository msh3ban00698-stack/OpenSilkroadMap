# PHASE 26 REPORT — Native Multi-Entity Runtime, Movement, Combat, Player Animation Census

Branch: `260831-feat-phase26-native-multi-entity` · Baseline: Phase 25 HEAD `98993977`
Date: 2026-08-31

This phase (a) formalizes the **pure-JVM multi-entity character runtime** as a
data-driven, testable class, and (b) recovers **movement / combat / player
animation** facts from the authoritative vSRO 1.193 archives into a machine-
readable evidence file, asserting them in bounded JVM tests. As in Phase 25,
nothing is invented: what the source cannot prove stays UNKNOWN and the
fail-closed runtime is preserved.

## 1. Scope, baseline, and deliverables

Baseline: Phase 25 HEAD `98993977`. Phase 26 branch created from it.

| Task | Deliverable |
|---|---|
| A | Locomotion root-motion recovery: the three committed player locomotion clips carry NO baked forward translation and are cyclic → walk/run speeds UNKNOWN, fail-closed |
| B | Combat recovery: skilldata_5000 attack rows order by weapon type (fist 1500 > sword 1200 > spear 1166 > bow 840) — candidate attack-cadence column, semantics UNVERIFIED; damage formulas / landing frame / range / cooldowns UNKNOWN |
| C | Player BSR clip census: 217 animations, zero word-start `attack` clips → player ATTACK/DAMAGE/DEATH states are MISSING (fail-closed), NPC ones resolve |
| D | Machine-readable evidence file `scripts/testdata/formats/phase26_source_evidence.json` + builder `scripts/build_phase26_evidence.py` |
| E | `CharacterWorld` — pure-JVM multi-entity runtime (many entities per model key, independent clocks, world clock, fail-closed spawn) |
| F | JVM tests: `CharacterWorldTest` (5) + `Phase26SourceEvidenceTest` (3) |
| G | Verification-integrity repair: switch the JVM harness to REAL JUnit assertions; repair the 9 pre-existing tests that genuine assertions exposed (6 Phase 25 evidence, 3 game/player) |
| H | This report |

## 2. Verification methodology and an integrity correction

The Phase 24/25 pure-JVM harness compiled an **empty-bodied** `org.junit.Assert`
stub, so `assertTrue(false)` threw nothing: the historical "N tests PASS"
claims were vacuous with respect to assertion values (only exceptions such as
missing files could fail a test).

Phase 26 re-runs the same pure-JVM set against the **real JUnit 4.13.2**
(org.junit.runner.JUnitCore) from the Gradle distribution, via
`/tmp/opencode/ph26build/phase26_build_and_run.sh` (fork of the Phase 25
harness; same android stubs: file-backed `AssetManager`, `Bitmap`,
`BitmapFactory`; view classes remain compile-only/excluded). Real assertions
immediately exposed **9 pre-existing broken tests**:

| Test | Defect | Repair |
|---|---|---|
| `Phase25SourceEvidenceTest` ×6 | string assertions written for a serialization the committed evidence file does not use (multi-line arrays, path-prefixed keys, backslash-escaped JSON, capitalised prose) | re-targeted each assertion to the exact committed evidence text |
| `PlayerSpawnTest.verifiedSpawnProjectsProvenWorldFormula` | expected `worldX(167)==156`; the proven formula yields `0` (`(sector−ref)*1920+local` with ref==sector) | corrected expectations to `0f` |
| `PlayerMoverTest.normalizedDiagonalKeepsUnitLength` | delta `1e-9` tighter than float normalization precision (`hypot≈0.99999998`) | delta `1e-6` |
| `PlayerWorldRegionTest.regionCode25000IsJangan` | asserted GATE_CH in teleportdata.tsv column 1 / zone in column 4; the committed file has them in columns 2 and 5 | corrected column indices |

Result: **134 JVM tests PASS, 0 FAIL** (126 pre-existing now genuinely passing
under real assertions + 8 new Phase 26 tests). §9.

## 3. TASK A — locomotion root motion (PROVEN negative)

`scripts/build_phase26_evidence.py` decodes the three committed player
locomotion clips from Data.pk2 and measures the root (`Bip01`) translation
range per axis:

| Clip | keys | x-range | y-range | z-range | cyclic (first−last) |
|---|---|---|---|---|---|
| `chinaman_fighter_walkforward.ban` | 26 | 0.152 | 0.355 | **0.0** | (0.0, 0.0, 0.0) |
| `chinaman_fighter_runforward.ban` | 13 | 0.726 | 0.792 | **0.0** | (0.0, 0.0, 0.0) |
| `chinaman_fighter_runforward_sword.ban` | 18 | 0.157 | 0.668 | **0.0** | (0.0, 0.0, 0.0) |

Forward travel is the **z** axis; all three clips carry constant z (0 or
0.0005) and are exact loops (first pose == last pose). x/y motion is weight-
shift/stride bobble only.

> **Conclusion:** movement speed is NOT baked into the animation data. No
> speed table exists in Data.pk2 / Map.pk2 / Media.pk2 (exhaustively searched
> in Phase 25 for spawn; the textdata corpus holds no locomotion-speed table).
> Walk/run speeds remain **UNKNOWN**; the Phase 24 fail-closed mover
> (displacement only with a proven speed) is preserved.

## 4. TASK B — combat (candidate cadence, semantics UNVERIFIED)

From `Media.pk2 /server_dep/silkroad/textdata/skilldata_5000.txt`, the four
basic attack rows by weapon type:

| Skill | refid | col13 | col14 | col69 |
|---|---|---|---|---|
| SKILL_PUNCH_01 (fist) | 172 | 1500 | 1500 | 6386804 |
| SKILL_CH_SWORD_BASE_01 | 173 | 1200 | 1200 | 6386804 |
| SKILL_CH_SPEAR_BASE_01 | 195 | 1166 | 1166 | 6386804 |
| SKILL_CH_BOW_BASE_01 | 217 | 840 | 840 | 6386804 |

The values order by weapon type and are consistent with an attack-cadence
column in ms, but the exact meaning (cast / pre-delay / attack interval) is not
documented in the repo's decoded schema: **UNVERIFIED, not asserted as
semantics**. Damage formulas, damage-landing frame, targeting range, and
cooldowns have no decoded archive source: **UNKNOWN**. The evidence file labels
each accordingly; the runtime continues to do no combat.

## 5. TASK C — player animation census (PROVEN)

`chinaman_fighter.bsr` resolves to **217** animations. Core-name census (after
stripping the `chinaman_fighter_`/`chinaman_`/`china_man_` prefix):

| Category | Count | Notes |
|---|---|---|
| skill | 160 | incl. all `skill_ch_sword_*` attacks |
| stand | 10 | standbattle, standcity, spear_stand… |
| run | 8 | runforward, runforward_sword, … (incl. 3 `nasrun1_man_*`) |
| walk | 4 | walkforward, walkbackward, … |
| die/knockdown | 6 | a_down*, a_diehardhit*, a_downdie |
| sit | 3 | a_sitbreath, a_sitground, a_sitstand |
| hit | 2 | a_behardhit, a_benormalhit |
| other | 24 | emotes, poses, pickups, casts, waits |
| **attack (word-start)** | **0** | no clip name begins with `attack` at a word boundary |

> **Consequence:** the player's combat clips are **skill-named**
> (`skill_ch_sword_downattack_a.ban`, …). The keyword state resolver only maps
> a keyword at a word boundary, so the player's ATTACK/DAMAGE/DEATH states
> resolve to **MISSING** — fail-closed, no guessed-idle fallback. NPC
> attack/damage/death clips (e.g. `bandit_attack01`, `bandit_damage01`,
> `bandit_die`) DO resolve, and the player's 5 committed locomotion clips
> resolve IDLE/WALK/RUN exactly as the committed manifest declares.

## 6. TASK E — `CharacterWorld`: the pure-JVM multi-entity runtime

`android/app/src/main/java/com/opensilkroadmap/app/world/CharacterWorld.java`
(A) formalizes what the Android renderer already exercised per-entity into a
pure-JVM, Android-free, data-driven container:

- **One model key → many entities.** A `CharacterMeshIndex` per key backs any
  number of `CharacterEntity` instances; each owns its own
  `CharacterAnimator`, so siblings of the same model animate independently.
- **Two clocks.** `update(dt)` advances every entity uniformly; an entity can
  also be stepped individually (e.g. a player driven by its own controller)
  without desyncing the rest.
- **Fail-closed spawn.** `spawn(id, modelKey, x, z)` returns `false` for an
  unknown model key or a duplicate id and changes nothing.
- **Ownership of scale.** Positions are world coordinates; the source gives no
  unit, so callers own the SRO→world scale factor (documented, not assumed).

`CharacterWorldTest` proves all of the above over **two real committed models**
(the player's animation chain and the full `res_mob_china_bandit` chain) loaded
via `CharacterMeshIndex.animationsOnlyIndex` — including that the bandit
resolves ATTACK/DAMAGE/DEATH while the player does not (§5), and that stepping
one sibling leaves its twin untouched.

## 7. Reproducing

```bash
# 1) Regenerate the evidence from the PK2 archives (needs Data.pk2/Media.pk2
#    extracted under /tmp/opencode/pk2raw/ as in prior phases)
python3 scripts/build_phase26_evidence.py

# 2) Compile + run the pure-JVM suite with real JUnit 4.13.2
#    (harness lives at /tmp/opencode/ph26build/phase26_build_and_run.sh)
#    Expect: OK (134 tests)
```

## 8. Commit

```
feat(android): Phase 26 native multi-entity runtime + movement/combat/player-animation evidence
- CharacterWorld: pure-JVM multi-entity container (independent per-entity animator clocks,
  world clock, fail-closed spawn) + CharacterWorldTest over real player/bandit manifests
- phase26_source_evidence.json: locomotion clips carry no root translation (speeds UNKNOWN),
  skilldata attack rows order by weapon type (semantics UNVERIFIED), 217-clip BSR census with
  zero word-start 'attack' clips -> player ATTACK/DAMAGE/DEATH MISSING fail-closed
- switch JVM harness to REAL JUnit assertions; repair 9 pre-existing tests that genuine
  assertions exposed (6 Phase 25 evidence string asserts, PlayerSpawn/PlayerMover column
  and precision asserts)
- 134 JVM tests PASS / 0 FAIL
```

## 9. Verification record

Full pure-JVM suite run from the harness, real JUnit 4.13.2:

```
OK (134 tests)
```

Run output captured at `/tmp/opencode/ph26build/junit.log`; harness
`/tmp/opencode/ph26build/phase26_build_and_run.sh`; evidence JSON and builder
committed under `scripts/`.
