package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

/**
 * PHASE 29: deep-runtime-forensics evidence over the recovered original PC
 * client executable + configuration and the recovered server package,
 * previously classified unavailable.
 *
 * <p>Reads {@code scripts/testdata/formats/phase29_source_evidence.json}, a
 * static (read-only) record derived from:
 *
 * <ul>
 *   <li>GameClient.exe / edxSilkroadDll5.dll / GFXFileManager.dll string-level
 *       forensics (RTTI class names, source file paths, movement member
 *       m_nSpeed2, network message-id format).</li>
 *   <li>Media.pk2 /config/ option.txt, cameradata.txt, command.txt, define.txt.</li>
 *   <li>Media.pk2 characterdata_*.txt positional speed triplet.</li>
 *   <li>SRO_VT_SHARD.Bak stored procedure _InsertRefChar (Speed1/Speed2/Scale).</li>
 *   <li>SR_GameServer.exe + SR_ShardManager.exe + GatewayServer.exe +
 *       AgentServer.exe ... string-level server forensics (motion states,
 *       EnterWorld/spawn flow, ref classes, SQL) and SR_GameRefData/*.txt.</li>
 *   <li>VSRO-R proxy_cfg.ini (protocol version 188, gateway port 15779, .NET
 *       admin tool) and Vietnam-R v193 Offsets.txt.</li>
 * </ul>
 *
 * <p>Every assertion is a PROVEN recovered fact. Column semantics that cannot be
 * proven are labelled UNKNOWN/INFERRED and are NOT asserted as named meaning.
 */
public class Phase29SourceEvidenceTest {

  private static final String[] EVIDENCE_DIRS = {
    "src/main/assets",
    "../src/main/assets",
    "app/src/main/assets",
    "../app/src/main/assets",
    "../scripts/testdata/formats",
    "scripts/testdata/formats",
    "../../scripts/testdata/formats",
  };

  private static String evidenceText() throws IOException {
    File base = null;
    for (String dir : EVIDENCE_DIRS) {
      File candidate = new File(dir, "phase29_source_evidence.json");
      if (candidate.isFile()) {
        base = candidate;
        break;
      }
    }
    assertNotNull("phase29_source_evidence.json not found", base);
    FileInputStream in = new FileInputStream(base);
    try {
      java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
      byte[] buf = new byte[8192];
      int n;
      while ((n = in.read(buf)) != -1) {
        out.write(buf, 0, n);
      }
      return new String(out.toByteArray(), StandardCharsets.UTF_8);
    } finally {
      in.close();
    }
  }

