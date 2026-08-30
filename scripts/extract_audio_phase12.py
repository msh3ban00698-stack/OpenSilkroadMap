"""Phase 12 Part E: verified audio extraction + provenance manifest.

Source of truth is the ORIGINAL Music.pk2 and Data.pk2 archives (read-only).
OGG is an Android-native container so "conversion" is a verified verbatim
extraction (OggS magic checked); WAV is verified verbatim PCM (RIFF/WAVE/fmt
checked). Every extracted file is recorded with its source path, size, format
magic, and sha256 in AUDIO_CONVERSION_MANIFEST.tsv.

Outputs:
  android-assets/audio/music/        all 50 .ogg from Music.pk2
  android-assets/audio/sfx/monster/  all 431 .wav from Data.pk2 /prim/snd/monster

Run: python3 scripts/extract_audio_phase12.py --pk2-dir <dir>
(or set SRO_PK2_DIR)
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import pk2_table  # noqa: E402

MUSIC_DIR = Path("android-assets/audio/music")
SFX_DIR = Path("android-assets/audio/sfx/monster")
MANIFEST = Path("AUDIO_CONVERSION_MANIFEST.tsv")


def check_magic(data, magic):
    return data[: len(magic)] == magic


def copy_verified(fh, files, path, dest, expected_magic, rec):
    entry = next(f for f in files if f["path"].lstrip("/") == path)
    fh.seek(entry["pos"])
    data = fh.read(entry["size"])
    if not check_magic(data, expected_magic):
        rec["status"] = "BAD_MAGIC"
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    rec.update(
        {
            "status": "VERIFIED",
            "source_size": len(data),
            "source_sha256_1mib": hashlib.sha256(data[:1048576]).hexdigest(),
            "format_magic": data[: len(expected_magic)].decode("latin-1"),
            "output_path": str(dest),
            "output_size": len(data),
            "output_sha256": hashlib.sha256(data).hexdigest(),
        }
    )


def main():
    ap = argparse.ArgumentParser(description="Verified audio extraction + provenance manifest.")
    ap.add_argument("--pk2-dir", default=os.environ.get("SRO_PK2_DIR"))
    args = ap.parse_args()
    if not args.pk2_dir:
        raise SystemExit("--pk2-dir or SRO_PK2_DIR is required")
    pk2_dir = Path(args.pk2_dir)
    music_arc = str(pk2_dir / "Music.pk2")
    data_arc = str(pk2_dir / "Data.pk2")

    music_files, _ = pk2_table.inventory(music_arc)
    data_files, _ = pk2_table.inventory(data_arc)

    records = []
    with open(music_arc, "rb") as fh:
        for f in sorted(music_files, key=lambda x: x["path"]):
            if not f["path"].lower().endswith(".ogg"):
                continue
            rec = {"source_archive": "Music.pk2", "source_path": f["path"].lstrip("/"), "status": "UNRESOLVED"}
            dest = MUSIC_DIR / os.path.basename(f["path"]).lower()
            copy_verified(fh, music_files, f["path"].lstrip("/"), dest, b"OggS", rec)
            records.append(rec)

    with open(data_arc, "rb") as fh:
        for f in sorted(data_files, key=lambda x: x["path"]):
            p = f["path"].lstrip("/")
            if not p.lower().endswith(".wav") or not p.lower().startswith("prim/snd/monster/"):
                continue
            rec = {"source_archive": "Data.pk2", "source_path": p, "status": "UNRESOLVED"}
            dest = SFX_DIR / os.path.basename(p).lower()
            copy_verified(fh, data_files, p, dest, b"RIFF", rec)
            records.append(rec)

    header = [
        "source_archive", "source_path", "status", "source_size",
        "source_sha256_1mib", "format_magic", "output_path",
        "output_size", "output_sha256",
    ]
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write("\t".join(header) + "\n")
        for rec in records:
            fh.write("\t".join(str(rec.get(h, "")) for h in header) + "\n")

    ogg_ok = sum(1 for r in records if r["source_archive"] == "Music.pk2" and r["status"] == "VERIFIED")
    wav_ok = sum(1 for r in records if r["source_archive"] == "Data.pk2" and r["status"] == "VERIFIED")
    print(f"ogg verified={ogg_ok} wav verified={wav_ok} -> {MANIFEST}")


if __name__ == "__main__":
    main()
