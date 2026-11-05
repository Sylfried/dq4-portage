## Agent "chargement" (a3e5cc796bd50fbd6) — 2026-11-02 21:03

FINAL REPORT, mission "chargement" (prefix CH)

Worktree /home/claude/wt45-chargement, branch agent45-chargement (from 84b3f22). Clean working tree, nothing pushed, branch unchanged. No file in docs/ (notes below). No save of Sylfried written (tests in /tmp/sv_*). All commits carry the two lines Co-Authored-By / Claude-Session.

SUMMARY
- Point 1, curtain at launch: PARTIAL. One real cause found and fixed (CH-1). The Windows-specific causes cannot be verified here: defensive measures, not verified.
- Point 2, micro-frames on map change: DONE on the engine and viewer side under Linux/xvfb. The rendering on a real GPU and Windows remains not verified.

COMMITS (in order)
1. f37696e Timestamped tracking of the startup and of the map changes (DQ_SUIVI), diagnostic tool. New dq4_pc/load_tracking.py plus measurement points in window.py. Without DQ_SUIVI, no effect.
2. 6239b16 CH-1: title screen, the 1st frame showed a sky without its side bands (the "curtain effect"). One line in Game._paint_sky: `self._linked_domain = None`.
3. 0be4137 CH-2: drawing hold during a map change.
4. 9848871 CH-3: the loading time is no longer caught up by the engine.
5. 9b06b98 CH-4: Windows launch (DWM transitions disabled, 2nd black frame). NOT VERIFIED.
6. 664c01f CH-2b: the hold counts its own frames (robust to the reloading of a savestate).
7. a5100a6 CH-2c: no camera interpolation on the frame that lifts the hold.
8. 31c5225 CH-3b: absorption limited to a real stall (> 133 ms), at most 3 frames per loading.

POINT 1: CURTAIN AT LAUNCH
Established (DQ_SUIVI log under xvfb, before/after screenshots):
- Cause CH-1. `_paint` only validates the buffers when the domain changes (`_linked_domain`). The title screen sky bands are created after the 1st paint of the frame, so they were not sent. 1st frame: skewed sky with black edges (/tmp/m_chg_d0_b1.png, line 360 non-black from x=278 to 1256). Next frame: full screen. After the fix: x=0 to 1279 (/tmp/m_chg_d1_b1.png).
- Launch timeline: window created hidden at +0.037 s, black frame presented at +0.058, window shown at +0.061. Size 1280x720 at creation, at display and in on_resize: no resizing. Logos 426 frames, worst deviation 107 ms. Title screen: ev01 loads in the 1st drawn frame, and the engine has already done 3 steps, so the title screen fade is at 0.87 at the 1st frame.
- Hypotheses ruled out or with no visible effect under Linux: size then resizing, buffer not cleared, logos/fade desync (13% of the fade already elapsed, not fixed), cache preparation (background thread), wrong camera (already complete at the 1st draw).
- Creation of the off-screen rendering (MSAA) during display: it is now created under the black of the map change hold (CH-2). At the very 1st draw of the title screen it remains in the 1st visible frame. I did not preload ev01 nor the PostFX in the constructor (no visible defect demonstrated, avoids touching the startup code).
Not verified, Windows only (CH-4): DWM opening animation, presentation of a flip on a hidden window, stalls of the 1st frame on a real GPU, full-screen flash (G-004 unchanged).
- `transitions_dwm`: DWMWA_TRANSITIONS_FORCEDISABLED during the opening, restored 2 s after the 1st frame. Any error has no effect (outside Windows: nothing). Tested with a fake dwmapi (3 tests).
- 2nd black frame right after `set_visible(True)`.
Reason: no Windows here. Assumed cause: an opening fade of the window over the black then the logos, or the window's class background during the loading.
If CH-4 changes nothing for Sylfried, it can be removed without risk. CH-1 is the certain fix.

POINT 2: MICRO-FRAMES ON MAP CHANGE
Engine timeline (106 town maps + death → church + church exit):
- frame k: packet 0 (scenery), 8, 9 (fade-in, restarts from opacity 1), 11, 12 (characters created without position), 37.
- frame k+1: packet 10 (camera) and 13 positions.
- k+2: 13 without position.
- k+6 or k+12: poses/directions.
- A few NPCs are only placed later, or never (then at the origin after ORIGIN_AFTER).
- Packet 0 does not reset the camera to zero.
Consequence: at frame k, new scenery + camera of the previous map + no character placed, under 3 to 7% opacity of the scene. Plus, in real time, the synchronous loading of the scenery (the 1st frame of a scene cost 56 to 793 ms) caught up by the engine: 3 steps at once, so the fade jumps.

