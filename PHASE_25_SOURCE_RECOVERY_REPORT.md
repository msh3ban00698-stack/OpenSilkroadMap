# PHASE 25 REPORT — Source Recovery: Player Identity, Skeleton, Gear, Movement, Camera

Branch: `260831-feat-phase25-source-recovery` · Baseline: Phase 24 HEAD `4b6b2224f323b8310fe1a5c34d9e51b1870ce5fe`
Date: 2026-08-31

This phase recovers **original-source evidence** for the native player runtime
from the authoritative vSRO 1.193 archives (Data.pk2 / Media.pk2) that are
already used by this repo's proven decoders. It is an investigation/evidence
phase: no game behavior is invented, no values are guessed to make the player
playable, and every claim is either PROVEN (byte-derived), PARTIAL, or UNKNOWN
with the evidence recorded. Where the original source is absent (player spawn,
walk/run speed values, camera field semantics) the record says UNKNOWN and the
Phase 24 fail-closed runtime is preserved.

## 1. Scope, baseline, and deliverables

Baseline (verified before this phase): commit `4b6b2224`, branch
`260831-feat-phase24-player-spawn-movement`, local==remote==HEAD, clean tree,
112 JVM tests PASS / 0 FAIL. Phase 25 branch created from that commit.

| Task | Deliverable |
|---|---|
| A | Player identity: `option.txt StartCharacter` chain + `characterdata` row resolution |
| B | Player spawn: exhaustive search for a start/spawn table → UNKNOWN, fail-closed |
| C | Skeleton binding: per-BSR mapping (30 China BSRs) + bone counts + anim-channel corroboration |
| D | Gear chain: clothes/sword bind resolution via item skeletons + itemdata linkage |
| E/F | Movement values & semantics: CharacterData col41–48 classification; speeds UNKNOWN |
| G | Camera: cameradata.txt rows + command.txt debug verbs; semantics UNKNOWN |
| H | Machine-readable evidence matrix (TSV + JSON) |
| J | Bounded JVM tests over recovered facts (8 new tests) |
| L | This report + provenance update to the player artifact |

## 2. Verification methodology

Pure-JVM harness at `/tmp/opencode/phase25_build_and_run.sh` (fork of Phase 24):
custom `JUnitRunner` + real `org.junit.Assert` (`junitreal`), JDK 17. Runs from
`/workspace/android/app` with bounded timeouts. One new test class,
`Phase25SourceEvidenceTest`, reads the committed byte-derived evidence file
`scripts/testdata/formats/phase25_source_evidence.json` and asserts the PROVEN
recovery facts. Android-bound classes remain compile-only as in Phase 24.

**120 JVM tests PASS, 0 FAIL** (112 Phase 24 + 8 Phase 25; §12).

## 3. TASK A — player identity (PROVEN)

Two independent strands now identify the player model in the original client.

1. **`Media.pk2 /config/option.txt`** (latin-1) records the debug client start:
   `Map = "0"`, `StartCharacter = "1907"`,
   `IntroName = "script\intro\constantinoplefw.txt"` (alternates commented:
   `china_wharf`, `roc`, `egypt`, `jupiter_login`, `arabia`).
2. **`Media.pk2 /server_dep/silkroad/textdata/characterdata_5000.txt`**
   (UTF-16LE) row `1907` resolves to `CHAR_CH_MAN_ADVENTURER` with model
   `char\china\chinaman_adventurer.bsr`, radius 100 (col48), level 1 (col57).
   `chinaman_adventurer.bsr` parses to 9 meshes, 217 animations, skeleton
   `europeman_skel.bsk` — the same chain as the committed
   `chinaman_fighter.bsr` player artifact.

Both `chinaman_adventurer.bsr` and `chinaman_fighter.bsr` are equivalent base
China-male models; the debug start targets the adventurer variant. The Phase 24
player artifact (`chinaman_fighter`) is corroborated as a real China-male base
character.

## 4. TASK B — player spawn (INVESTIGATED UNKNOWN, fail-closed)

Exhaustive search (cached full listings for Data/Map/Media) for a static
start/spawn table:
- Media listing grep for `start|birth|spawn|login|newchar|create` → only UI
  strings (`pscharactercreatechina.txt`, `pscharactercreate_europe.txt`), no table.
- Data listing grep for `startpos|spawn|birth|newchar|login` → only skill/audio
  (`skill_ch_water_rebirth_*`, `usk_cleric_rebirth_*`), no table.
