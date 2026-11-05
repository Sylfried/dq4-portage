## Agent ac898832ce067746b — 2026-11-02 02:59

REPORT "entrees" agent (worktree /home/claude/wt-entrees, branch agent-entrees, base 08f5785). Clean tree. No push. (Report resent: the first send may not have been received.)

COMMITS
- c4e6378 Entrees (WIP): wheel click, mouse after keyboard, F1 info on the right
- 57dbcfb tests of mouse after keyboard (Esc menu), command help texts, wheel gesture canceled without a button
- cb46c17 original init line kept (fewer conflicts)

EVALUATION OF THE PREDECESSOR'S WORK
Kept: `inputs.py` (pure logic), the `on_mouse_*` wirings and the wheel gesture.
Fixed:
- A debug `print('DBGMOL')` is removed.
- `_drivable_camera` and `_zoom_possible` ignored the license, the "Sauvegardes" screen, name entry and the open map.
- `rotate` did a full yaw turn before clamping when the place limits rotation.
- Point C (F1) was not wired: `info_zone` existed but was used nowhere.

A. CAMERA WITH THE MOUSE (wheel click)
- Held wheel drag: horizontal = yaw, vertical = tilt. Same variables (`self.yaw`, `angle_cam`, `reg['angle_camera']`), same bounds (`CAM_ANGLE_MIN/MAX`, `cam_limite`) and same directions as the arrows (right = right arrow, up = up arrow).
- Sensitivity in named constants in `inputs.py`: `CAM_MOUSE_YAW` = 180° and `CAM_SOURIS_ANGLE` = 120° per window height. It therefore does not depend on the resolution. The direction can be inverted by changing the sign.
- 4 px threshold (`DRAG_THRESHOLD`) between click and drag. When the threshold is crossed the camera does not jump. A drag cancels an animated recentering in progress.
- Simple wheel click: `recenter_camera()`, the same animation as "Touche spéciale + touche caméra" (factored out).
- Ctrl + wheel click: `regler_zoom(100 / DEFAULT['distance_camera'])`, without touching the direction. "Ctrl" = the pyglet modifier OR the "Touche spéciale" of the settings.
- Contexts: the drag and the click only act if `_drivable_camera()` (= `_terrain_free()` + town + not `cam_bloquee` + neither license, nor "Sauvegardes", nor name entry), hence like the arrows. The zoom (`_zoom_possible`) acts in towns and on the world map, outside message, menu, open map, Pause, title, license, "Sauvegardes", name.
- Behavior change of the zoom wheel: it no longer zooms on the title, the license, "Sauvegardes", name entry or the open map (before, only `msg_visible` and `active_menu` were tested).
- The middle button exits `on_mouse_press` / `on_mouse_release` before anything else. It therefore triggers no simulated left click, no menu, no interface editor, no chat. Before, `Pause.click` treated the middle button as a left click. It is also ignored while the D-pad or a game button is held.
- If a movement without a button arrives during a gesture, the gesture is abandoned (lost release).
- Help texts updated in `pause.py`: tooltip of the 4 camera keys, "Touche spéciale", "Distance caméra" and "Infos à l'écran".
- Harness (`window._test_keys`): `%x%y` press of the middle button, `&x&y` drag, `*x*y` release. For Ctrl: `+LCTRL` / `-LCTRL`. Hover alone already existed (`@x@y@2`).

B. MOUSE "UNUSABLE FOR ~1 s" AFTER THE KEYBOARD
Cause: no time delay exists in the code (no timer, no hidden cursor). It is movement thresholds that make the mouse look like a "dead" instrument:
1. `Pause.hovered` (Esc menu, base) compared each event to the previous one (movement < 3 px in Manhattan), `mouse_pos` being updated at each call. A slow mouse, which sends 1 to 2 px per event, therefore never took over before a fast gesture. The same test let a 2-3 px tremor through. And `output()` set `mouse_pos` to None, which ignored the first event.
2. Game: `mouse_freeze` (6 px Manhattan, only after the return from the Esc menu); `on_mouse_motion` switched to mouse mode on any event, even a null one.
Fix at the root: `inputs.MouseGuard`, a single keyboard/mouse memory.
- Each key freezes the pointer's reference position (`on_key_press`, `Pause.key_press`, `Pause.open_menu`, `pause_game(False)`).
- Hover and mouse mode resume as soon as the CUMULATIVE gap from this reference reaches `MOUSE_TOLERANCE` = 4 px (4 events of 1 px).
- A click always acts, immediately, and gives control back to the mouse (`guard.click()`). Unknown position (pointer outside the window): the first movement counts.
- `mouse_freeze` is no longer read (the attribute stays in the original init line, deliberately not touched: to be removed at the merge if desired).
Protection kept, with its reason: a mouse at rest under a menu that opens must not steal the selection from the keyboard. Known case from the notes: Esc selected "Sauvegarde rapide". The tolerance covers the tremor of the sensor or of the hand. Null events are already filtered by pyglet Win32 if my memory of the code is right (not verified here).
Test: `tools/test_entries.py` (37 tests, without a window). The Pause tests fail on the base code (I checked on a `git archive` of 08f5785: 3 failures) and pass on the new version.

