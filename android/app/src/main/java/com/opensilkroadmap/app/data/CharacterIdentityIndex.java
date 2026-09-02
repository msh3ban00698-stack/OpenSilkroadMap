package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Spawn-scoped character identity over the committed
 * {@code character_identity.tsv}, extracted from live Media.pk2
 * {@code characterdata_*.txt} using only the three Phase 29 proven anchors:
 *
 * <pre>
 * col1 refid       joins npcpos.tsv col0 (1180/1180 distinct) and
 *                  shopdata.tsv col5 merchant_refid
 * col2 code        CHAR_CH_* / NPC_* / MOB_* / STRUCTURE_* / COS_* code name
 * col52 model_path backslash .bsr path (Phase 28 verified)
 * </pre>
 *
 * <p>The committed table covers every distinct {@code npcpos.tsv} character
 * refid (1180) plus the one spawn-less merchant RefCharID (STORE_AM_SPECIAL /
 * 7568). Unproven characterdata columns (speed, stats, language keys) are not
 * present. Fail-closed: unknown refids return {@code null}. No Android
 * dependencies; pure JVM.
 */
public final class CharacterIdentityIndex {

  /** One proven character identity (refid + code + model path). */
  public static final class Identity {
    public final int refId;
    public final String code;
    public final String modelPath;

    public Identity(int refId, String code, String modelPath) {
      this.refId = refId;
      this.code = code;
      this.modelPath = modelPath;
    }
  }

  private final Map<Integer, Identity> byRefId;

  public CharacterIdentityIndex(TsvTable table) {
    Map<Integer, Identity> map = new LinkedHashMap<Integer, Identity>();
    for (String[] row : table.rows()) {
      int refId = TsvTable.intAt(row, 0);
      String code = TsvTable.strAt(row, 1);
      String model = TsvTable.strAt(row, 2);
      if (refId <= 0 || code.isEmpty()) {
        continue;
      }
      if (!map.containsKey(Integer.valueOf(refId))) {
        map.put(Integer.valueOf(refId), new Identity(refId, code, model));
      }
    }
    this.byRefId = Collections.unmodifiableMap(map);
  }

  public static CharacterIdentityIndex loadDefault() throws IOException {
    return new CharacterIdentityIndex(TsvTable.loadDefault("character_identity.tsv"));
  }

  public int size() {
    return byRefId.size();
  }

  /** Identity for a character refid, or {@code null} (fail-closed). */
  public Identity resolve(int refId) {
    return byRefId.get(Integer.valueOf(refId));
  }

  /** Code name for a character refid, or {@code null} (fail-closed). */
  public String code(int refId) {
    Identity id = resolve(refId);
    return id == null ? null : id.code;
  }

  /** Model path for a character refid, or {@code null} (fail-closed). */
  public String modelPath(int refId) {
    Identity id = resolve(refId);
    return id == null ? null : id.modelPath;
  }
}
