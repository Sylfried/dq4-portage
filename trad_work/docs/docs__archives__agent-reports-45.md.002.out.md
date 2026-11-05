## Agent "decor" (a1877ded1e12dc252) — 2026-11-02 20:42

FINAL REPORT — mission "décor" (DC), worktree /home/claude/wt45-decor, branch agent45-decor, clean tree (empty git status).

VERDICT: the stones do not "float" because of a viewer defect. Their height is faithful to the game. I changed nothing in the rendering. A single commit: a measurement test.

POINT 1 — map and framing: DONE.
- Established: the map is `maout`, the south end of the north-south flagstone path. The "blue" in ecran9 is the background color `e.background` (115,148,255), visible beyond the jagged edge of the grass. This void is only shown because `camera_centree` (default) removes the game's camera clamping. Framings reproduced: /tmp/m_dc_av_b117.png, /tmp/m_dc_av_b131.png, /tmp/m_dc_av_b173.png (south edge) and /tmp/m_dc_var_b35.png.
- Not verified: the exact cropping and scale of ecran9, and the original game's camera clamping near the south edge.

POINT 2 — nature of the stones: DONE.
- Established (extracted data): flat surface, no volume. It is the object `020_mast1` (stones maisiyk1..4, earth sn02/najimi02, pond), all vertices at y=-0.125. The grass below (`018_maoutsb1`) is at y=-0.25. Gap: 0.125.
- Established (datapack shaders): fld_atest, AlphaTest queue, ZWrite on, no blending, alpha cut-out, no cast shadow. Lighting baked into the vertices, consistent with the grass. ZTest LEqual, Cull Back, Offset 0/0: no depth offset in the game.
- Established (designers' rule): the decal layers are spaced 1/8 unit (0.125) apart. Over 63 maps, 21,543 flat cut-out decals placed on an opaque ground: 10,017 (46%) at 0.125, then 1,889 at 0.25, 1,474 at 0.375. 3,710 others have no opaque ground below. In maout: more than 50% of the decals are at a multiple of 0.125, less than 3% are coplanar, 0 faces downward. The `ModelOffset` (0.01 to 0.02) is only used for the flowers hana1/hana2 in 5 maps and dbdoku3 in dbout.
- Our elevation (`flat_sceneries.shift`, 3 mm per level, measured from 6 to 12 mm) is worth less than 0.6 px at 720p. It is negligible.

POINT 3 — comparison with Unity and dark fringe: PARTIAL.
- Established (GL measurement, maout, 720p): lowering the stones to the grass level only moves them by 4 px on screen (predicted 3.9). The 1/8 unit gap therefore does not explain the impression of floating. Comparison: /tmp/dc/cmp_av_po_pierres.png.
- Established: the dark fringe comes mainly from the transparent texels being (0,0,0,0) in the textures. Bilinear filtering and mipmaps blend them at the edge of each stone. Spreading color into these texels makes it disappear: /tmp/dc/cmp_av_bo_pierres.png (left: current; right: without fringe). On the south scene, 2.3% of the pixels change outside the dialogue, only on the outlines. In the stones area, 750 pixels become lighter and 0 darker. Difference map: /tmp/dc/diff_bo_sud1.png.
- Assumed: the original game has the same fringe, or even a wider one. Reason: AlphaTest shader without premultiplication, black texels, and our "sharp-bilinear" shader shrinks the blending zone. The dark green outline is also partly baked into the texture.
- Not verified: no mobile screenshot of a stone path in the project to settle it. Lighting, shadow, MSAA and a2c ruled out as causes of the apparent height.

POINT 4 — fix: NOT DONE, deliberately.
- The height is faithful, so nothing to fix globally. I changed nothing in the scenery rendering, nor in `fld.py`, `map_objects.py`, `flat_sceneries.py` and `window.py`. No conflict to expect with the "combat" agent on the alpha edges.
- Option A (not committed): spread the color of the opaque texels into the neighboring transparent texels (alpha unchanged). Files ready: /tmp/dc/proposition_bords_alpha/bords_alpha.py and test_bords_alpha.py (8 tests OK, pyflakes clean). Planned wiring: 2 calls `self._tex(...)` in `Game._load_map` (window.py ~1273 and ~1281), `_calc_hd_scenery` unchanged. If Sylfried wants it, it must become a setting: migration, ↺, `settings.py` key. The GL test was done with a hook on `_tex` (all textures), not with the scenery wiring alone.
- Option B (not recommended): place the decals on the ground. It departs from the original game and only moves by 4 px. The prototype `poser()` of /tmp/dc/wrap_multi.py wrongly lowered the flat edges of the fence: it would need a height ceiling and target only the decals.

COMMIT
- b788856 "Test: height of the flat decals above the ground (stones of the maout path)": `tools/test_ground_decals.py` only, with the two trailers. It keeps the measurement 0.125 / -0.125 / -0.25 from the extracted data; it does not test the rendering. Command: `DQ_CACHE_CARTES=<folder carte10_*.pkl> python3 -W ignore tools/test_ground_decals.py`. 2 tests OK, pyflakes clean, skipped without cache.

NOTES TO PASTE INTO docs/ (port technical notes)
"Flat decals on the ground (stones, earth, flowers, grasses). The game's scenery shaders (fld_normal, fld_atest, fld_trans) have no depth Offset. The designers separate the layers through geometry: each layer is placed 1/8 unit (0.125) above the previous one. Example maout: grass y=-0.25, earth and stones y=-0.125. Measurement over 63 maps: 46% of the cut-out decals are 0.125 above the opaque ground, then 0.25 and 0.375. The ModelOffset (0.01 to 0.02) only concerns the flowers hana1/hana2 (5 maps) and dbdoku3 (dbout). At 720p, 1/8 unit is worth about 4 px: the stones do not float by default. The viewer's elevation (3 mm per level, 12 mm at most) is negligible. The dark fringe of the stones comes from the black transparent texels blended by the filtering; the original probably has it too (not verified). The blue background of ecran9 is the background color of maout visible at the south edge thanks to camera_centree. Test: tools/test_ground_decals.py."

NOT VERIFIED: rendering under Windows and real GPU; mobile screenshot of a stone path; the fringe in the original; the effect of option A on the battle sceneries (stronger magnification, scope of the "combat" agent). Sylfried's default mobile settings are unknown.

MERGE PITFALLS: no game file touched, a single file added (tools/test_ground_decals.py). If option A is adopted later: new module bords_alpha.py, 2 lines in `_load_map`, to be coordinated with the "combat" agent.

SCREENSHOTS: /tmp/m_dc_av_b33.png (overview of maout), /tmp/m_dc_av_b47.png (flowers and pond), /tmp/m_dc_av_b117.png /tmp/m_dc_av_b131.png /tmp/m_dc_av_b173.png (south edge), /tmp/m_dc_av_b201.png (horizontal path), /tmp/m_dc_var_b35.png (current), /tmp/m_dc_var_b131.png (stones lowered), /tmp/m_dc_var_b227.png (without fringe). Top view: /tmp/dc/top_maout.png. Measurements per map: /tmp/dc/hauteurs_all.json.

TO REMEMBER (memory): the harness DQ_CARTE_TEST="name;x,y,z;cx,cy,cz" with DQ_CARTE_SANS_SPR=1 works well; a camera that is too close (k < 0.28) is cut by the near plane. An engine harness without GL (`Engine`, `step(held, decl)`, UP=1 DOWN=2 LEFT=4 RIGHT=8) avoids the xvfb lock.

---

## Agent "son" (aa98dee8079978f2c) — 2026-11-02 20:47

MISSION REPORT "son" (PR #45, worktree /home/claude/wt45-son, branch agent45-son, base 84b3f22). Clean git status. 4 commits, nothing pushed. Scope: sound.py + 2 lines of window.py + tools/test_sound_mixing.py.

== ANSWER TO SYLFRIED (« pas de jingle quand on meurt ? » (EN: "no jingle when you die?")) ==
The original game has NO jingle nor dedicated sound effect for death. Established (real engine under Unicorn, packets 35/36/37):
- Ally at 0 HP: only SE 403 (the damage sound, common to all hits) + the message. Nothing else.
- Party defeated (BattleExecVictory38): music stop (37, 16392 = 0x4008) then BGM 23 (113.5 s, loop, music of the "voice" scene). No short jingle. No "game over -> title" path in the engine.
- The original Unity layer itself only plays SE 300 (button) and the music resume (Sound.SystemUpdate): case (b) excluded, no hidden jingle on the C# side.
=> No "missing death jingle" to add (that would be inventing, contrary to the rule « comme le mobile » (EN: "like the mobile game")). Three causes on the viewer side explain a missing or truncated defeat sound/fanfare, all fixed (SN1 to SN3).

== INVENTORY (proof = trace of the engine packets, harnesses h45/wipe/battle_scenario/flee_battle/services/menu_sounds in son45_work) ==
- Ally falls: SE 403 only. Established.
- Total defeat: 16392 then BGM 23. Established.
- Victory: SE 409 (2.91 s, snd_vol 0.6) + music stop, at the same time (BattleEndTask). Established.
- Level up: (37,16384) then BGM 47 (3.1 s, no loop). Established (level replay).
- Escape: SE 408 (BattleExecEscape::setup); failed escape: SE 408 + message, no jingle. Established (flee_battle.py).
- Church save BGM 39, resurrection BGM 40, inn BGM 41 (the engine cuts it at 3 s). Established (services.py, real engine).
- Menu jingles: table MenuSoundManager::setPlaySound(MENU_SOUND) 1..15 read (menu_sounds.py). Established by disassembly.
- Chest / key / medal: BGM 48 via playRestart (0x1000|48), Assumed from the static code, NOT played in the engine.
- Real usage of BGM 36, 37, 38, 42, 49: Not verified.
Summary "present/absent": everything the engine requests is now played in the viewer; "absent" on the engine side = death jingle, escape jingle, failed escape jingle, game over -> title (do not exist in the game).

== FIXES (one commit per point) ==
SN1 08cc0d2 – engine music decoded in advance: BGM_PRELOADED = jingles 6, 8, 10, 13, 35-50 + 30 + 23 (22 tracks, 59 MB), separate thread (background_pool), one at a time, only when a music is playing and no requested decoding is waiting, pinned (never evicted by the LRU purge). Cause: BGM 23 was only decoded on the engine's order (0.6 to 1.2 s) and stop_bgm() cancels an ongoing decoding, so an engine stop arriving before the end = silence. Proof: replay of the real engine in real clock, game over at x3: BGM 23 order -> sound 0.70 s later before; 0 s after (rt_avant_x3.txt / rt_apres_A_x3.txt). Established: the delay. Assumed: the complete silence on a slow PC (not observed here, only unit test).
SN2 29413f1 – jingle protected in accelerated play. The engine chains its orders 2-3 times faster at x2/x3 and was cutting the fanfare: BGM 47 played 3.1 s at x1, 2.2 s at x2, 1.2 s at x3 before; 3.1 s at x1, x2 and x3 after (rt_niveau_avant_x*.txt / rt_niveau_apres_x*.txt). Mechanism: events(evts, engine_frame=None); as long as a jingle (category "jingles", no loop) is playing, a music order that would have arrived after it at normal speed is held until min(normal time = frame/30 s, end of the jingle), FIFO queue, emptied on savestate load / sound cut, pause releases nothing, sound effects never held. At x1, without engine frame, cut jingles or looping music: no change. window.py: engine_frame=eng.frames (line 2779). No speed logic touched. Real test without window (real pyglet, silent driver, real APK): stop order released after 3.17 s for a 3.1 s jingle.
SN3 d8d11ac – SE 409 (victory fanfare) filed under "Jingles et fanfares" (SFX_JINGLES, category_sfx); the game's "volume bruitages" option is still applied (Mixer.gain(category, own, option=None), the SE pass option='effets'). No new setting, no migration of settings.json; identical sounds by default. Classification choice (Assumed: a fanfare must follow the "Jingles et fanfares" slider), can be undone by emptying SFX_JINGLES.
SN4 c94433d – comments only (measured durations).
Tests: tools/test_sound_mixing.py 14 -> 30 (7 Preload, 8 ProtectionJingle of which 5 fail if the protection is disabled, 1 fanfare 409) OK; test_sound_text_settings 7 OK; test_battle_speed 42 OK (1 skipped, as before). pyflakes: only soundfile/LoopSource (known); window.py: dims and sel already existed at 84b3f22.

== NOTES READY TO MERGE INTO THE DOCS ==
1. Engine sounds: the only sound packets = 35 (PlaySE SE%04d), 36 (StopSE), 37 (PlayBGM; >=0x4000 stop, 0x1000|n = playRestart with resume of the previous music). Death of an ally = SE 403; party defeated = 0x4008 then BGM 23; victory = SE 409; level = BGM 47; escape and failure = SE 408; church 39, resurrection 40, inn 41; chest 48 (not played). Unity only plays SE 300 and the resume (Sound.SystemUpdate).
2. Decoding: BGM 23 0.59 s alone (0.7-1.2 s in game), BGM 30 0.43 s, jingles 0.01-0.14 s; preloading = SN1 (59 MB).
3. Speed: one engine step = 1/30 s at normal speed; the sound must be aligned on the engine frame, not on the wall clock (SN2).
4. snd_vol.dat: 1171 floats indexed by sound number (BGM = AKB header volumes, SE all at 1.0 except SE 409 = 0.6); the header x snd_vol product is not verified.
5. Harnesses: PartyStatus::add makes members() unreliable (real party in slot 1 = [3, 12], killing Doc = index 12); escape = button 3; church/bank via changeShopMenuPhase; a church list is under a message (menu priority before the message's "A", Yes/No port 2).

== NOT VERIFIED ==
Real window with sound (the xvfb queue had ~12 waiting jobs: test canceled, process killed, nothing left lying around); replaced by a test of the real Sound class with real silent pyglet without a window. Decoding speed under Windows / slow PC; real listening; BGM 48 in the engine; snd_vol semantics; 30 frames/s = normal speed (Assumed); whether Sylfried plays at x2/x3 (SN2 changes nothing at x1).

== MERGE PITFALLS ==
window.py: 2 lines (225: preload_music() after preload(COMMON_SFX); 2779: engine_frame=eng.frames): possible conflict if the "combat" agent touches these lines. State.apply, battle_speed.py, pause.py, settings.py not touched. Signature Sound.events(evts, engine_frame=None) compatible with test_battle_speed.

== USEFUL /tmp PATHS ==
Private: /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work/: replay.py + run_replay.py (RT=1 real clock, SON_DIR=.../avant for the old sound.py, MARCHE, SUITE; usage run_replay.py niveau|wipe FACTEUR), real_pyglet.py, rt_*.txt (before/after proofs), b1_out.txt, scan_imm.txt, avant/son.py. Cache /tmp/son45_cache.

== TO REMEMBER (memory) ==
The scratchpad is shared with other agents: use a private subfolder. Never run pkill -f with a pattern present in its own command line (kills its shell). Two replays with the same name overwrite /tmp/sv_NOM (FileExistsError). import pyglet without a screen requires pyglet.options['shadow_window']=False.

---

## Agent "camera" (a62435950b4b9be62) — 2026-11-02 20:51

REPORT agent "camera" (CA), batch 45, worktree /home/claude/wt45-camera, branch agent45-camera (base main 84b3f22). Clean tree (`git status` empty), 4 commits, no push. All tools/test_*.py pass headless (test_text_scrolling requires arguments, unrelated). Full test_window_mode (39) seen OK under xvfb before the split into commits; the final tree is byte-for-byte identical.

1) POINT BY POINT

1. Full-screen monitor: DONE (code and tests). New setting on the "Affichage" page, under "Plein écran": list of the monitors seen by pyglet ("Écran 1 (1920x1080), principal").
 - Automatic (↺) = the screen where the window is, failing that the primary one. Key `ecran_plein` in settings.py: None, or index + position + dimensions + name.
 - Used on each entry into full screen (F11, Alt+Enter, switch, launch in full screen). Already in full screen, changing the choice moves the window right away.
 - At the next launch, the screen is found by name, then position + dimensions, then index + dimensions, then dimensions alone. If it no longer exists: fallback to the window's screen, "Écran N (absent)" line + red note, choice kept, never an exception.
 - Return to windowed mode: the window comes back where it was (position remembered by pyglet). If that position no longer exists (screen unplugged, or launch in full screen), it is recentered on the full-screen monitor.
 - Bug fixed along the way: `set_fullscreen(False, *taille)` passed the size as screen/mode (pyglet wants width=/height=), hence a 640x480 window on return from a full-screen launch.
 - Established: tools/test_screens.py (35 tests, fake Screen: order changed, resolution changed, duplicate names, unreadable screen, absurd JSON) and test_window_mode. Real pyglet X11 with 2 monitors (/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/cam45/multi.out): choosing monitor 2 gives 800x600, return to windowed at (40,30), moving 1<->2 in full screen, recentering at (80,60). Limit: the two Xvfb screens are superimposed at (0,0), so only the sizes are discriminating.
 - Screenshot of the page: /tmp/m_cam45aff_b120.png.
 - Not verified: real multi-monitor Windows, different DPI per screen, real position of the screens, pyglet's behavior when the window is dragged from one screen to the other.

2. Stairs / vertical sliding: NO spurious sliding found, no camera code modified. A test is added. Established by disassembly and measurements, not by a feeling.
 - Engine: TownCamera::execute (0x1d165c) does setTarget(player position) on every step when the camera is not locked (+0x3e = 0), with no Lerp nor damping in Y. Measured on the 45° ramp of `ckf4` (ΔY ≈ 0.113 per step when walking): target Y = hero Y − 0.047 and camera Y = hero Y + 28.89, step for step.
 - Unity: SceneCamera has no smoothing field. `cmd_camera` only passes the position through FldObject.GetEventLimitedPos, and only on a very wide screen with an event limit (that is X/Z, not Y).
 - Viewer: `_town_camera` only corrects X/Z (`cam_dec`, `cam_res`), never Y. Simulation with the real `_town_camera` and the interpolation of `_interpolate` on the engine trace of `ckf4` (2552 frames): hero's NDC y constant (−0.01512, deviation < 1e-9) going up, at rest and going down. Same at 30/60/144 frames per second, with or without "Centrer la caméra".
 - Generalized: sweep of 529 maps, i.e. about twenty with slopes of 1 to 6 units (castles, towers, caves: `ckf4`, `ckout`, `ciido`, `cdido`, `chout`, `ckf3f5`, `cef2`, `dbout`, `cjf2b`…). Amplitude of the camera target equal to that of the hero, to within a hundredth. The only discrepancies come from maps where the hero exits onto the world map.
 - Conclusion: the vertical movement seen on the stairs is the original camera following the hero's height 1:1 (the scenery scrolls when the slope goes up or down). It is not a smoothing like in the case of the father. It is identical on the phone, and independent of running or walking, which matches « que je coure ou non » (EN: "whether I run or not").
 - To be decided with Sylfried: if this following bothers him, it would be a NEW option (camera that ignores the hero's height), not a bug fix. I did not do it: « le jeu d'origine fait foi » (EN: "the original game is the reference").
 - Not verified: real trace of a climb through the real stairs action between floors (`TownKaidanAction2`, objects with common id 0x8a/0x8b): I did not manage to trigger it in the harness. Established by the call list: it calls no TownCamera function, hence the same execution path as above. Ladders, ropes (TownActionRura), bridges and falls (TownFallAction, which locks the camera) not traced. The feel on Sylfried's machine is not verified.

3. Wheel resets: DONE. Ctrl + wheel (up OR down) = default distance (the wheel alone always zooms). Wheel click without movement = camera position (rotation + tilt). Ctrl + wheel click = both. A click followed by a movement of 4 px or more is a rotation, nothing is reset.
 - Conflict: the old "Ctrl + click = zoom only" is removed, because it is now Ctrl + wheel. "Wheel click = direction" is kept (it was already the position reset: no conflict).
 - The three gestures are in "Commandes" (read-only information lines, screenshot /tmp/m_cam45cmd_b175.png) and in the help texts of the entries "Distance caméra", "Touche spéciale" and camera keys.
 - Established: 49 tests in test_entries.py.
 - Not verified: the feel with a real mouse.

4. Mouse camera inversions: DONE. On the "Commandes" page, "Caméra à la souris" section: "Inverser gauche / droite" and "Inverser haut / bas". Keys `camera_inverser_gd` / `camera_inverser_hb`, default No (current behavior), ↺ restores No, absurd value in the JSON = No.
 - Each setting only inverts its axis (`inputs.rotate`, bounds kept). Keyboard arrows and resets unchanged.
 - Established by test (fake events, 4 combinations).

2) COMMITS (one per point; the 2 lines Co-Authored-By and Claude-Session are at the foot of each message)
 - 57ada9e  Full-screen monitor (point 1)
 - 4145112  Mouse: Ctrl + wheel, wheel click, Ctrl + wheel click (point 3)
 - 4b452e4  Invert left/right and up/down (point 4)
 - 91a2ab1  Test "slope without vertical sliding" in test_town_camera.py (point 2, test only)

3) NOTES TO MERGE INTO THE DOCS (ready to paste)
 - Settings: `ecran_plein` (None or dict `indice`/`x`/`y`/`largeur`/`hauteur`/`nom`), `camera_inverser_gd`, `camera_inverser_hb` (booleans, default No). No change to an existing default: no migration. `ecran_plein` is cleaned up on reading (`screens.valid`).
 - New module `dq4_pc/screens.py` (pure monitor logic) and tools/test_screens.py (35 tests).
 - API: `Game.set_full_screen(yes, move_to=False)`, `_set_full_screen(full, screen_page=None)`, `_apply_full_screen(full, size_value, screen_page=None)`, `regler_ecran_plein`, `valeurs_ecran`, `nom_ecran`, `note_ecran`. `WheelGesture.let_go()` returns 'direction' / 'tout' / None (no longer 'zoom'). `inputs.rotate(..., invert_gd=False, inverser_hb=False)`.
 - Controls: Ctrl + wheel = default distance; wheel click = position; Ctrl + wheel click = both. Ctrl = keyboard Ctrl or "Touche spéciale".
 - pyglet 2.1.19: on X11 Xinerama without RandR, `XlibScreenXinerama` has no `is_primary` (`get_default_screen` crashes: pyglet limitation, `listing` protects with try/except). Xvfb with RandR only shows one screen. The old `set_fullscreen(False, *taille)` was wrong.
 - Camera, established: TownCamera::execute does setTarget(player) on every step; modes +0x48: 0 nothing, 5 a character, 6 the player, 1 to 4 movements (MoveBase). No smoothing in Y on the engine, Unity or viewer side. `cmd_camera` (Unity, D14568) passes the position through FldObject.GetEventLimitedPos (event limits, only on a very wide screen, via UIFix.IsLargeAspectRatio): possible lead for the 16/9 bounds `bounds_x`, not explored.
 - Stairs between floors: `TownKaidanAction2` (objects with common id 138/139) moves the hero through TownActionMoveToTarget and calls no TownCamera function. List of the maps with stairs: /tmp/cam45/kaidan.json (about a hundred maps).
 - Engine test pitfall: `startTown(nom)` without teleportation places the hero at (0, 0.047, 0.78), often stuck. Test ramp: `ckf4`, walk UP / DOWN.

4) NOT VERIFIED (recap)
 Windows and real multi-monitor; DPI per screen; real position of the screens; mouse feel; climb through the real stairs action between floors; ladders, ropes, falls; Sylfried's feel on point 2.

