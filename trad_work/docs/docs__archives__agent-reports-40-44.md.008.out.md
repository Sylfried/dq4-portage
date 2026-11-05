## Notes for `docs/` (section "Feedback from 23:24 (#42)", I did not write in docs/)
- `bounds_x` is no longer applied when the camera is led by the game; criterion `cam_jeu` = lock +0x3e AND (mode +0x48 in 1..5, or movement +0x43, or target more than 1 u from the hero). Mode 6 or lock on the hero = player regime unchanged.
- Unity does not clamp the camera: `GetEventLimitedPos` CD4EE4 only serves the scenery `map/ev/ev02/out/ev02` (z >= -19.5, `IsLargeAspectRatio`).
- Centering: rigid correction + exponential remainder (14/s, real time) only at regime changes or cuts.
- Aspect: `SetViewAndCenterY` D1F5D0 keeps 9:16 whatever the screen; horizontal field of view 12.67°, vertical 22.3°. Numerical equivalence with the Unity pipeline: 4e-15.
- Route of the prologue up to the frog: save in the OLD folder `.../DQ4/saves/20261007_190735` slot 2 (`mlb1a`). In the NEW folder `dq4-portage/dq4_pc/sauvegardes`, slot 2 loads `caf1`.
- Windowed test tool: virtual-clock bench `/tmp/banc_camera.py`. Usage: `python3 banc_camera.py WT ETATDIR NOM "frame:+Q,..." "captures" NFRAMES [DT]`; environment `AUTO_A`, `AUTO_0`, `AUTO_ALL`, `RG`. Generation of the states of the prologue route: `/tmp/gen_etat_camera.py NOM IMAGE`. Ready states: `/tmp/camst/sv_frog_pre1272/etats/etat_01.dqs` and `/tmp/camst/sv_house470`, `sv_house900`.
- Test pitfall: `/tmp/rg.json` is rewritten by every window close; it contains `angle_camera` = -2.25 (residue). For a clean measurement, use a copy (`RG=...`) or `/tmp/rg_defaut.json`.

## For memory (not written by me)
- Environment: `pkill -f` on a name present in the command line of its own shell kills that shell (code 144). A waiting `flock` can remain orphaned after a kill.
- Slot 2 of the NEW saves folder = `caf1`; prologue in the old folder.
- The user's Screen 6 is the hero's house (father seated at a table), `mlb1a`.

---

## Agent a0a930f3486ff24a2 — 2026-11-02 00:52

