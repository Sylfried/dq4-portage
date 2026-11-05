## Agent a42c065e6f40f0601 — 2026-11-02 11:08

REPORT CAR (maps, NPCs, switches, scripts) - worktree /home/claude/wt44-cartes, branch agent44-cartes, 5 commits on ab22007, clean tree. Nothing in /home/claude/dq4-portage, no push, user's saves not touched (tests in /tmp/sv_car_*). Harness outside the repo: /tmp/car44/ (hl44.py, sweep_*.py, gl_*.py, planche_*.png).

## 1. Table
Legend: E = Established, S = Assumed, NV = Not verified.

| ID | what | evidence | status | class | fixed? |
|---|---|---|---|---|---|
| CAR-1 | 32 maps came out EMPTY (0 vertices): mesh carried by the ROOT of the .fld, no `NNN_` child: 18 battle sceneries (btl_mt_*, btl_po_*, btl_sd_* = world mountain/marsh/desert, btldc1, btldh1, btldp8_*, btlta2, btltd1_*) + 14 places (ddb1b, dnb1b2, dnb2b3, dnb3b4, ev04, za1f6, za1f8, za1f9, za2f4-7, za2f9, za3f1) | pkl 0 vertices -> 294 to 4482; captures /tmp/car44/planche_racap1-2.png, planche_btlcam.png (ground view: mountain, marsh, desert OK, same structure as btl_pl_*); before/after: zero-vertex maps 32 -> 0 | E (data + captures); NV (real battle) | bug | yes 9986244 (+test) | - |
| CAR-2 | Materials without any texture (948 vertices, 21 places + 10 battle sceneries): `None` group ignored at drawing | pkl carte9 vs carte10; pixel diff | E; S (genre 'normal', 'trans' if _Color.a != 1) | oversight | yes 759744c (+test). Weak visible effect (<= 18 px in overview, 1 px in the close-ups deb3a/dmb3: surfaces under the water/ground) | - |
| CAR-3 | 3 NPCs never drawn: slot 8 of mom2f1, mqtf3, msm1f1 (ids 0, 157, 24): animated pose, never a position | The NPC record in the engine memory (Fix32 at LIB+0x26a688 + 0x1c0*(slot-8), +0 and +0x140) = (0,0,0); the engine sends only the positions that change; 9 points of the map tested, never a position. Real captures: /tmp/car44/gl/real1_b180.png (mqtf3), real1_b480 (mom2f1), real1_b780 (msm1f1): the NPC stands in the middle of the room | E (engine); S (Unity creates the Chara at the origin) | oversight | yes 9aa363d (+test). Sprite without position + pose received >= 3 frames after creation -> (0,0,0). The 262 other sprites receive their position 1 frame after creation: no spurious appearance (154 maps) | - |
| CAR-4 | Old savestate (.dqs): `savestates.apply` replayed only speeds + "Paramètres" button; widened places window (_widen_symbols) and g_isAmazon lost | test with a state whose bytes are those of the original image: fails before (192/448/788 instead of 1600), passes after | E | latent bug | yes b5e9e9c (Engine.reapply_fixes) | - |
| CAR-5 | Old carte9_ caches never purged (regex carte[0-8]) after the switch to carte10_ | test | E | oversight | yes b5669fe | - |
| CAR-6 | Persistence of chests / jars / doors (open, leave, come back, save, reload: suspend, adventure log, .dqs) | harness t_persist*.py, t_coffre*.py, t_portes.py: open chest = the engine returns `anim 3` (instant open) on entry, broken jar reappears, door = alpha then onoff, no state kept; the viewer writes NO scenario variable | E | decision (faithful) | not applicable | - |
| CAR-7 | NPC placement: 73 maps, 499 sprites (351 NPCs, 26 walkers), 600 frames each | 0 wall crossings, 0 sprites outside the footprint / under the ground / in the air (16 "in the air" = small platforms, verified with all the triangles); NPC heading: 0 = +z, 1 = +x, 2 = -z, 3 = -x (n = 3500 moves, 0 diagonals) = rows 0..3 of the sheet (planche_sprites.png); 8-row sheets (ids 106, 109, 115, 136, 137) heading 0..7; 10 real captures (planche_real2.png): feet on the ground, shadows, consistent | E | decision / OK | - | - |
| CAR-8 | 5 hidden sprites (packet 14, vis False): ev07 x3, mlb1a, mlout1 | N1 530 maps | E | decision (script) | - | - |
| CAR-9 | Maps not swept (141 out of 670): 21 `btl_*` + 119 `btl*` = 140 battle sceneries (not places) + za3f3 | N3 of the 140 done (bx_*, planche_bx_*); za3f3: the engine crashes in startTown (FldStage::getCameraLimitL, null pointer), data OK (8 groups); ev01 (title) same | E | decision | - | - |
| CAR-10 | N3 of the 530 places + 140 sceneries (overview) | 670/670 captures; metrics: 0 magenta, 2 almost empty (za2f6, za2f7: objects of 30 and 54 vertices); sheets looked at: 00, 01, 06, 09, racap 1-2, bx_0, deb3a, 10 real captures | E (metric 670); NV (sheets 02-05, 07, 08, 10, 11, bx_1-2: metric only) | - | - | - |
| CAR-11 | "Floating" objects (analysis of 1147 flagged) | refined with all the triangles: 123 resting on a small object, 323 attached to a wall, 43 free = stalactites `slhnk1a` (29), birds, balloon: normal. Chests: 21/25 on a platform (deb3a verified in capture), 4 furniture drawers | E | decision | - | - |
| CAR-12 | "Suspect" textures (71 maps) | null01.tim (alpha 0: invisible objects), kuro01.tim (black 8x8), srkr1: intended by the data; duplicates ddb5b (doors x4 at the same point), sjzf6 | E; S (duplicates without effect) | decision | - | - |
| CAR-13 | Scripts: 528 maps x ~212 frames (idle + conversation with the 1st NPC), 55 distinct cmd_* commands executed | all the types seen are decoded EXCEPT 16: 12 packets (mlb1a, mlm2f1, taf1; with cmd_character_action_sleep), 17: 2 (taf1; cmd_set_sleep_near), 33: 13 (ml* maps; 3 floats 1.25 / 0.65 / 0.75; cmd_setup, cmd_map_animation_a, cmd_setup_music, cmd_change_map_link); 6 and 18: 0; 13: 58,959; 27 (FieldData::setup) not decoded but useless (grid read from memory) | E (counts); NV (effects) | - | - ("paquets" agent) | - |
| CAR-14 | Only ~55 of the 445 cmd_* are reached outside the scenario; neither appearance/disappearance of NPCs by event, nor scenes played | - | NV | - | - | ~1 day: replay the chapter saves with the hooks of /tmp/car44/sweep_cmd.py |

