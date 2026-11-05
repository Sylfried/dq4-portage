## Agent aebaa615370b7f262 — 2026-11-01 16:44

Audit finished. Deliverable: /tmp/specs/audit_menus_pave.md (per element, established/assumed kept separate, list of fixes by priority in section 7). Scripts: /tmp/specs/scripts/audit_reproduire.sh (regenerates the listings in /tmp/r4_repro/), audit_values.py (recomputes all the numbers), audit_dis.py, audit_eng.py, audit_scan_itemparam.py, audit_pad_meshes.py. Repository not modified.

Established conclusions (RVA and proofs in the document):

1. TouchPad: c_PadScaleTBL = (1.225, 1, 0.775), not 1.25/1/0.75. Ring = 256 x 0.63 x sc = 161.28 in diameter (port 165). Pills centered at 104/256 = 0.406 of the diameter (port 0.332: wrong). Dead zone 0.124 R (port 0.15), ball travel 0.4526 R (port 0.5), grabbed by a collider of 1.178 R. The fade to 40% after 0.5 s is invented: MOVE_WAIT_TIME and MOVE_LIMIT_ALPHA are dead constants. Orange ball and halo only at the tutorial blink, not during movement. The 8 sectors of 45° are faithful. Game default: g_pad_pos = 1 (D-pad in the center, buttons on the right). Floating ring not established: only the ball follows the finger.

2. HUD buttons: icons (3, 4, 15) and keys (0x1000, 0x800, 0x400) faithful; original plates 72x64 (Map, Commands) and 63x56.8 (Chat), not square; 9-slice plate of the Button sheet (the port uses a gradient chosen by eye).

3. ItemNumCTRL (type 9): passive two-digit counter. Changer(v): v < 2 gives two empty cells, otherwise tens and units. The port ignores it, so the quantities are never displayed. Exact rule in the document.

4. ICityMap (type 25): locations and veil faithful. Minor discrepancies: plane x -223..222.5, z 398..63.875 (scale 0.99) and marker (≤ 2.5 units). Code 4 (red cross, sheet 5 cell 3) is absent. ui_menu.py:187 contains a latent NameError (undefined variable s).

5. Map mode: pipeline bug in tools/ui_il2cpp/layout.py:99. CreateMenuPortItem (0xCE43DC, `sub w2, w21, w0`) passes the type minus the first index of the delegate, but the script passes the raw type. Type 22 is therefore exported with a single button. Original: Mode button in the window at (187.5, -300), plate 64x55.5, icon given by the engine (19 small map, 20 large map, 2 town). The port's HUD fixes the icon at 19. Groups 13-17, 35-37, 58/59, 60/61, 75/76 are probably affected too (to be verified).

6. PortalButton: title screen only, irrelevant for the HUD.

Priorities: (1) layout.py:99 then regeneration; (2) ItemNumCTRL; (3) D-pad constants; (4) ball and halo; (5) remove or keep deliberately the fade; (6) Mode button icon and position; (7) map plane and marker; (8) code 4; (9) NameError; (10) real plates.

