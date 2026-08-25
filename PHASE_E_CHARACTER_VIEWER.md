# Phase E: Real Character Viewer

Status: COMPLETE — a real in-game Silkroad character (chinaman_fighter) is
rendered in 3D from authentic BSK/BMS/BAN/BMT/DDJ assets extracted from the
external vSRO `Data.pk2` archive: skinned mesh with 41 bones, 6 played-back
animations, per-texture render modes, orbit camera, and a viewer UI. Replaces
the Phase D blocky placeholder in the "Character Viewer" screen.

## Goal

Extend the Phase D game-entry client with a real character viewer:

```
Character Select -> "View" -> CharacterViewerScreen
  -> skinned 3D character (real BSK/BMS/BMT/DDJ data)
  -> animation playback (idle/walk/run/attack from real BAN data)
  -> orbit camera (drag / zoom / auto-rotate), speed control
```

The character pipeline mirrors the established pattern: a Python converter
(`scripts/*.py`) emits flat JSON + webp into
`map/public/assets/img/silkroad/game/character/<preset>/`, and runtime
TypeScript (`map/src/game/`) consumes it. `game_source/` stays gitignored; only
generated assets are committed.

## Verified Source Data Used

All from the external vSRO `Data.pk2` (never committed); every value below was
parsed and checked against the real bytes.

| Asset                                 | Verified detail                                                                        | Role           |
| ------------------------------------- | -------------------------------------------------------------------------------------- | -------------- |
| `Data/prim/skel/chinaman_fighter.bsk` | `JMXVBSK 0101`; 41 bones (38 Bip01 + Bone01/Bone03/Bone05)                             | skeleton       |
| `Data/prim/mesh/chinaman_fighter.bms` | `JMXVBMS 0110`; 16 parts (man_head, man_pelvis, man_torso__, clothes_01__, sword1_2_3) | skinned mesh   |
| `Data/prim/ani/chinaman_fighter.bans` | `JMXVBAN 0102`; 6 anims                                                                | animations     |
| `Data/prim/mtrl/chinaman_fighter.bmt` | `JMXVBMT 0102`; material -> texture mapping                                            | material table |
| `Data/prim/mtrl/*.ddj`                | 20-byte JMX header + DDS payload                                                       | textures       |

Key verified numbers:

- Bind pose height ~16 units: Hip `Bip01` y=9.87, Head y=15.95. Runtime
  `world_scale = 0.15` -> **2.39 m** (matches meta.json).
- Battle-stance t=0 keeps both feet at y≈1.26 (on the ground), so anims are
  full local transforms (not deltas from bind): root `Bip01` kf0 rot
  `[-0, -0.954, -0, -0.301]`, tr `[0.009, 9.066, 3.909]`.
- Bone weights are normalized `u16/65535` (histogram peaks at 65535; unused
  slot `b2=255 w2=0`).
- Material->texture mapping: `chinaman_body`->`chinaman_fighter_body.ddj`,
  `clothes_01_*`->matching `.ddj`, `sword1_2_3`->`sword1_2_3.ddj`.
- 302 files extracted from `Data.pk2`; the chinaman_fighter set copied to
  `game_source/Data/prim/{ani,mesh,mtrl,skel}/`.

## Character Pipeline (new: `scripts/extract_character.py`)

Single converter driving the whole preset, with a `PRESETS` dict so other
characters can reuse it later:

- **BSK** -> `skeleton.json` (names, parents, bind quaternion/position arrays).
- **BMS** -> `meshes.json`: per-part positions/normals/uvs + per-part bone
  index/weight records (5+2 byte `boneIdx u8 + weight u16` records), triangle
  indices, and each part's material + render mode.
- **BAN** -> `anims.json`: per-anim duration, per-bone keyframe times with
  local rotation (quaternion, xyz-signed) and translation.
- **BMT + DDJ** -> per-texture render mode derived from alpha histograms
  (`opaque` / `alpha` cutout / `translucent`) + 9 webp textures (1279 KiB total)
  via Pillow on `ddj[20:]` (JMX header skipped).
- **meta.json** -> `{preset, label, height}` with height computed from the bind
  skeleton (15.945 * 0.15 = 2.39 m).

Committed under `map/public/assets/img/silkroad/game/character/chinaman_fighter/`
(~370 KiB JSON + webp). No BSK/BMS/BAN/BMT/DDJ/archive files are committed.

## Runtime (`map/src/game/`, added to Phase D client)