## 2. Fixes (one commit each)
- b5e9e9c savestates.py + engine.py + tools/test_savestate_fixes.py: memory fixes replayed when a state is loaded.
- 759744c data.py + test_map_items.py + tools/test_map_textures.py: white texture, cache carte10_ (the rename has a cost: the maps are re-prepared at the first launch, ~80 s here for 670).
- 9986244 data.py + tools/test_root_scenery.py: root-mesh sceneries (32 maps). Same cache version carte10.
- 9aa363d engine.py + tools/test_maps_npcs.py: sprite never positioned = origin.
- b5669fe data.py + test_map_textures.py: purge of the carte9_.
All the tools/test_*.py pass (DQ_CACHE_CARTES=/tmp/cache44); pyflakes: only known warnings.
Files outside my scope touched: engine.py (State.apply: sprite creation line (key 'cree') and packet 13 pose block; constant ORIGIN_AFTER; method Engine.reapply_fixes) and savestates.py (one call) = zone of the "paquets" agent: risk of merge conflict on these two blocks.

## 3. Notes to merge into the docs
- Sceneries: 32 maps have the mesh on the root GameObject (no NNN_ child); object 0 = the root (za1f6, za2f6/7/9: `sNN_` children = sequence images). Material without texture = 4x4 white texture (key WHITE_TEX) x vertex color x _Color. Cache carte10_; carte[0-9]_ purged.
- null01.tim = transparent on purpose; kuro01.tim = black on purpose.
- Engine: character positions are sent only if they change; NPC record: LIB+0x26a688, step 0x1c0, Fix32 (x, y, -z) at +0 and +0x140; an NPC placed at (0,0,0) is never sent.
- NPC headings (4-row sheets): 0 = +z, 1 = +x, 2 = -z, 3 = -x; hero and 8-row sheets: 0 N, 2 E, 4 S, 6 W.
- Test teleportation: write x, y, -z (Fix32 x 4096) into g_cmnPartyInfo (LIB+0x269810) then startTown(map).
- Chest FCAN animations: 1 closed instantaneous, 2 opening (10 frames), 3 open instantaneous (returned by the engine on entry), 4 closing; jar: anim 2 = broken sequence then onoff; door: alpha then onoff; none of these states is persistent.
- Viewer writes into the engine: g_isAmazon (1), message speed option, walking speeds (reset to the original), cmp instruction of the "Paramètres" button, places window (3 immediates at 1600), Global.Flag bits (fade 0x1, effect 0x2), message queue (buf2), key queue (buf1); NO scenario variable. Read: Global.Flag, part (+0xee), FieldData grid, options, message state.
- Static packet emitters (UnityGetPacket): 5 FLDObject::SetCommonAnimation; 7 SetMapObjOnOff/SetMapUidOnOff; 12/13/14 SpriteCharacter + DisplayCharacter; 17 cmd_set_sleep_near; 19 FieldSystem/BillboardItem/TownPlayerEtc; 21 DSSAObject; 22 Dssa_G3_BeginMesh; 27/28/29 FieldData; 31/32 ModelObject + TownMapEffect; 34 Global::SetScreenEffect. The other types go through another unidentified path.
- Risk: a .dqs does not write the game's save files: loading a state then the title may show a more recent save (normal).

