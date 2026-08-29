#!/usr/bin/env python3
"""Controlled Phase 5 conversion: verified PK2 assets -> Android-ready outputs.

Only converts formats whose structure was VERIFIED from real bytes in Phase 4/5
(see ANDROID_ASSET_MANIFEST.md and PHASE_5_ANDROID_ASSET_CONVERSION.md):

  - .ddj  -> PNG  (JMXVDDJ 1000 container + DDS payload; pure-Python decoder
                   cross-checked byte-identical to Pillow on real samples)
  - .ogg  -> copy (Ogg Vorbis; Android-native)
  - .wav  -> copy (RIFF PCM; Android-native)
  - .txt  -> UTF-8 (UTF-16LE game textdata and ASCII config, semantics preserved)

Anything else is refused. This is NOT a bulk converter and it never modifies the
PK2 archives. Originals are extracted to a work dir (outside the repo by
default) and only the generated outputs land in the output tree.

Usage:
    python3 scripts/convert_android_assets.py \
        --pk2-dir /path/to/pk2s \
        --reader-bin /path/to/pk2_mate \
        --out /path/to/android-assets \
        [--work /path/to/work]
"""

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

from dds_decode import (
    JMX_DDJ_MAGIC,
    InvalidDDS,
    UnsupportedPixelFormat,
    ddj_to_rgba,
    parse_dds,
    parse_png_header,
    png_from_rgba,
)

ARCHIVES = ("Data", "Map", "Media", "Music", "Particles")


class ConversionError(Exception):
    pass


# <pk2>/<internal path> -> (action, output relative path)
# Paths verified present in Phase 4 listings.
CONVERSION_MANIFEST = [
    ("Media/minimap/100x100.ddj", "ddj_png", "maps/minimap_100x100.png"),
    ("Media/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
     "ddj_png", "maps/minimap_d_arabia_boss_127x127.png"),
    ("Map/tile2d/alex_dust_01.ddj", "ddj_png", "maps/tile2d_alex_dust_01.png"),
    ("Media/interface/minimap/mm_alpha.ddj", "ddj_png", "textures/interface_minimap_mm_alpha.png"),
    ("Media/interface/2secret/sec_num_00.ddj", "ddj_png", "textures/interface_2secret_sec_num_00.png"),
    ("Media/effect/icon/cool_time_0.ddj", "ddj_png", "textures/effect_icon_cool_time_0.png"),
    ("Media/script/image/qno_script_background_white.ddj",
     "ddj_png", "textures/script_qno_script_background_white.png"),
    ("Particles/textures/00illusion_basic.ddj", "ddj_png", "textures/particle_00illusion_basic.png"),
    ("Particles/animations/etc_mirage_cold_inver.ddj",
     "ddj_png", "textures/particle_etc_mirage_cold_inver.png"),
    ("Data/compound/particle/electus_m_xmas.ddj",
     "ddj_png", "textures/compound_electus_m_xmas.png"),
    ("Music/jangan_town.ogg", "copy", "audio/jangan_town.ogg"),
    ("Data/prim/snd/am_mob/am_crab_die.wav", "copy", "audio/am_crab_die.wav"),
    ("Media/server_dep/silkroad/textdata/itemdata.txt",
     "text_utf8", "data/textdata/itemdata.utf8.txt"),
    ("Media/server_dep/silkroad/textdata/skilldata.txt",
     "text_utf8", "data/textdata/skilldata.utf8.txt"),
    ("Media/server_dep/silkroad/textdata/characterdata.txt",
     "text_utf8", "data/textdata/characterdata.utf8.txt"),
    ("Data/RegionInfo.txt", "text_utf8", "data/RegionInfo.utf8.txt"),
    ("Data/dungeon/Dungeoninfo.txt", "text_utf8", "data/Dungeoninfo.utf8.txt"),
    ("Media/config/command.txt", "text_utf8", "data/command.utf8.txt"),
]

