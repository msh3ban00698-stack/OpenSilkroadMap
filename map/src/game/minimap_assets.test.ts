/// <reference lib="deno.ns" />
import { assert, assertEquals, assertRejects, assertThrows } from "jsr:@std/assert@1";
import {
  BoundedMinimapCache,
  CachedMinimapLoader,
  MinimapAssetLoader,
  MinimapLoadError,
  MinimapManifestResolver,
  MinimapResolutionError,
  MinimapValidationError,
  normalizeSourcePath,
  parseMinimapManifest,
  validatePngBytes,
  type AssetReader,
  type MinimapManifest,
  type MinimapRecord,
} from "./minimap_assets.ts";

const ASSETS_DIR = new URL("../../../android-assets/", import.meta.url);

function fsReader(relativePath: string): Promise<Uint8Array> {
  return Deno.readFile(new URL(relativePath, ASSETS_DIR));
}

async function loadRealManifest(): Promise<MinimapManifest> {
  const bytes = await fsReader("manifest.json");
  return parseMinimapManifest(JSON.parse(new TextDecoder().decode(bytes)));
}

async function loadRealResolver(): Promise<MinimapManifestResolver> {
  return new MinimapManifestResolver(await loadRealManifest());
}

function mkRecord(partial: Partial<MinimapRecord> & { sourcePath: string; outputPath: string }): MinimapRecord {
  return {
    phase: "phase6",
    sourcePk2: "Media.pk2",
    detectedFormat: "DDJ+DDS(DXT1)",
    width: 256,
    height: 256,
    logicalWidth: null,
    logicalHeight: null,
    outputSize: 0,
    outputSha256: "",
    status: "ok",
    validationStatus: "PASS",
    ...partial,
  };
}

function distinctRealMinimapSources(manifest: MinimapManifest, count: number): string[] {
  const sources: string[] = [];
  for (const record of manifest.records) {
    if (
      record.phase === "phase6" &&
      (record.sourcePath.startsWith("/minimap/") || record.sourcePath.startsWith("/minimap_d/"))
    ) {
      sources.push(record.sourcePath);
      if (sources.length === count) break;
    }
  }
  return sources;
}

Deno.test("manifest parses the committed android-assets manifest with exact counts", async () => {
  const manifest = await loadRealManifest();
  assertEquals(manifest.records.length, 7755);
  assertEquals(manifest.targets.total, 7737);
  assertEquals(manifest.targets.minimap, 5523);
  assertEquals(manifest.targets.minimap_d, 2214);
  assert(manifest.schema.length > 0);
  assert(manifest.archive.length > 0);
});

Deno.test("minimap record lookup resolves known minimap and minimap_d sources", async () => {
  const resolver = await loadRealResolver();
  const plain = resolver.resolve("/minimap/100x100.ddj");
  assertEquals(plain.record.outputPath, "maps/minimap/100x100.png");
  assertEquals(plain.record.logicalWidth, 100);
  assertEquals(plain.record.logicalHeight, 100);
  const dungeon = resolver.resolve("/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj");
  assert(dungeon.outputPath.includes("minimap_d"));
  assertEquals(dungeon.record.logicalWidth, 127);
  assertEquals(dungeon.record.logicalHeight, 127);
});

Deno.test("path resolution returns exact manifest output paths both ways", async () => {
  const manifest = await loadRealManifest();
  const resolver = new MinimapManifestResolver(manifest);
  const phase6 = manifest.records.find(
    (r) => r.sourcePath === "/minimap/100x100.ddj" && r.phase === "phase6",
  );
  assert(phase6);
  const resolved = resolver.resolve("/minimap/100x100.ddj");
  assertEquals(resolved.outputPath, phase6.outputPath);
  const reverse = resolver.resolveByOutputPath(phase6.outputPath);
  assert(reverse);
  assertEquals(reverse.sourcePath, "/minimap/100x100.ddj");
});

Deno.test("missing minimap source fails explicitly", async () => {
  const resolver = await loadRealResolver();
  assertEquals(resolver.has("/minimap/does_not_exist.ddj"), false);
  assertThrows(() => resolver.resolve("/minimap/does_not_exist.ddj"), MinimapResolutionError);
  assertEquals(resolver.resolveAll("/minimap/does_not_exist.ddj").length, 0);
});

Deno.test("missing output file fails explicitly in the loader", async () => {
  const resolver = await loadRealResolver();
  const reader: AssetReader = async () => {
    throw new Error("ENOENT simulated");
  };
  const loader = new MinimapAssetLoader(resolver, { reader });
  await assertRejects(() => loader.load("/minimap/100x100.ddj"), MinimapLoadError);
});

