## 3. Draggable floating "Interface" window
- Long press (0.35 s, mouse; the finger is assumed to arrive as a mouse event): the panel lifts (enlarged frame, golden edging, golden title, truncated tooltip) and follows the pointer; moved by more than 8 px before the delay = canceled.
- Short press: fold / unfold (as before, Tab still works). When folded, the panel keeps its unfolded width (otherwise it runs away from under the pointer).
- Double click on the bar: return to the initial position computed for the chosen interface (top-right corner, otherwise a free corner; recomputed on each double click). Preserves the folded state.
- Always within the screen (clamp). Position remembered for the SESSION only (not saved, not tied to the interface; a new opening of the editor resets the automatic position).
- Test variables: `DQ_APPUI_LONG` (0.35) and `DQ_DOUBLE_CLIC` (0.40) in seconds.
Established by captures: lift + movement, fold, reset, unfolding by single click.

## Useful captures (absolute)
Before (code 1e87ca6): /tmp/m_avp_b100.png (page, reversed order: display option on the 1st line), /tmp/m_avp_b112.png, b126, b138, b150 (flat alphabetical list, "Aperçu d'objet" present). Contact sheet: /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/cmp_old_liste.png.
After: /tmp/m_ap1_b100.png (page), b112 / b124 / b136 / b148 / b160 (grouped list); before/after comparison: …/scratchpad/cmp_selecteur2.png and cmp_selecteur.png; tour of the 54 previews: …/scratchpad/tour_00.png to tour_04.png.
Per-interface display: …/scratchpad/opt1.png (buttons, D-pad, several interfaces), /tmp/m_mask1_b140.png ("Dialogues" hidden, "Masquée" label), in game …/scratchpad/hid1.png ("Argent" and "Chapitre" hidden, msg/YesNo/ChurchRoot moved, slot 1).
Floating panel: …/scratchpad/final_panneau.png (initial / long press / folded / double click, taken from the final commit), drag2.png, drag3.png.
Limit of the "before" captures in game: with the original code, the "Non" or "Oui" buttons give the same image in game on this slot (/tmp/m_avon_b172.png, /tmp/m_avoff_b172.png: message displayed, no visible HUD); the global scope of the old option is therefore established by the code, not by capture.

## Established / Assumed / Not verified
- Established (capture): page, grouped list, previews of the 54 entries, per-interface hiding in the editor and in game (slot 1: "Argent", "Chapitre", msg, Yes/No, ChurchRoot), panel gestures, settings migration (test script).
- Assumed: the finger (touch) arrives as mouse events in pyglet; the renamed labels (BCInfo = "Sauvegarde rapide" according to the notes; BattleIM = items and spells); an old `YesNo` setting saved by the old version is now read relative to the message (can shift an already adjusted Yes/No a little).
- Not verified: real battles with battle window settings; hidden window used with keyboard/mouse in a real game under Windows; "Statut du personnage" (types 13-17: the preview only shows the strip of the back button, usefulness of moving it alone not confirmed); frame rate: the editor runs at ~10 fps under xvfb, the delays were tested with the env variables.

## Merge traps (other agents on pause.py / window.py)
- pause.py: constants at the top (WINDOW_NAMES rewritten, INTERFACE_GROUPS, HEADER, WITHOUT_EDITING, DELAI_*), `__init__` (6 attributes pan_*/list_border), `_choice`/`_move_entries`/`_draw_entries`/`_entries_end` (subheadings), `_entries_interface` + `targets`/`_visible`/`_set_visible`, `draw_all` (panel placement and lifted frame), `click`/`release`/`drag_to`/`do_update`. If another agent adds a page or modifies `click`/`drag_to`/`do_update`, keep the `pan_pressed` test first in `drag_to`.
- window.py: `_draw_menus` (overrides loop, relative type 1, `mask` filters), `_zones` (returns [] if hidden), `preview_interface` (refactored into `_preview_window`).
- settings.py: DEFAULT (+`interface_masquees`) and cleanup loop in `Settings.__init__`.
- Commit footer: the brief gives `Claude-Session: …session_014GF7TVESqzjb1SFv4HoPvZ`, but the attribution provided by this turn's environment gives `…session_014GF7TUJhoy5Df7FLvSTYtw`; I used the latter (to be rewritten if you prefer the brief's identifier).