C. F1 INFO AT THE TOP RIGHT
- F1 = action `infos`: block of information lines (place, window, settings, sound, performance) in a translucent black frame, which was at the top left. This is NOT the "Interface" editor, whose panel is already at the top right by default.
- The block had no saved or movable position: no migration and no setting key. The brief's point about "moved position / double click / Rétablir l'interface" does not apply. I did not add an option (Sylfried deletes them). If you want it movable, that is another job.
- `_helptext_margin` returns `(side, width)` via `inputs.info_zone`: right side by default, left side if the interface column is on the right (`--ui-pos droite`). The width remains the free margin next to the interface column, with a minimum of 260 px. The frame is stuck at `width - 4`, and its width only grows while F1 is displayed (and is reset if the layout changes), so that the text does not vibrate.
- No change to `settings.py`. `test_interface_settings.py` and `test_interface_panel.py` pass without modification (12 and 10 tests OK).

ESTABLISHED / ASSUMED / NOT VERIFIED
- Established (read in the code or measured):
  - 37 tests of `test_entries.py`, as well as `test_interface_settings` (12), `test_interface_panel` (10), `test_pause_pages` (15), `test_sound_text_settings` (7) and `test_window_mode` (18, 1 skipped) pass.
  - Harness screenshot in town (slot 1, 1280x720): a wheel drag gives "rotation 15 °, angle +10 °", consistent with the constants. The F1 block is indeed at the top right at 1280x720, at 2560x1080 (21:9) and at 960x720 (4:3, text wrapped at 260 px).
  - The drag, the click and Ctrl+click have no effect under a game message or menu (verified in the harness: the church menu blocked the drag) and in all the cases of the list (tests with a dummy `Game` that uses the real methods).
- Assumed:
  - Cause B described above: established by reading and reproduced by a test, but never observed on your PC. Part of the discomfort may come from elsewhere.
  - A real Windows wheel sends `MIDDLE` in `on_mouse_press/drag/release`; Ctrl arrives in `modifiers`.
- Not verified:
  - Feel of the wheel drag on a real Windows mouse: sensitivity, direction, 4 px threshold.
  - Simple click (animated recentering) and Ctrl+click (100% zoom) in the harness: their handling is tested by unit tests but not seen in a screenshot.
  - The combined run `ed` (camera + hover of the Esc menu, screenshots `/tmp/m_ed_b*.png`, log `/tmp/out_ed.txt`) was still queued behind the xvfb lock at the time of handing in. I did not see its images; they may exist now.
  - No screenshot of the slow hover in the Esc menu.
  - No screenshot of F1 at 1080p or in full screen (the logic is the same).
  - The F1 block overlaps the "Interface" editor panel (also at the top right) when both are visible: acceptable, but not seen.

FILES TOUCHED
- `dq4_pc/inputs.py` (new)
- `dq4_pc/window.py`
- `dq4_pc/pause.py`
- `tools/test_entries.py` (new)
- `tools/test_window_mode.py`: one line, `fake_game` receives `mouse=(0,0), mouse_guard=MouseGuard()`, because `on_key_press` now remembers the pointer position.
Useful screenshots: `/tmp/m_ea_b45.png` (rotation 15° and angle +10° with F1 at the top right), `/tmp/m_ef_b40.png` (21:9), `/tmp/m_eg_b40.png` (4:3).

