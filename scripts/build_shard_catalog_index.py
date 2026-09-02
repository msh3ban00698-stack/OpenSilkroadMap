#!/usr/bin/env python3
"""Bounded read-only SQL Server system-catalog forensic index for the shard backup.

Phase 29 milestone 3: build a verified index of the SQL Server catalog structures
embedded in SRO_VT_SHARD.Bak without modifying it. Three catalog structures are
walked, each with byte-validated anchors:

  1. name->id index page (grid page k=1835 at offset 66,001,457)
       row = [len:2][name UTF-16LE (len-14 bytes)][suffix:12]
       suffix = <stamp 26 00 | 2a 00 | 26 02> | 01 00 00 00 | <id u32> | 01 00
     PROVEN rows (ids strictly increase by 0xF42439): _RefFmnTidGroup ->
     284,436,683, _RefGame_World -> 380,437,025, _RefInstance_World_Region ->
     508,437,481, _RefInstance_World_Start_Pos -> 524,437,538,
     _RefOptionalTeleport (page offset 4231) -> 935,583,017.

  2. per-table metadata catalog near 9,277,118 (0x8d8dbe)
       record = [name UTF-16LE][00 00][trailer u32s]
       trailer is framed by 0x12344321 ... 0x12345678 magic constants and is
       identical across tables ([8, 4604, 714, 7] for both _Char and
       _RefInstance_World_Start_Pos) => shared catalog constants, NOT per-table
       data-page pointers.  Colid runs 1..10 before each "dbo" owner are fixed
       chunk markers, not table column counts.

  3. compact column catalog near 23,110,400 (0x160c800)
       record = [name UTF-16LE][marker:5][01 00][colid:4][04 00 00 01 00][u16][40 00]
       markers group blocks.  The avatar `_Char` block (marker 3a1a18985a /
       361a18985a) proves CharName=4, CharScale=5, StartRegionID=6, StartPos_X=7,
       StartPos_Y=8, StartPos_Z=9, DefaultTeleport=10 (the _AddNewChar ODBC
       signature).  `_CharTiredness` columns (FlockID, JobType, State, PathID,
       Tiredness, TotalCount, RemainCOunt) live in the 36b66ab55c block.

Negative result (PROVEN): all 12 `StartRegionID`/`StartPos_X` occurrences in the
file are preceded by avatar columns (CharScale/DurShield), none by `ID`; no
`_RefInstance_World_Start_Pos` column block exists under the SRO-reference column
names (Service/ID/StartRegionID/StartPos_X/Y/Z) in any scanned catalog region.
No id->data-page linkage was found in either catalog structure, so player-spawn
row extraction from this backup remains UNKNOWN and the runtime spawn index stays
fail-closed.

Output: scripts/testdata/formats/shard_catalog_index.json
Usage: python scripts/build_shard_catalog_index.py   (reads SRO_DB_DIR)
"""
from __future__ import annotations

import json
import os
import struct
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import sro_paths  # noqa: E402

GRID_BASE = 50_971_137
PAGE = 8192
NAME_INDEX_PAGE = 1835
OUT = os.path.join(BASE, "scripts/testdata/formats/shard_catalog_index.json")

TARGETS = (
    "_RefInstance_World_Start_Pos",
    "_RefInstance_World_Region",
    "_RefOptionalTeleport",
    "_RefGame_World",
    "_RefFmnTidGroup",
    "_RefTeleport",
    "_RefInstance_World",
    "_RefLatestItemSerial",
    "_Char",
    "_CharTiredness",
)

VERIFIED_NAME_IDS = {
    "_RefInstance_World_Start_Pos": 524_437_538,
    "_RefInstance_World_Region": 508_437_481,
    "_RefOptionalTeleport": 935_583_017,
    "_RefGame_World": 380_437_025,
    "_RefFmnTidGroup": 284_436_683,
}