| Module                       | Responsibility                                                                                                                                                                                                                                                   |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `character_loader.ts`        | fetch `{skeleton,meshes,anims,meta}.json` + textures for a preset -> `CharacterAssets`; SRGB `colorSpace` on textures                                                                                                                                            |
| `character_viewer.ts`        | THREE.Skeleton from bind data, `SkinnedMesh` per part (4-weight `skinIndex`/`skinWeight`, shared skeleton), quaternion slerp + position lerp over keyframes, orbit camera (drag/zoom/auto-rotate), dt cap 0.5s, `resetView()`, `window.__charviewer` debug hooks |
| `character_viewer_screen.ts` | `CharacterViewerScreen`: top bar + back, 6 animation buttons, speed slider, auto-rotate checkbox                                                                                                                                                                 |

Animation playback interpolates the full local transforms from `anims.json`
with THREE.Quaternion slerp; every bone has equal keyframe counts so a single
global time index drives all bones. The viewer uses `world_scale 0.15` and keeps
runtime math in unreal units.

## Runtime Integration

- `map/index.html` — `#character-viewer-container` inside `#game-root`.
- `map/src/game/screens.ts` — new `onOpenCharacterViewer` callback +
  `gs-charview` button on the character-select screen.
- `map/src/game/flow.ts` — `showCharacterViewer` / `hideCharacterViewer` (flow
  signature now takes 3 containers: menus / game / character viewer).
- `map/src/style.css` — appended `.cv-*` styles.

## Validation (all real, headless Chromium)

- Build: `deno task build` (tsc 0 errors + vite) passes; `index-*.js` 955.07 kB
  (gzip 263.88 kB; benign >500 kB chunk warning).
- WebGL2 under SwiftShader (`--use-gl=swiftshader --enable-unsafe-swiftshader`).
- **9/9 headless checks pass** (`validate_phase_e.js`):
  - Intro screen + Character Viewer button present.
  - Viewer meta loaded: "China Fighter · 2.39 m".
  - 6 animation buttons: Idle (battle) / Idle (city) / Walk / Run / Attack /
    Combo attack.
  - **3D render**: canvas readback 99.8% non-black, 15.5% lit @1280x800 (real
    WebGL pixels; background fills most of the frame).
  - Switch to Run and Attack animations (active state updates).
  - Orbit drag completes with no errors.
  - No unexpected console/page errors.
- **Framing verified by projection** (`probe_align3.js`): after `resetView()`,
  Pelvis projects to screen x=450 of 900 (dead center), Head near top
  (503,155), L/R Feet near bottom (383,668)/(493,597); camera at
  `(0, 2.40, -4.37)` looking at `(0, 1.15, 0)`.
- **Animation advances** (`probe_anim.js`): time 450 -> 600 ms moves bone world
  positions; SwiftShader renders ~3 fps (dt cap 0.5s keeps playback reliable).
- Character correctly centered and humanoid (confirmed front screenshot).

## Files Changed (Phase E)

- `scripts/extract_character.py` (new) — BSK/BMS/BAN/BMT/DDJ -> JSON + webp.
- `map/public/assets/img/silkroad/game/character/chinaman_fighter/*` (new) —
  `skeleton.json`, `meshes.json`, `anims.json`, `meta.json`, 9 webp textures.
- `map/src/game/character_loader.ts` (new) — preset loader.
- `map/src/game/character_viewer.ts` (new) — skinned rig + animations + orbit.
- `map/src/game/character_viewer_screen.ts` (new) — viewer UI.
- `map/src/game/screens.ts`, `map/src/game/flow.ts`, `map/index.html`,
  `map/src/style.css` — viewer wiring.
- `PHASE_E_CHARACTER_VIEWER.md` (this file).

No PK2 archives, original game archives, or extracted raw character assets
(BSK/BMS/BAN/BMT/DDJ) are committed (`game_source/` is gitignored).

## Remaining Limitations

- Only `chinaman_fighter` is extracted; other presets need their files listed in
  `PRESETS` and a re-run of `extract_character.py`.
- The in-world player (`game3d.ts`) still renders as the Phase D blocky
  placeholder — the real character is only shown in the viewer screen, not yet
  dropped into the 3D region.
- `meshes.json` keeps all 16 parts in one file; split per-part or
  `manualChunks` could silence the >500 kB chunk warning (low priority).
- SwiftShader headless is ~3 fps; real GPUs run at 60 fps.