## 4. Not verified
- Real appearance in battle of the 18 new sceneries (approximate ground view on 4 only: btl_mt_d/e, btl_po_d, btl_sd_d; no random encounter played); `_battle_background` is applied only to the 21 `btl_*` sceneries (the other 119 have no fallback background: to be seen in a castle battle).
- Scenarios (chapters): NPCs that disappear/appear, scene actors (risk of an actor placed at (0,0,0) a few frames before its real position: same behavior as Unity, not seen).
- Real effects of packets 16, 17, 33 (only counted).
- N3 sheets not looked at one by one (7 out of 15); Windows / real GPU.
- Scenery duplicates (ddb5b, sjzf6): no visible defect, not inspected closely.

---

## Agent a6564d55a4c288220 — 2026-11-02 12:14

FINAL REPORT, mission "town services and vehicles" (prefix SRV). Worktree /home/claude/wt44-services, branch agent44-services, 1 commit (6d39f59) on ab22007. Clean tree. No push, no real save touched (writes in /tmp/sv_NOM), no FR patch file touched.

SUMMARY
- All the service windows (shops, bank, church, inn, status, equipment, Nène, hostage, Torneko's shop, arena) are rendered correctly by the viewer (real GL captures). A single real bug found and fixed: the Status pages did not turn with the keyboard.
- The vehicles (boat, balloon, wagon) exist and are drawn. The world map does draw the models 4289, 4279, 4232 and 4233, whereas the doc said "never drawn". That is false as soon as the chapter and the flags are forced.
- The engine has a single common entry point for all these menus: `window::CommandWindow::changeShopMenuPhase(TownWindowSystem::m_singleton, phase)`. By calling it directly (after `MaterielMenu_WINDOW_MANAGER::getSingleton()+0x10 = 0`), I can play any service without going through the script conditions.
- All the user's real saves are at chapter 1 (data1 `mak1f1`, data2 `caf1`, data4 `field`, data5 `dab1`). The following chapters can only be reached by forcing (chapter + flags).

1) TABLE OF FINDINGS
Legend: E = Established (observed), S = Assumed, NV = Not verified. Classes: D = decision, O = oversight, B = bug.

