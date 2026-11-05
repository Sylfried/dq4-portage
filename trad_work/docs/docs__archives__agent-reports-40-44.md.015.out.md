## Agent a0be64ffc1ded4a4a — 2026-11-02 12:24

FINAL REPORT - mission "casino and bestiary" (agent 44, CAS-*)

Worktree: /home/claude/wt44-casino, branch agent44-casino. 10 commits on top of ab22007. Clean tree, nothing uncommitted. No push, no branch change, no PR.
Tests: test_casino_bestiary (28), test_battle_speed, test_game_priority, test_town_camera and test_title_camera pass. pyflakes reports only 2 "unused variable" warnings already present on main (window.py `sel`, ui_menu.py `ax`).

Files touched: dq4_pc/window.py, dq4_pc/engine.py, dq4_pc/ui_menu.py and a new file tools/test_casino_bestiary.py. ui_menu.py (`Window.code()` + `_mask_code`) is the only one that goes beyond the window/engine/ui_menu list to report: no, the three authorized files are enough. No FR patch file or user save touched. history.py, ui_history.py and the "historique" page of pause.py are not touched. State.apply is not touched.

## 1. Findings (ID | what | evidence | status | class | fixed?)
| ID | what | evidence | status | class | fixed / effort |
|---|---|---|---|---|---|
| CAS-1 | Invisible poker: parts 0xf/0x10 unknown to the viewer, drawing guard of the dynamic meshes reserved for PART_TOWN | before /tmp/audit/gl_poker_b330.png; after /tmp/m_cas_pks_b700.png (table and cards drawn, hand played) | Established | oversight | yes, f93071b |
| CAS-2 | Poker: touch areas of the cards and "Donner" missing (window code 2, value 63 = bit mask, absent from the exported `fx` table) | full hand played with keyboard and mouse | Established | bug | yes, b9fe007 |
| CAS-3 | Numeric entry menus unplayable with the keyboard (slot machine, poker, tokens type 44, arena 49, bet 47/48): ◀▶ chooses the column, ▲▼ = pads 2/1 on the column | slot machine win obtained with the keyboard (/tmp/m_cas_sl_r02_b_arret.png); token purchase end to end (/tmp/m_cas_pc_phc_03.png); arena bet (/tmp/m_cas_pa_phf_00.png) | Established | oversight | yes, 57fe281 |
| CAS-4 | Esc always opened Pause in 0xf/0x10 instead of the back button of the open window | unit tests + GL scenario | Established | oversight | yes, 8b3b318 |
| CAS-5 | Bestiary: monster not drawn and a slice of the church `mak1f1` behind the list and the sheet | /tmp/m_cas_bk2_b330.png, /tmp/m_cas_bk3_b350.png | Established | bug | yes, dd0d007 (town scenery not painted in 0x10, monster drawn) |
| CAS-6 | Bestiary: ◀▶ of the sheet and L/R of the list wrongly routed; "Action" key (pad 0x800) | same | Established | oversight | yes, dd0d007 |
| CAS-7 | Accelerated walking possible in 0xf/0x10 (the held arrows are used for the menus); "Casino" / "Bestiaire" place absent from the savestates | tests; state loading in poker OK (/tmp/m_cas_e1_03_apres_load1.png) | Established | oversight | yes, 725bfcb |
| CAS-8 | Regression of my camera tests (method `_libre` on fake objects) | test_town_camera | Established | bug (in my code) | yes, 80854c1 (module function `camera_free`) |
| CAS-9 | Monster arena, battle: (a) the message "X a remporté la victoire !" never advances with the keyboard (the "Quitter" window, type 71, a single pad 0x400 button, swallowed A); (b) the V key has no effect (the "Quitter" window open throughout the battle counted as a player wait) | before /tmp/m_cas_ar_a3_fin.png (blocked); after /tmp/m_cas_ar3_b2_036.png ("Félicitations ! Vous avez gagné 33 jetons !", window type 51 "Jetons 497 / Gagnés 33"), return to 0xc then new bet /tmp/m_cas_ar3_b2_040.png. Speed measured in real time (DQ_TEMPS_REEL=1), battle of 900 engine steps: x1 = 31.1 s; x3 before the fix = 31.1 s (no effect); x3 after = 12.4 s (about 2.5 times faster) | Established | oversight | yes, bd7a2ef (A) and ea2d593 (speed) |
| CAS-10 | Pause (Esc), savestates, battle speed (V), game priority in 0xf/0x10 | V in casino: no engine acceleration; Esc = back or Pause; savestate load/save in poker OK; no crash | Established | verification | nothing to fix |
| CAS-11 | Access: poker/slot machine = `ChangeShopMenuPhase` 0xe / 0xd (see §3); Chandor casino `hcy1b1` rendered (/tmp/m_cas_h1_00_hcy1b1.png) | captures | Established | decision (doc) | n/a |
| CAS-12 | Tokens (44) and prizes (45, 46): playable with the keyboard end to end (token counter, prize exchange with target) | /tmp/m_cas_pc_phc_03.png; /tmp/m_cas_pg_ph5_00.png and _02.png | Established | n/a | nothing to fix after CAS-3 |
| CAS-13 | Colosseum (68, phase 0x16): engine crash (`checkHaveYakusou` -> `BaseHaveItem::getCount`, invalid pointer) with a chapter 1 save | trace | Assumed artifact of the artificial call (no chapter 2 party / Alina) | decision | cannot be verified here; a chapter 2 save is needed |
| CAS-14 | "ERROR 3080@" in some casino NPC dialogues | /tmp/m_cas_t1_s10_00.png | Assumed: text bank of another chapter | n/a | no |
| CAS-15 | Bingo animation (packet 6) | not rendered | Established | "paquets" agent | no (outside scope) |
| CAS-16 | H key (history) inactive in 0xf/0x10 | code reading | Established | coordinator (instruction from the 2nd message) | not touched |

