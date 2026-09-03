package com.opensilkroadmap.app.game;

import android.app.Activity;
import android.os.Bundle;
import com.opensilkroadmap.app.data.CharacterIdentityIndex;
import com.opensilkroadmap.app.data.ItemPackageIndex;
import com.opensilkroadmap.app.data.MerchantShopSpawns;
import com.opensilkroadmap.app.data.NpcSpawnIndex;
import com.opensilkroadmap.app.data.OptionalTeleportIndex;
import com.opensilkroadmap.app.data.OptionalTeleportTable;
import com.opensilkroadmap.app.data.ShopDataTable;
import com.opensilkroadmap.app.data.ShopMerchantIndex;
import com.opensilkroadmap.app.data.ShopTabDataTable;
import com.opensilkroadmap.app.data.SpawnZoneIndex;
import com.opensilkroadmap.app.data.TeleportBuildingTable;
import com.opensilkroadmap.app.data.TeleportDataTable;
import com.opensilkroadmap.app.data.TeleportDestinationMap;
import com.opensilkroadmap.app.data.TeleportGateIndex;
import com.opensilkroadmap.app.data.TsvTable;
import com.opensilkroadmap.app.data.WorldDataIndex;
import com.opensilkroadmap.app.data.WorldGameTable;
import com.opensilkroadmap.app.data.WorldMapInstanceIndex;
import com.opensilkroadmap.app.data.WorldMapInstanceTable;
import com.opensilkroadmap.app.data.WorldmapLocalinfoIndex;
import com.opensilkroadmap.app.world.CharacterCatalog;
import com.opensilkroadmap.app.world.CharacterEntity;
import com.opensilkroadmap.app.world.CharacterMeshIndex;
import com.opensilkroadmap.app.world.MeshObjectIndex;
import com.opensilkroadmap.app.world.NativeWorldRenderer;
import com.opensilkroadmap.app.world.RegionResolver;
import com.opensilkroadmap.app.world.RegionZoneCatalog;
import com.opensilkroadmap.app.world.TerrainHeightGrid;
import com.opensilkroadmap.app.world.WorldRegion;
import com.opensilkroadmap.app.world.WorldTerrainIndex;
import com.opensilkroadmap.app.world.WorldTerrainSet;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Phase 15 native world runtime host. Loads the verified world region windows
 * ({@code world_regions.tsv}), the verified terrain inventory
 * ({@code world_index.tsv}), and the verified NPC placement table
 * ({@code npcpos.tsv}); selects the first region whose reference sector has a
 * committed real {@code .hg}; then loads EVERY committed sector in that region
 * window into a {@link WorldTerrainSet} and renders the real multi-sector
 * terrain plus verified NPC placements through {@link NativeWorldRenderer}.
 *
 * <p>The renderer is a DIAGNOSTIC TERRAIN/PLACEMENT renderer (verified
 * heightfield wireframe + real npcpos markers), not a production 3D renderer:
 * no models, materials, normals, or textures are invented. Missing terrain
 * fails closed; no other region is substituted.
 *
 * <p>Phase 24 adds the PLAYER foundation on top: the player identity
 * ({@link PlayerIdentity}) resolves from the committed {@code "player"} manifest
 * + skeleton chain; the player spawn stays UNKNOWN (no verified start table in
 * source) and fails closed — no invented position; a {@link PlayerController}
 * binds the native joystick input to the player entity's proven IDLE/WALK/RUN
 * clips; the shared {@link InputController} is drained by the renderer (pan /
 * zoom) and the controller (move). The camera follows the player only once a
 * verified spawn has placed it.
 *
 * <p>This native activity is now the app launcher (see
 * {@code AndroidManifest.xml}); the legacy {@code MainActivity} WebView entry has
 * been retired to a redirect. The runtime is driven by a fixed-timestep
 * {@link GameLoop} heartbeat fed by a monotonic {@link GameClock}; no WebView or
 * Capacitor runtime is used.
 */
public final class GameActivity extends Activity {

