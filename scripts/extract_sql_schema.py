#!/usr/bin/env python3
"""Read-only SQL Server .Bak schema extraction (table/column names).

SQL Server backup files store object names in metadata pages as ASCII and
UTF-16LE strings. This extracts candidate table names (the SRO convention is a
leading underscore, e.g. _RefObjCommon, _Char, _Guild) and filters out SQL
Server internal statistics/index objects (_WA_Sys_, _Sys_, _sp_, _MScheck_,
__Param__ etc.) to yield the authoritative server-side data model.

Read-only: no restore, no modification of the .Bak files.

Output: SQL_DATABASE_SCHEMA.json (repo root) + human listing.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import sro_paths  # noqa: E402

BAK_DIR = sro_paths.resolve_db_dir()
REPO = BASE

BAK_FILES = [
    ("SRO_CERTIFICATION.Bak", "certification"),
    ("SRO_VT_ACCOUNT.Bak", "account"),
    ("SRO_VT_SHARD.Bak", "shard"),
    ("SRO_VT_SHARDLOG.Bak", "shardlog"),
]

INTERNAL_RE = re.compile(
    r"(_WA_Sys_|_Sys_|_MScheck|_sp_|_sqlagent_|_last_|_bloom_|_OVCSSQLDatabase|"
    r"__Param__|__Servi__|__ProbG__|__Const__|__Perio__|__dLogDat__|__Codename|"
    r"_WA_Sys|^_0$|_AAj|_C33mC|_Cff|_CR8|_CRN|_CTCHD|_CATA|_Dff|_DR8|_DES|_DAW|"
    r"_EfveD|_G7l|_H1bD|_HADD|_IgN|_I_I|_J7M|_J_J|_K0|_K_K|_KgN|_KtY|_L_L|_MAG|"
    r"_MK_|_M_M|_N_N|_O_O|_P_P|_RHtD|_BA_|_EU_|_EVE|_FA_|_RING|_MAX|_MEM|_NEW|"
    r"_OLD|_STRENGTH|_CUR|_LATEST)"
)


def extract_strings(path):
    names = set()
    for enc_flag in (["-a"], ["-a", "-el"]):
        try:
            out = subprocess.run(
                ["strings"] + enc_flag + [path], capture_output=True, text=True,
                timeout=300,
            ).stdout
        except (subprocess.TimeoutExpired, OSError):
            continue
        for line in out.splitlines():
            m = re.match(r"^_[A-Za-z][A-Za-z0-9_]{2,}$", line.strip())
            if m:
                names.add(m.group(0))
    return names


def clean(names):
    out = set()
    for n in names:
        if INTERNAL_RE.search(n):
            continue
        # drop trailing corruption noise like "dDa", "00a", "0R", "_bak"
        base = n
        while re.search(r"(dDa|dDa|d1|d2|d7|0R|00a|0R|0$|0R)$", base):
            base = base[:-1]
        out.add(base)
    return sorted(out)


def main():
    schema = {}
    for fname, label in BAK_FILES:
        path = os.path.join(BAK_DIR, fname)
        if not os.path.isfile(path):
            continue
        names = clean(extract_strings(path))
        schema[label] = {
            "file": fname,
            "size": os.path.getsize(path),
            "tables": names,
        }
        print(f"{fname:26s} tables={len(names):4d}")

    out = os.path.join(REPO, "SQL_DATABASE_SCHEMA.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(schema, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("\n=== SHARD tables ===")
    for t in schema.get("shard", {}).get("tables", []):
        print(" ", t)
    print("\n=== ACCOUNT tables ===")
    for t in schema.get("account", {}).get("tables", []):
        print(" ", t)
    print("wrote", out)


if __name__ == "__main__":
    main()