CH-2, hold (State.loading, engine.py + window.py):
- Set at packet 0 if the screen is covered: opacity ≥ 0.9 on a layer, or a fade-in of more than one frame started in the same batch.
- Lifted by State.update_loading: at least 1 engine frame, camera received, visible characters placed (2 waiting frames at most), tiles received on the world map, safeguard 6 frames.
- During the hold, Game._draw_scene only draws the black and the fades (same path as "scene not arrived"), and tick_fade suspends the fade-in. The fade durations do not change: the fade starts one frame later, on a complete scene. Verified by test (exact duration preserved).
- The off-screen rendering is created under this black.
CH-3 (+CH-3b): after `_load_map`, `t_loop = None` (the engine clock restarts). `_absorb_blocking` does the same for a frame of more than 4 steps among the 3 following a loading. My 1st threshold (2 steps, 6 frames) froze the engine on a slow software rendering (6 frames in a row at the same engine step): measured, fixed in CH-3b.

Before/after measurements (engine-only harness /tmp/chg/measure.py, default setting fade speed x2). A "faulty frame" = engine frame where the scene is visible at more than 2% while camera, characters or tiles are not in place.
- 106 town maps by teleportation (/tmp/chg/o_tpmax_*.txt): 111 faulty frames before, 0 after. The oracle reports 4 on one map (mom2f1). It is an NPC that the engine itself only places 6 frames after its creation, at the origin: engine behavior, not the hold's. Hold: 1 frame (105 maps), 2 frames (1 map).
- Death → church (slots 1, 2, 4, monster 100): 2 loadings each, with 1 faulty frame at 7% before, 0 after (/tmp/chg/o_mort*_*.txt). Slot 4, forced battle: 'ev01 → btl_pl_d' then 'btl_pl_d → mak1f1', same result.
- Church exit, slot 1 (/tmp/chg/o_marche*): mak1f1 → maout, 1 faulty frame before, 0 after. Loading of the slot (ev01 → mak1f1) same.
- Teleportation from the world map (slot 4, 10 maps): 10 faulty frames before, 0 after.
- World map: entry/exit without packet 0 (27/28), covered by the existing safeguard "world map not sent". The hold does not intervene. At the step where the tiles arrive, the fade is at 0.87 and the hero is placed.
- Viewer under xvfb, real time, software rendering, mak1f1 loading (logs /tmp/suivi_tr_avant.txt and /tmp/suivi_tr_apres.txt):
  - before: 1st visible frame at fade 0.80, then engine jumps +3/+2.
  - after: 3 black draws 'noir (retenue du chargement)' at fade 1.00, then 1st visible frame at fade 0.93, camera and 3/3 characters in place, regular fade (1 engine step per fade step).
- Viewer, one-step-per-frame mode (/tmp/suivi_ap1.txt): 'noir (retenue)' draw then 'scène' with new camera and 3/3 characters.
- With MSAA 4 (/tmp/suivi_msaa.txt, also launched without a screen via pyglet headless): same sequence, "Rendu hors écran x4" created under the hold.

No viewer measurement for: door/stairs leaving a building by keys, battle entry/exit with effect, savestate loading.
- Door/stairs: the hero did not move with my test keys. The church exit (mak1f1 → maout) is measured at the engine level, not in the viewer.
- Battle with effect: covered only at the engine level (forced battle).
- Savestate loading: `_apply_savestate` loads the map itself and resets t_loop to zero, no packet 0; I did not run a viewer test.

Not handled, by choice: a hard cut without a fade (screen not covered). It keeps the original behavior, because it would require freezing the last displayed frame. I did not find any case in the tested runs (doors, death, exits, forced battle).

Worth knowing: character poses and directions only arrive at k+6 or k+12, including in the original game. I do not wait for them (that would delay the fade by at least 5 frames).

TESTS
- New tools/test_loading.py: 22 tests (State rules, absorption, interpolation, simulated DWM, original engine on 5 teleportations with --apk/--saves).
- Full suite tools/test_*.py run headless on the final code: all OK. Only two exceptions from my script (argument passing), rerun by hand with the right ones: test_savestate_fixes OK, test_text_scrolling OK (OK before the commits CH-2c/CH-3b, not rerun since; they touch neither the text nor the savestates).
- pyflakes OK on engine.py, load_tracking.py, test_loading.py. window.py: 2 warnings already present at 84b3f22 (dims, sel), not on my lines.

