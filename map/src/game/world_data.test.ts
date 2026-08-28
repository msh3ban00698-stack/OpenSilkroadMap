/// <reference lib="deno.ns" />
import { assert, assertEquals } from "jsr:@std/assert@1";
import { REGIONS } from "./regions.ts";
import { loadTeleportPads, loadTownGates } from "./teleport_data.ts";
import { loadWorldNpcs } from "./world_npcs.ts";

const ROOT = new URL("../../public", import.meta.url);

function mockAssetsFetch(): typeof fetch {
  return async (input) => {
    const url = String(input);
    const path = url.replace(/^https?:\/\/[^/]+/, "").replace(/^\//, "");
    const file = new URL(path, ROOT.href + "/");
    try {
      const data = await Deno.readFile(file);
      return new Response(data, { status: 200, headers: { "content-type": "application/json" } });
    } catch {
      return new Response("missing", { status: 404 });
    }
  };
}

Deno.test("Constantinople loads original NPC markers", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = mockAssetsFetch();
  try {
    const npcs = await loadWorldNpcs(REGIONS[0]);
    assert(npcs.length > 0, "expected NPCs from bundled npcs.json");
    assert(npcs.some((n) => n.name.includes("Soldier") || n.name.includes("Guide")));
  } finally {
    globalThis.fetch = orig;
  }
});

Deno.test("town dimensional gates load from bundled teleports.json", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = mockAssetsFetch();
  try {
    const pads = await loadTeleportPads(REGIONS[0]);
    assert(pads.length > 0, "expected Constantinople dimensional gate");
    assertEquals(
      pads.some((p) => p.name.includes("Dimensional") || p.code.includes("STORE_EU_GATE")),
      true,
    );
    const towns = await loadTownGates();
    assert(towns.length >= 7, `expected town gates, got ${towns.length}`);
  } finally {
    globalThis.fetch = orig;
  }
});
