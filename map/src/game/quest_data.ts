import type { MobCamp } from "./mobs_data.js";

export interface QuestContent {
  sn: string;
  text: string;
  state: number;
}

export interface QuestReward {
  code: string;
  count: number;
}

export interface QuestDef {
  code: string;
  giver: string;
  title: string;
  contents: QuestContent[];
  rewards: QuestReward[];
}

export type ObjectiveKind = "hunt" | "collect" | "talk";

export interface QuestObjective {
  kind: ObjectiveKind;
  count: number;
  label: string;
}

let questsPromise: Promise<QuestDef[]> | null = null;

export function loadQuests(): Promise<QuestDef[]> {
  if (!questsPromise) {
    questsPromise = fetch("/assets/gamedata/quests.json").then((r) => r.json() as Promise<QuestDef[]>);
  }
  return questsPromise;
}

export function parseObjective(text: string): QuestObjective | null {
  const t = text.trim();
  if (!t) return null;
  const numMatch = t.match(/(\d+)/);
  const count = numMatch ? parseInt(numMatch[1], 10) : 1;
  if (/\b(hunt|capture|kill|eliminate|defeat)\b/i.test(t)) {
    return { kind: "hunt", count, label: t };
  }
  if (/\b(collect|gather|obtain)\b/i.test(t)) {
    return { kind: "collect", count, label: t };
  }
  if (/\b(deliver|speak|talk|bring|meet|visit)\b/i.test(t)) {
    return { kind: "talk", count: 1, label: t };
  }
  return { kind: "talk", count: 1, label: t };
}

export function questObjective(q: QuestDef): QuestObjective | null {
  const first = q.contents.find((c) => c.text);
  if (!first) return null;
  return parseObjective(first.text);
}

export function resolveHuntCamp(
  giverPos: { x: number; z: number },
  camps: MobCamp[],
  charLevel = 1,
): { code: string; name: string; cx: number; cz: number; radius: number } | null {
  const scored = camps.map((c) => ({
    camp: c,
    dist: Math.hypot(c.cx - giverPos.x, c.cz - giverPos.z),
    overLevel: c.mob.level > charLevel + 4,
  }));
  scored.sort((a, b) => {
    if (a.overLevel !== b.overLevel) return a.overLevel ? 1 : -1;
    return a.dist - b.dist;
  });
  const best = scored[0]?.camp;
  if (!best) return null;
  return {
    code: best.mob.code,
    name: best.mob.name,
    cx: best.cx,
    cz: best.cz,
    radius: best.radius,
  };
}

export function talkTargetName(label: string): string {
  const m = label.match(/\b(?:to|with)\s+((?:[A-Z][\w']*)(?:\s+[A-Z][\w']*)?)/) || null;
  return m ? m[1] : "";
}
