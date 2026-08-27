import type { GameCharacter } from "./types.js";
import { loadQuests, questObjective, resolveHuntCamp, talkTargetName, type QuestDef } from "./quest_data.js";
import type { MobCamp } from "./mobs_data.js";
import { loadItemInfo } from "./world_npcs.js";
import { registerAuthenticItem, authenticItemDef } from "./items.js";

export interface QuestPanelOpts {
  root: HTMLElement;
  character: GameCharacter;
  onMutate: () => void;
  log: (msg: string) => void;
  npcCode: string;
  npcName: string;
  getNpcPos: (npcCode: string) => { x: number; z: number } | null;
  camps: MobCamp[];
}

const campCache = new Map<string, string>();
const questByCode = new Map<string, QuestDef>();
loadQuests()
  .then((defs) => {
    for (const d of defs) questByCode.set(d.code, d);
  })
  .catch(() => {});

function ensureQuestFields(char: GameCharacter): {
  questLog: NonNullable<GameCharacter["questLog"]>;
  questsDone: NonNullable<GameCharacter["questsDone"]>;
} {
  if (!char.questLog) char.questLog = [];
  if (!char.questsDone) char.questsDone = [];
  return { questLog: char.questLog, questsDone: char.questsDone };
}

export async function questsForNpc(
  char: GameCharacter,
  npcCode: string,
): Promise<{ available: QuestDef[]; completable: QuestDef[]; active: QuestDef[] }> {
  const all = await loadQuests().catch(() => []);
  const { questLog, questsDone } = ensureQuestFields(char);
  const done = new Set(questsDone);
  const activeMap = new Map(questLog.map((p) => [p.code, p.progress]));
  const available: QuestDef[] = [];
  const completable: QuestDef[] = [];
  const active: QuestDef[] = [];
  for (const q of all) {
    if (q.giver !== npcCode || done.has(q.code)) continue;
    const prog = activeMap.get(q.code);
    if (prog === undefined) {
      available.push(q);
      continue;
    }
    const obj = questObjective(q);
    const need = obj ? obj.count : 1;
    if (prog >= need) completable.push(q);
    else active.push(q);
  }
  return { available, completable, active };
}

export function resolvedCampFor(
  q: QuestDef,
  getNpcPos: (code: string) => { x: number; z: number } | null,
  charLevel = 1,
  camps: MobCamp[] = [],
): { code: string; name: string } | null {
  const cached = campCache.get(q.code);
  if (cached) return JSON.parse(cached);
  const obj = questObjective(q);
  if (!obj || obj.kind === "talk") return null;
  const pos = getNpcPos(q.giver);
  if (!pos) return null;
  const camp = resolveHuntCamp(pos, camps, charLevel);
  if (!camp) return null;
  const res = { code: camp.code, name: camp.name };
  campCache.set(q.code, JSON.stringify(res));
  return res;
}

export function onMobKilled(character: GameCharacter, mobCode: string, log: (msg: string) => void): boolean {
  const { questLog } = ensureQuestFields(character);
  let changed = false;
  for (const entry of questLog) {
    const def = questByCode.get(entry.code);
    if (!def) continue;
    const obj = questObjective(def);
    if (!obj || obj.kind === "talk") continue;
    const camp = campCache.get(entry.code);
    if (!camp || JSON.parse(camp).code !== mobCode) continue;
    if (entry.progress >= obj.count) continue;
    entry.progress += 1;
    changed = true;
    log(`${def.title}: ${obj.label} (${entry.progress}/${obj.count})`);
  }
  return changed;
}

export function onNpcTalked(character: GameCharacter, npcName: string, log: (msg: string) => void): boolean {
  const { questLog } = ensureQuestFields(character);
  let changed = false;
  for (const entry of questLog) {
    const def = questByCode.get(entry.code);
    if (!def || entry.progress >= 1) continue;
    const obj = questObjective(def);
    if (!obj || obj.kind !== "talk") continue;
    const target = talkTargetName(obj.label);
    if (!target || !npcName.includes(target)) continue;
    entry.progress = 1;
    changed = true;
    log(`${def.title}: ${obj.label} — done. Return to the quest giver.`);
  }
  return changed;
}

const QUEST_GOLD_FALLBACK = 500;

export function updateQuestTracker(el: HTMLElement | null, char: GameCharacter): void {
  if (!el) return;
  const { questLog } = ensureQuestFields(char);
  if (questLog.length === 0 || questByCode.size === 0) {
    el.style.display = "none";
    return;
  }
  const rows: string[] = [];
  for (const entry of questLog.slice(0, 3)) {
    const def = questByCode.get(entry.code);
    if (!def) continue;
    const obj = questObjective(def);
    const need = obj ? obj.count : 1;
    const mark =
      entry.progress >= need
        ? "return to giver"
        : obj && obj.kind === "talk"
          ? "visit target"
          : `${entry.progress}/${need}`;
    rows.push(`<div class="hud-tracker-row"><span>${def.title}</span><b>${mark}</b></div>`);
  }
  if (rows.length === 0) {
    el.style.display = "none";
    return;
  }
  el.style.display = "block";
  el.innerHTML = `<div class="hud-tracker-title">Quests</div>${rows.join("")}`;
}

