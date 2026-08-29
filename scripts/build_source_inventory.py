"""Generate the complete machine-readable inventory of the real VSRO-R 1.193
archives (Data.pk2 / Map.pk2 / Media.pk2 / Music.pk2 / Particles.pk2).

This is the Phase 11 deliverable for the "COMPLETE ORIGINAL DATA / ASSET
EXTRACTION" stage: every archived file is listed with its path, size, and byte
offset inside the (unencrypted) data area, cross-indexed by format-status
classification. It never modifies the source archives.

Format status per extension:
  VERIFIED    magic + payload decoded (a real converter produced output)
  PARSEABLE   magic confirmed, internal structure researched from samples
  TEXT        decodable plain-text/tab data (UTF-16LE / UTF-8 / cp949)
  UNKNOWN     magic absent/unconfirmed, no honest claim made

Usage:
    python3 scripts/build_source_inventory.py --pk2-dir <dir> [--out <dir>]

Writes COMPLETE_SOURCE_INVENTORY.json and COMPLETE_SOURCE_INVENTORY.md at the
repo root (or --out). Requires the real archives; pass --pk2-dir or set
SRO_PK2_DIR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import pk2_table  # noqa: E402

ARCHIVE_ORDER = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")

TEXT_EXTS = {"txt", "ini", "c", "vsh", "psh", "ifo"}

VERIFIED_EXTS = {"wav", "ogg", "tga", "tmp", "m", "o2"}

PARSEABLE_EXTS = {
    "ddj", "bms", "bsr", "nvm", "t", "ban", "o", "bmt", "efp",
    "cpd", "dof", "mfo", "2dt", "bsk", "sfk",
}

UNKNOWN_EXTS = {"dat", "scc", "msf", "db", "scc", "unknown"}


def ext_status(ext: str) -> str:
    if ext == "(none)":
        return "PARSEABLE"
    if ext in TEXT_EXTS:
        return "TEXT"
    if ext in VERIFIED_EXTS:
        return "VERIFIED"
    if ext in PARSEABLE_EXTS:
        return "PARSEABLE"
    return "UNKNOWN"


FINGERPRINT_BYTES = 1 << 20


def fingerprint_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read(FINGERPRINT_BYTES))
    return h.hexdigest()


def build(pk2_dir: Path, out_dir: Path) -> None:
    archives = []
    files_out = []
    ext_counts = {}
    ext_bytes = {}
    for name in ARCHIVE_ORDER:
        path = pk2_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"archive not found: {path}")
        files, dirs = pk2_table.inventory(str(path))
        archives.append({
            "name": name,
            "fingerprint_sha256_1mib": fingerprint_of(path),
            "bytes": path.stat().st_size,
            "files": len(files),
            "dirs": len(dirs),
        })
        ai = len(archives) - 1
        for f in files:
            files_out.append([ai, f["path"], f["size"], f["pos"]])
            ext = f["path"].rsplit(".", 1)[-1].lower() if "." in f["path"] else "(none)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
            ext_bytes[ext] = ext_bytes.get(ext, 0) + f["size"]

    files_out.sort(key=lambda r: (r[0], r[1]))
    extensions = {}
    for ext in sorted(ext_counts):
        extensions[ext] = {
            "count": ext_counts[ext],
            "bytes": ext_bytes[ext],
            "status": ext_status(ext),
        }

    doc = {
        "schema": "sro-source-inventory-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archive_base": str(pk2_dir),
        "archives": archives,
        "extensions": extensions,
        "files": files_out,
    }

    json_path = out_dir / "COMPLETE_SOURCE_INVENTORY.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    write_markdown(doc, out_dir)
    return doc


def write_markdown(doc: dict, out_dir: Path) -> None:
    lines = []
    lines.append("# Complete Source Inventory - vSRO 1.193 Archives")
    lines.append("")
    lines.append(
        f"Generated {doc['generated_utc']} from read-only PK2 table walk "
        f"(pk2_table.py, Blowfish table decrypt, default key). Archives: "
        f"`{doc['archive_base']}`."
    )
    lines.append("")
    total_files = sum(a["files"] for a in doc["archives"])
    total_bytes = sum(a["bytes"] for a in doc["archives"])
    lines.append(f"- Archives: {len(doc['archives'])}")
    lines.append(f"- Files total: {total_files}")
    lines.append(f"- Bytes total: {total_bytes:,}")
    lines.append("")
    lines.append("## Per archive")
    lines.append("")
    lines.append("| Archive | Files | Bytes | Fingerprint (1 MiB head) |")
    lines.append("|---|---:|---:|---|")
    for a in doc["archives"]:
        lines.append(
            f"| {a['name']} | {a['files']:,} | {a['bytes']:,} | `{a['fingerprint_sha256_1mib'][:16]}...` |"
        )
    lines.append("")
    lines.append("## Format census")
    lines.append("")
    lines.append("| Extension | Files | Bytes | Status |")
    lines.append("|---|---:|---:|---|")
    by_status = {}
    for ext, info in doc["extensions"].items():
        lines.append(f"| `{ext}` | {info['count']:,} | {info['bytes']:,} | {info['status']} |")
        by_status[info["status"]] = by_status.get(info["status"], 0) + info["count"]
    lines.append("")
    lines.append("## Status rollup")
    lines.append("")
    lines.append("| Status | Files |")
    lines.append("|---|---:|")
    for status in ("TEXT", "VERIFIED", "PARSEABLE", "UNKNOWN"):
        lines.append(f"| {status} | {by_status.get(status, 0):,} |")
    lines.append("")
    lines.append("See `DATA_FORMAT_CATALOG.md` for per-format evidence.")
    lines.append("")
    (out_dir / "COMPLETE_SOURCE_INVENTORY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    ap.add_argument("--out", default=str(REPO))
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    build(Path(args.pk2_dir), Path(args.out))


if __name__ == "__main__":
    main()
