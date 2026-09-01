#!/usr/bin/env python3
"""Phase 29 deep-runtime-forensics evidence tests.

Verifies the committed phase29_source_evidence.json records, per finding, only
PROVEN recovered facts (with UNKNOWN/INFERRED labels where semantics cannot be
proven). Mirrors Phase29SourceEvidenceTest.java (run by Android CI); this Python
copy runs in a bare checkout so the evidence can be verified without an Android
SDK.

The client executable is never executed; all client facts come from static
string-level inspection of GameClient.exe / edxSilkroadDll5.dll /
GFXFileManager.dll and from Media.pk2 config / SRO_VT_SHARD.Bak / proxy_cfg.ini.
"""
import json
import os
import unittest

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "formats", "phase29_source_evidence.json")


class TestPhase29Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as fh:
            cls.doc = json.load(fh)

    def test_phase_tag(self):
        self.assertEqual(self.doc["phase"], "phase29")

    def test_client_executable_recovered_with_proven_symbols(self):
        ce = self.doc["client_executable"]
        self.assertTrue(ce["present"])
        self.assertIn("GameClient.exe", ce["binary"])
        self.assertIn("edxSilkroadDll5.dll", ce["binary"])
        self.assertIn("GFXFileManager.dll", ce["binary"])
        self.assertIn("CCameraSlid", ce["camera_classes"])
        self.assertIn("CCameraWorking", ce["camera_classes"])
        self.assertIn("SC_CameraShake", ce["camera_classes"])
        self.assertIn("CAniMixer", ce["animation_classes"])
        self.assertIn("CPrimAnimation", ce["animation_classes"])
        self.assertEqual(ce["movement_member"], "m_nSpeed2")

    def test_option_defaults(self):
        opt = self.doc["config"]["option"]
        self.assertEqual(opt["StartCharacter"], "1907")
        self.assertEqual(opt["Map"], "0")
        self.assertEqual(opt["StartWeapon"], "0")
        self.assertIn("CPSLoadingMission", opt["start_process"])
        self.assertIn("CPSVersionCheck", opt["start_process"])

    def test_camera_and_command_proven(self):
        cam = self.doc["config"]["cameradata"]
        self.assertEqual(cam["preset_count"], 2)
        self.assertEqual(cam["default_marker_line"], "-1")
        cmd = self.doc["config"]["command"]
        self.assertEqual(cmd["count"], 47)
        names = {c["command"] for c in cmd["commands"]}
        self.assertIn("/PlayerCount", names)
        self.assertIn("/GetPos", names)
        self.assertIn("/Debug", names)

    def test_db_insertrefchar_proves_speed_columns(self):
        db = self.doc["server_db_schema"]
        self.assertTrue(db["present"])
        self.assertEqual(db["procedure"], "_InsertRefChar")
        self.assertEqual(db["speed1_param_index"], 45)
        self.assertEqual(db["speed2_param_index"], 46)
        self.assertTrue(db["has_knockdown"])
        self.assertTrue(db["has_ko_recover_time"])
        names = [p[0] for p in db["param_order"]]
        for col in ("Speed1", "Speed2", "Scale", "CharGender", "MaxHP",
                    "MaxMP", "Knockdown", "KO_RecoverTime"):
            self.assertIn(col, names, col)

    def test_player_templates_raw_triplet_unproven_mapping(self):
        mv = self.doc["movement_speed"]
        self.assertIn("Speed1", mv["proven_db_columns"])
        self.assertIn("Speed2", mv["proven_db_columns"])
        self.assertIn("Scale", mv["proven_db_columns"])
        templates = mv["player_templates"]
        self.assertEqual(len(templates), 13)
        codes = {t["code"] for t in templates}
        self.assertIn("CHAR_CH_MAN_ADVENTURER", codes)
        adv = next(t for t in templates if t["code"] == "CHAR_CH_MAN_ADVENTURER")
        self.assertEqual(adv["refid"], "1907")
        self.assertEqual(adv["positional_col46"], "16")
        self.assertEqual(adv["positional_col47"], "50")
        self.assertEqual(adv["positional_col48"], "100")
        self.assertIn("INFERRED", mv["positional_triplet"]["status"])

    def test_proxy_protocol_and_authority(self):
        px = self.doc["proxy"]
        self.assertTrue(px["present"])
        self.assertEqual(px["client"]["version"], "188")
        self.assertEqual(px["client"]["gateway_port"], "15779")
        self.assertEqual(px["malicious_opcode_filtering"], "True")
        self.assertIn("server-authoritative", self.doc["conclusions"]["authority"])

    def test_unresolved_semantics_stay_unknown(self):
        c = self.doc["conclusions"]
        self.assertIn("caller-supplied", c["player_spawn"])
        self.assertIn("UNKNOWN", c["player_spawn"])
        self.assertIn("still UNKNOWN", c["skill_semantics"])
        self.assertIn("UNKNOWN", c["movement"])

    def test_server_package_recovered(self):
        sp = self.doc["server_package"]
        self.assertTrue(sp["present"])
        self.assertTrue(sp["has_refdata"])
        self.assertTrue(sp["has_server_cfg"])
        names = [s["name"] for s in sp["game_servers"]]
        for exe in ("SR_GameServer.exe", "SR_ShardManager.exe", "GatewayServer.exe",
                    "AgentServer.exe"):
            self.assertIn(exe, names, exe)
        self.assertIn("SR_GameServer.pdb",
                      next(s["pdb"] for s in sp["game_servers"]
                           if s["name"] == "SR_GameServer.exe"))

    def test_server_motion_states_proven(self):
        ss = self.doc["server_strings"]
        self.assertTrue(ss["present"])
        self.assertEqual(ss["motion_state_count"], 19)
        for m in ("MOTIONSTATE_WALK", "MOTIONSTATE_RUN", "MOTIONSTATE_SIT",
                  "MOTIONSTATE_JUMP", "MOTIONSTATE_RIDE", "MOTIONSTATE_SKILL",
                  "MOTIONSTATE_STAND"):
            self.assertIn(m, ss["motion_states"], m)

    def test_server_spawn_flow_proven(self):
        ss = self.doc["server_strings"]
        for s in ("CGame::EnterWorld() => CGObj::EnterWorld()",
                  "ResolveCellAndHeight()", "ActivatePC()",
                  "CGObj::EnterWorld Failed!!! at MoveTo()"):
            self.assertIn(s, ss["spawn_flow"], s)

    def test_server_refdata_inventory(self):
        sr = self.doc["server_refdata"]
        self.assertTrue(sr["present"])
        self.assertTrue(sr["has_refregion"])
        self.assertTrue(sr["has_gameworlddata"])
        self.assertEqual(sr["characterdata_files_missing"],
                         ["CharacterData_40000.txt"])

    def test_proxy_net_admin_and_opcodes(self):
        px = self.doc["proxy"]
        self.assertIn(".NET", px["binary_type"])
        self.assertEqual(px["malicious_opcodes"]["count"], 38)
        self.assertIn("0x7777", px["malicious_opcodes"]["opcodes"])

    def test_spawn_chain_caller_is_shardmanager(self):
        sc = self.doc["spawn_chain"]
        self.assertTrue(sc["present"])
        self.assertEqual(sc["_addnewchar_caller"], "SR_ShardManager.exe")
        self.assertIn("_AddNewChar", sc["_addnewchar_call_format"])
        self.assertTrue(sc["_addnewchar_start_params_are_caller_supplied"])
        self.assertIn("LatestRegion", sc["char_last_position_select"])
        self.assertIn("_CharInstanceWorldDataUpdate",
                      sc["instance_world_position_update"])
        self.assertIn("CRefInstanceWorldStartPos", sc["start_pos_source"])

    def test_communication_sc_classes_no_cs_classes(self):
        cm = self.doc["communication"]
        self.assertTrue(cm["present"])
        self.assertEqual(cm["rec_msg_dat"], "RecMsg.dat")
        self.assertIn("Wait My Char Data", cm["wait_my_char_data"])
        self.assertGreaterEqual(cm["sc_message_class_count"], 50)
        self.assertIn("SC_ObjectCreate", cm["sc_message_classes"])
        self.assertIn("SC_ObjectMoveTo", cm["sc_message_classes"])
        self.assertIn("SC_ObjectMotionState", cm["sc_message_classes"])
        self.assertTrue(cm["cs_message_classes_absent"])

    def test_position_system_and_navmesh_symbols(self):
        ss = self.doc["server_strings"]
        for s in ("Pos_RegionID", "DestPos_RegionID", "LastUpdateTick"):
            self.assertIn(s, ss["position_system"], s)
        self.assertIn("CRTNavMeshTerrain", ss["navmesh_terrain"])
        self.assertIn("regioninfo.txt", ss["navmesh_terrain"])

    def test_message_layer_dispatch_proven(self):
        ml = self.doc["message_layer"]
        self.assertTrue(ml["present"])
        client = ml["client_dispatch_serialization"]
        for s in ("MsgStreamBuffer.h", "NetEngine::MsgPool", "m_nCurrentReadMsg",
                  "RecMsg.dat"):
            self.assertIn(s, client, s)
        server = ml["gameserver_dispatch_serialization"]
        for s in ("CGame::ProcessMessage() MsgID : %x",
                  "Unhandled Game SR_MSG: 0x%x [data size: %d]",
                  "INVALID_MSG_HEADER", "INVALID_MSGSIZE", "NO_MSGTARGET",
                  "DumpMsgPool"):
            self.assertIn(s, server, s)
        self.assertIn("NOT recoverable", ml["opcode_message_mapping"])

    def test_coordinate_system_structure_proven_scale_unknown(self):
        cs = self.doc["coordinate_system"]
        self.assertTrue(cs["present"])
        rr = cs["refregion"]
        self.assertEqual(rr["column_count"], 21)
        self.assertGreaterEqual(rr["row_count"], 2000)
        mi = cs["worldmap_mapinfo"]
        self.assertIn("region_bounds", mi["proven_columns"])
        self.assertIn("coord_bounds", mi["proven_columns"])
        self.assertIn("UNKNOWN", cs["world_unit_conversion"])

    def test_instance_world_startpos_data_missing(self):
        sr = self.doc["server_refdata"]
        self.assertFalse(sr["has_refinstanceworldstartpos"])
        self.assertFalse(sr["has_refinstanceworldregion"])
        sc = self.doc["spawn_chain"]
        self.assertTrue(sc["instance_world_startpos_datafile_missing"])
        self.assertEqual(sc["instance_world_config_via_lua"],
                         "LuaSetInstanceWorldConfig")
        self.assertIn("RefGameWorldNPC", sc["instance_world_npc_ref"])

    def test_conclusions_record_new_pass(self):
        c = self.doc["conclusions"]
        self.assertIn("ProcessMessage()", c["message_layer"])
        self.assertIn("LuaSetInstanceWorldConfig", c["start_position"])
        self.assertIn("UNKNOWN", c["world_unit_conversion"])

    def test_regioncode_encoding_recorded(self):
        cs = self.doc["coordinate_system"]
        self.assertEqual(cs["regioncode"]["encoding"], "CP949 (Korean)")
        self.assertGreaterEqual(cs["regioncode"]["row_count"], 1000)


if __name__ == "__main__":
    unittest.main()
