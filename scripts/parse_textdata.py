#!/usr/bin/env python3
"""Parse all Media textdata tables (UTF-16) into a schema inventory.

Reads each table's BOM to detect encoding, decodes the header row, and reports
row count / column count. Emits TEXTDATA_SCHEMAS.json (repo root) plus a
compact human-readable listing of every table, its columns, and row count.

This turns the 159 textdata tables into queryable, evidence-backed data schemas
(column names are actual game source headers, not inferred).
"""
from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import sro_paths  # noqa: E402

DIR = os.path.join(sro_paths.resolve_full_extract_dir(), "Media", "server_dep", "silkroad", "textdata")
REPO = BASE


def decode(blob):
    if blob.startswith(b"\xff\xfe"):
        return blob[2:].decode("utf-16-le", "replace"), "utf-16-le"
    if blob.startswith(b"\xfe\xff"):
        return blob[2:].decode("utf-16-be", "replace"), "utf-16-be"
    for enc in ("utf-8", "cp949"):
        try:
            return blob.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return blob.decode("latin-1", "replace"), "latin-1"


def main():
    schemas = {}
    listing = []
    for name in sorted(os.listdir(DIR)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(DIR, name)
        with open(path, "rb") as fh:
            blob = fh.read()
        text, enc = decode(blob)
        lines = text.splitlines()
        header = lines[0] if lines else ""
        cols = [c for c in header.split("\t")] if header else []
        schemas[name] = {
            "encoding": enc,
            "rows": max(0, len(lines) - 1),
            "columns": cols,
        }
        listing.append((name, len(cols), max(0, len(lines) - 1), cols))

    out = os.path.join(REPO, "TEXTDATA_SCHEMAS.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(schemas, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print(f"tables: {len(schemas)}")
    for name, ncol, nrow, cols in listing:
        print(f"{name:40s} rows={nrow:7d} cols={ncol:3d}  {cols[:6]}")
    print("wrote", out)


if __name__ == "__main__":
    main()
