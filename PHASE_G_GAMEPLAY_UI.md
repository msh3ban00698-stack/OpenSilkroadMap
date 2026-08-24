# Phase G: Gameplay UI, Inventory, and NPC Interaction

Status: COMPLETE — the Phase F in-world character is now wrapped in a real
gameplay layer: a full HUD (HP/MP bars, level/class plate, gold, minimap radar,
target panel, 6-slot skill bar, log, virtual joystick + ATK/TALK buttons),
world-object picking (tap/click to select the Dungeon Exit NPC or the training
dummy), an NPC interaction dialog, a working inventory + equipment panel with
equip/unequip/use, class-based HP/MP with regeneration, potions, a dummy gold
reward loop, and a player death/respawn cycle. Character data (gold, HP/MP,
bag, equipped gear) persists across sessions in localStorage.

The intro -> character select -> create (now with a starter-kit choice) ->
naming -> enter-world flow is preserved, and the real chinaman_fighter rig /
sword mesh is reused: equipping the starter sword actually shows the sword in
the 3D model.

## Goal

```
Phase F world  ->  HUD + gameplay systems (all real DOM/3D wiring, no mock server)
  -> HUD: HP/MP bars, level/class, gold, minimap radar, target panel, skill bar
  -> controls: joystick + WASD + camera drag + tap/click world picking
  -> NPC interaction: select Dungeon Exit -> dialog (placeholder text, honest)
  -> inventory/equipment panel: bag grid + weapon/armor/accessory slots
     - equip/unequip/use with stat effects (armor +20 max HP)
     - sword equip/unequip reflected on the real sword mesh (part sword_01)
  -> player stats: class-based HP/MP + regen, damage, death overlay, respawn
  -> dummy rewards gold on defeat (light gameplay loop)
```

## Runtime (`map/src/game/`)

### New: `items.ts` — item definitions

- `ItemDef` (id, name, slot `weapon|armor|accessory|consumable`, color, stats,
  value) with procedural inline-SVG data-URI icons (no binary art committed).
- Starter set: Training Sword (real sword_01 mesh + tint), Leather Armor
  (+20 max HP), Guard Ring (+2 defense), Small/HP potions (heal 40/90).
- `isEquippable()` narrows to equipment slots.

### New: `inventory_panel.ts` — bag + equipment UI

- Overlay panel with a 12-slot bag grid and three equipment slots.
- Click any item to see a detail footer (icon, stats, description) and an
  action: Equip (bag -> slot, swapping any current item back), Unequip
  (slot -> bag), Use (consumable heal).
- Re-renders from the live character object, so flow re-renders after every
  mutation.

### Extended: `game_data.ts` / `storage.ts` / `types.ts` — character data

- `GameCharacter` gains `gold`, `hp/mp/maxHp/maxMp`, `inventory` (stacks), and
  `equipment` (per-slot item id). `createCharacter` seeds class stats, gold 100,
  a starter kit, and the pre-equipped Training Sword.
- `CLASS_STATS` per class (hp/mp + regen/s). Two starter kits: Blade Kit
  (armor + ring + 2 small potions) and Survival Kit (4 small + 2 HP potions).
- `normalizeCharacter()` migrates characters saved by earlier phases, backfilling
  the new fields so old saves still load.

### Extended: `game3d.ts` — gameplay state in the world

- Player HP/MP (from character), per-second regeneration, `damagePlayer`,
  death (overlay + 3.5 s wall-clock countdown) and respawn at the region spawn
  with full HP/MP. The respawn timer uses `performance.now()` deadlines so it is
  frame-rate independent (SwiftShader headless runs ~3 fps).
- Raycast `pick(clientX, clientY)` against the NPC groups + training dummy;
  selection ring highlight; `selectTarget`/`clearTarget`.
- Attack respects the selected target (NPCs cannot be attacked; the dummy can);
  the dummy occasionally retaliates for 6-14 damage (demonstrates HP loss), and
  defeating it grants 6-18 gold.
- `interact()` finds the nearest NPC and fires `onInteractNpc`, which flow
  routes to the HUD dialog.
- `applyEquipment()` toggles the real `sword_01` mesh part and tints it with the
  equipped weapon's color.
- `getState()` exposes everything the HUD polls: hp/mp/gold/level, selected
  target, position, NPC/dummy radar data, bounds, death/respawn info.

### Rewritten: `hud.ts` — full game HUD

- Character plate (name, Lv/class), HP + MP bars, gold coin + amount.
- Target panel (name, HP bar, distance) for the selected NPC/dummy.
- 6-slot skill bar: 1 = ATK, 2 = Potion (uses best potion), 3-6 locked.
- Minimap radar canvas (player triangle oriented by yaw, NPC/dummy dots, region
  bounds) polling the world every 150 ms.
- Log, virtual joystick, ATK/TALK buttons (unchanged wiring), death overlay, and
  an NPC dialog panel (placeholder dialogue, honest label).

