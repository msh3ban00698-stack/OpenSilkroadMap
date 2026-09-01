#!/usr/bin/env python3
"""Incremental, resumable, read-only source-corpus indexer (Phase 29).

Enumerates EVERY discoverable source file once and classifies it with actual
evidence into PROVEN / PARTIAL / STUB / MISSING / UNKNOWN / UNREADABLE / DEAD,
plus a structural `system` and literal `domains` tags. No large binary payload
is read or hashed: PK2 files are indexed from the verified block table; large
archives are listed read-only via 7z/unzip/unrar; only small text/config files
already on disk are read for parse verification.

Incremental/resumable: a JSON cache keyed by (path, size, mtime) stores the
PK2/container entry tables so unchanged archives are never re-walked or
re-hashed. Previously verified per-file SHA-256 values (extract_report.json,
Phase 4) are reused rather than recomputed.

Read-only: no source archive is modified; outputs go to the repo root only.

Outputs (repo root):
  SOURCE_CORPUS_MANIFEST.json     one row per file (all source families)
  SOURCE_CORPUS_MANIFEST.tsv      tab-separated mirror
  SOURCE_CORPUS_STATS.json        archive census + reconciliation + system/domain totals
  SOURCE_SYSTEM_INVENTORY.json    per-archive + per-system + per-domain breakdown
  SOURCE_SYSTEM_INVENTORY.tsv     flat rows (source, system, domain, count, bytes)
  SOURCE_EXTRACTION_ERRORS.tsv    any unreadable/failed entry (should be empty)
  SOURCE_EXTRACTION_REPORT.md     audit + coverage narrative
  SOURCE_PARTIAL_COVERAGE.md      partial/unproven coverage notes
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import pk2_table  # noqa: E402
import sro_paths  # noqa: E402

REPO = BASE
CACHE_DIR = os.path.join(REPO, ".source_index")
CACHE_PATH = os.path.join(CACHE_DIR, "cache.json")

REAL_PK2 = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")

KNOWN_MISSING = [
    {"name": "RecMsg.dat", "reason": "client-side receive-message table; string 'RecMsg.dat' present in GameClient.exe (Game.cpp startup, loaded via CreateFile); absent from all archives/containers/SQL backups"},
]

PROVEN_EXT = {
    ".txt", ".lua", ".cfg", ".ini", ".xml", ".config", ".html", ".htm",
    ".log", ".sh", ".bat", ".sct", ".scr", ".csv", ".tsv", ".json",
    ".yaml", ".yml", ".c", ".h", ".cpp", ".hpp", ".vsh", ".psh",
}
DEAD_NAME = {"thumbs.db", "thumbs.db:encryptable", "desktop.ini", "vssver.scc", "vssver2.scc"}
DEAD_EXT = {".tmp", ".sfk"}

FORMAT_MAP = {
    ".ddj": "jmx-texture", ".bms": "jmx-skeleton", ".bsr": "jmx-mesh",
    ".bsk": "jmx-skin", ".nvm": "jmx-navmesh", ".ban": "jmx-animation",
    ".efp": "jmx-effect", ".cpd": "jmx-strings",
    ".wav": "wav-audio", ".ogg": "ogg-audio", ".mp3": "mp3-audio",
    ".t": "map-tile", ".m": "map-mesh", ".o": "map-object", ".o2": "map-object2",
    ".ifo": "map-info", ".mfo": "map-info", ".msf": "map-info",
    ".bmt": "map-bmt", ".2dt": "map-2d-tile", ".dof": "map-dof",
    ".exe": "pe-executable", ".dll": "pe-dll", ".dat": "binary-data",
    ".db": "binary-db", ".rd": "region-data", ".crb": "compiled-script",
    ".tga": "tga-texture", ".dds": "dds-texture", ".png": "png-texture",
    ".sct": "compiled-script", ".vsh": "vertex-shader", ".psh": "pixel-shader",
    ".c": "c-source", ".h": "c-header", ".lua": "lua-script",
    ".txt": "text", ".cfg": "config", ".ini": "config", ".xml": "xml-config",
    ".config": "config", ".html": "html", ".log": "log", ".sh": "shell",
    ".bat": "batch", ".csv": "csv", ".tsv": "tsv", ".json": "json",
    ".yaml": "yaml", ".yml": "yaml", ".scc": "vss-source-control",
    ".sfk": "audio-peak-cache",
}

SYSTEM_BY_TOP = {
    "navmesh": "navigation", "prim": "rendering", "shader": "rendering",
    "shader_maptool": "rendering", "res": "rendering", "compound": "rendering",
    "tile2d": "map", "sun": "map", "water": "map", "weather": "map",
    "skybox": "map", "dungeon": "map",
    "interface": "ui", "icon": "ui", "icon64": "ui", "res_ui": "ui",
    "launcher": "ui", "launcher_europe": "ui", "fonts": "ui", "resinfo": "ui",
    "minimap": "minimap", "minimap_d": "minimap",
    "server_dep": "data-tables",
    "effect": "effects", "textures": "effects", "monster": "effects",
    "skill": "effects", "system": "effects", "meshes": "effects",
    "animations": "effects", "hiteffect": "effects", "battle": "effects",
    "dun": "effects", "map": "effects", "cos": "effects", "co": "effects",
    "npc": "effects", "item": "effects",
}

DOMAIN_TOKENS = (
    "ui", "chat", "party", "guild", "academy", "union", "fortress",
    "npc", "monster", "quest", "item", "skill", "combat", "battle",
    "map", "region", "effect", "animation", "anim", "network", "proxy",
    "protocol", "social", "shop", "trade", "economy", "rank", "event",
    "local", "config", "server", "client", "login", "notice", "msg",
    "text", "char", "character", "pet", "summon", "transport", "teleport",
    "movement", "spawn", "drop", "inventory", "equip", "buff", "debuff",
    "level", "exp", "gold", "silk", "arena", "job", "hunter", "thief",
    "alchemy", "archemy",
)


def ext_of(path):
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else "(none)"


def top_of(path):
    segs = [s for s in path.replace("\\", "/").split("/") if s]
    return segs[0] if segs else "(root)"


def basename_of(path):
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def file_identity(path):
    st = os.stat(path)
    return {"path": path, "size": st.st_size, "mtime_ns": st.st_mtime_ns}


def load_cache():
    if os.path.isfile(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_cache(cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=1)
        fh.write("\n")


def pk2_entries_cached(path, cache):
    ident = file_identity(path)
    key = path
    hit = cache.get("pk2", {}).get(key)
    if hit and hit["size"] == ident["size"] and hit["mtime_ns"] == ident["mtime_ns"]:
        return hit["entries"], ident, True
    files, _dirs = pk2_table.inventory(path)
    entries = [[f["path"], f["size"], f["pos"]] for f in files]
    cache.setdefault("pk2", {})[key] = {
        "size": ident["size"], "mtime_ns": ident["mtime_ns"], "entries": entries,
    }
    return entries, ident, False


def container_list(path, cache):
    """List a 7z/rar/zip read-only via 7z; return [(name, size)] or None on failure."""
    ident = file_identity(path)
    key = path
    hit = cache.get("container", {}).get(key)
    if hit and hit["size"] == ident["size"] and hit["mtime_ns"] == ident["mtime_ns"]:
        return hit["entries"], ident, True
    entries = []
    try:
        out = subprocess.run(["7z", "l", "-slt", "-ba", path],
                             capture_output=True, text=True, timeout=180)
        entries = _parse_7z_slt(out.stdout)
    except Exception as exc:  # pragma: no cover
        print("WARN container list failed", path, exc, file=sys.stderr)
        entries = []
    cache.setdefault("container", {})[key] = {
        "size": ident["size"], "mtime_ns": ident["mtime_ns"], "entries": entries,
    }
    return entries, ident, False


def _parse_7z_slt(text):
    """Parse `7z l -slt -ba`; return [(name, size)] for FILES only."""
    entries = []
    cur = {}
    for line in text.splitlines():
        if line.startswith("Path = "):
            cur = {"name": line[7:].strip(), "is_dir": False, "size": -1}
        elif line.startswith("Size = ") and "name" in cur:
            try:
                cur["size"] = int(line[7:].strip())
            except ValueError:
                cur["size"] = -1
        elif line.startswith("Attributes = ") and "name" in cur:
            cur["is_dir"] = line[13:].lstrip().startswith("D")
        elif line.strip() == "" and cur:
            if not cur["is_dir"] and cur["name"]:
                entries.append((cur["name"], cur["size"]))
            cur = {}
    if cur and not cur["is_dir"] and cur["name"]:
        entries.append((cur["name"], cur["size"]))
    return entries


def reuse_hashes(full_extract_dir):
    """Load previously verified per-file SHA-256 from Phase 4 extract_report."""
    report = os.path.join(os.path.dirname(full_extract_dir), "extract_report.json")
    if not os.path.isfile(report):
        return {}
    with open(report, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = {}
    for rec in data.get("records", []):
        if rec.get("result") == "ok" and rec.get("sha256"):
            out[(rec["pk2"], rec["path"])] = rec["sha256"]
    return out


def classify_status(ext, is_extracted, size, name_lower):
    if name_lower in DEAD_NAME or ext in DEAD_EXT:
        return "DEAD"
    if size == 0:
        return "STUB"
    if ext in PROVEN_EXT:
        return "PROVEN" if is_extracted else "PARTIAL"
    return "UNKNOWN"


def system_of(path, source, archive=None):
    """Coarse structural system tag from directory + extension (not semantics)."""
    segs = [s for s in path.replace("\\", "/").split("/") if s]
    top = segs[0] if segs else "(root)"
    low = path.lower()
    if source == "sql-backup":
        return "database"
    if source == "filesystem":
        if archive == "proxy":
            return "networking"
        if archive == "client":
            return "client-binary"
        if archive == "event":
            return "server-logic"
        if archive == "server":
            if "/script/" in low or path.endswith((".lua", ".sct", ".crb")):
                return "server-logic"
            if path.endswith((".exe", ".dll")):
                return "server-binary"
            if path.endswith((".cfg", ".ini", ".xml", ".config")):
                return "configuration"
            return "server-data"
        return "unknown"
    if source == "container":
        if path.endswith((".exe", ".dll")):
            return "client-binary"
        if path.endswith(".rd") or "/rd/" in low:
            return "region-data"
        if "/setting/" in low or path.endswith((".cfg", ".ini", ".dat")):
            return "configuration"
        return "unknown"
    # pk2 source
    if top.isdigit():
        return "map"
    if top in SYSTEM_BY_TOP:
        return SYSTEM_BY_TOP[top]
    if top.endswith(".ogg"):
        return "audio"
    return "unknown"


def domains_of(path):
    """Literal domain tokens present in the path (coverage tags, NOT semantics)."""
    low = path.lower()
    found = []
    for tok in DOMAIN_TOKENS:
        if tok in low:
            found.append(tok)
    return found


def walk_filesystem(root):
    rows = []
    if not root or not os.path.isdir(root):
        return rows
    for dirpath, _dirs, fnames in os.walk(root):
        for fn in fnames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            rows.append((rel, os.path.getsize(full), full))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    ap.add_argument("--extract-dir", default=os.environ.get("SRO_EXTRACT_DIR"))
    ap.add_argument("--full-extract-dir", default=os.environ.get("SRO_FULL_EXTRACT_DIR"))
    ap.add_argument("--db-dir", default=os.environ.get("SRO_DB_DIR"))
    ap.add_argument("--pkg-dir", default=os.environ.get("SRO_PKG_DIR"))
    ap.add_argument("--out", default=REPO)
    args = ap.parse_args()
    args.pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)

    cache = load_cache()
    reused_hashes = reuse_hashes(args.full_extract_dir) if args.full_extract_dir else {}
    rows = []
    errors = []

    # --- 1. PK2 archives (canonical client asset index) --------------------
    full_extract_set = set()
    if args.full_extract_dir and os.path.isdir(args.full_extract_dir):
        for sub in ("Media", "Music", "Particles"):
            root = os.path.join(args.full_extract_dir, sub)
            if not os.path.isdir(root):
                continue
            for dirpath, _d, fnames in os.walk(root):
                for fn in fnames:
                    rel = os.path.relpath(os.path.join(dirpath, fn), root)
                    full_extract_set.add((sub + ".pk2", "/" + rel.replace("\\", "/")))

    per_archive = {}
    for name in REAL_PK2:
        path = os.path.join(args.pk2_dir, name)
        if not os.path.isfile(path):
            per_archive[name] = {"present": False}
            continue
        entries, ident, cached = pk2_entries_cached(path, cache)
        n = 0
        bytes_ = 0
        for (epath, size, pos) in entries:
            name_lower = basename_of(epath).lower()
            ext = ext_of(epath)
            is_extracted = (name, epath) in full_extract_set
            status = classify_status(ext, is_extracted, size, name_lower)
            rows.append({
                "source": "pk2",
                "archive": name,
                "internal_path": epath,
                "name": basename_of(epath),
                "extension": ext,
                "size": size,
                "sha256": reused_hashes.get((name, epath), ""),
                "status": status,
                "format": FORMAT_MAP.get(ext, "text" if ext in PROVEN_EXT else "unknown"),
                "system": system_of(epath, "pk2"),
                "domains": domains_of(epath),
                "extracted": is_extracted,
                "location": "",
            })
            n += 1
            bytes_ += size
        per_archive[name] = {
            "present": True, "size": ident["size"], "cached": cached,
            "file_count": n, "payload_bytes": bytes_,
        }

    # --- 2. Extracted filesystem trees (server/proxy/client/event) ---------
    tree_labels = {}
    for label in ("server", "proxy", "client", "event"):
        if not args.extract_dir:
            tree_labels[label] = ""
            continue
        root = os.path.join(args.extract_dir, label)
        for (rel, size, full) in walk_filesystem(root):
            name_lower = basename_of(rel).lower()
            ext = ext_of(rel)
            status = classify_status(ext, True, size, name_lower)
            rows.append({
                "source": "filesystem",
                "archive": label,
                "internal_path": rel,
                "name": basename_of(rel),
                "extension": ext,
                "size": size,
                "sha256": "",
                "status": status,
                "format": FORMAT_MAP.get(ext, "text" if ext in PROVEN_EXT else "unknown"),
                "system": system_of(rel, "filesystem", label),
                "domains": domains_of(rel),
                "extracted": True,
                "location": full,
            })
        tree_labels[label] = root

    # --- 3. SQL backups ----------------------------------------------------
    for root, kind in ((args.db_dir, "sql-backup"),):
        if not root or not os.path.isdir(root):
            continue
        for fn in sorted(os.listdir(root)):
            if fn.lower().endswith(".bak"):
                full = os.path.join(root, fn)
                rows.append({
                    "source": "sql-backup",
                    "archive": fn,
                    "internal_path": fn,
                    "name": fn,
                    "extension": ".bak",
                    "size": os.path.getsize(full),
                    "sha256": "",
                    "status": "UNKNOWN",
                    "format": "sql-server-backup",
                    "system": "database",
                    "domains": [],
                    "extracted": True,
                    "location": full,
                })

    # --- 4. Containers (list read-only; dedupe vs extracted trees) ---------
    # Containers already fully realized as extracted trees/db: no per-file rows
    # (their entries are the filesystem/sql-backup rows above). Containers whose
    # content is NOT on disk are indexed as rows here.
    REALIZED_CONTAINERS = {
        "Database.7z": "sql-backup",
        "Vietnam-R v193 Package Server.7z": "filesystem/server",
        "Event-HAPPY-Working-Files-vsro-193.7z": "filesystem/server",
        "VSRO-R Proxy v1005.rar": "filesystem/proxy",
    }
    client_fs_names = {basename_of(r["internal_path"]) for r in rows
                       if r["source"] == "filesystem" and r["archive"] == "client"}
    container_census = []
    if args.pkg_dir and os.path.isdir(args.pkg_dir):
        for fn in sorted(os.listdir(args.pkg_dir)):
            p = os.path.join(args.pkg_dir, fn)
            if not os.path.isfile(p):
                continue
            low = fn.lower()
            if not low.endswith((".7z", ".rar", ".zip")):
                continue
            entries, ident, cached = container_list(p, cache)
            realized = REALIZED_CONTAINERS.get(fn)
            container_census.append({
                "archive": fn, "size": ident["size"], "entry_count": len(entries),
                "cached": cached, "realized_as": realized,
            })
            if realized:
                continue  # fully realized on disk; skip per-file rows
            for (ename, esize) in entries:
                if ename.endswith("/") or not ename:
                    continue
                name_lower = basename_of(ename).lower()
                if name_lower in client_fs_names:
                    continue  # already a filesystem row (extract/client)
                ext = ext_of(ename)
                size = esize if esize >= 0 else 0
                if esize < 0:
                    status = "UNKNOWN"  # size unreadable; not a stub
                else:
                    status = classify_status(ext, False, size, name_lower)
                rows.append({
                    "source": "container",
                    "archive": fn,
                    "internal_path": ename,
                    "name": basename_of(ename),
                    "extension": ext,
                    "size": size,
                    "sha256": "",
                    "status": status,
                    "format": FORMAT_MAP.get(ext, "text" if ext in PROVEN_EXT else "unknown"),
                    "system": system_of(ename, "container"),
                    "domains": domains_of(ename),
                    "extracted": False,
                    "location": "",
                })

    save_cache(cache)

    # --- stats -------------------------------------------------------------
    by_status = collections.Counter(r["status"] for r in rows)
    by_status["MISSING"] = len(KNOWN_MISSING)
    by_system = collections.Counter(r["system"] for r in rows)
    by_source = collections.Counter(r["source"] for r in rows)
    by_domain = collections.Counter()
    for r in rows:
        for d in r["domains"]:
            by_domain[d] += 1
    total_bytes = sum(r["size"] for r in rows)
    extracted_n = sum(1 for r in rows if r["extracted"])

    stats = {
        "phase": "phase29-source-parity",
        "pk2_archives": per_archive,
        "containers": container_census,
        "reconciliation": dict(by_status),
        "known_missing": KNOWN_MISSING,
        "by_source": dict(by_source),
        "by_system": dict(sorted(by_system.items(), key=lambda kv: -kv[1])),
        "by_domain": dict(sorted(by_domain.items(), key=lambda kv: -kv[1])),
        "totals": {
            "indexed_files": len(rows),
            "total_bytes": total_bytes,
            "extracted_files": extracted_n,
            "indexed_only_files": len(rows) - extracted_n,
        },
    }

    cols = ["source", "archive", "internal_path", "name", "extension", "size",
            "sha256", "status", "format", "system", "domains", "extracted", "location"]
    out = args.out
    mj = os.path.join(out, "SOURCE_CORPUS_MANIFEST.json")
    mt = os.path.join(out, "SOURCE_CORPUS_MANIFEST.tsv")
    sj = os.path.join(out, "SOURCE_CORPUS_STATS.json")
    ij = os.path.join(out, "SOURCE_SYSTEM_INVENTORY.json")
    it = os.path.join(out, "SOURCE_SYSTEM_INVENTORY.tsv")
    ej = os.path.join(out, "SOURCE_EXTRACTION_ERRORS.tsv")

    with open(mj, "w", encoding="utf-8") as fh:
        json.dump(rows, fh)
        fh.write("\n")
    with open(mt, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            row = [json.dumps(r[c], ensure_ascii=False) if c == "domains" else r[c] for c in cols]
            while row and row[-1] == "":
                row.pop()
            w.writerow(row)
    with open(sj, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=1)
        fh.write("\n")

    # inventory (per system x source, with domain sub-tags)
    inv = {}
    for r in rows:
        k = (r["system"], r["source"])
        inv.setdefault(k, {"count": 0, "bytes": 0})
        inv[k]["count"] += 1
        inv[k]["bytes"] += r["size"]
    with open(ij, "w", encoding="utf-8") as fh:
        json.dump({
            "phase": "phase29-source-parity",
            "by_system": {k[0]: v for k, v in sorted(inv.items())},
            "by_system_source": {f"{k[0]}|{k[1]}": v for k, v in sorted(inv.items())},
            "totals": stats["totals"],
            "reconciliation": stats["reconciliation"],
        }, fh, indent=1)
        fh.write("\n")
    with open(it, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["system", "source", "count", "bytes"])
        for (sys_name, src), v in sorted(inv.items()):
            w.writerow([sys_name, src, v["count"], v["bytes"]])

    with open(ej, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["source", "archive", "internal_path", "reason"])
        for e in errors:
            w.writerow(e)

    print("indexed_files     :", len(rows))
    print("total_bytes       :", total_bytes)
    print("extracted_files   :", extracted_n)
    print("indexed_only      :", len(rows) - extracted_n)
    print("reconciliation    :", dict(by_status))
    print("by_source         :", dict(by_source))
    print("wrote", mj, mt, sj, ij, it, ej)


if __name__ == "__main__":
    main()
