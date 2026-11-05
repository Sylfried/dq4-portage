## Agent a26ba55965f699b65 — 2026-11-02 03:21

REPORT "options" (worktree /home/claude/wt-options, branch agent-options, base 08f5785). Clean tree. 1 commit: 41b3ee8 (topic A). Topic B: no commit (fix attempt reverted, see below).

=== A. The game takes precedence over the player's settings ===
Code: new dependency-free module dq4_pc/game_priority.py (effective_value(player_setting, game_value=None), effective_factor, letters_per_frame, fade_duration). Three real fixes: walking, zoom, script fades. The text was already correct in DQ4: I only ran it through the pure function.

ESTABLISHED
- Text: DQ4 has no script command and no write of the speed word (MSG_SPEED 0x2523b0) outside ui_MsgSetup, which copies it from the per-window-type table (types 0,1,2,5 = 1; 3,4 = 100). The hook at ui_MsgLoop+0x128 already replaced only the standard speed (4 letters/frame); it now goes through letters_per_frame, same behavior. Engine test: writing the word as 2 (as a script would), the duration is identical (15 frames) for 0.5 / 4 / 16 / 4000 letters/frame; without that, the setting takes effect (140 frames at 0.5, 11 at 16). test_text_scrolling.py passes again unchanged (24 frames at 4.0; battle waits 12/22/32/42).
- Battle message scrolling (battleSpeed g_Option+5): written only by the "Paramètres" window and when a save is loaded; the cases where the game blocks auto-advance (disableAutoFeed, setDisableCursor) are separate flags that the setting does not touch. Unchanged.
- Walking x1 to x4 + accelerator: until now _speed_factor sped up the engine clock as soon as a direction was held, even during a scene with no message. Measured Global.Flag: free exploration = 0x38 (town), 0x28 (world map); game scene = 0x3c (bit 4 = player lock) with no message (83 frames in save 2, prologue: 0x1c/0x1d throughout the prologue); fade = bit 1. Now factor 1.0 if Flag & (1|4) (constants ENGINE.FADE_FLAG, ENGINE.PLAYER_LOCKED_FLAG).
- Fades ("Vitesse de transition", x2 by default): the script commands fade_in / fade_out (__cmd_fade_in::initialize 0x21b3c0, __cmd_fade_out::initialize 0x21b43c) supply their duration (save 2: fade_out 30 frames at frame 6, fade_in 60 at frame 385) and themselves wait for that number of frames (isEnd counts the frames). Shortening the fade therefore only left the screen black for longer. Hook in Engine._fade_hooks: packet 9 receives the bit 16 mark (PJ.SCRIPT_FADE_MARK) when UnitySetFade (0x17e120) is called from these two functions; State._fade does not shorten these fades. Engine fades (map changes: 45, 30, 60 frames) are still shortened; colored / white fades never. Measured at x4: script 30 → 30, 60 → 60; engine 30 → 8, 45 → 11, 60 → 15.
- Camera: manual rotation / tilt and camera speed are already neutralized by cam_bloquee (TownCamera lock or rotation forbidden); "caméra centrée" already subject to cam_jeu / cam_free. Unchanged.
- Tests: tools/test_game_priority.py (12 tests, OK: pure rules, _speed_factor on a fake object, zoom, engine with --apk/--saves/--slot/--slot-fondu 2), test_sound_text_settings.py (+1 test); test_town_camera, test_pause_pages, test_interface_settings, test_window_mode, test_interface_panel, test_sound_mixing OK; xvfb window smoke test OK (RG=/tmp/rg_opt_sm.json, walking x3). pyflakes: only the known warnings.

ASSUMED
- Zoom (camera distance, wheel): effective_factor(zoom, e.cam_free) → no zoom during a free scene camera (position, angles, field of view set by the script). During a travelling (cam_jeu), the game sets only the target: the zoom is kept.
- The script fade recognized = only fade_in / fade_out; I assume that the player does not want these fades to be shortened.