FILES TOUCHED
 dq4_pc/screens.py (new), dq4_pc/window.py, dq4_pc/pause.py, dq4_pc/settings.py, dq4_pc/inputs.py. Tests: tools/test_screens.py (new), test_window_mode.py, test_entries.py, test_interface_settings.py, test_town_camera.py. Strictly out of scope, minimal change: pause.py and window.py are shared areas (see pitfalls).

SCREENSHOTS AND TOOLS (/tmp)
 /tmp/m_cam45aff_b120.png ("Affichage"), /tmp/m_cam45cmd_b175.png ("Commandes"), /tmp/cam45/ (harness cam45_h.py, t_st.py, t_ndc.py, tr_ckf4.pkl, kaidan.json), RG /tmp/rg_cam45.json.

MERGE PITFALLS
 - pause.py, "Affichage" page: my "Écran du plein écran" line (`ecr`) is inserted right after `win`. If the "ui" agent reorders or renames, update the `ORDER` list of DisplayPage in test_window_mode.py (I added 'Écran du plein écran' in 2nd position and shifted `e[2]`) and the fake `J` of this test (valeurs_ecran, valeur_ecran, nom_ecran, note_ecran).
 - pause.py, `_entries_commands`: I added `inverse()`, the "Caméra à la souris" section, 5 'sep' lines with `v=`, and a case in `draw_all`. The changes to the help of the "Touche spéciale" line and of the 4 camera keys are mine too.
 - settings.py: two DEFAULT lines inserted, `SOUND_TEXT_BOOLEANS` extended (another agent probably: add their keys after).
 - test_interface_settings.py: two `OUTSIDE_INTERFACE |=` lines (one per commit).
 - window.py: `set_full_screen` and `_set_full_screen` have a new parameter; `_wheel_release` / `on_mouse_scroll` modified. To watch if the "combat" agent touches `set_fade`, or if another agent changes the toggle.
 - Fake of test_entries.py (`Fake`) depends on the list of copied `Game` methods.

---
