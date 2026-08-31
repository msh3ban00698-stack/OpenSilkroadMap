package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import android.content.res.AssetManager;
import com.opensilkroadmap.app.world.AnimState;
import com.opensilkroadmap.app.world.CharacterCatalog;
import com.opensilkroadmap.app.world.CharacterEntity;
import com.opensilkroadmap.app.world.CharacterMeshIndex;
import com.opensilkroadmap.app.world.WorldCoordinates;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import org.junit.Test;

/**
 * TASK C/D/E/G integration: the player controller over a REAL loaded player
 * model (the committed manifest -> 38-bone skeleton -> 16 skinned meshes -> 5
 * real anims chain, loaded via the file-backed {@link AssetManager} harness
 * stub).
 *
 * <p>Locked contracts:
 * <ul>
 *   <li>Unknown spawn -> fail-closed: never placed, never moved, no camera
 *       target, stays IDLE.</li>
 *   <li>Unresolved identity / no entity -> fail-closed idle.</li>
 *   <li>Verified spawn (SYNTHETIC in these tests) places the entity exactly
 *       once at the proven projected world coordinate.</li>
 *   <li>Input direction drives the proven IDLE/WALK/RUN animator on the player
 *       entity only; WALK is selected for locomotion (run split UNKNOWN).</li>
 *   <li>Displacement is applied ONLY with a proven speed; the current UNKNOWN
 *       speed plays the real walk clip without fabricated movement.</li>
 *   <li>Camera follow target mirrors the placed player position.</li>
 *   <li>The controller never advances another entity's animation clock.</li>
 * </ul>
 */
public class PlayerControllerTest {

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

