#!/usr/bin/env python3
"""Phase 20 Part A: character resolution primitives (hermetic)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import character_resolve as CR  # noqa: E402
import world_terrain as wt  # noqa: E402


def _bmt(ddj_value):
    """Build a minimal JMXVBMT 0102 blob with one material -> ddj."""
    name = b"bandit"
    ddj = ddj_value.encode("ascii")
    blob = bytearray(b"JMXVBMT 0102")
    blob += (1).to_bytes(4, "little")          # material count
    blob += len(name).to_bytes(4, "little") + name
    blob += b"\x00" * 0x48                     # skip 72-byte unknown block
    blob += len(ddj).to_bytes(4, "little") + ddj
    blob += b"\x00" * 7
    return bytes(blob)


class TestSplitModels(unittest.TestCase):
    def test_single(self):
        self.assertEqual(CR.split_models("mob\\china\\bandit.bsr"),
                         ["mob\\china\\bandit.bsr"])

    def test_multi_variant(self):
        self.assertEqual(
            CR.split_models("mob\\sd\\seth.bsr,mob\\sd\\seth_t2.bsr,mob\\sd\\seth_t3.bsr"),
            ["mob\\sd\\seth.bsr", "mob\\sd\\seth_t2.bsr", "mob\\sd\\seth_t3.bsr"])

    def test_empty(self):
        self.assertEqual(CR.split_models(""), [])
        self.assertEqual(CR.split_models(None), [])


class TestSlug(unittest.TestCase):
    def test_bsk(self):
        self.assertEqual(CR.slug("/prim/skel/mob/china/bandit.bsk"),
                         "prim_skel_mob_china_bandit")

    def test_ddj_backslash(self):
        self.assertEqual(CR.slug("prim\\mtrl\\mob\\jupiter\\charm_whitch.ddj"),
                         "prim_mtrl_mob_jupiter_charm_whitch")


class TestBsrPath(unittest.TestCase):
    def test_bsr(self):
        self.assertEqual(CR.bsr_path("mob\\china\\bandit.bsr"),
                         "/res/mob/china/bandit.bsr")


class TestResolveTexture(unittest.TestCase):
    def test_bare_filename_relative_to_bmt(self):
        exists = {"/prim/mtrl/mob/china/bandit.ddj"}
        got = CR.resolve_texture(
            lambda p: b"", lambda p: p.lower() in exists,
            _bmt("bandit.ddj"), "/prim/mtrl/mob/china/bandit.bmt", "bandit")
        self.assertEqual(got, "/prim/mtrl/mob/china/bandit.ddj")

    def test_root_relative_path(self):
        exists = {"/prim/mtrl/mob/jupiter/charm_whitch.ddj"}
        got = CR.resolve_texture(
            lambda p: b"", lambda p: p.lower() in exists,
            _bmt("prim\\mtrl\\mob\\jupiter\\charm_whitch.ddj"),
            "/prim/mtrl/mob/jupiter/charm_witch.bmt", "bandit")
        self.assertEqual(got, "/prim/mtrl/mob/jupiter/charm_whitch.ddj")

    def test_missing_material_raises(self):
        with self.assertRaises(KeyError):
            CR.resolve_texture(
                lambda p: b"", lambda p: False,
                _bmt("bandit.ddj"), "/prim/mtrl/mob/china/bandit.bmt", "nope")


class TestLoadCharacterdata(unittest.TestCase):
    @staticmethod
    def _char_line(refid, model):
        cols = [""] * 53
        cols[1] = refid
        cols[52] = model
        return "\t".join(cols)

    def test_join_and_split(self):
        text = "\r\n".join([
            self._char_line("1949", "mob\\china\\bandit.bsr"),
            self._char_line("26738", "mob\\sd\\seth.bsr,mob\\sd\\seth_t2.bsr"),
            self._char_line("9999", "not_a_model"),
        ])
        idx = CR.load_characterdata(text)
        self.assertEqual(idx["1949"], ["mob\\china\\bandit.bsr"])
        self.assertEqual(idx["26738"],
                         ["mob\\sd\\seth.bsr", "mob\\sd\\seth_t2.bsr"])
        self.assertNotIn("9999", idx)


if __name__ == "__main__":
    unittest.main()