LINES TOUCHED IN THE SHARED FILES (to rebase with "caméra" and "combat")
window.py:
- import load_tracking + hooks SV.note (Game.__init__ start, _create_window, _start_engine, constructor).
- function transitions_dwm before class Game.
- _create_window: 3 lines around set_visible(True) (dwm_cut, 2nd black flip, log note).
- on_draw: 1st frame (DWM scheduling), call of _absorb_blocking, _track_drawing.
- Game._absorb_blocking and Game._track_drawing (methods added).
- _snapshot: field `ret` added (the key `cle`, used by _coupure_camera, is unchanged); _interpolate: one more condition.
- _load_map: a log note at the end.
- _draw_scene: `retained`, `t_loop = None` after the loading, extended black safeguard condition, PostFX warm-up, tag _drawing_kind.
- _paint_sky: `_linked_domain = None`.
engine.py:
- constants LOADING_*.
- State: attribute loading, __setstate__, apply (start, packet 0, packet 10, block after the loop), update_loading, line in tick_fade.
- Engine.step: call of update_loading before tick_fade.

NOTES TO MERGE INTO docs (ready to paste)
Full text in /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/notes_chargement.md (sections: timeline of a map change, drawing hold, _linked_domain rule, loading stalls, DQ_SUIVI, Windows).
Key points:
- At packet 0, State.apply does not reset the camera to zero: camera, characters and tint arrive at k+1.
- Drawing rule: any vertex list created or rewritten after the 1st `_paint` of a frame must reset `self._linked_domain = None`.
- DQ_SUIVI=1 (console) or DQ_SUIVI=path gives a timestamped log of the launch and of the 16 draws that follow a loading.

TO REMEMBER (learned in this mission, no memory modified)
- The viewer launches without X nor xvfb lock: set pyglet.options['headless']=True before importing window (scripts /tmp/chg/after_viewer_h.py and avant_viewer_h.py). Useful when the /tmp/xvfb.lock queue exceeds 15 tasks (wait of more than 30 min measured this evening).
- /tmp/chg/measure.py (engine only, before/after mode) and /tmp/chg/analysis_tracking.py (DQ_SUIVI log reader) are reusable.

PROOF FILES
/tmp/m_chg_d0_b1.png (before) and /tmp/m_chg_d1_b1.png (after); /tmp/suivi_ap1.txt, /tmp/suivi_msaa.txt, /tmp/suivi_tr_avant.txt, /tmp/suivi_tr_apres.txt, /tmp/suivi_tr_h_*.txt; /tmp/chg/o_*.txt (engine measurements).

---

## Agent "texte" (af2afb0233cfb4a16) — 2026-11-02 21:19

REPORT TX (agent45-texte). Summary: the viewer's vertical / horizontal placement is ALREADY identical to the original game, so there is no viewer / mobile offset to fix. The text "too low" also exists in the original game. I nevertheless applied, as requested, a global fix in a single place: an optical recentering, which deliberately departs from the mobile. It is in a separate commit that you can discard if you prefer to stay faithful.

1. BY POINT

a) Root cause of the viewer / game offset: DONE, no offset. ESTABLISHED.
- The game uses Unity TextMeshes (anchor 0-8, alignment, characterSize, lineSpacing exported in `ui_layout.json`). It is not a UI Text component nor TextMeshPro.
- The engine sends the monster group names in the form `'Nom\n\n\t×2'`: 3 lines (break, empty line, tab, ×2). I read it in the battle log with `TXSTR` / `TXPLAQ`: `'Glacyclone\n\n\t×2'`. This is why "×2" is 2 line steps below the name.
- The mobile screenshot (ecran4) and the PC screenshot (ecran3) have the same scale: 1.688 px per unit (frame lines at 754.5 px).
- "Ragnar" text of the tab: line profile identical pixel for pixel on the PC and the mobile. The baseline is 8 px above the window body line on both sides, and the left edge 30.5 px from the frame line on both sides.
- Current viewer formula (block of N lines with step = leading 23.525 × characterSize × 0.1 × lineSpacing, top / middle / bottom anchor, baseline at ascent 18.887 below the top of the line, dy bias of 20): it reproduces the mobile's baselines to within ±0.6 unit.
  - "Rat volant" (1 line): −13.4 units below the button center; mobile −13.5.
  - "Scarapince" / "×2" (3 lines): −3.3 / −23.9; mobile −3.4 / −24.2.
