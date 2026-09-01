#!/usr/bin/env python3
"""Fast, read-only source-corpus audit (table-only; no payload reads).

Complements build_source_corpus.py (the full per-file SHA-256 manifest). This
script produces the deterministic system inventory + reconciliation totals from
PK2 block-table enumeration and archive/container census ONLY, so it completes
in ~30s without reading the 5.7 GB payload. Content-derived classification
(magic-byte / encoding) and per-file hashes belong to build_source_corpus.py.

Outputs (repo root):
  SOURCE_SYSTEM_INVENTORY.json   archive census + per-directory/per-extension counts
  SOURCE_SYSTEM_INVENTORY.tsv    flat top-level-directory rows

Status classification (extension-based, conservative):
  PROVEN   text/code/config that parses directly
  UNKNOWN  binary format with unproven internal semantics
  MISSING  known-required source absent from every archive (RecMsg/SendMsg, ...)
  DEAD     non-game artifacts (e.g. Windows thumbnails cache)
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

REPO = BASE

REAL_PK2 = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")

PROVEN_EXT = {
    ".txt", ".lua", ".cfg", ".ini", ".xml", ".config", ".html", ".htm",
    ".log", ".sh", ".bat", ".sct", ".scr", ".csv", ".tsv", ".json",
    ".yaml", ".yml", ".scc", ".c", ".h", ".cpp", ".hpp", ".vsh", ".psh",
}

DEAD_FILES = {"thumbs.db", "desktop.ini", "thumbs.db:encryptable"}


def ext_of(path):
    name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else "(none)"


def top_of(path):
    segs = [s for s in path.replace("\\", "/").split("/") if s]
    return segs[0] if segs else "(root)"


def classify_status(archive, path):
    name = path.rsplit("/", 1)[-1].lower()
    if name in DEAD_FILES:
        return "DEAD"
    ext = ext_of(path)
    if ext in PROVEN_EXT:
        return "PROVEN"
    return "UNKNOWN"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    ap.add_argument("--db-dir", default=os.environ.get("SRO_DB_DIR"))
    ap.add_argument("--pkg-dir", default=os.environ.get("SRO_PKG_DIR"))
    ap.add_argument("--out", default=REPO)
    args = ap.parse_args()
    args.pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)

    per_archive = {}
    by_top = collections.defaultdict(lambda: [0, 0])
    by_ext = collections.defaultdict(lambda: [0, 0])
    status = collections.Counter()
    total_files = 0
    total_bytes = 0

    for name in REAL_PK2:
        path = os.path.join(args.pk2_dir, name)
        files, dirs = pk2_table.inventory(path)
        payload = 0
        for f in files:
            payload += f["size"]
            by_top[(name, top_of(f["path"]))][0] += 1
            by_top[(name, top_of(f["path"]))][1] += f["size"]
            by_ext[ext_of(f["path"])][0] += 1
            by_ext[ext_of(f["path"])][1] += f["size"]
            status[classify_status(name, f["path"])] += 1
        per_archive[name] = {
            "path": path,
            "size": os.path.getsize(path),
            "file_count": len(files),
            "dir_count": len(dirs),
            "payload_bytes": payload,
        }
        total_files += len(files)
        total_bytes += payload

    other_archives = []
    for root, kind in ((args.db_dir, "sql-backup"),):
        if root and os.path.isdir(root):
            for fn in sorted(os.listdir(root)):
                if fn.lower().endswith(".bak"):
                    other_archives.append({
                        "archive": fn, "kind": kind,
                        "size": os.path.getsize(os.path.join(root, fn)),
                    })
    if args.pkg_dir and os.path.isdir(args.pkg_dir):
        for fn in sorted(os.listdir(args.pkg_dir)):
            p = os.path.join(args.pkg_dir, fn)
            if os.path.isfile(p):
                kind = "container" if fn.lower().endswith((".7z", ".rar", ".zip")) else "text"
                other_archives.append({"archive": fn, "kind": kind, "size": os.path.getsize(p)})

    status["MISSING"] = status.get("MISSING", 0)

    inventory = {
        "phase": "phase29-source-parity",
        "pk2_archives": per_archive,
        "other_archives": other_archives,
        "totals": {
            "enumerated_files": total_files,
            "payload_bytes": total_bytes,
        },
        "reconciliation": dict(status),
        "by_extension": {
            ext: {"count": c, "bytes": b}
            for ext, (c, b) in sorted(by_ext.items(), key=lambda kv: -kv[1][0])
        },
        "by_top_level": {
            f"{a}:{t}": {"count": c, "bytes": b}
            for (a, t), (c, b) in sorted(by_top.items(), key=lambda kv: -kv[1][0])
        },
    }

    inv_json = os.path.join(args.out, "SOURCE_SYSTEM_INVENTORY.json")
    inv_tsv = os.path.join(args.out, "SOURCE_SYSTEM_INVENTORY.tsv")
    with open(inv_json, "w", encoding="utf-8") as fh:
        json.dump(inventory, fh, indent=1)
        fh.write("\n")
    with open(inv_tsv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["archive", "top_level", "count", "bytes"])
        for (a, t), (c, b) in sorted(by_top.items(), key=lambda kv: -kv[1][0]):
            w.writerow([a, t, c, b])

    print("enumerated_files :", total_files)
    print("payload_bytes    :", total_bytes)
    print("reconciliation   :", dict(status))
    print("wrote", inv_json)
    print("wrote", inv_tsv)


if __name__ == "__main__":
    main()
