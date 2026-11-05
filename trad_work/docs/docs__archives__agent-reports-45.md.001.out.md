# Final reports of the batch #45 agents (feedback of 2026-11-02 14:08)

Raw reports handed in by the ten subagents (SubagentHandback); the useful notes are already merged into `docs/notes-*.md` ("Avance #45" sections). The `/tmp/...` paths cited no longer exist: the reusable scripts are in `tools/research/`.

---

## Agent "ui" (ac56d17dae2fc2e50) — 2026-11-02 20:32

MISSION REPORT "ui" (#45, feedback of 14:08) — worktree /home/claude/wt45-ui, branch agent45-ui (base main 84b3f22), 9 commits, clean tree.

Legend: Established = verified by test or screenshot. Assumed = deduced without direct verification. Not verified = not tested.

## 1. Point by point

1. History: no more "Favoris" tab, "Favoris seulement" checkbox — DONE. Established.
 - Proof: `History.entries(tab, favorites_only)` (history.py), `toggle_filter` (ui_history.py:143), test_message_history.py (76 tests OK).
 - Keyboard (F), gamepad ("carte" action), mouse, star and wheel are covered by the `HistoryView` tests.
 - H cycles through messages, battles, closing: tested.
 - `test_pause_pages.py` (28) and `test_message_history.py` were adapted.
 - Screenshot: /tmp/ui45_hist_apres_f1.png.
 - Choice to be aware of: the filter is shared by both tabs and is not remembered between two openings.
 - Choice to be aware of: in the history, Tab serves as star/menu (consequence of point 6).

2. Name of the speaker in the in-game dialogue box — DONE. Established.
 - Protocol: MenuPort port 1, command 4. `[4,0]` = no name. `[4,1]` = the next port 1 packet carries the name, one integer per character (engine.py:260-284, 395).
 - IL2CPP source `MenuMessage.NoticeReceive`: the name exists only if `m_nowType == 0` (field window). The frame goes from frameData 192 to 191 (tab).
 - `m_who`: TextMesh at (-104.5, 4.0, BIAS_FONT_Y-104.0), characterSize 10, UpperCenter anchor (ui_menu.py:654-672). `SetVisible(false)` clears the name.
 - Real engine: the name "Roi Bastien" appears at frames 751, 772, 800, 854, 908, 962 and 998. It is sent again on every page.
 - Screenshot: /tmp/ui45_nom_dialogue_apres.png. Mobile reference: /tmp/specs/img45/ecran2_mobile_dialogue_nom_Angus.jpg. The geometry matches to within 1 px.
 - No invented name: the name comes only from the game's packet. It is never displayed for type 1 to 3 windows (battle, etc.), in accordance with the original code.
 - Tests: `tools/test_dialogue_name.py`, 21 tests (protocol, window, real frames 191/192).
 - Assumed: the other types of message windows behave as the IL2CPP code describes (name only in type 0). I only observed type 0 in the game.

3. Same name cartouche in the "Dialogues" tab of the history — DONE. Established.
 - The history draws the game's real frame 191/192 via `MessageWindow`, so the rendering is identical to the game's.
 - Without a name: rendering unchanged (frame 192, no tab).
 - Screenshots with name / without name: /tmp/ui45_hist_apres_d1.png, d2, d3, as well as the "before" versions.

4. Two text scrolling options in a section under "Vitesses" — DONE, with a discrepancy to be confirmed. Established.
 - DISCREPANCY: Sylfried said « menu Affichage » (EN: "Display menu"). I placed the "Défilement du texte" section in "Commandes", under "Vitesses", because the "Vitesses" section is in "Commandes" and not in "Affichage". It is up to him to confirm.
 - If "Affichage" is really wanted, it is enough to move the call to `_text_scroll()` (pause.py:420) to the "Affichage" page.
 - Commit 8a8db96.

5. "Jeu" becomes "Triches", right under "Commandes" — DONE. Established.
 - pause.py:227 (root menu entry), 431 and 1082 (title). Commit ca8d109.

6. Default keys of the Menu = Enter + Tab — DONE. Established.
 - settings.py:9 (`'menu': ['RETURN', 'TAB']`), `OLD_MENU` (line 14), migration `touches_v: 5`.
 - A settings.json that still had the old default (Enter alone) switches to Enter + Tab. A customization is kept.
 - Tab conflicts verified and ↺ restores both keys: `tools/test_menu_key.py`, 15 tests OK. Commit 8ac08b5.

7. History window and entries = real 3-line dialogue box — DONE. Established for the geometry, Assumed for the rendering on a real GPU.
 - `class Box` (ui_history.py:45): width 452, height 126, tab 246×32, line step 28, text margin, font and cartouche. The dimensions are read from the real layout (frameData 191/192) with a fallback to the measured values.
 - Scale = H/800 × 1.12, the same as the in-game box (`window.UI_ZOOM`, tested).
 - Fixed frame identical for 1, 2 or 3 lines. Beyond 3 lines, an additional page is created with a "p/n" indicator (`paginate`, ui_history.py:88).
 - Battles use the same frame.
 - Positions measured on a screenshot of the game: text 11-12 px from the edge, first baseline 31 px from the top.
 - Before/after screenshots with 1, 2 and 3 lines: /tmp/ui45_hist_{avant,apres}_{d1,d2,d3}.png for "Dialogues", /tmp/ui45_hist_{avant,apres}_{c1,c2}.png for "Combats", /tmp/ui45_hist_apres_d2_1080.png and /tmp/ui45_hist_apres_d2_small.png for other sizes.
 - Layout tests updated: `TestBox` class of test_message_history.py. Commit 888dada.

8. Group subheadings of the "Interface à modifier" list and battle speed button — DONE. Established.
 - a) Group subheadings: dull golden gray (146,140,112) with a rule (72,69,54), at 0.76 of the font size (pause.py:21-25). The bright gold is now only the current value. Before/after screenshot: /tmp/ui45_liste_{avant,apres}_haut.png.
 - b) The speed button (`hud_mobile.BATTLE`) leaves "Boutons et croix de l'écran". It has its own entry "Combat : bouton de vitesse", first of the "Combat" group. Screenshot: /tmp/ui45_liste_{avant,apres}_combat.png.
 - Own settings: visible (`bouton_vitesse`), size (0.5 to 2.0 in steps of 0.05, `bouton_vitesse_taille`), position (`bouton_vitesse_pos`). A "Replacer sous la boîte de combat" button restores the default anchoring.
 - Opacity: NOT DONE. No editor interface has an opacity setting. Estimate: about 20 lines (add an alpha to `Render.plate` and to `hud_mobile.border`).
 - Position: meaningful. The button is anchored under the bottom box as long as `bouton_vitesse_pos` is empty, then freely movable.
 - Migration: `Settings.migrate_speed_button` (settings.py:236). The visibility and position of an old settings.json are kept. The size is kept only if the button had been positioned, because the anchored plate ignored it before.
 - Tests: `test_interface_settings.py` (22, including `SpeedButtonMigration` and `test_speed_button_alone`), `test_pause_pages.py` (`Headings`, `InterfaceEntries`), `test_battle_speed.py` (fake J adapted). Commits cccc029 (subheadings) then b13224b (button).