## Notes for the docs
- New key `interface_masquees` (names of Make_* windows or `msg`; buttons/D-pad handled by `boutons`). `REMOVED_WINDOWS` in settings.py; purge at load.
- Gestures of the "Interface" panel (long press = move, short = fold, double click = reset); non-persistent position; `DQ_APPUI_LONG`, `DQ_DOUBLE_CLIC`.
- Gesture test harness: `!x!y` (press), `^x^y` (drag), `~@x@y` (move), `@x@y` (click); held key = `+TOUCHE` / `-TOUCHE` (a RETURN/DOWN of several frames triggers the repeat at 0.4 s). The harness rewrites the `--reglages` file: always pass a copy of it.
- Yes/No relative to the message; hidden window = layout kept, neither drawn nor clickable; "Rétablir toutes" shows everything again.

---

## Agent ac00a9e82be6ce2bf — 2026-11-01 21:53

REPORT agent-texteson (worktree /home/claude/wt-texteson, branch agent-texteson, started from main 1e87ca6). Nothing pushed, no branch switch, /home/claude/dq4-portage not touched, saves read-only (tests in /tmp/sv_*), APK/*.mpt/docs/ not touched, engine .so not modified.

COMMITS (two-line footer, pyflakes OK: only the warnings already present on main remain):
- f101cc5 Engine: text speed + battle scrolling (hooks) + tools/test_texte_defilement.py
- 711593a Sound: categories, volumes, switches, listening during pause + tools/test_son_mixage.py
- 8f1197a Esc menu: "Son" page by categories, "Texte et défilement" page + settings.py + tools/test_reglages_son_texte.py

POINT 1: TEXT / SCROLLING — DONE
Decision: mixed. Text = viewer side (hook on the engine); battle scrolling = writing the value into the engine config (g_Option+5).
- "Texte et défilement" page (added to the root menu, one line): "Vitesse du texte" (7 notches: "Très lent", "Lent", "Assez lent", "Normal (jeu)", "Rapide", "Très rapide", "Instantané"); "Combats" section: "Défilement automatique" (switch), "Vitesse de défilement" (notches 1 to 4, grayed out if auto is off), "Rétablir le réglage du jeu". Defaults = behavior from before (nothing is imposed as long as nothing is touched).
- The label and the help text say "Combats seulement".
ESTABLISHED (read in the code + measured):
- The dialogue text is written at `vitesse x 4` letters per engine frame (30 Hz), speed = constant per window type (1 dialogues, 100 battle windows). It is NOT a game option. The hook replaces this number; at 4 it does nothing.
- The only game option that scrolls is OptionStatus.battleSpeed (g_Option+5, saved in each save), read by BattleAutoFeed: 0 to 3 = wait of 12/22/32/42 frames, 4 = by hand. Dialogues outside battle: never automatic (400 frames of waiting with code 0 or 2, measured).
- Measurements (engine frames, message opening -> end of page, 72 letters): 0.5 -> 140; 1 -> 73; 2 -> 40; 4 (default) -> 24; 8 -> 15; 16 -> 11; instant -> 8. Engine driven by hand without my hook: 24 as well (identical default). Battle waits: 12/22/32/42 for codes 0/1/2/3 (the other episodes = +5 or +6); code 4: no automatic passage, the message waits for A (tested).
- Via the Esc menu in the viewer (DQ_MSGDBG=1): "Lent" -> 74 frames, "Rapide" -> 16, "Instantané" -> 9, default 25. The menu does change g_Option+5 (4 -> 1; slot 1: 0 -> 4 via switch), and a click in the game's "Paramètres" window (notch 5 -> "Confirmer") while scrolling is imposed is adopted by the setting (g_Option = 4, imposed = 4).
- The "Divers" > game "Paramètres" window is called: "Menu Pause", "Volume musique", "Volume effets", "Vitesse texte" (5 notches 1..5, "Rapide" at the top, "Lent" at the bottom), "Taille de la croix", "Retour à l'écran titre". Its "Vitesse texte" = speed of BATTLE messages; notch 5 = code 4 = by hand (observed).
- Values of Sylfried's saves: battle speed 0, 2, 2, 4, 2 for slots 1..5; volumes 4/4 everywhere; new game: 2.
ASSUMED: durations in seconds (0.4/0.7/1.1/1.4 s) = frames / 30; names of the text notches ("Normal (jeu)" = 120 letters/s) chosen by me.
NOT VERIFIED: feel in a real game on a Windows PC; imposed speed written into the save that the game records (the imposed value is stored there; "Rétablir" gives back the game's value in memory, the already written save stays as is).

POINT 2: SOUND — DONE
"Son" page redone (same pattern: switches, 0-100% sliders, yellow frame depending on the device): "Général" ("Son" + "Volume général"), "Musique", "Jingles et fanfares", "Bruitages", "Interface" (switch + volume each). Applied immediately to the sounds in progress (music, jingle, sound effects already started). Music off = it runs silently and resumes at the right place; short sound effect off = not played; looping sound effect off = started at zero volume. On the "Son" page the sounds resume (game stopped) to hear the settings + test sound effect (SE 316 for sound effects, 300 for interface) when a volume is moved.
Categories (established by scanning the playSe/playBgm calls and the duration/loop of the AKBs): music (PlayBGM looping); jingles/fanfares (PlayBGM without loop, short <= 30 s, or requested with resume 0x1000|n); sound effects (PlaySE); interface = SE 300 to 304 (300 = Unity button + message page beep, 301, 304 established; 302/303 ASSUMED interface). No voice nor separate "ME" channel in Unity (only PlayBGM/PlaySE): no invented category.
Bonus: the music/effects volume options of the game's "Paramètres" window were IGNORED by the viewer; they are now applied ((index+1) x 0.2, like Unity) — default 4 so x1: no change as long as they are not touched. The exact conversion is deduced from the Unity code (not heard).
NOT VERIFIED: real listening (tests in PYGLET_AUDIO=silent); exact content of the "jingles" by ear; no test sound for the jingles volume (the volume plays at the next fanfare).

TESTS PROVIDED
- tools/test_texte_defilement.py --apk <APK> --saves <saves> [--slot 4]: 4 tests (text frames, battle waits, manual, outside battle), ~45 s, OK.
- tools/test_son_mixage.py: 12 unit tests (gain, categories, immediate volumes, switches, loops, jingle/resume, listening during pause), OK.
- tools/test_reglages_son_texte.py: 4 tests (old reglages.json, absurd values, notches, round trip), OK.
Captures (stable copies in /tmp/ts_caps/): son_defaut.png, son_modifie.png, texte_slot4_manuel.png, texte_slot1_auto_tres_rapide.png, texte_impose_rapide.png, jeu_parametres.png, jeu_parametres_vitesse_texte.png. Measurement scripts: /tmp/ts_work/ (run_texte.sh, run_defil.sh). Tooltips not captured (the simulated hover does not show them in tests).

FILES TOUCHED: dq4_pc/sound.py, settings.py, pause.py, window.py, engine.py; new: tools/test_*.py (3). Outside the initial list: engine.py and window.py (located, authorized), tools/ folder (new test files). No touch to "Commandes", "États", title/pre-game, interface editor, display.

MERGE TRAPS
- pause.py: line "Texte et défilement" added right after the "Son" line of _entries_root (next to "Commandes"); `titles['texte']` added on its own line before `with_mini = ...`; width rule `if wdir in ('texte',)` added right before the line `if wdir == 'commandes': pw = ...`; `_line_helptext`: curs/choix lines modified (prefix `entry['aide']`) next to the 'touche' line; `Pause.do_update`: 4 lines at the start; `names[...]` added after the dict; `_entries_sound` entirely rewritten.
- settings.py: new keys on separate lines after the 'son' line; `BOUNDS.update(...)` separate, but the loading BOUNDS loop was modified (exclusion of booleans) + 4 validation lines right after.
- window.py: init line after `self.sound.preload`, methods after `set_sfx_volume`, 3 lines after `self.sound.tick()`, constant SFX_PREVIEW before COMMON_SFX.
- engine.py: `_text_hooks()` called after the `_sca` hook in __init__, `_sv` hook (msg_visible) modified, 2 lines in step().

DOC NOTES (for docs/, not written): describe the "Texte et défilement" page, the 4 sound categories and their criteria, the new keys of reglages.json, the fact that the game's "Vitesse texte" = battle messages only, the game's volume options now taken into account, and the 3 tools/test_*.py scripts.

TO REMEMBER (memory, seen in this session): Sylfried's saves: battle speed 0,2,2,4,2 (slots 1-5), game volumes 4/4; his feedback: text speed option + scrolling (battles), sound options by category.

---

## Agent a194067a522b77b40 — 2026-11-01 22:08

REPORT agent-affichage (worktree /home/claude/wt-affichage, branch agent-affichage, base main 1e87ca6). Clean tree, nothing pushed.

COMMITS (5, all with the two-line footer)
- f46a3b7 Effective full screen from the opening of the window (logos included)
- e27ee24 Off-screen MSAA antialiasing (postfx.py), alpha-to-coverage, supersampling, sharpness, brightness
- c5c6983 Overlapping flat sceneries: end of the z-fighting flicker (flowers, paths)
- 6a5730e Shaders: removal of "Régions lissées" and "Bicubique"; the smoothing also applies to sprites
- 16042b9 postfx: a reduced window (zero drawing area) is no longer mistaken for a failure

FILES TOUCHED (all within my scope)
- New: dq4_pc/postfx.py, dq4_pc/decors_plats.py
- Modified: dq4_pc/fenetre.py, dq4_pc/hd.py, dq4_pc/reglages.py
- dq4_pc/pause.py: only `_entries_display` and the `names` dictionary ("Shader", "Suréchantillonnage"). No other page.
- pyflakes: only the warnings already present on main remain (`selected` in window.py; `H`, `R`, `yp`, `mh` in pause.py).

1. FULL SCREEN FROM LAUNCH: done, verified under xvfb with the final code.
- The window is created directly in full screen (`fullscreen=True`, desktop resolution), logos included, without going through windowed mode. If that fails, the game falls back to windowed mode and says so in the log. Option `--plein-ecran`.
- Log under xvfb 1920x1080 (/tmp/out_pe2.txt):
  - creation: PLEIN ÉCRAN 1920x1080
  - 1st frame of the logos: PLEIN ÉCRAN 1920x1080
  - 1st frame of the game: PLEIN ÉCRAN 1920x1080
  - off-screen rendering 1920x1080 with x4 antialiasing
  - captures 1920x1080.
- Hot switch tested (/tmp/out_fs.txt): "Plein écran" = yes gives 3840x2160 (capture 3840x2160), then = no gives 1280x720 again.
- I cannot verify under xvfb, so to be tested on his Windows PC: the total absence of flash or intermediate window at opening, the Windows behavior (WS_POPUP), and the return to windowed mode at the right size.

2. DISPLAY EFFECTS: added only those that are useful and verified.
Additions, in the "Affichage" page:
- MSAA antialiasing rewritten: the scene is drawn off-screen then copied. It applies hot (before: "au prochain lancement", and the window config failed silently) and is limited to GL_MAX_SAMPLES. A red note is displayed if the card cannot: "Limité à x4 par cette carte graphique". Capture: /tmp/m_mn1_b70.png.
- "Suréchantillonnage": "Aucun" / x1.5 / x2.
- "Netteté": slider 0 to 100%, adaptive sharpening without halo (CAS type).
- "Luminosité": slider 50 to 150%, gamma curve.
- With no active setting, the direct drawing from before is kept. Any GL error falls back to direct drawing and is logged.
Rejected ideas, with the reason:
- FXAA/SMAA: blur pixel art and texts, whereas MSAA and supersampling do better. This is exactly what the user complains about with some shaders.
- Scanlines/CRT: artificial effect, foreign to the game's HD rendering, and it would degrade legibility.
- Contrast and saturation: low interest, "Luminosité" is enough.
- Integer scaling: the game is 3D with free scale; the "Pixel perfect" mode already handles integer scaling on the world map.
- vsync: already active (vsync=True), a switch would bring nothing.
- FPS limiter: the engine runs at a fixed 30 Hz step with interpolation, and vsync bounds the display. Not measurable under xvfb anyway.
- Anisotropic: already applied (min(8, card max)) on the scenery textures. Under xvfb I cannot measure it; the anisotropy ratio is low (about 1.3:1) with this camera.
- Bloom/HDR: foreign to the original, not relevant.

3. "OPTION BY OPTION" AUDIT (code + A/B captures, church slot 1, frame 50; measurements by the script /tmp/aff/cmp.py)
- "Plein écran": WORKS. Creation and hot switch verified (see point 1). No capture, log only.
- "Résolution": WORKS in windowed mode (1280x720 then [1600,900]: the capture becomes 1600x900, /tmp/m_rs_b20.png). In full screen, the choice tries to change the video mode: NOT VERIFIED, xvfb has only one mode. Known limit, not fixed: at full-screen launch the game takes the desktop resolution, the `resolution` setting does not apply to it (as before, it was already not the case).
- "Shader": WORKS (3 sharp and distinct renderings, /tmp/aff/sh_cmp.png).
  - "Aucun": original pixels, borders softened by one screen pixel.
  - "EPX x8": rounded, sharp outlines.
  - "Pixel perfect": strict nearest neighbor.
  - "Régions lissées" and "Bicubique": REMOVED. An old reglages.json with 2 or 3 is read as 1 (EPX x8). Number 4 (pixel perfect) does not change and `--hd 4` remains valid.
  - Sharpness measurements (captures /tmp/m_t1_b40..120.png and /tmp/aff/t1_modes2.png). Mean Laplacian on the hero and the scenery: "Aucun" 20.7; EPX 22.6; "Régions" 21.9; "Bicubique" 16.6; "Pixel perfect" 20.7. Gradient p99: "Bicubique" 60 versus 73 for EPX.
  - "Bicubique" is therefore clearly blurry (-27%).
  - "Régions lissées" has the same measured sharpness as EPX, but it clogs fine details (eyes, fingers) and falls back to bicubic as soon as a sheet exceeds 40 colors. It is a judgment call: the code is in the history, easy to restore if the user misses it.
  - No new sharpness filter in "Shader" mode: the real sharpness is the "Netteté" option.
- "Lissage des textures": only acted on the scenery and the world map, not on the hero, NPCs, monsters or balloons. FIXED: it is now consistent everywhere, including on the EPX textures (nearest neighbor when it is turned off). Captures /tmp/aff/li_cmp.png (difference > 8 on 22,895 pixels for "Aucun", 17,989 for EPX).
- "Distance caméra": WORKS (50, 100, 200%: /tmp/aff/d_cmp.png).
- "Centrer la caméra sur le joueur": WORKS (cave, slot 5, frame 80). "Oui": hero centered, black map edge on the right. "Non": the camera stays bounded to the map. /tmp/aff/cc_cmp.png.
- "Effet de vignetage": WORKS (0, 30 and 100% outdoors: mean brightness 93.4 → 83.7 → 60.8). On the church (small scene surrounded by black), the effect is almost invisible, which is normal. /tmp/aff/vg_cmp.png.
- "Anticrénelage": FIXED (see point 2). Under xvfb x4 and x8 give the same rendering (max 4 according to llvmpipe: "x4 (demandé x8)"). On his real card x8 is not tested. Scene gradient 1.908 → 1.889.
- "Suréchantillonnage": NEW, WORKS (x1.5: 1920x1080 off-screen; x2: 2560x1440). Not measured for performance on a real GPU.
- "Netteté": NEW, WORKS. Gradient measured on the hero: 13.7 → 17.8 (50%) → 20.7 (100%), without visible halo. /tmp/aff/ne_cmp.png.
- "Luminosité": NEW, WORKS (mean 12.4 at 70%, 16.5 at 100%, 19.7 at 130%). /tmp/aff/lu_cmp.png.
- Regressions verified with the off-screen rendering: world map (/tmp/aff/mp_cmp.png), battle (/tmp/aff/cb_cmp.png), Esc menu over the scene (/tmp/m_mn_b40.png), logos and full screen, default path `--msaa 4`.

4. FLOWER FLICKER (capture 6): reproduced, two causes, fixed.
- (A) z-fighting. The flower beds are cut-out flat sceneries (textures 12862 and 14697 at y = -0.125) that overlap other flat sceneries and each other: same depth, so the depth test picks one or the other pixel by pixel, and it changes with each camera movement. Fixed by:
  - an increasing depth offset from one texture group to the next in `_paint_scenery`;
  - `flat_sceneries.shift`, which raises the overlapping flat triangles by 3 mm (30 to 130 ms per map, map cache intact, can be disabled by DQ_SANS_DECALAGE);
- (B) cut-out edges with the alpha test, which the window MSAA never smoothed. Fixed by alpha-to-coverage in the off-screen MSAA rendering (active by default, msaa = 4), plus supersampling as an option.
- Measurements under xvfb (maout, /tmp/aff/):
  - Z-fight, fixed camera, variable far plane (unstable pixels in the flowers/pond area): 110 → 61 (depth offset) → 40 (3 mm raise). The rest corresponds to the animated reflections of the water, not to z-fighting.
  - Camera sliding (0.01 in z per frame), excess temporal variation in the flower area, compared with a x2 supersampled reference:
    - base: 1.149;
    - raise alone: 1.142 (so cause B dominates);
    - MSAA 4 + alpha-to-coverage: 0.258 (-78%).
  - Global: J 2.03 → 1.64; ratio d2/d1 0.541 → 0.465.
  - Earlier measurements: MSAA 4 WITHOUT alpha-to-coverage gives no gain (J area 4.97 versus 4.92). Supersampling x2 alone reduces global J from 2.03 to 0.79.
- Honest limit: with "Anticrénelage" = "Aucun" and "Suréchantillonnage" = "Aucun", only the z-fighting is fixed; the shimmering of the flower edges remains. With the default settings (msaa 4) it is strongly reduced but not removed (0.258 residual). Not verified on his GPU.
- Captures: /tmp/m_ga_b40..50.png (before), /tmp/m_gb_b40..50.png (raise alone), /tmp/m_gc_b40..50.png (raise + MSAA 4 + alpha-to-coverage), reference /tmp/m_gr_b40..50.png (2560x1440), flicker maps /tmp/m_ga_J.png and /tmp/m_gc_J.png, z-fight /tmp/m_zd4_b40..44.png (after) and /tmp/m_zd5_b40..44.png (raise turned off) with /tmp/aff/zd45_overlay.png and /tmp/aff/zd45_roi.png.

ESTABLISHED / ASSUMED / NOT VERIFIED
- Established (measured or captured under xvfb/llvmpipe): everything above, unless stated otherwise.
- Assumed: the off-screen MSAA rendering and alpha-to-coverage work on real Windows GPUs (Intel/NVIDIA/AMD) as under Mesa. The buffers are standard GL 3.3.
- Not verified: the absence of flash at launch in full screen on Windows; x8 on his card; the video mode change in full screen via "Résolution"; performance on a real GPU (4K, supersampling x2, MSAA x8); the final look of the anisotropy.

MERGE TRAPS
Areas of window.py that other agents may also touch:
- window creation in `Game.__init__` (config without MSAA, `self.post = PF.PostFX(...)`; `self.msaa` removed);
- `_draw_scene`: `glViewport(0, 0, *self.post.begin(background))` at the start, `self.post.end()` between `_draw_fade(True)` and `_draw_damage(e)`;
- `_paint_scenery` (polygon offset and alpha-to-coverage loop);
- `_load_map` (call of `DP.shift`);
- `main()`: argument `--options-test`, `else: reg['msaa'] = a.msaa`, `a.hd` validated by `RG.valid_sprites_mode`.
- In pause.py: only `_entries_display` and the "Shader" / "Suréchantillonnage" keys of the `names` dictionary.
- In settings.py: new keys in DEFAULT and BOUNDS, the function `valid_sprites_mode` and the constants MODES_SPRITES / MSAA_VALUES before BOUNDS, two validation lines added right after the BOUNDS line in `Settings.__init__`.
- MODE_PP is now hard-coded to 4 (before: `len(HD.MODES)`), and `HD.MODES` now contains only 2 entries. If another agent writes code that indexes `HD.MODES` with a `mode_sprites` value, it must stay on 0 or 1.

TEST TOOLS ADDED (window.py)
- `--options-test "image:Libellé=valeur;..."` (value in JSON; applies an option of the "Affichage" page through the menu functions).
- Environment variables: DQ_ZDEBUG, DQ_CARTE_DEPL, DQ_SANS_DECALAGE, DQ_SANS_A2C, DQ_ATTENDRE_HD.
- Test scripts outside the repository in /tmp/aff/: run.sh, cmp.py, jit.py, flick.py, batch_ab.sh.

NOTES FOR docs/ (to be integrated by the parent)
- postfx.py: off-screen frame = MSAA color and 24-bit depth renderbuffers, resolve to texture, final pass (bilinear downscaling, CAS-type sharpness, gamma). Complete bypass when msaa = 0, scale ≤ 1, sharpness = 0, brightness = 1. Direct fallback on any error.
- Alpha-to-coverage: `GL_SAMPLE_ALPHA_TO_COVERAGE` (0x809E) enabled for the cut-out opaque scenery pass with blending disabled; the alpha is smoothed by fwidth in FRAG (uniform `a2c`); the transparent pass remains in classic alpha test.
- flat_sceneries.py: detection of overlapping flat triangles by bbox + SAT, 3 mm raise per stacking level, drawing order kept.
- Settings: `echelle_rendu` 1 to 2, `nettete` 0 to 1, `luminosite` 0.5 to 1.5, `mode_sprites` valid among 0, 1, 4 (2 and 3 migrated to 1), `msaa` among 0, 2, 4, 8.

DURABLE FACTS USEFUL FOR MEMORY (source: this session)
- Under xvfb/llvmpipe, GL_MAX_SAMPLES = 4 and no window MSAA config is available. MSAA can therefore only be tested through FBO.
- An xvfb run takes from about twenty seconds to several minutes depending on the /tmp/xvfb.lock lock that the other agents share.
- The flower flicker has two distinct causes; MSAA alone is not enough, alpha-to-coverage is needed for the cut-out scenery.
- The old mode_sprites values 2 and 3 no longer exist.

---
