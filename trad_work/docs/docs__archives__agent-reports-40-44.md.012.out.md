- agent-coffres, agent-libelles, agent-options, agent-titre2: no conflict (window.py merges automatically with all of them).
- After merge: grep for "Vitesse de l'accélérateur" (the other agents' branches still have it in their copies of test_pause_pages and help texts; any new test written with the old label will fail); `HM.EDITOR_NAMES` now has 5 elements (tests that count the rectangles); rerun the 3 logic tests above.

=== To remember (session observations, not memory) ===
Xvfb captures go through a single lock /tmp/xvfb.lock: one run waited 15 to 30 minutes behind the other agents. The logic tests run without a display (headless pyglet).

---

## Agent a3199f5d827423698 — 2026-11-02 04:30

FINAL REPORT, PR #43 batch, "histo" agent: message history

Branch `agent-histo`, base 08f5785, one commit: **bb9ca7f**. Clean working tree (only `dq4_pc/__pycache__/` is ignored). `dq4_pc/libelles.py` is NOT committed: it is not in the branch, I copied it to `/tmp/histo_libelles/` for the tests and captures.
Nothing was pushed, no PR, no branch change, `/home/claude/dq4-portage` and the user's saves were not touched (the tests write to `/tmp/sv_*`).

## The 5 points

**1. Capture exactly once, text as displayed**
- Single pass-through point: `TextBuffer::cat` (lib+0x157874), called once per message page, macros already resolved. x1 = UTF-8 text, x2 = speaker name given by the engine (the `@a<nom>@b` of the .mpt).
- The hook (`uc.hook_add(UC_HOOK_CODE, …)`) is installed in `Engine.__init__`, before the first steps: afterwards, the translated-block cache would ignore it.
- We record the cleaned text (`@cN`, control characters and the "*:" prefix removed), the game time (`status::g_Game+4`, 1/60 s, identical to the `duree` field of the saves), the map and the category (t field / c battle / s system).
- Duplicates are discarded (`doublon`): same text, same source, same instant.
- Measured: about 3.8 µs per frame, no perceptible loss.

**2. Who is speaking**
- Priority: explicit engine name > facility (`MaterielMenu_*`, `TownPlayerManager::loadChurch`) > searched object (`TownFurniture*`) > field character > battle (part 0xd or "Battle" in the stack) > "Message général".
- The sources are read by walking back up the stack (frame pointer, x29).
- Header: "speaker · place" for character, object and facility; name alone for an explicit name; "Message général" or "Combat" with no place.
- A text "*: …" (anonymous NPC speech from the FR patch) whose source is unknown becomes "Personnage".
- The place keeps the last known place for the maps `ev*` and `bt*`, and "Monde" on the world map.

**3. "Historique des messages" interface**
- `'historique'` page of the Pause menu. The engine stops as with the Esc menu (`J.pause_game(True)`).
- Game style: original plates, bitmap font SE-GARRIR (`BitmapFont`), golden arrow, darkening on hover, no yellow frame.
- Most recent at the bottom, consecutive messages from the same speaker grouped under one header (≤ 6 and ≤ 20 s of game time).
- Controls: wheel, ↑↓, PageUp/PageDown, Home/End, dragging the bar, Esc or B to close, filter "Tout" / "Combats" (←/→ or button).
- Opened by a configurable key: new action "Historique des messages", **H by default**.
  - H is free: no other default key, nor `RESERVED`, nor digit, nor `K.H` in `window.py`, nor another worktree.
  - It is added in "Commandes" (section "Actions du jeu").
- "Historique des messages" entry at the root of the Pause menu, right after "Reprendre".
- Can be opened during a message without disturbing it.

**4. Memory between sessions**
- Side file `history_messages.json` next to the viewer (option `--historique`), added to `.gitignore`. Never in the user's saves, no save modified.
- A "playthrough" = one adventure, recognized by `status::g_Game+8` (1 useful byte, 0x66 for slots 1 and 4, 0x04 for slots 2 and 5, constant from one save to another).
- Format: `{"version":1,"parties":{"<clé hex>":{"vu":…,"entrees":[[n,t,cat,genre,val,carte,texte],…]}}}`.
- Robust writing:
  - temporary file then `os.replace`;
  - batched (at least 5 s apart, forced on close);
  - corrupted file moved to `.corrompu`, invalid entries ignored;
  - limits: 3000 entries per playthrough, 6 playthroughs, 1500 characters per text.
- Rollback when an older save is reloaded:
  - the game time never goes backward, except in this case; a change must last 3 consecutive frames (margin of 120 ticks) to be taken into account;
  - the entries later than the current time are then deleted;
  - a different playthrough key switches to another list.
- Limits to state honestly:
  - the deletion is destructive (no undo);
  - the 8-bit key can collide one time in 256 between two adventures;
  - saves made before the feature have no history before them.

**5. Tests and captures**
- `tools/test_message_history.py`: 52 tests OK (OK with libelles; without libelles, 1 test skipped).
- Built-in test data generator: `--fixture FICHIER.json [CLE]`, 25 varied entries (key "66" for slot 1, "4" for slot 2).
- Other `tools/` tests rerun, all OK: test_pause_pages (root list updated), test_interface_settings, test_sound_text_settings, test_interface_panel, test_window_mode (1 skipped), test_town_camera, test_sound_mixing, test_text_scrolling (4 tests, with the real engine and the hooks).
- `pyflakes` clean on the new files. 4 warnings remain in `pause.py` (R l.461, yp, mh) and `window.py` (sel l.2203), already present before my work.

## Identifiers actually passed to `libelle_source`

- **NPC interacted with**: an **int**, `State.sprites[8+placement]['id']`, which is also the character index of `TownCharacterManager`.
  - Path: `ScriptGroup::execute` in the stack, then `getPlacementCtrlId()` (int at `L+0x29901c`, address verified at installation by decoding adrp+ldr), then `TownCharacterManager [L+0x26a548+8+8*pid]+0x14`.
  - Placement 0 = global scenario script = narration, hence "Message général".
- **Searched object**: a **str**, the FMAP model name `names[o['i']]`, for example `'015_hondana1'` or `'001_tbox01'`.
  - The numeric uid (`this+0x10` of `TownFurniture*`) is resolved by `HI.nom_objet(objects, names, uid)`; it is accepted only if it is 600 frames old or less.
- **Place**: map name (e.g. `'mak1f1'`, `'caf1'`) or `'monde'` (part 0xe) for `libelle_lieu`. `None` for `ev*` and `bt*` gives the last known place.
- In the delivered code, the import of `libelles` is protected with a fallback: "Personnage", "Objet", place omitted. Nothing breaks without `libelles.py`.

## Established, assumed, not verified

**ESTABLISHED (observed on the real engine or in captures)**
- Explicit NPC name.
- Field character: "Un vieil homme · Strattbourg" (actual label coming from `libelles.py`).
- Furniture: "Un tonneau · Strattbourg", shelf and chest searched.
- Battle: "Combat" for the encounter message (and the fixture group, rendered in capture).
- Narration: "Message général" on the map `caf1` (introduction of slot 2).
- Church: priestess message, in capture with the real engine: "Église · Strattbourg".
- Playthrough key and game time.
- Rollback (confirmed on the engine: the duration goes back when an older save is loaded).
- Persistence, atomic writing, tolerance to corruption.
- Opening and closing during a message.

**ASSUMED (facility label deduced from the symbol name, not seen in game)**
- "Boutique", "Auberge", "Banque", "Roi des médailles", "Arène", "Casino" (slot machine, poker, token room, prizes, stadium), "Sauvegarde" and "Chargement" (`MaterielMenu_*`).
- "Église" via `MaterielMenu_CHURCH` for the cases other than `loadChurch` (which is established).

**NOT VERIFIED**
- Jar messages: same `TownFurnitureItem` code as the chest (verified), hence probable, but not observed.
- Second "item found" message of a jar.
- Battle messages after the first (cause: battles not replayed in the session).
- World map messages.
- A second unreachable chest (hero blocked by a wall in the castle).
- **Windows**: no test possible here (Linux only). Defensive code: atomic write `os.replace`, explicit UTF-8 encoding.

**Known limits**
- A cutscene script driven by NPC X that makes NPC Y speak will label the speaker "X".
- Monsters and 3D models not identifiable (as announced by `libelles.py`).
- Model 34 is labeled "Un noble" by `libelles.py` (the captain of Bastione): it is the classification of `libelles.py`, not mine.

## Files touched and hooks

- NEW `dq4_pc/history.py` (415 lines): `Sensor`, `History`, pure functions (`clean`, `wrap_text`, `en_tete`, `locuteur`, `lieu_de`, `meme_groupe`, `doublon`, `nom_objet`).
- NEW `dq4_pc/ui_history.py` (252 lines): `HistoryView`, `grouper`, `game_time`.
- NEW `tools/test_message_history.py` (524 lines).
- `dq4_pc/engine.py`: import l.6; `self.sensor = Sensor(self)` l.379, right after `self._text_hooks()`.
- `dq4_pc/window.py`:
  - l.19 `import history as HI`;
  - l.184 `self.history = HI.History(getattr(args,'historique',None))` after the creation of `PA.Pause`;
  - l.595 `on_close`: `self.history.store(True)`;
  - l.622 `on_key_press`: opens if `reg.action_of(symbol)=='historique'` outside the title and in the town, battle or field part;
  - l.2588 `tick`: `self.history.do_update(eng, objs, names)` after `eng.step`;
  - l.3058 `main`: `--historique` (default `here/history_messages.json`).
- `dq4_pc/pause.py`:
  - import `ui_history` (l.14); `self.hist` (l.67);
  - `open_menu` (l.179); `_entries_history` (l.201); root entry (l.211); `T('historique')` in "Actions du jeu" (l.441);
  - a one-line hook `if self.screen_page=='historique': return self.hist.X(...)` at the top of `key_press`, `_move`, `hovered`, `click`, `release`, `drag_to`, `wheel`, `draw_all`.
- `dq4_pc/settings.py`: `DEFAULT_KEYS['historique']=['H',None]` and `ACTIONS += ('historique','Historique des messages')`.
- `tools/test_pause_pages.py`: root list updated.
- `.gitignore`: `history_messages.json*`.

## Screen captures

- **Slot 1 (key 66), opened with H during the priestess message**
  - `/tmp/m_w3_b140.png`: before opening.
  - `/tmp/m_w3_b170.png`: history open, 27 messages, last one under "Église · Strattbourg" (real engine capture).
  - `/tmp/m_w3_b220.png`, `/tmp/m_w3_b260.png`, `/tmp/m_w3_b300.png`: navigation.
  - `/tmp/m_w3_b360.png`: after Esc, direct return to the game.
  - Message intact: before/after differ only in the torch area (538–740 × 446–496, flame animation). The message window is identical.
- **Slot 2 (key 4)**
  - `/tmp/m_w4_b170.png`: list, fixture of 25 entries.
  - `/tmp/m_w4_b260.png`: scrolling with the "Combat" group.
  - `/tmp/m_w4_b300.png`: "Combats" filter.
  - `/tmp/m_w4_b400.png`: closing, then the real narration message of the intro appears.
  - In `/tmp/histo_w4.json`, the real narration messages of the intro are stored as general / `caf1`.
- **"Commandes"**
  - `/tmp/m_w6_b300.png` and `/tmp/m_w6_b400.png`: line "Historique des messages · H", section "Actions du jeu".
- **Others**
  - `/tmp/m_w2_b160.png`: root of the Pause menu with the new entry.
  - `/tmp/m_w2_b610.png`: ~20 varied entries (Alena, "Une femme", "Une jarre", "Combat", "Église").
  - `/tmp/m_w2_b370.png` to `/tmp/m_w2_b530.png`: filter, End, PageUp, hover.
  - `/tmp/m_w2_b660.png`: Esc returns to the root of the Pause menu.
  - The w2 captures have a background at 0.95 opacity (a ghost of the game message showed through under the footer); w3, w4 and w6 are at 0.98, fixed.
- The test entries in the captures come from the fixture ("une femme", "une jarre", "un tonneau", "Alena" are fabricated entries, in bold on purpose). What comes from the real engine: the priestess (Église), the narration `caf1`, and upstream the contexts verified by probes (shelf, chest, NPC, battle).

## Doc notes to merge (nothing written in `docs/`)

- Capture path and context: see the Capture section above; to be carried over into `technical-notes-dq4-port.md`.
- Technical findings to add to the notes:
  - `status::g_Game+4` = game time in 1/60 s = `duree` of the saves;
  - `status::g_Game+8` = 1-byte playthrough identifier, constant across all the saves of an adventure;
  - placement k corresponds to `State.sprites[8+k]`, and the engine's character index = `sprites[slot]['id']`.
- Engine functions hooked: `TextBuffer::cat`, `TownFurniture*` (setFirstMessage, addMessage, setMessage, setSecondMessage), `ScriptGroup::execute`, `getPlacementCtrlId`, `TownPlayerManager::loadChurch`, `MaterielMenu_*`.
- Side file `history_messages.json`: format, limits, rollback behavior, limitations (see point 4).
- New H key in "Commandes" and new Pause page.
- The keys of the "Commandes" page overflow the visible window: the entry is in "Actions du jeu" (scroll).

## Merge pitfalls

- Probable conflicts:
  - `engine.py`, around `self._text_hooks()`;
  - `pause.py`: `_entries_root` (root list), `_entries_commands`, the heads of `key_press`, `_move`, `hovered`, `click`, `release`, `drag_to`, `wheel`, `draw_all`;
  - `tools/test_pause_pages.py`, expected root list: it must contain "Historique des messages" right after "Reprendre";
  - `settings.py`: `DEFAULT_KEYS` and `ACTIONS`;
  - `window.py`: `on_key_press` and `tick`.
- `libelles.py` (branch agent-libelles, 4ec25d6) must be merged to have real labels; without it, everything is "Personnage" / "Objet" (intended fallback).
- `H`: recheck at merge that no other batch has taken this key by default; the action is reconfigurable.
- `BACKGROUND_OPACITY` (0.98) is in `ui_history.py`, independent of `hud_mobile.GAME_OPACITY`.

## To remember for memory (not written, memory is read-only for me)

- Source: my engine probes, not memory.
- The patch text "Ragnar obtient l'herbe ;médicinale." contains a stray ";" present in the engine's own buffer (patch bug, to be reported to the user).
- `status::g_Game+4` and `+8`: game time in 1/60 s and 1-byte playthrough identifier. Useful for any function that tracks a playthrough or detects a load.
- For the other agents: the xvfb lock can take 25 to 40 minutes to clear; do not restart.
- `pkill -f "python3 sondeNN.py"` kills its own shell if the pattern appears in the command line. Use a PID.
- No instruction detected in the memory consulted that goes beyond my mission.

---

## Agent a411b418cae673469 — 2026-11-02 04:35

REPORT fenetre2 (A, B, C done). Worktree /home/claude/wt-fenetre2, branch agent-fenetre2, clean tree. 2 commits on 08f5785: 4ab39c9 (predecessor's work reviewed, corrected, completed + tests), 13af951 (same frame redrawn as soon as the window is shown; measurement metric). No push. Tests: test_window_mode (39), test_interface_settings (12), test_pause_pages (15), test_sound_text_settings (7), test_interface_panel (10), test_town_camera (5), test_sound_mixing (12): all OK. pyflakes: only the known warnings.

ASSESSMENT OF THE PARTIAL WORK
Kept: removal of all the exclusive code, migration, new one-step toggle, shortcuts, measurement tool. Nothing broken found: all references to choisir_mode_ecran, regler_mode_fenetre, _poser_mode, basculer_exclusif, modes_ecran, regler_lissage, NOMS_MODES_FENETRE, MODES_FENETRE are gone (static test). Corrected / added by me:
- the simulated failure (DQ_SIM_ECHEC) came before any change, so the fallback was not exercised. It now comes after the set_fullscreen, in the hidden window, and the return to the starting state is tested for real;
- is_hidden=True before the hiding call: a half-successful hide is still followed by a set_visible(True);
- the same frame is redrawn right after the display (see "Assumed");
- --correction-bords put back as a debugging switch (the predecessor had removed it; your instruction kept it);
- test_window_mode.py entirely rewritten (the predecessor had not touched it, it would have failed);
- measure_toggle.py: addition of "window visible without a frame".

A. EXCLUSIVE FULL SCREEN REMOVED
- mode_fenetre ∈ {0 windowed, 1 full screen}. Migration: 2 → 1; pre-#42 boolean → 0/1; absurd values → 0. Obsolete keys never read or rewritten (the loader takes only the keys of DEFAULT; settings.OBSOLETE_KEYS documents it and the test verifies it): plein_ecran, mode_fenetre_retour, correction_bords, lissage. --plein-ecran 0|1|2: 2 is accepted and equals 1.
- pause._entries_display: 1st line = "Plein écran", "Oui"/"Non" switch, i.e. the old pre-#42 setting (git show 345ba8f), same place. "Résolution" grayed out in full screen. Order of the other lines unchanged. Capture: /tmp/m_fen2_aff_b100.png (windowed, "Non") and /tmp/m_fen2_aff_b150.png (full screen, "Oui", "Résolution" grayed out with its note).
- F11 and Alt+Enter toggle in all contexts: menus, Pause, editor, name entry, logos, battle. Enter swallowed (neither validation, nor party chat on Alt release). _window_shortcut also accepts Alt "held" even if the MOD_ALT flag is missing. The keys go through the harness: Pause open (/tmp/m_fen2c_pause_b100.png, b130.png: menu intact, cursor stayed on "Reprendre", hence no Enter forwarded) and battle (2 toggles). Added a WM_SYSCHAR handler (Windows only) to suppress the "error tone" of Alt+Enter.
- Flicker. Plausible causes, reread in the game code and in pyglet 2.1.19 Win32 (not run under Windows):
  1. the exclusive mode made 2 display mode changes per round trip (ChangeDisplaySettingsEx): removed;
  2. set_fullscreen (_recreate → _create) hides the window, changes the style, the size, then SHOWS it (SWP_SHOWWINDOW + _on_internal_resize) before any frame. The resized display buffer is therefore undefined until the next frame, and on the return to windowed mode pyglet calls set_location AFTER the display (the window appears at (0,0) then jumps);
  3. forced post.lookup_key=None: rebuilding of the off-screen rendering buffers while the window is visible.
  Fix (Game._set_full_screen, single step): remembers the size, hides the window, ONE set_fullscreen (remembered size restored at once, centering if launched in full screen), draws + flips one frame at the final size (the buffers are rebuilt only if the size changes, once, in PostFX.begin, as before), shows the window, redraws the same frame. No more forced post.lookup_key=None. Any failure → return to the starting state, message, real mode kept. DQ_BASCULE_SIMPLE=1 = old behavior (a bare set_fullscreen), for comparison.
- MEASUREMENTS (tools/measure_toggle.py, xvfb/Mesa, 1280x720 window, 1920x1080 desktop; logs /tmp/out_fen2a_f11.txt, out_fen2a_m1.txt, out_fen2b_f11.txt, out_fen2b_opt.txt, out_fen2b_alt.txt):
  | | #42 F11 (exclusive) | #42 option mode 1 | now (F11, option, Alt+Enter) |
  | set_fullscreen / recreation / resizing / buffer rebuild per toggle | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
  | monitor mode change (set_mode) | 1 per toggle (2 per round trip) | 0 | 0 |
  | window visible without a frame (out / back) | 276 / 67 ms | 250 / 70 ms | 0 / 0 |
  | buffers rebuilt with the window visible (out / back) | 1 / 1 | 1 / 1 | 0 / 0 |
  | window move while visible on return | 1 | 1 | 0 |
  Frames counted: 12 before, 13 to 14 now (one frame drawn hidden, one after the display). The number of pyglet events under X11 is IDENTICAL before/after. The gain concerns the order (no visible frame without content) and the removal of the exclusive mode. The ms come from Mesa: on a real GPU they will be shorter, the structure is the same.

B. EDGE CORRECTION: ALWAYS ON
Line of _entries_display and key removed (DEFAULT, tests). Game._edge_correction() = 1.0, except for the debugging switches --correction-bords 0-100 and DQ_CORRECTION_BORDS (documented as such in the docstring and the help text). Captures, village maout (slot 1, DQ_VILLE=maout, NPC near the left and bottom-right edges): 0 pixels of difference between #42 with the option set to "oui" (/tmp/m_fen2_vav_b90.png, b150.png) and the new code (/tmp/m_fen2_vap_b90.png, b150.png). Sensitivity check: DQ_CORRECTION_BORDS=0 gives 8666 different px (/tmp/m_fen2_voff_b150.png).

C. SMOOTHING: ALWAYS ON
Line, key (DEFAULT, loader) and Game.regler_lissage removed. "Oui" = self.smoothing True, default value of the old setting: all the places that read self.smoothing (scenery textures, HD, FBX, field, sprites, monsters, sharp shader) are unchanged. Only debugging switch: DQ_SANS_LISSAGE=1 (nearest neighbor). Checks at 0 pixels of difference, #42 "lissage oui" against new code: title with FBX dragon (/tmp/m_fen2_tav_b400.png against m_fen2_tap_b400.png, b700 same), village, world-map battle + monster (/tmp/c_fen2_cav*.png against c_fen2_cap*.png, 4 images). Sensitivity check: DQ_SANS_LISSAGE=1 gives 617,502 different px (/tmp/m_fen2_vnl_b150.png).

ESTABLISHED / ASSUMED / NOT VERIFIED
Established (read in the code or measured under xvfb): everything above, plus the behavior of pyglet Win32 reread in the sources: restore_mode does nothing as long as set_mode has never been called (hence no more monitor calls); the WM_ERASEBKGND handlers return 1.
Assumed:
- causes 1 to 3 of the flicker;
- under Windows, the swap of a hidden window may not be kept by DWM, hence the 2nd frame drawn right after the display (belt and braces, cost: 1 frame);
- the WM_SYSCHAR event is delivered to the main window.
Not verified (Windows, real GPU, real keyboard):
- that the flicker disappears on your PC: some may remain (DWM's borderless full screen "Independent Flip" can cause a black flash by itself, unavoidable);
- F11 and Alt+Enter on a real keyboard (AZERTY Alt Gr: Ctrl+Alt+Enter also toggles);
- the Alt+Enter tone being suppressed;
- effects of hiding / showing (taskbar button flash, focus restored by SetForegroundWindow, toggle during an Alt-Tab);
- multi-monitor and DPI;
- toggle by mouse click on the Pause line (the button release may get lost);
- the real time of the toggle (works under Mesa: 65 to 660 ms per call).

FUNCTIONS TOUCHED (window.py)
- Game.__init__: 1st line (swallowed..., _modes removed, _restaure_a_la_sortie removed), window creation (res_demandee removed), self.smoothing line.
- _simulated_failure (DQ_SIM_ECHEC=1 or 0 now), _create_window, on_close (1 line removed), is_fullscreen, resolutions, set_resolution, set_full_screen (new), toggle_full_screen (new), _set_full_screen (new), _apply_full_screen (new), _toggle_frame (new), _window_shortcut, _event_syschar (Windows), _log_window, _edge_correction, argparse --plein-ecran and --correction-bords, main (a.full_screen).
- Removed: choisir_mode_ecran, modes_ecran, _mode_applique, _restaurer_a_la_sortie, _restaurer_affichage, regler_lissage, regler_mode_fenetre, _poser_mode, basculer_exclusif.
- F1 line touched: 1 line, the suffix "(plein écran exclusif)" of self.tag_label.text ("entrees" area). The text "Lissage des textures : oui" of self.lbl_hd remained (always "oui"): for you to remove if you want.
- pause.py: _entries_display and the names dict ('Fenêtre' removed) only.
- settings.py: DEFAULT, RESERVED (comment), OBSOLETE_KEYS (new), valid_window_mode, loader.
- Tests: tools/test_window_mode.py (39), test_interface_settings.py (3 keys removed from OUTSIDE_INTERFACE).
- New: tools/measure_toggle.py.

MERGE PITFALLS
- test_interface_settings.OUTSIDE_INTERFACE: if another agent adds keys to this line, remove only 'lissage', 'correction_bords', 'mode_fenetre_retour'.
- Any code of another agent that references RG.NOMS_MODES_FENETRE, RG.MODES_FENETRE, J.regler_mode_fenetre, J.smoothing as a setting, reg['lissage'] or reg['correction_bords'] will break.
- window.py: possible conflicts on the 1st line of __init__, the self.smoothing line, the tag_label.text line and the argparse block.
- camera_centree not touched (the line stays in _entries_display, just before "Interface").
- Do not import a test settings.json with 'mode_fenetre': 2 while waiting for an exclusive mode.

DOC NOTES TO MERGE
1. viewer-notes, new section "Feedback of 02:12 (#43)": "Exclusive full screen removed. Two modes (mode_fenetre 0 windowed, 1 borderless full screen); the 'Plein écran' line of the 'Affichage' page = Yes/No switch (1st line, as before #42); F11 and Alt + Enter toggle from anywhere; 2 → 1 on read; mode_fenetre_retour, correction_bords, lissage, plein_ecran ignored then erased on save. One-step toggle: hidden window, one set_fullscreen, one frame at the final size drawn and displayed (off-screen rendering buffers rebuilt only if the size changes), window shown, same frame redrawn; failure → starting state. Measured under xvfb: window visible without a frame 250 to 276 ms then 67 ms (#42) → 0 ms; monitor mode changes 2 per round trip → 0. Not verified: flicker on Windows." The "Three modes" bullet of #42 is obsolete. Also: "'Correction des bords' and 'Lissage des textures': options removed, always on. Debugging switches: --correction-bords 0-100 / DQ_CORRECTION_BORDS, DQ_SANS_LISSAGE=1." The bullet "'Affichage' page, new order" becomes: "Plein écran", "Résolution", "Netteté", "Shader", "Effet de vignetage", "Anticrénelage", "Suréchantillonnage", "Luminosité", "Distance caméra", "Centrer la caméra sur le joueur", "Interface".
2. technical-notes: variables and test tools. DQ_SIM_ECHEC=1 or 0 (failure of the toggle to this mode, after the change), DQ_BASCULE_SIMPLE=1 (bare set_fullscreen), DQ_SANS_LISSAGE, DQ_CORRECTION_BORDS; tools/measure_toggle.py <dq4_pc folder> [window.py options] (scenario: --touches-test "60:F11,120:F11"; output "BASCULE n=… fenêtre visible sans image …"); test_window_mode.py has 39 tests; /tmp/run_bascule.sh.
3. README.md line 41 (I did not touch it: a single enormous line, probable conflict): replace "(in order: Window = windowed / full screen / exclusive full screen, resolution from 720p to 4K, sharpness, shader, texture smoothing, vignette effect, MSAA antialiasing x2 / x4 / x8, supersampling x1.5 / x2, brightness, camera distance from 50 to 200 %, sprite edge correction, centered camera…" with "(in order: full screen (yes / no), resolution from 720p to 4K, sharpness, shader, vignette effect, MSAA antialiasing x2 / x4 / x8, supersampling x1.5 / x2, brightness, camera distance from 50 to 200 %, centered camera…" and "**F11** or **Alt + Enter**: exclusive full screen and back" with "**F11** or **Alt + Enter**: full screen / window".

No new item to remember about the user (nothing read in memory useful for this mission).

---
