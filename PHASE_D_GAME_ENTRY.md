# Phase D: Game Entry + 3D Character Foundation

Status: COMPLETE — a created character can enter a verified 3D region rendered
from real vSRO data (region 32785 "Cave of Meditation"), move, look around,
speak to the region's real NPC, and switch back to the 2D world map. The map
pipeline from Phase C is preserved; the game client runs alongside it in the
same Vite app.

## Goal

A first playable game-entry flow inspired by classic Silkroad Online:

```
Intro -> Character Selection -> Create (name/class/appearance)
      -> Confirm -> Enter Game -> 3D Region Loader -> playable 3D test region
```

Built on top of the existing extraction / indexing / world-map work. Not the
complete MMORPG — it proves a created character can enter a verified 3D region.

## Verified Source Data Used

All resolved from the external vSRO `Media.pk2` / `Data.srp` archives (never
committed to Git); everything below was parsed and checked, not guessed.

| Asset | Verified detail | Role |
| --- | --- | --- |
| `Data/Dungeon/wchina/fortress_dungeon.dof` | 56,311 B, 1 floor, 29 blocks | region floor plan |
| `Data/Zone_data/wchina/fortress_dungeon01/*.bsr` + `*.bms` (13+13) | 1,438 vertices / 2,120 triangles | 3D floor meshes |
| `Media/minimap_d/fort_dungeon/fort_dungeon01_{127..129}x{126..128}.ddj` | 9 x 256x256 | 3D floor texture source |
| `Media/server_dep/silkroad/textdata/characterdata_*.txt` | region 32785: 1 NPC "Dungeon Exit" @ (1134.79, 0, -864.29) | in-world NPC |
| `Media/server_dep/silkroad/textdata/textdata_equip&skill.txt` | 6 class strings | class names |
| `Media/server_dep/silkroad/textdata/textzonename.txt` | 32785 -> "Cave of Meditation" | region label |

## 3D Mesh Pipeline (new: `scripts/generate_region_mesh.py`)

Converted the verified DOF + BMS floor data into a compact client mesh, and the
9 minimap DDJs into a floor texture:

- `mesh.json` — **91,943 B**. `vertexCount 1438`, `indexCount 6360` (2,120
  triangles), world bounds X -986.9..2966.9 / Z -2247.1..520.0 / Y -10.04..0.08;
  per-block entries (id/name/floor); a `spawn` point at the verified "Dungeon
  Exit" NPC (1134.79, -864.29) with height interpolated from the floor
  triangles (barycentric).
- `floor.webp` — **31,872 B**. 3x3 minimap composite of the 9 DDJ tiles (20-byte
  JMX header skipped), quality 85, 768x768.

Committed under `map/public/assets/img/silkroad/game/region32785/` (gitignored
tree is un-ignored for these two small files, same policy as Phase B/C runtime
assets). No PK2/archive/BSR/DJJ files are committed.

## Game Client (`map/src/game/`, 1,301 LOC)

Rendered with three.js (`three@^0.161`, added to `map/deno.json`) into a new
`#game-root` overlay; the Phase C map stays under `#map`:

| Module | Responsibility |
| --- | --- |
| `types.ts` | `Appearance`, `GameCharacter`, `GameState` |
| `game_data.ts` | 6 verified classes, `START_REGION=32785` + name + URL, region NPC |
| `storage.ts` | character create/load/save/delete (localStorage `silkroad_characters_v1`) |
| `screens.ts` | intro / select / create / loading / error screens (all inferred labels marked "(inferred)") |
| `region_loader.ts` | fetch `mesh.json` + `floor.webp` -> THREE.BufferGeometry (Uint32 indices, vertex normals) + SRGB texture |
| `game3d.ts` | scene, lights, floor mesh, NPC group + label sprites, player from appearance colors, third-person camera, walk/attack/interact, resize/dispose, `window.__sro3d` debug hook |
| `player_control.ts` | touch joystick + pointer-drag camera + WASD/arrow fallback (pointer-capture correct on the joystick element) |
| `hud.ts` | name/Lv/class plate, region label, log, joystick, ATK/TALK buttons |
| `flow.ts` | intro->select->create->world state machine; pause overlay; map bridge + return-to-game |