## 2. Fixes per commit
f93071b parts 0xf/0x10 + dynamic meshes; 57fe281 ▲▼ numeric entry; 8b3b318 Esc = back; b9fe007 bit-mask code (ui_menu.py); dd0d007 bestiary; 725bfcb non-accelerated walking and place; 80854c1 `camera_free`; db4c335 tests (22 cases, 28 with the next two commits); bd7a2ef arena: A advances the page; ea2d593 arena: V speeds up the battle.

## 3. Notes to merge into docs/ (text ready to paste)
- Engine parts: 3 start, 0xc town, 0xd battle, 0xe world map, 0xf casino (`Global::startCasino`, `setMinigame(0)` = poker, map `ev04`, type 48; otherwise slot machine, map `ev05`, type 47), 0x10 bestiary (`Global::startBook`, type 28, the town map stays loaded but is not drawn). Constants: `ENGINE.PART_CASINO`, `ENGINE.PART_BESTIARY`, `ENGINE.MINIGAME_PARTS`. In 0xf/0x10 the dynamic meshes are drawn; the casino camera follows `camera_free(e)` (cam_rot present); no accelerated walking, `_speed_factor` returns 1.0.
- Reaching the minigames without walking through them by hand: map `hcy1b1` (Chandor basement, slot machines uid 1416-1420, token counter uid 1410/1411, prize chests uid 1413-1415, monster arena pit 154/159); second casino `ss5b1b`. Direct call: `c.call(m.E('_ZN6window13CommandWindow19changeShopMenuPhaseEi'), c.export('_ZN16TownWindowSystem11m_singletonE'), phase)`. Phase table: 1/7 church (66), 2/8 weapons (57), 3/9 armor, 4/0xa/0x12 items, 5/0xb prize exchange (45/46, asks for tokens), 6 inn, 0xc token counter (44), 0xd slot machine (crashes outside a casino part), 0xe poker (48), 0xf arena (50 -> 49 -> battle), 0x10 bank, 0x11 mini medals, 0x13 castle armor sale, 0x15 type 13, 0x16 colosseum (68, crashes without a chapter 2 party), 0x17 party exchange, 0x18 Torneko, 0x1a save.
- Keyboard in the numeric entry menus (types 44, 47, 48, 49, 64, 65): ◀▶ chooses the column (1/10/100/1000/10000 for 44), ▲▼ = pads 2/1 on the active column, A validates, B goes back. Lists 45 (items 0-5, back -1), 46 (targets 0-3 + page arrows), 50 (monsters 0-3).
- Arena: battle in part 0xd, map `btlcc2`. During the battle, the only open window is "Quitter" (type 71, button id 0, pad 0x400): it has neither engine validation nor cursor. Viewer rule: in battle, a window without a 0x10 button and without a grid leaves A to the field (key word of GameUpdate) and is not a player wait (`without_validation`). End of battle: victory message, then window type 51 ("Jetons" / "Gagnés"), return to 0xc.
- Bestiary in the real game: the field menu (Enter key) has "Objets" / "Magie" / "Carac." / "Divers"; "Divers" page 1 = "Soigner tous", "Équipement", "Alignement", "Organiser les objets"; page 2 = "Trier contenu sac", "Résultats combats" (type 19: duration, battles, victories, title), "Paramètres" (opens the viewer's options page). No "bestiaire" button found: `TownMenuItemSelectCommand::menuUpdate` calls it, but the real access route remains to be found (see §4). To test it: call `startBook` directly.
- Harness pitfalls: the GL scenario is driven by `Game.tick`, called at every engine step (not at every displayed frame): `yield 45` = 45 engine steps. To measure a speed, compare real durations with DQ_TEMPS_REEL=1 (otherwise `fixed_test`: one step per frame, no acceleration). Opening Pause (Esc, or "Paramètres" of "Divers") stops the ticks and freezes the scenario: artifact, not a bug. Repeated `set_jetons` desynchronizes the engine counters (slot machine blocked at spin 12: artifact). Only one xvfb at a time (flock /tmp/xvfb.lock); the queue is shared with the other agents.

## 4. Not verified / still to be played
- Colosseum (type 68, phase 0x16): impossible without a chapter 2 save (Alina). To be replayed with such a save.
- Real route to the bestiary from the game: explored "Objets"/"Magie"/"Carac."/"Divers" (pages 1 and 2, "Résultats combats", "Paramètres") without finding an entry. The bestiary is verified by direct call only (list, sheet, monster drawn, return).
- Poker: the "Abandonner" label might overlap another element: not verified, I do not assert it.
- Bingo animation (packet 6): for the "paquets" agent.
- Before/after of CAS-9(b) measured by monkeypatching `_wait_for_player` (old behavior), not by checking out an earlier commit; equivalent by construction.
- Slot machine: maximum bet observed 5; the payout is credited after the message.

## 5. Merge pitfalls
- `_menu_input` (window.py, around line 1622): my ▲▼ generalization fits in 1 line before `if pages and ...`: `if not f.get('grille') and len(z) <= 1 and self._step_entry(port, f, fe, z, decl): return`, with the new methods `_step_columns`, `_active_step`, `_step_entry`, `cursor_step` and `_cursor` which returns the active column. The `if pages ...` block (page arrows, `_page_arrow`, Action 0x800) comes right after, then `if f.get('grille') or len(z) < 1:`. The 3 lines of the "services" agent placed just before `if f.get('grille') or len(z) < 1:` must stay AFTER my `_step_entry` block and my `pages` block; if its shop ◀▶ apply to single-column menus, check that they do not come before `_step_entry` (the keyboard bank depends on it: the bank bet is a numeric entry menu; ◀▶ = columns, ▲▼ = pads 2/1).
- Module functions added in window.py: `camera_free(e)` (used by `_town_camera`, `_game_border` and the mesh drawing) and `without_validation(eng, ui_g, port)` (before `matrix`). The camera and speed tests use fake objects: do not replace them with methods of `Game`.
- `_speed_factor`: early return `1.0` for `MINIGAME_PARTS`. `_wait_for_player`: a window without validation in battle is no longer a wait. Tick line: `if port is not None and eng.msg_visible and decl & ENGINE.A and self._quit_only(port): port = None`, after the `input_buf` test and before `_keyboard_port`.
- `_esc_back` has a MINIGAME branch and `_can_go_back`; mesh drawing guard extended to `ENGINE.PART_TOWN + ENGINE.MINIGAME_PARTS`; bestiary scenery skipped (`if e.part != ENGINE.PART_BESTIARY: self._paint_scenery(True)`).
- ui_menu.py: `Window.code()` calls `_mask_code(e, c)` when the code is not in `fx` (poker, code 2 value 63).

## 6. Useful captures
/tmp/m_cas_h1_00_hcy1b1.png (casino), /tmp/m_cas_pks_b700.png (poker), /tmp/m_cas_sl_r02_b_arret.png (slot machine win), /tmp/m_cas_pc_phc_03.png (tokens), /tmp/m_cas_pg_ph5_00.png and _02.png (prizes), /tmp/m_cas_pa_phf_00.png and _01.png (arena: list, bet), /tmp/m_cas_ar_a3_fin.png (before: victory blocked), /tmp/m_cas_ar3_b2_036.png and _040.png (after), /tmp/m_cas_bk2_b330.png and /tmp/m_cas_bk3_b350.png (bestiary), /tmp/m_cas_dd2_dd_04.png ("Divers" page 2), /tmp/m_cas_dd3_dd_06.png ("Résultats combats"), /tmp/m_cas_e1_03_apres_load1.png (state loaded in poker). Speed measurements: /tmp/out_cas_v1.txt, /tmp/out_cas_v3.txt, /tmp/out_cas_v3old.txt. Scripts outside the repo: /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/cas/ (sc_arene2.py, sc_divers2.py, run_scen.sh).

## 7. Facts to remember in memory (source: this session)
- The GL scenario harness of this project counts in engine steps (tick called by `_step`), not in displayed frames; to measure a speed, compare real durations with DQ_TEMPS_REEL=1.
- `ChangeShopMenuPhase` called directly in the engine is the quick way to reach the casino, arena, tokens and prizes (phases 0xc, 0xd, 0xe, 0xf, 5/0xb); the colosseum (0x16) crashes without a chapter 2 party.
- The bestiary (`startBook`) does not appear in the Enter menu/"Divers" of a chapter 1 save; its real route is unknown.
- Tests on fake objects (`SimpleNamespace` + `F.Game.method(fake)`) require module functions or default `getattr`s in window.py.
- `pkill -f` with a pattern present in its own command line kills the shell (exit 144): kill by PID.
