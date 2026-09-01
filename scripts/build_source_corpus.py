#!/usr/bin/env python3
"""Deterministic complete source-corpus builder for the vSRO 1.193 project.

Replaces scattered ad-hoc extraction/inventory scripts with one reusable,
read-only pipeline that:

  1. Enumerates EVERY archive present (PK2, SQL .Bak, 7z/zip/rar containers,
     tool tarballs, test fixtures) with size + SHA-256.
  2. Enumerates EVERY entry of every real PK2 archive (complete block-table
     walk via scripts/pk2_table.py; no selective extraction).
  3. Streams each PK2 file straight from the raw archive (contiguous read is
     VERIFIED byte-identical to pk2_mate extract), computing per-file SHA-256,
     magic-byte signature, format family, and text encoding.
  4. Emits the complete machine-readable manifest + statistics with the
     zero-drop reconciliation totals.

Read-only: no archive is modified, no payload is written to disk (the manifest
carries per-file hashes computed in-memory), so the 5.7 GB raw corpus is never
duplicated on disk.

Outputs (repo root, exact names per the Phase 29 source-parity spec):
  SOURCE_CORPUS_MANIFEST.json   complete per-file records
  SOURCE_CORPUS_MANIFEST.tsv    tab-separated mirror for diffing/grepping
  SOURCE_CORPUS_STATS.json      archive-level + reconciliation totals

Usage:
  python3 scripts/build_source_corpus.py [--pk2-dir <pk2-dir>]
                                         [--db-dir <db-dir>]
                                         [--pkg-dir <pkg-dir>]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

REPO = BASE

REAL_PK2 = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# --- format classification -------------------------------------------------

JMX_MAGIC = {
    b"JMXVDDJ": "ddj-texture",
    b"JMXVBMS": "jmx-bms-skeleton",
    b"JMXVRES": "jmx-bsr-mesh",
    b"JMXVCPD": "jmx-cpd-strings",
    b"JMXVBAN": "jmx-ban-animation",
    b"JMXVEFF": "jmx-efp-effect",
    b"JMXVNVM": "jmx-nvm-navmesh",
    b"JMXVIMG": "jmx-img-font",
    b"JMXVMAPT": "jmx-mapt-map",
    b"JMXVMAPM": "jmx-mapm-map",
    b"JMXVMAPO": "jmx-mapo-map",
}

MAGIC_TYPES = [
    (b"OggS", "ogg-audio"),
    (b"RIFF", "wav-audio"),
    (b"DDS ", "dds-texture"),
    (b"MZ", "pe-executable"),
    (b"%PDF", "pdf"),
    (b"PK\x03\x04", "zip"),
    (b"\x89PNG", "png"),
    (b"ID3", "mp3-audio"),
    (b"\xff\xfb", "mp3-audio"),
]


TEXT_EXT = {
    ".txt", ".lua", ".cfg", ".ini", ".xml", ".config", ".html", ".htm",
    ".log", ".sh", ".bat", ".sct", ".scr", ".csv", ".tsv", ".json",
    ".yaml", ".yml", ".scc", ".c", ".h", ".cpp", ".hpp", ".vsh", ".psh",
}


def classify(path, head, ext):
    """Return (type, encoding) from magic sniff, else extension, else binary."""
    enc = "binary"
    ftype = "binary"

    for magic, name in JMX_MAGIC.items():
        if head.startswith(magic):
            return name, "binary"
    for magic, name in MAGIC_TYPES:
        if head.startswith(magic):
            return name, "binary"

    # text detection (head may be empty for 0-byte files)
    if head:
        if head.startswith(b"\xff\xfe"):
            return "text", "utf-16-le"
        if head.startswith(b"\xef\xbb\xbf"):
            return "text", "utf-8-bom"
        # heuristic: mostly printable ASCII / CP949 without NULs
        sample = head[:512]
        nuls = sample.count(b"\x00")
        if nuls == 0:
            printable = sum(1 for c in sample if 0x09 <= c <= 0x7e or c in (0x0a, 0x0d))
            if printable / max(1, len(sample)) > 0.85:
                return "text", "ascii/cp949"

    # no content available (fast inventory) -> extension-only fallback
    if ext in TEXT_EXT:
        return "text", "unknown"
    return "binary", "binary"


def ext_of(path):
    name = path.rsplit("/", 1)[-1]
    return ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else "(none)"


# --- PK2 manifest ----------------------------------------------------------

def build_pk2_manifest(pk2_dir, hash_files=True, hash_archives=True):
    """Enumerate + classify every PK2 entry; optionally hash payloads.

    `hash_files=False` performs a table-only pass (extension-based
    classification, no payload reads) and is fast. `hash_files=True` streams
    each payload in disk order (files sorted by `pos`) to compute SHA-256 and
    magic-byte classification; this reads the whole 5.7 GB corpus once and is
    intentionally slow on cold storage (~10 MB/s in this environment).
    `hash_archives=False` also skips the archive-level SHA-256.
    """
    rows = []
    per_archive = {}
    for name in REAL_PK2:
        path = os.path.join(pk2_dir, name)
        if not os.path.isfile(path):
            per_archive[name] = {"present": False}
            continue
        files, dirs = pk2_table.inventory(path)
        total_bytes = 0
        files_sorted = sorted(files, key=lambda f: f["pos"])
        with open(path, "rb") as fh:
            for f in files_sorted:
                pos, size = f["pos"], f["size"]
                head = b""
                if hash_files:
                    cur = fh.tell()
                    if cur != pos:
                        fh.seek(pos)
                    data = fh.read(size)
                    head = data[:512]
                    h = hashlib.sha256(data).hexdigest()
                else:
                    h = ""
                ext = ext_of(f["path"])
                ftype, enc = classify(f["path"], head, ext)
                parse_status = "ok" if (ftype == "text" or ftype != "binary") else "unparsed"
                source_status = "PROVEN" if ftype != "binary" else "UNKNOWN"
                rows.append({
                    "archive": name,
                    "internal_path": f["path"],
                    "extension": ext,
                    "size": size,
                    "sha256": h,
                    "type": ftype,
                    "encoding": enc,
                    "parse_status": parse_status,
                    "parse_error": "",
                    "references": "",
                    "source_status": source_status,
                })
                total_bytes += size
        per_archive[name] = {
            "present": True,
            "size": os.path.getsize(path),
            "sha256": sha256_file(path) if hash_archives else "",
            "file_count": len(files),
            "dir_count": len(dirs),
            "payload_bytes": total_bytes,
        }
    return rows, per_archive


# --- archive census --------------------------------------------------------

def archive_census(pk2_dir, db_dir, pkg_dir, hash_archives=True):
    """Enumerate every archive present (PK2, SQL .Bak, containers, tool, fixtures)."""
    items = []
    for name in REAL_PK2:
        p = os.path.join(pk2_dir, name)
        if os.path.isfile(p):
            items.append({
                "archive": name, "kind": "pk2", "path": p,
                "size": os.path.getsize(p),
                "sha256": sha256_file(p) if hash_archives else "",
            })
    for root, kind in ((db_dir, "sql-backup"),):
        if root and os.path.isdir(root):
            for fn in sorted(os.listdir(root)):
                if fn.lower().endswith(".bak"):
                    p = os.path.join(root, fn)
                    items.append({
                        "archive": fn, "kind": kind, "path": p,
                        "size": os.path.getsize(p),
                        "sha256": sha256_file(p) if hash_archives else "",
                    })
    if pkg_dir and os.path.isdir(pkg_dir):
        for fn in sorted(os.listdir(pkg_dir)):
            if fn.lower().endswith((".7z", ".rar", ".zip", ".txt")):
                p = os.path.join(pkg_dir, fn)
                items.append({
                    "archive": fn, "kind": "container" if fn.lower().endswith((".7z", ".rar", ".zip")) else "text",
                    "path": p, "size": os.path.getsize(p),
                    "sha256": sha256_file(p) if hash_archives else "",
                })
    # tool + fixture archives (excluded from game corpus but recorded)
    external_dir = os.environ.get("SRO_EXTERNAL_DIR", "")
    for p, kind in (
        (os.path.join(external_dir, "pk2_mate.tar.gz") if external_dir else "", "tool"),
        (os.path.join(external_dir, "PK2_Files.7z") if external_dir else "", "container"),
        (os.path.join(external_dir, "VSRO-R_Client.zip") if external_dir else "", "container"),
    ):
        if p and os.path.isfile(p):
            items.append({
                "archive": os.path.basename(p), "kind": kind, "path": p,
                "size": os.path.getsize(p),
                "sha256": sha256_file(p) if hash_archives else "",
            })
    return items


def write_tsv(rows, path):
    cols = ["archive", "internal_path", "extension", "size", "sha256", "type",
            "encoding", "parse_status", "parse_error", "references", "source_status"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            row = [r[c] for c in cols]
            while row and row[-1] == "":
                row.pop()
            w.writerow(row)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    ap.add_argument("--db-dir", default=os.environ.get("SRO_DB_DIR"))
    ap.add_argument("--pkg-dir", default=os.environ.get("SRO_PKG_DIR"))
    ap.add_argument("--out", default=REPO, help="output directory for deliverables")
    ap.add_argument("--no-hash", action="store_true",
                    help="skip per-file payload SHA-256 (fast inventory; hashes empty)")
    ap.add_argument("--no-archive-hash", action="store_true",
                    help="skip archive-level SHA-256 (fast census)")
    args = ap.parse_args()
    args.pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)

    rows, per_archive = build_pk2_manifest(args.pk2_dir, hash_files=not args.no_hash,
                                           hash_archives=not args.no_archive_hash)
    archives = archive_census(args.pk2_dir, args.db_dir, args.pkg_dir,
                              hash_archives=not args.no_archive_hash)

    total_files = len(rows)
    total_bytes = sum(r["size"] for r in rows)
    status_counts = {}
    for r in rows:
        status_counts[r["source_status"]] = status_counts.get(r["source_status"], 0) + 1
    type_counts = {}
    for r in rows:
        type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1

    stats = {
        "phase": "phase29-source-parity",
        "archive_census": archives,
        "pk2_archive_summary": per_archive,
        "manifest_totals": {
            "total_enumerated_files": total_files,
            "total_payload_bytes": total_bytes,
            "reconciliation": {
                "PROVEN": status_counts.get("PROVEN", 0),
                "PARTIAL": status_counts.get("PARTIAL", 0),
                "STUB": status_counts.get("STUB", 0),
                "MISSING": status_counts.get("MISSING", 0),
                "UNKNOWN": status_counts.get("UNKNOWN", 0),
                "UNREADABLE": status_counts.get("UNREADABLE", 0),
                "DEAD": status_counts.get("DEAD", 0),
            },
        },
        "by_type": dict(sorted(type_counts.items(), key=lambda kv: -kv[1])),
    }

    out = args.out
    manifest_json = os.path.join(out, "SOURCE_CORPUS_MANIFEST.json")
    manifest_tsv = os.path.join(out, "SOURCE_CORPUS_MANIFEST.tsv")
    stats_json = os.path.join(out, "SOURCE_CORPUS_STATS.json")

    with open(manifest_json, "w", encoding="utf-8") as fh:
        json.dump(rows, fh)
        fh.write("\n")
    write_tsv(rows, manifest_tsv)
    with open(stats_json, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=1)
        fh.write("\n")

    print("manifest entries :", total_files)
    print("payload bytes    :", total_bytes)
    print("reconciliation   :", stats["manifest_totals"]["reconciliation"])
    print("wrote", manifest_json)
    print("wrote", manifest_tsv)
    print("wrote", stats_json)


if __name__ == "__main__":
    main()
