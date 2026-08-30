"""Phase 12 binary format research tests (BAN partial decoder).

Static tests run against the committed derived fixtures under
scripts/testdata/formats/ (extracted read-only from the real Data.pk2 archive,
recorded in FORMAT_RESEARCH.md):

  ban_ferry_boat.json   171 B      /prim/ani/bldg/china/cj_ferry/cj_ferry_boat_old.ban
  ban_royalsoldier.json 29,686 B   /prim/ani/mob/qinshi/royalsoldier/royalsoldier_die.ban
  ban_venefica.json     926,897 B  /prim/ani/mob/arabia/venefica/venefica_stand01.BAN

The live check re-extracts the same files from the real archives when
SRO_PK2_DIR is set; otherwise it reports SKIPPED. No test writes to the source
archives.

Running:
    python3 scripts/test_phase12_formats.py
"""

import json
import os
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import ban_decoder  # noqa: E402

TD = SCRIPTS / "testdata" / "formats"

FIXTURES = {
    "ban_ferry_boat": ("ban_ferry_boat.json", "/prim/ani/bldg/china/cj_ferry/cj_ferry_boat_old.ban", 171),
    "ban_royalsoldier": ("ban_royalsoldier.json", "/prim/ani/mob/qinshi/royalsoldier/royalsoldier_die.ban", 29686),
    "ban_venefica": ("ban_venefica.json", "/prim/ani/mob/arabia/venefica/venefica_stand01.BAN", 926897),
}


def load_fixture(key):
    with open(TD / FIXTURES[key][0], encoding="utf-8") as fh:
        return json.load(fh)


class BanHeaderTests(unittest.TestCase):
    def test_magic_version_reserved(self):
        for key in FIXTURES:
            doc = load_fixture(key)
            self.assertEqual(doc["header"]["magic"], "JMXVBAN ")
            self.assertEqual(doc["header"]["version"], "0102")
            self.assertEqual(doc["header"]["reserved_hex"], "0000000000000000")

    def test_name_length_matches_name(self):
        cases = {
            "ban_ferry_boat": "cj_ferry_boat_old",
            "ban_royalsoldier": "royalsoldier_die",
            "ban_venefica": "venefica_stand01",
        }
        for key, name in cases.items():
            doc = load_fixture(key)
            self.assertEqual(doc["header"]["name_length"], len(name))
            self.assertEqual(doc["header"]["name"], name)

    def test_body_start_is_name_end_no_nul(self):
        # Phase 13 Part D: proven from real bytes that the animation name has NO
        # trailing NUL; the body (5-field header) starts immediately at name_end.
        for key in FIXTURES:
            doc = load_fixture(key)
            self.assertEqual(
                doc["header"]["body_start"],
                doc["header"]["name_length"] + 0x18,
            )

    def test_full_parse_lands_exactly_on_file_end(self):
        # Phase 13 Part D: complete proven layout (duration/fps/kpb/timestamps/
        # bone_count/bones) parses each file to the last byte.
        for key in FIXTURES:
            doc = load_fixture(key)
            self.assertTrue(doc["parse_exact"])
            self.assertEqual(doc["parsed_end"], doc["source"]["size"])
            self.assertEqual(doc["frame_rate"], 30)
            self.assertEqual(doc["keyframes_per_bone"],
                             len(doc["timestamps"]))
            self.assertEqual(len(doc["bones"]), doc["bone_count"])
            self.assertEqual(doc["timestamps"][0], 0)
            self.assertEqual(doc["timestamps"][-1], doc["duration_ms"])


class BanKeyframeTests(unittest.TestCase):
    def test_record_layout_is_28_bytes(self):
        for key in FIXTURES:
            doc = load_fixture(key)
            self.assertEqual(doc["record_byte_size"], 28)
            self.assertEqual(doc["record_layout"], ["f32 rotation quaternion (x,y,z,w)", "f32 position (x,y,z)"])

    def test_runs_exist_on_all_real_files(self):
        self.assertGreaterEqual(load_fixture("ban_ferry_boat")["keyframe_runs"][0]["record_count"], 3)
        self.assertGreaterEqual(load_fixture("ban_royalsoldier")["keyframe_runs"][0]["record_count"], 27)
        self.assertGreaterEqual(load_fixture("ban_venefica")["keyframe_runs"][0]["record_count"], 181)

    def test_ferry_boat_runs_fit_file(self):
        doc = load_fixture("ban_ferry_boat")
        size = doc["source"]["size"]
        for run in doc["keyframe_runs"]:
            end = run["start_offset"] + run["record_count"] * 28
            self.assertLessEqual(end, size)

    def test_quaternion_normalized(self):
        for key in FIXTURES:
            doc = load_fixture(key)
            for run in doc["keyframe_runs"]:
                q = run["quaternion"]
                self.assertLess(abs(sum(x * x for x in q) - 1.0), 0.05)

    def test_sample_records_strided_by_28(self):
        doc = load_fixture("ban_royalsoldier")
        offsets = [r["offset"] for r in doc["sample_records"]]
        for a, b in zip(offsets, offsets[1:]):
            self.assertEqual(b - a, 28)

    def test_multiple_bones_multiple_runs(self):
        self.assertGreaterEqual(len(load_fixture("ban_royalsoldier")["keyframe_runs"]), 30)
        self.assertGreaterEqual(len(load_fixture("ban_venefica")["keyframe_runs"]), 100)


class BanLiveCheck(unittest.TestCase):
    def test_live_parse_from_archives(self):
        sro_dir = os.environ.get("SRO_PK2_DIR")
        if not sro_dir:
            self.skipTest("SRO_PK2_DIR not set (archives unavailable)")
        import pk2_table

        def read(arc, path):
            files, _ = pk2_table.inventory(arc)
            entry = next(f for f in files if f["path"] == path)
            with open(arc, "rb") as fh:
                fh.seek(entry["pos"])
                return fh.read(entry["size"])

        archive = str(Path(sro_dir) / "Data.pk2")
        for key, (_, path, expected_size) in FIXTURES.items():
            data = read(archive, path)
            self.assertEqual(len(data), expected_size)
            dec = ban_decoder.decode_keyframes(data)
            self.assertEqual(dec["header"]["name"], load_fixture(key)["header"]["name"])
            self.assertGreaterEqual(len(dec["keyframe_runs"]), 1)


if __name__ == "__main__":
    unittest.main()