  private static CharacterMeshIndex realPlayerModel() {
    // The FULL player model chain is PARTIAL (2 gear parts reference
    // europeman-skeleton bones absent from the committed 38-bone chinaman_skel),
    // so the strict loader fails closed. The ANIMATION chain is fully committed:
    // the animation-only index drives the real IDLE/WALK/RUN animator.
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    try {
      return CharacterMeshIndex.animationsOnlyIndex(
          CharacterCatalog.PLAYER_KEY,
          new InputStreamReader(new ByteArrayInputStream(readAsset(
              root, "player/manifest.json")), StandardCharsets.UTF_8),
          new InputStreamReader(new ByteArrayInputStream(readAsset(root,
              "shared/skel/prim_skel_char_china_chinaman_skel.json")),
              StandardCharsets.UTF_8));
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  @Test
  public void fullPlayerModelLoadIsPartialAndFailsClosed() {
    // The strict loader must NOT return a partial player model: 2 of 16 mesh
    // parts (clothes_01_sa, sword_01) reference bones (Bone01/03/05) absent
    // from the committed 38-bone skeleton — the PARTIAL identity in data.
    CharacterMeshIndex m =
        CharacterMeshIndex.load(new AssetManager(), CharacterCatalog.PLAYER_KEY);
    assertNull("full player model must fail closed (PARTIAL chain)", m);
  }

  private static PlayerIdentity realIdentity() throws IOException {
    File root = findRoot();
    assertNotNull("characters assets root not found", root);
    return PlayerIdentity.resolve(
        new InputStreamReader(new ByteArrayInputStream(readAsset(
            root, "player/manifest.json")), StandardCharsets.UTF_8),
        new InputStreamReader(new ByteArrayInputStream(readAsset(root,
            "shared/skel/prim_skel_char_china_chinaman_skel.json")),
            StandardCharsets.UTF_8));
  }

  private static PlayerSpawn syntheticSpawn() {
    return PlayerSpawn.verified(
        WorldCoordinates.packRegion(156, 89), 123f, 0f, 456f, "SYNTHETIC test source");
  }

  private static PlayerController controller(
      PlayerSpawn spawn, PlayerMovementConfig config, boolean withEntity)
      throws IOException {
    return new PlayerController(
        new InputController(),
        new PlayerState(CharacterCatalog.PLAYER_KEY, "Player"),
        withEntity ? new CharacterEntity(realPlayerModel()) : null,
        realIdentity(), spawn, config);
  }

  @Test
  public void unknownSpawnFailsClosed() throws IOException {
    PlayerController pc = controller(
        PlayerSpawn.unknown("no verified spawn"), PlayerMovementConfig.unknownSpeed(), true);
    pc.update(0.05);
    assertFalse(pc.placed());
    assertEquals("UNKNOWN_SPAWN", pc.reason());
    assertEquals(PlayerController.MOTION_IDLE, pc.motion());
    assertEquals(0.0, pc.state().x(), 1e-9);
    assertEquals(0.0, pc.state().z(), 1e-9);
    assertEquals(0f, pc.entity().worldX(), 1e-6f);
    assertNull("no camera follow without a placed spawn", pc.cameraTarget());
    assertEquals(AnimState.IDLE, pc.entity().animator().state());
    assertEquals("chinaman_standbattle", pc.entity().animator().currentClipName());
  }

  @Test
  public void unresolvedIdentityFailsClosed() throws IOException {
    CharacterEntity entity = new CharacterEntity(realPlayerModel());
    PlayerController pc = new PlayerController(
        new InputController(),
        new PlayerState(CharacterCatalog.PLAYER_KEY, "Player"),
        entity, PlayerIdentity.unresolved("manifest missing"),
        syntheticSpawn(), PlayerMovementConfig.withWalkSpeed(10.0));
    pc.update(0.05);
    assertFalse(pc.placed());
    assertEquals("UNRESOLVED_IDENTITY", pc.reason());
    assertFalse(pc.identityResolved());
  }

  @Test
  public void noEntityFailsClosed() throws IOException {
    PlayerController pc = controller(
        syntheticSpawn(), PlayerMovementConfig.withWalkSpeed(10.0), false);
    pc.update(0.05);
    assertEquals("NO_ENTITY", pc.reason());
    assertEquals(PlayerController.MOTION_IDLE, pc.motion());
  }

  @Test
  public void verifiedSpawnPlacesEntityExactlyOnce() throws IOException {
    PlayerController pc = controller(
        syntheticSpawn(), PlayerMovementConfig.unknownSpeed(), true);
    pc.update(0.05);
    assertTrue(pc.placed());
    assertEquals(123f, pc.entity().worldX(), 1e-4f);
    assertEquals(456f, pc.entity().worldZ(), 1e-4f);
    assertEquals(123f, pc.state().x(), 1e-4);
    assertEquals(456f, pc.state().z(), 1e-4);
    // A second tick must not re-place (position is stable).
    pc.update(0.05);
    assertEquals(123f, pc.entity().worldX(), 1e-4f);
    assertEquals(456f, pc.entity().worldZ(), 1e-4f);
  }

  @Test
  public void inputDrivesProvenWalkAnimationWithUnknownSpeed() throws IOException {
    PlayerController pc = controller(
        syntheticSpawn(), PlayerMovementConfig.unknownSpeed(), true);
    InputController in = new InputController();
    // Rebuild with the shared input to inject direction.
    pc = new PlayerController(in, pc.state(), pc.entity(),
        realIdentity(), syntheticSpawn(), PlayerMovementConfig.unknownSpeed());
    pc.update(0.05);
    in.joystick(100f, 0f, 100f); // push right -> world +X
    pc.update(0.05);
    assertEquals(PlayerController.MOTION_MOVING, pc.motion());
    assertEquals("UNKNOWN_SPEED", pc.reason());
    assertEquals(AnimState.WALK, pc.entity().animator().state());
    assertEquals("chinaman_fighter_walkforward",
        pc.entity().animator().currentClipName());
    // Facing world +X -> heading atan2(1, 0) = pi/2.
    assertEquals(Math.PI / 2.0, pc.state().heading(), 1e-4);
    // No fabricated displacement with unproven speed.
    assertEquals(123f, pc.state().x(), 1e-4);
    assertEquals(456f, pc.state().z(), 1e-4);
  }

  @Test
  public void releasingInputReturnsToIdle() throws IOException {
    PlayerController pc = controller(
        syntheticSpawn(), PlayerMovementConfig.unknownSpeed(), true);
    InputController in = new InputController();
    pc = new PlayerController(in, pc.state(), pc.entity(),
        realIdentity(), syntheticSpawn(), PlayerMovementConfig.unknownSpeed());
    pc.update(0.05);
    in.joystick(100f, 0f, 100f);
    pc.update(0.05);
    assertEquals(AnimState.WALK, pc.entity().animator().state());
    in.joystick(0f, 0f, 100f); // release
    pc.update(0.05);
    assertEquals(PlayerController.MOTION_IDLE, pc.motion());
    assertEquals(AnimState.IDLE, pc.entity().animator().state());
    assertEquals("chinaman_standbattle",
        pc.entity().animator().currentClipName());
  }

  @Test
  public void provenSpeedMovesStateAndEntity() throws IOException {
    PlayerController pc = controller(
        syntheticSpawn(), PlayerMovementConfig.withWalkSpeed(10.0), true);
    InputController in = new InputController();
    pc = new PlayerController(in, pc.state(), pc.entity(),
        realIdentity(), syntheticSpawn(), PlayerMovementConfig.withWalkSpeed(10.0));
    pc.update(0.05);
    in.joystick(100f, 0f, 100f);
    pc.update(0.10);
    assertEquals(PlayerMover.REASON_MOVED, pc.reason());
    assertEquals(123f + 10.0 * 0.10, pc.state().x(), 1e-4);
    assertEquals(456f, pc.state().z(), 1e-4);
    assertEquals((float) (123f + 1.0), pc.entity().worldX(), 1e-4f);
    assertEquals(456f, pc.entity().worldZ(), 1e-4f);
  }

  @Test
  public void cameraTargetMirrorsPlacedPlayer() throws IOException {
    PlayerController pc = controller(
        syntheticSpawn(), PlayerMovementConfig.withWalkSpeed(10.0), true);
    pc.update(0.05);
    double[] target = pc.cameraTarget();
    assertNotNull("placed player must provide a follow target", target);
    assertEquals(123f, target[0], 1e-4);
    assertEquals(456f, target[1], 1e-4);
    PlayerController unknown = controller(
        PlayerSpawn.unknown("no source"), PlayerMovementConfig.unknownSpeed(), true);
    unknown.update(0.05);
    assertNull(unknown.cameraTarget());
  }

  @Test
  public void controllerNeverTouchesAnotherEntityClock() throws IOException {
    PlayerController pc = controller(
        syntheticSpawn(), PlayerMovementConfig.withWalkSpeed(10.0), true);
    CharacterEntity other = new CharacterEntity(realPlayerModel());
    InputController in = new InputController();
    pc = new PlayerController(in, pc.state(), pc.entity(),
        realIdentity(), syntheticSpawn(), PlayerMovementConfig.withWalkSpeed(10.0));
    assertTrue("player entity and bystander must be distinct instances",
        pc.entity() != other);
    for (int i = 0; i < 5; i++) {
      in.joystick(100f, 0f, 100f);
      pc.update(0.05);
    }
    assertEquals(AnimState.WALK, pc.entity().animator().state());
    assertTrue("player clock must have advanced",
        pc.entity().animator().currentTimeMs() > 0);
    assertEquals("bystander must stay untouched (idle, time 0)",
        AnimState.IDLE, other.animator().state());
    assertEquals(0, other.animator().currentTimeMs());
  }
}
