import type { Appearance } from "./types";
import type { CharacterRig } from "./character_rig";

export const PLAYER_PRESET = "chinaman_fighter";
export const PLAYER_SCALE = 0.15;

export const SKIN_PARTS = [
  "man_pelvis",
  "man_torso_lower",
  "man_torso_upper",
  "man_arm_upper",
  "man_arm_lower",
  "man_thigh",
  "man_calf",
  "chinaman_fighter_face",
];

export const HAIR_PARTS = ["chinaman_fighter_hair"];

export const OUTFIT_PARTS = [
  "clothes_01_aa",
  "clothes_01_ba",
  "clothes_01_fa",
  "clothes_01_ha",
  "clothes_01_la",
  "clothes_01_sa",
];

export interface LookAppearance {
  skin?: string | null;
  hair?: string | null;
  outfit?: string | null;
}

export function playerPreset(classId: string, gender: "male" | "female"): string {
  void classId;
  void gender;
  return PLAYER_PRESET;
}

export function classShowsWeapon(classId: string): boolean {
  return classId === "warrior" || classId === "rogue";
}

export function appearanceToLook(appearance: Appearance): LookAppearance {
  return {
    skin: appearance.skinTone,
    hair: appearance.hairColor,
    outfit: appearance.outfitColor,
  };
}

export function applyCharacterAppearance(rig: CharacterRig, look: LookAppearance): void {
  const tint = (ids: string[], color: string | null | undefined): void => {
    for (const id of ids) rig.setPartTint(id, color ?? null);
  };
  tint(SKIN_PARTS, look.skin);
  tint(HAIR_PARTS, look.hair);
  tint(OUTFIT_PARTS, look.outfit);
}