| ID | what | evidence | status | class | fixed? | otherwise effort |
|---|---|---|---|---|---|---|
| SRV-01 | Church: priest (66), adventure log list (54), save (56), writing data*.dat | /tmp/m_eg1_b_eglise.png, /tmp/srv/sheet_eg4.png; /tmp/sv_eg4 (data1, data5, data9 written), keyboard | E | – | – | – |
| SRV-02 | Church: "Résurrection" / "Pénitence" (67) | /tmp/srv/sheet_eg5.png | E (rendering, flow). "Divination", "Bénédiction", "Purification": NV. Mouse at the church: NV | – | – | low: play each entry |
| SRV-03 | Weapon shop (phases 2, 8): root 57, list 58 with ◀ ▶ quantity, "Qui va le porter ?" (60), sale 62. Gold and bag correct, keyboard AND mouse | /tmp/srv/sheet_bt2a.png, bt3, bt4, bt5; /tmp/m_bt6_*.png (mouse) | E | – | – | – |
| SRV-04 | Armor shop (3) and item shop (4), direct call. Purchase ×3 with the keyboard (D D): 3000 G → 1950 G (armor, 3 × 350) and 3000 G → 2976 G (herbs, 3 × 8). Sale: +660 G, item removed | /tmp/out_shop2a.txt, /tmp/out_shop2b.txt | E | – | – | – |
| SRV-05 | Type 59 (2nd variant of the purchase list) never opened: all the lists seen are type 58. Type 63 (quantity to sell) never opened: this version sells item by item, each herb is a line at 6 G (p. 2 and 3 of the sale list). List pages with the keyboard OK (D turns the pages) | /tmp/out_shop3.txt | E (63 unreachable in chapter 1); 59 NV | D | – | – |
| SRV-06 | Inn (phase 0), direct call: gold 3000 → 2988 (12 G), "Oui" / "Non" with the keyboard AND the mouse, "Non", insufficient gold ("Cela me gêne…"), fade to black then fade in, message "Bonjour ! J'espère que vous avez…" | /tmp/srv/sheet_au3.png, sheet_au4.png | E | – | – | – |
| SRV-07 | Inn via the real NPC (script): the condition is `cmd_is_talked_at_shop(1)`, i.e. bit 2 of `[personnage+0x3c]` (speech across the counter). This bit is set by `TownCharacterManager::checkTalkingNearCharacter` only if `TownStageManager::checkCrossNum(héros, PNJ)` ≠ 0, and it is cleared otherwise. Forcing the bit is not enough. Tests: ring from 0.6 to 2.2 around the NPC (id 0 of `may1f1`, at (-2.74 ; 3.27)), 8 directions: always the "Hugues Esclin" dialogue | scripts, disassembly 0x21e8a0 and 0x1ccf6c | NV (lying-down poses of packets 16-18, HP/MP healing, full night by the script) | – | – | medium: find the customer-side cell of the counter |
| SRV-08 | Bank = phase 16 (maps `hcm2f1`, `hcy1b1`, `ss5b1b`), not a type of its own. Root 57 ("Dépôt" / "Retrait" / "Rien"), 64 "Déposer combien ?", 65 "Retirer combien ?", 6 digits of which only the first 3 have ▲ ▼ (amounts in thousands). With the mouse: deposit 3000 → 0 G, withdrawal 0 → 3000 G | /tmp/srv/sheet_ph16.png, sheet_bank1.png, /tmp/out_bank1.txt | E (mouse) | – | – | – |
| SRV-09 | **Bank with the keyboard: impossible to enter an amount.** Z and D have no effect on 64. `_menu_input` retains only the buttons with pad & 0x10, so the ▲ ▼ of the columns (pad 0x2 / 0x1) are never targeted. Same cause as the casino bet | /tmp/out_bank1.txt ("T64 apres clavier" identical to "T64") | E | O | NO: falls under the ▲ ▼ generalization by the "casino" agent | to be replayed after merge: ◀ ▶ will also be needed to choose the column |
| SRV-10 | **Status (types 13-17): Q / D / L / R / PageUp / PageDown do not turn the pages with the keyboard.** Cause: window without a grid or A button; `_menu_input` converts ◀ ▶ into pads 2 / 1 sent to a window that ignores them. Only the click on the arrows (type 6) worked | /tmp/out_stat2.txt (before) and /tmp/out_stat2b.txt (after) | E | B | **YES, 6d39f59** | – |
| SRV-11 | Field menu: 2×2 root ("Objets", "Magie", "Carac.", "Divers"), "Objets" (9) with page 1/3, commands (8) "Utiliser" / "Transférer" / "Équiper" / "Abandonner", tooltip (10), "Équiper" ("Ragnar s'équipe de l'épée de cuivre."), Status 4 pages (13, 14 equipment, 15 usual spells, 15 battle spells) | /tmp/srv/sheet_menu2.png, sheet_m3a.png | E | – | – | – |
| SRV-12 | Menu spells (type 7): "Magie" on a party without a caster gives a message only. No save with a caster (data1, data4, data5: Ragnar without MP; data2 starts on a dialogue) | /tmp/out_m3b.txt, /tmp/out_m3c.txt | NV | – | – | chapter 2-5 save with Alena / Mina or Doc: see §4 |
| SRV-13 | `cmd_menu_extra_shop` = phases 18 (arg 0) and 19 (arg 1). Phase 18: root 57 "Acheter" / "Vendre", repeated purchase of herbs at 8 G. Phase 19: "Accepteriez-vous de nous en vendre ?" (62, title "Vendre") | /tmp/out_ph18.txt, /tmp/out_ph19.txt, /tmp/srv/sheet_cdf1.png | E (windows). Actual sale NV: the chosen item is a weapon, refused | – | – | low |
| SRV-14 | `cmd_menu_nene` = phase 24: item list (9) + "Oui" / "Non", the item "Lance de fer" disappears from the list | /tmp/out_ph24.txt | E. Type 70 (NENE_ItemView): never opened, NV | – | – | – |
| SRV-15 | `cmd_menu_hostage` = phase 23: "Qui choisir ?" (type 21), party list with "PV", "PM", "Att", "Déf", message "Vous voulez échanger le détenu…". Doc's level is displayed "Nv.: ?": engine text | /tmp/srv/sheet_ph23_28.png | E | – | – | – |
| SRV-16 | Torneko's shop (type 69) = phase 28 (`mfw1f1`): list "Épée de cuivre" 100 G / "Dague divine" 200 G / "Arc de chasseur" 350 G, negotiation by messages and "Oui" / "Non". The frame is tall with an empty bottom (3 lines out of 6?) | /tmp/srv/sheet_ph23_28.png | E (rendering). Full sale NV (outside chapter 4); frame size: S | – | – | low |
| SRV-17 | Martial arena (68, phase 22; `cccf2`, `cmd_menu_colosseum` args 1 to 5): HP window and message "Princesse Alina… herbes médicinales… ?" are displayed. After "Oui", the engine crashes in `MaterielMenu_MARTIAL_COLOSSEUM::checkHaveYakusou`: member with index -1, chapter 1 party instead of that of chapter 2. Artifact of the forcing, not a viewer bug | /tmp/out_ph22b.txt, /tmp/srv/sheet_ph22b.png | E (display); full flow NV | – | – | chapter 2 save |
| SRV-18 | Phase 12: type 44 "Acheter combien ? 3000G / 0G / Acheter", in a town (`hcy1b1`, `ss5b1b`). Phases 5 and 11: token exchange, message only with 0 tokens. "casino" domain: to be passed on to them | /tmp/out_ph12.txt, /tmp/out_ph5.txt | E (window 44); 5 / 11 with tokens NV | – | – | – |
| SRV-19 | Phase 17 (mini medals, `shf1`, `hcy1b1`): message only without medals | /tmp/out_ph16.txt (phase 17 launched separately) | E (message) | – | – | – |
| SRV-20 | Boat, chapter 4 → 5 (script `field` g4, global flags 204 = 1 and 205 = 0, chapter 4): the models 4289 (slots 10 and 11) sail, the hero 4202 is hidden, "Terre en vue !", fade, disembarking, chapter title (messages on black), then `cmd_menu_save`. Camera that follows | /tmp/srv/sheet_sh1.png, sheet_sh1b.png, /tmp/out_sh1.txt | E | – | – | – |
| SRV-21 | Balloon: chapter 5 + global flag 344 = 1: model 4279 (slot 12) drawn with the touch HUD. No movement verified (test ball2 abandoned) | /tmp/srv/sheet_ball1.png | E (drawing); movement NV | – | – | low |
| SRV-22 | Wagon: chapter 5 + flag 388 = 1: horse 4232 (slot 1) and wagon 4233 (slot 2) follow the hero, in a line behind him when he walks | /tmp/srv/sheet_car1.png, sheet_car2.png | E | – | – | – |
| SRV-23 | Raft (`deb1`, `deb2a`, `deb3a`, `dnb4`, `dnb6`, `hhout`, g3 / g5), henge (`cjf2b`, `cjout` g5), wagon call (`ev07` g1 / g5, `srout`), `cmd_set_ship_pos` (`mrout`), whistle, Rura (`cmd_set_ruura_lock` in 54 maps, no interface) | scan of the 397 scripts | NV | – | – | medium: force chapter 3-5 + flags |
| SRV-24 | Credits: `cmd_the_end` (`mlb1a` g9, two variants depending on the global flag 0x1af) launches `TownEndrollManager::startTheEnd`. With chapter 9 + `startTown('mlb1a')`, the g9 script does not start within 3000 frames (flag 0xa4 stayed at 0, hero locked) | /tmp/claude-0/…/scratchpad/p17.py, p18.py | NV | – | – | medium: find the start condition of the scriptobject g9 o0 |
| SRV-25 | "Surechigai": `zaout` g1 o1 (NPC slot 8) chains `cmd_surechigai_mapname` (= phase 31, no window), `make_taishi`, `change_surechigai_part`. After the speech the hero stays locked (position frozen for 1400 frames). No script leads to `zaout`, and no other code calls `Global::startSurechigai` | scripts + /tmp/claude-0/…/scratchpad/p22.py | E (locking in the test), unreachable in normal play | D (online feature) | – | – |
| SRV-26 | `cmd_menu_present_exp` (`caf1` g1 o28, chapter 1; `ckf3f5` g5): the NPC (slot 35) is absent from the sprites in chapter 1 | p21.py | NV | – | – | appearance flag to be found |
| SRV-27 | Phase 13: the engine crashes (undefined phase). No script uses it | p15.py 13 | E | D | – | – |

