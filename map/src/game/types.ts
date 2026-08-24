export interface Appearance {
  gender: "male" | "female";
  skinTone: string;
  hairColor: string;
  outfitColor: string;
}

export interface GameCharacter {
  id: string;
  name: string;
  classId: string;
  level: number;
  appearance: Appearance;
  createdAt: number;
  lastPlayedAt: number;
  region: number;
  position: { x: number; y: number; z: number };
}

export type GameState =
  | "intro"
  | "select"
  | "create"
  | "loading"
  | "in-world"
  | "paused"
  | "map";
