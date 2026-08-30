#!/usr/bin/env python3
"""Phase 19 Part F animation candidate census (original archives).

Scans all PK2 archives for animation data using magic/header/record evidence,
NOT extension alone:
  * every .ban entry -> parse_ban_header; animation_data only when the
    JMXVBAN magic/version parses
  * every non-.ban entry -> first-bytes magic check; any JMXVBAN hit is a
    misclassified animation candidate (reported)
  * .bsk entries -> skeleton_data (skeleton, not animation)
  * everything else -> unrelated_binary

This module ships no PK2 reader; it operates on (entries, read_fn).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ban_decoder as BAN  # noqa: E402

ANIM_MAGIC = BAN.MAGIC  # b"JMXVBAN "

CANDIDATE_EXTS = (".ban", ".bka", ".bma", ".motion")


def _ext(path):
    return "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""


def classify_bytes(raw: bytes, path: str) -> dict:
    """Classify one file by its first bytes (no archive needed)."""
    head = raw[:8]
    ext = _ext(path)
    if head == ANIM_MAGIC:
        try:
            r = BAN.parse_ban(raw, keyframe_cap=0)
            return {
                "classification": "animation_data",
                "magic": r["header"]["magic"],
                "version": r["header"]["version"],
                "kpb": r["keyframes_per_bone"],
                "duration_ms": r["duration_ms"],
                "evidence": "JMXVBAN magic + byte-exact parse (%d bones, %d kpb)"
                            % (r["bone_count"], r["keyframes_per_bone"]),
            }
        except Exception as exc:  # noqa: BLE001
            version = raw[8:12].decode("ascii", "replace") if len(raw) >= 12 else "?"
            return {
                "classification": "animation_data_unparsed",
                "magic": head.decode("ascii", "replace"),
                "version": version,
                "evidence": "JMXVBAN magic v%s; full parse failed: %s"
                            % (version, exc),
            }
    if ext == ".bsk":
        return {"classification": "skeleton_data", "magic": raw[:12].hex(),
                "evidence": "extension .bsk (skeleton, not animation)"}
    if ext in CANDIDATE_EXTS:
        return {"classification": "motion_or_unknown", "magic": head.hex(),
                "evidence": "animation-like extension but no JMXVBAN magic"}
    return {"classification": "unrelated_binary", "magic": head.hex(),
            "evidence": "no animation magic; unrelated extension"}


def scan_candidates(entries, read_fn):
    """Scan all entries, classify each, and summarize. Returns a dict with
    counts, magic histogram, and per-class samples (capped)."""
    counts = {"animation_data": 0, "animation_data_unparsed": 0,
              "skeleton_data": 0, "motion_or_unknown": 0,
              "unrelated_binary": 0}
    magic_hist = {}
    version_hist = {}
    duration_buckets = {"lt_1000": 0, "1000_5000": 0, "gt_5000": 0}
    misclassified = []
    anomalies = []
    samples = []
    for e in entries:
        if e["size"] == 0:
            continue
        raw = read_fn(e)
        c = classify_bytes(raw, e["path"])
        counts[c["classification"]] += 1
        if c["classification"] == "animation_data":
            magic_hist[c["magic"]] = magic_hist.get(c["magic"], 0) + 1
            version_hist[c["version"]] = version_hist.get(c["version"], 0) + 1
            d = c["duration_ms"]
            bucket = "lt_1000" if d < 1000 else ("1000_5000" if d <= 5000 else "gt_5000")
            duration_buckets[bucket] += 1
        if c["classification"] != "unrelated_binary" or (
                not e["path"].lower().endswith(".ban")
                and c["classification"] == "animation_data"):
            misclassified.append(e["path"])
        if c["classification"] in ("animation_data_unparsed", "motion_or_unknown"):
            anomalies.append({
                "path": e["path"],
                "size": e["size"],
                "classification": c["classification"],
                "magic": c.get("magic"),
                "evidence": c.get("evidence", ""),
            })
        if c["classification"] != "unrelated_binary" and len(samples) < 64:
            samples.append({
                "path": e["path"],
                "size": e["size"],
                "classification": c["classification"],
                "magic": c.get("magic"),
                "version": c.get("version"),
                "kpb": c.get("kpb"),
                "duration_ms": c.get("duration_ms"),
            })
    return {
        "counts": counts,
        "magic_histogram": {k: v for k, v in sorted(magic_hist.items())},
        "version_histogram": {k: v for k, v in sorted(version_hist.items())},
        "duration_buckets": duration_buckets,
        "samples": samples,
        "anomalies": anomalies,
    }
