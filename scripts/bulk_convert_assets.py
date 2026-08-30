#!/usr/bin/env python3
"""Phase 6 bulk conversion of VERIFIED vSRO minimap assets to Android-ready PNG.

Bulk-converts only the two directories proven in Phase 5/6 to contain
JMXVDDJ+DDS images in the decoder-supported pixel formats:
    Media/minimap/     (5,523 .ddj, verified)
    Media/minimap_d/   (2,214 .ddj, verified)
into `android-assets/maps/...` PNG files via the deterministic pure-Python
decoder (scripts/dds_decode.py). No PK2 archive is modified, no full extraction
is performed, and every source file is verified from its real bytes before
conversion. Unknown/unsupported formats are recorded (never guessed, never
silently converted).

Usage:
    python3 scripts/bulk_convert_assets.py \
        --pk2-dir /path/to/pk2s --reader-bin /path/to/pk2_mate \
        --listing /path/to/Media.list.txt --out android-assets \
        [--archive Media] [--batch-size 300] [--limit N] [--work DIR]
        [--manifest PATH] [--resume]

Output mapping (collision-safe, preserves PK2 subpath):
    /minimap/X.ddj           -> maps/minimap/X.png
    /minimap_d/REGION/X.ddj  -> maps/minimap_d/REGION/X.png

All generated files are recorded in the manifest with full traceability
(source PK2, internal path, sizes, SHA256, detected format, output SHA256,
validation). Determinism: the same source always yields byte-identical output.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from dds_decode import (
    JMX_DDJ_MAGIC,
    InvalidDDS,
    UnsupportedPixelFormat,
    ddj_to_rgba,
    parse_dds,
    parse_png_header,
    png_from_rgba,
)
from inventory_pk2 import parse_listing

TARGET_PREFIXES = ("/minimap/", "/minimap_d/")
OUTPUT_ROOT = "maps"
DEFAULT_ARCHIVE = "Media.pk2"
RESULT_OK = "ok"
RESULT_FAILED = "failed"
RESULT_UNKNOWN = "unknown"


def png_dimensions(png):
    w, h, _bd, _ct = parse_png_header(png)
    return w, h


def png_roundtrip_ok(png, w, h):
    try:
        iw, ih, _bd, _ct = parse_png_header(png)
        if (iw, ih) != (w, h):
            return False
    except Exception:
        return False
    return True


def classify_format(data):
    if data[0:12] != JMX_DDJ_MAGIC:
        return "NOT-JMXVDDJ"
    try:
        hdr = parse_dds(data[20:])
    except Exception:
        return "MALFORMED-DDS"
    if hdr["pf_flags"] & 0x4:
        return "DDJ+DDS(%s)" % hdr["fourcc"].decode(errors="replace")
    masks = hdr["masks"]
    return "DDJ+DDS(RGB%d/%s)" % (hdr["bitcount"], masks)


def logical_size(path):
    base = os.path.basename(path)
    matches = re.findall(r"(\d+)x(\d+)", base)
    if matches:
        w, h = matches[-1]
        return int(w), int(h)
    return None


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def extract_targets(listing_path):
    text = Path(listing_path).read_text(encoding="utf-8", errors="replace")
    files, _dirs = parse_listing(text)
    return sorted(f for f in files if f.startswith(TARGET_PREFIXES))


def map_output(source_path):
    rel = source_path.lstrip("/")
    if not rel.endswith(".ddj"):
        raise ValueError("unexpected source suffix: " + source_path)
    return OUTPUT_ROOT + "/" + rel[:-4] + ".png"


def convert_one(reader, pk2_path, source_path, work_dir, out_dir, record):
    rel = source_path.lstrip("/")
    sub = os.path.join(work_dir, "w")
    os.makedirs(sub, exist_ok=True)
    proc = subprocess.run(
        [reader, "extract", "--archive", pk2_path, "--out", sub, "--path", rel],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        record["status"] = RESULT_FAILED
        record["error"] = "extract rc!=0: " + proc.stderr.strip()[:200]
        return None
    src_file = os.path.join(sub, os.path.basename(rel))
    if not os.path.isfile(src_file):
        record["status"] = RESULT_FAILED
        record["error"] = "extract produced no file"
        return None
    with open(src_file, "rb") as f:
        data = f.read()
    try:
        os.remove(src_file)
    except OSError:
        pass
    record["source_size"] = len(data)
    record["source_sha256"] = sha256_bytes(data)
    fmt = classify_format(data)
    record["detected_format"] = fmt
    try:
        w, h, pix = ddj_to_rgba(data)
    except UnsupportedPixelFormat as e:
        record["status"] = RESULT_UNKNOWN
        record["error"] = "unsupported format: " + str(e)
        return None
    except (InvalidDDS, Exception) as e:
        record["status"] = RESULT_FAILED
        record["error"] = "decode error: %s: %s" % (type(e).__name__, e)
        return None
    png = png_from_rgba(w, h, pix)
    if not png_roundtrip_ok(png, w, h):
        record["status"] = RESULT_FAILED
        record["error"] = "PNG round-trip validation failed"
        return None
    output_path = map_output(source_path)
    dest = os.path.join(out_dir, output_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(png)
    record["conversion"] = "DDJ_TO_PNG"
    record["output"] = output_path
    record["output_size"] = len(png)
    record["output_sha256"] = sha256_bytes(png)
    record["width"] = w
    record["height"] = h
    ls = logical_size(source_path)
    if ls:
        record["logical_width"], record["logical_height"] = ls
    record["validation"] = "PASS"
    record["status"] = RESULT_OK
    return output_path


def build_manifest(targets, archive, pk2_path):
    st = os.stat(pk2_path)
    return {
        "schema": "phase6-bulk-assets-v1",
        "archive": archive,
        "pk2_snapshot": {"size": st.st_size, "mtime_ns": st.st_mtime_ns},
        "targets": {
            "total": len(targets),
            "minimap": sum(1 for t in targets if t.startswith("/minimap/")),
            "minimap_d": sum(1 for t in targets if t.startswith("/minimap_d/")),
        },
        "batches": [],
        "records": [],
    }


def run_batch(batch_paths, reader, pk2_path, out_dir, work_dir, batch_no, manifest):
    counts = {"ok": 0, "failed": 0, "unknown": 0}
    consecutive_errors = 0
    for source_path in batch_paths:
        record = {
            "source_pk2": manifest["archive"],
            "source_path": source_path,
            "source_size": None,
            "source_sha256": None,
            "detected_format": None,
            "conversion": None,
            "output": None,
            "output_size": None,
            "output_sha256": None,
            "width": None,
            "height": None,
            "validation": None,
            "status": None,
            "error": None,
        }
        convert_one(reader, pk2_path, source_path, work_dir, out_dir, record)
        manifest["records"].append(record)
        counts[record["status"] or "failed"] += 1
        if record["status"] == RESULT_OK:
            consecutive_errors = 0
        else:
            consecutive_errors += 1
            if consecutive_errors >= 5:
                raise SystemExit(
                    "STOP: 5 consecutive failures in batch %d (%s); "
                    "systematic corruption suspected" % (batch_no, source_path)
                )
    manifest["batches"].append(
        {
            "batch": batch_no,
            "start_index": len(manifest["records"]) - len(batch_paths),
            "end_index": len(manifest["records"]),
            **counts,
        }
    )
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", required=True)
    ap.add_argument("--reader-bin", required=True)
    ap.add_argument("--listing", required=True, help="pk2_mate list output for the archive")
    ap.add_argument("--archive", default=DEFAULT_ARCHIVE)
    ap.add_argument("--out", default="android-assets")
    ap.add_argument("--batch-size", type=int, default=300)
    ap.add_argument("--limit", type=int, default=None, help="cap number of files (testing)")
    ap.add_argument("--work", default=None, help="persistent work dir (default: tempfile)")
    ap.add_argument("--manifest", default=None, help="manifest path (default: <out>/manifest.json)")
    ap.add_argument("--resume", action="store_true", help="skip records already status=ok")
    args = ap.parse_args()

    pk2_path = os.path.join(args.pk2_dir, args.archive)
    if not os.path.isfile(pk2_path):
        sys.exit("PK2 archive not found: " + pk2_path)
    if not os.path.isfile(args.reader_bin):
        sys.exit("reader binary not found: " + args.reader_bin)
    targets = extract_targets(args.listing)
    if args.limit:
        targets = targets[: args.limit]
    if not targets:
        sys.exit("no target files found in listing under " + ", ".join(TARGET_PREFIXES))

    manifest_path = args.manifest or os.path.join(args.out, "manifest.json")
    manifest = None
    done_paths = set()
    if args.resume and os.path.isfile(manifest_path):
        manifest = json.load(open(manifest_path))
        done_paths = {r["source_path"] for r in manifest["records"] if r["status"] == RESULT_OK}

    remaining = [t for t in targets if t not in done_paths]
    if manifest is None:
        manifest = build_manifest(targets, args.archive, pk2_path)
    print(
        "targets=%d done=%d remaining=%d batch_size=%d out=%s"
        % (len(targets), len(done_paths), len(remaining), args.batch_size, args.out),
        flush=True,
    )

    if args.work:
        os.makedirs(args.work, exist_ok=True)
        work_ctx = tempfile.TemporaryDirectory(prefix=".work-", dir=args.work)
    else:
        work_ctx = tempfile.TemporaryDirectory(prefix="bulk-")

    with work_ctx as work_dir:
        os.makedirs(args.out, exist_ok=True)
        for i in range(0, len(remaining), args.batch_size):
            batch = remaining[i : i + args.batch_size]
            batch_no = i // args.batch_size + 1
            counts = run_batch(batch, args.reader_bin, pk2_path, args.out, work_dir, batch_no, manifest)
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=1)
            print(
                "batch %d done: ok=%d failed=%d unknown=%d (total records=%d)"
                % (batch_no, counts["ok"], counts["failed"], counts["unknown"], len(manifest["records"])),
                flush=True,
            )

    summary = {"ok": 0, "failed": 0, "unknown": 0}
    for r in manifest["records"]:
        summary[r["status"] or "failed"] += 1
    manifest["summary"] = summary
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1)
    print(
        "DONE: processed=%d ok=%d failed=%d unknown=%d manifest=%s"
        % (len(manifest["records"]), summary["ok"], summary["failed"], summary["unknown"], manifest_path),
        flush=True,
    )


if __name__ == "__main__":
    main()
