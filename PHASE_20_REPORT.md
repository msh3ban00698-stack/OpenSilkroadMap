# PHASE 20 REPORT — Data-Driven Character Runtime (All Provable NPCs + Player)

Branch: `260830-feat-phase20-data-driven-character-runtime` · Baseline: Phase 19 final `22166379a3cf4fa76ca7283d09be978b249033f5`
Date: 2026-08-31

Phase 20 replaces the single-bandit pipeline with a bulk, data-driven runtime for
**every provable NPC plus the player**. All original `.bsr`/`.bsk`/`.bms`/`.ban`/
`.ddj` bytes are resolved, classified, and converted into a deduplicated shared
asset store with one manifest per character key. Nothing is invented: every count
below is read from the committed `coverage.json` audit (generated from archive
bytes) and from the committed shared-store file counts.

---

## Status vocabulary

- **PROVEN** — resolved from original archive bytes and converted; manifest committed.
- **PARTIAL** — a proven subset converted; the remainder documented with evidence.
- **UNKNOWN** — no honest claim possible; not converted.
- **NOT EXECUTED** — not run in this environment (no Gradle/Android SDK/device).

---

## 1. Coverage table

### Dataset totals (`characters/coverage.json` `totals`)

| Metric | Value |
|---|---|
| NPC spawn rows (`npcpos`) | 18,457 |
| Spawning refids | 1,180 |
| Refids with a resolved model | 1,089 |
| Distinct models (`.bsr`) | 477 |
| Distinct skeletons (`.bsk`) | 354 |
| Distinct mesh parts (`.bms`) | 1,573 |
| Distinct textures (`.ddj`) | 647 |
| Distinct animation clips (`.ban`) | 2,307 |

### Model integration

| Status | Count | Percentage |
|---|---|---|
| PROVEN (converted) | 473 | 99.16% |
| PARTIAL | 1 | 0.21% |
| UNKNOWN | 3 | 0.63% |
| **Total** | **477** | 100% |

### Committed shared asset store (`characters/shared/`)

| Store | Files | Keyed by |
|---|---|---|
| `shared/skel/` | 355 | `.bsk` path slug |
| `shared/mesh/` | 1,585 | `.bms` path slug |
| `shared/tex/` | 655 | `.ddj` path slug |
| `shared/anim/` | 2,300 | `.ban` path slug |

Per-key manifests: **473** NPC manifests + **1** player manifest = **474**.
`characters/index.tsv`: **1,094** data rows (`refid key variant status spawn_count`).

> The shared-store file counts differ slightly from the distinct-by-path counts in
> `coverage.json` because the store deduplicates by slug (byte-identical/path-case
> variants collapse), and the player skeleton/meshes/textures/anims are committed
> but are not part of the NPC `models` list. Verified: `ChinaEtc_IslamMan.bsr`
> and `chinaetc_islamman.bsr` are byte-identical (sha256 prefix
> `818ab26560e589a8`) and correctly dedup to a single key.

---

## 2. PROVEN / PARTIAL / UNKNOWN breakdown

### PROVEN (473 models)

Every PROVEN model has a committed `manifest.json` + `provenance.json` +
`npc_placements.tsv` (NPC only), referencing the shared store by slug. 474
skeletons, 1,997 mesh parts, and 3,698 animations are PROVEN across the resolved
models. Examples verified end-to-end during the live test: `open_market_juel`
(110 bones, 7 parts, 1 anim, 4 spawns), `sd_arena_changer` (3 parts, 1 anim).

### PARTIAL (1 model)

| Key | Model | Reason |
|---|---|---|
| `res_mob_arabia_karkadann` | `mob\arabia\karkadann.bsr` | `conversion failed: BMS parse failed: prefixed triangle 0 index out of range (512,35584,513)` |

Karkadann resolves fully (skeleton + 5 mesh parts + 12 animations all PROVEN in
the audit), but the triangle-section parse fails on `karkadann_tail.bms` /
`karkadann_part1.bms`, so no manifest is emitted. Status PARTIAL.

### UNKNOWN (3 models — not characters)

| Key | Model | Reason |
|---|---|---|
| `res_artifact_guild_pulley_gate_pulley` | `Artifact\Guild\pulley\gate_pulley.bsr` | not character (no `.bsk`) |
| `res_dun_property_com_property_recall` | `Dun\Property\com\property_recall.bsr` | not character (no `.bsk`) |
| `res_quest_ins_quest_teleport` | `quest\ins_quest_teleport.bsr` | not character (no `.bsk`) |

These three BSRs are static props referenced by NPC-position refids; they have no
`.bsk` and are correctly excluded from the character runtime (documented, not
characters).

---

## 3. Player pipeline status

- **PROVEN:** `chinaman_skel.bsk` (38 bones) + body/face/hair/clothes/weapon
  meshes (16) + 5 animations all convert; `player/` manifest + provenance committed.
- **MISMATCH (documented):** every `/res/char/china/chinaman_*.bsr` references
  `/prim/skel/char/europe/europeman_skel.bsk` (43 bones), NOT `chinaman_skel.bsk`;
  the player skeleton is a standalone asset, not BSR-referenced.
- **MISSING:** no static player spawn in the archives (npcpos is NPC-only).
- **Status: PARTIAL** — rendering components proven, spawn/BSR edges not.

The player is the only manifest not in the NPC `models` list; its `coverage.json`
entry is `player {converted: true, status: PARTIAL}`.

---

## 4. Known boundaries / UNKNOWN (verbatim)

- `bone_type` u8 meaning UNKNOWN — census across 29,957 bones = `{0: 29957}`.
- Child-bone `rot_local`/`tr_local` inverse-bind algebra PARTIAL/UNKNOWN (sign of
  the local vector part differs from the plain conjugate).
- BSR 8×u32 header table semantics UNKNOWN.
- 2 `JMXVBAN 0101` animations UNKNOWN (`spidey_attack01.ban`, `chakji_stand02.ban`);
  4,793/4,795 `.ban` parse byte-exact as `0102`.
- BAN `u32`@body+8 flag meaning UNKNOWN (looping proven separately from data).
- Karkadann triangle-section parse: `prefixed triangle 0 index out of range` (PARTIAL).
- Player BSR→skeleton mismatch + no static player spawn (PARTIAL, section 3).
- Java device rendering / APK build / runtime animation clock: NOT EXECUTED.

---

## 5. How to reproduce

```bash
# Hermetic classification + catalog tests (no archive needed)
python3 scripts/test_phase20_resolve.py
python3 scripts/test_phase20_catalog.py

# Live bulk conversion (requires extracted PK2 dir)
SRO_PK2_DIR=/tmp/opencode/pk2raw python3 scripts/test_phase20_conversion.py

# Full bulk build -> index.tsv + coverage.json + shared store + manifests
python3 scripts/build_character_catalog.py --pk2-dir /tmp/opencode/pk2raw
```

Outputs land under `android/app/src/main/assets/game/world/characters/`
(`index.tsv`, `coverage.json`, `shared/`, `<key>/`, `player/`).
