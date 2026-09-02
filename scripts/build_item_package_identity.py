#!/usr/bin/env python3
"""Extract the merchant-scoped itemdata package-join table.

Reads live Media.pk2 itemdata_*.txt (col1 id, col2 ITEM_* code, col52 model
path, col54 icon path — the proven identity anchors) and emits a UTF-8 TSV
covering every distinct ITEM_* code reached by stripping the leading
"PACKAGE_" prefix from NPC-merchant refshopgoods.tsv stock (1233/1233 rows,
784 unique).

Nothing else is copied. Unproven columns (SN_* language keys, prices, stats)
are not emitted. refscrapofpackageitem is NOT used: 854/1233 merchant stock
rows map PACKAGE_* to a different ITEM_* than prefix-strip, so scrap contents
remain UNKNOWN. The committed stub itemdata.tsv (source-file index) is not
overwritten.

316/318 is the refquestrewarditems.tsv -> itemdata col2 join (2 unmatched:
ITEM_QNO_EU_CONS_12_02 and the 'xxx' placeholder) and is not merchant stock.
"""
from __future__ import annotations

from pathlib import Path

from shop_merchant_evidence import build as build_merchants

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
ASSETS = REPO / "android" / "app" / "src" / "main" / "assets" / "game" / "textdata"
LIVE = Path("/tmp/opencode/textdata")
OUT = ASSETS / "item_package_identity.tsv"
PACKAGE_PREFIX = "PACKAGE_"


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return raw[2:].decode("utf-16-le")
    if raw[:2] == b"\xfe\xff":
        return raw[2:].decode("utf-16-be")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8")
    return raw.decode("utf-8")


def load_live_itemdata():
    by_code = {}
    sources = {}
    for path in sorted(LIVE.glob("itemdata_*.txt")):
        for line in _decode(path).splitlines():
            row = line.split("\t")
            if len(row) <= 54 or not row[2].startswith("ITEM_"):
                continue
            code = row[2].strip()
            if code in by_code:
                continue
            if not row[1].strip().isdigit():
                continue
            by_code[code] = (int(row[1]), row[52].strip(), row[54].strip())
            sources[code] = path.name
    return by_code, sources


def wanted_item_codes():
    wanted = []
    seen = set()
    ev = build_merchants()
    for m in ev["merchants"]:
        for t in m["tabs"]:
            for s in t["stock"]:
                pkg = s["item_code"]
                if not pkg.startswith(PACKAGE_PREFIX):
                    raise SystemExit("goods code is not PACKAGE_: %s" % pkg)
                code = pkg[len(PACKAGE_PREFIX):]
                if not code.startswith("ITEM_"):
                    raise SystemExit("stripped goods code is not ITEM_*: %s" % pkg)
                if code not in seen:
                    seen.add(code)
                    wanted.append(code)
    return wanted


def build():
    if not LIVE.is_dir():
        raise SystemExit("live textdata not present: %s" % LIVE)
    live, sources = load_live_itemdata()
    wanted = wanted_item_codes()
    missing = [c for c in wanted if c not in live]
    if missing:
        raise SystemExit("itemdata missing codes: %s" % missing)
    rows = []
    for code in wanted:
        item_id, model, icon = live[code]
        rows.append((code, item_id, model, icon, sources[code]))
    return rows


def write(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        for code, item_id, model, icon, _src in rows:
            fh.write("%s\t%d\t%s\t%s\n" % (code, item_id, model, icon))
    return OUT


def main() -> None:
    rows = build()
    path = write(rows)
    print("wrote %s (%d identities)" % (path, len(rows)))


if __name__ == "__main__":
    main()
