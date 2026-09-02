#!/usr/bin/env python3
"""Fail-closed unique-once SN_ZONE labels from worldmap_localinfo.tsv.

Keeps only committed col3 values that start with SN_ZONE_ and appear exactly
once. Duplicate SN_ZONE codes, ddj paths, STORE_*, SN_NPC_*, and unknown
codes resolve to None. Does not invent names or consume teleportlink.tsv.
"""
from collections import Counter
from pathlib import Path


def _rows(path):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        out.append(line.split("\t"))
    return out


def load_unique_labels(path):
    rows = _rows(path)
    counts = Counter()
    first = {}
    for r in rows:
        if len(r) <= 5:
            continue
        code = r[3]
        if not code.startswith("SN_ZONE_"):
            continue
        counts[code] += 1
        if code not in first:
            first[code] = r
    labels = {}
    for code, n in counts.items():
        if n != 1:
            continue
        r = first[code]
        labels[code] = {
            "zone_id": int(r[1]),
            "zone_code": code,
            "name": r[4],
            "description": r[5],
        }
    return labels


def resolve(labels, code):
    if not code:
        return None
    return labels.get(code)
