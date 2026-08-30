#!/usr/bin/env python3
"""Deterministic, read-only PK2 validation using the external pk2_mate reader.

Verifies each archive's header/signature against the format constants that are
documented from the reader source (Veykril/pk2, commit pinned in
PK2_READER_FOUNDATION.md), then delegates directory/index listing and a single
controlled file extraction to pk2_mate itself. Read-only: the source archive is
never modified and no full extraction is performed.

Usage:
    python3 scripts/validate_pk2.py --pk2-dir /path/to/pk2s
        [--reader-bin /path/to/pk2_mate] [--reader-dir /path/to/reader]
        [--sample N] [--extract-one]

Reader resolution order: an explicitly provided --reader-bin is authoritative
(validated immediately; the command fails clearly if it is not an executable
file), otherwise SRO_READER_BIN, --reader-dir/pk2_mate, SRO_READER_DIR/pk2_mate,
then "pk2_mate" on PATH. The command fails clearly and exits non-zero when the
reader cannot be found or any archive fails validation.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

PK2_SIGNATURE = b"JoyMax File Manager!\n" + b"\x00" * 9
PK2_VERSION = 0x0100_0002
PK2_HEADER_LEN = 256
PK2_ARCHIVES = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")


def find_pk2_mate(reader_bin=None, reader_dir=None):
    if reader_bin:
        if os.path.isfile(reader_bin) and os.access(reader_bin, os.X_OK):
            return os.path.abspath(reader_bin)
        return None
    candidates = []
    candidates.append(os.environ.get("SRO_READER_BIN"))
    for base in (reader_dir, os.environ.get("SRO_READER_DIR")):
        if base:
            candidates.append(os.path.join(base, "pk2_mate"))
    for cand in candidates:
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return os.path.abspath(cand)
    on_path = shutil.which("pk2_mate")
    if on_path:
        return on_path
    return None


def verify_header(header):
    """Return list of (check, ok, detail) for the 256-byte PK2 header."""
    if len(header) < PK2_HEADER_LEN:
        return [("header_size", False, "only {0} bytes".format(len(header)))]
    version = int.from_bytes(header[30:34], "little")
    checks = [
        ("signature", header[0:30] == PK2_SIGNATURE, repr(header[0:30])),
        ("version", version == PK2_VERSION, "0x{0:08x}".format(version)),
        ("encrypted_flag", header[34] != 0, "0x{0:02x}".format(header[34])),
        ("verify_field", header[35:38] != b"\x00\x00\x00", header[35:38].hex()),
        ("reserved_zero", all(b == 0 for b in header[51:256]), ""),
    ]
    return checks


def run_list(reader, archive):
    proc = subprocess.run(
        [reader, "list", "--archive", archive],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def sample_entries(list_output, sample):
    lines = [ln for ln in list_output.splitlines() if ln.strip()]
    head = lines[:sample]
    if len(lines) > sample:
        head.append("... ({0} more lines)".format(len(lines) - sample))
    return head


def extract_one(reader, archive, out_dir, path):
    proc = subprocess.run(
        [reader, "extract", "--archive", archive, "--out", out_dir, "--path", path],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def validate_archive(reader, pk2_dir, name, sample, extract_one_path):
    path = os.path.join(pk2_dir, name)
    if not os.path.isfile(path):
        return {"archive": name, "present": False, "size": None}
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        header = f.read(PK2_HEADER_LEN)
    header_checks = verify_header(header)
    header_ok = all(ok for _, ok, _ in header_checks)
    list_rc, list_out, list_err = run_list(reader, path)
    listing = sample_entries(list_out, sample) if list_rc == 0 else []
    extraction = None
    if list_rc == 0 and extract_one_path:
        norm = "/".join(extract_one_path.split("/"))
        listing_lines = [ln.strip() for ln in list_out.splitlines() if ln.strip()]
        if not any(ln.endswith(norm) for ln in listing_lines):
            extraction = {"rc": None, "files": [], "stderr": "", "skipped": "path not in archive"}
        else:
            with tempfile.TemporaryDirectory(prefix="pk2val_") as tmp:
                ext_rc, ext_out, ext_err = extract_one(reader, path, tmp, extract_one_path)
                files = []
                for root, _, names in os.walk(tmp):
                    for fn in names:
                        full = os.path.join(root, fn)
                        files.append((os.path.relpath(full, tmp), os.path.getsize(full)))
                extraction = {"rc": ext_rc, "files": files, "stderr": ext_err.strip()}
    return {
        "archive": name,
        "present": True,
        "size": size,
        "header_ok": header_ok,
        "header_checks": header_checks,
        "list_rc": list_rc,
        "entry_count_estimate": None,
        "listing": listing,
        "list_stderr": list_err.strip(),
        "extraction": extraction,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Read-only PK2 validation via pk2_mate (no full extraction)"
    )
    parser.add_argument("--pk2-dir", default=None, help="Directory with *.pk2 archives")
    parser.add_argument("--reader-bin", default=None, help="Path to pk2_mate binary")
    parser.add_argument("--reader-dir", default=None, help="Directory containing pk2_mate")
    parser.add_argument("--sample", type=int, default=15, help="Max listing lines to show")
    parser.add_argument("--extract-one", default=None, help="PK2-internal path to extract for proof")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    pk2_dir = args.pk2_dir or os.environ.get("SRO_PK2_DIR")
    if not pk2_dir:
        sys.exit("Error: --pk2-dir or SRO_PK2_DIR is required")

    reader = find_pk2_mate(args.reader_bin, args.reader_dir)
    if reader is None:
        sys.exit(
            "Error: pk2_mate (the verified PK2 reader) was not found. "
            "Set --reader-bin, --reader-dir, SRO_READER_BIN, SRO_READER_DIR, or add "
            "pk2_mate to PATH. See PK2_READER_FOUNDATION.md for the pinned source/version."
        )

    results = []
    for name in PK2_ARCHIVES:
        results.append(validate_archive(reader, pk2_dir, name, args.sample, args.extract_one))

    any_failure = False
    for r in results:
        if not r["present"]:
            print("[{0}] MISSING".format(r["archive"]))
            continue
        if not r["header_ok"]:
            any_failure = True
        for check, ok, detail in r["header_checks"]:
            print("[{0}] header.{1} = {2} {3}".format(r["archive"], check, "OK" if ok else "FAIL", detail))
        print("[{0}] list rc={1} header_ok={2} size={3}".format(
            r["archive"], r["list_rc"], r["header_ok"], r["size"]))
        if r["list_rc"] != 0:
            any_failure = True
            if r["list_stderr"]:
                print("    stderr: {0}".format(r["list_stderr"]))
        for line in r["listing"]:
            print("    {0}".format(line))
        if r["extraction"]:
            e = r["extraction"]
            if e.get("skipped"):
                print("    extract skipped: {0}".format(e["skipped"]))
            else:
                print("    extract rc={0} files={1}".format(e["rc"], e["files"]))
                if e["rc"] != 0:
                    any_failure = True
                    if e["stderr"]:
                        print("    extract stderr: {0}".format(e["stderr"]))

    if args.json:
        import json

        json.dump(results, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")

    if any_failure:
        sys.exit("FAILED: one or more PK2 archives failed validation")
    print("OK: all present PK2 archives passed header + list validation")


if __name__ == "__main__":
    main()
