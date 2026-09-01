"""Read-only inventory + normalization of the vSRO 1.193 server textdata.

Walks Media.pk2 `/server_dep/silkroad/textdata/` with the verified PK2 table
reader, decodes every file (UTF-16LE BOM / UTF-8 / cp949), profiles its
tab-schema, and writes:

  TEXTDATA_CATALOG.tsv              every file (encoding, records, schema width)
  TEXTDATA_NORMALIZED_MANIFEST.tsv  per-file decision (normalized / deferred)

For the allowlist it also writes normalized UTF-8 TSV copies under
android/app/src/main/assets/game/textdata/ so the Android app can load real
game data offline. Never modifies the source archives.

Usage:
    python3 scripts/build_textdata_catalog.py --pk2-dir <dir> [--out <repo>] [--assets <dir>]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import pk2_table  # noqa: E402

TEXTDATA_DIR = "/server_dep/silkroad/textdata/"

ALLOWLIST = [
    "characterdata.txt", "itemdata.txt", "skilldata.txt",
    "leveldata.txt", "levelgold.txt",
    "refoptionalteleport.txt", "teleportdata.txt", "teleportlink.txt",
    "teleportbuilding.txt", "regioncode.txt", "npcpos.txt",
    "refshop.txt", "refshopgoods.txt",
    "questdata.txt", "refqusetreward.txt", "refquestrewarditems.txt",
    "worldmap_mapinfo.txt", "worldmap_instanceinfo.txt", "worldmap_localinfo.txt",
    "gameworldconfigdata.txt", "gameworlddata.txt",
]


def decode(raw: bytes):
    if raw[:2] == b"\xff\xfe":
        return raw[2:].decode("utf-16-le"), "utf-16-le"
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8"), "utf-8-sig"
    try:
        return raw.decode("cp949"), "cp949"
    except UnicodeDecodeError:
        replaced = raw.decode("cp949", errors="replace")
        if replaced.count("\ufffd") <= max(2, len(raw) // 10000):
            return replaced, "cp949"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    return raw.decode("latin-1"), "latin-1"


def split_lines(text: str):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [l for l in text.split("\n") if l.strip()]


def profile(raw: bytes):
    text, enc = decode(raw)
    lines = split_lines(text)
    if not lines:
        return {"encoding": enc, "records": 0, "cols": 0, "rows_exact": 0,
                "rows_other": 0, "max_cols": 0, "ok": True}
    first = lines[0].split("\t")
    ncols = len(first)
    exact = 0
    other = 0
    max_cols = ncols
    for l in lines[1:]:
        n = len(l.split("\t"))
        max_cols = max(max_cols, n)
        if n == ncols:
            exact += 1
        else:
            other += 1
    return {"encoding": enc, "records": len(lines), "cols": ncols,
            "rows_exact": exact, "rows_other": other, "max_cols": max_cols,
            "ok": True}


def build(pk2_dir: Path, out_dir: Path, assets_dir: Path) -> None:
    media = pk2_dir / "Media.pk2"
    files, _dirs = pk2_table.inventory(str(media))
    by_path = {f["path"]: f for f in files}
    target = TEXTDATA_DIR.rstrip("/") + "/"
    names = sorted(
        p[len(target):] for p in by_path if p.startswith(target) and by_path[p]["size"] >= 0
    )

    catalog = []
    manifest = []
    normalized_dir = assets_dir / "textdata"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        f = by_path[target + name]
        with open(media, "rb") as fh:
            fh.seek(f["pos"])
            raw = fh.read(f["size"])
        prof = profile(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if "enc" in name.lower() and f["size"] > 65536:
            status = "ENCRYPTED"
        elif prof["encoding"] == "latin-1":
            if prof["cols"] > 1 and prof["records"] > 0:
                status = "NORMALIZED" if name in ALLOWLIST else "TEXT"
            else:
                status = "UNREADABLE"
        elif name in ALLOWLIST:
            status = "NORMALIZED"
        else:
            status = "CATALOGED"
        catalog.append((name, f["size"], prof["encoding"], prof["records"],
                        prof["cols"], prof["rows_exact"], prof["rows_other"],
                        prof["max_cols"], status, sha))
        manifest.append((name, f["size"], sha, status))
        if status == "NORMALIZED":
            text, _enc = decode(raw)
            (normalized_dir / (name[:-4] + ".tsv")).write_text(text, encoding="utf-8")

    catalog.sort(key=lambda r: r[0])
    with open(out_dir / "TEXTDATA_CATALOG.tsv", "w", encoding="utf-8") as fh:
        fh.write("file\tbytes\tencoding\trecords\tcols\trows_exact\trows_other\tmax_cols\tstatus\tsha256\n")
        for row in catalog:
            fh.write("\t".join(str(x) for x in row) + "\n")

    with open(out_dir / "TEXTDATA_NORMALIZED_MANIFEST.tsv", "w", encoding="utf-8") as fh:
        fh.write("file\tbytes\tsha256\tstatus\n")
        for row in sorted(manifest, key=lambda r: r[0]):
            fh.write("\t".join(str(x) for x in row) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    ap.add_argument("--out", default=str(REPO))
    ap.add_argument("--assets", default=str(REPO / "android" / "app" / "src" / "main" / "assets" / "game"))
    args = ap.parse_args()
    if not args.pk2_dir:
        ap.error("--pk2-dir or SRO_PK2_DIR is required")
    build(Path(args.pk2_dir), Path(args.out), Path(args.assets))


if __name__ == "__main__":
    main()
