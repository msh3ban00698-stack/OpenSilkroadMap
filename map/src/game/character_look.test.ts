/// <reference lib="deno.ns" />
import { assertEquals } from "jsr:@std/assert@1";
import {
  appearanceToLook,
  classShowsWeapon,
  PLAYER_PRESET,
  playerPreset,
} from "./character_look.ts";

Deno.test("every class and gender maps to the only playable mesh", () => {
  for (const classId of ["warrior", "rogue", "cleric", "warlock", "wizard", "bard"]) {
    for (const gender of ["male", "female"] as const) {
      assertEquals(playerPreset(classId, gender), PLAYER_PRESET);
    }
  }
});

Deno.test("melee classes keep the sword mesh visible", () => {
  assertEquals(classShowsWeapon("warrior"), true);
  assertEquals(classShowsWeapon("rogue"), true);
  assertEquals(classShowsWeapon("cleric"), false);
  assertEquals(classShowsWeapon("wizard"), false);
});

Deno.test("saved appearance fields map onto rig tints", () => {
  assertEquals(
    appearanceToLook({
      gender: "female",
      skinTone: "#c68642",
      hairColor: "#d4a437",
      outfitColor: "#1f4e79",
    }),
    { skin: "#c68642", hair: "#d4a437", outfit: "#1f4e79" },
  );
});
