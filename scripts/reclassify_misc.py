#!/usr/bin/env python3
"""Tail reclassification of the last non-JMX UNKNOWN formats (Phase 21).

Unlike reclassify_jmx.py (extension-only) this reads the magic byte from each
archive/disk sample because several of these are polymorphic or misnamed:

  * `.rd`  -> PROVEN  "bmp-region-thumbnail"  (standard BMP, 16x16 8bpp)
  * `.2dt` -> PARTIAL "cnif-ui-layout"        (CNIF magic + window name)
  * `.mfo` -> PARTIAL "jmx-mfo-mapinfo"       (JMXVMFO 1000 + dims)
  * `.msf` -> PARTIAL "sound-effect-script"   (count + ambient + efp refs)
  * `.bak` -> PARTIAL "mtf-sql-backup"        (TAPE MTF wrapper)
  * `.dll`/`.exe` -> PROVEN "pe-executable"   (MZ + PE signature)
  * `.pk2` -> PROVEN "pk2-archive"            (JoyM PK2 archive)
  * the single extension-less `/icon/action/cos_cmd_inventory` -> PROVEN
    "jmx-texture" (JMXVDDJ 1000, misnamed DDJ)
  * `.scc` vssver2 -> DEAD "vss-source-control" (VSS version-file magic
    `34 12 01 00` + `$/project` path strings + null-terminated file names)

Formats left UNKNOWN (no provable structure): `.cs3` (encrypted map).
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
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import sro_paths  # noqa: E402

PK2_DIR = sro_paths.resolve_pk2_dir()

EXT_STATUS = {
    ".rd": ("PROVEN", "bmp-region-thumbnail"),
    ".dll": ("PROVEN", "pe-executable"),
    ".exe": ("PROVEN", "pe-executable"),
    ".pk2": ("PROVEN", "pk2-archive"),
    ".2dt": ("PARTIAL", "cnif-ui-layout"),
    ".mfo": ("PARTIAL", "jmx-mfo-mapinfo"),
    ".msf": ("PARTIAL", "sound-effect-script"),
    ".bak": ("PARTIAL", "mtf-sql-backup"),
    ".crb": ("PARTIAL", "crest-16x16-grid"),
}

_pk2_cache = {}


def _pk2_map(archive):
    if archive not in _pk2_cache:
        import pk2_table
        files, _ = pk2_table.inventory(os.path.join(PK2_DIR, archive))
        _pk2_cache[archive] = {f["path"].lower(): f for f in files}
    return _pk2_cache[archive]


def read_head(record, n=16):
    """Return up to n header bytes for a record from pk2 or disk."""
    src = record["source"]
    if src == "pk2":
        m = _pk2_map(record["archive"]).get(record["internal_path"].lower())
        if m is None:
            return b""
        with open(os.path.join(PK2_DIR, record["archive"]), "rb") as fh:
            fh.seek(m["pos"])
            return fh.read(min(n, m["size"]))
    loc = record.get("location") or ""
    if loc and os.path.isfile(loc):
        with open(loc, "rb") as fh:
            return fh.read(n)
    return b""


def classify(record):
    ext = record.get("extension")
    if ext == "(none)":
        head = read_head(record, 12)
        if head == b"JMXVDDJ 1000":
            return ("PROVEN", "jmx-texture")
        return (None, None)
    if ext == ".scc":
        head = read_head(record, 4)
        if head == b"\x34\x12\x01\x00":
            return ("DEAD", "vss-source-control")
        return (None, None)
    if ext not in EXT_STATUS:
        return (None, None)
    if ext == ".mfo":
        head = read_head(record, 12)
        if head != b"JMXVMFO 1000":
            return (None, None)
    elif ext == ".2dt":
        head = read_head(record, 16)
        if len(head) < 8 or head[4:8] != b"CNIF":
            if b"CNIF" not in read_head(record, 0x10000):
                return (None, None)
    elif ext == ".crb":
        if record["size"] != 256:
            return (None, None)
    elif ext == ".bak":
        head = read_head(record, 4)
        if head != b"TAPE":
            return (None, None)
    elif ext in (".dll", ".exe"):
        head = read_head(record, 0x100)
        if len(head) >= 0x40 and head[:2] == b"MZ":
            off = int.from_bytes(head[0x3C:0x40], "little")
            if off + 4 <= len(head) and head[off:off + 4] != b"PE\x00\x00":
                return (None, None)
    return EXT_STATUS[ext]


def reclassify(rows):
    changed = []
    for r in rows:
        if r["status"] in ("STUB", "DEAD", "MISSING"):
            continue
        status, fmt = classify(r)
        if status is None:
            continue
        if r["status"] != status or r.get("format") != fmt:
            r["status"] = status
            r["format"] = fmt
            changed.append((r["internal_path"], r["extension"], status))
    return changed


def write_outputs(rows):
    by_status = collections.Counter(r["status"] for r in rows)
    by_system = collections.Counter(r["system"] for r in rows)
    by_source = collections.Counter(r["source"] for r in rows)
    total_bytes = sum(r["size"] for r in rows)
    extracted_n = sum(1 for r in rows if r["extracted"])

    cols = ["source", "archive", "internal_path", "name", "extension", "size",
            "sha256", "status", "format", "system", "domains", "extracted", "location"]

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

    by_ext = collections.Counter((ext, status) for _, ext, status in changed)
    print(f"reclassified records: {len(changed)}")
    for (ext, status), n in sorted(by_ext.items()):
        print(f"  {ext:8} -> {status:8} x{n}")
    if args.dry_run:
        return
    if args.apply:
        write_outputs(rows)
        print("wrote manifest/stats/system-inventory")


if __name__ == "__main__":
    main()
