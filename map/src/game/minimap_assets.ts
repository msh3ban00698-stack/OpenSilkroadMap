export const MINIMAP_ASSET_BASE_URL = "/assets/android/";

export interface MinimapRecord {
  sourcePath: string;
  outputPath: string;
  sourcePk2: string;
  phase: string;
  detectedFormat: string;
  width: number | null;
  height: number | null;
  logicalWidth: number | null;
  logicalHeight: number | null;
  outputSize: number | null;
  outputSha256: string;
  status: string;
  validationStatus: string;
}

export interface MinimapTargets {
  total: number | null;
  minimap: number | null;
  minimap_d: number | null;
}

export interface MinimapManifest {
  schema: string;
  archive: string;
  targets: MinimapTargets;
  records: MinimapRecord[];
}

export class MinimapError extends Error {}

export class MinimapManifestError extends MinimapError {}

export class MinimapResolutionError extends MinimapError {}

export class MinimapValidationError extends MinimapError {}

export class MinimapLoadError extends MinimapError {}

export function normalizeSourcePath(raw: string): string {
  let path = raw.trim();
  while (path.startsWith("/")) path = path.slice(1);
  return "/" + path;
}

export function kindOfSourcePath(sourcePath: string): "minimap" | "minimap_d" | "other" {
  const path = normalizeSourcePath(sourcePath).toLowerCase();
  if (path.startsWith("/minimap_d/")) return "minimap_d";
  if (path.startsWith("/minimap/")) return "minimap";
  return "other";
}

function requireString(record: Record<string, unknown>, field: string, index: number): string {
  const value = record[field];
  if (typeof value !== "string" || value.length === 0) {
    throw new MinimapManifestError(`manifest record ${index} is missing string field '${field}'`);
  }
  return value;
}

