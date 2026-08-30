#!/usr/bin/env python3
"""Canonical vSRO 1.193 data pipeline entrypoint.

    PK2 root -> extract -> game_source/ -> generate -> map/public/assets/gamedata/

pk2reader.py / jmblowfish.py are not in this repository. Supply them with
--reader-dir (defaults to --pk2-dir). Phase H starter JSON in
map/src/game/data/ is a separate committed dataset; full gamedata is optional
at runtime.
"""

import argparse
import os
import py_compile
import sys

import sro_paths

SCRIPTS = os.path.dirname(os.path.abspath(__file__))


def cmd_validate(_args):
    for name in (
        "sro_paths.py",
        "extract_sro.py",
        "extract_world.py",
        "extract_region.py",
        "build_game_database.py",
        "generate_game_data.py",
        "generate_phase_h_data.py",
    ):
        py_compile.compile(os.path.join(SCRIPTS, name), doraise=True)
    print("OK: pipeline scripts compile without PK2 archives")
    print("Phase H starter data: {0}".format(sro_paths.DEFAULT_PHASE_H_DIR))
    print("Full gamedata output: {0}".format(sro_paths.DEFAULT_OUTPUT_DIR))
    print("Extracted source root: {0}".format(sro_paths.DEFAULT_SOURCE_DIR))


def cmd_extract(args):
    try:
        pk2_dir = sro_paths.resolve_pk2_dir(args.pk2_dir)
        reader_dir = sro_paths.resolve_reader_dir(args.reader_dir, pk2_dir)
        sro_paths.require_pk2_reader(reader_dir)
    except sro_paths.PipelineConfigError as exc:
        sys.exit("Error: {0}".format(exc))
    media = sro_paths.pk2_archive(pk2_dir, "Media.pk2")
    if not os.path.isfile(media):
        sys.exit("Error: Media.pk2 not found under {0}".format(pk2_dir))
    source = sro_paths.resolve_source_dir(args.source_dir)
    print("PK2 dir: {0}".format(pk2_dir))
    print("Reader dir: {0}".format(reader_dir))
    print("Source dir: {0}".format(source))
    print("Dispatch extract_world.py")
    from extract_world import main as extract_world_main

    argv = [
        "extract_world.py",
        "--pk2-dir",
        os.path.dirname(media) if os.path.basename(os.path.dirname(media)) == "pk2" else pk2_dir,
        "--reader-dir",
        reader_dir,
        "--root",
        source,
    ]
    saved = sys.argv
    sys.argv = argv
    try:
        extract_world_main()
    finally:
        sys.argv = saved


def cmd_generate(args):
    source = sro_paths.resolve_source_dir(args.source_dir)
    output = sro_paths.resolve_output_dir(args.output_dir)
    textdata = sro_paths.textdata_dir(source)
    if not os.path.isdir(textdata):
        sys.exit("Error: Directory {0} not found.".format(textdata))
    from build_game_database import configure, run

    configure(source, output)
    run()


def main():
    parser = argparse.ArgumentParser(
        description="vSRO 1.193 extract/generate pipeline (no hardcoded PK2 path)"
    )
    sro_paths.add_common_args(parser, pk2=True, source=True, output=True)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("validate", help="Check pipeline scripts without PK2 archives")
    sub.add_parser("extract", help="Extract Media.pk2 textdata/minimaps into source dir")
    sub.add_parser("generate", help="Build map/public/assets/gamedata from textdata")
    args = parser.parse_args()
    if args.cmd == "validate":
        cmd_validate(args)
    elif args.cmd == "extract":
        cmd_extract(args)
    elif args.cmd == "generate":
        cmd_generate(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