2) FIXES PER COMMIT
- 6d39f59, "Status (types 13-17): Q / D / L / R turn the pages with the keyboard" (SRV-10), window.py, +3 lines in `_menu_input`, just before `if f.get('grille') or len(z) < 1:`.
  - A window without a grid or A button now sends ◀ ▶ (pads 8 / 4) to the port that carries the page arrows, via `_port_for_gamepad`.
  - Before, keyboard only (/tmp/srv/scen_stat2.py): R, D, PageDown, A, Q, PageUp leave "1/4".
  - After: R 2/4, D 3/4, PageDown 4/4, R 1/4 (loop), A 4/4, Q 3/4, PageUp 2/4.
  - pyflakes: a single warning, `window.py:2203 'sel'` unused, prior to my commit. `tools/test_entries.py` (37 tests) and `test_pause_pages.py` (16 tests) pass.
- Files touched: only `dq4_pc/window.py`. Nothing outside window.py / ui_menu.py / engine.py.

3) NOTES TO MERGE INTO docs/ (ready to paste)

**technical-notes-dq4-port.md, "Town services: `cmd_menu_shop` phases" (2026-11-02, SRV mission)**
- All the service menus go through `window::CommandWindow::changeShopMenuPhase(TownWindowSystem::m_singleton, phase)`. `__cmd_menu_shop::initialize` calls `TownCharacterManager::setPlayerDirection(placement)`, then this function, then sets `MaterielMenu_WINDOW_MANAGER::getSingleton()+0x10 = 0` and `g_cmnPartyInfo+0x974 = placement`.
- A service can be played without a script: set `[MaterielMenu_WINDOW_MANAGER+0x10] = 0` then call `changeShopMenuPhase(m_singleton, n)`. Phase 13: the engine crashes.
- Phases used by the 397 scripts:
  - 0 inn, 1 church, 2 weapons, 3 armor, 4 items; 6, 8, 9, 10 = variants of 0, 2, 3, 4;
  - 5 and 11 = token exchange; 12 = token purchase (type 44);
  - 16 = bank (types 57, 64, 65); 17 = mini medals;
  - 18 and 19 = `cmd_menu_extra_shop` (arg 0 and 1);
  - 22 = `cmd_menu_colosseum` (arg in `MaterielMenuPlayerControl+0x18`); 23 = `cmd_menu_hostage`; 24 = `cmd_menu_nene`;
  - 28 = Torneko's shop (type 69); 31 = `cmd_surechigai_mapname` (no window).