  private static final String WORLD_REGIONS_ASSET = "game/world/world_regions.tsv";
  private static final String WORLD_INDEX_ASSET = "game/world/world_index.tsv";
  private static final String REGION_CODE_ASSET = "game/textdata/regioncode.tsv";
  private static final String REGION_ZONE_ASSET = "game/world/region_zone.tsv";
  private static final String NPC_POS_ASSET = "game/textdata/npcpos.tsv";
  private static final String SHOP_DATA_ASSET = "game/textdata/shopdata.tsv";
  private static final String SHOP_TAB_DATA_ASSET = "game/textdata/shoptabdata.tsv";
  private static final String REFSHOP_ASSET = "game/textdata/refshop.tsv";
  private static final String REFSHOP_GOODS_ASSET = "game/textdata/refshopgoods.tsv";
  private static final String CHARACTER_IDENTITY_ASSET = "game/textdata/character_identity.tsv";
  private static final String ITEM_PACKAGE_IDENTITY_ASSET =
      "game/textdata/item_package_identity.tsv";
  private static final String TELEPORT_DATA_ASSET = "game/textdata/teleportdata.tsv";
  private static final String TELEPORT_BUILDING_ASSET = "game/textdata/teleportbuilding.tsv";
  private static final String WORLDMAP_INSTANCE_ASSET = "game/textdata/worldmap_instanceinfo.tsv";
  private static final String WORLD_DATA_ASSET = "game/textdata/gameworlddata.tsv";
  private static final String OPTIONAL_TELEPORT_ASSET = "game/textdata/refoptionalteleport.tsv";
  private static final String WORLDMAP_LOCALINFO_ASSET = "game/textdata/worldmap_localinfo.tsv";
  private static final String CHARACTER_INDEX_ASSET = "game/world/characters/index.tsv";
  private static final String PLAYER_MANIFEST_ASSET = "game/world/characters/player/manifest.json";
  private static final String PLAYER_SKELETON_ASSET =
      "game/world/characters/shared/skel/prim_skel_char_china_chinaman_skel.json";

  private NativeWorldRenderer world;
  private WorldTerrainSet terrain;
  private NpcSpawnIndex npc;
  private SpawnZoneIndex spawnZones;
  private TeleportGateIndex teleportGates;
  private OptionalTeleportIndex optionalTeleports;
  private TeleportDestinationMap teleportDestinations;
  private MerchantShopSpawns merchantShops;
  private WorldMapInstanceIndex instances;
  private WorldDataIndex worldData;
  private MeshObjectIndex meshObjects;
  private CharacterCatalog characterCatalog;
  private Map<String, CharacterMeshIndex> characterModels =
      new HashMap<String, CharacterMeshIndex>();
  private PlayerController playerController;

  private final GameClock clock = new GameClock();
  private final GameLoop loop = new GameLoop();
  private boolean running;

  private final Runnable frame = new Runnable() {
    @Override
    public void run() {
      if (!running || world == null) {
        return;
      }
      double dt = clock.tick(System.nanoTime());
      loop.advance(dt);
      world.advanceAnimations(dt);
      if (playerController != null) {
        playerController.update(dt);
        boolean placed = playerController.placed();
        world.setPlayer(playerController.entity(),
            playerController.state().heading(), placed);
        double[] target = playerController.cameraTarget();
        if (target != null) {
          world.setCamera((float) target[0], (float) target[1],
              world.pixelsPerUnit());
        }
      }
      world.postInvalidateOnAnimation();
      world.postOnAnimation(this);
    }
  };

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    WorldTerrainIndex index = loadTerrainIndex();
    List<WorldRegion> regions = loadWorldRegions();
    npc = loadNpcSpawns();
    spawnZones = loadSpawnZones(npc);
    merchantShops = loadMerchantShops(npc);
    teleportGates = loadTeleportGates();
    optionalTeleports = loadOptionalTeleports();
    teleportDestinations = loadTeleportDestinations(teleportGates, optionalTeleports);
    instances = loadInstances();
    worldData = loadWorldData();

    WorldRegion region = selectRegion(index, regions);
    terrain = loadRegionTerrain(index, region);
    if (region != null) {
      meshObjects = MeshObjectIndex.load(getAssets(), region.refSx, region.refSy);
    }
    characterCatalog = loadCharacterCatalog();
    characterModels = loadCharacterModels(region, npc);