NOT VERIFIED
- DQ5 / Nimzo: no DQ5 engine. A script that set the standard speed exactly (word 1) would be taken for the default; a memory-write hook on the word would then be needed.
- No cam_free scene observed in my traces (8 maps): the zoom fix is tested only on a fake object.
- Window loop with a direction held during the prologue: covered by a unit test + flag probe, not by a capture.
- Not handled: the chapter title fade (Global::fadeInBlack(60), called by cmd_event_chapter_title, address 0x18da7c) is still shortened (script command, but not via fade_in/fade_out). Also, the "common zoom" normalization HERO_FRAC overwrites the distance / fov set by script outside cam_free (a viewer choice, not a player setting): not touched.

TABLE A.1 (setting → can the game set it? → handling)
- Text speed → DQ4: no (per-window-type table); detected by the word ≠ standard → already respected; pure rule + tests.
- "Messages en combat" (defilement_force / combat) → not by script ("Paramètres" + save); auto-advance flags take precedence by construction → unchanged.
- "Vitesse de marche" + accelerator (key vitesse_accel) → yes (scenes: lock 4, fade 1) → FIXED (factor 1.0).
- Camera speed / camera accelerator → yes (TownCamera lock, rotation forbidden) → already neutralized (cam_bloquee).
- Camera distance / wheel → yes (free scene camera) → FIXED (neutral in cam_free; cam_jeu: zoom kept, assumed).
- "Caméra centrée" → yes (cam_jeu, cam_free) → already takes precedence for the game.
- Camera angle / yaw → yes (lock) → already neutralized.
- "Vitesse de transition" → yes (script fade_in / fade_out) → FIXED (packet 9 mark).
- Volumes, sound switches → no: packets 35-37 carry only the identifier; file volume and the game's "volume" option already multiplied → N/A.
- Brightness, sharpness, vignette, MSAA, rendering scale, smoothing, sprites, window mode, resolution, damage size, edge correction → no equivalent parameter on the game side (brightness is a final pass after the game's screen effects) → N/A.
- Buttons / D-pad / windows hidden or moved → player's display choice; the game already hides by PLAYER_LOCK / GUI_LOCK (hud_mobile.visible_ones) → N/A.
- Keys → N/A.
Setting of the "combat" agent touched by my inventory: vitesse_accel, via _speed_factor (I read the key, not the label: the rename to "Multiplicateur de l'accélérateur" has no effect on my code).

=== B. « Le nom de Ragnar est trop bas » (EN: "Ragnar's name is too low") ===
Opinion: the impression is justified but slight; I changed nothing.
ESTABLISHED
- 1280x720 capture (/tmp/c_opt_av_230.png, current rendering unchanged): inside of the banner y 30 to 48 (center 39); capitals y 35 to 46 (center 40.5), i.e. 1.5 px below center (≈ 2.3 px at 1080p); top margin 5 px, baseline 3 px from the separator, tail of the g at 0-1 px (it touches). Consistent with your capture /tmp/specs/img43/s4_nom_ragnar_combat.png; the "Ragnar" tab of the command window (s5) looks properly centered.
- Type 29: name = TextMesh anchor 1 (UpperCenter, cs 9.3925, ls 0.8013, z 385.5); HP/MP/Lv. lines = anchors 0 and 2 (Upper, ls 1.258, z 359). All anchored at the top: base0 = zp − ascent, independent of lineSpacing, hence the same formula for the name and for HP/MP/Lv. (which line up well with their gauges).
- Attempt at a global recentering ("glyphs centered in their line cell" in Window._text): raises the name by 2 px but LOWERS HP/MP/Lv. by ~1.5 px (the digits touch the gauges). Regression → reverted. Comparison: /tmp/c_opt_cmp_plaque.png (left = current rendering kept, right = rejected attempt); full frame: /tmp/c_opt_av_230.png (current) and /tmp/c_opt_ap_230.png (attempt); other images /tmp/c_opt_av_{170,185,200,215}.png and /tmp/c_opt_ap_*.
ASSUMED
- The offset comes from the data (z 385.5 + dy bias) and not from a viewer error: the original would have the name just as low. To be confirmed with a phone capture of the plate.
NOT VERIFIED
- The exact TextMesh formula in libunity for the bitmap font (Middle anchors: N steps or (N-1) steps + one line, ≈ 1 px difference, concerns the type 32 tabs, not this name).
- If you still want to raise it: a targeted shift of the type 29 plate texts by ≈ 1.5 px (720p), arbitrary choice to be validated.

=== Doc notes to merge (nothing written in docs/) ===
- viewer-notes: section "Game priority over the player's settings": principle (setting = default value, the game takes precedence when it sets the value), table A.1, pure rules of game_priority.py.
- technical-notes: Global.Flag in practice (free 0x38 town / 0x28 world map, scene 0x3c, fade bit 1: 0x39 / 0x3d, battle with bit 4 set); UnitySetFade 0x17e120 writes [9, v] and sets bit 0; __cmd_fade_*::initialize call Global::fadeOutBlack (0x17d600) / fadeIn (0x17dfec) with duration = (arg + 1) >> 1 and background plane via [Global+0xec]; engine fades seen: fadeOutBlack(45) at 0x15357c, fadeInBlack(30) at 0x18d9f0, fadeInBlack(60) at 0x18da7c; duration = bits 0-10 of v, viewer mark = bit 16.
- Unicorn pitfall: a hook added after a block has been translated does not fire; install them in Engine.__init__ before the steps (like _text_hooks) and call ctl_flush_tb().
- Help texts of the "Commandes" page (not touched), to be completed by whoever merges: "Vitesse de marche" → add "les scènes et les fondus du jeu gardent leur rythme"; "Vitesse de transition" → "sauf les fondus qu'un script du jeu fixe lui-même".

=== Merge pitfalls ===
- window.py: _speed_factor (+1 line after the pad() test, docstring); the "combat" agent probably touches it there: if the factor is extended to battle, do NOT take over my lock test (bit 4 is set in battle: flags 0x2d / 0x6e observed). _town_camera: th_v /= PJ.effective_factor(self.zoom, e.cam_free); import game_priority as PJ added after import settings as RG.
- engine.py: import game_priority as PJ after import emu_core; *_FLAG constants near BATTLE_MANUAL; body of _vt in _text_hooks; new method _fade_hooks inserted before _option, called right after self._text_hooks() in __init__; State._fade (2 lines).
- pause.py and settings.py: not modified (no new option).
- Script fades are no longer shortened: captures or duration tests that relied on "x2 fades" in a scene with fade_out / fade_in change.

Files touched: dq4_pc/game_priority.py (new), dq4_pc/engine.py, dq4_pc/window.py, tools/test_game_priority.py (new), tools/test_sound_text_settings.py. dq4_pc/ui_menu.py: modified then restored (no difference from 08f5785).
Outside the repo (scratch): /tmp/run_opt.sh, /tmp/rg_options.json, /tmp/rg_opt_sm.json; probes in /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/ (sonde_verrou*.py, sonde_fondus*.py, sonde_marque.py). Nothing to remember about the user (no personal fact learned).

---

## Agent ad9be5b9dfd5bdfb2 — 2026-11-02 03:22

COVERAGE REPORT (audit agent, read-only). Full deliverable: /tmp/audit/coverage.md (7 sections + summary at the top, ~59 KB). Repo intact (empty git status in /home/claude/wt-audit), no commits. Writes only in /tmp/audit and /tmp/sv_audit_*.

SUMMARY
- ESTABLISHED: headless v2 sweep of 529 maps (90 frames, 123 s in total): 528 without a crash, 0 sprites without a sheet (the 93 ids exist in the datapack), 0 NPCs off the map (507 analyzable maps), 0 stuck fades. The engine→viewer flow is sound; the gaps are in what is ignored or never played.
- ESTABLISHED: 16 memory-write sites in the viewer (§4), none touches scenario, variable, gold, inventory or position. Only point to watch: g_Option+5 (battle scrolling) is written every frame when the option is forced, hence recorded in the game's saves (this last point: Assumed, not tried). The save originals are never opened for writing (engine.py:41,53).

MOST SERIOUS GAPS (with evidence)
1. Invisible poker (ESTABLISHED, GL): gl_poker_b330.png = black screen + windows; gl_pokerv_b330.png (same scene, display forced to "ville" by my launcher outside the repo) shows the 5 cards. Cause: guard `e.part == ENGINE.PART_TOWN` at window.py:2913; the casino is part 0xf, unknown to the viewer (engine.py:8-11 defines only 3, 0xc, 0xd, 0xe). The map ev04 has no ground or texture: everything is dynamic mesh (packets 21/22).
2. Slot machine unplayable with the keyboard (ESTABLISHED, GL): the keyboard (Up×3 + Enter) leaves the bet at 0 (gl_slotkb_b420.png), the mouse works (gl_slotms_b350.png: "Jetons" 497, reels). Cause: `_menu_input` (window.py:1597-1621) exposes only the gamepad buttons 0x10; ▲/▼ are 0x2/0x1 and the window has no engine grid. On the engine side, slot and poker are playable (bet 500→497, spins, stop, clean exit).
3. Bestiary (part 0x10, ESTABLISHED GL): list and text sheet OK, but the monster is not drawn and the church mak1f1 appears in its frame (gl_booksel_b330.png). The engine does send the mesh (packet 22), though. Forcing the part to town changes nothing (byte-for-byte identical capture): cause NOT found.
4. Packet 33 (map_color_rate) ignored: emitted on 171/529 maps at load (149 at (1.25;0.65;0.75), 20 `te*` at (1.3;0.7;0.55), caf1/ev02 animated). On the Unity side (cmd_map_color_rate, RVA 0xD14E44, disassembled) = Field.SetColor(r,g,b,1). Also carries the world map day/night (FieldStage::ChangeTime) and the swamp (FieldPlayerDoku). Exact visual effect: Assumed.
5. Packets ignored without a trace (ESTABLISHED, no branch in State.apply): 1, 6 (event animations, including the slot machine win), 16/17/18 (lying-down poses, inn; seen in mlb1a, mlm2f1, taf1), 27 (bypassed by memory read), 30 (balloon zoom), 33. Packet 13: sprite scale (bit 0x800) read then discarded (mlb1a 0.738, ev07 0.952: effect Assumed). Packet 34: only the value 4 is replayed.
6. Shops, bank, church (resurrection, saving), inn, arena, colosseum, boat, balloon, wagon, credits: UNKNOWN, never opened (no automated test reaches them; only type 12 opens at load). They go through script commands (cmd_menu_shop/save/colosseum/extra_shop/nene/hostage/present_exp/event_imuru, cmd_the_end). It is the largest zone with no information.

NOT VERIFIED (detail §6): gameplay of the points above (I tried to open a shop through the engine, abandoned: it needs the CommandWindow object or placing the hero in front of the merchant); real Windows/GPU rendering (everything is Mesa/xvfb); decoding of the 686 .akb (sound.py swallows 12 exceptions); full battles; world map day/night, balloon, boat; poker to the end; ev01 (crashes through startTown, Assumed launcher artifact since the title loads it); exact effect of UnityInitTouchFlag.

FOR THE SWEEP (§5): startTown(name) does NOT place the hero at the entrance (235 hero/party-member sprites at the inherited position (1.97 ; 0.047 ; 44.08) on 117 maps): to be resolved before level 2. Measured cost N1: 0.23 s/map (90 frames); estimated 600 frames ≈ 14 min in 1 process, ≈ 7 min in 2 (indexes 0-265 / 265-529). N2 (talking to every NPC) ≈ 25 min on 2 cores (estimated). N3 (GL captures in a single process, a single xvfb at a time) ≈ 35-55 min (estimated). Detection rules R1-R12 in §5.4.

NOTES TO MERGE INTO THE DOCS (§7): (a) the line "custom IBase classes not reproduced" in the technical notes is outdated, the 5 classes are ported (ui_menu.py:199-413); (b) packet 33 is not limited to mlb1a (technical-notes:233); (c) engine parts 0xf casino and 0x10 bestiary unknown to the viewer; setMinigame(0)=poker ev04, other=slot ev05; startBook ← TownMenuItemSelectCommand::menuUpdate; startSurechigai ← cmd_change_surechigai_part; (d) keyboard: gamepad buttons 0x2/0x1 inaccessible without a grid; (e) key word: field bit A only if arg2 == 0x100 exactly (NativeExec 0x17d3d8); (f) table of packets with statuses (§1).

User memory: nothing read or used.

FILES (all in /tmp/audit/): coverage.md; sweep.py + bal2_tout.json + analysis.py (sweep v2 and its analysis); paquets_raw.txt, menutypes3_raw.txt; probe_slot3.py, probe_slot4.py, probe_poker2.py, probe_poker3.py, probe_grid.py, probe_book.py, probe_book2.py; gl_casino.py + run_gl_casino.sh (GL launcher outside the repo, same locks as run_wt.sh); captures gl_poker_b330.png, gl_pokerv_b330.png, gl_slot_b330.png, gl_slotms_b350.png, gl_slotkb_b420.png, gl_book_b230.png, gl_booksel_b330.png; callgraph.py + cg.pkl; scales.py; feuilles_datapack.json. Temporary: /tmp/audit/cache_donnees (3 MB), /tmp/audit/rg_audit.json, /tmp/sv_audit_*.

---

## Agent aeab3de440c6b8a30 — 2026-11-02 04:29

FINAL REPORT, "combat" agent (worktree /home/claude/wt-combat, branch agent-combat, base 08f5785). Clean tree, 2 commits (Co-Authored-By and Claude-Session trailers present, nothing pushed):
- 42de0fd Battle speed ("Normal" / "Rapide" / "Très rapide") and rename to "Multiplicateur de l'accélérateur"
- 79341e7 Test replaying a battle from the real engine: damage numbers compared, adjustable number of steps

=== A. Rename ===
"Vitesse de l'accélérateur" becomes "Multiplicateur de l'accélérateur" everywhere in the code: line of the "Commandes" page, help text of the accelerator key, docstring of `_maj_camera`, comment of the setting, test_pause_pages (with an assertNotIn of the old label). The key `vitesse_accel` did not change.
Occurrences outside the code, to be updated (I touched nothing outside the code):
- README.md:41 (accelerator key, "speed adjustable from 1 to 2 in Commandes"): to be completed with the V key and the battle speed;
- docs/viewer-notes-dq4-pc.md:386 ("vitesse de l'accélérateur");
- docs/viewer-notes-dq4-pc.md:429 (same, and says that battles keep their speed: to be fixed).
Remaining in the code: settings.py:152, comment about the old "Multiplicateur de la course" (migration), kept on purpose.

=== B. Battle speed ===
Setting `vitesse_combat` ∈ {1, 2, 3}, default Normal (1.0). Labels "Normal" / "Rapide" / "Très rapide", never "x2".
- settings.py: key in DEFAULT, `BATTLE_SPEEDS`, `BATTLE_SPEED_NAMES`, `battle_notch` (invalid value, boolean, nan or text → Normal; out of bounds brought back to 1..3; the nearest, on a tie the fastest), `next_battle_speed` (cycle 1→2→3→1) and validation at load. New action `vit_combat` "Touche de vitesse des combats", default key V (free: no other action uses it, not in RESERVED). If an old file has already given V to another action, the new one has no key and the other keeps V. `vitesse_combat` is classed OUTSIDE_INTERFACE (test).
- pause.py `_entries_commands`: just below the accelerator lines (key, multiplier), line "Vitesse des combats" (same form as the x1 to x4 choices, original plates, darkening on hover, no yellow frame, golden arrow with the keyboard), then "Touche de vitesse des combats". None of this can be sped up by the accelerator. The help texts say "Sans effet en combat" for the accelerator.
- In battle, two commands: the key (cycle) and an on-screen button "Vitesse / Normal|Rapide|Très rapide" (the label yellow then orange when it is faster). Each change saves the setting; the "Commandes" page re-reads it. The button is integrated into hud_mobile: movable and hideable in the editor, "Rétablir cette interface" puts it back, default position in the left strip (column 0.4, row 8, between "Carte" and "Commandes"), checked at several resolutions (1280x720 to 3440x1440): to the left of the column of the game's windows, without covering another button. It sends nothing to the engine. It hides during the black wait screen of the scene and during fades to black, like the field buttons. The key also acts outside battle; if the button is not on screen, a brief message announces the value.
- Effect (battle_speed.py, pure logic, new): the original engine is not modified; in battle the viewer makes it do 1, 2 or 3 times as many 1/30 s steps per real second. The original loop of `Game._loop` was extracted into `VC.advance_time` (identical for walking: equivalence test against the old loop). Compute budget 30 ms per frame (FAST_STEP_BUDGET unchanged): if the steps do not fit, the game slows down instead of freezing the display. `VC.factor`: None outside battle, 1.0 when the engine is waiting for the player, otherwise 1..3.
- "In battle" = the engine's battle part (0xd), plus the start screen effect and the black wait screen of the scene (which only a battle lifts). Outside of that, back to x1 with no effect on walking (x1 to x4), which remains independent.
- Accelerator: excluded by construction (`VC.factor` has no parameter for it; the battle branch of `_speed_factor` comes before the walking logic). It neither applies nor stacks in battle. Written in the code (docstrings of battle_speed.py and of `_speed_factor`, comment of settings.py) and in the help texts of the "Commandes" page.
- Player waits not sped up: command menu, target choice, Yes/No (`eng.active_menu()`), message that shows the ▼ cursor ("Messages en combat" = "Manuel"). A step that opens a menu interrupts the burst of frames. Automatic messages ("Rapide"/"Moyen"/"Lent"): their counters are in engine frames, hence shortened by 2 to 3 times.
- Music and sound effects: sound.py is not modified; playback remains in real time (file duration, pitch, tempo unchanged). Only the trigger time of a sound effect follows the engine, and `VC.sounds_to_play` prevents launching the same sound effect twice (packet 35) in the same displayed frame.
- Everything the viewer animates in battle follows the engine clock (`engine.frames + alpha`): damage numbers, FBX, start effect, fades (`tick_fade`), plate shakes, message scrolling (written by the engine), monster animation. A single real clock remains in the battle interface: the blinking of the target arrow (ui_menu.py, 0.7 s), which is an input wait. A test verifies by code inspection that none of the battle drawing functions uses a real clock.

=== Functions touched (files shared with the other agents) ===
window.py: `import battle_speed as VC`; `on_key_press` (+1 line after `info`); `on_mouse_release` (HUD branch, 2 lines); `_maj_camera` (docstring only); `_loop` (the step block replaced by `VC.advance_time`); `_speed_factor` (+1 line at the top); new: attribute `_sfx_this_frame`, `_battle_clock`, `_wait_for_player`, `_do_battle_step`, `change_battle_speed`; `tick` (1 line: `sound.events(VC.sounds_to_play(...))`).
pause.py: `_entries_commands` (accel, speed_accel, new lines vit_cb and key_battle, docstring, help text of "Vitesse de marche") + 1 line in the dict `names` (`'Vitesse des combats'`).
settings.py: DEFAULT_KEYS, ACTIONS, DEFAULT, comment of `vitesse_accel`, `BATTLE_SPEEDS`, `BATTLE_SPEED_NAMES`, `battle_notch`, `next_battle_speed`, 1 line in the loading.
hud_mobile.py: constants (BATTLE, BUTTONS, EDITOR_NAMES with 5 elements, DEFAULT, CAPTION, DQ_PLATE), `battle_visible` (new), `under`, `visible_ones`, `draw_all`, `_texte_combat` (new).
New: dq4_pc/battle_speed.py, tools/test_battle_speed.py. Updated tests: test_pause_pages.py, test_interface_settings.py (`OUTSIDE_INTERFACE`, mask dicts with 'combat', `_shown_rects()` = 5).

=== Established (measured or verified) ===
- 39 tests in test_battle_speed.py (1 skipped = the engine replay, opt-in), plus test_pause_pages (16), test_interface_settings (12), test_town_camera, test_window_mode, test_interface_panel, test_sound_text_settings, test_sound_mixing: all OK. pyflakes: only the known warnings (sel, R, yp, mh).
- Launch: `python3 tools/test_battle_speed.py` (no display). Engine replay: `DQ_APK=<APK folder> DQ_SAVES=<saves> [DQ_PAS_MAX=3000] python3 tools/test_battle_speed.py EngineReplay` (about 30 s).
- Results identical to x1: same battle replayed with the real `VC.advance_time` loop at 1, 2 and 3. Over 3000 engine steps (100 s of battle), packets, messages, states and damage numbers are identical step by step; the damage values are 11, 11, 8, 8 at steps 158, 502, 681, 857. In the real window (DQ_TEMPS_REEL=1, same key script), the DQ_PKTALL logs of x1 and x3 are identical over 8405 lines (17909 steps, including walking and battle). The outcome does not depend on the speed: the engine is deterministic step by step.
- Duration of the same battle (1100 steps, harness at simulated 60 Hz): x1 36.7 s, x2 19.6 s, x3 14.0 s (input waits stay at normal speed, hence a bit less than exact x2 / x3).
- Real window, loaded Xvfb 640x360, scripted input every 6 steps: 300 engine steps in 10.0 s at x1 (30 steps/s), 5.7 s at x2 (52 steps/s), 4.2 s at x3 (72 steps/s).
- Cost of an engine step in battle on this machine (2 cores, load 3.4): mean 2.6 ms, median 1.6 ms, p95 7.7 ms, max 37.6 ms. The 30 ms budget is therefore rarely reached; simulation: budget cut only if a step exceeds ~30 ms (x3 then falls back to 60 steps/s, never below x2 at 60 Hz).
- V key in the real window (`--touches-test`): two presses give "Normal" → "Rapide" → "Très rapide", saved in the JSON. Click on the button: the setting changes and is saved.
- Captures (all in /tmp/captures_vitesse_combat/):
  - /tmp/captures_vitesse_combat/combat_bouton_normal.png
  - /tmp/captures_vitesse_combat/combat_bouton_rapide.png
  - /tmp/captures_vitesse_combat/combat_bouton_tres_rapide.png
  - /tmp/captures_vitesse_combat/combat_bouton_3_valeurs_agrandi.png (the three side by side, enlarged)
  - /tmp/captures_vitesse_combat/combat_touche_V_cycle_agrandi.png (cycle through the V key)
  - /tmp/captures_vitesse_combat/commandes_cle_vitesse_combats.png ("Commandes" page, new line and its key)
  - /tmp/captures_vitesse_combat/commandes_vitesse_combats_liste.png (cursor on the line, list open)
  - /tmp/captures_vitesse_combat/editeur_interface_bouton_combat.png (button in the interface editor)

=== Assumed (consistent with the code and the measurements, not observed by eye / by ear) ===
- Feel at 60 Hz on the user's PC: at x2 exactly one engine step per frame; at x3 alternating 1 / 2 steps per frame (1.5 on average), hence a possible slight lack of regularity in the animations at x3.
- Monster animations follow the accelerated clock only during the non-waiting phases; during input waits, they keep their normal idle animation (intended).
- Victory jingle: its duration stays real while the engine chains faster (end-of-battle delays are counted in engine frames). At x3, the next music may cut the fanfare before it ends. To be checked by ear.
- Shortening the automatic messages by 2 to 3 times reduces the reading time; to read at one's own pace, stay on "Manuel" (not sped up) or on "Normal".

=== Not verified ===
- Everything that plays on Windows and on the user's real screen (no Windows here), in particular the performance if the step budget is exceeded on a slower PC: the game slows down (x3 falls back toward x2) instead of freezing, but this is tested only by simulation.
- No listening test (music, sound effects, fanfare); only fake players verifying that the duration of a sound effect is the same at all speeds and that a duplicate within the frame is removed.
- The last victory message waits for a key without showing ▼: undetectable, so it is sped up (no consequence, the monsters have disappeared).

=== Choices to validate ===
Default key V; default position of the button (col 0.4, row 8); button tied to the global visibility "Afficher cette interface" (no separate option: the editor page is outside my scope); battle start effect and black loading screen counted as battle (sped up); key also active outside battle with a brief message; target arrow not sped up.

=== Doc notes to merge (docs/ not touched) ===
Section "#43 Battle speed" in docs/viewer-notes-dq4-pc.md: principle (engine steps multiplied, 30 ms budget, factor 1 during input waits), independence from the accelerator, what follows the engine clock and what stays real (target arrow, sounds), new setting and new V key, button integrated into the editor, tests and measurements above. Update lines 386 and 429 (new label, battles now have their own speed) and README.md:41.

=== Merge pitfalls (tested with `git merge-tree`, read-only) ===
- agent-entrees: CONFLICT in pause.py `_entries_commands`. Resolution: keep their `edit` line (help text "clic molette") and their `info` line, with my `accel` (help text "Multiplicateur de l'accélérateur … Sans effet en combat"), my renamed `speed_accel`, then `vit_cb` and `key_battle`. Check that `info` stays in the returned list.
- agent-fenetre2: CONFLICT in settings.py (loading): keep my line `vitesse_combat` and delete the line `correction_bords` that they remove.