## 2. Fixes per commit (most recent to oldest)

- 888dada History: fixed 3-line dialogue boxes, frame and speaker name tab from the game.
- b13224b Editor: "Combat : bouton de vitesse" becomes its own interface.
- cccc029 Editor: group subheadings in dull golden gray.
- 10a4fa5 Dialogues: speaker name in the tab (command 4 of port 1, frame 191).
- 8ac08b5 Keys: Menu = Enter + Tab (migration).
- a1a0bf3 History tests: fake game of the Pause menu expecting the "Défilement du texte" section.
- ca8d109 Pause: "Jeu" becomes "Triches".
- 8a8db96 Pause: text scrolling in "Commandes", under "Vitesses".
- 0a32321 History: "Favoris seulement" checkbox.

Final tests (xvfb): test_message_history 76 OK, test_dialogue_name 21 OK, test_pause_pages 28 OK, test_interface_settings 22 OK, test_battle_speed 42 OK (1 skip: `test_same_battle_at_all_speeds` requires DQ_APK and DQ_SAVES, skip present before my work), test_menu_key 15 OK, test_entries 37 OK. pyflakes: only the known warnings.

## 3. Notes ready to paste into docs/

**Protocol of the speaker's name (port 1 of the MenuPort).** Command 4 of port 1: `[4,0]` = no name; `[4,1]` announces a name, carried by the next port 1 packet (one integer per character). The game sends the name again on every page (observed: "Roi Bastien"). IL2CPP source `MenuMessage.NoticeReceive`: the name exists only if `m_nowType == 0` (field window). The frame then goes from frameData 192 (base 452×126, x -223..229, z -251..-125) to 191 (same base plus a 246×32 tab above). `m_who` is a TextMesh at (-104.5, 4.0, BIAS_FONT_Y-104.0), characterSize 10, anchor 1 (UpperCenter), alignment 1. BIAS_FONT_Y = `hdr['lang']['dy']` = 20. `SetVisible(false)` clears the name. PC side: `Interface.msg['qui']` (engine.py), `MessageWindow.select_language(typ, y, feed, who)` (ui_menu.py). The editor preview deliberately stays without a tab.

