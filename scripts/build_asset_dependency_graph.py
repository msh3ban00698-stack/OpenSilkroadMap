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
        "from": {"kind": ".bsr", "role": "character resource (JMXVRES)"},
        "to": {"kind": ".ban/.bsk", "role": "animation + skeleton refs"},
        "relationship": "u32-length-prefixed path groups (bmt/bms/ban/bsk/efp/wav)",
        "status": "VERIFIED",
        "evidence": "Phase 18: bandit.bsr -> 3 bmt + 3 bms + 18 ban + 1 bsk; chinaquest_priest.bsr -> 1 bmt + 3 bms + 2 ban + 1 bsk; every ban/bsk path resolves in Data.pk2",
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
        "evidence": "Phase 13 Part J: refid 2023 -> npc\\npc\\chinaquest_priest.bsr; Phase 18: refid 1949 -> mob\\china\\bandit.bsr (3 world spawns on committed sector 156x90)",
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
        "evidence": "Phase 18: bsk_decoder byte-exhausts 1034/1035 nonzero Data.pk2 .bsk (1 outlier mob_select.bsk); bandit.bsk = 35 bones, chinaman_skel = 38; mesh-local bone names subset of skeleton names",
    },
    {
        "from": {"kind": ".bms", "role": "skinned/flagged vertices (flags==2)"},
        "to": {"kind": "skeleton", "role": "external bone/palette reference"},
        "relationship": "6 B skin record per vertex in bone section [u8 b1][u16 w1][u8 b2][u16 w2]; 0xFF sentinel; name-based bone mapping",
        "status": "VERIFIED",
        "evidence": "Phase 18: skin block s2-s1 == 6*vcount byte-exhausts on every character mesh (bandit part1 214, part2 556, sword 76; man_pelvis 79); skinned_vertex_count == flags==2 count; tail u32@36 = global palette index beyond skeleton (semantics UNKNOWN)",
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
    {
        "from": {"kind": "world_index.tsv", "role": "sector inventory entry"},
        "to": {"kind": ".hg", "role": "committed terrain height grid (VSHG v1)"},
        "relationship": "inventoried asset (size/min/max/sha256)",
        "status": "VERIFIED",
        "evidence": "Phase 10/15: 23 committed sectors, each derived read-only from a real Map.pk2 /{sy}/{sx}.m",
    },
    {
        "from": {"kind": ".hg", "role": "committed terrain sector"},
        "to": {"kind": "world_regions.tsv", "role": "region sector window"},
        "relationship": "sector within region window",
        "status": "VERIFIED",
        "evidence": "Phase 15: Jangan_Field ref sector 156x89; committed 156x89 + 156x90 fall inside window sx 156..182, sy 89..102",
    },
    {
        "from": {"kind": "npcpos.tsv", "role": "world spawn region_code"},
        "to": {"kind": ".hg", "role": "committed terrain sector"},
        "relationship": "spawn placement on committed terrain",
        "status": "VERIFIED",
        "evidence": "Phase 15: 3 world spawns resolve to committed sector 156x90, 0 to 156x89; worldCount 14800, dungeonCount 3657",
    },
    {
        "from": {"kind": ".o2", "role": "object instance overlay (Map.pk2)"},
        "to": {"kind": ".m", "role": "terrain sector (Map.pk2)"},
        "relationship": "per-sector object overlay",
        "status": "VERIFIED",
        "evidence": "Phase 17: walker from offset 16 consumes every one of the 4348 .o2 files exactly; record = [u16 cnt][cnt x 30 B], positions local to the (tx,tz) tail sector",
    },
    {
        "from": {"kind": ".bms", "role": "static mesh (JMXVBMS)"},
        "to": {"kind": "vertices+triangles", "role": "position/normal/uv[/uv2] + u16 index buffer"},
        "relationship": "s0 vertex records (stride = (s1-s0-4)/vcount) + s2 triangles",
        "status": "VERIFIED",
        "evidence": "Phase 16: 44 B standard layout (17,247 files) and 52 B lightmap layout (5,399) proven from live bytes; indices within vertex_count; AABB matches vertices",
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
