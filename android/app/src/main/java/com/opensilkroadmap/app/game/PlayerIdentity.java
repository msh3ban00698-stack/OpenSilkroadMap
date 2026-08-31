package com.opensilkroadmap.app.game;

import com.opensilkroadmap.app.world.AnimState;
import com.opensilkroadmap.app.world.AnimStateResolver;
import com.opensilkroadmap.app.world.CharacterMeshIndex;
import com.opensilkroadmap.app.world.IdleAnimResolver;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Resolved identity of the PLAYER character for the native runtime.
 *
 * <p>The player is the committed character key {@value #PLAYER_KEY}
 * ({@code game/world/characters/player/manifest.json}, provenance
 * {@code chinaman_fighter.bsr}). It is NOT in the NPC refid index and is never
 * spawned by npcpos; the player identity is resolved from its own committed
 * manifest + skeleton chain.
 *
 * <p>Identity is PARTIAL from the original source: the committed skeleton is
 * {@code chinaman_skel.bsk} (38 bones) while the provenance
 * {@code chinaman_fighter.bsr} references {@code europeman_skel} (43 bones), a
 * known original-source mismatch that this record keeps visible. Resolved
 * animation states are produced by {@link AnimStateResolver} over the real
 * committed clip list (stand -> IDLE, walk -> WALK, run -> RUN), so only
 * evidence-backed states appear. Fail-closed: when the manifest/skeleton chain
 * is unavailable the identity is {@link #unresolved(String)}.
 *
 * <p>Pure JVM, no Android.
 */
public final class PlayerIdentity {

  /** Committed player character key (never a npcpos refid). */
  public static final String PLAYER_KEY = "player";

  private final boolean resolved;
  private final List<IdleAnimResolver.Clip> clips;
  private final int boneCount;
  private final String skeletonPath;
  private final Map<AnimState, IdleAnimResolver.Clip> states;
  private final String reason;

  private PlayerIdentity(boolean resolved, List<IdleAnimResolver.Clip> clips,
      int boneCount, String skeletonPath, Map<AnimState, IdleAnimResolver.Clip> states,
      String reason) {
    this.resolved = resolved;
    this.clips = Collections.unmodifiableList(clips);
    this.boneCount = boneCount;
    this.skeletonPath = skeletonPath == null ? "" : skeletonPath;
    this.states = Collections.unmodifiableMap(states);
    this.reason = reason == null ? "" : reason;
  }

  /**
   * Resolves the player identity from the committed manifest and skeleton
   * readers. Any parse failure throws; callers treat that as unresolved.
   */
  public static PlayerIdentity resolve(Reader manifestReader, Reader skeletonReader)
      throws IOException {
    List<IdleAnimResolver.Clip> clips =
        CharacterMeshIndex.parseManifestClips(manifestReader);
    CharacterMeshIndex.Skeleton skel =
        CharacterMeshIndex.parseSkeleton(skeletonReader);
    Map<AnimState, IdleAnimResolver.Clip> states =
        AnimStateResolver.resolve(clips);
    return new PlayerIdentity(true, clips, skel.boneCount, skel.path, states, "");
  }

  /** Fail-closed identity: the manifest/skeleton chain is unavailable. */
  public static PlayerIdentity unresolved(String reason) {
    return new PlayerIdentity(false,
        Collections.<IdleAnimResolver.Clip>emptyList(),
        0, "", Collections.<AnimState, IdleAnimResolver.Clip>emptyMap(), reason);
  }

  public boolean isResolved() {
    return resolved;
  }

  public List<IdleAnimResolver.Clip> clips() {
    return clips;
  }

  public int clipCount() {
    return clips.size();
  }

  public int boneCount() {
    return boneCount;
  }

  public String skeletonPath() {
    return skeletonPath;
  }

  /** Resolved state -> real clip; only states present in the manifest appear. */
  public Map<AnimState, IdleAnimResolver.Clip> states() {
    return states;
  }

  public boolean hasState(AnimState state) {
    return states.containsKey(state);
  }

  public String reason() {
    return reason;
  }

  /** Immutable copy of the clip list (for callers that need to iterate). */
  public List<IdleAnimResolver.Clip> clipsCopy() {
    return new ArrayList<IdleAnimResolver.Clip>(clips);
  }
}
