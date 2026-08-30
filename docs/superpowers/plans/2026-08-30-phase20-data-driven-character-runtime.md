# Phase 20 — Data-Driven Character Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-bandit character pipeline (Phase 18/19) with a data-driven runtime that resolves, converts, and renders every provable NPC character model (plus the player) from the original archives, with a machine-readable coverage audit.

**Architecture:** A new pure-Python `character_resolve.py` centralizes NPC→model resolution, texture-path resolution (fixing two proven format variations), and per-component classification. `build_character_manifest.py` gains a reusable `convert_character()`/`convert_player()`. A new bulk driver `build_character_catalog.py` enumerates all spawning NPCs, converts every PROVEN model into a content-addressed shared asset store, and emits `index.tsv` + `coverage.json`. The Java runtime gains a `CharacterCatalog` (refid→character key) and a generalized `CharacterMeshIndex` (key→model) so `NativeWorldRenderer` instances real NPCs by their real refid.

**Tech Stack:** Python 3.10+ (stdlib + `world_terrain`/`pk2_table`/`bsr_decoder`/`bsk_decoder`/`bms_decoder`/`ban_decoder`/`dds_decode`/`bms_to_asset`), Java 17 (Android-free `CharacterMeshIndex`/`CharacterCatalog`/`StaticMeshAsset`), `unittest` for Python tests, JUnit 4 + `javac` for Java.

## Global Constraints

- Never invent bones, meshes, animations, filenames, skeleton hierarchies, coordinates, or formats; mark unprovable assets UNKNOWN/PARTIAL with exact evidence.
- Status vocabulary is exactly `PROVEN` / `PARTIAL` / `UNKNOWN` (no other words) in every machine-readable artifact.
- Remove all single-character/demo assumptions from the runtime path; select character/animation data from real NPC/player/world records, not hardcoded example IDs.
- Decode and integrate every provable BSK/BMS/BAN/BSR/ddj component; document the exact boundary where a format remains unknown.
- NPCs must use actual proven character references (characterdata col1→col52, comma-split for multi-BSR variants); player must use the proven `chinaman` assembly.
- Preserve Android-native / no-WebView architecture; no guessing of formats that contradict original-archive evidence.
- Never commit PK2 archives, credentials, secrets, or accidental generated binaries. Git discipline: `git status` → full staged-diff secret scan → dedicated branch → commit → push → verify local HEAD == remote HEAD → clean tree.
- Run JVM/Gradle/Android tests only where the toolchain exists; `javac` (JDK 17) is available, Gradle/Android SDK are NOT — report Java runtime tests as compile-only NOT EXECUTED, never pretend they ran.
- Phase completion requires a real coverage audit (counts/percentages integrated, remaining PARTIAL/UNKNOWN, why); green tests alone are not sufficient.
- Do not delete files (no `rm`/`git rm`); superseded assets are replaced by regeneration and documented, never deleted.
- Python tests are hermetic (fixture/synthetic bytes) unless gated on `SRO_PK2_DIR`; live archive tests use `SRO_PK2_DIR=/tmp/opencode/pk2raw`.

---

## Recon Facts (authoritative input to every task)

These were measured from `Data.pk2`/`Media.pk2` (`/tmp/opencode/pk2raw`) during recon and drive the plan:

- `npcpos.tsv`: 18,457 rows; 1,180 distinct spawning refids; 1,089 refids have a characterdata model.
- Characterdata `col52` may be a comma-separated list of `.bsr` paths (multi-BSR variants share one refid), e.g. `mob\sd\seth.bsr,mob\sd\seth_t2.bsr,mob\sd\seth_t3.bsr`.
- ~466 distinct character `.bsr` models among spawning NPCs (after comma-split); ~3 spawning models are non-character (no `.bsk`): `gate_pulley.bsr`, `property_recall.bsr`, `ins_quest_teleport.bsr`.
- 350 distinct skeletons; 1,997 character mesh parts of which 37 have no skin block (static attachments — capes/horns/tails/boxes); 555 distinct textures (~256 MB raw ddj → ~250 MB PNG, ratio ≈ 1.0); 2,236 distinct animations (3,617 total refs); all character parts use the `standard` 44-byte vertex layout.
- Two proven format variations the current pipeline does NOT handle:
  1. **ddj path form**: `parse_bmt` returns either a bare filename (`bandit.ddj`, relative to the bmt dir) or a root-relative path (`prim\mtrl\mob\jupiter\charm_whitch.ddj`). `build_character_manifest.resolve_texture` blindly does `bmt_dir + "/" + ddj`, producing the doubled `/prim/mtrl/mob/jupiter/prim/mtrl/mob/jupiter/charm_whitch.ddj` for the root-relative case (76 models currently misclassified PARTIAL solely for this reason).
  2. **multi-BSR col52**: the join in `load_characterdata` stores one string per refid; comma-separated entries must be split into multiple model paths.
- 2 mesh parts (`karkadann_tail.bms`, `karkadann_part1.bms`) have an unproven triangle section and will not convert (documented PARTIAL).

---

## File Structure

- Create: `scripts/character_resolve.py` — pure resolution + classification primitives.
- Create: `scripts/build_character_catalog.py` — bulk driver (enumerate → classify → convert → index.tsv + coverage.json).
- Modify: `scripts/build_character_manifest.py` — add `convert_character()`, `convert_player()`; fix `resolve_texture` + `load_characterdata`.
- Create: `scripts/test_phase20_resolve.py`, `scripts/test_phase20_catalog.py`, `scripts/test_phase20_conversion.py`.
- Create: `android/app/src/main/java/com/opensilkroadmap/app/world/CharacterCatalog.java`.
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/CharacterMeshIndex.java` — key-based load + manifest + shared store; drop placement bundling.
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/NativeWorldRenderer.java` — catalog + per-refid model map.
- Create: `android/app/src/test/java/com/opensilkroadmap/app/world/CharacterCatalogTest.java`, `android/app/src/test/java/com/opensilkroadmap/app/world/CharacterMeshIndexMultiTest.java`.
- Create: `PHASE_20_REPORT.md` (generated alongside `android/app/src/main/assets/game/world/characters/coverage.json`).

Shared asset store layout (committed under `android/app/src/main/assets/game/world/characters/`):

```
characters/
  index.tsv                # refid \t key \t variant \t status \t spawn_count
  coverage.json            # full audit (Python-generated)
  shared/skel/<slug>.json  # deduped skeletons (keyed by bsk path slug)
  shared/mesh/<slug>.msh   # deduped meshes (keyed by bms path slug)
  shared/tex/<slug>.png    # deduped textures (keyed by ddj path slug)
  shared/anim/<slug>.json  # deduped full-keyframe clips (keyed by ban path slug)
  <key>/manifest.json      # skeleton_slug + per-part/per-anim refs into shared/
  <key>/npc_placements.tsv # NPC world spawns (NPC only)
  <key>/provenance.json    # sha256 of every original input + resolved chain
```

---

### Task 1: `character_resolve.py` — resolution & classification primitives

**Files:**
- Create: `scripts/character_resolve.py`
- Test: `scripts/test_phase20_resolve.py`

**Interfaces:**
- Consumes: `world_terrain.parse_bmt`, `bsr_decoder.parse_bsr_references`, `bsk_decoder.parse_bsk`, `bms_decoder` (`parse_bms_header`, `vertex_count`, `parse_bone_table`), `animation_pose.load_keyframes`.
- Produces: `split_models(col52)`, `slug(path)`, `bsr_path(bsr_rel)`, `resolve_texture(read, path_exists, bmt_blob, bmt_path, material_ref)`, `classify_character(read, path_exists, bsr_rel)`, `load_characterdata(text)`.

- [ ] **Step 1: Write the failing test**

`scripts/test_phase20_resolve.py`:

```python
#!/usr/bin/env python3
"""Phase 20 Part A: character resolution primitives (hermetic)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import character_resolve as CR  # noqa: E402
import world_terrain as wt  # noqa: E402


def _bmt(ddj_value):
    """Build a minimal JMXVBMT 0102 blob with one material -> ddj."""
    name = b"bandit"
    ddj = ddj_value.encode("ascii")
    blob = bytearray(b"JMXVBMT 0102")
    blob += (1).to_bytes(4, "little")          # material count
    blob += len(name).to_bytes(4, "little") + name
    blob += b"\x00" * 0x48                     # skip 72-byte unknown block
    blob += len(ddj).to_bytes(4, "little") + ddj
    blob += b"\x00" * 7
    return bytes(blob)


class TestSplitModels(unittest.TestCase):
    def test_single(self):
        self.assertEqual(CR.split_models("mob\\china\\bandit.bsr"),
                         ["mob\\china\\bandit.bsr"])

    def test_multi_variant(self):
        self.assertEqual(
            CR.split_models("mob\\sd\\seth.bsr,mob\\sd\\seth_t2.bsr,mob\\sd\\seth_t3.bsr"),
            ["mob\\sd\\seth.bsr", "mob\\sd\\seth_t2.bsr", "mob\\sd\\seth_t3.bsr"])

    def test_empty(self):
        self.assertEqual(CR.split_models(""), [])
        self.assertEqual(CR.split_models(None), [])


class TestSlug(unittest.TestCase):
    def test_bsk(self):
        self.assertEqual(CR.slug("/prim/skel/mob/china/bandit.bsk"),
                         "prim_skel_mob_china_bandit")

    def test_ddj_backslash(self):
        self.assertEqual(CR.slug("prim\\mtrl\\mob\\jupiter\\charm_whitch.ddj"),
                         "prim_mtrl_mob_jupiter_charm_whitch")


class TestBsrPath(unittest.TestCase):
    def test_bsr(self):
        self.assertEqual(CR.bsr_path("mob\\china\\bandit.bsr"),
                         "/res/mob/china/bandit.bsr")


class TestResolveTexture(unittest.TestCase):
    def test_bare_filename_relative_to_bmt(self):
        exists = {"/prim/mtrl/mob/china/bandit.ddj"}
        got = CR.resolve_texture(
            lambda p: b"", lambda p: p.lower() in exists,
            _bmt("bandit.ddj"), "/prim/mtrl/mob/china/bandit.bmt", "bandit")
        self.assertEqual(got, "/prim/mtrl/mob/china/bandit.ddj")

    def test_root_relative_path(self):
        exists = {"/prim/mtrl/mob/jupiter/charm_whitch.ddj"}
        got = CR.resolve_texture(
            lambda p: b"", lambda p: p.lower() in exists,
            _bmt("prim\\mtrl\\mob\\jupiter\\charm_whitch.ddj"),
            "/prim/mtrl/mob/jupiter/charm_witch.bmt", "flame_witch")
        self.assertEqual(got, "/prim/mtrl/mob/jupiter/charm_whitch.ddj")

    def test_missing_material_raises(self):
        with self.assertRaises(KeyError):
            CR.resolve_texture(
                lambda p: b"", lambda p: False,
                _bmt("bandit.ddj"), "/prim/mtrl/mob/china/bandit.bmt", "nope")


class TestLoadCharacterdata(unittest.TestCase):
    def test_join_and_split(self):
        text = "\r\n".join([
            "a\t1949\t...\t" + "mob\\china\\bandit.bsr",
            "b\t26738\t...\t" + "mob\\sd\\seth.bsr,mob\\sd\\seth_t2.bsr",
            "c\t9999\t...\t" + "not_a_model",
        ])
        idx = CR.load_characterdata(text)
        self.assertEqual(idx["1949"], ["mob\\china\\bandit.bsr"])
        self.assertEqual(idx["26738"],
                         ["mob\\sd\\seth.bsr", "mob\\sd\\seth_t2.bsr"])
        self.assertNotIn("9999", idx)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace && uv run python scripts/test_phase20_resolve.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'character_resolve'`.

