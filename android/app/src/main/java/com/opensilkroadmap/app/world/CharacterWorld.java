package com.opensilkroadmap.app.world;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Data-driven multi-entity character world (pure JVM, Android-free).
 *
 * <p>Holds one {@link CharacterMeshIndex} per model key and many independent
 * {@link CharacterEntity} instances. Each entity owns its own animator clock,
 * so any number of NPCs of the same model animate independently. The world
 * clock {@link #update(double)} advances every entity's clock by the same
 * {@code dt}; entities can also be stepped individually (e.g. a player owned
 * by its own controller) without desyncing the rest.
 *
 * <p>Spawning is fail-closed: an unknown model key or a duplicate entity id
 * returns {@code false} and changes nothing. Positions are world coordinates;
 * their unit is UNKNOWN from the source archives (only placement math is
 * structural) — callers own the SRO-to-world scale factor.
 */
public final class CharacterWorld {

  /** An immutable spawn record: unique id, model key, and live entity. */
  public static final class Entry {
    public final String entityId;
    public final String modelKey;
    public final CharacterEntity entity;

    Entry(String entityId, String modelKey, CharacterEntity entity) {
      this.entityId = entityId;
      this.modelKey = modelKey;
      this.entity = entity;
    }
  }

  private final Map<String, CharacterMeshIndex> models;
  private final Map<String, Entry> entities = new HashMap<String, Entry>();
  private final List<Entry> ordered = new ArrayList<Entry>();

  public CharacterWorld(Map<String, CharacterMeshIndex> models) {
    this.models = new HashMap<String, CharacterMeshIndex>(models);
  }

  public boolean hasModel(String modelKey) {
    return models.containsKey(modelKey);
  }

  public CharacterMeshIndex model(String modelKey) {
    return models.get(modelKey);
  }

  /**
   * Spawns a new entity. Returns {@code false} (no-op) when the model key is
   * unknown or the entity id is already taken; otherwise registers a fresh
   * independent instance and returns {@code true}.
   */
  public boolean spawn(String entityId, String modelKey, float x, float z) {
    CharacterMeshIndex index = models.get(modelKey);
    if (index == null || entities.containsKey(entityId)) {
      return false;
    }
    CharacterEntity entity = new CharacterEntity(index);
    entity.setPosition(x, z);
    Entry entry = new Entry(entityId, modelKey, entity);
    entities.put(entityId, entry);
    ordered.add(entry);
    return true;
  }

  public Entry entry(String entityId) {
    return entities.get(entityId);
  }

  public int size() {
    return ordered.size();
  }

  /** Read-only snapshot of spawn order. */
  public List<Entry> entries() {
    return Collections.unmodifiableList(ordered);
  }

  /** Advances every entity's independent animation clock by {@code dt}. */
  public void update(double dtSeconds) {
    for (Entry entry : ordered) {
      entry.entity.update(dtSeconds);
    }
  }
}