MERGE PITFALLS (zones of `window.py`)
- Import `inputs as EN` (line 23).
- `__init__`: new line `mouse_guard` / `wheel` after the big line `self.yaw...`, left intact. Line `self.helptext = ... helptext_width, helptext_key` modified.
- New: `_zoom_possible`, `_drivable_camera`, `recenter_camera`, `_ctrl_actif`, `_wheel_press` / `_glisse` / `_relache`. They are inserted before `on_mouse_scroll`, whose last line changes.
- `on_mouse_drag` (3 lines), `on_key_press` (1 line `mouse_guard.keyboard`), `pause_game` (replacement of the line `mouse_freeze`).
- `on_mouse_press` (2 lines), `on_mouse_motion` (guard + cancellation of the wheel gesture + removal of the `mouse_freeze` block), `on_mouse_release` (1 line).
- `_maj_camera`: a call `recenter_camera()` replaces the 2 reset lines.
- `_helptext_margin` and `_draw_helptext` rewritten.
- `_test_keys`: docstring and 3 events.
- In `pause.py`: import, `open_menu`, `key_press`, `hovered`, new `_guard`, help texts ("Distance caméra", "Commandes") and variable `infos` in `_entries_commands`.

DOC NOTES TO MERGE (viewer-notes, "Feedback from 02:12 (#43)")
- Inputs. Wheel click (`window._wheel_*`, `inputs.WheelGesture`): simple = camera direction reset (animation of the arrows' recentering); Ctrl (or "Touche spéciale") + click = zoom at 100% without touching the direction; held + movement = rotation and tilt (`inputs.rotate`, same bounds and directions as the arrows; constants `CAM_MOUSE_YAW` / `CAM_SOURIS_ANGLE`, `DRAG_THRESHOLD`). Active only when the arrows are (the zoom also on the world map). Harness: `%x%y`, `&x&y`, `*x*y`, `+LCTRL`.
- Mouse after keyboard. `inputs.MouseGuard` replaces `mouse_freeze` and the per-event threshold of the Esc menu. The reference is frozen at each key, hover resumes at 4 px cumulative (`MOUSE_TOLERANCE`), a click always acts. The tests fail on 08f5785. Cause established by reading, not seen on Windows.
- F1: the info block is at the top right (`inputs.info_zone`), on the left only if the interface column is on the right. No saved position, no setting added.
- Test: `tools/test_entries.py`.

---

## Agent ab93c153d22168574 — 2026-11-02 03:01

REPORT: audit of GitHub issues and decisions (resumption). Read-only respected: repository stayed on main 08f5785 and clean; nothing written on GitHub, in the Project or in memory; `add_repo` not called; `claude/piste-3-projet-unity.md` not opened; saves, FR patch and the other agents' files not touched.

FILES (revised, not redone from scratch): /tmp/audit/github_issues.md (27.7 KB), /tmp/audit/decisions.md (61 KB), /tmp/audit/lacunes_connues.md (38 KB).

1. VOLUMES
- Issues (established, REST): `dq4-portage` 0 issues (issues enabled, 10 default GitHub labels, 0 milestones, 43 remote branches never deleted), 42 merged "Avance #N" PRs, 0 comments. `dq4-pc` (history) 43 issues: 27 open, 16 closed; 36 PRs; 9 comments. Recommendation per open issue in §5 of github_issues.md: 7 to close (#2, #5, #7, #10, #22, #23, #41), 2 to close after confirmation (#40, #17), 16 real, 2 to decide (#6, #57).
- Decisions: 128 D-xx identifiers. Sources: 7 read directly in the transcript [T] (messages from 02:27 to 02:38, all new), quotes copied by Claude [C] (the 23:24 message in full, sentences of the 18:02 and 20:46 batches, the 02:12 message), feedback reported in the PRs [R], 10 entries from memory [M] (D-01 to D-10), Claude's choices [K] kept separate. 21 contradictions (C-1 to C-21).
- Gaps: 161 lines (144 gaps + 17 requests of batch #43). Provisional classification: to verify 97, oversight 19, decision 17, bug 12 (a line may carry two tags).

2. THE 10 MOST SERIOUS GAPS FOR PLAYABILITY (assumed: reading classification)
1. G-092 shops (buy, sell, quantity): coded, never played.
2. G-120 real save at the church then reload: never confirmed under Windows (issue #9, prio:haute).
3. G-093 casino, bank, church: no documented test (to be decided by the coverage agent; the code names only 4 games).
4. G-031 boat, balloon and other transports: never studied.
5. G-001 / G-023 real Windows/GPU rendering and comparison with the mobile: never done.
6. G-044 allocator without release: `MemoryError` possible on a long session.
7. G-070, G-071, G-078 bosses, groups, spell effects, victory / level up / game over: not verified.
8. G-041, G-042, G-043, G-052, G-069 story scenes not replayed: packets 1, 6, 16, 17, 18, 27, 30 and 33 not handled, FEAN, inn, chapters, credits.
9. G-055 invisible walls and the `dbout` staircase; G-079 return to the title from a battle or a shop then new game.
10. G-099 / G-098 keyboard of the made-up name, refused name not tested, "Revenir à l'écran titre" that deletes the autosave.

3. CONTRADICTIONS DECISIONS / STATE (established by reading the code)
- C-1 exclusive full screen still present (`settings.py:78`, `window.py:272`) vs D-30. C-2 option `correction_bords` still present (`pause.py:292`) vs D-31. C-3 "Sauvegarde auto" plate hidden vs D-32. Same for D-46 (`pause.py:286`), D-48 (`pause.py:424-425`), D-49, D-17, D-34: no request from 02:12 to 02:38 is on main.
- C-19: D-47, the default of `camera_centree` is already True in the code (`settings.py:28`); the False would come from `settings.json` (not read).
- C-10 / C-14: D-14 « le jeu prend le dessus, valable pour tout » (EN: "the game takes precedence, valid for everything") has only one coded precedent (the camera, `window.py:987-990`); the rest is not inventoried.
- C-6: "the engine is not modified" vs memory patches. Two are requested by Sylfried (D-123, D-124), the others are Claude's.
- C-21: he cited an example of a useless editor choice, Claude removed 18.
- C-7: title sky « garder tel quel » (EN: "keep as is") vs « pattern répétitif » (EN: "repetitive pattern"). C-11 / C-12: outdated docs and README (tracking by issues, `Closes #`, "next issue #1").

4. CORRECTIONS TO WHAT THE PREDECESSOR OR THE BRIEF HAD
- ERROR NOT TO REPEAT: the 02:37 message says that the battle speed changes animations and dialogues, but NOT the music nor the sound effects (D-18). I had first read it backwards, it is corrected in the files.
- The 23:24 message exists in full (brief42): it was not "truncated". It contains a decision of principle absent from the register: show the back of the scenery if the mobile shows it (D-29d).
- Sylfried did ask to review the blurry shaders (D-131): the removal of "Bicubique" and "Régions lissées" answers his request, even if the choice of the two shaders is Claude's. The overflow of French texts is, for its part, a non-issue for the port (D-133).
- Ambiguous "notes l.N" references, all replaced by NV:N / NT:N. Also corrected: PR #36 (D-pad factors: proven or removed in the audit of #39), 30 Hz (engine established, Unity fades assumed), lines of `emu_core.py`.

5. WHAT I COULD NOT READ (not verified)
- Repositories `dq4-portage-unity` and `dq456-traductions-fr` (access not enabled, deliberately not bypassed), `claude/piste-3-projet-unity.md` (instruction).
- `Menu_Echap_DQ4_PC.xlsx` (absent from the repository).
- Sylfried's messages from before the compaction are known to me only through the brief, the missions and the PRs: the 20:46 batch has 21 points, I only have the text of about sixteen; those of 18:02 are partial.
- The Project reading tool is not available to me: I used the copies `/home/claude/pjdocs/`.
- No access to Windows/GPU, nor to his `settings.json`, nor to his saves. GraphQL unavailable, REST only.
- The old conversations gave nothing useful (Unity and FR patch only).

6. FACTS FROM MEMORY
Only D-01 to D-10 (§1 of the register, marked [M]): 16/9 project first, APKs already FR-patched, routes A/B/C, project separate from the FR patch, Claude manages all git, three repositories side by side, Unity track paused. The memory stops at 2026-10-30 22:50 for the port: it contains no decision from 2026-10-31 to 2026-11-02. No suspicious instruction found in the memory or in the documents.

7. TO REMEMBER (decision of the main session; source in brackets)
- The game takes precedence over the player's settings when a script changes the value, « valable pour tout » (EN: "valid for everything") [message 02:12].
- Exclusive full screen removed, F11 / Alt+Enter alternate between full screen and windowed [02:12].
- What must always be active is not an option: edge correction [02:12], texture smoothing [02:27].
- Battle: three speeds "Normal" / "Rapide" / "Très rapide", without speeding up music or sound effects [02:35, 02:37].
- Message history with the name of who is speaking [02:36].
- F1 at the top right by default [02:14].
- Rule "never delete a button that was not named" [23:24].
- Central portrait zone = the phone's view; show the back of the scenery if the mobile shows it [23:24, 02:12].
- Texts that overflow belong to the translation project [20:46].
- Sylfried often delegates the detail (« je te laisse choisir » (EN: "I'll let you choose"), « ne le fais que si c'est pertinent » (EN: "only do it if it's relevant")): Claude decides, then says so.
- Time zone Europe/Paris (UTC+1), established by the transcript.

---
