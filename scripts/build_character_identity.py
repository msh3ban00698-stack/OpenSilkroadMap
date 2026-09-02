#!/usr/bin/env python3
"""Extract the spawn-scoped character identity table.

Reads live Media.pk2 characterdata_*.txt (col1 refid, col2 code, col52 model
path — the three Phase 29 proven anchors) and emits a UTF-8 TSV covering:

  * every distinct npcpos.tsv character_refid (1180/1180)
  * every shopdata.tsv merchant_refid > 0 that is missing from npcpos
    (STORE_AM_SPECIAL / 7568)

Nothing else is copied. Unproven characterdata columns (speed, stats, SN_*)
are not emitted. The committed stub characterdata.tsv (source-file index) is
not overwritten.
"""
from __future__ import annotations

import csv
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
ASSETS = REPO / "android" / "app" / "src" / "main" / "assets" / "game" / "textdata"
LIVE = Path("/tmp/opencode/textdata")
OUT = ASSETS / "character_identity.tsv"


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return raw[2:].decode("utf-16-le")
    if raw[:2] == b"\xfe\xff":
        return raw[2:].decode("utf-16-be")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8")
    return raw.decode("utf-8")


def load_live_characterdata():
    by_refid = {}
    sources = {}
    for path in sorted(LIVE.glob("characterdata_*.txt")):
        for line in _decode(path).splitlines():
            row = line.split("\t")
            if len(row) <= 52 or not row[1].strip().isdigit():
                continue
            refid = row[1].strip()
            if refid in by_refid:
                continue
            by_refid[refid] = (row[2].strip(), row[52].strip())
            sources[refid] = path.name
    return by_refid, sources


def load_wanted_refids():
    wanted = set()
    with open(ASSETS / "npcpos.tsv", encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row or row[0].startswith("#") or row[0].startswith("//"):
                continue
            if row[0].strip().isdigit():
                wanted.add(int(row[0]))
    with open(ASSETS / "shopdata.tsv", encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row or row[0].startswith("#") or row[0].startswith("//"):
                continue
            if len(row) <= 5:
                continue
            try:
                refid = int(row[5])
            except ValueError:
                continue
            if refid > 0:
                wanted.add(refid)
    return wanted


def build():
    if not LIVE.is_dir():
        raise SystemExit("live textdata not present: %s" % LIVE)
    live, sources = load_live_characterdata()
    wanted = load_wanted_refids()
    missing = sorted(rid for rid in wanted if str(rid) not in live)
    if missing:
        raise SystemExit("characterdata missing refids: %s" % missing)
    rows = []
    for rid in sorted(wanted):
        code, model = live[str(rid)]
        rows.append((rid, code, model, sources[str(rid)]))
    return rows


def write(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        for rid, code, model, _src in rows:
            fh.write("%d\t%s\t%s\n" % (rid, code, model))
    return OUT


def main() -> None:
    rows = build()
    path = write(rows)
    print("wrote %s (%d identities)" % (path, len(rows)))


if __name__ == "__main__":
    main()
