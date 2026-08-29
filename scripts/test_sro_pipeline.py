"""Pipeline tests that run without PK2 archives or pk2reader.py.

These tests lock the Sprint 1 contract:
- no hardcoded /tmp/opencode/vsro fallback
- configurable PK2 / source / output roots
- missing reader and missing textdata fail with a clear message
- full gamedata skill scan is explicit about CH+EU tables
"""

import glob
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))


def run_script(*args, env=None, cwd=None):
    cmd = [sys.executable, *[str(a) for a in args]]
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO),
        env=merged,
        capture_output=True,
        text=True,
    )


class PathConfigTests(unittest.TestCase):
    def test_default_pk2_dir_is_not_vsro_tmp(self):
        import sro_paths

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SRO_PK2_DIR", None)
            os.environ.pop("SRO_READER_DIR", None)
            with self.assertRaises(sro_paths.PipelineConfigError) as ctx:
                sro_paths.resolve_pk2_dir()
        self.assertNotIn("/tmp/opencode/vsro", str(ctx.exception))
        self.assertIn("--pk2-dir", str(ctx.exception))

    def test_cli_pk2_dir_wins_over_env(self):
        import sro_paths

        with tempfile.TemporaryDirectory() as td:
            cli = os.path.join(td, "cli-pk2")
            envp = os.path.join(td, "env-pk2")
            os.makedirs(cli)
            os.makedirs(envp)
            with mock.patch.dict(os.environ, {"SRO_PK2_DIR": envp}):
                self.assertEqual(sro_paths.resolve_pk2_dir(cli), os.path.abspath(cli))

    def test_env_pk2_dir_used_without_cli(self):
        import sro_paths

        with tempfile.TemporaryDirectory() as td:
            envp = os.path.join(td, "env-pk2")
            os.makedirs(envp)
            with mock.patch.dict(os.environ, {"SRO_PK2_DIR": envp}):
                self.assertEqual(sro_paths.resolve_pk2_dir(), os.path.abspath(envp))

    def test_default_source_dir_is_repo_game_source(self):
        import sro_paths

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SRO_SOURCE_DIR", None)
            got = sro_paths.resolve_source_dir()
        self.assertEqual(got, str(REPO / "game_source"))

    def test_no_script_hardcodes_vsro_tmp(self):
        offenders = []
        for path in glob.glob(str(SCRIPTS / "*.py")):
            name = os.path.basename(path)
            if name.startswith("test_"):
                continue
            text = Path(path).read_text(encoding="utf-8")
            if "/tmp/opencode" in text:
                offenders.append(name)
        self.assertEqual(offenders, [], f"hardcoded /tmp/opencode paths in {offenders}")


class Pk2ReaderBoundaryTests(unittest.TestCase):
    def test_missing_reader_is_actionable_error(self):
        import sro_paths

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(sro_paths.MissingPk2ReaderError) as ctx:
                sro_paths.require_pk2_reader(td)
        msg = str(ctx.exception)
        self.assertIn("pk2reader.py", msg)
        self.assertIn("--reader-dir", msg)
        self.assertNotIn("/tmp/opencode/vsro", msg)

    def test_reader_import_uses_reader_dir(self):
        import sro_paths

        with tempfile.TemporaryDirectory() as td:
            Path(td, "pk2reader.py").write_text(
                "class PK2:\n    def __init__(self, path):\n        self.path = path\n",
                encoding="utf-8",
            )
            mod = sro_paths.require_pk2_reader(td)
            self.assertTrue(hasattr(mod, "PK2"))
            self.assertEqual(mod.PK2("x").path, "x")


class ImportWithoutPk2Tests(unittest.TestCase):
    def test_pk2_scripts_import_without_reader(self):
        names = [
            "extract_ui",
            "extract_icons",
            "extract_audio_minimaps",
            "extract_actors",
            "extract_ct",
            "extract_regions",
        ]
        for name in names:
            with self.subTest(module=name):
                sys.modules.pop(name, None)
                mod = importlib.import_module(name)
                self.assertIsNotNone(mod)