**Standard dialogue box and history.** In-game scale = H/800 × `UI_ZOOM` (1.12); at 720p, s = 1.008. Measurements on a screenshot of the game: text 11 px from the left edge of the frame, first baseline 31 px below the top edge, line step 28 units, 1 px of font = 1.09 units. The history (`ui_history.Box`) uses these values, read from the real layout with a fallback to the measurements. A fixed frame serves for 1, 2 or 3 lines. Beyond 3 lines, an additional page is created ("p/n"). Battles use the same frame.

**Interface editor.** The group subheadings of the drop-down list are in dull golden gray (146,140,112) at 0.76 of the size; gold is reserved for the current value. "Combat : bouton de vitesse" is its own interface (visible, size 0.5 to 2.0, free position or anchored under the bottom box), separate from "Boutons et croix de l'écran". Keys: `bouton_vitesse`, `bouton_vitesse_taille`, `bouton_vitesse_pos`, migrated from `boutons_pos['combat']`.

**Settings.** `'menu': ['RETURN', 'TAB']` by default (touches_v 5). The Pause menu has a "Triches" page (formerly "Jeu") under "Commandes". The "Défilement du texte" section is in "Commandes", under "Vitesses".

**Finding UI-1 (harmless).** In pyglet, `K.RETURN == K.ENTER` and `symbol_string` returns 'ENTER', so `reg.action_of(K.RETURN)` is None. The game reads the keys via `codes()`, so no effect was observed.

## 4. Not verified

- Windows and real screen: everything was done under xvfb/Linux, nothing on a real GPU nor on a real monitor.
- The filled history and the drop-down list were not run end to end in the real engine. My three queued runs (hnew1, ifavant, ifapres) were canceled to free the xvfb lock, which was too congested.
- The screenshots of the history and of the list come from a bench outside the engine (`/tmp/ui45_off/render_hist.py` and `render_list.py`) that uses the real `Render`, the real `Pause` and the real `HistoryView`.
- Only the screenshot of the name in the dialogue comes from the real engine, via the patched APK.
- The name was only observed in the game for window type 0 (Assumed for the other types).
- A screenshot of the game with the history open in the three window sizes was only taken for 720p, 1080p and a small window, via the bench outside the engine.

## 5. Files touched (15, +1012/-197)

- My files: dq4_pc/history.py, ui_history.py, pause.py, settings.py; tools/test_message_history.py, test_pause_pages.py, test_interface_settings.py, test_menu_key.py; tools/test_dialogue_name.py (new); README.md.
- Out of scope, minimal changes:
 - dq4_pc/engine.py (12 lines): reading the name on port 1 and reset in the SetVisible hook.
 - dq4_pc/ui_menu.py (44 lines): `MessageWindow` class (frame 191, "qui" node, `extent_x`, `rects`).
 - dq4_pc/window.py (8 lines): `_update_message` passes `m.get('qui', '')`, plus 3 comments/docstrings.
 - dq4_pc/hud_mobile.py (46 lines): speed button removed from `EDITOR_NAMES`, addition of `SPEED_EDITOR_NAMES`, `editor_names()`, `scale_factor(name_str)`, own position and visibility.
 - tools/test_battle_speed.py (12 lines): fake J and drag test.
 - I did not touch `battle_speed.py`, `inputs.py`, the FR patch files (APK, *.mpt) nor the saves.

## 6. Merge pitfalls