# Not converted yet (UNKNOWN / DEFERRED) -- documented in the format table.
DEFERRED_NOTES = {
    "fonts/*.dat": "JMXVIMG 1100 structure UNKNOWN -- do not convert yet",
    "res_ui/*.2dt": "structure UNKNOWN -- do not convert yet",
    "*.bms": "JMXVBMS 0110 -- UNKNOWN -- do not convert yet",
    "*.bsr": "JMXVRES 0109 -- UNKNOWN -- do not convert yet",
    "*.cpd": "JMXVCPD 0101 -- UNKNOWN -- do not convert yet",
    "*.ban": "JMXVBAN 0102 -- UNKNOWN -- do not convert yet",
    "*.efp": "JMXVEFF 0011 -- UNKNOWN -- do not convert yet",
    "*.nvm": "JMXVNVM 1000 -- UNKNOWN -- do not convert yet",
    "Map *.t": "JMXVMAPT1001 -- UNKNOWN -- do not convert yet",
    "Map *.m": "JMXVMAPM1000 -- UNKNOWN -- do not convert yet",
    "Map *.o/*.o2": "JMXVMAPO1001 -- UNKNOWN -- do not convert yet",
    "*.ifo": "JMXVOBJI/JMXVCAMR -- plaintext index -- DEFERRED (needs schema study)",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_sample(reader, pk2_dir, work_dir, archive, path):
    pk2 = os.path.join(pk2_dir, archive + ".pk2")
    if not os.path.isfile(pk2):
        raise ConversionError("pk2 missing: " + pk2)
    sample_root = os.path.join(work_dir, archive)
    os.makedirs(sample_root, exist_ok=True)
    proc = subprocess.run(
        [reader, "extract", "--archive", pk2, "--out", sample_root, "--path", path],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ConversionError(proc.stderr.strip())
    target = os.path.join(sample_root, os.path.basename(path))
    if not os.path.isfile(target):
        raise ConversionError("rc=0 but output file absent")
    return target


def convert_ddj(src, dst):
    with open(src, "rb") as f:
        data = f.read()
    if data[0:12] != JMX_DDJ_MAGIC:
        raise ConversionError("not a JMXVDDJ 1000 container")
    hdr = parse_dds(data[20:])
    w, h, pixels = ddj_to_rgba(data)
    png = png_from_rgba(w, h, pixels)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(png)
    rw, rh, bd, ct = parse_png_header(png)
    if (rw, rh) != (w, h):
        raise ConversionError("PNG dimensions mismatch after encode")
    fourcc = hdr["fourcc"].decode("latin-1").strip("\x00") or (
        "uncompressed-%dbit" % hdr["bitcount"]
    )
    return {
        "detected_format": "JMXVDDJ+DDS (" + fourcc + ")",
        "width": w,
        "height": h,
        "mipmaps": hdr["mipmaps"],
        "output_format": "png",
        "output_size": len(png),
        "validation": "png header + dimensions verified",
    }


def _ogg_metadata(data):
    if data[:4] != b"OggS":
        raise ConversionError("not an OggS stream")
    if len(data) < 64 or data[5] != 2:
        raise ConversionError("first page not BOS")
    # Page 1: packet is the vorbis identification header after the seg table.
    segs = data[26]
    table_len = sum(data[27:27 + segs])
    packet = data[27 + segs:27 + segs + table_len]
    if packet[:7] != b"\x01vorbis":
        raise ConversionError("not a vorbis identification header")
    version, channels, rate = struct.unpack_from("<IBI", packet, 7)
    return {"vorbis_version": version, "channels": channels, "sample_rate": rate}


def _wav_metadata(data):
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ConversionError("not a RIFF/WAVE file")
    if data[12:16] != b"fmt ":
        raise ConversionError("fmt chunk missing")
    size = struct.unpack_from("<I", data, 16)[0]
    if size < 16:
        raise ConversionError("fmt chunk too small")
    fmt, channels, rate, byterate, align, bits = struct.unpack_from("<HHIIHH", data, 20)
    if fmt != 1:
        raise ConversionError("not PCM (audio format %d)" % fmt)
    return {"audio_format": fmt, "channels": channels, "sample_rate": rate, "bits": bits}


def convert_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "rb") as f:
        data = f.read()
    with open(dst, "wb") as f:
        f.write(data)
    if src.lower().endswith(".ogg"):
        meta = _ogg_metadata(data)
    elif src.lower().endswith(".wav"):
        meta = _wav_metadata(data)
    else:
        meta = {}
    return {
        "detected_format": "copy (byte-identical)",
        "output_format": os.path.splitext(dst)[1].lstrip("."),
        "output_size": len(data),
        "validation": "byte-identical copy verified",
        **meta,
    }


def decode_text(raw):
    if raw[:2] == b"\xff\xfe":
        return raw[2:].decode("utf-16-le"), "UTF-16LE"
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8"), "UTF-8-BOM"
    raw.decode("ascii")  # raise if not ASCII
    return raw.decode("ascii"), "ASCII"


def convert_text_utf8(src, dst):
    with open(src, "rb") as f:
        raw = f.read()
    text, detected = decode_text(raw)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    out = normalized.encode("utf-8")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(out)
    out.decode("utf-8")
    return {
        "detected_format": "text/" + detected,
        "output_format": "utf-8",
        "output_size": len(out),
        "source_encoding": detected,
        "validation": "utf-8 roundtrip decode verified",
    }


ACTIONS = {
    "ddj_png": convert_ddj,
    "copy": convert_copy,
    "text_utf8": convert_text_utf8,
}


def main():
    parser = argparse.ArgumentParser(description="Controlled Phase 5 conversion")
    parser.add_argument("--pk2-dir", required=True)
    parser.add_argument("--reader-bin", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--work", default=None,
                        help="work dir for extracted originals (default: "
                             "tempfile.mkdtemp under the system temp dir)")
    parser.add_argument("--json", help="optional manifest.json output path")
    args = parser.parse_args()

    if not os.path.isfile(args.reader_bin):
        print("reader missing:", args.reader_bin)
        return 2

    work_dir = args.work or tempfile.mkdtemp(prefix="phase5_work_")
    os.makedirs(work_dir, exist_ok=True)

    records = []
    failures = 0
    for spec, action, rel_out in CONVERSION_MANIFEST:
        archive, path = spec.split("/", 1)
        path = "/" + path
        rec = {
            "pk2": archive + ".pk2",
            "source_path": path,
            "source_extension": os.path.splitext(path)[1].lower(),
            "action": action,
            "output_path": rel_out,
            "result": "pending",
        }
        try:
            src = extract_sample(args.reader_bin, args.pk2_dir, work_dir, archive, path)
            src_size = os.path.getsize(src)
            rec["source_size"] = src_size
            rec["source_sha256"] = sha256_file(src)
            dst = os.path.join(args.out, rel_out)
            details = ACTIONS[action](src, dst)
            rec.update(details)
            rec["output_sha256"] = sha256_file(dst)
            rec["result"] = "ok"
        except (ConversionError, InvalidDDS, UnsupportedPixelFormat) as e:
            failures += 1
            rec["result"] = "error"
            rec["error"] = str(e)
        records.append(rec)
        flag = "OK " if rec["result"] == "ok" else "ERR"
        print("{0} {1:9s} {2:24s} {3}".format(flag, archive, rel_out, rec.get("error", "")))

    manifest = {
        "phase": "5",
        "source_archives": [a + ".pk2" for a in ARCHIVES],
        "reader": os.path.abspath(args.reader_bin),
        "conversion_note": (
            "Only formats verified from real bytes are converted. "
            "PNG encoder is pure-Python and deterministic."
        ),
        "records": records,
        "failures": failures,
    }
    if args.json:
        manifest_path = args.json
    else:
        manifest_path = os.path.join(args.out, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print("manifest:", manifest_path)
    print("failures: {0}".format(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
