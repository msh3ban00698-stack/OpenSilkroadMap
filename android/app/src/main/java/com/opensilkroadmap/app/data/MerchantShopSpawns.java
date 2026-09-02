package com.opensilkroadmap.app.data;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Concrete runtime merchant shop placement index composed from the committed
 * verified merchant binding ({@link ShopMerchantIndex}) and the committed
 * verified world spawn table ({@link NpcSpawnIndex}). Every NPC-run store whose
 * merchant RefCharID has exactly one world spawn in {@code npcpos.tsv} becomes
 * one placed entry carrying the store's code and the spawn's proven sector +
 * local geometry. Strictly fail-closed: a store whose merchant RefCharID has no
 * world spawn (STORE_AM_SPECIAL / 7568) is never given invented coordinates and
 * is counted separately as spawnless.
 *
 * <p>When a {@link CharacterIdentityIndex} is attached, each placed merchant
 * also carries the proven characterdata code ({@code NPC_*}) and .bsr model
 * path for its RefCharID. Unknown refids fail closed with a null identity;
 * identity is never invented. STORE_AM_SPECIAL / 7568 still resolves in the
 * identity index (NPC_AM_SPECIAL) but is not placed.
 *
 * <p>Proven coverage on the committed tables (Phase 30): 52 NPC-run stores,
 * 51/52 merchant RefCharIDs have exactly one world spawn each; only
 * STORE_AM_SPECIAL (7568) has none. Store → merchant RefCharID → store tab →
 * item stock binding is provenance from {@link ShopMerchantIndex}; geometry is
 * provenance from {@link NpcSpawnIndex}; character code / model path is
 * provenance from {@link CharacterIdentityIndex}.
 *
 * <p>No Android dependencies; pure JVM.
 */
public final class MerchantShopSpawns {

  /** One placed merchant store with its verified world spawn geometry. */
  public static final class Entry {
    public final ShopMerchantIndex.Merchant merchant;
    public final NpcSpawnIndex.Spawn spawn;
    public final CharacterIdentityIndex.Identity identity;

    public Entry(ShopMerchantIndex.Merchant merchant, NpcSpawnIndex.Spawn spawn) {
      this(merchant, spawn, null);
    }

    public Entry(ShopMerchantIndex.Merchant merchant, NpcSpawnIndex.Spawn spawn,
                 CharacterIdentityIndex.Identity identity) {
      this.merchant = merchant;
      this.spawn = spawn;
      this.identity = identity;
    }

    /** The merchant RefCharID the store is bound to. */
    public int merchantRefId() {
      return merchant.merchantRefId;
    }

    /** The client store code (e.g. {@code STORE_CH_SMITH}). */
    public String storeCode() {
      return merchant.storeCode;
    }

    /** The server store numeric id resolved via {@code refshop.tsv}. */
    public int serverStoreId() {
      return merchant.storeId;
    }

    /** Sector x of the merchant's spawn. */
    public int sectorX() {
      return spawn.sectorX;
    }

    /** Sector y of the merchant's spawn. */
    public int sectorY() {
      return spawn.sectorY;
    }

    /** Sector-local x of the merchant's spawn. */
    public float localX() {
      return spawn.localX;
    }

    /** Sector-local z of the merchant's spawn. */
    public float localZ() {
      return spawn.localZ;
    }

    /** World x relative to a reference sector via the proven formula. */
    public float worldX(int refSx) {
      return spawn.worldX(refSx);
    }

    /** World z relative to a reference sector via the proven formula. */
    public float worldZ(int refSy) {
      return spawn.worldZ(refSy);
    }

    /** Proven characterdata code ({@code NPC_*}), or null (fail-closed). */
    public String characterCode() {
      return identity == null ? null : identity.code;
    }

    /** Proven characterdata .bsr model path, or null (fail-closed). */
    public String modelPath() {
      return identity == null ? null : identity.modelPath;
    }
  }

  private final List<Entry> entries;
  private final int merchantCount;
  private final int spawnlessCount;
  private final int identifiedCount;