- ui_menu.py: the "text alignment" agent is working on the text alignment in the `MessageWindow` area (≈ lines 654-720). My additions are contiguous blocks (constants `BORDER_WITH_NAME`, `WHO_POS`, `WHO_SIZE`, `select_language(..., who)`, `extent_x`, `rects`). Probable conflict: the "texte" node and `extent()`. To re-read after the merge: `extent()` uses `self._base['vtx']` when `with_name`.
- window.py: a single functional line (`_update_message`, around line 1542) plus 3 comments. Possible conflict with the camera/screen agent if their changes touch these lines.
- hud_mobile.py and battle_speed.py: the "combat" agent may touch the speed button. `hud_mobile.BUTTONS` still contains BATTLE, but `EDITOR_NAMES` no longer has it. `hud_mobile.anchor()` returns None if `bouton_vitesse_pos` is set.
- settings.py: `INTERFACE_KEYS` is checked by `test_interface_settings.py` (`OTHER` list). Any new key must be classified there.
- pause.py: `INTERFACE_GROUPS` and `OWN_INTERFACES`; if another agent adds an interface, add it to both and to `WINDOW_NAMES`.
- The worktree is clean: nothing forgotten in /home/claude/wt45-ui. No push, no branch change, no PR.

## 7. Useful screenshots (absolute paths)

- /tmp/ui45_nom_dialogue_apres.png — in-game dialogue with "Roi Bastien" tab
- /tmp/ui45_dialogue_sans_nom.png — dialogue without a name (frame 192 unchanged)
- /tmp/specs/img45/ecran2_mobile_dialogue_nom_Angus.jpg — mobile reference
- /tmp/ui45_hist_avant_d1.png, d2, d3 and /tmp/ui45_hist_apres_d1.png, d2, d3 — "Dialogues" with 1, 2, 3 lines
- /tmp/ui45_hist_avant_c1.png, c2 and /tmp/ui45_hist_apres_c1.png, c2 — "Combats"
- /tmp/ui45_hist_avant_f1.png and /tmp/ui45_hist_apres_f1.png — "Favoris seulement" filter
- /tmp/ui45_hist_apres_d2_1080.png, /tmp/ui45_hist_apres_d2_small.png — other window sizes
- /tmp/ui45_liste_avant_haut.png, /tmp/ui45_liste_apres_haut.png — group subheadings (top of the list)
- /tmp/ui45_liste_avant_combat.png, /tmp/ui45_liste_apres_combat.png — "Combat" group with "Combat : bouton de vitesse"

## 8. Decisions to be confirmed by Sylfried

- "Défilement du texte" section: "Commandes" (done) or "Affichage" (requested).
- "Favoris" filter shared by both tabs, not remembered.
- No opacity setting for the speed button (no editor interface has one; about 20 lines if wanted).
- Name tab hidden when the name is empty and never displayed for battle windows (types 1 to 3).

---

## Agent "effet" (a6d50dea86708b3b9) — 2026-11-02 20:42

MISSION REPORT "effet" (prefix EF) — worktree /home/claude/wt45-effet, branch agent45-effet (base 84b3f22), 2 commits, clean tree (empty git status), no push.

== SUMMARY ==
The green beam is not the church: it is the beam of the healing tile (map object `kifk01a`). Cause of the « tourne de ~5° puis revient » (EN: "turns about 5° then comes back"): the object's rotation motion (FPMV, 800/60 s) and its mesh sequence (FSQD, 84/60 s) shared ONE clock in the viewer, the sequence's, which looped at 84. The rotation therefore never exceeded 84/800 of a turn (~37°, ~5° of visible swing) before returning to the start. Fixed: one clock per animation, like the engine (FldObject.fld_motion_update). HP/MP healing: done by the engine, the viewer does not get involved.