- Map listing → no matches.

Conclusions, all recorded in the evidence JSON:
- No server-side start/spawn table exists in the supplied PK2 archives.
- The only start evidence is client config (`option.txt StartCharacter/Map`)
  and cinematic intro `S_CameraInsert` coordinates — neither is a spawn table.
- Player start location is set by the server runtime: **UNKNOWN from client
  data**, so Phase 24's fail-closed spawn handling is unchanged and correct.

## 5. TASK C — skeleton binding (PROVEN, reclassifies Phase 24 "mismatch")

Parsing all 30 `Data.pk2 /res/char/china/*.bsr` character files and their
skeleton groups gives a **systematic** result:

| Skeleton | BSR count | Notes |
|---|---|---|
| `/prim/skel/char/europe/europeman_skel.bsk` (43 bones) | 14 | incl. `chinaman_fighter`, `chinaman_adventurer`, `chinaman_warrior`, `chinaman_monk`, `chinaman_priest`, `char_cpd` |
| `/prim/skel/char/europe/europewoman_skel.bsk` (45 bones) | 13 | all `chinawoman_*` incl. `chinawoman_fighter` |
| `/prim/skel/char/china/chinaman_skel.bsk` (38 bones) | 1 | `chinaman_spidey` only |
| `/prim/skel/char/china/chinaman_hwan_hair.bsk` | 1 | hair-appendage model |
| `/prim/skel/char/china/chinawoman_hwan_hair.bsk` | 1 | hair-appendage model |

So the Phase 24 note "BSR references europeman_skel, not chinaman_skel" is
reclassified: it is the **systematic, original-source layout** of this client
build (China-race base characters are rigged to the European skeletons), not an
error to fix.

**Animation-level corroboration:** the committed player clip
`chinaman_fighter_runforward.ban` (42 channels) animates five europeman-only
bones — `cloak01..cloak04` and `Bip01 L HandMid2` — which do not exist in
`chinaman_skel.bsk`. The fighter locomotion set is therefore authored for the
europeman skeleton. The four 37-channel clips are subsets of both skeletons.
This means the committed player artifact (38-bone chinaman skeleton) silently
drops those 5 channels for `runforward`; the original rig is europeman. The
artifact's provenance is updated to cite this evidence while the skeleton is
left unchanged (documented, not silently flipped).

## 6. TASK D — gear chain (PROVEN via item skeletons)

Bone-table extraction for every player gear mesh resolves the earlier
"gear bones absent from character skeletons" puzzle:

| Part | Bind bones | Resolution |
|---|---|---|
| `clothes_01_aa/ba/fa/ha/la` | Bip01 R/L Forearm/Hand, Spine1, Clavicles, Pelvis, Thigh/Calf/Foot/Toe, Head, Neck1 | **All present in every character skeleton** (europeman 43, europewoman 45, chinaman 38, chinawoman 40). These 5 clothes bind directly to the character skeleton. |
| `clothes_01_sa` | `Bone05`, `Bone03` | Bind to the item skeleton `/prim/skel/item/china/clothes_sa.bsk` (5 bones: Bone01 → Bone05→Bone06, Bone01 → Bone03→Bone04). |
| `sword_01` | `Bone01` | Binds to the item skeleton `/prim/skel/item/china/weapon/sword_01.bsk` (4 bones: Bone01 → Bone02 → ai_start → ai_end). `Bone01` also happens to exist in the female character skeletons, but the authoritative bind is the weapon item skeleton. |

**itemdata linkage (Media.pk2, UTF-16LE):** `itemdata_5000.txt` rows confirm the
committed gear choices. col52 = in-hand `.bsr`, col54 = `.ddj`:

- `ITEM_CH_M_CLOTHES_01_AA_A` (971), `_BA_A` (899), `_FA_A` (1007), `_HA_A`
  (791), `_LA_A` (935), `_SA_A` (863) → `item\china\man_item\clothes_01_*.bsr`
- `ITEM_CH_SWORD_01_A` (71) → `item\china\weapon\sword_01.bsr`, ddj
  `item\china\weapon\sword_01.ddj`

The client-side attachment of an item skeleton root to a character bone (e.g.
sword root → hand) is client code, not archive data; the `ai_start`/`ai_end`
"artificial" bone pattern in all weapon skeletons is recorded as the design
evidence for that mechanism. It is not asserted beyond the data.

## 7. TASK E/F — movement values & semantics (UNKNOWN values; PROVEN classification)

