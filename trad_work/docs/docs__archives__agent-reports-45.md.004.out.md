### Menu text alignment (#45, agent TX)
- **Established**: the viewer places the TextMeshes like the original game. Check on ecran4 (mobile) and ecran3 (PC), same scale 1.688 px / unit: "Ragnar" text of the tab identical to the pixel; "Rat volant" (1 line) and "Scarapince / ×2" (3 lines) within ±1 px. Formula (`first_line_baseline`): block of N lines with step leading (23.525) × characterSize × 0.1 × lineSpacing, anchored at the top / middle / bottom of the point z − dy, baseline at ascent (18.887 × characterSize × 0.1) below the top of the line. Test: `tools/test_text_recentering.py`.
- **Established**: the engine sends the group names in the form `Nom\n\n\t×2` (3 lines) for the plates (type 31) and the target buttons (type 33). The step between the name and "×2" is therefore 2 × the step of one line.
- **Established (cause of the "text too low")**: the game's `lineSpacing` values (0.441 targets, 0.481 monster plates, 0.801 tabs / buttons / names, 0.873…) are computed for the Japanese font; they shorten the line box but the baseline stays at ascent from the top. The ink of SE-GARRIR sits (1 − ls) × 23.525 × u / 2 below the center of its box (6.5 units for the targets and plates, 2.3 for tabs and buttons). The original game has the same defect.
- **Fix (#45, deliberate departure, request from Sylfried of 2026-11-02 14:08)**: `text_recentering` raises any text with lineSpacing < 1 by this offset (a single place, `Render._text`). lineSpacing ≥ 1 ("PV" / "PM" / "Nv.", lists) unchanged. `DQ_TEXTE_ORIGINAL=1` gives the exact placement of the game. Measurements 1280×720: status plate name −2 px, monster plate −5 px, tab −2 px, buttons −2 px.
- **Assumed / not verified**: top and bottom anchorings (no mobile screenshot of the name in the status band nor of the monster plates); the plate's fitted window (VariableWindow, 142 × 18 or 36) is rebuilt by the viewer (`Window.plate`), the original's frame might be placed differently.
- The text between these two option sets is not a setting of the Pause window (environment variable only).
- Useful debugging: a temporary trace of `Window.param_str` and `Window.plate` showed the raw strings; it is not kept.

4. NOT VERIFIED
- Windows and real GPU: my renderings come from Mesa (llvmpipe).
- I did not launch a battle with several groups (slot 4 only has one "Glacyclone" group), so the target choice window (type 33) was only seen in off-screen rendering of the layout with the engine's strings, not in a real battle.
- Off-screen renderings made with pyglet "headless" (EGL) and not via xvfb, because the `/tmp/xvfb.lock` lock was saturated (more than 20 jobs waiting). The two real battle screenshots went through `/tmp/run_fen2_cmb.sh` (lock respected).
- Out of scope, not covered by the recentering: `ui_history.py` (history), `pause.py` (editor preview, guard `ui_font.otf`), name cartouche of the "ui" agent. If its cartouche reuses a TextMesh node of the layout, it benefits from the recentering; if it draws with `bm.line` directly, it can call `ui_menu.text_recentering(bm.leading, u, ls)`.
- Merge pitfall: only `dq4_pc/ui_menu.py` (≈ 25 lines around the constant `TEXT_MARKS`, one function added and 3 lines of `Render._text`) and the new file `tools/test_text_recentering.py` change; no other file touched.

Measurement log: `/tmp/specs/text_notes.md`. Measurement and off-screen rendering scripts: `/tmp/tx45/render_multi.py`, `/tmp/tx45/analysis.py`.

---

## Agent "combat" (a55458f8b35b63979) — 2026-11-02 21:23

FINAL REPORT, agent "combat" (prefix CB), PR #45. Worktree /home/claude/wt45-combat, branch agent45-combat (base 84b3f22). Clean `git status`, no push. 5 separate commits, one per point:
- 29fc3b7 point 1 (cascade and fades)
- acbb491 point 5 (auto speeds)
- d5eec0c point 2 (outlines)
- cea04cb point 3 (scenery by time of day)
- 7260542 point 4 (critical hit)

Tests rerun after the last commit, all OK: test_critical_hit, test_scenery_outlines, test_battle_speed (42), test_pause_pages, test_sound_text_settings, test_map_tint, test_battle_transition (15), test_turn_chaining, test_battle_scenery_time_of_day (4), test_root_scenery, test_map_textures, test_map_items, test_sound_mixing. pyflakes: only the warnings already present in the base (`dims`, `sel`, `struct`, `soundfile`, `R/yp/mh` of pause.py).

## Point 1. Pre-encounter cascade and end-of-battle fade: DONE (29fc3b7)

Established:
- The duration is now that of the original game whatever the setting: accelerator, walking speed, "Vitesse de transition" (`vitesse_fondu`), "Vitesse de combat", camera.
- `State.battle_transition()` groups the cascade effect, the loading wait, the 8-frame guard, and the fades marked "combat" (12-frame windows at the entry and at the return).
- `Game._speed_factor` returns 1.0 in these phases, and `_do_battle_step` / `_terrain_step` do not cut a transition in the middle.
- The message validation and the turn speed are not touched.

Proofs:
- Engine frames: `RealEngine` test of test_battle_transition.py (15 tests). Identical segments for transition x1, x2, x4; factor 1.0 over 72 combinations of settings.
- GL real time (`DQ_TEMPS_REEL=1`, normal window):

| Case | Before | After |
|---|---|---|
| Cascade, x1 | 2.17 s | 1.89-1.90 s |
| Cascade, x3 | 1.07 s | 1.89-1.90 s |
| End fade, x1 | 0.61 s | ≈ 0.95-0.98 s |
| End fade, x3 | 0.16 s | ≈ 0.95-0.98 s |

  The entry and exit fades were halved by `vitesse_fondu`=2. After the fix, the same durations also come out with transition x4 + walking x4 + accelerator held.
- Noisy real-time measurement (shared 2-core machine, 26-30 frames/s at x1): the main proof is in engine frames.

## Point 5. Auto battle speeds: DONE (acbb491)

Established, measured on the engine at 30 Hz (engine frames = 1/30 s):

| Typical turn at x1 | Before | After |
|---|---|---|
| Simple attack (command confirmed → next menu) | 171 frames (5.7 s) | 91 frames (3.0 s) |
| Effect of the hit → damage number | 23 frames (0.77 s) | 13 frames (0.43 s) |
| Critical | 245 frames | 125 frames |
| Escape | 247 frames | 127 frames |

- Effect durations unchanged: 5303 = 10 frames, 5344 = 17 frames.
- Intermediate code 1: 131 frames for the simple attack.
- **Spell: not measured.** No controllable spellcaster (Ragnar has no spells, Doc is an AI).
- "Normal", "Rapide" and "Très rapide" now impose the shortest automatic wait (code 0, 12 frames between two messages). The old "Normal" imposed code 2, i.e. 32 frames. "Rapide" and "Très rapide" remain x2 and x3 of "Normal". "Manuel" (code 4) is unchanged. Animations, music, SE and point 1 are unchanged.
- Change in `settings.py`: `CODE_SCROLL_AUTO = 0`. No new setting is added, so no ↺ nor key to create.

## Point 2. Outlines of the trees and mountains: DONE, MSAA 0 and 4 measured (d5eec0c)

Established cause:
- The silhouettes are in 256x256 textures whose alpha is strictly binary (0 or 255). This is verified: 41 cut-out textures out of 140 `btl*` sceneries, without intermediate alpha.
- The scenery is enlarged x6: a texel covers 4 to 10 screen pixels at 1280-2560 px wide. The outline (alpha 0.5) follows the texel grid, hence staircase steps that MSAA does not smooth (it only smooths one-pixel steps).
- The transparent texels are black (0,0,0), which creates a dark fringe with bilinear filtering. It is visible on Sylfried's screenshot.
- MSAA, alpha-to-coverage and mipmaps are not the cause.

Fix, new module `dq4_pc/scenery_outlines.py`:
- On cut-out textures with binary alpha of 128 px and more only: alpha x4 (2 EPX passes, 0.3 texel blur), color enlarged in bilinear after extending the opaque edge over 3 rings.
- Skies, grounds, transparent materials ('tr'), small textures and EPX x8 mode: unchanged.
- Interior of the drawing identical to the filtered original (mean deviation < 1 gray level).
- `DQ_SANS_CONTOURS=1` gives back the original for comparison.
- Cost: about 0.1 to 0.25 s per processed texture, at scenery loading. The 12 last enlarged textures are kept (5.6 MB with mipmaps).

Measurements (outline roughness in radians of turning per texel, numerical simulation of the textures):

| Scenery | Before | After | Change | Area |
|---|---|---|---|---|
| pl | 0.487 | 0.301 | -38% | +0.04% |
| mt | 0.264 | 0.181 | -32% | -0.03% |
| wd | 0.800 | 0.566 | -29% | -0.36% |
| po | 0.467 | 0.316 | -32% | -0.03% |
| sd | 0.380 | 0.232 | -39% | -0.05% |
| se | 0.140 | 0.067 | -52% | +0.02% |

GL before/after screenshots at 2560x1380 (size of Sylfried's screen), MSAA 0 and 4 (llvmpipe accepts x4, "msaa réel 4"), on pl, mt, wd, po, sd, se. The difference map shows that only the silhouettes change.

Visual: the staircase steps of the mountain, the firs, the ferns and the tufts disappear, and so does the dark fringe. The fine tips are kept. At MSAA 0, the one-pixel steps remain (hard cut), which are no longer texel steps.

Tests: tools/test_scenery_outlines.py (8 tests). They verify the straightened staircase, no worsened slope, a visible one-texel tip, the area, the color under the transparent, the interior, the choice of textures, and the 140 real sceneries (area within 1.5%).

Comparison with the original Unity material: not done. The `fld_atest` textures are those of the cache and the port's shader already filters them like the original. The smoothing is an addition of the port, not a copy of Unity.

## Point 3. Dusk and sunrise in battle: DONE (proof and safety, cea04cb)

Established on the real engine:
- The world time is `StageStatus+0xcc` (0 to 3391, it advances while walking). `WorldLocation::setCurrentTimeZone` derives the zone from it:

| Time | Zone |
|---|---|
| 0-127 | zone 1 |
| 128-1983 | zone 2 |
| 1984-2239 | zone 3 |
| 2240-3263 | zone 4 |
| 3264-3391 | zone 1 |

- `StageStatus::getBtlMapName` (0x1a4580) replaces the final letter of the scenery by the table "d n d e n" indexed by the zone: zones 1 and 4 → `_n`, zone 2 → `_d`, zone 3 → `_e`.
- Encounters forced at times 64, 1000, 1984, 2239, 2240, 3300 → `btl_pl_n`, `_d`, `_e`, `_e`, `_n`, `_n`.
- **The evening exists**: scenery `_e`, orange tones baked into the asset, requested by the engine, and the viewer already displays it. The 6 world sceneries each have `_d`, `_e`, `_n`.
- **The dawn does not exist** as a scenery: the start and end of the night (zone 1) reuse `_n`.
- Dark world (`Global::getFieldType() == 2`): tables `btl_*_dk` without a time letter.
- In battle the engine sends neither a tint (packet 33) nor a background color (packet 8, `UnitySetMapBackColor`). `getBattleMapBackColor` and `MenuAPI::setBattleBackDrop` are not called. The color of the moment is baked into the asset (vertex colors and textures): the evening is redder, the night darker and bluer.
- `assets/param/param_map_battle.dat` lists the battle sceneries (128 lines of 16 bytes: 3 bytes of background color in 5 bits + name). The viewer keeps its background color computed by `_battle_background`.
- GL screenshots of the variants (pl d, e, n, dk; wd e; mt n; po e; se e): correct rendering, orange evening, blue night, purple dark world.

Code added, for safety: `data.fallback_sceneries()`, used in `window._load_map` for the `btl*` names. If the engine requests a variant absent from the data, the closest one is taken. Example: `btlcc1_n` does not exist, we take `_e` then `_d`. Before, the scenery was empty. I could not find out whether the game actually requests this case.

Tests: tools/test_battle_scenery_time_of_day.py. It covers the real engine (6 times, no packet 33 nor 8), the assets (`DQ_CACHE`) and the fallback sceneries.

## Point 4. Critical hit effect: EXISTS and is DRAWN, nothing was missing (7260542)

Established on the real engine (critical forced on the hero by a Unicorn hook at 0x1a81dc, which sets `kaishinFlag_` = LIB+0x25c6ed; `[acteur+8]` = 0 for the hero, 1 for the monsters, which draw `rand(0x20)==0`). Comparison with a normal hit:
- A second effect model, **5344** (slot 3, 17 frames), is loaded in addition to the 5303 of the normal hit.
- Sound effects: 400, 402, 412 in normal, plus 407 and 0 in critical. `SE0407.akb` exists in the data; SE0000 does not exist.
- Damage 8 → 26 (11 → 27 on another measurement), plus the text "Coup critique !".
- No packet 34 (`cmd_screen_effect`), no message window shake, no flash: screen effects 3, 5 and 6 have nothing to do with criticals.

GL visual proof: a normal hit only displays the orange burst. A critical adds a white ball then a star of sparks (model 5344). Sylfried therefore did see the effect.

Code: `sound.py` now ignores sound effect 0 (one line). Before, "SE0000 illisible" was written at every critical. Test: tools/test_critical_hit.py.

## Files touched outside my scope (to report to the other agents)
- `window.py`: `_speed_factor`, `_loop`, `_do_battle_step`, `_terrain_step` (area shared with the "camera" agent, outside mouse, full screen and camera); `_load_map` and `_purge_outlines` (new), plus an import.
- `pause.py`: **a single line**, the help of "Vitesse de combat" (area of the "ui" agent).
- `engine.py` (battle transition windows), `settings.py` (scrolling codes), `data.py` (+11 lines) and `sound.py` (+1 line).
- `tools/test_pause_pages.py` line 138: `('combat', 0)`.

Merge pitfalls:
- The `window.py` hunks (`_loop` / `_do_battle_step`) may overlap those of the "camera" agent.
- `sound.py` may be modified by the "death jingle" agent.
- The maps cache is `carte10_` (unchanged).

## Notes ready to paste into docs/ (not written into docs/)

**technical-notes-dq4-port**
- Battle transitions: `State.battle_transition()` = cascade effect (BATTLE_EFFECT_FRAMES = 57, status word bit 1), loading wait, `transition_guard` of 8 frames, fades marked "combat" (`fd['combat']`). 12-frame windows at the entry (packet 0 bit 8) and at the return (part 0xd → 0xe). The viewer plays at 1.0 there with no exception.
- `OptionStatus.battleSpeed` (g_Option+5): 0, 1, 2, 3 = wait of 12, 22, 32, 42 frames between messages; 4 = manual. Auto speeds: code 0.
- Battle scenery: `getBtlMapName` (0x1a4580), table "d n d e n" indexed by the time zone (`StageStatus+0xc8`); zone derived from `StageStatus+0xcc` (thresholds 128, 1984, 2240, 3264, 3392) by `WorldLocation::setCurrentTimeZone` (0x1c6fb0). No dawn scenery. No tint nor background sent in battle. `param_map_battle.dat`: table of the sceneries with 3 bytes of background color in 5 bits.
- Critical hit: `BaseAction::kaishinFlag_` (LIB+0x25c6ed, GOT 0x23df78); `checkActorKaishin` 0x1a8098; exit at 0x1a81dc. Packets: model 5344 (slot 3, 17 frames), SE 407 and 0, no packet 34.
- Battle driving test: hook `BattleRoot::setupMonster` + `Encount+0x34/0x44` (a weak monster, id 3).

**viewer-notes-dq4-pc**
- Battle scenery outlines: `scenery_outlines.py` (alpha x4 by EPX and blur, color extension); disabled by `DQ_SANS_CONTOURS=1`; limits: textures with binary alpha of 128 px and more.
- Missing scenery: `fallback_sceneries`.

## Not verified or limits
- Windows and real GPU: everything is in llvmpipe (xvfb). MSAA 0 and 4 tested in Mesa's software, not on Sylfried's card.
- Real time measured on a shared 2-core machine, noisy (the proof of point 1 is in engine frames).
- Turn with a spell not measured (point 5).
- The background color of `param_map_battle.dat`: how Unity reads it is not determined; the viewer keeps its computation.
- Whether the game requests `btlcc1_n` and the variants `btl_mt_dk`, `btl_sd_dk`, `btl_se_dk`: unknown (the data does not have these `_dk`). The safety net covers `_d`, `_e`, `_n`.
- With MSAA 0, the edge keeps one-pixel steps (hard alpha test).
- The forced critical is a test hook; in the game it remains drawn randomly by the engine.
- To be observed in the game: the smoothness of the auto turns (point 5), the disappearance of the black fringe on his screen.

Useful screenshots and scripts (outside the repository):
- /tmp/cb45/captures/: c_pl_mont_m4.png, c_pl_pins_m4.png, c_pl_pin_zoom.png (MSAA 0 and 4, before/after), c_wd.png, diff_pl.png, mos_variantes_d_e_n_dk.png, mont_fx_crit1.png, mont_fx_normal_vs_critique.png
- /tmp/cb45/dec_btl_*_m{0,4}_{avant,apres}.png (2560x1380) and /tmp/cb45/var_btl_*_m4_apres.png
- /tmp/cb45/gl_cb.py, gl_sceneries.py, run_gl.sh, run_gl2.sh, run_tests.sh
- Caches: /tmp/cb45/cache (carte10_btl*)

---

## Agent "sprites" (a9dec662e83175ee7) — 2026-11-02 21:29

REPORT batch 45 "sprites" (worktree /home/claude/wt45-sprites, branch agent45-sprites, base 84b3f22). Clean `git status`. Three commits, one per point:
- 6f5d678 Lying pose of the characters (packets 16 / 17 / 18)
- 6ba5342 Test: the hero and the companions lie down through the same packets 16 as the NPCs (real engine)
- 08f7a18 Random encounters: (1 + a) / 2 per real second at accelerated walking
Files of my area: dq4_pc/lying_pose.py, dq4_pc/encounters.py, tools/test_lying_pose.py, tools/test_encounters.py, tools/simulate_encounters.py (all new).
Files outside my area, minimal changes:
- engine.py: packets 16/17/18 in State.apply, and the encounters hook.
- window.py: lying branch in the sprite loop, and one line in `_loop` (`self.engine.walking_speed = 1.0 if self._battle_clock() else f`).
- pause.py: a help sentence for "Vitesse de marche": "Rencontres aléatoires par seconde : (1 + x) / 2 fois plus (x2 : 1,5 fois, x4 : 2,5 fois)". To be coordinated with the "ui" agent.
No setting modified, so nothing to migrate. pyflakes clean on my files: 2 warnings remain in window.py (dims, sel) and 3 in pause.py (R, yp, mh), all already in the base.
Tests passed: test_lying_pose (20), test_encounters (9, of which 4 on the real engine), test_pause_pages, test_*_settings, test_game_priority, test_casino_bestiary, test_battle_speed, test_town_camera, test_maps_npcs, test_map_items, test_savestate_fixes.

=== POINT 1: lying NPC drawn standing ===
ESTABLISHED
- Cause: the viewer ignored packets 16, 17 and 18. The castle soldier (map taf1) receives `0x0c000508` (packet 16) and `[1040, 1863]` (packet 17).
- Read from the engine disassembly and the IL2CPP:
  - Packet 16: bit 0x100 = lying, bit 0x200 = stood up, bit 0x400 = direction (`SetSleepDir`), angle = (d & 0xffff) / -182.0444 + 180, quadrant = bits 14-15.
  - Packet 17: height of the lying body = 0.3104 if the offset is 0, otherwise offset × 1.6 / 8192 (here 0.3639).
  - Packet 18: sprite sheet number.
  - Lying mesh: same rectangle as the panel (0.48 × 0.64), but flat. The `Custom/CharaSleep` shader projects the sprite in top view, full size, without foreshortening, rotated by the sleep angle and the camera. The depth is that of the flat body (+0.1). Offset `s_lieOffset` according to the quadrant. The shadow is pushed 64 below the ground: it is not drawn.
- The only non-vertical path of `Chara` is the lying pose: the IL2CPP dump only has SetSleepPose, SetSleepDir and lieBillboard as rotation API. There is therefore nothing else to compose with the edge correction.
- Composition with the edge correction: a lying character has its own path (`PC.vertices`) and never goes through `_town_panel`. The latter only corrects standing panels, and nothing is forced to vertical.
- Before / after on taf1 (frames 120 and 200):
  - The soldier is lying, head to the right, quad 77.6 × 58.2 px, without foreshortening.
  - The hero's screen corners are identical before / after.
  - The image difference is limited to the soldier (bbox 903,378 to 971,451). Height and tilt of the standing NPCs are therefore unchanged, to the pixel.
  - Other camera yaws (DQ_LACET 40, -70, 180): same shape in top view, width / height ratio constant at 0.75 (0.48 / 0.64), orientation that follows the camera.
- Generalization by sprite slot:
  - mlb1a (lying hero, packets 0x500 / 0x0c000400 / 0x08000401 observed in the audit): before / after screenshot draws the lying hero, difference bbox limited to the hero, standing NPCs identical to the pixel. Montage: /tmp/sp45/mlb1a_avant_apres.png.
  - Real engine: `TownPartyDraw::setSleep(true / false)` (script `cmd_set_player_sleep`) sends 0x08000500 and 0x08000501 for the hero and the companion, then 0x200 and 0x201 on waking. State marks them as lying / stood up (automatic test `test_group_lies_down...`).
  - Same mechanism for `cmd_character_action_sleep` (NPC, 0x509 on mlm2f1): the code is per slot.
- Images to look at: /tmp/m_sp_taf1_{base,ap}_b200.png, /tmp/sp45/crop_{base,ap}.png (zoom), /tmp/sp45/yaws.png (3 yaws), /tmp/m_sp_mlb1a_{base,ap}_b600.png.
NOT VERIFIED
- GL rendering of a lying companion or of a bed that covers a body (z-buffer): the depth is verified in geometry (tests), not in a screenshot.
- The case of the separate shadow (`ombre_sep`) was not seen in a screenshot.
- mlm2f1 (NPC 0x509): packet decoded and tested, no GL screenshot.
- The in-game triggers (inn, sick person) were not played: only the maps taf1 and mlb1a and the engine forcing.

=== POINT 2: day / night cycle (question only, nothing changed) ===
ANSWER: the cycle follows neither real time nor the engine clock, but the distance walked on the world map. It advances by +2 per engine step where the hero's position changes; when stopped, in a menu or in battle, it does not move.
ESTABLISHED (code)
- World time = `g_Stage+0xcc`, cycle 0xd40 = 3392, zones at the marks 0x80 / 0x7c0 / 0x8c0 / 0xcc0.
- It only advances through `FieldStage::ChangeTime(0)` (+2), called from `FieldPlayerDoku::checkDokuDamage+0x38` when the position has changed. `g_Game+4` is only the play time. Towns have time zones fixed by script.
- Packet 33 (scenery color, `WorldLocation::calcPaletteRate`) is only emitted when the palette changes: 24 packets in 900 walking frames, 0 in 120 motionless frames. On the viewer side, `State.tint` = last received value, without smoothing nor clock (map_tint.py, `_scenery_tint`).
ESTABLISHED (engine measurement)
- Step-by-step trace on the world map: +2 per walked step, 0 when stopped.
- A full cycle = 3392 units = 1696 walked steps (engine: 1698 steps, exact return to 640).
MEASUREMENT IN REAL SECONDS of a full cycle
- Nominal clock: real `battle_speed.advance_time`, 60 frames per second, simulated clock: x1 = 56.57 s, x3 = 18.87 s (ratio 3.00).
- Real GL viewer, real clock, software xvfb on a loaded machine (robot in a corridor without an entrance, encounters disabled):
  - x1: 60.11 s (28.3 steps / s);
  - x3: 31.21 s (54.4 steps / s). The engine throughput caps out on this machine: the nominal would be 90 steps / s. The real duration of a cycle = 1698 steps ÷ real steps per second.
- Effect of each setting: accelerated walking and the accelerator speed up the cycle in proportion. Fast battles have no effect. Menus and messages freeze it.

=== POINT 3: random encounters (1 + a) / 2 ===
ESTABLISHED (game mechanism)
- At each step, `CommonWalkDamage::checkWalk` calls `Encount::execWalk` (if `encountFlag_` = 1). Every 16 steps, `execWalk` launches `Encount::exec` (5 times if [+0x2c] ≠ 0), which calls `CountDown::exec` (0x1f454c): the counter [Encount+0x134] loses 2 × [+0x144].
- Trigger when the counter becomes negative; counter drawn at each `Encount::setup`: 0x1e00 + table[rand(31)].
- The game counts steps and not time: a times more steps per second = a times more encounters per second.
- Implementation:
  - `encounters.factor_per_step(a) = (1 + a) / (2 a)` if a > 1, otherwise 1.
  - Unicorn hook on `str w8, [x0]` of `CountDown::exec` (+0xc): the engine's counter loss is multiplied by this factor, with fractions carried over. It is not an additional random draw.
  - The counter draw and the distribution of monster groups are not touched.
  - At x1, `Engine.walking_speed` ≤ 1: the hook does nothing, loss identical to the game (tested and simulated).
  - A counter that is already negative never goes back up.
- `a` = walking factor of `_speed_factor()` = walking speed × accelerator when it is held (up to 8). It is 1 in battle.
MEASUREMENT: simulation on the real engine, 24,000 steps per speed, seed 1, walking robot, tool `tools/simulate_encounters.py`
(`Encount::brew` neutralized to count the triggers, counter removed as on return from battle)
| Place | Speed | Encounters | Per step | Per step × a, relative to x1 | Expected | Counter loss applied / game |
|---|---|---|---|---|---|---|
| World map | x1 | 179 | 0.00746 | 1.00 | 1.00 | 1.0000 |
| World map | x2 | 133 | 0.00554 | 1.49 | 1.50 | 0.7500 |
| World map | x4 | 113 | 0.00471 | 2.53 | 2.50 | 0.6250 |
| Dungeon (dab1) | x1 | 157 | 0.00654 | 1.00 | 1.00 | 1.0000 |
| Dungeon (dab1) | x2 | 112 | 0.00467 | 1.43 | 1.50 | 0.7500 |
| Dungeon (dab1) | x4 | 93 | 0.00388 | 2.37 | 2.50 | 0.6250 |
Statistical uncertainty of about ±7 to 10%, deviations within the noise. The counter loss is exact, without randomness: 0.7500 and 0.6250.
- Towns: `encountFlag_` = 0 (read in caf1 and mak1f1) and the branch of `checkWalk` (0x1c4598) skips `execWalk`: no random encounters in town, so nothing to fix.
NOT VERIFIED / LIMITS
- No walking simulation in town: the hero did not move there in my test saves. The conclusion rests on the disassembly and the flag's value.
- The hook was not seen in the GL viewer with real encounters (the GL measurements had encounters disabled). The `_loop` line runs without error during the GL x3 measurements.
- Assumed: I use the nominal factor `a`. If the machine cannot keep up the throughput (budget of 30 ms per displayed frame), the hero goes slower than a and the encounters per second fall a bit below (1 + a) / 2 (x3 measured at 54 steps / s instead of 90 on my loaded machine). The measured real throughput could be used if you wish.

=== NOTES TO INTEGRATE INTO docs/ (I did not touch docs/) ===
technical-notes-dq4-port.md:
1. Packets 16/17/18: exact decoding (see point 1), lying mesh + CharaSleep shader, `s_lieOffset` = (0, h, 0.2), (-0.1, h, 0), (0, h, -0.2), (0.1, h, 0), shadow pushed by 64. Only non-vertical sprite path = lying pose. Maps with packet 16 in the audit: mlb1a (hero + companion), mlm2f1 (NPC 9), taf1 (soldier). `cmd_set_player_sleep` → `TownPartyDraw::setSleep` → `DisplayCharacter::setSleep` → packet 16 per party slot; `cmd_character_action_sleep` → `TownCharacterManager::setSleepCharacter`.
2. Day / night: conclusion of point 2, figures, ChangeTime +2 per step, 1696 steps per cycle.
3. Encounters: mechanism and hook of `CountDown::exec` + 0xc, constants (0x1e00 + table, loss 2 × [+0x144], 16 steps, [+0x1c] state, `encountFlag_`), `Encount::setup` at map initialization (Field and Town).
viewer-notes-dq4-pc.md:
1. Sprites section: lying pose via `lying_pose.py`, without `_town_panel`, shadow hidden.
2. Walking speed section: `Engine.walking_speed` written by `_loop`, (1 + a) / 2 encounters per second, `tools/simulate_encounters.py` and `tools/test_encounters.py`, a help sentence in pause.py.
3. Tools: /tmp/sp45/measure_cycle.py and cycle_sim.py (cycle measurement robot) are not in the repository; to be taken up again if useful.

---
