#!/usr/bin/env python3
"""Build the Android asset dependency graph (Phase 13 Part N).

Emits ANDROID_ASSET_DEPENDENCY_GRAPH.json describing the PROVEN references
between the runtime assets the Android client consumes. Every edge is backed
by a Phase 12/13 verification and carries its status + evidence; nothing is
invented. Two edge families are merged:

  1. textdata joins  — reproduced from the committed DATA_REFERENCE_GRAPH.json
     (id/code columns joined against each other or against archive listings).
  2. asset chain    — format-level references proven from real bytes:
       .o2 -> object.ifo -> .bsr -> {.bmt -> .ddj, .bms}
       characterdata -> .bsr (model column)
       .ddj -> DDS (20-byte header), .ban/.bsk -> skeleton bones, etc.

Run: python3 scripts/build_asset_dependency_graph.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REF_GRAPH = REPO / "DATA_REFERENCE_GRAPH.json"
OUT = REPO / "ANDROID_ASSET_DEPENDENCY_GRAPH.json"

# Proven format-level edges. Each maps a source asset kind to the target kind
# it references, with the proof source. Status is VERIFIED only when the
# reference is reproduced from real bytes; otherwise PARTIAL with a note.
ASSET_EDGES = [
    {
        "from": {"kind": ".o2", "role": "object instance overlay (Map.pk2)"},
        "to": {"kind": "object.ifo", "role": "bsr path index (Data.pk2)"},
        "relationship": "nameI index -> bsr path",
        "status": "VERIFIED",
        "evidence": "Phase 13 Part B: 9 distinct bsr refs of const_76x103 resolve via object.ifo",
    },
    {
        "from": {"kind": ".bsr", "role": "mesh resource (JMXVRES)"},
        "to": {"kind": ".bmt", "role": "material (JMXVBMT)"},
        "relationship": "material path string",
        "status": "VERIFIED",
        "evidence": "Phase 13 Part F: bsr header embeds .bmt path (e.g. avatar_w_angel_wing.bmt)",
    },
    {
        "from": {"kind": ".bsr", "role": "mesh resource (JMXVRES)"},
        "to": {"kind": ".bms", "role": "static mesh parts (JMXVBMS)"},
        "relationship": "mesh part path list",
        "status": "VERIFIED",
        "evidence": "Phase 13 Part F: bsr body lists .bms parts (part1/part2)",
    },
    {
        "from": {"kind": ".bmt", "role": "material (JMXVBMT)"},
        "to": {"kind": ".ddj", "role": "texture (JMXVDDJ -> DDS)"},
        "relationship": "bare ddj filename resolved against bmt directory",
        "status": "VERIFIED",
        "evidence": "Phase 13 Part B: bmt ddj refs resolved under /prim/mtrl/... in Data.pk2",
    },
    {
        "from": {"kind": "characterdata_*.txt", "role": "character definitions"},
        "to": {"kind": ".bsr", "role": "character model"},
        "relationship": "model path column (col 52)",
        "status": "VERIFIED",
        "evidence": "Phase 13 Part J: refid 2023 -> npc\\npc\\chinaquest_priest.bsr",
    },
    {
        "from": {"kind": ".ddj", "role": "texture (JMXVDDJ)"},
        "to": {"kind": "DDS", "role": "embedded image"},
        "relationship": "20-byte header + DDS body",
        "status": "VERIFIED",
        "evidence": "Phase 10/12: DDJ_HEADER=20; every .ddj carries a DDS body",
    },
    {
        "from": {"kind": ".ban", "role": "animation (JMXVBAN)"},
        "to": {"kind": "bones", "role": "skeleton bone names"},
        "relationship": "bone name table + quat/pos keyframes",
        "status": "VERIFIED",
        "evidence": "Phase 13 Part D: full .ban layout proven",
    },
    {
        "from": {"kind": ".bsk", "role": "skeleton (JMXVBSK)"},
        "to": {"kind": "bones", "role": "skeleton bone names"},
        "relationship": "embedded bone name table ([root], Bip01*, BoneNN)",
        "status": "VERIFIED",
        "evidence": "Phase 13 Part F: bsk embeds skeleton bone names",
    },
    {
        "from": {"kind": ".nvm", "role": "navmesh (JMXVNVM)"},
        "to": {"kind": "navmesh cells", "role": "navigation grid"},
        "relationship": "flat 8-byte nav-cell records (4 x u16)",
        "status": "PARTIAL",
        "evidence": "Phase 13 Part E: structure proven; record semantics UNKNOWN",
    },
    {
        "from": {"kind": ".efp", "role": "particle effect (JMXVEFF)"},
        "to": {"kind": "commands", "role": "emitter command stream"},
        "relationship": "u32-length-prefixed ASCII command tokens",
        "status": "PARTIAL",
        "evidence": "Phase 13 Part G: command vocabulary proven; params UNKNOWN",
    },
]


def load_reference_edges():
    graph = json.loads(REF_GRAPH.read_text(encoding="utf-8"))
    out = []
    for e in graph["edges"]:
        out.append({
            "from": {
                "kind": e["from"]["dataset"],
                "role": e["from"].get("name", ""),
            },
            "to": {
                "kind": e["to"]["dataset"],
                "role": e["to"].get("name", ""),
            },
            "relationship": "column join",
            "status": e["status"],
            "evidence": f"{e['matched']}/{e['total']} matched; {e.get('note', '')}",
        })
    return out


def build(out: Path):
    edges = load_reference_edges() + ASSET_EDGES
    doc = {
        "description": (
            "Proven references between Android runtime assets (Phase 13 Part N). "
            "Only edges reproduced from real data are present; status VERIFIED "
            "means the reference was reproduced from committed/live bytes, PARTIAL "
            "means the structure is proven but a downstream field is UNKNOWN."
        ),
        "textdata_edges": len(load_reference_edges()),
        "asset_edges": len(ASSET_EDGES),
        "edges": edges,
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


def main():
    ap = argparse.ArgumentParser(description="Build asset dependency graph")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    doc = build(Path(args.out))
    print(f"wrote {args.out}: {len(doc['edges'])} edges "
          f"({doc['textdata_edges']} textdata + {doc['asset_edges']} asset)")


if __name__ == "__main__":
    main()