Deno.test("corrupt PNG bytes fail validation", async () => {
  const resolver = await loadRealResolver();
  const real = await fsReader("maps/minimap/100x100.png");
  const corrupted = new Uint8Array(real);
  corrupted[45] ^= 0xff;
  const reader: AssetReader = async () => corrupted;
  const loader = new MinimapAssetLoader(resolver, { reader, verifySha256: false });
  await assertRejects(() => loader.load("/minimap/100x100.ddj"), MinimapValidationError);
});

Deno.test("non-PNG bytes fail validation", async () => {
  const resolver = await loadRealResolver();
  const reader: AssetReader = async () => new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  const loader = new MinimapAssetLoader(resolver, { reader });
  await assertRejects(() => loader.load("/minimap/100x100.ddj"), MinimapValidationError);
});

Deno.test("loaded PNG dimensions match manifest metadata", async () => {
  const resolver = await loadRealResolver();
  const loader = new MinimapAssetLoader(resolver, { reader: fsReader });
  for (const source of ["/minimap/100x100.ddj", "/minimap/27x53.ddj", "/minimap/237x124.ddj"]) {
    const loaded = await loader.load(source);
    assertEquals(loaded.png.width, loaded.record.width);
    assertEquals(loaded.png.height, loaded.record.height);
    assertEquals(loaded.sizeBytes, loaded.record.outputSize);
  }
});

Deno.test("dimension mismatch between manifest and PNG is rejected", async () => {
  const manifest = await loadRealManifest();
  const tampered = manifest.records.map((r) =>
    r.sourcePath === "/minimap/100x100.ddj" && r.phase === "phase6" ? { ...r, width: 999, height: 999 } : r
  );
  const resolver = new MinimapManifestResolver({ ...manifest, records: tampered });
  const loader = new MinimapAssetLoader(resolver, { reader: fsReader, verifySha256: false });
  await assertRejects(() => loader.load("/minimap/100x100.ddj"), MinimapValidationError);
});

Deno.test("real assets are valid PNGs with supported color types", async () => {
  const resolver = await loadRealResolver();
  const loader = new MinimapAssetLoader(resolver, { reader: fsReader });
  for (const source of [
    "/minimap/100x100.ddj",
    "/minimap/104x84.ddj",
    "/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
  ]) {
    const loaded = await loader.load(source);
    assert([2, 6].includes(loaded.png.colorType));
    assertEquals(loaded.png.bitDepth, 8);
  }
});

