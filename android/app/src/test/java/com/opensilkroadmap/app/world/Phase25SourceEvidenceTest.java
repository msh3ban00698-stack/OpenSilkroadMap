package com.opensilkroadmap.app.world;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

/**
 * PHASE 25: source-recovery evidence over the original vSRO archives.
 *
 * <p>Reads {@code scripts/testdata/formats/phase25_source_evidence.json}, a
 * byte-derived record produced from Data.pk2 / Media.pk2. Every assertion here
 * is a PROVEN recovered fact (no runtime behavior is invented):
 *
 * <ul>
 *   <li>All 30 {@code /res/char/china/*.bsr} character files reference European
 *       skeletons (14 europeman, 13 europewoman, 1 chinaman, 2 hwan-hair) — the
 *       Phase 24 "skeleton mismatch" is the systematic original-source layout.</li>
 *   <li>{@code chinaman_fighter_runforward.ban} animates 5 europeman-only bones
 *       (cloak01..04, Bip01 L HandMid2): the fighter rig is europeman-based.</li>
 *   <li>Player clothes aa/ba/fa/ha/la bind only character-skeleton bones, while
 *       {@code clothes_01_sa} binds the {@code clothes_sa.bsk} item skeleton and
 *       {@code sword_01} binds the {@code sword_01.bsk} item skeleton.</li>
 *   <li>itemdata_5000 links each default CH_M clothes part and the sword to its
 *       real {@code .bsr} (col52) and {@code .ddj} (col54).</li>
 *   <li>{@code option.txt} records StartCharacter=1907 (=CHAR_CH_MAN_ADVENTURER).</li>
 *   <li>cameradata.txt rows are preserved verbatim; semantics UNKNOWN.</li>
 *   <li>No static server-side start/spawn table exists (spawn = UNKNOWN).</li>
 * </ul>
 */
public class Phase25SourceEvidenceTest {

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
      File candidate = new File(dir, "phase25_source_evidence.json");
      if (candidate.isFile()) {
        base = candidate;
        break;
      }
    }
    assertNotNull("phase25_source_evidence.json not found", base);
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
  public void chinaBsrSkeletonBindingIsSystematic() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"/prim/skel/char/europe/europeman_skel.bsk\": 14"));
    assertTrue(ev.contains("\"/prim/skel/char/europe/europewoman_skel.bsk\": 13"));
    assertTrue(ev.contains("\"/prim/skel/char/china/chinaman_skel.bsk\": 1"));
    assertTrue(ev.contains("\"/prim/skel/char/china/chinaman_hwan_hair.bsk\": 1"));
    assertTrue(ev.contains("\"/prim/skel/char/china/chinawoman_hwan_hair.bsk\": 1"));
  }

  @Test
  public void fighterRunAnimAnimatesEuropemanOnlyBones() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"europeman_only_channels\""));
    assertTrue(ev.contains("\"Bip01 L HandMid2\""));
    assertTrue(ev.contains("\"cloak01\""));
    assertTrue(ev.contains("\"cloak02\""));
    assertTrue(ev.contains("\"cloak03\""));
    assertTrue(ev.contains("\"cloak04\""));
    assertTrue(ev.contains("chinaman_fighter_runforward.ban"));
  }

  @Test
  public void clothesBindCharacterSkeletonSaIbindsItemSkeleton() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"clothes_01_aa\""));
    assertTrue(ev.contains("\"Bip01 R Forearm\""));
    assertTrue(ev.contains("\"Bip01 L Hand\""));
    assertTrue(ev.contains("\"membership\""));
    assertTrue(ev.contains("\"chinaman_skel\": true"));
    assertTrue(ev.contains("\"clothes_sa\": false"));
    assertTrue(ev.contains("\"/prim/skel/item/china/clothes_sa.bsk\""));
    assertTrue(ev.contains("\"bone_count\": 5"));
    assertTrue(ev.contains("\"Bone06\""));
  }

  @Test
  public void swordBindsItsOwnItemSkeleton() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"/prim/skel/item/china/weapon/sword_01.bsk\""));
    assertTrue(ev.contains("\"bone_count\": 4"));
    assertTrue(ev.contains("\"Bone01\""));
    assertTrue(ev.contains("\"Bone02\""));
    assertTrue(ev.contains("\"ai_start\""));
    assertTrue(ev.contains("\"code\": \"ITEM_CH_SWORD_01_A\""));
    assertTrue(ev.contains("\"id\": \"71\""));
  }

  @Test
  public void defaultOutfitHasItemdataRows() throws IOException {
    String ev = evidenceText();
    for (String code : new String[] {
      "ITEM_CH_M_CLOTHES_01_AA_A", "ITEM_CH_M_CLOTHES_01_BA_A",
      "ITEM_CH_M_CLOTHES_01_FA_A", "ITEM_CH_M_CLOTHES_01_HA_A",
      "ITEM_CH_M_CLOTHES_01_LA_A", "ITEM_CH_M_CLOTHES_01_SA_A"}) {
      assertTrue("missing " + code, ev.contains("\"code\": \"" + code + "\""));
    }
    assertTrue(ev.contains("clothes_01_aa.bsr"));
    assertTrue(ev.contains("sword_01.bsr"));
  }

  @Test
  public void optionTxtStartCharacterIsAdventurer() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("StartCharacter = \\\"1907\\\""));
    assertTrue(ev.contains("CHAR_CH_MAN_ADVENTURER"));
    assertTrue(ev.contains("chinaman_adventurer.bsr"));
    assertTrue(ev.contains("Map = \\\"0\\\""));
  }

  @Test
  public void cameradataRowsPreservedSemanticsUnknown() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"first_line\": \"-1\""));
    assertTrue(ev.contains("\"1205\""));
    assertTrue(ev.contains("\"1466\""));
    assertTrue(ev.contains("\"schema_semantics\": \"UNKNOWN"));
  }

  @Test
  public void playerSpawnStaysUnknownFailClosed() throws IOException {
    String ev = evidenceText();
    assertTrue(ev.contains("\"status\": \"UNKNOWN\""));
    assertTrue(ev.contains("server-side start/spawn table"));
    assertTrue(ev.contains("StartCharacter=1907"));
  }
}