    world = new NativeWorldRenderer(this);
    if (terrain != null) {
      world.setWorld(terrain);
      world.setNpcSpawns(npc);
      world.setTeleportDestinations(teleportDestinations);
      world.setMerchantShops(merchantShops);
      world.setMeshObjects(meshObjects);
      world.setCharacters(characterCatalog, characterModels);
      world.setCamera(terrain.width() / 2f, terrain.height() / 2f, 0.5f);
    }
    wirePlayer();
    setContentView(world);
    start();
  }

  @Override
  protected void onResume() {
    super.onResume();
    start();
  }

  @Override
  protected void onPause() {
    stop();
    super.onPause();
  }

  private void start() {
    if (running || world == null) {
      return;
    }
    running = true;
    world.postOnAnimation(frame);
  }

  private void stop() {
    running = false;
  }

  private WorldRegion selectRegion(WorldTerrainIndex index, List<WorldRegion> regions) {
    if (index != null && regions != null) {
      for (WorldRegion r : regions) {
        if (index.find(r.refSx, r.refSy) != null) {
          return r;
        }
      }
    }
    return null;
  }

  private WorldTerrainSet loadRegionTerrain(WorldTerrainIndex index, WorldRegion region) {
    if (index == null || region == null) {
      return null;
    }
    List<WorldTerrainSet.Sector> sectors = new ArrayList<WorldTerrainSet.Sector>();
    for (WorldTerrainIndex.Entry e : index.entries()) {
      if (region.containsSector(e.sx, e.sy)) {
        TerrainHeightGrid grid = loadGrid(e.sx, e.sy);
        if (grid != null) {
          sectors.add(WorldTerrainSet.sector(e.sx, e.sy, region.refSx, region.refSy, grid));
        }
      }
    }
    return sectors.isEmpty() ? null : new WorldTerrainSet(sectors);
  }

  private TerrainHeightGrid loadGrid(int sx, int sy) {
    try {
      return TerrainHeightGrid.load(
          getAssets().open(WorldTerrainIndex.hgAssetPath(sx, sy)));
    } catch (IOException e) {
      return null;
    }
  }

  /** Package-private for the instrumented test (same package). */
  NativeWorldRenderer worldRenderer() {
    return world;
  }

  /** Package-private for the instrumented test (same package). */
  MeshObjectIndex meshObjects() {
    return meshObjects;
  }

  /** Package-private for the instrumented test (same package). */
  CharacterCatalog characterCatalog() {
    return characterCatalog;
  }

  /** Package-private for the instrumented test (same package). */
  PlayerController playerController() {
    return playerController;
  }

  /** Package-private for the instrumented test (same package). */
  NpcSpawnIndex npcSpawns() {
    return npc;
  }

  /** Package-private for the instrumented test (same package). */
  SpawnZoneIndex spawnZones() {
    return spawnZones;
  }

  /** Package-private for the instrumented test (same package). */
  TeleportGateIndex teleportGates() {
    return teleportGates;
  }

  /** Package-private for the instrumented test (same package). */
  OptionalTeleportIndex optionalTeleports() {
    return optionalTeleports;
  }

  /** Package-private for the instrumented test (same package). */
  TeleportDestinationMap teleportDestinations() {
    return teleportDestinations;
  }

  /** Package-private for the instrumented test (same package). */
  MerchantShopSpawns merchantShops() {
    return merchantShops;
  }

  /** Package-private for the instrumented test (same package). */
  WorldMapInstanceIndex instances() {
    return instances;
  }

  /** Package-private for the instrumented test (same package). */
  WorldDataIndex worldData() {
    return worldData;
  }

  /**
   * Wires the Phase 24 player foundation. The spawn is UNKNOWN by evidence (no
   * verified start table in the supplied source/data) so the controller fails
   * closed: the player entity is attached but invisible until a verified spawn
   * is placed.
   */
  private void wirePlayer() {
    PlayerIdentity identity = loadPlayerIdentity();
    CharacterMeshIndex playerModel =
        CharacterMeshIndex.load(getAssets(), CharacterCatalog.PLAYER_KEY);
    PlayerState playerState =
        new PlayerState(CharacterCatalog.PLAYER_KEY, "Player");
    playerController = new PlayerController(
        world.input(), playerState,
        playerModel == null ? null : new CharacterEntity(playerModel),
        identity,
        PlayerSpawn.unknown(
            "no verified spawn table in supplied source/data; npcpos is NPC-only"),
        PlayerMovementConfig.unknownSpeed());
    world.setPlayer(playerController.entity(), 0f, false);
  }

  private PlayerIdentity loadPlayerIdentity() {
    try {
      return PlayerIdentity.resolve(
          new InputStreamReader(
              getAssets().open(PLAYER_MANIFEST_ASSET), StandardCharsets.UTF_8),
          new InputStreamReader(
              getAssets().open(PLAYER_SKELETON_ASSET), StandardCharsets.UTF_8));
    } catch (IOException e) {
      return PlayerIdentity.unresolved("player manifest/skeleton unavailable");
    }
  }

  /** Package-private for the instrumented test (same package). */
  Map<String, CharacterMeshIndex> characterModels() {
    return characterModels;
  }

  private WorldTerrainIndex loadTerrainIndex() {
    try {
      return WorldTerrainIndex.parse(
          new InputStreamReader(getAssets().open(WORLD_INDEX_ASSET), StandardCharsets.UTF_8));
    } catch (IOException e) {
      return null;
    }
  }

  private List<WorldRegion> loadWorldRegions() {
    try {
      return WorldRegion.load(() -> getAssets().open(WORLD_REGIONS_ASSET));
    } catch (IOException e) {
      return null;
    }
  }

  private NpcSpawnIndex loadNpcSpawns() {
    try {
      TsvTable table = TsvTable.parse("npcpos.tsv",
          new InputStreamReader(getAssets().open(NPC_POS_ASSET), StandardCharsets.UTF_8));
      CharacterIdentityIndex identity = null;
      try {
        identity = new CharacterIdentityIndex(TsvTable.parse(
            "character_identity.tsv",
            new InputStreamReader(getAssets().open(CHARACTER_IDENTITY_ASSET),
                StandardCharsets.UTF_8)));
      } catch (IOException ignored) {
        identity = null;
      }
      return new NpcSpawnIndex(table, identity);
    } catch (IOException e) {
      return null;
    }
  }

  private SpawnZoneIndex loadSpawnZones(NpcSpawnIndex npc) {
    if (npc == null) {
      return null;
    }
    try {
      TsvTable regionCode = TsvTable.parse("regioncode.tsv",
          new InputStreamReader(getAssets().open(REGION_CODE_ASSET), StandardCharsets.UTF_8));
      RegionZoneCatalog server =
          RegionZoneCatalog.load(() -> getAssets().open(REGION_ZONE_ASSET));
      return new SpawnZoneIndex(npc, RegionResolver.load(regionCode, server));
    } catch (IOException e) {
      return null;
    }
  }

  private MerchantShopSpawns loadMerchantShops(NpcSpawnIndex npc) {
    if (npc == null) {
      return null;
    }
    try {
      ShopDataTable shop = new ShopDataTable(TsvTable.parse(
          "shopdata.tsv",
          new InputStreamReader(getAssets().open(SHOP_DATA_ASSET), StandardCharsets.UTF_8)));
      ShopTabDataTable tabs = new ShopTabDataTable(TsvTable.parse(
          "shoptabdata.tsv",
          new InputStreamReader(getAssets().open(SHOP_TAB_DATA_ASSET), StandardCharsets.UTF_8)));
      TsvTable refshop = TsvTable.parse(
          "refshop.tsv",
          new InputStreamReader(getAssets().open(REFSHOP_ASSET), StandardCharsets.UTF_8));
      TsvTable refshopGoods = TsvTable.parse(
          "refshopgoods.tsv",
          new InputStreamReader(getAssets().open(REFSHOP_GOODS_ASSET), StandardCharsets.UTF_8));
      ItemPackageIndex packages = null;
      try {
        packages = new ItemPackageIndex(TsvTable.parse(
            "item_package_identity.tsv",
            new InputStreamReader(getAssets().open(ITEM_PACKAGE_IDENTITY_ASSET),
                StandardCharsets.UTF_8)));
      } catch (IOException ignored) {
        packages = null;
      }
      ShopMerchantIndex shops = ShopMerchantIndex.build(
          shop, tabs, refshop, refshopGoods, packages);
      CharacterIdentityIndex identity = null;
      try {
        identity = new CharacterIdentityIndex(TsvTable.parse(
            "character_identity.tsv",
            new InputStreamReader(getAssets().open(CHARACTER_IDENTITY_ASSET),
                StandardCharsets.UTF_8)));
      } catch (IOException ignored) {
        identity = null;
      }
      return new MerchantShopSpawns(shops, npc, identity);
    } catch (IOException e) {
      return null;
    }
  }

  private TeleportDestinationMap loadTeleportDestinations(
      TeleportGateIndex gates, OptionalTeleportIndex destinations) {
    if (gates == null || destinations == null) {
      return null;
    }
    WorldmapLocalinfoIndex localinfo = null;
    try {
      localinfo = new WorldmapLocalinfoIndex(TsvTable.parse(
          "worldmap_localinfo.tsv",
          new InputStreamReader(getAssets().open(WORLDMAP_LOCALINFO_ASSET),
              StandardCharsets.UTF_8)));
    } catch (IOException ignored) {
      localinfo = null;
    }
    return new TeleportDestinationMap(gates, destinations, localinfo);
  }

  private TeleportGateIndex loadTeleportGates() {
    try {
      TeleportDataTable teleport = new TeleportDataTable(TsvTable.parse(
          "teleportdata.tsv",
          new InputStreamReader(getAssets().open(TELEPORT_DATA_ASSET), StandardCharsets.UTF_8)));
      TeleportBuildingTable buildings = new TeleportBuildingTable(TsvTable.parse(
          "teleportbuilding.tsv",
          new InputStreamReader(getAssets().open(TELEPORT_BUILDING_ASSET), StandardCharsets.UTF_8)));
      TsvTable regionCode = TsvTable.parse("regioncode.tsv",
          new InputStreamReader(getAssets().open(REGION_CODE_ASSET), StandardCharsets.UTF_8));
      RegionZoneCatalog server =
          RegionZoneCatalog.load(() -> getAssets().open(REGION_ZONE_ASSET));
      return new TeleportGateIndex(teleport, RegionResolver.load(regionCode, server), buildings);
    } catch (IOException e) {
      return null;
    }
  }

  private WorldMapInstanceIndex loadInstances() {
    try {
      WorldMapInstanceTable table = new WorldMapInstanceTable(TsvTable.parse(
          "worldmap_instanceinfo.tsv",
          new InputStreamReader(getAssets().open(WORLDMAP_INSTANCE_ASSET), StandardCharsets.UTF_8)));
      RegionCatalog regions = RegionCatalog.parse(new InputStreamReader(
          getAssets().open("game/regions.tsv"), StandardCharsets.UTF_8));
      return new WorldMapInstanceIndex(table, regions);
    } catch (IOException e) {
      return null;
    }
  }

  private WorldDataIndex loadWorldData() {
    try {
      return new WorldDataIndex(new WorldGameTable(TsvTable.parse(
          "gameworlddata.tsv",
          new InputStreamReader(getAssets().open(WORLD_DATA_ASSET), StandardCharsets.UTF_8))));
    } catch (IOException e) {
      return null;
    }
  }

  private OptionalTeleportIndex loadOptionalTeleports() {
    try {
      OptionalTeleportTable table = new OptionalTeleportTable(TsvTable.parse(
          "refoptionalteleport.tsv",
          new InputStreamReader(getAssets().open(OPTIONAL_TELEPORT_ASSET), StandardCharsets.UTF_8)));
      TsvTable regionCode = TsvTable.parse("regioncode.tsv",
          new InputStreamReader(getAssets().open(REGION_CODE_ASSET), StandardCharsets.UTF_8));
      RegionZoneCatalog server =
          RegionZoneCatalog.load(() -> getAssets().open(REGION_ZONE_ASSET));
      return new OptionalTeleportIndex(table, RegionResolver.load(regionCode, server));
    } catch (IOException e) {
      return null;
    }
  }

  private CharacterCatalog loadCharacterCatalog() {
    try {
      return CharacterCatalog.parse(new InputStreamReader(
          getAssets().open(CHARACTER_INDEX_ASSET), StandardCharsets.UTF_8));
    } catch (IOException e) {
      return null;
    }
  }

  private Map<String, CharacterMeshIndex> loadCharacterModels(
      WorldRegion region, NpcSpawnIndex npc) {
    Map<String, CharacterMeshIndex> models = new HashMap<String, CharacterMeshIndex>();
    if (characterCatalog == null || npc == null || region == null) {
      return models;
    }
    for (NpcSpawnIndex.Spawn sp :
        npc.inWindow(region.sx0, region.sx1, region.sy0, region.sy1)) {
      String key = characterCatalog.keyFor(sp.characterRefId);
      if (key == null || models.containsKey(key)) {
        continue;
      }
      CharacterMeshIndex m = CharacterMeshIndex.load(getAssets(), key);
      if (m != null) {
        models.put(key, m);
      }
    }
    return models;
  }
}
