#!/usr/bin/env python3
"""Read-only PK2 table reader with per-file sizes (Phase 11).

The byte layout is taken VERBATIM from the pk2 crate source that the pinned
pk2_mate binary is built from (Veykril/pk2, `src/format/entry.rs` /
`block_chain.rs` / `chain_index.rs`, pinned in PK2_READER_FOUNDATION.md). It is
NOT re-derived from memory:

    RawPackFileEntry (128 bytes, fixed):
      [0]      u8    ty                 0 = Empty, 1 = Directory, 2 = File
      [1..82]  u8[81] name              null-terminated (EUC-KR)
      [82..90] FILETIME access (u32 dwLow, u32 dwHigh)
      [90..98] FILETIME create
      [98..106] FILETIME modify
      [106..114] u64 position  file: stream offset of data chain;
                               dir: chain offset of children block
      [114..118] u32 size      file: total byte size; dir: 0
      [118..126] u64 next_block  absolute byte offset of next block (0 = none)
      [126..128] u16 padding

    PackBlock = 20 fixed entries x 128 bytes = 2560 bytes.
    Root block chain starts at byte 256 (after the 256-byte header).
    Blocks in a chain are linked via next_block.

This reader only walks the entry table; it NEVER reads file data and NEVER
writes to the archive (read-only). File sizes come directly from the entry's
`size` field, so no data-chain following is required.

Validation: `scripts/test_pk2_table.py` asserts the produced paths/counts match
the pk2_mate `list` output exactly and that extracted sample files match the
entry sizes.
"""

from __future__ import annotations

import struct
from pathlib import Path

PK2_HEADER_LEN = 256
PK2_ENTRY_SIZE = 128
PK2_BLOCK_ENTRY_COUNT = 20
PK2_BLOCK_SIZE = PK2_ENTRY_SIZE * PK2_BLOCK_ENTRY_COUNT

TY_EMPTY = 0
TY_DIRECTORY = 1
TY_FILE = 2

# Joymax PK2 block-table encryption (Phase 11, VERIFIED):
# standard Blowfish-ECB on the entry-table blocks, with the key salted by
# PK2_SALT. Byte order within each 32-bit word is little-endian (matching the
# pinned pk2 crate's blowfish.rs). Validated exactly against the header verify
# bytes (d8 da 30) and by round-trip of real archive entries.
PK2_SALT = bytes((0x03, 0xF8, 0xE4, 0x44, 0x88, 0x99, 0x3F, 0x64, 0xFE, 0x35))

try:  # pycryptodome (dev-time dependency; tests skip if absent)
    from Crypto.Cipher import Blowfish as _BF
    _HAS_BF = True
except Exception:  # pragma: no cover
    _HAS_BF = False


def pk2_blowfish_key(user_key: bytes) -> bytes:
    key = bytearray(user_key[:56])
    base = bytearray(56)
    base[: len(PK2_SALT)] = PK2_SALT
    for i in range(len(key)):
        key[i] ^= base[i]
    return bytes(key)


def _swap_words(chunk: bytes) -> bytes:
    return chunk[3::-1] + chunk[7:3:-1]


def pk2_encrypt_block_table(blob: bytes, user_key: bytes, decrypt: bool = True) -> bytes:
    """ECB on 8-byte blocks with LE word order (verified pk2 semantics).

    Creates one cipher for the whole blob (the key schedule is reused across
    all 8-byte chunks).
    """
    key = pk2_blowfish_key(user_key)
    cipher = _BF.new(key, _BF.MODE_ECB)
    out = bytearray(len(blob))
    for i in range(0, len(blob) - 7, 8):
        w = _swap_words(blob[i:i + 8])
        if decrypt:
            r = cipher.decrypt(w)
        else:
            r = cipher.encrypt(w)
        out[i:i + 8] = _swap_words(r)
    return bytes(out)