- Off-screen rendering of type 33 (target choice) at the mobile's scale: tabs, "Rat volant", "Scarapince / ×2" within ±1 px of the mobile screenshot.
- PC plate "Scarapince ×2": baselines 46 and 82 px below the inner top edge; mobile button (same string): 47 and 82.
- Cause of the "too low":
  - Unity places the baseline at `ascent` below the top of the line whatever `lineSpacing` is (glyph data).
  - The game's `lineSpacing` values (0.441 targets, 0.481 monster plates, 0.801 tabs / buttons / names, 0.873…) shorten the line box; they are tuned for the Japanese font.
  - The ink of SE-GARRIR, centered in its natural 23.5 px box, therefore sits (1 − lineSpacing) × 23.525 × characterSize × 0.1 / 2 below the center of its box.
  - This gives 6.5 units (11 px at 1.688) for "Rat volant" and the monster plates, and 2.3 units for tabs and buttons.
  - This is what sticks "×2" and "Rat volant" to the bottom of the frame.
- ASSUMED: for the top and bottom anchorings, no mobile reference. The ink / box offset does not depend on the anchoring, so I apply it the same way, but I could not compare it with the mobile (name in the status band, monster plates).

b) Global fix: DONE (deliberate departure from the original game).
- Function `text_recentering(leading, u, ls)` in `dq4_pc/ui_menu.py`, called only once by `Render._text`. It raises the text by (1 − ls) × leading × u / 2 when `lineSpacing` < 1.
- It applies to all menu and battle texts that go through `Render._text`, only with the SE-GARRIR font.
- `lineSpacing` ≥ 1 ("PV" / "PM" / "Nv.", lists): unchanged, they are tuned on the gauges.
- `DQ_TEXTE_ORIGINAL=1` restores the exact placement of the game. No setting in the Pause menu: that would have touched `pause.py`, `settings.py` and `window.py`, areas of the other agents. If Sylfried wants a button, it is a 3-line addition (key `texte_recentre`, `default=True`, `pause._choice`).
- Interpretation adopted: Sylfried asks to improve the alignment (« rien que tu puisses faire ? » (EN: "is there nothing you can do?")) so we depart from the mobile. If you prefer to stay faithful to the mobile, discard the commit f756c63; the first commit has no visible effect.

c) Before / after measurements (ESTABLISHED).
- Off-screen rendering at the scale of the screenshots (`/tmp/tx45/t33_cible_viewer_original.png` and `_recentre.png`):
  - "Rat volant": ink centered on the button, 0.6 px off versus 11 px before.
  - "Scarapince" / "×2": margins 13 / 11 px in the button; before, "×2" touched the bottom.
  - "Doc" header of the status plate: ink center 5 px below the center of the band (3 units), 1 px after.
  - "PV" / "PM" / "Nv.": unchanged.
- Real battle screenshots at 1280×720, same frames, `DQ_TEXTE_ORIGINAL=1` versus default (`/tmp/tx45/c_avant_126.png`, `/tmp/tx45/c_apres_126.png`, comparison `/tmp/tx45/combat_reel_avant_apres.png`):
  - "Ragnar" name of the status plate: raised by 2 px, ink center 0.5 px from the center of the band (2.5 px before);
  - "Glacyclone ×2" plate: raised by 5 px, centered;
  - "Ragnar" tab: −2 px; "Attaquer" buttons: −2 px;
  - 3831 pixels change, only in the texts.
- Other windows: 31 types rendered before / after with sample labels (shop 57 / 58 / 60, field menu 4 / 5, start menu 53 / 54, church 66, lists 35 / 36, 3 / 30, "Statut" 13–17…): only the texts move, toward the center, with no visible regression. Sheets `/tmp/tx45/feuille_gA.png`, `feuille_gB.png`, `feuille_g30.png`, `etat_plaques_avant_apres.png`, `commandes_avant_apres.png`.
- Not rendered: the history and the name cartouche (area of the "ui" agent).
- The line breaks fall at the same place as on the mobile (3 lines, "×2" under "Scarapince"): ESTABLISHED on the rendering, from the screenshot. The overflows of French text are not touched (D-133).

2. FIXES (branch agent45-texte, base 84b3f22, clean tree)
- ab76eb9: `first_line_baseline()` isolated in `ui_menu.py`; no rendering change; `tools/test_text_recentering.py` (3 tests aligned on the mobile measurements).
- f756c63: `text_recentering()` + call in `Render._text`; 5 more tests (8 in total). Pyflakes: only the known warning `ax`; test_start_menu_plate (12), test_interface_panel (10) and test_interface_settings (15) pass.

3. NOTES TO MERGE INTO docs/ (to paste into `viewer-notes-dq4-pc.md`, replaces "Ragnar's name too low" from #43)