`characterdata_5000.txt` cols 41–48 for every China player archetype
(ADVENTURER, FIGHTER male and female) are **identical**:
`6341 0 8000 0 18000 16 50 100`. Because they do not differ between
archetypes/classes, they are not class movement speeds; they are generic
stat-pool columns (semantics not asserted without a schema).

No movement table exists anywhere in Data/Map/Media. The client debug verbs in
`Media.pk2 /config/command.txt` (`/setspeed %d`=600, `/setfov %d`=500, `/camera`=114,
`/zoom`=110, `/fast`=111, `/getpos`/`/pos`=3/4) are debug-only controls, not the
authoritative walk/run rates. Walk/run speed values therefore remain **UNKNOWN**
(fail-closed as in Phase 24).

## 8. TASK G — camera (rows PROVEN, semantics UNKNOWN)

`Media.pk2 /config/cameradata.txt` (latin-1) decodes to:
```
-1
79 107 1205 80 396 30 10 0 50
77 105 1466 79 1488 30 10 270 50
```
Two 9-field numeric rows are preserved verbatim. The field semantics are
**UNKNOWN** — candidate roles (near/far plane, distance, height, fov, yaw
offset) are explicitly NOT asserted without a schema. The intro scripts
(`script/intro/china_wharf.txt`) provide `S_CameraInsert` lines
(region 188/95, world coords like `1713.326294 56.223167 484.136963`, camera
vector) as cinematic-camera evidence only — they are NOT player spawn
coordinates.

## 9. TASK H — evidence matrix

`scripts/testdata/formats/phase25_evidence_matrix.tsv` tabulates every recovered
fact with status PROVEN/UNKNOWN, source archive, source path, and evidence.
`scripts/testdata/formats/phase25_source_evidence.json` carries the full
machine-readable payload (per-BSR skeleton map, skeleton bone lists, gear bone
tables + membership, itemdata rows, cameradata rows, option.txt fields, spawn
conclusion). Both are generated by
`scripts/build_phase25_evidence.py` from the original archives.

## 10. Player artifact provenance update

`android/app/src/main/assets/game/world/characters/player/provenance.json` is
updated to cite the Phase 25 source evidence: the BSR→europeman binding is
systematic (30/30 China BSRs), and `chinaman_fighter_runforward.ban` animates
europeman-only bones. The artifact skeleton is left as the committed
`chinaman_skel` (documented PARTIAL), because flipping it would silently change
renderer semantics and the app cannot consume item skeletons; the mismatch
remains visible, not hidden.

## 11. Fail-closed / no-invention audit

| Item | State |
|---|---|
| Player spawn | UNKNOWN, fail-closed (unchanged) |
| Walk/run speed values | UNKNOWN (no archive table) |
| Camera field semantics | UNKNOWN (rows preserved only) |
| Player skeleton choice | chinaman_skel kept; europeman binding documented as original-source |
| Item skeleton attachment bone | recorded as client-code design (`ai_start`/`ai_end`), not asserted |
| CharacterData col41–48 | classified as generic stats; semantics not asserted |

## 12. Verification results

Harness: `/tmp/opencode/phase25_build_and_run.sh` from `/workspace/android/app`.

```
TOTAL pass=120 fail=0
```

- Phase 24 baseline: 112 PASS, 0 FAIL (preserved).
- Phase 25 new: 8 PASS, 0 FAIL (`Phase25SourceEvidenceTest`).
- Android device/APK verification: NOT EXECUTED (no SDK/Gradle/emulator/device).

## 13. Files changed in this phase

- `scripts/build_phase25_evidence.py` (new) — byte-derived evidence builder.
- `scripts/testdata/formats/phase25_source_evidence.json` (new) — recovery record.
- `scripts/testdata/formats/phase25_evidence_matrix.tsv` (new) — fact matrix.
- `android/app/src/test/java/com/opensilkroadmap/app/world/Phase25SourceEvidenceTest.java` (new) — 8 bounded tests.
- `android/app/src/main/assets/game/world/characters/player/provenance.json` (updated) — cites Phase 25 evidence.

## 14. Follow-ups (not in this phase's scope)

- Renderer support for item skeletons (clothes_sa / weapon) so the full player
  gear binds like the original client.
- Re-rig the player artifact to europeman_skel once the renderer consumes the
  43-bone skeleton and drops no runforward channels.
- Camera: recover field semantics from an original client binary or a second
  archive with a schema.