== BY MISSION POINT ==
1. Where the beam is (map) — DONE, Established for the maps. Object `kifk01a` in cmf1c (center -0.01; -0.03), dmb2 (-0.86; 12.47) and tab1a (0.0; 3.5). The ring on the ground (animated palette `tz_kifkyk1`, 24 keys cyan→green) also exists in za1f1. Sylfried's screenshot (blue niche) looks like cmf1c (blue panels on the wall): Assumed, not proven (dmb2/tab1a not rendered, xvfb queue saturated).
2. How the game activates it — DONE, Established (disassembly + engine test). Surface floor of type 4 (FldCollision::getSurfaceByType / TownStageManager::getHitSurfaceIdByType(4)) → TownActionWalk::checkCureFloor (0x1d6728) → TownPlayerManager::setCureFloor (0x1df284) → PartyStatus::recovery() + TownPlayerEtc::setupCureFloorEffect (SE 0x469 = 1129, setLock) then updateCureFloorEffect (fadeOutWhite 20, fadeIn 20, SE 0x1f5 = 501, unlock). The visual (`kifk01a` + ring) is scenery: it triggers nothing.
3. HP/MP healed on entry — DONE, Established. Engine only (Engine.start_town cmf1c, save 1, hero teleported onto the ring after closing the opening message): HP 1→47, 1→35, MP 0→30 as soon as entering, white fade 20/20 frames, SE 1129 then 501. The viewer does not intervene (it only replays the engine's packets): nothing to fix on that side. Test pitfall: the message "Quelle joie de vous revoir, Ragnar !" locks the player until it has been closed.
4. Root cause of the oscillation — DONE, Established. Hypotheses ruled out with proof: (a) quaternion slerp: no, `pmv_func` (RVA 0xCD94B8) = localRotation = rotateXZY(Euler interpolated per component) and the viewer was already doing Euler per component; (b) modulo: no, the counter's loop is correct; (c) WrapMode.Loop slope: no, FPMV is not a Unity AnimationCurve; (d) rotation order: no (rotate_xzy already exact, chests test #43 intact); (e) every other key: no, keys read 0/180/360; (f) engine frames vs real time: no (STEP = 2 per 30 Hz game frame, unit = 1/60 s). Real culprit: shared clock. Measurement (real map cmf1c, top view of a beam vertex over 800 frames): BEFORE angle min/max 0 to 36.9° (back and forth, period 42 frames); AFTER 0 to 720° (2 turns in 800 frames, one turn = 400 frames = 13.3 s).
5. Fix and generalization — DONE (see commits). Statistics: 96 map objects have sequence + motion, of which 57 with different durations (torches, birds, waterfalls, eyebrows, beams): all now have two independent clocks. Common animations (SetCommonAnimation): same, one clock per clip. fbx.py: player loop (modulo the duration) and Hermite curves already correct; battle_effect.py has no animated rotation (grep). The 17 loadable ImdChara models have 114 rotation curves, no sign inversion nor jump > 120° between keys; the other models (Custom/Effect0 shader, non-skinned meshes, ~29) are not loaded by the viewer: out of scope.
6. Unit tests — DONE. Interpolation: 0→360°, 0/90/180/270/360, negative angles, loop (2nd turn = 1st), no shortest path (0→270 goes through 135), per component, hold on the last key, start delay/delay between turns, two independent clocks, migration of an old state, real maps cmf1c/dmb2/tab1a + all the continuous animations of all the maps. Results: tools/test_map_items.py 35 tests OK (15 existing unchanged, including chests/doors/drawers); tools/test_fbx_anim.py 9 OK; test_map_textures, test_battle_speed, test_root_scenery, test_map_tint, test_maps_npcs OK. Verified that the new tests FAIL on the earlier code (test_a_full_turn_despite_the_short_sequence on an assertion; the fbx blending tests as well). pyflakes clean on the 4 touched files.
7. Before/after screenshots — PARTIAL. Done for cmf1c only (dmb2 and tab1a not rendered: the shared xvfb queue had more than 15 minutes of waiting per rendering, I canceled those two so as not to block the other agents). See files. Honest limit: the beam has 6 filaments (60° symmetry), so screenshots spaced 100 frames apart (= quarter turn, i.e. 30° modulo 60°) look alike; the strong proof is the angle graph, not the static screenshots. The screenshots also differ by the torches/flames (which had the same clock defect).
8. Non-regression — Established for what was tested: title dragon (c1018, ev01): simple poses bit-for-bit identical between the old and the new fbx.py; real cross-fades of the dragon (Take 002 looping toward 001/003): 0 different poses out of 4000; chests/doors/drawers: existing tests pass.

== COMMITS ==
- f6dd216 EF1: the healing beam finally rotates a full turn (one clock per object animation) — dq4_pc/map_objects.py (about +95/-33: `_clock`, `_advance`, `_migrate_auto`; `_init_seed`, `tick`, `_place`, `_src_seq`, `common_anim`, `restore`; states `tmot`/`tseq`) and tools/test_map_items.py (+221).
- 8d8b9ef EF2: fbx.py, cross-fade between two clips: blending of rotations on the same side of the sphere — dq4_pc/fbx.py (5 lines in `local`) + tools/test_fbx_anim.py (new, 117 lines). DEFENSIVE: q and -q are the same rotation, the weighted average of a CrossFade canceled them or made a half turn; the sign is aligned on the first pose. No known visible defect before; 224 poses out of 1890 (cross-fades between arbitrary instants of the dragon, which do not happen in the game) changed, 0 of the real cross-fades. Separated from EF1 so that it can be discarded without touching the main fix.
Files out of scope: none (window.py, sprites, battle, camera, etc. not touched). Compatibility: the snapshots saved before the fix (a single clock, flat `auto` entries, reloaded by window.py line ~969 via `restore(..., objets_auto)`) are migrated by `_migrate_auto` (tested synthetically only).

== FILES / SCREENSHOTS ==
- Before/after cmf1c (2 rows x 4 frames 150/250/350/450, cropped): /tmp/ef/avant_apres_cmf1c.png; sources: /tmp/m_efav_cmf1c_b{150,250,350,450}.png (before) and /tmp/m_efap_cmf1c_b{150,250,350,450}.png (after); old zoom: /tmp/ef/avant_cmf1c_zoom.png
- Top-view graph + angle curve over 2 turns (before: 0-37°; after: 0-720°): /tmp/ef/avant_apres_vue_dessus.png (script /tmp/ef/plot_avant_apres.py)
- Analysis scripts: /tmp/ef/ (scan_double.py = 96/57 objects, sim_kifk.py, scan_quat.py, scan_fondu.py, cmp_fbx.py, test_soin.py = healing on the engine)

== NOTES READY TO PASTE INTO docs/ ==
Healing beam (healing tile) and map object animations
- The green beam "that heals HP/MP" is the map object `kifk01a` (maps cmf1c, dmb2, tab1a) with a ring on the ground with an animated palette `tz_kifkyk1` (also in za1f1). It is purely decorative. The game effect comes from the floor surface of type 4: TownActionWalk::checkCureFloor (0x1d6728) → TownPlayerManager::setCureFloor (0x1df284) → PartyStatus::recovery() (HP and MP to the maximum) + setupCureFloorEffect (SE 1129, lock) / updateCureFloorEffect (white fade 20, fade-in 20, SE 501, unlock). Verified on the engine (cmf1c): HP 1→47 / 1→35, MP 0→30 on entering the ring. The viewer must do nothing more than replay the packets.
- Original semantics of the object animations (FldObject.fld_motion_update, RVA 0xCD69DC): each FLD_MOTION (FPMV motion) and each mesh sequence (FSQD) has ITS OWN clock: cur_frame (+0x2c), end_frame (+0x30), repeat_num (+0x24), start_delay (+0x26), repeat_delay (+0x28). Step per game frame = 2 (unit 1/60 s). During a delay the first key is applied and the delay is decremented; otherwise we interpolate then cur += step; when cur > end: repeat_num is decremented if it is ≥ 1; if it is 0 the last key is held, otherwise cur = overshoot and start_delay = repeat_delay. Rotation: pmv_func (0xCD94B8) = localRotation = rotateXZY(Euler linearly interpolated per component), no quaternion nor shortest path (so 0→360° really rotates). c_pmv_func (0xCD96D8) for flag&4. Only known difference: during the delay the original keeps cur_frame, the viewer resets it to 0 (kept as is).
- Bug fixed (EF1): a single clock shared by motion/sequence. For `kifk01a`: sequence 84, rotation 0→180→360 over 800 → swing of ~37°. 96 map objects have sequence + motion, 57 with different durations.
- Hypotheses ruled out for « tourne de ~5° » (EN: "turns about 5°"): quaternion slerp, modulo, WrapMode.Loop slope, rotation order, every other key, engine frames/real time.
- fbx.py: Unity models, rotations as quaternions (`m_EulerCurves` empty in the 46 clips), Hermite per component then normalization (like Unity); loop = modulo the duration. CrossFade: blending on the same side of the sphere (EF2). Compressed clips not handled. Only the Custom/ImdChara models are drawn.

== NOT VERIFIED ==
- Windows and real GPU (Xvfb/Mesa renderings only).
- Renderings of dmb2 and tab1a (the animation there is the same data, verified in test on the 3 real maps, but no screenshot).
- Exact map of Sylfried's screenshot (cmf1c Assumed).
- Origin of the cross-shaped stars/sparks around the beam (particles, out of mission scope).
- Material animations (FSRA) and event animations (FEAN, packet 6): not replayed by the viewer, not touched.
- Migration of an old snapshot on a real viewer save (synthetic test only).
- No information from user memory was used; nothing new to note there.

---
