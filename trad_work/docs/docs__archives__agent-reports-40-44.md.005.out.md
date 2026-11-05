## Agent a4b9be7dca00268af — 2026-11-01 22:13

REPORT agent-recherche (worktree /home/claude/wt-recherche, branch agent-recherche, base main 1e87ca6, no push). 2 commits: 48333ba (investigation 2) and 69e588f (investigation 1). Clean tree.

=== ANSWER FOR THE USER (to be relayed as is) ===

INVESTIGATION 1: darken or arrow?
On mobile there is not really a choice between the two: they are two unrelated things.
- The darkening is the "pressed" state. It exists only for the finger. When you put your finger on a button, the game sets it to "pushed": the plate changes pattern (texture offset), or, for a button that is just an icon, its color goes to 75%. As long as the finger stays on the button, it stays dark. If you slide the finger off the button, it lights back up; if you come back, it darkens again. You release on the button to confirm.
- There is NO selection arrow in the mobile menus, nor any keyboard/gamepad cursor. So on mobile there is no "hover" either: you press or you do not press.
- The arrows you see in the game have other roles: the golden ▶ of the battle turn (BattleUpCursor), the ◀ ▶ page-change buttons, the ▲▼ on some plates, and the ▼ at the end of a text page. They are not selection markers.
- The "cursor" message that the engine sends ([4,n]) is ignored by Unity.
So your PC convention (yellow frame for the mouse, arrow for the keyboard, darkening on click) is a consistent PC addition: only the darkening on click comes from the original.
Discrepancy fixed in the viewer: a pressed ◀ ▶ page arrow did not darken (it only lightened on hover), and a plate stayed dark if the mouse left the button during the press. This is fixed: pressed arrow at 75%, plate/arrow that light back up when the pointer leaves and darken again when it returns.

INVESTIGATION 2: the "Morph" spell
- It is not a battle spell: it is a story event (church, the frog/rabbit and Élisa). The effect is a small animated cloud (model 5902, 29 frames, sound 361) displayed on the character who transforms.
- You were right about the order: the cloud was drawn BEHIND the character (and slightly shifted, because the viewer's camera is not the engine's). In Unity it is drawn after the characters, hence in front. Fixed: in front, and anchored to the character.
- The latency came from the first display: the texture of the cloud was only loaded at the moment it appeared (2.7 s measured, versus 0.05 s once in memory). Fixed: these effect textures (186) are now prepared in the background with the rest (the first preparation takes about 3 s more, only once).
- The other effects (prologue slashes, battle, title) were compared before/after: identical.

=== DETAIL BY POINT ===

Commits (messages ending with Co-Authored-By + Claude-Session, two separate lines):
- 48333ba Town: mesh effects in front of the characters and anchored to them; effect textures m\d{4} prepared in the background. Files: dq4_pc/fenetre.py, dq4_pc/donnees.py.
- 69e588f Menus: pagination arrow pressed darkened x0.75 and lit back up if the finger leaves. Files: dq4_pc/fenetre.py, dq4_pc/ui_menu.py.
pyflakes: only the known warnings (selected, racine, em, ax); 'struct' unused in data.py already existed. py_compile ok. Regression: click on the Items window pixel-identical.

--- Investigation 1: Established / Assumed / Not verified ---
Established (GameAssembly disassembly, RVA):
- MenuPortItem.Update 0xD0670C: pushState 1 (press) -> SetPush(true); 2 (held) -> SetPush(isHit), so sliding outside lights it back up; 3 released. SetPush has only 4 callers: only touch drives "pushed".
- MenuParts.IButton: plate (DisplayClass5_0.b__0, 0xD043CC): pushed = texture offset (0.1875; 0); icon button (ctor(Material) 0xCFF9C8, DisplayClass6_0.b__0 0xD0469C): Material.color = 0.75 on the 4 RGBA channels; variant without effect.
- No selection arrow/cursor for buttons in the mobile build. Arrows: BattleUpCursor, page buttons (part 10), ▲▼ on plates, ▼ MenuMessage.
Assumed: the original tests the first touched button in the order of m_buttonList, the viewer takes the topmost (no difference seen).
Not verified / not coded (proposed): the `etat` state driven by the engine for the icon buttons (<0 hidden, otherwise 0.75) is ignored by the viewer (only the plates use it); `_is_button` accepts only parts 7 and 10 whereas 22 icon nodes exist (16 part 10, 6 part 3); the PC's keyboard/gamepad cursor is rendered as a darkened plate (PC addition, mobile has none).
Captures: /tmp/rech/fleche_cmp.png, /tmp/rech/fleche_av.png, /tmp/rech/fleche_ap.png, /tmp/rech/plaque_cmp.png; raw /tmp/m_e1fl_*, /tmp/m_e1pl_*.

