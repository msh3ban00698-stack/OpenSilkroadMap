"""Phase 13 Part D: complete proven `.ban` animation layout tests.

Phase 13 proved the full JMXVBAN layout (see FORMAT_RESEARCH.md) by parsing
three real files to the exact last byte:

  header: magic JMXVBAN 0102, reserved 8B, u32 name_len, name (no NUL)
  body  : u32 duration_ms, u32 frame_rate(30), u32 UNKNOWN, u32 kpb,
          kpb x u32 timestamp_ms (first 0, last = duration),
          u32 bone_count, then bone_count x [u32 name_len, name,
          u32 per-bone kf count (= kpb), kpb x 28 B keyframes]

Static tests run against the committed fixtures; the live check re-parses the
real archives when SRO_PK2_DIR is set.

Running:
    python3 scripts/test_phase13_ban.py
"""

import json
import os
import struct
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

TD = SCRIPTS / "testdata" / "formats"

FIXTURES = {
    "ban_ferry_boat": ("ban_ferry_boat.json", "/prim/ani/bldg/china/cj_ferry/cj_ferry_boat_old.ban", 171),
    "ban_royalsoldier": ("ban_royalsoldier.json", "/prim/ani/mob/qinshi/royalsoldier/royalsoldier_die.ban", 29686),
    "ban_venefica": ("ban_venefica.json", "/prim/ani/mob/arabia/venefica/venefica_stand01.BAN", 926897),
}


def load_fixture(key):
    with open(TD / FIXTURES[key][0], encoding="utf-8") as fh:
        return json.load(fh)


class BanFullLayoutTests(unittest.TestCase):
    def test_exact_parse_on_all_samples(self):
        for key in FIXTURES:
            doc = load_fixture(key)
            self.assertTrue(doc["parse_exact"], key)
            self.assertEqual(doc["parsed_end"], doc["source"]["size"], key)

    def test_header_fields(self):
        expected = {
            "ban_ferry_boat": (8000, 1, 3),
            "ban_royalsoldier": (2966, 38, 27),
            "ban_venefica": (6000, 182, 181),
        }
        for key, (dur, bones, kpb) in expected.items():
            doc = load_fixture(key)
            self.assertEqual(doc["duration_ms"], dur, key)
            self.assertEqual(doc["frame_rate"], 30, key)
            self.assertEqual(doc["bone_count"], bones, key)
            self.assertEqual(doc["keyframes_per_bone"], kpb, key)
            self.assertEqual(len(doc["bones"]), bones, key)

    def test_timestamps(self):
        for key in FIXTURES:
            doc = load_fixture(key)
            ts = doc["timestamps"]
            self.assertEqual(len(ts), doc["keyframes_per_bone"], key)
            self.assertEqual(ts[0], 0, key)
            self.assertEqual(ts[-1], doc["duration_ms"], key)
            self.assertEqual(ts, sorted(ts), key)
            if key == "ban_venefica":
                self.assertEqual(ts[1], 33)
                self.assertEqual(ts[2], 66)

    def test_royalsoldier_skeleton_names(self):
        doc = load_fixture("ban_royalsoldier")
        names = [b["name"] for b in doc["bones"]]
        for bone in ["Bip01", "Bip01 Pelvis", "Bip01 Spine", "Bip01 Head",
                     "Bip01 L UpperArm", "Bip01 R Thigh"]:
            self.assertIn(bone, names)
        self.assertIn("Bone01", names)
        self.assertEqual(len(names), len(set(names)))

    def test_venefica_attachment_names(self):
        doc = load_fixture("ban_venefica")
        names = [b["name"] for b in doc["bones"]]
        for bone in ["[root]", "Bip02", "L_bigfeather_01", "FR_chair_01",
                     "Effect_Bone04_end"]:
            self.assertIn(bone, names)

    def test_per_bone_keyframe_count_matches_kpb(self):
        for key in FIXTURES:
            doc = load_fixture(key)
            for b in doc["bones"]:
                self.assertEqual(b["keyframes"], doc["keyframes_per_bone"], (key, b["name"]))

    def test_keyframe_strides_are_28(self):
        doc = load_fixture("ban_royalsoldier")
        offs = [r["offset"] for r in doc["sample_records"]]
        for a, b in zip(offs, offs[1:]):
            self.assertEqual(b - a, 28)


class BanLiveCheck(unittest.TestCase):
    def test_live_full_parse(self):
        sro_dir = os.environ.get("SRO_PK2_DIR")
        if not sro_dir:
            self.skipTest("SRO_PK2_DIR not set (archives unavailable)")
        import ban_decoder
        import pk2_table
        files, _ = pk2_table.inventory(os.path.join(sro_dir, "Data.pk2"))
        by_name = {f["path"].split("/")[-1]: f for f in files}
        with open(os.path.join(sro_dir, "Data.pk2"), "rb") as fh:
            for key, (_, path, size) in FIXTURES.items():
                e = by_name.get(path.split("/")[-1])
                fh.seek(e["pos"])
                data = fh.read(e["size"])
                self.assertEqual(len(data), size, key)
                parsed = ban_decoder.parse_ban(data)
                self.assertEqual(parsed["parsed_end"], size, key)
                self.assertEqual(parsed["bone_count"], load_fixture(key)["bone_count"], key)
                self.assertEqual([b["name"] for b in parsed["bones"]],
                                 [b["name"] for b in load_fixture(key)["bones"]], key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
