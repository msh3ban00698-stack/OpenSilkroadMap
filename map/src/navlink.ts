import { PMTilesDB } from "./pmtiles_db";

export let navlinkData: any = null;

const NAVLINK_KEY = "navigation_linkage";
const NAVLINK_LOCAL_URL = "/assets/navigation_linkage.json.gz";
const NAVLINK_PROXY_URL = "/navlink-proxy";

async function fetchWithFallback(): Promise<Response> {
  const urls = [NAVLINK_LOCAL_URL, NAVLINK_PROXY_URL];
  for (const url of urls) {
    const res = await fetch(url);
    if (res.ok) return res;
  }
  throw new Error(`Failed to download from all sources`);
}

export async function getNavlinkData(): Promise<any | null> {
  if (navlinkData) return navlinkData;

  const cachedBlob = await PMTilesDB.get(NAVLINK_KEY);
  if (cachedBlob) {
    const text = await cachedBlob.text();
    navlinkData = JSON.parse(text);
    return navlinkData;
  }
  return null;
}

async function responseToText(response: Response): Promise<string> {
  const contentEncoding = response.headers.get("content-encoding");
  const contentType = response.headers.get("content-type") || "";

  if (contentEncoding?.includes("gzip")) {
    return await response.text();
  }

  if (contentType.includes("gzip")) {
    const buffer = await response.arrayBuffer();
    return decompressGzipBufferToText(buffer);
  }

  const text = await response.text();
  try {
    JSON.parse(text);
    return text;
  } catch {
    const buffer = await response.arrayBuffer();
    return decompressGzipBufferToText(buffer);
  }
}

export async function downloadAndCacheNavlink(
  onProgress: (percent: number, message: string) => void,
): Promise<any | null> {
  onProgress(0, "Downloading navigation linkage...");

  try {
    const response = await fetchWithFallback();

    onProgress(50, "Processing...");
    const text = await responseToText(response);
    navlinkData = JSON.parse(text);

    await PMTilesDB.set(NAVLINK_KEY, new Blob([text], { type: "application/json" }));

    onProgress(100, "Done");
    return navlinkData;
  } catch (e) {
    onProgress(-1, `Error: ${e}`);
    return null;
  }
}

export async function decompressGzipBufferToText(buffer: ArrayBuffer): Promise<string> {
  const cs = new CompressionStream("gzip");
  const writer = cs.writable.getWriter();
  writer.write(new Uint8Array(buffer));
  writer.close();

  const chunks: Uint8Array[] = [];
  const reader = cs.readable.getReader();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (value) chunks.push(value);
  }

  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return new TextDecoder().decode(result);
}

export function clearNavlinkCache(): void {
  navlinkData = null;
}