function optionalString(record: Record<string, unknown>, ...fields: string[]): string {
  for (const field of fields) {
    const value = record[field];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return "";
}

function optionalNumber(record: Record<string, unknown>, field: string, index: number): number | null {
  const value = record[field];
  if (value === undefined || value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new MinimapManifestError(`manifest record ${index} field '${field}' must be a finite number`);
  }
  return value;
}

function parseRecord(input: unknown, index: number): MinimapRecord {
  if (typeof input !== "object" || input === null) {
    throw new MinimapManifestError(`manifest record ${index} must be an object`);
  }
  const raw = input as Record<string, unknown>;
  return {
    sourcePath: normalizeSourcePath(requireString(raw, "source_path", index)),
    outputPath: requireString(raw, "output_path", index),
    sourcePk2: optionalString(raw, "source_pk2", "pk2"),
    phase: optionalString(raw, "phase"),
    detectedFormat: optionalString(raw, "detected_format"),
    width: optionalNumber(raw, "width", index),
    height: optionalNumber(raw, "height", index),
    logicalWidth: optionalNumber(raw, "logical_width", index),
    logicalHeight: optionalNumber(raw, "logical_height", index),
    outputSize: optionalNumber(raw, "output_size", index),
    outputSha256: optionalString(raw, "output_sha256"),
    status: optionalString(raw, "status", "result"),
    validationStatus: optionalString(raw, "validation_status"),
  };
}

export function parseMinimapManifest(input: unknown): MinimapManifest {
  if (typeof input !== "object" || input === null) {
    throw new MinimapManifestError("manifest root must be an object");
  }
  const root = input as Record<string, unknown>;
  if (!Array.isArray(root.records)) {
    throw new MinimapManifestError("manifest is missing 'records' array");
  }
  const targetsRaw = root.targets;
  const targets: MinimapTargets = { total: null, minimap: null, minimap_d: null };
  if (typeof targetsRaw === "object" && targetsRaw !== null) {
    const t = targetsRaw as Record<string, unknown>;
    for (const key of ["total", "minimap", "minimap_d"] as const) {
      if (typeof t[key] === "number" && Number.isFinite(t[key])) targets[key] = t[key] as number;
    }
  }
  return {
    schema: typeof root.schema === "string" ? root.schema : "",
    archive: typeof root.archive === "string" ? root.archive : "",
    targets,
    records: root.records.map(parseRecord),
  };
}

function phaseRank(phase: string): number {
  const parsed = parseInt(phase.replace(/^phase/, ""), 10);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function pickPreferred(records: MinimapRecord[]): MinimapRecord {
  const sorted = [...records].sort((a, b) => {
    const rankA = phaseRank(a.phase);
    const rankB = phaseRank(b.phase);
    if (rankA !== rankB) return rankB - rankA;
    return a.outputPath < b.outputPath ? -1 : a.outputPath > b.outputPath ? 1 : 0;
  });
  return sorted[0];
}

export interface ResolvedAsset {
  record: MinimapRecord;
  sourcePath: string;
  outputPath: string;
}

export class MinimapManifestResolver {
  readonly manifest: MinimapManifest;
  private readonly bySource = new Map<string, MinimapRecord[]>();
  private readonly preferred = new Map<string, MinimapRecord>();
  private readonly byOutput = new Map<string, MinimapRecord>();

  constructor(manifest: MinimapManifest) {
    this.manifest = manifest;
    for (const record of manifest.records) {
      const existing = this.bySource.get(record.sourcePath);
      if (existing) existing.push(record);
      else this.bySource.set(record.sourcePath, [record]);
      if (!this.byOutput.has(record.outputPath)) this.byOutput.set(record.outputPath, record);
    }
    for (const [source, records] of this.bySource) {
      this.preferred.set(source, pickPreferred(records));
    }
  }

  get recordCount(): number {
    return this.manifest.records.length;
  }

  get uniqueSourceCount(): number {
    return this.bySource.size;
  }

  get uniqueOutputCount(): number {
    return this.byOutput.size;
  }

  has(sourcePath: string): boolean {
    return this.preferred.has(normalizeSourcePath(sourcePath));
  }

  resolve(sourcePath: string): ResolvedAsset {
    const key = normalizeSourcePath(sourcePath);
    const record = this.preferred.get(key);
    if (!record) {
      throw new MinimapResolutionError(`no manifest record for minimap source '${key}'`);
    }
    return { record, sourcePath: key, outputPath: record.outputPath };
  }

  resolveAll(sourcePath: string): ResolvedAsset[] {
    const key = normalizeSourcePath(sourcePath);
    const records = this.bySource.get(key);
    if (!records) return [];
    return records.map((record) => ({ record, sourcePath: key, outputPath: record.outputPath }));
  }

  resolveByOutputPath(outputPath: string): ResolvedAsset | undefined {
    const record = this.byOutput.get(outputPath);
    if (!record) return undefined;
    return { record, sourcePath: record.sourcePath, outputPath: record.outputPath };
  }

  duplicateSources(): string[] {
    const duplicates: string[] = [];
    for (const [source, records] of this.bySource) {
      if (records.length > 1) duplicates.push(source);
    }
    return duplicates.sort();
  }

  minimapSourceCount(): number {
    let count = 0;
    for (const record of this.preferred.values()) {
      if (kindOfSourcePath(record.sourcePath) !== "other") count++;
    }
    return count;
  }
}

const PNG_SIGNATURE = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const MAX_PNG_BYTES = 4 * 1024 * 1024;
const MAX_CHUNK_LENGTH = 64 * 1024 * 1024;

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

export function crc32(bytes: Uint8Array, start = 0, end = bytes.length): number {
  let crc = 0xffffffff;
  for (let i = start; i < end; i++) {
    crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

export interface PngInfo {
  width: number;
  height: number;
  bitDepth: number;
  colorType: number;
}

function isChunkType(bytes: Uint8Array, offset: number, a: number, b: number, c: number, d: number): boolean {
  return (
    bytes[offset] === a &&
    bytes[offset + 1] === b &&
    bytes[offset + 2] === c &&
    bytes[offset + 3] === d
  );
}

export function validatePngBytes(bytes: Uint8Array): PngInfo {
  if (bytes.length < 8 + 25 || bytes.length > MAX_PNG_BYTES) {
    throw new MinimapValidationError(`not a PNG: unexpected byte length ${bytes.length}`);
  }
  for (let i = 0; i < 8; i++) {
    if (bytes[i] !== PNG_SIGNATURE[i]) throw new MinimapValidationError("not a PNG: signature mismatch");
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const ihdrLength = view.getUint32(8, false);
  if (ihdrLength !== 13 || !isChunkType(bytes, 12, 0x49, 0x48, 0x44, 0x52)) {
    throw new MinimapValidationError("not a PNG: first chunk is not a valid IHDR");
  }
  const width = view.getUint32(16, false);
  const height = view.getUint32(20, false);
  const bitDepth = bytes[24];
  const colorType = bytes[25];
  let position = 8;
  let seenIend = false;
  while (position < bytes.length) {
    if (position + 8 + 4 > bytes.length) throw new MinimapValidationError("corrupt PNG: truncated chunk header");
    const length = view.getUint32(position, false);
    if (length > MAX_CHUNK_LENGTH) throw new MinimapValidationError("corrupt PNG: chunk too large");
    const dataEnd = position + 8 + length;
    if (dataEnd + 4 > bytes.length) throw new MinimapValidationError("corrupt PNG: chunk out of bounds");
    const expectedCrc = crc32(bytes, position + 4, dataEnd);
    const actualCrc = view.getUint32(dataEnd, false);
    if (actualCrc !== expectedCrc) throw new MinimapValidationError("corrupt PNG: CRC mismatch");
    if (isChunkType(bytes, position + 4, 0x49, 0x45, 0x4e, 0x44)) {
      seenIend = true;
      position = dataEnd + 4;
      break;
    }
    position = dataEnd + 4;
  }
  if (!seenIend) throw new MinimapValidationError("corrupt PNG: missing IEND chunk");
  if (position !== bytes.length) throw new MinimapValidationError("corrupt PNG: trailing data after IEND");
  return { width, height, bitDepth, colorType };
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const input = bytes.slice();
  const digest = await crypto.subtle.digest("SHA-256", input);
  const out = new Uint8Array(digest);
  let hex = "";
  for (let i = 0; i < out.length; i++) hex += out[i].toString(16).padStart(2, "0");
  return hex;
}

export type AssetReader = (relativePath: string) => Promise<Uint8Array>;

export async function fetchAssetReader(relativePath: string): Promise<Uint8Array> {
  const url = MINIMAP_ASSET_BASE_URL + relativePath;
  const response = await fetch(url);
  if (!response.ok) {
    throw new MinimapLoadError(`asset fetch failed (${response.status}): ${url}`);
  }
  return new Uint8Array(await response.arrayBuffer());
}

export interface LoadedMinimap {
  sourcePath: string;
  outputPath: string;
  record: MinimapRecord;
  png: PngInfo;
  bytes: Uint8Array;
  sizeBytes: number;
  sha256: string;
}

export interface MinimapLoadOptions {
  reader?: AssetReader;
  verifySha256?: boolean;
}

export class MinimapAssetLoader {
  private readonly reader: AssetReader;
  private readonly verifySha256: boolean;

  constructor(
    readonly resolver: MinimapManifestResolver,
    options: MinimapLoadOptions = {},
  ) {
    this.reader = options.reader ?? fetchAssetReader;
    this.verifySha256 = options.verifySha256 ?? true;
  }

  async load(sourcePath: string): Promise<LoadedMinimap> {
    const resolved = this.resolver.resolve(sourcePath);
    const record = resolved.record;
    let bytes: Uint8Array;
    try {
      bytes = await this.reader(record.outputPath);
    } catch (error) {
      throw new MinimapLoadError(
        `minimap asset missing for '${record.sourcePath}' (${record.outputPath}): ${
          error instanceof Error ? error.message : String(error)
        }`,
      );
    }
    const png = validatePngBytes(bytes);
    if (record.width !== null && record.width !== png.width) {
      throw new MinimapValidationError(
        `dimension mismatch for '${record.sourcePath}': manifest width ${record.width} != PNG width ${png.width}`,
      );
    }
    if (record.height !== null && record.height !== png.height) {
      throw new MinimapValidationError(
        `dimension mismatch for '${record.sourcePath}': manifest height ${record.height} != PNG height ${png.height}`,
      );
    }
    if (record.logicalWidth !== null && (record.logicalWidth <= 0 || record.logicalWidth > png.width)) {
      throw new MinimapValidationError(
        `logical width out of range for '${record.sourcePath}': ${record.logicalWidth} not in (0, ${png.width}]`,
      );
    }
    if (record.logicalHeight !== null && (record.logicalHeight <= 0 || record.logicalHeight > png.height)) {
      throw new MinimapValidationError(
        `logical height out of range for '${record.sourcePath}': ${record.logicalHeight} not in (0, ${png.height}]`,
      );
    }
    const computedSha = await sha256Hex(bytes);
    if (this.verifySha256 && record.outputSha256.length > 0 && computedSha !== record.outputSha256) {
      throw new MinimapValidationError(
        `sha256 mismatch for '${record.sourcePath}': expected ${record.outputSha256}, got ${computedSha}`,
      );
    }
    return {
      sourcePath: record.sourcePath,
      outputPath: record.outputPath,
      record,
      png,
      bytes,
      sizeBytes: bytes.byteLength,
      sha256: computedSha,
    };
  }
}

export interface BoundedCacheConfig {
  maxBytes?: number;
  maxEntries?: number;
}

export interface CacheStats {
  entries: number;
  bytes: number;
  hits: number;
  misses: number;
  evictions: number;
  maxBytes: number;
  maxEntries: number;
}

export const DEFAULT_CACHE_MAX_BYTES = 8 * 1024 * 1024;
export const DEFAULT_CACHE_MAX_ENTRIES = 64;

export class BoundedMinimapCache {
  private readonly maxBytes: number;
  private readonly maxEntries: number;
  private readonly entries = new Map<string, LoadedMinimap>();
  private byteCount = 0;
  private hitCount = 0;
  private missCount = 0;
  private evictionCount = 0;

  constructor(config: BoundedCacheConfig = {}) {
    this.maxBytes = config.maxBytes ?? DEFAULT_CACHE_MAX_BYTES;
    this.maxEntries = config.maxEntries ?? DEFAULT_CACHE_MAX_ENTRIES;
  }

  get(sourcePath: string): LoadedMinimap | undefined {
    const hit = this.entries.get(sourcePath);
    if (!hit) {
      this.missCount++;
      return undefined;
    }
    this.hitCount++;
    this.entries.delete(sourcePath);
    this.entries.set(sourcePath, hit);
    return hit;
  }

  put(entry: LoadedMinimap): void {
    const existing = this.entries.get(entry.sourcePath);
    if (existing) {
      this.byteCount -= existing.sizeBytes;
      this.entries.delete(entry.sourcePath);
    }
    this.entries.set(entry.sourcePath, entry);
    this.byteCount += entry.sizeBytes;
    this.trim();
  }

  private trim(): void {
    while ((this.byteCount > this.maxBytes || this.entries.size > this.maxEntries) && this.entries.size > 0) {
      const oldest = this.entries.keys().next().value;
      if (oldest === undefined) return;
      const removed = this.entries.get(oldest);
      if (removed) this.byteCount -= removed.sizeBytes;
      this.entries.delete(oldest);
      this.evictionCount++;
    }
  }

  delete(sourcePath: string): boolean {
    const entry = this.entries.get(sourcePath);
    if (!entry) return false;
    this.byteCount -= entry.sizeBytes;
    this.entries.delete(sourcePath);
    return true;
  }

  clear(): void {
    this.entries.clear();
    this.byteCount = 0;
  }

  size(): number {
    return this.entries.size;
  }

  stats(): CacheStats {
    return {
      entries: this.entries.size,
      bytes: this.byteCount,
      hits: this.hitCount,
      misses: this.missCount,
      evictions: this.evictionCount,
      maxBytes: this.maxBytes,
      maxEntries: this.maxEntries,
    };
  }
}

export class CachedMinimapLoader {
  constructor(
    readonly loader: MinimapAssetLoader,
    readonly cache: BoundedMinimapCache,
  ) {}

  async load(sourcePath: string): Promise<LoadedMinimap> {
    const cached = this.cache.get(sourcePath);
    if (cached) return cached;
    const loaded = await this.loader.load(sourcePath);
    this.cache.put(loaded);
    return loaded;
  }

  release(sourcePath: string): boolean {
    return this.cache.delete(sourcePath);
  }

  releaseAll(): void {
    this.cache.clear();
  }

  stats(): CacheStats {
    return this.cache.stats();
  }
}
