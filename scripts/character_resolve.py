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