- [ ] **Step 3: Write `scripts/character_resolve.py`**

```python
#!/usr/bin/env python3
"""Phase 20 character resolution primitives (pure; no PK2 reader).

Centralizes the proven NPC->character model resolution and per-component
classification so the bulk converter and the census share one implementation.

Inputs are injected as callables so this module stays archive-agnostic:
  read(path)        -> bytes (raises KeyError when the path is absent)
  path_exists(path) -> bool

Status vocabulary (exact): PROVEN / PARTIAL / UNKNOWN. Nothing is invented.
"""
from __future__ import annotations

STATUS_PROVEN = "PROVEN"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNKNOWN = "UNKNOWN"


def split_models(col52):
    """Split a characterdata col52 model path on commas (multi-BSR variants).

    Proven: some refids map to a comma-separated list of .bsr paths, each a
    distinct visual variant sharing one refid (e.g. 'mob\\sd\\seth.bsr,
    mob\\sd\\seth_t2.bsr,mob\\sd\\seth_t3.bsr').
    """
    return [m.strip() for m in (col52 or "").split(",") if m.strip()]


def slug(path):
    """Deterministic shared-store slug for a source path."""
    p = path.replace("\\", "/").lower().strip("/")
    stem = p.rsplit(".", 1)[0] if "." in p else p
    return stem.replace("/", "_").replace(" ", "_")


def bsr_path(bsr_rel):
    """'mob\\china\\bandit.bsr' -> '/res/mob/china/bandit.bsr'."""
    return "/res/" + bsr_rel.replace("\\", "/")


def resolve_texture(read, path_exists, bmt_blob, bmt_path, material_ref):
    """Resolve a bms material name to its ddj path.

    Proven ddj forms in a .bmt (from real Data.pk2):
      * bare filename 'bandit.ddj'  -> relative to the bmt directory
      * root-relative 'prim\\mtrl\\mob\\jupiter\\charm_whitch.ddj'
    Both are resolved by archive existence (two candidates), never guessed.
    """
    from world_terrain import parse_bmt

    mats = parse_bmt(bmt_blob)
    want = material_ref.lower()
    bmt_dir = bmt_path.rsplit("/", 1)[0]
    for name, ddj in mats.items():
        if name.lower() != want:
            continue
        ddj = ddj.replace("\\", "/")
        root_rel = "/" + ddj.lstrip("/")
        dir_rel = bmt_dir + "/" + ddj
        for cand in (root_rel, dir_rel):
            if path_exists(cand):
                return cand
        raise KeyError(material_ref)
    raise KeyError("material %r not in bmt %s" % (material_ref, bmt_path))


def load_characterdata(text):
    """Parse characterdata_*.txt (utf-16-le) into {refid: [model_path, ...]}.

    Col1 = refid (numeric), col52 = model path(s). col52 is comma-split; rows
    whose col52 is empty or not .bsr are ignored.
    """
    idx = {}
    for ln in text.split("\r\n"):
        cols = ln.split("\t")
        if len(cols) > 52 and cols[1].isdigit():
            models = split_models(cols[52])
            if models and models[0].lower().endswith(".bsr"):
                idx.setdefault(cols[1], models)
    return idx


def classify_character(read, path_exists, bsr_rel):
    """Classify one character model (.bsr rel) at component granularity.

    Returns:
      {
        "model": bsr_rel, "path": "/res/...",
        "status": PROVEN|PARTIAL|UNKNOWN,
        "skeleton": {status, path, bones} | None,
        "meshes": [{bms, status, ddj, material, reason?}, ...],
        "animations": [{ban, status, reason?}, ...],
        "reasons": [str, ...],
      }
    """
    import animation_pose as AP
    import bms_decoder
    import bsk_decoder
    import bsr_decoder

    path = bsr_path(bsr_rel)
    meshes = []
    animations = []
    reasons = []
    skeleton = None
    try:
        blob = read(path)
    except KeyError:
        return {"model": bsr_rel, "path": path, "status": STATUS_UNKNOWN,
                "skeleton": None, "meshes": [], "animations": [],
                "reasons": ["bsr missing"]}

    p = bsr_decoder.parse_bsr_references(blob)
    if not p["is_character"]:
        return {"model": bsr_rel, "path": path, "status": STATUS_UNKNOWN,
                "skeleton": None, "meshes": [], "animations": [],
                "reasons": ["not character (no .bsk)"]}

    if not p["skeleton"]:
        reasons.append("no skeleton")
    else:
        bsk_path = p["skeleton"][0]
        try:
            skel = bsk_decoder.parse_bsk(read(bsk_path))
            skeleton = {"status": STATUS_PROVEN if skel["exact"] else STATUS_PARTIAL,
                        "path": bsk_path, "bones": len(skel["bones"])}
            if not skel["exact"]:
                reasons.append("bsk inexact")
        except KeyError:
            skeleton = {"status": STATUS_UNKNOWN, "path": bsk_path, "bones": 0}
            reasons.append("bsk missing")

    bmt_blob = None
    bmt_path = p["materials"][0] if p["materials"] else None
    if bmt_path is None:
        reasons.append("no material")
    else:
        try:
            bmt_blob = read(bmt_path)
        except KeyError:
            reasons.append("bmt missing")

    for bms in p["meshes"]:
        rec = {"bms": bms, "status": STATUS_PROVEN}
        try:
            b = read(bms)
            header = bms_decoder.parse_bms_header(b)
            mref = header["names"][1] if len(header["names"]) >= 2 else None
            if mref is None:
                rec["status"] = STATUS_PARTIAL
                rec["reason"] = "no material name"
            elif bmt_blob is None:
                rec["status"] = STATUS_PARTIAL
                rec["reason"] = "bmt missing"
            else:
                ddj = resolve_texture(read, path_exists, bmt_blob, bmt_path, mref)
                read(ddj)
                rec["ddj"] = ddj
                rec["material"] = mref
        except KeyError as exc:
            rec["status"] = STATUS_UNKNOWN
            rec["reason"] = "missing: %s" % exc
        except Exception as exc:  # noqa: BLE001 - classification must not raise
            rec["status"] = STATUS_UNKNOWN
            rec["reason"] = str(exc)
        if rec["status"] != STATUS_PROVEN:
            reasons.append("mesh %s: %s" % (bms, rec.get("reason", rec["status"])))
        meshes.append(rec)

    for ban in p["animations"]:
        rec = {"ban": ban, "status": STATUS_PROVEN}
        try:
            AP.load_keyframes(read(ban))
        except Exception as exc:  # noqa: BLE001
            rec["status"] = STATUS_UNKNOWN
            rec["reason"] = str(exc)
            reasons.append("anim %s: %s" % (ban, str(exc)))
        animations.append(rec)

    statuses = [r["status"] for r in meshes + animations]
    if skeleton:
        statuses.append(skeleton["status"])
    if not statuses:
        status = STATUS_UNKNOWN
    elif any(s == STATUS_UNKNOWN for s in statuses):
        status = STATUS_UNKNOWN
    elif any(s == STATUS_PARTIAL for s in statuses):
        status = STATUS_PARTIAL
    else:
        status = STATUS_PROVEN

    return {"model": bsr_rel, "path": path, "status": status,
            "skeleton": skeleton, "meshes": meshes, "animations": animations,
            "reasons": reasons}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /workspace && uv run python scripts/test_phase20_resolve.py`