Deno.test("tampered PNG signature fails format validation", () => {
  const real = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13, 0x49, 0x48, 0x44, 0x52];
  const bytes = new Uint8Array([...real, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  bytes[0] = 0x00;
  assertThrows(() => validatePngBytes(bytes), MinimapValidationError);
});

Deno.test("duplicate source records resolve deterministically to the later phase", async () => {
  const resolver = await loadRealResolver();
  const duplicates = resolver.duplicateSources();
  assertEquals(duplicates.length, 2);
  for (const source of duplicates) {
    const all = resolver.resolveAll(source);
    assertEquals(all.length, 2);
    const phases = all.map((a) => a.record.phase).sort();
    assertEquals(phases, ["phase5", "phase6"]);
    const preferred = resolver.resolve(source);
    assertEquals(preferred.record.phase, "phase6");
  }
});

Deno.test("resolution keys by exact normalized path, not basename", () => {
  const manifest: MinimapManifest = {
    schema: "test",
    archive: "Media.pk2",
    targets: { total: 2, minimap: 1, minimap_d: 1 },
    records: [
      mkRecord({ sourcePath: "/minimap_d/x/same.ddj", outputPath: "maps/minimap_d/x/same.png" }),
      mkRecord({ sourcePath: "/minimap/same.ddj", outputPath: "maps/minimap/same.png" }),
    ],
  };
  const resolver = new MinimapManifestResolver(manifest);
  assertEquals(resolver.resolve("/minimap/same.ddj").outputPath, "maps/minimap/same.png");
  assertEquals(resolver.resolve("/minimap_d/x/same.ddj").outputPath, "maps/minimap_d/x/same.png");
  assertEquals(normalizeSourcePath("minimap/100x100.ddj"), "/minimap/100x100.ddj");
});

Deno.test("bounded cache stays within configured limits", async () => {
  const manifest = await loadRealManifest();
  const resolver = new MinimapManifestResolver(manifest);
  const loader = new MinimapAssetLoader(resolver, { reader: fsReader });
  const cache = new BoundedMinimapCache({ maxBytes: 4 * 1024 * 1024, maxEntries: 16 });
  const cached = new CachedMinimapLoader(loader, cache);
  const sources = distinctRealMinimapSources(manifest, 40);
  for (const source of sources) {
    await cached.load(source);
  }
  let stats = cached.stats();
  assert(stats.bytes <= 4 * 1024 * 1024);
  assert(stats.entries <= 16);
  assert(stats.evictions > 0);
  assert(stats.misses === 40);
  for (const source of sources.slice(-10)) {
    await cached.load(source);
  }
  stats = cached.stats();
  assert(stats.hits >= 10);
  assert(stats.bytes <= 4 * 1024 * 1024);
  assert(stats.entries <= 16);
});

Deno.test("cache releases resources on demand and on bulk clear", async () => {
  const manifest = await loadRealManifest();
  const resolver = new MinimapManifestResolver(manifest);
  const loader = new MinimapAssetLoader(resolver, { reader: fsReader });
  const cache = new BoundedMinimapCache({ maxBytes: 1024 * 1024, maxEntries: 16 });
  const cached = new CachedMinimapLoader(loader, cache);
  const sourceA = "/minimap/100x100.ddj";
  const sourceB = "/minimap/27x53.ddj";
  await cached.load(sourceA);
  await cached.load(sourceB);
  assertEquals(cache.size(), 2);
  assert(cached.release(sourceA));
  assertEquals(cache.size(), 1);
  assert(cache.delete(sourceB));
  assertEquals(cache.size(), 0);
  await cached.load(sourceA);
  await cached.load(sourceB);
  cached.releaseAll();
  assertEquals(cache.size(), 0);
  assertEquals(cached.stats().bytes, 0);
});

Deno.test("controlled real-asset proof loads small/medium/large with matching sha256", async () => {
  const manifest = await loadRealManifest();
  const resolver = new MinimapManifestResolver(manifest);
  const loader = new MinimapAssetLoader(resolver, { reader: fsReader, verifySha256: true });
  const cases: Array<[string, number, number]> = [
    ["/minimap/27x53.ddj", 27, 53],
    ["/minimap/100x100.ddj", 100, 100],
    ["/minimap/105x101.ddj", 105, 101],
    ["/minimap/237x124.ddj", 237, 124],
    ["/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj", 127, 127],
    ["/minimap_d/jupiter/jupiter_a_237x124.ddj", 237, 124],
  ];
  for (const [source, logicalWidth, logicalHeight] of cases) {
    const loaded = await loader.load(source);
    assertEquals(loaded.record.logicalWidth, logicalWidth);
    assertEquals(loaded.record.logicalHeight, logicalHeight);
    assertEquals(loaded.sha256, loaded.record.outputSha256);
    assertEquals(loaded.png.width, 256);
    assertEquals(loaded.png.height, 256);
    assertEquals(loaded.sizeBytes, loaded.record.outputSize);
    assert(loaded.record.sourcePk2.length > 0);
  }
});

Deno.test("manifest resolution is deterministic across resolver instances", async () => {
  const manifest = await loadRealManifest();
  const first = new MinimapManifestResolver(manifest);
  const second = new MinimapManifestResolver(JSON.parse(JSON.stringify(manifest)) as MinimapManifest);
  for (const source of [
    "/minimap/100x100.ddj",
    "/minimap/27x53.ddj",
    "/minimap/237x124.ddj",
    "/minimap_d/Arabia/RN_ARABIA_FIELD_02_BOSS_127x127.ddj",
  ]) {
    const a = first.resolve(source);
    const b = second.resolve(source);
    assertEquals(a.outputPath, b.outputPath);
    assertEquals(a.record.phase, b.record.phase);
    assertEquals(a.record.outputSha256, b.record.outputSha256);
  }
});

Deno.test("repeated loads produce identical bytes", async () => {
  const resolver = await loadRealResolver();
  const loader = new MinimapAssetLoader(resolver, { reader: fsReader, verifySha256: true });
  const first = await loader.load("/minimap/100x100.ddj");
  const second = await loader.load("/minimap/100x100.ddj");
  assertEquals(first.sha256, second.sha256);
  assertEquals(first.bytes.byteLength, second.bytes.byteLength);
  assertEquals(first.outputPath, second.outputPath);
});

Deno.test("sequential loads stay memory-bounded with no directory preload", async () => {
  const manifest = await loadRealManifest();
  const resolver = new MinimapManifestResolver(manifest);
  let readCount = 0;
  const readPaths = new Set<string>();
  const reader: AssetReader = async (relativePath) => {
    readCount++;
    readPaths.add(relativePath);
    return fsReader(relativePath);
  };
  const loader = new MinimapAssetLoader(resolver, { reader });
  const cache = new BoundedMinimapCache({ maxBytes: 256 * 1024, maxEntries: 8 });
  const cached = new CachedMinimapLoader(loader, cache);
  const sources = distinctRealMinimapSources(manifest, 30);
  for (const source of sources) {
    await cached.load(source);
  }
  assertEquals(readCount, 30);
  assertEquals(readPaths.size, 30);
  const stats = cached.stats();
  assert(stats.bytes <= 256 * 1024);
  assert(stats.entries <= 8);
  assert(stats.evictions > 0);
});
