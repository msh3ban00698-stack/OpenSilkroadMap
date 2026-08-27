# Responsive UI Refactor — Verification Report

This document records the mobile-landscape-first responsive refactor of the game UI and the
programmatic verification performed against the six mandated viewports.

## 1. Summary

The entire game UI was refactored into a true responsive system driven by a single set of
centralized CSS design tokens. No `transform: scale(...)`, `zoom`, or global-shrink hacks remain.
The previously broken ~1536x687 landscape experience (and the landscape experience at every other
tested size) now renders without clipping, off-viewport controls, or page overflow.

Automated layout verification at all six mandated viewports reports **0 issues** across every
screen.

| Viewport  | Login | Create Acct | Select | Create | World HUD | Inv | Pause | NPC | Shop | Quest | Party | Warehouse |
| --------- | ----- | ----------- | ------ | ------ | --------- | --- | ----- | --- | ---- | ----- | ----- | --------- |
| 800x360   | 0     | 0           | 0      | 0      | 0         | 0   | 0     | 0   | 0    | 0     | 0     | 0         |
| 960x540   | 0     | 0           | 0      | 0      | 0         | 0   | 0     | 0   | 0    | 0     | 0     | 0         |
| 1280x720  | 0     | 0           | 0      | 0      | 0         | 0   | 0     | 0   | 0    | 0     | 0     | 0         |
| 1536x687  | 0     | 0           | 0      | 0      | 0         | 0   | 0     | 0   | 0    | 0     | 0     | 0         |
| 1600x720  | 0     | 0           | 0      | 0      | 0         | 0   | 0     | 0   | 0    | 0     | 0     | 0         |
| 1920x1080 | 0     | 0           | 0      | 0      | 0         | 0   | 0     | 0   | 0    | 0     | 0     | 0         |

## 2. Centralized responsive design system

All screen/HUD geometry is defined once in `map/src/style.css` on `:root` as clamp()/min()/dvh
tokens, consumed by every component rule. No scattered one-off pixel values drive layout.

- Safe-area / viewport gutters: `--gx`, `--gx-r`, `--gy`, `--gy-b` (`max()` + `env(safe-area-*)`)
- Panel widths: `--panel-w`, `--sheet-w`, `--modal-w`, `--dialog-w`
- Panel heights: `--sheet-h`, `--modal-h` (dvh-clamped)
- HUD geometry: `--plate-w/-h`, `--bar-h`, `--ctl-lg/-md/-sm/-xs`, `--joy-d/-k`, `--minimap-d`, `--hud-bottom-zone`
- Typography: `--txt-xs/-sm/-md`
- Panels sized with `width: min(88vw, var(--modal-w))`, `max-height: var(--modal-h)`, etc.

Landscape behavior is driven by `@media (min-width: 700px) and (orientation: landscape)`
(row splits, side-by-side panels, orientation-tuned HUD positions) with a
`@media (max-width: 640px) and (orientation: portrait)` block for phone-portrait only.

## 3. What was fixed this iteration

1. **Create-character screen row split was dead.** The landscape media query that switched the
   screen to a 58/42 form/preview row layout was being overridden by a later base rule
   (`flex-direction: column-reverse`). The screen had been stacking preview-on-top / form-below at
   every landscape size. Moved the landscape block after all base select/create rules so it is the
   authoritative source.
2. **Create-character color selectors were below the fold.** The three color fields
   (Skin / Hair / Outfit) occupied three stacked rows. Consolidated them into a single responsive
   "Appearance" field with three inline color groups that sit side-by-side in landscape and stack
   in portrait. All 13 swatches now render inside the visible form area at 1280x720 and above
   (verified: appearance field bottom == form scroll viewport bottom at 1536x687).
3. **Create form compaction in landscape.** Tighter field margins, 11px labels, 40px min-height
   cards/segments, 38px swatches, and zero margin on the last field so the form fits without
   scrolling at 1280x720+ (the form scrolls gracefully on smaller landscape screens).
4. **HUD combat log clipped newest messages.** `.hud-log` was `overflow: hidden` with a
   `max-height` (12vh) while the log appends new lines at the bottom — the newest line was cut off.
   Removed the clip; the log auto-sizes to its 4-line cap.
5. **Harness robustness** (tooling only, not shipped code): screenshots of the WebGL world were
   taking ~60s under SwiftShader and repeatedly tripping timeouts. Added a single
   canvas-hidden window for panel screenshots (1.4s vs 66s) and per-viewport browser isolation.

## 4. Verification methodology

Playwright + headless Chromium, one fresh browser per viewport, `deviceScaleFactor: 1`.

For every viewport, the app is driven through the real flow: login -> create-account -> select ->
create-character -> enter world (3D world boots, `#game-container` becomes visible) -> world HUD ->
inventory -> pause -> NPC dialog -> shop -> quest -> party -> warehouse.

In-page checks (run for every screen at every viewport):

- `document.scrollWidth/scrollHeight` vs viewport (horizontal/vertical page overflow)
- Every visible element's `getBoundingClientRect()` must be within the viewport (off-viewport
  detection; content inside a scrollable container is treated as reachable, not clipped)
- Every `overflowY: hidden` container whose content overflows (true clipping, e.g. the hud-log bug)
- Every interactive control (button/input/select/[role=button]) must be on-screen or scroll-reachable

Each screen is also captured to a PNG as evidence. See the `*.png` files in this directory
(12 screens x 6 viewports = 72 files).

## 5. Screen-by-screen audit coverage

All UI screens and surfaces were audited during the refactor:

- Login, create account, character select, character create (fully redesigned)
- World HUD: plates (HP/MP/EXP), portrait, minimap, skill bar, slots, target plate, action buttons
  (ATK/TALK), joystick, combat log, quest tracker, level-up/gold/region, dialog panel
- Game panels: inventory, equipment, skills, masteries (via inventory/skill flows), NPC dialogs,
  shops, quest dialogs, teleport, party, guild, warehouse, pause menu, settings, chat (HUD log),
  map/minimap, loading screens, notifications/tooltips, confirmation dialogs

## 6. No scale-as-a-fix hacks

The built stylesheet contains no `transform: scale(...)` and no `zoom:` declarations. The only
remaining `grayscale(.8)` filter is a disabled-button state. The old
`@media (max-height: 430px)` block that applied `transform: scale(0.72)` to the minimap was
replaced with vh-driven tokens and `orientation` media queries.

## 7. Evidence

- Screenshots: this directory (`72x...` naming = viewport-screen).
- Raw run logs: `/tmp/opencode/verify/full-run2.log`
- Machine-readable issues: `/tmp/opencode/verify/report.json`
- Verification harness (tooling, not shipped): `/tmp/opencode/verify/check.mjs`
