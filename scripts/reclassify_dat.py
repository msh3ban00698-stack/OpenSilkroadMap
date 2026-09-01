#!/usr/bin/env python3
"""Targeted `.dat` reclassification (read-only on archives).

Loads the existing SOURCE_CORPUS_MANIFEST.json, re-classifies ONLY the `.dat`
records by their leading bytes (via dat_families.classify_dat), and rewrites the
manifest/stats/system-inventory outputs with recomputed counts. All other
records are preserved byte-for-byte. No full re-scan is performed.

Status/format mapping per family:
    bmp        PROVEN  "bmp"
    jmxvimg    PROVEN  "jmxvimg"
    ainavdata  PARTIAL "ainavdata"
    palette    PROVEN  "palette"
    hex-token  PROVEN  "hex-token"
    config     PARTIAL "config"
    ddj        PROVEN  "ddj"
    unknown    UNKNOWN "binary-data" (unchanged)
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import dat_families  # noqa: E402
import sro_paths  # noqa: E402

ROOT = SCRIPTS.parent
PK2_DIR = sro_paths.resolve_pk2_dir()
CLIENT_EXTRACT = sro_paths.resolve_client_extract_dir()

FAMILY_MAP = {
    "bmp": ("PROVEN", "bmp"),
    "jmxvimg": ("PROVEN", "jmxvimg"),
    "ainavdata": ("PARTIAL", "ainavdata"),
    "palette": ("PROVEN", "palette"),
    "hex-token": ("PROVEN", "hex-token"),
    "config": ("PARTIAL", "config"),
    "plugin": ("PROVEN", "plugin"),
    "ddj": ("PROVEN", "ddj"),
    "unknown": ("UNKNOWN", "binary-data"),
}

_pk2_pos_cache = {}


def _pk2_pos_map(archive):
    if archive not in _pk2_pos_cache:
        import pk2_table
        files, _ = pk2_table.inventory(os.path.join(PK2_DIR, archive))
        _pk2_pos_cache[archive] = {f["path"]: f for f in files}
    return _pk2_pos_cache[archive]


def read_header(record):
    """Return up to 2048 header bytes for a record (full for small files,
    bounded for large) without materializing the whole body."""
    limit = min(2048, record["size"])
    src = record["source"]
    archive = record["archive"]
    path = record["internal_path"]
    if src == "pk2":
        m = _pk2_pos_map(archive)
        e = m.get(path)
        if e is None:
            return b""
        with open(os.path.join(PK2_DIR, archive), "rb") as fh:
            fh.seek(e["pos"])
            return fh.read(min(limit, e["size"]))
    if src == "filesystem":
        loc = record["location"]
        if loc and os.path.isfile(loc):
            with open(loc, "rb") as fh:
                return fh.read(limit)
        return b""
    if src == "container":
        loc = os.path.join(CLIENT_EXTRACT, path)
        if os.path.isfile(loc):
            with open(loc, "rb") as fh:
                return fh.read(limit)
        return b""
    return b""


def reclassify(rows):
    changed = []
    for r in rows:
        if r.get("extension") != ".dat":
            continue
        header = read_header(r)
        fam = dat_families.classify_dat(header, r["internal_path"])["family"]
        status, fmt = FAMILY_MAP.get(fam, ("UNKNOWN", "binary-data"))
        if r["status"] != status or r["format"] != fmt:
            r["status"] = status
            r["format"] = fmt
            changed.append((r["internal_path"], fam, status))
        if fam == "palette" and r["system"] == "unknown":
            r["system"] = "ui"
    return changed


def write_outputs(rows):
    by_status = collections.Counter(r["status"] for r in rows)
    by_system = collections.Counter(r["system"] for r in rows)
    by_source = collections.Counter(r["source"] for r in rows)
    total_bytes = sum(r["size"] for r in rows)
    extracted_n = sum(1 for r in rows if r["extracted"])

    cols = ["source", "archive", "internal_path", "name", "extension", "size",
            "sha256", "status", "format", "system", "domains", "extracted", "location"]

    # manifest json + tsv
    with open(ROOT / "SOURCE_CORPUS_MANIFEST.json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh)
        fh.write("\n")
    with open(ROOT / "SOURCE_CORPUS_MANIFEST.tsv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            row = [json.dumps(r[c], ensure_ascii=False) if c == "domains" else r[c] for c in cols]
            while row and row[-1] == "":
                row.pop()
            w.writerow(row)

    # stats (preserve known_missing / archive / container census)
    stats = json.load(open(ROOT / "SOURCE_CORPUS_STATS.json", encoding="utf-8"))
    by_status["MISSING"] = len(stats.get("known_missing", []))
    stats["reconciliation"] = dict(by_status)
    stats["by_source"] = dict(by_source)
    stats["by_system"] = dict(sorted(by_system.items(), key=lambda kv: -kv[1]))
    stats["totals"]["indexed_files"] = len(rows)
    stats["totals"]["total_bytes"] = total_bytes
    stats["totals"]["extracted_files"] = extracted_n
    stats["totals"]["indexed_only_files"] = len(rows) - extracted_n
    with open(ROOT / "SOURCE_CORPUS_STATS.json", "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=1)
        fh.write("\n")

    # system inventory
    inv = {}
    for r in rows:
        k = (r["system"], r["source"])
        inv.setdefault(k, {"count": 0, "bytes": 0})
        inv[k]["count"] += 1
        inv[k]["bytes"] += r["size"]
    with open(ROOT / "SOURCE_SYSTEM_INVENTORY.json", "w", encoding="utf-8") as fh:
        json.dump({
            "phase": "phase29-source-parity",
            "by_system": {k[0]: v for k, v in sorted(inv.items())},
            "by_system_source": {f"{k[0]}|{k[1]}": v for k, v in sorted(inv.items())},
            "totals": stats["totals"],
            "reconciliation": stats["reconciliation"],
        }, fh, indent=1)
        fh.write("\n")
    with open(ROOT / "SOURCE_SYSTEM_INVENTORY.tsv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["system", "source", "count", "bytes"])
        for (sys_name, src), v in sorted(inv.items()):
            w.writerow([sys_name, src, v["count"], v["bytes"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "SOURCE_CORPUS_MANIFEST.json"))
    ap.add_argument("--apply", action="store_true", help="write back manifest/stats")
    ap.add_argument("--dry-run", action="store_true", help="print changes only")
    args = ap.parse_args()

    rows = json.load(open(args.manifest, encoding="utf-8"))
    changed = reclassify(rows)

    print(f"reclassified .dat records: {len(changed)}")
    for path, fam, status in changed:
        print(f"  {path:45} -> {fam:10} {status}")
    if args.dry_run:
        return
    if args.apply:
        write_outputs(rows)
        print("wrote manifest/stats/system-inventory")


if __name__ == "__main__":
    main()