def _decode_name(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("cp949", errors="replace")


class Pk2Entry:
    __slots__ = ("ty", "name", "position", "size", "next_block", "access",
                 "create", "modify")

    def __init__(self, ty, name, position, size, next_block, access, create, modify):
        self.ty = ty
        self.name = name
        self.position = position
        self.size = size
        self.next_block = next_block
        self.access = access
        self.create = create
        self.modify = modify

    @property
    def is_directory(self):
        return self.ty == TY_DIRECTORY

    @property
    def is_file(self):
        return self.ty == TY_FILE


def parse_entry(data: bytes) -> Pk2Entry | None:
    if len(data) != PK2_ENTRY_SIZE:
        raise ValueError("entry must be 128 bytes")
    ty = data[0]
    if ty == TY_EMPTY:
        return None
    if ty not in (TY_DIRECTORY, TY_FILE):
        return None
    name = _decode_name(data[1:82])
    access = struct.unpack_from("<II", data, 82)
    create = struct.unpack_from("<II", data, 90)
    modify = struct.unpack_from("<II", data, 98)
    position, size = struct.unpack_from("<QI", data, 106)
    next_block = struct.unpack_from("<Q", data, 118)[0]
    return Pk2Entry(ty, name, position, size, next_block, access, create, modify)


def iter_blocks(fh, start_offset, user_key=b"169841"):
    """Yield (block_offset, [entry,...]) chains starting at start_offset.

    Entry-table blocks are Blowfish-encrypted (verified); each 2560-byte block
    is decrypted before parsing. File data is NOT encrypted.
    """
    offset = start_offset
    visited = set()
    while offset and offset not in visited:
        visited.add(offset)
        fh.seek(offset)
        block = fh.read(PK2_BLOCK_SIZE)
        if len(block) != PK2_BLOCK_SIZE:
            break
        if _HAS_BF:
            block = pk2_encrypt_block_table(block, user_key)
        entries = []
        next_block = 0
        for i in range(PK2_BLOCK_ENTRY_COUNT):
            e = parse_entry(block[i * PK2_ENTRY_SIZE:(i + 1) * PK2_ENTRY_SIZE])
            if e is not None:
                entries.append(e)
                next_block = e.next_block
        yield offset, entries
        offset = next_block


def inventory(path, progress_cb=None, user_key=b"169841"):
    """Walk a PK2 archive read-only; return (files, dirs).

    files: list of {"path": str, "size": int, "pos": int, "create": (lo,hi),
                    "modify": (lo,hi)}
    dirs:  list of {"path": str, "pos": int}
    """
    files, dirs = [], []
    visited_blocks = set()
    dirs.append({"path": "/", "pos": PK2_HEADER_LEN})

    def walk(dir_path, children_offset, depth):
        for block_offset, entries in iter_blocks(fh, children_offset, user_key):
            if block_offset in visited_blocks:
                continue
            visited_blocks.add(block_offset)
            for e in entries:
                if e.is_directory:
                    if e.name in (".", ".."):
                        continue
                    p = f"{dir_path}/{e.name}"
                    dirs.append({"path": p, "pos": e.position})
                    walk(p, e.position, depth + 1)
                elif e.is_file:
                    p = f"{dir_path}/{e.name}"
                    files.append({
                        "path": p, "size": e.size, "pos": e.position,
                        "create": e.create, "modify": e.modify,
                        "block": block_offset,
                    })

    with open(path, "rb") as fh:
        walk("", PK2_HEADER_LEN, 0)
    files.sort(key=lambda r: r["path"])
    dirs.sort(key=lambda r: r["path"])
    return files, dirs


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", help="path to a .pk2 archive (read-only)")
    ap.add_argument("--out", help="optional JSON output path")
    ap.add_argument("--stats", action="store_true", help="print stats only")
    args = ap.parse_args()

    files, dirs = inventory(args.archive)
    print(f"{Path(args.archive).name}: {len(dirs)} dirs, {len(files)} files")
    if args.stats:
        return
    if args.out:
        json.dump({"archive": args.archive, "files": files, "dirs": dirs},
                  open(args.out, "w"))
    else:
        for d in dirs:
            print(f"D {d['path']}  {d['pos']}")
        for f in files:
            print(f"F {f['path']}  {f['size']}")


if __name__ == "__main__":
    main()