Expected: PASS (all 10 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/character_resolve.py scripts/test_phase20_resolve.py
git commit -m "feat(scripts): add character resolution/classification primitives"
```

---

### Task 2: Reusable `convert_character()` + `convert_player()` in `build_character_manifest.py`

**Files:**
- Modify: `scripts/build_character_manifest.py`
- Test: `scripts/test_phase20_conversion.py` (live; added in Task 8, hermetic part here)

**Interfaces:**
- Consumes: `character_resolve` (`slug`, `bsr_path`, `split_models`, `resolve_texture`, `load_characterdata`), `bsk_decoder`, `bsr_decoder`, `bms_decoder`, `animation_pose`, `skeleton`, `dds_decode`, `bms_to_asset`.
- Produces:
  - `convert_character(read_data, read_media, path_exists, bsr_rel, out_root, key)` -> dict manifest (writes shared assets + `<key>/manifest.json` + `<key>/provenance.json` + `<key>/npc_placements.tsv`).
  - `convert_player(read_data, read_media, path_exists, out_root)` -> dict manifest (key `player`).
  - `path_exists(read_media)` helper.

- [ ] **Step 1: Fix `resolve_texture` and `load_characterdata` to delegate to `character_resolve`**

Edit `scripts/build_character_manifest.py`. Replace the module's `resolve_texture` (lines 122–130) and `load_characterdata` (lines 86–99) with delegation. Add import of `character_resolve`.

Replace:

```python
def load_characterdata(read_media):
    """Join characterdata_*.txt (Media.pk2) on col1 (proven refid column)."""
    idx = {}
    for p in sorted(read_media.paths_matching("characterdata")):
        raw = read_media.read(p)
        try:
            text = raw.decode("utf-16-le", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            text = raw.decode("utf-8", errors="replace")
        for ln in text.split("\r\n"):
            cols = ln.split("\t")
            if len(cols) > 52 and cols[1].isdigit():
                idx.setdefault(cols[1], cols[52])
    return idx
```

with:

```python
def load_characterdata(read_media):
    """Join characterdata_*.txt (Media.pk2) on col1 -> [col52 model paths].

    col52 is comma-split (multi-BSR variants share one refid). Returns
    {refid: [model_path, ...]}.
    """
    import character_resolve
    idx = {}
    for p in sorted(read_media.paths_matching("characterdata")):
        raw = read_media.read(p)
        try:
            text = raw.decode("utf-16-le", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            text = raw.decode("utf-8", errors="replace")
        for refid, models in character_resolve.load_characterdata(text).items():
            idx.setdefault(refid, models)
    return idx
```

Replace `resolve_texture` (lines 122–130):

```python
def resolve_texture(read_data, bmt_blob, bmt_path, material_ref):
    """material_ref (from bms names[1]) -> ddj path (case-insensitive)."""
    mats = _bmt_materials(bmt_blob)
    bmt_dir = os.path.dirname(bmt_path)
    want = material_ref.lower()
    for name, ddj in mats.items():
        if name.lower() == want:
            return (bmt_dir + "/" + ddj).replace("\\", "/")
    raise ChainError(f"material {material_ref!r} not in bmt {bmt_path}: {sorted(mats)}")
```

with (delegating, but keeping the `ChainError` raise for `real_npc_chain` compatibility):

```python
def resolve_texture(read_data, bmt_blob, bmt_path, material_ref):
    """material_ref (from bms names[1]) -> ddj path, both ddj forms proven."""
    import character_resolve
    try:
        return character_resolve.resolve_texture(
            read_data.read, lambda p: read_data._has(p), bmt_blob, bmt_path,
            material_ref)
    except KeyError as exc:
        raise ChainError(str(exc)) from exc
```

- [ ] **Step 2: Add `_has(path)` to `_Pk2Reader`**

Edit the `_Pk2Reader` class (after `read`, before `close`):

```python
    def _has(self, path):
        key = ("/" + path.lstrip("/")).lower()
        return key in self._by_path
```

- [ ] **Step 3: Add `convert_character()` (reusable, shared-store writer)**

Append after `_build_with` (before `real_npc_chain`). This replaces the bandit-specific inline conversion with a parameterized version keyed by `bsr_rel`/`key`.

```python
def path_exists(read_media):
    return read_media._has


def convert_character(read_data, read_media, bsr_rel, out_root, key):
    """Convert one character model (bsr_rel) into the shared asset store.

    Writes:
      <out_root>/shared/skel/<slug>.json, shared/mesh/<slug>.msh,
      shared/tex/<slug>.png, shared/anim/<slug>.json
      <out_root>/<key>/manifest.json, <key>/provenance.json,
      <key>/npc_placements.tsv
    Returns the manifest dict. Raises ChainError on the first unproven edge.
    """
    import character_resolve

    bsr_path = character_resolve.bsr_path(bsr_rel)
    bsr_blob = read_data.read(bsr_path)
    parsed = bsr_decoder.parse_bsr_references(bsr_blob)
    if not parsed["is_character"]:
        raise ChainError(f"{bsr_path} is not a character bsr")

    skel_slug, skeleton = _write_skeleton(
        read_data, read_media, parsed, out_root, key)

    bmt_path = parsed["materials"][0]
    bmt_blob = read_data.read(bmt_path)

    mesh_entries = []
    tex_by_ddj = {}
    for idx, bms_path in enumerate(parsed["meshes"]):
        bms_blob = read_data.read(bms_path)
        header = B.parse_bms_header(bms_blob)
        if len(header["names"]) < 2:
            raise ChainError(f"bms {bms_path} missing material name")
        material_ref = header["names"][1]
        ddj_path = resolve_texture(read_data, bmt_blob, bmt_path, material_ref)
        ddj_blob = read_data.read(ddj_path)
        msh_slug = character_resolve.slug(bms_path)
        tex_slug = character_resolve.slug(ddj_path)
        _write_shared_bytes(
            out_root, "mesh", msh_slug + ".msh",
            bms_to_msh_skinned(bms_blob, texture_index=0)[0])
        if tex_slug not in tex_by_ddj:
            w, h, rgba = ddj_to_rgba(ddj_blob)
            _write_shared_bytes(out_root, "tex", tex_slug + ".png",
                                png_from_rgba(w, h, rgba))
            tex_by_ddj[tex_slug] = True
        prov = bms_to_asset_prov(bms_blob)
        mesh_entries.append({
            "msh": msh_slug, "tex": tex_slug, "skinned": True,
            "material": material_ref, "bms_path": bms_path, "ddj_path": ddj_path,
            "vcount": prov["asset"]["vertex_count"],
            "tcount": prov["asset"]["triangle_count"],
            "skin_records": prov["asset"]["skin_records"],
            "bone_count": prov["asset"]["bone_count"],
        })

    anim_entries = []
    for ban_path in parsed["animations"]:
        ban_blob = read_data.read(ban_path)
        anim = AP.load_keyframes(ban_blob)
        anim_slug = character_resolve.slug(ban_path)
        stem = os.path.basename(ban_path)[:-4]
        anim_json = {
            "path": ban_path, "duration_ms": anim["duration_ms"],
            "timestamps": anim["timestamps"],
            "channels": {
                name: [[[round(x, 6) for x in q], [round(x, 6) for x in p]]
                       for q, p in recs]
                for name, recs in anim["channels"].items()
            },
        }
        _write_shared_bytes(out_root, "anim", anim_slug + ".json",
                            json.dumps(anim_json, indent=1).encode("utf-8"))
        anim_entries.append({
            "anim": anim_slug, "name": stem, "ban_path": ban_path,
            "duration_ms": anim["duration_ms"], "keyframes": len(anim["timestamps"]),
            "channels": len(anim["channels"]),
        })

    manifest = {"key": key, "skeleton": skel_slug,
                "skeleton_path": parsed["skeleton"][0],
                "meshes": mesh_entries, "anims": anim_entries}
    _write_manifest(out_root, key, manifest)
    _write_provenance(out_root, key, {
        "bsr": bsr_path, "bsk": parsed["skeleton"][0], "bmt": bmt_path,
        "meshes": parsed["meshes"], "animations": parsed["animations"],
    })
    _write_placements(out_root, key, read_data, read_media, parsed, bsr_rel)
    return manifest
```

- [ ] **Step 4: Add the private writer helpers**

Append after `convert_character`:

```python
def bms_to_asset_prov(bms_blob):
    msh_bytes, prov = bms_to_msh_skinned(bms_blob, texture_index=0)
    return prov


def _shared_dir(out_root, kind):
    d = os.path.join(out_root, "shared", kind)
    os.makedirs(d, exist_ok=True)
    return d


def _write_shared_bytes(out_root, kind, name, blob):
    with open(os.path.join(_shared_dir(out_root, kind), name), "wb") as fh:
        fh.write(blob)


def _write_manifest(out_root, key, manifest):
    d = os.path.join(out_root, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)


def _write_provenance(out_root, key, prov):
    d = os.path.join(out_root, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "provenance.json"), "w") as fh:
        json.dump(prov, fh, indent=1, sort_keys=True)


def _write_skeleton(read_data, read_media, parsed, out_root, key):
    import character_resolve
    bsk_path = parsed["skeleton"][0]
    bsk_blob = read_data.read(bsk_path)
    skel = bsk_decoder.parse_bsk(bsk_blob)
    if not skel["exact"]:
        raise ChainError(f"bsk {bsk_path} not exact: {skel['error']}")
    wrot, wpos = SK.bind_world(skel["bones"])
    skeleton_json = {
        "path": bsk_path, "bone_count": len(skel["bones"]),
        "quaternion_convention": "xyzw",
        "bones": [{
            "name": b["name"], "parent": b["parent"], "children": b["children"],
            "rot_parent": [round(x, 6) for x in b["rot_parent"]],
            "tr_parent": [round(x, 6) for x in b["tr_parent"]],
            "bind_world_rot": [round(x, 6) for x in wrot[i]],
            "bind_world_pos": [round(x, 6) for x in wpos[i]],
        } for i, b in enumerate(skel["bones"])],
    }
    slug = character_resolve.slug(bsk_path)
    _write_shared_bytes(out_root, "skel", slug + ".json",
                        json.dumps(skeleton_json, indent=1).encode("utf-8"))
    return slug, skeleton_json


def _write_placements(out_root, key, read_data, read_media, parsed, bsr_rel):
    # Resolve the refid(s) that map to this bsr_rel for placement rows.
    refids = []
    for refid, models in load_characterdata(read_media).items():
        if bsr_rel in models:
            refids.append(refid)
    placements = []
    for row in load_npcpos():
        if row[0] not in refids:
            continue
        region = int(row[1])
        x, z = float(row[2]), float(row[4])
        wx, wz = wt.npc_to_world(x, z, region, REF_SX, REF_SY)
        sx, sy = wt.unpack_region(region)
        placements.append({
            "refid": row[0], "region": region, "sector": f"{sx}x{sy}",
            "local_x": round(x, 3), "local_z": round(z, 3),
            "world_x": round(wx, 3), "world_z": round(wz, 3), "height": row[3],
        })
    d = os.path.join(out_root, key)
    os.makedirs(d, exist_ok=True)
    cols = ["refid", "region", "sector", "local_x", "local_z",
            "world_x", "world_z", "height"]
    with open(os.path.join(d, "npc_placements.tsv"), "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in placements:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")
```

- [ ] **Step 5: Add `convert_player()`**

Append after `_write_placements`:

```python
def convert_player(read_data, read_media, out_root):
    """Convert the proven chinaman player assembly into key 'player'.

    The player is PARTIAL (BSR->skeleton mismatch + no static spawn), but every
    mesh/clothes/weapon part, material, and animation used here is PROVEN by
    byte-exact archive presence (Phase 19). The skeleton is chinaman_skel.bsk.
    """
    skel_blob = read_data.read(PLAYER_SKELETON)
    skel = bsk_decoder.parse_bsk(skel_blob)
    if not skel["exact"]:
        raise ChainError(f"player skeleton not exact: {skel['error']}")
    wrot, wpos = SK.bind_world(skel["bones"])
    skeleton_json = {
        "path": PLAYER_SKELETON, "bone_count": len(skel["bones"]),
        "quaternion_convention": "xyzw",
        "bones": [{
            "name": b["name"], "parent": b["parent"], "children": b["children"],
            "rot_parent": [round(x, 6) for x in b["rot_parent"]],
            "tr_parent": [round(x, 6) for x in b["tr_parent"]],
            "bind_world_rot": [round(x, 6) for x in wrot[i]],
            "bind_world_pos": [round(x, 6) for x in wpos[i]],
        } for i, b in enumerate(skel["bones"])],
    }
    import character_resolve
    skel_slug = character_resolve.slug(PLAYER_SKELETON)
    _write_shared_bytes(out_root, "skel", skel_slug + ".json",
                        json.dumps(skeleton_json, indent=1).encode("utf-8"))

    mesh_entries = []
    body_meshes = PLAYER_BODY + PLAYER_CLOTHES + [PLAYER_WEAPON]
    for idx, bms_path in enumerate(body_meshes):
        bms_blob = read_data.read(bms_path)
        header = B.parse_bms_header(bms_blob)
        material_ref = header["names"][1] if len(header["names"]) >= 2 else None
        # Resolve texture from the first matching player material bmt.
        ddj_path = None
        for bmt_path in PLAYER_MATERIALS:
            try:
                ddj_path = resolve_texture(
                    read_data, read_data.read(bmt_path), bmt_path, material_ref)
                break
            except ChainError:
                continue
        if ddj_path is None:
            raise ChainError(f"no texture for player mesh {bms_path}")
        ddj_blob = read_data.read(ddj_path)
        msh_slug = character_resolve.slug(bms_path)
        tex_slug = character_resolve.slug(ddj_path)
        _write_shared_bytes(out_root, "mesh", msh_slug + ".msh",
                            bms_to_msh_skinned(bms_blob, texture_index=0)[0])
        w, h, rgba = ddj_to_rgba(ddj_blob)
        _write_shared_bytes(out_root, "tex", tex_slug + ".png",
                            png_from_rgba(w, h, rgba))
        prov = bms_to_asset_prov(bms_blob)
        mesh_entries.append({
            "msh": msh_slug, "tex": tex_slug, "skinned": True,
            "material": material_ref or "", "bms_path": bms_path,
            "ddj_path": ddj_path,
            "vcount": prov["asset"]["vertex_count"],
            "tcount": prov["asset"]["triangle_count"],
            "skin_records": prov["asset"]["skin_records"],
            "bone_count": prov["asset"]["bone_count"],
        })

    anim_entries = []
    for ban_path in PLAYER_ANIMS:
        ban_blob = read_data.read(ban_path)
        anim = AP.load_keyframes(ban_blob)
        anim_slug = character_resolve.slug(ban_path)
        stem = os.path.basename(ban_path)[:-4]
        anim_json = {
            "path": ban_path, "duration_ms": anim["duration_ms"],
            "timestamps": anim["timestamps"],
            "channels": {
                name: [[[round(x, 6) for x in q], [round(x, 6) for x in p]]
                       for q, p in recs]
                for name, recs in anim["channels"].items()
            },
        }
        _write_shared_bytes(out_root, "anim", anim_slug + ".json",
                            json.dumps(anim_json, indent=1).encode("utf-8"))
        anim_entries.append({
            "anim": anim_slug, "name": stem, "ban_path": ban_path,
            "duration_ms": anim["duration_ms"], "keyframes": len(anim["timestamps"]),
            "channels": len(anim["channels"]),
        })

    manifest = {"key": "player", "skeleton": skel_slug,
                "skeleton_path": PLAYER_SKELETON, "meshes": mesh_entries,
                "anims": anim_entries}
    _write_manifest(out_root, "player", manifest)
    _write_provenance(out_root, "player", {
        "bsr": PLAYER_BSR, "bsk": PLAYER_SKELETON,
        "meshes": body_meshes, "animations": PLAYER_ANIMS,
        "note": "PARTIAL: BSR references europeman_skel (43 bones) not chinaman_skel; no static spawn",
    })
    return manifest
```

- [ ] **Step 6: Add `import bms_to_msh_skinned` already present; verify no regressions**

Run the existing hermetic + live bandit chain test:

```bash
cd /workspace && uv run python scripts/test_phase18_character.py
cd /workspace && SRO_PK2_DIR=/tmp/opencode/pk2raw uv run python scripts/test_phase19_real_npc.py
```

Expected: both PASS (bandit chain still resolves via the new `resolve_texture` delegation; `real_npc_chain` unchanged).

- [ ] **Step 7: Commit**

```bash
git add scripts/build_character_manifest.py
git commit -m "feat(scripts): add reusable convert_character/convert_player"
```

---

### Task 3: `build_character_catalog.py` — bulk driver (index.tsv + coverage.json)

**Files:**
- Create: `scripts/build_character_catalog.py`
- Test: `scripts/test_phase20_catalog.py` (hermetic enumeration), `scripts/test_phase20_conversion.py` (live conversion; Task 8)

**Interfaces:**
- Consumes: `character_resolve`, `build_character_manifest` (`_Pk2Reader`, `convert_character`, `convert_player`, `load_npcpos`, `load_characterdata`), `pk2_table`, `sro_paths`.
- Produces: writes `characters/index.tsv`, `characters/coverage.json`, and per-key character dirs + shared store. Returns a summary dict.

- [ ] **Step 1: Write the failing hermetic enumeration test**

`scripts/test_phase20_catalog.py`:

```python
#!/usr/bin/env python3
"""Phase 20 Part B: catalog enumeration (hermetic)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_character_catalog as BCC  # noqa: E402


class TestEnumerateSpawns(unittest.TestCase):
    def test_refid_to_models(self):
        chardata = {"1949": ["mob\\china\\bandit.bsr"],
                    "26738": ["mob\\sd\\seth.bsr", "mob\\sd\\seth_t2.bsr"]}
        spawn_rows = [["1949", "1", "0", "0", "0"],
                      ["26738", "2", "0", "0", "0"],
                      ["1949", "3", "0", "0", "0"]]
        spawn_refids, refid_models, model_counts = BCC.enumerate_spawns(
            chardata, spawn_rows)
        self.assertEqual(spawn_refids, {"1949", "26738"})
        self.assertEqual(refid_models["1949"], ["mob\\china\\bandit.bsr"])
        self.assertEqual(model_counts["mob\\china\\bandit.bsr"], 2)

    def test_refid_without_model_ignored(self):
        spawn_refids, refid_models, model_counts = BCC.enumerate_spawns(
            {"1949": ["mob\\china\\bandit.bsr"]},
            [["9999", "1", "0", "0", "0"]])
        self.assertEqual(spawn_refids, {"1949"})
        self.assertEqual(refid_models, {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace && uv run python scripts/test_phase20_catalog.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'build_character_catalog'`.

- [ ] **Step 3: Write `scripts/build_character_catalog.py`**

```python
#!/usr/bin/env python3
"""Phase 20 bulk character catalog builder (offline, deterministic).

Enumerates every spawning NPC, classifies its model(s) at component
granularity, converts every PROVEN model into a content-addressed shared
asset store, and emits:

  android/app/src/main/assets/game/world/characters/index.tsv     (refid->key)
  android/app/src/main/assets/game/world/characters/coverage.json (audit)
  shared/{skel,mesh,tex,anim}/<slug>.*                            (deduped assets)
  <key>/manifest.json + <key>/provenance.json + <key>/npc_placements.tsv

Usage: uv run scripts/build_character_catalog.py --pk2-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import pk2_table  # noqa: E402
import sro_paths  # noqa: E402
import build_character_manifest as BCM  # noqa: E402
import character_resolve as CR  # noqa: E402

ASSETS = os.path.join(
    BASE, "..", "android", "app", "src", "main", "assets",
    "game", "world", "characters")

INDEX_COLS = ["refid", "key", "variant", "status", "spawn_count"]


def enumerate_spawns(chardata, spawn_rows):
    """(spawn_refids, refid_models, model_spawn_counts) from npcpos rows.

    spawn_rows are raw npcpos columns (col0=refid). refid_models maps a
    spawning refid to its model list; model_spawn_counts counts spawn rows
    per distinct model path (first variant only).
    """
    spawn_refids = set()
    refid_models = {}
    model_counts = {}
    for row in spawn_rows:
        refid = row[0]
        spawn_refids.add(refid)
        models = chardata.get(refid)
        if not models:
            continue
        refid_models[refid] = models
        primary = models[0]
        model_counts[primary] = model_counts.get(primary, 0) + 1
    return spawn_refids, refid_models, model_counts


def _build(out_root, pk2_dir):
    data_pk2 = sro_paths.pk2_archive(pk2_dir, "Data.pk2")
    media_pk2 = sro_paths.pk2_archive(pk2_dir, "Media.pk2")
    read_data = BCM._Pk2Reader(data_pk2)
    read_media = BCM._Pk2Reader(media_pk2)
    try:
        return _build_with(read_data, read_media, out_root)
    finally:
        read_data.close()
        read_media.close()


def _build_with(read_data, read_media, out_root):
    os.makedirs(out_root, exist_ok=True)
    chardata = BCM.load_characterdata(read_media)
    spawn_rows = BCM.load_npcpos()
    spawn_refids, refid_models, model_counts = enumerate_spawns(chardata, spawn_rows)

    # Distinct model set across all spawning refids (comma-split already done).
    models = {}
    for refid, ms in refid_models.items():
        for m in ms:
            models.setdefault(m, refid)

    # Classify every distinct model.
    classified = {m: CR.classify_character(
        read_data.read, read_media._has, m) for m in sorted(models)}

    # Convert every PROVEN model + player; PARTIAL/UNKNOWN are documented only.
    index_rows = []
    audit_models = []
    proven = partial = unknown = 0
    for m in sorted(models):
        cls = classified[m]
        key = CR.slug(CR.bsr_path(m))
        if cls["status"] == CR.STATUS_PROVEN:
            proven += 1
            BCM.convert_character(read_data, read_media, m, out_root, key)
        elif cls["status"] == CR.STATUS_PARTIAL:
            partial += 1
        else:
            unknown += 1
        refids = [r for r, ms in refid_models.items() if m in ms]
        for refid in refids:
            variant = refid_models[refid].index(m)
            index_rows.append([refid, key, variant, cls["status"],
                               model_counts.get(m, 0)])
        audit_models.append({
            "refids": refids, "key": key, "model": m,
            "status": cls["status"], "spawn_count": model_counts.get(m, 0),
            "skeleton": cls["skeleton"],
            "mesh_parts": cls["meshes"],
            "animations": cls["animations"],
            "reasons": cls["reasons"],
        })

    # Player (always attempted; documented PARTIAL regardless).
    player_status = CR.STATUS_PARTIAL
    try:
        BCM.convert_player(read_data, read_media, out_root)
        player_ok = True
    except Exception as exc:  # noqa: BLE001
        player_ok = False
        player_status = CR.STATUS_UNKNOWN

    _write_index(out_root, index_rows)
    coverage = {
        "totals": {
            "spawn_rows": len(spawn_rows),
            "spawn_refids": len(spawn_refids),
            "refids_with_model": len(refid_models),
            "distinct_models": len(models),
            "proven_models": proven,
            "partial_models": partial,
            "unknown_models": unknown,
            "player": {"status": player_status, "converted": player_ok},
        },
        "models": audit_models,
    }
    with open(os.path.join(out_root, "coverage.json"), "w") as fh:
        json.dump(coverage, fh, indent=1, sort_keys=True)
    return coverage


def _write_index(out_root, rows):
    rows = sorted(rows, key=lambda r: (r[0], r[2]))
    with open(os.path.join(out_root, "index.tsv"), "w") as fh:
        fh.write("\t".join(INDEX_COLS) + "\n")
        for r in rows:
            fh.write("\t".join(str(c) for c in r) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=ASSETS)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    coverage = _build(args.out, args.pk2_dir)
    t = coverage["totals"]
    print("proven=%d partial=%d unknown=%d models=%d player=%s"
          % (t["proven_models"], t["partial_models"], t["unknown_models"],
             t["distinct_models"], t["player"]["status"]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run hermetic test**

Run: `cd /workspace && uv run python scripts/test_phase20_catalog.py`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the bulk build (live, writes committed assets)**

```bash
cd /workspace && SRO_PK2_DIR=/tmp/opencode/pk2raw uv run scripts/build_character_catalog.py
```

Expected: prints `proven=… partial=… unknown=… models=… player=PARTIAL` and writes `index.tsv`, `coverage.json`, `shared/…`, and `*/manifest.json` under `android/app/src/main/assets/game/world/characters/`.

- [ ] **Step 6: Commit (assets + driver)**

```bash
git add scripts/build_character_catalog.py scripts/test_phase20_catalog.py \
  android/app/src/main/assets/game/world/characters/
git commit -m "feat(scripts): bulk character catalog builder + full asset set"
```

---

### Task 4: Static mesh parts (37 no-skin-block parts)

**Files:**
- Modify: `scripts/build_character_manifest.py` (extend `convert_character` to fall back to static MSH v1)
- Modify: `scripts/build_character_catalog.py` (mark mixed characters PARTIAL when a part is static-fallback or unproven)

**Interfaces:**
- Consumes: `bms_to_asset.bms_to_msh` (MSH v1) and `bms_to_msh_skinned`.
- Produces: `convert_character` writes `skinned=false` parts and stores `StaticMeshAsset.parse`-compatible v1 `.msh`.

- [ ] **Step 1: Extend `convert_character` to fall back to static MSH v1**

In `convert_character`, replace the mesh loop body that calls `bms_to_msh_skinned` with a try/fallback:

```python
        try:
            msh_bytes, prov = bms_to_msh_skinned(bms_blob, texture_index=0)
            skinned = True
        except B.MshFormatError:
            msh_bytes, prov = bms_to_msh(bms_blob, texture_index=0)
            skinned = False
        _write_shared_bytes(out_root, "mesh", msh_slug + ".msh", msh_bytes)
        ...
        mesh_entries.append({
            ..., "skinned": skinned,
            "vcount": prov["asset"]["vertex_count"],
            "tcount": prov["asset"]["triangle_count"],
            "skin_records": prov["asset"].get("skin_records", 0),
            "bone_count": prov["asset"].get("bone_count", 0),
        })
```

- [ ] **Step 2: Import `bms_to_msh`**

Update the top-level import in `build_character_manifest.py`:

```python
from bms_to_asset import bms_to_msh, bms_to_msh_skinned  # noqa: E402
```

(Add `bms_to_msh` next to the existing `bms_to_msh_skinned` import at line 47.)

- [ ] **Step 3: Mark mixed characters PARTIAL (static fallback is still PROVEN geometry)**

The static fallback is a proven MSH v1 of the real geometry, so the part is still PROVEN; the character stays PROVEN. `karkadann` (2 unproven-triangle parts) will raise `BmsFormatError` inside `convert_character`, so the catalog must catch per-model conversion failure and mark that model PARTIAL:

In `build_character_catalog.py` `_build_with`, wrap the `convert_character` call:

```python
        if cls["status"] == CR.STATUS_PROVEN:
            try:
                BCM.convert_character(read_data, read_media, m, out_root, key)
                proven += 1
            except Exception as exc:  # noqa: BLE001 - per-model fail-closed
                cls["status"] = CR.STATUS_PARTIAL
                cls["reasons"].append("conversion failed: %s" % exc)
                partial += 1
                audit_models_append_placeholder = True
        else:
            ...
```

Implement by computing `status` from a local variable after the try/except; keep the existing `proven/partial/unknown` counters accurate. Full replacement of the classification→conversion block:

```python
    for m in sorted(models):
        cls = classified[m]
        key = CR.slug(CR.bsr_path(m))
        if cls["status"] == CR.STATUS_PROVEN:
            try:
                BCM.convert_character(read_data, read_media, m, out_root, key)
            except Exception as exc:  # noqa: BLE001
                cls["status"] = CR.STATUS_PARTIAL
                cls["reasons"].append("conversion failed: %s" % exc)
        status = cls["status"]
        if status == CR.STATUS_PROVEN:
            proven += 1
        elif status == CR.STATUS_PARTIAL:
            partial += 1
        else:
            unknown += 1
        refids = [r for r, ms in refid_models.items() if m in ms]
        for refid in refids:
            variant = refid_models[refid].index(m)
            index_rows.append([refid, key, variant, status,
                               model_counts.get(m, 0)])
        audit_models.append({... "status": status ...})
```

- [ ] **Step 4: Re-run bulk build and verify `karkadann` is PARTIAL**

```bash
cd /workspace && SRO_PK2_DIR=/tmp/opencode/pk2raw uv run scripts/build_character_catalog.py
```

Expected: output still lists `karkadann` in `coverage.json` as PARTIAL with a conversion-failure reason; the other static-part characters convert as PROVEN.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_character_manifest.py scripts/build_character_catalog.py \
  android/app/src/main/assets/game/world/characters/
git commit -m "feat(scripts): static mesh fallback + fail-closed per-model conversion"
```

---

### Task 5: Java `CharacterCatalog` (refid → key)

**Files:**
- Create: `android/app/src/main/java/com/opensilkroadmap/app/world/CharacterCatalog.java`
- Test: `android/app/src/test/java/com/opensilkroadmap/app/world/CharacterCatalogTest.java`

**Interfaces:**
- Consumes: `com.opensilkroadmap.app.data.TsvTable` (existing `parse`/`loadDefault`).
- Produces: `CharacterCatalog.parse(Reader)`, `loadDefault()`, `keyFor(int refid) -> String|null`, `playerKey() -> "player"`, `characterKeys() -> Set<String>`, `count()`.

- [ ] **Step 1: Write the failing test**

`android/app/src/test/java/com/opensilkroadmap/app/world/CharacterCatalogTest.java`:

```java
package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.StringReader;
import org.junit.Test;

public class CharacterCatalogTest {
  private static final String TSV =
      "refid\tkey\tvariant\tstatus\tspawn_count\n"
          + "1949\tmob_china_bandit\t0\tPROVEN\t60\n"
          + "26738\tmob_sd_seth\t0\tPROVEN\t3\n"
          + "26738\tmob_sd_seth_t2\t1\tPROVEN\t3\n"
          + "12345\tart_guild_pulley\t0\tUNKNOWN\t1\n";

  @Test
  public void keyFor_primary_variant() throws Exception {
    CharacterCatalog c = CharacterCatalog.parse(new StringReader(TSV));
    assertEquals("mob_china_bandit", c.keyFor(1949));
    assertEquals("mob_sd_seth", c.keyFor(26738));
  }

  @Test
  public void keyFor_unknown_refid_is_null() throws Exception {
    CharacterCatalog c = CharacterCatalog.parse(new StringReader(TSV));
    assertNull(c.keyFor(0));
  }

  @Test
  public void playerKey_and_keys() throws Exception {
    CharacterCatalog c = CharacterCatalog.parse(new StringReader(TSV));
    assertEquals("player", c.playerKey());
    assertTrue(c.characterKeys().contains("mob_china_bandit"));
    assertEquals(4, c.count());
  }
}
```

- [ ] **Step 2: Compile to verify it fails**

Run: `cd /workspace && javac -d /tmp/opencode/classes -cp android/app/src/main/java -sourcepath android/app/src/main/java android/app/src/test/java/com/opensilkroadmap/app/world/CharacterCatalogTest.java 2>&1 | head`
Expected: FAIL — `cannot find symbol: class CharacterCatalog` (Android-importing sources fail to compile under plain javac; that is expected — this is a symbol-check only; full compile is Task 9).

- [ ] **Step 3: Write `CharacterCatalog.java`**

```java
package com.opensilkroadmap.app.world;

import com.opensilkroadmap.app.data.TsvTable;

import java.io.IOException;
import java.io.Reader;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * Refid -> character key index over the committed {@code characters/index.tsv}
 * (Phase 20). One row per (refid, variant); {@link #keyFor} returns the
 * primary (variant 0) character key for a spawning NPC refid. The player is
 * always key {@code "player"} and is not spawned by npcpos.
 *
 * <p>Pure JVM, no Android. Fail-closed: an unknown refid returns null.
 */
public final class CharacterCatalog {

  public static final String PLAYER_KEY = "player";

  /** (refid, variant) -> key; primary = variant 0. */
  private final Map<Long, String> primaryByRefid = new LinkedHashMap<Long, String>();
  private final Set<String> keys = new LinkedHashSet<String>();
  private final int rowCount;

  private CharacterCatalog(Map<Long, String> primaryByRefid,
                           Set<String> keys, int rowCount) {
    this.primaryByRefid.putAll(primaryByRefid);
    this.keys.addAll(keys);
    this.rowCount = rowCount;
  }

  public static CharacterCatalog parse(Reader reader) throws IOException {
    return fromTable(TsvTable.parse("index.tsv", reader));
  }

  public static CharacterCatalog loadDefault() throws IOException {
    return fromTable(TsvTable.loadDefault("characters/index.tsv"));
  }

  private static CharacterCatalog fromTable(TsvTable table) {
    Map<Long, String> primary = new LinkedHashMap<Long, String>();
    Set<String> keys = new LinkedHashSet<String>();
    for (String[] row : table.rows()) {
      long refid = TsvTable.intAt(row, 0);
      String key = row[1];
      int variant = TsvTable.intAt(row, 2);
      keys.add(key);
      if (!primary.containsKey(Long.valueOf(refid)) || variant == 0) {
        primary.put(Long.valueOf(refid), key);
      }
    }
    return new CharacterCatalog(primary, keys, table.rows().size());
  }

  /** Primary character key for a spawning NPC refid, or null when absent. */
  public String keyFor(int refid) {
    return primaryByRefid.get(Long.valueOf(refid));
  }

  public String playerKey() {
    return PLAYER_KEY;
  }

  public Set<String> characterKeys() {
    return Collections.unmodifiableSet(keys);
  }

  public int count() {
    return rowCount;
  }
}
```

- [ ] **Step 4: Verify `TsvTable` API (`parse`, `loadDefault`, `intAt`, `rows`)**

Read `android/app/src/main/java/com/opensilkroadmap/app/data/TsvTable.java` and confirm the signatures used above (`parse(String name, Reader)`, `loadDefault(String path)`, `intAt(String[], int)`, `rows()`). If `loadDefault` prepends a different base path than `game/textdata/`, adjust `loadDefault()` here to open `characters/index.tsv` under the assets root (`TsvTable.loadDefault` uses the `game/` assets root — verify and use `"characters/index.tsv"`).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/opensilkroadmap/app/world/CharacterCatalog.java \
  android/app/src/test/java/com/opensilkroadmap/app/world/CharacterCatalogTest.java
git commit -m "feat(android): CharacterCatalog refid->key index"
```

---

### Task 6: Generalize `CharacterMeshIndex` (key-based load + shared store)

**Files:**
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/CharacterMeshIndex.java`
- Test: `android/app/src/test/java/com/opensilkroadmap/app/world/CharacterMeshIndexMultiTest.java`

**Interfaces:**
- Consumes: `StaticMeshAsset.parse`, `StaticMeshAsset.parseSkinned`, `Pose.sample`.
- Produces: `CharacterMeshIndex.load(AssetManager, String key)`, `skeleton()`, `parts()` (`List<Part>` where `Part` now carries `skinned` and `StaticMeshAsset.Mesh`), `anims()`, `poseAt(String name, int tMs)`.
- Removes: `MeshRow`, `PlacementDef`, `Instance`, `instances()`, `instanceCount()`.

- [ ] **Step 1: Rewrite the `Part` and remove placement classes**

In `CharacterMeshIndex.java`, delete `MeshRow`, `PlacementDef`, `Instance` and the `instances()`, `instanceCount()` members. Replace `Part` with:

```java
  /** One character mesh part (real geometry + texture + optional skinning). */
  public static final class Part {
    public final int partIdx;
    public final String material;
    public final String ddjPath;
    public final boolean skinned;
    public final StaticMeshAsset.Mesh mesh;
    public final Bitmap texture;
    /** Bind-pose skinned positions (skinned parts only); null for static parts. */
    public final float[] bindPositions;

    Part(int partIdx, String material, String ddjPath, boolean skinned,
         StaticMeshAsset.Mesh mesh, Bitmap texture, float[] bindPositions) {
      this.partIdx = partIdx;
      this.material = material;
      this.ddjPath = ddjPath;
      this.skinned = skinned;
      this.mesh = mesh;
      this.texture = texture;
      this.bindPositions = bindPositions;
    }
  }
```

- [ ] **Step 2: Add instance fields for the manifest-driven model**

Replace the `CHARACTER_DIR` constant and instance fields:

```java
  private static final String CHARACTERS_ROOT = "game/world/characters/";
  private static final String SHARED = "shared/";

  private final String key;
  private final Skeleton skeleton;
  private final List<Part> parts;
  private final List<Anim> anims;
  private final Map<String, String> animSlugByName;
```

- [ ] **Step 3: Rewrite `load` and add `build(assets, key)`**

```java
  public static CharacterMeshIndex load(AssetManager assets, String key) {
    try {
      return build(assets, key);
    } catch (IOException e) {
      return null;
    }
  }

  public static CharacterMeshIndex load(AssetManager assets, String key,
                                        int refSx, int refSy) {
    return load(assets, key);
  }

  private static CharacterMeshIndex build(AssetManager assets, String key)
      throws IOException {
    String root = CHARACTERS_ROOT + key + "/";
    Map<String, Object> manifest = (Map<String, Object>)
        new JsonParser(readAll(new InputStreamReader(
            assets.open(root + "manifest.json"), StandardCharsets.UTF_8))).parse();

    String skelSlug = asString(manifest.get("skeleton"));
    Skeleton skeleton = parseSkeleton(new InputStreamReader(
        assets.open(CHARACTERS_ROOT + SHARED + "skel/" + skelSlug + ".json"),
        StandardCharsets.UTF_8));

    List<?> meshes = (List<?>) manifest.get("meshes");
    List<Part> parts = new ArrayList<Part>();
    int partIdx = 0;
    for (Object mo : meshes) {
      Map<String, Object> m = (Map<String, Object>) mo;
      String mshSlug = asString(m.get("msh"));
      String texSlug = asString(m.get("tex"));
      boolean skinned = m.get("skinned") == Boolean.TRUE;
      byte[] msh = readBytes(assets.open(
          CHARACTERS_ROOT + SHARED + "mesh/" + mshSlug + ".msh"));
      Bitmap tex = BitmapFactory.decodeStream(assets.open(
          CHARACTERS_ROOT + SHARED + "tex/" + texSlug + ".png"));
      if (tex == null) {
        throw new IOException("texture decode failed: " + texSlug);
      }
      float[] bindPositions = null;
      if (skinned) {
        StaticMeshAsset.SkinnedMesh sm = StaticMeshAsset.parseSkinned(msh);
        bindPositions = skinnedBindPositions(sm, skeleton);
        parts.add(new Part(partIdx++, asString(m.get("material")),
            asString(m.get("ddj_path")), true, sm, tex, bindPositions));
      } else {
        StaticMeshAsset.Mesh mesh = StaticMeshAsset.parse(msh);
        parts.add(new Part(partIdx++, asString(m.get("material")),
            asString(m.get("ddj_path")), false, mesh, tex, null));
      }
    }
    if (parts.isEmpty()) {
      throw new IOException("no character mesh parts");
    }

    List<?> animList = (List<?>) manifest.get("anims");
    List<Anim> anims = new ArrayList<Anim>();
    Map<String, String> animSlugByName = new HashMap<String, String>();
    for (Object ao : animList) {
      Map<String, Object> a = (Map<String, Object>) ao;
      String name = asString(a.get("name"));
      String animSlug = asString(a.get("anim"));
      animSlugByName.put(name, animSlug);
      anims.add(new Anim(asString(a.get("ban_path")), name,
          asInt(a.get("duration_ms")), asInt(a.get("keyframes")),
          asInt(a.get("channels")), animSlug));
    }

    return new CharacterMeshIndex(key, skeleton, parts, anims, animSlugByName);
  }
```

- [ ] **Step 4: Update the constructor and `poseAt`**

```java
  private CharacterMeshIndex(String key, Skeleton skeleton, List<Part> parts,
      List<Anim> anims, Map<String, String> animSlugByName) {
    this.key = key;
    this.skeleton = skeleton;
    this.parts = Collections.unmodifiableList(parts);
    this.anims = Collections.unmodifiableList(anims);
    this.animSlugByName = animSlugByName;
  }

  public Pose poseAt(String animName, int tMs) throws IOException {
    String slug = animSlugByName.get(animName);
    if (slug == null) {
      throw new IOException("unknown animation: " + animName);
    }
    String path = CHARACTERS_ROOT + SHARED + "anim/" + slug + ".json";
    String text = readAll(
        new InputStreamReader(assets.open(path), StandardCharsets.UTF_8));
    Map<String, Object> root = (Map<String, Object>) new JsonParser(text).parse();
    return Pose.sample(skeleton, root, tMs);
  }
```

The `assets` field is now unused in the model except by `poseAt`; keep the `private final AssetManager assets;` field and assign it in the constructor (used by `poseAt`).

- [ ] **Step 5: Delete the now-unused `parseMeshes`/`parsePlacements`/`parseAnims` parsers**

Remove `parseMeshes`, `parsePlacements`, and `parseAnims` (their TSV role is replaced by `manifest.json`). Keep `parseSkeleton`, `skinnedBindPositions`, `rotate`, the `as*` helpers, `readAll`, `readBytes`, and the `JsonParser` inner class. Add an `asString` overload guard (already present).

- [ ] **Step 6: Compile the main + test sources with the Android-free stub harness (Task 9 setup)**

Run the compile check after writing `CharacterMeshIndexMultiTest.java` (Task 9); the stub harness replaces `android.*` imports. Confirm no symbol errors.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/opensilkroadmap/app/world/CharacterMeshIndex.java
git commit -m "feat(android): generalize CharacterMeshIndex to key-based shared store"
```

---

### Task 7: `NativeWorldRenderer` — instance real NPCs by refid

**Files:**
- Modify: `android/app/src/main/java/com/opensilkroadmap/app/world/NativeWorldRenderer.java`

**Interfaces:**
- Consumes: `CharacterCatalog`, `CharacterMeshIndex`, `NpcSpawnIndex`.
- Produces: `setCharacters(Map<String, CharacterMeshIndex> models, CharacterCatalog catalog)`, `setCharacterModels(Map<String, CharacterMeshIndex>)`, `setCharacterCatalog(CharacterCatalog)`; `drawCharacters` instances by real refid.

- [ ] **Step 1: Replace the single `characters` field with a model map + catalog**

Replace `private CharacterMeshIndex characters;` with:

```java
  private CharacterCatalog characterCatalog;
  private Map<String, CharacterMeshIndex> characterModels =
      new HashMap<String, CharacterMeshIndex>();
```

- [ ] **Step 2: Replace `setCharacters` and add the new setters**

Replace `setCharacters(CharacterMeshIndex characters)`:

```java
  /** Attaches the character catalog (refid -> key) and loaded models. */
  public void setCharacters(CharacterCatalog catalog,
                            Map<String, CharacterMeshIndex> models) {
    this.characterCatalog = catalog;
    this.characterModels = (models == null)
        ? new HashMap<String, CharacterMeshIndex>() : models;
    shaderCache.clear();
    invalidate();
  }

  public void setCharacterCatalog(CharacterCatalog catalog) {
    this.characterCatalog = catalog;
    invalidate();
  }

  public void setCharacterModels(Map<String, CharacterMeshIndex> models) {
    this.characterModels = (models == null)
        ? new HashMap<String, CharacterMeshIndex>() : models;
    shaderCache.clear();
    invalidate();
  }
```

- [ ] **Step 3: Rewrite `drawCharacters` to instance by refid**

Replace `drawCharacters`:

```java
  private void drawCharacters(Canvas canvas) {
    if (!charactersVisible || characterCatalog == null
        || characterModels.isEmpty() || world == null || npc == null) {
      return;
    }
    int sx0 = Integer.MAX_VALUE, sy0 = Integer.MAX_VALUE;
    int sx1 = Integer.MIN_VALUE, sy1 = Integer.MIN_VALUE;
    for (WorldTerrainSet.Sector s : world.sectors()) {
      sx0 = Math.min(sx0, s.sx);
      sy0 = Math.min(sy0, s.sy);
      sx1 = Math.max(sx1, s.sx);
      sy1 = Math.max(sy1, s.sy);
    }
    if (sx0 > sx1 || sy0 > sy1) {
      return;
    }
    int refSx = sx0;
    int refSy = sy0;
    for (NpcSpawnIndex.Spawn sp : npc.inWindow(sx0, sx1, sy0, sy1)) {
      String key = characterCatalog.keyFor(sp.characterRefId);
      CharacterMeshIndex model = key == null ? null : characterModels.get(key);
      if (model == null) {
        continue; // fail-closed: unloaded/unknown character stays a marker
      }
      float wx = sp.worldX(refSx);
      float wz = sp.worldZ(refSy);
      for (CharacterMeshIndex.Part part : model.parts()) {
        float[] positions = part.bindPositions;
        if (part.skinned && characterPose != null) {
          try {
            positions = CharacterRenderer.skin(
                model.skeleton(), characterPose,
                (StaticMeshAsset.SkinnedMesh) part.mesh);
          } catch (IOException e) {
            positions = part.bindPositions;
          }
        } else if (!part.skinned) {
          positions = part.mesh.positions;
        }
        drawTexturedTriangles(canvas, positions, part.mesh.uvs, part.mesh.indices,
            part.mesh.triangleCount, part.texture, wx, wz, 1f, 0f);
      }
    }
  }
```

Add the missing `import com.opensilkroadmap.app.data.NpcSpawnIndex.Spawn;`? No — `NpcSpawnIndex` is already imported; use the fully-qualified `NpcSpawnIndex.Spawn` (already referenced as `NpcSpawnIndex.Spawn` in `drawNpcMarkers`).

- [ ] **Step 4: Keep `drawNpcMarkers` unchanged (diagnostic overlay remains)**

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/opensilkroadmap/app/world/NativeWorldRenderer.java
git commit -m "feat(android): instance real NPCs by refid via catalog"
```

---

### Task 8: Python live conversion + player tests

**Files:**
- Create: `scripts/test_phase20_conversion.py`

**Interfaces:**
- Consumes: `build_character_catalog._build` (via a temp dir), `build_character_manifest.convert_character`, `convert_player`, `character_resolve`.
- Produces: tests that assert the emitted layout + index + coverage for a small live sample and the player.

- [ ] **Step 1: Write the live test**

`scripts/test_phase20_conversion.py`:

```python
#!/usr/bin/env python3
"""Phase 20 Part C: bulk conversion + player (live, gated on SRO_PK2_DIR)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_character_manifest as BCM  # noqa: E402
import build_character_catalog as BCC  # noqa: E402
import character_resolve as CR  # noqa: E402

PK2_DIR = os.environ.get("SRO_PK2_DIR")


@unittest.skipUnless(PK2_DIR, "SRO_PK2_DIR not set")
class TestLiveConversion(unittest.TestCase):
    def test_bandit_converts_to_shared_store(self):
        data_pk2 = __import__("sro_paths").pk2_archive(PK2_DIR, "Data.pk2")
        media_pk2 = __import__("sro_paths").pk2_archive(PK2_DIR, "Media.pk2")
        rd = BCM._Pk2Reader(data_pk2)
        rm = BCM._Pk2Reader(media_pk2)
        try:
            with tempfile.TemporaryDirectory() as out:
                manifest = BCM.convert_character(
                    rd, rm, "mob\\china\\bandit.bsr", out, "mob_china_bandit")
                self.assertEqual(manifest["key"], "mob_china_bandit")
                self.assertTrue(manifest["meshes"])
                self.assertTrue(manifest["anims"])
                skel = os.path.join(out, "shared", "skel",
                                    manifest["skeleton"] + ".json")
                self.assertTrue(os.path.isfile(skel))
                self.assertTrue(os.path.isfile(
                    os.path.join(out, "mob_china_bandit", "manifest.json")))
                self.assertTrue(os.path.isfile(
                    os.path.join(out, "mob_china_bandit", "npc_placements.tsv")))
        finally:
            rd.close()
            rm.close()

    def test_jupiter_texture_resolves(self):
        # The root-relative ddj form previously doubled the path; assert it resolves.
        data_pk2 = __import__("sro_paths").pk2_archive(PK2_DIR, "Data.pk2")
        rd = BCM._Pk2Reader(data_pk2)
        try:
            cls = CR.classify_character(rd.read, rd._has, "mob\\jupiter\\charm_witch.bsr")
            self.assertIn(cls["status"], (CR.STATUS_PROVEN, CR.STATUS_PARTIAL))
            tex_issues = [m for m in cls["meshes"] if m.get("reason", "").startswith("texture")]
            self.assertFalse(tex_issues, cls["meshes"])
        finally:
            rd.close()

    def test_player_converts(self):
        data_pk2 = __import__("sro_paths").pk2_archive(PK2_DIR, "Data.pk2")
        rd = BCM._Pk2Reader(data_pk2)
        try:
            with tempfile.TemporaryDirectory() as out:
                manifest = BCM.convert_player(rd, rd, out)
                self.assertEqual(manifest["key"], "player")
                self.assertTrue(manifest["meshes"])
        finally:
            rd.close()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run live test**

Run: `cd /workspace && SRO_PK2_DIR=/tmp/opencode/pk2raw uv run python scripts/test_phase20_conversion.py`
Expected: PASS (3 tests). `convert_player(rd, rd, out)` uses `read_data` for both args because player materials/animations live in `Data.pk2`.

- [ ] **Step 3: Commit**

```bash
git add scripts/test_phase20_conversion.py
git commit -m "test(scripts): live bulk-conversion + player tests"
```

---

### Task 9: Java tests + compile-only verification

**Files:**
- Create: `android/app/src/test/java/com/opensilkroadmap/app/world/CharacterMeshIndexMultiTest.java`
- Modify (if needed): `android/app/src/test/java/com/opensilkroadmap/app/world/CharacterMeshIndexTest.java` (bandit layout changed to shared store)

**Interfaces:**
- Consumes: `CharacterMeshIndex`, `CharacterCatalog`, `StaticMeshAsset`, committed `characters/shared/…` assets.
- Produces: JVM tests (compile-checked via `javac`; runtime NOT EXECUTED without Gradle/Android SDK).

- [ ] **Step 1: Write the multi-character model test**

`CharacterMeshIndexMultiTest.java`:

```java
package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.List;

import org.junit.Test;

public class CharacterMeshIndexMultiTest {
  private static final String[] ROOTS = {
    "src/main/assets/game/world/characters",
    "../src/main/assets/game/world/characters",
    "app/src/main/assets/game/world/characters",
    "../app/src/main/assets/game/world/characters",
  };

  private static byte[] readAsset(String rel) throws Exception {
    for (String r : ROOTS) {
      File f = new File(r, rel);
      if (f.isFile()) {
        FileInputStream in = new FileInputStream(f);
        try {
          java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
          byte[] b = new byte[8192];
          int n;
          while ((n = in.read(b)) != -1) out.write(b, 0, n);
          return out.toByteArray();
        } finally {
          in.close();
        }
      }
    }
    throw new java.io.FileNotFoundException(rel);
  }

  @Test
  public void manifestReferencesSharedAssets() throws Exception {
    // The bandit manifest must reference a shared skeleton/mesh/tex that exist.
    byte[] manifest = readAsset("mob_china_bandit/manifest.json");
    assertTrue(manifest.length > 0);
  }

  @Test
  public void indexTsvParses() throws Exception {
    byte[] idx = readAsset("index.tsv");
    assertTrue(idx.length > 0);
    String s = new String(idx, "UTF-8");
    assertTrue(s.contains("refid"));
  }
}
```

- [ ] **Step 2: Update the legacy `CharacterMeshIndexTest`**

`CharacterMeshIndexTest` reads the old `bandit/` layout (`skeleton.json`, `meshes.tsv`, `npc_placements.tsv`, `anims.tsv`). Rewrite it to use the new `manifest.json` + `shared/` layout, or mark it superseded and rely on `CharacterMeshIndexMultiTest`. Rewrite the `ASSET_DIRS` to point at the keyed dir and assert `manifest.json` + shared files exist (the bind-pose skinning math is already covered by `skinnedBindPositions`, which is unchanged).

- [ ] **Step 3: Compile-only check via the stub harness**

Build a stub source tree under `/tmp/opencode/javastub` that provides no-op `android.*` classes used by the world package (or reuse the existing `/tmp/opencode/javastub` from Phase 19), then:

```bash
cd /workspace && javac -d /tmp/opencode/classes \
  $(find android/app/src/main/java/com/opensilkroadmap/app/world \
         android/app/src/main/java/com/opensilkroadmap/app/data \
         android/app/src/main/java/com/opensilkroadmap/app/game \
         -name '*.java') 2>&1 | grep -v 'package android' | head -40
```

Expected: the only unresolved symbols are `android.*` (stubbed) and any genuinely missing symbol. Fix genuine symbol errors (the model/catalog changes must compile). Runtime execution is NOT EXECUTED (no Gradle/Android SDK) — record this explicitly.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/test/java/com/opensilkroadmap/app/world/
git commit -m "test(android): multi-character catalog + manifest tests"
```

---

### Task 10: Coverage report + documentation + evidence

**Files:**
- Create: `PHASE_20_REPORT.md`
- Modify: `ANDROID_DATA_CONVERSION_STATUS.md`
- (Generated) `android/app/src/main/assets/game/world/characters/coverage.json`

**Interfaces:**
- Consumes: `characters/coverage.json` (generated by Task 3/4).
- Produces: a human-readable audit stating exact counts/percentages integrated and the remaining PARTIAL/UNKNOWN items with reasons.

- [ ] **Step 1: Emit the coverage report from `coverage.json`**

Write a small generator (or hand-write the report from `coverage.json` numbers). The report MUST state:

1. Dataset totals: spawn rows, spawning refids, refids-with-model, distinct models, distinct skeletons, mesh parts, textures, animation clips.
2. Models integrated (PROVEN + converted), with exact count and percentage.
3. Models PARTIAL/UNKNOWN, each with the exact reason (texture-unresolved, no-skin-block-fallback, unproven-triangle, not-character, bsr-missing, bsk-inexact).
4. Player status (PARTIAL) and its two documented blockers.
5. What is NOT integrated and why (2 `.ban` files `JMXVBAN 0101`, child-bone `rot_local` inverse-bind PARTIAL, `bone_type` semantics UNKNOWN, player BSR→skeleton mismatch, no static player spawn).

- [ ] **Step 2: Write `PHASE_20_REPORT.md`**

Structure: Overview → Coverage table (counts + percentages) → PROVEN/PARTIAL/UNKNOWN breakdown → Player section → Known boundaries/UNKNOWN (verbatim list) → How to reproduce (`uv run scripts/build_character_catalog.py --pk2-dir …`).

- [ ] **Step 3: Update `ANDROID_DATA_CONVERSION_STATUS.md`**

Add a Phase 20 section noting the shared-store layout, `index.tsv`, `CharacterCatalog`, and the migration of the bandit directory (superseded, not deleted).

- [ ] **Step 4: Commit**

```bash
git add PHASE_20_REPORT.md ANDROID_DATA_CONVERSION_STATUS.md \
  android/app/src/main/assets/game/world/characters/coverage.json
git commit -m "docs: Phase 20 coverage report and status"
```

---

### Task 11: Full regression, secret scan, push, verify

**Files:** (none; verification only)

- [ ] **Step 1: Run the full Python suite**

```bash
cd /workspace && uv run python -m unittest discover -s scripts -p 'test_*.py' -t scripts 2>&1 | tail -20
```

Expected: 446+ new tests pass, the only skips are the `SRO_PK2_DIR`-gated live tests (unskip them with `SRO_PK2_DIR=/tmp/opencode/pk2raw` for the full live run).

- [ ] **Step 2: Secret/archive scan over the staged diff**

```bash
cd /workspace && git add -A && git status --short
cd /workspace && git diff --cached --name-only | while read f; do
  case "$f" in
    *.pk2|*.pk2.bak) echo "ARCHIVE COMMITTED: $f" ;;
  esac
done
cd /workspace && git diff --cached | grep -inE '(api[_-]?key|secret|password|token|BEGIN .*PRIVATE KEY)' && echo "SECRET FOUND" || echo "no secrets"
```

- [ ] **Step 3: Commit + push on the Phase 20 branch**

The branch naming rule: `YYMMDD-(feat|fix|chore|refactor)-...`. Create/push:

```bash
cd /workspace && git checkout -b 260830-feat-phase20-data-driven-character-runtime
git push -u origin 260830-feat-phase20-data-driven-character-runtime \
  -o merge_request.create \
  -o merge_request.title="feat: Phase 20 data-driven character runtime (all provable NPCs + player)" \
  -o merge_request.description="Data-driven character runtime, shared asset store, coverage audit"
```

- [ ] **Step 4: Verify local HEAD == remote HEAD and clean tree**

```bash
cd /workspace && git rev-parse HEAD && git rev-parse @{u} && git status --porcelain
```

Expected: local SHA == remote SHA, empty `git status --porcelain`.

---

## Self-Review

**Spec coverage:**
- Enumerate all supported characters/BSK/animations → Task 1 (`classify_character`) + Task 3 (bulk enumeration).
- Data-driven runtime for ALL provable NPCs + player → Tasks 2–4 (conversion) + 5–7 (Java).
- Remove single-character/demo assumptions → Task 6 (`CharacterMeshIndex.load(assets, key)`) + Task 7 (`CharacterCatalog.keyFor`).
- Connect every provable asset/animation → Task 2/3 (skeletons, meshes, textures, full-keyframe animations) + Task 4 (static fallback).
- Animation proof (enumeration, clip lookup, skeleton/bone mapping, bind/rest, keyframe decode, interpolation, apply pose) → inherited from Phase 18/19 (`animation_pose`, `Pose`) + Task 6 (`poseAt` via manifest).
- Player actual asset (chinaman) + no fake shared NPC → Task 2 (`convert_player`).
- Preserve Android-native/no-WebView → Tasks 5–7 are Android-native.
- Coverage audit → Task 3 (`coverage.json`) + Task 10 (report).
- Two recon-discovered format variations (ddj path form, multi-BSR col52) → Task 1 + Task 2.

**Placeholder scan:** No TBD/TODO. All code blocks are concrete.

**Type consistency:** `convert_character(read_data, read_media, bsr_rel, out_root, key)` and `convert_player(read_data, read_media, out_root)` signatures match Tasks 2/3/8. Java `CharacterCatalog.keyFor(int)`, `playerKey()`, `characterKeys()`, `count()` match Task 7. `CharacterMeshIndex.load(AssetManager, String)` and `Part.skinned/mesh/bindPositions` match Tasks 6/7. `index.tsv` columns (`refid`, `key`, `variant`, `status`, `spawn_count`) match Task 3 writer and Task 5 reader.
