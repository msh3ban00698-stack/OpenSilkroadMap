package com.opensilkroadmap.app.game;

import com.opensilkroadmap.app.world.AnimState;
import com.opensilkroadmap.app.world.CharacterEntity;

/**
 * Player controller for the native runtime: binds the shared input intent
 * ({@link InputController} move axis) to the player {@link PlayerState}, the
 * player {@link CharacterEntity}, and the entity's proven animation state
 * machine, each update tick.
 *
 * <p>Fail-closed ordering:
 * <ol>
 *   <li>No entity or unresolved identity -> stays idle, never moves.</li>
 *   <li>No verified spawn -> stays idle; position is NEVER invented. The
 *       controller reports {@code reason = UNKNOWN_SPAWN} and the host keeps
 *       the player invisible (no world placement to draw).</li>
 *   <li>A verified spawn is applied exactly once ({@link #placed()}), at the
 *       proven projected world coordinate.</li>
 * </ol>
 *
 * <p>While spawned: a non-zero joystick direction drives the entity into the
 * proven locomotion state (WALK preferred, RUN fallback, IDLE last — the
 * walk/run split is UNKNOWN from source so the selection is explicit and
 * documented, not invented). The {@link PlayerMover} step applies displacement
 * ONLY when a speed is proven; with the current UNKNOWN speed the player plays
 * the real walk clip without fabricated movement ({@code reason = UNKNOWN_SPEED}).
 * Idle input returns the entity to IDLE. Each entity keeps its own animation
 * clock: this controller advances only the player entity, never NPCs.
 *
 * <p>Camera follow: {@link #cameraTarget()} returns the player's world position
 * once a verified spawn has been placed, or null (host keeps its own center).
 * Pure JVM, no Android.
 */
public final class PlayerController {

  /** Motion state: no movement direction. */
  public static final String MOTION_IDLE = "IDLE";
  /** Motion state: a movement direction is held (locomotion clip playing). */
  public static final String MOTION_MOVING = "MOVING";

  private final InputController input;
  private final PlayerState state;
  private final CharacterEntity entity;
  private final PlayerIdentity identity;
  private final PlayerSpawn spawn;
  private final PlayerMovementConfig config;

  private boolean placed;
  private String reason = "";
  private String motion = MOTION_IDLE;

  public PlayerController(InputController input, PlayerState state,
      CharacterEntity entity, PlayerIdentity identity, PlayerSpawn spawn,
      PlayerMovementConfig config) {
    if (input == null) {
      throw new NullPointerException("input");
    }
    if (state == null) {
      throw new NullPointerException("state");
    }
    if (identity == null) {
      throw new NullPointerException("identity");
    }
    if (spawn == null) {
      throw new NullPointerException("spawn");
    }
    if (config == null) {
      throw new NullPointerException("config");
    }
    this.input = input;
    this.state = state;
    this.entity = entity;
    this.identity = identity;
    this.spawn = spawn;
    this.config = config;
  }

  /** Advances the player one tick with a frame delta (same convention as NPCs). */
  public void update(double dt) {
    reason = "";
    if (entity == null) {
      reason = "NO_ENTITY";
      stayIdle();
      return;
    }
    if (!identity.isResolved()) {
      reason = "UNRESOLVED_IDENTITY";
      stayIdle();
      return;
    }
    if (!spawn.isKnown()) {
      reason = "UNKNOWN_SPAWN";
      stayIdle();
      return;
    }
    if (!placed) {
      place();
    }
    float mx = input.moveX();
    float mz = -input.moveY(); // screen +Y -> world -Z (proven projection)
    if (Math.hypot(mx, mz) < 1e-4f) {
      reason = "IDLE";
      stayIdle();
      return;
    }
    double len = Math.hypot(mx, mz);
    float dirX = (float) (mx / len);
    float dirZ = (float) (mz / len);
    state.setHeading((float) PlayerMover.headingFromDirection(dirX, dirZ));
    PlayerMover.Step step = PlayerMover.step(dirX, dirZ, dt, config);
    if (step.moved) {
      state.setPosition(state.x() + step.dx, state.y(), state.z() + step.dz);
      entity.setPosition((float) state.x(), (float) state.z());
      reason = PlayerMover.REASON_MOVED;
    } else {
      reason = step.reason;
    }
    entity.animator().setState(locomotionState());
    entity.update(dt);
    motion = MOTION_MOVING;
  }

  /** Applies the verified spawn exactly once at its proven world coordinate. */
  private void place() {
    float wx = spawn.worldX(spawn.sectorX());
    float wz = spawn.worldZ(spawn.sectorY());
    state.setPosition(wx, spawn.localY(), wz);
    entity.setPosition(wx, wz);
    placed = true;
  }

  /** Returns the entity to IDLE without disturbing position or state. */
  private void stayIdle() {
    if (entity != null && entity.animator().state() != AnimState.IDLE) {
      entity.animator().setState(AnimState.IDLE);
    }
    motion = MOTION_IDLE;
  }

  /**
   * Locomotion clip selection: WALK preferred, RUN fallback, IDLE last. The
   * original walk/run split depends on unproven speed rules, so the preference
   * is explicit and documented rather than invented.
   */
  private AnimState locomotionState() {
    if (identity.hasState(AnimState.WALK)) {
      return AnimState.WALK;
    }
    if (identity.hasState(AnimState.RUN)) {
      return AnimState.RUN;
    }
    return AnimState.IDLE;
  }

  public PlayerState state() {
    return state;
  }

  public CharacterEntity entity() {
    return entity;
  }

  /** True once a verified spawn has been placed (entity is world-positioned). */
  public boolean placed() {
    return placed;
  }

  /** True when the player identity chain (manifest + skeleton) resolved. */
  public boolean identityResolved() {
    return identity.isResolved();
  }

  /** Last update outcome reason (idle/unknown-spawn/moved/unknown-speed...). */
  public String reason() {
    return reason;
  }

  public String motion() {
    return motion;
  }

  /**
   * Camera follow target in world units, or null when the player has no placed
   * verified spawn (host keeps its own camera center).
   */
  public double[] cameraTarget() {
    if (!spawn.isKnown() || !placed) {
      return null;
    }
    return new double[] {state.x(), state.z()};
  }
}
