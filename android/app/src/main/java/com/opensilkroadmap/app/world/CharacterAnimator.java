package com.opensilkroadmap.app.world;

import com.opensilkroadmap.app.game.AnimationPlayer;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Per-entity character animation state machine. Binds a resolved clip set
 * (state -> clip from {@link AnimStateResolver}) to a single
 * {@link AnimationPlayer} clock, so every character instance animates
 * independently with its own state and elapsed time.
 *
 * <p>Each instance starts in {@link AnimState#IDLE}. Switching to a state with
 * no resolved clip falls back to idle (or clears playback when idle itself is
 * absent). One-shot states ({@code ATTACK}, {@code DAMAGE}) return to idle when
 * the clip completes; {@code DEATH} is terminal and holds its final frame.
 * {@code DOWN} and {@code WAKEUP} are proven clip states whose transition order
 * is client code (UNKNOWN), so the runtime never drives them and they hold
 * their final frame rather than auto-transitioning.
 *
 * <p>Pure JVM: state selection and timing only; pose sampling and rendering are
 * done by the Android {@code NativeWorldRenderer} via
 * {@code CharacterMeshIndex.poseAt}.
 */
public final class CharacterAnimator {

  private final Map<AnimState, IdleAnimResolver.Clip> clips;
  private final AnimationPlayer player = new AnimationPlayer();
  private AnimState state;

  public CharacterAnimator(Map<AnimState, IdleAnimResolver.Clip> clips) {
    Map<AnimState, IdleAnimResolver.Clip> copy =
        new LinkedHashMap<AnimState, IdleAnimResolver.Clip>();
    if (clips != null) {
      copy.putAll(clips);
    }
    this.clips = Collections.unmodifiableMap(copy);
    this.state = AnimState.IDLE;
    IdleAnimResolver.Clip idle = this.clips.get(AnimState.IDLE);
    if (idle != null) {
      player.setClip(idle.name, idle.durationMs, AnimState.IDLE.looping());
    }
  }

  public AnimState state() {
    return state;
  }

  /** True when the character has a resolved clip for the given state. */
  public boolean hasClip(AnimState s) {
    return clips.containsKey(s);
  }

  /** Switches state; no-op when already in that state (avoids clip restart). */
  public void setState(AnimState s) {
    if (s == state) {
      return;
    }
    IdleAnimResolver.Clip clip = clips.get(s);
    AnimState target = s;
    if (clip == null && s != AnimState.IDLE) {
      clip = clips.get(AnimState.IDLE);
      target = AnimState.IDLE;
    }
    if (clip == null) {
      player.clear();
    } else {
      player.setClip(clip.name, clip.durationMs, target.looping());
    }
    state = target;
  }

  /** Advances the clock; transient one-shot states return to idle on finish. */
  public void update(double dtSeconds) {
    player.advance(dtSeconds);
    if ((state == AnimState.ATTACK || state == AnimState.DAMAGE)
        && player.isFinished()) {
      setState(AnimState.IDLE);
    }
  }

  /** Name of the active clip, or "" when no clip is active. */
  public String currentClipName() {
    return player.name();
  }

  public int currentTimeMs() {
    return player.currentTimeMs();
  }

  public boolean isFinished() {
    return player.isFinished();
  }

  /** True when a clip is currently playing. */
  public boolean active() {
    return player.durationMs() > 0;
  }
}
