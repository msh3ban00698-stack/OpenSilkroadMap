#!/usr/bin/env python3
"""Merge the Phase 5 proof manifest and the Phase 6 bulk manifest into one
authoritative `android-assets/manifest.json`.

Phase 5 and Phase 6 used slightly different record schemas. This script emits a
superset schema so that BOTH the Phase 5 and Phase 6 test suites can read it:

- every record keeps ALL of its original fields (so per-phase extras such as
  `sample_rate`/`channels`/`bits` on audio, `mipmaps`, `logical_width` survive);
- alias keys are added so records are uniform: `output` == `output_path`,
  `status` == `result`, plus `phase`, `source_pk2`, `validation_status`;
- top-level `failures` (count of non-ok) is present for the Phase 5 suite.

It is read-only with respect to the PK2 archives and never rewrites the
original manifests.

Usage:
    python3 scripts/merge_android_manifests.py \
        --phase5 android-assets/manifest.json \
        --phase6 /tmp/manifest.bulk.json \
        --out android-assets/manifest.json
"""

import argparse
import json


def normalize(rec, phase):
    out = dict(rec)
    out["phase"] = phase
    if "output" not in out and "output_path" in out:
        out["output"] = out["output_path"]
    if "output_path" not in out and "output" in out:
        out["output_path"] = out["output"]
    if "status" not in out and "result" in out:
        out["status"] = out["result"]
    if "result" not in out and "status" in out:
        out["result"] = out["status"]
    if "source_pk2" not in out and "pk2" in out:
        out["source_pk2"] = out["pk2"]
    out["validation_status"] = "PASS" if out.get("status") == "ok" else "FAIL"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase5", required=True, help="Phase 5 manifest.json")
    ap.add_argument("--phase6", required=True, help="Phase 6 bulk manifest.json")
    ap.add_argument("--out", required=True, help="merged output path")
    args = ap.parse_args()

    phase5 = json.load(open(args.phase5))
    phase6 = json.load(open(args.phase6))

    records = [normalize(r, "phase5") for r in phase5.get("records", [])]
    records += [normalize(r, "phase6") for r in phase6.get("records", [])]

    ok = sum(1 for r in records if r.get("status") == "ok")
    failed = sum(1 for r in records if r.get("status") == "failed")
    unknown = sum(1 for r in records if r.get("status") == "unknown")

    merged = {
        "schema": "sro-android-assets-v2",
        "phases": ["phase5", "phase6"],
        "archive": phase6.get("archive", "Media.pk2"),
        "targets": phase6.get("targets", {}),
        "pk2_snapshot": phase6.get("pk2_snapshot"),
        "batches": phase6.get("batches", []),
        "records": records,
        "summary": {
            "total": len(records),
            "ok": ok,
            "failed": failed,
            "unknown": unknown,
        },
        "failures": failed,
    }
    with open(args.out, "w") as f:
        json.dump(merged, f, indent=1)
    print(
        "merged %d records (phase5=%d, phase6=%d) -> %s"
        % (len(records), len(phase5.get("records", [])), len(phase6.get("records", [])), args.out)
    )


if __name__ == "__main__":
    main()