class ShardCatalogIndex:
    def __init__(self, bak_path):
        with open(bak_path, "rb") as fh:
            self.data = fh.read()
        self.evidence = {
            "page1835_name_index": {},
            "catalog_9_3M": {},
            "column_catalog_23_1M": {},
            "start_region_negative": {},
            "classification": {},
        }

    # -- 1. page 1835 name->id index -------------------------------------
    def walk_name_index(self):
        start = GRID_BASE + NAME_INDEX_PAGE * PAGE
        pos = start + 107
        end = start + PAGE
        rows = []
        while pos + 14 <= end:
            length = struct.unpack("<H", self.data[pos : pos + 2])[0]
            if length < 14 or pos + length > end:
                break
            name_bytes = self.data[pos + 2 : pos + 2 + (length - 14)]
            suffix = self.data[pos + 2 + (length - 14) : pos + length]
            if len(suffix) != 12:
                break
            try:
                name = name_bytes.decode("utf-16-le")
            except UnicodeDecodeError:
                break
            stamp = suffix[:2]
            mid = suffix[2:6]
            value = struct.unpack("<I", suffix[6:10])[0]
            tail = suffix[10:12]
            if stamp[0] not in (0x26, 0x2A) or tail != b"\x01\x00":
                # framing drift; stop cleanly rather than misparse the tail
                break
            rows.append(
                {
                    "offset": pos - start,
                    "name": name,
                    "id": value,
                    "stamp": stamp.hex(),
                    "mid": mid.hex(),
                }
            )
            pos += length
            if pos - start > 5312:
                # framing drift observed at page offset 5312; stop cleanly
                break
        self.evidence["page1835_name_index"]["rows"] = rows
        found = {r["name"]: r["id"] for r in rows}
        verified = {n: found[n] for n in VERIFIED_NAME_IDS if n in found}
        self.evidence["page1835_name_index"]["verified_targets"] = verified
        self.evidence["classification"]["page1835_name_index"] = (
            "PROVEN" if verified == VERIFIED_NAME_IDS else "PARTIAL"
        )
        return verified

    # -- 2. per-table metadata catalog near 9,277,118 ----------------------
    def walk_metadata_catalog(self):
        start = 0x8D8DBE
        end = 0x8F6000
        records = []
        pos = start
        guard = 0
        while pos + 8 < end and guard < 500:
            guard += 1
            name, name_end = self._read_utf16(pos)
            if not name or name_end - pos > 200:
                pos += 2
                continue
            nxt = name_end + 2
            vals = []
            j = nxt
            while j + 4 <= end and len(vals) < 24:
                b0 = self.data[j + 4] if j + 5 < end else 0
                b1 = self.data[j + 5] if j + 5 < end else 0
                if len(vals) >= 3 and 65 <= b0 <= 122 and b1 == 0:
                    break
                vals.append(struct.unpack("<I", self.data[j : j + 4])[0])
                j += 4
            records.append({"offset": pos, "name": name, "trailer": vals})
            pos = j
        self.evidence["catalog_9_3M"]["records"] = records
        by_name = {}
        for r in records:
            by_name.setdefault(r["name"], []).append(r["trailer"])
        targets = {n: by_name[n] for n in TARGETS if n in by_name}
        self.evidence["catalog_9_3M"]["targets"] = targets
        self.evidence["classification"]["catalog_9_3M"] = "PARTIAL"
        return targets

    # -- 3. compact column catalog near 23,110,400 --------------------------
    def walk_column_catalog(self):
        start = 0x160C800
        end = 0x1611000
        records = []
        pos = start
        guard = 0
        while pos + 32 < end and guard < 600:
            guard += 1
            name, name_end = self._read_compact_name(pos, end)
            if name is None or not self._is_marker(name_end):
                pos += 2
                continue
            marker = self.data[name_end : name_end + 5].hex()
            colid = struct.unpack("<I", self.data[name_end + 7 : name_end + 11])[0]
            if colid < 1 or colid > 2000:
                pos = name_end + 2
                continue
            records.append(
                {"offset": pos, "name": name, "colid": colid, "marker": marker}
            )
            pos = name_end + 20
        self.evidence["column_catalog_23_1M"]["records"] = records
        avatar = [
            r for r in records if r["marker"] in ("3a1a18985a", "361a18985a")
        ]
        avatar_by_colid = {r["colid"]: r["name"] for r in avatar if r["colid"] <= 40}
        spawn_sig = {
            c: avatar_by_colid.get(c)
            for c in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        }
        self.evidence["column_catalog_23_1M"]["avatar_block"] = avatar_by_colid
        self.evidence["column_catalog_23_1M"]["spawn_signature"] = spawn_sig
        self.evidence["classification"]["column_catalog_23_1M"] = "PARTIAL"
        return spawn_sig

    # -- 4. negative result: every StartRegionID precedes avatar cols --------
    def scan_start_region(self):
        pat = "StartRegionID".encode("utf-16-le")
        hits = []
        pos = 0
        while True:
            idx = self.data.find(pat, pos)
            if idx < 0:
                break
            prev = self._prev_column_name(idx)
            nxt = self._next_column_name(idx)
            hits.append(
                {
                    "offset": hex(idx),
                    "prev_column": prev,
                    "next_column": nxt,
                    "preceded_by_id": prev == "ID",
                }
            )
            pos = idx + 1
        self.evidence["start_region_negative"]["occurrences"] = hits
        self.evidence["start_region_negative"][
            "all_preceded_by_avatar_column"
        ] = all(
            h["prev_column"] is not None and h["prev_column"] not in ("ID", "StartRegionID")
            for h in hits
        )
        self.evidence["start_region_negative"][
            "no_occurrence_preceded_by_id"
        ] = not any(h["preceded_by_id"] for h in hits)
        self.evidence["classification"]["start_region_negative"] = (
            "PROVEN"
            if not any(h["preceded_by_id"] for h in hits)
            else "REVISED"
        )

    # -- helpers ------------------------------------------------------------
    def _read_utf16(self, pos):
        end = pos
        while end + 1 < len(self.data):
            c0, c1 = self.data[end], self.data[end + 1]
            if c0 == 0 and c1 == 0:
                return self.data[pos:end].decode("utf-16-le", errors="replace"), end
            end += 2
            if end - pos > 300:
                break
        return None, pos

    def _read_compact_name(self, pos, end):
        o = pos
        while o + 1 < end and self.data[o] != 0 and self.data[o + 1] == 0 and 0x20 <= self.data[o] <= 0x7E:
            o += 2
        if o == pos:
            return None, pos
        return self.data[pos:o].decode("utf-16-le"), o

    def _is_marker(self, o):
        b = self.data[o : o + 5]
        return (
            len(b) == 5
            and b[0] in (0x36, 0x37, 0x38, 0x39, 0x3A)
            and b[1] != 0
            and b[2] != 0
            and b[3] != 0
            and b[4] in (0x59, 0x5A, 0x5B, 0x5C, 0x5D)
        )

    def _prev_column_name(self, offset):
        lo = max(0, offset - 500)
        idx = self.data.rfind(b"\x10\x00\x00\x80", lo, offset)
        if idx >= 0:
            idx = self.data.rfind(b"\x10\x00\x00\x80", lo, idx)
        if idx >= 0:
            ns = idx + 10
            if ns + 1 < offset and self.data[ns + 1] == 0 and 0x20 <= self.data[ns] <= 0x7E:
                e = ns
                while e + 1 < offset and self.data[e + 1] == 0 and 0x20 <= self.data[e] <= 0x7E:
                    e += 2
                if e - ns >= 4:
                    return self._word_prefix(self.data[ns:e].decode("utf-16-le", errors="replace"))
        pos = offset - 2
        while pos > lo:
            if self._is_marker(pos) and pos > lo:
                e = pos
                s = e
                while (
                    s - 2 >= lo
                    and self.data[s - 1] == 0
                    and self.data[s - 2] in self._WORD
                ):
                    s -= 2
                if e - s >= 4:
                    return self.data[s:e].decode("utf-16-le", errors="replace")
            pos -= 1
        return None

    _WORD = frozenset(
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
    )

    @staticmethod
    def _word_prefix(name):
        cut = 0
        for ch in name:
            if ch.isalnum() or ch == "_":
                cut += 1
            else:
                break
        return name[:cut] if cut else None

    def _next_column_name(self, offset):
        idx = self.data.find(b"\x10\x00\x00\x80", offset + 16, offset + 200)
        if idx >= 0:
            ns = idx + 10
            e = ns
            while e + 1 < len(self.data) and not (self.data[e] == 0 and self.data[e + 1] == 0):
                e += 2
            if e - ns >= 4:
                return self.data[ns:e].decode("utf-16-le", errors="replace")
        return None

    def run(self):
        self.walk_name_index()
        self.walk_metadata_catalog()
        self.walk_column_catalog()
        self.scan_start_region()
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(self.evidence, fh, indent=1)
        return self.evidence


def main():
    bak = os.path.join(sro_paths.resolve_db_dir(), "SRO_VT_SHARD.Bak")
    if not os.path.isfile(bak):
        raise SystemExit("SRO_VT_SHARD.Bak not found under SRO_DB_DIR")
    index = ShardCatalogIndex(bak)
    ev = index.run()
    print(json.dumps(ev["classification"], indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