- Windows observed:
  - 57 root ("Acheter" / "Vendre" / "Rien", or "Dépôt" / "Retrait" / "Rien");
  - 58 purchase list (◀ ▶ = quantity per row);
  - 60 "Qui va le porter ?";
  - 62 sale list (one line per item);
  - 64 and 65 bank: 6 digits, ▲ ▼ on the first 3 (thousands);
  - 44 token purchase; 68 arena (HP and "Oui" / "Non"); 69 Torneko's shop;
  - 21 "Qui choisir ?" (hostage); 9 item list for Nène.
- Never opened in chapter 1: 59 (2nd purchase variant), 63 (quantity to sell: one sale = one item), 70.
- Inn: the speech condition is `cmd_is_talked_at_shop(1)`. It reads bit 2 of `[TownCharacterBase+0x3c]` (`getCounterTalk`), set when `TownStageManager::checkCrossNum(héros, PNJ)` ≠ 0 (counter cell between the two).
- Chapter: `status::g_Story` is the object of `StoryStatus::setChapter(g_Story, n)`; the value is at `[g_Story+4]`. To play a chapter script: load save 4 (world map), `setChapter`, set the global flags (L+0x25b3d8, bit n), call `Global::startField()`.

**Vehicles (world map `field`)**
- Models: 4289 (×2, slots 10 and 11) = boat; 4279 (slot 12) = balloon; 4232 (horse) and 4233 (wagon) = slots 1 and 2 when the party gets into the wagon; 4202 = hero (slot 0, hidden during navigation).
- The sentence of the technical-notes "slots 10 to 12 created without ever receiving a position: not drawn" holds only outside the scenario.
- Chapter 4, g4: flag 205 = 0 and 204 = 1 → boat arrival, chapter title, `cmd_set_chapter 5`, `cmd_menu_save`.
- Chapter 5: flag 344 = balloon, 388 = wagon, 343 = boat (S, not tested).

