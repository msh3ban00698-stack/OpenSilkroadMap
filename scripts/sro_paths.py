"""Shared path resolution for the vSRO 1.193 extraction/generation pipeline.

PK2 archives, pk2reader.py, and generated gamedata live outside the committed
tree. Callers must pass --pk2-dir / --output-dir, set SRO_* environment
variables, or accept repo-relative defaults for extracted source and output.

This module does not ship or invent a PK2 reader. Expected reader API:

    PK2(path) -> archive
    archive.find(path) -> entry | None
    archive.read_file(entry) -> bytes
"""

import argparse
import importlib.util
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SOURCE_DIR = os.path.join(REPO_ROOT, "game_source")
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "map", "public", "assets", "gamedata")
DEFAULT_PHASE_H_DIR = os.path.join(REPO_ROOT, "map", "src", "game", "data")
TEXTDATA_REL = os.path.join("Media", "server_dep", "silkroad", "textdata")
PK2_ARCHIVES = ("Data.pk2", "Map.pk2", "Media.pk2", "Music.pk2", "Particles.pk2")


class PipelineConfigError(Exception):
    pass


class MissingPk2ReaderError(PipelineConfigError):
    pass


def resolve_pk2_dir(cli_value=None):
    raw = cli_value or os.environ.get("SRO_PK2_DIR")
    if not raw:
        raise PipelineConfigError(
            "PK2 directory is required. Pass --pk2-dir or set SRO_PK2_DIR. "
            "Expected layout: <dir>/Data.pk2 (and Media/Map/Music.pk2) or "
            "<dir>/pk2/*.pk2. listing_media.txt may sit next to pk2/."
        )
    return os.path.abspath(raw)


def resolve_reader_dir(cli_value=None, pk2_dir=None):
    raw = cli_value or os.environ.get("SRO_READER_DIR")
    if raw:
        return os.path.abspath(raw)
    if pk2_dir:
        return os.path.abspath(pk2_dir)
    raise MissingPk2ReaderError(
        "pk2reader.py location is unknown. Pass --reader-dir or --pk2-dir."
    )


def resolve_source_dir(cli_value=None):
    raw = cli_value or os.environ.get("SRO_SOURCE_DIR")
    if raw:
        return os.path.abspath(raw)
    return DEFAULT_SOURCE_DIR


def resolve_output_dir(cli_value=None):
    raw = cli_value or os.environ.get("SRO_OUTPUT_DIR")
    if raw:
        return os.path.abspath(raw)
    return DEFAULT_OUTPUT_DIR


def resolve_phase_h_dir(cli_value=None):
    if cli_value:
        return os.path.abspath(cli_value)
    return DEFAULT_PHASE_H_DIR


def textdata_dir(source_dir):
    return os.path.join(source_dir, TEXTDATA_REL)


def resolve_ext_dir(env_var, cli_value=None, label=""):
    """Resolve an external (non-committed) data directory from env or CLI."""
    raw = cli_value or os.environ.get(env_var)
    if not raw:
        raise PipelineConfigError(
            "{0} directory is required. Set {1} or pass it as an argument.".format(
                label, env_var
            )
        )
    return os.path.abspath(raw)


def resolve_db_dir(cli_value=None):
    return resolve_ext_dir("SRO_DB_DIR", cli_value, "Database")


def resolve_extract_dir(cli_value=None):
    return resolve_ext_dir("SRO_EXTRACT_DIR", cli_value, "Extract")


def resolve_pkg_dir(cli_value=None):
    return resolve_ext_dir("SRO_PKG_DIR", cli_value, "Package")


def resolve_client_extract_dir(cli_value=None):
    return resolve_ext_dir("SRO_CLIENT_EXTRACT_DIR", cli_value, "Client extract")


def resolve_client_bin_dir(cli_value=None):
    return resolve_ext_dir("SRO_CLIENT_BIN_DIR", cli_value, "Client binaries")


def resolve_client_install_dir(cli_value=None):
    return resolve_ext_dir("SRO_CLIENT_INSTALL_DIR", cli_value, "Client install")


def resolve_pk2_mate_dir(cli_value=None):
    return resolve_ext_dir("SRO_PK2_MATE_DIR", cli_value, "pk2_mate")


def resolve_work_dir(cli_value=None):
    return resolve_ext_dir("SRO_WORK_DIR", cli_value, "Work")


def resolve_full_extract_dir(cli_value=None):
    return resolve_ext_dir("SRO_FULL_EXTRACT_DIR", cli_value, "Full extract")


def pk2_archive(pk2_dir, name):
    direct = os.path.join(pk2_dir, name)
    nested = os.path.join(pk2_dir, "pk2", name)
    if os.path.isfile(direct):
        return direct
    if os.path.isfile(nested):
        return nested
    if os.path.isdir(os.path.join(pk2_dir, "pk2")):
        return nested
    return direct


def listing_path(pk2_dir, name):
    candidates = [
        os.path.join(pk2_dir, name),
        os.path.join(os.path.dirname(os.path.abspath(pk2_dir)), name),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[0]


def require_pk2_reader(reader_dir):
    if not reader_dir:
        raise MissingPk2ReaderError(
            "pk2reader.py not found. Pass --reader-dir pointing at a directory "
            "that contains pk2reader.py and jmblowfish.py."
        )
    reader_dir = os.path.abspath(reader_dir)
    path = os.path.join(reader_dir, "pk2reader.py")
    if not os.path.isfile(path):
        raise MissingPk2ReaderError(
            "pk2reader.py not found in {0}. Pass --reader-dir pointing at a "
            "directory that contains pk2reader.py and jmblowfish.py. This "
            "repository does not include a PK2 reader. Expected API: PK2(path), "
            "find(path), read_file(entry).".format(reader_dir)
        )
    spec = importlib.util.spec_from_file_location("pk2reader", path)
    if spec is None or spec.loader is None:
        raise MissingPk2ReaderError("unable to load pk2reader.py from {0}".format(path))
    sys.modules.pop("pk2reader", None)
    sys.modules.pop("jmblowfish", None)
    if reader_dir not in sys.path:
        sys.path.insert(0, reader_dir)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pk2reader"] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "PK2"):
        raise MissingPk2ReaderError("pk2reader.py must export class PK2")
    return mod


def add_common_args(parser, *, pk2=False, source=False, output=False):
    if pk2:
        parser.add_argument(
            "--pk2-dir",
            default=None,
            help="Directory containing PK2 archives, or a parent with pk2/",
        )
        parser.add_argument(
            "--reader-dir",
            default=None,
            help="Directory with pk2reader.py/jmblowfish.py (default: pk2-dir)",
        )
    if source:
        parser.add_argument(
            "--source-dir",
            default=None,
            help="Extracted source root (default: <repo>/game_source)",
        )
    if output:
        parser.add_argument(
            "--output-dir",
            default=None,
            help="Generated JSON output (default: map/public/assets/gamedata)",
        )
    return parser


def make_parser(description, *, pk2=False, source=False, output=False):
    parser = argparse.ArgumentParser(description=description)
    return add_common_args(parser, pk2=pk2, source=source, output=output)