  @Test
  public void clientExecutableIsRecoveredWithProvenSymbols() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"phase\": \"phase29\""));
    assertTrue(ev.contains("\"present\": true"));
    assertTrue(ev.contains("GameClient.exe"));
    assertTrue(ev.contains("edxSilkroadDll5.dll"));
    assertTrue(ev.contains("GFXFileManager.dll"));
    assertTrue(ev.contains("CCameraSlid"));
    assertTrue(ev.contains("CCameraWorking"));
    assertTrue(ev.contains("SC_CameraShake"));
    assertTrue(ev.contains("CAniMixer"));
    assertTrue(ev.contains("CPrimAnimation"));
    assertTrue(ev.contains("\"movement_member\": \"m_nSpeed2\""));
  }

  @Test
  public void optionDefaultsAreProven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"StartCharacter\": \"1907\""));
    assertTrue(ev.contains("\"Map\": \"0\""));
    assertTrue(ev.contains("\"StartWeapon\": \"0\""));
    assertTrue(ev.contains("CPSLoadingMission"));
    assertTrue(ev.contains("CPSVersionCheck"));
  }

  @Test
  public void cameraPresetsAndDebugCommandsAreProven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"preset_count\": 2"));
    assertTrue(ev.contains("\"default_marker_line\": \"-1\""));
    assertTrue(ev.contains("\"count\": 47"));
    assertTrue(ev.contains("\"/PlayerCount\""));
    assertTrue(ev.contains("\"/GetPos\""));
    assertTrue(ev.contains("\"/Debug\""));
  }

  @Test
  public void serverDbInsertRefCharProvesSpeedColumns() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"procedure\": \"_InsertRefChar\""));
    assertTrue(ev.contains("\"speed1_param_index\": 45"));
    assertTrue(ev.contains("\"speed2_param_index\": 46"));
    assertTrue(ev.contains("\"Speed1\""));
    assertTrue(ev.contains("\"Speed2\""));
    assertTrue(ev.contains("\"Scale\""));
    assertTrue(ev.contains("\"has_knockdown\": true"));
    assertTrue(ev.contains("\"has_ko_recover_time\": true"));
  }

  @Test
  public void playerTemplatesHaveRawSpeedTripletButUnprovenMapping() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"code\": \"CHAR_CH_MAN_ADVENTURER\""));
    assertTrue(ev.contains("\"refid\": \"1907\""));
    assertTrue(ev.contains("\"positional_col46\": \"16\""));
    assertTrue(ev.contains("\"positional_col47\": \"50\""));
    assertTrue(ev.contains("\"positional_col48\": \"100\""));
    assertTrue(ev.contains("INFERRED"));
    assertTrue(ev.contains("UNKNOWN"));
  }

  @Test
  public void proxyProtocolAndAuthorityAreProven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"version\": \"188\""));
    assertTrue(ev.contains("\"gateway_port\": \"15779\""));
    assertTrue(ev.contains("\"malicious_opcode_filtering\": \"True\""));
    assertTrue(ev.contains("server-authoritative"));
  }

  @Test
  public void serverPackageIsRecovered() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"SR_GameServer.exe\""));
    assertTrue(ev.contains("\"SR_ShardManager.exe\""));
    assertTrue(ev.contains("\"GatewayServer.exe\""));
    assertTrue(ev.contains("\"AgentServer.exe\""));
    assertTrue(ev.contains("SR_GameServer.pdb"));
    assertTrue(ev.contains("\"has_refdata\": true"));
    assertTrue(ev.contains("\"has_server_cfg\": true"));
  }

  @Test
  public void serverMotionStatesAreProven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"motion_state_count\": 19"));
    assertTrue(ev.contains("\"MOTIONSTATE_WALK\""));
    assertTrue(ev.contains("\"MOTIONSTATE_RUN\""));
    assertTrue(ev.contains("\"MOTIONSTATE_SIT\""));
    assertTrue(ev.contains("\"MOTIONSTATE_SKILL\""));
    assertTrue(ev.contains("\"MOTIONSTATE_STAND\""));
  }

  @Test
  public void serverSpawnFlowIsProvenAtSymbolLevel() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("CGame::EnterWorld() => CGObj::EnterWorld()"));
    assertTrue(ev.contains("ResolveCellAndHeight()"));
    assertTrue(ev.contains("ActivatePC()"));
    assertTrue(ev.contains("CGObj::EnterWorld Failed!!! at MoveTo()"));
    assertTrue(ev.contains("caller-supplied"));
  }

  @Test
  public void serverRefdataInventoryIsProven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"has_refregion\": true"));
    assertTrue(ev.contains("\"has_gameworlddata\": true"));
    assertTrue(ev.contains("CharacterData_40000.txt"));
  }

  @Test
  public void proxyIsDotNetAdminToolWithOpcodeList() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains(".NET"));
    assertTrue(ev.contains("\"count\": 38"));
    assertTrue(ev.contains("0x7777"));
  }

  @Test
  public void skillSemanticsAndSpawnRemainUnresolved() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("caller-supplied"));
    assertTrue(ev.contains("skill column semantics still UNKNOWN"));
    assertTrue(ev.contains("server package"));
  }

  @Test
  public void spawnChainCallerIsShardManager() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("SR_ShardManager.exe"));
    assertTrue(ev.contains("{?=CALL _AddNewChar"));
    assertTrue(ev.contains("LatestRegion"));
    assertTrue(ev.contains("_CharInstanceWorldDataUpdate"));
    assertTrue(ev.contains("CRefInstanceWorldStartPos"));
  }

  @Test
  public void communicationHasScClassesButNoCsClasses() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("RecMsg.dat"));
    assertTrue(ev.contains("Wait My Char Data"));
    assertTrue(ev.contains("SC_ObjectCreate"));
    assertTrue(ev.contains("SC_ObjectMoveTo"));
    assertTrue(ev.contains("SC_ObjectMotionState"));
    assertTrue(ev.contains("\"cs_message_classes_absent\": true"));
  }

  @Test
  public void positionSystemAndNavmeshSymbolsAreProven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("Pos_RegionID"));
    assertTrue(ev.contains("DestPos_RegionID"));
    assertTrue(ev.contains("LastUpdateTick"));
    assertTrue(ev.contains("CRTNavMeshTerrain"));
    assertTrue(ev.contains("regioninfo.txt"));
  }

  @Test
  public void messageLayerDispatchIsProvenButOpcodeMappingIsNot() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("MsgStreamBuffer.h"));
    assertTrue(ev.contains("NetEngine::MsgPool"));
    assertTrue(ev.contains("m_nCurrentReadMsg"));
    assertTrue(ev.contains("CGame::ProcessMessage() MsgID : %x"));
    assertTrue(ev.contains("Unhandled Game SR_MSG: 0x%x [data size: %d]"));
    assertTrue(ev.contains("INVALID_MSG_HEADER"));
    assertTrue(ev.contains("INVALID_MSGSIZE"));
    assertTrue(ev.contains("NO_MSGTARGET"));
    assertTrue(ev.contains("DumpMsgPool"));
    assertTrue(ev.contains("NOT recoverable"));
  }

  @Test
  public void coordinateSystemStructureIsProvenButScaleIsUnknown() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"column_count\": 21"));
    assertTrue(ev.contains("worldmap_mapinfo"));
    assertTrue(ev.contains("region_bounds"));
    assertTrue(ev.contains("coord_bounds"));
    assertTrue(ev.contains("CP949 (Korean)"));
    assertTrue(ev.contains("\"world_unit_conversion\": \"UNKNOWN:"));
  }

  @Test
  public void instanceWorldStartPosDataIsMissingAndLuaDriven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"has_refinstanceworldstartpos\": false"));
    assertTrue(ev.contains("\"has_refinstanceworldregion\": false"));
    assertTrue(ev.contains("\"instance_world_startpos_datafile_missing\": true"));
    assertTrue(ev.contains("LuaSetInstanceWorldConfig"));
    assertTrue(ev.contains("RefGameWorldNPC"));
  }

  @Test
  public void conclusionsRecordMessageLayerAndStartPosition() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("ProcessMessage()"));
    assertTrue(ev.contains("LuaSetInstanceWorldConfig"));
    assertTrue(ev.contains("concrete start values UNKNOWN"));
  }
}