--- Investigation 2: Established / Assumed / Not verified ---
Reproduction: savestates recorded headless (engine ~700 frames/s, very fast, versus slow xvfb), church scene mlb1a (Élisa sprite 143, frog 174, rabbit 173). Three successive Morphs verified.
Established:
- (a) packet 21 [0, 5902] on mesh slot 0 -> texture m5902 (32x32), shader 3 DssaCharaTransparent, 29 frames, SE 361. Frog splash in the river: model 5917 (64x64). Prologue slashes: 5303/5311. battle_effect.py is not concerned (it is the tile burst at the start of battle).
- (b) latency: cold synchronous loading of m5902 from the datapack via UnityPy: 2718 ms at the first draw (52 ms when warm, 8.8 ms after preparation). Measured with DQ_TEMPS_IMAGES. Logs: /tmp/rech/ft_cold.txt, ft_warm.txt, ft_apres.txt.
- (c) order: render queues read from the datapack: Chara 3000, CharaShadow 2999, DssaChara 3100, DssaMonster0 3150, DssaMonster1 3200, DssaCharaTransparent and Riseup 3850 (ZTest Always, billboard). The effects therefore come after the sprites. The engine places the effect in the middle of the segment (engine camera -> sprite); the real Unity camera = engine position + 4.0 forward, pitch -0.2; the viewer's town camera (zoom, cam_dec, yaw, angle_cam) is different, hence the offset.
Fixes: effect drawing block moved after sprites and icons (without depth test for shader 3, without depth write); _anchor_effects/_effect_pos/_game_border: find the targeted sprite (t in ]0.05; 1.5[, residual < 0.05), memorize the depth ratio and the angular offset, and replay them in the frame of the viewer's camera with the interpolated position of the sprite (fallback: position unchanged). data.py: 'effets' list (m\d{4}, 186 textures) added to _elements and prepare.
Regressions identical: prologue slashes (frames 226-277), title screen, battle.
Captures: /tmp/rech/planche_av.png / planche_ap.png (angle -2.25); planche0_av.png / planche0_ap.png (angle 0); planche_m3.png, planche_m4.png (2nd and 3rd Morph); planche_frog_av.png / planche_frog_ap.png / diff_frog62.png (splash); raw /tmp/m_morph_*, /tmp/m_morph0_*, /tmp/m_m3_*, /tmp/m_m4_*.
Assumed: exact size and placement of the original cloud (no capture of the real game); the Morph of the night in the destroyed village (b0065000 line 63, copy of the hero) follows the same mechanism but was not reproduced.
Not verified: whether a monster casts Morph in battle; link between id 5902 and a file assets/effect/eNNN.dssa (no e5902.dssa, files e001..e919); latency of the first SE 361 (sound out of scope, tested --sans-son); possible "pop" of the sprite HD modes (EPX...) on the effect texture (background task).

--- Merge traps ---
- data.py modified out of scope (6 lines: _elements + prepare). preparation.json is rebuilt once (key 'effets' absent = stale list).
- window.py: the mesh-effects block was removed from the town branch of _draw and reinserted after the icons, before self.prog.stop(); _step gains tick + _anchor_effects + _log_timing; new attributes anchor_effect and _view_border (init + _apply_savestate); end of _town_camera memorizes _view_border; _battle_meshes has a parameter town; _game_border duplicates part of _town_camera (to be resynchronized if this camera changes).
- Investigation 1 also touches window.py: on_mouse_drag (self.mouse), block wnd.selected_node/press_node in the menu loop (~l.1771), editing mode (wnd.press_node = None). Likely conflicts with the Pause / interface editor / display agents.
- Old battle savestates (/tmp/sv_b1) incompatible with the current code (AttributeError 'systeme'), in both trees; new savestate: /tmp/rech/svc.

--- Test recipe ---
Prologue: saves Downloads (/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735), slot 2, then mlout1 -> church -> talk to Élisa. The headless scripts are /tmp/rech/lib.py (Pilote) and h1..h19.py. Captures via /tmp/run_wt.sh, tokens @x@y hover, !x!y press, ^x^y drag.

--- To remember (learned here) ---
- Headless engine ~700 frames/s; viewer tests under xvfb slow; test mode = one engine step per loop frame (deterministic) (observed while testing).
- Morph scene: prologue save (Downloads folder above), slot 2, mlout1 -> church -> talk to Élisa.
- Sprites: 174 frog, 173 rabbit, 143 Élisa. Effect models: 5902 Morph, 5917 splash, 5303/5311 slashes.
- The user's saves are called "Solo" / "Sofià" (seen in the save folders).
- The mobile build has no selection cursor for buttons; the port's cursor is a PC addition (disassembly of MenuPortItem.Update).

---