  /**
   * Composes the shop index and the spawn index. A store is placed only when
   * its merchant RefCharID has exactly one world spawn (verified 51/52);
   * merchants with zero (or, unexpectedly, more than one) world spawn fail
   * closed and are not given coordinates.
   */
  public MerchantShopSpawns(ShopMerchantIndex shops, NpcSpawnIndex npc) {
    this(shops, npc, null);
  }

  /**
   * Composes shop + spawn + optional character identity. Identity is attached
   * only when the index resolves the merchant RefCharID; unknown refids stay
   * null and are never invented.
   */
  public MerchantShopSpawns(ShopMerchantIndex shops, NpcSpawnIndex npc,
                            CharacterIdentityIndex identity) {
    Map<Integer, List<NpcSpawnIndex.Spawn>> byRef =
        new HashMap<Integer, List<NpcSpawnIndex.Spawn>>();
    for (int i = 0; i < npc.worldCount(); i++) {
      NpcSpawnIndex.Spawn s = npc.worldSpawn(i);
      List<NpcSpawnIndex.Spawn> list = byRef.get(s.characterRefId);
      if (list == null) {
        list = new ArrayList<NpcSpawnIndex.Spawn>();
        byRef.put(s.characterRefId, list);
      }
      list.add(s);
    }
    List<Entry> out = new ArrayList<Entry>();
    int spawnless = 0;
    int identified = 0;
    for (ShopMerchantIndex.Merchant m : shops.merchants()) {
      List<NpcSpawnIndex.Spawn> list = byRef.get(m.merchantRefId);
      if (list == null || list.size() != 1) {
        spawnless++;
        continue;
      }
      CharacterIdentityIndex.Identity id =
          identity == null ? null : identity.resolve(m.merchantRefId);
      if (id != null) {
        identified++;
      }
      out.add(new Entry(m, list.get(0), id));
    }
    this.entries = Collections.unmodifiableList(out);
    this.merchantCount = shops.merchantCount();
    this.spawnlessCount = spawnless;
    this.identifiedCount = identified;
  }

  public static MerchantShopSpawns loadDefault() throws IOException {
    return new MerchantShopSpawns(
        ShopMerchantIndex.loadDefault(), NpcSpawnIndex.loadDefault(),
        CharacterIdentityIndex.loadDefault());
  }

  /** Placed merchant stores in the ShopMerchantIndex (shopdata) file order. */
  public List<Entry> entries() {
    return entries;
  }

  /** Number of placed merchant stores (each with exactly one world spawn). */
  public int placedCount() {
    return entries.size();
  }

  /** Total NPC-run stores in the merchant binding. */
  public int merchantCount() {
    return merchantCount;
  }

  /** NPC-run stores with no (single) world spawn; never given coordinates. */
  public int spawnlessCount() {
    return spawnlessCount;
  }

  /** Placed merchants whose RefCharID resolved in the identity index. */
  public int identifiedCount() {
    return identifiedCount;
  }

  /**
   * Placed-merchant stock rows whose PACKAGE_ code resolved to an ITEM_*
   * identity (codes/icons only). STORE_AM_SPECIAL / 7568 is not placed and
   * has empty stock, so this equals the NPC-store total (1233).
   */
  public int stockIdentifiedCount() {
    int n = 0;
    for (Entry e : entries) {
      n += e.merchant.identifiedStockCount();
    }
    return n;
  }

  /** Placed store at the given index (0 .. placedCount()-1). */
  public Entry placed(int i) {
    return entries.get(i);
  }

  /**
   * Placed store whose merchant spawn sector lies inside the given inclusive
   * sector window (same semantics as {@code NpcSpawnIndex.inWindow}).
   */
  public List<Entry> inWindow(int sx0, int sx1, int sy0, int sy1) {
    List<Entry> out = new ArrayList<Entry>();
    for (Entry e : entries) {
      if (e.sectorX() >= sx0 && e.sectorX() <= sx1
          && e.sectorY() >= sy0 && e.sectorY() <= sy1) {
        out.add(e);
      }
    }
    return out;
  }
}