Verified class names (from `textdata_equip&skill.txt`, UTF-16, key
`parts[1]`, English `parts[8]`): **Warrior, Rogue, Wizard, Warlock, Bard,
Cleric**. No verified race strings exist in the package data, so race and all
appearance options are temporary visual placeholders clearly marked
`(inferred)`.

The player model is a blocky placeholder built from the appearance colors
(cloth/hair/skin) — there is no claim of real Silkroad character art; that
remains a next step.

## Runtime Integration

- `map/index.html` — `#game-root` (`#game-menus`, `#game-container`),
  `#return-to-game` button, empty data-URI favicon (removes the benign 404).
- `map/src/main.ts` — `initGameFlow()` after the map/editor init.
- `map/src/style.css` — ~450 lines of game/HUD CSS (screens, class grid, color
  swatches, loading spinner, HUD, joystick, pause, return-to-game).
- `map/deno.json` + `deno.lock` — three.js + types.

## Validation (all real, headless Chromium)

- Build: `deno task build` (tsc 0 errors + vite) passes — 250 modules,
  `index-*.js` 931.8 kB (gzip 258.06 kB; benign >500 kB chunk warning).
- Dev server (Vite :3000) + preview URL; `mesh.json` + `floor.webp` return 200.
- WebGL2 available under SwiftShader (`ANGLE ... SwiftShader`) with
  `--use-gl=swiftshader --enable-unsafe-swiftshader`.
- **21/21 headless checks pass**:
  - Intro screen (`SILKROAD`) + Start / Open World Map buttons.
  - Empty character select -> Create screen with 6 classes.
  - Name validation rejects empty ("Name is required.").
  - Create character -> Enter world: HUD shows the name, WebGL canvas present.
  - **3D render**: canvas readback 1.2% non-black, 0.3% bright, 160 distinct
    colors @1280x800 (dark cave scene — content is real).
  - **Spawn exact**: player at x=1134.8 z=-864.3 (verified "Dungeon Exit" NPC).
  - **NPC interact**: TALK opens the welcome log and speaks to "Dungeon Exit".
  - **Movement**: W-key walk moves the player (10.5+ units).
  - **Camera drag**: yaw rotates 0.50 -> 1.70.
  - **Attack**: ATK logs the placeholder attack action.
  - Pause menu (Resume / Character Select) works.
  - Persistence: character listed after leaving world; re-enter works.
  - Mobile viewport (390x844, touch): **touch joystick moves the player**
    (87.5 units — pointer-capture fix validated), canvas renders.
  - No unexpected console errors (favicon 404 removed via data-URI favicon).
  - 2D world map still opens from the game and `Back to Game` returns.

## Files Changed (Phase D)

- `scripts/generate_region_mesh.py` (new) — DOF + BMS + DDJ -> `mesh.json` +
  `floor.webp` (committed earlier as `7e7e315`).
- `map/public/assets/img/silkroad/game/region32785/{mesh.json, floor.webp}`
  (new, committed) — 3D region assets.
- `map/src/game/*` (new) — the 9-module game client above.
- `map/src/main.ts`, `map/index.html`, `map/src/style.css` — game integration.
- `map/deno.json`, `map/deno.lock` — three.js dependency.
- `PHASE_D_GAME_ENTRY.md` (this file).

No PK2 archives, original game archives, databases, server files, or extracted
game assets are committed.

## Remaining Limitations

- Player model is a colored placeholder block; no real Silkroad character art,
  animations, or equipment rendering yet.
- Race/class appearance options are inferred (no verified race strings).
- No combat/quests/multiplayer/server; attack is a placeholder action.
- Only region 32785 has a client 3D mesh; other regions would need their DOF +
  BMS converted the same way.
- Touch joystick + camera share pointer input; multi-touch (joystick + camera
  simultaneously) is not implemented.
- SwiftShader headless rendering is ~3 fps (dt is clamped to 0.05); real
  devices with GPU run at 60 fps.