REPORT "titre" agent (PR #42) — worktree /home/claude/wt-titre, branch agent-titre, base 345ba8f. Clean tree. No push, no change to docs/, to the FR patch or to the saves.

COMMITS (message footer compliant)
- 60aa233 "Titre : le dragon de l'ecran d'accueil (FbxObject c1018, paquets 31 et 32)" (point 5)
- b76d293 "Titre : textes des credits centres comme le logo" (point 8, window.py only)
pyflakes: only the known warnings (struct, selected).

POINT 8 — CREDITS CENTERED: DONE AND MEASURED
- Cause: the whole `ev01` scene is raised by TITRE_HAUT = 0.3 to center logo + island; the credits (mesh model 8905, drawn by packets 21/22 like the logo) followed this offset whereas the engine places them low in the original image. Before: block center at 0.355 (Horii page, 3 lines) and 0.378 (2-line pages) of the height.
- Fix (_decalage_credits, called from _battle_meshes): for each page, the vertical center of the INK (pixels with alpha > 32 of each line, read from the original texture) is brought back to screen ordinate 0 by a shift along the camera's up vector. The depth does not change, so it is exact at any format. Cached per page. Any error: no shift (single message in the console).
- Measurements (screenshot diff with / without credits via DQ_SANS_CREDITS): block center at 0.5000 to 0.5007 of the height everywhere: 1280x720 (4 pages: Horii 100, Toriyama 240, Sugiyama 370, Majima 520), 1920x1080 and 2560x1080 (21:9) and 1024x768 (4:3) (pages 100 and 240). Horizontal center 0.499 to 0.501.
- Verified: "Touchez l'ecran" and copyright: 0 pixel different before / after (frame 900); sky, logo, island unchanged (the only difference is the dragon).
- Choice: exact centering per page (as instructed). Consequence: the name stays at a fixed height in the original engine, here it rises by 4 px (Horii page) to 18 px (2-line pages) depending on the page, at 720p. Otherwise, canceling only TITRE_HAUT for the credits would give -0.011 / -0.049 in normalized ordinate (2-line pages at ~18 px below the center).
- Observation: once centered, "YUJI HORII" and the top of the island graze each other (the text stays above the island, with no visible overlap).
- Test switches: DQ_SANS_CREDITS=1 (without credits), DQ_CREDITS_ORIGINE=1 (old behavior).

POINT 5 — DRAGON: DONE (to be validated by eye by Sylfried)
Established (read in the engine / the data):
- At the start of ev01 the engine sends packet 31 (cmd_fbx_load: slot 0, model 1018 = Resources "fbx/c1018", FbxObject) then packets 32 (cmd_fbx: bits 8-9 visibility, 0x400 force the animation, 0x800 scale x3, 0x1000 color x4, 0x2000 position x3, 0x4000 rotation x3 in degrees, 0x8000 sequence number). Decoded from the disassembly (RVA 0xD13508 / 0xD136A0, FbxObject 0xCD1528...) and confirmed by the packet log. The dragon is created hidden, rotation (0,180,0).
- Model: 566 vertices, 692 triangles, 31 bones, one bone per vertex, 256x256 texture, 3 clips: "Take 001" 21.98 s (Once, = the 659 frames the engine waits for), "Take 002" 2.18 s (Loop, hovering), "Take 003" 26.78 s. Clip name = "Take %03d" (sequence + 1).
- Shader Custom/ImdChara (read in the data pack): no light, vertex color x _Color x texture, alpha blend, ZWrite, ZTest LEqual, Cull Back, Geometry queue. So the dragon passes BEHIND the logo and the credits (queue 3850, ZTest Always). Backface culling enabled by default (without it, internal faces hid the face: sheet dragon_cull_sans_vs_back_660.png).
- Animation reproduced like Unity Animation: Play / PlayQueued / CrossFade 0.3 s if the previous one is a loop, Hermite of AnimationCurve, time in engine frames at 30 Hz (fraction of a step included). numpy skinning: ~2 ms per frame.
- Observed phases: the dragon appears at the top around frame 510-520, dives to the left around 600, settles hovering above the logo around 660 (the logo appears at ~640), then wing loop until the press on "Touchez l'ecran"; it disappears in the menu (after the press, frame 925).
- Cache: fbx1_c1018.pkl (1.5 MB, ~4.7 s to extract) added to Data._elements / prepare (background preparation). Tested without cache: on-demand reading in a background thread, the dragon appears, pickle written (disposable cache, deleted).
Assumed (to be validated):
- Vertical placement: TITRE_DRAGON_HAUT = 0.0 (constant in window.py, test via DQ_FBX_DY): the dragon keeps the original framing, it is NOT raised with the logo + island group. Raised by 0.3 it would leave the screen (only the claws visible). With 0.0: visible above the logo, head and wings cut by the top edge when hovering, claws that graze the top of the logo (the logo is in front). The original framing also cuts the dragon at the top in the viewer's camera (same vertical field of view as the mobile), but I have no screenshot from a real phone. To keep it whole: increase TITRE_DRAGON_HAUT or reduce the scale (for Sylfried to decide).
Not verified:
- Real Windows GPU (everything tested under xvfb / Mesa). Dragon rendering on a real phone. The 1-frame flash in rest pose at frame 2. The game's other fbx models (clean ValueError and ignored if the shader differs, several skinned meshes, MeshRenderer, compressed animation). The engine's end-of-animation return (m_anim_list, ID_ANIM_END) is NOT implemented: the title engine does not wait on it, but another scene might. The fbx models are only drawn in town scenes (town branch of _draw_scene), not in battle or on the world map. No test on a real user profile with an already prepared cache (only the case of a cache without the fbx file).

FILES AND LINES TOUCHED (outside the strict scope, to watch at merge)
- dq4_pc/fbx.py: NEW (156 lines).
- dq4_pc/data.py: +66 lines, lines 304-369 (fbx_model, _extract_fbx); +1 line, line 394 (_elements); +1 line, line 435 (prepare).
- dq4_pc/engine.py: State.__init__ line 87 (self.fbx / self.image); __setstate__ line 93 (setdefault); line 101 (packet 0: self.fbx.clear() added at the end of a long line: conflict likely if another agent adds camera resets here); branches t == 31 / 32 lines 154-165; Engine.step line 604 (self.state.image = self.frames before apply). Old savestates: compatible (setdefault).
- dq4_pc/window.py: import fbx line 26; __init__ line 211 (fbx_cache / fbx_player); _battle_meshes lines 1003-1004 and line 1013 (credits); big new block lines 1141-1234 between _paint_scenery and _battle_background (TITRE_DRAGON_HAUT, _fbx_ready, _paint_fbx, _decalage_credits); _draw_scene, town branch lines 2644-2645 ("self._paint_scenery(True); self._M_town = M" + "if e.fbx: self._paint_fbx(e)"). _town_camera and the TITRE_HAUT line (lines 97 / 883) NOT touched. No change to the shape of the tuple returned by _battle_meshes.

MERGE PITFALLS
- The camera agent modifies _town_camera and probably the line "M, cam3d = self._town_camera(e, aspect)": my hook is on the next line of the town branch ("self._paint_scenery(True)"). _decalage_credits reads self._M_town (= the final matrix M with the TITRE_HAUT offset): if the camera changes how M is built or renames M, adapt this single line. The sprites agent may touch _draw_scene / _battle_meshes: my 3 credits lines are isolated there.
- The packet 0 line of State.apply (engine.py line 101) is the most fragile (a single very long line).
- The preparation cache now includes an "fbx" element: at the first launch with the old cache, the background preparation resumes for this element only (~5 s).

NOTES TO ADD TO docs/ (I did not write them)
- viewer-notes-dq4-pc.md, section "Feedback from 23:24 (#42) — title": (1) Credits: centered per page on the ink, in the middle of the drawing area (measured 0.500 at 4 formats); test switches DQ_SANS_CREDITS / DQ_CREDITS_ORIGINE. (2) Dragon: animated fbx/c1018 model (fbx.py), behind the logo, TITRE_DRAGON_HAUT = 0.0 (original framing, not raised); DQ_FBX_DY to try, DQ_FBX_CULL=0 to turn culling off; phases of appearance (510 -> 660 -> loop -> disappearance at the menu). Put the vertical placement under "to be validated".
- technical-notes-dq4-port.md: packets 31 (cmd_fbx_load: slot, model; < 0 = release) and 32 (cmd_fbx, bits above); FbxObject = Resources prefab "fbx/c<no>" (SkinnedMeshRenderer + legacy Animation; clip "Take %03d", CrossFade 0.3 s if the previous one is a loop, otherwise PlayQueued); Custom/ImdChara: Cull Back, ZTest LEqual, ZWrite, blend 5/10, Geometry queue; m_defScale 0.4 for model 10 only; State.image; fbx1_c%04d.pkl.

SCREENSHOTS (all in /tmp/titre42/, named copies; sheets to open first)
- Credits before / after (1280x720, 4 pages): /tmp/titre42/credits_avant_apres_planche.png; pages alone credits_avant_{100,240,370,520}.png and credits_apres_{100,240,370,520}.png ("avant" = DQ_CREDITS_ORIGINE=1, old placement; at 520 the dragon is already there in both). State of main without dragon: /tmp/titre42/avant_main_*.png and avant_main_planche_20_620.png / avant_main_planche_640_1500.png.
- Formats: /tmp/titre42/credits_formats_planche.png (4:3, 21:9, 16:9 1080p); credits_apres_{1080,2180,768}_{100,240}.png (2180 = 2560x1080).
- Dragon by phase: /tmp/titre42/dragon_apres_planche.png (frames 520, 560, 600, 640, 660, 700, 800, 900) and dragon_apres_*.png; after pressing Enter (700 and 900): dragon_entree_planche.png and dragon_entree_*.png (the 1st press at 700 skips the sequence: black screen then final title, the 2nd at 900 opens the menu without the dragon).
- Culling: /tmp/titre42/dragon_cull_sans_vs_back_660.png. Variant with the dragon raised by 0.3 (claws only): /tmp/dv_0.3_{600,640,700}.png; variant 0.0: /tmp/dv_0.0_{600,640,700}.png.
- Test tools (scratchpad): credits measurement /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/tools/measure_credits.py (usage: avec.png sans.png threshold).

MEMORY DATA USED: none; this report comes only from the repository, the game data and my measurements.

---

## Agent a8597c32837357eeb — 2026-11-02 01:31

REPORT "sprites" agent — PR #42, points 13 ("!" bubble) and 15 (sprites flattened at the edges)

Worktree /home/claude/wt-sprites, branch agent-sprites, base 345ba8f. A single commit: 299cab5, with the two footer lines (Co-Authored-By and Claude-Session). Clean tree. No push, no branch change, pause.py not touched. The worktrees /tmp/wt-bisect-a and -b are deleted.

=== DONE ===

POINT 15 — sprites tilted / flattened at the left and right edges

Cause:
- The panel of a town character has its vertices offset toward the camera by 0.185 (bottom) and 0.65 (top) along the camera axis (Chara.s_vtxDepthD / U).
- The top, being closer, therefore moves away from the image center by (offset × gap / depth).
- The original portrait, with its narrow horizontal field of view, hid this defect. 16/9 and 21/9 make it visible.
- The viewer keeps the mobile's vertical field of view, so the defect depends neither on the FOV nor on the tilt.

Fix, `Game._town_panel` in window.py:
- The panel is rebuilt on screen: same position, same height, same depths as before.
- Size, overlaps and z-buffer are therefore unchanged.
- The edges become vertical and the width equals 0.74 × the height on screen. This is the panel's proportion at the center, where the width is the average of the bottom and the top.
- At the center of the image, no change.
- The computation goes through the viewer's camera (`cam3d` and `_view_border`). It assumes neither FOV nor pitch.
- Shadows and world (world map): code unchanged.
- Another version tried then abandoned: offset along the view ray. It also gave 0.75 everywhere, but the height varied by ±10 to 20% depending on the position on screen. I rejected it because it changes the size of the NPCs.

Setting `correction_bords`:
- In `settings.py`: default True; 0 or False = as before; a value between 0 and 1 = partial correction.
- An invalid value falls back to the default.
- Command-line option `--correction-bords 0-100`, and environment variable `DQ_CORRECTION_BORDS=0-100`.
- Tested: CLI 0, CLI 50, setting False in the JSON, setting True.

Measurements (scene: Strattbourg, slot 1, hero and NPCs walking south, projection of the 4 corners of each panel). "On screen" = sprites whose feet are in the image.

| Resolution | Distance | Max lean before | w/h on screen before | Max lean after | w/h after |
|---|---|---|---|---|---|
| 1280×720 | 100% | -13.1° | 0.65–0.79 | 0.0° | 0.74 |
| 1280×720 | 200% | -20.5° | 0.66–0.91 | 0.0° | 0.73–0.74 |
| 1920×1080 | 100% | -13.1° | 0.65–0.79 | 0.0° | 0.74 |
| 1920×1080 | 200% | -20.5° | 0.65–0.91 | 0.0° | 0.73–0.74 |
| 2560×1080 (21:9) | 100% | -13.1° | 0.65–0.79 | 0.0° | 0.74 |
| 2560×1080 (21:9) | 200% | -20.5° | 0.65–0.91 | 0.0° | 0.73–0.74 |

- The three resolutions give the same values: the defect depends on the angular position, not on the pixels.
- Right edge: same scene with the camera rotated by 180° (`DQ_LACET`). Max lean before +19.9°, after 0.0°.
- Height on screen: identical before and after (for example 71–79 px at 1280×720).
- Hero at the center: width 56.8 px against 56.2 (bottom) and 57.8 (top) before.
- At 50% intensity, the lean is divided by two (-10.6°).

No regression:
- Title screen (2 frames): 0 pixel of difference.
- Slots 2, 3 and 4 (including the world map, slot 4): 0 pixel of difference.
- Battle: 6 frames compared, 0 pixel of difference (code distinct from `_town_panel`).
- Cave (slot 5): only the sprites change.
- Shader modes 0 (originals), 1 (EPX) and 4 (pixel perfect): correct renderings, lean 0.0°. Mode 4 is the mode of all the measurements above (default setting).
- No anchoring code reads the vertices of the panels: `_anchor_effects`, Morph and damage are unchanged by construction.

POINT 13 — "!" bubble too high

Established:
- No rendering regression between #39 and #41: 0 pixel of difference with the default camera. The bubble code has not changed since d6d9b20, so there is no faulty commit to isolate by bisect.
- Real defect: the bubble was advanced by 0.48 along the axis of the GAME's camera (`fwd`) and not the viewer's.
- Other defect: the engine places it at 1.294 above the feet, in world coordinates, whereas the sprite faces the screen.
- As soon as the player tilts or turns the camera, the bubble drifts relative to the head. Its height relative to the head then depends on the tilt.

Fix:
- Advance of 0.48 along the viewer's view ray (`_shift_depth`).
- Bubble anchored to the character it sits above (`_anchor_icon`): the offset is kept as the game's camera sees it, then carried over to the viewer's camera.

Measurements, bubble of an NPC (the priest of the Strattbourg church). Gap = (top of the sprite's panel - bottom of the bubble) / panel height, more negative = bubble lower on the sprite:

| Condition | Before | After |
|---|---|---|
| pitch -20° | -0.10 | -0.395 |
| pitch 0° | -0.38 | ≈ -0.40 |
| pitch +20° | -0.74 | -0.398 |
| pitch +40° | -1.09 | ≈ -0.37 to -0.40 |
| yaw 45° | -0.33, lateral offset +0.20 width | -0.395, offset -0.013 |
| yaw 90° | -0.22, lateral offset +0.28 | -0.397, offset -0.035 |
| pitch 20°, distance 200% | -0.74 | -0.375 |

- With the default camera, the bubble is at the same place to within about 1 px (less than 2% of the sprite height).
- For pitch +40°, the "after" values come from the previous version of the panel (-0.371 measured), not from the final commit; the gap is in the noise.

=== ESTABLISHED / ASSUMED / NOT VERIFIED ===

Established:
- The figures above.
- The bubble no longer drifts with the player's camera.
- The sprites are straight at all the tested resolutions.

Assumed:
- The user's screenshot (s4, bubble too high) corresponds to a tilted or rotated camera, or to an object lower than the panel height of a character. I could not confirm which.
- The screenshot s5 (flattened peasant) is indeed the off-axis lean: the before/after contact sheet confirms it visually, but the exact position of the peasant in the screenshot is unknown.

Not verified:
- The exact case of the screenshot s4 (green hero + barrels, adventure log 1): the hero stayed stuck against the scenery.
  - For a barrel or a jar with no character underneath, `_anchor_icon` returns the engine's position unchanged.
  - If the bubble looks too high there with the default camera, it is probably the engine's position (1.294 above the feet), identical to the original.
- Windows, no machine: everything is pure numpy and tested only under Linux / xvfb.
- Merge with the other branches: not run at runtime (see below).
- Battle with effects and damage on screen: only the command screen was compared (0 pixel of difference).
- Morph effect at runtime: only read in the code.
- World map with sprites at the edge: slot 4, 0 pixel of difference, but the correction is not applied there (branch without `cam3d`).
- Menu screen with characters: not encountered on the available slots.

=== FOR THE MAIN AGENT: line for pause.py (which I did not modify) ===

- Key: `correction_bords`.
- Values: True (default) / False.
- Proposed label: "Correction des bords des sprites".
- Placement: "Affichage" page, right after "Distance caméra" and before "Centrer la caméra sur le joueur".
- Line, same model as "Centrer la caméra sur le joueur" (pause.py line 270):
  `self._choice('Correction des bords des sprites', [True, False], lambda: R['correction_bords'], lambda v: R.__setitem__('correction_bords', v)),`
- Immediate effect: the setting is re-read every frame, no `regler_*` needed.

=== MERGE PITFALLS (tested with `git merge-tree`, nothing applied) ===

All the conflicts are neighboring insertions: keep both sides.
- agent-camera and retours-23h24: window.py. My methods `_dbg_proj`, `_edge_correction`, `_shift_depth`, `_town_panel` land in the same place as their `_camera_menee`. Keep both.
- agent-fenetre and retours-23h24: window.py, `main()`. Their `--plein-ecran` line (choices 0,1,2) is to be kept, plus my `--correction-bords` line.
- agent-fenetre and retours-23h24: settings.py, `DEFAULT`. Keep `mode_fenetre`, `mode_fenetre_retour` and my `correction_bords` line.
- agent-pause2 and retours-23h24: settings.py, value cleanup block. Keep their two lines `defilement_combat` / `SPEEDS_X_KEYS` and my two lines (validation of `correction_bords` and `defilement_vitesse`).
- agent-titre and agent-editeur2: automatic merge without conflict.
- Semantics to re-read after merging with agent-camera: my computation uses `_view_border` and `cam3d`, it must stay valid if the angle or the FOV change. To re-measure with `DQ_PROJ=40` (see below).

=== FILES TOUCHED ===

- /home/claude/wt-sprites/dq4_pc/window.py: +94 -7
- /home/claude/wt-sprites/dq4_pc/settings.py: +2

Detail window.py:
- `_town_panel` (new).
- `_shift_depth` (new).
- `_edge_correction` (new).
- `_anchor_icon` (new).
- `_icons` (`cam3d` branch rewritten).
- Town sprite loop.
- Option `--correction-bords`.
- Debugging: `DQ_PROJ=n` (pixels of the panels and bubbles) and `DQ_CAMV_SPR=1` (sprites and icons in `DQ_CAMV`).

pyflakes: only warning `selected`, already known.

=== USEFUL SCREENSHOTS (absolute /tmp paths) ===

- /tmp/spr_planche_bords.png: before (top) / after (bottom), 3 NPCs at the left edge and 3 at the right edge, 2560×1080 at 200%.
- /tmp/nr_planche.png: slots 2, 3 and 4 (world), and cave before / after.
- /tmp/nr_combat.png: battle unchanged (6 frames, 0 pixel of difference).
- /tmp/nr_hd.png: Shader modes 0 and 1, before / after.
- /tmp/spr_bulc.png: bubble before / after at default (rendered by an intermediate state of the bubble code, which has not changed since).
- Raw outputs: /tmp/out_mx_*.txt (before) and /tmp/out_mx3_*.txt (after), /tmp/out_bul_avant_*.txt and /tmp/out_bul_apres_*.txt.
- Scripts: /tmp/spr_resume.py, /tmp/spr_resume2.py, /tmp/spr_bulle.sh, /tmp/spr_bulle.py.

=== NOTES FOR docs/ ===

1. The town sprites are panels facing the screen, offset in depth along the camera axis. The offset is 0.185 at the bottom and 0.65 at the top in original units, i.e. ×(w/0.48) in the viewer. This gives an outward lean proportional to the gap from the center, and a height on screen compressed toward the bottom of the image.
2. The correction rebuilds the panel on screen (x/z and y/z coordinates of each corner): same vertical positions and same depths as the original, vertical edges, width = 0.74 × height. `correction_bords` (0 to 1) takes the linear average between the original and the corrected version.
3. The Riseup bubble is set with the viewer's camera, not the engine's. The engine places the icon in the world at +1.294 above the feet. The viewer relates it to the character under it in the game's camera frame, then re-expresses it in the viewer's camera frame.
4. Measurement tools: `DQ_PROJ=n` prints the 4 projected corners in pixels of each panel and of the bubble every n frames. `DQ_CAMV_SPR=1` adds the sprites and icons to `DQ_CAMV`.
5. Test pitfall: the keys of `--touches-test` depend on the settings file. With `touches_v` 4, `A` = E and `discussion` = SPACE, so SPACE no longer advances a dialogue in some configurations. The outputs also depend on `vitesse_marche` of the file passed to `--reglages`. The app rewrites this file on exit: use one copy per scenario.
6. Cache: the current map cache is `carte8_*`. `carte7_*` files written by an old commit linger in /tmp/uicache4 (harmless, never re-read by the current code).

---