class CliTests(unittest.TestCase):
    def test_extract_sro_help(self):
        proc = run_script(SCRIPTS / "extract_sro.py", "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--pk2-dir", proc.stdout)
        self.assertIn("--output-dir", proc.stdout)

    def test_validate_runs_without_pk2(self):
        proc = run_script(SCRIPTS / "extract_sro.py", "validate")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("OK", proc.stdout)
        self.assertNotIn("/tmp/opencode/vsro", proc.stdout)

    def test_extract_without_pk2_dir_fails_clearly(self):
        env = os.environ.copy()
        env.pop("SRO_PK2_DIR", None)
        env.pop("SRO_READER_DIR", None)
        proc = run_script(SCRIPTS / "extract_sro.py", "extract", env=env)
        self.assertNotEqual(proc.returncode, 0)
        combined = proc.stdout + proc.stderr
        self.assertIn("--pk2-dir", combined)
        self.assertNotIn("/tmp/opencode/vsro", combined)


class GeneratorMissingSourceTests(unittest.TestCase):
    def test_build_game_database_missing_source(self):
        with tempfile.TemporaryDirectory() as td:
            missing = os.path.join(td, "nope", "textdata")
            out = os.path.join(td, "gamedata")
            proc = run_script(
                SCRIPTS / "build_game_database.py",
                "--source-dir",
                os.path.join(td, "nope"),
                "--output-dir",
                out,
            )
            self.assertEqual(proc.returncode, 1)
            combined = proc.stdout + proc.stderr
            self.assertIn("Error", combined)
            self.assertTrue("textdata" in combined.lower() or missing in combined or "not found" in combined.lower())

    def test_generate_phase_h_missing_source(self):
        with tempfile.TemporaryDirectory() as td:
            proc = run_script(
                SCRIPTS / "generate_phase_h_data.py",
                "--source-dir",
                os.path.join(td, "nope"),
                "--output-dir",
                os.path.join(td, "out"),
            )
            self.assertEqual(proc.returncode, 1)
            combined = proc.stdout + proc.stderr
            self.assertIn("Error", combined)

    def test_generate_game_data_missing_source(self):
        with tempfile.TemporaryDirectory() as td:
            proc = run_script(
                SCRIPTS / "generate_game_data.py",
                "--source-dir",
                os.path.join(td, "nope"),
            )
            self.assertEqual(proc.returncode, 1)
            combined = proc.stdout + proc.stderr
            self.assertIn("Error", combined)


class SkillScanTests(unittest.TestCase):
    def test_build_skills_reads_ch_and_eu_from_all_skilldata_tables(self):
        import build_game_database as gdb

        with tempfile.TemporaryDirectory() as td:
            def write_table(name, rows):
                path = os.path.join(td, name)
                header = "h\n"
                body = "".join("\t".join(r) + "\n" for r in rows)
                Path(path).write_bytes(("\ufeff" + header + body).encode("utf-16"))

            def skill_row(code, sid="1", name_sn="SN_SKILL_X"):
                cols = ["0"] * 66
                cols[0] = "1"
                cols[1] = sid
                cols[3] = code
                cols[7] = "1"
                cols[8] = "0"
                cols[12] = "10"
                cols[14] = "5"
                cols[61] = "icon.ddj"
                cols[62] = name_sn
                return cols

            write_table("skilldata_5000.txt", [skill_row("SKILL_CH_SWORD_SMASH_A_01", "174", "SN_CH")])
            write_table("skilldata_10000.txt", [skill_row("SKILL_EU_WIZARD_MENTALA_DAMAGEUP_A_01", "900", "SN_EU")])
            write_table("skilldata_enc.txt", [skill_row("SKILL_CH_SHOULD_SKIP", "1", "SN_SKIP")])
            names = {"SN_CH": "Strike Smash", "SN_EU": "Mental Damage Up"}
            skills = gdb.build_skills(names, td)
            self.assertIn("SKILL_CH_SWORD_SMASH_A_01", skills)
            self.assertIn("SKILL_EU_WIZARD_MENTALA_DAMAGEUP_A_01", skills)
            self.assertNotIn("SKILL_CH_SHOULD_SKIP", skills)
            self.assertEqual(skills["SKILL_CH_SWORD_SMASH_A_01"]["name"], "Strike Smash")


if __name__ == "__main__":
    unittest.main()
