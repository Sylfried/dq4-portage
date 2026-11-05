## Agent abe62037682218817 — 2026-11-02 00:44

FINAL REPORT — "fenetre" agent (batch PR #42), points 1, 2, 3, 9
Worktree /home/claude/wt-fenetre, branch agent-fenetre, base 345ba8f. Clean tree (empty git status), no push, main and saves intact.

COMMITS
- 6cf5517: black loading screen, 3 window modes, order of the "Affichage" page, F11 / Alt+Enter
- 9624ec2: robust reading of "Résolution" during a mode change + tests of the shortcuts (F11, Alt+Enter, Alt Gr, Alt alone, Alt-Tab, Pause open, key capture)
Pyflakes: only the known warnings (selected, R, yp, mh). Unit test: `timeout 100 xvfb-run -a -s "-screen 0 800x600x24" python3 tools/test_window_mode.py` → 23 tests OK (the tests depending on pyglet are skipped without DISPLAY).

BY POINT
1. Black screen at startup: DONE. `_wait` no longer draws any text (message in the console only); the Label "Chargement du moteur..." of the loop is removed; "Chargement de la carte..." (--slot option only) too. Other waiting texts found: "Chargement de la sauvegarde..." (removed), `etiq_conseil` (menu tip, not at startup, left alone). No "Suréchantillonage" typo in the code (the label is already "Suréchantillonnage").
2. Three modes: DONE. Setting `mode_fenetre` (0 windowed, 1 borderless full screen at the desktop resolution = current behavior, 2 exclusive = real display mode change to "Résolution"). The old boolean `plein_ecran` is migrated silently (True→1, False→0), then is no longer written. CLI `--plein-ecran 0/1/2`. Window created directly in the saved mode (hidden, first frame black, then shown: no flash). Defensive fallback exclusive → full screen → windowed, console message, at creation and at toggle. Postfx FBO: `post.cle = None` forced after each mode change (recreation at the right size, verified with msaa 4, ×1.5, sharpness, brightness).
   Semantics of "Résolution": mode 0 = window size; mode 1 = grayed, note "Sans effet en plein écran" (the desktop decides); mode 2 = real screen resolution (choice of the closest mode, 16/9 preferred, depth ≥ 24 bits, highest refresh rate). Note: in the old code, changing the resolution in full screen already did nothing (pyglet no-op, established by reading the code).
3. Order of "Affichage": DONE ("Fenêtre" > "Résolution" > "Netteté" > "Shader" > "Lissage des textures" > "Effet de vignetage" > "Anticrénelage" > "Suréchantillonnage" > "Luminosité" > "Distance caméra" > "Centrer la caméra sur le joueur", then "Interface" last; labels unchanged).
9. F11 / Alt+Enter: DONE. Works everywhere (logos, title, start menu, game, Pause menu), second press = return to the previous mode. Decision: the shortcut CHANGES the "Fenêtre" setting (the menu shows the real mode, the next launch finds it again); the previous mode is remembered in `mode_fenetre_retour` (never 2). Conflicts: F11 is "reserved" (removed from the assignable keys, in addition to Esc), the key is swallowed (neither validation nor game action); "Discussion de groupe" on Alt became "Alt alone, on release" (Alt+Enter therefore no longer triggers it; Alt Gr ignored); the Enter key alone still validates.

ESTABLISHED (observed under Xvfb / read in the code)
- Logos → map: non-black pixels during the 3 waits = 0 with my code, against 1595 / 2151 / 1637 with the old code (control /tmp/out_fenBase.txt).
- Migration, bounds, save round trip, F11 removed from an old file: unit tests.
- Simulated fallback (variable `DQ_SIM_ECHEC` = 2 | 1 | 2,1 | 2s, at launch and at F11 toggle), F11 and Alt+Enter during the logos, repeated toggles, off-screen rendering recreated at 1920x1080 / 2880x1620, no error; screenshot at 1920x1080, 1280x720, 1920x1080 depending on the toggles.
- Persistence of the mode and direct launch in exclusive; `--options-test`: change of "Résolution" accepted in exclusive, then "Fenêtre"=0 → back to windowed 1280x720.
- Pyglet 2.1.19 Win32 (read in the code): `fullscreen=True` = borderless window at the screen size without a mode change; `set_mode` fails silently (hence my fallback, which checks the size actually obtained).
ASSUMED
- The real display mode change (ChangeDisplaySettings) works under Windows as in pyglet; the restoration at close (`on_close` + `atexit`) does put the desktop back; the hidden-then-shown window avoids any white flash; the refresh-rate choice (the highest) is suitable.
NOT VERIFIED (needs Windows: Xvfb has only one 1920x1080 mode)
- Real resolution switch, monitor refusal, desktop restoration in case of a crash, Alt-Tab in exclusive (not handled: the monitor keeps the game's resolution until F11 or close), multi-monitor, DPI scaling, Alt Gr on a real AZERTY keyboard, Alt+Enter with the Windows key behavior (I tested through the harness with MOD_ALT).

FILES TOUCHED
- dq4_pc/window.py (+243/−~50): function `choisir_mode_ecran`, `Game.__init__` (window creation), `_create_window`, `modes_ecran`, `resolutions` / `set_resolution`, `regler_mode_fenetre`, `_poser_mode`, `basculer_exclusif`, `_window_shortcut`, `_wait`, `on_key_press`, `on_key_release`, `_held`, `_edges`, harness (`_test_keys`, MOD_ALT), CLI, `on_close`.
- dq4_pc/settings.py (+22): DEFAULT (`mode_fenetre`, `mode_fenetre_retour`, without `plein_ecran`), `MODES_FENETRE`, `NOMS_MODES_FENETRE`, `valid_window_mode`, migration in the loader, `RESERVED = ('ESCAPE','F11')`.
- dq4_pc/pause.py (+15, minimal): one line in the dict `names` (`'Fenêtre': RG.NOMS_MODES_FENETRE`) and rewrite of `_entries_display` only.
- tools/test_window_mode.py (new, 208 lines).

SCREENSHOTS (/tmp)
- "Affichage" in full screen ("Résolution" grayed + note): /tmp/m_fenP1_b60.png; exclusive full screen: /tmp/m_fenP2_b60.png; "Fenêtre" drop-down list (windowed mode): /tmp/m_fenP0_b60.png
- Black screen during loading: /tmp/m_fenN_b30.png (log /tmp/out_fenN.txt); control, old code: /tmp/m_fenBase_b30.png (/tmp/out_fenBase.txt)
- Simulated fallbacks: /tmp/m_fenF3_b20.png, /tmp/m_fenF4_b20.png, /tmp/m_fenF5_b20.png; failure at F11 toggle: /tmp/m_fenF6_b30.png, /tmp/m_fenF6_b60.png, /tmp/m_fenF7_b30.png
- F11 / Alt+Enter during the logos: /tmp/m_fenL_b40.png; toggles with off-screen rendering: /tmp/m_fenFX_b30.png, _b60.png, _b90.png; exclusive launch + resolution change: /tmp/m_fenR_b40.png
- Others: /tmp/m_fen0_b60.png, /tmp/m_fen1_b60.png, /tmp/m_fen2_b30.png, /tmp/m_fen2_b60.png, /tmp/m_fenA..E. Logs: /tmp/out_fen*.txt

MERGE PITFALLS
- pause.py: I touch one line of the `names` dict (adding the key `'Fenêtre'`) and the WHOLE list of `_entries_display` (reordered). The "pause2" agent modifies the rest of pause.py: conflict unlikely, but if the sprites agent adds an "Affichage" option line, insert it by hand into MY reordered list (keep "Interface" last).
- window.py: possible conflicts with the other agents on `__init__` (window creation block: `res_demandee`, `_create_window`), `_wait`, `on_key_press/on_key_release`, `_held`, `_edges` (Alt excluded from the "discussion" edge, `alt_tap`), the `_test_keys` harness and the CLI options (`--plein-ecran` becomes choices (0,1,2)).
- settings.py: DEFAULT (key `plein_ecran` replaced by `mode_fenetre` + `mode_fenetre_retour`), `RESERVED`, migration in the loader. Any code that reads `reg['plein_ecran']` must read `reg['mode_fenetre']` (I migrated those of window.py; check the additions of other agents).
- Pause (agent pause2), "Commandes" page: the "Discussion de groupe" tooltip could say "Alt seul, au relâchement ; Alt+Entrée = plein écran exclusif"; not modified by me (out of scope).

NOTES FOR docs/ (to merge into viewer-notes-dq4-pc.md, section "Feedback from 23:24 (#42)")
- Startup: entirely black loading screen (no text, console messages only). Window created hidden in the saved mode, shown after a first black frame.
- Setting `mode_fenetre`: 0 windowed / 1 full screen (borderless at the desktop resolution) / 2 exclusive full screen (real display mode change). Silent migration of the old `plein_ecran`. CLI option `--plein-ecran 0|1|2`. `mode_fenetre_retour` = mode (0 or 1) to which F11 returns from exclusive.
- Semantics of "Résolution": windowed = window size; full screen = no effect (grayed); exclusive = real screen resolution (closest mode, 16/9 preferred, ≥ 24 bits, highest refresh rate).
- Fallback: exclusive refused → borderless full screen → windowed, with a console message. Test hook `DQ_SIM_ECHEC` (values 2, 1, 2,1, 2s: simulates the refusal at creation and at toggle). Display mode restored at close (`on_close` + `atexit`).
- F11 / Alt+Enter: toggles exclusive ↔ previous mode from any screen; the shortcut modifies the "Fenêtre" setting. F11 is a reserved key (not assignable in "Commandes"). "Discussion de groupe" (Alt) now triggers on the release of Alt alone (so Alt+Enter, Alt+Tab and Alt Gr do not trigger it).
- "Affichage" page: new order (see point 3); "Interface" last.
- Test: `tools/test_window_mode.py` (23 tests, Xvfb recommended). Known limits: see "Not verified" (Windows required).

To remember for the main session (sources: brief and mission): Sylfried tests on Windows; the "Not verified" points above are the ones to have him try first (Alt-Tab in exclusive, real resolution, F11 round trip, closing with desktop restoration).

---

## Agent a8d3c9b371f180c4e — 2026-11-02 00:46

CAMERA AGENT (#42) — worktree /home/claude/wt-camera, branch agent-camera, base 345ba8f. 1 commit: 09006ce. Clean tree. pyflakes OK (only known warning: `selected`).

**UP FRONT: NO change of FOV or tilt (before = after).** Towns: nominal fov 9.5 (None on the engine side), horizontal field of view 12.67° (9.5 x 4/3) fixed, vertical 22.3° at the original aspect 0.5625. Pitch = the engine's (47.03°, distance 39.55), lookDown 0.2°, advance 4.0, near 5 / far 100 by default. The sprites agent can keep the current projection.

## Point 14 (prologue frog): fixed
- Scene: trigger ~(0.93 ; 10.57) on `mlout1`. TownCamera lock: mode 1 (diagonal pan, ~+0.088 x / -0.046 z per frame) -> mode 5 (follows the frog, which exits toward +x up to x = 6.07) -> mode 4 (return to the player) -> lock released.
- Cause (Established, frame-by-frame trace): the viewer clamped the camera in x (`bounds_x`, 16/9 framing) as soon as `cam_jeu` became true. The rendering stayed stuck at x = 1.978 while the engine went to 6.07: max gap 4.09 u before, **0.000 after** over 1470 scene frames. Hence « droite puis bas » (EN: "right then down") and the end of the tracking.
- Unity clamps nothing (Established by disassembly): `SceneCamera.Update` D16180 without Clamp/Min/Max; `TownCamera::execute` without clamp in free mode; `NativeManager.cmd_camera` D14568 calls `FldObject.GetEventLimitedPos` CD4EE4 for the position, but only if `UIFix.IsLargeAspectRatio()`, and `s_eventLimitList` (.cctor CDDC08) has only ONE entry: scenery `map/ev/ev02/out/ev02`, events {0,1}, z >= -19.5. It is not `mlout1`.
- Fix (`window.py`): new `Game._camera_menee(eng)`; `cam_jeu` = lock AND camera led somewhere other than on the player (target mode 1 to 5, movement in progress, or target more than `CAM_MENE_DIST` = 1.0 u from the hero, or hero out of frame). `poids_cible = 1.0 if option or self.cam_jeu else 0.0`: no 16/9 bounds when the camera is led, with or without the "Centrer la caméra sur le joueur" option; the bounds come back progressively (exp(-14 t), real time) at the end.
- Before/after screenshots: sheets `/tmp/cam_fr_trajet_av_ap.png` (frames 146 to 296) and `/tmp/cam_fr_depart_av_ap.png` (frames 1530 to 1602); traces `/tmp/cam_av14.csv` (before) and `/tmp/cam_ap14b.csv` (after); single frames `/tmp/cam_av14_f<n>.png` and `/tmp/cam_ap14b_f<n>.png`.

## Point 17 (father, camera that « continue son chemin » (EN: "keeps going on its way")): probable cause fixed, exact scene not found
- Cause found (Established by test, but conditional): the centering correction (hero - game target) was smoothed as a block by exp(-14 t). As soon as the game clamps its target (map edge) and the hero runs, the camera lagged behind (gap from the hero to the center up to 0.03 NDC at x1 and 0.10 at x4, growing with speed and frame rate), then caught up after the stop (0.015 to 0.09 NDC): exactly « elle continue légèrement son chemin avant de se recentrer » (EN: "it keeps going slightly on its way before recentering"). Measurement: `tools/test_town_camera.py` (frame rates 1/30, 1/60, 1/144; speeds x1 to x4).
- Fix: correction = target followed frame-accurately (camera rigid on the hero) + a remainder that only arises from a regime change (scene <-> player control) or a cut, and which fades in real time. Result: gap 0.0000 everywhere, independent of the number of engine steps per frame and of the frame rate. The real bench (`/tmp/cam_r17_{av,ap}_{a1,a15,a4}.csv`, run toward the frog trigger at x1 / x1.5 / x4) confirms: the rendering equals the engine in scene, whatever the speed.
- Second contributor fixed: a lock that keeps the hero in the center (mode 6, or shot on the hero) no longer changes regime. Before, it made the camera slide toward the bounded framing of the room in ~0.2 s at the trigger, then come back.
- Assumed / Not verified: I did NOT reproduce the symptom in the father's house. In the prologue (`mlb1a`) the engine's camera = hero everywhere, without lock during the 1st conversation: the defect therefore does not occur there. The father moves later and the event concerning him was not reached. The event of Screen 6 remains to be confirmed on the user's save. Another lead NOT fixed: under lock (`cam_bloquee`), the rotation / tilt chosen by the user are cut at once (jump), and this also affects the orientation of the sprites.

## Point 16 (is the camera angle the right one?): yes, for the game mode. Very high certainty on the code side, no phone screenshot available.
- Established (disassembly):
  - `SceneCamera.Update`: LookAt(position, target), `eulerAngles.x -= s_lookDownAdjust` (0.2°), advance of `s_distanceAdjust` 4.0, `Perspective(fov x 4/3, 1/Camera.aspect)` with [0] and [5] swapped (fixed horizontal field of view), `s_yOffset` by matrix product.
  - `SetViewAndCenterY` D1F5D0 sets the rect height from screen_aspect / 0.5625: the 3D view therefore ALWAYS has the 9:16 aspect on any phone (letterbox / crop). Field of view 12.67° x 22.3° everywhere, `ASPECT_DEF` = 0.5625.
  - Near 5 / far 100: `Global.CameraInitParams[0]`, already in the notes.
- Numerical verification: a separately rewritten Unity pipeline (left-handed LookAt, euler, Perspective, [0]/[5], yOffset) compared to `_town_camera` on 200 poses x 18 points at 0.5625: max gap 4e-15 NDC. Permanent test: `tools/test_town_camera.py`.
- Scan of the 518 loaded maps (`/tmp/scan_cams.txt`, 3 maps not loadable): 514 have distance 39.55, pitch 47.03°, default fov, default near / far / yOffset. Exceptions: `dpout` (pitch 28.04°, far 150), `sjout` and `tdout` (near 1.0). No difference between towns / caves / towers.
- Walk-through of 2300 frames of the prologue: the only difference = title screen `ev01` (distance 44, pitch 39°, fov 10, far 150, bottom 3.02), already handled by `TITRE_HAUT`. Outside the title, never a change of distance or fov during the tested scenes.
- World maps and battle: read in previous sessions (notes of 2026-10-30 and 2026-10-31: orthographic world `Field.Init`, battle fov 48 x 4/3, 4/3 reference, yOffset 0.04). I did not re-verify them here. `_battle_camera`: vertical fov 50.25°, near 0.25, far 500, yOffset 0.04.
- Assumed: near/far for the maps that send their own values (followed as is).
- Intended deviations of the viewer (unchanged): the mobile's field-of-view height kept and more scenery on the sides in 16/9; "common zoom" (the hero keeps HERO_FRAC of the window height).
- Possible lead for « l'angle ne va pas » (EN: "the angle is off"): `settings.angle_camera` (up / down arrows) is SAVED. In `/tmp/rg.json` (shared test settings) it is -2.25° (default 0 = like the game). An accidental press is enough to shift the pitch permanently. To check in the user's real settings ("Caméra" command; the F1 information line shows the angle).

## Files touched
`dq4_pc/window.py`: `_town_camera` (centering block + weight), `tick` (computation of `cam_jeu`), new `_camera_menee`, constant `CAM_MENE_DIST`, attributes `cam_res` and `cam_centre`. `tools/test_town_camera.py` (new, 5 tests without a window, 1 s, pyglet "headless" under Linux). I touched neither `engine.py` nor `settings.py`. On the old code, 3 tests out of 5 fail (centering, led camera, predicate): they do detect the defects.

## Merge pitfalls
- `self.cam_jeu` changes meaning: "lock AND camera led somewhere other than on the player" (before: the lock alone). `cam_bloquee` keeps the lock meaning.
- `cam_poids` is kept: same name, same role (share without bounds), its target is simply different. `_camv` still displays it.
- Other agents on `_town_camera` (`TITRE_HAUT`, sprites): my change is localized between `t = time.perf_counter()...` and `if abs(self.cam_dec[0]) > 1e-4` (computation of `cam_dec`, `cam_res`, `poids_cible`), then in `tick` and `__init__` (line 185: addition of `cam_res` and `cam_centre`).
- `cam_dec` remains the applied value (`dec + remainder`).
