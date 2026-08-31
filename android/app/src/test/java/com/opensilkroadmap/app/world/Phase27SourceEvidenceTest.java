package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

/**
 * PHASE 27: source-recovery evidence over the original vSRO sources for the
 * real player runtime (spawn, input, movement, camera).
 *
 * <p>Reads {@code scripts/testdata/formats/phase27_source_evidence.json}, a
 * byte-derived record produced from SRO_VT_SHARD.Bak (server DB backup) and
 * Media.pk2. Every assertion is a PROVEN recovered fact:
 *
 * <ul>
 *   <li>_AddNewChar receives @StartRegionID / @StartPos_X/Y/Z from the caller
 *       and writes them into _Char.LatestRegion / PosX / PosY / PosZ; the only
 *       server hint is the developer comment "set @StartRegionID=25000", so the
 *       runtime start position stays UNKNOWN (fail-closed).</li>
 *   <li>Client reference table regioncode.txt maps region 25000 to RN_CH_JANGAN
 *       (CP949 caption decodes to Korean "Jangan"), proving the commented example
 *       means "start in Jangan".</li>
 *   <li>Input: client defines an input-options window (shortcut-key user rule),
 *       a key-option slot widget and a per-user binary OptionSet (681 bytes);
 *       the key-to-action mapping semantics are client-code and UNKNOWN.</li>
 *   <li>Camera: three modes (FREE, THIRD_PERSON, QUARTER_VIEW) and a camera-data
 *       debug window; numeric camera parameters are client-code and UNKNOWN.</li>
 *   <li>Movement: only client debug commands /fast and /setspeed exist; Phase 26
 *       negative proof (no speed table, no baked root motion) stands.</li>
 * </ul>
 */
public class Phase27SourceEvidenceTest {

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
      File candidate = new File(dir, "phase27_source_evidence.json");
      if (candidate.isFile()) {
        base = candidate;
        break;
      }
    }
    assertNotNull("phase27_source_evidence.json not found", base);
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
  public void startPositionIsCallerSuppliedAndUnknown() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"creation_proc\": \"_AddNewChar\""));
    assertTrue(ev.contains("\"@StartRegionID\""));
    assertTrue(ev.contains("\"@StartPos_X\""));
    assertTrue(ev.contains("\"LatestRegion\""));
    assertTrue(ev.contains("\"start_position\": \"UNKNOWN (fail-closed)\""));
    assertTrue(ev.contains("set @StartRegionID=25000"));
  }

  @Test
  public void region25000IsRN_CH_JANGAN() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"region_id\": 25000"));
    assertTrue(ev.contains("\"code\": \"RN_CH_JANGAN\""));
  }

  @Test
  public void inputEvidenceProvenSemanticsUnknown() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("UIIT_STT_SHORTENKEY_USER_RULE"));
    assertTrue(ev.contains("\"size_bytes\": 681"));
    assertTrue(ev.contains("Runtime keyboard input"));
  }

  @Test
  public void cameraModesProvenParametersUnknown() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("UIIT_STT_SIGHT_QUARTER_VIEW_DESC"));
    assertTrue(ev.contains("UIIT_STT_SIGHT_THIRD_PERSON_DESC"));
    assertTrue(ev.contains("UIIT_STT_SIGHT_FREE_DESC"));
    assertTrue(ev.contains("GDR_ST_CAMERA_ROTATION"));
  }

  @Test
  public void movementRemainsFailClosed() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("/setspeed %d"));
    assertTrue(ev.contains("/fast"));
    assertTrue(ev.contains("Walk/run speed: UNKNOWN (fail-closed)"));
  }
}