## Agent a43c4de91404229b5 — 2026-11-01 22:19

REPORT agent-textes (worktree /home/claude/wt-textes, branch agent-textes, base main 1e87ca6)

COMMITS (2, clean, two-line footer; working tree clean; pyflakes: only the known warnings racine / ax / selected)
- 86428e2  Menu texts: original SE-GARRIR font, without compression (chapter banner, plates)   [points 2 and 4]
- eb2d216  Shops: left / right change the quantity of the selected row   [point 3]
- Point 1: no commit (nothing reproduced, no code changed).
Files touched: dq4_pc/ui_menu.py (+99 / −13 in the font commit) and dq4_pc/fenetre.py (+3 lines, in `_menu_input`). pre_game.py unchanged (`hyodai1` is already in RESOURCES there, `ap_hyodai1.png`).
A last pass over the code after the rebase (church shop, slot 1, Garrick font) is correct: /tmp/txt/fin1_sheet.png.

POINT 1: prologue text on a black screen — UNRESOLVED
- Established: engine message 200119 = "@a@bEt c'est ainsi que commence notre histoire...\n@c0@" (without "*:" prefix, empty name). The Unity layer (`MenuMessage`, RVA 0xCFA4B4, `NoticeReceive` 0xCFBA34) has only 4 canvas types (frames 192/193/194/194), type 0 being the bottom box. `NoticeReceive` only acts on param[0] = 0..4: canvas type, cursor + render on/off, shake (8), texture offset (scrolling), "who speaks" text. No frameless, centered or letter-by-letter mode exists on the Unity side. The text is a 512x512 canvas rendered by the engine.
- Tried without success: direct call of `TownWindowSystem::openMessage` (shows nothing in exploration, because `CommandWindow::MESSAGEWINDOW` first calls `InputControl::goNext(8)`, which is refused); a full run of the prologue by script (slot 2, captures /tmp/m_pro1_b2000..2750.png, summary /tmp/txt/pro1_sheet.png) only reached free exploration: you have to walk to the house before dinner, which is too long to automate.
- Assumed: the original displays this text as a normal type 0 message (bottom box, same Garrick font as the menus, the engine drawing the canvas). If the defect seen by Sylfried is real, it would come from the context (touch buttons / HUD over the black, fades, position of the box in the 16/9 window; `--msg-origine` keeps it at its portrait place) and not from the window. A capture from Sylfried (or from the mobile) at that exact moment would be needed to settle it. Not verified: the look of the original.

POINT 2: chapter banner — FIXED
- Established: the menu font in language 1 (English, that of the French patch) is the Unity bitmap font SE-GARRIR (Font "Garrick", serif, 20 px, line spacing 23.525, ascent 18.887, 218 glyphs including the French set, atlas 256x256, bilinear filter), not GMaruGoPro-M (Japanese, wrongly used by the viewer). Sources: `MenuParts..cctor` 0xD03278, `LangParam.Apply` 0xCFD5E8, `SystemInit` 0xCF9A70, `CreateBuildTextMenu` 0xD02074. 1 px of font = characterSize × 0.1 unit; width = sum of the advances (no kerning). "Flipped" glyphs = transposed in the atlas.
- Banner image: the only existing chapter texture is `Menu/map/hyodai1` (450x225, fitted to the width); `Make_Chapter` (type 12) = `hyodai1` quad + text node 1532 (param 0, anchor 1, z 30) and node 1558 (param 1, anchor 4, z 17.5); the title arrives in node 1558. The image was already displayed; only the font was wrong. No additional resource in RESOURCES.
- Implementation: class `BitmapFont` + `extract_garrir` (ui_menu.py); `prepare_resources` extracts `ui_garrir.json` and `ui_garrir.png` from base.apk (optional files: without them, fallback to GMaruGoPro-M). `Render._text` uses the original metrics.
- Captures: /tmp/txt/cmp_chapitre.png (before | after), /tmp/txt/avant_chapitre.png (taken in the middle of a fade, hence darker), /tmp/txt/apres_chapitre.png.

POINT 3: shops — FIXED (keyboard and touch verified)
- The keyboard cursor keeps the whole row. In types 58 / 59 (Make_ShopBuy) and 63 (sale quantity), left / right (movement ZQSD, camera arrows, L / R) send `[port, 1, rangée, 8 ou 4]`, like the touch of an arrow (the rows carry pad 16 + ◀ 8 + ▶ 4 under the same buttonId).
- Established: the engine only does ±1 (quantity 1 to 9 with wraparound, the other rows return to 1). There is no ±10 in the original, so it was not added.
- Verified: keys (1→2→3, row 2, wraparound at 9) and clicks on ◀ ▶; before, the keys did nothing. Captures: /tmp/txt/shk2.png (after, keyboard), /tmp/txt/shm.png (after, touch), /tmp/txt/shkb.png (before), /tmp/txt/shq.png (shop flow), /tmp/txt/shs.png and shs2.png (sale), /tmp/txt/cmp_achat.png, cmp_qui.png, cmp_vente.png.
- Not verified: type 28, type 63 (sale quantity screen not reached).
- Shop test: `changeShopMenuPhase(phase)` via the harness opens a shop (2 = weapons, 3 = armor, 0 = inn, 1 = church).

