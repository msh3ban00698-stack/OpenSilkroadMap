#!/usr/bin/env python3
"""JMX-family and decodable binary reclassification (read-only on archives).

Reconciles the per-file `status` field of SOURCE_CORPUS_MANIFEST.json with the
verified findings in FORMAT_RESEARCH.md / DATA_FORMAT_CATALOG.md. The extension
-> status mapping below is backed by a committed, tested decoder (or a standard
codec) that produced real output from real samples in a prior phase. Every
format not listed here keeps its existing status (UNKNOWN is preserved rather
than guessed).

Mapping (extension -> status) and the evidence basis:
    .ddj  PROVEN   jmx_ddj.py + convert_ddjs.py + dds_decode.py (20-byte JMX wrapper + DDS)
    .ban  PROVEN   ban_decoder.py (full layout; 4,793/4,795 byte-exact)
    .bsk  PROVEN   bsk_decoder.py (full layout; 1,034/1,035 byte-exact)
    .bsr  PROVEN   bsr_decoder.py (full layout; path groups)
    .bmt  PROVEN   world_terrain.parse_bmt_entries (name + 18 f32 props + ddj + 7-byte tail)
    .cpd  PROVEN   cpd_decoder.py (compound manifest: name + .bsr component paths; 124/124 byte-exact)
    .m    PROVEN   world_terrain.py (97x97 height grid fully decoded, Phase 10)
    .o    PROVEN   o2_decoder.parse_o (28-byte record layout proven, 9 tests)
    .o2   PROVEN   o2_decoder.py (record layout proven, Phase 17, 12 tests)
    .wav  PROVEN   standard RIFF/WAVE PCM (audio pipeline)
    .ogg  PROVEN   standard OggS/Vorbis (audio pipeline)
    .tga  PROVEN   standard TGA (header verified)
    .bms  PARTIAL  bms_decoder.py (structure+vertex proven; skinning tail UNKNOWN)
    .dof  PARTIAL  dof_decoder.py (8-u32 section-offset header + .bsr/RN_ strings proven; per-section records UNKNOWN)
    .nvm  PARTIAL  jmx_nvm.py (structure proven; cell semantics UNKNOWN)
    .efp  PARTIAL  version tree proven; command-stream body UNKNOWN
    .t    PARTIAL  world_terrain.parse_t (header+size+tile2d refs proven; grid layout UNKNOWN)

Formats with confirmed magic but no committed production decoder remain
UNKNOWN (mfo, msf, 2dt, sfk). STUB/DEAD/MISSING and all
other statuses are left untouched.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent

EXT_STATUS = {
    ".ddj": "PROVEN",
    ".ban": "PROVEN",
    ".bsk": "PROVEN",
    ".bsr": "PROVEN",
    ".bmt": "PROVEN",
    ".cpd": "PROVEN",
    ".m": "PROVEN",
    ".o": "PROVEN",
    ".o2": "PROVEN",
    ".wav": "PROVEN",
    ".ogg": "PROVEN",
    ".tga": "PROVEN",
    ".bms": "PARTIAL",
    ".dof": "PARTIAL",
    ".nvm": "PARTIAL",
    ".efp": "PARTIAL",
    ".t": "PARTIAL",
}


def reclassify(rows):
    changed = []
    for r in rows:
        ext = r.get("extension")
        if ext not in EXT_STATUS:
            continue
        if r["status"] in ("STUB", "DEAD", "MISSING"):
            continue
        new_status = EXT_STATUS[ext]
        if r["status"] != new_status:
            r["status"] = new_status
            changed.append((r["internal_path"], ext, new_status))
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

    by_ext = collections.Counter(ext for _, ext, _ in changed)
    print(f"reclassified records: {len(changed)}")
    for ext, n in sorted(by_ext.items()):
        print(f"  {ext:6} -> {EXT_STATUS[ext]:8} x{n}")
    if args.dry_run:
        return
    if args.apply:
        write_outputs(rows)
        print("wrote manifest/stats/system-inventory")


if __name__ == "__main__":
    main()
