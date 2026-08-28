/// <reference lib="deno.ns" />
import { assertEquals, assertExists } from "jsr:@std/assert@1";
import { getSkillFull, loadSkillsFull } from "./skill_data.ts";

Deno.test("Strike Smash resolves from bundled class skills without skills_full.json", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = () => Promise.resolve(new Response("missing", { status: 404 }));
  try {
    await loadSkillsFull();
    const full = getSkillFull("SKILL_CH_SWORD_SMASH_A_01");
    assertExists(full);
    assertEquals(full.code, "SKILL_CH_SWORD_SMASH_A_01");
    assertEquals(full.name, "Strike Smash");
  } finally {
    globalThis.fetch = orig;
  }
});
