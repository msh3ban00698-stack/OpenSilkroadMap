# Phase H: Verified Game Data (Levels, Items, Skills, Masteries)

Status: COMPLETE — the placeholder gameplay data from earlier phases is now
backed by verified data extracted from the external package's
`server_dep/silkroad/textdata` files. The game loads real level curves, real
item entries, real class skills and real mastery groupings at runtime, and the
HUD surfaces them: an EXP bar (with the verified level-1 curve), real class
skill names/codes/masteries on the skill bar, a level-up flow with a banner,
and real starter gear names.

Everything that is still gameplay tuning (attack/defense numbers, HP/MP growth,
EXP rewards, potion heal rates, colors/icons) is explicitly marked as such in
code comments and in this document. Nothing is silently claimed to be
data-derived when it is not.

## Goal

```
Placeholder items/skills/exp  ->  real data loaded from the extracted textdata
  -> scripts/generate_phase_h_data.py extracts small JSON from the package
  -> src/game/data_loader.ts imports it (bundled, no runtime fetch)
  -> items.ts / HUD use real names, codes, levelReq, mastery, exp curve
  -> new gameplay: EXP bar, level-up (banner + stat growth), real skill slots
  -> warlock/bard honestly have no skill data in the package (noted in UI)
```

## Extraction script (`scripts/generate_phase_h_data.py`)

Reads UTF-16 `server_dep/silkroad/textdata` files and writes four small JSON
files under `map/src/game/data/` (committed, bundled by Vite):

- `level_progression.json` — 150 levels from `leveldata.txt` (exp-to-next,
  SP, mastery columns).
- `items.json` — the seven level-1 starter items from `itemdata_5000.txt`
  (refId, code, official name, levelReq, slot, raw columns for heal/speed).
- `skills.json` — the verified level-1 skills per class from
  `skilldata_*.txt` + `textdata_equip&skill.txt` official names.
- `masteries.json` — mastery rows from `skillmasterydata.txt` +
  `learnablemastery.txt` (class -> mastery id mapping).

Run it with `uv run scripts/generate_phase_h_data.py`. It is idempotent.

## Runtime (`map/src/game/`)

### New: `data_loader.ts`

- `expToNext(level)` — the real exp curve (Lv.1 -> Lv.2 needs 118 exp; maxes
  at 150). `MAX_LEVEL = 150`.
- `getRealItem(id)` / `getMastery(id)` / `getClassSkills(classId)` /
  `getClassMasteryName(classId)` — accessors over the bundled JSON.

### Rewritten: `items.ts` — real starter items

- `sword_01_a` (Copper Sword), `m_heavy_01_ba_a` (Copper Armor),
  `ring_01_a` (Ume Copper Ring), `hp_potion_01` (HP Recovery Herb),
  `hp_potion_02` (HP Recovery Potion (Small)) — names, codes, refIds and
  levelReq come from `itemdata_5000.txt`. Heal values are the game's
  ItemLifeColumn (60 / 110). Attack/defense/hpBonus/value stay tuning.

### Extended: `game_data.ts` — verified class descriptors

- Class descriptions now name the verified mastery for each class from the
  package (Sword/Lightning for Warrior, Spear/Cold for Rogue, Bow/Fire + the
  Water heal line for Cleric, European Wizard/Force for Wizard).
- Warlock and Bard are honest: the package has their class name only in the
  UI strings, no skill data.
- Added `HP_PER_LEVEL` / `MP_PER_LEVEL` (tuning) for the level-up stat growth.

### Extended: `storage.ts` / `types.ts` — EXP persistence

- `GameCharacter.exp` added and backfilled by `normalizeCharacter()` so old
  saves still load.

### Extended: `game3d.ts` — EXP + level-up + skill casting

- Defeating the training dummy grants `DUMMY_EXP_REWARD` (20, tuning) EXP.
- `gainExp()` consumes the real exp curve, levels up through `MAX_LEVEL`, full
  heals and fires `onLevelUp` (banner + log) and a "LEVEL UP!" floater.
- `useSkill(code, name)` — plays the attack swing and logs the verified skill
  name + code. Skill effects are explicitly placeholder (no damage/heal
  tables were extracted); this is stated in the log line.

### Extended: `hud.ts` — EXP bar, real skills, level-up banner

- EXP bar under MP (with "MAX" at level 150), driven by `exp`/`expToNext`.
- Skill bar slot 3-6 now show the class's real level-1 skills, each labelled
  with a compact code tail (e.g. `SMASH A`) and a `title` tooltip with the
  full official name + code. Mastery name is shown on the character plate.
- New `Hud.showLevelUp(level)` banner overlay with a fade animation.
- New `HudOptions.onUseSkill` / `onLevelUp` callbacks.

### Extended: `flow.ts`

- `persist` now recomputes max HP/MP from class base + level growth + item
  bonuses (`recomputeStats`) before saving, so level-ups and equips stay
  consistent.
- `useBestPotion` uses the real potion ids (`hp_potion_02` then
  `hp_potion_01`).

## Honest gaps

- Warlock and Bard skill slots stay locked: the package contains no skill data
  for them (only their class names). The HUD says so.
- Damage/heal values for skills are not implemented (no skill effect tables
  were extracted); casting logs the verified name/code.
- Item attack/defense, class HP/MP, EXP rewards and icons remain gameplay
  tuning, marked as such in code.

## Validation

- `python3 scripts/generate_phase_h_data.py` regenerates the four data files
  idempotently (150 levels, 7 items, 10 masteries, 16 skills) with no diff.
- `deno task build` (tsc strict + `vite build`) passes clean; 261 modules
  transformed, no type errors, no unused-symbol warnings.
- Dev server (`deno task dev`) serves the app at 200; `data_loader.ts` and the
  data JSON transform and bundle correctly through Vite.
- Preview link: https://3000-4e7ff0392c22603c.monkeycode-ai.live

## Shipped files

- `scripts/generate_phase_h_data.py` — extraction script.
- `map/src/game/data/{level_progression,items,masteries,skills}.json` —
  generated, committed data.
- `map/src/game/data_loader.ts` — runtime accessors.
- `map/src/game/{items,game_data,storage,types,game3d,hud,flow}.ts` +
  `map/src/style.css` — wiring changes.
- `README.md` — added the new script to the processing step list.