To remember (source: this audit): the layout.py:99 bug; g_pad_pos default 1; the buttons on the left are a choice of Sylfried (feedback #36), not an error; the docs notes-visionneuse:300, 305 and notes-technique:87 are to be updated.

---

## Agent ad6ee147e8091d8ae — 2026-11-01 16:45

Spec written: /tmp/specs/unity_avant_partie.md (16 sections, each value marked Established / Assumed / Not found, with RVA or trace). PNGs in /tmp/specs/img/ (boot_*, title_*, dssatex_*), scripts in /tmp/specs/scripts/ (including consts_flt.py, trace_titre2.py), traces in /tmp/specs/work/t2_*.log.

Key conclusions
- Before the game, Unity only draws: 2 logos (sqex, arte; "warning" only in JA), BackColor, Fade, and TapToStart + copyright. The rest (3D title, BGM, menus) comes from the engine.
- Logos: 450x450 square centered (texture 720x720), linear alpha 1 s / 3 s / 1 s (real time), click = skip. Established.
- TapToStart (type 73): quad 223.04x41.48 centered at 228 below the center; copyright 450x40 at 25 above the bottom. Triangle-wave blinking (±0.025/frame, steps of 20 frames, period of 120 frames), first display at frame 720 except for message `[12,0,0]` (CountReset), which launches it immediately and sets the copyright to alpha 1. Without input, the engine waits indefinitely for pad A. 1st A = fade 4126 + CountReset + fade 30. 2nd A = fade + part 3, title menu (type 53).
- Title menu: selection is done by message `[1,idBouton,16]` on port 13, never by the pad. Ids: 0, 1, 2, 3, 8 ("Sauv. cloud"), 11 ("Licence"). New game: `13:1,2,16`, then `14:1,0,16`, then type 55.
- License (id 11): fade 20510, then port 15 type 80; return by `15:1,-1,32` (fade 16414). Established by trace.
- "Sauv. cloud" (id 8): the engine closes the menus, creates a category 4 port (NetConnection) and waits for Unity. Without a reply, the screen stays blocked. To be hidden on PC.
- Google, ObbDownloadRes and PortalButton: dead or ignorable code, proven by the absence of callers.
- Name entry: the engine crashes if `[2,len]` and the packed UTF-8 bytes are not sent on the SAME frame. Recommendation: PC text box, not a 5x7 keyboard.
- No extra button to add: the "Fade bit 14" config is decoded (0x4000 = variant).

Unknowns
- Touch-to-pad routing, and role of the 1st phase of the title.
- Who sets `ApplicationQuit.s_quitStatus = 1` (Android Back assumed).
- InputName: origin of the grid, function buttons, SetMode, final confirmation.
- Make_License window (positions) and LicenseNobu in detail.
- NetConnection replies.
- 3D rendering of the title (ids 8900/8901/8905, BGM packets).
- 30 Hz assumed.

To remember for memory (source: this mission)
- `runall2.make()` requires `DQ_META=/tmp/specs/work/base_extract/assets/bin/Data/Managed/Metadata/global-metadata.dat` in addition to `DQ_IL2`.
- The engine crashes if the name is sent over two frames.
- Type-to-Make table: /tmp/specs/work/type_to_make.txt.

---

## Agent a85a7118884ad1696 — 2026-11-01 17:15

P1 to P5 and the `s` bug are done, in 6 commits on `audit-interface` in `/home/claude/wt-audit` (base 752c7fd). Nothing is pushed, no PR, `dq4-portage` was not touched.

**Commits**: faf7162 (`s` bug), a5d40c6 (P1 church), b3e4ed9 (P2), be149e1 (P3), 4071160 (P4), e6ac6b2 (P5). Each commit compiles.

**Files touched**: `dq4_pc/ui_menu.py` (+165/-8) and `dq4_pc/fenetre.py` (call of `ui_g.tick()` after `eng.step`, and `_ui_monster_x(entries)`). No node identifier is hard-coded.

**Verified**
- **P1**: real engine in the church (save 1). Mouse click and keyboard send the right button on the 5 buttons.
- **P2**: real battle on `btl_pl_d`: the shake (8 frames) and the red at the end of the shake are correct. The blink lasts about 0.7 s.
- **Arrow**: it was never displayed before (the SetActive(true) was missing, confirmed in the disassembly). It now appears only on type 29, id 5.
- **P3**: poisoned and dead do have the skull and the red cross in the Resurrection list; the eye and the yellow are tested with synthetic data.
- **P4**: the marks appear at target selection and are cleared afterward.
- **P5**: "Continuer votre aventure" now has its frame.
- **Renders**: the 72 types are identical before/after. Menu, message and Yes/No are identical. In battle, only the arrow and the marks change. Screenshots in `/tmp/specs/img/`.

**Unverified hypotheses**
- Shake rate at 30 Hz.
- Red exactly at the end of the shake.
- Marks at z=-64 in 16:9.
- Meaning of code 2 of type 54 and position of the back button.
- Hover over the church and shop buttons not tested end to end.
- Docs not updated.

**Other point**: `/home/claude/dq4-portage` has uncommitted modifications by another contributor (`window.py`, `engine.py`, `ui_menu.py`). A merge conflict is possible.

**For memory**
- Church reproducible via slot 1.
- `HaveStatusInfo` is at PlayerStatus+0x10, poison = flag 0x16 (+0x198).
- Headless tests: `xvfb-run -a`, variable `DQ4_SRC`, scripts in `/tmp/specs`.
- Trap: `pgrep -f` in a monitor kills itself.

---

## Agent aba9c8fd03df2b6dd — 2026-11-01 17:27

FINAL REPORT, branch `audit-pave` (worktree /home/claude/wt-pave, from main 752c7fd). Nothing pushed, no PR, `main` and the Project not touched, `self.map_name = s` (ui_menu.py, `param_int`) left for A9.

COMMITS (in French, with the 2 Co-Authored-By / Claude-Session lines)
- 39b406a Fix of the Unity layout (A1)
- 6c127c9 ItemNumCTRL (A2)
- d2825f3 Small map: plane, feather, red cross code 4 (A7, A8)
- 45f0a13 D-pad, button plates, Mode button (A3, A4, A5, A6, A10)
- 0275e93 Notes (the two docs, dated section "Fidelity audit", without PR number)

FIXED
- A1: `layout.py` `export_type` passes `typ - premier rang du délégué dans R.tbl` (proof 0xCE43DC). `GENERATION = 3` (`header.py`). I also changed `launch_dq4.bat` (`gen >= 3`, previously `>= 2`): without this the user's cache would not have been rebuilt. New layout in /tmp/uicache4. Types whose layout changes: 13, 14, 15, 16, 17 (Status pages: 1 node -> 5, 3, 4, 3, 5; the Status screen was empty), 22 (gains the Mode button; new 22 = old 23 + Mode), 35, 36, 37 (BattleIM 8 -> 20, 16, 20 nodes; the battle Items list was empty), 58 (lines moved up by 141 units, line spacing 2.46; the old 58 was equal to 59), 60 (21 -> 31 nodes; the old 60 was equal to 61). Unchanged: 23, 59, 61, 75, 76 and the 69 single-delegate types. No regression observed, so the fix is kept for all the types.
- A2: `ui_menu.Window._item_num`, called from `param_int` for the ItemNumCTRL class (rule of the spec). Verified by injecting quantities (57, 9, 10, 123 -> "23").
- A3: D-pad constants in `hud_mobile.py` (DPAD_DIAMETER 161.28; DPAD_SCALE 1.225/1/0.775; DOT_RADIUS 104/256; DEAD_ZONE 0.124; BALL_TRAVEL 0.4526; DPAD_GRAB 1.178).
- A4: no more orange ball or halo when holding the D-pad; only the pill of the held sector is lit.
- A5: fade to 40% after 0.5 s removed (`croix_t`, ATTENTE_CROIX, ALPHA_CROIX deleted). It was invented: MOVE_WAIT_TIME and MOVE_LIMIT_ALPHA are dead constants.
- A6: Mode button = button of the type 22 window (icon 19/20/2 sent by the engine), clickable with the mouse and the keyboard (M key unchanged). The HUD `mode_carte` button is removed. The HUD is entirely hidden when the map is open.
- A7: map plane x -223..222.5, z 398..63.875 (type 25 only); feather `-223 + 1.740234 px`, `398 - 1.740234 py`.
- A8: red cross of code 4 (sheet 5, cell 3, 21.6 units, `(-227 + lo*1.7578, 402 - hi*1.7578)`, bottom-left anchoring), via `Window.special`.
- A10: HUD buttons with the 9-slice plate `Render.plate` (new parameter `corner=16`), formats 72x64 (Map, Commands) and 63x56.8 (Chat). The procedural gradient remains as a fallback if `Render` is unavailable.

NOT FIXED / WHY
- A9 (`s` undefined): reserved for the other agent.
- Large map (type 26): original position not read, old rectangle (-225..225) kept.
- Default position of the buttons and the D-pad, `g_pad_pos` option, camera rotation bar, PadPos button: not touched (user's choice in #36, or irrelevant on PC).

VERIFIED BY CAPTURE (xvfb)
- Status before/after: /tmp/pave_st_old_b150.png (empty) and /tmp/pave_st_new_b150.png (filled); pages 2 to 4: /tmp/pave_stp_b190.png, b230.png, b270.png.
- Battle, Items: /tmp/pave_cbi_uicache3_b290.png (empty) and /tmp/pave_cbi_uicache4_b290.png (4 buttons).
- Injected quantities: /tmp/pave_qte_b130.png.
- Map with Mode + Back: /tmp/pave_mp_b95.png, b150.png. Click on Mode then closing: /tmp/pave_mc_b100.png, b150.png, b230.png, b310.png.
- Red cross of code 4 (injected): /tmp/pave_c4_b150.png.
- D-pad at rest and held: /tmp/pave_hud_b90.png and b130.png. Interface editor: /tmp/pave_edit_b90.png.
- Simple menus without `ui_layout.json`: /tmp/pave_simple_b90.png, b130.png, b190.png. Last check on HEAD with the gen 3 cache: /tmp/pave_fin_b90.png (the game starts).
- pyflakes: same set of warnings as main on the 5 touched .py files (none new).
- The captures are those of a gallery of empty windows for 58/60/75/76 and 14 to 17, 36, 37; no in-situation rendering.

WHAT REMAINS "NOT VERIFIED" (Sylfried's Windows PC / out of reach)
- Real OpenGL rendering (my captures come from Mesa under xvfb) and cache regeneration by `launch_dq4.bat` (gen 3, a few minutes, once).
- Shops (types 58 and 60): no test save leads there.
- The other groups of types touched by A1 are assumed to read like `Make_MapButton`, the only one read line by line; the captures showed no regression.
- Bottom-left anchoring of the red cross (assumed by analogy with the feather), SmallMapSymbol shader, never received in the test saves.
- Absence of a floating ring and of a fade: established for the TouchPad C# code, not for an external animation; no Android capture available.
- The engine sends 0 as the quantity for all the lines of the test save (non-stacked items): the real rendering of the quantities was only seen by injection.
- Simple menus (without `ui_layout.json`): the map window is not drawn (as before), so there is no more Mode button on screen in this mode; the M key remains.

FILES / FUNCTIONS TOUCHED (for the merge with `audit-interface`)
- `tools/ui_il2cpp/layout.py` (`export_type`), `tools/ui_il2cpp/header.py` (GENERATION), `dq4_pc/launch_dq4.bat` (`gen` test).
- `dq4_pc/ui_menu.py`: `Window.__init__` (+ `self.special`), `Window.param_int` (1 ItemNumCTRL line, right after the ICityMap line `self.map_name = s` left intact), new `Window._item_num`, `Render.plate` (param `corner`), `Render._map` (type 25 rectangle + red cross).
- `dq4_pc/fenetre.py`: `on_mouse_press` (type 22 window, buttons 0x400 and 2), `on_mouse_release` (`mode_carte` branch removed, pad button 2 -> `map_toggle`), `_plan_window` (code 4 + feather position).
- `dq4_pc/hud_mobile.py`: constants, `scale_factor/size_value/dims/rect`, `visible_ones`, `_plate`, `_dpad` (import of `time` removed).
- `docs/viewer-notes-dq4-pc.md` and `docs/technical-notes-dq4-port.md`: corrected passages (GENERATION, gaps, feather, D-pad, plates) + new "Fidelity audit" section at the end of each.
- Probable friction points with `audit-interface`: `ui_menu.py` (`param_int`, `Render.plate`, `Render._map`) and `window.py` (`on_mouse_press` / `on_mouse_release`, `_plan_window`).

GOOD TO KNOW (method)
- I had to undo a first badly split ItemNumCTRL commit (371e588): `git apply --unidiff-zero` had placed the lines at the wrong place. It was reverted before any other commit; the current history is clean and each commit compiles (py_compile).

---

## Agent a9a69c9aad072e46d — 2026-11-01 18:44

Camera-beep report: the camera is fixed, the beep is normal and I changed nothing on the sound side. One commit on the branch `camera-bip`: 75eae46, nothing pushed, `docs/` and README untouched.

**1. Camera: fixed and verified**
- **New criterion**: the lock of the engine's `TownCamera` (+0x3e), read by `Engine.camera_game()`. The "center on the player" option applies only when this lock is 0.
- **Rejected**: the "player locked" flag (`Global.Flag` bit 0x4), because it is set during all the messages while the camera follows the hero. The old criterion (target within 60 units of the hero) also failed: in the prologue the target is only 23 units away, so the room appeared instead of the black "Prologue" screen.
- **During an event**: the game's camera applies as is, with the viewer's 16/9 limits, as if the option were disabled.
- **Transition**: the old smoothing is kept. If the target jumps (map change, shot cut, threshold of 1.5 units per step), the centering follows immediately, without sliding.
- **Verified by captures**:
  - Prologue (slot 2, `mlb1a`, lock at 1 until capture ~368): option enabled pixel-identical to option disabled. After release, the camera centers on the hero.
  - Free exploration church -> door -> `maout` (5 captures, including the map change): pixel-identical to the old code.
  - NPC message in the church (3 captures): pixel-identical.
  - The lock stays at 0 during jars and barrels (engine probe without window), so the centering stays active.
  - `pyflakes`: only the old `selected` warning (line ~1700).

**1bis. Partial or not verified**
- Jar or chest with a message: only in the engine probe without window, not in capture. Since the prologue cannot be replayed with key presses, I could not break a jar in the viewer. The NPC message does pass in capture.
- I could not see a scene with a visible camera with the hero near a map edge.
- I did not verify entering the lock through a slow movement (only cuts and a simulation), nor falls and return spells.
- **My choice**: the 16/9 limits remain applied during the scenes.

**2. Beep: normal, commanded by the engine**
- It is sound effect 300 (packet 35), played by the engine at the start of a message when the player has just regained control. It is the same one as for the page turn.
- Mechanism: `ui_MsgLoop` (0x157044) plays 300 only once, then clears the byte `ui_MsgBeginTalkSE` (lib+0x252388). This byte is re-armed when the player is released (`PlayerManager::setLock(false)`).
- Trace of a jar with a message: jar broken (319, or 320 for a barrel), item icon (326), message opening, then 300. Jars without an item have neither message nor beep.
- The viewer plays a single sound per packet, with the right file (`SE0300`), and adds nothing at the opening of a message. No double playback.
- Not compared with the Android game: the real volume (`vol_b × volume du fichier` here).

**Files touched**
- `dq4_pc/fenetre.py`
- `dq4_pc/moteur.py`
- `/tmp/specs/camera_bip.md`: addresses, traces, established / assumed / unknown.

**To flag**
- Two out-of-scope points, not touched, and the second concerns the title / prologue screens agent:
  - The keyboard keys of the screen buttons (Enter = Commands, Space = Chat, M = Map) do not play 300, whereas the mouse click plays it.
  - In the prologue, the key wait (`cmd_key_wait_type_b`) never receives a raw A: Space becomes `BTN_TALK` and A / B are removed from the gamepad. This blocks automated tests.
- To remember: `Engine.camera_game()` returns (lock +0x3e, mode +0x48, viewpoint lock +0x40, movement +0x43). Prologue value: (1, 5, 0, 0); free state: (0, 0, 0, 0).
- Another agent is still running ("Prologue: chapter frames…"). No xvfb was active when I launched my captures.

---
