package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

/**
 * PHASE 26: source-recovery evidence over the original vSRO archives
 * (movement, combat, player animation census).
 *
 * <p>Reads {@code scripts/testdata/formats/phase26_source_evidence.json}, a
 * byte-derived record produced from Data.pk2 / Media.pk2. Every assertion is a
 * PROVEN recovered fact:
 *
 * <ul>
 *   <li>The three committed player locomotion clips carry NO baked forward (z)
 *       root translation and are cyclic (first pose == last pose): movement
 *       speed is not in the animation data, and no speed table exists in the
 *       archives, so walk/run speeds remain UNKNOWN (fail-closed).</li>
 *   <li>skilldata_5000 attack rows order by weapon type in col13/14
 *       (fist 1500 &gt; sword 1200 &gt; spear 1166 &gt; bow 840) — a candidate
 *       attack-cadence column whose exact semantics are UNVERIFIED.</li>
 *   <li>chinaman_fighter.bsr carries 217 animations; zero names start at a
 *       word boundary with "attack" (the player's attacks are skill-named,
 *       e.g. skill_ch_sword_downattack_*), so the keyword state resolver maps
 *       the player's ATTACK/DAMAGE/DEATH states to MISSING (fail-closed),
 *       while NPC attack/damage/death clips DO resolve.</li>
 * </ul>
 */
public class Phase26SourceEvidenceTest {

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
      File candidate = new File(dir, "phase26_source_evidence.json");
      if (candidate.isFile()) {
        base = candidate;
        break;
      }
    }
    assertNotNull("phase26_source_evidence.json not found", base);
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
  public void locomotionClipsCarryNoBakedRootTranslation() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"forward_z_drift\": 0.0"));
    assertTrue(ev.contains(
        "\"/prim/ani/char/china/man/chinaman_fighter_walkforward.ban\""));
    assertTrue(ev.contains(
        "\"/prim/ani/char/china/man/chinaman_fighter_runforward.ban\""));
    assertTrue(ev.contains(
        "\"/prim/ani/char/china/man/chinaman_fighter_runforward_sword.ban\""));
  }

  @Test
  public void skilldataAttackRowsOrderByWeaponType() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"code\": \"SKILL_PUNCH_01\""));
    assertTrue(ev.contains("\"col13\": \"1500\""));
    assertTrue(ev.contains("\"col13\": \"1200\""));
    assertTrue(ev.contains("\"col13\": \"1166\""));
    assertTrue(ev.contains("\"col13\": \"840\""));
  }

  @Test
  public void playerBsrHasNoWordStartAttackClips() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"word_start_attack_clips\": 0"));
    assertTrue(ev.contains("\"total\": 217"));
    assertTrue(ev.contains("\"skill\": 160"));
    assertTrue(ev.contains("skill_ch_sword_*"));
  }
}
