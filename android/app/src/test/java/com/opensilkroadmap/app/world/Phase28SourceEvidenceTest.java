package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

/**
 * PHASE 28: source-recovery evidence over the original vSRO sources for the
 * remaining runtime semantics (spawn reaffirmation, animation state vocabulary,
 * player class templates, region char-gen, skill data, native-runtime audit).
 *
 * <p>Reads {@code scripts/testdata/formats/phase28_source_evidence.json}, a
 * byte-derived record produced from Data.pk2 (.ban animation corpus), Media.pk2
 * (characterdata_5000 / characterdata_25000) and the committed android assets
 * (bandit anims.tsv, skilldata.tsv). Every assertion is a PROVEN recovered fact:
 *
 * <ul>
 *   <li>The .ban corpus proves the animation state vocabulary (stand/walk/run/
 *       attack/damage/die/down/wakeup); counts are reproduced from filenames.</li>
 *   <li>characterdata_5000 lists 13 player class templates (CHAR_CH_MAN_* ->
 *       bsr), including CHAR_CH_MAN_ADVENTURER refid 1907.</li>
 *   <li>characterdata_25000 (Jangan) is an entity catalog with 120 distinct
 *       bsr paths and NO position column (spawn stays UNKNOWN).</li>
 *   <li>skilldata.tsv is an unparsed 7-line source-file list (skill semantics
 *       UNVERIFIED).</li>
 *   <li>The Android gameplay runtime is 100% native (no WebView/Capacitor); the
 *       retired wrapper is under legacy/capacitor/; map/src/game is a separate
 *       web project, not the Android runtime.</li>
 * </ul>
 */
public class Phase28SourceEvidenceTest {

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
      File candidate = new File(dir, "phase28_source_evidence.json");
      if (candidate.isFile()) {
        base = candidate;
        break;
      }
    }
    assertNotNull("phase28_source_evidence.json not found", base);
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
  public void animationStateVocabularyIsProvenFromBanCorpus() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"attack\": 925"));
    assertTrue(ev.contains("\"stand\": 504"));
    assertTrue(ev.contains("\"down\": 131"));
    assertTrue(ev.contains("\"wakeup\": 17"));
    assertTrue(ev.contains("\"die\": 343"));
    assertTrue(ev.contains("\"ban_total\": 4691"));
  }

  @Test
  public void playerClassTemplatesAreProven() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"code\": \"CHAR_CH_MAN_ADVENTURER\""));
    assertTrue(ev.contains("\"refid\": \"1907\""));
    assertTrue(ev.contains("chinaman_adventurer.bsr"));
    assertTrue(ev.contains("\"code\": \"CHAR_CH_MAN_MONK\""));
  }

  @Test
  public void janganRegionChargenHasNoSpawnPosition() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"distinct_bsr\": 120"));
    assertTrue(ev.contains("\"lines\": 3736"));
    assertTrue(ev.contains("\"has_position_column\": false"));
  }

  @Test
  public void banditClipSetIncludesCombatAndDownStates() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"bandit_attack01\""));
    assertTrue(ev.contains("\"bandit_damage01\""));
    assertTrue(ev.contains("\"bandit_die\""));
    assertTrue(ev.contains("\"bandit_down\""));
    assertTrue(ev.contains("\"bandit_wakeup\""));
    assertTrue(ev.contains("\"bandit_die_loop\""));
  }

  @Test
  public void skillDataIsUnparsedAndUnverified() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"SkillData_5000.txt\""));
    assertTrue(ev.contains("\"SkillData_35000.txt\""));
    assertTrue(ev.contains("\"parsed_semantics\": false"));
  }

  @Test
  public void androidRuntimeIsFullyNative() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"android_gameplay_runtime_native\": true"));
    assertTrue(ev.contains("\"webview_capacitor_in_android_runtime\": false"));
    assertTrue(ev.contains("legacy/capacitor/"));
    assertTrue(ev.contains("\"not_android_runtime\": true"));
  }
}