**viewer-notes-dq4-pc.md**
- Test keys: B = BACKSPACE (not Esc, which opens the Pause and freezes the loop), Menu = Enter, up / down = Z / S, left / right = Q / D, L / R = A / R.
- Status: Q, D, L, R turn the pages (6d39f59). Inn: fades OK. "Oui" / "Non" with the mouse OK.
- Bank and casino bet: no keyboard entry until the ▲ ▼ are generalized.

**coverage.md §2, status updates**
- 56: Seen in game (writing of data1, data5, data9). 57, 58, 60, 62: Seen. 64, 65: Seen with the mouse, keyboard absent. 66, 67, 69, 68, 44, 21: windows seen. 59, 63, 70: never opened (unreachable in chapter 1).
- 8, 9, 10, 13 to 15: Seen. 7: NV.

4) NOT VERIFIED (with what would be needed)
- Windows and real GPU: everything above comes from Mesa under xvfb (1280×720).
- Inn via the real NPC: lying-down poses (packets 16-18, "paquets" agent), HP/MP healing, full night. One must stand on the customer side of the counter of `may1f1`.
- Menu spells (7) and out-of-battle healing: save with a spellcaster (chapters 2 to 5, Alena / Mina / Doc with MP).
- Arena (chapter 2, party Alina / Kiryl / Borya), Torneko's shop and credits (chapters 4 and 9), hostage (`cip1b1`, chapter 5), `hcm2f1` (Nène in chapter 3: NPC absent without a flag), extra_shop with a sellable item.
- Bank and types 64 / 65 with the keyboard; token entry (44); phases 5 and 11 with tokens.
- Balloon movement, piloted boat (g5, flag 343), raft, henge, whistle, Rura, wagon call (`ev07`).
- Credits `mlb1a` g9 does not start when forced; Surechigai unreachable.
- Mouse at the church; "Divination" / "Bénédiction" / "Purification"; type 59.