### Extended: `player_control.ts` — tap vs drag

- A short press (<= 6 px movement) selects a world target via `onSelect(x, y)`;
  a drag still orbits the camera. Joystick/WASD unchanged.

### Extended: `screens.ts` / `flow.ts` — create kit choice + wiring

- Create screen adds a starter-kit picker (Blade / Survival).
- `GameFlow` wires HUD <-> world: pick, NPC dialog, potions, equip/unequip,
  character persistence (`onCharacterMutated` -> `saveCharacter`), and the
  inventory panel; `teardownWorld` disposes everything.

## Validation (all real, headless Chromium + SwiftShader)

- Build: `deno task build` (tsc 0 errors + vite) passes.
- **Phase G: 20/20 pass** (`/tmp/opencode/validate_phase_g.js`, desktop 1280x800 +
  mobile 390x844): enter world with warrior (HUD bars 140/140 & 60/60, gold 100,
  minimap, 6 skill slots, target/death hidden) -> HP regen -> tap selects the
  Dungeon Exit NPC (real pointer events) -> TALK opens its dialog -> skill-bar
  POT heals after self-damage -> inventory shows equipped Training Sword +
  armor/potions in bag -> equipping Leather Armor raises max HP 140 -> 160 and
  unequipping restores it -> dummy target panel -> defeating the dummy grants
  gold (100 -> 112) -> self-damage triggers the death overlay -> respawn at
  spawn with full HP -> screenshots confirm rendering (litPct ~3% desktop, ~11%
  mobile) -> no console errors. Mobile: HUD present, Survival Kit honored
  (potions, no armor), touch tap selects the NPC.
- **Persistence: pass** (`/tmp/opencode/validate_phase_g_persist.js`) — equip
  armor (max HP 140 -> 160), reload, re-enter: equipment, max HP and gold are
  restored from localStorage.
- **Phase F regression: 15/15 pass** — movement, rotation, attack anim, damage,
  idle, canvas render all stay green.
- **Phase E regression: 9/9 pass** — character viewer and map screens unaffected.

## Files Changed (Phase G)

- `map/src/game/items.ts` (new) — item definitions + SVG icons.
- `map/src/game/inventory_panel.ts` (new) — bag + equipment panel.
- `map/src/game/game3d.ts` — HP/MP/regen, death/respawn, picking, targets,
  NPC interaction callback, dummy retaliation + gold, weapon mesh reflection,
  `getState`/`pick`/`selectTarget`/`usePotion`/`applyEquipment`/`damagePlayer`.
- `map/src/game/hud.ts` — full HUD (bars, gold, minimap, target panel, skill
  bar, death overlay, NPC dialog).
- `map/src/game/player_control.ts` — tap-vs-drag + world select.
- `map/src/game/game_data.ts` — class stats, starter kits, gold default.
- `map/src/game/storage.ts` — new fields + save/migration.
- `map/src/game/types.ts` — gold/hp/mp/inventory/equipment fields.
- `map/src/game/screens.ts` — starter-kit choice on the create screen.
- `map/src/game/flow.ts` — HUD/world/inventory wiring + persistence.
- `map/src/game/character_rig.ts` — `findPartIndex`/`setPartVisible`/`setPartTint`.
- `map/src/style.css` — HUD, minimap, skill bar, inventory, dialog, kit styles.
- `PHASE_G_GAMEPLAY_UI.md` (this file).

`game_source/` stays untracked; no PK2/archive/database/server files committed.

## Real Assets vs Placeholders

| Feature | Source |
|---|---|
| Character / animations | Real chinaman_fighter rig (Phase E/F exports) |
| Sword appearance (equip/unequip) | Real `sword1_2_3.webp` mesh part `sword_01` (tint + visibility) |
| Dungeon Exit NPC + position | Real `npcs.json` / `REGION_NPCS` (region 32785) |
| Region terrain/spawn/bounds | Real Phase D exports |
| Classes, gold, HP/MP, potions, kits | Gameplay tuning — no extracted balance data |
| Item icons | Procedural SVG (no icon art extracted) |
| Armor/accessory 3D appearance | None exists — stat-only change (labeled in UI) |
| NPC dialogue text | Placeholder (labeled in the dialog) |
| Minimap | Procedural radar from live world state |

## Remaining Limitations

- Only the Training Sword maps to a real 3D part; armor/accessory only change
  stats. No item icons are extracted, so they are procedural SVGs.
- HP/MP numbers, potion values, gold rewards and dummy retaliation are invented
  tuning (no real game balance data was available).
- NPC dialogue is a placeholder; there is no real NPC script/quest data wired.
- Levels stay at 1 (no EXP/level-up yet); the skill bar slots 3-6 are locked
  because no per-class skill data is wired.
- SwiftShader headless runs ~3 fps; real GPUs run at 60 fps.