POINT 4: alignment with mobile — DONE by construction
- Cause: the viewer used the wrong font (GMaruGoPro-M) and in addition compressed the texts that were too wide. The text / plate gaps are now those of the mobile (the text overflows as on mobile, with no compression or foreign font), which Sylfried accepted.
- BEFORE / AFTER captures of several windows: /tmp/txt/ba4_sheet.png (before) and /tmp/txt/aa4_sheet.png (after), 2x2 grid: item list, item menu, characteristics, "Divers"; separate archives avant_liste_objets / avant_menu_objet / avant_caracteristiques / avant_divers.png; pairs cmp_achat / cmp_qui / cmp_vente / cmp_chapitre.png.
- Assumed: vertical placement about 1 px lower (TextMesh anchoring model). Not verified: no capture of the real mobile for a pixel comparison.
- `DQ_POLICE_GMARU=1` restores the old font (comparison).

ESTABLISHED / ASSUMED / NOT VERIFIED (summary)
- Established: SE-GARRIR font and its metrics; banner chain (`Make_Chapter`, `hyodai1` the only image); shop quantity mechanics (±1, 1..9); shop keys and clicks; message 200119 without special mode on the Unity side.
- Assumed: the original displays the prologue text in a normal box; vertical offset of 1 px.
- Not verified: the original look of the prologue text; types 28 / 63; pixel comparison with mobile.

MERGE TRAPS
- ui_menu.py: changes in `Render._text` and `Texts.__init__`, plus new class `BitmapFont` (before `Texts`) and `extract_garrir`; the comments of `LINE_HEIGHT` / `FONT_SIZE` mark them as fallbacks. Conflict probable only if another agent touches `_text`.
- window.py: a single block of 3 lines inserted in `_menu_input` before the "single column" test.
- The new optional files `ui_garrir.json / png` make base.apk be re-read once by `prepare_resources`; the existing caches remain valid (fallback if absent). All menu text changes font: the captures of the other agents (start menu, pre-game text, etc.) will change appearance, this is expected.
- pause.py and the interface editor preview (window.py) still use `ui_font.otf` (GMaruGo): not touched (out of scope).
- Private test cache: /tmp/uicache_txt (ui_garrir.* present); the test script deletes /tmp/m_NOM*.png, hence the archiving in /tmp/txt/.

NOTES FOR docs/ (I wrote nothing in docs/)
- docs/technical-notes-dq4-port.md (text layout, around l.85-100) is wrong for language 1: the menu font is SE-GARRIR (bitmap, 20 px, line spacing 23.525, ascent 18.887, 1 px = characterSize × 0.1), not GMaruGoPro-M; no text compression.
- Chapter title: text node 1558 of `Make_Chapter`; image `Menu/map/hyodai1` alone.
- Shops: types 57 (root), 58 / 59 (Make_ShopBuy: pad 16 + ◀ 8 + ▶ 4 per row), 60 / 61 ("Qui va le porter ?", arrows buttonId −1), 62 (sale), 63 (sale quantity); quantity 1..9 handled by the engine.
- Harness tip: `DQ_APPEL="image:symbole:args"` with /tmp/h_appel.py calls an engine function; `changeShopMenuPhase(phase)`: 0 inn, 1 church, 2 weapons, 3 armor.
- Prologue text: message 200119, `MenuMessage` has only 4 canvas types; any special rendering would be on the engine side.

TO REMEMBER (memory, source: IL2CPP and engine analysis of this session)
- The original EN / FR menu font is SE-GARRIR (Unity bitmap); the technical notes wrongly say GMaruGoPro-M.
- `changeShopMenuPhase(phase)` opens a shop (2 weapons, 3 armor).
- SE-GARRIR atlas: the "flipped" glyphs are stored transposed.

USEFUL CAPTURES (absolute paths): /tmp/txt/cmp_chapitre.png, /tmp/txt/aa4_sheet.png, /tmp/txt/ba4_sheet.png, /tmp/txt/shk2.png, /tmp/txt/shm.png, /tmp/txt/shkb.png, /tmp/txt/cmp_achat.png, /tmp/txt/cmp_qui.png, /tmp/txt/cmp_vente.png, /tmp/txt/fin1_sheet.png, /tmp/txt/pro1_sheet.png.

---
