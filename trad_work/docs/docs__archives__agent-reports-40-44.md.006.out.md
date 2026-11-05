## Agent aec9b0976be625290 — 2026-11-01 23:49

REPORT editeur2 (PR #42, points 10, 11 + dragging the floating panel)

Branch `agent-editeur2`, worktree /home/claude/wt-editeur2, base 345ba8f. A single commit: `fa3619e`. Clean tree. No push, `docs/` untouched.

## What is done

### Point 10: "Masquée" label for every hidden element
- **The D-pad has two separate options** under "Boutons et croix de l'écran":
  - "Afficher cette interface à l'écran" (`boutons`) hides Map, Commands, Chat and the D-pad together.
  - "Afficher la croix" (`croix`) hides the D-pad alone. This is the option the user calls « option pour la croix » (EN: "option for the D-pad").
- Before, only the whole interface was veiled and marked. A D-pad hidden alone was merely faded (alpha 0.35), with no word.
- Now `Pause._preview_elements()` returns, for each element shown, `(rect, hidden, masculine)`. It serves both the label and `_shown_rects()` (panel placement).
- The buttons stay tied to the global `boutons` setting. There is no button-by-button setting (decision by Sylfried in #37, « ça ira comme ça » (EN: "that'll do")). The Mode button belongs to the `MapButton` window and therefore follows `interface_masquees`.
- Gender agreement: "Masqué" for the 3 buttons, "Masquée" for the D-pad and the windows (constant `HIDDEN_WORDS`, easy to make invariant if the user prefers).
- The veil is drawn, then the label, then the yellow selection frame is redrawn on top: it stays identical, not covered by the veil.
- The label is fitted to the element's width: it fits in the small buttons (zoom `/tmp/ed2_masque_boutons_zoom.png`).
- In `hud_mobile._dpad`, the 0.35 alpha is removed: the common veil is enough, the D-pad is no longer darkened twice.
- Selectable: a hidden element can still be grabbed in the editor. Screenshot: a hidden button moved with the mouse (`/tmp/ed2_masques.png`, 2nd image).
- Sweep of the 53 windows with a temporary debug print, removed (`git diff` clean): all have a preview rectangle, all are veiled and marked when hidden. None falls back to `None`. Message and Yes / No checked in screenshots.

### Point 11: complete resets
**Inventory of the setting keys** (46 keys in `DEFAULT`, 9 affect the interface). The classification is in `settings.py`:
- `SCREEN_KEYS` = `boutons`, `croix`, `croix_taille`, `boutons_taille`, `boutons_pos`.
- `WINDOW_KEYS` = `interface_fenetres`, `interface_masquees`.
- `EDITOR_KEYS` = `grille_edition`, `boutons_aimant`.
- `DEFAULT_WINDOW` = (1.0, 0.0, 0.0): value of a window with no setting. It replaces the `[1.0, 0.0, 0.0]` and `default=1.0` / `0.0` copied in `pause.py` and `window.py`.
- Classified as non-interface: `infos` (F1, information lines), `taille_degats` (fixed value) and everything else (sound, display, keys, camera, speeds).

**Reset functions**, all built from `DEFAULT` (JSON copy, nothing copied over):
- `Settings.reset_interface(target)`:
  - `boutons`: all of `SCREEN_KEYS` comes back (display, sizes, positions, D-pad shown).
  - window or `msg`: its entry in `interface_fenetres` and `interface_masquees` comes back.
  - Only it changes. Neither the editor nor the other windows move.
- `Settings.reset_interfaces()`: all of `INTERFACE_KEYS`, hence also grid and snapping.
- `Pause._reset_this` and `Pause._reset_all` replace `_rien_ov` and `_remettre_boutons`. `_reset_all` also resets `pan_pos = None` (panel place for the session).
- `hud.remettre()` is deleted (no longer called).
- Tooltips added on the two "Rétablir" buttons.
- The result is immediate: the preview and the game re-read `reg` every frame.

**Test** `tools/test_interface_settings.py` (12 tests, OK):
- The test sets all the keys to non-default values, resets one interface (only it changes), then everything (everything returns to default, the rest intact).
- It checks the round trip through the file.
- It checks `Pause._entries_interface` with a dummy game.
- It checks `_preview_elements` (hidden or not, gender).
- **Pitfall**: `test_classification_complete` fails if a key is added to `DEFAULT` without being classified.

**Before / after screenshots** (starting state: `/tmp/rg_ed2_non_master.json`, sizes, positions, hidden D-pad, shifted windows):
- D-pad and buttons, preview: `/tmp/ed2_cette_boutons.png`.
- Menu window (`RootMenu`), preview: `/tmp/ed2_cette_menu.png`.
- Message, preview: `/tmp/ed2_cette_msg.png`.
- In game on the world map, with `--force-champ` (game HUD and menu reset without relaunching): `/tmp/ed2_cette_jeu.png`. The state before is `/tmp/ed2_jeu_av_sheet.png`.
- Message in game (church, slot 1), before / middle / after: `/tmp/ed2_msg_jeu.png`.
- "Rétablir toutes les interfaces": `/tmp/ed2_toutes.png`. The grid reappears, everything is default, the panel returns to its origin. The saved `settings.json` equals `DEFAULT` for the 9 keys.
- `Status` is not touched by "Rétablir cette interface" applied to `boutons`, `RootMenu` and `msg`: the saved file confirms it.

### Dragging the floating panel (extra point from the coordinator)
- **Cause established**: in `Pause.drag_to`, a movement of more than 8 px before 0.35 s set `annule = True`. Anyone who presses and drags right away (the normal case) moves nothing and folds nothing. Without waiting 0.35 s without moving, nothing worked.
- **Reproduced** with the harness (press, drag, release in under 0.35 s, `DQ_APPUI_LONG=5`): `/tmp/ed2_drag_av_sheet.png`, the panel does not move.
- **Fixed** in `pause.py` (`_press_bar`, `drag_to`, `release`, `do_update`). The `annule` key is deleted.
  - The panel follows the pointer as soon as it moves 8 px (`PRESS_TOLERANCE`) away from the press point. It then lifts (golden title, enlarged frame), without waiting.
  - A press held without moving for 0.35 s also lifts it, then it follows on the first movement.
  - A short press without movement (jolt of up to 8 px) folds or unfolds.
  - Double click resets the original position. **Behavior change**: the reset to the origin happens on release of the 2nd click, no longer on press. A 2nd press followed by a drag moves the panel.
- **Test** `tools/test_interface_panel.py`: 10 tests, press / drag / release sequences with a simulated clock and `Pause.do_update` every frame. It fails 3 times on the old code and passes on the new. It also checks that the position stays within the screen at 1280 x 720, 1920 x 1080 and 2560 x 1440.
- **Screenshots after**: 1280 x 720 `/tmp/ed2_drag_ap_sheet.png`, 1920 x 1080 `/tmp/ed2_drag1080_sheet.png`. In both, the panel follows the pointer, with the exact press offset.

## Established / Assumed / Not verified
- **Established** (read in the code or observed under xvfb with Mesa): everything above. The simulated events go through the same `Pause.click`, `Pause.drag_to` and `Pause.release` as `on_mouse_press`, `on_mouse_drag` and `on_mouse_release` of `Window` (which only relay them).
- **Assumed**: a real mouse under Windows sends the same sequence of pyglet events as the simulation, and a finger arrives as a mouse event. 8 px threshold: my choice.
- **Not verified**:
  - Real mouse under Windows (no Windows here), touch screen.
  - Does Sylfried like the choice of "Masqué" (buttons) versus "Masquée" (D-pad, windows)?
  - Message in game with a hidden window: code unchanged, not replayed.
  - The game option "Taille de la croix" (`g_pad_size`, in the save) is not touched: it is no longer accessible.
- **Not done / chosen**:
  - No button-by-button visibility.
  - "Rétablir toutes" does not change the interface chosen in the list, and only `pan_pos` is reset (not `folded`, inaccessible when the panel is folded).
  - No confirmation message (everything is visible right away).

## Files touched
- `dq4_pc/settings.py`: constants `SCREEN_TARGET`, `*_KEYS`, `DEFAULT_WINDOW`; methods `default`, `reset_interface`, `reset_interfaces`.
- `dq4_pc/pause.py`: see the zones below.
- `dq4_pc/window.py`: 3 lines (`preview_interface` and `_yesno_preview`: `RG.DEFAULT_WINDOW`).
- `dq4_pc/hud_mobile.py`: 2 lines (D-pad alpha, `remettre()` deleted). Out of scope, minimal.
- `tools/test_interface_settings.py` and `tools/test_interface_panel.py`: new.
- `pyflakes`: only the existing warnings (`R`, `yp`, `mh` in `pause.py`, `selected` in `window.py`).

## Merge pitfalls
- **`pause.py` constants**: my additions are `SELECTION_BORDER`, `HIDDEN_WORDS`, and the comments of `LONG_PRESS_DELAY` and `PRESS_TOLERANCE`. If pause2 adds a yellow-frame constant, do not duplicate it.
- **`pause.py` zones I modified**:
  - the header (constants, comment of `__init__`);
  - `_ov`, `_set_ov`, `_visible`, `_set_visible`, `_entries_interface` and the resets;
  - `do_update` (1 line);
  - `_press_bar`, `release`, `drag_to` (`pan_pressed` block);
  - `_preview_elements`, `_shown_rects`, `_preview` (end).
- **Zones I did not touch**: `_entries_display` (fenetre agent, its last lines touch my block) and `draw_all` (pause2). Possible context conflict but no overlap.
- **Keys added to `DEFAULT` by another agent** (window mode, etc.): `test_classification_complete` will fail until they are in `OUTSIDE_INTERFACE` of the test. This is intended.
- `Settings.default` is a static method, `RG.DEFAULT` remains the dict.
- The harness tests clicks at 1280 x 720 in pixels from the top-left; for another format, pass `--largeur` and `--hauteur` after the script's arguments (which takes precedence over the script's own).

## Notes to add to `docs/viewer-notes-dq4-pc.md` (section "Feedback from 23:24", interface editor)
- **"Masquée" label**: every element not shown in game is veiled (black at 150/255) and marked in the preview, with the yellow selection frame intact: either the whole interface hidden (buttons "Masqué", D-pad and windows "Masquée") or the D-pad alone ("Afficher la croix" = "Non"). `Pause._preview_elements()` gives rectangles, hidden state and gender. The D-pad is no longer faded: the veil is enough. The Map / Commands / Chat buttons share the global `boutons` setting; Mode follows the `MapButton` window. A hidden element can still be grabbed.
- **Resets**: "Rétablir cette interface" resets all of `SCREEN_KEYS` (display, sizes of the buttons and the D-pad, positions, D-pad shown) for "Boutons et croix de l'écran", or the window's entry in `interface_fenetres` and `interface_masquees` (size, position, display). Grid and snapping do not change. "Rétablir toutes les interfaces" also resets grid, snapping and the panel place (`pan_pos`). Everything comes from `DEFAULT` (`Settings.reset_interface` / `reset_interfaces`). A new setting key must be classified in `*_KEYS` or in `OUTSIDE_INTERFACE` of `tools/test_interface_settings.py`.
- **Floating panel**: dragging starts as soon as the pointer moves 8 px away from the press on the title bar (the old code canceled the gesture if you moved before 0.35 s: impossible to drag for anyone who did not wait). Short press = fold / unfold, held press = lift, double click = original position (on release). Test: `tools/test_interface_panel.py`.

---

## Agent a377ad026145bcbc1 — 2026-11-02 00:38

FINAL REPORT pause2 (points 4, 6, 7, 12) - worktree /home/claude/wt-pause2, branch agent-pause2, base main 345ba8f. Clean working tree (empty git status).

COMMITS (3, each with the two lines Co-Authored-By / Claude-Session)
- 7593b20 Pause: "Son" page (one line per sound), text scroll speed ("Messages en combat"), speeds x1 to x4, no more yellow frame (darkening on hover)
- 3d52d1f Pause: the pointer leaving the window makes the plates light up again (on_mouse_leave -> pause.output())
- c9e1250 Pre-game screens: no more yellow frame on hover ("Sauvegardes" screen, name entry, license). SEPARATE COMMIT because outside the scope of the Pause (pre_game.py, saves_screen.py, name_entry.py): to be set aside with `git revert c9e1250` or by skipping it at cherry-pick if the title screen agent touches these files. It also removes the `import hud_mobile as HM` that became useless in the first two (pyflakes).

FILES TOUCHED
dq4_pc/pause.py (+196/-), dq4_pc/window.py, dq4_pc/settings.py, dq4_pc/pre_game.py, dq4_pc/saves_screen.py, dq4_pc/name_entry.py, tools/test_sound_text_settings.py (modified), tools/test_pause_pages.py (new). Nothing in docs/. Original engine, FR patches and user saves not touched.

TESTS (all green): test_pause_pages.py 15 tests; test_sound_text_settings.py 7 tests (including 3 for migration); test_sound_mixing.py 12 tests. pyflakes: only 4 warnings already present on the base remain (pause.py variables R, yp, mh; window.py selected). test_text_scrolling.py requires --apk/--saves (not rerun, its logic was not modified).

POINT 4 - "SON" PAGE (Established, by screenshots + tests)
- No more sections. 5 lines: "General", "Musique", "Jingles et fanfares", "Bruitages", "Interface". Aligned columns: name | volume bar (yellow fill kept) | value in % | speaker button (mute) | round button (default).
- Keyboard: up/down = line, left/right = volume, Enter = mute/restore, Delete = default. Mouse: bar clickable and draggable, speaker and round buttons clickable, click on the value = type it (kept). The sounds keep playing while the page is open (a test sound effect is played when a volume is changed or a sound is restored).
- DECISION: the default button/key resets the volume to its default value AND restores the sound (cancels the mute). Button grayed when the line is already at default. Muted line: label and bar grayed, speaker crossed out by a red cross. Clicking next to the buttons on a line of the "Son" page does nothing (avoids muting by mistake).
- The mixing code is not modified: mute toggles the existing switches (musique_active, jingles_actifs, bruitages_actifs, interface_active; "General" = global mute).

POINTS 6 and 7 - TEXT (Established)
- Root entry, page title and titles[...]: "Vitesse de defilement du texte". No more sections. "Defilement automatique" deleted. "Vitesse du texte" first ("Normal (jeu)" becomes "Normal"), then "Messages en combat": "Rapide" / "Moyen" / "Lent" / "Manuel". The "Retablir le reglage du jeu" line is kept.
- CORRESPONDENCE ESTABLISHED in the original engine (OptionStatus.battleSpeed = g_Option+5; BattleAutoFeed::setMessageSpeed 0x201558): 0/1/2/3 -> wait of 12/22/32/42 frames, 4 -> -1 (manual, waits for a key), 5 -> DEBUG_WAIT. Game default = 2 (OptionStatus::initialize 0x1a344c). CHOSEN values: "Rapide" = 0, "Moyen" = 2 (original default), "Lent" = 3, "Manuel" = 4. The value 1 (possible in a save) is displayed "Moyen" (cran_defilement: 1 -> 2). So the choice 1 / 22 frames is not offered.
- Migration (settings.py): if 'defilement_combat' is absent and the old file has defilement_auto / defilement_vitesse: auto=False -> "Manuel" (4), otherwise the old speed is brought back to the nearest notch. The save's value is NOT overwritten as long as the user has not touched the menu: 'defilement_force' stays False (window.py: defilement_actuel() then reads game_options()[2]); "Retablir le reglage du jeu" puts defilement_force back to False. Unit tested (test_battle_scroll_migration, test_crans_du_defilement, test_choix_impose_la_valeur_puis_rien_tant_qu_on_ne_touche_pas).
- VERIFICATION IN REAL BATTLE (forced battle, Unicorn):
  * "Manuel" (4), slot 4: with 90 frames without a key the message stays on screen; Enter, Space and left click each make it advance, 3 frames after the press. Established.
  * Control "Rapide" (0), slot 4, log /tmp/p2_rapide.log: the messages pass by themselves after 12 to 18 frames; game_options goes from (4,4,4) to (4,4,0), so the setting is indeed written and effective. Some waiting messages (end of battle probably) still wait for a key even in "Rapide", and Enter / Space / click make them advance (3 frames). Established.
  * CAVEAT: the slot 4 save was already at battleSpeed 4. The direct switch 2 -> 4 in battle (slot 2 = start at the default value) could not be replayed: both launches on slot 2 displayed nothing before the 600 s timeout (cause not investigated, presumably waiting for a field state). It is the same call regler_defilement(code) as for 0, so I hold it as Assumed (not Established) in that direction.

POINT 12 - COMMANDES > VITESSES (Established unless noted)
- The "Vitesse de marche" / "de camera" / "de transition" drop-down lists: x1, x2, x3, x4 (no more sliders). "Vitesse de l'accelerateur" keeps its 1-2 slider (default 1.5).
- Migration: old values 0.5-2 brought back to the nearest x notch (int(v+0.5), floor x1, ceiling x4; invalid value or boolean -> default): 0.5->x1, 1->x1, 1.5->x2, 2->x2. Tested (test_speeds_to_x_migration).
- DEFAULTS: walking x1, camera x1, transition x2. DEVIATION FROM THE BRIEF: the brief said x1; I kept x2 for the transition because it was the already documented default (vitesse_fondu 2.0); changing it = one line in settings.py (DEFAULT['vitesse_fondu']).
- Walking x3 / x4: the engine has no structural limitation (fast walking = more engine steps per displayed frame, `_speed_factor` caps at 8.0). I added a time budget per frame for the fast steps (FAST_STEP_BUDGET = 30 ms, environment variable DQ_BUDGET_PAS): if the steps do not fit in 30 ms, the game slows down instead of freezing the display.
- MEASUREMENT (real clock, DQ_TEMPS_REEL=1, continuous walking, scratchpad script mesure_marche.py; 3 series, one of them without budget):
  * Window 400x225 (cheap rendering): x1 = 29.7-30.0 steps/s (x1.00); x2 = 49.9-51.5 (x1.66-1.72); x3 = 85.0-87.7 (x2.83-2.92); x4 = 111.6-115.1 (x3.72-3.84); x4 + accelerator x2 held = 202.5-217.0 (x6.75-7.23). With or without budget the results are equivalent here.
  * Window 1280x720 (Xvfb software rendering, 10-26 frames/s): x4 = 85 steps/s (x2.84), x4 + accelerator = 167 (x5.58). Measurements limited by the shared CPU of the sandbox (software rendering + other agents), not by the engine.
  * MAXIMUM STACKING: x4 (walking) x 2.0 (accelerator) = x8 theoretical (code cap) = 240 engine steps/s, i.e. about 0.85 s of CPU per second if a step costs ~3.5 ms: this saturates a slow PC, in which case the budget makes the game slow down. On this bench we reach x6.8-7.2 at best.
  * NOT VERIFIED: real performance on Windows (the user's GPU/CPU) at x4 and x8; encounter rate over a long walk at x3/x4 (reasoned: counted per engine step, hence per distance, not measured); transition fades x3/x4 on a real map change (reasoned: the fade duration is divided, 30 -> 8 frames at x4, <= 1 frame = immediate; not tested through a real transition). Camera: x4 with accelerator = 800 deg/s, stable (dt capped at 0.1 s, recentering by jump).

YELLOW FRAME (Established by screenshots and by a test on the code)
- Removed everywhere in the Pause: root, "Etats" (list, Yes/No windows), "Son", "Texte", "Commandes" (lines, drop-down lists, key slots, sliders), help, pagination buttons, default round button, red crosses, back button, drop-down list items. Rule: mouse = darkened plate ("enfonce" pattern shifted on a plate, color at 75% on an icon button), which lights up again when the pointer leaves (including when it leaves the window: on_mouse_leave -> pause.output()); keyboard = golden cursor (arrow) in front of the chosen line. The yellow fill of the sliders and (editor, not mine) the yellow element-selection rectangle are kept.
- On a sub-button (speaker, round button, cross, scroll arrows), only the sub-button darkens, not the line.
- A static test (test_no_more_yellow_border_in_page_code) checks that no "JAUNE if sel" remains in pause.py. The `outline` parameter of _plate is KEPT (the pre-game screens used it; no caller passes it any more in the modified code). Fallback HM.plate of hud_mobile.py not modified.
- NOT visually verified: the three pre-game screens of commit c9e1250 (pyflakes only; same _plate call as in the Pause). No "ecran Sauvegardes" folder ever captured by me.

USEFUL SCREENSHOTS (absolute, /tmp)
- BEFORE (yellow frame + tooltip): /tmp/m_p2_base1_b200.png ("Commandes", "Vitesse de camera" framed in yellow, sliders); other base: /tmp/m_p2_base1_b100.png
- AFTER "Son": /tmp/m_p2_s2_b190.png (5 lines, "General" and "Bruitages" muted, "Musique" at default grayed); /tmp/m_p2_a_b150.png ("Son" with hover and help); other series: /tmp/m_p2_a_b50.png /_b90 /_b110 /_b130
- AFTER "Texte": /tmp/m_p2_t1_b170.png (title "Vitesse de defilement du texte", "Messages en combat : Moyen", golden cursor); others: /tmp/m_p2_t1_b50.png /_b100 /_b120 /_b140
- AFTER "Commandes" (x1-x4, "Vitesses" section): /tmp/m_p2_c2_b170.png; series /tmp/m_p2_c2_b130.png /_b150 /_b190 /_b210 /_b230 /_b250; /tmp/m_p2_c1_b100.png /_b150 /_b200
- Yes/No windows: /tmp/m_p2_e1_b200.png ("Etats", "Supprimer l'etat 1 ?"); hover crop Yes / No / rest: /tmp/p2_pop_all.png (also /tmp/p2_pop180.png /p2_pop200.png /p2_pop220.png)
- Battle check log: /tmp/p2_rapide.log

NOTES FOR docs/ (to be written by the lead)
- Pause menu > "Son": one line per sound, columns name | bar | % | mute | default; keyboard up-down / left-right / Enter / Delete; default = volume AND sound restored.
- "Texte et defilement" becomes "Vitesse de defilement du texte". Messages in battle -> OptionStatus.battleSpeed: "Rapide" 0, "Moyen" 2 (original default), "Lent" 3, "Manuel" 4; 1 displays "Moyen"; setting not imposed as long as the user does not touch it (defilement_force). Setting keys: defilement_combat replaces defilement_auto and defilement_vitesse (automatic migration).
- "Commandes" > "Vitesses": x1-x4 (walking, camera, transition; default x1 x1 x2); accelerator 1-2 (default 1.5); maximum stacking x8; budget of 30 ms per frame (DQ_BUDGET_PAS).
- Interface rule: no more yellow frame on hover; darkened plate (mouse) + golden cursor (keyboard). Intended exceptions: yellow fill of the sliders, yellow element-selection rectangle in the interface editor.
- Tools: tools/test_pause_pages.py (new).

MERGE PITFALLS
- pause.py: the line drawing loop (the area where zones are reset to zero, computation of selected / anc, _plate call without outline), the pw width formula (+36 for 'son') and _validate/click/_line_helptext are the places most likely to clash with the changes of the fenetre / editeur2 agents; _entries_display, _entries_interface and the floating panel are NOT touched. A field n_f used `.get('fixe')`: fixed to `is True` (a 'fixe' lambda created a false gap after the first "Son" line).
- window.py: scroll block (defilement_actuel / regler_defilement / retablir_defilement / apply_scroll / _adopt_scroll), constant FAST_STEP_BUDGET after ENGINE_STEP, loop _loop (cuts at the budget), on_mouse_leave (hover_node = None + pause.output()).
- settings.py: DEFAULT (defilement_combat replaces defilement_auto/vitesse; speeds 1.0/1.0/2.0), BOUNDS (1,4), SOUND_TEXT_BOOLEANS without defilement_auto, new functions cran_defilement / notch_x and migration in the loader. If another agent adds keys, keep the order: migration before the BOUNDS loop.
- The settings file is rewritten by Pause.shutdown() at each test: copy /tmp/rg.json before each launch (no cross-pollution).
- Capture harness in THIS worktree: "~@x@y" is the mouse RELEASE; hover is "@x@y@2" (instead of ~). Another worktree may have a different syntax.
- c9e1250 is independent: set it aside if it conflicts with the title screen agent.

ESTABLISHED / ASSUMED / NOT VERIFIED
Established: layout and behavior of the "Son", "Texte", "Commandes" pages (screenshots + tests); battleSpeed correspondence (reading the original code); "Manuel" 4 in real battle (Enter, Space, click); "Rapide" 0 passes by itself in 12-18 frames; migrations (unit tests); no more yellow frame in the Pause (screenshots + static test); walking x2-x4 measured on the bench.
Assumed: transition 2 -> 4 in battle (same call as 0 -> ... but not replayed from the default value); fades x3/x4; encounter rate per distance; feel of walking x4 x accelerator.
Not verified: Windows (real GPU/CPU, speed x4/x8), audible rendering of mute and volumes on real speakers (the mixing tests check the values, not the sound), figures of the original Config window (1 to 5), appearance of the three pre-game screens modified by c9e1250.

DECISION POINTS TO BE VALIDATED BY THE USER
1) Transition default: x2 (existing) or x1 (brief)? 2) Does the "default" button of a "Son" line also restore the sound (current choice: yes)? 3) Are "Moyen" = 2 (game default) and "Lent" = 3 suitable, given that 1 (22 frames) is no longer offered?

---
