"""SRO Map.pk2 object-placement decoders: .o2 (30-byte) and .o (28-byte).

Both extensions share the same magic "JMXVMAPO1001" and the same group-stream
framing; they differ only in record width. .o2 carries an extra zero u16
(unknown3) that .o omits.

Shared file layout (proven from live archives, Phase 17 forensics):

  - 12-byte magic  "JMXVMAPO1001"   (a minority of .o files are empty and use
                                     "JMXVMAPO1000" with a zero payload)
  - u32 @12        == 0 (always observed)
  - group stream from offset 16: repeated  [u16 count][count x record]
    The "variable header" observed in Phase 15 is simply leading zero-count
    groups (pure zero padding); starting the walker at offset 16 yields the
    same instances as starting at the first non-zero byte for every file in a
    4,348-file census (all consume exactly, result-equivalent).

  - instance record (little-endian):
      u32 @0   nameI            (index into navmesh/object.ifo -> .bsr path)
      f32 @4   x                (sector-local coordinate, tail sector)
      f32 @8   y                (height; ~ terrain height for planted objects)
      f32 @12  z                (sector-local coordinate, tail sector)
      u16 @16  unknown0         (0x0000 or 0xFFFF observed; semantics UNKNOWN)
      f32 @18  theta            (Y-axis rotation, radians; 0.0 or real values)
      u16 @22  unknown1         (varies per record; packed grid? UNKNOWN)
      u16 @24  unknown2         (0 observed)
      u16 @26  unknown3         (.o2 only; 0 observed)
      u16 @26  tail             (.o only)
      u16 @28  tail             (.o2 only)

    tail encodings differ between the two extensions:
      .o2 tail = absolute packed sector (tx = tail & 0xFF, tz = tail >> 8);
                equals the file's own sector for non-boundary objects.
      .o  tail = relative offset from the file's own sector: 0 = own sector,
                1 = +x neighbour, 256 = +z neighbour (observed values only).

Positions are LOCAL to sector (tx, tz). World coords follow the proven formula
world = (tail - ref) * 1920 + local (see world_terrain.local_to_world).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

O2_MAGIC = b"JMXVMAPO1001"
O2_HEADER = 16          # magic(12) + u32(4)
O2_RECORD = 30          # bytes per .o2 instance record

#: .o uses the same magic but a 28-byte record (no unknown3).
O_MAGIC = b"JMXVMAPO1001"
#: .o empty placeholder magic (zero payload).
O_EMPTY_MAGIC = b"JMXVMAPO1000"
O_RECORD = 28           # bytes per .o instance record

#: object.ifo magic line observed in Data.pk2/navmesh/object.ifo
IFO_MAGIC = b"JMXVOBJI1000"


class O2FormatError(ValueError):
    pass


@dataclass(frozen=True)
class Placement:
    """A single proven object instance from an .o2 overlay."""

    nameI: int
    x: float
    y: float
    z: float
    theta: float
    tx: int
    tz: int
    unknown0: int
    unknown1: int
    unknown2: int
    unknown3: int

    @property
    def tail(self) -> int:
        return (self.tz << 8) | (self.tx & 0xFF)

    @property
    def is_boundary(self) -> bool:
        """True when the record's coordinate sector is not its own file sector."""
        return self.unknown0 == 0xFFFF

    def local_to_world(self, ref_sx: int, ref_sy: int, sector_world: float = 1920.0):
        """World-space placement relative to a reference sector."""
        return (
            self.x + (self.tx - ref_sx) * sector_world,
            self.y,
            self.z + (self.tz - ref_sy) * sector_world,
        )


def _parse_placements(blob: bytes, record_size: int) -> list[Placement]:
    """Shared group-stream walker (offset 16) for .o2 and .o records."""
    out: list[Placement] = []
    pos = O2_HEADER
    n = len(blob)
    while pos < n:
        if pos + 2 > n:
            break
        cnt = struct.unpack_from("<H", blob, pos)[0]
        pos += 2
        if pos + cnt * record_size > n:
            # malformed tail group: stop (documented, not silently corrupt)
            break
        for _ in range(cnt):
            rec = blob[pos : pos + record_size]
            nameI, x, y, z = struct.unpack_from("<Ifff", rec, 0)
            u0 = struct.unpack_from("<H", rec, 16)[0]
            theta = struct.unpack_from("<f", rec, 18)[0]
            u1 = struct.unpack_from("<H", rec, 22)[0]
            u2 = struct.unpack_from("<H", rec, 24)[0]
            if record_size >= O2_RECORD:
                u3 = struct.unpack_from("<H", rec, 26)[0]
                tail = struct.unpack_from("<H", rec, 28)[0]
            else:
                u3 = 0
                tail = struct.unpack_from("<H", rec, 26)[0]
            out.append(
                Placement(
                    nameI=int(nameI),
                    x=float(x),
                    y=float(y),
                    z=float(z),
                    theta=float(theta),
                    tx=tail & 0xFF,
                    tz=tail >> 8,
                    unknown0=int(u0),
                    unknown1=int(u1),
                    unknown2=int(u2),
                    unknown3=int(u3),
                )
            )
            pos += record_size
    return out


def parse_o2(blob: bytes) -> list[Placement]:
    """Parse an .o2 blob into proven Placement instances (30-byte records)."""
    if not blob.startswith(O2_MAGIC):
        raise O2FormatError("not a .o2 blob (bad magic)")
    return _parse_placements(blob, O2_RECORD)


def parse_o(blob: bytes) -> list[Placement]:
    """Parse an .o blob into proven Placement instances (28-byte records).

    .o shares the JMXVMAPO1001 magic and framing with .o2 but omits the
    always-zero unknown3 u16, so its tail lands at offset 26 instead of 28.
    """
    if not blob.startswith(O_MAGIC):
        raise O2FormatError("not a .o blob (bad magic)")
    return _parse_placements(blob, O_RECORD)


def parse_object_ifo_map(text: str) -> dict[int, str]:
    """Parse object.ifo text into {nameI: bsr_path} (path with forward slashes).

    The first two text lines are magic (JMXVOBJI1000) and the entry count;
    the first quoted path is entry 0 (nameI == position in the quoted list).
    """
    out: dict[int, str] = {}
    idx = 0
    for ln in text.splitlines():
        i = ln.find('"')
        j = ln.rfind('"')
        if i >= 0 and j > i:
            p = ln[i + 1 : j].replace("\\", "/")
            if not p.startswith("/"):
                p = "/" + p
            out[idx] = p
            idx += 1
    return out
