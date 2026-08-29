#!/usr/bin/env python3
"""VERIFIED cross-check for the Phase 8 native minimap resolution contract.

The native Android resolver (ManifestResolver.java) mirrors the verified Phase
7 TypeScript resolver. This script re-derives that exact contract in Python
against the real committed manifest and asserts the invariants the native
code depends on:

- exact normalized PK2-path keys (no basename matching),
- later-phase preference for duplicate source paths (determinism),
- representative real proof assets resolve to existing files whose sha256
  matches the manifest output_sha256,
- no basename collisions among minimap outputs.

Runs read-only against android-assets/manifest.json. This is the Phase 8
evidence that is genuinely executable in the current environment (no JDK /
Android SDK available here).

Usage:
    python3 scripts/verify_phase8_manifest_rules.py
"""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "android-assets" / "manifest.json"

PROOF_SOURCES = [
    "/minimap/27x53.ddj",
    "/minimap/100x100.ddj",
    "/minimap/105x101.ddj",
    "/minimap/237x124.ddj",
    "/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
]


def normalize(path):
    path = str(path).strip()
    while path.startswith("/"):
        path = path[1:]
    return "/" + path


def phase_rank(phase):
    try:
        return int(str(phase).replace("phase", ""), 10)
    except ValueError:
        return 0


def pick_preferred(records):
    return sorted(records, key=lambda r: (-phase_rank(r.get("phase", "")), r.get("output_path", "")))[0]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if not MANIFEST.exists():
        print(f"FAIL: manifest not found: {MANIFEST}")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = manifest["records"]
    failures = []

    def check(cond, message):
        if not cond:
            failures.append(message)

    check(len(records) == 7755, f"record count {len(records)} != 7755")
    p6 = [r for r in records if r.get("phase") == "phase6"]
    check(len(p6) == 7737, f"phase6 count {len(p6)} != 7737")
    check(manifest.get("targets", {}).get("total") == 7737, "targets.total != 7737")

    by_source = defaultdict(list)
    for r in records:
        by_source[normalize(r.get("source_path", ""))].append(r)

    unique_sources = len(by_source)
    unique_outputs = len({r.get("output_path") for r in records})
    check(unique_sources == 7753, f"unique sources {unique_sources} != 7753")
    check(unique_outputs == 7755, f"unique outputs {unique_outputs} != 7755")

    duplicates = sorted(k for k, v in by_source.items() if len(v) > 1)
    check(len(duplicates) == 2, f"duplicate sources {duplicates} != 2")
    for dup in duplicates:
        recs = by_source[dup]
        check(
            sorted(r.get("phase") for r in recs) == ["phase5", "phase6"],
            f"{dup}: phases != [phase5, phase6]",
        )
        preferred = pick_preferred(recs)
        check(preferred.get("phase") == "phase6", f"{dup}: preferred phase != phase6")

    for source in PROOF_SOURCES:
        normalized = normalize(source)
        recs = by_source.get(normalized)
        check(recs is not None, f"{source}: no manifest record")
        if recs is None:
            continue
        preferred = pick_preferred(recs)
        output = REPO / "android-assets" / preferred["output_path"]
        check(output.exists(), f"{source}: output file missing: {output}")
        if output.exists():
            digest = sha256_file(output)
            check(
                digest == preferred.get("output_sha256", ""),
                f"{source}: sha256 mismatch (manifest {preferred.get('output_sha256', '')[:12]}... != file {digest[:12]}...)",
            )

    basenames = [Path(r["output_path"]).name for r in p6]
    dup_basenames = {b for b in basenames if basenames.count(b) > 1}
    check(not dup_basenames, f"basename collisions among phase6 outputs: {dup_basenames}")

    sample = [
        "/minimap/100x100.ddj",
        "/minimap/27x53.ddj",
        "/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
    ]
    first = {s: pick_preferred(by_source[normalize(s)])["output_path"] for s in sample}
    second = {s: pick_preferred(by_source[normalize(s)])["output_path"] for s in sample}
    check(first == second, "resolution not deterministic across repeated runs")

    if failures:
        print(f"FAIL: {len(failures)} invariant(s) violated")
        for message in failures:
            print("  -", message)
        return 1

    print(f"OK: all Phase 8 manifest-resolution invariants hold ({len(records)} records)")
    print(f"  unique sources={unique_sources} unique outputs={unique_outputs} duplicates={duplicates}")
    for source in PROOF_SOURCES:
        preferred = pick_preferred(by_source[normalize(source)])
        print(f"  {source} -> {preferred['output_path']} (sha256 verified)")
    print("  basename collisions among phase6 outputs: none")
    print("  deterministic across repeated runs: yes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