async function completeQuest(opts: QuestPanelOpts, def: QuestDef): Promise<void> {
  const { character, onMutate, log } = opts;
  const { questLog, questsDone } = ensureQuestFields(character);
  character.questLog = questLog.filter((p) => p.code !== def.code);
  questsDone.push(def.code);
  let granted = 0;
  const infos = await loadItemInfo(def.rewards.map((r) => r.code));
  for (const r of def.rewards) {
    const info = infos[r.code];
    if (!info) continue;
    registerAuthenticItem(r.code, authenticItemDef(r.code, info.name, info.price, info.iconUrl, info.level));
    const existing = character.inventory.find((it) => it.id === r.code);
    if (existing) existing.count += r.count;
    else character.inventory.push({ id: r.code, count: r.count });
    granted += r.count;
  }
  if (granted === 0 && def.rewards.length > 0) {
    character.gold += QUEST_GOLD_FALLBACK;
    log(`Quest complete: ${def.title}. Reward converted to ${QUEST_GOLD_FALLBACK} gold.`);
  } else {
    log(`Quest complete: ${def.title}.`);
  }
  onMutate();
}

async function acceptQuest(
  opts: Pick<QuestPanelOpts, "character" | "onMutate" | "log" | "getNpcPos" | "camps">,
  def: QuestDef,
): Promise<void> {
  const { questLog } = ensureQuestFields(opts.character);
  questLog.push({ code: def.code, progress: 0 });
  const obj = questObjective(def);
  const camp =
    obj && obj.kind !== "talk" ? resolvedCampFor(def, opts.getNpcPos, opts.character.level, opts.camps) : null;
  if (camp && obj && obj.kind !== "talk") {
    opts.log(`Quest accepted: ${def.title} — ${obj.label}; hunt ${camp.name}.`);
  } else {
    opts.log(`Quest accepted: ${def.title}.`);
  }
  opts.onMutate();
}

export async function hasQuestActions(char: GameCharacter, npcCode: string): Promise<boolean> {
  ensureQuestFields(char);
  const { available, completable, active } = await questsForNpc(char, npcCode);
  return available.length > 0 || completable.length > 0 || active.length > 0;
}

export async function openQuestPanel(root: HTMLElement, opts: QuestPanelOpts): Promise<void> {
  root.querySelectorAll(":scope > .shop-panel").forEach((el) => el.remove());
  const sheet = document.createElement("div");
  sheet.className = "shop-panel";
  const backdrop = document.createElement("div");
  backdrop.className = "shop-backdrop";
  const panel = document.createElement("div");
  panel.className = "sro-window shop-sheet";
  panel.innerHTML = `
    <div class="sro-window-title">${opts.npcName} — Quests</div>
    <div class="quest-list"></div>
    <button class="sro-btn sro-btn-secondary quest-close-btn" type="button">Close</button>
  `;
  sheet.appendChild(backdrop);
  sheet.appendChild(panel);
  root.appendChild(sheet);

  const close = (): void => sheet.remove();
  backdrop.addEventListener("click", close);
  panel.querySelector(".quest-close-btn")!.addEventListener("click", close);

  const list = panel.querySelector<HTMLElement>(".quest-list")!;
  const { available, completable, active } = await questsForNpc(opts.character, opts.npcCode);
  const allDefs = [...completable, ...available, ...active];
  const itemInfos = await loadItemInfo(allDefs.flatMap((q) => q.rewards.map((r) => r.code)));

  const renderQuest = (def: QuestDef, mode: "accept" | "complete" | "active"): void => {
    const card = document.createElement("div");
    card.className = "quest-card";
    const obj = questObjective(def);
    const camp =
      obj && obj.kind !== "talk" ? resolvedCampFor(def, opts.getNpcPos, opts.character.level, opts.camps) : null;
    const progEntry = opts.character.questLog?.find((p) => p.code === def.code);

    const rewardText = def.rewards
      .map((r) => {
        const nm = itemInfos[r.code]?.name || "Mystery Reward";
        return `${nm}${r.count > 1 ? ` x${r.count}` : ""}`;
      })
      .join(", ");
    card.innerHTML = `
      <div class="quest-title">${def.title}</div>
      <div class="quest-content"></div>
      <div class="quest-objective"></div>
      ${rewardText ? `<div class="quest-rewards">Rewards: ${rewardText}</div>` : ""}
      <div class="quest-actions"></div>
    `;
    card.querySelector<HTMLElement>(".quest-content")!.textContent = def.contents[0]?.text || "";
    const objEl = card.querySelector<HTMLElement>(".quest-objective")!;
    if (mode === "active" && progEntry && obj) {
      objEl.textContent = camp
        ? `${obj.label} — hunt ${camp.name} (${Math.min(progEntry.progress, obj.count)}/${obj.count})`
        : `${obj.label}${progEntry.progress >= 1 ? " — done, return to giver" : ""}`;
    } else if (obj) {
      objEl.textContent = camp ? `${obj.label} — hunt ${camp.name}` : obj.label;
    }
    const actions = card.querySelector<HTMLElement>(".quest-actions")!;
    if (mode === "complete" || mode === "accept") {
      const btn = document.createElement("button");
      btn.className = "sro-btn sro-btn-primary";
      btn.type = "button";
      btn.textContent = mode === "complete" ? "Complete" : "Accept";
      btn.addEventListener("click", () => {
        const done = mode === "complete" ? completeQuest(opts, def) : acceptQuest(opts, def);
        void done.then(close);
      });
      actions.appendChild(btn);
    } else {
      const tag = document.createElement("span");
      tag.className = "quest-inprogress";
      tag.textContent = progEntry && obj && progEntry.progress >= obj.count ? "Return to giver" : "In progress";
      actions.appendChild(tag);
    }
    list.appendChild(card);
  };

  for (const q of completable) renderQuest(q, "complete");
  for (const q of available) renderQuest(q, "accept");
  for (const q of active) renderQuest(q, "active");

  if (list.children.length === 0) {
    const empty = document.createElement("div");
    empty.className = "quest-empty";
    empty.textContent = "No quests available right now.";
    list.appendChild(empty);
  }
}
