package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import com.opensilkroadmap.app.world.AnimState;
import com.opensilkroadmap.app.world.CharacterCatalog;
import com.opensilkroadmap.app.world.CharacterMeshIndex;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

/**
 * TASK B: player identity resolution over the committed {@code player} chain.
 *
 * <p>PROVEN at file level: the player key is {@value PlayerIdentity#PLAYER_KEY}
 * ({@link CharacterCatalog#PLAYER_KEY}); the committed manifest references 5
 * real {@code .ban} clips and the committed skeleton parses to 38 bones
 * ({@code chinaman_skel.bsk}). The resolved states are exactly IDLE/WALK/RUN
 * with the real clip names and real durations (no attack/damage/death clips
 * exist in the player manifest).
 *
 * <p>PARTIAL: the provenance records the original {@code chinaman_fighter.bsr}
 * referencing {@code europeman_skel} (43 bones), not the committed 38-bone
 * {@code chinaman_skel} — an original-source mismatch kept visible, not hidden.
 *
 * <p>Fail-closed: an unavailable chain yields an unresolved identity.
 */
public class PlayerIdentityTest {

  private static final String[] ASSET_DIRS = {
    "src/main/assets/game/world/characters",
    "../src/main/assets/game/world/characters",
    "app/src/main/assets/game/world/characters",
    "../app/src/main/assets/game/world/characters",
  };

  private static File findRoot() {
    for (String dir : ASSET_DIRS) {
      File f = new File(dir);
      if (f.isDirectory()) {
        return f;
      }
    }
    return null;
  }

  private static byte[] readAsset(File root, String name) throws IOException {
    File f = new File(root, name);
    if (!f.isFile()) {
      throw new IOException("asset not found: " + name);
    }
    FileInputStream in = new FileInputStream(f);
    try {
      java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
      byte[] buf = new byte[8192];
      int n;
      while ((n = in.read(buf)) != -1) {
        out.write(buf, 0, n);
      }
      return out.toByteArray();
    } finally {
      in.close();
    }
  }

  private static PlayerIdentity resolveReal() throws IOException {
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    return PlayerIdentity.resolve(
        new InputStreamReader(new ByteArrayInputStream(readAsset(
            root, "player/manifest.json")), StandardCharsets.UTF_8),
        new InputStreamReader(new ByteArrayInputStream(readAsset(root,
            "shared/skel/prim_skel_char_china_chinaman_skel.json")),
            StandardCharsets.UTF_8));
  }

  @Test
  public void playerKeyIsTheCatalogPlayerKey() {
    assertEquals(CharacterCatalog.PLAYER_KEY, PlayerIdentity.PLAYER_KEY);
    assertEquals("player", PlayerIdentity.PLAYER_KEY);
  }

  @Test
  public void realPlayerChainResolves() throws IOException {
    PlayerIdentity id = resolveReal();
    assertTrue("player manifest+skeleton chain must resolve", id.isResolved());
    assertEquals(5, id.clipCount());
    assertEquals(38, id.boneCount());
    assertTrue(id.skeletonPath().contains("chinaman_skel.bsk"));
  }

  @Test
  public void realPlayerStatesAreExactlyLocomotion() throws IOException {
    PlayerIdentity id = resolveReal();
    assertEquals(3, id.states().size());
    assertTrue(id.hasState(AnimState.IDLE));
    assertTrue(id.hasState(AnimState.WALK));
    assertTrue(id.hasState(AnimState.RUN));
    assertFalse(id.hasState(AnimState.ATTACK));
    assertFalse(id.hasState(AnimState.DAMAGE));
    assertFalse(id.hasState(AnimState.DEATH));
    assertEquals("chinaman_standbattle",
        id.states().get(AnimState.IDLE).name);
    assertEquals(2000, id.states().get(AnimState.IDLE).durationMs);
    assertEquals("chinaman_fighter_walkforward",
        id.states().get(AnimState.WALK).name);
    assertEquals(1166, id.states().get(AnimState.WALK).durationMs);
    assertEquals("chinaman_fighter_runforward_sword",
        id.states().get(AnimState.RUN).name);
    assertEquals(666, id.states().get(AnimState.RUN).durationMs);
  }

  @Test
  public void identityIsPartialFromProvenanceNotHidden() throws IOException {
    // The provenance explicitly records the 43-bone europeman_skel reference;
    // the committed skeleton is 38 bones. The record keeps the mismatch visible.
    PlayerIdentity id = resolveReal();
    assertEquals(38, id.boneCount());
    File root = findRoot();
    assertTrue("provenance.json must record the mismatch",
        readProvenance(root).contains("europeman_skel"));
    assertTrue(readProvenance(root).contains("43"));
  }

  @Test
  public void unresolvedIdentityFailsClosed() {
    PlayerIdentity u = PlayerIdentity.unresolved("manifest missing");
    assertFalse(u.isResolved());
    assertEquals(0, u.clipCount());
    assertEquals(0, u.boneCount());
    assertFalse(u.hasState(AnimState.WALK));
    assertEquals("", u.skeletonPath());
    assertEquals("manifest missing", u.reason());
  }

  private static String readProvenance(File root) throws IOException {
    byte[] b = readAsset(root, "player/provenance.json");
    return new String(b, StandardCharsets.UTF_8);
  }
}
