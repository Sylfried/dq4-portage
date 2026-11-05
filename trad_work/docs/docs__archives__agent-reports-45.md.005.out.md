## Agent "magie" (afd84db2f3277f278) — 2026-11-02 21:31

FINAL REPORT, mission "magie" (PR #45, prefix MG)
Worktree /home/claude/wt45-magie, branch agent45-magie (base 84b3f22). Clean `git status`. No push, no branch change, no PR. FR patch files and the user's saves not touched (tests in /tmp/sv_*, RG /tmp/rg_mg1.json, cache /tmp/uicache4).

COMMITS (all with the 2 footer lines)
- 220cd36 Magic: the phantom row of the spell list (code 6 of Make_NameButton) no longer exists  [points 1, 2, 4]
- b340625 Magic: "Coût en PM:<tab>  2", the tab is worth 8 spaces (TextMesh.tabSize)  [point 3]
- 757c841 test of the spell list, of the cost line and of the uses without effect (original engine)  [points 2, 4, 5]
- 670b8a0 Window.code tolerates the fake Window objects of the tests (getattr is_name_list)  [fix of my change: test_casino_bestiary was breaking]
- 061ac13 MG: spell info panel, the cost line and the description fit in their frames  [point 3 and point 4: touches the shared "texte" area, Render._text]
Files modified: dq4_pc/ui_menu.py (+56) and tools/test_magic_entries.py (new, 23 tests of which 8 on the real engine).

POINT 1, reproduction: DONE (Established)
Save slot 1: Ragnar (MP 0) + Doc (guest level 255, 30 MP, spell 196 "Premiers secours"). Field menu, "Magie" (root button id 1), Doc (id 3 of port 5), click on "Premiers secours": I find exactly Sylfried's screens 7 and 8. Screenshots before: /tmp/m_magie45av_b110.png, b180, b250, b320. After: /tmp/m_magie45ap_b110.png, b180, b250, b320.

POINT 2, origin of <ERR 0x07000000.0> / <ERR 0x03000000.0>: DONE (Established)
Root cause: the engine sets the layout of the named button list (Make_NameButton, type 8) through code 6 = preset (NAMES_PRESETS, MenuPortItemTable.name_button_param), which the viewer ignored. Result: a 5th phantom row remained visible and clickable under "Premiers secours" (Doc's list has only one spell). The click sent button 4 to the engine, i.e. a nonexistent spell. The texts <ERR 0x07000000.0> (name missing), <ERR 0x03000000.0> (description missing) and "Coût en PM  0/ 30" are the engine's fallback strings for a missing spell (the "ERROR %d" too). Fix: `Window.code` applies the preset (`_name_entries`); only the rows whose code is not 0 are active; idempotent, unknown preset ignored. The action menu of the items (preset 1, 5 rows) keeps its logic. Tested end to end on the real engine: Doc's list = 1 row (codes [2,0,0,0,0]); name, description, cost, "Lancer", target, effect and MP spent work (MP 30 to 28, Ragnar's HP 20 to 47, message "Les blessures de Ragnar guérissent !" displayed in the message window, name's ";" consumed).

POINT 3, "Coût en PM": DONE for the spell list and the spell info panel; PARTIAL AUDIT
- List (b340625): the engine's text is "Coût en PM:<tab>  2" with TextMesh.tabSize = 8. The viewer's font had no glyph for the tab (zero width), hence the stuck-together "Coût en PM: 2". Unity counts a tab as tabSize spaces: it becomes 8 spaces. Limited to Make_NameButton.
- Spell info panel, type 7 (061ac13): "Coût en PM 10/ 30" (FR) overflowed the right frame (text from 154 to 160 units from x=75 for a frame x 63 to 221; the English version fit). The line (node 2) now carries a right limit `fit_x = CARD_COST_X_MAX = 214` (frame minus the plates margin, 7) and `Render._text` compresses it (minimum factor 0.7; here about 0.88) even with the original bitmap font. The name, "Lancer" and the description do not change. Screenshot: /tmp/m_magie45k2_b110.png ("Évac'" 1/30), b180 ("Protection sacrée" 4/30), b250 ("Multisoin" 10/30), b320 ("Rappel" 8/30), b390 ("Téléportation").
- Not verified: the other windows with a tabSize in the layout: type 20 Make_MemberShift (8), 34 Make_BattleGo (8), 35 Make_BattleIM (8), 31/33/39 (monsters, 25). The same rule (tab = tabSize spaces) would be faithful to Unity there, but I did not generalize it for lack of being able to test in battle ("combat" area of another batch; battle_history.py handles "\t×3" separately). One-line extension: remove `self.is_name_list` from the condition in `Window.param_str`. "Statut" screen and current/max MP on other screens: not audited (the MP screens of the field menu, character lists "PM 30/ 30", display correctly on the screenshots).

POINT 4, spell list: DONE (Established, unless mentioned)
4 rows per page; page arrows and "1/2" (2/2, 4/4 with 13 spells); no grayed-out spell: the engine refuses with "Pas assez de PM !"; keyboard (DOWN moves the cursor, RIGHT turns the page, SPACE confirms, BACKSPACE goes back) and mouse click work; Ragnar alone: game message "Ragnar n'a appris aucun sort ni aptitude pour d'autres situations que le combat !" (screenshot /tmp/m_magie45n_b110.png); only members with spells are clickable.
Another defect found and fixed in 061ac13: 9 of the 18 field spells have a FR description of 3 or 4 lines (cut at about 20 characters) for a 2-line frame; the 3rd line went out of the frame then out of the screen ("Multisoin", "Rappel", "Résurrection", "Téléportation", "Évac'", "Coup d'oeil", "Passage sûr", "Protection sacrée", "Tic-tac"). Beyond 2 lines, `Render._recoupe` replaces the line breaks with spaces and rewraps to the width of the frame (CARD_DESC_X_MAX = 148, the frame goes up to the back button): all 18 fit on 2 lines (k2 screenshots above). The text sent by the engine is not modified; a text that does not reduce its lines stays as is; ≤ 2 lines: unchanged. Assumed: the original mobile also cut these descriptions (2-line frame); I could not verify it.

POINT 5, useless actions: DONE on the engine; DECISION TO BE MADE for the message
Proofs by packet traces on the real engine (RealEngine tests):
- "Premiers secours" on Ragnar at full HP: the engine displays "Doc lance le sort Premiers secours !" then "Les blessures de Ragnar guérissent !" (the same message as at low HP, misleading), and spends NO MP (30 to 30). Rule: `BaseAction::useMp` (0x1a7424) only spends if the byte [this+0x14] is 1 (the action had an effect). On an injured target: MP 30 to 28, HP 20 to 47.
- "Rappel" on a living character; "Antipoison" without poison: "Mais rien ne se passe.", no MP spent (the text b0802000.mpt also contains "Mais il ne se passe rien." and "Mais le sort échoue.").
- "Antipoison" on a poisoned character: "Ragnar n'est plus empoisonné !", MP 30 to 28. "Rappel" on a dead character: "Ragnar revient à la vie !", MP 30 to 22.
- Insufficient MP: "Pas assez de PM !", nothing spent, nothing applied.
- Items (tests on the engine, scripts in the scratchpad): an item without effect is not consumed.
The viewer lets the engine decide and displays its messages (message window verified by screenshot: /tmp/m_magie45m_b390.png). There is therefore no bug on the viewer side. Sylfried's wish (a message of the kind « ça n'a pas grande utilité » (EN: "that's not very useful")) is a deliberate departure from the original, for healing spells at full HP. I did not implement it, it is up to him to decide. If yes: case to detect on the engine side (HP before = HP after, MP unchanged) and message to add in the "effet" area. Not verified: sound playback (only SE ids 300/306/501 observed on the engine side).

NOTES FOR THE DOCS (ready to paste)
- Field spells (engine ids 196 to 216): 196 "Premiers secours" (2 MP), 197 "Soins partiels" (4), 198 "Soins complets" (6), 199 "Multisoin" (10, no target), 200 "Rappel" (8), 201 "Résurrection" (15), 202 "Antipoison" (2), 203 "Téléportation" (1), 204 "Évac'" (1), 205 "Coup d'oeil" (2), 206 "Passage sûr" (2), 207 "Protection sacrée" (4), 208 "Tic-tac" (4), 209 "Mappille" (0), 212 "Détectrésor" (0), 213 "Fouille" (2), 216 "Sifflet" (0). Id 214 ("Discreto") gives a description <ERR 0x03000000.0> and "ERROR 0" (artificial id). Ids 157 to 160, if learned, appear in the field list with names <ERR 0x07000000.0>.
- Button ids: root menu "Objets"=2, "Magie"=1, "Caractéristiques"=4, "Divers"=5; "Magie": port 5 character list (Doc=3, Ragnar=2), port 8 spell list (port 7 = pagination), cmd(8,row) opens the info panel (port 12: name, description, cost "Coût en PM  2/ 30" = cost/current MP, "Lancer"), target = cmd(6,k); spell without target: "Lancer" = row 2 of port 8. Items: cmd(4,2), then cmd(5,3) ("Sac"), port 9 list, port 8 action menu (preset 1), port 6 target. Inputs: A=16, B=32, arrows 8/4/2/1, menu 0x800, speech 0x100. Viewer keyboard: A=SPACE, B=BACKSPACE.
- Make_NameButton: root + 6 row parts; code 6 = preset (NAMES_PRESETS: (number of rows, starting y, step)); row code 0 hidden, 1 visible, 2 on two lines (name raised, cost line). For ports < 12, command 1 does not clear `cases`: the texts of old hidden rows remain but are not displayed.
- TextMesh.tabSize: a tab = tabSize spaces (no tab stops).
- Engine offsets: PlayerStatus = `_ZN6status9PartyData15originalPlayer_E` + 0x530*i; HaveStatus +0x58 (HP +0x22, max HP +0x24, MP +0x26, max MP +0x28); HaveStatusInfo = HaveStatus − 0x48 (StatusChange +0x198, poison id 0x16); HaveAction +0xd0 (getCount, getAction(i), add(id,0), clear).
- Bitmap font (SE-GARRIR): the space advances by 5 px; with it `Render._text` never compressed the text (its condition is `not bm`): any FR overflow is therefore corrected nowhere other than by explicit limits like `fit_x`.

NOT HANDLED / NOT VERIFIED
- Tabs of types 20, 31, 33, 34, 35, 39 (see point 3).
- "Téléportation": destination choice interface not tested (only the start of the info panel is). Battle spell (id 26) of slot 3 not tested. Item descriptions ("Objets" menu) not audited: the rewrapping only applies to type 7.
- Appearance of the tab (8-space gap) compared with the original mobile: Assumed faithful (Unity semantics), not compared with a mobile screenshot.
- Sounds: playback not verified.
- Source of the top frames (name | "Lancer" | cost) and of the bottom frame of the info panel: not identified in the code (the type 7 window has no mesh); my limits 214 and 148 come from measurements on the screenshots (cost frame x 63 to 221; bottom frame up to 155.5, in units). If the layout of the frames changes, these two constants (CARD_COST_X_MAX, CARD_DESC_X_MAX at the top of ui_menu.py) must be revisited.

MERGE PITFALLS
- ui_menu.py: constants NAMES_PRESETS, NAMES_START, NAMES_STEP, CARD_COST_X_MAX, CARD_DESC_X_MAX; `Window.__init__` (is_name_list, names_offset); `Window.code` (code 6 branch); `Window.param_str` (tab and markers fit_x / wrap_x, right before `nd['text']['text'] = s`); new method `Window._name_entries`; `Render._text` ("texte" area): `N = len(lines)` moved after the rewrapping, two lines added (wrap_x, fit_x) and the compression condition becomes `(not bm or fit_x)`; new method `Render._recoupe`.
- The Make_NameButton windows are touched globally (items action menu: logic unchanged).
- Tests of other batches that build fake Window objects must go through getattr (already done in `code`).
- Tests: `python3 tools/test_magic_entries.py` (interface part, 15 tests); with `DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes`: 23 tests OK in 22 s. Also passing: test_casino_bestiary, test_start_menu_plate, test_interface_settings, test_interface_panel, test_pause_pages, test_message_history, test_sound_text_settings. pyflakes: only the known warning `ax` (ui_menu.py:1076, pre-existing).

TO BE DECIDED BY THE COORDINATOR / SYLFRIED
1. Message on healing at full HP (departure from the original, see point 5).
2. Generalize the tab handling to types 20, 34, 35 (battle) after a test in battle.
3. The rewrapping of the descriptions changes how the FR patch text is displayed (without changing the text): to be confirmed against what Sylfried sees on his mobile.

INFORMATION TO REMEMBER (memory, learned in this session)
- Slot 1: Ragnar (MP 0) + Doc (guest level 255, 30 MP, spell 196); field spells ids 196 to 216; "Objets"=button 2, "Magie"=button 1; A=SPACE, B=BACKSPACE.
- The xvfb lock (/tmp/xvfb.lock) is heavily contended: a job can wait 15 minutes and more.

SCREENSHOTS (absolute)
Before: /tmp/m_magie45av_b110.png, b180, b250, b320. After: /tmp/m_magie45ap_b110.png, b180, b250, b320. Spell info panel after 061ac13: /tmp/m_magie45k2_b110.png, b180, b250, b320, b390; /tmp/m_magie45j_b110.png ("Multisoin") and b180 ("Premiers secours"). Casting message: /tmp/m_magie45m_b390.png. Ragnar alone: /tmp/m_magie45n_b110.png. Paginated list: /tmp/m_magie45m_b180.png and /tmp/m_magie45k_b110.png to b740. Sylfried's screens: /tmp/specs/img45/ecran7_pc_magie_liste_cout_pm.png and /tmp/specs/img45/ecran8_pc_magie_ecran_ERR.png.