5) USEFUL CAPTURES (absolute paths, /tmp)
Sheets: /tmp/srv/sheet_eg4.png (save), sheet_eg5.png (67), sheet_bt2a.png, sheet_bt3.png, sheet_bt4.png, sheet_bt5.png (weapon shop), sheet_au3.png, sheet_au4.png (inn), sheet_ph16.png, sheet_bank1.png (bank), sheet_menu2.png, sheet_m3a.png (field menu and status), sheet_sh1.png, sheet_sh1b.png (boat), sheet_ball1.png, sheet_car1.png, sheet_car2.png (balloon, wagon), sheet_cdf1.png, sheet_ph23_28.png, sheet_ph22b.png.
Individual captures: /tmp/m_bt6_*.png (mouse, shop), /tmp/m_eg1_b_eglise.png, /tmp/m_eg4_05_liste.png.
Test saves: /tmp/sv_eg4/data1.dat, data5.dat, data9.dat.
Logs: /tmp/out_<nom>.txt.
Tools:
- /tmp/srv/run_srv.sh (GL launcher with generator scenarios; ABSOLUTE scenario path mandatory), /tmp/srv/gl_srv.py, /tmp/srv/lib_scen.py;
- scenarios: scen_phase.py (PHASE, PH_ARG, PH_COINS), scen_field.py (F_CHAP, F_FLAGS, F_N, F_WALK), scen_npc.py, scen_bank.py, scen_shop2.py, scen_shop3.py, scen_menu2.py, scen_menu3.py, scen_stat2.py;
- engine-only probes in /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/: outils44.py, hl44.py, scripts.py, tabcmd.json, p15.py to p22.py.

6) MERGE PITFALLS
- window.py `_menu_input`: my insertion (3 lines) is just before `if f.get('grille') or len(z) < 1:`. The "casino" agent modifies the loop `for bit, pad in dirs` just below. Probable textual conflict but trivial: keep both blocks. After merge, replay /tmp/srv/scen_stat2.py (must end 2/4, 3/4, 4/4, 1/4, 4/4, 3/4, 2/4) and /tmp/srv/scen_bank.py (the keyboard entry of the amount must change the digits).
- For the "paquets" agent: the inn played by direct call does not show the lying-down poses (no script). To be looked at via the real NPC.

7) TO REMEMBER (for memory, learned in this session)
- The user's real saves are all at chapter 1 (data1, data2, data4, data5; data3 empty). Source: decoding with /tmp/specs/dq4_sauvegarde.py.
- The /tmp/xvfb.lock lock is shared between all the agents: the GL scenarios wait several minutes each (source: /proc/locks).
- `pkill -f pattern` also kills the calling shell if the pattern appears in the command: use PIDs.
- In a GL scenario: B = BACKSPACE, Esc = Pause (blocks the loop), Menu = Enter.

---
